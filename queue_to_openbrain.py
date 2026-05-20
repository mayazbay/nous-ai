"""Queue -> OpenBrain emitter (Ship 2 wave 3c).

Posts OpenBrain thoughts for queue events, fire-and-forget. Two operations:

* ``emit-done <task_id>``: posts a ``task_completed`` thought when a task has
  moved to ``status='done'`` in ``tools/task_queue.py``'s shadow JSONL. Idempotent
  via ``pages/systems/queue-openbrain-cursor.jsonl`` — each emit appends
  ``{task_id, event_seq, ts}`` so retries don't duplicate. If Popen itself
  raises (rare), the cursor is NOT updated and ``reason='capture_failed'`` is
  returned so the next call retries.

* ``weekly-digest``: enumerates all tasks whose latest state is ``done`` with
  ``done`` timestamp inside the last 7 days, renders one markdown digest, and
  posts a ``weekly_retro`` thought.

Both fire-and-forget side-channels mirror the Ship-1 Step-8b pattern in
``tools/model_failover_state.py`` (``subprocess.Popen`` with
``start_new_session=True``, output redirected to a log file).

State files:

* Cursor: ``pages/systems/queue-openbrain-cursor.jsonl`` (append-only).
* Log:    ``logs/openbrain-queue.log`` (append-only).

Stdlib only. Loaded queue module via ``importlib`` because the stdlib
``queue`` package shadows the filename when imported normally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

ALMATY = dt.timezone(dt.timedelta(hours=5))
CURSOR_REL = Path("pages/systems/queue-openbrain-cursor.jsonl")
LOG_REL = Path("logs/openbrain-queue.log")


# ---------------------------------------------------------------------------
# Path resolution (mirrors tools/task_queue.py)
# ---------------------------------------------------------------------------

def default_wiki() -> Path:
    """Resolve wiki root. Honors ``NOUS_WIKI`` env, else parent of this file."""
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


def _cursor_path(wiki: Path) -> Path:
    return wiki / CURSOR_REL


def _log_path(wiki: Path) -> Path:
    return wiki / LOG_REL


# ---------------------------------------------------------------------------
# Queue module loader (stdlib ``queue`` shadows the filename)
# ---------------------------------------------------------------------------

def _load_queue_module(wiki: Path):
    """Load ``tools/task_queue.py`` via importlib.

    The stdlib ``queue`` module would otherwise shadow this name. Resolved
    relative to *this* file so the loader works in tmp_path test sandboxes
    too (``wiki`` is only used to provide the queue API its wiki root later).
    """
    del wiki  # not needed for module location, only at call sites
    queue_path = Path(__file__).resolve().parent / "task_queue.py"
    spec = importlib.util.spec_from_file_location("tools_queue", queue_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load queue module from {queue_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tools_queue"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Cursor IO (dedup source of truth)
# ---------------------------------------------------------------------------

def _read_cursor(wiki: Path) -> list[dict[str, Any]]:
    path = _cursor_path(wiki)
    out: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return out
    except OSError as exc:
        print(f"queue_to_openbrain: cursor OSError {path}: {exc}", file=sys.stderr)
        return out
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _already_emitted(wiki: Path, task_id: str, event_seq: int) -> bool:
    """True if a row matching (task_id, event_seq) is already in the cursor."""
    for row in _read_cursor(wiki):
        if row.get("task_id") == task_id and row.get("event_seq") == event_seq:
            return True
    return False


def _append_cursor(wiki: Path, task_id: str, event_seq: int) -> None:
    """Append ``{task_id, event_seq, ts}`` to cursor.jsonl, fcntl-locked."""
    import fcntl  # local import keeps top-of-file stdlib-bash-y

    path = _cursor_path(wiki)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "task_id": task_id,
        "event_seq": event_seq,
        "ts": now_kzt().isoformat(),
    }
    line = json.dumps(row, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# OpenBrain fire-and-forget capture
# ---------------------------------------------------------------------------

def _capture_openbrain(payload: dict[str, Any], wiki: Path) -> None:
    """Fire-and-forget OpenBrain capture.

    Spawns ``mcp call claude.ai_Open_Brain capture_thought <json>`` via
    ``subprocess.Popen(..., start_new_session=True)``. Output goes to
    ``logs/openbrain-queue.log``. **Raises** if ``Popen`` itself fails so
    callers can avoid cursor-updating in that case (retry safety).
    """
    log_path = _log_path(wiki)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    title = str(payload.get("title", "?"))
    encoded = json.dumps(payload, ensure_ascii=False)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[{now_kzt().isoformat()}] queue: {title}\n")
        log.flush()
        subprocess.Popen(
            ["mcp", "call", "claude.ai_Open_Brain", "capture_thought", encoded],
            stdout=log,
            stderr=log,
            start_new_session=True,
        )


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _fmt_duration(claimed_iso: str | None, done_iso: str | None) -> str:
    if not claimed_iso or not done_iso:
        return "—"
    try:
        c = dt.datetime.fromisoformat(claimed_iso)
        d = dt.datetime.fromisoformat(done_iso)
    except (TypeError, ValueError):
        return "—"
    if c.tzinfo is None:
        c = c.replace(tzinfo=ALMATY)
    if d.tzinfo is None:
        d = d.replace(tzinfo=ALMATY)
    secs = int((d - c).total_seconds())
    if secs < 0:
        secs = 0
    if secs < 60:
        return f"{secs}s"
    m = secs // 60
    if m < 60:
        rem = secs - m * 60
        return f"{m}m{rem:02d}s"
    h = m // 60
    rm = m - h * 60
    return f"{h}h{rm:02d}m"


def render_task_body(task: dict[str, Any]) -> str:
    """Render a task as markdown body for an OpenBrain thought."""
    title = str(task.get("title") or "")
    tid = str(task.get("id") or "")
    lane = str(task.get("lane") or "")
    scope_paths = task.get("scope_paths") or []
    if isinstance(scope_paths, list):
        scope_str = ",".join(str(p) for p in scope_paths)
    else:
        scope_str = str(scope_paths)
    created = str(task.get("created") or "")
    claimed = str(task.get("claimed") or "")
    done_ts = str(task.get("done") or "")
    duration = _fmt_duration(task.get("claimed"), task.get("done"))
    owner = str(task.get("owner") or "—")
    parent = str(task.get("parent") or "none")
    blocked_raw = task.get("blocked_by") or []
    if isinstance(blocked_raw, list) and blocked_raw:
        blocked_str = ",".join(str(b) for b in blocked_raw)
    else:
        blocked_str = "none"
    lines = [
        f"# {title}",
        "",
        f"- id: {tid}",
        f"- lane: {lane}",
        f"- scope: {scope_str}",
        f"- created: {created}",
        f"- claimed: {claimed}",
        f"- done: {done_ts}",
        f"- duration: {duration}",
        f"- owner: {owner}",
        f"- parent: {parent}",
        f"- blocked_by: {blocked_str}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Queue lookup helpers
# ---------------------------------------------------------------------------

def _find_task_and_seq(
    q_mod, wiki: Path, task_id: str
) -> tuple[dict[str, Any] | None, int | None]:
    """Return the current task dict + its latest event_seq from shadow.

    ``tools/task_queue.py``'s public ``list_tasks`` already reduces rows per task,
    but we also need the event_seq of the *latest* row matching ``task_id`` —
    so we re-scan the shadow ourselves using the private ``_load_shadow``.
    Private access is acceptable because both modules ship together.
    """
    rows = q_mod._load_shadow(wiki)  # noqa: SLF001 — internal sibling
    best_row: dict[str, Any] | None = None
    best_seq = -1
    for r in rows:
        if r.get("id") != task_id:
            continue
        seq = r.get("event_seq")
        if isinstance(seq, int) and seq > best_seq:
            best_seq = seq
            best_row = r
    if best_row is None:
        return None, None
    return best_row, best_seq


# ---------------------------------------------------------------------------
# Public API: emit_done
# ---------------------------------------------------------------------------

def emit_done(task_id: str, *, wiki: Path | None = None) -> dict[str, Any]:
    """Emit a ``task_completed`` thought for the given task_id.

    Returns a result dict with ``task_id``, ``emitted``, ``reason``.

    Reasons:
        * ``task_not_found``     — id not in shadow.
        * ``task_not_done``      — current status != ``done``.
        * ``already_emitted``    — cursor already has (task_id, event_seq).
        * ``capture_failed``     — Popen raised; cursor untouched, retry safe.
        * ``ok``                 — emitted + cursor appended.
    """
    wiki = _resolve_wiki(wiki)
    q_mod = _load_queue_module(wiki)

    info, event_seq = _find_task_and_seq(q_mod, wiki, task_id)
    if info is None or event_seq is None:
        return {"task_id": task_id, "emitted": False, "reason": "task_not_found"}
    if info.get("status") != "done":
        return {"task_id": task_id, "emitted": False, "reason": "task_not_done"}
    if _already_emitted(wiki, task_id, event_seq):
        return {"task_id": task_id, "emitted": False, "reason": "already_emitted"}

    payload = {
        "type": "task_completed",
        "title": f"Task done: {info.get('title', '')}",
        "body": render_task_body(info),
        "tags": [
            "nous-queue",
            f"lane:{info.get('lane', '')}",
            f"task:{info.get('id', '')}",
        ],
    }

    try:
        _capture_openbrain(payload, wiki)
    except Exception as exc:  # noqa: BLE001 — fire-and-forget, retry next call
        # Log the failure but do NOT update cursor (retry safe).
        try:
            log_path = _log_path(wiki)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log:
                log.write(
                    f"[{now_kzt().isoformat()}] queue: capture_failed "
                    f"task={task_id} err={exc!r}\n"
                )
        except OSError:
            pass
        return {"task_id": task_id, "emitted": False, "reason": "capture_failed"}

    _append_cursor(wiki, task_id, event_seq)
    return {"task_id": task_id, "emitted": True, "reason": "ok"}


# ---------------------------------------------------------------------------
# Public API: weekly_digest
# ---------------------------------------------------------------------------

def _parse_done_ts(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        d = dt.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=ALMATY)
    return d


def weekly_digest(
    *,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """List done tasks in the last 7 days. Emit ONE ``weekly_retro`` thought."""
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)
    cutoff = moment - dt.timedelta(days=7)

    q_mod = _load_queue_module(wiki)
    rows = q_mod._load_shadow(wiki)  # noqa: SLF001
    current = q_mod._latest_per_task(rows)  # noqa: SLF001

    in_window: list[dict[str, Any]] = []
    for info in current.values():
        if info.get("status") != "done":
            continue
        done_dt = _parse_done_ts(info.get("done"))
        if done_dt is None:
            continue
        if done_dt < cutoff:
            continue
        in_window.append(info)

    in_window.sort(key=lambda r: r.get("done") or "")

    lanes_count: dict[str, int] = {}
    for info in in_window:
        lane = str(info.get("lane") or "?")
        lanes_count[lane] = lanes_count.get(lane, 0) + 1

    date_str = moment.strftime("%Y-%m-%d")
    title = f"Weekly queue retro {date_str}"

    body_lines: list[str] = [
        f"# {title}",
        "",
        f"Window: last 7 days (since {cutoff.isoformat()}).",
        f"Total done tasks: {len(in_window)}.",
        "",
        "## By lane",
        "",
    ]
    if lanes_count:
        for lane in sorted(lanes_count.keys()):
            body_lines.append(f"- {lane}: {lanes_count[lane]}")
    else:
        body_lines.append("(none)")
    body_lines.append("")
    body_lines.append("## Tasks")
    body_lines.append("")
    if in_window:
        for info in in_window:
            tid = str(info.get("id") or "")
            lane = str(info.get("lane") or "")
            ttitle = str(info.get("title") or "")
            duration = _fmt_duration(info.get("claimed"), info.get("done"))
            body_lines.append(f"- {tid} [{lane}] {ttitle} ({duration})")
    else:
        body_lines.append("(none)")

    payload = {
        "type": "weekly_retro",
        "title": title,
        "body": "\n".join(body_lines),
        "tags": ["nous-queue", "weekly-retro", f"date:{date_str}"],
    }

    emitted = False
    try:
        _capture_openbrain(payload, wiki)
        emitted = True
    except Exception as exc:  # noqa: BLE001 — fire-and-forget
        try:
            log_path = _log_path(wiki)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log:
                log.write(
                    f"[{now_kzt().isoformat()}] queue: weekly_digest_failed "
                    f"err={exc!r}\n"
                )
        except OSError:
            pass

    return {
        "emitted": emitted,
        "task_count": len(in_window),
        "lanes": lanes_count,
        "title": title,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Queue -> OpenBrain emitter")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_emit = sub.add_parser("emit-done")
    p_emit.add_argument("--id", required=True)
    p_emit.add_argument("--json", action="store_true")

    p_weekly = sub.add_parser("weekly-digest")
    p_weekly.add_argument("--json", action="store_true")

    args = parser.parse_args()
    wiki = default_wiki()

    if args.cmd == "emit-done":
        result = emit_done(args.id, wiki=wiki)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"{result['reason']} emitted={result['emitted']}")
        return 0 if result["emitted"] else 1
    if args.cmd == "weekly-digest":
        result = weekly_digest(wiki=wiki)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"emitted={result['emitted']} tasks={result['task_count']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
