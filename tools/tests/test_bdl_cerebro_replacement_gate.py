from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path

from tools import bdl_cerebro_replacement_gate as gate


def _make_events_db(path: Path, *, fresh: bool, parsed_raw: bool = True) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    event_time = now.isoformat() if fresh else "2026-04-05T22:08:05.856+05:00"
    received_at = now.isoformat()
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE vehicle_events (
              id INTEGER PRIMARY KEY,
              event_uuid TEXT,
              plate_number TEXT NOT NULL,
              plate_confidence REAL DEFAULT 0,
              vehicle_speed REAL DEFAULT 0,
              speed_limit REAL DEFAULT 0,
              is_violation INTEGER DEFAULT 0,
              event_time TEXT DEFAULT '',
              created_at TEXT DEFAULT ''
            );
            CREATE TABLE raw_events (
              raw_event_id INTEGER PRIMARY KEY,
              received_at TEXT NOT NULL,
              payload_hash TEXT NOT NULL,
              byte_length INTEGER NOT NULL,
              peer TEXT NOT NULL,
              path TEXT NOT NULL,
              content_type TEXT NOT NULL,
              stored_path TEXT NOT NULL,
              parse_status TEXT DEFAULT 'pending',
              quarantine_reason TEXT DEFAULT '',
              idempotency_key TEXT DEFAULT ''
            );
            CREATE TABLE ingest_quarantine (
              id INTEGER PRIMARY KEY,
              raw_event_id INTEGER,
              payload_hash TEXT NOT NULL,
              reason TEXT NOT NULL,
              detail TEXT DEFAULT '',
              created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """INSERT INTO vehicle_events
               (event_uuid, plate_number, plate_confidence, vehicle_speed, speed_limit,
                is_violation, event_time, created_at)
               VALUES ('evt-1', '013ABC15', 98, 79, 60, 1, ?, ?)""",
            (event_time, event_time),
        )
        status = "parsed" if parsed_raw else "quarantined"
        reason = "" if parsed_raw else "parse_error"
        conn.execute(
            """INSERT INTO raw_events
               (received_at, payload_hash, byte_length, peer, path, content_type, stored_path,
                parse_status, quarantine_reason)
               VALUES (?, 'hash', 100, '10.235.0.3', '/ISAPI/Event/notification/alertStream',
                       'multipart/form-data', '/tmp/raw.bin', ?, ?)""",
            (received_at, status, reason),
        )


def _make_health_db(path: Path, *, fresh: bool = True, online: int = 3, total: int = 3) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    last_check = now.isoformat() if fresh else "2026-04-01T00:00:00+00:00"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE camera_status (
              camera_ip TEXT PRIMARY KEY,
              status TEXT DEFAULT 'unknown',
              last_check TEXT DEFAULT ''
            )"""
        )
        for idx in range(total):
            status = "online" if idx < online else "offline"
            conn.execute(
                "INSERT INTO camera_status (camera_ip, status, last_check) VALUES (?, ?, ?)",
                (f"10.235.0.{idx+1}", status, last_check),
            )


def _make_38_stale_online_dark_fleet_db(path: Path) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    stale = "2026-03-31 13:06:51"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE camera_status (
              camera_ip TEXT PRIMARY KEY,
              status TEXT DEFAULT 'unknown',
              last_check TEXT DEFAULT ''
            )"""
        )
        for idx in range(38):
            conn.execute(
                "INSERT INTO camera_status (camera_ip, status, last_check) VALUES (?, 'online', ?)",
                (f"10.235.99.{idx+1}", stale),
            )
        for idx in range(209):
            conn.execute(
                "INSERT INTO camera_status (camera_ip, status, last_check) VALUES (?, 'offline', ?)",
                (f"10.170.0.{idx+1}", now),
            )
        for idx in range(34):
            conn.execute(
                "INSERT INTO camera_status (camera_ip, status, last_check) VALUES (?, 'error', ?)",
                (f"10.235.0.{idx+1}", now),
            )


def _make_queue_db(path: Path, *, fresh: bool = True) -> None:
    updated = dt.datetime.now(dt.timezone.utc).isoformat() if fresh else "2026-03-17T18:34:59+00:00"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE submission_queue (
              id INTEGER PRIMARY KEY,
              message_id TEXT UNIQUE NOT NULL,
              payload TEXT NOT NULL,
              status TEXT DEFAULT 'pending',
              updated_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO submission_queue (message_id, payload, status, updated_at) VALUES ('msg-1', '{}', 'submitted', ?)",
            (updated,),
        )


