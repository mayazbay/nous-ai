---
type: alias
target: skills/website-deploy/skill
id: lesson-067-next-build-passes-doesnt-mean-runtime-works
title: "LESSON-067 (alias) — next build passing ≠ runtime works"
tags: [alias, lesson-migration, rule-zero, website-deploy, evidence-verification]
date: 2026-04-30
status: alias-redirect
related:
  - "[[website-deploy]]"
  - "[[evidence-verification]]"
---

# LESSON-067 (alias) — `next build` passing is NOT sufficient

> **Migrated per RULE ZERO** — absorbed into [[website-deploy]] +
> [[evidence-verification]] skills. Alias preserves historical link resolution.

**Original takeaway:** Client-side hydration crashes are invisible to the build
step. `next build` green is necessary but NOT sufficient. Always run `next dev`
+ browser console smoke + Vercel preview deploy before `--prod`.

## See also
- [[website-deploy]]
- [[evidence-verification]]
