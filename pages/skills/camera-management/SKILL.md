---
tier: 3
type: skill
name: camera-management
version: 2.10.0
description: CRUD + health monitoring + ISAPI2 event activation for the Satory VKO Hikvision camera network. Wraps the existing ISAPI codebase at /opt/nous-agaas/erap/. Requires route, WireGuard-handshake, event-freshness, and registry-alignment proof before diagnosing dashboard camera-health failures as frontend bugs.
triggers:
  - camera health check or CRUD operation
  - activating ЛУ camera ISAPI2 subscription
  - debugging events-stop at listener
  - verifying camera hardware compliance vs ЕРАП spec
  - camera credential rotation for ЛУ
  - Hikvision ISAPI device query
  - calibration expiry tracking
  - dashboard shows 0 online cameras
  - wg-satory camera route failure
tools:
  - python3 (>=3.10)
  - requests, pytest
  - VPN tunnel to 10.170.0.0/16 and 10.235.0.0/16 (Satory network)
mutating: true
absorbs_lessons:
  - LESSON-015 (registry MRGN IDs vs camera IPs — no direct mapping)
  - LESSON-023 (АПК is NOT a camera type; correct types are ЛУ/ПРК/ОВН)
  - LESSON-124 (camera pipeline break: check BOTH sides — receiver AND camera push source)
  - LESSON-024 (iDS-2CD9396-BIS model string comes from camera self-report — real but Satory may not recognize it)
  - LESSON-026 (three camera types: ЛУ, ПРК, ОВН — not two)
  - LESSON-047 (photo retention shorter than violation retention — old violations have dead photo paths)
  - LESSON-058 (ERAP capture mode — observability-first for reverse-engineering)
  - LESSON-085 (false declaration — verify end-to-end before declaring done)
  - LESSON-102 (events stopped: camera re-point + subscribe_events overwrites + NOU-108 silent drop)
  - LESSON-012 (count UNIQUE camera IDs — never report raw Excel row counts as camera counts)
  - LESSON-021 (LU cameras online with 0 events = ISAPI push subscriptions not configured)
  - LESSON-107 (store one raw protocol sample per N events; replay without sample is impossible)
  - LESSON-117 (vendor-lock bypass — Satory owns infrastructure, BDL is software-only vendor; 5-level bypass pattern)
absorbs_laws:
  - LAW-018 (data contract — save ALL camera events to DB, filter at query time)
  - LAW-002 (violation auto-fine thresholds — cameras are the source; speed excess ≥10 km/h → violation. Wave 4 cross-reference.)
tags: [cameras, isapi, hikvision, health, crud, vko, isapi2, erap]
date: 2026-04-15
last_updated: 2026-04-30
title: "camera-management v2.10.0"
---

# camera-management v2.10.0

Manages 243 Hikvision cameras across the VKO Safe City network:
- **209 LU speed cameras** — 10.170.1.3 – 10.170.209.3 (USK + Ridder + Altay subnets)
- **34 ПРК intersection cameras** — 10.235.0.3 – 10.235.33.3 (USK only, active)

All camera operations go through Hikvision ISAPI (REST over HTTP). The existing codebase at `/opt/nous-agaas/erap/` has 33 modules and 295 tests — this skill wraps it, does NOT rewrite it.

---

## Purpose

Provide a single authoritative interface for camera CRUD, health monitoring, ISAPI2 event subscription activation, and hardware compliance verification against the ЕРАП spec. Every production action must pass the pytest gate first.

---

## Contract

1. **Pytest gate mandatory** — run 23+ tests before any production mutation.
2. **Credentials from env vars only** — `CAMERA_LU_USER`, `CAMERA_LU_PASS`, `CAMERA_P_USER`, `CAMERA_P_PASS`. Never hardcode. Never commit to wiki/git.
3. **Timezone UTC+5** — KZ since March 2024. Hardcoded in `hikvision_isapi.py:34` as `hours=5`.
4. **Digest auth required on production cameras** — never set ISAPI2 auth to None.
5. **Calibration expiry blocks legal use** — 109 cameras have expired calibration. `is_calibration_valid()` returns False → speed violations from those cameras are legally void.

---

## Phases

### P1 — Health Check & CRUD

Basic camera status queries, registry CRUD, and health reporting. The original v1.x skill scope.

#### `camera status [IP_OR_ALL]`

```bash
# Single camera
python3 -c "
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.camera_monitor import check_camera
result = check_camera('10.170.1.3', cam_type='lu')
print(result)
"

# All cameras (concurrent, 5-min cycle)
cd /opt/nous-agaas/erap && python3 -m erap.camera_monitor
```

**Returns:** online/offline status, firmware version, model, response_ms, last_check.

#### `camera list [--type lu|prk|ovn] [--status active|offline|expired]`

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.camera_registry import CameraRegistry
reg = CameraRegistry()

cameras = reg.get_all(status='active', camera_type='lu')
for cam in cameras:
    print(f"{cam.ip_address} | {cam.id} | cal_valid={reg.is_calibration_valid(cam.id)}")

expiring = reg.get_expiring_cameras(days=30)
```

#### `camera register IP TYPE SERIAL FIRMWARE`

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.camera_registry import CameraRegistry, Camera
from datetime import date

reg = CameraRegistry()
cam = Camera(
    id="DS-ABC123",
    model="DS-2CD7A26G0/P-IZS",
    firmware="V5.7.20 build 240830",
    ip_address="10.170.100.3",
    camera_type="lu",          # must be lu / prk / ovn — NOT apk (see AP-4)
    calibration_date=date.today().isoformat(),
    calibration_cert="CERT-2026-001",
    city="Усть-Каменогорск",
    status="active"
)
success = reg.register(cam)
```

#### `camera health-report`

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.camera_registry import CameraRegistry
reg = CameraRegistry()
stats = reg.get_stats()
print(f"Total: {stats['total']}, Active: {stats['active']}, Expired: {stats['calibration_expired']}")
```

#### `camera isapi-check IP`

```python
import sys, os; sys.path.insert(0, '/opt/nous-agaas/erap')
import requests
from requests.auth import HTTPDigestAuth

ip = "10.170.1.3"
user = os.environ.get("CAMERA_LU_USER", "oper")
passwd = os.environ.get("CAMERA_LU_PASS", "")

r = requests.get(
    f"http://{ip}/ISAPI/System/deviceInfo",
    auth=HTTPDigestAuth(user, passwd),
    timeout=5
)
print(r.status_code, r.text[:500])
```

#### `camera onvif-enable IP`

```python
import sys, os; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.hikvision_isapi import HikvisionISAPIClient

