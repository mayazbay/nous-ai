---
tier: 3
type: skill
name: metrology-cert-tracker
description: Tracks metrological calibration (поверка) expiry for Satory VKO cameras. Generates ЦСМ ВКО renewal application lists in CSV and Russian-language application text. Cameras with expired certs cannot legally issue speed fines (Order 62-NQ).
triggers:
  - metrology calibration
  - camera certification expired
  - legally-void violations
  - camera calibration tracking
  - verification certificate
  - ГОСТ calibration
  - КоАП calibration compliance
version: 1.2.0
last_updated: 2026-05-25
tags: [metrology, calibration, certs, vko, legal, csm, cameras]
author: Madi Ayazbay
requires:
  - python: ">=3.10"
  - packages: [pytest]
  - modules: [erap.camera_registry, erap.config]
  - no network required (works on registry data, no VPN needed)
title: "metrology-cert-tracker v1.2.0"
---

# metrology-cert-tracker v1.2.0

Tracks calibration certificate (поверка) status for all cameras in the Satory VKO network.

**Legal basis:** Приказ МЮ РК №62-НҚ — cameras must be re-certified annually. Expired cameras:
- ❌ CANNOT issue speed or red-light fines (legally void, court-challengeable)
- ✅ CAN still capture visual violations (seatbelt, phone, parking)

**Current state (as of 2026-05-25, v1.2.0 ROOT-CAUSE CONFIRMED):** 🔴 **TRACKER REPORTS 0 CAMERAS — empty registry, not data drift.** Per v1.2.0 AP-2 investigation: `/opt/nous-agaas/erap/data/erap_dev.db` exists (24,576 bytes, mtime 2026-03-17), `camera_registry` table schema is **intact**, but the table was **never populated** — 0 rows since database creation. The April 2026 "109 expired certs" figure in v1.0.0 must have come from a different data source (likely a working copy that was lost OR a manual one-off load). The 5,800 Hikvision cameras referenced in `erap/camera_registry.py` source comments were never imported. Fix requires external data source — see § Action packet below.

**Module:** `/opt/nous-agaas/erap/metrology_cert_tracker.py` (VPS at `root@65.108.215.200`; NOT on Air-host filesystem; OpenClaw container mounts the same path)

---

## TRAPS — READ BEFORE ANYTHING

1. **3-month lead time at ЦСМ ВКО** — applications must be filed IMMEDIATELY. Every day of delay = another day cameras can't issue speed fines = revenue loss.
2. **Batch size 30 per application** — ЦСМ ВКО physically processes ~30 cameras per visit. Split large lists into batches automatically.
3. **No cert date ≠ valid cert** — cameras with empty `calibration_date` are treated as expired (status `expired`, `days_overdue=9999`). They appear in the application list.
4. **calibration_max_days = 365** (config, DO NOT change) — set by Order 62-NQ. Auto-computed: `calibration_valid_until = calibration_date + 365 days`.
5. **NO PERSONAL DATA in output** — only camera serial numbers, models, addresses. No driver/plate data. Safe for Hetzner processing.

---

## Commands

### `metrology summary`
Print expiry status counts.

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.metrology_cert_tracker import MetrologyCertTracker

tracker = MetrologyCertTracker()
s = tracker.get_summary()
print(f"Total cameras:    {s['total_cameras']}")
print(f"Expired:          {s['expired']}  ← cannot issue speed fines")
print(f"Expiring soon:    {s['expiring_soon']}  (within 30 days)")
print(f"Valid:            {s['valid']}")
print(f"Most overdue:     {s['most_overdue_days']} days")
print(f"Report date:      {s['report_date']}")
```

---

### `metrology export-csv [--all]`
Export expired cameras to CSV for ЦСМ ВКО submission.

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.metrology_cert_tracker import MetrologyCertTracker

tracker = MetrologyCertTracker()

# Expired only (for ЦСМ submission)
csv_text = tracker.export_csv(expired_only=True)
with open('/tmp/csm_vko_expired_cameras.csv', 'w', encoding='utf-8') as f:
    f.write(csv_text)
print("Saved to /tmp/csm_vko_expired_cameras.csv")

# All cameras (for full audit)
csv_all = tracker.export_csv(expired_only=False)
with open('/tmp/all_cameras_cert_status.csv', 'w', encoding='utf-8') as f:
    f.write(csv_all)
```

**CSV columns:** №, Серийный номер, Модель, IP-адрес, Тип камеры, Город, Адрес установки, №поверочного свидетельства, Дата последней поверки, Действительно до, Просрочено (дней)

