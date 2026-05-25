---
type: spec
id: SPEC-ERAP-GAP-2026-04-16
title: "ERAP Pipeline Technical Gap Assessment — honest status 2026-04-16"
tags: [spec, erap, gap-analysis, smartbridge, bdl, gvt, strategy]
date: 2026-04-16
status: reviewed
last_updated: 2026-04-16
priority: p0
related: [source-madi-rosa-gvt-strategy-2026-04-16, global-vision-technologies, smartbridge-soap-client, camera-management, bdl-replacement-state-2026-04-07]
---

# ERAP Pipeline — Technical Gap Assessment (2026-04-16)

> Honest status: what we have, what works, what is missing, what GVT could fill.

## Executive summary

**Pipeline is ~65% built.** The camera layer (ISAPI listener + event parser + violation detector + camera registry) is production-tested with 154K real events in DB. The SmartBridge SOAP client is coded (853 lines) and passes 26 tests — but in MOCK MODE only. We have never sent a single real packet through SmartBridge to ERAP. Three critical blockers remain.

## What we HAVE (working, tested)

| Component | File | Lines | Tests | Status |
|-----------|------|-------|-------|--------|
| ISAPI event listener | isapi_listener.py | 10,896 | Part of integration | PROD — received 154,516 real events |
| Event XML parser | event_parser.py | 12,019 | Part of integration | PROD — parses Hikvision multipart |
| Camera registry | camera_registry.py | 13,225 | 12 tests pass | PROD — 243 cameras registered |
| Camera health monitor | camera_monitor.py | 7,662 | — | PROD — runs every 5 min |
| Hikvision ISAPI client | hikvision_isapi.py | 18,724 | 11 tests pass | PROD — dual-target, ONVIF, subscribe |
| SOAP envelope builder | soap_client.py | 35,300 | 26 tests pass | MOCK — builds valid XML envelopes |
| SmartBridge client | smartbridge_client.py | 15,839 | Part of SOAP tests | MOCK — HTTP transport, capture mode |
| Violation queue processor | submission_queue.py | 15,237 | — | MOCK — queue logic done |
| KoAP violation codes | koap_codes.py | 13,903 | — | READY — 21+ violation articles mapped |
| Plate validator (KZ format) | plate_validator.py | 19,567 | — | READY — KZ plate parsing |
| Metrology cert tracker | metrology_cert_tracker.py | 12,623 | 17 tests pass | READY — tracks 243 cameras |
| GOST crypto (mock signer) | crypto.py | 17,595 | Part of SOAP tests | MOCK — MockSigner works, real signer needs cert |
| Evidence collage builder | evidence_collage.py | 8,290 | — | READY — 2-photo + GPS overlay |
| Pipeline orchestrator | pipeline.py | 25,263 | — | READY — ties everything together |
| Schema/models | schema.py / models.py | 29,809 | — | READY — ViolationCard, SpeedData, etc. |
| SmartBridge credentials | .env on VPS | — | — | HAVE — login + test/prod passwords |
| SmartBridge service registration | sb.egov.kz portal | — | — | SUBMITTED — KPSISU-S-5827 |

**Total codebase: 36 Python modules, 295K+ bytes, 66 tests passing.**

## What is MISSING (the 35% gap)

### GAP-1: NIT VPN to SmartBridge (CRITICAL — but government-dependent, LESSON-110)
- **What:** IPsec/StrongSwan tunnel to ERAP endpoint (195.12.122.44)
- **Reality:** NIT is a government entity. PSK will NOT come on any predictable timeline (LESSON-110). Do NOT plan around this arriving.
- **Status:** Application submitted. No ETA. Government bureaucracy — months minimum, likely rejection (foreign-hosted VPS = cross-border security exception).
- **Our readiness:** StrongSwan installed on VPS, ipsec.conf template prepared — but this may never be used
- **Alternative:** GVT has their own VPN channel (Klubtika). Or: test via sb.egov.kz test environment which may not require NIT VPN.
- **If PSK miraculously arrives:** 1-2 hours to configure

### GAP-2: ECP certificate for GOST digital signatures (CRITICAL — blocks real submissions)
- **What:** GOST 34.10-2015 certificate from NUC RK (via Aidana)
- **Who blocks:** Aidana — OID registration pipeline
- **Status:** OID registration in progress, ETA unknown
- **Our readiness:** crypto.py has MockSigner (works); real GostSigner skeleton exists but needs real cert
- **Effort when cert arrives:** 2-4 hours to integrate KalkanCrypt/gostcrypto with real cert

### GAP-3: Real SmartBridge endpoint validation (CRITICAL — the unknown)
- **What:** We have NEVER tested against real SmartBridge. Our SOAP envelope format is based on reverse-engineering of WSDL + captured traffic from BDL (April 3 diagnostics). Format may be wrong.
- **Risk:** XML namespace mismatch, missing fields, wrong signature format → ERAP rejects
- **Mitigation:** ERAP_CAPTURE=1 mode saves every request/response for debugging
- **GVT advantage:** They have already passed this validation. They know the exact format.

