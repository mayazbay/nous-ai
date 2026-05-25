---
type: amendment
id: AMD-003
title: "Twice-Daily Wiki Sync"
status: permanent
enforcement: cron
tags: [sync, cron, wiki-integrity, mem0]
related: [LAW-005, LAW-001]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# AMENDMENT 3: WIKI SYNC
Status: PERMANENT. ENFORCED via cron (9AM+6PM Almaty).
Updated: 2026-04-06

## The Rule
- Cron job runs twice daily (9 AM + 6 PM Almaty = 4:00 + 13:00 UTC)
- Cleans stale Mem0 entries
- Verifies all laws present in wiki
- Flags contradictions between wiki and Mem0
- Reports wiki entry count

## Current status
BUILT April 6 2026. Cron: 0 4,13 * * * memory_sync.py

## Why
Mem0 pollution — 288 cycle reports/day drowning real lessons.
Wiki and Mem0 diverged silently. Nobody noticed until agents hallucinated.

## See also
- [[LAW-001-evolution|LAW-001]]
- [[LAW-005-obsidian-master|LAW-005]]