---

### `metrology generate-application`
Generate ЦСМ ВКО application letters (Russian text, batched by 30).

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.metrology_cert_tracker import MetrologyCertTracker

tracker = MetrologyCertTracker()
applications = tracker.generate_application_text(batch_size=30)

print(f"Generated {len(applications)} application(s)")
for i, app_text in enumerate(applications, 1):
    path = f'/tmp/csm_application_{i}.txt'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(app_text)
    print(f"Application {i} saved to {path}")
    print(app_text[:300])
    print("...")
```

**Output:** Russian-language application addressed to РГП «КазИнМетр» — Филиал ВКО, signed by ТОО «Spectra ITS», referencing Order 62-НҚ.

---

### `metrology validate`
Validate all cert date fields for data integrity (quality gate).

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.metrology_cert_tracker import MetrologyCertTracker

tracker = MetrologyCertTracker()
errors = tracker.validate_cert_dates()

if not errors:
    print("All calibration dates are valid.")
else:
    print(f"{len(errors)} validation error(s):")
    for e in errors:
        print(f"  {e['camera_id']}: {e['field']} = {e['value']} → {e['error']}")
```

---

### `metrology expiring-soon [DAYS]`
Cameras expiring within N days (default 30). Plan ahead.

```python
import sys; sys.path.insert(0, '/opt/nous-agaas/erap')
from erap.metrology_cert_tracker import MetrologyCertTracker

tracker = MetrologyCertTracker()
expiring = tracker.get_expiring_soon(days=60)
for s in expiring:
    days_left = -s.days_overdue
    print(f"{s.camera_id} | {s.ip_address} | expires in {days_left} days ({s.calibration_valid_until})")
```

---

## Pytest Gate

**Run before ANY production action:**

```bash
cd /opt/nous-agaas && python3 -m pytest erap/tests/test_metrology.py -v --tb=short
```

**Expected:** 17 tests pass.

Full combined gate (camera-management + metrology):
```bash
cd /opt/nous-agaas && python3 -m pytest erap/tests/test_camera_registry.py erap/tests/test_hikvision.py erap/tests/test_metrology.py -q 2>&1 | tail -3
# Expected: 40 passed
```

---

## Key file paths

| File | Purpose |
|------|---------|
| `/opt/nous-agaas/erap/metrology_cert_tracker.py` | Core tracker + CSV/text export |
| `/opt/nous-agaas/erap/tests/test_metrology.py` | 17 tests (pytest gate) |
| `/opt/nous-agaas/erap/camera_registry.py` | Data source (`get_expired_cameras`, etc.) |
| `/opt/nous-agaas/erap/config.py` | `calibration_alert_days=30`, `calibration_max_days=365` |

---

## ЦСМ ВКО submission workflow

```
1. Run `metrology summary` → confirm expired count
2. Run `metrology validate` → 0 errors required
3. Run `metrology generate-application` → generates /tmp/csm_application_*.txt
4. Print + sign + stamp (ТОО Spectra ITS печать)
5. Deliver to: г. Усть-Каменогорск, РГП «КазИнМетр» Филиал ВКО
6. Track batch status in registry notes field
```

---

## See also
- [[camera-management]] — SKILL.md v1.1.0 (registers cameras, manages status)
- [[camera_registry]] — Registry schema, `get_expired_cameras()`
- [[bdl-cerebro-replacement-gate]] v1.2.0 AP-6 — the sibling state-transition-tracking doctrine for the BDL/Cerebro replacement gate; AP-1 below mirrors that discipline.

## Anti-patterns

### AP-1 — State-of-system tracking must land in Timeline same-session (2026-05-25, v1.1.0)

