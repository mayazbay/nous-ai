---
tier: 3
name: kazakhstan-regulatory
description: "Use for ANY question about Kazakhstan traffic law, ERAP fines, BIN numbers, GOST crypto standards, camera types, data residency, or ЭЦП. Triggers on: МРП, Ст.591-601, BIN, GOST, ЭЦП, SmartBridge, ERAP, satory, violation, fine, camera, APK, OVN."
type: skill
id: SKILL-KAZAKHSTAN-REGULATORY
version: 1.0.0
status: active
absorbs_laws: [LAW-002]
absorbs_lessons: []
tags: [skill, regulatory, kazakhstan, erap, camera, fines, gost, 2026-04-16]
date: 2026-04-16
source_count: 0
last_updated: 2026-04-16
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, camera-management, smartbridge-soap-client, nazel-lawyer, roza-sadyrova, spectra-its, satory]
title: "kazakhstan-regulatory v1.0.0"
---

# kazakhstan-regulatory v1.0.0

## Current rules (compiled truth)

### Traffic fine rates (КоАП — Кодекс об административных правонарушениях)

1. **МРП 2026 = 4,325 ₸** (Месячный расчётный показатель). Updated annually every January. NEVER hardcode — use `config.MRP_2026` or equivalent. Verify against egov.kz each January.

2. **Speed violations (Ст.592):**
   - ч.1 (10–20 km/h over): 5 МРП = 21,625 ₸
   - ч.2 (20–40 km/h over): 10 МРП = 43,250 ₸
   - ч.3 (40+ km/h over): 20 МРП = 86,500 ₸
   - ч.3-1 (60+ km/h over): 40 МРП = 173,000 ₸

3. **Other violation articles:**
   - Red light = Ст.599
   - Seatbelt = Ст.593
   - Phone use = Ст.591
   - Stop line crossing = Ст.601

4. **Camera violations = BASE FINES ONLY.** For camera-detected offenses, ONLY ч.1 through ч.3-1 apply. NEVER cite ч.4 or ч.5 (repeat offender escalation) — those require a prior conviction record, which cameras cannot establish.

5. **50% discount:** Ст.810-811. 7 business days from предписание (notification date). Spectra must accurately report предписание dates for discount eligibility.

### Cryptographic and data standards

6. **GOST 34.10-2015** for ЭЦП (electronic digital signature) via KalkanCrypt. mTLS + JWT required for all ERAP-facing API calls.
7. **Data residency:** Backend MUST be hosted in Kazakhstan (Law 94-V). Current: Hetzner VPS is gateway only; production backend must move to Alem.Cloud. **Digital Code of KZ (July 2026)** tightens this requirement.

### BIN directory (triple-verified, do not change without Madi approval)

| Entity | BIN | Purpose |
|---|---|---|
| Nous AI | 260240032631 | Holding company |
| Spectra ITS | 070640013540 | Government VMS/ERAP contractor (ERAP BIN for violation submission) |
| Satory Company LTD | 040940014188 | Client / general contractor |

### Camera facts (from Руслан Генетинов xlsx, 27.03.2026)

8. **APK:** 109 cameras (Ust-Kamenogorsk only, Hikvision, certificates expired 31.12.2024)
9. **OVN:** 5,691 cameras
10. **Total:** 5,800
11. **Camera types:** ЛУ (lane unit), ПРК (intersection), ОВН (video surveillance). NOT APK (that is the certification system, not a camera type).
12. **KZ plates format:** 3 digits + 3 Latin letters + 2-digit region (16=ВКО, 18=Абайская)

### Timezone and locale

13. **Always use Asia/Almaty (+06:00).** In code: `config.now_kz()`, never `datetime.now()`.

### Coding rules (KZ-specific)

14. `import xml.etree` → `import defusedxml.ElementTree` (XXE prevention)
15. Helvetica/Times in PDF → DejaVu Sans TTF (Cyrillic rendering)
16. YOLO/Ultralytics → BANNED (AGPL-3.0), use RT-DETR

## P1 — Annual re-verification ritual (every January)

1. Check egov.kz for new МРП value. Update `config.MRP_YYYY`.
2. Check if any Ст. articles changed in КоАП amendments.
3. Verify BIN status for all 3 entities (check egov.kz business register).
4. Check camera cert expiry (APK certs were expired 31.12.2024 — are they renewed?).

## P2 — Citation lookup (when Madi or Smatay asks about a fine)

1. Identify the article (Ст.591-601).
2. Identify the part (ч.1-ч.3-1 for cameras, ч.1-ч.5 for officer-issued).
3. Calculate: fine = ч.N × МРП × 4,325₸.
4. Check 50% discount eligibility (Ст.810-811, 7 business days from предписание).

## P3 — When to escalate to legal

Escalate to Nazel (lawyer) or Rose (legal/GR director) when:
- ЭЦП certificate renewal or revocation
- SmartBridge VPN application
- Government tender filing
- BIN change or registration
- Data residency compliance question under Law 94-V
- Any question involving the Digital Code of KZ (July 2026)

## Anti-patterns

### AP-1: Hardcoded МРП in source code
**Problem:** МРП changes annually. Hardcoded 4,325 becomes wrong on Jan 1 next year.
**Fix:** Use `config.MRP_YYYY` or database lookup. The skill rule says: NEVER hardcode.

### AP-2: Citing ч.4/ч.5 for camera violations
**Problem:** Camera violations cannot establish prior conviction history. ч.4/ч.5 are for repeat offenders identified by officers.
**Fix:** Camera fines are ALWAYS ч.1 through ч.3-1. No exceptions.

### AP-3: Forgetting timezone in datetime operations
**Problem:** Using `datetime.now()` gives server-local time, not Almaty time. ERAP timestamps must be Asia/Almaty.
**Fix:** Always `config.now_kz()`.

### AP-4: Using Ultralytics for plate recognition
**Problem:** AGPL-3.0 requires open-sourcing any derivative work. Satory/Spectra code is proprietary.
**Fix:** Use RT-DETR or other permissively-licensed detection models. YOLO is BANNED.

## Rules absorbed from LAWs

- **LAW-002** (Violation Auto-Fine Rules): speed excess ≥10 km/h → violation. All events to DB, filter at query time (NOU-108).

---

## Evidence trail (append-only)

- **2026-04-16** | v1.0.0 created per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P2 Task 9. Absorbs GOD_PROMPT §9 KZ domain rules + LAW-002. Source data: Руслан Генетинов xlsx 27.03.2026 for camera counts.

## See also

- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[camera-management]] — ISAPI / Hikvision-specific
- [[smartbridge-soap-client]] — SmartBridge / ВШЭП integration
- [[nazel-lawyer]] — legal escalation contact
- [[roza-sadyrova]] — ЭЦП owner / legal director
- [[spectra-its]] — BIN 070640013540
- [[satory]] — BIN 040940014188
- [[LAW-002-violation-auto-fine-rules]]
