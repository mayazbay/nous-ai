---
tier: 2
type: skill
name: model-failover
id: SKILL-MODEL-FAILOVER
title: "model-failover v1.0.1"
version: 1.0.1
status: active
date: 2026-05-20
last_updated: 2026-05-21
description: "Doctrine for atomic failover ledger, orphan sweep, parity verification, resume-prompt-v2, OpenBrain capture, and weekly mistake-to-skill absorption. Use when /resume fires, sweeper materializes orphans, designing new failure paths, debugging cross-host parity drift, or extending the failover engine. Substrate-mediated, fcntl-locked, fail-soft on side channels. v1.0.1 adds AP-7: tests importing command_center must patch failover side effects or isolate the wiki path before exercising /ask routing."
absorbs_laws: [LAW-001, LAW-013, LAW-015, LAW-017]
absorbs_lessons: []
tags: [skill, failover, resume, parity, openbrain, dream-cycle, ship-1, 2026-05-20]
source_count: 0
related: [mistake-to-skill, session-coordination, musk-algorithm, karpathy-coding-principles, library-grade-audit, ceo-hierarchy, command-center, session-operating-contract, gbrain-ops, openbrain-projection, agent-quality]
---

# model-failover v1.0.1

## Why this exists

The original failover ledger (commit `4cdabaf7` by GPT, ~2026-05-19) shipped a Telegram failover Markdown writer that worked on the happy path only. The 2026-05-20 audit (plan `pages/plans/from-gpt-implemented-the-delightful-riddle.md`) surfaced seven structural defects: (1) the lock was released BEFORE `git push`, so concurrent writers could interleave their ledger appends with conflicting pushes; (2) `started` rows with no paired `finished` row accumulated forever as ghost work; (3) the ledger file existed at zero bytes — no live mutation had ever exercised the path; (4) `/resume` never re-checked parity post-resume, so a host could resume against drifted substrate without notice; (5) no provider-health gate before declaring failover — a transient 429 looked identical to a permanent rate-cap; (6) token-budget accounting was absent — there was no way to know whether `original_model` had failed because it ran out of headroom or because it crashed; (7) repeated failures never absorbed into a skill — every recurrence was a fresh surprise.

Ship 1 (Steps 1-9, commits `f6869658` → `85f00f37`) made the ledger atomic, orphan-aware, parity-tracked, OpenBrain-captured, and skill-loop-integrated. This SKILL.md is the doctrine all future failover work pulls from. 77 tests across six files (`test_failover_schema.py`, `test_failover_sweeper.py`, `test_model_failover_state.py`, `test_parity_check.py`, `test_provider_probe.py`, `test_command_center_failover_resume.py`) prove the doctrine on Mac. Ship 2 (atomic lane control plane) and Ship 3 (unified library graph) build on top of this substrate.

## Current rules

- The ledger at `pages/systems/model-failover-ledger.jsonl` is append-only, schema-validated on read via `tools/failover_schema.parse_row`. Malformed rows quarantine to `pages/systems/model-failover-ledger.broken.jsonl`; the original file is never rewritten.
- Every `_mutate_state` call writes a WAL row to `logs/model-failover.wal` BEFORE the ledger append. `git push` happens OUTSIDE the lock; failed pushes are retried by `tools/failover_sweeper.py` reading WAL `pushed=false` markers older than 60s.
- `latest_state()` pairs started+finished by `event_id`. A `started` row with no matching `finished` AND age > `ORPHAN_TIMEOUT_SEC` (15 min) is reported as `status='abandoned'` with a synthetic in-memory finish. The sweeper materializes synthetic abandoned rows to the ledger on its next pass.
- Before declaring failover, `tools/provider_probe.py` runs a 200ms cheap probe per provider (anthropic / openai / xai / deepseek) with exponential backoff `[2, 4, 8, 16]s`. Only on terminal failure does `/resume <lane>` route to a replacement provider.
- Every `_mutate_state` ALSO calls `tools/parity_check.compute_and_write(wiki)` inside the lock, which hashes the files listed in `pages/systems/parity-manifest.txt` and writes `pages/systems/parity-latest.json`. Air and VPS run `tools/parity_check.py --verify` after every `git pull` — drift → exit 1, stop.
- `build_resume_prompt_from_state` returns the `[RESUME-v2]` template (Plan §4.6) with: event_id, original_model, failure_reason (timeout/rate_limit/crash/token_cap/abandoned/provider_down), token budget (placeholder for future), packet+handoff+parity sha256s, live provider-probe result, CONTRACT block.
- Every non-ok terminal status (error/timeout/abandoned) fires `_capture_openbrain_event` (fire-and-forget `subprocess.Popen` with `start_new_session=True`; log to `logs/openbrain-capture.log`) and `_append_mistake_to_skill` (deduped JSONL append to `pages/skills/mistake-to-skill/ledger.jsonl`).
- The `dream_cycle.py` weekly digest reads the mistake-to-skill ledger and proposes version bumps on this SKILL.md.

