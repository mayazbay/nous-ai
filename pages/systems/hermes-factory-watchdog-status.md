---
type: system
id: hermes-factory-watchdog-status
title: "Hermes Factory Watchdog Status"
last_updated: 2026-05-25T10:42:44.984122+05:00
status: not_done
tags: [hermes, factory, watchdog, openclaw, todoist, notion, github]
---

# Hermes Factory Watchdog Status

- Last run: `2026-05-25-104244`
- Overall: `not_done`

| Check | Status | Summary |
|---|---:|---|
| control_plane_recency | `done` | fresh age_s=2641 |
| openclaw_supervision | `done` | OpenClaw health endpoint green |
| factory_probe | `not_done` | factory probe not green: reds=1 |
| sync_failure_escalation | `done` | no repeated Todoist/Notion failures |
| human_owner_reminder | `done` | fresh age_s=3574 |
| github_failure_noise | `done` | known failed GitHub run already recorded: 26274555590 |
| model_bakeoff_freshness | `done` | fresh age_s=404279 |
