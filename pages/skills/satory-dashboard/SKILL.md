---
tier: 3
type: skill
name: satory-dashboard
description: How to keep satory.nousagaas.com truthful and useful as the Satory client operating surface replacing all BDL and Cerebro capabilities, then exceeding them with AGaaS autonomous agents — backend freshness contract applied across all /api/* endpoints, camera_monitor scheduling, LAW-016 frontend lock, self-healing chain, events-flowing-again watcher, entity-nature classification before any network/access ask, product-value checks against full BDL/Cerebro displacement, BDL/Cerebro replacement gate, and agent autonomy proof.
version: 1.14.0
tags: [skill, satory, dashboard, freshness, camera_health, police_dashboard, frontend-locked, self-healing, api-contract, entity-classification]
related: [LESSON-103, LESSON-123, LESSON-110, LAW-016, LAW-002, LESSON-021, LESSON-046, infrastructure/SKILL.md, satory-api-freshness-audit-2026-04-15, asyl-nit-vpn-request-2026-04-15]
last_updated: 2026-05-18
triggers:
  - Satory АПК / ЕРАП status
  - ПО работает с АПК
  - фиксирует ли АПК
  - аппаратно-программный комплекс
  - APK in Satory traffic-enforcement context
  - satory dashboard health
  - camera freshness
  - portal broken
  - cameras not reflecting in dashboard
  - violation count wrong
  - API endpoint freshness
  - dashboard shows stale data
  - LAW-002 violation threshold
  - camera_monitor scheduling
  - NIT VPN access request
  - government network access ask
  - PSK from third party
  - replacing BDL
  - replacing Cerebro
  - client portal
  - Satory client operating system
  - AGaaS autonomy
  - full displacement matrix
absorbs_lessons: [LESSON-103, LESSON-123, LESSON-109, LESSON-110]
absorbs_laws: [LAW-002]
title: "satory-dashboard v1.14.0"
---

# satory-dashboard v1.14.0

> Keep `satory.nousagaas.com` telling the truth — even when the camera fleet dies, VPN is unplugged, or the frontend is locked.

## P0-A — Client product mandate (BDL + Cerebro replacement)

This is not a marketing website. `satory.nousagaas.com` is the client operating surface for Satory VKO and must be judged by whether it replaces the two incumbent dependency layers:

| Layer | Incumbent | Nous/Satory replacement must own |
|---|---|---|
| Data plane | BDL / Mergen / BigDataLab | Camera/APK access, event ingestion, violation classification, evidence package generation, ERAP/SmartBridge handoff, freshness and audit logs |
| Ops and analytics plane | Cerebro | VMS-like operator workflows: camera map, live/archival visibility, event search, violation review, outage reporting, analytics, role-based operator experience |

Therefore a dashboard check is incomplete if it only says "site loads." Every check must answer:

1. Which BDL/Cerebro workflow does this screen or endpoint replace?
2. Is the workflow backed by live/fresh data rather than placeholders or stale tables?
3. Can a Satory operator use it without asking an engineer?
4. Does it reduce dependency on BDL/Cerebro today?

If the answer is "loads but does not replace an operational workflow," record it as partial, not done.

The full scoreboard lives at [[satory-agaas-full-displacement-capability-matrix-2026-04-26]]. Use it when deciding whether a dashboard/API/task is actually valuable.

### AP-14 — In Satory/ERAP context, АПК is traffic-enforcement hardware, not Android APK

When an operator asks in Russian/Kazakhstan traffic context whether "АПК фиксирует" or "ПО работает с АПК", interpret АПК as аппаратно-программный комплекс: camera/radar/event/evidence/ERAP pipeline. Do not answer with Android APK/mobile-app language, and do not answer with internal AI substrate plumbing (`gbrain`, `Todoist`, `Obsidian`) unless the operator explicitly asks about the AI factory itself.

Before replying, ground the answer in the operational evidence pages:

1. [[satory-erap-testing-status-2026-05-13]]
2. [[apk-status-bot]]
3. [[skills/camera-management]]
4. [[skills/smartbridge-soap-client]]

The correct operator-facing answer must state what is actually fixed/recorded for ERAP readiness: event/detection, timestamp, camera/APK identity, location, photo/video evidence, speed/violation metadata, pipeline status, missing proof, and responsible owner. If the exact АПК/object is unknown, ask for object/IP/serial while still explaining the dashboard/proof model.

### AP-15 — Do not collapse LU landmarks into the target VAR camera

When a Satory operator says "ЛУ100" or another site object is an ориентир / one-switch context and then asks whether we see "камера Вар" or another radar/camera on nearby ports, treat the target camera as unresolved until the exact IP/serial/event source is proven. Do not assume the landmark IP is the VAR camera, and do not claim access from a single private IP check.

Correct answer shape:
1. State what was actually checked: receiver health, raw intake, parsed `vehicle_events`, and direct reachability for the known IP only.
2. Preserve the topology clue: same object/switch may have two ports/two cameras; VAR may be a separate endpoint.
3. Ask for one observable proof path: a test event with exact timestamp, a local LAN discovery result, or the second camera IP/serial.
4. Keep credentials out of group replies; if access details are needed, exchange them privately and store only redacted context in the vault.

Detector: `tools/tests/test_factory_orchestration_policy.py::test_satory_var_camera_access_query_routes_to_chatgpt_codex` and `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_satory_var_camera_access_query_routes_to_codex`.

## P0 — The Freshness Contract (read this first)

The frontend at `satory.nousagaas.com` is **locked** to Vercel deploy `satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app` (asset `index-BSiWURaO.js`) per **LAW-016**. You cannot ship a new bundle. The bundle renders whatever backend says — blindly.

Therefore:

**Every dict-shaped `/api/*` endpoint that serves data derived from an async-populated table MUST:**

1. Return a `data_freshness` object with these canonical keys (applied across 7 endpoints as of v1.2.0):
   ```json
   "data_freshness": {
     "as_of":             "<ISO8601 now>",
     "events_last_seen":  "<ISO8601 or null>",    // when any endpoint reads events.db
     "events_age_seconds": <int or null>,
     "events_stale":       <bool or null>,          // true when events_age_seconds > 3600
     "poll_last_run":     "<ISO8601 or null>",    // when endpoint reads camera_health.db
     "audit_last_seen":   "<ISO8601 or null>"     // when endpoint reads audit_trail.db
   }
   ```
2. Downgrade per-item status to `"stale"` / `"unknown"` when `now - source_last_write > max_age`.
3. Recompute from a live signal when one is available (e.g. `/api/cameras` cross-references `events.db` for push-based truth).
4. **Never change response SHAPE** — the frontend is locked (LAW-016). If an endpoint currently returns a bare JSON array, only ADD to its entries; do NOT wrap in an object. See AP-5.

**Implementation:** use the `_data_freshness(event_db=?, cam_db=?, audit_db=?)` helper defined in `police_dashboard.py` near `get_cam_db()`. Single source of truth.

If you skip this, the dashboard lies confidently forever the moment the updater stops. See LESSON-103. If you mutate shape, you brick the locked frontend. See LESSON-123 / AP-5.

## Endpoints and their contracts (v1.2.0 state)

| Endpoint | Shape | Has envelope? | Source |
|---|---|---|---|
| `/api/health` | dict | ✅ v1.2.0 (added `today_events`, `today_violations`, envelope) | events.db |
| `/api/cameras` | dict | ✅ v1.0.0 (events + poll + stale per-camera) | camera_health.db + events.db |
| `/api/stats` | dict | ✅ v1.2.0 (+ `scope: "all_time"`) | events.db |
| `/api/violations` | dict | ✅ v1.2.0 | events.db |
| `/api/events` | dict | ✅ v1.2.0 | events.db |
| `/api/map` | dict | ✅ v1.2.0 | events.db + camera_health.db |
| `/api/erap` | dict | ✅ v1.2.0 | events.db |
| `/api/tracking` | **array** | ❌ skipped (AP-5 shape-lock) | events.db (plate search) |
| `/api/system-events` | **array** | ❌ skipped (AP-5 shape-lock) | audit_trail.db |
| Single-item, searches, writes, auth, not_implemented stubs | — | N/A | — |

## Architecture at a glance

```
┌────────────────────────┐       ┌───────────────────────────────┐
│  camera_monitor.py     │──┬───▶│  /opt/nous-agaas/erap/data/   │
│  */5 * * * * cron      │  │    │    camera_health.db            │
│  (poll HTTP ISAPI)     │  │    │    (camera_status table)       │
└────────────────────────┘  │    └───────────────┬───────────────┘
                            │                    │
