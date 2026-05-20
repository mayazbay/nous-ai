"""Session-start handshake — lock-then-claim protocol.

Called by ``/code``, ``/codex``, and ``/grok`` slash command handlers at the
start of a new agent session. Implements the **lock-first, claim-second**
sequence so two sessions in different lanes can never race their way into
overlapping scopes:

1. List active lane locks → build operator-facing summary of who's holding what.
2. ``queue.top(lane=...)`` → fetch the oldest claimable task for this lane.
3. ``lane_lock.acquire(...)`` FIRST. If conflict (another lane's overlapping
   token), refuse and emit a Telegram-ready nudge.
4. If lock OK, ``queue.claim(...)``. If claim loses a race (someone beat us to
   it), release the lock we just took so we never leave zombie locks.
5. Best-effort STATUS.md re-render via ``status_render`` (parallel subagent
   may not have committed it yet — wrap in try/except).

Companion to ``tools/lane_lock.py`` (advisory layer) and ``tools/task_queue.py``
(durable layer). Ship 2 wave 3b.

CLI::

    python3 tools/handshake.py start --lane claude [--intent "..."] [--session ID] [--json]
    python3 tools/handshake.py end --lock-token lk-claude-... [--task-id t-...]
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

ALMATY = dt.timezone(dt.timedelta(hours=5))
KNOWN_LANES = ("claude", "codex", "grok", "opus")
DEFAULT_TTL_SEC = 600  # 10 min — long enough for a slow startup; heartbeat extends.


# ---------------------------------------------------------------------------
# Module-level loader for tools/task_queue.py
# ---------------------------------------------------------------------------
# tools/task_queue.py would collide with stdlib `queue` if we used a normal import,
# so load it by file path and stash under a non-clashing module name.

_THIS_DIR = Path(__file__).resolve().parent
_QUEUE_PATH = _THIS_DIR / "task_queue.py"


def _load_queue_module():
    if "tools_queue" in sys.modules:
        return sys.modules["tools_queue"]
    spec = importlib.util.spec_from_file_location("tools_queue", _QUEUE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_QUEUE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tools_queue"] = module
    spec.loader.exec_module(module)
    return module


_queue_mod = _load_queue_module()


# ---------------------------------------------------------------------------
# Dual-import for lane_lock (package + file-path fallback for direct CLI use)
# ---------------------------------------------------------------------------

try:
    from tools import lane_lock as _lane_lock  # type: ignore
except ImportError:  # pragma: no cover — exercised when run as a script
    if str(_THIS_DIR) not in sys.path:
        sys.path.insert(0, str(_THIS_DIR))
    import lane_lock as _lane_lock  # type: ignore


# ---------------------------------------------------------------------------
# Path / time helpers (mirror lane_lock / queue conventions)
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


def session_id() -> str:
    """Default session id: ``<hostname>-<pid>-<unix_ts>``."""
    return f"{socket.gethostname()}-{os.getpid()}-{int(time.time())}"


def _resolve_wiki(wiki: Path | None) -> Path:
    return wiki if wiki is not None else default_wiki()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _scope_summary(scope_paths: list[str], limit: int = 60) -> str:
    """Comma-join scope paths with length cap for inline display."""
    if not scope_paths:
        return "—"
    joined = ",".join(scope_paths)
    if len(joined) <= limit:
        return joined
    return joined[: limit - 1] + "…"


def _build_active_lanes(wiki: Path) -> list[dict[str, Any]]:
    """Summarise active lock tokens grouped by lane.

    Returns one entry per lane with at least one active token::

        {"lane": "codex", "tokens": 1, "scope_summary": "tools/task_queue.py"}
    """
    try:
        active = _lane_lock.list_active(wiki=wiki)
    except (OSError, ValueError) as exc:
        print(f"handshake: list_active failed: {exc}", file=sys.stderr)
        return []
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for entry in active:
        lane = entry.get("lane") or "?"
        by_lane.setdefault(lane, []).append(entry)
    out: list[dict[str, Any]] = []
    for lane in sorted(by_lane.keys()):
        entries = by_lane[lane]
        scopes: list[str] = []
        for e in entries:
            for p in e.get("scope_paths", []) or []:
                if p not in scopes:
                    scopes.append(p)
        out.append({
            "lane": lane,
            "tokens": len(entries),
            "scope_summary": _scope_summary(scopes),
        })
    return out


def _find_overlap_token(
    wiki: Path,
    lane: str,
    scope_paths: list[str],
) -> dict[str, Any] | None:
    """Return the first *other-lane* token whose scope overlaps *scope_paths*.

    Used only to enrich the refusal message — ``lane_lock.acquire`` already
    enforces the conflict semantics atomically.
    """
    try:
        active = _lane_lock.list_active(wiki=wiki)
    except (OSError, ValueError):
        return None
    for entry in active:
        if entry.get("lane") == lane:
            continue
        existing = list(entry.get("scope_paths") or [])
        if _lane_lock.overlap(scope_paths, existing):
            return entry
    return None


def _best_effort_status_render(wiki: Path) -> None:
    """Re-render STATUS.md if status_render is importable. Never blocks."""
    sr = None
    try:  # Prefer package import.
        from tools import status_render as sr  # type: ignore  # noqa: F401
    except ImportError:
        try:  # Fallback: file-path import (script context).
            if str(_THIS_DIR) not in sys.path:
                sys.path.insert(0, str(_THIS_DIR))
            import status_render as sr  # type: ignore  # noqa: F401
        except ImportError:
            print(
                "handshake: status_render not importable yet — STATUS.md re-render skipped",
                file=sys.stderr,
            )
            return
    try:
        sr.render_and_write(wiki=wiki)
    except (AttributeError, OSError, ValueError) as exc:
        print(
            f"handshake: status_render.render_and_write failed: {exc} — skipped",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start(
    *,
    lane: str,
    intent: str = "",
    session: str | None = None,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Start-of-session handshake. Returns a dict with the outcome.

    Outcome shape::

        {
            "lane": "claude",
            "session": "mac-12345-1747800000",
            "result": "claimed" | "no_pending" | "refused" | "error",
            "task_id": "t-..." | None,
            "lock_token": "lk-claude-..." | None,
            "scope_paths": [...] | [],
            "greeting": "<agent-facing one-liner>",
            "telegram_nudge": "<operator-facing one-liner>" | None,
            "active_lanes": [{"lane": ..., "tokens": N, "scope_summary": ...}, ...],
        }
    """
    if lane not in KNOWN_LANES:
        raise ValueError(f"lane must be one of {KNOWN_LANES}, got {lane!r}")
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)
    sess = session or session_id()

    # Tag intent into stderr trail (purely informational) so refusal/claim
    # forensic logs can correlate to the operator's stated intent.
    if intent:
        print(f"handshake: lane={lane} session={sess} intent={intent!r}", file=sys.stderr)

    active_lanes = _build_active_lanes(wiki)

    # Look up top-of-queue for this lane.
    try:
        task = _queue_mod.top(lane=lane, wiki=wiki)
    except (OSError, ValueError) as exc:
        result = {
            "lane": lane,
            "session": sess,
            "result": "error",
            "task_id": None,
            "lock_token": None,
            "scope_paths": [],
            "greeting": f"[lane={lane} session={sess}] ERROR reading queue: {exc}",
            "telegram_nudge": None,
            "active_lanes": active_lanes,
        }
        _best_effort_status_render(wiki)
        return result

    if task is None:
        result = {
            "lane": lane,
            "session": sess,
            "result": "no_pending",
            "task_id": None,
            "lock_token": None,
            "scope_paths": [],
            "greeting": (
                f"[lane={lane} session={sess}] Read STATUS.md. "
                f"No pending task for {lane}. Idle."
            ),
            "telegram_nudge": None,
            "active_lanes": active_lanes,
        }
        _best_effort_status_render(wiki)
        return result

    task_id = str(task.get("id") or "")
    title = str(task.get("title") or "")
    scope_paths = list(task.get("scope_paths") or [])
    scope_str = _scope_summary(scope_paths)

    # Step A: acquire lane lock FIRST (lock-then-claim).
    try:
        token = _lane_lock.acquire(
            lane,
            scope_paths,
            ttl_sec=DEFAULT_TTL_SEC,
            session_id=sess,
            wiki=wiki,
            now=moment,
        )
    except (OSError, ValueError) as exc:
        result = {
            "lane": lane,
            "session": sess,
            "result": "error",
            "task_id": task_id,
            "lock_token": None,
            "scope_paths": scope_paths,
            "greeting": (
                f"[lane={lane} session={sess}] ERROR acquiring lane lock: {exc}"
            ),
            "telegram_nudge": None,
            "active_lanes": active_lanes,
        }
        _best_effort_status_render(wiki)
        return result

    if token is None:
        # Conflict — find the offender for a richer refusal message.
        offender = _find_overlap_token(wiki, lane, scope_paths)
        if offender is not None:
            other_lane = offender.get("lane", "?")
            other_token = offender.get("token", "?")
            other_scope = _scope_summary(list(offender.get("scope_paths") or []))
        else:
            other_lane = "?"
            other_token = "?"
            other_scope = "?"
        greeting = (
            f"[lane={lane} session={sess}] REFUSED. {other_lane} holds "
            f"{other_token} scope={other_scope}. My intended scope {scope_str} "
            f"overlaps. Picking next non-overlapping OR waiting."
        )
        result = {
            "lane": lane,
            "session": sess,
            "result": "refused",
            "task_id": task_id,
            "lock_token": None,
            "scope_paths": scope_paths,
            "greeting": greeting,
            "telegram_nudge": f"[handshake-refused] {greeting}",
            "active_lanes": active_lanes,
        }
        _best_effort_status_render(wiki)
        return result

    # Step B: lock acquired. Now claim the task. If we lose the race, release
    # the lock so we don't leave a zombie.
    try:
        claimed = _queue_mod.claim(
            id=task_id,
            session_id=sess,
            wiki=wiki,
            now=moment,
        )
    except (OSError, ValueError) as exc:
        # Release the lock we just acquired — no zombie locks.
        try:
            _lane_lock.release(token, wiki=wiki)
        except (OSError, ValueError):
            pass
        result = {
            "lane": lane,
            "session": sess,
            "result": "error",
            "task_id": task_id,
            "lock_token": None,
            "scope_paths": scope_paths,
            "greeting": (
                f"[lane={lane} session={sess}] ERROR claiming task {task_id}: {exc}"
            ),
            "telegram_nudge": None,
            "active_lanes": active_lanes,
        }
        _best_effort_status_render(wiki)
        return result

    if not claimed:
        # Race: someone else claimed between top() and claim(). Release lock.
        try:
            _lane_lock.release(token, wiki=wiki)
        except (OSError, ValueError) as exc:
            print(
                f"handshake: failed to release lock after claim race: {exc}",
                file=sys.stderr,
            )
        greeting = (
            f"[lane={lane} session={sess}] REFUSED. Race: task {task_id} "
            f'"{title}" was claimed by another session between top() and '
            "claim(). Lock released. Retry."
        )
        # Refresh active lanes after the release so the operator nudge
        # reflects current state.
        active_lanes = _build_active_lanes(wiki)
        result = {
            "lane": lane,
            "session": sess,
            "result": "refused",
            "task_id": task_id,
            "lock_token": None,
            "scope_paths": scope_paths,
            "greeting": greeting,
            "telegram_nudge": f"[handshake-refused] {greeting}",
            "active_lanes": active_lanes,
        }
        _best_effort_status_render(wiki)
        return result

    # Success.
    greeting = (
        f"[lane={lane} session={sess}] Read STATUS.md. Top of {lane} queue: "
        f'{task_id} "{title}". Claiming. Scope: {scope_str}.'
    )
    # Active-lanes summary now includes us; recompute for accuracy.
    active_lanes = _build_active_lanes(wiki)
    result = {
        "lane": lane,
        "session": sess,
        "result": "claimed",
        "task_id": task_id,
        "lock_token": token,
        "scope_paths": scope_paths,
        "greeting": greeting,
        "telegram_nudge": None,
        "active_lanes": active_lanes,
    }
    _best_effort_status_render(wiki)
    return result


