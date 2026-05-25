---
tier: 2
type: skill
name: session-architecture
id: SKILL-SESSION-ARCHITECTURE
version: 1.0.1
last_updated: 2026-04-25
status: active
description: "The 1+3+dispatch hybrid pattern for agent-session topology. Replaces the implicit 'spawn N parallel Claude Code sessions' pattern that produced AP-54 attribution drift, MEMORY single-writer bottleneck, Obsidian dup files, and 30% coordination overhead. Doctrine: ONE interactive driver session at a time on shared scope, THREE substrate cron streams for parallel non-shared-scope work, AD-HOC parallel-research subagent dispatch fired from the driver. Karpathy ground-truth + Musk step-2 (delete the 4-session-on-same-repo collision pattern) + Tan-YC reframe (one revenue critical-path driver + cron-scheduled background substrate)."
triggers:
  - user proposes 'N simultaneous sessions' on the same repo
  - vault has 2+ active interactive sessions in registry
  - AP-54 attribution drift recurs (auto-sync stole authorial commit)
  - MEMORY.md prepend race (peer collision on top-block)
  - Obsidian dup files (` 2.md` / ` 3.md`) appear from concurrent writes
tools: [Bash, Read, Edit, Write]
mutating: false
absorbs_laws: []
related: [session-coordination, session-operating-contract, infrastructure, audit, karpathy-loop, musk-algorithm]
tags: [skill, runtime, architecture, parallelism, cron, dispatch, billion-dollar-solopreneur, karpathy-tan-musk]
title: "session-architecture v1.0.1"
---

# session-architecture v1.0.1

## Purpose

Define **what kinds of agent sessions exist, how they coordinate, and which scopes each owns** — replacing the implicit multi-session pattern that produced collision after collision.

## The pattern: 1 driver + 3 substrate cron streams + ad-hoc dispatch

```
                     ┌─────────────────────────┐
                     │   Stream A — DRIVER     │  ← exactly 1 at a time
                     │   Interactive Claude    │  ← Madi at keyboard
                     │   Code on Mac           │  ← Spectra critical-path
                     │                         │
                     │   May dispatch ↓        │
                     └────────┬────────────────┘
                              │
                  ┌───────────┴───────────┐
                  │  Stream D — DISPATCH  │  ← Agent tool subagents
                  │  Parallel research /  │  ← ephemeral, no shared write
                  │  audit / Explore      │  ← scope, return synthesized
                  │  (fired by Stream A)  │  ← findings to Stream A
                  └───────────────────────┘

   ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
   │  Stream B — SUBSTRATE│  │  Stream C — AUDIT    │  │  Stream B (continued)│
   │  CRON                │  │  CRON                │  │                      │
   │  launchd / cron      │  │  OpenClaw factory    │  │  detector-FP-tracker │
   │                      │  │                      │  │  zombie-cleanup      │
   │  wiki-lint           │  │  morning-brief 04:00 │  │  parity-snapshot     │
   │  4-way parity        │  │  nightly-audit       │  │  gbrain-reembed      │
   │  obsidian-sync       │  │  daily-factory-      │  │                      │
   │                      │  │   analysis           │  │                      │
   └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
       (no human, no Opus, runs while Madi sleeps or works on Stream A)
```

## Why this pattern (the case for change)

**The pattern it replaces: 4 simultaneous interactive Claude Code sessions on Mac, each with broad declared scope, all writing to the same vault.** Empirically observed (s73, 2026-04-25):

- ~30% of each session burned on coordination, not work
- AP-54 attribution drift — Nth recurrence (peer auto-sync stole authorial commit message)
- AP-55 hook canon drift — would not have happened if only one session was patching hooks
- Obsidian dup files (`* 2.md`, `* 3.md`) every time 2+ sessions wrote the same path
- `MEMORY.md` top-block-prepend doctrine is a single-writer bottleneck — 3 peers can't all prepend safely
- Gate-5 hook blocks on peer house-keeping (cross-session contamination on `git status`)
- 0 Spectra commits / 4 infra commits (Tan-YC ratio inverted)

**Cost analysis:** 3 Opus 4.7 sessions × 1h ≈ $15-30 burned, all on substrate quality-of-life work, none on customer-revenue work. A billion-dollar one-employee company would not run this pattern.

## Stream definitions

### Stream A — DRIVER (exactly one at a time)

**What:** The single interactive Claude Code session on Mac with Madi at the keyboard. Owns the critical path — the Spectra ITS / customer-revenue / "ONE thing" work.

**Scope:** Whatever Madi is driving toward today. Typical: code in `pages/tenants/satory/`, `tools/`, app code, customer-facing fixes.

