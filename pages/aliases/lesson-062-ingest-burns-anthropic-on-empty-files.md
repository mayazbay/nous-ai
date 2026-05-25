---
type: alias
target: skills/factory-ops/skill
id: lesson-062-ingest-burns-anthropic-on-empty-files
title: "LESSON-062 (alias) — Ingest pipeline burns API on 0-byte files"
tags: [alias, lesson-migration, rule-zero, factory-ops]
date: 2026-04-30
status: alias-redirect
related:
  - "[[factory-ops]]"
---

# LESSON-062 (alias) — Empty file ingest burned $$$

> **Migrated per RULE ZERO** — absorbed into [[factory-ops]] skill.

**Original takeaway:** Empty file in `raw/pending/` burned ~440 wasted Anthropic
API calls in 7 hours. `ingest_pending.py` patched to skip 0-byte files.

## See also
- [[factory-ops]]
