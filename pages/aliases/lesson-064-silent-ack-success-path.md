---
type: alias
target: skills/agent-quality/skill
id: lesson-064-silent-ack-success-path
title: "LESSON-064 (alias) — Silent ACK success path (you cannot audit what you cannot log)"
tags: [alias, lesson-migration, rule-zero, agent-quality, command-center]
date: 2026-04-30
status: alias-redirect
related:
  - "[[agent-quality]]"
  - "[[command-center]]"
---

# LESSON-064 (alias) — Silent success path is unauditable

> **Migrated per RULE ZERO** — absorbed into [[agent-quality]] (AP-7) +
> [[command-center]] skills.

**Original takeaway:** `telegram_poll.py` `send_ack` had silent success path —
"you cannot audit what you cannot log." Fixed with explicit success/failure
logging + plain-send fallback.

## See also
- [[agent-quality]]
- [[command-center]]
