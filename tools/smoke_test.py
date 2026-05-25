#!/usr/bin/env python3
"""
smoke_test.py — Daily end-to-end factory smoke test.

Sends a known prompt to OpenClaw via run_task.py and verifies the agent
responds correctly. Sends Telegram result.

Distinct from factory_health.py (which checks Docker/LiteLLM infrastructure):
this verifies that the GLM-5.1 agent chain actually reasons and responds.

Run:
    python3 /opt/nous-agaas/smoke_test.py
Cron:
    0 3 * * * source /root/nous-agaas/.env && python3 /opt/nous-agaas/smoke_test.py >> /root/nous-agaas/logs/smoke_test.log 2>&1
"""

import json
import logging
import os
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

KZ_TZ = timezone(timedelta(hours=5))

# ── Configuration ─────────────────────────────────────────────────────────────

VENV_PYTHON = "/root/nous-agaas/venv/bin/python3"
RUN_TASK = "/opt/nous-agaas/run_task.py"
RUN_TASK_TIMEOUT = 60          # seconds; agent should respond well within this
EXPECTED_MARKER = "SMOKE_OK"
# Outcome probe — verifies agent can answer from wiki context, not just run
OUTCOME_QUESTION = (
    "From the injected factory context, what is the status of the "
    "NIIS software registration? Name the lawyer handling it and the application number."
)
OUTCOME_MARKERS = ["Nazel", "455466", "newcab.kazpatent.kz"]
OUTCOME_TIMEOUT = 120  # seconds — context injection adds latency
   # agent must echo this back
BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
HTTP_TIMEOUT = 10
LOG_PATH = Path("/opt/nous-agaas/logs/smoke_test.log")


def build_probe_message(ts: datetime | None = None) -> str:
    """Build the deterministic probe message sent to the agent."""
    if ts is None:
        ts = datetime.now(KZ_TZ)
    date_str = ts.strftime("%Y-%m-%d")
    return f'Reply with exactly this text and nothing else: {EXPECTED_MARKER}_{date_str}'


def run_probe(probe_message: str, timeout: int = RUN_TASK_TIMEOUT) -> tuple[bool, str]:
    """
    Run the probe message through run_task.py.

    Returns:
        (ok, detail_message)
        ok=True  → agent responded and output contains EXPECTED_MARKER
        ok=False → subprocess error, timeout, or wrong output
    """
    try:
        proc = subprocess.run(
            [VENV_PYTHON, RUN_TASK, "--no-context", probe_message],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout.strip()

        if proc.returncode != 0:
            stderr = proc.stderr.strip()[:200]
            return False, f"exit {proc.returncode}: {stderr or '(no stderr)'}"

        if not output:
            return False, "agent returned empty output"

        if EXPECTED_MARKER not in output:
            preview = output[:120]
            return False, f"marker missing in output: {preview!r}"

        return True, output

    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except FileNotFoundError:
        return False, f"run_task.py not found at {RUN_TASK}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def send_telegram(text: str, bot_token: str | None = None, chat_id: str | None = None) -> bool:
    """Send Telegram message. Returns True on success."""
    if bot_token is None:
        bot_token = os.environ.get(BOT_TOKEN_ENV, "")
    if chat_id is None:
        chat_id = os.environ.get(CHAT_ID_ENV, "")
    if not bot_token or not chat_id:
        log.warning("smoke_test: BOT_TOKEN or CHAT_ID not set — skipping Telegram send")
        return False

    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT):
            return True
    except Exception as exc:
        log.error("smoke_test: Telegram send failed: %s", exc)
        return False


def format_result(ok: bool, detail: str, duration_ms: int) -> str:
    """Format smoke test result as Telegram HTML message."""
    ts = datetime.now(KZ_TZ).strftime("%Y-%m-%d %H:%M Almaty")
    icon = "🟢" if ok else "🔴"
    status = "PASSED" if ok else "FAILED"
    lines = [
        f"{icon} <b>Daily smoke test {status}</b> — {ts}",
        f"Duration: {duration_ms}ms",
    ]
    if ok:
        lines.append(f"Agent replied: <code>{detail[:80]}</code>")
    else:
        lines.append(f"Reason: {detail}")
        lines.append("Check: <code>tail /root/nous-agaas/logs/smoke_test.log</code>")
    return "\n".join(lines)




def run_outcome_probe(timeout: int = OUTCOME_TIMEOUT) -> tuple[bool, str]:
    """Verify the agent answers a real project question from injected wiki context.

    This proves outcome correctness, not just mechanical health. The agent must
    identify Nazel Urist (lawyer), application #455466, or newcab.kazpatent.kz.
    """
    try:
        proc = subprocess.run(
            [VENV_PYTHON, RUN_TASK, OUTCOME_QUESTION],  # WITH context injection
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout.strip()
        if proc.returncode != 0:
            return False, f"exit {proc.returncode}: {proc.stderr.strip()[:200]}"
        for marker in OUTCOME_MARKERS:
            if marker in output:
                return True, f"found {marker!r} in response"
        preview = output[:150]
        return False, f"none of {OUTCOME_MARKERS} in: {preview!r}"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

def run_smoke_test(
    bot_token: str | None = None,
    chat_id: str | None = None,
    probe_timeout: int = RUN_TASK_TIMEOUT,
) -> tuple[bool, str]:
    """
    Full smoke test: probe → verify → notify.

    Returns:
        (ok, detail_message)
    """
    now = datetime.now(KZ_TZ)
    probe_message = build_probe_message(now)
    log.info("smoke_test: probe message: %s", probe_message[:60])

    t0 = datetime.now(KZ_TZ)
    ok, detail = run_probe(probe_message, timeout=probe_timeout)
    duration_ms = int((datetime.now(KZ_TZ) - t0).total_seconds() * 1000)

    log.info("smoke_test: ok=%s duration=%dms detail=%s", ok, duration_ms, detail[:80])

    # Outcome probe — verify agent can answer a real project question
    outcome_ok, outcome_detail = run_outcome_probe()
    log.info("smoke_test: outcome_ok=%s detail=%s", outcome_ok, outcome_detail[:80])
    if not outcome_ok:
        ok = False
        detail = f"mechanism OK but outcome FAIL: {outcome_detail}"
        log.error("smoke_test: outcome probe FAILED — factory cannot answer project questions")

    text = format_result(ok, detail, duration_ms)
    sent = send_telegram(text, bot_token=bot_token, chat_id=chat_id)
    if not sent:
        log.warning("smoke_test: Telegram send skipped or failed")

    return ok, detail


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ok, detail = run_smoke_test()
    if ok:
        print(f"✅ SMOKE_OK: {detail[:60]}")
    else:
        print(f"❌ SMOKE_FAIL: {detail}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
