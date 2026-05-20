#!/usr/bin/env python3
"""Status daemon: re-render STATUS.md every 30s + reap stale lane locks.

Designed for launchd (``com.nous.status-daemon.plist`` at
``~/Library/LaunchAgents/``). On macOS, launchd handles restart-on-failure
and the 30s scheduling — this script just runs ONE pass and exits, so
``StartInterval=30`` re-fires it every 30s. ``--loop`` is available for
non-launchd environments (manual run, systemd, foreground debugging).

Each pass does two things:

  1. ``lane_lock.reap_stale`` — drop expired tokens (the lock-then-claim
     handshake relies on stale locks not blocking new claims indefinitely).
  2. ``status_render.render_and_write`` — atomic rewrite of STATUS.md.

CLI::

    python3 tools/status_daemon.py                 # single pass, prints JSON, exits
    python3 tools/status_daemon.py --loop          # foreground loop (non-launchd)
    python3 tools/status_daemon.py --wiki <path>   # override wiki root
"""

from __future__ import annotations

import argparse
import json
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

try:  # pragma: no cover — package vs script-mode dual import
    from tools import status_render
except ImportError:
    _THIS_DIR = Path(__file__).resolve().parent
    if str(_THIS_DIR) not in sys.path:
        sys.path.insert(0, str(_THIS_DIR))
    import status_render  # type: ignore[no-redef]


def run_pass(wiki: Path) -> dict:
    """One pass: reap stale lane locks, then render STATUS.md.

    Returns a dict with two keys:
      * ``reaped``: list of token strings released by ``reap_stale``.
      * ``status_written``: absolute path to STATUS.md as a string.
    """
    reaped = lane_lock.reap_stale(wiki=wiki)
    path = status_render.render_and_write(wiki=wiki)
    return {"reaped": list(reaped), "status_written": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Status daemon — one pass (launchd) or --loop (manual)",
    )
    parser.add_argument("--wiki", type=Path, default=None)
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop forever (vs single pass for launchd)",
    )
    parser.add_argument("--interval-sec", type=int, default=30)
    args = parser.parse_args()
    wiki = args.wiki if args.wiki is not None else lane_lock.default_wiki()

    if args.loop:
        while True:
            try:
                result = run_pass(wiki)
                print(json.dumps(result))
                sys.stdout.flush()
            except Exception as exc:  # noqa: BLE001 — fail-soft; log + keep looping
                print(f"status_daemon: {exc}", file=sys.stderr)
            time.sleep(args.interval_sec)
        # unreachable; here for completeness
        return 0  # pragma: no cover
    else:
        result = run_pass(wiki)
        print(json.dumps(result))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
