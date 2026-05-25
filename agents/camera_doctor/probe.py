"""agents.camera_doctor.probe — read-only probes against tenant ERAP data.

Phase 2 Task 2.1 of PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1.

Three probes, each returning a plain dict (mockable for tests):

  query_events_db(sqlite_path)    -> {max_event_time, total_rows, age_hours}
  query_camera_health(sqlite_path)-> {total, online, online_pct, fresh_check_count}
  wg_handshake_age(interface)     -> {age_seconds}

Tests run against local golden fixtures. Production runs read the live tenant
DBs over SSH.
"""

from __future__ import annotations

import datetime as dt
import shlex
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_event_time(raw: str) -> dt.datetime:
    """Parse the various event_time string formats produced by the ERAP
    pipeline. Examples seen in production:
      - '2026-04-05T22:08:05.856+05:00'
      - '2026-04-05 22:08:05'
    """
    s = (raw or "").strip()
    if not s:
        raise ValueError("empty event_time")
    # Normalise space-separated to ISO T
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        # Last-ditch: drop fractional seconds + tz
        head = s.split(".", 1)[0].split("+", 1)[0].split("Z", 1)[0]
        return dt.datetime.fromisoformat(head)


def query_events_db(sqlite_path: str) -> dict[str, Any]:
    """Return MAX(event_time), row count, and age in hours from vehicle_events."""
    p = Path(sqlite_path)
    if not p.is_file():
        raise FileNotFoundError(f"events DB not found: {p}")
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT MAX(event_time), COUNT(*) FROM vehicle_events;")
        max_raw, total_rows = cur.fetchone()
    if max_raw is None or total_rows == 0:
        return {"max_event_time": None, "total_rows": 0, "age_hours": float("inf")}
    max_dt = _parse_event_time(max_raw)
    # Normalise to UTC for math
    if max_dt.tzinfo is None:
        max_dt = max_dt.replace(tzinfo=dt.timezone.utc)
    age = _now_utc() - max_dt.astimezone(dt.timezone.utc)
    return {
        "max_event_time": max_dt,
        "total_rows": int(total_rows),
        "age_hours": age.total_seconds() / 3600.0,
    }


