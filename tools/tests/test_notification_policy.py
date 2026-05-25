"""Tests for notification_policy.py — all mocked, no filesystem side effects by default.

Coverage:
  test_suppress_class_returns_false
  test_immediate_class_returns_true
  test_digest_class_returns_false_but_appends_queue
  test_flush_digest_builds_compact_text
  test_flush_digest_returns_none_on_empty_queue
  test_dedup_blocks_repeat_within_ttl
  test_dedup_allows_after_ttl
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

# Ensure tools/ is on path
TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import notification_policy as np_mod
from notification_policy import (
    DEDUP_TTL_SECONDS,
    DIGEST,
    IMMEDIATE,
    SUPPRESS,
    EVENT_CLASS_REGISTRY,
    flush_daily_digest,
    should_ping,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_memory_cache() -> None:
    """Reset in-memory dedup cache between tests."""
    np_mod._DEDUP_CACHE.clear()


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


def test_registry_contains_all_three_categories() -> None:
    categories = set(EVENT_CLASS_REGISTRY.values())
    assert SUPPRESS in categories
    assert DIGEST in categories
    assert IMMEDIATE in categories


def test_suppress_events_present() -> None:
    assert EVENT_CLASS_REGISTRY["auto-checkpoint"] == SUPPRESS
    assert EVENT_CLASS_REGISTRY["goal-cycle"] == SUPPRESS
    assert EVENT_CLASS_REGISTRY["control-plane-sync"] == SUPPRESS
    assert EVENT_CLASS_REGISTRY["heartbeat-green"] == SUPPRESS


def test_immediate_events_present() -> None:
    assert EVENT_CLASS_REGISTRY["supervisor-escalation"] == IMMEDIATE
    assert EVENT_CLASS_REGISTRY["credential-needed"] == IMMEDIATE
    assert EVENT_CLASS_REGISTRY["budget-cap-reached"] == IMMEDIATE


# ---------------------------------------------------------------------------
# T1: SUPPRESS returns False
# ---------------------------------------------------------------------------


def test_suppress_class_returns_false(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    result = should_ping("auto-checkpoint", "info", digest_queue=queue, dedup_state=dedup)

    assert result is False
    assert not queue.exists(), "SUPPRESS must not write to digest queue"


def test_suppress_never_writes_digest(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    for event in ["queue-timestamp", "wiki-sync", "openbrain-projection", "heartbeat-green"]:
        should_ping(event, "info", digest_queue=queue, dedup_state=dedup)

    assert not queue.exists(), "No SUPPRESS events should touch the digest queue"


# ---------------------------------------------------------------------------
# T2: IMMEDIATE returns True
# ---------------------------------------------------------------------------


def test_immediate_class_returns_true(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    result = should_ping("supervisor-escalation", "critical", digest_queue=queue, dedup_state=dedup)

    assert result is True


def test_immediate_unknown_event_returns_true(tmp_path: Path) -> None:
    """Unknown event_class defaults to IMMEDIATE (fail-open)."""
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    result = should_ping("brand-new-unknown-event", "critical", digest_queue=queue, dedup_state=dedup)

    assert result is True


# ---------------------------------------------------------------------------
# T3: DIGEST returns False but appends to queue
# ---------------------------------------------------------------------------


def test_digest_class_returns_false_but_appends_queue(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "pages" / "systems" / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    result = should_ping("yellow-autorepaired", "warn", digest_queue=queue, dedup_state=dedup)

    assert result is False
    assert queue.exists(), "DIGEST must write to queue"
    lines = [l for l in queue.read_text().strip().splitlines() if l.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_class"] == "yellow-autorepaired"
    assert record["severity"] == "warn"
    assert "ts" in record


def test_digest_multiple_events_all_appended(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    for _ in range(3):
        should_ping("red-green-flip", "info", digest_queue=queue, dedup_state=dedup)
    should_ping("cost-daily-summary", "info", digest_queue=queue, dedup_state=dedup)

    lines = [l for l in queue.read_text().strip().splitlines() if l.strip()]
    assert len(lines) == 4


# ---------------------------------------------------------------------------
# T4: flush_daily_digest builds compact text
# ---------------------------------------------------------------------------


def test_flush_digest_builds_compact_text(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    # Accumulate some events
    should_ping("yellow-autorepaired", "warn", digest_queue=queue, dedup_state=dedup)
    should_ping("yellow-autorepaired", "warn", digest_queue=queue, dedup_state=dedup)
    should_ping("red-green-flip", "info", digest_queue=queue, dedup_state=dedup)
    should_ping("cost-daily-summary", "info", digest_queue=queue, dedup_state=dedup)

    text = flush_daily_digest(digest_queue=queue)

    assert text is not None
    assert "Daily digest:" in text
    assert "yellow-autorepaired" in text
    assert "2x" in text or "2" in text  # 2 yellow-autorepaired events
    assert "red-green-flip" in text
    assert "cost-daily-summary" in text


def test_flush_digest_clears_queue(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"

    should_ping("yellow-autorepaired", "warn", digest_queue=queue, dedup_state=dedup)
    assert queue.stat().st_size > 0

    flush_daily_digest(digest_queue=queue)

    # Queue cleared — second flush returns None
    result2 = flush_daily_digest(digest_queue=queue)
    assert result2 is None


# ---------------------------------------------------------------------------
# T5: flush_daily_digest returns None on empty queue
# ---------------------------------------------------------------------------


def test_flush_digest_returns_none_on_empty_queue(tmp_path: Path) -> None:
    queue = tmp_path / "empty.jsonl"
    # File does not exist
    result = flush_daily_digest(digest_queue=queue)
    assert result is None


def test_flush_digest_returns_none_on_empty_file(tmp_path: Path) -> None:
    queue = tmp_path / "empty.jsonl"
    queue.write_text("", encoding="utf-8")
    result = flush_daily_digest(digest_queue=queue)
    assert result is None


# ---------------------------------------------------------------------------
# T6: dedup blocks repeat within TTL
# ---------------------------------------------------------------------------


def test_dedup_blocks_repeat_within_ttl(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"
    now = time.time()

    first = should_ping(
        "supervisor-escalation", "critical",
        dedup_key="fp-abc123",
        digest_queue=queue, dedup_state=dedup,
        _now=now,
    )
    second = should_ping(
        "supervisor-escalation", "critical",
        dedup_key="fp-abc123",
        digest_queue=queue, dedup_state=dedup,
        _now=now + 60,  # 1 minute later — within 4h TTL
    )

    assert first is True
    assert second is False, "Same dedup_key within TTL must be blocked"


def test_dedup_blocks_via_disk_state(tmp_path: Path) -> None:
    """Dedup persists across in-memory cache clears (simulates new process)."""
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"
    now = time.time()

    should_ping(
        "supervisor-escalation", "critical",
        dedup_key="fp-disk-test",
        digest_queue=queue, dedup_state=dedup,
        _now=now,
    )

    # Simulate new process — clear in-memory cache
    _clear_memory_cache()

    second = should_ping(
        "supervisor-escalation", "critical",
        dedup_key="fp-disk-test",
        digest_queue=queue, dedup_state=dedup,
        _now=now + 60,
    )

    assert second is False, "Dedup must persist on disk across cache clears"


# ---------------------------------------------------------------------------
# T7: dedup allows after TTL
# ---------------------------------------------------------------------------


def test_dedup_allows_after_ttl(tmp_path: Path) -> None:
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"
    now = time.time()

    first = should_ping(
        "supervisor-escalation", "critical",
        dedup_key="fp-expire",
        digest_queue=queue, dedup_state=dedup,
        _now=now,
    )
    # Clear in-memory cache to force disk read
    _clear_memory_cache()

    after_ttl = should_ping(
        "supervisor-escalation", "critical",
        dedup_key="fp-expire",
        digest_queue=queue, dedup_state=dedup,
        _now=now + DEDUP_TTL_SECONDS + 1,  # 1 second past TTL
    )

    assert first is True
    assert after_ttl is True, "After TTL expiry the event must fire again"


def test_no_dedup_key_always_fires(tmp_path: Path) -> None:
    """IMMEDIATE without dedup_key always returns True (no dedup applied)."""
    _clear_memory_cache()
    queue = tmp_path / "digest.jsonl"
    dedup = tmp_path / "dedup.json"
    now = time.time()

    results = [
        should_ping("credential-needed", "critical", digest_queue=queue, dedup_state=dedup, _now=now + i)
        for i in range(3)
    ]
    assert all(results), "No dedup_key → every call returns True"
