"""Tests for VPS-side Air watchdog alerting."""

from __future__ import annotations

import argparse
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import air_watchdog


def _args(tmp_path):
    return argparse.Namespace(
        health_url="http://air/healthz",
        air_ssh="madia@air",
        poller_label="com.nous.telegram-poll",
        state_path=str(tmp_path / "state.json"),
        tg_send=str(tmp_path / "tg_send.sh"),
        timeout=0.1,
        fail_threshold=3,
        no_poller_check=False,
    )


def test_three_consecutive_failures_send_one_alert(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setattr(air_watchdog, "check_http", lambda *_args: (False, "http_error:down"))
    monkeypatch.setattr(air_watchdog, "check_poller", lambda *_args: (False, "poller_label_missing"))
    monkeypatch.setattr(air_watchdog, "send_alert", lambda _path, message: (sent.append(message) or True, "sent"))
    args = _args(tmp_path)

    codes = [air_watchdog.evaluate(args)[0] for _ in range(4)]

    assert codes == [2, 2, 2, 2]
    assert len(sent) == 1
    assert sent[0].startswith("🔴 Air poller dead")
    state = air_watchdog.load_state(pathlib.Path(args.state_path))
    assert state["fail_count"] == 4
    assert state["alert_active"] is True


def test_success_resets_failure_state(monkeypatch, tmp_path):
    sent = []
    args = _args(tmp_path)
    monkeypatch.setattr(air_watchdog, "send_alert", lambda _path, message: (sent.append(message) or True, "sent"))
    monkeypatch.setattr(air_watchdog, "check_http", lambda *_args: (False, "http_error:down"))
    monkeypatch.setattr(air_watchdog, "check_poller", lambda *_args: (False, "poller_label_missing"))
    for _ in range(3):
        air_watchdog.evaluate(args)

    monkeypatch.setattr(air_watchdog, "check_http", lambda *_args: (True, "http_200"))
    monkeypatch.setattr(air_watchdog, "check_poller", lambda *_args: (True, "poller_ok:123 0 label"))
    code, payload = air_watchdog.evaluate(args)

    assert code == 0
    assert payload["ok"] is True
    state = air_watchdog.load_state(pathlib.Path(args.state_path))
    assert state["fail_count"] == 0
    assert state["alert_active"] is False


def test_poller_failure_alerts_even_when_http_is_green(monkeypatch, tmp_path):
    sent = []
    args = _args(tmp_path)
    monkeypatch.setattr(air_watchdog, "check_http", lambda *_args: (True, "http_200"))
    monkeypatch.setattr(air_watchdog, "check_poller", lambda *_args: (False, "poller_label_missing"))
    monkeypatch.setattr(air_watchdog, "send_alert", lambda _path, message: (sent.append(message) or True, "sent"))

    for _ in range(3):
        code, payload = air_watchdog.evaluate(args)

    assert code == 2
    assert payload["alert_sent"] is True
    assert "poller=poller_label_missing" in sent[0]


def test_http_green_poller_ssh_timeout_is_unknown_not_dead(monkeypatch, tmp_path):
    sent = []
    args = _args(tmp_path)
    monkeypatch.setattr(air_watchdog, "check_http", lambda *_args: (True, "http_200"))
    monkeypatch.setattr(
        air_watchdog,
        "check_poller",
        lambda *_args: (False, "poller_ssh_error:timed out after 7.0 seconds"),
    )
    monkeypatch.setattr(air_watchdog, "send_alert", lambda _path, message: (sent.append(message) or True, "sent"))

    code, payload = air_watchdog.evaluate(args)

    assert code == 0
    assert payload["ok"] is True
    assert payload["checks"]["poller"].startswith("poller_unknown_ssh_transport:")
    assert sent == []


def test_running_poller_pid_overrides_stale_negative_exit_status():
    ok, detail = air_watchdog.parse_launchctl_line("73732 -15 com.nous.telegram-poll")

    assert ok is True
    assert detail == "poller_ok:73732 -15 com.nous.telegram-poll"