┌────────────────────────┐  │    ┌───────────────▼───────────────┐
│  isapi_listener.py     │──┴───▶│    events.db                   │
│  :9080 (push receive)  │       │    (vehicle_events table)      │
└────────────────────────┘       └───────────────┬───────────────┘
                                                 │
                                 ┌───────────────▼───────────────┐
                                 │ police_dashboard.py            │
                                 │ /api/cameras                   │
                                 │ merges: events (push truth)    │
                                 │       + camera_status (poll)   │
                                 │ returns data_freshness envelope│
                                 └───────────────┬───────────────┘
                                                 │ Vercel proxy
                                 ┌───────────────▼───────────────┐
                                 │ satory.nousagaas.com (LOCKED) │
                                 │ Vite/React SPA                │
                                 │ renders status field verbatim │
                                 └───────────────────────────────┘
```

## Phase P1 — Daily health check (run this any time the user says "the site is broken")

```bash
# 1. Is the locked bundle still live?
CURRENT_JS=$(curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1)
[ "$CURRENT_JS" = "index-BSiWURaO.js" ] && echo "LOCK OK" || echo "LOCK BROKEN — DO NOT DEPLOY, RESTORE"

# 2. Is the backend up?
curl -s -o /dev/null -w "backend %{http_code}\n" https://api.nousagaas.com/api/health

# 3. Is /api/cameras returning freshness envelope?
curl -s https://api.nousagaas.com/api/cameras | python3 -c "
import sys, json; d = json.load(sys.stdin)
print('total:', d.get('total'), 'online:', d.get('online'), 'stale:', d.get('stale'))
print('freshness:', d.get('data_freshness', 'MISSING — fix not deployed'))
"

