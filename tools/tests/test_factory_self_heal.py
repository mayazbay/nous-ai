from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import factory_self_heal as heal


def _args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        wiki=tmp_path,
        ledger=tmp_path / "logs/factory-self-heal.jsonl",
        state=tmp_path / "state/factory-self-heal-state.json",
        status_page=Path("pages/systems/factory-self-healing-supervisor-status.md"),
        source="test",
        stdin_probe_json=False,
        stdin_light_changes=False,
        notify=True,
        write_status=False,
        dry_run=False,
        json=True,
        max_attempts=1,
        probe_timeout=10,
        notification_ttl_seconds=3600,
    )


def _probe(overall: str, *checks: dict) -> dict:
    return {"overall": overall, "reds": sum(1 for row in checks if row.get("status") == "RED"), "checks": list(checks)}


def test_green_probe_is_silent(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    monkeypatch.setattr(heal, "run_probe", lambda _args: _probe("GREEN", {"check": "openclaw", "status": "GREEN", "detail": "ok"}))
    notifications = []
    monkeypatch.setattr(heal, "send_notification", lambda _args, report: notifications.append(report) or {"sent": False})

    result = heal.evaluate(args)

    assert result["overall"] == "green"
    assert notifications == []


def test_repair_then_green_does_not_notify(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    red = _probe("RED", {"check": "telegram_poller", "status": "RED", "detail": "crashed exit=1"})
    green = _probe("GREEN", {"check": "telegram_poller", "status": "GREEN", "detail": "running pid=123"})
    probes = [red, green]
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return {"ok": True, "cmd": " ".join(cmd), "stdout": "", "stderr": "", "returncode": 0}

    monkeypatch.setattr(heal, "run_probe", lambda _args: probes.pop(0))
    monkeypatch.setattr(heal, "run", fake_run)

    result = heal.evaluate(args)

    assert result["overall"] == "repaired"
    assert result["notification"]["sent"] is False
    assert any(cmd[:3] == ["launchctl", "kickstart", "-k"] for cmd in commands)


def test_unresolved_human_required_notifies_once(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    red = _probe("RED", {"check": "openrouter_cap", "status": "RED", "detail": "spend exceeds cap"})
    sends = []

    def fake_run(cmd, **kwargs):
        sends.append(cmd)
        return {"ok": True, "cmd": " ".join(cmd), "stdout": "sent", "stderr": "", "returncode": 0}

    monkeypatch.setattr(heal, "run_probe", lambda _args: red)
    monkeypatch.setattr(heal, "run", fake_run)

    first = heal.evaluate(args)
    second = heal.evaluate(args)

    assert first["overall"] == "human_required"
    assert first["notification"]["sent"] is True
    # Second call must be blocked — either by internal dedup or by notification_policy gate.
    assert second["notification"]["sent"] is False
    assert second["notification"]["reason"] in {"deduped", "policy_suppressed"}
    assert len([cmd for cmd in sends if cmd[:2] == ["bash", "tools/tg_send.sh"]]) == 1


def test_stdin_probe_json_repairs(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    args.stdin_probe_json = True
    green = _probe("GREEN", {"check": "openclaw", "status": "GREEN", "detail": "ok"})
    monkeypatch.setattr(heal, "run_probe", lambda _args: green)
    monkeypatch.setattr(heal, "run", lambda cmd, **kwargs: {"ok": True, "cmd": " ".join(cmd), "stdout": "", "stderr": "", "returncode": 0})

    red_text = json.dumps(_probe("RED", {"check": "openclaw", "status": "RED", "detail": "HTTP 000"}))
    result = heal.evaluate(args, red_text)

    assert result["overall"] == "repaired"


def test_shell_probes_delegate_to_supervisor() -> None:
    drift = (REPO_ROOT / "tools/factory_no_drift_probe.sh").read_text(encoding="utf-8")
    light = (REPO_ROOT / "tools/light-probe.sh").read_text(encoding="utf-8")

    assert "factory_self_heal.py" in drift
    assert "--stdin-probe-json" in drift
    assert "factory_self_heal.py" in light
    assert "--stdin-light-changes" in light
