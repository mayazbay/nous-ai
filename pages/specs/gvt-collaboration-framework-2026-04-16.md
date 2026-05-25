---
type: spec
id: SPEC-GVT-COLLAB-FRAMEWORK
title: "GVT Collaboration Framework — IP protection + access model"
tags: [spec, gvt, partnership, ip-protection, legal, contract, dorazrabotka]
date: 2026-04-16
status: draft
last_updated: 2026-04-16
priority: p0
related: [global-vision-technologies, source-madi-rosa-gvt-strategy-2026-04-16, erap-technical-gap-assessment-2026-04-16]
---

# GVT Collaboration Framework — IP Protection + Access Model

> DRAFT — for Aleksey (legal) review before formalizing with GVT.

## Problem statement

Satory needs the SmartBridge bridge layer (GAP-3 + GAP-5 from gap assessment). GVT has a working production version. Engaging GVT as subcontractor risks repeating the BDL/Mergen scenario where the vendor builds critical infrastructure then holds it hostage by threatening disconnection.

## Proposed contract structure

### 1. Scope: Bridge Module Only

GVT delivers ONE module: a software component that:
- Accepts input: ViolationCard data structure (plate, speed, location, timestamps, photos)
- Produces output: SmartBridge-compatible SOAP/XML packet
- Submits to ERAP via SmartBridge and returns success/failure + ERAP reference

GVT does NOT touch:
- Camera infrastructure (ISAPI listener, event parser, camera registry)
- Violation detection logic (speed thresholds, KoAP codes, plate validation)
- Frontend / police dashboard
- Evidence collection / photo management
- Server infrastructure (VPS, Air, Docker)

### 2. IP ownership

- All code written under this contract is work-for-hire: Satory owns 100%
- GVT retains right to use their own pre-existing SmartBridge integration code in other projects
- GVT does NOT get rights to any Satory code, data, or infrastructure
- Source code delivered to Satory git repository, not hosted on GVT infrastructure

### 3. Access model during engagement

**GVT gets:**
- Read-only access to our SOAP envelope output (mock XML samples)
- Read-only access to our ViolationCard schema definition
- Test environment access (ERAP test endpoint only, not production)
- SmartBridge test credentials for the engagement period only (rotate after)

**GVT does NOT get:**
- SSH access to VPS or Air
- Camera credentials
- Production SmartBridge credentials
- Access to events.db or any production data
- Access to police dashboard or frontend code
- Access to our NIIS registration

### 4. Delivery format

GVT delivers:
- Python module(s) implementing the bridge interface
- Integration tests that pass against SmartBridge test endpoint
- Documentation of ERAP packet format (field-by-field mapping)
- List of ERAP rejection codes and their meanings (from their production experience)

### 5. Post-delivery

- Rotate SmartBridge test credentials used during engagement
- GVT access to test environment revoked
- No ongoing access to any Satory system
- Support period: 30 days for bug fixes on delivered module

### 6. Price framework

| Scope | GVT quoted (full turnkey) | Proposed (bridge only) |
|-------|--------------------------|----------------------|
| 243 APK → ERAP | 98,000,000 KZT | N/A |
| Bridge module only | N/A | 10-20M KZT (negotiable) |
| Per-unit (if they insist) | 403,300 KZT/APK | N/A — flat fee for module |

Rationale for 10-20M: GVT quoted 98M for full integration of 243 APK (hardware config + software + VPN + ERAP). We only need the software bridge component, which is maybe 15-20% of the total scope.

### 7. Mergen-proofing (anti-hostage clauses)

From Rosa's concern:
1. **Source code escrow:** delivered source is in our git repo on day 1, not hosted by GVT
2. **No runtime dependency on GVT systems:** bridge module runs on our infrastructure
3. **No GVT VPN dependency:** we do NOT depend on GVT Klubtika VPN for ongoing operations — we use sb.egov.kz test endpoint or, if NIT VPN ever arrives, our own tunnel
4. **Kill switch test:** before final payment, Satory must verify the bridge works WITHOUT any GVT system access
5. **Credential rotation:** all shared credentials rotated within 24h of engagement end

## Decision gates

- [ ] **Gate 1:** Aleksey reviews this framework and flags legal risks
- [ ] **Gate 2:** Madi approves the scope and price range
- [ ] **Gate 3:** GVT agrees to bridge-only scope (not full turnkey)
- [ ] **Gate 4:** Contract signed with IP ownership and anti-hostage clauses
- [ ] **Gate 5:** Post-delivery kill switch test passes
- [ ] **Gate 6:** Present results to Saken with clear cost/benefit

## See also
- [[global-vision-technologies]] — GVT entity profile
- [[source-madi-rosa-gvt-strategy-2026-04-16]] — strategy call
- [[erap-technical-gap-assessment-2026-04-16]] — what is missing technically
