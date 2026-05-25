---
type: spec
id: SPEC-BDL
title: "BDL Replacement Checklist"
tags: [spec, bdl, replacement, checklist]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# BDL Replacement Checklist
Target: Replace BDL's Cerebro system with Satory VKO

## Must-Have (Phase 1)
- [ ] Camera grid: 243 cameras, online/offline status, last ping
- [ ] Live event feed: plate, speed, camera, timestamp, photo
- [ ] Violation cards: Form 1-AB (KoAP format)
- [ ] Photo evidence: scene + plate crop
- [ ] Search: by plate, date range, camera, speed range
- [ ] CSV export with BOM for Russian chars
- [ ] Map view: camera locations on OpenStreetMap
- [ ] Stats: hourly violations, top plates, speed distribution

## Nice-to-Have (Phase 2)
- [ ] ERAP integration (ШЭП/ЕРАП submission)
- [ ] Auto-violation detection (speed threshold)
- [ ] Operator audit trail
- [ ] Print-ready violation cards

## See also
- [[cameras|Camera Network]]
- [[erap|ERAP Pipeline]]
- [[koap_speed_fines|KoAP]]
- [[cerebro_bdl_vms_requirements|VMS Requirements]]
