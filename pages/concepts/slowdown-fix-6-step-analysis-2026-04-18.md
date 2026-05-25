---
type: concept
id: CONCEPT-SLOWDOWN-FIX-6-STEP-ANALYSIS-2026-04-18
title: "6-step OpenClaw slowdown-fix advice — first-principles analysis against OUR factory stack"
tags: [concept, analysis, openclaw, factory, performance, session-48, 2026-04-18, first-principles]
date: 2026-04-18
source_count: 1
status: reviewed
last_updated: 2026-04-18
owner: claude-code-mac
related:
  - infrastructure
  - audit
  - AUDIT-OPENCLAW-HEALTH-2026-04-18
  - HANDOFF-AUTO-2026-04-18-session-48
  - feedback_default_right_way
---

# 6-Step OpenClaw Slowdown-Fix Advice — Analysis vs OUR Stack

**Source:** Twitter/Telegram-posted advice shared by Madi session 48, 2026-04-18. Written for Claude Code CLI users experiencing slowdown.

**Driver:** Third Reinforcement rule 6 — "first-principles the inputs. External best practices verified against OUR architecture before acting."

**Our stack (per `infrastructure` v2.38 + `MEMORY-ARCHITECTURE.md`):**
- **Factory = OpenClaw container** (Air Docker, port 18789, WebSocket) + `run_task.py` entry + LiteLLM proxy + GLM-5.1 via ZAI resource package. **NOT Claude Code CLI.**
- **Scheduled jobs = 17 `com.nous.*` launchd services** on Air. Majority are bash/python scripts that invoke `run_task.py` (not `claude`).
- **Context source = `tools/context_injector_v2.py`** with G4 cap 8192 bytes (codified session 46 AP-37) — already aggressive.
- **Skills = 20 domain SKILL.md files** in vault + `skillsSnapshot` of 4 loaded into OpenClaw's active session (`camera-management`, `infrastructure`, `metrology-cert-tracker`, `smartbridge-soap-client`).

**Verdict:** 2/6 steps apply as-is. 2/6 partially apply with adaptation. 2/6 don't apply.

## Step-by-step analysis

### Step 1 — Clear sessions

> "Every cron job creates a session record. All session records get sent as context, slowing claw down big time. Ask OC to clear these."

**Our stack state:** OpenClaw has **ONE** main session (`agent:nous:main` = `00518026-...`), 375 KB active jsonl + 5 checkpoint files (3.4 MB) + 33 KB `sessions.json`. Total `/home/node/.openclaw` = 11 MB.

**Applicability:** 🟡 **PARTIAL.** We don't have session sprawl — just one main session. BUT 5 checkpoints accumulating = checkpoint bloat. Not a clear RED, but worth investigating if checkpoints are load-bearing (agent re-reads them each task) vs. historical (append-only, never read).

**Session-49 action:** Probe — does OpenClaw re-read checkpoint jsonl on each task? If yes, they DO load into context → purge candidates. If no, they're cold storage, leave alone. Check OpenClaw source or behavior via controlled test.

### Step 2 — Use topics in Telegram

> "Start a group chat and just add your claw. Then create topics. In each topic, only the context from that topic gets sent to your claw."

**Our stack state:** Telegram setup is **1-on-1 DM** between Madi and `@nousAGaaSbot` (HARD-RULE-1: never use Telegram MCP in Claude Code; handler is `telegram_poll.py` on Air).

**Applicability:** ❌ **NOT APPLICABLE.** Topics only exist in groups. Madi uses DM. Bot doesn't receive group context anyway. Converting to a group for topics would be over-engineering for a 1-user deployment.

**No action.**

### Step 3 — Kill unused crons

> "We love to add cron jobs but never take them away. Every time a cron is run, your openclaw becomes basically unusable during that time."

**Our stack state:** 17 `com.nous.*` launchd services. Per session-48 P-SAFE-01 probe, ALL 17 have `last_exit=0` (or long-running). Per session-47 AP-39 + session-47 W5/M6, 13 `.bak-*` orphan plists were deleted already.

**Applicability:** 🟢 **APPLIES but LOW-YIELD.** Every current cron has a named purpose. Killing any breaks something. Per AP-39 proof-of-deadness discipline, we don't delete without 4-test evidence. Only 4 of 17 crons actually invoke `run_task.py` (auto-checkpoint, dream-cycle, morning-brief, morning-update-apply) + 1 uses OpenClaw via Telegram routing (telegram-poll) + 1 long-running service (litellm). The other 11 are pure bash scripts with NO factory load. Already lean.

**Session-49 action (low priority):** Run `audit evolution` sub-audit to get "skills never used in 30d" metric. If any cron's purpose has lapsed, apply AP-39 Mode B proof-of-deadness.

### Step 4 — Use `--light-context` on cron jobs

> "This flag stops crons from loading your full SOUL.md/MEMORY.md/AGENTS.md every run. Massive token savings."

**Our stack state:** `--light-context` is a **Claude Code CLI flag**. Our crons invoke **`run_task.py` (our wrapper around OpenClaw), not `claude`**. The flag doesn't transfer. Factory's context loading is handled by `context_injector_v2.py` with G4 cap 8192 bytes already (per AP-37).

**Applicability:** ❌ **NOT APPLICABLE as-is.** The flag is for a product we don't use from crons.