**What happened:** Original skill body (v1.0.0, written ~2026-04) hard-coded "Current state (April 2026): 109 cameras have expired calibration certs." That was true on the day of writing. Skill had no `## Timeline` section, no AP set, so when the underlying camera_registry changed (likely cleared/wiped during Mergen's ERAP reset workstream 2026-05-09 — see `pages/tenants/satory/tasks/mergen-erap-reset-apk-receiver-program-2026-05-09-*.md`), the skill body did not get updated. Audit on 2026-05-25 ran the live tracker on VPS (`MetrologyCertTracker().get_summary()`) and got `total_cameras=0, expired=0, expiring_soon=0, valid=0` — direct contradiction of the body assertion. Madi (or any agent reading the skill cold) would have acted on the stale 109-figure when ЦСМ ВКО application planning is actually blocked on registry re-population first.

**Rule:** any skill that asserts an operational state ("N cameras are X", "Y violations pending", "Z certs expired") in its body MUST: (a) include a bracketed `(as of YYYY-MM-DD)` qualifier on the assertion; (b) have a `## Timeline` section; (c) land a Timeline entry whenever the asserted state materially changes (transition rule, mirroring [[bdl-cerebro-replacement-gate]] AP-6). The discipline applies symmetrically to skills with mechanical verifiers AND to skills whose runtime is "Madi will read it and act." The verifier-backed flavour also gets a queued `tools/test_<skill>_state_freshness.sh` detector (classifier-AP), but the rule itself is not gated on tooling — Timeline-with-date qualifiers is the always-on minimum.

**Cross-ref:** [[bdl-cerebro-replacement-gate]] v1.2.0 AP-6 (the same-class doctrine at a tier-2 skill); [[session-operating-contract]] Rule 2 (ground-truth-over-recall — same anti-pattern at the always-on session layer); [[karpathy-loop]] AP-4 (scorecard honesty — Timeline freshness IS honesty at the skill layer). No new LESSON (RULE ZERO).

### AP-2 — Runtime-vs-doctrine drift: 0 cameras returned by tracker vs 109 asserted in body (v1.1.0 captured; v1.2.0 root-caused)

**What happened (v1.1.0, 2026-05-25):** Live run of `MetrologyCertTracker().get_summary()` on VPS at 2026-05-25T10:35 KZT returned all-zero counts. The skill body asserted 109 expired (April 2026 baseline). Two plausible causes hypothesized: (a) the camera_registry data source was cleared; (b) the registry path or schema changed.

**Root cause confirmed (v1.2.0, 2026-05-25, via Explore subagent investigation):** Hypothesis (a) is correct — **EMPTY REGISTRY, NOT DATA DRIFT.** Evidence:

- `/opt/nous-agaas/erap/data/erap_dev.db` exists, 24,576 bytes, mtime 2026-03-17.
- `camera_registry` table schema is **intact** (id, calibration_date, calibration_cert, calibration_valid_until, all columns present, matches `CameraRegistry` class definition).
- `camera_registry` table has **0 rows** — never populated.
- `camera_reachability` table in `apk_health.db` has 108,200 rows — but that's reachability probes (IPs, ping status), NOT calibration metadata. Loses Order 62-NQ semantics if re-pointed there.
- `camera_status.db` file is **0 bytes** (empty stub). Earlier v1.1.0 AP-2 mentioned "281 cameras in camera_status table per bdl-cerebro gate" — that was an inferred reference from the bdl-cerebro gate's `fleet_health` JSON output, but it does NOT correspond to a populated `camera_status` SQLite table at the path the tracker would expect.
- `events.db` has `raw_events`, `vehicle_events`, but NO `camera_status` table.
- No backups of `erap_dev.db` from before 2026-03-17 mtime exist that the investigation could find.
- 5,800 Hikvision cameras referenced in `erap/camera_registry.py` source comments were never imported via the `register()` method.

**Implication:** The April 2026 "109 expired certs" figure must have come from a working copy that was lost OR a manual one-off load. The metrology tracker has been mostly-vapor since database initialization. The legal calibration tracking workflow (Order 62-NQ ЦСМ ВКО renewals) has been silently non-functional.

**Hypothesis (b) rejected:** schema is correct, path is correct, no re-pointing fix is appropriate (camera_reachability lacks calibration metadata; camera_status table doesn't exist as a populated SQLite table).

**Rule (this AP, post-root-cause):** until external data source (bulk ISAPI scan, historical export, or operator-provided CSV) populates `camera_registry`, the ЦСМ ВКО renewal application workflow cannot run from this skill — the application generator will produce empty letters. Block any "generate ЦСМ application" call against this skill until `get_summary()` returns non-zero. Status: documentation-of-known-broken with confirmed root cause and operator-action packet. NOT silent-pretend-it-works.

**Detector (shipped 2026-05-25, commit `efcdbcc5c`):** `tools/test_metrology_tracker_nonzero.sh` — runs `get_summary()` on VPS and asserts `total_cameras > 0`. Flags drift as YELLOW (not RED — the skill correctly documents the broken state per AP-1). Currently returns YELLOW; will go GREEN automatically when registry is populated.

**Cross-ref:** AP-1 (this skill — meta-rule that captured this AP); [[bdl-cerebro-replacement-gate]] AP-6 (sibling drift class); session-coordination v1.35.0 AP-2 (registry-is-incomplete-by-construction parent class). No new LESSON (RULE ZERO).

## Action packet — populate the empty registry

**Goal:** make `MetrologyCertTracker().get_summary()` return non-zero so ЦСМ ВКО renewal application workflow can run.

**Exact action (one of A or B; A preferred for legal completeness):**

A. **Bulk ISAPI scan + historical calibration cert import.** Run ISAPI scan against the Satory VKO camera fleet to discover serial numbers / models / IPs (the 5,800 Hikvision cameras mentioned in code comments). For each camera, look up historical calibration cert in: (1) any pre-2026-03-17 backup of `erap_dev.db` someone may have; (2) the v1.0.0 "109 expired" working copy (lost?); (3) physical paper records at ЦСМ ВКО (РГП «КазИнМетр» Филиал ВКО, г. Усть-Каменогорск) for the most recent cert per camera. Bulk `register()` into `camera_registry` table.

B. **Operator-provided CSV.** Operator (Mergen / Daniyar / ops team) exports cert data from their working spreadsheet into the column layout per skill body (`№, Серийный номер, Модель, IP-адрес, Тип камеры, Город, Адрес установки, №поверочного свидетельства, Дата последней поверки, Действительно до, Просрочено (дней)`). Bulk-import via `register()`.

**Exact endpoint:** VPS `root@65.108.215.200`, db at `/opt/nous-agaas/erap/data/erap_dev.db`, registry table `camera_registry`.

**Expected proof:** `ssh root@65.108.215.200 "cd /opt/nous-agaas && python3 -c 'from erap.metrology_cert_tracker import MetrologyCertTracker; print(MetrologyCertTracker().get_summary())'"` returns `total_cameras > 0`.

**Validator we will run:** `bash tools/test_metrology_tracker_nonzero.sh` — must flip from YELLOW to GREEN.

**Deadline / urgency:** Operational legal exposure — expired cameras issuing speed fines today (if any) are court-challengeable per Order 62-NQ. Severity scales with fine volume. No hard deadline, but every day of delay maintains the legal-risk surface.

**Rollback / stop condition:** Import is additive (INSERT, not DELETE); if it pollutes the registry, `DELETE FROM camera_registry` resets to empty. Safe.

**Who owns this:** Madi (decision on data source A vs B) → Mergen or operator (execution).

## Timeline

- **2026-05-25** | v1.1.0 → v1.2.0 — AP-2 root cause CONFIRMED via Explore subagent investigation on VPS. Evidence: `erap_dev.db` exists (24KB, mtime 2026-03-17), `camera_registry` table schema intact, **0 rows — never populated**. Hypothesis (a) empty-registry confirmed; hypothesis (b) re-pointing rejected (no suitable alternate table; `camera_reachability` lacks calibration metadata, `camera_status.db` is empty stub, no `camera_status` table in `events.db`). Body's "Current state" updated with confirmed root cause. Section "Action packet" added per SOC v1.17.0 Rule 20 (billion-dollar tiny-team external-action-packet format): two paths (A bulk ISAPI scan + historical cert import, B operator-CSV); validator `tools/test_metrology_tracker_nonzero.sh` will flip YELLOW→GREEN when registry populated. Authorial commit per Rule 19. Lane 1 (s0952) Mission 3.5 Item 3. Lane 4 (Explore subagent) investigation: 28 tool uses, 2 minutes, conclusive evidence chain.

- **2026-05-25** | v1.0.0 → v1.1.0 — First Timeline entry for this skill (was missing entirely under v1.0.0; itself an AP-1 violation that motivated the rule). Captured: live VPS run of `MetrologyCertTracker().get_summary()` returned `total_cameras=0, expired=0` against skill body's "April 2026: 109 expired" assertion. Two APs codified: AP-1 (state-of-system tracking must land in Timeline same-session, mirroring [[bdl-cerebro-replacement-gate]] AP-6) and AP-2 (drift evidence: 0 vs 109; likely cause = Mergen's 2026-05-09 ERAP camera reset cleared `camera_registry` but not `camera_status`; root cause investigation deferred). Skill body updated: "Current state (April 2026)" → "Current state (as of 2026-05-25): TRACKER REPORTS 0 CAMERAS — registry-load drift". Module path clarified: VPS host, not Air, with OpenClaw mount context. Detector `tools/test_metrology_tracker_nonzero.sh` queued (classifier-AP). Authorial commit per SOC v1.17.0 Rule 19. 4-session handshake Lane 1 (s0952) Mission 3 slice 3. No new LESSON (RULE ZERO).
- [[AGAAS-ARCHITECTURE-DECISION-v2-GOLDEN]] — Blocker #1: 109 expired certs
