---
tier: 3
type: skill
name: smartbridge-soap-client
last_updated: 2026-04-17
description: Submits police-approved violation cards to ERAP via Kazakhstan's SmartBridge (ШЭП) e-government bus. Builds SOAP/XML envelopes with GOST signing, handles the submission queue, and captures real traffic for reverse-engineering. Currently in mock mode — no VPN or service registration required to test.
triggers:
  - SmartBridge SOAP
  - ВШЭП ЭЦП integration
  - GOST 34.10-2015
  - electronic signature submission
  - шлюз ЭЦП
  - SmartBridge API
  - XML signing
version: 1.0.0
tags: [smartbridge, soap, erap, gost, shep, government, vko, xml]
author: Madi Ayazbay
requires:
  - python: ">=3.10"
  - packages: [pytest]
  - modules: [erap.soap_client, erap.smartbridge_client, erap.crypto, erap.schema]
  - env (for real mode only):
      SMART_BRIDGE_URL: "SmartBridge endpoint URL (empty = mock mode)"
      ERAP_SMARTBRIDGE_MODE: "mock | test | real (default: mock)"
      ERAP_SYSTEM_BIN: "Spectra ITS BIN for routing header"
      ERAP_CAPTURE: "'1' to save request/response pairs to disk (default: 1)"
title: "smartbridge-soap-client v1.0.0"
---

# smartbridge-soap-client v1.0.0

Routes police-approved violation cards to ERAP via the Kazakhstan e-government SmartBridge (ШЭП) bus.

**Architecture:**
```
violation_cards DB (status=approved)
  → SOAPEnvelopeBuilder (builds XML + GOST signature)
    → SmartBridgeClient (adds routing headers, POSTs to ШЭП)
      → ERAP endpoint
        → callback updates DB to status=sent|erap_rejected
```

**Current status:** Mock mode active. Real mode requires:
- SmartBridge service registration (КПСиСУ)
- ETS GO VPN provisioned
- OID registration (Aidana, ~Apr 15)

**Key files:**
- `/opt/nous-agaas/erap/soap_client.py` — `SOAPEnvelopeBuilder`, `ErapSoapError` (853 lines)
- `/opt/nous-agaas/erap/smartbridge_client.py` — `SmartBridgeClient`, `ViolationQueueProcessor` (405 lines)

---

## TRAPS — READ BEFORE ANYTHING

1. **NEVER use zeep or suds** — raw XML + `urllib.request` only. zeep adds unpredictable namespace handling that breaks SmartBridge's strict XML parser.
2. **GOST 34.10-2015 only** — existing `MockSigner` is fine for testing. Production signer MUST use `gostcrypto` with GOST 34.10-2015. The old GOST 34.310-2004 in `crypto.py` is flagged for replacement.
3. **`_KZ_TZ = UTC+5`** — FIXED in both files (was UTC+6). All SOAP timestamps now correct.
4. **ERAP_CAPTURE=1 by default** — every real submission is saved to `/root/nous-agaas/wiki/raw/erap-captures/YYYY-MM-DD/`. DO NOT disable in test/real mode — this is the "connect-and-extract" reverse-engineering strategy.
5. **mock mode returns fake ERAP refs** — `SB-YYYYMMDD-XXXXXX`. Do NOT treat these as real ERAP refs. Check `result["mock"] == True`.
6. **NO personal data leaves Kazakhstan** — video frames and plate images must NEVER be passed to this module on Hetzner. Only plate number strings are in the SOAP envelope.

---

## Commands

### `smartbridge test-envelope`
Build a SOAP envelope (dry run, no network) and inspect the XML.

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.soap_client import SOAPEnvelopeBuilder
from erap.crypto import MockSigner
from erap.schema import ViolationCard, ViolationType, LocationData, SpeedData

builder = SOAPEnvelopeBuilder(signer=MockSigner())

card = ViolationCard(
    camera_id="CAM-001",
    violation_type=ViolationType.SPEED,
    violation_code=592,
    violation_subcode="ч.1",
    vehicle_plate="013АВС15",
    plate_confidence=0.97,
    location=LocationData(
        latitude=49.9480, longitude=82.6282,
        address="ул. Протозанова, 44",
        city="Усть-Каменогорск", region="ВКО",
    ),
    speed_data=SpeedData(
        measured_speed=82, speed_limit=60,
        error_margin=3.0,
        calibration_date="2026-01-15",
        calibration_cert_number="KTRM-2026-001",
    ),
)

