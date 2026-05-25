"""Atomic task queue — append-only JSONL shadow + rendered TASK_QUEUE.md view.

Companion to ``tools/lane_lock.py``. Whereas lane_lock is the *advisory* layer
(can lane X edit path Y right now?), queue.py is the *durable* layer (what is
each lane working on across sessions?).

State files:

* Shadow:        ``pages/systems/tasks.jsonl``      — append-only, newest-last.
* Rendered view: ``TASK_QUEUE.md`` at wiki root     — auto-rendered atomically.
* fcntl lock:    ``logs/queue-state.lock``          — serializes all mutations.

Statuses: ``pending → claimed → done | released | stale``.

Each row carries a monotonic ``event_seq`` (1-based) used by Ship 2's
``queue_to_openbrain`` projection for dedup.

CLI::

    python3 tools/task_queue.py add --title "T" --lane claude --scope tools/x.py
    python3 tools/task_queue.py claim --id t-2026-05-20-001 --session s108-mac-7421
    python3 tools/task_queue.py release --id t-2026-05-20-001
    python3 tools/task_queue.py done --id t-2026-05-20-001
    python3 tools/task_queue.py heartbeat --id t-2026-05-20-001
    python3 tools/task_queue.py list [--lane claude] [--status pending] [--json]
    python3 tools/task_queue.py top  [--lane claude] [--json]
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import socket
import sys
import uuid
from pathlib import Path
from typing import Any, Iterator

ALMATY = dt.timezone(dt.timedelta(hours=5))
SHADOW_REL = Path("pages/systems/tasks.jsonl")
VIEW_REL = Path("TASK_QUEUE.md")
QUEUE_STATE_LOCK_REL = Path("logs/queue-state.lock")
KNOWN_LANES = ("claude", "codex", "grok", "opus")
KNOWN_STATUSES = ("pending", "claimed", "done", "released", "stale")


# ---------------------------------------------------------------------------
# Path resolution helpers (mirrors lane_lock.default_wiki / now_kzt)
# ---------------------------------------------------------------------------

def default_wiki() -> Path:
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parents[1]
    if (here / "pages").exists():
        return here
    if (here / "wiki" / "pages").exists():
        return here / "wiki"
    return here


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def _resolve_wiki(wiki: Path | None) -> Path:
    return wiki if wiki is not None else default_wiki()


def _shadow_path(wiki: Path) -> Path:
    return wiki / SHADOW_REL


def _view_path(wiki: Path) -> Path:
    return wiki / VIEW_REL


def _state_lock_path(wiki: Path) -> Path:
    return wiki / QUEUE_STATE_LOCK_REL


def _ensure_dirs(wiki: Path) -> None:
    _shadow_path(wiki).parent.mkdir(parents=True, exist_ok=True)
    _view_path(wiki).parent.mkdir(parents=True, exist_ok=True)
    _state_lock_path(wiki).parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _parse_iso(s: str) -> dt.datetime | None:
    try:
        d = dt.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=ALMATY)
    return d


def _default_session_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


# ---------------------------------------------------------------------------
# fcntl state lock context manager (mirrors lane_lock._with_state_lock)
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _with_state_lock(wiki: Path) -> Iterator[None]:
    """Context manager that takes fcntl.LOCK_EX on logs/queue-state.lock."""
    _ensure_dirs(wiki)
    lock_path = _state_lock_path(wiki)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Shadow IO
# ---------------------------------------------------------------------------

def _load_shadow(wiki: Path) -> list[dict[str, Any]]:
    """Read all shadow rows. Malformed lines are logged to stderr and skipped."""
    path = _shadow_path(wiki)
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return rows
    except OSError as exc:
        print(f"queue: OSError reading shadow {path}: {exc}", file=sys.stderr)
        return rows
    for lineno, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            print(
                f"queue: skipping malformed shadow line {lineno}: {exc}",
                file=sys.stderr,
            )
            continue
        if not isinstance(obj, dict):
            print(
                f"queue: skipping non-object shadow line {lineno}",
                file=sys.stderr,
            )
            continue
        rows.append(obj)
    return rows


def _append_shadow(wiki: Path, row: dict[str, Any]) -> None:
    """Append-only JSONL write. Caller MUST hold the queue state lock."""
    _ensure_dirs(wiki)
    path = _shadow_path(wiki)
    line = json.dumps(row, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as fh:
        # Inner advisory lock — belt + suspenders. The outer fcntl on
        # logs/queue-state.lock is the primary serializer; this guards
        # against rogue processes that happen to write into tasks.jsonl
        # without going through the state lock.
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _next_event_seq(wiki: Path) -> int:
    """Monotonic across all queue mutations. Returns max(event_seq) + 1, or 1."""
    rows = _load_shadow(wiki)
    best = 0
    for r in rows:
        seq = r.get("event_seq")
        if isinstance(seq, int) and seq > best:
            best = seq
    return best + 1


def _latest_per_task(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Reduce shadow rows to one current-state dict per task id.

    Most recent ``event_seq`` wins. Rows without an integer ``event_seq`` are
    ignored for ordering purposes (but their fields are merged into whatever
    we settle on as "current" iff they happen to share the id and were last).
    """
    by_id: dict[str, dict[str, Any]] = {}
    best_seq: dict[str, int] = {}
    for r in rows:
        tid = r.get("id")
        if not isinstance(tid, str) or not tid:
            continue
        seq = r.get("event_seq")
        if not isinstance(seq, int):
            # Treat rows without seq as oldest possible — only adopt if we
            # have no row at all yet for this id.
            if tid not in by_id:
                by_id[tid] = dict(r)
                best_seq[tid] = -1
            continue
        if tid not in by_id or seq > best_seq[tid]:
            by_id[tid] = dict(r)
            best_seq[tid] = seq
    return by_id


