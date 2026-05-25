"""Tests for the read-only Todoist Sync API poller."""

from __future__ import annotations

import json
import pathlib
import types
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import log_event
import todoist_sync


def _state(monkeypatch, tmp_path):
    state = tmp_path / "state"
    monkeypatch.setenv(todoist_sync.STATE_ENV, str(state))
    monkeypatch.setenv(log_event.LEDGER_ENV, str(state / "ops_events.jsonl"))
    return state


def test_sync_form_is_read_only():
    form = todoist_sync.sync_form("*", ["items"])

    assert form == {"sync_token": "*", "resource_types": '["items"]'}
    assert "commands" not in form


def test_poll_once_uses_sync_token_and_logs_deltas(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    seen = {}

    def fake_request(api_token, sync_token, resource_types):
        seen["api_token"] = api_token
        seen["sync_token"] = sync_token
        seen["resource_types"] = resource_types
        return {
            "sync_token": "next-token",
            "full_sync": True,
            "items": [{"id": "task-1", "content": "Check ledger"}],
            "projects": [{"id": "project-1", "name": "Ops"}],
        }

    monkeypatch.setattr(todoist_sync, "request_sync", fake_request)

    result = todoist_sync.poll_once(
        api_token="token",
        owner="air",
        resource_types=["items", "projects"],
        correlation_id="corr",
    )

    assert seen == {
        "api_token": "token",
        "sync_token": "*",
        "resource_types": ["items", "projects"],
    }
    assert result["events_logged"] == 2
    assert result["new_sync_token"] == "next-token"
    assert (state / "todoist_sync_token").read_text(encoding="utf-8").strip() == "next-token"
    assert not (state / "todoist_sync_token.pending").exists()
    events = log_event.replay_events()
    assert [event["external_id"] for event in events] == ["items:task-1", "projects:project-1"]


def test_poll_once_reuses_cached_sync_token(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    state.mkdir()
    (state / "todoist_sync_token").write_text("old-token\n", encoding="utf-8")

    def fake_request(_api_token, sync_token, _resource_types):
        assert sync_token == "old-token"
        return {"sync_token": "new-token", "items": []}

    monkeypatch.setattr(todoist_sync, "request_sync", fake_request)

    result = todoist_sync.poll_once(api_token="token", owner="air")

    assert result["old_sync_token"] == "old-token"
    assert (state / "todoist_sync_token").read_text(encoding="utf-8").strip() == "new-token"


def test_duplicate_delta_replay_deduplicates_ledger(monkeypatch, tmp_path):
    _state(monkeypatch, tmp_path)
    response = {
        "sync_token": "next-token",
        "items": [{"id": "task-1", "content": "same"}],
    }
    monkeypatch.setattr(todoist_sync, "request_sync", lambda *_args: response)

    todoist_sync.poll_once(api_token="token", owner="air")
    todoist_sync.poll_once(api_token="token", owner="air")

    events = log_event.replay_events()
    assert len(events) == 1
    assert events[0]["idempotency_key"].startswith("todoist-sync:items:task-1:")


def test_pending_token_written_before_delta_handler(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    monkeypatch.setattr(
        todoist_sync,
        "request_sync",
        lambda *_args: {"sync_token": "next-token", "items": [{"id": "task-1"}]},
    )
    monkeypatch.setattr(todoist_sync, "log_deltas", lambda *_args: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        todoist_sync.poll_once(api_token="token", owner="air")

    assert (state / "todoist_sync_token.pending").read_text(encoding="utf-8").strip() == "next-token"
    assert not (state / "todoist_sync_token").exists()


def test_loop_poll_cycle_contains_transient_todoist_http_error(monkeypatch, capsys):
    args = types.SimpleNamespace(interval=300.0, error_backoff=60.0)
    monkeypatch.setattr(
        todoist_sync,
        "poll_once",
        lambda **_kwargs: (_ for _ in ()).throw(todoist_sync.requests.HTTPError("503 Server Error")),
    )

    next_poll = todoist_sync.run_due_poll(
        args, api_token="token", owner="air", resource_types=["items"], now=1000.0
    )

    payload = json.loads(capsys.readouterr().out)
    assert next_poll == 1060.0
    assert payload == {"detail": "503 Server Error", "error": "HTTPError", "ok": False}