# 4. Is the poll cron running?
ssh root@65.108.215.200 'crontab -l | grep camera_health_wrapper' || echo "CRON MISSING — reinstall"

# 5. Is camera_health.db moving?
ssh root@65.108.215.200 'stat -c "mtime: %y" /opt/nous-agaas/erap/data/camera_health.db'
# mtime > 10 min old = cron broken

# 6. Is events.db moving?
ssh root@65.108.215.200 'stat -c "mtime: %y" /opt/nous-agaas/erap/data/events.db'
# mtime > 1 h old in working-hours = push pipeline broken
```

## Phase P2 — If `/api/cameras` lacks `data_freshness` field

You're looking at a pre-session-24 backend. Re-apply the patch:

- File: `/opt/nous-agaas/erap/police_dashboard.py`
- Handler: `elif path == "/api/cameras":` (~line 2005)
- Reference implementation: `police_dashboard.py.bak-2026-04-15-session24-freshness` on VPS

Patch must:

1. Query `events.db` for `SELECT DISTINCT camera_ip FROM vehicle_events WHERE event_time >= (now - 10 min)`.
2. Mark those IPs `"online"` with `online_source="events"`.
3. For remaining cameras, compute `age = now_kz() - last_check`. If `age > 1h`, override `status = "stale"`, `online_source = "stale_data"`.
4. Add `data_freshness: {poll_last_run, events_last_seen, events_recent_count, as_of}`.
5. Add per-camera `last_check_age_seconds`.

After patching: `systemctl restart spectra-dashboard` and verify via `curl https://api.nousagaas.com/api/cameras | python3 -m json.tool | head`.

## Phase P3 — If `camera_health.db` mtime is stale (no cron writing)

```bash
# Install the cron if missing
ssh root@65.108.215.200 '(crontab -l; echo "*/5 * * * * /root/nous-agaas/tools/camera_health_wrapper.sh >> /root/nous-agaas/logs/camera_health.log 2>&1") | crontab -'

# Wrapper must source .env and use .venv Python
ssh root@65.108.215.200 'cat /root/nous-agaas/tools/camera_health_wrapper.sh'
# Expected:
# #!/bin/bash
# set -e; set -a; source /opt/nous-agaas/.env 2>/dev/null || true; set +a
# cd /opt/nous-agaas/erap
# exec /opt/nous-agaas/.venv/bin/python3 camera_monitor.py 2>&1
```

Cron will run even when VPN is down. Result on VPS-without-VPN: all cameras go `offline` with fresh `last_check`. My backend patch then classifies those as `"offline"` (not stale) because `last_check` is fresh. **This is honest** — it means "VPS just tried and couldn't reach them."

When VPN comes up, polls succeed and cameras transition to real statuses **without any code change**. Zero babysit.

## Phase P4 — If events.db is stale (push pipeline broken)

Not fixable from VPS-only work. Requires:

1. Verify `isapi_listener.py` on port 9080 is alive and externally reachable: `ss -tln | grep 9080` + `nmap` from outside.
2. Coordinate with **Denis** (camera DevOps) to confirm APK cameras have HTTP notification target = `<vps-public-ip>:9080/isapi/Event/notification/alertStream` (Hikvision ISAPI format).
3. If VPN was changed, re-verify NAT path from camera VLAN to VPS public IP.

### P4-A — Camera dashboard red-state proof before any frontend work

When the portal shows `0 / N` online cameras, prove the transport and event path before touching React or Vercel. The locked frontend only displays backend truth.

Run this exact bundle:

```bash
curl -s https://satory.nousagaas.com/api/proxy/cameras | python3 -m json.tool | head -80
ssh root@65.108.215.200 'sqlite3 /opt/nous-agaas/erap/data/events.db "select count(*), max(event_time), max(created_at) from vehicle_events;"'
ssh root@65.108.215.200 'wg show wg-satory latest-handshakes; wg show wg-satory endpoints; wg show wg-satory transfer'
ssh root@65.108.215.200 'ip route | grep -E "10\\.170|10\\.235|wg-satory"'
ssh root@65.108.215.200 'sqlite3 /opt/nous-agaas/erap/data/camera_health.db "select status, count(*) from camera_status group by status;"'
```

Interpretation:

- `events_last_seen` older than 1h and `events_recent_count=0` means the push/event path is stale.
- `wg-satory latest-handshakes=0`, `(none)` endpoint, and `0 0` transfer means the Satory WG peer is not connected.
- `10.235.0.0/16 dev wg-satory` with no peer handshake is a dead route.
- Missing `10.170.0.0/16` route means LU probes cannot work from VPS, regardless of dashboard code.
- Historical `online` rows in `camera_health.db` with old `last_check` are stale inventory, not live availability.

If these conditions hold, the action is network/on-site restoration and task escalation, not frontend patching.

## Phase P5 — If LAW-016 lock is broken (wrong JS asset served)

**DO NOT PUSH** a new deploy. Run the restore runbook:

```bash
# From Mac or Air
vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
# Verify
curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js'
# Must equal: index-BSiWURaO.js
```

See [[website-restore-runbook-2026-04-09]].

## Known lies in the locked bundle (cannot fix without lifting LAW-016)

| Frontend label | Reality | Honest fix needs |
|---------------|---------|------------------|
| "НАРУШЕНИЙ СЕГОДНЯ 154,516" | That is lifetime total, not today's count | Frontend rewrite |
| License plate ticker "886BK16: 42× / 62км/ч" | Hard-coded demo data | Frontend rewrite |
| "система активна" (always green) | No correlation to actual health | Frontend rewrite |
| "64.2% онлайн" (when data fresh, before my patch) | Relied on stored camera_status without freshness check | Fixed in session 24 |

## Anti-Patterns

### AP-1 — Trusting daemon-level scheduling for ops-critical polls

Symptom: a polling task stops silently when its host daemon crashes; nobody notices until someone visits the UI.

**Why:** daemons can crash, be killed, be migrated, be forgotten. Cron/systemd is visible in `crontab -l` and `systemctl list-timers`.

**How to apply:** if the output of a polling task populates a dashboard, schedule it via cron/systemd. Period. Add a log-gap alarm (if log file mtime > 2× interval → alert).

### AP-2 — Backend serves async-populated data without freshness envelope

Symptom: the updater dies on day N, the dashboard still shows confident "online" numbers on day N+30.

**Why:** UIs can't detect staleness if the API doesn't tell them. A locked frontend makes this fatal.

**How to apply:** any endpoint reading from a table written by a background job must return a `data_freshness` object AND downgrade per-row status when stale. See this skill's P0.

### AP-3 — "Online" from one signal only

Symptom: poll fails (VPN down) and the UI says 0/N even though APK cameras are actively pushing events.

**Why:** ops reality has multiple truth sources (push webhooks, poll, metric heartbeat). Relying on one makes the UI lie in asymmetric failure modes.

**How to apply:** combine signals. `online = recent_event OR recent_successful_poll`. Mark the `online_source` so debugging is trivial.


### AP-5 — Shape-lock: when the frontend is frozen, response shape is immutable

**LESSON-123 / finding 1.** `satory.nousagaas.com` reads `/api/tracking` as a bare array: `data.filter(...)`. Wrapping it to `{items: [...], data_freshness: {...}}` would hard-break the page — `.filter` doesn't exist on objects.

**Rule:**
- Under LAW-016, you can ADD fields to dict responses but NEVER change shape.
- Array endpoints stay arrays until LAW-016 is lifted.
- New endpoints designed under LAW-016 should wrap items as `{items: [...], ...}` from day 1 so future envelopes are additive.

**How to verify the frontend's assumption before changing shape:**
```bash
# Grep the locked bundle for consumer patterns
grep -oE '[a-zA-Z_]+\.(filter|map|forEach|length)' /tmp/satory_bundle.js | grep -i <endpoint-keyword>
```
If you see `.filter(` on the response, it's an array. Don't wrap.

### AP-6 — ISO 8601 string compare is a trap with variable-precision timestamps

**LESSON-123 / finding 2.** The first `satory_events_watcher.py` compared two ISO timestamps as strings:
```python
"2026-04-05T22:08:05.856" > "2026-04-05T22:08:05"  # True — .856 sorts AFTER
```
→ the longer (with-ms) string sorts after the shorter → watcher thought events advanced → false-positive Telegram alert fired.

**Rule:**
- **Never** compare ISO 8601 timestamps as strings unless you control the serialization on both sides (same precision, same tz).
- Parse to `datetime.fromisoformat(s.replace("Z", "+00:00"))`. Compare as `(lhs - rhs).total_seconds() >= threshold`.
- For watcher/alerter scripts: add a secondary guard (`age_seconds < threshold`) so one normalization bug can't false-fire.

### AP-4 — Violation vs tracking: apply the correct KoAP threshold (LAW-002)

**LAW-002.** In the ERAP speed camera system, NOT every camera detection event is a violation. The dashboard MUST apply the correct business rules:

**Violation = tracking event WHERE speed excess >= 10 km/h AND plate confidence >= 80%**

Classification rules (KoAP Article 592):
| Condition | Classification |
|-----------|---------------|
| Speed excess < 10 km/h | Tracking only (NOT a violation) |
| Speed excess >= 10 km/h AND plate confidence >= 80% | Violation (auto-fine eligible) |
| Speed excess >= 10 km/h AND plate confidence < 80% | Tracking only (plate unreadable) |
| No speed excess regardless of plate | Tracking only |

Example: 154,000 events/day = TRACKING (every car detected). Violations = only the subset where speed excess >= 10 km/h AND plate readable.

Rules:
- Never display raw event count as "violation count" — this inflates fines by 100x and violates KoAP
- The `/api/violations` endpoint MUST apply the threshold filter
- The `/api/cameras` count must show cameras with at least 1 real violation, not cameras with any detection
- Plate confidence threshold: below 80 = plate unreadable in court = cannot issue fine

### AP-7 — Classify entity nature before proposing any network/access ask

