---
type: law
id: LAW-014
title: "Watchdog — Independent Monitor"
status: permanent
enforcement: code-gate
tags: [watchdog, crash-recovery, self-healing, systemd]
related: ["AMD-001"]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-014: WATCHDOG
Status: PERMANENT. ENFORCED via watchdog.py + systemd.
Updated: 2026-04-06

## The Law
Independent watchdog monitors factory health. If factory crashes, watchdog diagnoses and fixes automatically. No human intervention needed.

## How it works
1. watchdog.py runs as cron every 5 min
2. Checks: is nous-agaas systemd service active?
3. Checks: has a cycle run in the last 15 min? (stuck detection)
4. If down: restart via systemctl
5. If 5+ restarts fail: CEO (Opus) diagnoses from crash log
6. If CEO fix fails: Researcher investigates
7. Watchdog reads PERMANENT-RULES.md + lessons for context

## Scope restrictions (added April 6)
- Can only write to /root/nous-agaas/ files
- CANNOT modify config.py, .env, or watchdog.py itself
- Rules injected into diagnosis prompt

## Code
- /root/nous-agaas/watchdog.py
- Cron: */5 * * * * task_watchdog.py

## See also
- [[AMENDMENT-001-circuit-breaker|AMD-001]]
