---
type: alias
target: skills/command-center/skill
id: lesson-086-polling-dedup-save-state-before-slow-handler
title: "LESSON-086 (alias) — Polling dedup: save state BEFORE slow handler"
tags: [alias, lesson-migration, rule-zero, command-center, agent-quality]
date: 2026-04-30
status: alias-redirect
related:
  - "[[command-center]]"
  - "[[agent-quality]]"
---

# LESSON-086 (alias) — Polling save-state-first pattern

> **Migrated per RULE ZERO** — absorbed into [[command-center]] +
> [[agent-quality]] skills.

**Original takeaway:** In polling loops (e.g. `telegram_poll.py`), save the
last-processed offset BEFORE invoking the slow handler. Otherwise crashes
re-process the same message and produce duplicate side-effects.

## See also
- [[command-center]]
- [[agent-quality]]
