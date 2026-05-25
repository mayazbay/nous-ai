---
type: law
id: LAW-006
title: "Every Task Must Trace to a Requirement"
status: permanent
enforcement: code-gate
tags: [tasks, requirements, vms, deploy-gate]
related: ["LAW-011"]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-006: EVERY TASK = A REQUIREMENT
Status: PERMANENT
Enforcement: HARD BLOCK in graph.py deploy_node. REQ-xxx regex required.
Updated: 2026-04-06

## The Law
Every task must trace to a real requirement from:
- 89 VMS requirements (wiki/pages/specs/cerebro_bdl_vms_requirements.md)
- ERAP requirements (wiki/pages/specs/erap_requirements.md)
- BDL features (wiki/pages/specs/bdl_features.md)
- CEO Madi direct instruction

## Rules
- NO task without a requirement link
- NO "cleanup" or "refactor" tasks unless they fix a requirement
- CEO reads requirements at cycle start and creates tasks FROM them
- If task has no requirement → REJECT

## Why
Previous factory created 97 tasks that were all reverted. Many were invented busywork with no real requirement behind them. Agent generated tasks like "optimize CSS" when the actual need was "show real camera data."

## Code enforcement (ACTIVE)
graph.py deploy_node line 455: re.search(r"REQ-\d{1,3}") blocks deploy if no REQ-xxx found.

## See also
- [[cameras|Camera Network]]
- [[erap|ERAP Pipeline]]
- [[LAW-011-business-gate|LAW-011]]
- [[cerebro_bdl_vms_requirements|VMS Requirements]]
