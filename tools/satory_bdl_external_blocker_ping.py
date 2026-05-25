#!/usr/bin/env python3
"""Weekday 08:00 KZT ping for the external Satory BDL/Cerebro blocker."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import bdl_cerebro_replacement_gate as gate


KZT = ZoneInfo("Asia/Almaty")
DEFAULT_ENV_FILE = "/Users/madia/nous-agaas/.env"
DEFAULT_TG_SEND = "tools/tg_send.sh"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)
    parser.add_argument("--tg-send", default=DEFAULT_TG_SEND)
    parser.add_argument("--chat-id", default="")
    parser.add_argument("--receipt", default=gate.DEFAULT_EXTERNAL_PROOF_RECEIPT)
    parser.add_argument("--gate-json", help="Use an existing gate JSON report instead of running the live gate")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Send even outside the weekday 08:00 KZT window")
    parser.add_argument("--now", help="ISO timestamp for tests")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    _load_env_file(Path(args.env_file))
    now = _parse_now(args.now)
    if not args.force and not _is_ping_window(now):
        result = {"action": "skipped", "reason": "outside_weekday_0800_kzt", "now": now.isoformat()}
        _emit(result, args.json)
        return 0

    report = _load_or_run_gate(args)
    stop = _stop_condition_met(report)
    if stop:
        result = {"action": "stopped", "reason": "external_proof_and_freshness_green", "gate_overall": report["overall"]}
        _emit(result, args.json)
        return 0

    message = _build_message(report, now)
    if args.dry_run:
        result = {"action": "would_send", "message": message, "gate_overall": report["overall"]}
        _emit(result, args.json)
        return 0

    chat_id = args.chat_id or os.environ.get("SATORI_TELEGRAM_GROUP_CHAT_ID") or os.environ.get("TELEGRAM_GROUP_CHAT_ID") or ""
    rc, out = _send(args.tg_send, message, chat_id)
    result = {
        "action": "sent" if rc == 0 else "send_failed",
        "reason": _send_failure_reason(rc),
        "exit_code": rc,
        "output": out,
        "gate_overall": report["overall"],
    }
    _emit(result, args.json)
    return 0 if rc == 0 else rc


def _load_or_run_gate(args: argparse.Namespace) -> dict[str, Any]:
    if args.gate_json:
        return json.loads(Path(args.gate_json).read_text(encoding="utf-8"))
    gate_args = argparse.Namespace(
        fixture_events_db=None,
        fixture_health_db=None,
        fixture_queue_db=None,
        ssh_host=gate.DEFAULT_SSH_HOST,
        events_db=gate.DEFAULT_EVENTS_DB,
        health_db=gate.DEFAULT_HEALTH_DB,
        queue_db=gate.DEFAULT_QUEUE_DB,
        fresh_hours=24.0,
        health_fresh_hours=2.0,
        listener_url=gate.DEFAULT_VPS_HEALTH_URL,
        portal_health_url=gate.DEFAULT_PORTAL_HEALTH_URL,
        external_proof_receipt=args.receipt,
        skip_http=False,
    )
    return gate.run_gate(gate_args)


def _stop_condition_met(report: dict[str, Any]) -> bool:
    checks = {c.get("check"): c for c in report.get("checks", [])}
    required = [
        "external_proof_receipt",
        "listener",
        "event_ingestion",
        "fleet_health",
        "law002_classification",
        "erap_queue",
        "operator_portal",
    ]
    return all(checks.get(name, {}).get("status") == gate.GREEN for name in required)


def _build_message(report: dict[str, Any], now: dt.datetime) -> str:
    checks = {c.get("check"): c for c in report.get("checks", [])}
    proof = checks.get("external_proof_receipt", {})
    bdl = checks.get("bdl_replacement", {})
    blockers = bdl.get("blockers") or [c.get("detail", "") for c in report.get("checks", []) if c.get("status") == gate.RED]
    blocker_text = "; ".join(str(b) for b in blockers if b)[:900]
    proof_line = str(proof.get("detail") or "external proof receipt missing")
    # AP-1 (2026-05-21, SOC Rule 13 audience-language discipline): operators
    # group reads Russian. Template emits Cyrillic; proper nouns kept native
    # (Cyrillic Асыл/Денис matches their entity pages). Technical terms
    # (HTTP-200, egress, PSK, BDL, Cerebro, KZT, proof gate, freshness)
    # remain English — operators know the stack vocabulary and translating
    # them would obscure the signal.
    return (
        "🔴 Внешний блокер BDL/Cerebro всё ещё открыт.\n"
        f"Время: {now.astimezone(KZT).strftime('%Y-%m-%d %H:%M')} KZT.\n"
        "\n"
        "Асыл: пришлите PSK + подтверждение endpoint для egress-пути Satory.\n"
        "Денис: пришлите HTTP-200 egress-probe изнутри Satory к VPS-слушателю.\n"
        "\n"
        f"Текущий proof gate: {proof_line}\n"
        f"Текущий BDL gate: {report.get('overall')} — {blocker_text}\n"
        "\n"
        "Условие остановки: получено внешнее подтверждение И все BDL freshness-проверки зелёные."
    )


def _send(tg_send: str, message: str, chat_id: str) -> tuple[int, str]:
    cmd = ["bash", tg_send]
    if chat_id:
        cmd.extend(["--chat", chat_id])
    cmd.append(message)
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return proc.returncode, proc.stdout.strip()


def _send_failure_reason(exit_code: int) -> str:
    if exit_code == 0:
        return ""
    if exit_code == 4:
        return "tg_send_policy_block_exit_4"
    return "tg_send_failed"


def _is_ping_window(now: dt.datetime) -> bool:
    local = now.astimezone(KZT)
    return local.weekday() < 5 and local.hour == 8 and local.minute == 0


def _parse_now(raw: str | None) -> dt.datetime:
    if not raw:
        return dt.datetime.now(tz=KZT)
    parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KZT)
    return parsed.astimezone(KZT)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _emit(result: dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    sys.exit(main())
