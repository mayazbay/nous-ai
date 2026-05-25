import importlib.util
import json
import os
import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import langsmith_observer as obs


def test_redacts_secret_keys_and_values():
    payload = {
        "api_key": "lsv2_should_not_show_abcdefghijklmnopqrstuvwxyz",
        "nested": {"Authorization": "Bearer secret"},
        "text": "token sk-abcdefghijklmnopqrstuvwxyz123456 should be hidden",
    }
    redacted = obs.redact(payload)
    assert redacted["api_key"] == "<redacted>"
    assert redacted["nested"]["Authorization"] == "<redacted>"
    assert "sk-" not in redacted["text"]


def test_redaction_preserves_safe_token_metrics():
    redacted = obs.redact({"input_tokens": 123, "output_tokens": 45, "api_token": "secret"})
    assert redacted["input_tokens"] == 123
    assert redacted["output_tokens"] == 45
    assert redacted["api_token"] == "<redacted>"


def test_config_uses_new_project_not_legacy_langchain_project(monkeypatch, tmp_path):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_test_key")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "satory-vko-agents")
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("NOUS_LANGSMITH_PROJECT", raising=False)
    monkeypatch.setenv("NOUS_LANGSMITH_LOG", str(tmp_path / "langsmith.jsonl"))

    config = obs.get_config(load_env=False)

    assert config.tracing is True
    assert config.api_key_present is True
    assert config.project == "nous-agaas-control-plane"
    assert config.workspace_id == obs.DEFAULT_WORKSPACE_ID


def test_emit_event_always_writes_local_jsonl(monkeypatch, tmp_path):
    log = tmp_path / "langsmith.jsonl"
    monkeypatch.setenv("NOUS_LANGSMITH_LOG", str(log))
    monkeypatch.setenv("NOUS_LANGSMITH_DISABLE", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_test_key")

    event = obs.emit_event(
        "nous.test",
        inputs={"prompt": "hello"},
        outputs={"answer": "world"},
        metadata={"source": "unit-test"},
        tags=["test"],
    )

    assert event["name"] == "nous.test"
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["name"] == "nous.test"
    assert rows[0]["langsmith"]["reason"] == "disabled_by_env"


def test_sdk_availability_probe_matches_importlib():
    config = obs.get_config(load_env=False)
    assert config.sdk_available == (importlib.util.find_spec("langsmith") is not None)
