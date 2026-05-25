---
type: amendment
id: AMD-002
title: "Post-Deploy Content Check"
status: permanent
enforcement: code-gate
tags: [deploy, content-check, api-verification, playwright, bundle]
related: [LAW-012, LAW-003]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# AMENDMENT 2: POST-DEPLOY CONTENT CHECK
Status: PERMANENT. ENFORCED (8 API endpoints + JS bundle + Playwright).
Updated: 2026-04-06

## The Rule
After every deploy, verify CONTENT not just HTTP 200:
1. curl HTML → check JS bundle filename changed
2. curl JS bundle → grep for expected string literals (camera_type)
3. curl every API proxy route → verify real JSON
4. Check bundle size > 500KB (not empty)

## Current enforcement (ALL ACTIVE in graph.py deploy_node)
- 8 API endpoints checked: cameras, health, stats, violations, erap, camera-registry, system-events, tracking
- JS bundle: hash extracted from HTML, size > 500KB, contains "camera_type"
- Playwright: headless browser renders page, checks for React errors, SATORY text
- If ANY check fails → ROLLBACK automatically

## Why
Deployed 3 times with old bundle cached. Said "deployed" with broken site.

## See also
- [[cameras|Camera Network]]
- [[erap|ERAP Pipeline]]
- [[LAW-003-continuous-audit|LAW-003]]
- [[LAW-012-golden-deploy|LAW-012]]