**Lock mechanism:** `tools/stream_a_claim.sh` writes `~/nous-agaas/state/stream_a.lock` containing the active session-id + PID + started-at + intent. SessionStart hook checks this lock:
- If no lock → claim it (this session becomes Stream A driver)
- If lock exists and is stale (PID dead OR >2h since heartbeat) → revoke and claim
- If lock exists and active → register as **Stream D dispatch fallback** (not as driver)

**Implication:** Opening a 2nd Mac CC terminal while Stream A is active means the 2nd terminal is NOT a peer driver — it's available to be used as a research-dispatch endpoint or a non-shared-scope tactical session (e.g., editing `~/.claude/` config, no vault writes).

### Stream B — SUBSTRATE CRON (no human, no Opus, no interactive)

**What:** Scheduled background jobs running on Mac launchd or VPS/Air cron. **Cheap models or no model at all** — most are pure shell scripts.

**Owns:** lint, parity, obsidian-sync, gbrain-reembed, zombie-session-cleanup, detector-FP-tracker, log-rotate.

**Schedule:** hourly to daily, never sub-minute (would burn cycles). Most run at "human-asleep" hours (02:00-05:00 KZT).

**Existing precedents (already running):**
- `com.nous.obsidian-sync.plist`
- `com.nous.session-heartbeat.plist`
- VPS gbrain autopilot every 5 min
- VPS `vps_skill_extractor.py` every 10 min

**New for this skill (proof candidate):** `tools/detector_fp_tracker.sh` — samples each `tools/test_*.sh` detector for FP rate, writes `pages/dashboards/detector-fp-rates.md`. Hourly. ~50 lines bash.

### Stream C — AUDIT CRON (factory agent, GLM-cheap, scheduled)

**What:** OpenClaw factory agent on Air running scheduled audits via GLM-5.1. Already exists; this skill formalizes its role.

**Owns:** morning-brief, nightly-audit, daily-factory-analysis, /ask handler.

**Schedule:** 04:00 + 22:00 + on /ask trigger. ≤ \$0.50/day total.

**Stays in this stream — do not promote to Stream A.** Factory is NOT for Spectra critical-path work; it's the periodic substrate audit that surfaces issues for the next Stream A session to address.

### Stream D — DISPATCH (subagents, fired from Stream A)

**What:** `Agent` tool subagents spawned BY Stream A for parallelizable work that does NOT need shared-vault-write access. Ephemeral; return synthesized findings; never persist directly to vault.

**Use when:**
- Need to scan many files for a pattern (`Agent(subagent_type=Explore)`)
- Need an independent code review (`Agent(subagent_type=code-reviewer)`)
- Need parallel research on multiple skills/specs
- Need adversarial review (multi-virtual-reviewer per karpathy-loop AP-5)

**Don't use for:** anything that writes to vault. Only Stream A writes to vault.

**Cost:** subagents share token budget with Stream A; ~10-30% premium over inline work. Pay this when work is genuinely parallel.

## Anti-Patterns

### AP-1 — opening N interactive Mac CC sessions and calling them "parallel"

**Symptom:** 2+ sessions registered with `host:mac` and overlapping declared_scope. Substrate-awareness then forces narrow-scope-pivots, AP-54 attribution drift, dup files.

**Why bad:** vault is a single shared write surface. Multiple writers = collisions. The "parallelism" is illusory — net throughput is lower than 1 session because of coordination cost.

**Fix:** Stream A claim lock. 2nd session detects lock, opts into Stream D dispatch role OR refuses to register interactive.

**Evidence:** s73 2026-04-25 — 3 simultaneous Mac sessions, ~30% coordination overhead, AP-54 Nth recurrence, 0 Spectra commits.

### AP-2 — promoting Stream B/C cron to interactive

**Symptom:** Madi runs `tools/wiki_lint.py` interactively in Stream A instead of letting the hourly cron handle it.

**Why bad:** burns Opus tokens on work that GLM or pure-shell can do for free. Tan-YC: this is a tech-debt-as-feature pattern.

**Fix:** if you find yourself running a `tools/test_*.sh` or `tools/wiki_lint.py` interactively as more than spot-check, file a Stream B cron candidate task.

### AP-3 — Stream A writing to non-Spectra scopes when Madi is at keyboard

**Symptom:** Stream A session spends 1h shipping infra commits (hook keyword extensions, lint dashboards) with 0 customer-revenue commits.

**Why bad:** Madi-keyboard-time is the most expensive time in the system. Opus 4.7 in interactive mode is the most expensive agent. This combination should be reserved for highest-leverage critical-path work.

**Fix:** Stream A session-close protocol must show Spectra-ratio (Spectra commits / infra commits this session). If 0:N, the session was misallocated — file infra work as Stream B cron candidates instead.

