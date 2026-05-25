---
type: law
id: LAW-017
title: "LAW-017 — Every Success Is a Skill: Save Everywhere So All Agents Evolve"
tags: [law, skill, write-back, factory, evolution, mandatory]
date: 2026-04-14
source_count: 0
status: reviewed
last_updated: 2026-04-14
related: [LAW-015-root-cause-evolution, LESSON-085-false-declaration-feature-done-without-end-to-end-test]
---

# LAW-017 — Every Success Is a Skill: Save Everywhere So All Agents Evolve

## The Law

**When any task succeeds in a non-obvious way, that success MUST be captured as a reusable skill and written to the wiki immediately.**

This applies to:
- Claude Code sessions (write to `pages/skills/` or `pages/tools/` in vault)
- Factory tasks run via `run_task.py` (Hermes auto-extracts via `factory-poller.py`)
- Manual problem-solving that took >5 min and isn't obvious
- Any workaround, fix pattern, or approach that future agents would waste time re-discovering

## Why

Madi's directive (session 14, 2026-04-14):

> "when you are success — that is skill, so everybody evolve. save to everywhere. must always do that so that next sessions and the factory does that"

Without this law:
- Every agent starts from zero on problems already solved
- Factory spends tokens rediscovering known patterns
- Human has to re-explain the same thing in every session

With this law:
- Each success compounds into future capability
- The factory extracts skills autonomously (Hermes poller)
- Claude Code sessions leave the wiki better than they found it

## What counts as a "skill"

A skill is worth saving if:
- The task required a non-obvious multi-step approach
- The same type of task will likely recur
- A future agent finding this skill would save >5 min

A skill is NOT needed for:
- Trivial one-liners
- Steps already documented in an existing SKILL.md
- Pure data retrieval with no technique involved

## Format

Skills live in `pages/skills/` (for factory SKILL.md files) or in `pages/tools/` (for helper scripts and tools).

For a success worth capturing as a SKILL.md:

```markdown
---
type: skill
id: [slug]
title: "[What this skill does]"
tags: [skill, domain, ...]
date: YYYY-MM-DD
status: reviewed
---

# [Skill Name]

## When to use
[Conditions that trigger this skill]

## How to do it
[Step-by-step, non-obvious approach]

## Pitfalls
[What went wrong before / what to avoid]

## Verification
[How to confirm it worked]
```

## Enforcement

1. **Claude Code sessions:** At session end, review what worked. If any non-obvious solution was found, write a skill or update an existing one before writing the handoff.
2. **Factory tasks:** `factory-poller.py` on Air polls VPS task-results every 5 min. Hermes auto-extracts skills via `hermes chat -q`. No human action needed.
3. **LAW-015 for failures, LAW-017 for successes** — the pair ensures the knowledge base compounds in both directions.

## See also

- [[LAW-015-root-cause-evolution]] — every failure produces a LESSON
- [[HANDOFF-2026-04-14-session14]] — session where this law was codified
- `pages/tools/factory-poller.py` — automated skill extraction via Hermes (script ref, not a wiki page)
