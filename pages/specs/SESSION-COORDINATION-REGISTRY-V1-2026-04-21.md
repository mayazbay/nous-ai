---
type: spec
id: SESSION-COORDINATION-REGISTRY-V1-2026-04-21
title: "Session-coordination registry v1 — host-central JSONL substrate so parallel agents see each other before they clobber"
tags: [spec, session-coordination, registry, parallel-sessions, infrastructure, gbrain-pattern, karpathy-loop, 2026-04-21, session-56]
date: 2026-04-21
status: draft
last_updated: 2026-04-21
related:
  - "[[infrastructure]]"
  - "[[session-operating-contract]]"
  - "[[karpathy-loop]]"
  - "[[gbrain-ops]]"
  - "[[audit]]"
---

# Session-coordination registry v1 — substrate-as-coordination, no mutex

**Status at write-time:** Madi greenlit ("agree. go") after the (c) Phase-0 audit then (a) coordination registry sequencing. Phase-0 audit shipped E2E earlier this session; this is (a). Per `session-operating-contract` Rule 17 (just-codified by parallel session-56): no re-ask at phase boundaries inside an already-approved workstream — execute.

## Problem

**Two prior APs documented this exact gap; neither closed it.**

- `infrastructure` AP-30 (session 39, 2026-04-17): "Parallel-agent concurrent write race on same SKILL.md"
- `infrastructure` AP-34 (session 45, 2026-04-17): "Parallel Claude Code session detected via <2min commit cadence; defer destructive ops". Root-cause #3: *"No shared-lock. No status file. Only signal is git ls-remote + commit cadence."*

**Live evidence today (session 56, 2026-04-21):** two Mac claude sessions (PIDs 83508 + 85687) both ran session-56 pickup independently, both edited `factory-ops/SKILL.md`, cat-and-mouse with `com.nous.obsidian-sync` 60s loop produced a duplicate Timeline entry that lived ~40 min before being deduped. Near-miss on `session-operating-contract` v1.7→v1.8 (parallel session bumped first; my session was about to bump for unrelated reason). Coordination is hand-rolled via `git status` polling + Telegram, which doesn't scale.

## Goal

