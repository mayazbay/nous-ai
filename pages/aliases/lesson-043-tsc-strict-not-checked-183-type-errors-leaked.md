---
type: alias
target: skills/agent-quality/skill
id: lesson-043-tsc-strict-not-checked-183-type-errors-leaked
title: "LESSON-043 (alias) — TSC strict not checked, 183 errors leaked"
tags: [alias, lesson-migration, rule-zero, agent-quality, website-deploy]
date: 2026-04-30
status: alias-redirect
related:
  - "[[agent-quality]]"
  - "[[website-deploy]]"
---

# LESSON-043 (alias) — Always run tsc --noEmit before declaring done

> **Migrated per RULE ZERO** — absorbed into [[agent-quality]] (AP-18) +
> [[website-deploy]] skills.

**Original takeaway:** TypeScript strict mode wasn't being checked; 183 type
errors leaked to deploy. Mandatory: `tsc --noEmit` before any TypeScript
project is declared done.

## See also
- [[agent-quality]]
- [[website-deploy]]
