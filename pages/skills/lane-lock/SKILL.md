---
tier: 2
type: skill
name: lane-lock
id: SKILL-LANE-LOCK
title: "lane-lock v1.0.1 — cross-agent advisory coordination"
version: 1.0.1
status: active
date: 2026-05-20
last_updated: 2026-05-21
description: "Ship 2 doctrine for atomic lane control plane: fcntl-locked lane tokens, scope-glob enforcement, lock-then-claim handshake, parented heartbeats, RULE 7 pre-commit gate, queue→OpenBrain dedup, status_daemon reaper. Use when starting a new agent session, declaring lane scope, debugging zombie locks, extending the queue, or adding a new lane. Substrate-mediated, fcntl-locked, scope-glob-typed."
absorbs_laws: []
absorbs_lessons: []
tags: [skill, lane-lock, ship-2, control-plane, 2026-05-20]
source_count: 0
related: [model-failover, session-coordination, mistake-to-skill, musk-algorithm]
---

# lane-lock v1.0.1

## Why this exists

Before Ship 2, multi-agent coordination on the Nous repo was pure convention. No file locks, no heartbeat, no per-lane parity. Session 56 had two sessions independently author conflicting `satory_bdl` files because the pre-action handshake was skipped. The s1030 + s108 peer-session race during this very ship absorbed each other's COORD file by accident (one session's `git add -A` after a stash-pop pulled in the peer's in-flight handshake page and the conflict was only caught at push time). This skill codifies the atomic spine that prevents both classes of conflict going forward.

Ship 2 (waves 1-5, commits `f297b822` → this commit) shipped: `lane_lock.py` (token + scope-glob + history.jsonl), `queue.py` (atomic tasks.jsonl + TASK_QUEUE.md render), `status_render.py` (STATUS.md dashboard), `handshake.py` (lock-then-claim session-start), `queue_to_openbrain.py` (fire-and-forget capture + cursor dedup + weekly digest), `heartbeat_lane.py` (parented detached heartbeat), `status_daemon.py` (30s reap + render), `pre_commit_lane_check.sh` (RULE 7), launchd plist, plus 80+ tests across 8 Ship-2 test files. This SKILL.md is the doctrine all future lane work pulls from.

## Current rules

- Four lanes: `claude`, `codex`, `grok`, `opus`. Each lane operates inside its declared scope; cross-lane writes go through `tools/lane_lock.acquire(lane, scope_paths)` first.
- `pages/systems/lane-locks.json` is the active-locks state file (atomic temp+rename writes under `fcntl.LOCK_EX` on `logs/lane-locks-state.lock`).
- `pages/systems/lane-locks.history.jsonl` is the append-only audit log (`acquired` / `heartbeat` / `released` / `reaped_stale` / `conflict` events).
- Token format: `lk-<lane>-<uuid8>-<unix_ts>`. Default TTL 300s. Heartbeat extends by 90s. Expired tokens auto-released by next `list_active()` call or by `status_daemon` every 30s.
- Scope-path glob rules: `tools/*` = single-segment-narrow for code roots (`tools`, `agents`, `tests`); `tenants/*` = dir-prefix recursive for data/tenant scopes; `**` = recursive everywhere.
- The queue at `pages/systems/tasks.jsonl` (shadow) + `TASK_QUEUE.md` (rendered) is the SOURCE OF TRUTH for what each lane is working on. Mutations go through `tools/queue.py` (fcntl-locked, atomic render).
- Session-start handshake (`tools/handshake.py start --lane <L>`): lock-then-claim. If the lock fails (overlapping scope), refuse and emit a Telegram-ready nudge. If the lock succeeds but the queue.claim races and fails, release the lock immediately (no zombie locks).
- Pre-commit RULE 7 (`tools/pre_commit_lane_check.sh`) refuses commits whose staged paths don't match the lane's active lock globs. Bypass: `--no-verify` only (no env-var bypass).
- Heartbeat is per-session, forked at session start (`tools/heartbeat_lane.py --session-id <S> --parent-pid <PID>`), `os.setsid()`-detached, dies when the parent dies — no orphan heartbeats.
- `status_daemon` runs every 30s via launchd (`com.nous.status-daemon.plist`); reaps stale locks + re-renders `STATUS.md`. `STATUS.md` is runtime-only and ignored by git because it contains volatile `last_render` and live dirty-count fields. Synchronous render also happens on every queue mutation.
- Queue events flow to OpenBrain via `tools/queue_to_openbrain.py` (fire-and-forget Popen). Dedup via `pages/systems/queue-openbrain-cursor.jsonl`. Sunday 03:00 KZT weekly digest aggregates 7 days of done tasks into one retro thought.

