---
type: law
id: LAW-004
title: "5 Commandments for Agent Deployments"
status: permanent
enforcement: code-gate
tags: [scope, observability, audit, data-quality, throughput]
related: [LAW-003, LAW-007, LAW-012]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-004: 5 COMMANDMENTS FOR AGENT DEPLOYMENTS
Status: PERMANENT
Enforcement: Scope checks in graph.py (files_to_modify), observability (smoke test)
Updated: 2026-04-06

## The 5 Commandments (IN ORDER)

### 1. AUDIT BEFORE AUTOMATE
Map ACTUAL process, not idealized. Include edge cases, undocumented exceptions.
- OUR MISTAKE: Built factory without auditing real camera workflow → 101 bugs
- OUR FIX: LAW-003 continuous audit

### 2. FIX DATA FIRST
Single source of truth, strict schemas, validation BEFORE giving agent access.
- OUR MISTAKE: MRGN IDs vs IP addresses — no mapping, mismatched reports
- OUR FIX: transforms.ts, camera_registry.json, single DB query

### 3. REDESIGN FOR THROUGHPUT
If agent multiplies production, humans get overwhelmed with reviews.
- OUR MISTAKE: CEO marked 97 tasks done — nobody reviewed, all reverted
- OUR FIX: Auditor role (LAW-003), Validator enforces lessons

### 4. OBSERVABILITY DAY ONE
Independent verification. NEVER trust agent self-reporting.
- OUR MISTAKE: Factory said "done" but site was black screen
- OUR FIX: Post-deploy content check, continuous auditor

### 5. SCOPE AUTHORITY
Clear guardrails, strict permissions. No dangerously skipping.
- OUR MISTAKE: Coder edited wrong directory, killall killed production
- OUR FIX: files_to_modify enforcement, specific PIDs only

## Key principle
Agent = high-speed rail on HARDWIRED TRACKS. Not off-road vehicle guessing.
- Deterministic workflows (graph.py) = tracks
- LLM decisions (what to code) = agent strength
- NEVER let agent decide deployment process
- NEVER trust agent self-reporting success

## See also
- [[cameras|Camera Network]]
- [[LAW-003-continuous-audit|LAW-003]]
- [[LAW-007-hub-and-spoke|LAW-007]]
- [[LAW-012-golden-deploy|LAW-012]]
