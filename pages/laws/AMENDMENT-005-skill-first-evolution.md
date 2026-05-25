---
type: law
id: AMENDMENT-005-skill-first-evolution
title: "AMENDMENT-005: Skill-first evolution (7-day absorption SLA)"
tags: [law, amendment, evolution, skill-first, rule-zero]
date: 2026-04-16
status: active
related:
  - "[[skills/karpathy-loop/skill]]"
  - "[[skills/mistake-to-skill/skill]]"
  - "[[skills/session-operating-contract/skill]]"
  - "[[LAW-001-evolution]]"
  - "[[LAW-009-self-evolution]]"
  - "[[LAW-015-root-cause-evolution]]"
  - "[[LAW-017-success-is-skill]]"
---

# AMENDMENT-005: Skill-first evolution

## Rule

When a substrate-level mistake, bug, or learning is observed, the absorption SLA is **7 days from the triggering event** to:

1. Update the relevant `pages/skills/<skill>/SKILL.md` (new AP / new phase / new bullet under "Current rules")
2. Bump the skill's `version:` field per `mistake-to-skill` AP-11 3-edit ritual
3. Append a `## Timeline` or `## Evidence trail` entry on that SKILL.md
4. Push the matching `mcp__gbrain__add_timeline_entry` for the skill page

If the absorption SLA expires without codification, the learning is at risk of decaying and the substrate compounds less than it should.

## Why

Per RULE ZERO (project `CLAUDE.md`), all learnings land in `SKILL.md` + gbrain timeline — never in new `LESSON-NNN-*.md` files. Skills compound (re-read every invocation); lessons rot (written once, never re-read). The 7-day window is the empirically observed maximum between when a learning is fresh enough to absorb without context loss and when it starts decaying into unstructured memory.

## How to apply

- At each session-close, scan the session for new mistakes / fixes / learnings worth persisting.
- For each one, identify the relevant existing skill (or create a new one and register it in `pages/skills/_gbrain/RESOLVER.md`).
- Apply the 3-edit ritual + gbrain timeline push within the session if possible, or as the first action of the next session.
- If the 7-day window passes, the next-session agent that reads handoff carryover MUST prioritize absorbing the deferred learning before any new work — same axis-1 of `karpathy-loop` 6-axis scorecard.

## Compounding

This amendment is referenced from:
- `pages/skills/karpathy-loop/SKILL.md` (rules absorbed)
- `pages/skills/session-operating-contract/SKILL.md` (rules absorbed)
- `pages/skills/mistake-to-skill/SKILL.md` (the mechanism)
- `MEMORY.md` (substrate top-block)

## Timeline

- **2026-04-16** | Conceived via session 35 RULE ZERO codification (Tan/Karpathy/Finn pattern). Originally referenced as `AMD-005` and `AMENDMENT-005` across multiple SKILL files and MEMORY.md but never had a dedicated page. Cross-references resolved against MEMORY.md text only.
- **2026-04-30** (s104) | Created proper AMENDMENT-005 page during AUDIT-LIBRARY-CROSSREFS-2026-04-30 to close 4 Tier-A1 broken wikilinks pointing at `[[AMENDMENT-005-skill-first-evolution]]` and `[[AMD-005-skill-first-evolution]]`. No new LESSON file (RULE ZERO).