Make every active claude/openclaw session **discoverable to every other agent on every host** via append-only host-central substrate, so SOAO at session-start prints overlaps before any work begins. **Zero mutex, zero block.** The gbrain pattern (substrate enriches awareness, doesn't gate writes) — not the Postgres-row-lock pattern (which kills evolution).

## Non-goals (MVP scope discipline)

- **NOT** a hard lock — sessions can still race. Awareness ≥ blocking.
- **NOT** a per-file mutex — too granular; declare scope at the file/skill level only.
- **NOT** a PreToolUse hook wrapping Edit/Write — complex, per-host install, deferred to v2 if v1 isn't enough.
- **NOT** a pre-commit `Parallel-Session-Overlap` trailer — requires touching pre-commit hook in 3 working copies (Mac/Air/VPS), deferred to v2.
- **NOT** dynamic scope expansion — declared once at session-start; reshape via re-register if needed.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Air (host-central registry):                               │
│  ~/nous-agaas/state/active-sessions.jsonl                   │
│  (append-only JSONL, stale-clean cron 60s)                  │
└─────────────────────────────────────────────────────────────┘
        ▲                      ▲                      ▲
        │ ssh                  │ ssh                  │ local
        │                      │                      │
┌───────┴───────┐    ┌─────────┴─────────┐    ┌──────┴──────┐
│ Mac claude    │    │ /code-spawned     │    │ Air         │
│ session-N     │    │ Claude on Air     │    │ openclaw    │
│ PID xxxxx     │    │ PID yyyyy         │    │ factory     │
└───────────────┘    └───────────────────┘    └─────────────┘
```

Each session's lifecycle hits 3 substrate operations:
1. **register** at session-start (append one JSONL line)
2. **heartbeat** every ~3 min via launchd/cron (in-place mtime update OR append `{op:heartbeat,session_id:...,ts:...}`)
3. **close** at session-end (append `{op:close,session_id:...,ts:...}`)

Stale cleanup cron on Air (60s cadence) reads the JSONL, computes per-session "last activity" (max of register/heartbeat ts), deletes records where `now - last_activity > 30min`.

## Record schema

One JSON object per line. Records are immutable; lifecycle progression = additional records, not edits.

```json
{
  "op": "register",
  "session_id": "s56-mac-85687-20260421T1150",
  "host": "mac",
  "pid": 85687,
  "started_at": "2026-04-21T11:50:00+05:00",
  "start_head": "a23a58f1",
  "intent": "AP-18 STOP pickup karpathy-loop steps 1-7 + Phase-0 audit + coordination registry",
  "declared_scope": [
    "pages/skills/karpathy-loop/SKILL.md",
    "pages/skills/_gbrain/RESOLVER.md",
    "CLAUDE.md",
    "pages/entities/nous-gpu.md",
    "tools/session_*.sh"
  ],
  "ttl_minutes": 180
}
```

Subsequent records reference `session_id`:
```json
{"op": "heartbeat", "session_id": "s56-mac-85687-20260421T1150", "ts": "2026-04-21T13:35:00+05:00"}
{"op": "close",     "session_id": "s56-mac-85687-20260421T1150", "ts": "2026-04-21T14:10:00+05:00", "exit_status": "ok"}
```

`session_id` format: `s<session-number>-<host>-<pid>-<YYYYMMDDTHHmm>` — globally unique, human-readable, sortable.

## Components (MVP — 11 artifacts)

### 1. `tools/session_register.sh` (vault-tracked)
Args: `--host <mac|air|vps|nous-gpu>` `--intent "<text>"` `--scope "path1,path2,..."`. Computes session_id, appends register record to Air registry via `ssh air 'cat >> ~/nous-agaas/state/active-sessions.jsonl'`. Echoes session_id to stdout for the caller (SessionStart hook captures + writes to `~/.claude/sessions/current_session_id` for in-session tools).

### 2. `tools/session_heartbeat.sh` (vault-tracked)
Reads `~/.claude/sessions/current_session_id`, appends heartbeat record to Air registry. Idempotent. Called from launchd every 3 min on Mac + Air + VPS.

### 3. `tools/session_close.sh` (vault-tracked)
Reads current_session_id, appends close record. Manual or via SessionEnd hook (if/when Claude Code adds one).

### 4. `tools/session_scan.sh` (vault-tracked)
Reads Air registry, computes per-session last-activity, filters to stale-cutoff 30min, prints active-sessions table. With `--overlap-with <path1,path2,...>`, intersects against this session's declared_scope and prints overlapping records loudly. Used by SOAO Section 8.

### 5. `tools/cron_session_cleanup.sh` (vault-tracked, runs on Air)
Cron 60s on Air. Reads registry, computes per-session last-activity, archives + truncates records where stale (>30min) OR explicitly closed (>1 day ago). Archive to `~/nous-agaas/state/archive/active-sessions-YYYY-MM.jsonl` for forensics.

### 6. SOAO Section 8 (modify `tools/soao.sh`)
After existing 7 sections, add:
```
--- 8. Parallel-session scan ---
  ✅ no other active sessions
  OR
  🟡 PARALLEL: s56-mac-83508 (started 11:36, scope: factory-ops/SKILL.md, SOC, MEMORY)
     → overlap with our scope: factory-ops/SKILL.md
     → recommend: skip factory-ops; coordinate via TG if you must touch it
```

### 7. SessionStart hook integration (`~/.claude/hooks/session-start-soao.sh`)
After existing soao.sh invocation, add a `session_register.sh` call with auto-detected scope (start with `--scope "*"` placeholder; user/agent narrows mid-session via re-register). Capture session_id to `~/.claude/sessions/current_session_id`.

### 8. Air launchd plist `com.nous.session-cleanup` + `com.nous.session-heartbeat`
Two launchd jobs on Air:
- `com.nous.session-cleanup`: 60s cadence, runs `cron_session_cleanup.sh`
- `com.nous.session-heartbeat`: 180s cadence, runs `session_heartbeat.sh` (only fires if `current_session_id` exists)

Mac/VPS get heartbeat-only via local launchd/cron; cleanup is Air-only since registry is on Air.

### 9. New skill `pages/skills/session-coordination/SKILL.md` v1.0.0
Full skill with Purpose / Current rules / Anti-Patterns / Rules absorbed / Evidence trail. Cross-refs `infrastructure` AP-30 + AP-34 (which this skill closes), `session-operating-contract` Rule 17 (sibling discipline at execution-question layer).

### 10. RESOLVER registration (`pages/skills/_gbrain/RESOLVER.md`)
Insert under AGaaS Factory:
```
| Every session start (read parallel-session scan) / about to declare scope / detected overlap with another session / pre-commit on shared file | `skills/session-coordination/SKILL.md` |
```

### 11. Sibling test `tools/test_session_coordination_e2e.sh`
Dogfoods the registry: spawns a fake "second session" record, asserts `session_scan.sh` detects it, asserts `--overlap-with` intersection works, asserts close record removes it from active-set, asserts cron cleanup archives stale records. Pass/fail count + exit code. Wires into SOAO Section 4 alongside existing structural scanners.

## Data flow

```
[Mac claude session opens]
    │
    │ 1. SessionStart hook fires soao.sh
    │ 2. soao.sh's existing 7 sections + NEW Section 8 (session_scan.sh)
    │      → reads Air registry via ssh air 'cat ~/nous-agaas/state/active-sessions.jsonl'
    │      → prints "✅ no other active" OR "🟡 PARALLEL: ..."
    │ 3. SessionStart hook calls session_register.sh
    │      → ssh air 'echo "<json>" >> ~/nous-agaas/state/active-sessions.jsonl'
    │      → echoes session_id, written to ~/.claude/sessions/current_session_id
    ▼
[Agent works for ~3 min]
    │
    │ 4. Mac launchd com.nous.session-heartbeat fires
    │      → reads current_session_id, appends heartbeat record
    ▼
[Agent finishes]
    │
    │ 5. session_close.sh manually OR via tg_send.sh (`/close`) OR
    │      stale cleanup cron on Air sees no heartbeat for 30min, auto-archives
```

## Error handling

- **Air unreachable at session-start:** session_register.sh writes the record to a local fallback `~/.claude/sessions/pending-registers.jsonl`; next successful heartbeat flushes the queue. SOAO Section 8 prints a warning "🟡 Air unreachable — session not registered; running with degraded coordination".
- **Multiple sessions race-write the same JSONL line:** append is line-atomic on POSIX (write < PIPE_BUF) for short JSON; for long records, use `flock` on a sidecar lockfile `~/nous-agaas/state/active-sessions.jsonl.lock` for the duration of the append.
- **Cleanup cron malfunctions** (deletes active records by mistake): heartbeats re-register the session at next firing (heartbeat detects "my session_id is missing from active-set" and writes a fresh register record).
- **Registry file grows unbounded:** monthly archive rotation in `cron_session_cleanup.sh` keeps active file <1 MB.

## Testing

`tools/test_session_coordination_e2e.sh` — pass/fail count, runs:

1. **fresh-state**: empty registry → session_register → assert 1 active record visible
2. **double-session**: register session A, register session B → assert session_scan shows both
3. **overlap detect**: A declared scope ["x.md"], B declares scope ["y.md","x.md"] → assert `session_scan.sh --overlap-with y.md,x.md` outputs A's id with overlap=["x.md"]
4. **heartbeat**: register A, sleep 5s, heartbeat A → assert last-activity timestamp moved
5. **close**: register A, close A → assert active-set is empty
6. **stale-cleanup**: register A with backdated ts (>30min ago), no heartbeat → run `cron_session_cleanup.sh` → assert A archived not active
7. **Air-unreachable degradation**: simulate Air SSH fail → assert session_register writes to pending-registers.jsonl and exits 0 with warning

Wires into `tools/test_skill_version_parity.sh`-style structural scanners. Wires into SOAO Section 4 ("✅/🔴 test_session_coordination_e2e (AP-XX)").

## Cut-over criteria

Session-coordination v1 is SHIPPED when all four are true:
1. Registry exists on Air at `~/nous-agaas/state/active-sessions.jsonl`; readable from Mac + Air + VPS via SSH.
2. SOAO Section 8 prints either ✅ or 🟡 within 2 seconds of session-start (no >2s latency penalty).
3. End-to-end test: open a 2nd terminal/session on Mac → 1st session's next SOAO/refresh shows the parallel session in Section 8.
4. `tools/test_session_coordination_e2e.sh` exits 0 with `7 pass, 0 fail`.

## Compounding (karpathy-loop AP-3 — multi-virtual-reviewer applied)

| Reviewer | Critique | Resolution |
|---|---|---|
| **CEO** | "Does this actually displace conflict?" | Yes — turns invisible races (post-commit detection) into visible declarations (pre-work declarations). AP-34's #3 root cause closed. |
| **DevEx** | "Will agents actually use it without forgetting?" | SessionStart hook auto-registers + heartbeat is launchd-driven — zero agent compliance required. |
| **Designer** | "What does the agent see?" | One readable Section 8 in SOAO. ✅ or 🟡 with concrete next-action. |
| **Engineer** | "Is the failure mode safe?" | Append-only + `flock` + Air-unreachable degradation = no data loss, no false-positives, no false-negatives. |

## Musk 5-step pre-filter applied

1. **Question:** Do we need this at all? YES — AP-30 + AP-34 are recurring failures; today's near-miss with factory-ops+SOC concurrent edits proves it.
2. **Delete:** Can we delete a component? — Pre-commit trailer + PreToolUse advisory deferred to v2 (delete from MVP scope).
3. **Simplify:** JSONL > database > distributed lock manager. One file, append-only, SSH-readable.
4. **Accelerate:** SessionStart hook auto-registers; agent doesn't have to remember.
5. **Automate:** Cleanup cron runs without human; heartbeat launchd-driven without agent.

## Cross-refs

- [[infrastructure]] AP-30 (session 39 — same problem, file-level race)
- [[infrastructure]] AP-34 (session 45 — same problem, cadence-detection only)
- [[session-operating-contract]] Rule 17 + AP-11 (just-codified by parallel session-56 — sibling at execution-question layer)
- [[karpathy-loop]] AP-3 (multi-virtual-reviewer — applied above to this spec)
- [[gbrain-ops]] AP-33 (CLI fallback when MCP disconnects — same substrate-as-truth pattern)
- [[audit]] AP-20 (probe E2E-verify discipline — applied to test_session_coordination_e2e.sh)

## See also

- [[PHASE-0-COLLECTOR-DEPLOYMENT-2026-04-21]] — sibling session-56 spec (Phase-0 collector); both written same day under same Madi directive.
- [[HANDOFF-AUTO-2026-04-21-session-55-AP18-stop-karpathy-loop-half-shipped]] — session-55 STOP that surfaced the parallel-session pain in this session