## Operations

### Atomic write protocol (`_mutate_state`)

Under a single `fcntl.LOCK_EX` on `logs/model-failover-state.lock`:

1. `mutation_seq := _next_mutation_seq(wiki)` — monotonic sequence number.
2. Append WAL row `{mutation_seq, event_id, ts, pushed: false}` to `logs/model-failover.wal`, fsync.
3. Append ledger row to `pages/systems/model-failover-ledger.jsonl`, fsync.
4. `render_latest(wiki)` — atomic temp+rename of `pages/systems/MODEL-FAILOVER-LATEST.md`.
5. `_recompute_parity(wiki)` → `parity_check.compute_and_write(wiki)` writes `pages/systems/parity-latest.json` atomically. Fail-soft: exceptions log to stderr but never abort the mutation.
6. `git add` + `git commit --allow-empty` (no network) — timeout 15s.
7. Release fcntl lock.

Outside the lock:

8. `git push origin main` (best-effort, timeout 45s).
9. On returncode 0: append second WAL row `{same mutation_seq, fresh ts, pushed: true}`, fsync.
10. On push failure: stderr log; sweeper retries on next cadence.

### Orphan sweeper (`failover_sweeper.py`)

- 10-min launchd cadence (`~/Library/LaunchAgents/com.nous.failover-sweeper.plist`, pending install).
- Two timeouts: `ORPHAN_TIMEOUT = 15min` (started with no finished pair), `WAL_TIMEOUT = 60s` (WAL row with `pushed: false`).
- For each orphan: append synthetic `finished` row with `status="abandoned"`, `abandonment_reason="orphan_timeout"`. Fires the mistake-to-skill append + OpenBrain capture per side-channel rules.
- For each unpushed WAL row past `WAL_TIMEOUT`: re-runs `git push`, marks `pushed: true` on success.

### Provider probe (`provider_probe.py`)

Before declaring failover from `<original_model>` to `<replacement_model>`, probe `<original_model>` with `[2, 4, 8, 16]s` backoff (200ms timeout each). If any probe succeeds, resume the original. Only on terminal failure does the resume route to the replacement.

### Resume prompt v2 (`build_resume_prompt_from_state`)

The `[RESUME-v2]` header carries `event_id`, `original_model`, `replacement_model`, `failure_reason`, packet_sha256, handoff_sha256, parity_hash, probe result, and a `CONTRACT` block forbidding the worker from asking Madi to restate context. The prompt always includes four substrate pointers: `AGENT-CONTINUITY-PACKET.md`, the latest HANDOFF, `MODEL-FAILOVER-LATEST.md`, and `parity-latest.json`.

### Side-channel writes (`finish_event` epilogue)

After `_mutate_state` returns, `finish_event` re-reads `latest_state(wiki)` to get the paired (started+finished) row. If status ∈ {`error`, `timeout`, `abandoned`}, two fire-and-forget helpers fire:

- `_capture_openbrain_event(state, wiki)` — `subprocess.Popen([...], start_new_session=True)`. Failures log to `logs/openbrain-capture.log`. Never blocks.
- `_append_mistake_to_skill(state, wiki)` — append deduped row to `pages/skills/mistake-to-skill/ledger.jsonl`. `dream_cycle.py` reads this weekly and proposes a version bump for this skill if the same failure_reason appears ≥2× in the last 7 days.

### Cross-host parity verification

`tools/parity_check.py --verify` is the STOP gate Air and VPS run after `git pull --ff-only`. It recomputes the manifest hash for the local working copy and compares against `parity-latest.json`. Mismatch → STOP and report, never auto-resolve.

## Anti-Patterns

### AP-1: Lock released before push

**Symptom:** A second writer acquires the lock between the first writer's lock release and `git push`. The two pushes race; one fails with non-fast-forward; ledger appears append-consistent locally but cross-host drift is silent.

**Why this happened:** The original (`4cdabaf7`) released `fcntl.flock(..., LOCK_UN)` before `git add + commit + push`. Two concurrent writers could both clear the lock, then both commit, with no ordering guarantee.

