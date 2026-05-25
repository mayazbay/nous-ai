"""agents.camera_doctor.main — Camera Doctor entrypoint + config loader.

Phase 1 Task 1.3 of PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1: minimal skeleton
that loads the per-tenant TOML config and (optionally) prints what it
loaded. Detectors + render layer + delivery ship in Phase 2/3.

Usage:
    python3 -m agents.camera_doctor.main --tenant <tenant> --dry-run --config-only
    python3 -m agents.camera_doctor.main --tenant <tenant> --dry-run
    python3 -m agents.camera_doctor.main --tenant <tenant>            # live (gated by [mode] in TOML)
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path
from typing import Any, Callable

from agents.camera_doctor import detectors, probe, render, runlog


def repo_root() -> Path:
    """Resolve the vault/repo root by walking up from this file."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tenants").is_dir() and (parent / "agents").is_dir():
            return parent
    # Fallback: assume we're at <root>/agents/camera_doctor/main.py
    return here.parents[2]


def tenant_config_path(tenant: str) -> Path:
    return repo_root() / "tenants" / tenant / "camera_doctor.toml"


def load_tenant_config(tenant: str) -> dict:
    path = tenant_config_path(tenant)
    if not path.is_file():
        raise FileNotFoundError(f"tenant config not found: {path}")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _tenant_slug(config: dict) -> str:
    return str(config.get("tenant", {}).get("slug") or "default")


def _erap_config(config: dict) -> dict:
    """Return normalized ERAP config with legacy [vps] fallback."""
    return config.get("erap") or config.get("vps", {})


def _query_config(config: dict) -> dict:
    erap_queries = config.get("erap", {}).get("queries")
    if erap_queries:
        return erap_queries
    return config.get("vps", {}).get("queries", {})


def _brand_config(config: dict) -> dict:
    brand = dict(config.get("brand", {}))
    tenant = config.get("tenant", {})
    brand.setdefault("language", tenant.get("brief_language", "ru"))
    brand.setdefault("brief_language", tenant.get("brief_language", "ru"))
    brand.setdefault("brief_title", f"{tenant.get('display_name', _tenant_slug(config))} Camera Doctor Brief")
    return brand


def _alert_chat_id(config: dict) -> Any:
    notify = config.get("notify", {})
    return notify.get("alert_chat_id", notify.get("tg_chat_id"))


def _pdf_path(config: dict, now: dt.datetime) -> Path:
    notify = config.get("notify", {})
    tenant = config.get("tenant", {})
    filename_template = notify.get("pdf_naming") or "{tenant}-Camera-Doctor-{YYYY-MM-DD}.pdf"
    filename = (
        filename_template
        .replace("{YYYY-MM-DD}", now.strftime("%Y-%m-%d"))
        .replace("{tenant}", str(tenant.get("slug", _tenant_slug(config))))
    )
    return Path(notify.get("pdf_archive_path", "briefs/")) / filename


def _default_log_dir(config: dict) -> str:
    return str(Path.home() / "nous-agaas" / "logs" / f"{_tenant_slug(config)}-camera-doctor")


def _tg_send_shell_fn(repo: Path) -> Callable[..., dict[str, Any]]:
    script = repo / "tools" / "tg_send.sh"

    def send(chat_id, text, files=None):  # noqa: ARG001 - shell helper sends text only
        out = subprocess.check_output(
            ["bash", str(script), "--chat", str(chat_id), str(text)],
            stderr=subprocess.STDOUT,
            timeout=30,
        ).decode("utf-8", errors="replace")
        match = re.search(r"msg_id=(\d+)", out)
        return {"msg_id": int(match.group(1)) if match else None, "output": out}

    return send


def print_config_summary(config: dict) -> None:
    """Print loaded TOML in a smoke-test-friendly format."""
    for section, body in config.items():
        print(f"[{section}]")
        if isinstance(body, dict):
            for key, value in body.items():
                # Avoid dumping nested dicts (e.g. vps.queries) verbosely
                if isinstance(value, dict):
                    print(f"  {key}: <{len(value)} entries>")
                elif isinstance(value, list):
                    print(f"  {key}: <{len(value)} items>")
                else:
                    print(f"  {key} = {value!r}")
        else:
            print(f"  {body!r}")


