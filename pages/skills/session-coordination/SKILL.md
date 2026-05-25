---
tier: 2
type: skill
name: session-coordination
id: SKILL-SESSION-COORDINATION
version: 1.35.0
last_updated: 2026-05-21
status: active
description: "Host-central JSONL session registry on Air. Every claude/openclaw/codex session declares intent + scope before shared-substrate work; SOAO Section 8 prints overlaps; launchd-driven heartbeat + cleanup. Closes infrastructure AP-30 + AP-34. Substrate-as-coordination, no mutex — gbrain pattern. v1.35 AP-34 codifies closeout for stale Codex Desktop app-server PID rows: targeted close plus active-id removal before declaring parallel sessions clear. v1.34 AP-33 suppresses dead local PID rows at scan time and makes Codex Desktop self-registration use the durable app-server PID instead of a one-shot shell PID."
triggers:
  - every session start (auto-fires via SOAO Section 8)
  - SOAO Section 8 reports 🟡 PARALLEL active session(s)
  - about to edit a file another session has declared in scope
  - need to query "who's working on X right now"
  - planning a multi-step workflow on shared substrate
  - declaring or expanding session scope mid-session
tools: [Bash]
mutating: true
absorbs_aps: [infrastructure/AP-30, infrastructure/AP-34]
related: [infrastructure, session-operating-contract, karpathy-loop, gbrain-ops, audit]
tags: [skill, session-coordination, registry, parallel-sessions, gbrain-pattern, substrate, no-mutex, 2026-04-21]
title: "session-coordination v1.35.0"
---

# session-coordination v1.35.0

## Purpose

Make every active claude/openclaw/codex session **discoverable to every other agent on every host** via append-only host-central JSONL on Air. So when two sessions both intend to touch `factory-ops/SKILL.md` (real session-56 incident, 2026-04-21), the second session's SOAO Section 8 prints the overlap **before any work begins** — instead of discovering it post-commit via duplicate Timeline entries and 40-min cat-and-mouse with auto-sync.

This skill is the substrate-layer answer to a problem that `infrastructure` AP-30 (session 39) and AP-34 (session 45) both diagnosed but neither closed. AP-34's 5-why #3 was explicit: *"No shared-lock. No status file. Only signal is git ls-remote + commit cadence."* This skill ships the status file.

**Design choice — no mutex.** Per Madi's 2026-04-21 directive against hard-block ("that will actually block for it to evolve"), this is the gbrain pattern (substrate enriches awareness; never gates writes), not the Postgres-row-lock pattern (which kills evolution). Sessions can still race. Awareness > blocking.

## Current rules (binding)

### 1. Read SOAO Section 8 before declaring "no parallel work"

Every SOAO run prints Section 8:
- `✅ no other active sessions` → free to operate
- `🟡 PARALLEL: N active session(s)` → list of sessions with started-at, intent, declared-scope

Never claim "I'm the only session" without consulting Section 8. AP-34 documented the cost: a session that didn't check assumed solo and hit merge-conflict / clobber.

### 2. Declare scope at session start (default `*`; narrow as soon as you know)

The SessionStart hook auto-registers your session with `--scope "*"` (everything-touchable). This is safe but uninformative — every other session sees you as "could touch anything."

**As soon as you know your real scope** (from handoff, plan, or first 2-3 file reads), re-register with the narrow scope:

```bash
SESSION_NUM=56 SESSION_PID=$$ bash tools/session_register.sh \
  --host mac --intent "exact intent" --scope "path1.md,path2.md,tools/foo.sh"
```

Re-registering appends a new register record; older one is implicitly superseded by `last_activity` ordering (the cleanup cron eventually archives it). Don't worry about deleting; the registry is append-only.

### 3. Pre-edit overlap check on shared files

Before editing a known-shared file (any `pages/skills/*/SKILL.md`, `MEMORY.md`, `pages/skills/_gbrain/RESOLVER.md`, `tools/soao.sh`, `~/.claude/hooks/*`, `CLAUDE.md`), run:

```bash
bash tools/session_scan.sh --overlap-with "pages/skills/factory-ops/SKILL.md"
```

If 0 results → free to proceed. If ≥1 → coordinate via Telegram (`bash tools/tg_send.sh "..."`) before touching the file.

**Append-only Timeline edits are conflict-safe.** Body rewrites are not. AP-1 below has the canonical example.

### 4. Heartbeat is automatic; close is manual-or-stale

- **Heartbeat:** Mac launchd `com.nous.session-heartbeat` (180s) updates your session's `last_activity` automatically as long as `~/.claude/sessions/current_session_id` exists.
- **Close:** call `bash tools/session_close.sh` at session end OR let stale-cleanup archive you 30min after last heartbeat. Both are clean states.

If you finish a session knowing you won't return (e.g., explicit close handoff), call `session_close.sh` so other sessions immediately see you're gone. Otherwise: cleanup cron handles it within 60s of the 30min stale window.

If `session_scan.sh` shows dozens of old "active" sessions, inspect `~/.claude/sessions/active/*.id` on the emitting host before blaming Air cleanup. Heartbeat reads every file in that directory; stale ID files make dead sessions look fresh. See AP-29.

Heartbeat must skip per-session local `active/*.id` files whose embedded `s*-mac-<pid>-*` PID is no longer alive. The compatibility `current_session_id` file may still be refreshed, but the multi-ID directory must not keep dead lanes alive forever. See AP-30.

Registry scripts must derive the vault path from their own script location, not from a Mac-only absolute path. Air runtime lives at `/Users/madia/nous-agaas/wiki`; Mac runtime lives at `/Users/madia/Documents/Projects/Nous AGaaS/Nous`. Hard-coded Mac paths can hang or return false state on Air. See AP-31.

The pre-action handshake applies to every durable substrate write, not only doctrine SKILL.md body rewrites. Before creating or changing `tools/*`, launchd plists, `pages/audits/*`, `pages/systems/*`, `pages/skills/*`, or runtime routing files, run the registry overlap scan and recent-git-touch check for the exact path or topic class. See AP-32.

Registry readers must suppress local-host records whose registered PID is already dead. In Codex Desktop, `session_self_register.sh` must register the durable `codex app-server` PID when it detects that process as a parent or grandparent, because direct tool commands run in short-lived shells. See AP-33.

Codex Desktop app-server PID rows are not enough to prove a peer lane is live. The app-server can outlive many tabs/tasks, so stale `~/.claude/sessions/active/*.id` files for the same app-server PID can keep superseded registry rows fresh. When closing parallel sessions, use targeted `tools/session_close.sh --session-id <sid>` for every stale row, verify the matching active-id files are gone, and only then trust `session_scan.sh --json == []`. See AP-34.

Before claiming an old controller/reviewer lane is abandoned or superseded, prove both layers are clear: `session_scan.sh --overlap-with <scope-file>` has no owner, and `ps` has no matching terminal command for the same mission prompt/model. Registry-only closure is not enough when terminal processes are still alive. See AP-28.

### 5. Air unreachable → degraded coordination, NOT blocked work

If `session_register.sh` can't reach Air, it queues to `~/.claude/sessions/pending-registers.jsonl` and prints `🟡 Air unreachable; queued` to stderr. SOAO Section 8 still runs (returns "✅ no other active sessions" because no remote registry to read) — but it's wrong-by-omission. **Treat ✅ as suspect when you know Air is down.** Manual coordination via Telegram + git log cadence is the fallback.

### 6. Don't add per-file mutex; if you need it, ship v2

v1 is intentionally lock-free at the file level. If you find a v1 case where awareness alone isn't enough — two sessions both genuinely needed to modify the same file at the same time and overlap-warning didn't prevent the conflict — that's evidence for v2 (PreToolUse hook OR pre-commit `Parallel-Session-Overlap:` trailer). Don't reach for the lock first. Ship the smaller intervention; iterate.

### 7. Registry readers must tolerate corrupt JSONL rows

`active-sessions.jsonl` is append-only operational substrate, not a pristine database. A single malformed historical row must never make `session_scan.sh` return blank output or a malformed "PARALLEL:  active session(s)" line. Registry readers must parse line-by-line, keep valid JSON objects, ignore invalid rows, and then compute active sessions from the cleaned stream.

### 8. Cleanup owns registry hygiene, including orphan heartbeats

`cron_session_cleanup.sh` is the recovery loop. It must archive closed sessions, stale sessions, malformed rows, and heartbeat-only groups with no matching register record. `session_scan.sh` may ignore bad data for live safety, but cleanup must remove it so strict JSONL checks recover.

### 9. Tests use isolated registries; heartbeat tracks all active IDs

Never truncate or rewrite the live Air registry from a test. Test suites must set `SESSION_REGISTRY_PATH` to an isolated test file and clean only that file. Multiple local sessions must not depend on one global `current_session_id`; `session_register.sh` also writes per-session ID files under `SESSION_ID_DIR`, and `session_heartbeat.sh` heartbeats the union of the current file plus active ID files.

### 10. Overlap checks are normalized path-prefix checks, not exact string checks

Declared scopes and requested paths must be normalized before comparison: strip `./`, strip leading `Nous/`, treat `*` as universal, and treat parent directory scopes as overlapping child files. Exact string membership is too brittle for mixed Codex/Claude sessions launched from different working directories.

### 11. Air-local sessions must not SSH to `air`

The registry lives on Air, so Mac sessions use `ssh air`; Air sessions read/write the same registry as local files. Any registry tool that always shells through `ssh air` will silently report empty state when the `air` alias is absent on Air itself, making `/codex` and Air Claude Code sessions invisible.

### 12. Four-session handshake is the default for broad audits

When Madi asks for "four simultaneous sessions" or a task spans >3 independent subsystems, run a **four-session handshake**:

1. **Controller lane** owns the critical-path write set, registers first, and declares the exact files it may edit.
2. **Three helper lanes** register read-only scopes or disjoint write scopes before they inspect files.
3. **Handshake check:** controller runs `session_scan.sh` after helper registration and confirms all lanes are visible.
4. **Do-not-disturb rule:** helper lanes return findings only; they do not interrupt peers unless they find a blocker or an ownership collision.
5. **Integration rule:** controller owns final edits, commits with `git commit -o <paths>`, and does not sweep other lanes' staged work.
6. **Close rule:** every helper lane closes its session; controller runs a final scan before claiming the handshake is clear.

This is **parallel awareness, not a mutex**. The goal is to evolve faster without breaking each other: more eyes, clear ownership, one integrator.

### 13. Local interactive Codex uses `tools/codex-nous.sh`

Claude Code has a SessionStart hook. Telegram `/code` and `/codex` have command-center context injection. Local interactive Codex has neither. When launching a local Codex session that may touch Nous AGaaS substrate, use:

```bash
CODEX_SESSION_SCOPE="pages/skills/session-coordination/SKILL.md,tools/codex-nous.sh" \
  bash tools/codex-nous.sh
```

The launcher runs `tools/session_self_register.sh` first, then `exec`s Codex. Set `CODEX_SESSION_INTENT` / `CODEX_SESSION_SCOPE` before launch to make ownership useful. Use `CODEX_BIN=/path/to/codex` when testing or when the binary is outside PATH.

### 14. Registration env aliases must preserve scope, or fail loudly

`tools/session_self_register.sh` accepts both env vocabularies:

- `SESSION_INTENT` / `SESSION_SCOPE` — canonical for generic session registration.
- `CODEX_SESSION_INTENT` / `CODEX_SESSION_SCOPE` — compatibility aliases for Codex launcher/helper flows.

Silent fallback to `scope=*` is a coordination bug. If a caller provides a narrow scope through a supported env alias, the registry record must show that exact narrow scope in `tools/session_scan.sh`. If a new launcher introduces a third vocabulary, either translate it before calling `session_self_register.sh` or make the script reject it loudly; never let it register as wildcard by accident. See AP-25.

## Anti-Patterns

### AP-1 — Body-rewrite on a file under another session's declared scope (v1.0, 2026-04-21, session 56)

**Pattern:** Two sessions both have a target file in declared scope. Session A is doing a body rewrite (e.g., new AP block). Session B is doing an append (Timeline entry). Without coordination, both commit; auto-sync interleaves; result is either a merge conflict OR a duplicate (the exact factory-ops incident, 2026-04-21).

**Root cause:** Body rewrites and appends are NOT both conflict-safe. Append-to-end is line-atomic across writers. Body rewrites are not — the second writer's diff applies against the OLD body it read, missing the first writer's change.

**Fix:**
1. Pre-edit: `tools/session_scan.sh --overlap-with "<file>"`. If overlap → see step 2.
2. Decide who owns the body: the session with the new substantive doctrine. The other session (append-only Timeline / Evidence-trail) waits for the body-owner to commit, pulls, then appends.
3. Or coordinate via Telegram: `tg_send.sh "I'm rewriting body of factory-ops; will commit in 5min then ping you"`. Append-session waits.

**Detector (mechanical, session-57+ candidate):** `tools/test_no_concurrent_body_rewrite.sh` — parses recent N commits for same-file edits within <120s by different `Author:` (heuristic for multi-session) AND involving non-Timeline lines. Flags for review.

**Cross-ref:** `infrastructure` AP-30 (parent — race on same SKILL.md); session-operating-contract Rule 17 (no re-ask, but DO pause for genuine coordination need); `karpathy-loop` AP-3 (multi-virtual-reviewer caught this scenario in the spec design phase).

### AP-2 — When registry is incomplete, file-scope grep + `ps aux` are authoritative; never claim "no parallel work" from registry alone (session 60, 2026-04-22)

**What happened:** Session 59 SOAO Section 8 reported "1 PARALLEL active session (me)." `ps aux` showed **4 `claude` processes** on Mac (PID 93004 me, 85687 11:50, 83508 11:36, 56591 Monday). The 3 others never appeared in the registry because (hypothesis) they either: (a) started before the SessionStart hook fired, (b) were in different project directories where the hook isn't configured, or (c) bypassed the hook entirely. **Meanwhile**, session-57-extension edited `pages/tenants/satory/skills/task-extraction/SKILL.md` earlier in the same calendar day and shipped 7 Todoist writes — zero record in the registry, zero overlap-warning. The "no other active sessions" signal from my registry scan was **incomplete-by-construction**, not "actually no one else."

**Root cause:** registry = OPT-IN system. SOAO hook auto-registers Claude Code sessions launched in this vault; does not register:
- Sessions in other project directories (`~/.claude/projects/*/memory/` variants)
- Sessions spawned without the hook (programmatic `claude -p` invocations)
- Openclaw / factory sessions (separate launchd, no registry integration yet)
- Background / cron-driven automation that touches vault files
- Any parallel agent invocation via MCP / WebSocket clients

**Rule:** before claiming "no other active work on this scope" — run THREE checks, NOT just the registry:
1. `bash tools/session_scan.sh` (registry) — necessary but not sufficient.
2. `ps aux | grep -E 'claude|openclaw' | grep -v grep` — catches un-registered processes.
3. `git log --since="1 hour ago" --all --name-only --pretty=format:%s -- <target-file>` — catches recent commits by any actor touching your target file.

If any of (2) or (3) surface activity not in (1), treat registry as incomplete-silent, not clean.

**Compounding gate candidates (session 61+):**
(a) Extend `tools/session_scan.sh` to include `ps aux` + recent-git-touch as additional awareness sources. Single tool, three signals.
(b) Openclaw factory — teach the runtime to append to `active-sessions.jsonl` on task start / completion. Closes "openclaw session invisible to Claude Code" class.
(c) Pre-commit hook could warn "file has been edited by another actor within the last 5 minutes" using `git log --since="5.minutes.ago" -- <file>` on staged paths.

