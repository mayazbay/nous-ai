---
type: amendment
id: AMD-001
title: "Circuit Breaker"
status: permanent
enforcement: code-gate
tags: [circuit-breaker, failure, auto-pause, self-healing]
related: [LAW-014, LAW-012]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# AMENDMENT 1: CIRCUIT BREAKER
Status: PERMANENT. ENFORCED in graph.py.
Updated: 2026-04-06

## The Rule
- 3 DIFFERENT tasks fail → factory PAUSES + Telegram alert to Madi
- Same task fails 3x → SKIP to next (mark as "blocked")
- Fully automated. Madi can sleep. Factory self-manages.

## Why
Overnight money burning loops ($40+ wasted). Factory kept retrying the same broken task forever.

## Code enforcement
graph.py: MAX_RETRIES = 3. After 3 attempts → task marked "failed" → cycle ends.
store_error_lesson() called so agents learn from the failure.

## See also
- [[LAW-012-golden-deploy|LAW-012]]
- [[LAW-014-watchdog|LAW-014]]
