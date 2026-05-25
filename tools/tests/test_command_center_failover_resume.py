from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
cost_tracker = types.ModuleType("cost_tracker")
cost_tracker.daily_report = lambda *args, **kwargs: {}
cost_tracker.format_report = lambda *args, **kwargs: ""
sys.modules.setdefault("cost_tracker", cost_tracker)

factory_health = types.ModuleType("factory_health")
factory_health.run_checks = lambda *args, **kwargs: []
factory_health._load_extra_envs = lambda *args, **kwargs: {}
sys.modules.setdefault("factory_health", factory_health)

sys.path.insert(0, str(TOOLS_DIR))
spec = importlib.util.spec_from_file_location("command_center_failover_under_test", TOOLS_DIR / "command_center.py")
assert spec and spec.loader
command_center = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command_center)


def test_extract_query_supports_resume_prefix() -> None:
    assert command_center.extract_query("/resume gpt") == "gpt"


def test_failover_capture_can_be_disabled_by_env(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setenv("NOUS_FAILOVER_CAPTURE", "0")
    monkeypatch.setattr(
        command_center,
        "_start_failover_event",
        lambda **kwargs: calls.append(kwargs) or "event-should-not-write",
    )

    event_id = command_center._failover_start(
        "/ask",
        1,
        110793056,
        "probe should not mutate ledger",
        model="openclaw-router",
        via="test",
    )

    assert event_id is None
    assert calls == []


def test_failover_capture_defaults_off_under_pytest(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.delenv("NOUS_FAILOVER_CAPTURE", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_command_center.py::case")
    monkeypatch.setattr(
        command_center,
        "_start_failover_event",
        lambda **kwargs: calls.append(kwargs) or "event-should-not-write",
    )

    event_id = command_center._failover_start(
        "/ask",
        1,
        110793056,
        "pytest should not mutate ledger",
        model="openclaw-router",
        via="test",
    )

    assert event_id is None
    assert calls == []


def test_resume_without_target_sends_latest_status(monkeypatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(command_center, "_format_failover_resume_status", lambda: "latest failover")
    monkeypatch.setattr(command_center, "_tg_send", lambda token, chat, text, reply_to=None: sent.append(text))

    assert command_center.handle("token", 110793056, 1800, "/resume") is True
    assert sent == ["latest failover"]


def test_resume_gpt_runs_codex_with_resume_prompt(monkeypatch) -> None:
    sent: list[str] = []
    starts: list[dict] = []
    finishes: list[dict] = []

    monkeypatch.setattr(command_center, "_build_failover_resume_prompt", lambda target: f"resume prompt for {target}")
    monkeypatch.setattr(command_center, "_tg_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(command_center, "_tg_send", lambda token, chat, text, reply_to=None: sent.append(text))
    monkeypatch.setattr(command_center, "_run_codex", lambda prompt: f"codex saw: {prompt}")
    monkeypatch.setattr(command_center, "_write_telegram_task_result_receipt", lambda *args, **kwargs: "pages/task-results/resume.md")
    monkeypatch.setattr(command_center, "_observe_telegram_command", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        command_center,
        "_failover_start",
        lambda command, msg_id, chat_id, query, model, via: starts.append(
            {"command": command, "query": query, "model": model, "via": via}
        ) or "event-1",
    )
    monkeypatch.setattr(
        command_center,
        "_failover_finish",
        lambda event_id, response, status=None, receipt=None: finishes.append(
            {"event_id": event_id, "response": response, "receipt": receipt}
        ),
    )

    assert command_center.handle("token", 110793056, 1801, "/resume gpt") is True
    assert starts[0]["command"] == "/resume-codex"
    assert starts[0]["query"] == "resume prompt for codex"
    assert starts[0]["model"] == command_center.CODEX_MODEL
    assert finishes[0]["event_id"] == "event-1"
    assert finishes[0]["receipt"] == "pages/task-results/resume.md"
    assert sent == ["codex saw: resume prompt for codex"]
