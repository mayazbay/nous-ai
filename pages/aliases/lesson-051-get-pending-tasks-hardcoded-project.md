---
type: alias
target: skills/factory-ops/skill
id: lesson-051-get-pending-tasks-hardcoded-project
title: "LESSON-051 (alias) — get_pending_tasks hardcoded project filter"
tags: [alias, lesson-migration, rule-zero, factory-ops]
date: 2026-04-30
status: alias-redirect
related:
  - "[[factory-ops]]"
---

# LESSON-051 (alias) — Hardcoded project filter caused factory idle

> **Migrated per RULE ZERO** — absorbed into [[factory-ops]] skill.

**Original takeaway:** Factory idle 10 cycles because `get_pending_tasks`
hardcoded `project=CEREBRO`; CEREBRO project tasks were invisible. Never
hardcode project filters in queue-readers.

## See also
- [[factory-ops]]
