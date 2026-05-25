---
type: amendment
id: AMD-006
title: "AMD-006: Auto-Memory as Session-Continuity Substrate"
aliases: [AMD-006-auto-memory-session-continuity-substrate]
tags: [law, amendment, auto-memory, session-continuity, karpathy, tan-pattern, 2026-04-18]
date: 2026-04-18
source_count: 0
status: reviewed
last_updated: 2026-04-24
related: [LAW-005-obsidian-master, AMENDMENT-005-skill-first-evolution, SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, PLAN-GOD-PROMPT-V1-2026-04-15, HANDOFF-GODPROMPT-V1-COMPLETE-2026-04-18]
---

# AMD-006: Auto-Memory as Session-Continuity Substrate

**Amends:** PLAN-GOD-PROMPT-V1-2026-04-15 Task 30, and supplements AMD-005 + LAW-005.

**Effective:** 2026-04-18 (session 46 close).

## The Amendment

**GOD_PROMPT v1.0 plan Task 30 required:** Trim `pages/progress/claude-memory/MEMORY.md` to ≤60 lines (architecture ground-truth only).

**AMD-006 formally defers Task 30** and reclassifies MEMORY.md as follows:

> **MEMORY.md is the session-continuity substrate.** It is an append-at-top, historically-preserved, LLM-curated session diary — NOT an architecture snapshot. Truncating it to ≤60 lines destroys the compound audit trail that lets session N+1 begin where session N ended. The architecture-ground-truth view that Task 30 sought belongs in a separate compiled document (`MEMORY-ARCHITECTURE.md`, to be drafted), not as a replacement for the live continuity vehicle.

## Why the original Task 30 target is wrong

1. **The plan was written 2026-04-15** when MEMORY.md was ~95 lines and substantively matched the "architecture ground-truth" description.
2. **Session 35 rolled out RULE ZERO** (skills + gbrain timeline, no new LESSON files — Tan/Karpathy/Finn pattern). The filesystem LESSON corpus was frozen at 129; the LESSON layer stopped growing as an audit trail.
3. **The audit trail had to land somewhere.** MEMORY.md absorbed that load — each session prepends a dense block with: open carryovers, skill-version deltas, sync state, AP-absorption audit, priority-ordered session-N+1 checklist, 4-way HEAD at close.
4. **Today's MEMORY.md (686+ lines)** is the result of that architectural shift. It is how session 46 reads session 45's close-audit, session 45 reads session 44's TaskCompleted hook patch, session 46-B coordinates with the concurrent GOD_PROMPT thread, etc.
5. **Truncating to 60 lines** would erase that coordination channel. Sessions would regress to "read the handoff, hope it's comprehensive." Handoffs are dense; the MEMORY block at top of every new session is the pre-chewed executive summary that gets the agent oriented in 30 seconds.

## Rules

1. **MEMORY.md is load-bearing architecture, not noise.** Treat it as tier-1 alongside CLAUDE.md + `pages/skills/*/SKILL.md`. Do not truncate in bulk.

2. **Top-block-prepend discipline is the correct long-term pattern.** Each session prepends a new `## Session <N>` H2 block at the top; older blocks shift down. This is append-only where it matters (the session-to-session audit trail) and revisable where it helps (the top block summarizes the most recent work).

3. **Size-management policy (future).** When MEMORY.md crosses a size threshold (to be determined empirically; 2000 lines is a reasonable first anchor), older bottom blocks may be archived to `pages/progress/claude-memory/session-history-archive/MEMORY-pre-session-NN.md`. Archiving preserves the content with provenance; deletion does not. This is a separate future amendment if needed.

4. **Architecture ground-truth view goes in a NEW compiled file.** If Task 30's original intent ("architecture table + skill versions + identity + open blockers in ≤60 lines") is still useful — and it may be — draft `pages/progress/claude-memory/MEMORY-ARCHITECTURE.md` as a distinct compiled artifact, curated less frequently than MEMORY.md and with a clearer invariant. Do NOT implement this by truncating MEMORY.md.

5. **GOD_PROMPT v1.0 plan Task 30 is formally CLOSED-DEFERRED.** Session 46 completion handoff documents this with full reasoning; AMD-006 ratifies it. The 33-task ledger reads 32 shipped + 1 AMENDED (Task 30 → AMD-006).

## Evidence for the reclassification

| Evidence | Source |
|---|---|
| MEMORY.md evolved 95 → 686 lines over sessions 35-46 as audit-trail substrate | `git log pages/progress/claude-memory/MEMORY.md` |
| Session-open checklist lives in MEMORY.md top block, not handoff | `CLAUDE.md` + multiple HANDOFF-AUTO-* files reference "Read MEMORY.md top block" |
| Deep-audit findings (session 46) absorbed as top-block addendum, not separate doc | `pages/progress/claude-memory/MEMORY.md` Session 46 DEEP-AUDIT ADDENDUM |
| RULE ZERO (session 35) froze LESSON corpus; the audit trail migrated to MEMORY + gbrain timeline | `pages/skills/mistake-to-skill/SKILL.md` AP-8 + gbrain timeline on `pages/skills/mistake-to-skill/skill` |

## Compliance

- LAW-005 (Obsidian master): MEMORY.md is in the vault at `pages/progress/claude-memory/MEMORY.md`, symlinked via `~/.claude/projects/.../memory/`. This amendment does not change the location — only the content-policy.
- AMD-005 (7-day absorption SLA): AMD-006 is orthogonal. Lessons still must absorb to skills within 7 days; MEMORY.md is a distinct artifact.
- RULE ZERO (session 35): AMD-006 does NOT create new LESSON files. It is a law/amendment (content-policy rule) saved to `pages/laws/`, which is where amendments live.
- GOD_PROMPT v1.0 spec §5 Gate G-none: MEMORY.md was never a named gate target. Task 30 was a plan item, not a spec gate. Deferring it does not affect the 10-gate verification.

## See also

- [[LAW-005-obsidian-master]] — vault as single source of truth
- [[AMENDMENT-005-skill-first-evolution]] — 7-day absorption SLA for lessons (not MEMORY)
- [[PLAN-GOD-PROMPT-V1-2026-04-15]] — original Task 30 (now formally deferred by this amendment)
- [[HANDOFF-GODPROMPT-V1-COMPLETE-2026-04-18]] — session 46 completion handoff, §"Deferred: Task 30"
- [[mistake-to-skill]] — AP-8 (RULE ZERO) + AP-11 (session 46: SKILL.md version parity)
- [[audit]] — AP-14 (session 46: post-close deep audit catches cross-cut drift)

## Timeline

- **2026-04-18** | session 46 close: drafted AMD-006 to formalize Task 30 deferral + codify MEMORY.md as the session-continuity substrate. MEMORY-ARCHITECTURE.md file not yet drafted — session-47 candidate if Task-30's original intent is still useful as a separate artifact. Absorbs the deep-audit insight that truncating MEMORY.md would regress session-to-session continuity. No new LESSON (RULE ZERO).