client = HikvisionISAPIClient(
    ip="10.170.1.3",
    username=os.environ["CAMERA_LU_USER"],
    password=os.environ["CAMERA_LU_PASS"],
)
success = client.enable_onvif()
```

---

### P2 — Event Subscription (single camera)

Subscribe one camera to push ISAPI alert events to our listener.

#### `camera subscribe-events IP PUSH_HOST`

```python
import sys, os; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.hikvision_isapi import HikvisionISAPIClient

ip = "10.170.1.3"
push_host = "65.108.215.200"  # VPS IP reachable from camera subnet
push_port = 9080

client = HikvisionISAPIClient(
    ip=ip,
    username=os.environ["CAMERA_LU_USER"],
    password=os.environ["CAMERA_LU_PASS"],
)
# WARNING: subscribe_events is DESTRUCTIVE — see AP-10
# For dual-target (preserve existing + add ours), use add_notification_target()
success = client.add_notification_target(push_host, push_port)
print(f"Added target {ip} -> {push_host}:{push_port}:", success)
```

**Note:** push_host must be reachable from the camera's subnet. VPN tunnel required. VPS and Air have NO route to 10.235.*/10.170.* without VPN (see AP-8).

---

### P3 — Activate ЛУ camera ISAPI2 subscription (bulk)

Activate ISAPI2 event push for the 145 ЛУ cameras that are online but NOT currently configured to push events. Reference: 51 APK cameras were active before 2026-04-05; ЛУ cameras are silent.

**Prerequisites:** Machine inside Satory network (10.235.*) with route to cameras — VPS and Air have NO direct route (see AP-8). `CAMERA_LU_USER` / `CAMERA_LU_PASS` set in env.

#### Step 3a — Load credentials

```bash
# VPS only — credentials live in /opt/nous-agaas/.env (600 deploy:deploy)
# Air copy: ~/nous-agaas/.env (600 madia:staff)
set -a && source /opt/nous-agaas/.env && set +a
echo "User: $CAMERA_LU_USER"  # should show: oper
```

#### Step 3b — Use camera-dual-target.sh (preferred for re-pointing)

```bash
# Run from inside Satory network (Denis's machine)
# Script adds 65.108.215.200:9080 as second target WITHOUT removing existing 10.141.0.104:8581
bash /opt/nous-agaas/erap/tools/camera-dual-target.sh
```

#### Step 3c — Or subscribe each ЛУ camera programmatically

```python
import os, requests
from requests.auth import HTTPDigestAuth
from xml.etree.ElementTree import tostring, Element, SubElement

LISTENER_URL = "http://65.108.215.200:9080/"
CAMERA_USER = os.environ["CAMERA_LU_USER"]
CAMERA_PASS = os.environ["CAMERA_LU_PASS"]

def add_notification_target(ip: str) -> bool:
    """Non-destructively add our listener as a second push target."""
    # Step 1: GET existing config
    r = requests.get(
        f"http://{ip}/ISAPI/Event/notification/httpHosts",
        auth=HTTPDigestAuth(CAMERA_USER, CAMERA_PASS),
        timeout=10,
    )
    # Step 2: parse existing IDs, find max
    # Step 3: append new entry with id = max+1
    # Step 4: PUT combined list
    # Full implementation in erap/hikvision_isapi.py add_notification_target()
    from erap.hikvision_isapi import HikvisionISAPIClient
    client = HikvisionISAPIClient(ip=ip, username=CAMERA_USER, password=CAMERA_PASS)
    return client.add_notification_target("65.108.215.200", 9080)
```

**ISAPI2 camera-side config template reference** (Daniyar spec 2026-04-15):
- Existing BDL target: `10.141.0.104:8581/events/camera/hxml` (DO NOT remove — preserve as ID 1)
- Our target to add: `65.108.215.200:9080` as ID 2
- Protocol: HTTP, Auth: Digest

#### Step 3d — Verify subscription

```python
def verify_subscription(ip: str) -> bool:
    """GET /ISAPI/Event/notification/httpHosts — expect our listener host present."""
    r = requests.get(
        f"http://{ip}/ISAPI/Event/notification/httpHosts",
        auth=HTTPDigestAuth(CAMERA_USER, CAMERA_PASS),
        timeout=10,
    )
    return "65.108.215.200" in r.text or "9080" in r.text
```

#### Step 3e — Verify DB receives events

```bash
# Check current event count
ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/events.db 'SELECT COUNT(*) FROM events'"
# Expected: 154516 rows as of 2026-04-15 (25 columns)

# After subscribing a camera, trigger a test detection and re-check count
# Count should increase within 30-60 seconds
```

#### Step 3f — Debugging events-stop (observability-first, see AP-9)

If nothing arrives after subscription:

1. **Check listener stats FIRST** — `curl http://localhost:9080/stats` on VPS. If `total_events=0` since restart, cameras are not pushing to us — their push target has changed.
2. **Check camera push config** — GET /ISAPI/Event/notification/httpHosts (needs access to camera subnet)
3. **iptables** — verify port 9080 open: `ssh root@65.108.215.200 "iptables -L INPUT -n | grep 9080"`
4. **VPN route** — can VPS reach camera? `ping -c 1 10.170.1.3` (from VPS via VPN). Reminder: VPS has NO route to 10.235.* without VPN.
5. **Camera firewall** — some cameras block outbound HTTP. Check camera web UI → Network → Firewall.
6. **2026-04-05 gap** — cameras were re-pointed to 10.141.0.104:8581 (BDL private IP). Use `camera-dual-target.sh` to add dual-target from inside Satory network.

---

## Verification Checklist

Before declaring any camera operation "done" (per LESSON-085):

- [ ] **pytest gate passed** — `python3 -m pytest tests/test_camera_registry.py tests/test_hikvision.py -v --tb=short` → 23 tests pass
- [ ] **Listener stats healthy** — `curl http://localhost:9080/stats` → `total_events > 0` and `last_event` within expected time window
- [ ] **Camera push target verified** — GET /ISAPI/Event/notification/httpHosts confirms our VPS IP is listed
- [ ] **isapi_listener version** — must be v2.3+ (NOU-108 drop removed; all events saved to DB)
- [ ] **Credentials via env** — `echo $CAMERA_LU_USER` shows `oper`; not hardcoded anywhere
- [ ] **events.db row count increases** after camera subscription (within 30-60s of a vehicle detection event)
- [ ] **Network access confirmed** — any ISAPI camera config requires a machine in 10.235.*/10.170.* subnet; VPS and Air cannot reach cameras directly

---

## Anti-Patterns

### AP-1 — Never set ISAPI2 auth to None on production cameras
Require Digest. The Daniyar spec lists "Auth: None" for the camera-side template but this is for lab/testing only. Production cameras must use Digest auth to prevent unauthorized event injection.