def run_pipeline(
    config: dict,
    *,
    events_db_path: str | None = None,
    camera_health_db_path: str | None = None,
    _events_override: dict | None = None,
    _health_override: dict | None = None,
    send_fn: Callable[..., Any] | None = None,
    now: dt.datetime | None = None,
    dry_run: bool = True,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Run one Camera Doctor cycle: probes -> detectors -> render -> runlog -> send.

    Returns a dict with all artifacts. Tenant-agnostic: paths and callbacks
    are dependency-injected so the same code runs against fixture (tests)
    or against live VPS (production). _events_override/_health_override accept
    pre-fetched probe results (e.g. from remote SSH queries) to skip local DB I/O.
    """
    n = now or dt.datetime.now(dt.timezone.utc)
    correlation_id = correlation_id or f"corr-{n.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"

    erap_cfg = _erap_config(config)

    # ---- Probes (use overrides if provided, else read local SQLite) ----
    if _events_override is not None:
        events = _events_override
    else:
        events_db = events_db_path or erap_cfg.get("events_db")
        if not events_db:
            raise RuntimeError("events_db not configured and no override provided")
        events = probe.query_events_db(events_db)

    if _health_override is not None:
        fleet = _health_override
    else:
        health_db = camera_health_db_path or erap_cfg.get("camera_health_db")
        if not health_db:
            raise RuntimeError("camera_health_db not configured and no override provided")
        fleet = probe.query_camera_health(health_db)

    wg_interface = config.get("network", {}).get("wg_interface", "wg0")
    wg = probe.wg_handshake_age(wg_interface)

    # ---- Detectors ----
    thresholds = config.get("thresholds", {})
    orientation_probe = config.get("orientation_probe", {})
    findings = [f for f in (
        detectors.detect_mirror_data_stale(events, fleet, thresholds),
        detectors.detect_vpn_network_down(wg, fleet, thresholds),
        # historical p10 will land in Phase 6 once we have 14d of data;
        # for MVP day-1 use 0.0 (red severity ladder still holds)
        detectors.detect_fleet_degraded(fleet, thresholds, historical_p10_pct=0.0),
        detectors.detect_cameras_offline_over_7d(fleet, thresholds),
        detectors.detect_camera_pointing_wrong_direction(orientation_probe, thresholds),
    ) if f is not None]

    # ---- Render ----
    brand = _brand_config(config)
    md = render.render_markdown(
        findings=findings,
        fleet=fleet,
        brand=brand,
        events_age_hours=events.get("age_hours"),
        now=n,
    )

    pdf_path = _pdf_path(config, n)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    render.render_pdf(md, pdf_path, brand)

    # ---- Send (if live and findings warrant) ----
    tg_msg_id = None
    alert_sent = False
    if not dry_run and send_fn:
        chat_id = _alert_chat_id(config)
        # Telegram message: lead line + link to PDF
        lead = next((l for l in md.splitlines() if l.strip()), "")
        msg_text = f"{lead}\n\nПолный отчёт: {pdf_path.name}"
        try:
            ret = send_fn(str(chat_id), msg_text, files=[str(pdf_path)])
            if isinstance(ret, dict):
                tg_msg_id = ret.get("msg_id")
            alert_sent = True
        except Exception as exc:  # pragma: no cover (defensive)
            alert_sent = False
            print(f"send failed: {exc}", file=sys.stderr)

    # ---- Runlog ----
    log_dir = config.get("runlog", {}).get("log_dir", _default_log_dir(config))
    queries = _query_config(config)
    record = runlog.build_record(
        run_id=correlation_id,
        ssh_rtt_ms=0,
        query_ms=0,
        rows_returned=int(events.get("total_rows", 0)),
        online_pct=float(fleet.get("online_pct", 0.0)),
        online_pct_p10_14d=0.0,
        threshold=float(thresholds.get("online_pct_min", 0.85)),
        decision="fire" if findings else "silent",
        alert_sent=alert_sent,
        tg_msg_id=tg_msg_id,
        pdf_path=str(pdf_path),
        exact_sql=str(queries),
        exact_ssh_command=f"ssh {erap_cfg.get('ssh_host', '')} 'sqlite3 {erap_cfg.get('events_db', '')} ...'",
        raw_query_result_sample=[
            {"max_event_time": str(events.get("max_event_time")),
             "total_rows": events.get("total_rows"),
             "age_hours": events.get("age_hours")}
        ],
        correlation_id=correlation_id,
        now=n,
    )
    runlog.append(record, log_dir=log_dir, now=n)

    return {
        "findings": findings,
        "fleet": fleet,
        "events": events,
        "markdown": md,
        "pdf_path": str(pdf_path),
        "tg_msg_id": tg_msg_id,
        "alert_sent": alert_sent,
        "decision": "fire" if findings else "silent",
        "correlation_id": correlation_id,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="agents.camera_doctor.main",
        description="Camera Doctor / Daily Operator Brief entrypoint",
    )
    ap.add_argument("--tenant", required=True, help="tenant slug")
    ap.add_argument("--dry-run", action="store_true",
                    help="do not send Telegram or write PDF; render to stdout/log only")
    ap.add_argument("--config-only", action="store_true",
                    help="load tenant config and print summary; do not run probes/detectors")
    ap.add_argument("--no-send", action="store_true",
                    help="alias for --dry-run; render but skip delivery (Phase 4 wiring)")
    args = ap.parse_args(argv)

    try:
        config = load_tenant_config(args.tenant)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.config_only:
        print_config_summary(config)
        return 0

    mode = (config.get("mode") or {}).get("mode", "dry_run")
    effective_dry_run = args.dry_run or args.no_send or mode == "dry_run"

    # Default send_fn: repo send-only Telegram script, tenant-selected chat_id.
    send_fn = None
    if not effective_dry_run:
        script = repo_root() / "tools" / "tg_send.sh"
        if script.is_file():
            send_fn = _tg_send_shell_fn(repo_root())
        else:
            print(f"WARN: tg_send unavailable at {script}; forcing dry-run", file=sys.stderr)
            effective_dry_run = True

    # Resolve DB paths: use local file if it exists (fixture/test),
    # else query remotely via SSH (avoids copying 60+ MB events.db).
    erap_cfg = _erap_config(config)
    events_db_cfg = erap_cfg.get("events_db", "")
    health_db_cfg = erap_cfg.get("camera_health_db", "")
    events_override: dict | None = None
    health_override: dict | None = None
    events_db_local: str | None = None
    health_db_local: str | None = None

    if events_db_cfg and not Path(events_db_cfg).is_file():
        ssh_host = erap_cfg.get("ssh_host", "")
        if not ssh_host:
            print("ERROR: events_db not found locally and no ssh_host configured", file=sys.stderr)
            return 2
        print(f"querying VPS remotely via {ssh_host} ...", file=sys.stderr)
        try:
            events_override = probe.query_events_remote(ssh_host, events_db_cfg)
            health_override = probe.query_camera_health_remote(ssh_host, health_db_cfg)
        except Exception as exc:
            print(f"ERROR: remote queries failed: {exc}", file=sys.stderr)
            return 2

    result = run_pipeline(
        config,
        events_db_path=events_db_local,
        camera_health_db_path=health_db_local,
        _events_override=events_override,
        _health_override=health_override,
        send_fn=send_fn,
        dry_run=effective_dry_run,
    )

    print(f"camera_doctor: tenant={args.tenant} mode={mode} dry_run={effective_dry_run} "
          f"decision={result['decision']} findings={len(result['findings'])} "
          f"alert_sent={result['alert_sent']} pdf={result['pdf_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
