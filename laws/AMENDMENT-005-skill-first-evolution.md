---
type: amendment
id: AMD-005
title: "AMD-005: Skill-First Evolution — 7-Day Absorption SLA"
aliases: [AMD-005-skill-first-evolution]
tags: [law, amendment, skill-first, evolution, absorption-sla, karpathy, 2026-04-16]
date: 2026-04-16
source_count: 0
status: reviewed
last_updated: 2026-04-24
related: [LAW-015-root-cause-evolution, SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, LESSON-114-empty-openclaw-system-prompt]
---

# AMD-005: Skill-First Evolution

**Amends:** LAW-015 (Root-Cause Evolution)

**Effective:** 2026-04-16

## The Amendment

**LAW-015 required:** Every bug produces a LESSON file.

**AMD-005 adds:** Every lesson MUST be absorbed into a SKILL.md within 7 days. A standalone LESSON file that remains unabsorbed for >7 days triggers a Telegram alert (via `lesson_absorption_watcher.py`). The SKILL layer is what the agent reads at task-time; a standalone LESSON alone does not reach the agent.

## Rules

1. **Skills are the evolution substrate.** Lessons are the audit trail. Knowledge that tells an agent *what to do step-by-step* compounds; knowledge that tells an agent *what to remember* decays (NASA lessons-DB: <25% useful retrieval; JPL fix: embed into procedures).

2. **7-day SLA.** Any lesson unabsorbed for ≥7 days is flagged by `dream_cycle.py` (nightly) and `lesson_absorption_watcher.py` (every 6h). Target: ≥95% absorption rate.

3. **Skill + gbrain timeline (session-35 update).** Per session-35 architectural correction: the dual-write of "SKILL + LESSON file" was retired. The pattern now matches Tan/Karpathy/Finn exactly: rules live in `pages/skills/<skill>/SKILL.md`, evidence lives in the gbrain timeline of that same skill page. Procedure when persisting a new rule:
   - Update `pages/skills/<skill>/SKILL.md` (add the rule, bump skill version, append a one-line `## Timeline` entry).
   - Append a gbrain timeline entry on the same skill page: `mcp__gbrain__add_timeline_entry slug="pages/skills/<skill>/skill" date=YYYY-MM-DD summary="..."`
   - **Do NOT create `pages/lessons/individual/LESSON-NNN-*.md`.** The pre-commit hook (in every wiki working copy) PHYSICALLY REJECTS new LESSON files (`--diff-filter=A` match). See `mistake-to-skill` AP-8.
   - Sync to runtime: `wiki-to-runtime-rsync.sh` handles this automatically (only syncs `pages/skills/`).
   - Existing LESSON-001 … LESSON-129 are historical receipts — may be edited (subject to AP-7 drift gate) or deleted (during eventual migration). They MUST NOT grow in number.

4. **Skills use compiled-truth format.** `## Current rules` above the `---` separator (editable, rewritable). `## Evidence trail` below the separator (append-only, never delete).

5. **Dream cycle is READ-ONLY.** The nightly `dream_cycle.py` proposes absorption but NEVER mutates skills directly. All proposals require human or interactive-session review.

## Research Basis

| Source | Finding |
|---|---|
| Karpathy "System Prompt Learning" | System prompt should be LLM-authored procedures, not human instructions |
| Garry Tan GBrain | Compiled truth above separator, append-only evidence below |
| NASA lessons-DB (GAO 2001) | <25% retrieval success. JPL fix: embed into executable procedures |
| Mem^p (Zhejiang/Alibaba 2025) | Procedural memory transfers across model tiers |
| Anthropic Agent Skills Standard | Progressive disclosure: metadata → body → resources |

## Enforcement

- `dream_cycle.py` (daily 03:15): scans, proposes, alerts
- `lesson_absorption_watcher.py` (every 6h): flags overdue
- `ghost_debt_dashboard.py`: tracks absorption rate over time
- `audit evolution` sub-audit (audit skill v1.2.0): verifiable on-demand

---

## Timeline

- **2026-04-16** | AMD-005 enacted as part of GOD_PROMPT v1.0 migration. Codifies the skill-first principle validated by 5 independent research sources + 28 sessions of operational evidence.
- **2026-04-16** | Session 35 amendment: dropped the LESSON-file requirement from Rule 3. Pattern now matches Tan/Karpathy/Finn exactly: SKILL.md doctrine + gbrain timeline evidence; no LESSON file. Pre-commit hook physically blocks new LESSON files (`mistake-to-skill` AP-8). Existing LESSONs preserved as historical receipts. Removes the "agents always write LESSON files" trap that recurred across sessions 33–35.

## See also

- [[LAW-015-root-cause-evolution]]
- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[mistake-to-skill]]
- [[evidence-verification]]
