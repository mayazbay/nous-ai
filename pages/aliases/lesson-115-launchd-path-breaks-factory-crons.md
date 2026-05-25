---
type: alias
target: skills/factory-ops/skill
id: lesson-115-launchd-path-breaks-factory-crons
title: "LESSON-115 (alias) — launchd $PATH breaks factory crons"
tags: [alias, lesson-migration, rule-zero, factory-ops, infrastructure]
date: 2026-04-30
status: alias-redirect
related:
  - "[[factory-ops]]"
  - "[[infrastructure]]"
---

# LESSON-115 (alias) — launchd minimal `$PATH` breaks scripts

> **Migrated per RULE ZERO** — absorbed into [[factory-ops]] +
> [[infrastructure]] skills.

**Original takeaway:** macOS launchd uses minimal `$PATH` (no Homebrew, no
asdf). Factory crons silently lose `git`, `gh`, `node`. Always set
`EnvironmentVariables.PATH` explicitly in plist.

## See also
- [[factory-ops]]
- [[infrastructure]]
