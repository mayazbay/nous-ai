#!/usr/bin/env python3
"""Per-lane heartbeat process — extends lane-lock TTL while the parent agent is alive.

Forked by `/code` / `/codex` / `/grok` session handlers right after the parent
agent acquires its lane locks. Loops every ``--interval-sec`` seconds (default
90s, matching ``lane_lock.DEFAULT_EXTEND_SEC``), heartbeating every active
lock token whose ``session_id`` matches the agent's own session. Exits cleanly
when:

  * the parent process (``--parent-pid``) is no longer alive,
  * SIGTERM / SIGINT is received,
  * ``iterations`` (test mode) is reached.

The daemon ``setsid()``s itself so it survives the parent's controlling tty
closing but still observes the parent's death via ``kill(pid, 0)`` polling.

CLI::

    python3 tools/heartbeat_lane.py --session-id sess-X --parent-pid 12345
    python3 tools/heartbeat_lane.py --session-id sess-X --parent-pid 12345 --interval-sec 90
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path

try:  # pragma: no cover — package vs script-mode dual import
    from tools import lane_lock
except ImportError:
    _THIS_DIR = Path(__file__).resolve().parent
    if str(_THIS_DIR) not in sys.path:
        sys.path.insert(0, str(_THIS_DIR))
    import lane_lock  # type: ignore[no-redef]


DEFAULT_INTERVAL_SEC = 90


def is_alive(pid: int) -> bool:
    """Return True if the given pid is alive on this host.

    ``kill(pid, 0)`` is the POSIX idiom: it sends no signal but raises
    ``ProcessLookupError`` if the pid does not exist (or ``PermissionError``
    if it exists but we cannot signal it — still alive from our viewpoint).
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — still "alive".
        return True
    except OSError:
        return False


def heartbeat_loop(
    *,
    session_id: str,
    parent_pid: int,
    interval_sec: int = DEFAULT_INTERVAL_SEC,
    wiki: Path | None = None,
    iterations: int | None = None,
) -> int:
    """Loop heartbeating tokens owned by *session_id* until parent dies.

    On each cycle:
      1. If parent_pid no longer alive → break.
      2. If a stop signal was received (SIGTERM/SIGINT) → break.
      3. If ``iterations`` (test mode) reached → break.
      4. Otherwise: enumerate all active lane-lock tokens whose
         ``session_id`` matches *session_id*, and call ``lane_lock.heartbeat``
         on each.

    Returns the number of cycles completed.
    """
    wiki = wiki if wiki is not None else lane_lock.default_wiki()
    cycles = 0

    # Graceful shutdown on signals — flip a flag and let the loop exit
    # at the top of its next iteration so the in-flight heartbeat cycle
    # is never half-done.
    stop = {"flag": False}

    def _on_signal(_signum, _frame):  # noqa: ANN001 — signal handler signature
        stop["flag"] = True

    # Best-effort signal install. Some environments (e.g. non-main threads
    # in tests) raise ValueError; ignore so the loop still runs.
    try:
        signal.signal(signal.SIGTERM, _on_signal)
    except (ValueError, OSError):
        pass
    try:
        signal.signal(signal.SIGINT, _on_signal)
    except (ValueError, OSError):
        pass

    while True:
        if stop["flag"]:
            break
        if not is_alive(parent_pid):
            break
        if iterations is not None and cycles >= iterations:
            break

        try:
            active = lane_lock.list_active(wiki=wiki)
        except Exception as exc:  # noqa: BLE001 — fail-soft, keep looping
            print(f"heartbeat_lane: list_active failed: {exc}", file=sys.stderr)
            active = []

        for tok in active:
            if tok.get("session_id") != session_id:
                continue
            try:
                lane_lock.heartbeat(tok["token"], wiki=wiki)
            except Exception as exc:  # noqa: BLE001 — fail-soft per-token
                print(
                    f"heartbeat_lane: heartbeat({tok.get('token')}) failed: {exc}",
                    file=sys.stderr,
                )

        cycles += 1
        if iterations is not None and cycles >= iterations:
            break
        time.sleep(interval_sec)

    return cycles


def main() -> int:
    parser = argparse.ArgumentParser(description="Lane heartbeat daemon")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--interval-sec", type=int, default=DEFAULT_INTERVAL_SEC)
    parser.add_argument("--wiki", type=Path, default=None)
    args = parser.parse_args()

    # Detach into our own session so the parent's controlling terminal
    # closing (e.g. ssh disconnect) doesn't kill the heartbeat process.
    # Best-effort: fails harmlessly if we're already a session leader.
    try:
        os.setsid()
    except (OSError, PermissionError):
        pass

    heartbeat_loop(
        session_id=args.session_id,
        parent_pid=args.parent_pid,
        interval_sec=args.interval_sec,
        wiki=args.wiki,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
