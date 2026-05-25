---
type: alias
target: skills/website-deploy/skill
id: lesson-069-vercel-rollback-doesnt-move-custom-domains
title: "LESSON-069 (alias) — Vercel rollback doesn't move custom domains"
tags: [alias, lesson-migration, rule-zero, vercel, deploy]
date: 2026-04-30
status: alias-redirect
related:
  - "[[website-deploy]]"
  - "[[LAW-016-pre-send-fact-check]]"
---

# LESSON-069 (alias) — Vercel rollback doesn't move custom domains

> **Migrated per RULE ZERO** — this LESSON was absorbed into [[website-deploy]] skill.
> The original learning lives there as an Anti-Pattern; this alias preserves
> historical link resolution for handoffs and audits that referenced the legacy
> LESSON-069 file.

**Original takeaway:** `vercel rollback` only updates the project's default
`<project>.vercel.app` subdomain. For production custom domains like
`satory.nousagaas.com`, ALWAYS use `vercel alias set <deploy-url> <custom-domain>`.

**Source skill:** [[website-deploy]] (production deploy doctrine)
**Hard-rule cross-ref:** [[LAW-016-pre-send-fact-check]] (golden deploy lock)

## See also
- [[website-deploy]]
