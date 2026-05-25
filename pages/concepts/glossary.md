---
type: concept
id: GLOSSARY
title: "Glossary — Acronyms & Domain Terms"
tags: [glossary, reference, acronyms]
date: 2026-04-07
related: [SPEC-ERAP, spectra-its, cameras, LESSON-023]
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Glossary — Satory VKO / Nous AGaaS Domain Terms

Single source of truth for every acronym or technical term used across this wiki. When you see a term in any page, look here for its definition. New terms must be added here **before** they are used in a wiki page.

## Core government / legal systems

### ЕРАП / ERAP
**Единый Реестр Административных Производств** (Unified Registry of Administrative Proceedings).
- Owner: Комитет по правовой статистике и специальным учетам Генеральной прокуратуры РК (Legal Statistics Committee of the General Prosecutor's Office of Kazakhstan)
- System ID: `erap_violation_receiver`
- Protocol: SOAP over HTTPS, WS-Security with ЭЦП (XML Digital Signature)
- Flow: Satory VKO server → ВШЭП Gateway → ИС ЕРАП
- Purpose: the single national system where every approved speeding / traffic violation must be submitted to generate a legally-enforceable fine.
- See: [[erap_requirements]], [[erap_requirements]], [[source-erap-decision-apr1]]

### ВШЭП / VSHEP / SHEP
**Внешний Шлюз Электронного Правительства** (External E-Government Gateway).
- The legal gateway for inter-ministry data exchange in Kazakhstan. In practice we do not talk to ВШЭП directly — we use [[glossary|SmartBridge|SmartBridge]], a Sergek-supplied client that rides the ВШЭП rails.
- Every outbound SOAP call to ЕРАП goes through ВШЭП.
- Requires accredited EDS (ЭЦП) signature on every request.


### SmartBridge
**Sergek SmartBridge** — the concrete integration product that sits on top of ВШЭП and is our actual path to submit violations to ERAP.
- Operator: Sergek Group (same org behind the `esb.sergek.kz` namespace)
- Role: a certified SOAP/REST integration broker that handles ЭЦП signing, envelope formatting, and delivery to ИС ЕРАП through the legal ВШЭП gateway
- **Relationship to ВШЭП:** SmartBridge is *not* a parallel path — it is the vendor-supplied client that rides the ВШЭП rails. Calling "via SmartBridge" and "via ВШЭП" refers to the same underlying data flow.
- Test environment: does NOT require infosec certification — only production does. Test onboarding is fast (~15 business days).
- Decision (2026-04-01): connect to ERAP via SmartBridge instead of inheriting BDL's existing connection. Fresh registration under Spectra entity.
- See: [[source-smartbridge-apr3]], [[source-erap-decision-apr1]]

### КоАП РК
**Кодекс РК об административных правонарушениях** (Code of Administrative Offenses of Kazakhstan).
- Law defining speeding fines, rejection reasons, retention periods.
- Key article for our system: 592 (превышение скорости / speeding).
- Stores fine amounts in МРП (Monthly Calculation Index).

## Camera / hardware terms

### АПК / APK
**Аппаратно-Программный Комплекс** (Hardware-Software Complex).
- The general umbrella term for ALL cameras in the Satory VKO network.
- **NOT a camera type.** Common early mistake — see [[LESSON-023-apk-not-camera-type]].
- Cameras split into exactly two types:
  - **ЛУ / LU** — Линейный Участок (Linear Segment) — speed cameras on highways
  - **ПРК / PRK** — Перекрёсток (Intersection) — cameras at intersections
- In backend API and code, always use `lu` or `prk`. Never `apk`.

### ЛУ / LU
**Линейный Участок** — Linear Segment. Speed cameras mounted along highway stretches. Primary source of speeding violations in the VKO region.

### ПРК / PRK
**Перекрёсток** — Intersection. Cameras at intersections. Detect red-light running, wrong-direction, illegal turns.

### MRGN
**Mobile Roadside GNSS Node** (our internal name — used as camera registry ID format).
- Example: `MRGN-ALM-001`, `MRGN-UKK-042`
- Distinct from `camera_ip` (the actual IP of the device).
- **No IP↔MRGN mapping table exists today.** This is why tracking returns honest `lat: null, lng: null` — see [[LESSON-046-mrgn-ip-mismatch]].

### ОВН / OVN
Third-party sensor class (non-Satory), referenced in some camera rows. Rare, mostly legacy.

## Video management systems

### VMS
**Video Management System.**
- The software layer that ingests RTSP/ONVIF streams from cameras, records footage, serves playback, and triggers analytics.
- The government has historically used **BDL + Cerebro VMS** (see below). Satory VKO is the successor.
- Spectra ITS is titled "Government VMS/ERAP Contractor" — they operate both layers for the VKO region.

### BDL
**Big Data Lab** — the previous company/platform running VKO's video infrastructure before Satory VKO took over.
- Led by Mergen (see [[source-bdl-bypass-feb20]], [[source-bdl-replacement-apr2]]).
- Ongoing criminal case: refused to hand over codes, passwords, and access during handover.
- Our system intentionally **does not depend on BDL** — Phase 2 reality conversion eliminated every remaining BDL bridge.

### Cerebro VMS
The specific VMS product BDL was running. Legacy. Being replaced by Satory VKO.

## Organizations & people (high-level — see entity pages for full)

### Satory VKO
Our product name. The frontend + backend system deployed at `satory.nousagaas.com` serving the VKO (East Kazakhstan) region. Built by Nous Ltd for Spectra ITS.

### Spectra ITS
The government contractor that owns the VKO monitoring contract. They are our direct customer. See [[spectra-its]].

### Nous Ltd / Nous AGaaS
Our company. Madi Ayazbay, CEO. AGaaS = Autonomous Government-as-a-Service (the broader vision; Satory VKO is the first product).

### Komitet
Short for "Комитет по правовой статистике и специальным учетам" — the committee inside the Kazakhstan Prosecutor General's office that owns ЕРАП and is the ultimate legal consumer of our violation submissions.

## Technical terms

### ЭЦП / EDS
**Электронная Цифровая Подпись** / Electronic Digital Signature. Required on every SOAP request to ВШЭП. Issued by accredited Kazakhstani certificate authorities.

### ГРНЗ / GRNZ
**Государственный Регистрационный Номерной Знак** — State Vehicle License Plate Number. Our LPR (License Plate Recognition) pipeline extracts these from camera frames.

### МРП / MRP
**Месячный Расчётный Показатель** (Monthly Calculation Index). Kazakhstan's reference unit for fines. Speeding fines in КоАП 592 are denominated in MRP, so the absolute tenge amount changes yearly. Our backend calculates actual tenge at submission time.

### КОАП (article 592)
The specific КоАП article covering speeding. Defines threshold brackets (e.g. 11-20 km/h over = X MRP, 21-40 = Y MRP, etc.).

## How to use this glossary
- **Adding terms:** new acronym or technical term → add an entry here FIRST, then reference it in your page via `[[glossary|TERM]]`.
- **Checking:** before writing an acronym in a page, check here. If missing, add it.
- **Linting:** `tools/wiki_lint.py` will flag acronyms used in 3+ pages with no glossary entry.

## See also
- [[erap_requirements]] — full ERAP integration spec
- [[spectra-its]] — customer entity
- [[cameras]] — camera registry
- [[LESSON-023-apk-not-camera-type]] — why APK is not a camera type
- [[LESSON-046-mrgn-ip-mismatch]] — why MRGN↔IP mapping matters

## Additional terms (added 2026-04-07)

### ВКО / VKO
**Восточно-Казахстанская Область** (East Kazakhstan Region / Oblast). Our deployment region. Capital: Усть-Каменогорск (Oskemen). Satory VKO is the pilot deployment for this oblast under the Spectra ITS contract. Future expansion targets other oblasts.

### КоАП / KoAP
**Кодекс Республики Казахстан об Административных Правонарушениях** — Code of the Republic of Kazakhstan on Administrative Offenses. See [[koap_speed_fines]]. The specific article relevant to us is 592 (speeding). Fine amounts denominated in МРП (see below).

### AGaaS
**Autonomous Government-as-a-Service** — Nous Ltd's long-term product vision: AI agents running core government workflows autonomously. Satory VKO is the first concrete AGaaS product (violation detection + submission pipeline).

### SWR
**stale-while-revalidate** — the React data-fetching hook library (`swr` on npm) used everywhere in the Satory VKO frontend. Each component calls `useSWR(key, fetcher)` with a **unique key** (per-feature). Reusing a bare key like `/api/proxy/violations` across multiple components causes cache collisions — see [[LESSON-016-swr-cache-collision-critical]].

### RCA
**Root Cause Analysis** — the discipline of tracing failures to their underlying cause rather than patching symptoms. Every LESSON in `pages/lessons/individual/` is effectively an RCA. See the umbrella document [[root_cause_analysis]].

### ESB / ЭСБ
**Enterprise Service Bus** — the SOAP namespace root we use for ERAP: `http://esb.sergek.kz/cxf/violation`. Sergek is the operator of the national violation receiver.

### VPN (in the context of ERAP integration) — THREE SEPARATE VPNs, reconciled in AUDIT-029

The project has **three different network-layer things** called "VPN" in different contexts. Don't confuse them — [[AUDIT-029-three-vpns-reconciled-camera-nit-firewall]] is the canonical reference.

1. **Camera IPsec VPN** — ✅ **ESTABLISHED** since 2026-03-30. 5/5 SAs up. Our end `65.108.215.200` ↔ camera gateway `89.40.56.150`. Unlocks subnets `10.235.0.0/18`, `10.170.0.0/18`, `10.164.72.0/24`, `10.165.72.0/24`, `10.164.80.0/24`. Purpose: pull RTSP/ISAPI from cameras. Owner: Denis.
2. **NIT SmartBridge IPsec VPN** — 🟡 **PENDING** (Asyl submitted ШЭП form on 2026-04-08, NIT will deliver PSK "нарочно"). Our end `65.108.215.200` ↔ NIT gateway `195.12.122.44`. IPsec/IKEv2 per the 7-requirement NIT spec ([[source-nit-vpn-tech-conditions-2026-04-08]]). Purpose: reach the internal ERAP SOAP endpoint (`erap_violation_receiver`). Required for вне ЕТС ГО clients (us, on Hetzner Finland). Owner: NIT provisions their side, Claude Code configures StrongSwan on ours.
3. **MikroTik Firewall ACL** — 🟡 **PENDING accept** (not a VPN — a Layer-3 firewall rule). Denis must add an accept rule for `65.108.215.200` on the MikroTik camera-network router. Without this, VPN #1 brings packets to the MikroTik but they get dropped before reaching the camera subnet.

**Previous misconception (AUDIT-021 "VPN myth busted")**: concluded ШЭП needs no VPN, based on reading the SmartBridge application-layer spec (HTTPS + SOAP + WS-Security + ЭЦП — all correct). Missed that the NETWORK-LAYER endpoint for PRODUCTION ERAP lives behind VPN #2 for вне ЕТС ГО clients. AUDIT-021 is marked "PARTIALLY REVISED" and points to [[AUDIT-029-three-vpns-reconciled-camera-nit-firewall]] for the corrected picture.
