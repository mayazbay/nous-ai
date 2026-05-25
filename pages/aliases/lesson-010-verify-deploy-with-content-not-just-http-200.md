---
type: alias
target: skills/website-deploy/skill
id: lesson-010-verify-deploy-with-content-not-just-http-200
title: "LESSON-010 (alias) — Verify deploy with CONTENT, not just HTTP 200"
tags: [alias, lesson-migration, rule-zero, website-deploy, evidence-verification]
date: 2026-04-30
status: alias-redirect
related:
  - "[[website-deploy]]"
  - "[[evidence-verification]]"
---

# LESSON-010 (alias) — HTTP 200 ≠ deploy success

> **Migrated per RULE ZERO** — absorbed into [[website-deploy]] +
> [[evidence-verification]] skills.

**Original takeaway:** Deploy verification via HTTP status alone misses
broken pages serving 200 with empty/error content. Always grep response
body for an expected fingerprint string.

## See also
- [[website-deploy]]
- [[evidence-verification]]
