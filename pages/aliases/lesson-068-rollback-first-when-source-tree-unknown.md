---
type: alias
target: skills/website-deploy/skill
id: lesson-068-rollback-first-when-source-tree-unknown
title: "LESSON-068 (alias) — Rollback first when source tree unknown"
tags: [alias, lesson-migration, rule-zero, website-deploy, evidence-verification]
date: 2026-04-30
status: alias-redirect
related:
  - "[[website-deploy]]"
  - "[[evidence-verification]]"
---

# LESSON-068 (alias) — Rollback-first principle

> **Migrated per RULE ZERO** — absorbed into [[website-deploy]] +
> [[evidence-verification]] skills. **CORRECTED 2026-04-09** — see
> [[lesson-069-vercel-rollback-doesnt-move-custom-domains]] for the real
> root cause that this lesson initially misdiagnosed.

**Original takeaway (six rules):** When production breaks and source tree is
unknown — (1) rollback first via fingerprint-matched prior deploy,
(2) fingerprint via `vercel inspect` (bundle size + build outputs),
(3) verify HTML body never HTTP status alone,
(4) test backend integration after rollback,
(5) retain broken deploy ID for forensics,
(6) `ls` parent dir before declaring source unknown.

## See also
- [[website-deploy]]
- [[evidence-verification]]
- [[lesson-069-vercel-rollback-doesnt-move-custom-domains]]