**Adaptation candidates (session-49+ investigation):**
1. Does `run_task.py` have a skip-preamble or minimal-context flag? Grep `run_task.py` for arg parsing.
2. Does OpenClaw read `SOUL.md` / `AGENTS.md` equivalents we could bypass per-cron?
3. Our context-injector v2 cap is already 8192 bytes — verify no cron is bypassing this cap (nightly regression gate AP-38 covers this).

**No action session 48.** Pre-session-48 probe already confirmed G4 cap live.

### Step 5 — Trim system prompts (MEMORY.md / CLAUDE.md / SOUL.md / AGENTS.md)

> "Your system prompts only grow over time. Very rarely do they shrink. More growth → more context per prompt."

**Our stack state:**
- `MEMORY.md` — **130 KB / 965 lines**. Large. **AMD-006 explicitly vetoes bulk-truncate** (auto-memory is load-bearing architecture, not clutter).
- `CLAUDE.md` — 7.2 KB (~250 lines). Concise.
- `SKILL.md` files — 20 files; largest `infrastructure/SKILL.md` = 1060 lines. Others 242-786.
- `AGENTS.md` — doesn't exist in our stack.
- **Not all files load into every prompt.** CLAUDE.md is always loaded. Skills load per-task via `skillsSnapshot` (4/20 currently). MEMORY.md loads only in Claude Code sessions (symlinked), not factory cron runs.

**Applicability:** 🟡 **PARTIAL.** AMD-006 blocks MEMORY.md trim (architectural, not bloat). CLAUDE.md + SKILL.md are already within reason. But 20 skills × 400 avg lines = ~8K lines of doctrine — if ALL ever load simultaneously, that's a real context hit.

**Session-49 action (medium priority):** Investigate WHY factory loads only 4/20 skills. Intentional (only 4 are factory-relevant) or a registration bug? If intentional, fine. If bug, we have a different problem — skills authored but not reachable by factory = wasted authoring. Surfaced in AUDIT doc post-publication addenda.

### Step 6 — Compact more often (threshold 80% vs 100%)

> "If you have a good custom memory system, you can compact more often without your claw getting dumb."

**Our stack state:** Compaction is a **Claude Code internal** — 127K token context with auto-compaction. Factory stack doesn't use this. Our equivalent = `context_injector_v2.py` + dream-cycle + auto-checkpoint (all Mac-authored artifacts that periodically summarize state).

**Applicability:** ❌ **NOT APPLICABLE as-is.** Different codepath.

**Parallel already in place:** Our `context_injector_v2.py` caps at 8192 bytes (G4), which IS our aggressive-compaction equivalent. Regression tested nightly (launchd `com.nous.context-injector-regression`).

## Actionable items for session 49

| Step | Action | Priority | Scope |
|---|---|---|---|
| 1 | Probe: does OpenClaw re-read checkpoint jsonl per task? (Controlled test.) If yes → purge candidates. | 🟡 Medium | 20 min probe + decision |
| 3 | Run `audit evolution` sub-audit for "skills never used in 30d" metric. Check if any cron's purpose is stale. | 🟢 Low | 10 min |
| 4 | Investigate `run_task.py` arg parsing for a minimal-context flag. If exists, candidate for morning-brief / auto-checkpoint (read-only monitoring crons). | 🟡 Medium | 30 min |
| 5 | Investigate factory skill-load scope (4/20 loaded). Intentional or registration gap? | 🟡 Medium | 30 min |

## What NOT to do (anti-patterns surfaced by this analysis)

1. ❌ **Do not apply `--light-context` to launchd plists.** It's a Claude Code CLI flag; our plists invoke `run_task.py` / bash scripts. Was session-48 W8 planned action — pivoted after first-principles check. Would have been a no-op at best, broken cron at worst (unknown flag rejected).
2. ❌ **Do not truncate MEMORY.md.** AMD-006 Rule 1: MEMORY.md is tier-1 load-bearing architecture, not bloat. Bulk truncation destroys session continuity.
3. ❌ **Do not delete session checkpoints blindly.** AP-39 proof-of-deadness gate applies: need evidence that checkpoints are COLD (never re-read) before deletion. Assumption ≠ evidence.

## Karpathy-compounding win from this analysis

This doc IS the compounding artifact. External advice was ingested, first-principled, mapped to OUR stack. Future sessions find this via gbrain search (`slowdown`, `6-step`, `--light-context`, `compaction`) before re-evaluating — saves future-Mac from re-doing this analysis. Absorbs `feedback_default_right_way.md` rule 6 ("first-principles the inputs") in a concrete worked example.

**Counter-evidence:** I was about to apply step 4 (W8 plan) without first-principles check. The Third Reinforcement rule 6 lived in memory but didn't gate execution until the wrong target (`com.nous.staleness`, a bash script) surfaced a mismatch between advice and stack. **Rule is only a gate if it's checked BEFORE action, not after.** Session-49+ candidate: consider a pre-execution "external-input verifier" checklist for operational crons.

## Timeline

- **2026-04-18** | Session 48 W8 pivot — initial plan was "apply `--light-context` to low-risk crons." First probe (`com.nous.staleness` plist) revealed the flag/stack mismatch. Rather than silently drop the plan, codified the per-step analysis for future sessions. Closes W8/W9/W10 as documentation + defers 4 actionable items to session 49. [[HANDOFF-AUTO-2026-04-18-session-48]]
