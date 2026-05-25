"""Tests for the append-only ops event ledger."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import log_event


def _use_tmp_ledger(monkeypatch, tmp_path):
    path = tmp_path / "state" / "ops_events.jsonl"
    monkeypatch.setenv(log_event.LEDGER_ENV, str(path))
    return path


def test_append_event_writes_schema_and_returns_intent_id(monkeypatch, tmp_path):
    ledger = _use_tmp_ledger(monkeypatch, tmp_path)
    payload = {"kind": "todoist_delta", "task_id": "123"}

    intent_id = log_event.append_event(
        "todoist_sync",
        "task:123",
        "codex-pane2",
        payload,
        "corr-1",
    )

    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    event = rows[0]
    assert set(event) == log_event.REQUIRED_FIELDS
    assert event["intent_id"] == intent_id
    assert event["idempotency_key"] == intent_id
    assert event["payload_hash"] == log_event.payload_hash(payload)
    assert event["source"] == "todoist_sync"
    assert event["external_id"] == "task:123"
    assert event["actor"] == "codex-pane2"
    assert event["correlation_id"] == "corr-1"
    assert event["version"] == log_event.SCHEMA_VERSION


def test_replay_events_preserves_append_order(monkeypatch, tmp_path):
    _use_tmp_ledger(monkeypatch, tmp_path)

    first = log_event.append_event("todoist_sync", "task:1", "actor", {"n": 1}, "corr")
    second = log_event.append_event("todoist_sync", "task:2", "actor", {"n": 2}, "corr")

    events = log_event.replay_events()
    assert [event["intent_id"] for event in events] == [first, second]
    assert [event["external_id"] for event in events] == ["task:1", "task:2"]


def test_idempotency_key_deduplicates_appends(monkeypatch, tmp_path):
    ledger = _use_tmp_ledger(monkeypatch, tmp_path)
    payload = {"idempotency_key": "todoist-command-uuid", "delta": "created"}

    first = log_event.append_event("todoist_sync", "task:1", "actor", payload, "corr")
    second = log_event.append_event("todoist_sync", "task:1", "actor", payload, "corr")

    assert first == second
    assert log_event.check_idempotent("todoist-command-uuid") is True
    assert log_event.check_idempotent("missing-command") is False
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_payload_hash_verification_detects_tampering(monkeypatch, tmp_path):
    _use_tmp_ledger(monkeypatch, tmp_path)
    payload = {"idempotency_key": "cmd-1", "value": "original"}
    log_event.append_event("todoist_sync", "task:1", "actor", payload, "corr")

    event = log_event.replay_events()[0]
    assert event["payload_hash"] == log_event.payload_hash(payload)
    assert event["payload_hash"] != log_event.payload_hash({"idempotency_key": "cmd-1", "value": "tampered"})


def test_malformed_payload_rejected_without_writing(monkeypatch, tmp_path):
    ledger = _use_tmp_ledger(monkeypatch, tmp_path)

    with pytest.raises(log_event.EventLedgerError, match="payload must be a JSON object"):
        log_event.append_event("todoist_sync", "task:1", "actor", ["not", "object"], "corr")  # type: ignore[arg-type]

    with pytest.raises(log_event.EventLedgerError, match="JSON-serializable"):
        log_event.append_event("todoist_sync", "task:1", "actor", {"bad": object()}, "corr")

    assert not ledger.exists()


def test_malformed_ledger_line_rejected_on_replay(monkeypatch, tmp_path):
    ledger = _use_tmp_ledger(monkeypatch, tmp_path)
    ledger.parent.mkdir(parents=True)
    ledger.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(log_event.EventLedgerError, match="malformed ledger JSON"):
        log_event.replay_events()
