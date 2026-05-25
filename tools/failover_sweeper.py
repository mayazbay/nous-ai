#!/usr/bin/env python3
"""Failover sweeper — materialize orphans + retry WAL pushes (Ship 1 Step 5).

Two idempotent jobs:

  1. Orphan materialization: scan the ledger via mfs.find_orphans(wiki). For each
     orphan, append a synthetic finished row via mfs._mutate_state so the normal
     fcntl lock + WAL + commit discipline runs. The synthetic row carries
     status='abandoned' and abandonment_reason='orphan_timeout'. Once a finished
     row exists, find_orphans no longer returns the event — so re-running yields
     an empty list.

  2. WAL push retry: read logs/model-failover.wal. Group rows by mutation_seq.
     For each group where the latest row has pushed=false AND age > 60s, run
     `git push origin main`. On success, append a follow-up WAL row with
     pushed=true. Skip mutation_seqs whose latest row is already pushed=true.

Both are fail-soft: subprocess failures log to stderr and return; the sweeper
never raises. Safe to run on a timer (launchd, cron, watchdog) — repeated runs
are no-ops once state has converged.

Plan §4.5 (god-tier failover plan).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from tools import model_failover_state as mfs  # when imported as a package
except ImportError:  # pragma: no cover - exercised when invoked from tools/ dir directly
    import model_failover_state as mfs  # type: ignore[no-redef]


WAL_PUSH_RETRY_TIMEOUT_SEC = 60


def _now(now: dt.datetime | None) -> dt.datetime:
    return now if now is not None else mfs.now_kzt()


def sweep_orphans(wiki: Path, *, now: dt.datetime | None = None) -> list[str]:
    """Find orphans via mfs.find_orphans; append synthetic finished rows.

    For each orphan, writes a row with phase='finished', status='abandoned',
    abandonment_reason='orphan_timeout' via mfs._mutate_state — which runs the
    normal lock + WAL + ledger + render + commit/push flow.

    Returns the list of event_ids that were materialized this call. Idempotent:
    once a finished row pairs the started row, find_orphans skips it on the
    next call.
    """
    wiki = Path(wiki)
    now_dt = _now(now)

    try:
        orphans = mfs.find_orphans(wiki, now=now_dt)
    except Exception as exc:  # pragma: no cover - find_orphans is robust
        print(f"failover_sweeper: find_orphans failed: {exc}", file=sys.stderr)
        return []

    materialized: list[str] = []
    for orphan in orphans:
        event_id = orphan.get("event_id", "")
        if not event_id:
            continue
        try:
            git_head = mfs.git_head(wiki)
        except Exception as exc:  # pragma: no cover
            print(
                f"failover_sweeper: git_head probe failed for {event_id}: {exc}",
                file=sys.stderr,
            )
            git_head = ""

        row: dict[str, Any] = {
            "event_id": event_id,
            "phase": "finished",
            "status": "abandoned",
            "ts": now_dt.isoformat(),
            "response_head": "",
            "receipt": "",
            "git_head": git_head,
            "abandonment_reason": "orphan_timeout",
        }
        try:
            mfs._mutate_state(wiki, row, commit=None)
        except Exception as exc:
            print(
                f"failover_sweeper: _mutate_state failed for orphan {event_id}: {exc}",
                file=sys.stderr,
            )
            continue
        materialized.append(event_id)

    return materialized


def _read_wal_rows(wiki: Path) -> list[dict[str, Any]]:
    """Read logs/model-failover.wal as a list of row dicts. Skips malformed lines.

    Preserves file order (lower index = earlier row).
    """
    path = wiki / mfs.WAL_REL
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"failover_sweeper: WAL read failed: {exc}", file=sys.stderr)
        return []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            print(
                f"failover_sweeper: WAL line {lineno} malformed, skipping: {exc}",
                file=sys.stderr,
            )
            continue
        if not isinstance(row, dict):
            print(
                f"failover_sweeper: WAL line {lineno} not an object, skipping",
                file=sys.stderr,
            )
            continue
        rows.append(row)
    return rows


def _parse_wal_ts(ts_str: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(ts_str)
    except (TypeError, ValueError):
        return None


def _git_push(wiki: Path) -> int:
    """Run `git push origin main`. Fail-soft: returns non-zero on any failure.

    Indirected so tests can monkeypatch a single function instead of subprocess.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(wiki), "push", "origin", "main"],
            capture_output=True,
            timeout=45,
        )
        return proc.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"failover_sweeper: git push failed: {exc}", file=sys.stderr)
        return 1