**LESSON-110.** During session 24 I wrote an action packet asking Asyl to obtain a VPN PSK from NIT for our VPS. Asyl responded: *«Нит не даст никогда доступ такой. that was silly of you to even ask.»* NIT is a Kazakh government IT body, not a commercial VPN vendor. Government orgs don't grant third-party VPN tunnels to foreign-hosted private VPS as a convenience — the request has no path to yes.

**Classification matrix to apply BEFORE drafting any access-ask packet:**

| Entity type | Appropriate ask channel | Expected timeline |
|---|---|---|
| Commercial vendor (API provider, cloud host, SaaS) | Technical / support ticket, SLA-backed | Hours–days |
| Government / regulatory body (НИТ, МВД, ЕРАП, МЦРИАП, city administration) | **DO NOT** send as technical ask. Route via the COMMERCIAL PARTY that already has the contract (e.g. Satory Company Ltd) — OR choose an operational workaround that doesn't require the access | Months → never |
| NGO / civic / community | Case-by-case, usually informal | Unpredictable |
| Individual operator (DevOps contact like Denis) | Treat as coordination, not authority — they can only do what they already have rights to do | Same-day if they agree |

**Signal of a #2 entity**: a blocker that's been "tracked" unchanged for months across multiple sessions. Multi-month immobility is structural, not scheduling. Stop packaging it as a coordination problem.

**How to apply:**
- Any packet that starts with "Ask X for credentials/access to Y" — first answer: *what is X's entity type?*
- If #2, rewrite as either (a) a commercial-party-first ask to whoever holds the contract, or (b) an operational workaround.
- Don't spend tokens on technical specs (PSK type, subnet list, security commitments) for a #2 — it's wasted work and sends a silly signal when the packet arrives.

See [[LESSON-110-classify-entity-before-access-ask]] for the full retrospective and the retracted packet [[asyl-nit-vpn-request-2026-04-15]].

### AP-8 — Never share one SWR key across fetchers with different return shapes (LESSON-016)

**LESSON-016.** Two components fetched the same URL (`/api/proxy/cameras`) using different SWR fetchers. Header's fetcher returned a raw dict; Dashboard's fetcher returned a `Camera[]`. SWR caches by key — whichever loaded first won. Header loaded first → cache contained dict → Dashboard ran `cameras.filter()` on a dict → TypeError → BLACK SCREEN.

**Rule:** An SWR key is a promise about the cached value's shape. If two components need different transforms of the same URL, use different keys (`"header:/api/proxy/cameras"` vs `"/api/proxy/cameras"`), or share one fetcher and transform at use-site. Never have two fetchers whose return types differ mapped under the same key.

**Detection:** before committing any new `useSWR(...)` or `useSWRInfinite(...)` call, grep for the exact key string across the codebase. If any other site uses the same key with a different fetcher, either merge the fetchers or fork the key.

### AP-9 — JWT MFA upgrade = issue NEW token, never mutate claims (LESSON-074)

**LESSON-074.** JWTs are signed and immutable. When a user completes TOTP and their session should lose the `mfa_pending: true` claim, the only correct flow is to ISSUE A NEW JWT and overwrite the cookie. Mutating the old JWT is mathematically impossible; attempting to "update claims" means your code isn't actually JWT-based.

**Rule for MFA-over-JWT flows:**
1. **Login handler:** if the account has MFA, issue JWT with `mfa_pending: true`, return `{"mfa_required": true}`.
2. **Auth middleware:** when a JWT carries `mfa_pending: true`, allow ONLY `/api/mfa/*` and `/api/auth/*`; return 403 `{"error": "mfa_required"}` for everything else.
3. **MFA verify handler:** on success, issue a NEW JWT without `mfa_pending`, set via `Set-Cookie` on the response. The client now presents the new token on subsequent requests; the old one remains valid until expiry but is locked to the `/api/mfa/*` surface.
4. **Never** attempt `session.pop("mfa_pending")` or similar mutation on a JWT-derived claim object — it's a no-op that gives the illusion of progress.

**Test contract:** the MFA verify response MUST carry `Set-Cookie: <new-jwt>`. Integration test asserts (a) cookie header present, (b) new token decodes without `mfa_pending`, (c) subsequent request with the new token accesses a protected route (not 403).

### AP-10 — "Website works" is not enough; prove client-ops replacement value

**Session 2026-04-26.** A live audit proved `satory.nousagaas.com` still renders on the locked bundle and authenticates, but Madi corrected the frame: this is the client product surface for Satory, and it must help replace Cerebro and BDL. A cosmetic website pass can hide the real failure: the UI loads while the replacement workflows are incomplete or unusable.

**Rule:** every Satory portal audit must include a replacement matrix:

| Workflow | Current owner | Portal/API proof required |
|---|---|---|
| Camera/APK fleet health | BDL data plane | `/api/proxy/cameras` fresh counts, per-camera status, last-check age, source of truth |
| Violation ingestion and legal classification | BDL + ERAP handoff | `/api/proxy/violations` filtered by LAW-002, evidence fields, pending/submitted ERAP status |
| VMS/operator visibility | Cerebro | map, live/archival visibility, search, roles, no placeholder-only screens |
| Outage and accountability reporting | Cerebro/BDL informal reporting | system events, audit trail, freshness envelope, daily report |
| Client task control | human coordination + Notion/Todoist | Satory-scoped task queue only; personal Todoist/Notion must stay untouched |