**Cross-ref:** `audit` AP-21 (pagination — same "your probe saw a partial truth" meta-pattern); `audit` AP-17 (SOAO — this extends SOAO Section 8's awareness without replacing it); `infrastructure` AP-30 (parent class — race on shared substrate). No new LESSON (RULE ZERO).

### AP-3 — `session_close.sh` needs `--session-id` for targeted close (session 60, 2026-04-22)

**What happened:** Session 59 registered twice (auto-register on SessionStart produced s1051 with `scope="*"`; manual re-register with narrow scope produced s59). To close the stale s1051, ran `session_close.sh` — but the script only read from `$HOME/.claude/sessions/current_session_id`, which had been overwritten with `s59` by the re-register. Script closed **s59** (the live session), not **s1051** (the stale one). Recovery required manual JSONL append to Air via direct SSH — error-prone workaround.

**Fix (SHIPPED session 60):** `tools/session_close.sh` now accepts `--session-id <SID>` flag (and `--session-id=<SID>` form). When used: closes the specified session by appending the close record to Air JSONL; does NOT touch `current_session_id` (preserving the live session's file-tracked identity). Order-independent arg parsing so both `--session-id X ok` and `ok --session-id X` work. Legacy call `bash session_close.sh [exit_status]` unchanged.

**Rule:** when closing a session OTHER than the currently-tracked one:
```bash
bash tools/session_close.sh --session-id <stale-sid> <exit_status>
```
Use-case: auto-register creates `s<PID>-mac-TIMESTAMP` on session start; you manually re-register with narrow scope producing a new SID; close the first at your leisure with --session-id.

**Dogfood verification (session 60):** `bash tools/session_close.sh --session-id s60-TESTDOGFOOD-20260422 test` → JSONL record appended `{op:"close","session_id":"s60-TESTDOGFOOD-20260422","exit_status":"test"}`; `current_session_id` file still contained live session `s60-mac-11768-20260422T1318` (preserved, correct).

**Compounding gate candidate (session 61+):** `tools/test_session_close_flags.sh` — regression guard that verifies (a) no-arg close still closes file-tracked session + removes file, (b) `--session-id X` closes X + leaves file intact, (c) unknown flag exits 2.

**Cross-ref:** AP-2 (registry awareness — targeted-close is the other half of the registry lifecycle). No new LESSON (RULE ZERO).

### AP-28 — Audit closeout must clear registry rows AND live terminal PIDs (session s108-mac-25615, 2026-05-11)

**Pattern:** OpenBrain audit closeout said the old controller/reviewer lanes were superseded, but `ps` still showed a live Opus controller process and two Codex reviewer processes holding the original audit mission for ~5 hours. The Air session registry also still showed stale owners for `pages/audits/AUDIT-openbrain-projection-2026-05-11.md`, so later repair lanes could not truthfully say the file was unowned.

**Root cause:** closeout treated the registry and the terminal process table as separate concerns. AP-2 already said registry-only scans are incomplete, and AP-3 shipped targeted close, but the audit closeout ritual did not require applying both signals together before declaring a lane gone.

**Rule:** when retiring a controller/reviewer lane after an audit or handoff, run both checks and record both results:

```bash
ps -axo pid,ppid,stat,etime,tty,command | grep -E 'claude|codex|openbrain|<mission-token>' | grep -v grep
bash tools/session_scan.sh --overlap-with <owned-file>
```

If a real stale terminal process remains, terminate it politely first (`kill -TERM <pid>`), re-check `ps`, then close stale registry rows with:

```bash
bash tools/session_close.sh --session-id <stale-sid> stale-terminal-closed
```

Only after `ps` has no matching mission process and `session_scan.sh --overlap-with <owned-file>` reports no owner may a later audit claim the old lane is closed. If either layer is still non-empty, status is yellow, not green.

**Verification:** OpenBrain residual repair closed PIDs `31219`, `37127`, and `37181`; targeted-closed stale OpenBrain controller/reviewer SIDs; then `session_scan.sh --overlap-with pages/audits/AUDIT-openbrain-projection-2026-05-11.md` returned `no other active sessions`.

### AP-29 — Local active-ID files can keep dead sessions alive forever (OpenBrain closeout follow-up, 2026-05-11)

**Pattern:** After the OpenBrain projection bridge was fully verified and the current lane closed, `session_scan.sh` still reported 94 active sessions, many from days earlier. Air cleanup did not archive them because fresh heartbeat rows kept arriving.

**Root cause:** `tools/session_heartbeat.sh` heartbeats the union of `~/.claude/sessions/current_session_id` plus every `~/.claude/sessions/active/*.id` file. On Mac, 109 old `.id` files had accumulated. The heartbeat launchd dutifully refreshed those stale IDs every 180s, so Air's 30-minute stale cutoff never fired. The registry was not the root cause; stale local ID files were.

**Detector:**

```bash
find ~/.claude/sessions/active -maxdepth 1 -type f -name '*.id' | wc -l
bash tools/session_scan.sh --json | jq 'length'
printf 'current_session_id='; cat ~/.claude/sessions/current_session_id 2>/dev/null || true; echo
```

If `active/*.id` count is much larger than the expected live terminal count, heartbeat is likely refreshing dead lanes. Confirm with:

```bash
ssh air 'grep "<stale-session-id>" ~/nous-agaas/state/active-sessions.jsonl | tail -5'
```

Fresh heartbeat rows for a days-old session prove this AP.

**Repair sequence:**

```bash
CUR=$(cat ~/.claude/sessions/current_session_id 2>/dev/null || true)
ARCH="$HOME/.claude/sessions/active-stale-$(date +%Y%m%dT%H%M%S)"
mkdir -p "$ARCH"
find "$HOME/.claude/sessions/active" -maxdepth 1 -type f -name '*.id' -mmin +30 -print |
while read -r f; do
  sid=$(cat "$f" 2>/dev/null || true)
  [ -n "$sid" ] || continue
  [ "$sid" = "$CUR" ] && continue
  mv "$f" "$ARCH/"
  bash tools/session_close.sh --session-id "$sid" stale-id-file-archived
done
ssh air 'cd ~/nous-agaas/wiki && bash tools/cron_session_cleanup.sh'
bash tools/session_scan.sh
```

**Verification:** OpenBrain closeout archived 108 stale Mac ID files, preserving current `s1638-mac-62141-20260511T1638`; targeted-closed the remaining 7 stale registry rows; `session_scan.sh --json | jq length` dropped from 94 to 1. The only remaining active SID was the current lane.

**Why no new LESSON file:** RULE ZERO. This is session-coordination lifecycle doctrine, not a new standalone lesson.

### AP-30 — Heartbeat must not refresh dead-PID active ID files (2026-05-12)

**Pattern:** One day after AP-29, `session_scan.sh` again reported 19 active sessions. Every reported SID had a dead embedded Mac PID, but all 19 had a fresh heartbeat timestamp from the same minute.

**Root cause:** AP-29 documented the manual cleanup sequence but left `tools/session_heartbeat.sh` behavior unchanged. The heartbeat launchd continued to read every local `~/.claude/sessions/active/*.id` file and emit heartbeats blindly, so stale local files could recreate the same false-active registry state.

**Fix (SHIPPED):** `tools/session_heartbeat.sh` now parses `s*-mac-<pid>-*` session IDs from the per-session active directory and skips any file whose local PID is no longer alive. The compatibility `current_session_id` file remains untouched to preserve older one-session flows and tests.

**Rule:** stale lease prevention belongs in the producer, not only in cleanup. Cleanup archives bad history; heartbeat must stop producing bad fresh rows.

**Regression:** `tools/test_session_coordination_e2e.sh` section 4b injects a backdated stale register plus a dead-PID active ID file, runs heartbeat, and asserts that the stale SID does not become active.

**Verification:** closed 19 dead-PID leases via `session_close.sh --session-id ... stale-pid`; local active ID count dropped to 0; `session_scan.sh` returned `✅ no other active sessions`; E2E test added for recurrence.

### AP-31 — Registry scripts must not use Mac-only vault paths on Air (2026-05-12)

**Pattern:** Air-side `test_session_coordination_e2e.sh` hung immediately after starting `session_register.sh`. Debug trace showed the script blocking while trying to compute `START_HEAD` from `/Users/madia/Documents/Projects/Nous AGaaS/Nous`, a Mac-local path.

**Root cause:** `session_register.sh` correctly derived `VAULT_DIR` from its script path for handoff-number discovery, but still used a hard-coded Mac path for `START_HEAD`. On Air, the canonical wiki checkout is `/Users/madia/nous-agaas/wiki`, so the hard-coded path is the wrong substrate.

**Fix (SHIPPED):** `session_register.sh` now computes `SCRIPT_DIR` and `VAULT_DIR` once near startup and uses `VAULT_DIR` for both handoff discovery and `START_HEAD`.

**Rule:** registry scripts must be host-relative and script-relative. A path in `/Users/madia/Documents/Projects/...` is valid only for the Mac vault; it must never be embedded in Air runtime registry code.

**Verification:** Air direct `session_register.sh` invocation returned promptly with the current Air wiki HEAD after the patch, and the Air E2E no longer hangs at register startup.

### AP-32 — Pre-action handshake is MANDATORY before ANY substrate write, not just doctrine-skill body rewrites (session s0908-mac-56990, 2026-05-17)

**What happened:** Session s0908 (this Mac session, Sunday 2026-05-17 ~11:20 KZT) and a parallel peer Mac/Codex session both interpreted Madi's "ship the BDL/Cerebro ping" directive and independently authored implementations:

- Peer shipped `tools/satory_bdl_external_blocker_ping.py` (178 lines, imports gate as module, exact 08:00 single-shot trigger, English message, no atomic ledger), `tools/launchd/com.nous.satory-bdl-external-blocker-ping.plist`, `tools/uninstall_satory_bdl_external_blocker_ping.sh`, two test files, and the canonical SP3 audit doc at `pages/audits/SP3-BDL-PING-RESCOPED-2026-05-17.md`. Committed as `bcc302f1` + `85b39525`, LaunchAgent installed on Air, factory probe GREEN at `81a6aae2`.
- This session shipped `tools/satory_bdl_blocker_ping.py` (380 lines, subprocess gate, 08-17 window + workday-aware, atomic ledger, Russian message, 14-day circuit breaker, hall-pass for `tg_send.sh` AP-4 autonomy gate) plus a parallel SP3 audit at the SAME path — the linter/auto-sync overwrote my audit with peer's version mid-session. Discovered the duplicate only when the file-overwrite system reminder fired.

**Root cause:** I never ran the pre-action handshake. Specifically:

1. Did NOT run `bash tools/session_scan.sh --overlap-with tools/satory_bdl_*` (registry scan against my intended scope; AP-2 signal 1).
2. Did NOT run `git log --since='30.minutes.ago' --all -- tools/satory_bdl_* pages/audits/SP3-*` (recent-touch probe; AP-2 signal 3 + AP-4's named pre-edit gate, extended to non-doctrine paths).
3. Did NOT run `ps aux | grep -E "claude|codex"` (live process scan; AP-2 signal 2).

AP-4 narrows the mandatory pre-edit ritual to **doctrine** SKILL.md files (SOC, karpathy-loop, audit, infrastructure, mistake-to-skill, session-coordination, gbrain-ops, evidence-verification). It is silent on new files under `tools/`, `pages/audits/`, or `pages/skills/<new-name>/` — exactly the category I touched. The handshake mechanism EXISTS; the doctrine narrowly bounded WHEN it was mandatory.

**Meta-pattern: "scope-class-extension" failure.** AP-4 covered the highest-frequency stage-bleed class (doctrine bodies) but left adjacent classes uncovered. Today's failure proves the ritual needs to extend to ALL non-trivial substrate writes when peer sessions are plausibly active.

**Rule — pre-action handshake is MANDATORY before:**

(a) Creating a new file under `tools/`, `pages/audits/`, `pages/skills/<name>/`, `pages/systems/`, `pages/plans/`, `pages/specs/`, `agents/` (any path that produces durable substrate state)
(b) Body-rewriting any SKILL.md (already covered by AP-4 — this AP supersedes/extends AP-4's narrower scope)
(c) Editing any file recently touched by a peer (commit in last 30 minutes)
(d) Authoring an audit or plan doc whose subject overlaps an ongoing topic (e.g., another agent's open task)

```bash
# The handshake (single ritual; <5s; fails open with a printed warning):
TARGET_GLOB="$1"  # e.g., "tools/satory_bdl_*" or "pages/skills/bdl-cerebro-*"
echo "=== 1. Registry scope-overlap (AP-2 signal 1) ==="
bash tools/session_scan.sh --overlap-with "$TARGET_GLOB" 2>&1 || true

echo "=== 2. Recent-git-touch (AP-2 signal 3; AP-4 + AP-32 extended to all paths) ==="
git log --since='30.minutes.ago' --all --name-only --pretty='%h %an %ar | %s' -- $TARGET_GLOB 2>&1 | head -30

echo "=== 3. Live-process scan (AP-2 signal 2) ==="
ps aux | grep -E "(^|/)(claude|codex)( |$)" | grep -v grep | head -10

echo "=== 4. Topic-class glob — files whose names match the intent ==="
# e.g., for a BDL/Cerebro ping plan, also probe related names:
find tools pages -type f -newer .git/refs/heads/main \( -name "*satory*" -o -name "*bdl*" -o -name "*cerebro*" \) 2>/dev/null | head -10

echo "=== 5. Audit-recency check — same topic, last 14 days ==="
ls -t pages/audits/*.md 2>/dev/null | xargs -I{} bash -c 'grep -l "BDL\|Cerebro\|<your-topic>" "{}" 2>/dev/null' | head -5
```

If ANY signal returns peer activity:
- **Read the peer's work first** (don't blindly trust the registry's claim of "no overlap" — peer may have unregistered work).
- **Defer to their canonical implementation** if they shipped first; close the substrate gap they left (like this session shipped `bdl-cerebro-replacement-gate` skill v1.0.0 after peer shipped the ping itself).
- **Communicate via Telegram (`tg_send.sh`)** only when blocked. Default is silence; "do not disturb each other unless help is needed" (Madi 2026-05-17 directive).

**Detector (deferred; v0.1 candidate):** `tools/test_pre_action_handshake.sh` — wraps the 5-step ritual above into one command, accepts glob argument, exits 0/1/2 with structured output. Not built yet because the ritual is composable from existing tools; AP-32 is the doctrine, the wrapper is Musk-step-5 (automate) that comes after we prove the ritual is followed by hand for N≥3 sessions.

**Generic name for non-trivial substrate writes:** if you find yourself about to use Write/Edit on a path you haven't touched in this session, AP-32 fires. The 5-second cost of the handshake is dwarfed by the cost of stage-bleed (today: ~30 minutes of duplicate work + an audit-doc overwrite + a session-coordination AP that needs codifying — meta-cost).

**Cross-ref:** AP-4 (doctrine-skill subset of this rule — narrower scope, same mechanism); AP-5 (cross-session stage-bleed at git-index layer — sibling at commit boundary); AP-9 (path-prefix overlap normalization — handshake needs glob expansion); AP-13 (SessionStart hook fires once per CC restart — registry may not have new sessions); [[bdl-cerebro-replacement-gate]] AP-3 (brain-first violation — sibling lesson on the same session); [[karpathy-loop]] AP-5 (mental simulation forbidden — handshake is mechanical, not mental). No new LESSON (RULE ZERO).

musk-step-2: considered building `tools/session_handshake.sh` as a 6-line wrapper around the 5-step ritual immediately — rejected because (a) AP-32 codifies the routine first; the wrapper is Musk-step-5 (automate) which comes AFTER step 3 (simplify) and validation that the ritual is followed; (b) building a tool while the doctrine isn't proven would Musk-step-1-violate the requirement; (c) shipping just doctrine first lets future sessions catch the next stage-bleed by running the existing tools by hand, which builds operator muscle and validates the ritual before automating. Detector deferred until N≥3 same-class incidents prove the ritual is in active use.

### AP-33 — Dead local PID rows are false-active overlap, and Codex Desktop must not register one-shot shell PIDs (2026-05-21)

**Pattern:** A live `session_scan.sh` showed multiple fresh active Mac lanes on the same residual-cleanup scope, but `ps -p <pid>` showed every listed PID was already gone. A new self-registration from Codex Desktop reproduced the same failure immediately: the registered PID was the one-shot shell process used for the tool call, not a durable Codex session process.

**Root cause:** AP-30 stopped `session_heartbeat.sh` from refreshing dead local `active/*.id` files, but `session_scan.sh` still trusted any fresh register/heartbeat row until the 30-minute stale cutoff. Codex Desktop made the class worse because local tool commands are short-lived children of the long-lived `codex app-server`; registering `$$` from `session_self_register.sh` created a fresh false-active row as soon as the shell exited.

**Fix (SHIPPED):** `session_scan.sh` now filters records for the scanner's own host when `.register.pid` is not present in the local process table. Remote-host rows are not filtered by local `ps`, because a Mac scanner cannot prove Air/VPS PID liveness. `session_self_register.sh` now detects a `codex app-server` parent/grandparent and registers that durable parent PID unless `SESSION_PID` is explicitly supplied.

**Rule:** TTL is a fallback, not the first line of truth for local process liveness. If the registered host is this host and the PID is dead, the lane is not active. For Codex Desktop, the durable process is the app server, not the shell spawned for a single command.

**Regression:** `tools/test_session_scan_dead_pid.sh` registers one alive local PID, one dead local PID, and one non-local dead PID. The scan must keep the alive local and non-local rows while filtering only the dead local row. Existing synthetic registry tests explicitly disable local-PID filtering because they use fake PIDs by design.

**Verification:** live registry false-active rows were targeted-closed with `session_close.sh --session-id ... stale-no-live-pid-janitor`; re-registration with the live Codex app-server PID stayed visible; the dead-PID scanner regression passed.

### AP-34 — Codex Desktop app-server PID rows need explicit closeout, not heartbeat trust (2026-05-21)

**Pattern:** Parallel-session cleanup found fresh active Mac registry rows with different intents/scopes but the same long-lived Codex Desktop app-server PID. Heartbeat kept those rows fresh because the app-server was alive, while the underlying logical tasks/tabs were already superseded or closed.

**Root cause:** AP-33 correctly switched Codex Desktop registration away from one-shot shell PIDs to the durable app-server PID, but that PID is shared by multiple logical tabs/tasks. A stale `~/.claude/sessions/active/*.id` file for the same app-server can therefore keep a dead logical lane active until it is explicitly closed.

**Rule:** For Codex Desktop closeout, do not treat a live app-server PID as sufficient proof that every row with that PID is live. Close stale/superseded session IDs with `tools/session_close.sh --session-id <sid> <reason>`, verify the matching active-id files are gone, and require `tools/session_scan.sh --json` to return `[]` or only known live owners before declaring parallel sessions clear.

**Verification:** Target-closed stale Mac rows including `s108-mac-56688-20260521T1101`, `...T1107`, `...T1112`, `...T1348`, `...T1353`, and stale current markers `s1354-mac-6957-20260521T1354` / `s1357-mac-35908-20260521T1357`; then `bash tools/session_scan.sh --json` returned `[]` and the matching active-id files were absent.

### AP-4 — Doctrine-skill body-rewrite REQUIRES `git log --since` pre-edit gate, not just registry scan (session 61, 2026-04-22)

**What happened:** Session 60 codified `session-operating-contract` Rule 18 "no-defer-on-textbook-bug" with a full 3-edit ritual. At the SAME time, session-57 (parallel, hidden from registry at the moment s60 started editing) received the SAME Madi global directive and codified the SAME Rule 18 independently. **Result: Rule 18 block written byte-identically twice in SOC v1.10 (lines 245-265 and 267-287).** Session-60 MASTER closed without catching the duplicate → silent substrate drift. Session-57 caught + deduped with commit `7d7b2623` "SOC v1.10 cleanup: de-duplicate session-60's Rule 18 block (collision artifact)". 0-byte diff between the two blocks = byte-identical, confirming both agents executed the same directive.

**Root cause:** Session-60 pre-edit overlap check used `tools/session_scan.sh` (registry) only. At that moment, session-57 was not yet in the registry (registered 13:42 KZT, session-60's SOC edit was earlier). Registry is **opt-in and time-lagged** — a session that starts editing before registering is invisible. AP-2 already codified the 3-signal rule (registry + ps aux + recent-git-touch) but did NOT specify WHEN each signal is mandatory. For a general scope scan, registry suffices. For **doctrine-skill body-rewrites** (SOC, karpathy-loop, audit, infrastructure, mistake-to-skill, session-coordination — any skill whose SKILL.md is read by every session) the `git log --since` check is mandatory — these are the files most likely to get a "Madi told us this" class of parallel codification where two agents hear the same directive and codify independently.

**Meta-pattern: "duplicate-from-shared-directive" class.** Unlike the body-rewrite-vs-append collision in AP-1 (different content, merge-conflict), the AP-4 class produces byte-identical content at different line ranges — no conflict, no warning, silent drift. Auto-sync merges both, parity scanners see content valid, MD5 scanner sees citations valid — everything green while Rule 18 is written twice.

**Rule — mandatory pre-edit gate for any body-rewrite on a DOCTRINE skill:**

```bash
TARGET="pages/skills/<skill>/SKILL.md"
# 1. Registry scan (AP-2 signal 1)
bash tools/session_scan.sh --overlap-with "$TARGET"

# 2. Recent-git-touch (AP-2 signal 3, NEW gate — mandatory for doctrine skills)
RECENT=$(git log --since='15.minutes.ago' --all --pretty='%h %an %s' -- "$TARGET")
if [ -n "$RECENT" ]; then
    echo "⚠️ $TARGET touched in last 15min:"
    echo "$RECENT"
    echo "→ PAUSE. Verify whether your intended edit duplicates or conflicts with the recent commit."
    echo "→ If duplicates: skip this edit (parallel session already shipped it)."
    echo "→ If conflicts: coordinate via Telegram before proceeding."
fi

# 3. Process-list (AP-2 signal 2) — catches unregistered live claude sessions
ps aux | grep -E "^[a-z]+ +[0-9]+.+ claude(\s|$)" | grep -v grep
```

All three checks MUST run before the first Edit tool call on a doctrine SKILL.md. Codify as a pre-edit ritual, not a post-hoc scan.

**What counts as a "doctrine skill" (enumerated, so the rule is mechanical):**
- `pages/skills/session-operating-contract/SKILL.md` — read every session-start
- `pages/skills/karpathy-loop/SKILL.md` — read every session-close
- `pages/skills/audit/SKILL.md` — read every /audit invocation + every SOAO
- `pages/skills/infrastructure/SKILL.md` — read on every deploy/restart
- `pages/skills/mistake-to-skill/SKILL.md` — read on every failure→skill codification
- `pages/skills/session-coordination/SKILL.md` — read every parallel-session check (this skill)
- `pages/skills/gbrain-ops/SKILL.md` — read on every gbrain op
- `pages/skills/evidence-verification/SKILL.md` — read on every DONE claim

Any new skill that becomes cross-cutting (read by >3 other skills' triggers, or referenced in CLAUDE.md top) joins this list.

**Post-close verification (session-close gate, AP-1 sibling):** after MASTER close, grep the just-bumped SKILL.md for duplicate headers:
```bash
grep -c "^### <AP-N>\b\|^### <rule-N>\." "$TARGET"  # expect 1, not 2
```
Session-60 should have run this for Rule 18; it didn't; session-57 caught the drift; codify so the next session runs it automatically.

**Compounding gate candidates (session 62+):**
(a) `tools/test_pre_edit_doctrine_gate.sh` — stub that wraps an Edit on a doctrine-skill with the 3-signal pre-edit check; fails the edit if unverified. **Still queued.**
(b) Pre-commit hook RULE 7 — for any doctrine-skill change, emit a warning if the commit author's session-id doesn't match the top-most timeline entry's session attribution; suggests duplicate-from-shared-directive. **Still queued.**
(c) `tools/test_no_duplicate_skill_headers.sh` — **SHIPPED session 63, 2026-04-22.** Parses all SKILL.md files under `pages/skills/*/` + `pages/tenants/*/skills/*/`, normalizes `###` headings (lowercase + whitespace collapse), flags intra-file duplicate normalized forms. POSITIVE-verified on real vault (0 dups across 10 skills); NEGATIVE-verified on `/tmp/fake-skill-dup-test` with byte-identical `### AP-1` dup → exit=1 with offending skill + normalized header listed. Supports `VAULT=<path>` env override for testing. Regression guard against AP-4 recurrence now mechanical.

**Cross-ref:** AP-1 (body-rewrite collision — different-content variant); AP-2 (3-signal awareness — this AP specifies WHEN each signal is mandatory); AP-3 (targeted close — separate lifecycle concern); `session-operating-contract` Rule 18 (no-defer-on-textbook-bug — duplicate-from-shared-directive IS a textbook class now that session-57 and 60 demonstrated it); `audit` AP-15 (codification ≠ self-application — session-60 codified AP-2 with `git log --since` as signal 3 but did not self-apply when editing SOC). No new LESSON (RULE ZERO).

### AP-5 — Cross-session stage-bleed: shared `.git/index` means `git add` in one session + `git commit` in another produces silent cross-attribution (session 68, 2026-04-23)

**Pattern:** Two sessions share a single working tree (same local clone). Session A runs `git add <A-file>` which stages A-file into the shared `.git/index`. Before A runs `git commit`, Session B runs `git add <B-file> && git commit -m '<B-message>'`. Because `git commit` with no path args commits **everything in the index**, B's commit now contains BOTH A-file AND B-file under B's authorial message. A's later `git commit` becomes a no-op ("no changes added to commit") because A-file already landed.

**What happened (session 68, 2026-04-23):**
- 13:15 — s68 (me) ran `git add pages/progress/HANDOFF-AUTO-2026-04-23-session-68-audit-and-claudemd-mirror.md` to stage the session handoff.
- 13:16 — Peer s67 ran `git add tools/daily-skill-evals.sh && git commit -m 'ship tools/daily-skill-evals.sh — Tan/Karpathy/Musk skillify Step 5 daily cron wrapper'`.
- Result: commit `9d8b45c5` landed containing **both files** (my 156-line handoff + s67's 109-line tool) under s67's authorial message. s68's HEREDOC authorial commit (per SOC v1.12 Rule 19) became a no-op.
- s67's commit message itself stated "No collision" — factually wrong because s67 only checked declared-scope overlap (correct: scopes were orthogonal) but NOT git-index overlap (the real channel).

**Root cause:** session-coordination v1.3's 3-signal pre-edit gate (registry + ps aux + recent-git-touch, AP-4) covers **file-content** collisions but NOT **git-index** collisions. The shared `.git/index` is a cross-session shared resource — declared-scope separation is not sufficient when multiple sessions can stage to the same index.

**Sibling class to AP-1 at the git-layer:**
- AP-1 (file-content collision): two sessions rewrite same file body → merge conflict OR duplicate.
- AP-5 (git-index collision): two sessions share staging → commit sweeps unintended files + wrong authorial attribution.

Both derive from the shared-substrate root. AP-1 is policed at the SKILL.md-body layer by 3-signal pre-edit gate. AP-5 must be policed at the `git commit` layer.

**Rule (binding, session-68+):**

**Use `git commit -o <path>...` (the `--only` flag) for every authorial commit on a shared working tree.** This form commits the *specified paths only*, bypassing the index for everything else. Cross-session stage-bleed is eliminated by construction — another session's `git add` cannot contaminate your commit.

```bash
# ✅ CORRECT — anti-collision commit (bypass index)
git commit -o pages/skills/<skill>/SKILL.md -m "$(cat <<'EOF'
<authorial HEREDOC per SOC v1.12 Rule 19>
EOF
)"

# 🔴 WRONG on shared working tree — sweeps whole index
git add pages/skills/<skill>/SKILL.md
git commit -m "..."  # may capture peer-session's staged files silently
```

**Legitimate uses of `git add` + `git commit`:**
- You are the only session on this working tree (verified by `bash tools/session_scan.sh` showing 0 parallel + `ps aux` showing 1 claude PID).
- Auto-sync daemon (it IS the only process running at that moment per cron schedule).
- Committing multiple intentional paths in one logical unit: use `git commit -o path1 path2 path3 -m '...'` (multi-path `--only` is supported).

**Detector (SHIPPED v0.1, session 72, 2026-04-24):** `tools/test_pre_commit_index_scope.sh` — POST-HOC surveillance scanner (NOT a git-commit wrapper). Scans last N commits (default 20, configurable via `LOOKBACK=`). For each commit:

- Skip auto-sync / vps auto-sync / air-sync / Merge (covered by AP-54 `test_authorial_commits.sh`).
- Extract path hints from commit subject line via regex (paths + backtick-quoted words matching `*.{md,sh,py,yaml,...}` or `(tools|pages|laws|docs|scripts)/...`).
- If subject hints at 1-3 specific paths (= narrow authorial scope) AND the actual diff has files NOT matching those hints → flag as **CANDIDATE stage-bleed**.
- Exit 0 clean, 1 if any candidates (warn-only; non-blocking).

**Musk-step-2 applied to v1.0 design:** v0.1 is intentionally registry-FREE and heuristic. The originally-queued v1.0 (registry-coupled — match commit author-time to Air session register/close intervals; compare diff to declared_scope globs) is **DEFERRED until N≥2 incidents justify the complexity**. v0.1 ships now because it's ~100 lines, no SSH dependency, fails-safe (no gate), and surfaces the class mechanically. Session-68 + session-71 dogfooding shows `git commit -o <paths>` muscle-memory is working (s71 used it 4 times successfully). Building the registry-coupled wrapper today would optimize before the real recurrence signal arrives.

**Dogfood (session 72):** scanned 20 commits; 1 CANDIDATE surfaced = my own task-5 commit "migrate AMD-005 + AMD-006 to canonical laws/AMENDMENT-NNN path". Hinted scope "laws/AMENDMENT-NNN" (regex matched the literal placeholder "NNN") didn't substring-match real diff files "laws/AMENDMENT-005-*.md" → flag. **False positive expected class** — multi-path bundled authorial commits with placeholder-in-subject will always flag. Tool is surveillance, not gate. Operator reviews flags; most will be FP on bundled logical commits. 4-target parity shipped Mac vault only (Air/VPS not yet — vault-to-runtime-rsync covers `pages/skills/`; tools/ rsyncs separately per wiki-to-runtime-rsync extension AP-53).

**Dogfood (session 68):** the addendum commit `a3443579` (156-line handoff post-forensics) AND this AP-5 codification commit (THIS commit) both used `git commit -o <path>` pattern. Zero collision, authorial HEREDOC preserved. Rule validated twice in first session of existence.

**Cross-ref:**
- `session-operating-contract` v1.12.0 Rule 19 (authorial commits discipline — AP-5 is the mechanical enforcement at git layer). Rule 19 says "agent commits own substantive work explicitly with authorial message"; AP-5 ships the technique that makes it physically robust under parallel-session conditions.
- `musk-algorithm` AP-1 (optimize-before-delete): AP-5 is Musk Step 5 (automate LAST) — we validated the rule in session 68 before wrapping it; wrapper `session_safe_commit.sh` stays DEFERRED to recurrence or next validation cycle, not rushed today.
- `session-coordination` AP-1 (file-content collision): sibling class at different layer.
- `audit` AP-21 (pagination — partial truth from single signal): s67's "No collision" assertion was a partial-truth-from-single-signal (declared-scope only, not index). AP-5 adds the missing signal.

No new LESSON (RULE ZERO upheld).

### AP-6 — Substrate path map: agents reading from the wrong host see "missing file" not "wrong-host" (session 74, 2026-04-25)

**Pattern:** OpenClaw factory agent (running in container with `/opt/nous-agaas/wiki/` mount) was given a checkpoint task that included a relative path `pages/task-results/`. The agent's CWD inside the workspace was `/home/node/.openclaw/workspaces/<agent>/`, NOT the wiki mount, so `pages/task-results/` resolved to `/home/node/.openclaw/workspaces/<agent>/pages/task-results/` — empty — agent honestly reported "missing pages/task-results/". Fixed by AP-30 in factory-ops (orchestrator pre-injects evidence in prompt). But the same root-cause class surfaced TWICE more on 2026-04-25 17:26 + 17:27 task-results: agent received an absolute Mac-host path `/Users/madia/...` from a task instruction and refused to fabricate a read because that path is unreachable from the OpenClaw sandbox. **Both times the agent was right to refuse**; the bug was task generation handing the wrong substrate path to the wrong agent.

**Substrate map (each path resolves on a SPECIFIC host; do not mix):**

| Substrate | Reachable paths | Unreachable from this substrate |
|---|---|---|
| **Mac-interactive Claude Code** | `/Users/madia/Documents/Projects/Nous AGaaS/...` (vault), `/Users/madia/.claude/...` (CC config), `/tmp/...`, `~/.local/bin`. ssh remote: `air`, `root@65.108.215.200`. | Air-host filesystem (only via ssh); Docker container internals (must `docker exec`). |
| **Air-interactive shell (ssh air)** | `/Users/madia/nous-agaas/...` (Air vault working copy + tools/ + sessions/ + state/), `/Users/madia/Library/LaunchAgents/...` (Mac-style on Air's M2 hardware), Docker daemon (Air hosts OpenClaw). | Mac-host filesystem (only via reverse ssh which we don't use); container `/opt/nous-agaas/` filesystem (must `docker exec openclaw`). |
| **OpenClaw container (`agent --local`, factory tasks, `/code` flow)** | `/opt/nous-agaas/wiki/` (read-only mount of Air's `/Users/madia/nous-agaas/wiki/`), `/opt/nous-agaas/skills/` (mount of Air's `/Users/madia/nous-agaas/skills/`), `/home/node/.openclaw/workspaces/<agent>/` (per-agent ephemeral CWD). | Mac-host paths (`/Users/madia/...` on Mac); Air-host paths outside the mounts (`/Users/madia/nous-agaas/tools/`, `~/.claude/`, `~/Library/...`); other Air substrates. |
| **VPS shell (`ssh root@65.108.215.200`)** | `/root/nous-agaas/wiki/` (working copy), `/root/nous-agaas/obsidian-wiki.git` (bare), `/opt/nous-agaas/...` (legacy + Langfuse + NCAnode), `/var/log/...`. | Mac-host + Air-host filesystems (only via reverse ssh). |
| **gbrain MCP / QMD MCP** | gbrain page slugs (e.g. `pages/skills/factory-ops/skill`, no leading slash); QMD path-glob queries (collections, `nous` only). | Filesystem paths of any flavor — both MCPs operate on slug/path-relative-to-collection, not absolute filesystem paths. |

**Rule (binding for task-generation, prompts, and dispatch):**

When you write a task that another substrate will execute, the path arguments MUST be reachable from THAT substrate. If unsure, prefix the path with the substrate name and verify reachability before dispatch:
- `MAC: /Users/madia/Documents/Projects/Nous AGaaS/...` — only Mac CC can read this
- `AIR: ~/nous-agaas/wiki/...` — Air shell + Air launchd can read; OpenClaw cannot (use `WIKI: pages/...` instead, the container-relative form)
- `WIKI: pages/skills/<name>/SKILL.md` — relative-to-wiki form; reachable from Mac CC (cwd vault), Air shell (cwd ~/nous-agaas/wiki), VPS shell (cwd /root/nous-agaas/wiki), AND OpenClaw container (cwd /opt/nous-agaas/wiki). This is the safest path form for cross-substrate task generation.

**Detection:** if an agent honestly reports "file not found / missing X" and the path was injected by another substrate, **do not assume the agent failed** — verify the path was reachable from that substrate's mount map FIRST. The agent's refusal is correct under LAW-013 (no fabrication).

**Compounding artifact (queued, session-75+):** `tools/test_substrate_path_routing.sh` — scan task-prompts in `pages/task-results/` for absolute Mac-host paths handed to OpenClaw-routable agents (`agent_id` ∈ `{nous, grok-ceo, ...}`). Posthoc surveillance, exit 0 clean / 1 if any candidates. Same shape as AP-5's `test_pre_commit_index_scope.sh` (detect-after, surface to operator, no gate).

**Cross-ref:**
- `factory-ops` AP-30 (substrate-aware prompt injection: orchestrator runs `_recent_task_results(8)` on Air host BEFORE dispatch) — sibling fix at the prompt-construction layer.
- `factory-ops` AP-31 (orchestrator owns file I/O; agent only returns body text) — same root-cause class at the write-side.
- `audit` AP-10 (LAW-013 verification: refuse to fabricate from unreachable substrate) — the agent's correct behavior in this AP's dogfood examples 17:26/17:27.
- `LAW-013` — agent must not fabricate; "missing file" is the truthful response when path is unreachable.

**Why this lives in session-coordination, not audit:** session-coordination is the substrate-routing skill (per its name + scope). `audit` AP-10 already covers the agent-side "refuse to fabricate" correctly. The missing piece is **task-side**: who writes the prompt with the right path. That's coordination across substrates. session-coordination owns it.

No new LESSON (RULE ZERO upheld).

### AP-7 — Whole-file JSONL slurp makes the session scanner blind when one registry row is corrupt (session 81, 2026-04-29)

**Pattern:** `tools/session_scan.sh` read Air's append-only `active-sessions.jsonl` and piped the full file into `jq -s`. One malformed historical close record (`+\\1:\\2` timezone artifact) made `jq` fail for the entire registry. Because stderr was swallowed, SOAO Section 8 printed `🟡 PARALLEL:  active session(s)` and `--json` returned zero bytes even though live sessions were registered.

**Root cause:** an append-only coordination log was treated as an all-or-nothing JSON document stream. In append-only operational logs, one bad row is data quality debt, not permission for the scanner to go blind.

**Fix (SHIPPED):** `tools/session_scan.sh` now normalizes input with `jq -Rrc 'fromjson? | select(type=="object")'` before grouping sessions. Invalid rows are ignored; valid rows still drive active-session and overlap output. Existing E2E suite remains green.

**Rule:** every future reader of `~/nous-agaas/state/active-sessions.jsonl` must be row-tolerant. If it needs strictness, strictness belongs in a separate audit command, not in the live coordination path that agents depend on for handshakes.

**Verification:** red reproduced on production registry (`session_scan.sh --json` produced `bytes=0`; human scan printed malformed count). Green after patch: `session_scan.sh --json` returned a JSON array with the registered session; human scan printed `PARALLEL: 1 active session(s)`; `test_session_coordination_e2e.sh` reported `8 pass, 0 fail`.

No new LESSON (RULE ZERO upheld).

### AP-8 — E2E tests that truncate the live registry break the handshakes they are supposed to verify (session 81, 2026-04-29)

**Pattern:** `tools/test_session_coordination_e2e.sh` backed up and truncated the production Air `active-sessions.jsonl`. During a four-lane audit, this erased live lane registrations and left the central registry proving only one coordinator session. The same test also called `session_register.sh` without `SESSION_ID_FILE`, overwriting the account-global `current_session_id` with fixture IDs.

**Root cause:** verification shared the same mutable substrate as production coordination. A test that rewrites the live registry is not a test; it is a coordination incident generator. The single-file session pointer was also a hidden single-writer assumption, incompatible with four simultaneous Codex/Claude lanes.

**Fix (SHIPPED):**
- `SESSION_REGISTRY_PATH` now overrides the Air registry path for register/scan/heartbeat/close/cleanup.
- `test_session_coordination_e2e.sh` uses an isolated test registry and temporary ID file/dir, then deletes only those test artifacts.
- `session_register.sh` writes both the compatibility `current_session_id` and a per-session active ID file.
- `session_heartbeat.sh` heartbeats all active ID files plus the compatibility current file.
- `session_close.sh` removes the matching active ID file when closing.
- `cron_session_cleanup.sh` honors `SESSION_REGISTRY_PATH` and ignores corrupt rows.

**Verification:** `test_session_coordination_e2e.sh` reported `8 pass, 0 fail`; production registry line count stayed `3 -> 3`; live `session_scan.sh` still showed the coordinator session after the test.

No new LESSON (RULE ZERO upheld).

### AP-9 — Exact-string overlap checks miss the same file under different working-directory prefixes (session 81, 2026-04-29)

**Pattern:** `session_scan.sh --overlap-with` only checked whether a requested path string exactly appeared in `declared_scope`. A session declaring `Nous/pages/skills` did not overlap a caller checking `pages/skills/session-coordination/SKILL.md`, and `*`/parent-directory scopes were not treated as broad ownership.

**Root cause:** coordination scopes are human-authored strings from different host contexts. Treating them as exact IDs ignores the repo's real path shape.

**Fix (SHIPPED):** overlap filtering now normalizes paths (`./`, leading `Nous/`, trailing slashes), honors `*`, and treats parent/child path-prefix relationships as overlap. E2E now asserts `Nous/pages/skills` intersects `pages/skills/session-coordination/SKILL.md`.

No new LESSON (RULE ZERO upheld).

### AP-10 — Air-local registry tools that SSH to `air` make Air sessions invisible (session 81, 2026-04-29)

**Pattern:** after syncing v1.9 to Air, running `tools/session_scan.sh` from Air returned `[]` because the script tried `ssh air` from Air and swallowed the failed lookup as an empty registry. The E2E test also failed on Air when its direct `ssh air` calls could not resolve the alias.

**Root cause:** the coordination registry is Air-local, but the tooling assumed the caller is always Mac. That breaks the exact sessions Madi asked to coordinate: Air-spawned `/codex` and Claude Code lanes.

**Fix (SHIPPED):** register/scan/heartbeat/close now detect Air by hostname and use local file I/O there; Mac continues to use `ssh air`. The E2E test's direct Air commands use the same local-vs-ssh transport helper.

No new LESSON (RULE ZERO upheld).

### AP-11 — Orphan heartbeat rows survive cleanup and create invisible registry debt (session 81, 2026-04-29)

**Pattern:** after the E2E test overwrote `current_session_id` with a fixture ID, the heartbeat launchd job appended heartbeat-only rows for `s99-*`. `session_scan.sh` ignored them because there was no register record, but `cron_session_cleanup.sh` kept them because it only looked at freshness/closed state.

**Root cause:** cleanup and scan disagreed on what counts as a valid active session. Scan required a register record; cleanup did not. That made invisible registry debt accumulate and kept strict JSONL/data-quality probes noisy.

**Fix (SHIPPED):** `cron_session_cleanup.sh` now computes `has_register`; active output keeps only non-closed, fresh, registered sessions. Closed, stale, malformed, and no-register groups are archived. E2E now injects a corrupt row plus orphan heartbeat and verifies strict JSONL recovery, no orphan remains, and the valid active record survives.

No new LESSON (RULE ZERO upheld).

### AP-12 — Subagent research lanes are not write capacity; real 4-lane parallelism is driver + 2 writers + 1 factory worker (session 82c, 2026-04-29)

**Pattern:** Madi's standing directive is "make sure 4 simultaneous sessions are happening with handshake; help each other out; do not disturb." Sessions 81 + 82 dispatched 3 read-only `Agent` subagent lanes alongside the driver and called this "the four-lane handshake." It WORKED for research (Lane B web-fetched upstream gbrain status; Lane C scanned Mercury prereqs; Lane D verified peer activity) but it is NOT real writer parallelism — subagents return findings to the driver and never acquire stream locks, never commit, never carry independent scope.

**Root cause:** confusion between **research parallelism** (cheap; bounded by subagent token budget) and **writer parallelism** (real; requires multiple harness instances each holding a stream claim). Subagents amplify *one* writer's research throughput. They do not multiply *writers*. Conflating them lets a session feel like 4-lane while only ever being 1-lane writer.

**Rule — real 4-lane decomposition:**
1. **Lane 1 (driver)**: 1 Mac CC session, holds `stream_a` claim, owns the critical path. Commits via `git commit -o <path>` for surgical anti-collision.
2. **Lane 2 (writer #2)**: 1 second writer on a different harness — `/code` from phone, OR Codex CLI in another shell, OR a second Mac CC window if the user is willing. Acquires its OWN claim (e.g., `stream_b`), owns a parallel-safe scope (e.g., Mercury Phase 2 while driver handles substrate-S0). Commits independently; rebase + `commit -o` to anti-collide with Lane 1.
3. **Lane 3 (factory worker)**: 1 OpenClaw / DeepSeek V4 Flash background worker on the `/ask` queue or scheduled job. Owns long-running labor. Writes via `auto_checkpoint.py` orchestrator pattern — never directly to git.
4. **Lane 4 (research bursts)**: ephemeral `Agent` subagents OR `Skill(plan-eng-review)` etc. dispatched by ANY of lanes 1-3 when they need parallel research. Read-only by contract. Never holds a claim. Returns findings within the dispatching lane's commit.

**Substrate IS the handshake.** No agent talks to another directly. Skills + facts.jsonl + handoffs are the shared write-through memory. SOAO Section 8 + `session_scan.sh` make ownership visible. `git commit -o` makes commits non-overlapping. Auto-sync absorbs to all 4 git targets.

**Detection (mechanical):** when a session claims "4 lanes running," check `~/nous-agaas/state/active-sessions.jsonl` for 4 distinct `session_id` values with `status=active` and timestamps within heartbeat freshness. Subagent dispatches do NOT appear there. If only 1 active session-id exists, the session has subagent lanes (research) not writer lanes (parallelism). State this honestly in handoffs.

**Spawn protocol when Madi asks for "4 simultaneous sessions":**
- Driver acquires `stream_a` (or `stream_b/c/d`) and announces scope.
- Driver tells Madi exactly which Lane 2 to spawn (`/code` from phone OR `codex` CLI in shell), with a self-contained prompt + scope boundary + claim handle.
- Lane 3 is the always-running factory; no spawn needed if `com.nous.telegram-poll` is up and `/ask` queue accepts work.
- Lane 4 is dispatched per-task by whichever writer needs research. No registry entry.
- Driver writes a coordination plan into the handoff so the spawned writer reads cold context with claim + scope.

**Cross-ref:** AP-5 (cross-session stage-bleed `git commit -o`), AP-6 (substrate path map per host), this skill's "Rules absorbed" `infrastructure` AP-34, `karpathy-loop` AP-8 (substrate-evolution Musk-step-2 self-audit — apply BEFORE spinning up Lane 2 to avoid parallelizing deletable work), `session-architecture` 1+3 dispatch model.

**Why no new LESSON file:** RULE ZERO. Empirical evidence in [[HANDOFF-AUTO-2026-04-29-session-82-substrate-S0-beta-insufficient]] (3 subagent lanes called "4-lane handshake" — corrected to "1 driver + 3 research bursts") and session 82c continuation block (this AP).

### AP-13 — SessionStart hook fires ONCE per CC restart, not per /clear or continuation; long sessions may have empty registry (session 82e, 2026-04-29)

**Pattern:** Session 82e Lane G audit found `~/nous-agaas/state/active-sessions.jsonl` was **0 bytes** while a 3-hour Mac CC driver session was actively running (s82e holding Stream-A). The driver had not appeared in the registry the entire session. AP-13 is a doctrine clarification: the SessionStart hook (`~/.claude/hooks/session-start-soao.sh`) fires only on a fresh Claude Code launch. It does NOT fire on `/clear`, `/reset`, conversation continuation, or wake-from-sleep. Long sessions that started hours ago may have stale or missing registry entries even when the session is healthy.

**Root cause:** Confusion between "session" as a CC harness instance and "session" as a conversation. The registry tracks the former; agents perceive the latter. Hook fires on CC restart; conversations span multiple "sessions" by the registry's definition.

**Rule:** When the registry shows 0 active sessions, **DO NOT** interpret that as "no peers active." Possible causes: (a) hooks fired but Air SSH was transiently unreachable → silent failure (b) sessions are in long-continuation mode without re-fire (c) cleanup cron just truncated stale entries. Always cross-check `who` / `ps aux | grep claude` / Stream-A claim file before declaring a session solo.

**Fix (SHIPPED):** `tools/session_self_register.sh` — idempotent script any session can call to ensure it appears in the registry. Reads `~/.claude/sessions/current_session_id` by default, honors `SESSION_ID_FILE` / `SESSION_REGISTRY_PATH` for tests, derives the vault path from its own script location, cross-checks Air registry presence, re-registers if absent. Default no-op when already registered + fresh; `--force` for explicit re-register. Falls back to `pending-registers.jsonl` queue when Air unreachable (uses existing recovery path).

**Detection (mechanical):** add to SOAO Section 8 a "self-register check": if Mac CC process is running (lsof on /Users/madia/.claude/) AND `current_session_id` is empty OR not in Air registry → print 🟡 `not registered (long-session AP-13); run tools/session_self_register.sh to attach`. Tool detector candidate: `tools/test_session_self_register.sh` for unit-level confirmation that the script registers + idempotent + survives Air-unreachable.

**Cross-ref:** AP-12 (real 4-lane writer parallelism — depends on registry actually working), AP-5 (cross-session stage-bleed — also depends on visibility), `infrastructure` AP-34 (parallel session detection — registry is the substrate AP-34 anticipated).

**Why no new LESSON file:** RULE ZERO. Empirical evidence: Lane G audit transcript + manual `bash tools/session_register.sh` from s82e successfully wrote line 1 → registry went 0 → 3 lines after manual + heartbeat fires. Doctrine alone, doctrine + retry tool ships next.

### AP-14 — Doctrine asserted a recovery path that was never implemented (session 82f, 2026-04-29)

**Pattern:** AP-13 (shipped session 82e) said `tools/session_self_register.sh` falls back to `pending-registers.jsonl` when Air SSH is unreachable, and that "next successful heartbeat flushes the queue." Lane K audit (s82f) found this drain code was **NEVER IMPLEMENTED**. `tools/session_heartbeat.sh` only handled `pending-heartbeats.jsonl` (and even there, no flush — only enqueue on Air-fail). The doctrine described a recovery pipeline that ended in `/dev/null`. Currently harmless (Air reachable + write succeeds), but the moment Air goes down, queued registers and queued heartbeats accumulate forever with no drainage.

**Root cause:** documentation sprint (codifying AP-13) shipped before the doctrine's mechanical claims were verified end-to-end. The 3-edit ritual (frontmatter + H1 + Timeline) catches version drift, NOT *"does the recovery path the AP describes actually exist in code?"*. AP-13 self-applied incompletely.

**Rule:** any AP that claims a recovery path / drain pipeline / fallback handler MUST be paired with a same-session dogfood test that exercises the failure path end-to-end. Concretely: "queue grows when X breaks; queue drains when X recovers; net=0 after a round-trip." Without this dogfood, the AP is doctrine-as-fiction.

**Fix (SHIPPED):** `tools/session_heartbeat.sh` now drains BOTH `pending-heartbeats.jsonl` AND `pending-registers.jsonl` on every successful Air round-trip. Truncates after successful flush. Dogfood verified s82f: wrote a fake `s99-test-drain-2` register entry to the queue, ran heartbeat, observed queue 1 → 0 lines + Air registry contains the drained entry. Cleanup removed the test row.

**Detection (mechanical):** `tools/test_pending_queue_drain.sh` writes one pending register and one pending heartbeat into an isolated temp pending dir, runs `session_heartbeat.sh` against an isolated Air-side test registry, and verifies both queues drain to zero and all three expected records land in the registry.

**Cross-ref:** AP-13 (this AP fixes the missing half of AP-13's claim), `karpathy-loop` AP-8 (substrate-evolution Musk-step-2: question the premise — does the recovery code exist? Apply this BEFORE codifying).

**Why no new LESSON file:** RULE ZERO. Dogfood evidence captured in s82f handoff. Cap holding 24/129.

### AP-15 — Local Codex sessions had no lifecycle hook, so the handshake skipped a whole writer class (session 83, 2026-04-29)

**Pattern:** Lane B lifecycle audit found Claude Code had `~/.claude/settings.json` SessionStart coverage, Telegram `/code` and `/codex` had command-center context injection, but local interactive Codex had no equivalent hook. `~/.codex/AGENTS.md` was also empty. A human could open Codex locally, edit shared substrate, and never appear in `active-sessions.jsonl`, making the four-session handshake incomplete.

**Root cause:** the registry assumed every writer has a lifecycle event. Codex desktop/CLI does not currently expose a project SessionStart hook we can wire the same way as Claude Code. Treating "Codex reads AGENTS.md" as equivalent to "Codex is registered" confused instruction memory with operational visibility.

**Rule:** local interactive Codex sessions that may touch Nous AGaaS must launch through `tools/codex-nous.sh` or an equivalent wrapper. A blank or instructional `~/.codex/AGENTS.md` is not a handshake. The mechanical contract is: register first, then exec Codex.

**Fix (SHIPPED):** `tools/codex-nous.sh` runs `tools/session_self_register.sh --intent "$CODEX_SESSION_INTENT" --scope "$CODEX_SESSION_SCOPE"` and then execs `CODEX_BIN`, PATH `codex`, or the Codex.app binary fallback. `tools/test_codex_nous_launcher.sh` uses a fake Codex binary plus isolated Air-side registry to prove the launcher writes a session id, creates one active registry row, preserves intent/scope, and then execs Codex with the original args.

**Detection (mechanical):** `tools/test_codex_nous_launcher.sh` must stay green. `tools/test_top_cto_loop_wired.sh` must also stay green when invoked from the wiki copy and from the Air runtime tools copy; runtime tools resolve the canonical wiki via `../wiki` when `pages/skills` is not adjacent. A future Codex hook can replace the wrapper only after an E2E test proves a fresh local Codex process appears in `session_scan.sh` without manual launch discipline.

**Cross-ref:** AP-12 (real four-session handshake depends on real writer visibility), AP-13 (self-register helper), AP-14 (doctrine claim must have code + dogfood), `karpathy-loop` AP-8 (Musk step-2 the premise: "is this writer class actually visible?").

**Why no new LESSON file:** RULE ZERO. Doctrine lives here; gbrain timeline is evidence.

### AP-16 — Mac/wiki-green recovery tests can still fail on Air runtime layout (session 83, 2026-04-29)

**Pattern:** After the local Codex launcher passed on Mac and Air wiki, Air runtime verification found two portability holes: `tools/test_top_cto_loop_wired.sh` was green from the wiki but false-red from the Air runtime copy because it assumed wiki-style skill paths, and `tools/session_heartbeat.sh` drained pending queues only on the Mac→Air SSH branch, not the Air-local branch. `/codex` and `/code` lanes run on Air, so this was a real factory-path gap.

**Root cause:** verification stopped at Mac/wiki equivalence before executing the exact runtime root where Air agents run. AP-14 fixed the remote-caller recovery path, but the Air-local branch returned before the drain block.

**Rule:** session-coordination recovery and wiring gates must be verified in three roots before being treated as factory-safe: Mac wiki, Air wiki, and Air runtime (`~/nous-agaas`). Runtime-aware tests must resolve both skill layouts: wiki `pages/skills/...` and runtime `skills/...`.

**Fix (SHIPPED):** `tools/session_heartbeat.sh` now drains pending queues through one shared `drain_pending_queues` helper after both Air-local writes and remote SSH writes. `tools/test_top_cto_loop_wired.sh` resolves the canonical skill root from `pages/skills` when present, otherwise `skills`, and can run from the runtime tools copy.

**Detection (mechanical):**
```bash
ssh air 'cd ~/nous-agaas && bash tools/test_pending_queue_drain.sh'
ssh air 'cd ~/nous-agaas && bash tools/test_top_cto_loop_wired.sh'
```

**Cross-ref:** AP-10 (Air-local tools must not SSH to `air`), AP-14 (pending queue drain), AP-15 (local Codex launcher), `gbrain-ops` AP-48 (runtime injection must preserve salient facts, not just docs).

**Why no new LESSON file:** RULE ZERO. Runtime failure is codified into this skill and gbrain timeline.

### AP-17 — Air-unreachable registry scans and queued registers must be yellow, not false-green (session 86, 2026-04-29)

**Pattern:** Helper audit found `session_scan.sh` collapsed SSH failure and a genuinely empty Air registry into the same `RAW=""` branch, printing `✅ no other active sessions`. The same audit found `session_self_register.sh` could queue a register locally during Air outage while printing `✅ registered`, making a lane look centrally visible when it was only pending.

**Rule:** Air-unreachable coordination is degraded, not clean. `session_scan.sh` must print a yellow unavailable state and exit nonzero when it cannot read Air. `session_self_register.sh` may stay non-blocking and queue the record for heartbeat drain, but it must say `queued` / `not centrally visible` instead of `registered`. A four-session handshake is proven only by a later `session_scan.sh` that sees the lanes in the central registry.

**Fix (SHIPPED):** `session_scan.sh` now distinguishes remote fetch failure from empty registry and supports `SESSION_FORCE_REMOTE=1` for tests. `session_register.sh` checks Air-local registry write failures before returning central-registration success. `session_self_register.sh` writes queued session ids for heartbeat draining but reports them as not centrally visible. `tools/test_session_coordination_e2e.sh` covers the Air-unreachable false-clear branch; `tools/test_session_self_register.sh` covers queued self-register output and pending queue creation on both Mac-remote and Air-local execution paths.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/session-coordination/skill`.

### AP-18 — Self-register idempotency must check active set, not raw registry rows (session 86, 2026-04-29)

**Pattern:** Codex landed-commit review found `session_self_register.sh` treated any raw registry line containing the current `session_id` as proof of active registration. Closed and stale sessions still contain that ID, so a continuation could print `already registered` while the active handshake was actually empty.

**Rule:** Idempotency checks must use the same active-session projection as humans: `session_scan.sh --json`, which filters close records and stale heartbeats. Raw registry grep is acceptable for forensics, not for live registration truth.

**Fix (SHIPPED):** `session_self_register.sh` now asks `session_scan.sh --json` whether the SID exists in the active set, and `tools/test_session_self_register.sh` covers the closed-SID re-registration path.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/session-coordination/skill`.

### AP-19 — Overlap scans must expand glob scopes against exact paths (session 88, 2026-04-29)

**Pattern:** A live read-only verifier found active lanes claiming glob scopes like `tools/session_*.sh` and `pages/skills/*/SKILL.md`, while `session_scan.sh --overlap-with tools/session_scan.sh` and `--overlap-with pages/skills/session-coordination/SKILL.md` printed false-clear. Querying the same glob text found the lane, so the bug was in scope/path intersection rather than registry visibility.

**Rule:** Declared scopes are allowed to be shell-style globs. The overlap predicate must treat a glob owner as overlapping any exact path it matches, and a glob query as overlapping any exact owner it matches. Exact equality and parent/child prefix checks are insufficient for pre-edit safety.

**Fix (SHIPPED):** `session_scan.sh` now converts `*`/`?` glob scopes into anchored regexes inside the overlap predicate. `tools/test_session_coordination_e2e.sh` adds regressions proving `tools/session_*.sh` matches `tools/session_scan.sh`, `pages/skills/*/SKILL.md` matches a concrete skill file, and glob-to-glob queries still work.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/session-coordination/skill`.

### AP-20 — Auto-sync `git pull --rebase` produces working-tree conflict markers on hot multi-host wiki files (session 85, 2026-04-29; 4× recurrence)

**Pattern:** Session 85 observed `pages/skills/session-coordination/SKILL.md` regaining `<<<<<<< Updated upstream` / `======= ` / `>>>>>>> Stashed changes` markers in the Mac working tree FOUR separate times across one session — each time after a `wiki-sync` launchd cycle ran `git fetch && git pull --rebase` against VPS. Air working tree was clean throughout (1.20.0 with no markers); only Mac kept regaining them. Pre-commit parity hook hard-blocks any commit while markers exist, so every authorial commit was blocked until manual resolution. Across the session: 5 conflict blocks resolved on recurrence #1, 3 on #2, 3 on #3, 5 on #4 (this codification).

**Root cause:** `tools/wiki-sync.sh` (and the auto-sync sibling) does a `git stash → git pull --rebase → git stash pop` cycle for safety on uncommitted Mac edits. When the upstream rebase changes the same lines the local stash touched, `git stash pop` produces conflict markers tagged `<<<<<<< Updated upstream` (the rebased upstream side) vs `>>>>>>> Stashed changes` (the local stashed side). Auto-sync's `git add -A && git commit` then commits the conflicted file as-is, propagating the markers to VPS bare → back to Mac next cycle. The cycle compounds.

**Why session-coordination/SKILL.md specifically:** highest write-frequency skill in the substrate during high-parallelism sessions (every peer touches it for AP additions). Probability of stash-pop conflict scales with peer-cadence × file-write-rate.

**Rule:**

1. **Detection (mechanical):** pre-commit hook should reject any staged file containing `<<<<<<< ` / `======= ` / `>>>>>>> ` at line start. Currently the parity hook catches it indirectly (via YAML-invalid frontmatter on hot files), but a direct marker-presence gate is cheaper + clearer.
2. **Recovery (mechanical):** the regex `<<<<<<< Updated upstream
(.*?)=======
.*?>>>>>>> Stashed changes
` (DOTALL) reliably resolves auto-sync stash-pop markers by keeping the upstream side, which is the authorial peer work. The "Stashed changes" side is by definition older/stale local state. **Never keep "Stashed changes"** unless the local stash is verified-newer (rare; usually a sign that auto-sync's stash predated authorial uncommitted work).
3. **Prevention (deferred — needs separate session):** `tools/wiki-sync.sh` should: (a) refuse to auto-commit files containing markers, (b) emit a Telegram alert on stash-pop conflict instead of committing it, (c) stop and surface the conflict to the operator, (d) consider switching from `stash → rebase → pop` to `merge --no-rebase` which produces clearer marker provenance and a single resolution point.

**Verification (this session):** After Mac-side regex resolution + commit + push, Air working tree stayed clean. The recurrence cycle was always Mac-pull-from-VPS-bare. VPS bare repo never had markers in HEAD (verified via `git show <commit>:pages/skills/session-coordination/SKILL.md | grep -c "^<<<<<<< "` → 0). Markers were transient working-tree artifacts of the stash-pop cycle, NOT committed state — but pre-commit hook still blocks until cleared.

**Detector:** `tools/test_no_merge_markers.sh` — scans tracked/staged files for line-start git conflict markers. Wired into pre-commit before parity checks in v1.22/AP-21.

**Cross-ref:** `infrastructure` AP-30 (parallel-agent concurrent write race — this is a special case), `gbrain-ops` AP-29 (auto-sync regex format drift — same auto-sync class), session-operating-contract Rule 19 (`git commit -o <path>` anti-collision — partial mitigation, doesn't help with stash-pop class).

**Why no new LESSON file:** RULE ZERO. The pattern + recovery + prevention path live here + gbrain timeline on `pages/skills/session-coordination/skill`.

### AP-21 — Merge-marker detection must be a pre-commit gate, not a handoff wish (session 91, 2026-04-29)

**Pattern:** Session 91 reopened after the top-CTO closeout and immediately hit the AP-20 class again: `tools/session_scan.sh` failed with `syntax error near unexpected token '<<<'`, and nine files were in `UU` state with `<<<<<<< Updated upstream` / `>>>>>>> Stashed changes` blocks. AP-20 already named the root cause and queued `tools/test_no_merge_markers.sh`, but the detector was not yet enforced.

**Root cause:** Detection was documented as a candidate, not wired into the hook. A candidate detector is not a gate; auto-sync and human commits can still carry marker files until the scanner is executable and invoked before the usual YAML/version parity checks.

**Rule:** any repository-local or canonical pre-commit hook for the wiki must run `bash tools/test_no_merge_markers.sh --staged` before skill, MD5, lesson, or env gates. The marker gate must fail directly on line-start `<<<<<<<`, `=======`, or `>>>>>>>` signatures so the operator sees the actual disease instead of a downstream YAML/frontmatter symptom.

**Fix (SHIPPED):** `tools/test_no_merge_markers.sh` scans tracked files or staged paths, skips raw/binary artifacts, and reports marker-bearing files. `tools/pre-commit-hook-tan-pattern.sh` and the live `.git/hooks/pre-commit` call it as RULE 0.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/session-coordination/skill`.

### AP-22 — Staged marker gates must scan index blobs, not worktree files (session 91, 2026-04-29)

**Pattern:** The first v1.22 marker gate listed staged paths via `git diff --cached --name-only`, then grepped the worktree copy of each path. A bad staged blob could pass if the operator cleaned the worktree without restaging.

**Root cause:** the hook confused "which path is staged" with "what content is staged." Pre-commit gates must verify the exact index blob that `git commit` will write.

**Rule:** staged-content detectors must read from the index (`git show ":$path"` or equivalent), not the worktree. If a detector supports both tracked and staged modes, explicitly test the staged-bad/worktree-clean case in a temp repo.

**Fix (SHIPPED):** `tools/test_no_merge_markers.sh --staged` now scans `git show ":$path"` for each staged ACMR file. `tools/test_no_merge_markers_e2e.sh` proves the staged-bad/worktree-clean regression in a temp repo: the bad index blob returns exit 1 and reports `a.txt`, then passes after the cleaned blob is staged.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/session-coordination/skill`.

### AP-23 — PREVENTION layer for AP-20 class: skip stash-dance when working tree is clean (session 82r, 2026-04-29)

**Pattern:** AP-20 (auto-sync stash-pop produces conflict markers, 4× recurrence in s85), AP-21 (pre-commit gate added), AP-22 (gate fixed to scan index). Detection layer is now bulletproof — but the underlying class keeps RECURRING. Round 14 (s82p) cleaned 9 files. Round 15 (s82q) found markers AGAIN at session-start. Round 16 (s82r): N≥3 recurrence in one calendar day. The detector catches; the **prevention** is missing.

**Root cause of recurrence:** every session-start ritual (mine + peer + auto-sync cron) does the same `git stash push -u && git pull --rebase && git stash pop` cycle even when the working tree is CLEAN. When clean, the stash is empty → `stash push` is a no-op → but if remote moves between `push` and `pop`, peer's auto-sync may have committed conflicting content into the index that pop then pollutes. Even when there's nothing to stash, the dance can produce markers via auto-sync race.

**Prevention rule:** session-start sync MUST check `git status --porcelain` first. If empty: skip stash entirely, do bare `git pull --rebase` (no markers possible). If dirty: pre-check whether any dirty file is also touched by upstream commits we'd pull in. If overlap → exit 1 with manual resolution paths (commit dirty work first OR discard OR explicit stash + manual conflict-resolve). If no overlap → safe to stash + pull + pop (small remaining race window, but no overlap = no marker class).

**Fix (SHIPPED):** `tools/session_safe_sync.sh` — drop-in replacement for the stash-pull-pop ritual. Three modes:
- Clean tree → bare `git pull --rebase` (most sessions, fastest, zero risk)
- Dirty + no remote-overlap → traditional stash dance (small race remaining)
- Dirty + remote-overlap → exit 1 + 3 manual paths (A: stash with manual resolve / B: commit first / C: discard)

Dogfood evidence (s82r): clean tree → "✅ working tree clean — direct rebase (no stash dance)" exit 0; dirty tree (mid-session with this AP being authored + peer-modified `nous-obsidian-sync.sh`) → "🟡 working tree dirty: ... no upstream commits to pull — staying as-is, no sync needed" exit 0. Zero markers possible in either path.

**Detection (mechanical):** future session-start scripts that still use raw `git stash push -u + git pull --rebase + git stash pop` are detectable via `grep -l 'git stash push.*git pull.*git stash pop' tools/ ~/.claude/hooks/ -rE`. Tool detector candidate: `tools/test_no_raw_stash_pop_in_session_start.sh` — flags any script that uses the brittle pattern instead of `session_safe_sync.sh`.

**Cross-ref:** AP-20 (the class this PREVENTS), AP-21 (detection layer at commit-time), AP-22 (detection scope fix), `karpathy-loop` AP-9 (round-15 named N≥3 recurrence; round 16 ships the prevention).

**Why no new LESSON file:** RULE ZERO. The prevention rule + tool ship together.

### AP-24 — Auto-sync `git merge -X theirs` can leave inline markers; post-merge guard refuses to push polluted worktree (session 82s, 2026-04-29)

**Pattern:** Round-17 audit traced the auto-sync-side recurrence source for the AP-20 class. `tools/nous-obsidian-sync.sh` falls through to `git merge -X theirs vps/main` when rebase fails (line 230). `-X theirs` auto-resolves most conflicts BUT can leave inline `<<<<<<<` / `=======` / `>>>>>>>` markers when both sides edited the same lines (edit-edit collision the strategy can't disambiguate). The merge "succeeds" (exit 0), the script logs "rebase failed, used merge -X theirs fallback", and pushes the polluted worktree to VPS bare. Next pull on Mac brings the markers back to the working tree → AP-20 recurrence.

**Root cause:** `git merge -X theirs` is documented as "favor theirs on conflict" — but for non-trivial overlapping edits, Git refuses to invent a resolution and writes markers. The strategy reduces but doesn't eliminate the marker class. Without a post-merge guard, polluted state propagates.

**Fix (SHIPPED):** `tools/nous-obsidian-sync.sh` step 3.5 (between merge and push) runs `tools/test_no_merge_markers.sh` against the worktree. If markers found → log FAIL + `return 1` BEFORE the push. Polluted state stays local; next manual run can resolve cleanly.

**Detection (mechanical):** `tools/test_no_merge_markers.sh` (already wired into pre-commit by AP-21). The same detector now gates auto-sync push too. Tool detector candidate: `tools/test_obsidian_sync_marker_guard.sh` — temp-repo simulation that injects an edit-edit conflict, runs the sync script, asserts push is BLOCKED + markers stay local.

**Empirical reference (s82s):** No scripts other than `nous-obsidian-sync.sh` use `merge -X theirs` against vps/main. Inline session-start commands (`git stash push -u && git pull --rebase && git stash pop`) are now prevented by AP-23 (`session_safe_sync.sh`). With both layers shipped, AP-20 class should approach zero recurrence.

**Cross-ref:** AP-20 (parent class), AP-21 (commit-time detector), AP-22 (detector scope), AP-23 (session-start prevention), this AP-24 (auto-sync prevention).

**Why no new LESSON file:** RULE ZERO. The two prevention layers (AP-23 session-start, AP-24 auto-sync) close the AP-20 recurrence loop end-to-end.

### AP-25 — Env-alias mismatch makes helper lanes silently register as wildcard `scope=*` (session 95, 2026-04-29)

**Pattern:** A helper/controller prompt sets `CODEX_SESSION_INTENT` / `CODEX_SESSION_SCOPE` before calling `tools/session_self_register.sh` directly. The script only reads `SESSION_INTENT` / `SESSION_SCOPE`, so registration succeeds but records default intent and wildcard `scope=*`. The handshake looks mechanical, but the ownership signal is polluted: every helper appears as able to touch everything.

**Root cause:** Two launcher vocabularies existed. `tools/codex-nous.sh` translates `CODEX_SESSION_*` into CLI `--intent/--scope`, but direct helper flows reused the Codex env names without that wrapper. `session_self_register.sh` accepted missing canonical env silently, which made the narrow-scope failure invisible.

**Fix:**
1. `session_self_register.sh` treats `CODEX_SESSION_INTENT` / `CODEX_SESSION_SCOPE` as compatibility aliases behind canonical `SESSION_INTENT` / `SESSION_SCOPE`.
2. `tools/test_session_self_register.sh` includes a Codex-env regression that forces registration with only `CODEX_SESSION_*` and asserts the Air registry preserves the exact intent and scope.
3. Future launchers must either use canonical `SESSION_*`, pass explicit `--intent/--scope`, or add a tested alias. Silent wildcard fallback is forbidden.

**Detector:** `tools/test_session_self_register.sh` section `4c` — fails if Codex env aliases register as default intent or `scope=*`.

**Cross-ref:** Rule 12 (four-session handshake), Rule 13 (Codex launcher), Rule 14 (env aliases), AP-12 (real four-lane vs research burst), AP-17 (false-green registration visibility), AP-18 (self-register idempotency). No new LESSON.

### AP-26 — High-velocity peer-session collision: multi-tool edit→commit sequences race against linter/peer/auto-stash; atomic single-Bash edit-commit-push is the only safe pattern (session 100, 2026-04-30)

**Pattern:** during a single 1-hour session, four distinct collision events occurred while shipping doctrine to `pages/skills/gbrain-ops/SKILL.md` and `pages/skills/audit/SKILL.md`:
1. **Linter race:** `Edit` tool succeeded; subsequent `Edit` failed with "File has been modified since read" because Obsidian / a Mac auto-formatter rewrote the file between the two `Edit` calls.
2. **Peer-revert race:** peer shipped `f3423f8e`, then reverted with `d709f786`, then my `pull --rebase --autostash` re-introduced `f3423f8e` content via stash-pop, which then committed under my message and silently undid peer's revert intent.
3. **Version-drift race:** I bumped frontmatter v1.48.0 → v1.49.0 with `Edit`; meanwhile peer pushed v1.50.0; my pull merged frontmatter at v1.50.0 but my locally edited H1 stayed at v1.49.0 → pre-commit drift gate blocked the commit.
4. **File-revert race:** between `Edit` succeeding and `git add` running, an unidentified Mac process (Obsidian sync, com.nous.obsidian-sync launchd, or similar) reverted the file to HEAD content. `git add` then staged nothing, `git commit` produced "no changes added", silently no-op.

**Root cause:** Claude Code (and any harness with separate Edit/Bash/git tools) introduces tool-boundary windows where peer commits, linters, IDE auto-saves, and auto-sync daemons can mutate the working tree. The longer the multi-tool sequence, the higher the collision probability. With 1-2 commits/min peer velocity, the probability of a multi-tool sequence completing without interference approaches zero.

**Rule:**
1. **Doctrinal SKILL.md edits with version bump must be ATOMIC in a single `Bash` invocation.** Use `git pull --rebase --autostash` → `python3 -c '...'` (or `<<EOF` heredoc) to apply all three required edits (frontmatter version, H1 version, Timeline/Evidence-trail entry) → `git add -p`/`git add <specific path>` → `git commit -m "..."` → `git push` — all in one Bash call. No tool boundary between the edit and the commit.
2. **Multi-file edits must use `git commit -o <path1> -o <path2>`** (per AP-5 anti-collision) so concurrent autostash pops cannot sweep peer's reverted work into your commit.
3. **Pre-commit drift gate failures during high-velocity collisions must be resolved by re-pulling and re-aligning version numbers**, not by `--no-verify`. Choosing the next-major version (peer's v1.50.0 + 1 = v1.51.0) is the correct response when peer just took your intended number.
4. **`Edit` tool followed by separate `Bash git add`** is the high-risk pattern; `Edit` followed immediately by `Bash git status` to confirm changes survive is the safer audit, but the truly safe path is the single-Bash pattern above.

**Detection:**

```bash
# After any Edit-then-commit sequence, before declaring done:
git log -1 --format='%H %s' HEAD
git diff HEAD~1..HEAD --stat | grep -v '0 files changed'   # must show your file with non-trivial delta
git rev-list --left-right --count HEAD...vps/main          # must be >0 ahead
```

If the commit shows 0 files changed, your edit got silently reverted; redo via the atomic pattern.

**Cross-ref:** AP-5 (cross-session stage-bleed via `git commit -o`), AP-20 (auto-sync conflict marker pollution), AP-23 (PREVENTION layer), `session-operating-contract` Rule 19 (authorial commits), `gbrain-ops` AP-33 (CLI fallback when MCP races). No new LESSON (RULE ZERO).

### AP-27 — Session-start ritual: every writer Claude Code session MUST call `tools/session_self_register.sh` at start, or it's invisible to the registry and other lanes can't handshake (session 100, 2026-04-30)

**Pattern:** session 100 (s100-mac-23069) shipped 6 substrate doctrine commits (`audit` AP-42, `gbrain-ops` AP-61, `session-coordination` AP-26, plus auto-checkpoint observability + skill-parity monitor + handoff). Throughout, peer-session writers `s103-mac-77714` (Mercury grader) and `s103-mac-77748` (scheduled follow-ups) were correctly registered with narrow scopes and shipped in parallel without collision. But session 100 itself was UNREGISTERED — the substrate could not see Lane 1's existence, scope, or intent. Madi's standing directive ("4 simultaneous sessions with handshake; help each other out; do not disturb") was satisfied by *peer* discipline, not by mine. The recovery action — calling `session_self_register.sh` mid-session and shipping AP-27 — only worked because peer lanes happened to choose orthogonal scopes by luck, not by handshake.

**Root cause:** Claude Code sessions on Mac do not have an enforced session-start hook. The doctrine is in `session-coordination` (AP-25 codifies env-alias support), and the tool exists (`tools/session_self_register.sh`), but agents start a session and dive into work without invoking it. Any pre-existing SID file lingers from a stale session, masking the gap. AP-26 closed the *intra-edit* race; AP-27 closes the *session-existence* race that comes one level up.

**Rule:**
1. **Every writer Claude Code session MUST call `tools/session_self_register.sh --intent <text> --scope <paths>` within the first 3 tool invocations of session start.** Read-only research-burst sessions are exempt (per AP-12: subagents do not hold claims).
2. The intent string MUST identify the lane purpose ("Lane-1: <task>", "Lane-2: <task>", etc.) so other writers can avoid scope overlap.
3. The scope string MUST be the narrowest accurate file/dir list — never `*` or empty (AP-25's silent-wildcard trap). If scope is broad early in a session, narrow it via `--update-scope` once the working set is clear.
4. **Handshake check:** before any non-trivial edit, run `bash tools/session_scan.sh` and confirm no overlap with other active sessions. If overlap, defer the edit, message the peer (Telegram or wiki HANDOFF stub), or pick an orthogonal sub-scope.

**Detection:**

```bash
# At session start (first 3 turns):
ssh air "bash ~/nous-agaas/wiki/tools/session_self_register.sh --intent 'Lane-N: <purpose>' --scope '<paths>'"

# Before any peer-collision-prone edit:
ssh air "cd ~/nous-agaas/wiki && bash tools/session_scan.sh"
```

Live verification at codification: registered as `s104-air-57214-20260430T1152` (host=air) before pushing AP-27. `session_scan.sh` confirms 1 active session with non-wildcard scope.

**Cross-ref:** AP-25 (env-alias silent-wildcard prevention; AP-27 makes the registration *required*, AP-25 makes it *correct-when-done*), AP-12 (real four-lane decomposition; AP-27 is the entry-ticket to Lane 1/2 status), AP-26 (atomic edit pattern; AP-27 is the equivalent at session-start scope), `session-operating-contract` Rule 19 (authorial-commit; AP-27 is its session-start sibling). No new LESSON (RULE ZERO).

## Rules absorbed

- **`infrastructure` AP-30** (session 39, 2026-04-17): "Parallel-agent concurrent write race on same SKILL.md" — this skill closes that gap by making the race visible at session-start.
- **`infrastructure` AP-34** (session 45, 2026-04-17): "Parallel Claude Code session detected via <2min commit cadence; defer destructive ops on shared resources" — this skill replaces "detect via cadence after-the-fact" with "declare at start; intersect at SOAO."
- **`session-operating-contract` Rule 17** (session 56, 2026-04-21): "Execute previously-approved workstreams; no re-ask at phase boundaries" — sibling discipline. Coordination ≠ permission-asking; coordination = informed parallel execution.
- **`karpathy-loop` AP-3** (session 56, 2026-04-21): multi-virtual-reviewer (CEO/DevEx/Designer/Engineer) — applied to this skill's spec design.
- **`gbrain-ops` AP-33** (session 55, 2026-04-21): CLI fallback pattern when MCP disconnects — same substrate-over-API-as-truth model.
- **`audit` AP-20** (session 51, 2026-04-20): probe E2E-verify discipline — `tools/test_session_coordination_e2e.sh` ships with 7 pass-asserts dogfooding the registry before declaring SHIPPED.

## Evidence trail

- **2026-05-21** | v1.34.0 -> v1.35.0 — Absorbed **AP-34** after parallel-session closeout found stale Codex Desktop rows sharing a live app-server PID, so heartbeats kept superseded logical tasks active. Codified targeted close + active-id removal + `session_scan.sh --json == []` as the closeout proof, and pruned dead locked Claude worktrees after proving their branch tips were patch-equivalent in `main`. No new LESSON. gbrain-timeline-ok: pages/skills/session-coordination/skill. OpenBrain: [[openbrain-0bc648aa-b5c9-456c-9922-2e01663ac790]].

- **2026-05-21** | v1.33.0 -> v1.34.0 — Absorbed **AP-33** after active-session scans showed fresh Mac lanes whose PIDs were already dead, including Codex Desktop self-registration rows created from one-shot shell commands. Patched `session_scan.sh` to filter dead local-host PIDs immediately, patched `session_self_register.sh` to use the durable `codex app-server` parent PID in Desktop context, and added `tools/test_session_scan_dead_pid.sh` to prove alive local + non-local rows stay visible while dead local rows disappear. No new LESSON. gbrain-timeline-ok: pages/skills/session-coordination/skill.

- **2026-05-17 17:00 KZT** | **Two duplicate-prevention wins** from AP-32 + RULE ZERO firing in same Mac Claude Code session (s1638-mac-claude-opus-4-7). Evidence-only Timeline entry; no doctrine change, no version bump. (1) **AP-32 5-step handshake caught peer session s1428-mac-73048 commit `b307da62`** ("command-center: recover openclaw empty stdout") before this session redid the same surgical 43-line edit to `tools/run_task.py`. Peer shipped AP-35 telegram-silent-failure fix ~9 minutes before this session started. Without pre-action handshake, would have wasted ~30min on duplicate code + stage-bleed risk. Counter-checked: peer's 7 unit tests pass on my Mac, peer's pytest suite 40/40 also passes. (2) **Reading actual `pages/skills/ceo-hierarchy/SKILL.md` head revealed v1.8.6** (not v1.7.0 as `[[HANDOFF-SESSION-CLOSE-2026-05-17-TO-TERMINAL]]` claimed). Handoff doc was 2 days stale. ceo-hierarchy v1.8.6 already ships AP-21 (Hermes Agent as `nouscanary` canary on Air with 24h cutover gate via `tools/hermes_canary_gate.py`), AP-23 (LangGraph route spine via `tools/factory_orchestration_policy.py` 236 LOC + `tools/langgraph_factory_orchestrator.py`), and AP-24 (token-aware route markers). Spec at `[[2026-05-17-hermes-factory-design]]` (commit `53e87e9e`) overlapped ~80% with what already shipped — caught BEFORE proposed v1.7.0→v1.8.0 bump would have **regressed** v1.8.6 (lower version number) and BEFORE writing duplicate doctrine into a new hermes-factory skill. Spec amended (commit `73d25708`) to 20% genuinely-new scope: `cheap_pool_winner_picker.py` (weekly auto-rotation with /approve gate), `cheap_pool_benchmark.py` (monthly validation), `hermes_promotion_runner.py` (walks the 10 canary→production proofs in spec Section 9). HANDSHAKE doc at `[[HANDSHAKE-2026-05-17-claude-codex-hermes-promotion-rotation]]`. **System worked as designed.** session-coordination v1.33.0 AP-32 + RULE ZERO + Karpathy "think before coding" + "no duplicate work" memory rule + Musk step-2 elimination all fired together. Pattern captured in narrative; if recurs N≥2 in future sessions, codify as new AP per Musk step-5 (automate last, validate first). gbrain-timeline-ok: pages/skills/session-coordination/skill. OpenBrain capture ID `761a2d7e-52ee-4fe1-97c4-ee9d0f7fb8c0`. No new LESSON (RULE ZERO).

- **2026-05-17** | v1.32.0 -> v1.33.0 — Session s0908 absorbed **AP-32** after parallel BDL/Cerebro ping work created duplicate/adjacent substrate artifacts because the pre-action handshake was skipped for new `tools/`, launchd, and audit files. Generalized AP-4 from doctrine SKILL.md body rewrites to every durable substrate write: registry overlap scan, recent-git-touch, live process scan, topic-class glob, and audit-recency check before writing. This audit later found the update present as an uncommitted local skill mutation and completed the missing Timeline entry before sync. No new LESSON.
- **2026-05-14 openbrain** | OpenBrain Capture - 2026-05-14 Round-2 ship 2026-05-14 s108-mac-74559 — OpenBra… [[openbrain-66a969be-9528-4752-b567-7bd03a76fa1b]]
- **2026-05-14 openbrain** | OpenBrain Capture - 2026-05-14 Nous AGaaS audit handshake — session s108-mac-74… [[openbrain-8059b962-6a58-4492-9fde-8c3f2c2d336c]]
- **2026-05-12** | v1.31.0 -> v1.32.0 — Air runtime E2E for the AP-30 heartbeat fix hung inside `session_register.sh`; `bash -x` proved `START_HEAD` still read a Mac-only vault path. Patched `session_register.sh` to derive `VAULT_DIR` from script location for both handoff discovery and `START_HEAD`, so Air uses `/Users/madia/nous-agaas/wiki` and Mac uses the local vault. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-05-12** | v1.30.0 -> v1.31.0 — Same-day control-plane audit absorbed **AP-30** after 19 dead-PID Mac `active/*.id` files were still receiving fresh heartbeats and showing as active sessions. Closed the 19 stale leases, patched `tools/session_heartbeat.sh` to skip dead-PID per-session active IDs, and added E2E section 4b to prove a backdated dead-PID SID is not refreshed into the active set. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-05-11** | v1.29.0 -> v1.30.0 — OpenBrain bridge follow-up absorbed **AP-29** after `session_scan.sh` reported 94 active sessions even after the OpenBrain lane closed. Root cause was 109 stale Mac `~/.claude/sessions/active/*.id` files; `session_heartbeat.sh` refreshed every ID file every 180s, so Air cleanup never saw them age out. Repaired by archiving 108 stale ID files, targeted-closing stale registry rows, running Air cleanup, and verifying `session_scan.sh --json | jq length` dropped from 94 to 1 with only current `s1638-mac-62141-20260511T1638` active. No new LESSON.

- **2026-05-11** | v1.28.0 -> v1.29.0 — Residual repair absorbed **AP-28** after the OpenBrain projection audit left old Opus/Codex terminal processes alive and stale registry rows still owning the original audit file. Codified two-layer closeout: clear matching terminal PIDs and close stale registry rows before declaring a lane abandoned. Verification: killed PIDs 31219/37127/37181, targeted-closed stale OpenBrain SIDs, and `session_scan.sh --overlap-with pages/audits/AUDIT-openbrain-projection-2026-05-11.md` returned no owners. No new LESSON.
- **2026-04-30** | v1.27.0 → v1.28.0 — Session 100/104 (s100-mac-23069 → s104-air-57214) absorbed **AP-27** after shipping 6 doctrine commits without ever calling `session_self_register.sh`. Peer s103 lanes correctly handshook around me by orthogonal scope luck. Codified mandatory session-start registration ritual + handshake check before peer-collision-prone edits. Live verification: registered as s104-air-57214 immediately before this commit. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.
- **2026-04-30** | v1.26.0 → v1.27.0 — Session 100 (s100-mac-23069) absorbed **AP-26** after observing 4 distinct collision events during high-velocity (1-2 commits/min) peer parallelism: linter race, peer-revert race, version-drift race, file-revert race. Codified the atomic single-Bash edit-commit-push pattern as the only safe ship pattern under high peer velocity. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.
- **2026-04-29** | v1.25.0 → v1.26.0 — Session 95 four-lane Obsidian/gbrain/OpenClaw audit absorbed **AP-25** after helper lanes registered with `CODEX_SESSION_INTENT/SCOPE` but `session_self_register.sh` only read `SESSION_INTENT/SCOPE`, producing silent wildcard `scope=*` records. Patched alias support and added `test_session_self_register.sh` section 4c to prove Codex env aliases preserve exact intent/scope. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.24.0 → v1.25.0 — Session 82s/92 absorbed **AP-24** after tracing the remaining AP-20 recurrence source to auto-sync's `git merge -X theirs` fallback: the strategy can still leave inline conflict markers on edit-edit collisions, then push polluted worktree state to VPS bare. Patched `tools/nous-obsidian-sync.sh` with a post-merge `tools/test_no_merge_markers.sh` guard before push and corrected the AP reference in the script comment. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.22.0 → v1.23.0 — Session 91 absorbed **AP-22** after reviewer lane Planck found the first staged marker gate grepped worktree files instead of index blobs. Hardened `tools/test_no_merge_markers.sh --staged` to scan `git show ":$path"` and added `tools/test_no_merge_markers_e2e.sh` for the staged-bad/worktree-clean regression. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.21.0 → v1.22.0 — Session 91 converted AP-20's marker detector candidate into a real gate after `tools/session_scan.sh` failed on literal `<<<<<<< Updated upstream` conflict markers in a fresh top-CTO continuation. Resolved the current stash-pop conflict by AP-20 (keep upstream side), added `tools/test_no_merge_markers.sh`, and wired it into `tools/pre-commit-hook-tan-pattern.sh` + live `.git/hooks/pre-commit` as RULE 0. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.20.0 → v1.21.0 — Session 85 codified **AP-20** after observing 4× recurrence of working-tree merge-conflict markers on this exact file from auto-sync `git stash → git pull --rebase → git stash pop` cycles. Air clean throughout; Mac kept regaining markers. Resolution is mechanical (keep upstream side); prevention requires `tools/wiki-sync.sh` rework (deferred). Detector candidate `tools/test_no_merge_markers.sh` queued. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.19.0 → v1.20.0 — Session 88 verifier found **AP-19**: glob-owned session scopes produced false-clear pre-edit checks for exact files. Patched `session_scan.sh` to expand `*`/`?` globs in the overlap predicate and added E2E regressions for tool and skill glob scopes. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.18.0 → v1.18.1 — Air runtime counter-check found AP-17's queued-register regression was Mac-remote-only: on Air, `session_register.sh` treated local append failures as success, so `session_self_register.sh` printed `✅ registered` instead of queued/not-centrally-visible. Patched the Air-local append branch to set `APPEND_OK=0` on failed mkdir/write and made the queued regression use an unwritable registry path that exercises both Mac fake-SSH and Air-local failure. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.18.1 → v1.19.0 — Live Codex review on GitHub mirror commit `fb28fae` absorbed **AP-18**: raw registry grep let closed/stale session IDs suppress re-registration. Patched `session_self_register.sh` to query `session_scan.sh --json` active set and added a closed-SID regression. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.16.0 → v1.17.0 — Same-session Air runtime verification found `tools/test_top_cto_loop_wired.sh` green from the wiki but false-red from Air runtime skill layout, and `tools/test_pending_queue_drain.sh` false-green from Mac/Air-wiki but failed in Air runtime because `session_heartbeat.sh` exited before draining pending queues on Air-local. Absorbed **AP-16**: Mac/wiki green is insufficient for factory-safe session coordination. Shipped runtime skill-root detection and shared Air-local/remote queue draining. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.17.0 → v1.18.0 — Session 86 four-lane top-CTO audit absorbed **AP-17** after helper B found two false-green handshake paths: Air SSH failure printed `✅ no other active sessions`, and locally queued self-registers printed `✅ registered`. Patched scan/register output to distinguish central visibility from queued degraded mode, added fake-SSH regressions to `test_session_coordination_e2e.sh` and `test_session_self_register.sh`. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON.

- **2026-04-29** | v1.15.0 → v1.16.0 — Session 83 local-Codex lifecycle audit found the four-session handshake still skipped local interactive Codex: Claude hooks and Telegram command-center paths were covered, but `~/.codex/AGENTS.md` was 0 bytes and Codex had no SessionStart hook. Absorbed **AP-15**: instruction memory is not operational visibility. Shipped `tools/codex-nous.sh` launcher plus `tools/test_codex_nous_launcher.sh` red/green proof (`8 pass, 0 fail`) so local Codex self-registers before exec. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.14.1 → v1.15.0 — Session 82f Lane K audit found AP-13 codified an Air-unreachable recovery pipeline that was never coded: `tools/session_heartbeat.sh` only enqueued on failure, never drained the queues on Air recovery. Absorbed **AP-14**: doctrine asserts a recovery path that was never implemented. Shipped drain block for both `pending-registers.jsonl` AND `pending-heartbeats.jsonl` on every successful Air round-trip, plus `SESSION_PENDING_DIR` override and `tools/test_pending_queue_drain.sh` so the recovery path is regression-tested without touching live queues. Proof: `pending-queue-drain: 6 pass, 0 fail`; dogfood also wrote `s99-test-drain-2` to queue, ran heartbeat, observed queue 1 → 0 lines + Air registry contains drained entry. Currently harmless (Air reachable) but real leak on outage. Cross-ref karpathy-loop AP-8 (Musk-step-2 the premise: does the recovery code exist? Apply BEFORE codifying). gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.14.0 → v1.14.1 — Session 83 retry found the first `tools/session_self_register.sh` implementation was Mac-path-bound (`/Users/madia/Documents/Projects/...`) and ignored `SESSION_ID_FILE` / `SESSION_REGISTRY_PATH`, which would make the helper unreliable from Air and untestable without touching live state. Hardened it to derive `VAULT` from `BASH_SOURCE`, respect registry/id-file overrides, and use Air-local reads when already on Air. Added `tools/test_session_self_register.sh`; proof: `session-self-register: 13 pass, 0 fail` plus `session-coordination-e2e: 17 pass, 0 fail`. No new LESSON.

- **2026-04-29** | v1.24.0 → v1.25.0 — Session 82s round-17 absorbed **AP-24**: auto-sync-side prevention complement. `tools/nous-obsidian-sync.sh:230` `git merge -X theirs vps/main` can leave inline markers on edit-edit collisions; merge "succeeds" exit 0 but worktree polluted; push propagates markers to VPS bare → next Mac pull brings them back = AP-20 recurrence loop. Shipped post-merge marker guard (step 3.5): runs `tools/test_no_merge_markers.sh` after merge fallback, refuses push + returns 1 if markers found. Combined with AP-23 (`session_safe_sync.sh` for session-start), the two prevention layers close the AP-20 recurrence loop end-to-end. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.23.0 → v1.24.0 — Session 82r round-16 absorbed **AP-23**: PREVENTION layer for AP-20 conflict-marker class. After 4× recurrence in s85 (AP-20), pre-commit gate (AP-21), gate scope fix (AP-22), AND 2 more recurrences in rounds 14+15 — the detection layer is bulletproof but recurrences keep happening because every session-start does the same `git stash push -u && git pull --rebase && git stash pop` dance even when working tree is clean. Shipped `tools/session_safe_sync.sh`: clean tree → bare `git pull --rebase` (no stash possible); dirty + no overlap → traditional dance; dirty + overlap → exit 1 with 3 manual paths instead of inline marker pollution. Dogfooded both clean and dirty branches in s82r. Detector candidate: `tools/test_no_raw_stash_pop_in_session_start.sh` for future audits. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.13.0 → v1.14.0 — Session 82e Lane G audit found `~/nous-agaas/state/active-sessions.jsonl` empty (0 bytes) while a 3-hour Mac CC driver session held Stream-A. Absorbed **AP-13**: SessionStart hook fires once per CC restart, not per /clear or continuation. Empty registry ≠ "no peers." Shipped `tools/session_self_register.sh` (idempotent re-registration helper, falls back to `pending-registers.jsonl` queue when Air unreachable). Manual dogfood: registry went 0 → 3 lines after one invocation + heartbeat fire. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.13.0 → v1.13.1 — Session 83 retest after Madi said "try again" found AP-12 was doctrine-correct but the E2E suite did not mechanically prove a controller + three helpers are all visible, scoped, and closable. Added `test_session_coordination_e2e.sh` 6b assertions for four-session visibility, intended-overlap, unrelated-clear, and all-lanes-closed. No new LESSON (RULE ZERO).

- **2026-04-29** | v1.12.0 → v1.13.0 — Session 82c (Mac CC continuation) absorbed **AP-12** after Madi's directive "4 simultaneous sessions with handshake" exposed a categorical confusion: prior sessions (81, 82) used 3 read-only `Agent` subagent lanes alongside 1 driver and called it 4-lane parallelism. AP-12 disambiguates: subagent lanes are *research bursts*, not *write capacity*. Real 4-lane = driver + 2 writers (each holding its own claim, e.g., `stream_a` + `stream_b` via separate harness instances — Mac CC + phone `/code` OR Codex CLI) + 1 factory worker (OpenClaw on `/ask` queue) + ephemeral research subagents dispatched by any writer as needed. Substrate (skills + facts.jsonl + handoffs) IS the handshake. No new LESSON (RULE ZERO).

- **2026-04-29** | v1.11.0 → v1.12.0 — Session 82 four-lane top-CTO continuation. Lane-4 audit found the registry had operational four-lane behavior but did not name "four-session handshake" as a first-class doctrine phrase. Added Current Rule 12: controller + three helpers, register scopes first, scan after registration, helper lanes read-only/disjoint, controller integrates with `git commit -o`, all helpers close, final scan clears. `musk-step-2:` deleted any new lock/mutex design; the existing registry is enough when ownership is explicit. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.10.0 → v1.11.0 — Session 81 integration pass found a second-order registry debt: heartbeat-only `s99-*` rows survived cleanup because cleanup did not require a matching register record while scan did. Absorbed **AP-11**. `cron_session_cleanup.sh` now archives malformed rows and no-register groups; E2E injects both a corrupt row and orphan heartbeat and passes `13 pass, 0 fail`. Production registry was cleaned back to strict JSONL with only the live coordinator session. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.9.0 → v1.10.0 — Session 81 Air-runtime verification found `session_scan.sh` on Air returned `[]` because it SSHed to `air` from Air and swallowed the lookup failure. Absorbed **AP-10**: registry tools now use local file I/O when hostname contains Air, and `ssh air` only from non-Air hosts. `test_session_coordination_e2e.sh` now uses the same transport helper, so it runs from Mac and Air. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.8.0 → v1.9.0 — Session 81 follow-up to Lane 2 finding P2. Absorbed **AP-9**: exact-string overlap checks missed equivalent scopes across `Nous/...` vs vault-relative `pages/...` paths and parent-directory ownership. Fixed `session_scan.sh` to normalize paths, honor `*`, and use parent/child prefix overlap. Added E2E assertion for `Nous/pages/skills` matching `pages/skills/session-coordination/SKILL.md`. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.7.0 → v1.8.0 — Session 81 follow-up to four-lane top-CTO handshake audit. Absorbed **AP-8** after Lane 2/Lane 4 proved the E2E test itself truncated production `active-sessions.jsonl`, erasing the four registered lanes. Fixed the class by adding `SESSION_REGISTRY_PATH` overrides to register/scan/heartbeat/close/cleanup, moving `test_session_coordination_e2e.sh` onto an isolated test registry, and making heartbeat multi-session aware via per-session active ID files (`SESSION_ID_DIR`) instead of a single global pointer. Verification: isolated E2E `8 pass, 0 fail`; production registry line count stayed `3 -> 3`; live scan still showed coordinator session. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.6.0 → v1.7.0 — Session 81 (Mac-interactive, four-lane top-CTO/agent-workflow audit). Absorbed **AP-7** after SOAO Section 8 printed malformed `PARALLEL:  active session(s)`. Root cause: one corrupt JSONL close row in Air's append-only `active-sessions.jsonl` made `jq -s` fail the whole scanner; stderr was swallowed, so the live coordination path went blind. Fixed `tools/session_scan.sh` to parse row-by-row with `fromjson?`, preserve valid records, and ignore corrupt rows. Red test: `session_scan.sh --json` returned `bytes=0`; green test: JSON array returned + human scan showed active sessions; sibling `tools/test_session_coordination_e2e.sh` stayed `8 pass, 0 fail`. This unblocked the requested four simultaneous registered lanes without adding a mutex. gbrain timeline pushed `{status: ok}`. No new LESSON (RULE ZERO).

- **2026-04-25** | v1.5.0 → v1.6.0 — Session 74 (Mac-interactive, `s74-mac-12354`, post-/clear from s73). Absorbed **AP-6** (substrate path map: each path resolves on a SPECIFIC host; mixing is the bug). Trigger: factory checkpoint 2026-04-25-17-33 KZT explicitly carried forward "codify Mac-host paths unreachable from OpenClaw sandbox" — 2 dogfood examples 17:26/17:27 where the agent honestly refused to fabricate from `/Users/madia/...` injected into a containerized task. AP-6 codifies the substrate-path map (Mac CC / Air shell / OpenClaw container / VPS shell / gbrain+QMD MCP) + binding rule that task-generation MUST use paths reachable from the executing substrate (preferring `WIKI: pages/...` relative form for cross-substrate safety). Musk step-2 applied to the original carryover binary fork (extend `audit` AP-10 OR add to `session-coordination`): chose session-coordination, deleted the audit-extension option — `audit` AP-10 already covers agent-side refuse-to-fabricate; the missing piece was task-side path-routing, which is by name session-coordination's scope. Detector candidate `tools/test_substrate_path_routing.sh` queued (session-75+, posthoc surveillance shape per AP-5's v0.1 pattern; not a gate). Cross-ref: factory-ops AP-30 (orchestrator pre-injects evidence — sibling fix at prompt layer), factory-ops AP-31 (orchestrator owns file I/O — same class at write-side), audit AP-10 (LAW-013 verify — agent's correct behavior in dogfood), LAW-013 (no fabrication). gbrain timeline pushed `{status: ok}`. No new LESSON (RULE ZERO).

- **2026-04-24** | v1.4.0 → v1.5.0 — Session 72 (Mac-interactive, post-/clear) shipped `tools/test_pre_commit_index_scope.sh` v0.1 — POSTHOC surveillance scanner for AP-5 cross-session stage-bleed. Applied Musk step-1 + step-2 on the task: the v1.0 registry-coupled design (match commit author-time to Air session register/close intervals; compare diff to declared_scope globs) was DEFERRED until N≥2 incidents justify the complexity. v0.1 is registry-FREE, ~120 lines of bash, purely heuristic: extract subject path hints via regex; if subject hints at 1-3 paths AND diff has files NOT matching hints → flag CANDIDATE. Excludes auto-sync / Merge / session-close commits (covered by AP-54 `test_authorial_commits.sh`). Dogfooded on 20 most recent commits: surfaced 1 candidate = this session's own task-5 commit "migrate AMD-005 + AMD-006 to canonical laws/AMENDMENT-NNN path" — false positive class (placeholder NNN in subject didn't match real diff paths `AMENDMENT-005-*`). Tool is SURVEILLANCE, not gate; warn-only; operator reviews flags manually. Enters same class as AP-54 (test_authorial_commits.sh, infrastructure) — both are posthoc surveillance, neither gates git history (immutable). Detector bumped from "candidate (session-69+)" to "SHIPPED v0.1" in AP-5 body. Wrapper `tools/session_safe_commit.sh` remains DEFERRED per musk-algorithm step 5. gbrain-timeline-ok: pages/skills/session-coordination/skill. No new LESSON (RULE ZERO). Cross-ref AP-5 (this SKILL), AP-54 (infrastructure sibling surveillance), musk-algorithm step-1+2 applied recursively to own plan.

- **2026-04-23** | v1.3.0 → v1.4.0 — Session 68 (Mac-interactive, continuation after Madi directive *"failure→skill, don't stop for human factors"* correcting agent's initial "defer AP-5 codification to session-69+" stance — musk-algorithm AP-4 violation). Absorbed **AP-5** (cross-session stage-bleed: shared `.git/index` enables commit-level stage-bleed that declared-scope check cannot see). Trigger: session 68 handoff file staged by me at 13:15 was swept into peer s67's commit `9d8b45c5` at 13:16; s67's declared-scope check (against their own scope) said "No collision" but missed the git-index channel; my HEREDOC authorial commit became a no-op. Root cause: 3-signal pre-edit gate (AP-4: registry + ps aux + recent-git-touch) covers file-content collisions but not git-index collisions. Rule: use `git commit -o <path>` (--only flag) on shared working trees — bypasses index entirely; cross-session stage-bleed eliminated by construction. Sibling class to AP-1 at git-layer; derives from same shared-substrate root. Dogfooded twice in same session (addendum commit `a3443579` + this codification commit both via `git commit -o`). Detector candidate `tools/test_pre_commit_index_scope.sh` queued session-69+. Wrapper `tools/session_safe_commit.sh` DEFERRED per musk-algorithm Step 5 (automate last, validate first). No new LESSON (RULE ZERO). Cross-ref: SOC v1.12 Rule 19 (authorial commits — AP-5 is its mechanical enforcement at git layer); musk-algorithm AP-1 (optimize-before-delete — don't rush the wrapper); audit AP-21 (pagination — s67's "No collision" was partial-truth-from-single-signal).
- **2026-04-22** | v1.2.0 → v1.3.0 — Session 63 (Musk-execute, shipped 1 compounding-gate detector from the 9-queued carryover list). Shipped `tools/test_no_duplicate_skill_headers.sh` — mechanical enforcement of AP-4's post-close grep-for-duplicate-headers gate. POSITIVE-tested against real vault (0 dups across 10 skills); NEGATIVE-tested against `/tmp/fake-skill-dup-test` with byte-identical `### AP-1` dup (exit=1, offending skill + normalized header reported). VAULT env override supports sandbox testing. AP-4 body updated: gate candidate (c) moved from QUEUED → SHIPPED. Other 2 gate candidates (a pre-edit doctrine-gate + b pre-commit RULE 7 duplicate-from-shared-directive warn) still queued session-64+. Cross-ref `infrastructure` v2.45 AP-51 extension (session 63 same-commit). No new LESSON (RULE ZERO).
- **2026-04-22** | v1.1.0 → v1.2.0 — Session 61 (Mac-interactive, immediately after session-60 close). Absorbed **AP-4** (doctrine-skill body-rewrite requires `git log --since` pre-edit gate, not just registry scan). Trigger: session 60 codified SOC Rule 18 while session-57 independently codified byte-identical Rule 18 from same Madi directive → duplicate block lines 245-265 + 267-287 in SOC v1.10 → session-60 MASTER closed silent → session-57 caught + dedupped via commit `7d7b2623`. Root cause: registry-only pre-edit scan missed session-57 because they weren't yet registered when session-60 began editing. Registry opt-in + time-lagged; `git log --since='15.minutes.ago'` is ground truth. AP-4 codifies the 3-signal pre-edit ritual as MANDATORY for any body-rewrite on a doctrine SKILL.md (enumerated list: SOC, karpathy-loop, audit, infrastructure, mistake-to-skill, session-coordination, gbrain-ops, evidence-verification). Post-close grep-for-duplicate-headers added as sibling session-close gate. Compounding gate candidates: `test_pre_edit_doctrine_gate.sh`, `test_no_duplicate_skill_headers.sh`, pre-commit RULE 7 duplicate-from-shared-directive warn. Cross-ref SOC Rule 18 (this class is textbook after 57+60 demonstration); `audit` AP-15 (codification ≠ self-application — session-60 codified AP-2's 3-signal rule but didn't self-apply on SOC edit). No new LESSON (RULE ZERO).
- **2026-04-22** | v1.0.0 → v1.1.0 — Session 60 (deep-audit extension of session 59, Madi-directed "billion-dollar-solopreneur standard: no defer, no bullshit"). Absorbed **AP-2** (registry-awareness: 3-signal discipline — registry + `ps aux` + recent-git-touch — when any registry claim of "no other sessions" needs corroboration). Session 59 evidence: registry said "1 session = me"; `ps aux` showed 4 `claude` processes; session-57-extension touched the same SKILL.md earlier in the day with zero registry record. Absorbed **AP-3** (`session_close.sh` --session-id flag for targeted close): shipped + dogfooded. Prior close-scripts could only close the file-tracked session, making stale-session cleanup require direct SSH JSONL append. Fix: order-independent arg parsing, does NOT touch `current_session_id` when `--session-id` override used. Dogfooded in same session with fake SID + tail-verified JSONL record appended + live session's file preserved. Both APs cross-ref `audit` AP-21 (same session 60 codification) under common meta-class: single-source signals are often incomplete-by-construction. Compounding gate candidates queued: `test_session_close_flags.sh`, extend `session_scan.sh` with `ps aux` + recent-git-touch integration. No new LESSON (RULE ZERO).
- **2026-04-21** | v1.0.0 created. Session 56 (Mac-interactive). Madi greenlit (c) Phase-0 audit + (a) coordination registry. Phase-0 audit shipped E2E earlier in session; this is (a). Designed via `karpathy-loop` AP-3 multi-virtual-reviewer pass (CEO + DevEx + Designer + Engineer). Spec at [[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]]; plan at [[PLAN-SESSION-COORDINATION-REGISTRY-V1-2026-04-21]]. 11 components shipped: registry substrate on Air; 5 vault-tracked scripts (`session_register.sh`, `session_scan.sh`, `session_heartbeat.sh`, `session_close.sh`, `cron_session_cleanup.sh`); 2 launchd plists (Mac heartbeat 180s + Air cleanup 60s, both loaded + verified); SOAO Section 8 modification (`tools/soao.sh`); SessionStart hook auto-register (`~/.claude/hooks/session-start-soao.sh` + vault backup `tools/hooks/`); RESOLVER row; sibling test `tools/test_session_coordination_e2e.sh` — **8 pass, 0 fail** (7 assertions + 1 deferred Air-unreachable manual-test). MVP cut-over criteria from spec all met. v2 deferred: PreToolUse hook for inline pre-edit advisory + pre-commit `Parallel-Session-Overlap:` trailer + dynamic scope expansion CLI. Trigger: today's near-miss between two Mac claude session-56 instances both editing `factory-ops/SKILL.md` (45-min cat-and-mouse with auto-sync produced a duplicate Timeline entry that lived 40min before sed-deduped). Madi: *"Make sure that every session is synchronized to other sessions so nobody will break anything."* Then on hard-block-vs-soft choice: *"That will actually block for it to evolve."* → gbrain pattern (substrate-as-coordination, no mutex). Closes `infrastructure` AP-30 + AP-34. AP-1 codified at v1.0 (body-rewrite on shared scope). No new LESSON (RULE ZERO).

## See also

- [[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]] — design spec
- [[PLAN-SESSION-COORDINATION-REGISTRY-V1-2026-04-21]] — implementation plan (12 tasks, all green)
- [[infrastructure]] AP-30 + AP-34 — recurring problems this skill closes
- [[session-operating-contract]] Rule 17 — sibling at execution-question layer
- [[karpathy-loop]] AP-3 — multi-virtual-reviewer applied to this skill's design
- [[gbrain-ops]] AP-33 — CLI-fallback substrate model
- [[audit]] AP-20 — sibling test E2E-verify discipline
