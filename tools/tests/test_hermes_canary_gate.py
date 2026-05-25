from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import hermes_canary_gate as gate


def _args(tmp_path: Path, smoke: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        wiki=tmp_path,
        alias="hermes-nouscanary",
        profile="nouscanary",
        codex_cli="codex",
        openclaw_health_url="http://openclaw/health",
        litellm_health_url="http://litellm/health",
        webui_health_url="http://webui/health",
        webui_events_url="http://webui/api/factory-events?limit=1",
        webui_env_file=tmp_path / "hermes-webui.env",
        factory_probe=False,
        webui_probe=False,
        smoke=smoke,
        smoke_timeout=1,
        json=True,
    )


def test_gate_green_when_canary_is_isolated(monkeypatch, tmp_path: Path) -> None:
    def fake_http(url: str, timeout: float = 5.0):
        return True, "HTTP 200"

    def fake_run(cmd, **kwargs):
        joined = " ".join(cmd)
        if joined == "launchctl list":
            return {"ok": True, "returncode": 0, "stdout": "123\t0\tcom.nous.telegram-poll", "stderr": ""}
        if joined == "command -v hermes-nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "/Users/madia/.local/bin/hermes-nouscanary\n", "stderr": ""}
        if joined == "hermes profile show nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "Profile: nouscanary\nGateway: stopped\n.env:    exists\n", "stderr": ""}
        if joined == "hermes-nouscanary status":
            return {
                "ok": True,
                "returncode": 0,
                "stdout": "Model:        gpt-5.5\nProvider:     OpenAI Codex\nTelegram      ✗ not configured\nStatus:       ✗ not loaded\n",
                "stderr": "",
            }
        raise AssertionError(joined)

    monkeypatch.setattr(gate, "http_status", fake_http)
    monkeypatch.setattr(gate, "webui_factory_events_status", lambda *_args, **_kwargs: (True, "events ok"))
    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(
        gate.shutil,
        "which",
        lambda name: f"/Users/madia/.local/bin/{name}" if name in {"hermes-nouscanary", "codex"} else None,
    )

    result = gate.evaluate(_args(tmp_path))

    assert result["overall"] == "GREEN"
    assert result["reds"] == 0


def test_gate_accepts_new_gateway_stopped_wording(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gate, "http_status", lambda *_args, **_kwargs: (True, "HTTP 200"))
    monkeypatch.setattr(
        gate.shutil,
        "which",
        lambda name: f"/Users/madia/.local/bin/{name}" if name in {"hermes-nouscanary", "codex"} else None,
    )

    def fake_run(cmd, **kwargs):
        joined = " ".join(cmd)
        if joined == "launchctl list":
            return {"ok": True, "returncode": 0, "stdout": "123\t0\tcom.nous.telegram-poll", "stderr": ""}
        if joined == "hermes profile show nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "Profile: nouscanary\nGateway: stopped\n.env:    exists\n", "stderr": ""}
        if joined == "hermes-nouscanary status":
            return {
                "ok": True,
                "returncode": 0,
                "stdout": "Model:        gpt-5.5\nProvider:     OpenAI Codex\nTelegram      ✗ not configured\nStatus:       ✗ stopped\n",
                "stderr": "",
            }
        raise AssertionError(joined)

    monkeypatch.setattr(gate, "run", fake_run)

    result = gate.evaluate(_args(tmp_path))

    assert result["overall"] == "GREEN"
    assert result["reds"] == 0


def test_gate_red_when_hermes_gateway_loaded(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gate, "http_status", lambda *_args, **_kwargs: (True, "HTTP 200"))
    monkeypatch.setattr(
        gate.shutil,
        "which",
        lambda name: f"/Users/madia/.local/bin/{name}" if name in {"hermes-nouscanary", "codex"} else None,
    )

    def fake_run(cmd, **kwargs):
        joined = " ".join(cmd)
        if joined == "launchctl list":
            return {"ok": True, "returncode": 0, "stdout": "123\t0\tcom.nous.telegram-poll", "stderr": ""}
        if joined == "command -v hermes-nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "/Users/madia/.local/bin/hermes-nouscanary\n", "stderr": ""}
        if joined == "hermes profile show nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "Profile: nouscanary\nGateway: stopped\n.env:    exists\n", "stderr": ""}
        if joined == "hermes-nouscanary status":
            return {
                "ok": True,
                "returncode": 0,
                "stdout": "Model:        gpt-5.5\nProvider:     OpenAI Codex\nTelegram      ✓ configured\nStatus:       ✓ loaded\n",
                "stderr": "",
            }
        raise AssertionError(joined)

    monkeypatch.setattr(gate, "run", fake_run)

    result = gate.evaluate(_args(tmp_path))

    assert result["overall"] == "RED"
    assert any(item["check"] == "hermes_gateway_not_production" for item in result["checks"] if item["status"] == "RED")


