---
type: law
id: LAW-009
title: "Self-Evolution — Agents Get Better Every Cycle"
status: permanent
enforcement: code-partial
tags: [evolution, kpi, learning, error-lessons]
related: [LAW-001, AMD-003]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-009: SELF-EVOLUTION — AGENTS GET BETTER EVERY CYCLE
Status: PERMANENT
Enforcement: Error lesson storage in memory_manager.py
Updated: 2026-04-06

## The Law
Every failure feeds the learning loop. Every success gets documented.

## The Loop
1. Task fails → root cause analysis
2. Root cause → new lesson in wiki
3. Lesson → validator checks for it in future cycles
4. Next time same pattern appears → auto-caught

## KPI tracking
- Log every cycle: tasks completed, tasks failed, cost, time
- Compare cycle N to cycle N-1
- If getting worse → investigate why
- If getting better → document what changed

## Rules
- Every error → store_error_lesson() → wiki + Mem0
- Every success pattern → document in wiki
- Weekly: review if lessons are being followed

## See also
- [[AMENDMENT-003-memory-sync|AMD-003]]
- [[LAW-001-evolution|LAW-001]]
