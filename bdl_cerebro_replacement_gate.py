#!/usr/bin/env python3
"""BDL/Cerebro replacement proof gate.

Read-only verifier for the Satory replacement claim. It intentionally does not
mutate cameras, queues, Todoist, Notion, or the portal. A GREEN result means the
actual customer workflow is proven, not just that the frontend or listener is up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SSH_HOST = "root@65.108.215.200"
DEFAULT_EVENTS_DB = "/opt/nous-agaas/erap/data/events.db"
DEFAULT_HEALTH_DB = "/opt/nous-agaas/erap/data/camera_health.db"
DEFAULT_QUEUE_DB = "/opt/nous-agaas/erap/data/erap_queue.db"
DEFAULT_VPS_HEALTH_URL = "http://127.0.0.1:9080/health"
DEFAULT_PORTAL_HEALTH_URL = "http://127.0.0.1:8090/api/health"
DEFAULT_EXTERNAL_PROOF_RECEIPT = "pages/systems/satory-bdl-external-proof-receipt.json"
ALLOWED_EXTERNAL_PROOF_SOURCES = {
    "asyl_psk",
    "asyl_endpoint_proof",
    "denis_http_200_egress_probe",
}

GREEN = "GREEN"
YELLOW = "YELLOW"
RED = "RED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    parser.add_argument("--fixture-events-db", help="Local events.db fixture path")
    parser.add_argument("--fixture-health-db", help="Local camera_health.db fixture path")
    parser.add_argument("--fixture-queue-db", help="Local erap_queue.db fixture path")
    parser.add_argument("--ssh-host", default=DEFAULT_SSH_HOST)
    parser.add_argument("--events-db", default=DEFAULT_EVENTS_DB)
    parser.add_argument("--health-db", default=DEFAULT_HEALTH_DB)
    parser.add_argument("--queue-db", default=DEFAULT_QUEUE_DB)
    parser.add_argument("--fresh-hours", type=float, default=24.0)
    parser.add_argument("--health-fresh-hours", type=float, default=2.0)
    parser.add_argument("--listener-url", default=DEFAULT_VPS_HEALTH_URL)
    parser.add_argument("--portal-health-url", default=DEFAULT_PORTAL_HEALTH_URL)
    parser.add_argument("--external-proof-receipt", default=DEFAULT_EXTERNAL_PROOF_RECEIPT)
    parser.add_argument("--skip-http", action="store_true", help="Skip HTTP listener/portal probes")
    args = parser.parse_args()

    report = run_gate(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    else:
        print_human(report)
    return 0 if report["overall"] == GREEN else 1


def run_gate(args: argparse.Namespace) -> dict[str, Any]:
    source = _make_source(args)
    now = dt.datetime.now(dt.timezone.utc)

    checks: list[dict[str, Any]] = []
    listener = _http_check("listener", args.listener_url, source, args.skip_http)
    portal = _http_check("operator_portal", args.portal_health_url, source, args.skip_http)
    event_ingestion = _event_ingestion_check(source, now, args.fresh_hours)
    raw_intake = _raw_intake_check(source, now, args.fresh_hours)
    fleet = _fleet_health_check(source, now, args.health_fresh_hours)
    law002 = _law002_check(source, now, args.fresh_hours)
    erap_queue = _erap_queue_check(source, now, args.fresh_hours)
    external_proof = _external_proof_receipt_check(Path(args.external_proof_receipt), now)

    checks.extend([listener, portal, event_ingestion, raw_intake, fleet, law002, erap_queue, external_proof])
    bdl_status, bdl_blockers = _bdl_replacement_status(checks)
    cerebro_status, cerebro_blockers = _cerebro_replacement_status(bdl_status, checks)
    checks.append({
        "check": "bdl_replacement",
        "status": bdl_status,
        "detail": _detail_from_blockers(bdl_blockers, "BDL replacement data-plane proof is complete"),
        "blockers": bdl_blockers,
    })
    checks.append({
        "check": "cerebro_replacement",
        "status": cerebro_status,
        "detail": _detail_from_blockers(cerebro_blockers, "Cerebro replacement operator-plane proof is complete"),
        "blockers": cerebro_blockers,
    })

    overall = _rollup([c["status"] for c in checks])
    return {
        "schema_version": 1,
        "ts": now.isoformat(),
        "overall": overall,
        "reds": sum(1 for c in checks if c["status"] == RED),
        "yellows": sum(1 for c in checks if c["status"] == YELLOW),
        "mode": source.mode,
        "replacement_definition": [
            "camera/APK events ingested without BDL middleware",
            "fleet health current and auditable",
            "LAW-002 violation classification present",
            "ERAP/SmartBridge queue states visible",
            "operator portal uses fresh data without Cerebro/BDL help",
            "Satory-side external proof receipt exists: Asyl PSK/endpoint proof or Denis HTTP-200 egress probe",
        ],
        "checks": checks,
    }


class QuerySource:
    def __init__(self, *, mode: str, ssh_host: str | None, events_db: str, health_db: str, queue_db: str):
        self.mode = mode
        self.ssh_host = ssh_host
        self.events_db = events_db
        self.health_db = health_db
        self.queue_db = queue_db

    def sql(self, db_key: str, sql: str) -> str:
        db_path = {
            "events": self.events_db,
            "health": self.health_db,
            "queue": self.queue_db,
        }[db_key]
        if self.mode == "local":
            return _local_sql(db_path, sql)
        return _remote_sql(self.ssh_host or DEFAULT_SSH_HOST, db_path, sql)

    def http_get(self, url: str, timeout_s: int = 5) -> tuple[int, str]:
        if self.mode == "remote":
            cmd = f"curl -s -o - -w '\\n%{{http_code}}' --max-time {int(timeout_s)} {shlex.quote(url)}"
            out = _ssh(self.ssh_host or DEFAULT_SSH_HOST, cmd, timeout_s + 5)
            body, _, code = out.rpartition("\n")
            try:
                return int(code.strip()), body
            except ValueError:
                return 0, out
        try:
            with urllib.request.urlopen(url, timeout=timeout_s) as resp:
                return int(resp.status), resp.read(2000).decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 - gate must return evidence, not crash
            return 0, str(exc)


def _make_source(args: argparse.Namespace) -> QuerySource:
    if args.fixture_events_db:
        events_db = args.fixture_events_db
        health_db = args.fixture_health_db or args.fixture_events_db
        queue_db = args.fixture_queue_db or args.fixture_events_db
        return QuerySource(mode="local", ssh_host=None, events_db=events_db, health_db=health_db, queue_db=queue_db)
    return QuerySource(
        mode="remote",
        ssh_host=args.ssh_host,
        events_db=args.events_db,
        health_db=args.health_db,
        queue_db=args.queue_db,
    )


def _http_check(name: str, url: str, source: QuerySource, skip: bool) -> dict[str, Any]:
    if skip:
        return {"check": name, "status": YELLOW, "detail": "HTTP probe skipped by flag", "url": url}
    code, body = source.http_get(url)
    if code == 200:
        return {"check": name, "status": GREEN, "detail": f"HTTP 200 from {url}", "sample": body[:240]}
    return {"check": name, "status": RED, "detail": f"HTTP probe failed for {url}: code={code}", "sample": body[:240]}


def _event_ingestion_check(source: QuerySource, now: dt.datetime, fresh_hours: float) -> dict[str, Any]:
    row = _row(source.sql("events", "SELECT COUNT(*), MAX(event_time), MAX(created_at) FROM vehicle_events;"))
    total = _int(row, 0)
    last_event = _parse_dt(_get(row, 1))
    last_created = _parse_dt(_get(row, 2))
    age_h = _age_hours(now, last_event)
    detail = f"vehicle_events total={total} last_event={_iso(last_event)} age_h={_round(age_h)}"
    if total <= 0:
        return {"check": "event_ingestion", "status": RED, "detail": "vehicle_events has no parsed events"}
    if age_h <= fresh_hours:
        return {"check": "event_ingestion", "status": GREEN, "detail": detail, "last_created": _iso(last_created)}
    return {
        "check": "event_ingestion",
        "status": RED,
        "detail": f"{detail}; stale > {fresh_hours}h, BDL-free live event path is not proven",
        "last_created": _iso(last_created),
    }


def _raw_intake_check(source: QuerySource, now: dt.datetime, fresh_hours: float) -> dict[str, Any]:
    if not _table_exists(source, "events", "raw_events"):
        return {"check": "raw_intake", "status": YELLOW, "detail": "raw_events table missing; listener may predate lossless intake"}
    row = _row(source.sql(
        "events",
        "SELECT COUNT(*), MAX(received_at), "
        "SUM(CASE WHEN parse_status='parsed' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN parse_status='quarantined' THEN 1 ELSE 0 END) FROM raw_events;",
    ))
    total = _int(row, 0)
    latest = _parse_dt(_get(row, 1))
    parsed = _int(row, 2)
    quarantined = _int(row, 3)
    age_h = _age_hours(now, latest)
    if total <= 0:
        return {"check": "raw_intake", "status": YELLOW, "detail": "raw_events has no intake records"}
    if age_h <= fresh_hours and parsed > 0:
        status = GREEN
    elif age_h <= fresh_hours and quarantined >= total:
        status = YELLOW
    else:
        status = YELLOW
    return {
        "check": "raw_intake",
        "status": status,
        "detail": (
            f"raw_events total={total} parsed={parsed} quarantined={quarantined} "
            f"latest={_iso(latest)} age_h={_round(age_h)}"
        ),
    }


def _fleet_health_check(source: QuerySource, now: dt.datetime, health_fresh_hours: float) -> dict[str, Any]:
    row = _row(source.sql(
        "health",
        "SELECT COUNT(*), "
        "SUM(CASE WHEN status='online' THEN 1 ELSE 0 END), "
        "MAX(last_check) FROM camera_status;",
    ))
    total = _int(row, 0)
    online = _int(row, 1)
    latest = _parse_dt(_get(row, 2))
    age_h = _age_hours(now, latest)
    online_pct = (online / total) if total else 0.0
    detail = f"camera_status total={total} online={online} online_pct={online_pct:.3f} latest_check={_iso(latest)} age_h={_round(age_h)}"
    if total <= 0:
        return {"check": "fleet_health", "status": RED, "detail": "camera_status has no fleet rows"}
    if age_h > health_fresh_hours:
        return {"check": "fleet_health", "status": RED, "detail": f"{detail}; fleet health not current"}
    if online_pct < 0.85:
        return {"check": "fleet_health", "status": YELLOW, "detail": f"{detail}; current but degraded below 85%"}
    return {"check": "fleet_health", "status": GREEN, "detail": detail}


def _law002_check(source: QuerySource, now: dt.datetime, fresh_hours: float) -> dict[str, Any]:
    row = _row(source.sql(
        "events",
        "SELECT COUNT(*), MAX(event_time) FROM vehicle_events "
        "WHERE (vehicle_speed - speed_limit) >= 10 "
        "AND plate_confidence >= 80 "
        "AND is_violation = 1;",
    ))
    count = _int(row, 0)
    latest = _parse_dt(_get(row, 1))
    age_h = _age_hours(now, latest)
    detail = f"LAW-002 classified violations count={count} latest={_iso(latest)} age_h={_round(age_h)}"
    if count <= 0:
        return {"check": "law002_classification", "status": RED, "detail": "no LAW-002 compliant classified violations found"}
    if age_h <= fresh_hours:
        return {"check": "law002_classification", "status": GREEN, "detail": detail}
    return {"check": "law002_classification", "status": YELLOW, "detail": f"{detail}; capability exists but live proof is stale"}


def _erap_queue_check(source: QuerySource, now: dt.datetime, fresh_hours: float) -> dict[str, Any]:
    if not _table_exists(source, "queue", "submission_queue"):
        return {"check": "erap_queue", "status": RED, "detail": "submission_queue table missing"}
    rows = _rows(source.sql("queue", "SELECT status, COUNT(*), MAX(updated_at) FROM submission_queue GROUP BY status ORDER BY status;"))
    if not rows:
        return {"check": "erap_queue", "status": YELLOW, "detail": "submission_queue exists but is empty"}
    states = {r[0]: {"count": _int(r, 1), "latest": _get(r, 2)} for r in rows}
    latest = max((_parse_dt(v["latest"]) for v in states.values()), default=None)
    age_h = _age_hours(now, latest)
    known_states = {"pending", "processing", "submitted", "failed", "retry", "dlq", "expired"}
    unknown = sorted(set(states) - known_states)
    status = GREEN
    detail_suffix = ""
    if unknown:
        status = RED
        detail_suffix = f"; unknown queue states={unknown}"
    elif age_h > fresh_hours:
        status = YELLOW
        detail_suffix = f"; queue visible but stale > {fresh_hours}h"
    return {
        "check": "erap_queue",
        "status": status,
        "detail": f"submission_queue states={states} latest_age_h={_round(age_h)}{detail_suffix}",
        "states": states,
    }


def _external_proof_receipt_check(path: Path, now: dt.datetime) -> dict[str, Any]:
    if not path.exists():
        return {
            "check": "external_proof_receipt",
            "status": RED,
            "detail": f"missing receipt file {path}; need Asyl PSK/endpoint proof or Denis HTTP-200 egress probe from inside Satory",
            "path": str(path),
        }
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - gate must report evidence, not crash
        return {
            "check": "external_proof_receipt",
            "status": RED,
            "detail": f"receipt file is not valid JSON: {exc}",
            "path": str(path),
        }

    status = str(receipt.get("status", "")).strip().lower()
    source = str(receipt.get("source", "")).strip()
    received_at = _parse_dt(str(receipt.get("received_at", "")))
    evidence = str(receipt.get("evidence", "")).strip()
    http_status = receipt.get("http_status")

    if status != "received":
        return {
            "check": "external_proof_receipt",
            "status": RED,
            "detail": f"external proof requested but not received; status={status or 'missing'}",
            "path": str(path),
            "receipt": _public_receipt(receipt),
        }

    blockers: list[str] = []
    if source not in ALLOWED_EXTERNAL_PROOF_SOURCES:
        blockers.append(f"source must be one of {sorted(ALLOWED_EXTERNAL_PROOF_SOURCES)}")
    if received_at is None:
        blockers.append("received_at must be an ISO timestamp")
    if not evidence and not (source == "denis_http_200_egress_probe" and _safe_int(http_status) == 200):
        blockers.append("evidence is required unless Denis probe carries http_status=200")

    if blockers:
        return {
            "check": "external_proof_receipt",
            "status": RED,
            "detail": "; ".join(blockers),
            "path": str(path),
            "receipt": _public_receipt(receipt),
        }

    age_h = _age_hours(now, received_at)
    return {
        "check": "external_proof_receipt",
        "status": GREEN,
        "detail": f"external Satory proof received from {source} at {_iso(received_at)} age_h={_round(age_h)}",
        "path": str(path),
        "receipt": _public_receipt(receipt),
    }


def _bdl_replacement_status(checks: list[dict[str, Any]]) -> tuple[str, list[str]]:
    by_name = {c["check"]: c for c in checks}
    required = [
        ("external_proof_receipt", "external Satory proof receipt must be present before BDL/Cerebro can be green"),
        ("listener", "VPS ISAPI listener must be reachable"),
        ("event_ingestion", "fresh parsed vehicle_events must prove BDL-free camera/APK ingestion"),
        ("fleet_health", "camera fleet health must be current and operator-usable"),
        ("law002_classification", "LAW-002 classification must exist on fresh events"),
        ("erap_queue", "ERAP queue must expose current pending/submitted/failed/retry states"),
    ]
    blockers = []
    for name, fallback in required:
        check = by_name.get(name, {})
        if check.get("status") != GREEN:
            blockers.append(_bdl_blocker(name, check, fallback))
    return (GREEN if not blockers else RED, blockers)


def _cerebro_replacement_status(bdl_status: str, checks: list[dict[str, Any]]) -> tuple[str, list[str]]:
    by_name = {c["check"]: c for c in checks}
    blockers = []
    if bdl_status != GREEN:
        blockers.append("Cerebro replacement is blocked until BDL data-plane proof is green")
    if by_name.get("operator_portal", {}).get("status") != GREEN:
        blockers.append("operator portal health must be reachable")
    if by_name.get("event_ingestion", {}).get("status") != GREEN:
        blockers.append("operator portal must be backed by fresh events, not stale tables")
    return (GREEN if not blockers else RED, blockers)


def _bdl_blocker(name: str, check: dict[str, Any], fallback: str) -> str:
    detail = str(check.get("detail", ""))
    if name == "fleet_health" and check.get("status") == YELLOW:
        return "camera fleet health is current but degraded below the operator threshold"
    if name == "law002_classification" and check.get("status") == YELLOW:
        return "LAW-002 classification exists only on stale events"
    if name == "erap_queue" and check.get("status") == YELLOW:
        return "ERAP queue exists but has no current state transitions"
    if name == "raw_intake" and "quarantined" in detail:
        return "raw intake is recent but quarantined, not parsed camera proof"
    return fallback


def _public_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    allowed = {"status", "source", "received_at", "owner", "evidence", "http_status", "endpoint"}
    return {k: v for k, v in receipt.items() if k in allowed}


def _detail_from_blockers(blockers: list[str], success: str) -> str:
    return success if not blockers else "; ".join(blockers)


def _rollup(statuses: list[str]) -> str:
    if any(s == RED for s in statuses):
        return RED
    if any(s == YELLOW for s in statuses):
        return YELLOW
    return GREEN


def _local_sql(db_path: str, sql: str) -> str:
    with sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True) as conn:
        cur = conn.execute(sql)
        return "\n".join("|".join("" if v is None else str(v) for v in row) for row in cur.fetchall())


def _remote_sql(ssh_host: str, db_path: str, sql: str) -> str:
    return _ssh(ssh_host, f"sqlite3 {shlex.quote(db_path)} {shlex.quote(sql)}", timeout_s=20)


def _ssh(ssh_host: str, command: str, timeout_s: int) -> str:
    return subprocess.check_output(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", ssh_host, command],
        stderr=subprocess.STDOUT,
        timeout=timeout_s,
        text=True,
    ).strip()


def _table_exists(source: QuerySource, db_key: str, table: str) -> bool:
    safe = table.replace("'", "''")
    out = source.sql(db_key, f"SELECT name FROM sqlite_master WHERE type='table' AND name='{safe}';")
    return out.strip() == table


def _row(output: str) -> list[str]:
    rows = _rows(output)
    return rows[0] if rows else []


def _rows(output: str) -> list[list[str]]:
    if not output.strip():
        return []
    return [line.split("|") for line in output.splitlines() if line.strip()]


def _get(row: list[str], idx: int) -> str:
    return row[idx] if idx < len(row) else ""


def _int(row: list[str], idx: int) -> int:
    try:
        raw = _get(row, idx)
        return int(float(raw)) if raw not in ("", "None") else 0
    except (TypeError, ValueError):
        return 0


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return 0


def _parse_dt(raw: str | None) -> dt.datetime | None:
    s = (raw or "").strip()
    if not s or s.lower() in {"none", "null"}:
        return None
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(s)
    except ValueError:
        head = s.split(".", 1)[0].split("+", 1)[0]
        try:
            parsed = dt.datetime.fromisoformat(head)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _age_hours(now: dt.datetime, value: dt.datetime | None) -> float:
    if value is None:
        return float("inf")
    return max(0.0, (now - value).total_seconds() / 3600.0)


def _round(value: float) -> float | str:
    if value == float("inf"):
        return "inf"
    return round(value, 2)


def _iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value else None


def _json_default(value: Any) -> Any:
    if isinstance(value, dt.datetime):
        return value.isoformat()
    return str(value)


def print_human(report: dict[str, Any]) -> None:
    print(f"BDL/Cerebro replacement gate: {report['overall']} red={report['reds']} yellow={report['yellows']}")
    for check in report["checks"]:
        print(f"- {check['status']:6} {check['check']}: {check['detail']}")


if __name__ == "__main__":
    sys.exit(main())
