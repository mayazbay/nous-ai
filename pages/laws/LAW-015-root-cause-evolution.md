---
type: law
id: LAW-015
title: "LAW-015: Root Cause Evolution"
tags: [law, absorbed]
date: 2026-04-16
absorbed_into: gbrain-ops
---

# LAW-015 - Root Cause Evolution

This law has been absorbed into the **gbrain-ops** skill (session 24, Wave 4).

See pages/skills/gbrain-ops/SKILL.md for the current enforcement rules.

---

## Session 35 amendment (2026-04-16)

The original LAW-015 phrasing — "Every Level-2+ error produces a LESSON file" — has been **superseded** by the Tan/Karpathy/Finn pattern. The current rule is:

- **Every persistent rule lands in a SKILL.md** (new AP, phase, or "Current rules" bullet); bump skill version; append one-line `## Timeline` entry.
- **Evidence lands in the gbrain timeline of that same skill page** (`mcp__gbrain__add_timeline_entry`).
- **No new LESSON-NNN file.** The pre-commit hook in every wiki working copy physically rejects them (`mistake-to-skill` AP-8).

Authoritative reference: [[mistake-to-skill]] v1.4.0 AP-8 + AMD-005 (session-35 amendment) + RULE ZERO in `CLAUDE.md` (Mac project + wiki, both updated session 35).