def test_gate_can_require_webui_health(monkeypatch, tmp_path: Path) -> None:
    urls: list[str] = []

    def fake_http(url: str, timeout: float = 5.0):
        urls.append(url)
        return True, "HTTP 200"

    def fake_run(cmd, **kwargs):
        joined = " ".join(cmd)
        if joined == "launchctl list":
            return {"ok": True, "returncode": 0, "stdout": "123\t0\tcom.nous.telegram-poll", "stderr": ""}
        if joined == "hermes profile show nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "Profile: nouscanary\nGateway: stopped\n.env:    exists\n", "stderr": ""}
        if joined == "hermes-nouscanary status":
            return {
                "ok": True,
                "returncode": 0,
                "stdout": "Model:        gpt-5.5\nProvider:     OpenAI Codex\nTelegram      ✗ not configured\nStatus:       ✗ not loaded\n",
                "stderr": "",
            }
        raise AssertionError(joined)

    args = _args(tmp_path)
    args.webui_probe = True

    monkeypatch.setattr(gate, "http_status", fake_http)
    monkeypatch.setattr(gate, "webui_factory_events_status", lambda *_args, **_kwargs: (True, "events ok"))
    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(
        gate.shutil,
        "which",
        lambda name: f"/Users/madia/.local/bin/{name}" if name in {"hermes-nouscanary", "codex"} else None,
    )

    result = gate.evaluate(args)

    assert result["overall"] == "GREEN"
    assert "http://webui/health" in urls
    assert any(item["check"] == "hermes_webui_canary_health" for item in result["checks"])
    assert any(item["check"] == "hermes_webui_factory_events_auth" for item in result["checks"])


def test_gate_red_when_webui_events_auth_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gate, "http_status", lambda *_args, **_kwargs: (True, "HTTP 200"))
    monkeypatch.setattr(gate, "webui_factory_events_status", lambda *_args, **_kwargs: (False, "HTTP 401"))
    monkeypatch.setattr(
        gate.shutil,
        "which",
        lambda name: f"/Users/madia/.local/bin/{name}" if name in {"hermes-nouscanary", "codex"} else None,
    )

    def fake_run(cmd, **kwargs):
        joined = " ".join(cmd)
        if joined == "launchctl list":
            return {"ok": True, "returncode": 0, "stdout": "123\t0\tcom.nous.telegram-poll", "stderr": ""}
        if joined == "hermes profile show nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "Profile: nouscanary\nGateway: stopped\n.env:    exists\n", "stderr": ""}
        if joined == "hermes-nouscanary status":
            return {
                "ok": True,
                "returncode": 0,
                "stdout": "Model:        gpt-5.5\nProvider:     OpenAI Codex\nTelegram      ✗ not configured\nStatus:       ✗ not loaded\n",
                "stderr": "",
            }
        raise AssertionError(joined)

    args = _args(tmp_path)
    args.webui_probe = True
    monkeypatch.setattr(gate, "run", fake_run)

    result = gate.evaluate(args)

    assert result["overall"] == "RED"
    assert any(item["check"] == "hermes_webui_factory_events_auth" for item in result["checks"] if item["status"] == "RED")


def test_gate_red_when_codex_cli_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gate, "http_status", lambda *_args, **_kwargs: (True, "HTTP 200"))
    monkeypatch.setattr(gate.shutil, "which", lambda name: "/Users/madia/.local/bin/hermes-nouscanary" if name == "hermes-nouscanary" else None)

    def fake_run(cmd, **kwargs):
        joined = " ".join(cmd)
        if joined == "launchctl list":
            return {"ok": True, "returncode": 0, "stdout": "123\t0\tcom.nous.telegram-poll", "stderr": ""}
        if joined == "hermes profile show nouscanary":
            return {"ok": True, "returncode": 0, "stdout": "Profile: nouscanary\nGateway: stopped\n.env:    exists\n", "stderr": ""}
        if joined == "hermes-nouscanary status":
            return {
                "ok": True,
                "returncode": 0,
                "stdout": "Model:        gpt-5.5\nProvider:     OpenAI Codex\nTelegram      ✗ not configured\nStatus:       ✗ not loaded\n",
                "stderr": "",
            }
        raise AssertionError(joined)

    monkeypatch.setattr(gate, "run", fake_run)

    result = gate.evaluate(_args(tmp_path))

    assert result["overall"] == "RED"
    assert any(item["check"] == "codex_cli_available" for item in result["checks"] if item["status"] == "RED")


def test_run_reports_missing_executable() -> None:
    result = gate.run(["definitely-not-a-real-hermes-test-command"])

    assert result["ok"] is False
    assert result["returncode"] == 127
    assert "missing executable" in result["stderr"]
