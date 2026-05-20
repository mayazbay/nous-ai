"""Unit tests for tools/queue_to_openbrain.py.

Each test uses a fresh ``tmp_path`` as wiki root (NOUS_WIKI for the CLI test
case). subprocess.Popen is monkeypatched so the fire-and-forget OpenBrain
capture never actually shells out.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Make tools/ importable.
THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Load both modules via importlib (stdlib ``queue`` shadows the queue filename).
_QUEUE_PATH = TOOLS_DIR / "task_queue.py"
_qspec = importlib.util.spec_from_file_location("tools_queue", _QUEUE_PATH)
assert _qspec is not None and _qspec.loader is not None
q = importlib.util.module_from_spec(_qspec)
sys.modules["tools_queue"] = q
_qspec.loader.exec_module(q)

_QOB_PATH = TOOLS_DIR / "queue_to_openbrain.py"
_qobspec = importlib.util.spec_from_file_location("tools_queue_to_openbrain", _QOB_PATH)
assert _qobspec is not None and _qobspec.loader is not None
qob = importlib.util.module_from_spec(_qobspec)
sys.modules["tools_queue_to_openbrain"] = qob
_qobspec.loader.exec_module(qob)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KZT = dt.timezone(dt.timedelta(hours=5))


def _ts(year=2026, month=5, day=20, hour=11, minute=0, second=0) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, second, tzinfo=KZT)


class _FakeProc:
    def __init__(self) -> None:
        self.pid = 9999


def _install_popen_recorder(monkeypatch, captured: dict) -> None:
    """Replace subprocess.Popen in qob's namespace with a recorder."""

    def _fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        # Drain a stdout target if provided so the fd stays usable.
        return _FakeProc()

    monkeypatch.setattr(qob.subprocess, "Popen", _fake_popen)


def _install_popen_raiser(monkeypatch, exc: BaseException) -> None:
    def _raise(args, **kwargs):  # noqa: ARG001
        raise exc

    monkeypatch.setattr(qob.subprocess, "Popen", _raise)


def _make_done_task(
    wiki: Path,
    *,
    title: str = "test task",
    lane: str = "claude",
    scope: list[str] | None = None,
    created: dt.datetime | None = None,
    claimed: dt.datetime | None = None,
    done: dt.datetime | None = None,
) -> str:
    """Create+claim+done a task in the queue. Returns task id."""
    created = created or _ts(hour=10)
    claimed = claimed or _ts(hour=10, minute=5)
    done = done or _ts(hour=11)
    tid = q.add(
        title=title,
        lane=lane,
        scope_paths=scope or ["tools/x.py"],
        wiki=wiki,
        now=created,
    )
    q.claim(id=tid, session_id="s-test", wiki=wiki, now=claimed)
    q.done(id=tid, wiki=wiki, now=done)
    return tid


# ---------------------------------------------------------------------------
# 1. emit_done — task not found
# ---------------------------------------------------------------------------

def test_emit_done_task_not_found(tmp_path: Path, monkeypatch):
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)
    res = qob.emit_done("t-fake-001", wiki=tmp_path)
    assert res["task_id"] == "t-fake-001"
    assert res["emitted"] is False
    assert res["reason"] == "task_not_found"
    assert "args" not in captured  # no shell-out happened


# ---------------------------------------------------------------------------
# 2. emit_done — task not done (claimed only)
# ---------------------------------------------------------------------------

def test_emit_done_task_not_done(tmp_path: Path, monkeypatch):
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)
    tid = q.add(
        title="claimed-only",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    q.claim(id=tid, session_id="s-test", wiki=tmp_path, now=_ts(minute=5))
    res = qob.emit_done(tid, wiki=tmp_path)
    assert res["emitted"] is False
    assert res["reason"] == "task_not_done"
    assert "args" not in captured


# ---------------------------------------------------------------------------
# 3. emit_done — happy path writes to log and shells out
# ---------------------------------------------------------------------------

def test_emit_done_happy_path_logs_to_log_file(tmp_path: Path, monkeypatch):
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)

    tid = _make_done_task(tmp_path, title="ship the thing")

    res = qob.emit_done(tid, wiki=tmp_path)
    assert res["emitted"] is True
    assert res["reason"] == "ok"

    log_path = tmp_path / qob.LOG_REL
    assert log_path.exists(), "openbrain-queue.log not written"
    log_text = log_path.read_text(encoding="utf-8")
    assert "queue:" in log_text
    assert "ship the thing" in log_text  # title appears in log line

    assert "args" in captured, "subprocess.Popen was not invoked"
    assert captured["args"][:2] == ["mcp", "call"]
    # The JSON payload is the last arg.
    payload = json.loads(captured["args"][-1])
    assert payload["type"] == "task_completed"
    assert payload["title"].startswith("Task done: ")
    assert any(t.startswith("task:") for t in payload["tags"])


# ---------------------------------------------------------------------------
# 4. emit_done — idempotent via cursor
# ---------------------------------------------------------------------------