def sweep_wal_push(wiki: Path, *, now: dt.datetime | None = None) -> list[int]:
    """Retry git push for WAL mutation_seqs whose latest row is pushed=false AND age > 60s.

    Reads logs/model-failover.wal, groups by mutation_seq, keeps the LATEST row
    per seq (highest position in file). If latest.pushed is False and
    (now - latest.ts) > WAL_PUSH_RETRY_TIMEOUT_SEC, runs git push origin main.
    On success, appends a new WAL row {mutation_seq, event_id, ts: now,
    pushed: true}.

    Returns list of mutation_seqs that were successfully pushed this call.
    Skips mutation_seqs where the latest row is already pushed=true (idempotent).
    """
    wiki = Path(wiki)
    now_dt = _now(now)

    rows = _read_wal_rows(wiki)
    if not rows:
        return []

    # Group: mutation_seq → latest row (highest position wins).
    latest_by_seq: dict[int, dict[str, Any]] = {}
    for row in rows:
        seq = row.get("mutation_seq")
        if not isinstance(seq, int):
            continue
        latest_by_seq[seq] = row  # later overwrites earlier — file-order = chronology

    pushed_seqs: list[int] = []
    for seq in sorted(latest_by_seq.keys()):
        latest = latest_by_seq[seq]
        if latest.get("pushed") is True:
            continue  # already pushed — idempotent skip
        # Even if pushed isn't strictly False, treat anything not True as needs-retry.
        ts_str = latest.get("ts", "")
        ts = _parse_wal_ts(ts_str) if isinstance(ts_str, str) else None
        if ts is None:
            print(
                f"failover_sweeper: WAL seq {seq} has unparseable ts {ts_str!r}, skipping",
                file=sys.stderr,
            )
            continue
        age = (now_dt - ts).total_seconds()
        if age <= WAL_PUSH_RETRY_TIMEOUT_SEC:
            continue  # too young — give the original mutator a chance to finish

        rc = _git_push(wiki)
        if rc != 0:
            print(
                f"failover_sweeper: push retry rc={rc} for mutation_seq={seq}, will retry next sweep",
                file=sys.stderr,
            )
            continue

        # Push succeeded — append a follow-up WAL row marking it pushed.
        event_id = latest.get("event_id", "")
        if not isinstance(event_id, str):
            event_id = str(event_id)
        try:
            mfs._append_wal(wiki, seq, event_id, pushed=True)
        except Exception as exc:
            # Push happened but we couldn't record it — next sweep will see the
            # remote is up-to-date but try again. Acceptable; surface the failure.
            print(
                f"failover_sweeper: pushed seq={seq} but WAL append failed: {exc}",
                file=sys.stderr,
            )
            continue
        pushed_seqs.append(seq)

    return pushed_seqs


def sweep_all(wiki: Path, *, now: dt.datetime | None = None) -> dict[str, list]:
    """Run both sweep_orphans and sweep_wal_push. Returns {'orphans': [...], 'pushed': [...]}."""
    return {
        "orphans": sweep_orphans(wiki, now=now),
        "pushed": sweep_wal_push(wiki, now=now),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Failover sweeper: materialize orphans + retry WAL pushes",
    )
    parser.add_argument("--wiki", type=Path, default=mfs.default_wiki())
    parser.add_argument("--once", action="store_true", help="Run one pass and exit (default)")
    parser.add_argument("--orphans-only", action="store_true")
    parser.add_argument("--push-only", action="store_true")
    args = parser.parse_args()

    if args.orphans_only:
        result: dict[str, list] = {"orphans": sweep_orphans(args.wiki), "pushed": []}
    elif args.push_only:
        result = {"orphans": [], "pushed": sweep_wal_push(args.wiki)}
    else:
        result = sweep_all(args.wiki)

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