### AP-2 — Do not commit CAMERA_LU_* creds to wiki or any git repo
Credentials live only in `/opt/nous-agaas/.env` on VPS (600 deploy:deploy) and `~/nous-agaas/.env` on Air (600 madia:staff). Never write them to wiki pages, SKILL.md files, or commit them to git.

### AP-3 — Do not assume every camera is pushing
Always verify via `curl http://localhost:9080/stats`. 145 ЛУ cameras are online but NOT configured to push events. After P3 activation, verify each subscription — do not bulk-subscribe and assume success.

### AP-4 — Camera types: THREE types (ЛУ, ПРК, ОВН) — not two, not APK
АПК (Аппаратно-Программный Комплекс) = general name for ALL camera complexes — it is NOT a camera type.
Correct `camera_type` values: `lu` (ЛУ — speed cameras on highways), `prk` (ПРК — intersection cameras), `ovn` (ОВН — overview video, no radar).
`camera_type="apk"` is WRONG. Reports showing "АПК cameras: 34" should say "ПРК cameras: 34".
Source: LESSON-023, LESSON-026.

### AP-5 — MRGN IDs and camera IPs are separate namespaces with no direct mapping
Excel registry uses MRGN-0201, MRGN-0202 etc. as camera IDs.
API and network use IP addresses (10.170.1.3, etc.).
No direct mapping table exists. Serve both datasets; frontend merges for display.
Future: Denis or мониторщики must provide MRGN→IP mapping table.
Source: LESSON-015.

### AP-6 — Camera model string (iDS-2CD9396-BIS) comes from camera self-report — not for public display without confirmation
Model comes from ISAPI /System/deviceInfo response (camera_monitor.py line 93: `model = _txt("model")`).
156 online cameras report: "iDS-2CD9396-BIS" (118) or "Hikvision iDS-2CD9396" (38). This is a real Hikvision Traffic Capture Camera product, not a hallucination. But Satory may not recognize this model name — they may know it by a different designation.
Rule: do NOT display camera model in UI/reports without Satory confirmation of the model name they use.
Source: LESSON-024.

### AP-7 — Photo retention (5 days) is shorter than violation retention (indefinite) — old violations have dead photo paths
Photo cleanup cron (`tools/photo_cleanup.sh`, daily 22:00) prunes photos older than ~5 days.
Violation rows in `violation_cards` are kept indefinitely. Result: violations older than ~5 days have `detection_photo_path` pointing to deleted files → HTTP 404 on photo fetch → violation cannot be sent to ERAP without evidence.
Fix: photo cleanup MUST check `violation_cards` — never delete a photo referenced by a non-finalized violation.
Frontend: `onError` handler shows "Фото недоступно" gracefully. Backend cleanup script must be corrected.
Source: LESSON-047.

### AP-8 — VPS and Air have NO route to 10.235.* or 10.170.* without VPN
```
VPS 65.108.215.200  → NO route to 10.235.* / 10.170.*
Air 100.122.219.22  → NO route to 10.235.* / 10.170.*
```
Any ISAPI configuration of cameras (subscribe_events, add_notification_target, firmware update, time sync) **requires a machine inside the Satory network** or an active VPN connection. Denis must run `camera-dual-target.sh` from inside Satory. Do NOT attempt direct ISAPI calls to cameras from VPS or Air without VPN.
Source: LESSON-102.

### AP-9 — Events stopped? Check push target FIRST — not the listener
When `curl http://localhost:9080/stats` returns `total_events=0` and listener responds to health check, the cameras have been re-pointed away from our VPS. Do NOT debug the listener — debug the camera push target.
Diagnostic order:
1. `curl http://localhost:9080/stats` → if 0 events since restart → cameras not pushing to us
2. GET /ISAPI/Event/notification/httpHosts (needs camera network access) → verify our IP is listed
3. If cameras point to 10.141.0.104:8581 (BDL) only → Denis must run `camera-dual-target.sh`
Source: LESSON-102 (Bug 1).

### AP-10 — `subscribe_events()` is DESTRUCTIVE — it overwrites ALL push targets
`PUT /ISAPI/Event/notification/httpHosts` with a list replaces the entire configuration. A single `<id>1</id>` in the body removes any other existing entry.
**Use `add_notification_target()` instead** — it GETs current config, checks if our endpoint is already present, and appends a new entry with `id = max_existing + 1`.
`subscribe_events()` is preserved but MUST only be used when you intend to replace ALL targets.
Source: LESSON-102 (Bug 2).

