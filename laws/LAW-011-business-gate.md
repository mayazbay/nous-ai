---
type: law
id: LAW-011
title: "Business Gate — Every Task Must Have Business Outcome"
status: permanent
enforcement: code-gate
tags: [business, demo-ready, revenue, risk, deploy-gate]
related: ["LAW-006"]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-011: BUSINESS GATE — EVERY TASK MUST HAVE BUSINESS OUTCOME
Status: PERMANENT
Enforcement: HARD BLOCK in graph.py deploy_node. Business outcome keywords required.
Updated: 2026-04-06

## The Law
Every task must be tagged as ONE of:
- (a) Demo-Ready — improves what Satory/police will see
- (b) Revenue Impact — directly affects money (fines, contracts)
- (c) Risk Reduction — prevents data loss, security issues, outages

## Rules
- Pure "cleanup" or "refactor" tasks → REJECTED unless they serve a/b/c
- CEO must tag every task with business outcome
- Tasks without business outcome → blocked

## Why
Factory wasted 97 cycles on internal tasks that didnt move the product forward. CSS optimization doesnt matter if police cant see real violations.

## Code enforcement (ACTIVE)
graph.py deploy_node line 460: keyword check for demo-ready/revenue/risk-reduction. HARD BLOCK if missing.

## See also
- [[LAW-006-task-equals-requirement|LAW-006]]
