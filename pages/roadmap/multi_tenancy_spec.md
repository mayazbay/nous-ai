---
type: roadmap
id: ROAD-MULTI
title: "Multi-tenancy Spec (Post-Demo)"
tags: [roadmap, multi-tenancy, scaling]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
status: reviewed
---
# Multi-Tenancy Implementation Spec (Gemini, April 5 2026)

## STATUS: BLUEPRINT — Do NOT implement until after Monday demo.

## Thread ID Format
tenant:{tenant_id}:project:{project_id}:session:{uuid}

## State Extension
Add to FactoryState: tenant_id, project_id, audit_log

## Checkpointer Migration
From SQLite to AsyncPostgresSaver with dynamic DSN (kz -> KZ host, else EU)
conversations table with RLS for tenant isolation

## New Node: validate_tenant (FIRST node after START)

## 7-Day Rollout starts day after demo
Day 0-1: Migration script + state extension
Day 2-3: Postgres + RLS + cycle loop refactor
Day 4-5: Mem0 namespaces + e2e test
Day 6-7: Observability + production cutover

## Factory Prompt (drop into task queue post-demo)
Implement full multi-tenancy in 12-node LangGraph factory. Extend state. Migrate checkpointer. Add RLS. Preserve all tasks and tests.

## See also
- [[LAW-005-obsidian-master|LAW-005]]
- [[LAW-006-task-equals-requirement|LAW-006]]
