"""Tests for bot_to_bot_gates.py — R1 of HANDSHAKE-2026-05-19-residuals.

Mock-only. No live Telegram, no live file watching.
Run: python3 -m pytest tools/tests/test_bot_to_bot_gates.py -q
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import bot_to_bot_gates as btb


# ---------------------------------------------------------------------------
# KillSwitchGate
# ---------------------------------------------------------------------------

def test_killswitch_rejects_when_env_not_true(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BOT_TO_BOT_ENABLED", raising=False)
    gate = btb.KillSwitchGate(tmp_path)
    result = gate.check({})
    assert result is not None
    assert result.code == "ERR_KILL_SWITCH_ENV"


def test_killswitch_allows_when_env_true_and_no_runtime_override(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BOT_TO_BOT_ENABLED", "true")
    gate = btb.KillSwitchGate(tmp_path)
    assert gate.check({}) is None


def test_killswitch_rejects_when_runtime_override_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BOT_TO_BOT_ENABLED", "true")
    state_path = tmp_path / btb.KILLSWITCH_STATE_REL
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps({"enabled": False, "reason": "operator killed via /kill"}))
    gate = btb.KillSwitchGate(tmp_path)
    result = gate.check({})
    assert result is not None
    assert result.code == "ERR_KILL_SWITCH_RUNTIME"
    assert "operator killed" in result.detail


def test_killswitch_treats_unparseable_state_as_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BOT_TO_BOT_ENABLED", "true")
    state_path = tmp_path / btb.KILLSWITCH_STATE_REL
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{this is not json")
    gate = btb.KillSwitchGate(tmp_path)
    result = gate.check({})
    assert result is not None
    assert result.code == "ERR_KILL_SWITCH_PARSE"


# ---------------------------------------------------------------------------
# LoopDepthGate
# ---------------------------------------------------------------------------

def test_loop_depth_allows_at_zero() -> None:
    gate = btb.LoopDepthGate(max_depth=2)
    assert gate.check({"thread_via_markers": []}) is None


def test_loop_depth_allows_at_one_below_max() -> None:
    gate = btb.LoopDepthGate(max_depth=2)
    assert gate.check({"thread_via_markers": ["bot_a"]}) is None


def test_loop_depth_rejects_at_max() -> None:
    gate = btb.LoopDepthGate(max_depth=2)
    result = gate.check({"thread_via_markers": ["bot_a", "bot_b"]})
    assert result is not None
    assert result.code == "ERR_LOOP_DEPTH"


def test_loop_depth_operator_bypass_via_handoff() -> None:
    gate = btb.LoopDepthGate(max_depth=2)
    # Even at depth=5, /handoff bypasses
    assert gate.check({"thread_via_markers": ["a", "b", "c", "d", "e"], "body": "/handoff bot_x do thing"}) is None


# ---------------------------------------------------------------------------
# DedupeGate
# ---------------------------------------------------------------------------

def test_dedupe_allows_first_occurrence(tmp_path) -> None:
    gate = btb.DedupeGate(tmp_path, window_s=300)
    result = gate.check({"sender_bot_id": "a", "recipient_bot_id": "b", "body": "hello"})
    assert result is None


def test_dedupe_rejects_repeat_within_window(tmp_path) -> None:
    gate = btb.DedupeGate(tmp_path, window_s=300)
    ctx = {"sender_bot_id": "a", "recipient_bot_id": "b", "body": "hello"}
    first = gate.check(ctx)
    assert first is None
    second = gate.check(ctx)
    assert second is not None
    assert second.code == "ERR_DEDUPE"


def test_dedupe_allows_after_window(tmp_path) -> None:
    gate = btb.DedupeGate(tmp_path, window_s=300)
    ctx = {"sender_bot_id": "a", "recipient_bot_id": "b", "body": "hello"}
    gate.check(ctx)
    # Manually expire by writing state with old timestamp
    state_path = tmp_path / btb.DEDUPE_STATE_REL
    raw = json.loads(state_path.read_text())
    for k in raw:
        raw[k] = time.time() - 1000  # >> 300s window
    state_path.write_text(json.dumps(raw))
    second = gate.check(ctx)
    assert second is None


def test_dedupe_idempotency_key_bypasses(tmp_path) -> None:
    """Caller-supplied idempotency_key marks a legitimate retransmit; dedupe allows."""
    gate = btb.DedupeGate(tmp_path, window_s=300)
    ctx = {"sender_bot_id": "a", "recipient_bot_id": "b", "body": "hello"}
    gate.check(ctx)
    second = gate.check({**ctx, "idempotency_key": "retry-1"})
    assert second is None


def test_dedupe_distinguishes_normalized_whitespace(tmp_path) -> None:
    """Whitespace-only changes do NOT bypass dedupe (normalized comparison)."""
    gate = btb.DedupeGate(tmp_path, window_s=300)
    gate.check({"sender_bot_id": "a", "recipient_bot_id": "b", "body": "hello world"})
    second = gate.check({"sender_bot_id": "a", "recipient_bot_id": "b", "body": "hello   world"})
    assert second is not None
    assert second.code == "ERR_DEDUPE"


# ---------------------------------------------------------------------------
# RateLimitGate
# ---------------------------------------------------------------------------

def test_rate_limit_allows_under_cap() -> None:
    gate = btb.RateLimitGate(k=6, window_s=60)
    for i in range(6):
        ctx = {"sender_bot_id": "a", "chat_id": "chat1"}
        assert gate.check(ctx) is None, f"send #{i+1} should be allowed"


def test_rate_limit_rejects_seventh_in_one_minute() -> None:
    gate = btb.RateLimitGate(k=6, window_s=60)
    ctx = {"sender_bot_id": "a", "chat_id": "chat1"}
    for _ in range(6):
        gate.check(ctx)
    seventh = gate.check(ctx)
    assert seventh is not None
    assert seventh.code == "ERR_RATE_LIMIT"


def test_rate_limit_per_pair() -> None:
    """Limit is per (sender, chat) — different chats have independent buckets."""
    gate = btb.RateLimitGate(k=2, window_s=60)
    gate.check({"sender_bot_id": "a", "chat_id": "chat1"})
    gate.check({"sender_bot_id": "a", "chat_id": "chat1"})
    # chat1 is at cap; chat2 should still be allowed
    assert gate.check({"sender_bot_id": "a", "chat_id": "chat2"}) is None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def test_pipeline_short_circuits_on_first_rejection(tmp_path, monkeypatch) -> None:
    """If kill-switch rejects, dedupe/rate-limit shouldn't even run."""
    monkeypatch.delenv("BOT_TO_BOT_ENABLED", raising=False)  # kill-switch will reject
    gates = btb.make_default_pipeline(tmp_path)
    ctx = {"sender_bot_id": "a", "recipient_bot_id": "b", "body": "x", "chat_id": "c1", "thread_via_markers": []}
    rejection = btb.run_pipeline(gates, ctx, wiki_root=tmp_path)
    assert rejection is not None
    assert rejection.code == "ERR_KILL_SWITCH_ENV"


