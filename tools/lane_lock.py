"""Lane lock primitive — fcntl advisory locks for cross-agent coordination.

Used by queue.py, pre_commit_lane_check, and handshake to prevent concurrent
agents from stepping on each other's work. State is stored at
``pages/systems/lane-locks.json`` with an append-only history at
``pages/systems/lane-locks.history.jsonl``. All mutations are serialized
through an fcntl ``LOCK_EX`` on ``logs/lane-locks-state.lock`` and committed
via atomic temp+rename.

CLI:
    python3 tools/lane_lock.py acquire --lane claude --scope tools/x.py
    python3 tools/lane_lock.py heartbeat --token lk-claude-...
    python3 tools/lane_lock.py release --token lk-claude-...
    python3 tools/lane_lock.py list-active [--lane claude] [--json]
    python3 tools/lane_lock.py match --path tools/x.py --lane codex
    python3 tools/lane_lock.py reap-stale
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import fnmatch
import json
import os
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

ALMATY = dt.timezone(dt.timedelta(hours=5))
LOCKS_REL = Path("pages/systems/lane-locks.json")
HISTORY_REL = Path("pages/systems/lane-locks.history.jsonl")
LOCKS_STATE_LOCK_REL = Path("logs/lane-locks-state.lock")  # fcntl lock for state file
DEFAULT_TTL_SEC = 300         # 5 min
DEFAULT_EXTEND_SEC = 90       # heartbeat refresh window
KNOWN_LANES = ("claude", "codex", "grok", "opus")


# ---------------------------------------------------------------------------
# Path resolution helpers
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


def _locks_path(wiki: Path) -> Path:
    return wiki / LOCKS_REL


def _history_path(wiki: Path) -> Path:
    return wiki / HISTORY_REL


def _state_lock_path(wiki: Path) -> Path:
    return wiki / LOCKS_STATE_LOCK_REL


# ---------------------------------------------------------------------------
# Glob / scope rules
# ---------------------------------------------------------------------------

def _normalize(p: str) -> str:
    """Drop trailing slashes; collapse repeated slashes."""
    while "//" in p:
        p = p.replace("//", "/")
    return p.rstrip("/")


# Roots whose ``/*`` glob is interpreted as single-segment (narrow code scope).
# Everything else with a ``/*`` suffix is treated as a dir-prefix (broad data
# scope) — e.g. ``tenants/satory/*`` covers the whole satory subtree, while
# ``tools/*`` covers just the files directly inside ``tools/``.
_NARROW_SINGLE_SEGMENT_ROOTS = ("tools", "agents", "tests", "tools/tests")


def _is_narrow_root(prefix: str) -> bool:
    return prefix in _NARROW_SINGLE_SEGMENT_ROOTS


def scope_matches(staged_path: str, locked_globs: list[str]) -> bool:
    """Check if a staged file path matches ANY of the locked glob patterns.

    Rules:
      - ``tools/*`` matches ``tools/x.py`` (single segment) but NOT ``tools/sub/x.py``.
      - ``tools/**`` matches recursively (any depth).
      - ``tenants/satory/*`` is dir-prefix: matches ``tenants/satory/anything/under``.
      - Exact path also matches itself.
    """
    staged = _normalize(staged_path)
    for raw in locked_globs:
        glob = _normalize(raw)
        if not glob:
            continue
        # Recursive: tools/**  -> anything under tools/ at any depth
        if glob.endswith("/**"):
            prefix = glob[:-3]  # drop '/**'
            if not prefix:
                return True
            if staged == prefix or staged.startswith(prefix + "/"):
                return True
            continue
        # /* suffix: narrow (single-segment) for code roots, dir-prefix elsewhere.
        if glob.endswith("/*"):
            prefix = glob[:-2]
            if not prefix:
                if "/" not in staged:
                    return True
                continue
            if staged.startswith(prefix + "/") or staged == prefix:
                if _is_narrow_root(prefix):
                    tail = staged[len(prefix) + 1:] if staged != prefix else ""
                    if tail and "/" not in tail:
                        return True
                else:
                    # dir-prefix style — any depth under prefix matches.
                    return True
            continue
        # No glob chars: treat as exact OR dir-prefix
        if "*" not in glob and "?" not in glob and "[" not in glob:
            if staged == glob:
                return True
            if staged.startswith(glob + "/"):
                return True
            continue
        # Anything else: fall back to fnmatch
        if fnmatch.fnmatchcase(staged, glob):
            return True
    return False


def _glob_to_prefix(glob: str) -> tuple[str, str]:
    """Return (prefix, kind) where kind is 'exact', 'single', 'recursive'."""
    g = _normalize(glob)
    if g.endswith("/**"):
        return g[:-3], "recursive"
    if g.endswith("/*"):
        return g[:-2], "single"
    if "*" not in g and "?" not in g and "[" not in g:
        return g, "exact"
    # Generic fallback — treat the part before the first wildcard as a prefix.
    head = g
    for ch in ("*", "?", "["):
        idx = head.find(ch)
        if idx != -1:
            head = head[:idx]
    head = head.rstrip("/")
    return head, "single"


def _patterns_overlap(a: str, b: str) -> bool:
    """Return True if globs *a* and *b* could possibly select an overlapping path."""
    # Cheap symmetric check: does either glob match the other's prefix or vice versa?
    pa, ka = _glob_to_prefix(a)
    pb, kb = _glob_to_prefix(b)

    # Equal prefixes always overlap (e.g. tools/* vs tools/**, tools/foo.py vs tools/foo.py).
    if pa == pb:
        return True

    # Recursive cone vs anything underneath.
    if ka == "recursive" and (pb == pa or pb.startswith(pa + "/")):
        return True
    if kb == "recursive" and (pa == pb or pa.startswith(pb + "/")):
        return True

    # Single-segment glob vs exact path sitting directly inside its prefix.
    if ka == "single" and kb == "exact":
        if pb.startswith(pa + "/"):
            tail = pb[len(pa) + 1:]
            if tail and "/" not in tail:
                return True
    if kb == "single" and ka == "exact":
        if pa.startswith(pb + "/"):
            tail = pa[len(pb) + 1:]
            if tail and "/" not in tail:
                return True

    # Exact-vs-exact already handled by equality.
    # Exact-vs-exact-prefix (dir-prefix style): if one exact path is a parent dir of another.
    if ka == "exact" and kb == "exact":
        if pa.startswith(pb + "/") or pb.startswith(pa + "/"):
            return True

    # Single-vs-single with one prefix containing the other: e.g. tools/* and tools/sub/*
    # — these do NOT overlap (single-segment scope). Skip.

    # Concrete cross-check via scope_matches.
    if scope_matches(pb, [a]) or scope_matches(pa, [b]):
        return True
    return False


def overlap(scope_a: list[str], scope_b: list[str]) -> list[str]:
    """Return overlapping path patterns from *scope_a* that intersect *scope_b*."""
    hits: list[str] = []
    for pat_a in scope_a:
        for pat_b in scope_b:
            if _patterns_overlap(pat_a, pat_b):
                hits.append(pat_a)
                break
    return hits


# ---------------------------------------------------------------------------
# State / history IO
# ---------------------------------------------------------------------------

def _ensure_dirs(wiki: Path) -> None:
    _locks_path(wiki).parent.mkdir(parents=True, exist_ok=True)
    _history_path(wiki).parent.mkdir(parents=True, exist_ok=True)
    _state_lock_path(wiki).parent.mkdir(parents=True, exist_ok=True)


def _read_locks_state(wiki: Path) -> dict[str, Any]:
    """Read pages/systems/lane-locks.json. Returns {} if missing or malformed."""
    path = _locks_path(wiki)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"version": 1, "tokens": {}}
    except OSError:
        return {"version": 1, "tokens": {}}
    if not raw.strip():
        return {"version": 1, "tokens": {}}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"version": 1, "tokens": {}}
    if not isinstance(data, dict):
        return {"version": 1, "tokens": {}}
    data.setdefault("version", 1)
    tokens = data.get("tokens")
    if not isinstance(tokens, dict):
        data["tokens"] = {}
    return data


def _write_locks_state_atomic(wiki: Path, state: dict[str, Any]) -> None:
    """Atomic write: write to .tmp + os.rename. Caller must hold the state lock."""
    _ensure_dirs(wiki)
    path = _locks_path(wiki)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.rename(tmp, path)


def _append_history(wiki: Path, event: dict[str, Any]) -> None:
    """Append-only event log: pages/systems/lane-locks.history.jsonl."""
    _ensure_dirs(wiki)
    path = _history_path(wiki)
    line = json.dumps(event, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


@contextlib.contextmanager
def _with_state_lock(wiki: Path) -> Iterator[None]:
    """Context manager that takes fcntl.LOCK_EX on logs/lane-locks-state.lock."""
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
# Token helpers
# ---------------------------------------------------------------------------

def _parse_iso(s: str) -> dt.datetime:
    """Parse an ISO-8601 string with timezone, normalised to ALMATY."""
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=ALMATY)
    return d


def _default_session_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}-{int(time.time())}"


def _new_token(lane: str, now: dt.datetime) -> str:
    return f"lk-{lane}-{uuid.uuid4().hex[:8]}-{int(now.timestamp())}"


def _reap_inside_lock(
    state: dict[str, Any],
    wiki: Path,
    now: dt.datetime,
) -> list[str]:
    """Drop expired tokens from *state* (mutates in place). Returns released tokens.

    Writes one ``reaped_stale`` history event per token. Caller must hold the
    state lock and is responsible for persisting *state*.
    """
    tokens: dict[str, Any] = state.get("tokens", {})
    released: list[str] = []
    for tok, info in list(tokens.items()):
        try:
            exp = _parse_iso(info["expires_at"])
        except (KeyError, TypeError, ValueError):
            # Malformed entry — drop it.
            del tokens[tok]
            released.append(tok)
            _append_history(wiki, {
                "event": "reaped_stale",
                "token": tok,
                "ts": now.isoformat(),
                "reason": "malformed",
            })
            continue
        if exp <= now:
            del tokens[tok]
            released.append(tok)
            _append_history(wiki, {
                "event": "reaped_stale",
                "token": tok,
                "ts": now.isoformat(),
                "reason": "ttl_expired",
            })
    return released


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def acquire(
    lane: str,
    scope_paths: list[str],
    *,
    ttl_sec: int = DEFAULT_TTL_SEC,
    session_id: str | None = None,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> str | None:
    """Try to acquire a lane lock. Returns token string on success, None on conflict."""
    if not scope_paths:
        raise ValueError("scope_paths must be non-empty")
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)
    session = session_id or _default_session_id()
    expires = moment + dt.timedelta(seconds=ttl_sec)

    with _with_state_lock(wiki):
        state = _read_locks_state(wiki)
        _reap_inside_lock(state, wiki, moment)
        tokens: dict[str, Any] = state.setdefault("tokens", {})

        # Conflict check: any other lane holding an overlapping scope?
        for tok, info in tokens.items():
            if info.get("lane") == lane:
                continue
            existing_scope = list(info.get("scope_paths", []))
            hits = overlap(scope_paths, existing_scope)
            if hits:
                _append_history(wiki, {
                    "event": "conflict",
                    "requesting_lane": lane,
                    "requesting_scope": list(scope_paths),
                    "existing_token": tok,
                    "existing_lane": info.get("lane"),
                    "existing_scope": existing_scope,
                    "overlap": hits,
                    "ts": moment.isoformat(),
                })
                # Persist any reaped-stale changes even on conflict.
                _write_locks_state_atomic(wiki, state)
                return None

        token = _new_token(lane, moment)
        # Ensure uniqueness (paranoia — uuid4 collisions are astronomically unlikely).
        while token in tokens:
            token = _new_token(lane, moment)
        tokens[token] = {
            "lane": lane,
            "scope_paths": list(scope_paths),
            "session_id": session,
            "acquired_at": moment.isoformat(),
            "expires_at": expires.isoformat(),
            "ttl_sec": int(ttl_sec),
        }
        _write_locks_state_atomic(wiki, state)
        _append_history(wiki, {
            "event": "acquired",
            "token": token,
            "lane": lane,
            "scope_paths": list(scope_paths),
            "session_id": session,
            "ts": moment.isoformat(),
            "ttl_sec": int(ttl_sec),
        })
        return token


def heartbeat(
    token: str,
    *,
    extend_sec: int = DEFAULT_EXTEND_SEC,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> bool:
    """Extend a held token's expiry by *extend_sec* from now."""
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        state = _read_locks_state(wiki)
        tokens: dict[str, Any] = state.get("tokens", {})
        info = tokens.get(token)
        if info is None:
            return False
        try:
            exp = _parse_iso(info["expires_at"])
        except (KeyError, ValueError, TypeError):
            return False
        if exp <= moment:
            # Already expired — reap and refuse.
            del tokens[token]
            _append_history(wiki, {
                "event": "reaped_stale",
                "token": token,
                "ts": moment.isoformat(),
                "reason": "ttl_expired_on_heartbeat",
            })
            _write_locks_state_atomic(wiki, state)
            return False
        new_expires = moment + dt.timedelta(seconds=extend_sec)
        info["expires_at"] = new_expires.isoformat()
        _write_locks_state_atomic(wiki, state)
        _append_history(wiki, {
            "event": "heartbeat",
            "token": token,
            "ts": moment.isoformat(),
            "new_expires_at": new_expires.isoformat(),
        })
        return True


def release(token: str, *, wiki: Path | None = None) -> bool:
    """Release a token. Returns True if it was active."""
    wiki = _resolve_wiki(wiki)
    moment = now_kzt()
    with _with_state_lock(wiki):
        state = _read_locks_state(wiki)
        tokens: dict[str, Any] = state.get("tokens", {})
        if token not in tokens:
            return False
        del tokens[token]
        _write_locks_state_atomic(wiki, state)
        _append_history(wiki, {
            "event": "released",
            "token": token,
            "ts": moment.isoformat(),
            "reason": "manual",
        })
        return True


def list_active(
    *,
    wiki: Path | None = None,
    lane: str | None = None,
    now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """List active (unexpired) lock tokens. Optionally filter by lane."""
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        state = _read_locks_state(wiki)
        released = _reap_inside_lock(state, wiki, moment)
        if released:
            _write_locks_state_atomic(wiki, state)
        tokens: dict[str, Any] = state.get("tokens", {})
        entries: list[dict[str, Any]] = []
        for tok, info in tokens.items():
            if lane is not None and info.get("lane") != lane:
                continue
            entries.append({
                "token": tok,
                "lane": info.get("lane"),
                "scope_paths": list(info.get("scope_paths", [])),
                "session_id": info.get("session_id"),
                "acquired_at": info.get("acquired_at"),
                "expires_at": info.get("expires_at"),
                "ttl_sec": info.get("ttl_sec"),
            })
    entries.sort(key=lambda e: e.get("acquired_at") or "")
    return entries


def reap_stale(
    *,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> list[str]:
    """Release all expired tokens. Returns list of released token strings."""
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_state_lock(wiki):
        state = _read_locks_state(wiki)
        released = _reap_inside_lock(state, wiki, moment)
        if released:
            _write_locks_state_atomic(wiki, state)
    return released


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Lane lock CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_acquire = sub.add_parser("acquire")
    p_acquire.add_argument("--lane", required=True, choices=KNOWN_LANES)
    p_acquire.add_argument(
        "--scope",
        action="append",
        required=True,
        help="Repeat for multiple scope paths/globs",
    )
    p_acquire.add_argument("--ttl-sec", type=int, default=DEFAULT_TTL_SEC)
    p_acquire.add_argument("--session-id")

    p_heartbeat = sub.add_parser("heartbeat")
    p_heartbeat.add_argument("--token", required=True)
    p_heartbeat.add_argument("--extend-sec", type=int, default=DEFAULT_EXTEND_SEC)

    p_release = sub.add_parser("release")
    p_release.add_argument("--token", required=True)

    p_list = sub.add_parser("list-active")
    p_list.add_argument("--lane", choices=KNOWN_LANES)
    p_list.add_argument("--json", action="store_true")

    p_match = sub.add_parser("match")
    p_match.add_argument("--path", required=True)
    p_match.add_argument("--lane", required=True, choices=KNOWN_LANES)
    p_match.add_argument("--quiet", action="store_true")

    sub.add_parser("reap-stale")

    args = parser.parse_args()
    wiki = default_wiki()

    if args.cmd == "acquire":
        tok = acquire(
            args.lane,
            args.scope,
            ttl_sec=args.ttl_sec,
            session_id=args.session_id,
            wiki=wiki,
        )
        if tok is None:
            print("CONFLICT", file=sys.stderr)
            return 1
        print(tok)
        return 0
    if args.cmd == "heartbeat":
        ok = heartbeat(args.token, extend_sec=args.extend_sec, wiki=wiki)
        return 0 if ok else 1
    if args.cmd == "release":
        ok = release(args.token, wiki=wiki)
        return 0 if ok else 1
    if args.cmd == "list-active":
        active = list_active(wiki=wiki, lane=args.lane)
        if args.json:
            print(json.dumps(active, ensure_ascii=False))
        else:
            for entry in active:
                print(
                    f"{entry['token']}  lane={entry['lane']}  "
                    f"scope={','.join(entry['scope_paths'])}  "
                    f"expires={entry['expires_at']}"
                )
        return 0
    if args.cmd == "match":
        active = list_active(wiki=wiki, lane=args.lane)
        for entry in active:
            if scope_matches(args.path, entry["scope_paths"]):
                if not args.quiet:
                    print(f"MATCH token={entry['token']}")
                return 0
        if not args.quiet:
            print(
                f"NO MATCH for path={args.path} lane={args.lane}",
                file=sys.stderr,
            )
        return 1
    if args.cmd == "reap-stale":
        released = reap_stale(wiki=wiki)
        print(json.dumps(released))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
