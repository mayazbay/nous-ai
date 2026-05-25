---
type: law
id: LAW-002
title: "Violation Auto-Fine Rules"
status: permanent
enforcement: code-gate
tags: [koap, fines, speed, plate-confidence, violations]
related: [LAW-003, LAW-013]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-002: VIOLATION AUTO-FINE RULES
Status: PERMANENT. Business rules from CEO Madi.
Enforcement: Code in police_dashboard.py
Updated: 2026-04-06

## Speed violations (KoAP 592)
- 10-20 km/h excess → 21,625 tg (ch.1)
- 20-40 km/h excess → 43,250 tg (ch.2)
- 40-60 km/h excess → 86,500 tg (ch.3)
- 60+ km/h excess → 173,000 tg (ch.3-1)
- **excess = vehicle_speed - speed_limit** (NO additional tolerance subtraction)
- If excess >= 10 → IT IS A VIOLATION. Period.

## License plate confidence
- >= 90% confidence → AUTO-FINE immediately, no human review
- < 90% confidence → HUMAN OPERATOR must review and confirm
- Never auto-fine with low confidence plates
- Never skip fines on high confidence plates

## What is violation vs tracking
- 154K events = TRACKING (every car detected)
- Violation = tracking event WHERE speed excess >= 10 km/h
- Only violations get fined
- Dashboard must show VIOLATIONS count, not TRACKING count

## Known bug (must fix)
Backend calculates excess = speed - limit - 10 (double-counting threshold). WRONG.
Should be excess = speed - limit. 76 in 60 zone = 16 excess = ch.1 fine.

## See also
- [[koap_speed_fines|KoAP]]
- [[LAW-003-continuous-audit|LAW-003]]
- [[LAW-013-truth|LAW-013]]
