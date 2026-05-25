---
type: law
id: LAW-003
title: "Continuous Audit"
status: permanent
enforcement: code-gate
tags: [validator, audit, banned-patterns, done-definition]
related: [LAW-008, LAW-012, AMD-002]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-003: CONTINUOUS AUDIT
Status: PERMANENT
Enforcement: Validator V2 + hardwired banned pattern checks in graph.py
Updated: 2026-04-06

## The Law
One agent audits NON-STOP. Every page, every button, every number. Flags everything wrong. Other agents fix flags. Auditor re-checks. ONLY when auditor says zero issues = actually done.

## What "DONE" means
DONE = Madi opens satory.nousagaas.com, clicks every button, sees:
- Real camera data (243 cameras, IPs, GPS, status)
- Real violations (plates, speeds, KoAP fines)
- Real map with VKO coordinates (49.9N, 82.6E)
- Every page loads. Every button works. Every number is real.

NOT DONE:
- "Code merged" — NOT DONE
- "Tests passed" — NOT DONE
- "Deployed to Vercel" — NOT DONE
- "Smoke test passed" — NOT DONE
- "CEO marked done" — NOT DONE (CEO marked 97 fake-done tasks)

## Validator content checks (10 checks)
1. File exists and non-empty
2. No syntax errors
3. No banned patterns: Math.random, picsum.photos, setTimeout, hardcoded 29086
4. Imports resolve
5. No fake data
6. API field names match transforms.ts
7. No duplicate SWR keys with different fetchers
8. Build succeeds
9. Bundle hash changes after deploy
10. Real data in API response (curl and verify)

## Code enforcement
- graph.py: banned patterns checked in Python, not just by Gemini prompt
- If banned pattern found → auto-BLOCK regardless of Gemini approval
- Hardcoded safety > prompt instructions

## See also
- [[AMENDMENT-002-post-deploy-check|AMD-002]]
- [[cameras|Camera Network]]
- [[koap_speed_fines|KoAP]]
- [[LAW-008-anti-hallucination|LAW-008]]
- [[LAW-012-golden-deploy|LAW-012]]
