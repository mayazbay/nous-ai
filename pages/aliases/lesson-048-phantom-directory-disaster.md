---
type: alias
target: skills/factory-ops/skill
id: lesson-048-phantom-directory-disaster
title: "LESSON-048 (alias) — Phantom directory: factory wrote to nested INNER never deployed"
tags: [alias, lesson-migration, rule-zero, factory-ops, website-deploy]
date: 2026-04-30
status: alias-redirect
related:
  - "[[factory-ops]]"
  - "[[website-deploy]]"
---

# LESSON-048 (alias) — Phantom inner directory wrote-but-never-deployed

> **Migrated per RULE ZERO** — absorbed into [[factory-ops]] +
> [[website-deploy]] skills.

**Original takeaway:** `file_ops` double-join produced phantom INNER directory;
factory wrote files there, deploy never picked them up. Always verify file path
matches actual deploy source via `ls` parent dir.

## See also
- [[factory-ops]]
- [[website-deploy]]