**Pass condition:** a route or endpoint is green only when it is (a) reachable, (b) populated with fresh live data, (c) tied to a named BDL/Cerebro replacement workflow, and (d) usable by Satory operators. If any of those are missing, the result is yellow/red even if HTTP and React are fine.

**Immediate 2026-04-26 example:** production render was green; source-of-truth was red/yellow; camera health was red (`0 / 281` online); Recharts warnings were yellow. Therefore the portal is alive but not yet replacement-complete.

### AP-11 — Full displacement means all incumbent capabilities plus AGaaS autonomy

**Session 2026-04-26, Madi correction #2.** The replacement target is not "some BDL/Cerebro workflows." It is everything BDL and Cerebro can do, plus an AGaaS agent layer that makes the system almost fully autonomous.

**Rule:** every Satory work item must be mapped to one of these layers:

1. **BDL/Mergen data plane** — APK/camera access, event ingestion, violation classification, evidence package, ERAP/SmartBridge handoff, metrology/certification, credentials, audit trail.
2. **Cerebro VMS/operator plane** — live feeds, map, archive/search, roles, camera tree, event dashboard, face/vehicle/video analytics, reports, exports, high availability.
3. **AGaaS agent plane** — fleet doctor, event ingestion, violation QA, ERAP submission, VMS operator assistant, detector trainer, report agent, librarian, task sync, security/cost agents.

If a task maps to none of these, apply Musk step 2 and delete/defer it.

### AP-12 — Probe egress before asking for camera reconfig (s2148/s0501, 2026-05-01)

**Failure mode:** When the Satory ingest pipeline goes stale, the temptation is to forward Denis the dual-target script and ask him to run it on hundreds of cameras. That's a heavy-touch ask: it requires running on each camera/network, depends on credentials, and reverses cleanly only if you know it ran cleanly. If the Satory egress firewall blocks `:9080` outbound to our VPS, the script "succeeds" silently and we still see zero events — burning a Denis cycle and not learning anything.

**Rule:** Two-step ladder. **Always probe egress with one `curl` BEFORE the dual-target script.** The probe is 60 seconds, zero risk, and tells us in one command whether the Satory network can reach our endpoint at all.

**Mechanical gate:**
```
# B-step-1 (probe — Denis runs this; 60 sec, zero risk)
curl -v --max-time 5 http://65.108.215.200:9080/health
# Expected on success: HTTP/1.1 200 OK + body "OK"

# B-step-2 (dual-target — only if B-step-1 returns 200; THREE-PASS to avoid blind PUT)
# Pass 1: dry-run --limit 1   → see PLAN for one camera, no PUT
# Pass 2: dry-run (no limit)   → see PLAN for ALL cameras, no PUT
# Pass 3: live (no flags)      → PUT changes
bash /opt/nous-agaas/erap/tools/camera-dual-target.sh --dry-run --limit 1
bash /opt/nous-agaas/erap/tools/camera-dual-target.sh --dry-run
bash /opt/nous-agaas/erap/tools/camera-dual-target.sh
```

Vault canonical copy: `tools/camera-dual-target.sh` (md5 `36aa93bf`). VPS mirror at `/opt/nous-agaas/erap/tools/`. The `--dry-run` and `--limit N` flags were added s2148→s0501 to prevent blind PUTs against ~50 cameras.

**Pre-flight (our side, before Denis runs the probe):**
- `ssh root@<vps> "ss -tlnp | grep 9080"` → must show `LISTEN` with PID
- `curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://<vps>:9080/health` from outside Satory → must return `200`
- `iptables -L INPUT -n | grep 9080` or `ufw status | grep 9080` → must show `ALLOW`

**4-branch decision tree on Denis's output** (saves a round-trip per outcome):

