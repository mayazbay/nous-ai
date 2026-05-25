---
type: law
id: LAW-010
title: "Escalation-Only — Madi Out of the Loop"
status: permanent
enforcement: cron
tags: [telegram, daily-summary, anti-spam, escalation]
related: [LAW-007, AMD-001]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-010: ESCALATION-ONLY — MADI OUT OF THE LOOP
Status: PERMANENT
Enforcement: Cron job daily_summary.py at 18:00 UTC (23:00 Almaty). Dedup in telegram_bot.py.
Updated: 2026-04-06

## The Law
Madi does NOT get bothered with every detail. ONE daily summary at 23:00 Almaty time.

## Rules
- Factory runs autonomously 24/7
- Problems → CEO handles, NOT Madi
- Daily summary at 23:00 Almaty (18:00 UTC) via Telegram
- Summary in RUSSIAN
- Only PRESIDENTIAL decisions escalate to Madi:
  - Money decisions
  - Contract decisions
  - Government submissions
  - Architecture changes that affect revenue

## Anti-spam
- Same message within 30 min → DONT SEND AGAIN
- "No pending tasks" → NEVER send to Madi (CEO must create tasks)
- Only send when there is actual news

## Code enforcement (ACTIVE)
- Cron job daily_summary.py BUILT and active at 18:00 UTC
- Message dedup BUILT in telegram_bot.py (30 min window, md5 hash)

## See also
- [[AMENDMENT-001-circuit-breaker|AMD-001]]
- [[LAW-007-hub-and-spoke|LAW-007]]
