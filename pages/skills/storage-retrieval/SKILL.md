---
tier: 2
type: skill
id: storage-retrieval-skill
name: storage-retrieval
title: "SKILL — Storage & Retrieval"
description: Video evidence archival + retrieval pattern for Satory VKO cameras. Covers 90-day КоАП minimum retention, expiry management, contested-violation pull-back, and retention policy compliance per Kazakhstan administrative code. Required whenever camera footage needs long-term archival or case-driven retrieval.
status: current
version: 1.0.0
date: 2026-04-13
last_updated: 2026-04-18
triggers:
  - video archival
  - video retrieval
  - camera footage retention
  - КоАП 90 days
  - violation evidence storage
  - video storage policy
  - contested violation archive
tags: [skill, storage, retrieval, video, archival]
---
# storage-retrieval v1.0.0

**Purpose:** Video footage archival, retention policy enforcement, and forensic search. Manages the full lifecycle of camera clips — from registration to KZ-compliant deletion — with SQLite metadata index and integrity checksums.

**Owner:** Madi Ayazbay  
**Status:** ✅ Module live on VPS. Footage root: Alem.Cloud (KZ, pending migration).  
**Tests:** 31/31 pass  
**KZ Law:** КоАП retention 90 days (violation evidence), 7 days (continuous), indefinite (contested)

---

## What it does

| Component | Description |
|-----------|-------------|
| `RetentionPolicy` | Configurable rules per footage type. Subclass to override per project. |
| `StorageManager` | Register clips, apply retention purges, quota monitoring. |
| `ForensicSearch` | Query by camera, date range, plate number, violation ID, footage type. |
| `compute_checksum` | SHA-256 of file for evidence integrity (court-admissible). |

---

## Files

| File | Location |
|------|----------|
| Core module | `/opt/nous-agaas/erap/storage_manager.py` |
| Tests | `/opt/nous-agaas/erap/tests/test_storage.py` |
| SQLite DB (VPS) | `/opt/nous-agaas/erap/footage.db` (create on first use) |
| Footage root (prod) | `/mnt/footage/` on Alem.Cloud (KZ) |

---

## Retention policy (KZ law)

| Footage type | Retention | Legal basis |
|--------------|-----------|-------------|
| `violation` | 90 days | КоАП appeal period 30d + 60d processing buffer |
| `continuous` | 7 days | KZ PDP Art. 21 — minimise personal data retention |
| `event` | 30 days | Near-miss, access events, maintenance |
| `system_log` | 30 days | Health-check, calibration |
| `contested` | **Indefinite** | Locked until case closed — NEVER purge |

---

## Quick start

```python
from erap.storage_manager import StorageManager, ForensicSearch, FootageRecord
from datetime import datetime, timezone, timedelta

KZ_TZ = timezone(timedelta(hours=5))

mgr = StorageManager(
    db_path="/opt/nous-agaas/erap/footage.db",
    footage_root="/mnt/footage",
    quota_limit_gb=500.0,
)

# Register a violation clip
rec = FootageRecord(
    camera_id="DS-CAM-001",
    recorded_at=datetime.now(KZ_TZ),
    filename="2026-04-13T14-32-00_CAM001_violation.mp4",
    filepath="/mnt/footage/2026-04/CAM001/2026-04-13T14-32-00_violation.mp4",
    duration_secs=15,
    size_bytes=18_000_000,   # ~18 MB
    footage_type="violation",
    violation_id="V-2026-04-001234",
    plate="013АВС15",
    checksum="abc123...",    # from compute_checksum(filepath)
)
footage_id = mgr.register(rec)

# Lock a contested violation (appeal filed)
mgr.mark_contested(footage_id)

# Nightly purge cron (safe — contested records are never touched)
stats = mgr.apply_retention()
# → {"purged": 42, "freed_bytes": 756000000, "errors": 0, "skipped_contested": 3}

# Quota check
quota = mgr.get_quota()
if quota["over_limit"]:
    hitl.notify(f"⚠️ Storage over limit: {quota['total_bytes'] / 1e9:.1f} GB")
```

---

## Forensic search

```python
search = ForensicSearch(db_path="/opt/nous-agaas/erap/footage.db")

# Find all footage for a specific plate in the last 7 days
from datetime import datetime, timedelta, timezone
KZ_TZ = timezone(timedelta(hours=5))
results = search.query(
    plate="013АВС15",
    from_dt=datetime.now(KZ_TZ) - timedelta(days=7),
)

# Get full evidence chain for a violation (for export to ERAP)
chain = search.get_evidence_chain("V-2026-04-001234")
# Returns all clips: wide-angle approach, plate crop, post-violation departure
```

---

## Traps

### TRAP-1: Contested footage loses retain_until if mark_contested cleared it
**Symptom:** `apply_retention` shows 0 `skipped_contested` even for locked records.  
**Root cause:** Old code did `UPDATE ... SET retain_until=NULL` — records dropped out of the expiry query entirely, silently un-tracked.  
**Fix (in v1.0.0):** `mark_contested` only sets `contested=1`. `retain_until` stays for the audit trail. The contested flag blocks deletion in the loop.

### TRAP-2: `contested=True` at registration time
`_compute_retain_until` always uses footage_type (ignores contested flag at compute time). This means contested records still get a `retain_until` date in the DB — for audit purposes. The contested flag is what prevents deletion, not a NULL retain_until.

### TRAP-3: Footage root not mounted
If `/mnt/footage` is not mounted (Alem.Cloud VM reboot), `apply_retention` will delete DB records for files that no longer exist on the mount — footage is actually still safe on the storage volume. Add a mount check before calling `apply_retention` in production.

### TRAP-4: SHA-256 must be computed BEFORE registration
`compute_checksum(filepath)` reads the entire file. Do it before calling `register()` and pass the result via `rec.checksum`. Don't compute it inside `register()` — the file may be on a remote mount that's slow or unavailable.

### TRAP-5: KZ PDP enforcement date
KZ Digital Code takes full effect July 11, 2026. Continuous footage retention >7 days becomes a fineable offence for PII (licence plates = personal data). The 7-day default in `RetentionPolicy.CONTINUOUS` is already compliant.

---

## Retention cron (add to VPS crontab)

```bash
# Daily at 03:00 Almaty — purge expired footage, check quota
0 22 * * * cd /opt/nous-agaas && /root/nous-agaas/venv/bin/python3 -c "
from erap.storage_manager import StorageManager
import os
mgr = StorageManager(
    db_path='/opt/nous-agaas/erap/footage.db',
    footage_root='/mnt/footage',
    quota_limit_gb=float(os.getenv('FOOTAGE_QUOTA_GB', '500')),
)
stats = mgr.apply_retention()
quota = mgr.get_quota()
print(f'retention: {stats}')
print(f'quota: total={quota[\"total_bytes\"]/1e9:.1f}GB over_limit={quota[\"over_limit\"]}')
" >> /root/nous-agaas/logs/footage_retention.log 2>&1
```

---

## Pytest gate

```bash
cd /opt/nous-agaas/erap
/root/nous-agaas/venv/bin/pytest tests/test_storage.py -v
# Expected: 31 passed

/root/nous-agaas/venv/bin/pytest tests/ -q
# Expected: 468 passed, 5 skipped
```
