---
type: concept
id: CONCEPT-ERAP
title: "ERAP — Government Violation Processing System"
tags: [concept, erap, government, violations, fines]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# ERAP (ЕРАП) — Government Violation Processing System

Government system that receives traffic violation data and issues fines automatically.

## How it works
Camera detects speeding → our system packages evidence (2 photos + video + GPS) → SmartBridge gateway → Spectra ITS → ERAP → fine issued to vehicle owner

## How we use it
- Pipeline: ISAPI listener → event parser → violation detector → GOST signer → SmartBridge client → ERAP submitter
- Requires ECP digital signature (GOST 34.10-2018)
- Requires 30-day evidence retention (by law)

## Key facts
- Not yet connected (need VPN + ECP certificate)
- SmartBridge gateway confirmed working (April 3)
- 3-week timeline via Spectra ITS platform

## See also
- [[cameras|Camera Network]]
- [[koap_speed_fines|KoAP]]
- [[LAW-002-autofine|LAW-002]]
