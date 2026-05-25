---
type: spec
id: SPEC-TWO-TRACK-ERAP-2026-04-16
title: "Two-Track ERAP Strategy — self-build + GVT dorazrabotka"
tags: [spec, strategy, erap, smartbridge, bdl, gvt, two-track]
date: 2026-04-16
status: active
last_updated: 2026-04-16
priority: p0
related: [erap-technical-gap-assessment-2026-04-16, gvt-collaboration-framework-2026-04-16, global-vision-technologies, source-madi-rosa-gvt-strategy-2026-04-16]
---

# Two-Track ERAP Strategy (2026-04-16)

## Track A: Self-build (continue + accelerate)

**Goal:** Independent ERAP connection without any vendor dependency.

### A1. NIT VPN tunnel (unblocks SmartBridge + cameras)
- **Reality:** NIT is a government entity (LESSON-110). PSK will NOT come on any predictable timeline. Do NOT treat as an actionable blocker with an owner or ETA.
- **Status:** Application submitted. No expected delivery date. Government bureaucracy.
- **Implication:** Track A CANNOT depend on NIT VPN. Must find alternative SmartBridge access path (GVT's Klubtika VPN, or direct test endpoint access via sb.egov.kz without NIT tunnel).
- **If PSK miraculously arrives:** 1-2 hours to configure StrongSwan

### A2. ECP certificate (unblocks GOST digital signing)
- **Owner:** Aidana (OID registration) → Rose (ECP request)
- **Status:** OID registration in progress
- **Action:** Weekly check with Aidana
- **When cert arrives:** 2-4 hours to integrate real signer

### A3. SmartBridge test submission (validates our SOAP format)
- **Requires:** A1 (VPN) + A2 (cert)
- **Action:** Switch soap_client to test mode, submit one synthetic violation
- **ERAP_CAPTURE=1 saves everything for debugging**
- **Success criteria:** ERAP returns a real reference (not mock SB-YYYYMMDD-*)
- **If fails:** Captured request/response XML tells us exactly what is wrong

### A4. Camera re-pointing (restores event pipeline)
- **Requires:** Denis physically on-site at Satory network (10.235.*/10.170.* subnets)
- **Owner:** Denis
- **Action:** Denis runs camera-dual-target.sh from inside Satory network
- **Note:** Does NOT depend on NIT VPN — Denis has physical access
- **Preserves BDL target (10.141.0.104:8581) as fallback**

### A5. BDL server access (optional — higher risk)
- **Goal:** Gain admin access to 10.141.0.104 to inspect bridge software
- **Legal basis:** Satory owns the camera infrastructure; BDL is a terminated vendor
- **Risk:** May require state authorization letter (Blocker B5 from bdl-replacement-state)
- **Action:** Madi + Rose to evaluate legal path with Aleksey
- **Lower priority than A1-A4** — if A3 succeeds, we don't need BDL's software

## Track B: GVT dorazrabotka (parallel, insurance)

**Goal:** Use GVT's production experience to fill GAP-3 (SmartBridge format validation) and GAP-5 (bridge software) if our self-build hits walls.

### B1. Technical scoping meeting with GVT
- **Owner:** Madi
- **Action:** Show GVT our mock SOAP envelope output. Ask: would this work? What is missing?
- **Share:** XML sample from soap_client.py mock output, ViolationCard schema
- **Do NOT share:** credentials, code, infrastructure details
- **Output:** GVT provides specific list of what needs dorazrabotka

### B2. Legal framework (Aleksey review)
- **Owner:** Rose / Aleksey
- **Action:** Review gvt-collaboration-framework-2026-04-16.md
- **Key clauses:** IP ownership, source code delivery, no runtime dependency, kill switch test
- **Output:** Contract template approved

### B3. Negotiate scope + price
- **Owner:** Madi
- **Action:** Based on B1 scoping, negotiate bridge-module-only contract
- **Target price:** 10-20M KZT (vs 98M full turnkey)
- **Timeline:** 7-20 working days (per GVT letter)

### B4. GVT delivers + integrate
- **Requires:** B2 (contract) + B3 (agreement)
- **Action:** GVT delivers Python bridge module, we integrate into our pipeline
- **Kill switch test:** verify it works WITHOUT any GVT system access
- **Credential rotation:** within 24h of delivery

## Decision matrix: when to activate Track B

| Condition | Action |
|-----------|--------|
| NIT VPN PSK arrives (unlikely, government — LESSON-110) | Bonus: configure StrongSwan, test SmartBridge ourselves |
| NIT VPN does NOT arrive (expected outcome) | Track B is the primary path |
| GVT scoping reveals small gap | Narrow dorazrabotka contract (10-20M) |
| GVT scoping reveals large gap | Full engagement or alternative vendor |
| ECP certificate arrives (Aidana) | Unblocks GOST signing regardless of track |

## Timeline (optimistic)

| Week | Track A (self-build, no VPN dependency) | Track B (GVT dorazrabotka — PRIMARY) |
|------|---------|---------|
| Apr 16-18 | Fix hikvision_isapi.py (done); pytest gate green; Denis camera re-pointing | Technical scoping meeting with GVT |
| Apr 19-25 | If ECP cert arrives: integrate real GOST signer | Aleksey reviews framework, negotiate scope + price |
| Apr 26-30 | Test SmartBridge via sb.egov.kz test env (if accessible without NIT VPN) | GVT delivers bridge module |
| May 1+ | Integration + production test | Kill switch test + go-live |

## What to tell Saken (when ready)

Only after either Track A test succeeds OR Track B contract is scoped:

1. We have 65% of the ERAP pipeline built (36 modules, 154K real events, 66 tests passing)
2. The missing 35% is the SmartBridge connection layer
3. Two options: (a) self-build for free if bureaucratic blockers clear, (b) GVT dorazrabotka for 10-20M
4. Both options protect Satory IP — no vendor lock-in
5. Timeline: 2-4 weeks from blocker clearance

## See also
- [[erap-technical-gap-assessment-2026-04-16]] — technical gap details
- [[gvt-collaboration-framework-2026-04-16]] — IP protection framework
- [[global-vision-technologies]] — GVT entity profile
- [[bdl-replacement-state-2026-04-07]] — BDL replacement history
- [[smartbridge-soap-client]] — SOAP client skill