def test_emit_done_idempotent_via_cursor(tmp_path: Path, monkeypatch):
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)
    tid = _make_done_task(tmp_path, title="idempotent")

    first = qob.emit_done(tid, wiki=tmp_path)
    assert first["emitted"] is True
    assert first["reason"] == "ok"

    # Reset capture so we can detect whether second call shelled out.
    captured.clear()
    _install_popen_recorder(monkeypatch, captured)

    second = qob.emit_done(tid, wiki=tmp_path)
    assert second["emitted"] is False
    assert second["reason"] == "already_emitted"
    assert "args" not in captured  # no second shell-out

    # Cursor has exactly one row for the task.
    cursor_path = tmp_path / qob.CURSOR_REL
    lines = [
        ln for ln in cursor_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["task_id"] == tid
    assert isinstance(row["event_seq"], int)


# ---------------------------------------------------------------------------
# 5. _capture_openbrain uses start_new_session=True
# ---------------------------------------------------------------------------

def test_capture_openbrain_uses_start_new_session(tmp_path: Path, monkeypatch):
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)

    qob._capture_openbrain(
        {"type": "x", "title": "T", "body": "B", "tags": []}, tmp_path
    )

    assert captured.get("kwargs", {}).get("start_new_session") is True


# ---------------------------------------------------------------------------
# 6. render_task_body shape
# ---------------------------------------------------------------------------

def test_render_task_body_shape():
    fake = {
        "id": "t-2026-05-20-007",
        "lane": "opus",
        "status": "done",
        "owner": "s108-mac-7421",
        "created": "2026-05-20T10:00:00+05:00",
        "claimed": "2026-05-20T10:05:00+05:00",
        "done": "2026-05-20T11:30:00+05:00",
        "scope_paths": ["tools/a.py", "tools/b.py"],
        "blocked_by": [],
        "parent": None,
        "title": "my title",
    }
    body = qob.render_task_body(fake)
    assert "# my title" in body
    assert "- id: t-2026-05-20-007" in body
    assert "- lane: opus" in body
    assert "- scope: tools/a.py,tools/b.py" in body
    assert "- duration:" in body


# ---------------------------------------------------------------------------
# 7. weekly_digest groups by lane
# ---------------------------------------------------------------------------

def test_weekly_digest_groups_by_lane(tmp_path: Path, monkeypatch):
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)
    now = _ts(day=20, hour=12)

    # Three done tasks across three lanes, within the last 7 days.
    for lane in ("claude", "codex", "grok"):
        _make_done_task(
            tmp_path,
            title=f"{lane}-task",
            lane=lane,
            created=_ts(day=18, hour=10),
            claimed=_ts(day=18, hour=11),
            done=_ts(day=19, hour=12),
        )

    res = qob.weekly_digest(wiki=tmp_path, now=now)
    assert res["emitted"] is True
    assert res["task_count"] == 3
    assert res["lanes"] == {"claude": 1, "codex": 1, "grok": 1}
    assert res["title"].startswith("Weekly queue retro ")

    # Confirm the shell-out fired once.
    assert "args" in captured
    payload = json.loads(captured["args"][-1])
    assert payload["type"] == "weekly_retro"


# ---------------------------------------------------------------------------
# 8. weekly_digest excludes older than 7 days
# ---------------------------------------------------------------------------

def test_weekly_digest_excludes_older_than_7_days(tmp_path: Path, monkeypatch):
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)
    now = _ts(day=20, hour=12)

    # One in-window done task.
    _make_done_task(
        tmp_path,
        title="recent",
        lane="claude",
        created=_ts(day=18, hour=10),
        claimed=_ts(day=18, hour=11),
        done=_ts(day=19, hour=12),
    )
    # One out-of-window done task (10 days old).
    _make_done_task(
        tmp_path,
        title="ancient",
        lane="codex",
        created=_ts(day=8, hour=10),
        claimed=_ts(day=8, hour=11),
        done=_ts(day=10, hour=12),
    )

    res = qob.weekly_digest(wiki=tmp_path, now=now)
    assert res["task_count"] == 1
    assert res["lanes"] == {"claude": 1}


# ---------------------------------------------------------------------------
# 9. CLI roundtrip — emit-done with --json on missing task
# ---------------------------------------------------------------------------

def test_main_cli_emit_done_json(tmp_path: Path):
    env = os.environ.copy()
    env["NOUS_WIKI"] = str(tmp_path)
    # Strip PYTHONPATH so the child process doesn't accidentally import the
    # repo's other paths in unexpected order.
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "queue_to_openbrain.py"),
        "emit-done",
        "--id",
        "t-fake-cli-001",
        "--json",
    ]
    proc = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # task not found → exit 1, JSON on stdout.
    assert proc.returncode == 1, f"stderr={proc.stderr!r} stdout={proc.stdout!r}"
    data = json.loads(proc.stdout.strip())
    assert data["task_id"] == "t-fake-cli-001"
    assert data["emitted"] is False
    assert data["reason"] == "task_not_found"


# ---------------------------------------------------------------------------
# 10. Popen raises → cursor untouched → second call retries
# ---------------------------------------------------------------------------

def test_emit_done_popen_failure_no_cursor_update(tmp_path: Path, monkeypatch):
    tid = _make_done_task(tmp_path, title="retry me")

    # First call: Popen raises.
    _install_popen_raiser(monkeypatch, OSError("simulated spawn failure"))
    first = qob.emit_done(tid, wiki=tmp_path)
    assert first["emitted"] is False
    assert first["reason"] == "capture_failed"

    # Cursor must be empty (no row appended).
    cursor_path = tmp_path / qob.CURSOR_REL
    if cursor_path.exists():
        lines = [
            ln
            for ln in cursor_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        assert lines == [], f"cursor should be empty, got {lines!r}"

    # Second call: Popen works → reason='ok', cursor now has one row.
    captured: dict = {}
    _install_popen_recorder(monkeypatch, captured)
    second = qob.emit_done(tid, wiki=tmp_path)
    assert second["emitted"] is True
    assert second["reason"] == "ok"
    assert "args" in captured

    lines = [
        ln for ln in cursor_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["task_id"] == tid