# ---------------------------------------------------------------------------
# View rendering
# ---------------------------------------------------------------------------

def _format_age(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    s = int(seconds)
    if s < 60:
        return f"{s}s ago"
    m = s // 60
    if m < 60:
        return f"{m}m ago"
    h = m // 60
    return f"{h}h ago"


def _md_escape(value: str) -> str:
    """Escape a value for safe inclusion in a markdown table cell."""
    return value.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _render_view_atomic(wiki: Path, now: dt.datetime | None = None) -> None:
    """Render TASK_QUEUE.md from shadow. Atomic temp+rename.

    * Groups by lane in KNOWN_LANES order; one ``## Lane: <lane>`` section each.
    * Filters out ``done`` rows from the view (they still accumulate in shadow).
    * Within a lane: newest-first by ``created`` timestamp.
    * Computes ``claimed_age`` from ``claimed`` vs ``now`` for claimed rows;
      pending rows use ``created`` instead.
    """
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    rows = _load_shadow(wiki)
    current = _latest_per_task(rows)

    # Per-lane bucket of non-done active rows.
    lanes: dict[str, list[dict[str, Any]]] = {lane: [] for lane in KNOWN_LANES}
    for tid, info in current.items():
        if info.get("status") == "done":
            continue
        lane = info.get("lane")
        if lane in lanes:
            lanes[lane].append(info)
        # Unknown lanes silently dropped from the rendered view.

    # Sort each lane newest-first by ``created``.
    for lane in lanes:
        lanes[lane].sort(
            key=lambda r: r.get("created") or "",
            reverse=True,
        )

    lines: list[str] = []
    lines.append("---")
    lines.append("type: system")
    lines.append("id: task-queue-view")
    lines.append("auto_rendered_by: tools/task_queue.py")
    lines.append(f"last_render: {moment.isoformat()}")
    lines.append("---")
    lines.append("")
    lines.append("# TASK_QUEUE")
    lines.append("")

    for lane in KNOWN_LANES:
        lines.append(f"## Lane: {lane}")
        lines.append("")
        entries = lanes[lane]
        if not entries:
            lines.append("(empty)")
            lines.append("")
            continue
        lines.append("| id | status | owner | claimed_age | scope | title |")
        lines.append("|---|---|---|---|---|---|")
        for e in entries:
            status = str(e.get("status") or "")
            owner = str(e.get("owner") or "—")
            anchor_ts: dt.datetime | None
            if status == "claimed":
                anchor_ts = _parse_iso(str(e.get("claimed") or ""))
            else:
                anchor_ts = _parse_iso(str(e.get("created") or ""))
            if anchor_ts is None:
                age_str = "—"
            else:
                age_str = _format_age((moment - anchor_ts).total_seconds())
            scope_paths = e.get("scope_paths") or []
            if isinstance(scope_paths, list):
                scope_str = ",".join(str(p) for p in scope_paths)
            else:
                scope_str = str(scope_paths)
            title = str(e.get("title") or "")
            row_cells = [
                _md_escape(str(e.get("id") or "")),
                _md_escape(status),
                _md_escape(owner),
                _md_escape(age_str),
                _md_escape(scope_str),
                _md_escape(title),
            ]
            lines.append("| " + " | ".join(row_cells) + " |")
        lines.append("")

    payload = "\n".join(lines).rstrip() + "\n"
    path = _view_path(wiki)
    _ensure_dirs(wiki)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.rename(tmp, path)


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def _new_task_id(wiki: Path, moment: dt.datetime) -> str:
    """Generate ``t-YYYY-MM-DD-NNN`` using day-scoped counter scan.

    Counter = (max existing -NNN suffix among today's task IDs in the shadow) + 1.
    """
    prefix = moment.strftime("t-%Y-%m-%d-")
    rows = _load_shadow(wiki)
    seen: set[int] = set()
    for r in rows:
        tid = r.get("id")
        if isinstance(tid, str) and tid.startswith(prefix):
            tail = tid[len(prefix):]
            try:
                seen.add(int(tail))
            except ValueError:
                continue
    n = max(seen) + 1 if seen else 1
    return f"{prefix}{n:03d}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add(
    *,
    title: str,
    lane: str,
    scope_paths: list[str],
    blocked_by: list[str] | None = None,
    parent: str | None = None,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> str:
    """Create a new pending task. Returns the new task id."""
    if not title:
        raise ValueError("title must be non-empty")
    if lane not in KNOWN_LANES:
        raise ValueError(f"lane must be one of {KNOWN_LANES}, got {lane!r}")
    if not scope_paths:
        raise ValueError("scope_paths must be non-empty")

    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        tid = _new_task_id(wiki, moment)
        seq = _next_event_seq(wiki)
        row = {
            "id": tid,
            "lane": lane,
            "status": "pending",
            "owner": None,
            "created": moment.isoformat(),
            "claimed": None,
            "heartbeat_last": None,
            "scope_paths": list(scope_paths),
            "blocked_by": list(blocked_by or []),
            "parent": parent,
            "title": title,
            "done": None,
            "event_seq": seq,
        }
        _append_shadow(wiki, row)
        _render_view_atomic(wiki, now=moment)
        return tid


def claim(
    *,
    id: str,
    session_id: str,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> bool:
    """Claim a pending task. Returns False if non-existent or already claimed."""
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        rows = _load_shadow(wiki)
        current = _latest_per_task(rows)
        info = current.get(id)
        if info is None:
            return False
        if info.get("status") == "claimed":
            return False
        # released / stale / pending are all claimable. done is not.
        if info.get("status") == "done":
            return False
        seq = _next_event_seq(wiki)
        row = {
            "id": id,
            "lane": info.get("lane"),
            "status": "claimed",
            "owner": session_id,
            "created": info.get("created"),
            "claimed": moment.isoformat(),
            "heartbeat_last": moment.isoformat(),
            "scope_paths": list(info.get("scope_paths") or []),
            "blocked_by": list(info.get("blocked_by") or []),
            "parent": info.get("parent"),
            "title": info.get("title"),
            "done": None,
            "event_seq": seq,
        }
        _append_shadow(wiki, row)
        _render_view_atomic(wiki, now=moment)
        return True


def release(
    *,
    id: str,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> bool:
    """Release a task back to claimable state.

    Appends a ``status='released'`` row. Loaders treat ``released`` as
    re-claimable (i.e. equivalent to pending for the purposes of ``claim``).
    Returns False if the task does not exist.
    """
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        rows = _load_shadow(wiki)
        current = _latest_per_task(rows)
        info = current.get(id)
        if info is None:
            return False
        seq = _next_event_seq(wiki)
        row = {
            "id": id,
            "lane": info.get("lane"),
            "status": "released",
            "owner": None,
            "created": info.get("created"),
            "claimed": None,
            "heartbeat_last": None,
            "scope_paths": list(info.get("scope_paths") or []),
            "blocked_by": list(info.get("blocked_by") or []),
            "parent": info.get("parent"),
            "title": info.get("title"),
            "done": None,
            "event_seq": seq,
        }
        _append_shadow(wiki, row)
        _render_view_atomic(wiki, now=moment)
        return True


def done(
    *,
    id: str,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> bool:
    """Mark task done. Status='done', done=now. Returns False if non-existent."""
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        rows = _load_shadow(wiki)
        current = _latest_per_task(rows)
        info = current.get(id)
        if info is None:
            return False
        seq = _next_event_seq(wiki)
        row = {
            "id": id,
            "lane": info.get("lane"),
            "status": "done",
            "owner": info.get("owner"),
            "created": info.get("created"),
            "claimed": info.get("claimed"),
            "heartbeat_last": info.get("heartbeat_last"),
            "scope_paths": list(info.get("scope_paths") or []),
            "blocked_by": list(info.get("blocked_by") or []),
            "parent": info.get("parent"),
            "title": info.get("title"),
            "done": moment.isoformat(),
            "event_seq": seq,
        }
        _append_shadow(wiki, row)
        _render_view_atomic(wiki, now=moment)
        return True


def heartbeat_task(
    *,
    id: str,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> bool:
    """Update ``heartbeat_last`` on a claimed task.

    Returns False if the task does not exist or is not currently claimed.
    """
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        rows = _load_shadow(wiki)
        current = _latest_per_task(rows)
        info = current.get(id)
        if info is None:
            return False
        if info.get("status") != "claimed":
            return False
        seq = _next_event_seq(wiki)
        row = {
            "id": id,
            "lane": info.get("lane"),
            "status": "claimed",
            "owner": info.get("owner"),
            "created": info.get("created"),
            "claimed": info.get("claimed"),
            "heartbeat_last": moment.isoformat(),
            "scope_paths": list(info.get("scope_paths") or []),
            "blocked_by": list(info.get("blocked_by") or []),
            "parent": info.get("parent"),
            "title": info.get("title"),
            "done": None,
            "event_seq": seq,
        }
        _append_shadow(wiki, row)
        _render_view_atomic(wiki, now=moment)
        return True


def list_tasks(
    *,
    lane: str | None = None,
    status: str | None = None,
    wiki: Path | None = None,
) -> list[dict[str, Any]]:
    """List tasks (current state per task). Filter by lane and/or status."""
    wiki = _resolve_wiki(wiki)
    rows = _load_shadow(wiki)
    current = _latest_per_task(rows)
    out: list[dict[str, Any]] = []
    for info in current.values():
        if lane is not None and info.get("lane") != lane:
            continue
        if status is not None and info.get("status") != status:
            continue
        out.append(dict(info))
    # Stable order: by created ascending (oldest first) — same as top()'s
    # FIFO ordering. Callers that want newest-first can reverse.
    out.sort(key=lambda r: r.get("created") or "")
    return out


def top(
    *,
    lane: str | None = None,
    wiki: Path | None = None,
) -> dict[str, Any] | None:
    """Return the oldest claimable task for the lane (FIFO claim order).

    Claimable = current status is ``pending`` or ``released``. ``None`` if none.
    """
    wiki = _resolve_wiki(wiki)
    rows = _load_shadow(wiki)
    current = _latest_per_task(rows)
    candidates: list[dict[str, Any]] = []
    for info in current.values():
        if info.get("status") not in ("pending", "released"):
            continue
        if lane is not None and info.get("lane") != lane:
            continue
        candidates.append(info)
    if not candidates:
        return None
    candidates.sort(key=lambda r: r.get("created") or "")
    return dict(candidates[0])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Atomic task queue CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--lane", required=True, choices=KNOWN_LANES)
    p_add.add_argument("--scope", action="append", required=True)
    p_add.add_argument("--blocked-by", action="append", default=[])
    p_add.add_argument("--parent")

    p_claim = sub.add_parser("claim")
    p_claim.add_argument("--id", required=True)
    p_claim.add_argument("--session", required=True)

    p_release = sub.add_parser("release")
    p_release.add_argument("--id", required=True)

    p_done = sub.add_parser("done")
    p_done.add_argument("--id", required=True)

    p_heartbeat = sub.add_parser("heartbeat")
    p_heartbeat.add_argument("--id", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--lane", choices=KNOWN_LANES)
    p_list.add_argument("--status", choices=KNOWN_STATUSES)
    p_list.add_argument("--json", action="store_true")

    p_top = sub.add_parser("top")
    p_top.add_argument("--lane", choices=KNOWN_LANES)
    p_top.add_argument("--json", action="store_true")

    args = parser.parse_args()
    wiki = default_wiki()

    if args.cmd == "add":
        tid = add(
            title=args.title,
            lane=args.lane,
            scope_paths=args.scope,
            blocked_by=args.blocked_by,
            parent=args.parent,
            wiki=wiki,
        )
        print(tid)
        return 0
    if args.cmd == "claim":
        ok = claim(id=args.id, session_id=args.session, wiki=wiki)
        if ok:
            print(args.id)
            return 0
        print("REFUSED", file=sys.stderr)
        return 1
    if args.cmd == "release":
        return 0 if release(id=args.id, wiki=wiki) else 1
    if args.cmd == "done":
        return 0 if done(id=args.id, wiki=wiki) else 1
    if args.cmd == "heartbeat":
        return 0 if heartbeat_task(id=args.id, wiki=wiki) else 1
    if args.cmd == "list":
        items = list_tasks(lane=args.lane, status=args.status, wiki=wiki)
        if args.json:
            print(json.dumps(items, ensure_ascii=False))
        else:
            for t in items:
                print(
                    f"{t['id']}  lane={t.get('lane')}  "
                    f"status={t.get('status')}  title={t.get('title', '')}"
                )
        return 0
    if args.cmd == "top":
        t = top(lane=args.lane, wiki=wiki)
        if t is None:
            return 1
        if args.json:
            print(json.dumps(t, ensure_ascii=False))
        else:
            print(t["id"])
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
