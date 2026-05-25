---
type: alias
target: skills/infrastructure/skill
id: lesson-091-docker-image-transfer-scp-not-pipe
title: "LESSON-091 (alias) — Docker image transfer: scp, not stdin pipe"
tags: [alias, lesson-migration, rule-zero, infrastructure]
date: 2026-04-30
status: alias-redirect
related:
  - "[[infrastructure]]"
---

# LESSON-091 (alias) — Docker image cross-host transfer

> **Migrated per RULE ZERO** — absorbed into [[infrastructure]] skill.

**Original takeaway:** When moving Docker images between hosts, use
`docker save | gzip | ssh ... 'gunzip | docker load'` carefully OR scp the
.tar then load. Direct stdin pipe with sudo can lose data on TTY conflicts.

## See also
- [[infrastructure]]