## Anti-Patterns

### AP-1: Lock-acquire WITHOUT scope

**Symptom:** A lane acquires `acquire(lane, [])` "to get started" and then any subsequent staged path satisfies RULE 7 by default (empty scope = nothing to match against = nothing to refuse).

**Fix:** Never call `acquire(lane, [])` — empty scope means "no paths," which is meaningless and would let any staged path bypass RULE 7. Always declare concrete `scope_paths`. The CLI rejects empty `--scope`; programmatic callers MUST pass at least one glob.

### AP-2: Heartbeat from a different process tree

**Symptom:** A heartbeat process outlives the agent session it was supposed to track. TTL extends indefinitely because no parent-death signal ever reaches the heartbeat loop. Stale lock sits on the substrate; status_daemon never reaps it because heartbeat keeps it fresh.

**Fix:** Heartbeat MUST be the child of the session it's heartbeating, with `--parent-pid` set to the actual parent. `tools/heartbeat_lane.py` `os.setsid()`-detaches but polls `os.kill(parent_pid, 0)` every cycle and exits the moment the parent dies. A heartbeat that outlives its agent is worse than no heartbeat.

### AP-3: Claim BEFORE lock

**Symptom:** Lane A calls `queue.claim(task_id, session_id)` first, then tries `lane_lock.acquire(...)` and the lock fails because lane B already holds an overlapping scope. The task is now claimed (in tasks.jsonl) but no work can proceed; meanwhile lane B does its work and Lane A's claim looks "in progress" forever.

**Fix:** Always lock first, then claim. The reverse opens a window where a concurrent lane could claim+work the same task because lock acquisition is the only authoritative gate. `handshake.py start` enforces lock-then-claim and releases the lock immediately on claim failure (no zombie locks).

### AP-4: Bypassing RULE 7 with env var

**Symptom:** A lane sets `NOUS_LANE_BYPASS=1` to "just commit this one thing" and the pre-commit hook silently approves. The path doesn't match the lane's scope; peer lanes are unaware their files are being written.

**Fix:** `NOUS_LANE_BYPASS=1` is NOT honored. The only escape hatch is `git commit --no-verify`, which requires explicit human keystrokes. If you find yourself routinely bypassing, the lane scopes are wrong — fix the scopes, not the hook.

### AP-5: Stash-and-pop across sessions

**Symptom:** Mid-ship, peer sessions race on `git pull --rebase`. Lane A runs `git stash --include-untracked && git pull --rebase && git stash pop`. The popped state includes the peer session's untracked WIP files (e.g. peer's HANDSHAKE doc); lane A then `git add -A` and commits all of it as its own. The peer session loses its WIP authorship attribution and a conflict-on-rebase surfaces only at push time.

**Fix:** When peer sessions are writing to the repo, the stash-and-pop dance is fine for completing a rebase, but the popped state belongs to the OTHER session. Never `git add -A` after pop — only commit your own files via `git commit -o <paths>` (per `session-coordination` v1.33.0 AP-5). The s1030/s108 absorption race during Ship 2 is the canonical example.

### AP-6: Queue mutations outside `tools/queue.py`

**Symptom:** A helper script appends a row to `pages/systems/tasks.jsonl` directly to "save a CLI call". The next `status_render` reads a half-written row and emits a corrupt `TASK_QUEUE.md`; downstream lanes see a phantom in-flight task that doesn't exist.

**Fix:** Never write to `tasks.jsonl` directly. The shadow + view atomicity depends on the locked + atomic-render path in `queue.py`. Direct writes WILL corrupt the rendered view. All mutations go through `tools/queue.py {add|claim|done|requeue}`.

### AP-7: OpenBrain cursor without dedup

**Symptom:** `queue_to_openbrain.py` is called twice for the same `task_id` (e.g. caller retries on a transient Popen exception); two `task_completed` thoughts land in OpenBrain; the weekly digest now double-counts.

**Fix:** Re-emitting a `task_completed` thought duplicates effort. The cursor at `pages/systems/queue-openbrain-cursor.jsonl` is the dedup source of truth. If a capture's Popen raises, the cursor is NOT updated — retry-safe. Always go through `queue_to_openbrain.emit_done(...)`; never call `mcp__openbrain__capture` directly from queue handlers.

