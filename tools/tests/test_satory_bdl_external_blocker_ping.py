from __future__ import annotations

import datetime as dt

from tools import satory_bdl_external_blocker_ping as ping


def _check(name: str, status: str, detail: str = "ok") -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def _report(*, proof: str = "GREEN", freshness: str = "GREEN") -> dict:
    checks = [
        _check("external_proof_receipt", proof, "proof"),
        _check("listener", freshness),
        _check("event_ingestion", freshness),
        _check("fleet_health", freshness),
        _check("law002_classification", freshness),
        _check("erap_queue", freshness),
        _check("operator_portal", freshness),
        {"check": "bdl_replacement", "status": freshness, "blockers": ["blocker"] if freshness != "GREEN" else []},
    ]
    return {"overall": "GREEN" if proof == freshness == "GREEN" else "RED", "checks": checks}


def test_stop_condition_requires_proof_and_freshness() -> None:
    assert ping._stop_condition_met(_report(proof="GREEN", freshness="GREEN"))
    assert not ping._stop_condition_met(_report(proof="RED", freshness="GREEN"))
    assert not ping._stop_condition_met(_report(proof="GREEN", freshness="RED"))


def test_ping_window_is_weekday_0800_kzt_only() -> None:
    monday_0800 = dt.datetime(2026, 5, 18, 8, 0, tzinfo=ping.KZT)
    monday_0830 = dt.datetime(2026, 5, 18, 8, 30, tzinfo=ping.KZT)
    monday_1700 = dt.datetime(2026, 5, 18, 17, 0, tzinfo=ping.KZT)
    sunday_0800 = dt.datetime(2026, 5, 17, 8, 0, tzinfo=ping.KZT)

    assert ping._is_ping_window(monday_0800)
    assert not ping._is_ping_window(monday_0830)
    assert not ping._is_ping_window(monday_1700)
    assert not ping._is_ping_window(sunday_0800)


def test_message_names_asyl_denis_and_stop_condition() -> None:
    # AP-1 (2026-05-21): template is Russian for the operators group. Test
    # asserts Cyrillic markers (Асыл/Денис) + retained English technical
    # tokens (HTTP-200, BDL/Cerebro) + Russian stop-condition phrase.
    # Negative asserts guard against language drift back to English.
    message = ping._build_message(
        _report(proof="RED", freshness="GREEN"),
        dt.datetime(2026, 5, 18, 8, 0, tzinfo=ping.KZT),
    )

    assert "Асыл" in message, "must address Asyl in Cyrillic for the Russian operators group"
    assert "Денис" in message, "must address Denis in Cyrillic for the Russian operators group"
    assert "HTTP-200" in message, "technical token retained in English"
    assert "BDL/Cerebro" in message, "doctrine name retained"
    assert "Условие остановки:" in message, "stop-condition phrase must be Russian"
    # Negative: English phrasings must NOT appear (audience-language drift gate).
    assert "Asyl:" not in message, "Latin 'Asyl:' indicates language drift back to English"
    assert "Denis:" not in message, "Latin 'Denis:' indicates language drift back to English"
    assert "Stop condition: external-proof receipt" not in message, "English stop-condition indicates language drift"


def test_send_failure_reason_names_exit_code_4() -> None:
    assert ping._send_failure_reason(0) == ""
    assert ping._send_failure_reason(4) == "tg_send_policy_block_exit_4"
    assert ping._send_failure_reason(3) == "tg_send_failed"