### AP-11 — Never filter events at DB ingest — filter at query layer (WHERE clause)
DB-level event filtering (e.g., dropping non-violations at ingest) breaks any metric needing total vehicle counts (Column A/B of detection-accuracy dashboard).
Rule: Save ALL events to DB. Filter in SQL WHERE clauses on read. Photo file writes CAN be filtered (they're expensive). DB row writes CANNOT.
The NOU-108-v2 filter bug (dropped all pass-throughs from 2026-04-02 to 2026-04-05) created a data gap that cannot be recovered.
Source: LESSON-102 (Bug 3).

---

## Output Format

All camera commands return structured results:
- **status:** `online` | `offline` | `pending_access` | `expired`
- **ip:** dotted quad
- **model:** Hikvision model string (e.g. `iDS-2CD9396-BIS`) — see AP-6 before displaying to users
- **firmware:** version string
- **calibration_valid:** boolean
- **response_ms:** integer or null
- **events_pushing:** boolean (after P3 — is camera actively pushing to our listener?)

---

## Files

| File | Location | Purpose |
|------|----------|---------|
| `camera_monitor.py` | `/opt/nous-agaas/erap/` (VPS) | Health check runner (concurrent, 5-min cycle) |
| `camera_registry.py` | `/opt/nous-agaas/erap/` (VPS) | CRUD registry + calibration tracking |
| `hikvision_isapi.py` | `/opt/nous-agaas/erap/` (VPS) | Low-level ISAPI client + `add_notification_target()` |
| `isapi_listener.py` | `/opt/nous-agaas/erap/` (VPS) | ISAPI event listener v2.3+, port 9080 (NOU-108 drop removed) |
| `event_parser.py` | `/opt/nous-agaas/erap/` (VPS) | Multipart MIME + XML parser |
| `events.db` | `/opt/nous-agaas/erap/data/` (VPS) | 25 columns, 154 516 rows as of 2026-04-15 |
| `camera_health.db` | `/opt/nous-agaas/erap/data/` (VPS) | SQLite health DB |
| `camera-dual-target.sh` | `/opt/nous-agaas/erap/tools/` (VPS) | Batch dual-target config — Denis runs from inside Satory network |
| `test_camera_registry.py` | `/opt/nous-agaas/erap/tests/` (VPS) | Registry tests (pytest gate) |
| `test_hikvision.py` | `/opt/nous-agaas/erap/tests/` (VPS) | ISAPI tests (pytest gate) |
| `.env` | `/opt/nous-agaas/` (VPS, 600 deploy:deploy) | CAMERA_LU_USER, CAMERA_LU_PASS, CAMERA_P_USER, CAMERA_P_PASS |
| `.env` | `~/nous-agaas/` (Air, 600 madia:staff) | Same vars (Air copy) |

---

## Pytest Gate

**Run before ANY production action (add, update, or bulk operation):**

```bash
cd /opt/nous-agaas/erap
python3 -m pytest tests/test_camera_registry.py tests/test_hikvision.py -v --tb=short
```

**Expected:** 23 tests pass. If any fail → STOP, do not proceed.

Smoke subset only:
```bash
python3 -m pytest tests/test_camera_registry.py -k "not slow" -v --tb=short
```

---

## Anti-Pattern AP-12: Assume receiver fault when events stop
When events stop flowing, the VPS receiver may be healthy but cameras stopped pushing.
**Always check both sides:** VPS listener health (port 9080) AND camera network connectivity.
Trigger was disk exhaustion (LESSON-124), but the actual break was camera-side network loss.
Denis must re-run dual-target config from inside the Satory 10.235.x.x network.

### AP-13 — Parsers that discard the raw body lose all replay capability
`isapi_listener.py` parses multipart events into DB columns + JPEG files, then discards the raw bytes. When Daniyar asked for the exact XML format, we had to synthesize a sample.
**Rule:** Always keep a sampled raw archive (env `ISAPI_RAW_SAMPLE_RATE`, default 0.1%, 100% for debug windows) with 14-day rotation in `data/raw/YYYY-MM-DD/`. One raw capture per 1000 events costs ~45 MB/day.
Detection: `[ -d "/opt/nous-agaas/erap/data/raw" ] || echo "GAP: no raw archive"`
Source: LESSON-107.

### AP-14 — Count UNIQUE camera IDs — never report raw row counts
Excel registry had 955 rows but only 109 unique cameras (rest were empty rows). Reporting `max_row` as camera count produces hallucinated numbers (e.g. "955 LU cameras").
**Rule:** Always `COUNT(DISTINCT camera_id)` or `len(set(ids))`. Cross-check Excel data against API data before reporting numbers.
Source: LESSON-012.

### AP-15 — Never depend on a single vendor-controlled push path; infrastructure ownership trumps vendor software lock
When a vendor (BDL/Mergen) "locks" camera configuration, the lock exists only at the management platform level. Satory owns the cameras, network (10.235.x.x, 10.170.x.x), switches, routers, and servers — the vendor has software access only. A vendor lock that blocks config changes is a management-software lock, not a hardware or network lock, and is always bypassable via one of these five levels (pick the least-invasive that works):
1. **Direct Camera Web UI** — Hikvision native HTTP:80 UI is independent of the management platform. Browser → `http://10.235.X.3` → login with oper creds → add second notification target. Vendor software does not see this change.
2. **Network Traffic Duplication (iptables TEE)** — on Satory's gateway/router, `iptables -t mangle -A PREROUTING -s 10.235.0.0/16 -d <vendor> -p tcp --dport 8581 -j TEE --gateway <next-hop>`. Zero camera changes; vendor sees nothing different; we get a copy.
3. **WireGuard Tunnel + ISAPI Polling** — WireGuard server at VPS, poller at `/opt/nous-agaas/erap/tools/isapi_poller.py`. Pure READ via `GET /ISAPI/Event/notification/alertStream` or `GET /ISAPI/Traffic/.../plates`. Vendor cannot block standard HTTP GETs.
4. **Switch Port Mirroring (SPAN)** — if cameras connect through a managed switch, enable SPAN to copy all camera traffic to a Satory-controlled port.
5. **Camera Factory Reset** — if vendor changed passwords: physically reset the hardware. Satory owns the device.

**Prevention rule (absorb into every camera deployment):** always maintain an independent READ path (polling) as backup to any push path. Infrastructure ownership is the ultimate trump card — keep WireGuard tunnel + poller ready even while push is working (defense in depth).
Source: LESSON-117.

### AP-16 — Lead the on-site executor; never accept narrative; verify every claim with raw command output

Camera/network work at Satory depends on a non-expert on-site executor (Denis Rykov primarily; sometimes Rahat / Satory IT / physical staff). Narrative replies like "не получилось", "реализовать не сможем", "камеры offline" WITHOUT attached command output are a **lazy-signal** — we cannot plan on them. Madi's directive (2026-04-17 session-42 close): *"he can be lazy and not smart enough, so double check him all the time, he can be useful to lead him and command him."*

**Rules when composing any message to an on-site executor:**

1. **Command, don't ask.** Numbered steps, exact copy-paste commands, pre-filled values (IPs, URLs, file paths). Never "figure out X and tell me" — always "run `<command>` and paste the output."
2. **No open-ended options.** Binary or small-enumerated multi-choice (а/б/в). Banned: "опиши ситуацию", "что думаешь", "попробуй что-нибудь". Allowed: "выбери букву", "пришли HTTP-код и первые 300 символов ответа".
3. **Verify every claim with raw output.** "Доступа нет" → demand `ssh -v` or login screenshot. "Камера упала" → demand `curl -v http://10.235.X.3/ISAPI/System/deviceInfo` stdout + HTTP code. Narrative claims go unverified; commands do.
4. **Pre-stage everything.** Scripts pre-placed on VPS (`/opt/nous-agaas/erap/tools/`) or inline-pasteable in the message. Never "напиши скрипт, который...". The one exception: a 1–5 line `curl` they paste verbatim.
5. **One action per message.** Multi-step messages stall at step 2. Send step 1 → wait for raw output → verify → send step 2.
6. **Lead with physical/low-skill work.** If possible, reduce executor's role to "воткни кабель / вставь эту строку / перешли пароль в личку". Technical judgment (RouterOS config, iptables, ISAPI XML) we do remotely once they give us access.
7. **Stall rule.** If executor silent >1h on a step with no known blocker, or replies narratively 2× without command output, **escalate to Madi** — don't wait multiple cycles. Switch to an alternate path that doesn't need them (e.g., ship small Linux box on-site, ask different person at Satory).

**Example pair (session 42, Denis + BDL MikroTik):**

❌ **Bad (open-ended, stalls):** "Денис, у вас есть доступ к роутеру? Можешь настроить iptables TEE или port-mirror?"

✅ **Good (runbook, binary):** *"ШАГ 1 — кто админ микротика, одной буквой: а — БДЛ / б — чужое железо / в — пароль у Сатори. ШАГ 2 (только если в) — скинь в личку: `IP:порт логин пароль`, дальше я сам. ШАГ 3 — проверь креды: `curl -s -u oper:'<пароль>' --digest -o /tmp/hik.xml -w "HTTP=%{http_code}\n" http://10.235.0.3/ISAPI/System/deviceInfo && cat /tmp/hik.xml`. Пришли HTTP-код + первые 300 символов."*

Difference: good version has 0 ambiguity, 3 concrete actions, 2-minute time budget, raw-output verification built in.

**Detection:** grep the last executor message for `\b(curl|ssh|HTTP=|вывод|output|200|401|403)\b`. If zero matches AND message >30 words → narrative reply, demand raw output before proceeding.

Source: session-42 Denis-bypass brainstorm (2026-04-17); `project_denis_handling.md` memory.

### AP-17 — BDL-detected access is political ammunition; L2-only until Phase-3 authorized reset (v2.8.0, 2026-04-20 session 52)

**Pattern:** [[azamat-bdl|Azamat @ BDL]] weaponizes authorized camera access events as political leverage against Satory. On Friday 2026-04-18, when Denis logged in with BDL-provided interim credentials (approved by BDL themselves earlier that day), Azamat reframed the login as unauthorized intrusion: *"зачем тогда вы заходили с помощью пароля и этих кодов?"* — attempting to build a case against Satory.

**Root cause:** BDL's network monitoring captures Layer-7 authentication events (ISAPI login, HikVision web UI session) and preserves them as log evidence. The political narrative is retroactive: a login BDL authorized today becomes "unauthorized intrusion" tomorrow if BDL's interests shift.

**Fix (binding):**
1. **Phase 0 + Phase 1 of the [[nous-gpu]] displacement trajectory stay L2-only.** Port-mirror at MikroTik core switch captures a copy of camera traffic at the hardware layer. TZSP-encapsulated packets flow to `obsrv` for decode. BDL's network monitoring operates at L7 (application-layer auth logs, ISAPI subscription registrations) — **L2 mirror traffic is invisible to them.**
2. **No L7 authentication against cameras from Nous infrastructure** (Mac, Air, Nous-GPU) until Phase 3 fires. Reading cameras via `curl -u admin:...` is permitted ONLY from `obsrv` on the Satory side, and ONLY with Daniyar's written authorization on record.
3. **Phase 3 (camera factory-reset + own-passwords) must be preceded by:**
   - Written Daniyar authorization in vault (not verbal)
   - [[roza|Роза]]'s official-letter to Управление пассажирского транспорта demonstrating customer-authorized maintenance
   - Chosen camera is unused or pre-transfer (no live-traffic impact)
4. **Communication discipline:** Azamat by name in BDL-reachable channels (Telegram with non-Nous participants, email to BDL) is banned. Vault is Satory-internal — name is safe here.

**Detection:** grep the recent transcript/task log for any `curl.*10\.(235|170|141)\.` or SSH against camera IPs from non-obsrv sources. Any hit without Daniyar-authorization-on-record = AP-17 violation.

**Cross-ref:** AP-15 (5-level bypass ladder — L2 SPAN / port-mirror = bypass level 4). AP-16 (lead the executor — Denis is the MikroTik operator for the L2 mirror).

Source: [[source-satory-meeting-2026-04-20-license-handover-bdl-access]] Decision 4 (operational-security); Daniyar's verbatim *"А сейчас кто-нибудь со стороны зайдет, ну я как бы лишний раз не запятствую. Назначена экспертиза по уголовному делу."*

### AP-18 — Camera-reset execution requires named-trained-authorized field executor (Vlad-hands pattern) (v2.8.0, 2026-04-20 session 52)

**Pattern:** Camera factory-reset + own-password-set is a multi-step Hikvision-specific procedure. Assigning it loosely ("кто-нибудь сбросит") produces stalls, misconfiguration, and AP-16-class narrative responses.

**Root cause:** Camera-level work is not Denis's default lane (network + VPN are his). It belongs to a specialized field engineer. Satory has [[vlad|Vlad]] in that role; prior sessions did not surface him, producing 5+ weeks of implicit blocking.

**Fix (binding for Phase 3):**

1. **Named executor:** [[vlad]] is the designated hands for all camera factory-reset + re-config work. Alternates: none currently. If Vlad unavailable, escalate to Daniyar for designation, do not default to Denis.
2. **Training-first:** Vlad must complete HikVision documentation study (iDS-2CD9396-BIS specifically — the ITCCAM-model) BEFORE any reset attempt. Madi's directive 2026-04-20: *"заставить выучить всю документацию по камерам, скорее всего много знает уже."* Create a training checklist in JIRA; Vlad reports completion in writing.
3. **Authorization-second:** Daniyar's written authorization in vault per AP-17 BEFORE Vlad touches a camera. Vendor-request path (Agant/HikVision → factory-reset password) via Роза OR factory-reset-via-hardware-button (Madi's explicit suggestion: *"кнопочка есть там"*) — Madi decides which path.
4. **Verify-third:** After reset + own-password-set, Vlad produces raw command output (per AP-16): `curl -u admin:'<new-password>' --digest http://<camera-ip>/ISAPI/System/deviceInfo` → HTTP 200 + full XML. Then ISAPI push-target re-point to Nous ingest endpoint. Then end-to-end event verified by Nous-GPU ingest-svc logs.
5. **Nous's role is RECEPTIVE, not driving:** our pipeline ingests whatever Vlad's reset camera produces. We do not drive Vlad's keyboard; we are ready when his output lands.