def query_camera_health(sqlite_path: str) -> dict[str, Any]:
    """Return fleet inventory + online% + recent-check freshness from camera_status."""
    p = Path(sqlite_path)
    if not p.is_file():
        raise FileNotFoundError(f"camera_health DB not found: {p}")
    with sqlite3.connect(f"file:{p}?mode=ro", uri=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM camera_status;")
        total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM camera_status WHERE status='online';")
        online = cur.fetchone()[0] or 0
        cur.execute(
            "SELECT COUNT(*) FROM camera_status "
            "WHERE last_check > datetime('now', '-1 hour');"
        )
        fresh = cur.fetchone()[0] or 0
        cur.execute(
            "SELECT COUNT(*) FROM camera_status "
            "WHERE status!='online' "
            "AND COALESCE(NULLIF(last_online,''), last_check) != '' "
            "AND julianday(COALESCE(NULLIF(last_online,''), last_check)) < julianday('now','-7 day');"
        )
        offline_over_7d = cur.fetchone()[0] or 0
        cur.execute(
            "SELECT camera_ip FROM camera_status "
            "WHERE status!='online' "
            "AND COALESCE(NULLIF(last_online,''), last_check) != '' "
            "AND julianday(COALESCE(NULLIF(last_online,''), last_check)) < julianday('now','-7 day') "
            "ORDER BY camera_ip LIMIT 5;"
        )
        offline_sample = [row[0] for row in cur.fetchall()]
    online_pct = (online / total) if total > 0 else 0.0
    return {
        "total": int(total),
        "online": int(online),
        "online_pct": float(online_pct),
        "fresh_check_count": int(fresh),
        "offline_over_7d_count": int(offline_over_7d),
        "offline_over_7d_sample": offline_sample,
    }


def _wg_latest_handshake_seconds(interface: str) -> int:
    """Read latest WireGuard handshake age (seconds since epoch -> age) from
    `wg show <iface> latest-handshakes`. Returns 10**9 (effectively infinite)
    if no handshake yet or wg not available.

    Tests should monkeypatch this function.
    """
    try:
        out = subprocess.check_output(
            ["wg", "show", interface, "latest-handshakes"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode("utf-8", errors="replace")
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return 10**9
    # Output format: <pubkey>\t<unix-timestamp>\n
    latest = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            ts = int(parts[1])
        except ValueError:
            continue
        latest = max(latest, ts)
    if latest == 0:
        return 10**9
    age = int(_now_utc().timestamp()) - latest
    return max(age, 0)


def wg_handshake_age(interface: str = "wg0") -> dict[str, Any]:
    """Return age in seconds since latest WireGuard handshake on `interface`."""
    return {"age_seconds": _wg_latest_handshake_seconds(interface)}


def query_events_remote(ssh_host: str, remote_path: str, timeout_s: int = 15) -> dict[str, Any]:
    """Query vehicle_events MAX/COUNT via SSH without copying the 61MB file.

    Runs two sqlite3 commands over SSH and parses the output.
    Falls back to age=inf on any failure.
    """
    try:
        out = subprocess.check_output(
            ["ssh", "-o", "StrictHostKeyChecking=no",
             ssh_host,
             f'sqlite3 {shlex.quote(remote_path)} "SELECT MAX(event_time), COUNT(*) FROM vehicle_events;"'],
            timeout=timeout_s,
        ).decode("utf-8", errors="replace").strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return {"max_event_time": None, "total_rows": 0, "age_hours": float("inf")}

    if not out:
        return {"max_event_time": None, "total_rows": 0, "age_hours": float("inf")}

    # sqlite3 pipe-separated output: max_event_time|count
    parts = out.split("|")
    if len(parts) < 2:
        return {"max_event_time": None, "total_rows": 0, "age_hours": float("inf")}
    max_raw, total_str = parts[0].strip(), parts[1].strip()
    try:
        total_rows = int(total_str)
    except ValueError:
        total_rows = 0
    if not max_raw or total_rows == 0:
        return {"max_event_time": None, "total_rows": total_rows, "age_hours": float("inf")}
    max_dt = _parse_event_time(max_raw)
    if max_dt.tzinfo is None:
        max_dt = max_dt.replace(tzinfo=dt.timezone.utc)
    age = _now_utc() - max_dt.astimezone(dt.timezone.utc)
    return {
        "max_event_time": max_dt,
        "total_rows": int(total_rows),
        "age_hours": age.total_seconds() / 3600.0,
    }


def query_camera_health_remote(ssh_host: str, remote_path: str, timeout_s: int = 15) -> dict[str, Any]:
    """Query camera_status totals via SSH without copying the file."""
    # Use double-quote shell wrapping so embedded single quotes (e.g. 'online') survive SSH.
    queries = [
        "SELECT COUNT(*) FROM camera_status;",
        "SELECT COUNT(*) FROM camera_status WHERE status='online';",
        "SELECT COUNT(*) FROM camera_status WHERE last_check > datetime('now', '-1 hour');",
        "SELECT COUNT(*) FROM camera_status WHERE status!='online' "
        "AND COALESCE(NULLIF(last_online,''), last_check) != '' "
        "AND julianday(COALESCE(NULLIF(last_online,''), last_check)) < julianday('now','-7 day');",
    ]
    results = []
    for q in queries:
        try:
            out = subprocess.check_output(
                ["ssh", "-o", "StrictHostKeyChecking=no", ssh_host,
                 f'sqlite3 {shlex.quote(remote_path)} "{q}"'],
                timeout=timeout_s,
            ).decode("utf-8", errors="replace").strip()
            results.append(int(out) if out.isdigit() else 0)
        except (subprocess.SubprocessError, ValueError, OSError):
            results.append(0)
    total, online, fresh, offline_over_7d = results[0], results[1], results[2], results[3]
    online_pct = (online / total) if total > 0 else 0.0
    return {
        "total": int(total),
        "online": int(online),
        "online_pct": float(online_pct),
        "fresh_check_count": int(fresh),
        "offline_over_7d_count": int(offline_over_7d),
        "offline_over_7d_sample": [],
    }


def fetch_dbs_from_vps(
    ssh_host: str,
    events_remote: str,
    health_remote: str,
    timeout_s: int = 30,
) -> tuple[Path, Path, Path]:
    """SCP-copy ERAP SQLite DBs from VPS to a local temp dir.

    Note: events.db is typically 60+ MB. Prefer query_events_remote for that.
    Kept for completeness / local fixture refresh use-case.
    Returns (events_local, health_local, tmpdir). Caller must shutil.rmtree(tmpdir).
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="camera_doctor_"))
    events_local = tmpdir / "events.db"
    health_local = tmpdir / "camera_health.db"
    for remote, local in ((events_remote, events_local), (health_remote, health_local)):
        subprocess.run(
            ["scp", "-q", "-o", "StrictHostKeyChecking=no",
             f"{ssh_host}:{remote}", str(local)],
            check=True,
            timeout=timeout_s,
        )
    return events_local, health_local, tmpdir