### GAP-4: Camera VPN to 10.170.*/10.235.* subnets (blocks remote camera config)
- **What:** Our VPS/Air cannot reach cameras directly
- **Workaround:** Denis has physical access to Satory network. Camera-dual-target.sh runs FROM INSIDE the network — does NOT require NIT VPN
- **Impact:** 243 cameras still push to BDL server (10.141.0.104), not to us
- **Action:** Denis runs script on-site. No NIT dependency for this.

### GAP-5: BDL server bridge software (the black box)
- **What:** Software on 10.141.0.104 that reformats camera ISAPI events into SmartBridge-compatible packets and submits to ERAP
- **What we know:** It receives events on port 8581 (/events/camera/hxml), does some processing, and sends to SmartBridge
- **What we DON'T know:** Exact transformation logic, any ERAP-specific field mappings, error handling, retry logic
- **This is what GVT could help reverse-engineer or replace**

## What GVT brings vs what we already have

| Capability | Satory (us) | GVT | Verdict |
|-----------|-------------|-----|---------|
| Camera hardware knowledge | Strong (Hikvision ISAPI, 243 cameras documented) | Strong (same Hikvision) | Parity |
| ISAPI event reception | PROD (154K events in DB) | Unknown | We're ahead |
| SmartBridge SOAP client | MOCK (coded, untested on real endpoint) | PROD (confirmed working) | **GVT ahead** |
| SmartBridge VPN channel | Pending NIT PSK | Have own (Klubtika VPN) | **GVT ahead** |
| GOST digital signing | MockSigner only | Unknown (not mentioned in letter) | Unknown |
| ERAP packet format | Reverse-engineered (untested) | Known (production-validated) | **GVT ahead** |
| Camera configuration | camera-dual-target.sh ready | Presumably can do same | Parity |
| Violation processing | Full pipeline (plate → violation → KoAP → fine) | Unknown scope | We may be ahead |
| Frontend/dashboard | police_dashboard.py (182K lines), satory.nousagaas.com | Not their scope | We're ahead |
| NIIS registration | Application #455466 filed | Not mentioned | We're ahead |

## Strategic recommendation

### Track A: Self-build (continue current path)
**Pros:** Full IP ownership, no vendor dependency, lower long-term cost
**Cons:** 2 government blockers (NIT VPN — likely never, ECP cert — unknown ETA) + untested SmartBridge format
**Risk:** HIGH. NIT VPN is government (LESSON-110) — PSK may never come. April deadline = survival month. Cannot bet the company on government bureaucracy.

### Track B: GVT as доразработка subcontractor
**Pros:** They have working SmartBridge integration, fast (7-20 days), known price
**Cons:** 98M KZT is expensive for what may be a small gap. Vendor dependency risk (Mergen repeat).
**Key question:** Can we scope GVT to ONLY the SmartBridge bridge layer (GAP-3 + GAP-5) and keep everything else ourselves?

### Recommended: Hybrid approach
1. **Continue self-build** for GAP-1 (VPN) and GAP-2 (ECP cert) — these are bureaucratic, not technical
2. **Engage GVT for GAP-3 + GAP-5 ONLY** — SmartBridge packet format validation + bridge software
3. **Scope the contract tightly:** GVT delivers a working bridge module that takes our ViolationCard format and produces SmartBridge-compatible output. We integrate it into our pipeline.
4. **IP protection:** Work product belongs to Satory. GVT gets read-only access to assess, code delivered to our repo, no ongoing access to our systems after delivery.
5. **Price negotiation:** 98M for 243 APK is their full turnkey price. A scoped доразработка contract for just the SmartBridge bridge layer should be 10-20M range.

## Negotiation brief for GVT meeting

What to tell GVT / what they need to assess:
1. We have 243 cameras documented and 36 Python modules handling the pipeline
2. We need them to validate our SOAP envelope format against real SmartBridge
3. We need them to help build/validate the bridge component (events → SmartBridge packet)
4. Show them our soap_client.py output (mock envelope) and ask: would this be accepted by ERAP?
5. Ask: what fields are we missing? What format differences exist vs their ISAP protocol?

What NOT to share with GVT:
- SmartBridge credentials (spectraerap2026 / passwords)
- Camera credentials (CAMERA_LU_USER/PASS)
- Full codebase access
- Dashboard / police workflow source code
- NIIS registration details

## See also
- [[source-madi-rosa-gvt-strategy-2026-04-16]] — strategy call transcript
- [[global-vision-technologies]] — GVT entity profile
- [[smartbridge-soap-client]] — SOAP client skill (mock mode)
- [[camera-management]] — camera management skill
- [[bdl-replacement-state-2026-04-07]] — BDL replacement progress
- [[smartbridge-vshp-client-credentials-2026-04-08]] — SmartBridge credentials