**Detection:** grep last Vlad-related task for `training|документаци|прочитал|изучил` + Daniyar-authorization-in-vault + verify-output. Missing any = AP-18 violation.

**Cross-ref:** AP-16 (lead the executor with command-not-narrative). AP-15 level 5 (factory reset = ultimate bypass).

Source: [[source-satory-meeting-2026-04-20-license-handover-bdl-access]] Decision 1; [[vlad]] entity.

### AP-19 — Preserve MADI enrichment contract — any new pipe is a drop-in replacement for BDL, not for MADI (v2.8.0, 2026-04-20 session 52)

**Pattern:** [[madi-program]] (Satory's in-house enrichment layer) has a strict input contract: it expects raw camera events and joins them with Excel-derived metadata (address, speed limit, certificate, LU/LVN ID) before submission to ERAP. A new pipe that emits differently-shaped events breaks MADI.

**Root cause:** Easy mistake to over-scope a Nous pipeline as "replace BDL AND MADI," producing a rewrite scope 10× larger than needed. The actual customer need is narrow: **replace BDL as data-plane provider; keep MADI as the enrichment boundary.**

**Fix (binding):**

1. **Nous port-mirror decoder output schema = BDL's original ISAPI push body schema.** MADI already parses this. No translation layer on our side. If BDL's XML format changes, ours changes in lockstep.
2. **Decoder writes events to the same VPS endpoint** (`10.141.0.104:8581`-equivalent = our listener at `65.108.215.200:9080` established pre-2026-04-05). MADI reads from there unchanged.
3. **Enrichment (address, speed limit, certificate) stays in MADI.** Do not replicate the Excel-import logic in the decoder. Keep responsibility boundaries clean.
4. **Confidence threshold ≥ 90% is MADI's call, not the decoder's.** Do not pre-filter events by confidence on the Nous side — ship everything with raw confidence scores intact.
5. **JIRA remains metadata source of truth.** If the decoder needs a camera lookup (e.g., "which camera is `10.235.0.3`?"), read from JIRA (via API or Excel snapshot), don't hardcode.
6. **Phase 5 (Cerebro displacement) is the ONLY time MADI's enrichment logic can be touched.** Before that, respect the contract.

**Detection:** grep decoder source for `if confidence >` or `address = ` or `certificate_number` — should be ABSENT on Nous side. If present, AP-19 violation.

**Cross-ref:** AP-11 (never filter at ingest; filter at query). AP-15 (infrastructure-ownership-over-vendor-lock — but MADI is OURS, not vendor; different logic). LAW-018 (data contract).

Source: [[source-satory-meeting-2026-04-20-license-handover-bdl-access]] — Madi's verbatim architecture explanation; [[madi-program]] entity.

### AP-20 — `0 / N online` is a network/event-freshness diagnosis, not a frontend diagnosis (v2.9.0, 2026-04-27 Codex audit)

**Symptom:** `satory.nousagaas.com` rendered correctly and `/api/proxy/cameras` returned valid JSON, but showed `0 / 281` online, `events_last_seen=2026-04-05T22:08:05.856+05:00`, `events_recent_count=0`, and all current poll checks failing. A naive agent could call the portal broken or try to patch React.

**Root cause chain from the live audit:**

1. `events.db` had `154516` rows but `MAX(event_time)=2026-04-05T22:08:05.856+05:00` — no fresh camera push events.
2. `wg show wg-satory latest-handshakes` returned `0`, `endpoints` returned `(none)`, and transfers were `0 0` — the peer has never handshaked in this boot context.
3. `ip route` had `10.235.0.0/16 dev wg-satory` but no route for `10.170.0.0/16`.
4. Pings/probes to `10.235.0.3` returned `Destination Host Unreachable`; `10.170.*` timed out/no route.
5. `camera_health.db` contained 38 historical `online` rows whose `last_check` was 2026-03-31; the API correctly downgraded them to `stale` while current 243-camera polls were offline/error.

**Rule:** before touching frontend, schemas, labels, or dashboard copy for a camera-health red state, run this proof bundle and classify the root cause:

```bash
curl -s https://satory.nousagaas.com/api/proxy/cameras | python3 -m json.tool | head -80
ssh root@65.108.215.200 'sqlite3 /opt/nous-agaas/erap/data/events.db "select count(*), max(event_time), max(created_at) from vehicle_events;"'
ssh root@65.108.215.200 'wg show wg-satory latest-handshakes; wg show wg-satory endpoints; wg show wg-satory transfer'
ssh root@65.108.215.200 'ip route | grep -E "10\\.170|10\\.235|wg-satory"'
ssh root@65.108.215.200 'sqlite3 /opt/nous-agaas/erap/data/camera_health.db "select status, count(*) from camera_status group by status;"'
```

**Classification:**

- No fresh events + no WireGuard handshake = on-site/VPN path down, not frontend.
- Fresh `last_check` with all current probes offline/error = camera network unreachable or credentials/path broken.
- Historical `online` rows older than 1h are stale inventory evidence, not live availability.
- A fix requires restoring the Satory network path or on-site push target first; React work is deleted by Musk Step 2 until that proof changes.

**Detection:** any task saying "fix Satory camera dashboard" must include the five proof outputs above, or it is under-specified.

### AP-21 — Camera credentials committed to git history require filter-repo + pre-receive hook, not just tree-scrub (v2.10.0, 2026-04-30)

**Incident:** `oper/***REDACTED***` (LU cameras, 10.170.x.x) and `admin/***REDACTED***` (Perekrestok cameras, 10.235.x.x) were committed to the wiki git repo in plaintext. Session 26 scrubbed the current tree but did NOT rewrite history. The credential remained in 29+ commits spanning 2026-04-06 → 2026-04-23 — recoverable by `git log -p` from any clone made during that window.

**Root cause chain:**
1. `pages/systems/cameras.md` added credentials in a table on the initial commit (2026-04-06).
2. `raw/satory/denis-2026-04-15-credentials.md`, `code/erap/camera_monitor.py` (hardcoded CREDS dict), Claude-export JSONs, MEMORY.md, and HANDOFF files propagated the credential across sessions.
3. Session 52 (2026-04-20) Denis confirmed `admin:***REDACTED***` working via curl — this re-introduced the credential into MEMORY.md and HANDOFF files AFTER a partial cleanup.
4. Parallel sessions kept pushing pre-rewrite history back to VPS after each `git filter-repo` run, re-introducing dirty commits via merge commits.

**Fix applied (2026-04-30 session):**
1. `git filter-repo --replace-text <(printf 'CREDENTIAL==>***REDACTED***') --force` run 3× on VPS bare repo until all parallel session pushes were caught.
2. Force-reset all clones: Air + Mac main + 8 Mac worktrees (including 5 in `/Users/madia/.config/superpowers/worktrees/` and 3 in `/private/tmp/`).
3. **Pre-receive hook installed** at `/root/nous-agaas/obsidian-wiki.git/hooks/pre-receive` — rejects any push containing the credential in any object. Permanent protection.
4. Password in Air `.env` (`~/nous-agaas/.env`) still has the old value. **Denis must rotate** the physical camera passwords before the old credential is fully harmless.

**Rules (binding from v2.10.0):**

1. **Credentials go ONLY in `.env` files** (600 perms, gitignored). Never in wiki pages, SKILL.md, HANDOFF, MEMORY.md, code files, or raw/ documents.
2. **If a credential appears in a git diff or `git grep`, STOP** — do not commit. Redact first, commit second.
3. **Tree scrub alone is insufficient.** A `git rm` commit leaves the credential in `git log -p`. Always follow with `git filter-repo --replace-text` + force-push + reset ALL clones (including worktrees and `/tmp/` paths).
4. **Parallel sessions break single-pass filter-repo.** Stop ALL auto-sync (launchd on Air: `launchctl stop com.nous.auto-checkpoint com.nous.wiki-sync`) AND verify no active Claude/Codex sessions are pushing BEFORE running filter-repo. Install a pre-receive hook IMMEDIATELY after filter-repo to reject re-introduction.
5. **Verification command after cleanup:**
   ```bash
   # Must return 0 on all three:
   ssh root@65.108.215.200 "cd /root/nous-agaas/obsidian-wiki.git && git log --all --oneline -S 'CREDENTIAL' | wc -l"
   ssh air "cd ~/nous-agaas/wiki && git log --all --oneline -S 'CREDENTIAL' | wc -l"
   cd /path/to/wiki && git reflog expire --expire=now --all && git gc --prune=now && git log --all --oneline -S 'CREDENTIAL' | wc -l
   ```
6. **Password rotation is mandatory** regardless of history cleanup. History cleanup prevents future exposure; rotation invalidates the leaked credential for anyone who already cloned the dirty history.

**Detection trigger:** `git grep 'CAMERA_LU_PASS\|CAMERA_P_PASS\|oper/\|admin/' HEAD` in any wiki repo → stop, redact, filter-repo, rotate.

Source: session-100 (2026-04-30) security remediation. Pre-receive hook: `/root/nous-agaas/obsidian-wiki.git/hooks/pre-receive`.

---

## Brain-aware invocation (gstack v0.18.0.0, 2026-04-17)

Before any camera-level work (UUID lookup, IP change, push config), `mcp__gbrain__search` with the camera UUID or IP — prior session may have documented a hardware/network gotcha (e.g., LESSON-021 / AP-6 about ЛУ push pre-config). Use fast keyword search, not hybrid `query`. After action, `mcp__gbrain__add_timeline_entry slug="pages/skills/camera-management/skill"` with one-line "Camera <UUID>: <action>, <outcome>". See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

## Rules absorbed from lessons

### Imperative rules (LESSON absorption batch 2026-04-16)

1. **Count UNIQUE camera IDs, never report raw Excel row counts as camera counts.** Cross-check Excel data against API `/System/deviceInfo` before quoting numbers. (LESSON-012)
2. **LU cameras online with 0 events means ISAPI push subscriptions are not configured.** Online = responds to ping/health-check. Pushing = configured to POST events to our listener. Do not confuse the two. (LESSON-021)
3. **Events stopped? Check camera push target BEFORE debugging the listener.** `curl http://localhost:9080/stats` returning `total_events=0` with a healthy listener means cameras are not pushing to us. Use `add_notification_target()`, never `subscribe_events()` (destructive). (LESSON-102)
4. **Store one raw protocol sample per N events; replay without a sample is impossible.** Set `ISAPI_RAW_SAMPLE_RATE` env var (default 0.001 = 0.1%). Keep 14-day rotation in `data/raw/`. When a partner asks for the exact format, `ls data/raw/` must return files. (LESSON-107)
5. **When events stop, check BOTH sides of the pipeline — receiver AND camera push source.** A healthy receiver does not mean data is arriving. Also monitor disk space proactively (original trigger was disk exhaustion on 2026-04-01). Add alerts at 90% disk usage. (LESSON-124)
6. **Vendor-lock on camera config is bypassable — infrastructure ownership trumps management-platform lock.** Satory owns cameras, network, switches; vendor has software access only. When blocked: direct Hikvision UI → iptables TEE duplication → WireGuard + ISAPI polling → SPAN → factory reset (see AP-15). Never depend on a single vendor-controlled push path; always maintain an independent READ path (polling) as backup. (LESSON-117)

- **RAW-SATORY-2026-04-15-DANIYAR-ISAPI:** ISAPI(XML) SDK is the agreed protocol between Satory and ЕРАП. Camera-side config template documented in `raw/satory/daniyar-isapi-spec-2026-04-15.md`. Existing BDL target: 10.141.0.104:8581 (preserve). Our target: 65.108.215.200:9080 (add as dual-target).
- **RAW-SATORY-2026-04-15-DENIS-CREDS:** ЛУ admin credentials are `CAMERA_LU_USER` (oper) / `CAMERA_LU_PASS` (<REDACTED-see-.env>). Stored only in `.env` files on VPS and Air. Never commit to wiki or git.
- **CONCEPT-ISAPI:** ISAPI passive HTTP push architecture. 51 APK cameras were active pre-2026-04-05. 145 ЛУ cameras online but NOT configured to push. Events stopped 2026-04-05 22:08 +05:00 — cameras re-pointed to BDL (10.141.0.104:8581). Fix: camera-dual-target.sh (Denis runs from inside Satory).
- **GOST 34.10-2015 only** — existing `crypto.py` uses OLD GOST 34.310-2004. Any new signing MUST use `gostcrypto` library with GOST 34.10-2015.
- **109 cameras have expired calibration** — speed violations from these cameras are legally void. `is_calibration_valid()` returns False for them.
- **Ridder/Altay cameras** (10.170.34.3+) — unreachable until Board coordinates access. Timeout ≠ dead; mark as `status=pending_access`.

### Laws absorbed

- **LAW-002 (Violation Auto-Fine Rules):** Cameras are the physical source of every tracking event that can become a violation. The LAW-002 threshold — `excess = vehicle_speed - speed_limit` with no tolerance subtraction, violation iff `excess >= 10 km/h` — is applied downstream (in `police_dashboard.py` and the dashboard API), but camera-management's job is to guarantee the upstream data is accurate: calibration in-date (109 cameras with expired calibration produce legally-void violations), plate recognition confidence preserved in the event record (≥90% auto-fine, <90% human review), and NO DB-level filter at ingest (save ALL events, filter at query — see AP-11). If camera-management loses any of these, LAW-002 cannot be enforced correctly at the fine-issuance layer.

- **LAW-018 (Data Contract Camera):** Cameras MUST save ALL events to the database at ingest time — never filter, drop, or deduplicate at the ingestion layer. Filtering happens exclusively at the SQL query layer (WHERE clauses). The NOU-108 filter bug (2026-04-02 to 2026-04-05) proved that ingestion-time filtering creates unrecoverable data gaps. This law reinforces AP-11 (never filter events at DB ingest) and is the formal codification of the data contract between camera pipeline and downstream consumers.

---

## Network layout

```
VPS (65.108.215.200)
  └── NO VPN route to camera subnets by default (AP-8)
  └── isapi_listener.py :9080 (receives ISAPI event pushes FROM cameras)
  └── events.db (25 cols, 154K rows — ALL events saved, filter at query layer only)

Air (100.122.219.22)
  └── NO VPN route to camera subnets by default (AP-8)

Satory network (requires on-site machine or VPN):
  ├── 10.170.1.3 – 10.170.33.3    ЛУ speed cameras, USK (active)
  ├── 10.170.34.3 – 10.170.209.3  ЛУ cameras, Ridder/Altay (pending_access)
  └── 10.235.0.3 – 10.235.33.3    ПРК intersection cameras, USK (active)
       └── Currently push to: 10.141.0.104:8581 (BDL — internal Satory target)
       └── Need to ALSO push to: 65.108.215.200:9080 (our VPS — dual-target)

BDL (Сатори internal):
  └── 10.141.0.104:8581/events/camera/hxml (preserve — do NOT replace)
```

Tested camera model: **iDS-2CD9396-BIS** (from ISAPI /System/deviceInfo self-report — AP-6).

Auth: Digest auth on all cameras. Use env vars, never hardcoded strings.

---

## Timeline

- 2026-04-13 | v1.0.0 — initial skill (CRUD, health, ISAPI client)
- 2026-04-13 | v1.1.0 — timezone fix (UTC+6→UTC+5), ONVIF enable, event subscribe command
- 2026-04-15 | v2.0.0 — Wave-2 absorption: Daniyar ISAPI2 template, Denis ЛУ creds, iDS-2CD9396-BIS reference, 2026-04-05 events-stop gap, P3 activation runbook.
- 2026-04-15 | v2.1.0 — Wave-3: absorbed LESSON-015, 023, 024, 026, 047, 058, 102. Added AP-4 through AP-11 (camera types ЛУ/ПРК/ОВН, MRGN↔IP namespace split, model string caveat, photo retention gap, observability-first, events-stop diagnosis, subscribe_events destructive, NOU-108 DB-level drop). Added Verification Checklist. Updated network layout with BDL dual-target. Fixed camera_type="apk" → "prk"/"lu"/"ovn".
- 2026-04-15 | v2.1.1 — Wave-4 cross-reference: LAW-002 added to `absorbs_laws`. New "Laws absorbed" subsection explains how camera-management's upstream data quality (calibration, plate confidence, no DB-ingest filter) is a prerequisite for LAW-002 enforcement downstream in satory-dashboard. Added LAW-002 + satory-dashboard links in See also.
- 2026-04-16 | v2.3.0 — Absorbed LESSON-012/021/102/107/116a (session 32 triage). Added AP-13 (raw protocol sample archive), AP-14 (unique camera ID counting). Added 5 numbered imperative rules in "Rules absorbed from lessons" section.
- 2026-04-16 | v2.3.1 — Absorbed LAW-018 (data contract camera: save ALL events to DB, filter at query). Formal codification of AP-11.
- 2026-04-16 | v2.5.0 — Absorbed LESSON-117 (vendor-lock bypass). Added AP-15 (5-level bypass pattern: direct UI → iptables TEE → WireGuard + ISAPI poll → SPAN → factory reset) + imperative rule #6 ("infrastructure ownership > vendor software lock; always maintain independent READ path").
- 2026-04-17 | v2.6.0 — Session 37: added Brain-aware invocation (gstack v0.18.0.0 adoption). Before camera UUID/IP work, `mcp__gbrain__search` for prior findings; after, `add_timeline_entry`. No new LESSON (RULE ZERO).
- 2026-04-18 | v2.7.0 — Session 49-B (BDL-bypass brainstorm awaiting Denis): added AP-16 (lead the on-site executor, never accept narrative, verify every claim with raw command output). Source: Madi's directive session-42 close + Denis stall pattern (WG client unused 36h, MikroTik reply "реализовать не сможем" with no attached evidence). Runbook-vs-narrative example pair included. No new LESSON (RULE ZERO).
- 2026-04-20 | v2.8.0 — Session 52 triple absorption from Satory all-hands meeting ([[source-satory-meeting-2026-04-20-license-handover-bdl-access]]) + Denis's Telegram reply. Added AP-17 (BDL-detected access is political ammunition — [[azamat-bdl]] weaponized Denis's authorized login; L2-only port-mirror for Phase 0-1, no L7 auth from Nous until Phase-3 authorized reset). Added AP-18 (Camera-reset execution requires named-trained-authorized field executor — [[vlad]] as designated hands for Phase-3, training + Daniyar authorization + verify output before touching camera). Added AP-19 (Preserve [[madi-program]] enrichment contract — Nous pipe replaces BDL data-plane, NOT MADI; decoder output = BDL's original ISAPI schema; enrichment stays in MADI; JIRA remains metadata source-of-truth; no confidence pre-filter). Fourth absorption — Denis's 2026-04-20 reply confirmed BDL runs a config-reversion auto-config script (Phase-2 reverse-engineer target, captured in [[denis]] entity + [[source-satory-meeting-2026-04-20-license-handover-bdl-access]]). No new LESSON (RULE ZERO).
- 2026-04-27 | v2.9.0 — Codex full-factory audit: added AP-20 after proving Satory portal `0 / 281` online was a network/event-freshness failure, not a frontend failure. Live evidence: events stale since 2026-04-05, `wg-satory` no handshake/endpoints/transfers, `10.235/16` routed into dead WG, no `10.170/16` route, 38 historical online rows correctly downgraded to stale. No new LESSON (RULE ZERO).
- 2026-04-30 | v2.10.0 — AP-21: credential-in-history remediation. `oper/***REDACTED***` (LU cameras) and `admin/***REDACTED***` (Perekrestok) found in git log via session-26 audit. Fix: stop Air auto-sync + install pre-receive hook on VPS bare repo + run `git filter-repo --replace-text` 3× (race condition with parallel session required 3 passes) + reset all 8 Mac worktrees + Air clone. Password rotation pending Denis (hardware change on ~196 cameras). Binding rules codified: credentials in .env only, stop ALL auto-sync before filter-repo, pre-receive hook is permanent gate, verify with `git log --all -S 'CREDENTIAL' | wc -l` = 0 on all three repo locations.

---

## See also

- [[isapi-concept]] — ISAPI passive HTTP push architecture
- [[hikvision_isapi]] — ISAPI protocol details
- [[camera_registry]] — Registry schema and calibration rules
- [[daniyar-isapi-spec-2026-04-15]] — Daniyar's ЕРАП ISAPI2 camera-side config template
- [[denis-2026-04-15-credentials]] — Denis credential handoff
- [[LESSON-102-isapi-events-stop-camera-reconfigure-dual-target]] — root-cause of 2026-04-05 events stop
- [[HANDOFF-2026-04-13-session5]] — Deployment context
- [[AGAAS-ARCHITECTURE-DECISION-v2-GOLDEN]] — Why single-skill not multi-agent
- [[LAW-002-autofine]] — Violation auto-fine thresholds; camera events feed the violation pipeline
- [[SKILL]] — downstream consumer that enforces LAW-002 at fine-issuance
- [[LESSON-117-bdl-blocks-camera-config-ownership-bypass]] — vendor-lock bypass root lesson (AP-15)
