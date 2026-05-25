---
type: alias
target: skills/factory-ops/skill
id: lesson-055-budget-hit-retry-loop
title: "LESSON-055 (alias) — Budget gate retry-loop without sleep"
tags: [alias, lesson-migration, rule-zero, factory-ops]
date: 2026-04-30
status: alias-redirect
related:
  - "[[factory-ops]]"
---

# LESSON-055 (alias) — Budget gate must sleep on rejection

> **Migrated per RULE ZERO** — absorbed into [[factory-ops]] skill.

**Original takeaway:** Budget gate returned but didn't sleep — burned API
calls in tight retry loop. Fix: exponential backoff on budget-rejection
return path.

## See also
- [[factory-ops]]