**Fix:** Never let `git push` run outside the same lock window as the ledger append. Step 3 (`13c40c47`) reordered so commit happens inside the lock and push happens outside but with sweeper retry. If you find a code path that mutates ledger state and pushes outside an fcntl lock without WAL backing, fix it — do not paper over with sleeps.

### AP-2: Orphan starts never expire

**Symptom:** `latest_state` returns a `started` row from a session that crashed two days ago; the dashboard reports the lane as "in-flight"; nothing triggers resume; the user assumes the original worker is still working.

**Why this happened:** The original code returned orphans as "running" forever because it had no concept of `ORPHAN_TIMEOUT_SEC`. There was no pairing logic — `started` without `finished` was indistinguishable from "in progress".

**Fix:** Never assume `latest_state` returning a `started` row means the work is in-flight. After 15 min with no finish, treat it as abandoned. `latest_state` is orphan-aware (`c86fb710`); the sweeper materializes synthetic abandoned rows on the 15-min cadence so the ledger has a durable receipt. New failure paths MUST integrate with `find_orphans` — never bypass.

### AP-3: Embedding-claim theatre

**Symptom:** Log line says "embedded 12 chunks" when the underlying embedding API returned an error and the database write rolled back. Down-stream consumers act on the success log; debugging takes hours because the receipt was a lie.

**Why this happened:** The audit found this pattern in gbrain — success log lines printed unconditionally at the end of a function, before checking return codes or row counts. Ship 1's failover ledger explicitly bans the same shape: `finish_event` only logs success after `_mutate_state` returns and the ledger row was confirmed appended.

**Fix:** Never print "embedded N chunks" / "wrote N rows" / "captured N events" success log lines when N is zero or when no actual operation happened. Ship 3 (library graph) bans this codebase-wide via `tools/test_no_lying_logs.py` (to be added). In this skill: every "success" log line MUST be guarded by a check that the operation actually mutated state.

### AP-4: Synchronous OpenBrain capture

**Symptom:** `/resume` hangs for 30+ seconds when OpenBrain MCP is slow or down; the user retries, doubling the load on the already-slow side-channel.

**Why this happened:** A synchronous `mcp_call(...)` (or any `.wait()`) inside `_capture_openbrain_event` blocks the resume thread on a network round-trip.

**Fix:** Never `.wait()` on the OpenBrain subprocess. Use `subprocess.Popen` + `start_new_session=True`. Stderr → `logs/openbrain-capture.log`. If the MCP CLI is missing or hangs, the failover handler MUST complete unaffected. Landed in `85f00f37`.

### AP-5: Parity hash assumed stable

**Symptom:** A handoff says "parity 4cdabaf7 across mac/air/vps/github" and the next session trusts it; reality is that two of the three hosts haven't pulled since, and the SHA in the handoff was a git commit SHA, not a content-parity proof.

**Why this happened:** The original commit `4cdabaf7` declared parity using the git SHA — but a git SHA only proves "these commits are reachable", not "the working trees agree". Manifest drift can survive a clean `git pull` if a file is generated, gitignored, or sourced from a non-tracked path.

**Fix:** Never assume the manifest hash didn't drift. Re-run `parity_check.py --verify` after every `git pull` on every host. Mismatch → STOP and report; never auto-resolve. The parity manifest's listed file order is part of the hash input — never reorder existing rows; only append, and recompute the reference hash everywhere immediately.

### AP-6: Schema laxity

**Symptom:** An unknown `phase` value lands in the ledger from a future code path; `latest_state` silently skips it; resume picks up a stale `finished` row instead of the real terminal event; the user sees stale context after resume.

**Why this happened:** Early ledger readers used `try/except` to skip parse errors, swallowing real bugs. There was no quarantine path — a corrupt row was indistinguishable from "no row".

**Fix:** Never let an unrecognized phase or missing required field land silently. `failover_schema.parse_row` returns a `BrokenRow` for every malformed input; the caller MUST quarantine to `pages/systems/model-failover-ledger.broken.jsonl`, not skip silently. Adding new phases or fields requires extending `failover_schema` first — the schema is the contract.

### AP-7: Operator-routing tests must patch failover side effects

**Symptom:** Running `python3 -m pytest tools/test_operator_boundaries.py tools/test_daily_0300_substrate_sync.py -q` from the real wiki produced a stream of local commits named `model-failover: capture latest lane state` and left `MODEL-FAILOVER-LATEST.md`, `model-failover-ledger.jsonl`, and `parity-latest.json` dirty. The test was supposed to verify Telegram/operator routing, not mutate production failover state.

