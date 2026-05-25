---
type: alias
target: skills/air-ssh-access/skill
id: lesson-089-macos-ssh-tailscale-bypass
title: "LESSON-089 (alias) — macOS SSH bypass for Tailscale stability"
tags: [alias, lesson-migration, rule-zero, air-ssh-access, tailscale-stability]
date: 2026-04-30
status: alias-redirect
related:
  - "[[air-ssh-access]]"
  - "[[tailscale-stability]]"
---

# LESSON-089 (alias) — macOS SSH/Tailscale bypass pattern

> **Migrated per RULE ZERO** — absorbed into [[air-ssh-access]] +
> [[tailscale-stability]] skills.

**Original takeaway:** When Tailscale routing is unstable on macOS, bypass via
direct LAN IP + ssh-config Host alias. Document the fallback path so agents
on any host can reach Air without depending on Tailscale being healthy.

## See also
- [[air-ssh-access]]
- [[tailscale-stability]]
