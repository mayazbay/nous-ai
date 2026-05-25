---
type: system
id: SYS-NOUS-AGENT-HEARTBEAT
title: "Nous Agent HEARTBEAT.md — Cron Catalog (Layer 4)"
tags: [system, heartbeat, cron, launchd, openclaw, layer-4, nous-agent, 2026-04-15]
date: 2026-04-15
source_count: 0
status: active
last_updated: 2026-04-15
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, SYS-NOUS-AGENT-SOUL, SYS-NOUS-AGENT-PROCEDURES]
---

# Nous Agent — HEARTBEAT.md (cron catalog)

Layer 4. **Not loaded in hot path** — reference doc for human audit + agent introspection. Actual scheduling is in macOS launchd on Air. This file documents what runs when and why.

Auto-rsynced: `Nous/pages/systems/nous-agent-heartbeat.md` → `/opt/nous-agaas/agents/HEARTBEAT.md`.

## Scheduled jobs on Air

| launchd label | When | Script | Purpose |
|---|---|---|---|
| `com.nous.litellm` | always-on | LiteLLM server | Model router (glm-5.1 → glm-4.5-flash → sonnet) |
| `com.nous.telegram-poll` | every 60s | `telegram_poll.py` | `@nousAGaaSbot` → factory routing |
| `com.nous.wiki-sync` | every 5 min | `sync_obsidian_wiki.sh` | 3-way git sync (Mac ↔ VPS ↔ Air) |
| `com.nous.auto-checkpoint` | 8×/day smart-skip | `auto_checkpoint.py` | HANDOFF-AUTO-*.md writes |
| `com.nous.session-rotate` | 03:45 daily | session cleanup | Prevent OpenClaw session accumulation (LESSON-101) |
| `com.nous.morning-brief` | 04:00 daily | brief generator | Overnight state diff alerts |
| `com.nous.nightly-update` | 03:00 daily | update check | Notify on new upstream versions |
| `com.nous.nightly-audit` | 04:00 daily | health + e2e | Full stack check |
| `com.nous.morning-update-apply` | 05:07 daily | selective upgrade | Apply approved updates |
| `com.nous.light-probe` | every 15 min | factory liveness | Passive monitoring |
| `com.nous.staleness` | hourly | staleness check | Flag stale facts |
| `com.nous.log-rotate` | Sun 03:00 | log rotation | Prevent disk fill |
| `com.nous.wiki-to-runtime-rsync` *(NEW)* | WatchPath on wiki skills | `wiki-to-runtime-rsync.sh` | Close manual Rule-6 loop |
| `com.nous.lesson-absorption` *(NEW)* | every 6h | `lesson-absorption-watcher.py` | Flag unabsorbed lessons ≥7d |
| `com.nous.dream-cycle` *(NEW)* | 03:15 daily | `dream-cycle.py` (part of ghost-debt-dashboard.py) | Read-only nightly compilation |

## Scheduled jobs on VPS

| cron | When | Script | Purpose |
|---|---|---|---|
| gbrain autopilot | every 5 min | `gbrain autopilot` | sync + embed + backlinks |
| legacy skill extractor | every 10 min | `vps_skill_extractor.py` | Draft skills from task-results → `pages/skills/extracted/` |

## Ordering constraints

- Dream cycle (03:15) runs BEFORE session-rotate (03:45) so it analyzes the prior day's sessions before they're cleared.
- Morning-brief (04:00) runs AFTER dream-cycle so it can reference the proposals.
- Morning-update-apply (05:07) runs AFTER nightly-update-check so only approved updates land.
- Lesson-absorption is interval-based (6h), not tied to specific time — flags a ghost regardless of when it was written.

## What HEARTBEAT does NOT do

- Mutate skills directly (anti-slop)
- Send Telegram messages autonomously (LAW-010 escalation-only)
- Deploy code
- Run LLM in loops (LESSON-054 — $6/day empty CEO loop burned)

## If a job fails

1. `launchctl print gui/$UID/<label>` — check exit code
2. `~/Library/Logs/nous-agaas/<label>.stdout` + `.stderr`
3. If 3 consecutive failures → nightly-audit raises alert → Telegram to Madi
4. Root-cause → fix → absorb into the `infrastructure` skill

---

## Timeline

- **2026-04-15** | v1.0 written per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]. Documents existing launchd jobs + adds 3 new ones (wiki-to-runtime-rsync, lesson-absorption, dream-cycle) to be activated in Phase P5.

## See also

- [[nous-agent-soul]] — Layer 1
- [[nous-agent-user]] — Layer 1b user model
- [[nous-agent-procedures]] — Layer 2
- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[infrastructure]] — skill covering launchd + cron topology
