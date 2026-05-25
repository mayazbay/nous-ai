---
type: alias
target: skills/agent-quality/skill
id: lesson-109-iso-timestamp-string-compare-false-positive
title: "LESSON-109 (alias) — ISO timestamp string-compare false positive"
tags: [alias, lesson-migration, rule-zero, agent-quality, evidence-verification]
date: 2026-04-30
status: alias-redirect
related:
  - "[[agent-quality]]"
  - "[[evidence-verification]]"
---

# LESSON-109 (alias) — Compare ISO timestamps as datetimes, not strings

> **Migrated per RULE ZERO** — absorbed into [[agent-quality]] +
> [[evidence-verification]] skills.

**Original takeaway:** String-comparing ISO timestamps with TZ offsets
silently produces wrong order. Parse to datetime first, compare as
datetime.

## See also
- [[agent-quality]]
- [[evidence-verification]]
