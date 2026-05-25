from __future__ import annotations

from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from telegram_ask_e2e_probe import classify  # noqa: E402


def test_classify_green_when_nonce_routes_to_openclaw_and_reply_sends() -> None:
    logs = {
        "telegram_poll.err": "\n".join(
            [
                "2026-05-17 15:12:01 +05 [INFO] Natural command: chat=110793056 msg_id=1801 text='/ask E2E-CODEX-123 reply OK'",
                "2026-05-17 15:12:02 +05 [INFO] _tg_send sent OK: chat=110793056 bot_msg_id=9001 reply_to=1801 text_len=48",
                "2026-05-17 15:12:15 +05 [INFO] _tg_send sent OK: chat=110793056 bot_msg_id=9002 reply_to=1801 text_len=210",
                "2026-05-17 15:12:15 +05 [INFO] /ask handled: chat=110793056 q_len=28 r_len=210",
            ]
        ),
        "ask-hierarchy.jsonl": '{"correlation_id":"tg_1801","decision":"ok","model":"grok-reasoning"}\n',
        "launchd": "123\t0\tcom.nous.telegram-poll\n",
    }

    result = classify(logs, "E2E-CODEX-123")

    assert result["status"] == "GREEN"
    assert result["msg_id"] == "1801"
    assert result["correlation_id"] == "tg_1801"
    assert result["checks"] == {
        "inbound_nonce_seen": True,
        "correlation_id_found": True,
        "openclaw_decision_ok": True,
        "ask_handled_logged": True,
        "telegram_reply_sent": True,
    }


def test_classify_yellow_when_inbound_is_missing() -> None:
    logs = {
        "telegram_poll.err": "2026-05-15 09:24:27 +05 [INFO] /ask handled: chat=110793056 q_len=22 r_len=288\n",
        "ask-hierarchy.jsonl": "",
        "launchd": "",
    }

    result = classify(logs, "E2E-CODEX-404")

    assert result["status"] == "YELLOW"
    assert result["checks"]["inbound_nonce_seen"] is False
    assert result["checks"]["ask_handled_logged"] is False
    assert result["checks"]["telegram_reply_sent"] is False


def test_classify_yellow_when_worker_finishes_but_send_success_is_not_logged() -> None:
    logs = {
        "telegram_poll.err": "\n".join(
            [
                "2026-05-17 15:12:01 +05 [INFO] Natural command: chat=110793056 msg_id=1801 text='/ask E2E-CODEX-123 reply OK'",
                "2026-05-17 15:12:15 +05 [INFO] /ask handled: chat=110793056 q_len=28 r_len=210",
            ]
        ),
        "ask-hierarchy.jsonl": '{"correlation_id":"tg_1801","decision":"ok","model":"grok-reasoning"}\n',
    }

    result = classify(logs, "E2E-CODEX-123")

    assert result["status"] == "YELLOW"
    assert result["checks"]["openclaw_decision_ok"] is True
    assert result["checks"]["telegram_reply_sent"] is False