### AP-8: Hardcoded session ID

**Symptom:** Two processes spawn with the same `session_id="opus-1"` (copy-pasted from a doc); both heartbeat the same lock; the ownership check passes for both; on parent-death of one, the other keeps the heartbeat alive — but the lane_lock's `owner_session_id` is now ambiguous.

**Fix:** Always derive `session_id` at runtime (`<hostname>-<pid>-<unix_ts>`). Reusing a `session_id` across processes breaks the heartbeat ownership check. `handshake.py start` auto-generates a unique session_id; never override it from a doc.

### AP-9: Tracking volatile STATUS.md

**Symptom:** `com.nous.status-daemon` is healthy and rewrites `STATUS.md` every 30s, but the Air wiki is permanently dirty because `STATUS.md` is tracked and includes `last_render`, active lock ages, and dirty-count fields.

**Root cause:** A runtime dashboard was treated as source. The daemon and a clean git tree had incompatible contracts: every successful render changed the tracked file.

**Fix:** `STATUS.md` is a generated runtime artifact, not source-of-truth substrate. Keep the renderer and daemon, but remove `STATUS.md` from git tracking and ignore it. Durable control-plane state remains in `pages/systems/lane-locks.json`, `pages/systems/tasks.jsonl`, `pages/systems/parity-latest.json`, and the queue/history JSONL files; the dashboard is only a view.

## Timeline

- **2026-05-21** | v1.0.0 -> v1.0.1 — AP-9 codified after Air launchd proof showed `com.nous.status-daemon` healthy but impossible to reconcile with a clean working tree while tracked `STATUS.md` carried volatile render timestamps. Removed `STATUS.md` from git tracking and ignored it; daemon remains on Air as runtime view generation. No new LESSON (RULE ZERO).
- **2026-05-20** | v1.0.0 created by Ship 2 of the god-tier 3-ship plan (waves 1-5). APs absorbed from the session 56 conflict (two sessions authoring conflicting `satory_bdl` files without handshake) and the s1030/s108 COORD absorption race during this very ship (peer-session `git add -A` after stash-pop absorbed the peer's HANDSHAKE doc). 80+ tests across 8 Ship-2 test files (`test_lane_lock.py`, `test_queue.py`, `test_status_render.py`, `test_handshake.py`, `test_queue_to_openbrain.py`, `test_heartbeat_lane.py`, `test_status_daemon.py`, `test_parity_check.py`, plus the `test_pre_commit_lane_check.sh` harness) prove the doctrine on Mac. Wave commits: `f297b822` (wave 2: queue.py), `728900d5` (wave 3b: handshake.py), `c7c2b0b1` (wave 3c: queue_to_openbrain.py), `f8687e61` (wave 3a: status_render.py), `32d01ed5` (wave 4: heartbeat_lane + status_daemon + plist), this commit (wave 5: SKILL.md + verify_ship2_e2e.sh). Plan: `/Users/madia/.claude/plans/from-gpt-implemented-the-delightful-riddle.md` §5. Next: Ship 3 (unified library graph) per §6.

## See also

- [[model-failover]] — Ship 1's atomic substrate; lane-lock builds on its parity manifest and fcntl-lock pattern. Ship 1's `_mutate_state` lock discipline is the template for lane_lock's `acquire`.
- [[session-coordination]] v1.33.0 — pre-existing advisory pattern for cross-session anti-collision; lane-lock formalizes its mechanism (fcntl, scope globs, RULE 7) without bumping that page (peer-session scope during Ship 2). AP-5 stash-and-pop draws directly from session-coordination v1.33.0 AP-5.
- [[mistake-to-skill]] — 7-day SLA absorption that catches new APs surfaced by lane-lock failures. When a lane-lock failure repeats ≥2× in 7 days, dream_cycle proposes a version bump to this skill.
- [[musk-algorithm]] — 5-step elimination ethos: AP-1 (no empty scope) deletes a category of false-positive locks rather than patching them. Ship 2 applied step 2 (delete) by removing the env-var bypass entirely rather than gating it.
- `pages/plans/from-gpt-implemented-the-delightful-riddle.md` (mirror at `/Users/madia/.claude/plans/from-gpt-implemented-the-delightful-riddle.md`) — the operating plan this skill was extracted from. §5 (Ship 2) is the wave-by-wave spec; §6 (Ship 3) is the next ship.
