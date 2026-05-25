---
type: alias
target: skills/infrastructure/skill
id: lesson-090-litellm-native-vs-docker-macos
title: "LESSON-090 (alias) — LiteLLM native vs Docker on macOS"
tags: [alias, lesson-migration, rule-zero, infrastructure, litellm]
date: 2026-04-30
status: alias-redirect
related:
  - "[[infrastructure]]"
---

# LESSON-090 (alias) — LiteLLM native vs Docker on macOS

> **Migrated per RULE ZERO** — absorbed into [[infrastructure]] skill.

**Original takeaway:** On Air-side macOS, run LiteLLM as a native launchd
service (com.nous.litellm), NOT inside Docker. Docker on Mac adds VM overhead
and TLS-cert complexity that native install avoids.

## See also
- [[infrastructure]]
