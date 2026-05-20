"""Unit tests for tools/handshake.py.

Each test uses a fresh ``tmp_path`` as the wiki root via ``NOUS_WIKI``, so the
shadow JSONL, lane-lock state, history events, and TASK_QUEUE.md view are
isolated. We exercise the lock-then-claim ordering, refusal-on-overlap with
Telegram-nudge formatting, race-release semantics, and the CLI roundtrip.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

# Make tools/ importable when running pytest from anywhere.
THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Load tools/task_queue.py by file path (avoids stdlib `queue` collision).
_QUEUE_PATH = TOOLS_DIR / "task_queue.py"
_qspec = importlib.util.spec_from_file_location("tools_queue", _QUEUE_PATH)
assert _qspec is not None and _qspec.loader is not None
q = importlib.util.module_from_spec(_qspec)
sys.modules["tools_queue"] = q
_qspec.loader.exec_module(q)

import lane_lock  # noqa: E402

# Load handshake the same way handshake itself does — by file path under a
# fresh module name — so monkey-patches via sys.modules align with the module
# the handshake.py source resolved at import time.
import handshake  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_task(wiki: Path, *, lane: str, title: str, scope: list[str]) -> str:
    return q.add(title=title, lane=lane, scope_paths=scope, wiki=wiki)


# ---------------------------------------------------------------------------
# 1. No pending task → no_pending
# ---------------------------------------------------------------------------

def test_start_no_pending_task(tmp_path: Path):
    result = handshake.start(lane="claude", wiki=tmp_path)
    assert result["result"] == "no_pending"
    assert result["task_id"] is None
    assert result["lock_token"] is None
    assert result["scope_paths"] == []
    assert result["telegram_nudge"] is None
    assert "No pending task" in result["greeting"]
    assert "claude" in result["greeting"]


# ---------------------------------------------------------------------------
# 2. Pending task → claim + lock
# ---------------------------------------------------------------------------

def test_start_with_pending_task_claims_and_locks(tmp_path: Path):
    tid = _seed_task(tmp_path, lane="claude", title="do thing", scope=["tools/x.py"])

    result = handshake.start(lane="claude", wiki=tmp_path)

    assert result["result"] == "claimed"
    assert result["task_id"] == tid
    assert result["lock_token"] is not None
    assert result["lock_token"].startswith("lk-claude-")
    assert result["scope_paths"] == ["tools/x.py"]
    assert result["telegram_nudge"] is None

    # Task was actually claimed.
    rows = q.list_tasks(lane="claude", wiki=tmp_path)
    assert len(rows) == 1
    assert rows[0]["id"] == tid
    assert rows[0]["status"] == "claimed"

    # Lock is active.
    active = lane_lock.list_active(wiki=tmp_path)
    assert any(e["token"] == result["lock_token"] for e in active)


# ---------------------------------------------------------------------------
# 3. Refused when another lane holds an overlapping lock
# ---------------------------------------------------------------------------

def test_start_refuses_when_other_lane_holds_overlapping_lock(tmp_path: Path):
    # Pre-acquire a grok lock on tools/*
    grok_token = lane_lock.acquire(
        "grok",
        ["tools/*"],
        ttl_sec=600,
        session_id="grok-pre",
        wiki=tmp_path,
    )
    assert grok_token is not None

    # Add a claude task with scope tools/x.py (overlaps tools/*).
    tid = _seed_task(tmp_path, lane="claude", title="will refuse", scope=["tools/x.py"])

    result = handshake.start(lane="claude", wiki=tmp_path)

    assert result["result"] == "refused"
    assert result["task_id"] == tid
    assert result["lock_token"] is None
    assert result["telegram_nudge"] is not None
    assert result["telegram_nudge"].startswith("[handshake-refused]")
    assert "grok" in result["telegram_nudge"]
    assert grok_token in result["telegram_nudge"]

    # Task was NOT claimed (still pending).
    rows = q.list_tasks(lane="claude", wiki=tmp_path)
    assert rows[0]["status"] == "pending"

    # No new claude lock exists.
    active_claude = lane_lock.list_active(wiki=tmp_path, lane="claude")
    assert active_claude == []


# ---------------------------------------------------------------------------
# 4. If queue.claim loses the race, lock must be released
# ---------------------------------------------------------------------------

def test_start_releases_lock_if_queue_claim_loses_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    tid = _seed_task(tmp_path, lane="claude", title="race-task", scope=["tools/y.py"])

    # Force queue.claim to return False exactly once (simulating a race loss).
    calls = {"n": 0}
    real_claim = handshake._queue_mod.claim  # noqa: SLF001

    def fake_claim(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return False
        return real_claim(*args, **kwargs)

    monkeypatch.setattr(handshake._queue_mod, "claim", fake_claim)

    result = handshake.start(lane="claude", wiki=tmp_path)

    assert result["result"] == "refused"
    assert result["task_id"] == tid
    assert result["lock_token"] is None
    assert result["telegram_nudge"] is not None
    assert "Race" in result["greeting"] or "race" in result["greeting"]

    # Critically: no zombie lock for claude.
    active = lane_lock.list_active(wiki=tmp_path, lane="claude")
    assert active == [], f"zombie lock(s) found: {active}"


# ---------------------------------------------------------------------------
# 5. end() releases the lock
# ---------------------------------------------------------------------------

def test_end_releases_lock(tmp_path: Path):
    _seed_task(tmp_path, lane="claude", title="end-test", scope=["tools/z.py"])
    started = handshake.start(lane="claude", wiki=tmp_path)
    token = started["lock_token"]
    assert token is not None

    ended = handshake.end(
        lock_token=token,
        task_id=started["task_id"],
        wiki=tmp_path,
    )
    assert ended["released_lock"] is True
    assert ended["task_id"] == started["task_id"]

    active = lane_lock.list_active(wiki=tmp_path)
    assert not any(e["token"] == token for e in active)


# ---------------------------------------------------------------------------
# 6. end() with no lock token is a no-op
# ---------------------------------------------------------------------------

def test_end_with_none_lock_no_error(tmp_path: Path):
    out = handshake.end(lock_token=None, task_id=None, wiki=tmp_path)
    assert out == {"released_lock": False, "task_id": None}


# ---------------------------------------------------------------------------
# 7. active_lanes summary includes existing tokens
# ---------------------------------------------------------------------------

def test_active_lanes_includes_existing_tokens(tmp_path: Path):
    codex_tok = lane_lock.acquire(
        "codex", ["agents/c.py"], ttl_sec=600, session_id="codex-pre", wiki=tmp_path,
    )
    grok_tok = lane_lock.acquire(
        "grok", ["pages/x.md"], ttl_sec=600, session_id="grok-pre", wiki=tmp_path,
    )
    assert codex_tok and grok_tok

    result = handshake.start(lane="claude", wiki=tmp_path)
    lanes = {e["lane"]: e for e in result["active_lanes"]}
    assert "codex" in lanes
    assert "grok" in lanes
    assert lanes["codex"]["tokens"] >= 1
    assert lanes["grok"]["tokens"] >= 1
    assert "agents/c.py" in lanes["codex"]["scope_summary"]
    assert "pages/x.md" in lanes["grok"]["scope_summary"]


# ---------------------------------------------------------------------------
# 8. STATUS.md best-effort: never blocks the handshake
# ---------------------------------------------------------------------------

def test_status_md_is_re_rendered_after_handshake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    # status_render is NOT committed yet in the parallel-subagent timeline, so
    # the handshake must NOT raise when it cannot be imported. Force both
    # import paths to fail via meta_path injection.
    class _BlockStatusRender:
        def find_spec(self, fullname, path=None, target=None):
            if fullname in ("status_render", "tools.status_render"):
                raise ImportError("blocked by test")
            return None

    finder = _BlockStatusRender()
    monkeypatch.setattr(sys, "meta_path", [finder] + sys.meta_path)
    # Also evict any already-imported copies.
    for name in ("status_render", "tools.status_render"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    # Should still succeed end-to-end without exception.
    result = handshake.start(lane="claude", wiki=tmp_path)
    assert result["result"] == "no_pending"


# ---------------------------------------------------------------------------
# 9. greeting contains lane and session
# ---------------------------------------------------------------------------

def test_greeting_contains_lane_and_session(tmp_path: Path):
    _seed_task(tmp_path, lane="claude", title="greet", scope=["tools/g.py"])
    result = handshake.start(lane="claude", session="sess-xyz-123", wiki=tmp_path)
    assert result["result"] == "claimed"
    assert "claude" in result["greeting"]
    assert "sess-xyz-123" in result["greeting"]


# ---------------------------------------------------------------------------
# 10. CLI: `start --json` emits parseable JSON with expected keys
# ---------------------------------------------------------------------------

def test_main_cli_start_json_output(tmp_path: Path):
    env = os.environ.copy()
    env["NOUS_WIKI"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "handshake.py"),
         "start", "--lane", "claude", "--json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert proc.returncode == 0, (
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    for key in (
        "lane", "session", "result", "task_id", "lock_token",
        "scope_paths", "greeting", "telegram_nudge", "active_lanes",
    ):
        assert key in payload, f"missing key {key} in {payload}"
    assert payload["lane"] == "claude"
    assert payload["result"] == "no_pending"


# ---------------------------------------------------------------------------
# 11. session_id() default format
# ---------------------------------------------------------------------------

def test_session_id_default_format():
    sid = handshake.session_id()
    # <hostname>-<pid>-<10-digit-unix>
    pat = re.compile(r"^.+-\d+-\d{10}$")
    assert pat.match(sid), f"unexpected format: {sid!r}"
    # Hostname prefix should match this host.
    assert sid.startswith(socket.gethostname() + "-")