xml_bytes = builder.build_violation_envelope(card)
print(xml_bytes.decode("utf-8")[:2000])
print(f"\nTotal size: {len(xml_bytes)} bytes")
```

**Verify:** output must contain `Envelope`, `Header`, `Security`, `BinarySecurityToken`, `GOST`, `MeasuredSpeed`.

---

### `smartbridge mock-submit`
Submit a card in mock mode (no network, instant response).

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.smartbridge_client import SmartBridgeClient
from erap.soap_client import SOAPEnvelopeBuilder
from erap.crypto import MockSigner
from erap.schema import ViolationCard, ViolationType, LocationData

builder = SOAPEnvelopeBuilder(signer=MockSigner())
client = SmartBridgeClient(mode="mock")

card = ViolationCard(
    camera_id="CAM-001",
    violation_type=ViolationType.SPEED,
    violation_code=592, violation_subcode="ч.1",
    vehicle_plate="013АВС15", plate_confidence=0.97,
    location=LocationData(
        latitude=49.9480, longitude=82.6282,
        address="ул. Тест, 1", city="УК", region="ВКО",
    ),
)
xml_bytes = builder.build_violation_envelope(card)
result = client.submit(xml_bytes, card_id="TEST-001")

print(f"success:      {result['success']}")
print(f"erap_ref:     {result['erap_ref']}")
print(f"status:       {result['status']}")
print(f"mock:         {result['mock']}")
# Expected: success=True, erap_ref=SB-YYYYMMDD-XXXXXX, mock=True
```

---

### `smartbridge process-queue`
Process all `approved` violation cards from `mission_control.db` (up to 20 per call).

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.smartbridge_client import ViolationQueueProcessor

processor = ViolationQueueProcessor()  # uses mock mode by default
stats = processor.process_pending()

print(f"Submitted: {stats['submitted']}")
print(f"Accepted:  {stats['accepted']}")
print(f"Rejected:  {stats['rejected']}")
print(f"Errors:    {stats['errors']}")
```

**DB side effects:** `violation_cards.status` updated to `sent` (accepted) or `erap_rejected` (rejected). `notes` field set to ERAP reference or rejection reason.

---

### `smartbridge check-captures`
Inspect saved request/response captures (ERAP_CAPTURE=1).

```bash
ls -lt /root/nous-agaas/wiki/raw/erap-captures/$(date +%Y-%m-%d)/
# Shows: YYYYMMDDTHHMMSS_<card_id>_request.xml
#        YYYYMMDDTHHMMSS_<card_id>_response.xml
#        YYYYMMDDTHHMMSS_<card_id>_meta.json

# Inspect a request
cat /root/nous-agaas/wiki/raw/erap-captures/$(date +%Y-%m-%d)/*_request.xml | head -50
```

---

### `smartbridge switch-to-test URL`
Switch to real SmartBridge test environment (after VPN + service registration).

```bash
# In /opt/nous-agaas/.env, set:
SMART_BRIDGE_URL=https://smartbridge.egov.kz/sbws/WsProvider  # or test URL
ERAP_SMARTBRIDGE_MODE=test
ERAP_SYSTEM_BIN=180440040428  # Spectra ITS BIN
ERAP_CAPTURE=1                # keep captures ON in test mode
```

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
import os
os.environ["SMART_BRIDGE_URL"] = "https://smartbridge-test.egov.kz/..."
os.environ["ERAP_SMARTBRIDGE_MODE"] = "test"

from erap.smartbridge_client import SmartBridgeClient
client = SmartBridgeClient.from_env()
print(f"Mode: {client.mode}")  # Must print: test
```

---

## Pytest Gate

```bash
cd /opt/nous-agaas && python3 -m pytest erap/tests/test_soap.py erap/tests/test_soap_integration.py -v --tb=short
```

**Expected:** 26 tests pass (XML schema validation + GOST signature verification).

Full combined gate (all skills):
```bash
cd /opt/nous-agaas && python3 -m pytest \
  erap/tests/test_camera_registry.py \
  erap/tests/test_hikvision.py \
  erap/tests/test_metrology.py \
  erap/tests/test_soap.py \
  erap/tests/test_soap_integration.py \
  -q 2>&1 | tail -3
# Expected: 66 passed
```

---

## Real mode pre-flight checklist

Before switching from mock → test → real:

- [ ] OID registration approved (КПСиСУ) — Aidana
- [ ] SmartBridge service registration approved
- [ ] ETS GO VPN provisioned and active on VPS
- [ ] `SMART_BRIDGE_URL` set in `.env`
- [ ] `ERAP_SMARTBRIDGE_MODE=test` first (never jump straight to real)
- [ ] Test with 1 synthetic card, verify capture files look correct
- [ ] Confirm `result["mock"] == False` in response
- [ ] Verify `erap_ref` is a real ERAP reference (not `SB-YYYYMMDD-*`)
- [ ] Set `ERAP_SMARTBRIDGE_MODE=real` only after test succeeds

---

## See also
- [[soap_client]] — `SOAPEnvelopeBuilder`, SOAP namespace constants, GOST signing
- [[camera-management]] — Camera IDs used in violation cards
- [[metrology-cert-tracker]] — Only calibrated cameras can issue speed violations
- [[AGAAS-ARCHITECTURE-DECISION-v2-GOLDEN]] — SmartBridge is week 2-3 skill

