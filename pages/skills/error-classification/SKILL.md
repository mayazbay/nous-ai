---
tier: 1
name: error-classification
description: "Classify errors BEFORE reacting. 5 severity levels (L0 noise → L4 legal/gov) with deterministic classification protocol, response matrix, and 3-strike escalation rule. Triggers on 'error', 'exception', 'fail', 'timeout', 'retry', 'crash', 'alert'."
type: skill
id: SKILL-ERROR-CLASSIFICATION
version: 1.0.0
status: active
absorbs_laws: [LAW-015]
absorbs_lessons: [LESSON-104]
tags: [skill, error, classification, severity, escalation, god-prompt, 2026-04-15]
date: 2026-04-15
source_count: 0
last_updated: 2026-04-15
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, mistake-to-skill, factory-ops, LAW-015-root-cause-evolution, LESSON-104-litellm-router-dual-provider-cooldown-crash]
title: "error-classification v1.0.0"
---

# error-classification v1.0.0

## Current rules (compiled truth)

Not all errors are equal. Classify BEFORE reacting. Pick the level, apply the response. If 3 failed fixes at any level → escalate one level up.

## The 5 levels (deterministic, picked at error-time)

### Level 0 — Noise (ignore)
**Examples:** Token budget warnings, transient network blips, API rate-limit retry-after within normal window, cosmetic lint warnings.
**Action:** Do not alert. Do not log beyond existing default. Do not interrupt flow.
**Trap:** If the SAME "noise" fires 10+ times in an hour, it's not noise — it's Level 1.

### Level 1 — Self-heal (fix automatically)
**Examples:** Failed test, syntax error, missing import, config typo, single-retry rate limit, flaky network call with backoff.
**Action:** Fix → re-run → continue. Log only if the pattern is novel (not seen in existing skills/lessons). If novel + recurring → escalate to L2.
**Trap:** Silent retries that mask a real bug. Always log the fix, even if automated.

### Level 2 — Root cause (investigate)
**Examples:** Same error 3+ times, regression on previously-working code, data mismatch, cross-service call failing.
**Action:** Full root-cause protocol (from skill: mistake-to-skill). Reproduce minimally → isolate → trace → fix root → regress all tests → absorb into skill. Lessons file required if novel (LAW-015).
**Trap:** Fixing the symptom. If the first fix didn't take in 1 try, you're treating a symptom.

### Level 3 — Architecture (needs human decision)
**Examples:** Design choice affecting multiple modules, data-model change, new external dependency, security boundary shift.
**Action:** Write an ADR (Architecture Decision Record) in `pages/decisions/` (or `pages/specs/`) with context/decision/consequences. Ping Madi via handoff or summary. WAIT for response.
**Trap:** Making a Level-3 call on your own "to keep momentum." Architecture debt compounds 10x harder than code debt.

### Level 4 — Legal / government (requires authority)
**Examples:** ERAP submission, government letter, ЭЦП signing, SmartBridge VPN application, BIN change, tender filing.
**Action:** HITL gate — ping Madi via handoff/telegram (via telegram_poll.py, never MCP). WAIT. No government action is ever autonomous.
**Trap:** "Madi already approved X so Y is close enough." Authorization stands for scope specified, not beyond.

## P1 — Classification protocol (run in order on any error)

1. Is it one of the known-noise patterns listed in L0?
2. Has the same error happened >3 times in the last hour? → L2+
3. Does fixing it touch >2 files in different subsystems? → L3
4. Does it touch government/legal/BIN/ЭЦП/contract? → L4
5. Else → L1

## P2 — Response matrix

| Level | Retry? | Log? | Alert Madi? | Lesson file? | ADR? | Skill update? |
|---|---|---|---|---|---|---|
| L0 | default | no | no | no | no | no |
| L1 | auto | only if novel | no | only if novel + recurring | no | yes if pattern |
| L2 | only after root-cause | yes | summary in handoff | yes (LAW-015) | no | yes |
| L3 | N/A — needs decision | yes | yes (Telegram via poller) | yes | yes | after decision |
| L4 | N/A — needs authority | yes | yes (immediate) | yes | if permanent | after approval |

## Anti-patterns

### AP-1: "I'll escalate later"
**Problem:** Later never comes. The agent hands off the session without the L3/L4 flag.
**Fix:** Alert at classification time, not completion time.

### AP-2: Treating L2 as L1 (retry loop)
**Problem:** Same fix attempted 10 times → burn tokens, never works. LESSON-104 is this exact pattern (dual-provider cooldown crash).
**Fix:** 3-strike rule. 3 failed fixes → stop, reclassify upward.

### AP-3: Letting L0 noise accumulate
**Problem:** 100 "noise" warnings in a week mask a real L1 issue.
**Fix:** Weekly sweep via nightly-audit → if any "noise" pattern fired >50x → investigate.

## Rules absorbed

- **LAW-015** (root-cause evolution): enforced at L2+
- **LESSON-104** (LiteLLM dual-provider cooldown): the canonical L2 example — 3-strike rule exists because of it

---

## Evidence trail

- **2026-04-15** | v1.0.0 created per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P2. Absorbs GOD_PROMPT §7 + LAW-015 + LESSON-104.

## See also

- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[mistake-to-skill]] — the L2+ response engine
- [[factory-ops]] — 3-strike retry logic lives here
- [[LAW-015-root-cause-evolution]]
- [[LESSON-104-litellm-router-dual-provider-cooldown-crash]]
