---
type: alias
target: skills/infrastructure/skill
id: lesson-094-docker-wiki-mount-node-user-traversal
title: "LESSON-094 (alias) — Docker wiki mount: node user traversal failure"
tags: [alias, lesson-migration, rule-zero, infrastructure]
date: 2026-04-30
status: alias-redirect
related:
  - "[[infrastructure]]"
---

# LESSON-094 (alias) — Docker bind-mount permission discipline

> **Migrated per RULE ZERO** — absorbed into [[infrastructure]] skill.

**Original takeaway:** OpenClaw container's `node` user couldn't traverse
host-owned wiki dirs. Fix: `chmod -R o+rX ~/nous-agaas/wiki` (other-readable,
other-traverse on dirs). Mount permissions ≠ file access for non-root
container users.

## See also
- [[infrastructure]]
