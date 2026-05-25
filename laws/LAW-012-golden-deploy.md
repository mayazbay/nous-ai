---
type: law
id: LAW-012
title: "Golden Deploy — All Checks Pass Before Production"
status: permanent
enforcement: code-gate
tags: [deploy, rollback, smoke-test, build, tests]
related: [LAW-003, AMD-002]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-012: GOLDEN DEPLOY — ALL CHECKS PASS BEFORE PRODUCTION
Status: PERMANENT
Enforcement: Code gates in graph.py deploy_node
Updated: 2026-04-06

## The Law
No code reaches production unless ALL gates pass:
1. Pre-merge pytest baseline captured
2. Code merged to main
3. Post-merge pytest — no new failures vs baseline
4. npm build succeeds (returncode 0)
5. Vercel deploy completes
6. Smoke test passes (HTTP 200 + content > 200 bytes + API health)

## Rollback triggers (automatic)
- Post-merge test regression → rollback + task failed
- Build failure → rollback + task failed
- Smoke test failure → rollback + task failed

## What smoke test checks
- HTTP 200 from site URL
- Response body > 500 bytes (was 200, check current)
- API health endpoint returns "ok"

## Code enforcement
All gates are hardwired in graph.py deploy_node. Cannot be bypassed by prompts.

## See also
- [[AMENDMENT-002-post-deploy-check|AMD-002]]
- [[LAW-003-continuous-audit|LAW-003]]
