#!/usr/bin/env python3
"""Observe a live Telegram `/ask` E2E proof without polling Telegram.

This probe never calls Telegram `getUpdates`. Air's launchd-owned
`telegram_poll.py` remains the only inbound poller. The probe can optionally
send one outbound request to Madi via `tg_send.sh`, then watches Air logs for:

- inbound command containing the nonce,
- routed Telegram message id,
- OpenClaw/tier log with `correlation_id=tg_<msg_id>`,
- `/ask handled`,
- successful Telegram `sendMessage` log from `command_center._tg_send`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 360
POLL_INTERVAL_SECONDS = 8

INBOUND_RE = re.compile(
    r"(?:Natural command|Command handled|Group natural command): "
    r"chat=(?P<chat>-?\d+) msg_id=(?P<msg_id>\d+) text='(?P<text>[^']*)'"
)
ASK_HANDLED_RE = re.compile(r"/ask(?: [^:]+)? handled: chat=(?P<chat>-?\d+) q_len=(?P<q_len>\d+) r_len=(?P<r_len>\d+)")
SEND_OK_RE = re.compile(
    r"_tg_send sent OK: chat=(?P<chat>-?\d+) bot_msg_id=(?P<bot_msg_id>\d+|None|\?) "
    r"reply_to=(?P<reply_to>\d*) text_len=(?P<text_len>\d+)"
)


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60, env: dict[str, str] | None = None) -> CommandResult:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
            text=True,
            capture_output=True,
            env=env,
        )
        return CommandResult(proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, exc.stdout or "", exc.stderr or f"timeout after {timeout}s")


def air(script: str, *, timeout: int = 60) -> CommandResult:
    return run(["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "air", script], timeout=timeout)


def make_nonce() -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"E2E-CODEX-{stamp}"


def send_operator_request(nonce: str) -> CommandResult:
    message = (
        "Telegram E2E proof needed now.\n"
        "Send this exact DM to @nousAGaaSbot:\n"
        f"/ask {nonce} reply OK in one short sentence and include {nonce}"
    )
    env = dict(os.environ)
    env["AUTONOMY_BYPASS"] = "1"
    return run(["bash", str(REPO / "tools" / "tg_send.sh"), message], cwd=REPO, timeout=30, env=env)


def fetch_air_logs() -> dict[str, str]:
    script = r"""