**Why this happened:** `tools/test_operator_boundaries.py` patched `_run_openclaw`, `_run_codex`, and Telegram sends, but it imported the real `command_center.py`. The `/ask` path starts a failover event before the mocked worker call and finishes it afterward. Those wrappers call `model_failover_state.start_event/finish_event`, which append the ledger, render latest state, recompute parity, and run git commits against the real wiki.

**Fix:** Tests that import `command_center.py` and execute `handle("/ask ...")` must patch `command_center._failover_start` and `command_center._failover_finish`, or must redirect the failover wiki path into a temp repo before the route executes. Mocking the worker is not enough. `command_center._failover_capture_enabled()` also defaults failover capture off under `PYTEST_CURRENT_TEST`; use `NOUS_FAILOVER_CAPTURE=1` only when a test intentionally exercises the real ledger in an isolated temp repo. The regression proof is a paired test run plus git counter-check: model-failover commit count before and after the test run must be unchanged.

No new LESSON (RULE ZERO).

## Timeline

- **2026-05-21** | v1.0.0 -> v1.0.1 — Added **AP-7** after `tools/test_operator_boundaries.py` generated local `model-failover: capture latest lane state` commits while testing `/ask` fallback paths. Root cause: tests mocked worker calls but not `command_center._failover_start/_failover_finish`, so real failover side effects wrote the production ledger. Patched the test module with module-level failover side-effect mocks, added the `command_center._failover_capture_enabled()` pytest/env guard, and proved `python3 -m pytest tools/test_operator_boundaries.py tools/test_daily_0300_substrate_sync.py -q` passes 57 tests while model-failover commit count stays unchanged. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/model-failover/skill.
- **2026-05-20** | v1.0.0 created by Ship 1 of the god-tier 3-ship plan (Steps 1-11). APs absorbed from the 2026-05-20 audit of commit `4cdabaf7`. 77 tests across 6 test files prove the doctrine. Steps 1-10 landed in commits `f6869658` (Step 1: failover_schema), `282ade80` (Step 2: quarantine), `13c40c47` (Step 3: WAL + lock reorder), `c86fb710` (Step 4: orphan-aware latest_state), `da23943c` (Step 5: sweeper), `3f7bb788` (Step 6: provider probe), `7b045bea` (Step 7: parity_check + manifest), `85f00f37` (Steps 7b+8+9: parity wiring, resume-v2, OpenBrain capture, mistake-to-skill ledger). Step 11 (this SKILL.md + `tools/verify_ship1_e2e.sh`) closes Ship 1. Plan: `pages/plans/from-gpt-implemented-the-delightful-riddle.md` (mirror at `/Users/madia/.claude/plans/from-gpt-implemented-the-delightful-riddle.md`). Next: Ship 2 (atomic lane control plane) per plan §5.

## See also

- [[mistake-to-skill]] — 7-day SLA absorption pattern this skill follows; `_append_mistake_to_skill` writes to its ledger and the weekly digest absorbs ≥2× repeats back into this skill.
- [[session-coordination]] — lane-lock contract (extended by Ship 2); the failover ledger is the substrate Ship 2's atomic lane control plane builds on.
- [[musk-algorithm]] — 5-step elimination ethos Ship 1 applied. Step 2 (delete) removed the race-before-push pattern entirely rather than patching it; Step 5 (automate) materialized orphan recovery via the sweeper so no human reads the ledger to find ghost work.
- [[karpathy-coding-principles]] — surgical-change discipline used per Ship 1 step (one commit = one defect closed; no adjacent-code "improvements"; every changed line trace to the AP it closes).
- [[library-grade-audit]] — Phase-1 7-gate scorecard format informing future failover audits; the next audit of this skill will use that scaffold.
- [[ceo-hierarchy]] — `/ask` routing; resume-prompt-v2 dispatches via this hierarchy.
- [[command-center]] — `_failover_start`, `_failover_finish`, `_resume` handlers.
- [[session-operating-contract]] — DONE protocol; resume-prompt-v2 `CONTRACT` block enforces SOC rituals.
- [[openbrain-projection]] — OpenBrain capture pipeline; this skill writes to it fire-and-forget.
- [[gbrain-ops]] — parity / sync / discoverability hygiene.
- [[agent-quality]] — broader anti-pattern catalog.