**Evidence:** s73 2026-04-25 — exactly this happened. 4 infra commits, 0 Spectra commits.

### AP-4 — Stream D subagent persists to vault directly

**Symptom:** an `Agent(...)` subagent writes a file to `pages/...` from inside its own context.

**Why bad:** loses Stream A as the single-writer; reintroduces collision; the subagent's commits are detached from main session intent.

**Fix:** subagents return findings as text; Stream A applies the writes. If a subagent must write, it claims Stream A briefly (lock pattern) and releases on completion.

## How to use this skill (operator)

**On session start (any host, any agent):**

1. Read this skill before deciding "spawn N sessions" — pattern is **1+3+dispatch**, not 4-on-same-repo.
2. If you're starting an interactive Mac CC session: run `tools/stream_a_claim.sh acquire` — succeeds → you're Stream A; fails → you're Stream D fallback or non-vault scope.
3. If you're starting a research/audit task that doesn't need vault writes: dispatch as `Agent(subagent_type=Explore|code-reviewer|general-purpose)` from your active Stream A. Don't open a new terminal.
4. If you're scheduling a recurring substrate task: `Skill(schedule)` to add a launchd job (Stream B) or extend the OpenClaw factory cron (Stream C). NEVER make the user run it interactively.

**On session close:**

1. Stream-A close: report **Spectra-ratio** (commits to `pages/tenants/satory/`, customer-facing app code, ERAP/VMS spec work / total commits this session). Anything <50% is a misallocation flag.
2. Release the Stream A claim: `tools/stream_a_claim.sh release`.

## Migration plan (incremental, not big-bang)

Stage 1 (this session — 2026-04-25): doctrine page (this file) + claim mechanism (`tools/stream_a_claim.sh`) + first Stream-B cron proof (`tools/detector_fp_tracker.sh`).

Stage 2 (s74-s76): SessionStart hook checks the claim lock and warns/refuses on conflict. MEMORY.md migrates from prepend to per-session append (eliminates single-writer bottleneck — see AP-1 fix).

Stage 3 (s77+): Spectra-ratio metric automated in session_close.sh; surfaces in `pages/dashboards/spectra-ratio.md` as a daily KPI.

## Evidence trail

- **2026-04-25 / s73-mac-44149:** session-architecture v1.0.0 created. Replaces implicit multi-session pattern observed in s73 (3 simultaneous Mac sessions, ~30% coordination overhead, AP-54 Nth recurrence, 0 Spectra commits). Karpathy ground-truth (the 4-session pattern doesn't actually parallelize on shared vault) + Musk step-2 (delete the collision pattern) + Tan-YC (1 critical-path driver + cron substrate, what a billion-dollar 1-employee company runs).

## See also

- [[skills/session-coordination/SKILL]] — peer-session handshake (AP-5 substrate-awareness) — works WITH this skill: when 1+3+dispatch is followed, session-coordination's substrate-awareness handles the rare legitimate dual-session case (e.g., dispatch claim transfer)
- [[skills/session-operating-contract/SKILL]] — runtime contract; Stream A close protocol absorbs from here
- [[skills/musk-algorithm/SKILL]] — step-2 delete applied to the workflow itself
- [[skills/karpathy-loop/SKILL]] — ground-truth (the 4-session pattern was performing worse than it appeared)
- [[skills/audit/SKILL]] — Spectra-ratio is an audit-class metric

## Timeline

- **2026-04-25** | s74-mac-12354: v1.0.1 — Stream-A claim lock bug fix. `tools/stream_a_claim.sh:is_active()` required `kill -0 $stored_pid` BUT the stored PID was the acquire-script's own ephemeral `$$` (script exits immediately after writing the lock). Result: every freshly-acquired lock reported `status:"stale"` with exit 2 on the very next status call, breaking peer-collision detection in Stage 2 SessionStart hook design. Fix: time-only staleness — drop PID-alive check, retain epoch-vs-MAX_AGE (7200s) check. Verified: positive (held + exit 0), negative (3h-old simulated → stale + exit 2), restore (1s old → held + exit 0). PID retained in JSON for diagnostics. Compounding: Stage-2 SessionStart hook (carryover #2) can now reliably read status without false-stale on every fresh acquire. No new LESSON (RULE ZERO).
- **2026-04-25** | s73-mac-44149: v1.0.0 created. Replaces implicit "spawn N Mac CC sessions" pattern with 1 Stream-A driver + 3 substrate cron streams + ad-hoc Stream-D dispatch. Doctrine grounded in s73 empirical observations (AP-54 attribution drift Nth recurrence, MEMORY single-writer bottleneck, Obsidian dup files, 30% coordination overhead, 0 Spectra commits / 4 infra commits). Madi approved hybrid option (3) in chat.