def end(
    *,
    lock_token: str | None,
    task_id: str | None,
    wiki: Path | None = None,
) -> dict[str, Any]:
    """End-of-session: release the lane lock.

    Does NOT mark the task done — that's the agent's responsibility (call
    ``queue.done`` only on real completion). This releases the LOCK so the
    next session in this lane can claim. If *lock_token* is None, returns
    ``released_lock=False`` without error.
    """
    wiki = _resolve_wiki(wiki)
    if lock_token is None:
        return {"released_lock": False, "task_id": task_id}
    try:
        released = _lane_lock.release(lock_token, wiki=wiki)
    except (OSError, ValueError) as exc:
        print(f"handshake: release failed: {exc}", file=sys.stderr)
        released = False
    # Best-effort STATUS.md re-render so the operator dashboard reflects the
    # freed slot immediately.
    _best_effort_status_render(wiki)
    return {"released_lock": bool(released), "task_id": task_id}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Session start/end handshake")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start")
    p_start.add_argument("--lane", required=True, choices=KNOWN_LANES)
    p_start.add_argument("--intent", default="")
    p_start.add_argument("--session")
    p_start.add_argument("--json", action="store_true")

    p_end = sub.add_parser("end")
    p_end.add_argument("--lock-token")
    p_end.add_argument("--task-id")

    args = parser.parse_args()
    wiki = default_wiki()

    if args.cmd == "start":
        result = start(
            lane=args.lane,
            intent=args.intent,
            session=args.session,
            wiki=wiki,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(result["greeting"])
            if result.get("telegram_nudge"):
                print(f"[telegram] {result['telegram_nudge']}", file=sys.stderr)
        return 0 if result["result"] in ("claimed", "no_pending") else 1
    if args.cmd == "end":
        result = end(
            lock_token=args.lock_token,
            task_id=args.task_id,
            wiki=wiki,
        )
        print(json.dumps(result))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