def _make_external_proof(path: Path, *, received: bool = True, source: str = "denis_http_200_egress_probe") -> None:
    payload = {
        "status": "received" if received else "requested",
        "source": source,
        "received_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "owner": "Denis",
        "evidence": "HTTP 200 egress probe from inside Satory",
        "http_status": 200,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _args(events: Path, health: Path, queue: Path, proof: Path) -> argparse.Namespace:
    return argparse.Namespace(
        fixture_events_db=str(events),
        fixture_health_db=str(health),
        fixture_queue_db=str(queue),
        ssh_host="unused",
        events_db="unused",
        health_db="unused",
        queue_db="unused",
        fresh_hours=24.0,
        health_fresh_hours=2.0,
        listener_url="http://unused",
        portal_health_url="http://unused",
        external_proof_receipt=str(proof),
        skip_http=True,
    )


def test_gate_green_when_fixture_has_fresh_parsed_event_fleet_and_queue(tmp_path: Path) -> None:
    events = tmp_path / "events.db"
    health = tmp_path / "health.db"
    queue = tmp_path / "queue.db"
    _make_events_db(events, fresh=True, parsed_raw=True)
    _make_health_db(health, fresh=True, online=3, total=3)
    _make_queue_db(queue, fresh=True)
    proof = tmp_path / "external-proof.json"
    _make_external_proof(proof)

    report = gate.run_gate(_args(events, health, queue, proof))
    by_check = {c["check"]: c for c in report["checks"]}

    assert by_check["external_proof_receipt"]["status"] == "GREEN"
    assert by_check["event_ingestion"]["status"] == "GREEN"
    assert by_check["raw_intake"]["status"] == "GREEN"
    assert by_check["fleet_health"]["status"] == "GREEN"
    assert by_check["law002_classification"]["status"] == "GREEN"
    assert by_check["erap_queue"]["status"] == "GREEN"


def test_gate_red_when_vehicle_events_are_stale_even_if_raw_intake_is_recent(tmp_path: Path) -> None:
    events = tmp_path / "events.db"
    health = tmp_path / "health.db"
    queue = tmp_path / "queue.db"
    _make_events_db(events, fresh=False, parsed_raw=False)
    _make_health_db(health, fresh=True, online=1, total=3)
    _make_queue_db(queue, fresh=False)
    proof = tmp_path / "external-proof.json"
    _make_external_proof(proof)

    report = gate.run_gate(_args(events, health, queue, proof))
    by_check = {c["check"]: c for c in report["checks"]}

    assert report["overall"] == "RED"
    assert by_check["event_ingestion"]["status"] == "RED"
    assert "stale" in by_check["event_ingestion"]["detail"]
    assert by_check["raw_intake"]["status"] == "YELLOW"
    assert by_check["bdl_replacement"]["status"] == "RED"
    assert "fresh parsed vehicle_events" in by_check["bdl_replacement"]["detail"]


def test_gate_marks_degraded_but_current_fleet_yellow(tmp_path: Path) -> None:
    events = tmp_path / "events.db"
    health = tmp_path / "health.db"
    queue = tmp_path / "queue.db"
    _make_events_db(events, fresh=True, parsed_raw=True)
    _make_health_db(health, fresh=True, online=1, total=10)
    _make_queue_db(queue, fresh=True)
    proof = tmp_path / "external-proof.json"
    _make_external_proof(proof)

    report = gate.run_gate(_args(events, health, queue, proof))
    by_check = {c["check"]: c for c in report["checks"]}

    assert by_check["fleet_health"]["status"] == "YELLOW"
    assert "degraded" in by_check["fleet_health"]["detail"]


def test_gate_marks_38_stale_online_rows_as_red_dark_fleet(tmp_path: Path) -> None:
    events = tmp_path / "events.db"
    health = tmp_path / "health.db"
    queue = tmp_path / "queue.db"
    _make_events_db(events, fresh=True, parsed_raw=True)
    _make_38_stale_online_dark_fleet_db(health)
    _make_queue_db(queue, fresh=True)
    proof = tmp_path / "external-proof.json"
    _make_external_proof(proof)

    report = gate.run_gate(_args(events, health, queue, proof))
    by_check = {c["check"]: c for c in report["checks"]}

    assert by_check["fleet_health"]["status"] == "RED"
    assert "online_fresh=0" in by_check["fleet_health"]["detail"]
    assert "stale_online=38" in by_check["fleet_health"]["detail"]
    assert "ZERO cameras online with current last_check" in by_check["fleet_health"]["detail"]
    assert by_check["bdl_replacement"]["status"] == "RED"
    assert "camera fleet health must be current" in by_check["bdl_replacement"]["detail"]


def test_gate_remains_red_without_external_satory_proof_even_if_data_plane_is_fresh(tmp_path: Path) -> None:
    events = tmp_path / "events.db"
    health = tmp_path / "health.db"
    queue = tmp_path / "queue.db"
    proof = tmp_path / "missing-proof.json"
    _make_events_db(events, fresh=True, parsed_raw=True)
    _make_health_db(health, fresh=True, online=3, total=3)
    _make_queue_db(queue, fresh=True)

    report = gate.run_gate(_args(events, health, queue, proof))
    by_check = {c["check"]: c for c in report["checks"]}

    assert report["overall"] == "RED"
    assert by_check["external_proof_receipt"]["status"] == "RED"
    assert by_check["bdl_replacement"]["status"] == "RED"
    assert "external Satory proof receipt" in by_check["bdl_replacement"]["detail"]


def test_external_proof_requires_received_status(tmp_path: Path) -> None:
    events = tmp_path / "events.db"
    health = tmp_path / "health.db"
    queue = tmp_path / "queue.db"
    proof = tmp_path / "external-proof.json"
    _make_events_db(events, fresh=True, parsed_raw=True)
    _make_health_db(health, fresh=True, online=3, total=3)
    _make_queue_db(queue, fresh=True)
    _make_external_proof(proof, received=False)

    report = gate.run_gate(_args(events, health, queue, proof))
    by_check = {c["check"]: c for c in report["checks"]}

    assert by_check["external_proof_receipt"]["status"] == "RED"
    assert "not received" in by_check["external_proof_receipt"]["detail"]