set -o pipefail
printf '--- telegram_poll.err ---\n'
tail -1200 ~/nous-agaas/logs/telegram_poll.err 2>/dev/null || true
printf '\n--- ask-hierarchy.jsonl ---\n'
tail -800 ~/nous-agaas/logs/ask-hierarchy.jsonl 2>/dev/null || true
printf '\n--- launchd ---\n'
launchctl list 2>/dev/null | grep 'com.nous.telegram-poll' || true
"""
    result = air(script, timeout=30)
    sections = {"telegram_poll.err": "", "ask-hierarchy.jsonl": "", "launchd": "", "ssh_error": ""}
    if not result.ok:
        sections["ssh_error"] = result.stderr.strip() or f"exit={result.returncode}"
        return sections
    current: str | None = None
    for line in result.stdout.splitlines():
        if line == "--- telegram_poll.err ---":
            current = "telegram_poll.err"
            continue
        if line == "--- ask-hierarchy.jsonl ---":
            current = "ask-hierarchy.jsonl"
            continue
        if line == "--- launchd ---":
            current = "launchd"
            continue
        if current:
            sections[current] += line + "\n"
    return sections


def _find_inbound(log_text: str, nonce: str) -> dict[str, str] | None:
    for match in INBOUND_RE.finditer(log_text):
        if nonce in match.group("text"):
            return match.groupdict()
    return None


def _find_ask_handled(log_text: str, chat_id: str | None) -> dict[str, str] | None:
    matches = [m.groupdict() for m in ASK_HANDLED_RE.finditer(log_text)]
    if chat_id:
        matches = [m for m in matches if m.get("chat") == chat_id]
    return matches[-1] if matches else None


def _find_send_success(log_text: str, msg_id: str | None) -> list[dict[str, str]]:
    sends = [m.groupdict() for m in SEND_OK_RE.finditer(log_text)]
    if msg_id:
        sends = [m for m in sends if m.get("reply_to") == msg_id]
    return sends


def _find_hierarchy_entry(jsonl_text: str, correlation_id: str | None) -> dict | None:
    if not correlation_id:
        return None
    found = None
    for line in jsonl_text.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("correlation_id") == correlation_id:
            found = item
    return found


def classify(logs: dict[str, str], nonce: str) -> dict:
    poll_log = logs.get("telegram_poll.err", "")
    hierarchy_log = logs.get("ask-hierarchy.jsonl", "")
    inbound = _find_inbound(poll_log, nonce)
    msg_id = inbound.get("msg_id") if inbound else None
    chat_id = inbound.get("chat") if inbound else None
    correlation_id = f"tg_{msg_id}" if msg_id else None
    hierarchy = _find_hierarchy_entry(hierarchy_log, correlation_id)
    ask_handled = _find_ask_handled(poll_log, chat_id) if inbound else None
    send_successes = _find_send_success(poll_log, msg_id) if inbound else []

    checks = {
        "inbound_nonce_seen": bool(inbound),
        "correlation_id_found": bool(hierarchy),
        "openclaw_decision_ok": bool(hierarchy and hierarchy.get("decision") == "ok"),
        "ask_handled_logged": bool(ask_handled),
        "telegram_reply_sent": bool(send_successes),
    }
    status = "GREEN" if all(checks.values()) else "YELLOW"
    return {
        "status": status,
        "nonce": nonce,
        "checks": checks,
        "msg_id": msg_id,
        "correlation_id": correlation_id,
        "inbound": inbound,
        "hierarchy": hierarchy,
        "ask_handled": ask_handled,
        "send_successes": send_successes[-4:],
        "launchd": logs.get("launchd", "").strip(),
        "ssh_error": logs.get("ssh_error", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nonce", default=make_nonce(), help="Probe nonce expected in the inbound /ask text")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Seconds to wait for live evidence")
    parser.add_argument("--request-human", action="store_true", help="Send one tg_send.sh prompt asking Madi to DM the exact /ask probe")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    request_result = None
    if args.request_human:
        request_result = send_operator_request(args.nonce)
        if not request_result.ok and not args.json:
            print(f"request_send_failed exit={request_result.returncode}: {request_result.stderr.strip()}", file=sys.stderr)

    deadline = time.monotonic() + max(1, args.timeout)
    latest = None
    while True:
        logs = fetch_air_logs()
        latest = classify(logs, args.nonce)
        if request_result is not None:
            latest["request_send"] = {
                "ok": request_result.ok,
                "returncode": request_result.returncode,
                "stdout": request_result.stdout.strip()[-300:],
                "stderr": request_result.stderr.strip()[-300:],
            }
        if latest["status"] == "GREEN" or time.monotonic() >= deadline:
            break
        time.sleep(POLL_INTERVAL_SECONDS)

    assert latest is not None
    if args.json:
        print(json.dumps(latest, ensure_ascii=False, indent=2))
    else:
        print(f"status={latest['status']} nonce={latest['nonce']} msg_id={latest.get('msg_id')}")
        print(json.dumps(latest["checks"], ensure_ascii=False, indent=2))
        if latest.get("request_send"):
            print("request_send=" + json.dumps(latest["request_send"], ensure_ascii=False))
        if latest.get("hierarchy"):
            print("hierarchy=" + json.dumps(latest["hierarchy"], ensure_ascii=False))
        if latest.get("send_successes"):
            print("send_successes=" + json.dumps(latest["send_successes"], ensure_ascii=False))
        if latest.get("ssh_error"):
            print(f"ssh_error={latest['ssh_error']}", file=sys.stderr)
    return 0 if latest["status"] == "GREEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
