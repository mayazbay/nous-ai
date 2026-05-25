"""Unit tests for tools/task_queue.py.

Each test uses a fresh ``tmp_path`` as the wiki root so the shadow JSONL,
TASK_QUEUE.md view, and fcntl state lock are isolated. Concurrent claim,
monotonic event_seq, and the CLI roundtrip are all exercised.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
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

# Load tools/task_queue.py by file path to avoid colliding with stdlib `queue`
# module (which pytest itself imports, locking it into sys.modules first).
_QUEUE_PATH = TOOLS_DIR / "task_queue.py"
_spec = importlib.util.spec_from_file_location("tools_queue", _QUEUE_PATH)
assert _spec is not None and _spec.loader is not None
q = importlib.util.module_from_spec(_spec)
sys.modules["tools_queue"] = q
_spec.loader.exec_module(q)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KZT = dt.timezone(dt.timedelta(hours=5))


def _ts(year=2026, month=5, day=20, hour=11, minute=0, second=0) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, second, tzinfo=KZT)


def _read_shadow(wiki: Path) -> list[dict]:
    path = wiki / q.SHADOW_REL
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# 1. add() basic shape
# ---------------------------------------------------------------------------

def test_add_returns_id_with_date_prefix(tmp_path: Path):
    tid = q.add(
        title="hello",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    assert tid.startswith("t-2026-05-20-")
    assert tid == "t-2026-05-20-001"


def test_add_increments_daily_counter(tmp_path: Path):
    moment = _ts()
    ids = []
    for _ in range(3):
        ids.append(q.add(
            title="x",
            lane="claude",
            scope_paths=["tools/x.py"],
            wiki=tmp_path,
            now=moment,
        ))
    assert ids == [
        "t-2026-05-20-001",
        "t-2026-05-20-002",
        "t-2026-05-20-003",
    ]


def test_add_renders_task_queue_md(tmp_path: Path):
    tid = q.add(
        title="render-me",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    view = (tmp_path / q.VIEW_REL).read_text(encoding="utf-8")
    assert "render-me" in view
    assert tid in view
    assert "## Lane: claude" in view
    # Other lanes render empty.
    assert "## Lane: codex" in view
    assert "(empty)" in view


# ---------------------------------------------------------------------------
# 2. claim() — atomicity + already-claimed refusal
# ---------------------------------------------------------------------------

def test_claim_atomic_concurrent(tmp_path: Path):
    tid = q.add(
        title="race",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    results: list[bool] = []
    lock = threading.Lock()

    def worker(idx: int) -> None:
        ok = q.claim(
            id=tid,
            session_id=f"sess-{idx}",
            wiki=tmp_path,
            now=_ts(hour=11, minute=1),
        )
        with lock:
            results.append(ok)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(1 for r in results if r) == 1
    assert sum(1 for r in results if not r) == 3


def test_claim_returns_false_if_already_claimed(tmp_path: Path):
    tid = q.add(
        title="x",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    assert q.claim(id=tid, session_id="A", wiki=tmp_path, now=_ts(minute=1)) is True
    assert q.claim(id=tid, session_id="B", wiki=tmp_path, now=_ts(minute=2)) is False


# ---------------------------------------------------------------------------
# 3. release + done + heartbeat
# ---------------------------------------------------------------------------

def test_release_lets_another_session_claim(tmp_path: Path):
    tid = q.add(
        title="x",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    assert q.claim(id=tid, session_id="A", wiki=tmp_path, now=_ts(minute=1)) is True
    assert q.release(id=tid, wiki=tmp_path, now=_ts(minute=2)) is True
    assert q.claim(id=tid, session_id="B", wiki=tmp_path, now=_ts(minute=3)) is True

    # And the current owner is B.
    items = q.list_tasks(wiki=tmp_path)
    assert len(items) == 1
    assert items[0]["owner"] == "B"
    assert items[0]["status"] == "claimed"


def test_done_marks_status_done_with_timestamp(tmp_path: Path):
    tid = q.add(
        title="d",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    assert q.claim(id=tid, session_id="A", wiki=tmp_path, now=_ts(minute=1)) is True
    assert q.done(id=tid, wiki=tmp_path, now=_ts(minute=5)) is True
    items = q.list_tasks(status="done", wiki=tmp_path)
    assert len(items) == 1
    assert items[0]["id"] == tid
    assert items[0]["status"] == "done"
    # done is an ISO timestamp parseable back to a datetime.
    parsed = dt.datetime.fromisoformat(items[0]["done"])
    assert parsed.year == 2026


def test_heartbeat_updates_heartbeat_last(tmp_path: Path):
    tid = q.add(
        title="hb",
        lane="claude",
        scope_paths=["tools/x.py"],
        wiki=tmp_path,
        now=_ts(),
    )
    assert q.claim(id=tid, session_id="A", wiki=tmp_path, now=_ts(minute=1)) is True
    items_before = q.list_tasks(wiki=tmp_path)
    hb_before = items_before[0]["heartbeat_last"]

    assert q.heartbeat_task(id=tid, wiki=tmp_path, now=_ts(minute=4)) is True
    items_after = q.list_tasks(wiki=tmp_path)
    hb_after = items_after[0]["heartbeat_last"]

    assert hb_after != hb_before
    assert dt.datetime.fromisoformat(hb_after) > dt.datetime.fromisoformat(hb_before)


# ---------------------------------------------------------------------------
# 4. list / top filters
# ---------------------------------------------------------------------------

def test_list_filters_by_lane_and_status(tmp_path: Path):
    tid_claude = q.add(
        title="c",
        lane="claude",
        scope_paths=["tools/c.py"],
        wiki=tmp_path,
        now=_ts(minute=0),
    )
    tid_codex = q.add(
        title="cx",
        lane="codex",
        scope_paths=["tools/cx.py"],
        wiki=tmp_path,
        now=_ts(minute=1),
    )
    # Claim the codex one so it's status=claimed.
    assert q.claim(id=tid_codex, session_id="A", wiki=tmp_path, now=_ts(minute=2)) is True

    claude_only = q.list_tasks(lane="claude", wiki=tmp_path)
    assert len(claude_only) == 1
    assert claude_only[0]["id"] == tid_claude

    claimed_only = q.list_tasks(status="claimed", wiki=tmp_path)
    assert len(claimed_only) == 1
    assert claimed_only[0]["id"] == tid_codex


def test_top_returns_oldest_pending_per_lane(tmp_path: Path):
    t1 = q.add(title="1", lane="claude", scope_paths=["tools/a.py"],
               wiki=tmp_path, now=_ts(minute=0))
    q.add(title="2", lane="claude", scope_paths=["tools/b.py"],
          wiki=tmp_path, now=_ts(minute=1))
    q.add(title="3", lane="claude", scope_paths=["tools/c.py"],
          wiki=tmp_path, now=_ts(minute=2))
    head = q.top(lane="claude", wiki=tmp_path)
    assert head is not None
    assert head["id"] == t1


# ---------------------------------------------------------------------------
# 5. event_seq monotonic
# ---------------------------------------------------------------------------

def test_event_seq_monotonic_across_operations(tmp_path: Path):
    tid = q.add(title="m", lane="claude", scope_paths=["tools/x.py"],
                wiki=tmp_path, now=_ts(minute=0))
    assert q.claim(id=tid, session_id="A", wiki=tmp_path, now=_ts(minute=1)) is True
    assert q.done(id=tid, wiki=tmp_path, now=_ts(minute=2)) is True

    rows = _read_shadow(tmp_path)
    assert len(rows) == 3
    seqs = [r["event_seq"] for r in rows]
    assert seqs == [1, 2, 3]


# ---------------------------------------------------------------------------
# 6. View excludes done tasks
# ---------------------------------------------------------------------------

def test_render_view_done_tasks_excluded(tmp_path: Path):
    tid = q.add(title="DONE-TITLE-XYZ", lane="claude", scope_paths=["tools/x.py"],
                wiki=tmp_path, now=_ts(minute=0))
    assert q.claim(id=tid, session_id="A", wiki=tmp_path, now=_ts(minute=1)) is True
    assert q.done(id=tid, wiki=tmp_path, now=_ts(minute=2)) is True
    view = (tmp_path / q.VIEW_REL).read_text(encoding="utf-8")
    assert "DONE-TITLE-XYZ" not in view
    # And the claude lane renders empty now.
    assert "## Lane: claude" in view
    # The done row is gone, so the lane shows "(empty)" *somewhere*. Verify
    # by checking that the claude section's immediate body is "(empty)".
    lines = view.splitlines()
    idx = lines.index("## Lane: claude")
    # Allow blank line, then "(empty)".
    body = [ln for ln in lines[idx + 1: idx + 4] if ln.strip()]
    assert body and body[0] == "(empty)"


# ---------------------------------------------------------------------------
# 7. CLI roundtrip
# ---------------------------------------------------------------------------

def test_main_cli_add_then_claim_then_done(tmp_path: Path):
    env = {**os.environ, "NOUS_WIKI": str(tmp_path)}
    script = TOOLS_DIR / "task_queue.py"

    # add
    add_proc = subprocess.run(
        [sys.executable, str(script), "add",
         "--title", "cli-task",
         "--lane", "claude",
         "--scope", "tools/x.py"],
        env=env, capture_output=True, text=True, check=True,
    )
    tid = add_proc.stdout.strip()
    assert tid.startswith("t-")

    # claim
    claim_proc = subprocess.run(
        [sys.executable, str(script), "claim",
         "--id", tid, "--session", "cli-sess"],
        env=env, capture_output=True, text=True, check=True,
    )
    assert claim_proc.stdout.strip() == tid

    # done
    done_proc = subprocess.run(
        [sys.executable, str(script), "done", "--id", tid],
        env=env, capture_output=True, text=True, check=True,
    )
    assert done_proc.returncode == 0

    # list --json
    list_proc = subprocess.run(
        [sys.executable, str(script), "list", "--json"],
        env=env, capture_output=True, text=True, check=True,
    )
    items = json.loads(list_proc.stdout)
    assert len(items) == 1
    assert items[0]["id"] == tid
    assert items[0]["status"] == "done"


# ---------------------------------------------------------------------------
# 8. _load_shadow gracefully skips malformed lines
# ---------------------------------------------------------------------------

def test_load_shadow_skips_malformed_lines(tmp_path: Path, capsys):
    shadow = tmp_path / q.SHADOW_REL
    shadow.parent.mkdir(parents=True, exist_ok=True)
    valid_a = json.dumps({"id": "t-1", "event_seq": 1, "status": "pending",
                          "lane": "claude", "title": "a"})
    valid_b = json.dumps({"id": "t-2", "event_seq": 2, "status": "pending",
                          "lane": "claude", "title": "b"})
    shadow.write_text(valid_a + "\n" + "{not json at all" + "\n" + valid_b + "\n",
                      encoding="utf-8")
    rows = q._load_shadow(tmp_path)
    assert len(rows) == 2
    assert {r["id"] for r in rows} == {"t-1", "t-2"}
    captured = capsys.readouterr()
    assert "malformed" in captured.err
