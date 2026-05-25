#!/usr/bin/env python3
"""VPS-side watchdog for Air and the Telegram poller."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_HEALTH_URL = "http://madis-air-2.tailab95f4.ts.net:18789/healthz"
DEFAULT_AIR_SSH = "madia@100.122.219.22"
DEFAULT_STATE = Path("/opt/nous-agaas/watchdog/air_watchdog_state.json")
DEFAULT_TG_SEND = Path("/root/nous-agaas/wiki/tools/tg_send.sh")
DEFAULT_FAIL_THRESHOLD = 3
DEFAULT_LABEL = "com.nous.telegram-poll"


def load_state(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"fail_count": 0, "alert_active": False}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def check_http(url: str, timeout_s: float) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:
            body = response.read(512).decode("utf-8", errors="replace")
            if 200 <= response.status < 300:
                return True, f"http_{response.status}"
            return False, f"http_{response.status}:{body[:120]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"http_error:{exc}"


def check_poller(ssh_target: str, label: str, timeout_s: float) -> tuple[bool, str]:
    remote = (
        "launchctl list | "
        f"awk '$3 == \"{label}\" {{print $1, $2, $3}}'"
    )
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                f"ConnectTimeout={int(timeout_s)}",
                ssh_target,
                remote,
            ],
            text=True,
            capture_output=True,
            timeout=timeout_s + 2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"poller_ssh_error:{exc}"

    line = result.stdout.strip()
    if result.returncode != 0:
        return False, f"poller_ssh_exit_{result.returncode}:{result.stderr.strip()[:160]}"
    if not line:
        return False, "poller_label_missing"
    return parse_launchctl_line(line)


def parse_launchctl_line(line: str) -> tuple[bool, str]:
    parts = line.split()
    if len(parts) < 3:
        return False, f"poller_bad_launchctl_line:{line}"
    pid = parts[0]
    last_exit = parts[1]
    if pid != "-":
        return True, f"poller_ok:{line}"
    if last_exit != "0":
        return False, f"poller_last_exit_{last_exit}:{line}"
    return True, f"poller_ok:{line}"


def is_poller_transport_uncertain(detail: str) -> bool:
    """Return true when SSH failed before it could prove poller state."""
    return detail.startswith(("poller_ssh_error:", "poller_ssh_exit_255:"))


def send_alert(tg_send: Path, message: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["bash", str(tg_send), message],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def evaluate(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    state_path = Path(args.state_path)
    state = load_state(state_path)
    checks: dict[str, str] = {}

    http_ok, http_detail = check_http(args.health_url, args.timeout)
    checks["http"] = http_detail

    poller_ok = True
    poller_detail = "poller_check_skipped"
    if not args.no_poller_check:
        poller_ok, poller_detail = check_poller(args.air_ssh, args.poller_label, args.timeout)
        if http_ok and not poller_ok and is_poller_transport_uncertain(poller_detail):
            poller_ok = True
            poller_detail = f"poller_unknown_ssh_transport:{poller_detail}"
    checks["poller"] = poller_detail

    ok = http_ok and poller_ok
    if ok:
        state.update(
            {
                "fail_count": 0,
                "alert_active": False,
                "last_ok_at": int(time.time()),
                "last_checks": checks,
            }
        )
        save_state(state_path, state)
        return 0, {"ok": True, "checks": checks, "fail_count": 0}

    fail_count = int(state.get("fail_count", 0)) + 1
    state.update(
        {
            "fail_count": fail_count,
            "last_fail_at": int(time.time()),
            "last_checks": checks,
        }
    )
    alert_sent = False
    alert_output = ""
    if fail_count >= args.fail_threshold and not state.get("alert_active", False):
        message = "🔴 Air poller dead"
        detail = f" ({'; '.join(f'{k}={v}' for k, v in checks.items())})"
        alert_sent, alert_output = send_alert(Path(args.tg_send), message + detail)
        state["alert_active"] = alert_sent
        state["last_alert_at"] = int(time.time())
        state["last_alert_output"] = alert_output

    save_state(state_path, state)
    return 2, {
        "ok": False,
        "checks": checks,
        "fail_count": fail_count,
        "alert_sent": alert_sent,
        "alert_output": alert_output,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="VPS-side Air watchdog.")
    ap.add_argument("--health-url", default=os.environ.get("AIR_HEALTH_URL", DEFAULT_HEALTH_URL))
    ap.add_argument("--air-ssh", default=os.environ.get("AIR_SSH_TARGET", DEFAULT_AIR_SSH))
    ap.add_argument("--poller-label", default=os.environ.get("AIR_POLLER_LABEL", DEFAULT_LABEL))
    ap.add_argument("--state-path", default=os.environ.get("AIR_WATCHDOG_STATE", str(DEFAULT_STATE)))
    ap.add_argument("--tg-send", default=os.environ.get("AIR_WATCHDOG_TG_SEND", str(DEFAULT_TG_SEND)))
    ap.add_argument("--timeout", type=float, default=float(os.environ.get("AIR_WATCHDOG_TIMEOUT", "5")))
    ap.add_argument("--fail-threshold", type=int, default=int(os.environ.get("AIR_WATCHDOG_FAIL_THRESHOLD", DEFAULT_FAIL_THRESHOLD)))
    ap.add_argument("--no-poller-check", action="store_true")
    args = ap.parse_args(argv)

    code, payload = evaluate(args)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