def test_pipeline_passes_when_all_gates_clear(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BOT_TO_BOT_ENABLED", "true")
    gates = btb.make_default_pipeline(tmp_path)
    ctx = {"sender_bot_id": "a", "recipient_bot_id": "b", "body": "x", "chat_id": "c1", "thread_via_markers": []}
    rejection = btb.run_pipeline(gates, ctx, wiki_root=tmp_path)
    assert rejection is None


def test_pipeline_writes_ledger_on_reject(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BOT_TO_BOT_ENABLED", raising=False)
    gates = btb.make_default_pipeline(tmp_path)
    ctx = {"sender_bot_id": "a", "recipient_bot_id": "b", "body": "x", "chat_id": "c1", "thread_via_markers": []}
    btb.run_pipeline(gates, ctx, wiki_root=tmp_path)
    ledger = tmp_path / btb.LEDGER_REL
    assert ledger.exists()
    line = ledger.read_text().strip()
    entry = json.loads(line)
    assert entry["rejection"]["gate"] == "KillSwitchGate"
    assert entry["body_head"] == "x"


def test_pipeline_does_not_write_ledger_on_pass(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BOT_TO_BOT_ENABLED", "true")
    gates = btb.make_default_pipeline(tmp_path)
    ctx = {"sender_bot_id": "a", "recipient_bot_id": "b", "body": "x", "chat_id": "c1", "thread_via_markers": []}
    btb.run_pipeline(gates, ctx, wiki_root=tmp_path)
    ledger = tmp_path / btb.LEDGER_REL
    # On pass, ledger may not exist OR may be empty
    if ledger.exists():
        assert ledger.read_text().strip() == ""
