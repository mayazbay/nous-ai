---
type: system
id: SYS-ERAP
title: "ERAP Pipeline Technical"
tags: [system, erap, pipeline, smartbridge]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# ERAP Pipeline

**Flow:** APK cameras → SERVER (our erap/ modules) → SmartBridge gateway → ERAP

## Pipeline Modules (erap/)
- isapi_listener.py — Receives ANPR events from Hikvision cameras
- event_parser.py — Parses plate numbers, speeds, timestamps
- violation_detector.py — Filters violations based on speed limits per location
- camera_registry.py — GPS, speed limits, certificates for each camera
- koap_codes.py — KoAP violation articles and fine calculations
- gost_signer.py — GOST 34.10-2015 digital signatures (KalkanCrypt)
- smartbridge_client.py — SOAP/REST client for SmartBridge
- erap_submitter.py — Assembles and submits ERAP packets
- submission_queue.py — Queue management
- audit_logger.py — Audit trail logging

## SmartBridge Status
- Gateway: CONFIRMED WORKING (18 requests April 3, 2026)
- Format change: Old (bip.bee.kz/SendMessageResponse with SCSS001) → New (otgroup.kz/onEventResponse with just return=true)
- Test environment: Apply Monday via sb.egov.kz

## GOST Requirements
- GOST 34.10-2018 for digital signatures
- GOST 34.11-2018 (Streebog) for hashing
- Must use KalkanCrypt or pygost — standard RSA/ECDSA rejected

## Blockers
- ERAP data format specs needed from Dias
- ECP certificate chain: OID (Aidana) → ECP (Roza) → KalkanCrypt
- 109 APK metrology certificates expired since Dec 2024

See also: [SmartBridge](smartbridge.md), [GOST Crypto](gost.md), [KoAP Articles](../legal/koap.md)

## See also
- [[cameras|Camera Network]]
- [[koap_speed_fines|KoAP]]
- [[isapi-concept|ISAPI Protocol]]
