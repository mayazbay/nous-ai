---
type: alias
target: skills/agent-quality/skill
id: lesson-049-session-key-username-vs-user
title: "LESSON-049 (alias) — session.get(username) silent fallback to system"
tags: [alias, lesson-migration, rule-zero, agent-quality]
date: 2026-04-30
status: alias-redirect
related:
  - "[[agent-quality]]"
---

# LESSON-049 (alias) — Silent session-key fallback to system

> **Migrated per RULE ZERO** — absorbed into [[agent-quality]] skill (AP-22).

**Original takeaway:** `session.get('username')` silently fell back to `system`
when key absent — wrong user attribution in logs/audit. Always test with a
real logged-in session, never rely on fallback defaults.

## See also
- [[agent-quality]]