| Output contains | Verdict | Next |
|---|---|---|
| `HTTP/1.1 200 OK` | ✅ egress works | proceed to B-step-2 dual-target |
| `Connection timed out` | 🟡 egress firewall blocks 9080 outbound | request firewall rule OR fall back to Path A (VPN) |
| `Connection refused` | 🔴 our listener died between pre-flight and probe | re-verify our `:9080`; investigate listener |
| `Could not resolve host` (with raw IP) | 🔴 transparent HTTP proxy / SSL-only egress | expose `:9443` with cert |

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/satory-dashboard/skill`. Companion content in `pages/dashboards/revenue-blockers.md` Path-B-step-1 section.

### AP-13 — BDL/Cerebro replacement requires the replacement gate, not portal uptime

**2026-05-15 failure mode.** A portal can be HTTP-green while the replacement claim is false. On the live VPS, `:9080/health` and `/api/health` both returned HTTP 200, but `vehicle_events` was still stale from 2026-04-05, `raw_events` contained only quarantined parser-error intake, LAW-002 classifications were historical, and the ERAP queue had no current transitions. That is a live system surface, not a proven BDL/Cerebro replacement.

**Rule:** before claiming BDL or Cerebro is replaced, run:

```bash
python3 tools/bdl_cerebro_replacement_gate.py --json
```

The gate must be GREEN for any replacement claim. A green website, healthy OpenClaw, or fresh camera-health poll is insufficient by itself.

**Pass condition:** all of these must be green together:

1. VPS ISAPI listener reachable.
2. Fresh parsed `vehicle_events` prove BDL-free camera/APK ingestion.
3. Fleet health is current and operator-usable.
4. LAW-002 classification exists on fresh events.
5. ERAP/SmartBridge queue states are current and visible.
6. Operator portal is reachable and backed by fresh events, not stale tables.

**Interpretation rules:**

- Recent `raw_events` with `parse_status=quarantined` are intake/noise, not camera replacement proof.
- Historical LAW-002 classifications prove capability, not current operation.
- Current but degraded fleet health is a yellow blocker, not green.
- Cerebro replacement stays blocked until the BDL data plane is green; otherwise the operator portal is only displaying stale substrate.

**Autonomy target:** routine monitoring, reporting, memory capture, and safe software/data repairs should run at L3-L4 autonomy. Human approval remains for legal submissions, credential rotations, protected production deploys, budget commitments, government/vendor communications, and roadmap exposure to BDL/Cerebro.

**Evidence standard:** a "replacement" claim must state which incumbent capability is now covered, what live proof was run, what autonomy level is active, and what human gate remains.

## Brain-aware invocation (gstack v0.18.0.0, 2026-04-17)

Before touching any `/api/*` endpoint, camera_monitor, police_dashboard flow, or deploy, `mcp__gbrain__search` with the component name + "satory" — past deploys and regressions (JS hash `index-BSiWURaO.js` lock, SWR cache shape-lock, JWT session) often share root-cause DNA. Fast keyword search only, not hybrid `query`. After work, `mcp__gbrain__add_timeline_entry slug="pages/skills/satory-dashboard/skill"` with "<component>: <change>, JS hash <hash>". See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

## Rules absorbed from lessons

- **LESSON-103** — Satory dashboard lies when camera DB is stale. Rooted 3 causes: missing cron, no VPN, frontend lock. Fix: freshness envelope in backend + `*/5` cron.
- **LESSON-123** — API evolution under a locked frontend: shape-adds only (AP-5); ISO timestamp compare requires datetime parsing (AP-6).
- **LESSON-110** — Classify entity nature before any network/access ask; government ≠ technical vendor (AP-7).
- **LESSON-123 (reinforced):** Under a locked frontend, API can only ADD fields to dict responses; never change response shape. Array endpoints stay arrays. See AP-5.
- **LESSON-109:** Never compare ISO 8601 timestamps as strings; parse to datetime via fromisoformat(), require minimum forward delta >=1s before declaring state change. A watcher that false-fires and auto-retires becomes silently deaf. See AP-6.
- **LESSON-021** — 145 LU cameras "online" but 0 events — push-based ISAPI must be configured per camera.
- **LESSON-046** — 59 cameras registered without credentials — they'll always auth_error.
- **LAW-016** — Never redeploy satory.nousagaas.com. Fix must live in backend.

## Verification checklist

- [ ] `curl https://api.nousagaas.com/api/cameras` returns `data_freshness` field
- [ ] `crontab -l` on VPS shows the `camera_health_wrapper.sh` every-5-min entry
- [ ] `stat -c %y /opt/nous-agaas/erap/data/camera_health.db` within last 10 min
- [ ] Dashboard header at `satory.nousagaas.com` matches API truth (0/N stale, or real live counts)
- [ ] Log file `/root/nous-agaas/logs/camera_health.log` has recent entries
- [ ] Replacement matrix completed: BDL data plane, Cerebro ops plane, ERAP handoff, reporting, task-control surfaces
- [ ] `python3 tools/bdl_cerebro_replacement_gate.py --json` is GREEN before any "BDL/Cerebro replaced" claim
- [ ] Any "working" claim names the exact client workflow that now needs less BDL/Cerebro help
- [ ] Task maps to the full displacement matrix: BDL layer, Cerebro layer, or AGaaS agent layer
- [ ] Autonomy level stated: L0 manual, L1 assisted, L2 read-only tool use, L3 controlled write, L4 self-repair, L5 business-autonomous

## Rules absorbed from laws

- **LAW-002:** Violation = speed excess >= 10 km/h AND plate confidence >= 80%. Raw event count != violation count. See AP-4.

- 2026-04-15 | v1.1.0 — Wave 4: added AP-4 (violation threshold LAW-002). absorbs_laws: [LAW-002].
## Timeline

