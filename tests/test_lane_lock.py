"""Unit tests for tools/lane_lock.py.

Each test uses a fresh ``tmp_path`` as the wiki root so state and history files
are isolated. Atomic-write and conflict semantics are covered alongside the
scope-glob rules and the CLI roundtrip.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

# Make tools/ importable when running pytest from anywhere.
THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import lane_lock  # noqa: E402  (sys.path tweak above)


# ---------------------------------------------------------------------------
# scope_matches
# ---------------------------------------------------------------------------

def test_scope_matches_single_segment_glob():
    assert lane_lock.scope_matches("tools/x.py", ["tools/*"]) is True
    assert lane_lock.scope_matches("tools/sub/x.py", ["tools/*"]) is False


def test_scope_matches_recursive_glob():
    assert lane_lock.scope_matches("tools/sub/x.py", ["tools/**"]) is True
    assert lane_lock.scope_matches("tools/x.py", ["tools/**"]) is True
    assert lane_lock.scope_matches("tools/sub/deep/file.py", ["tools/**"]) is True
    assert lane_lock.scope_matches("other/x.py", ["tools/**"]) is False


def test_scope_matches_dir_prefix():
    assert lane_lock.scope_matches(
        "tenants/satory/anything/deep/path",
        ["tenants/satory/*"],
    ) is True
    # bare exact dir name also matches its children
    assert lane_lock.scope_matches(
        "tenants/satory/anything/deep",
        ["tenants/satory"],
    ) is True


def test_scope_matches_exact():
    assert lane_lock.scope_matches("tools/queue.py", ["tools/queue.py"]) is True
    assert lane_lock.scope_matches("tools/queue2.py", ["tools/queue.py"]) is False


# ---------------------------------------------------------------------------
# acquire
# ---------------------------------------------------------------------------

def test_acquire_basic(tmp_path: Path):
    tok = lane_lock.acquire("claude", ["tools/x.py"], wiki=tmp_path)
    assert tok is not None
    assert tok.startswith("lk-claude-")

    state = json.loads((tmp_path / lane_lock.LOCKS_REL).read_text())
    assert "tokens" in state
    assert len(state["tokens"]) == 1
    assert tok in state["tokens"]
    entry = state["tokens"][tok]
    assert entry["lane"] == "claude"
    assert entry["scope_paths"] == ["tools/x.py"]
    assert "acquired_at" in entry and "expires_at" in entry

    history_lines = (tmp_path / lane_lock.HISTORY_REL).read_text().strip().splitlines()
    events = [json.loads(line) for line in history_lines]
    acquired = [e for e in events if e.get("event") == "acquired"]
    assert len(acquired) == 1
    assert acquired[0]["token"] == tok


def test_acquire_conflict_same_lane_ok(tmp_path: Path):
    tok_a = lane_lock.acquire("claude", ["tools/a.py"], wiki=tmp_path)
    tok_b = lane_lock.acquire("claude", ["tools/b.py"], wiki=tmp_path)
    assert tok_a is not None
    assert tok_b is not None
    assert tok_a != tok_b
    active = lane_lock.list_active(wiki=tmp_path)
    assert len(active) == 2


def test_acquire_conflict_different_lane_overlap_refused(tmp_path: Path):
    tok = lane_lock.acquire("claude", ["tools/*"], wiki=tmp_path)
    assert tok is not None
    refused = lane_lock.acquire("codex", ["tools/queue.py"], wiki=tmp_path)
    assert refused is None

    history_lines = (tmp_path / lane_lock.HISTORY_REL).read_text().strip().splitlines()
    events = [json.loads(line) for line in history_lines]
    conflicts = [e for e in events if e.get("event") == "conflict"]
    assert len(conflicts) == 1
    assert conflicts[0]["requesting_lane"] == "codex"
    assert conflicts[0]["existing_token"] == tok


# ---------------------------------------------------------------------------
# heartbeat
# ---------------------------------------------------------------------------

def test_heartbeat_extends_expiry(tmp_path: Path):
    t0 = dt.datetime(2026, 5, 20, 11, 0, 0, tzinfo=lane_lock.ALMATY)
    tok = lane_lock.acquire(
        "claude", ["tools/x.py"], ttl_sec=300, wiki=tmp_path, now=t0,
    )
    assert tok is not None
    state_before = json.loads((tmp_path / lane_lock.LOCKS_REL).read_text())
    exp_before = state_before["tokens"][tok]["expires_at"]

    t1 = t0 + dt.timedelta(seconds=60)
    ok = lane_lock.heartbeat(tok, extend_sec=300, wiki=tmp_path, now=t1)
    assert ok is True
    state_after = json.loads((tmp_path / lane_lock.LOCKS_REL).read_text())
    exp_after = state_after["tokens"][tok]["expires_at"]
    assert dt.datetime.fromisoformat(exp_after) > dt.datetime.fromisoformat(exp_before)


def test_heartbeat_returns_false_for_unknown_token(tmp_path: Path):
    assert lane_lock.heartbeat("lk-claude-deadbeef-0", wiki=tmp_path) is False


# ---------------------------------------------------------------------------
# release
# ---------------------------------------------------------------------------

def test_release_idempotent(tmp_path: Path):
    tok = lane_lock.acquire("claude", ["tools/x.py"], wiki=tmp_path)
    assert tok is not None
    assert lane_lock.release(tok, wiki=tmp_path) is True
    assert lane_lock.release(tok, wiki=tmp_path) is False


# ---------------------------------------------------------------------------
# list_active
# ---------------------------------------------------------------------------

def test_list_active_filters_by_lane(tmp_path: Path):
    tok_claude = lane_lock.acquire("claude", ["tools/a.py"], wiki=tmp_path)
    tok_codex = lane_lock.acquire("codex", ["other/b.py"], wiki=tmp_path)
    assert tok_claude is not None
    assert tok_codex is not None

    claude_only = lane_lock.list_active(wiki=tmp_path, lane="claude")
    assert len(claude_only) == 1
    assert claude_only[0]["token"] == tok_claude
    assert claude_only[0]["lane"] == "claude"

    all_active = lane_lock.list_active(wiki=tmp_path)
    assert len(all_active) == 2


# ---------------------------------------------------------------------------
# reap_stale
# ---------------------------------------------------------------------------

def test_reap_stale_releases_expired_tokens(tmp_path: Path):
    t0 = dt.datetime(2026, 5, 20, 11, 0, 0, tzinfo=lane_lock.ALMATY)
    tok = lane_lock.acquire(
        "claude", ["tools/x.py"], ttl_sec=1, wiki=tmp_path, now=t0,
    )
    assert tok is not None
    t1 = t0 + dt.timedelta(seconds=10)
    released = lane_lock.reap_stale(wiki=tmp_path, now=t1)
    assert tok in released
    state = json.loads((tmp_path / lane_lock.LOCKS_REL).read_text())
    assert tok not in state["tokens"]


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

def test_atomic_write_no_torn_state_on_concurrent_writers(tmp_path: Path):
    """Spawn 4 threads each acquiring a distinct, non-overlapping lock.

    After all complete, the state file must parse cleanly and contain all
    4 tokens. fcntl serialization should prevent torn writes.
    """
    results: dict[int, str | None] = {}
    barrier = threading.Barrier(4)

    def worker(idx: int) -> None:
        barrier.wait()
        # Each lane is the same ("claude") so we don't trip cross-lane conflict
        # rules, but the scopes are disjoint so no scope conflicts either.
        results[idx] = lane_lock.acquire(
            "claude", [f"tools/worker_{idx}.py"], wiki=tmp_path,
        )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(tok is not None for tok in results.values()), results
    # Final state must be a valid JSON document with all 4 tokens.
    state = json.loads((tmp_path / lane_lock.LOCKS_REL).read_text())
    assert len(state["tokens"]) == 4
    for tok in results.values():
        assert tok in state["tokens"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_main_cli_acquire_release_round_trip(tmp_path: Path):
    env = os.environ.copy()
    env["NOUS_WIKI"] = str(tmp_path)
    cli = [sys.executable, str(TOOLS_DIR / "lane_lock.py")]

    acq = subprocess.run(
        cli + ["acquire", "--lane", "claude", "--scope", "tools/x.py"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert acq.returncode == 0, acq.stderr
    token = acq.stdout.strip()
    assert token.startswith("lk-claude-")

    rel = subprocess.run(
        cli + ["release", "--token", token],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rel.returncode == 0, rel.stderr

    # Second release should return non-zero.
    rel2 = subprocess.run(
        cli + ["release", "--token", token],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rel2.returncode == 1
