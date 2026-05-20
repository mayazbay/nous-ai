"""Unit tests for tools/heartbeat_lane.py.

Each test uses a fresh ``tmp_path`` as the wiki root. Loop tests use the
``iterations`` parameter + ``interval_sec=0`` so they never sleep.
"""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Make tools/ importable when running pytest from anywhere.
THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import heartbeat_lane  # noqa: E402
import lane_lock  # noqa: E402


KZT = dt.timezone(dt.timedelta(hours=5))


def _wiki(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "pages" / "systems").mkdir(parents=True)
    (root / "logs").mkdir()
    return root


# ---------------------------------------------------------------------------
# is_alive
# ---------------------------------------------------------------------------

def test_is_alive_for_current_pid():
    assert heartbeat_lane.is_alive(os.getpid()) is True


def test_is_alive_for_dead_pid():
    # 999999 is well above the typical max pid on macOS (~99999); extremely
    # unlikely to be in use. ``kill(pid, 0)`` returns ProcessLookupError.
    # If by some chance it is in use, this test would be a false positive —
    # but on a developer Mac that's essentially never the case.
    assert heartbeat_lane.is_alive(999999) is False


# ---------------------------------------------------------------------------
# heartbeat_loop
# ---------------------------------------------------------------------------

def test_heartbeat_loop_exits_when_parent_dies(tmp_path: Path):
    wiki = _wiki(tmp_path)
    # Spawn a short-lived child process; capture its pid; wait for it to die.
    proc = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.exit(0)"],
    )
    dead_pid = proc.pid
    proc.wait(timeout=5)
    assert heartbeat_lane.is_alive(dead_pid) is False

    cycles = heartbeat_lane.heartbeat_loop(
        session_id="test-sess",
        parent_pid=dead_pid,
        interval_sec=0,
        wiki=wiki,
        iterations=5,
    )
    # Parent already dead at first check → loop exits at cycle 0.
    assert cycles == 0


def test_heartbeat_loop_extends_owned_tokens(tmp_path: Path):
    wiki = _wiki(tmp_path)
    # Acquire at wall-clock-now (so list_active inside the heartbeat loop,
    # which uses wall-clock, doesn't reap us as stale).
    token = lane_lock.acquire(
        "opus",
        ["tools/x.py"],
        session_id="test-sess",
        wiki=wiki,
        ttl_sec=300,
    )
    assert token is not None

    # Snapshot expires_at before the heartbeat.
    active_before = lane_lock.list_active(wiki=wiki)
    assert len(active_before) == 1
    before_expires = active_before[0]["expires_at"]
    acquired_dt = dt.datetime.fromisoformat(active_before[0]["acquired_at"])

    # Tiny sleep so heartbeat's wall-clock-now is strictly after acquired_at,
    # producing a new (and different) expires_at value.
    time.sleep(0.05)

    # Run exactly one cycle. parent_pid = our own pid (we're alive).
    cycles = heartbeat_lane.heartbeat_loop(
        session_id="test-sess",
        parent_pid=os.getpid(),
        interval_sec=0,
        wiki=wiki,
        iterations=1,
    )
    assert cycles == 1

    active_after = lane_lock.list_active(wiki=wiki)
    assert len(active_after) == 1
    after_expires = active_after[0]["expires_at"]
    # Heartbeat extends expires_at from wall-clock now → must differ.
    assert after_expires != before_expires
    after_dt = dt.datetime.fromisoformat(after_expires)
    assert after_dt > acquired_dt


def test_heartbeat_loop_skips_other_session_tokens(tmp_path: Path):
    wiki = _wiki(tmp_path)
    # Acquire at wall-clock-now so list_active doesn't reap.
    token_a = lane_lock.acquire(
        "opus",
        ["tools/a.py"],
        session_id="sess-A",
        wiki=wiki,
        ttl_sec=300,
    )
    token_b = lane_lock.acquire(
        "codex",
        ["tools/b.py"],
        session_id="sess-B",
        wiki=wiki,
        ttl_sec=300,
    )
    assert token_a is not None
    assert token_b is not None

    before = {t["token"]: t["expires_at"] for t in lane_lock.list_active(wiki=wiki)}
    assert token_a in before and token_b in before

    # Tiny sleep so heartbeat's wall-clock-now is strictly after acquired_at.
    time.sleep(0.05)

    cycles = heartbeat_lane.heartbeat_loop(
        session_id="sess-A",
        parent_pid=os.getpid(),
        interval_sec=0,
        wiki=wiki,
        iterations=1,
    )
    assert cycles == 1

    after = {t["token"]: t["expires_at"] for t in lane_lock.list_active(wiki=wiki)}
    # A's expires_at should have changed (heartbeated).
    assert after[token_a] != before[token_a]
    # B's expires_at must NOT have changed.
    assert after[token_b] == before[token_b]


def test_heartbeat_loop_iterations_parameter(tmp_path: Path):
    wiki = _wiki(tmp_path)
    cycles = heartbeat_lane.heartbeat_loop(
        session_id="no-such-session",
        parent_pid=os.getpid(),
        interval_sec=0,
        wiki=wiki,
        iterations=3,
    )
    assert cycles == 3