- v1.14.0 — 2026-05-18: added AP-15 after Satory group context clarified that LU100 can be an ориентир / same-switch landmark with two ports and two cameras, while the requested VAR radar camera may be a separate endpoint. Future answers must not collapse the landmark IP into the target camera; they must state exactly what was checked and ask for test-event time, LAN discovery, or the second camera IP/serial. No new LESSON (RULE ZERO).
- v1.13.0 — 2026-05-18: added AP-14 after Telegram `/ask` answered Asyl's "ПО работает с АПК, фиксирует что-то?" as if APK meant Android/mobile package and internal gbrain/Todoist tracking. Root cause: context routing did not bind Cyrillic АПК/ЕРАП/operator wording to the Satory dashboard/camera evidence domain. Rule: in Satory traffic-enforcement context, АПК means аппаратно-программный комплекс; replies must ground in event/evidence/ERAP status, not AI substrate internals. No new LESSON (RULE ZERO).
- v1.5.0 — 2026-04-17 (session 36): absorbed 2 UNMATCHED dream-cycle lessons. AP-8 (SWR key shape-lock across fetchers, LESSON-016), AP-9 (JWT MFA verify = new token not mutation, LESSON-074). No new LESSON files (RULE ZERO).
- v1.6.0 — 2026-04-17: Session 37 — added Brain-aware invocation (gstack v0.18.0.0 adoption). Before any `/api/*` endpoint or component work, `mcp__gbrain__search` + save after. No new LESSON (RULE ZERO).
- v1.7.0 — 2026-04-26: Madi corrected website frame from "site check" to client operating product replacing BDL and Cerebro. Added P0-A product mandate and AP-10 replacement matrix: "website works" requires fresh data + named BDL/Cerebro workflow replacement, not just HTTP/React green.
- v1.8.0 — 2026-04-26: Madi clarified replacement means all BDL/Cerebro capabilities plus AGaaS autonomous agents. Added AP-11 and linked the full displacement matrix: BDL data plane + Cerebro VMS/operator plane + AGaaS agent plane, with autonomy level proof required.
- v1.9.0 — 2026-04-27: Codex full-factory audit added P4-A camera red-state proof. `0 / 281` online on the live portal must first prove event freshness, `wg-satory` handshake/endpoints/transfers, `10.235/10.170` routes, and `camera_health.db` status counts before any frontend work. No new LESSON (RULE ZERO).
- v1.10.0 — 2026-05-01 (session s2148→s0501): pipeline still dead at day 26 because Path B has been a heavy-touch ask (run dual-target on hundreds of cameras, blind to whether Satory egress permits it). Added **AP-12** — two-step ladder: ALWAYS probe egress with one `curl -v http://65.108.215.200:9080/health` from inside Satory net BEFORE the dual-target script. Pre-flight checked our side bulletproof (`:9080` listening PID 834871, external HTTP 200 OK in 172ms, firewall ALLOW v4+v6). Decision tree maps Denis's 4 likely curl outcomes (200/timeout/refused/DNS-fail) to one next action each, eliminating the round-trip class. Companion update in `pages/dashboards/revenue-blockers.md` Path-B-step-1. No new LESSON (RULE ZERO).
- v1.11.0 — 2026-05-01 (session s0501): pre-staged B-step-2 so the moment Denis's probe returns 200 we don't lose another round-trip negotiating the dual-target script. Mirrored `/opt/nous-agaas/erap/tools/camera-dual-target.sh` into vault at `tools/camera-dual-target.sh` (md5 `36aa93bf`, original on VPS backed up to `.bak.s2148`). Added `--dry-run` and `--limit N` flags so Denis can preview against 1 camera, then all cameras, before the final live PUT. AP-12 mechanical gate updated to require the three-pass (dry-1 → dry-all → live) protocol, not a blind PUT against ~50 cameras. revenue-blockers.md Path-B-step-2 carries the Russian forwardable text. No new LESSON (RULE ZERO).
- v1.12.0 — 2026-05-15: added AP-13 and `tools/bdl_cerebro_replacement_gate.py` after live proof showed portal/listener green but replacement red: `vehicle_events` stale since 2026-04-05, `raw_events` 9/9 quarantined, fleet current but 38/281 online, LAW-002 only historical, ERAP queue stale. Future BDL/Cerebro replacement claims require this gate GREEN, not just HTTP or factory green.
- v1.4.0 — 2026-04-16: Absorbed LESSON-109 (ISO timestamp string compare trap — parse to datetime, require >=1s delta). Reinforced LESSON-123 rules (shape-lock + ISO compare). Evidence: bulk lesson absorption session.
- v1.3.0 — 2026-04-15 session 24 retrospective. Added AP-7 (classify entity before access ask) after Asyl rejected the naive NIT VPN packet. Absorbs LESSON-110. Path chosen going forward: stay push-only; Denis's dual-target is the sanctioned channel.
- v1.2.0 — 2026-04-15 session 24 phase 2. Audit swept `/api/*`; 7 dict endpoints now carry the envelope. New anti-patterns AP-5 (shape-lock) and AP-6 (ISO string compare). `satory_events_watcher.py` deployed on Air. Absorbs LESSON-123.
- v1.1.0 — 2026-04-15 (autopilot). AP-4 for KoAP violation threshold added (Wave 4 / LAW-002).
- v1.0.0 — 2026-04-15 session 24. Created after LESSON-103. Codified: freshness envelope, every-5-min cron, events-based online signal, LAW-016 interaction.
