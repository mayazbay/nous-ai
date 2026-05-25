---
type: lesson
id: LESSON-054
title: "CEO LLM called every empty cycle, hallucinated REQ numbers, all rejected — $6/day burn"
enforcement: code-gate
tags: [lesson, factory, root-cause, cost, hidden-loop]
date: 2026-04-07
related: [LESSON-051, LAW-015]
last_updated: 2026-04-07
source_count: 1
integrated_into: [factory-ops]
status: implicit-already-in-skill
absorbed_into: [factory-ops]
absorbed_at: 2026-04-16
---
# LESSON-054 — CEO loop burned ~$6/day on a guaranteed-empty result

## Symptom
After Phase 2 finished and the queue drained (with LESSON-051 fixing project filter), the factory ran into a different idle loop:
- Every cycle (5 min apart): no pending tasks
- CEO LLM called with prompt "create 3 P0 tasks from VMS specs"
- CEO returns 3 task candidates with hallucinated REQ numbers (e.g. REQ-024, REQ-042, REQ-065)
- Duplicate detector (FIX 3) rejects all 3 because those REQ numbers are already done
- Cycle returns "no_tasks", sleeps 5 min, repeats
- **63 such cycles today.** ~$0.10 each = **$6.30 wasted**

## Root cause (two layers)

### Layer 1: spec file had no REQ tags
`pages/specs/cerebro_bdl_vms_requirements.md` listed 81 numbered requirements as `1.`, `2.`, ..., `81.` with no `REQ-xxx` tags. The CEO prompt asked "create REQ-xxx tasks from these specs," so the LLM **made up REQ numbers from thin air every time** — sometimes REQ-024, sometimes REQ-042, sometimes REQ-065. Non-deterministic.

The duplicate detector caught them because those numbers HAPPENED to overlap with already-done historical tasks. But the LLM never converged on the ~59 truly fresh requirements because it was always guessing.

### Layer 2: no pre-flight check before CEO LLM call
`ceo_node` in `graph.py` (line 287) checks `if not pending` and immediately calls the Opus LLM. There was no logic of the form "before spending $0.10 on Opus, check if there are even any fresh REQs to work on."

The duplicate-rejection happened AFTER the LLM call, so the cost was already burned.

## Fix
Two changes:

### Fix A: Tag the spec
`tag_spec.py` rewrote `1. text` → `1. [REQ-001] text` for all 81 items in the spec file. Now the spec is the deterministic source of truth for valid REQ numbers.
- Spec REQs: 81
- DB REQs (any status): 23
- Overlap: 22
- Fresh REQs ready for the factory: 59

### Fix B: Pre-flight check in ceo_node
Added before the CEO LLM call:
```python
# Compute fresh REQs from spec
spec_reqs = parse(specs_file)
existing = {req for task in get_all_tasks() if task.status in (done, in_progress, pending, blocked, failed)}
fresh = spec_reqs - existing
if not fresh:
    log.warning("All spec REQs are already tracked. Skipping CEO LLM call.")
    return {error: "no_fresh_reqs"}
state["_fresh_reqs"] = sorted(fresh)[:10]  # hint the CEO so it doesn't re-hallucinate
```

Both fixes together: empty cycle now costs **$0** instead of $0.10. Daily savings: **~$6** at current cycle rate.

## Permanent prevention
1. **Specs must be tagged.** Every requirement in any `pages/specs/*.md` MUST have a `REQ-xxx` tag at the time of writing. Add this rule to CLAUDE.md schema.
2. **Never call an LLM from a code path that has no productive work to do.** Always answer "is there work?" with cheap deterministic code BEFORE invoking the model.
3. **State the fresh REQ list TO the CEO** so it converges instead of guessing. The fix passes `state["_fresh_reqs"]` for the CEO to use.
4. **If a class of cycle returns "no_tasks" 5 times in a row, the cycle interval should exponentially back off.** TODO for next fix.

## What everyone learns
- **Empty work + idle retry is the most expensive failure mode in autonomous LLM systems.** Idle loops at $0.10/cycle × 24h = $30/day. This is how you wake up to a dead bank account.
- **LLM-generated identifiers without grounding will not converge.** Always anchor LLMs to a deterministic source of truth (here: the tagged spec).
- **The duplicate detector is a failsafe, not a primary defense.** Failsafes should fire rarely; if they're firing every cycle, the primary defense is missing.

## Cost accounting (today)
- Useful work: 4 deploys × $2.30 = $9.20
- Wasted on this leak: 63 cycles × $0.10 = $6.30
- Wasted on budget retry loop: ~$0 (LESSON-055 — small cost, big log noise)
- Wasted on credit-low retry: ~$0 (LESSON-056 — same)
- Total today: $15.57 ÷ 4 deploys = $3.89 per actual deployed feature (target: <$2.50)

## See also
- [[LESSON-051-get-pending-tasks-hardcoded-project]]
- [[LESSON-055-budget-hit-retry-loop]]
- [[LESSON-056-anthropic-credit-exhausted-retry]]
- [[LAW-015-root-cause-evolution]]
