#!/usr/bin/env python3
"""File-backed leader lease for active/passive pollers."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import socket
import sys
import time
from pathlib import Path
from typing import Any


LEASE_ENV = "NOUS_LEADER_LOCK_PATH"
DEFAULT_LEASE_PATH = Path("/Users/madia/nous-agaas/state/leader.lock")
DEFAULT_TTL_S = 90.0
DEFAULT_REFRESH_S = 30.0


class LeaseError(RuntimeError):
    """Raised when the lease file is malformed or cannot be updated."""


class LeaderLease:
    def __init__(self, path: Path | None = None, ttl_s: float = DEFAULT_TTL_S) -> None:
        self.path = path or lease_path()
        self.ttl_s = float(ttl_s)

    def try_acquire(self, owner: str) -> bool:
        _validate_owner(owner)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        with self.path.open("a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            fh.seek(0)
            current = _load_record(fh.read())
            if current and current.get("owner") != owner and not _expired(current, now):
                return False
            record = _new_record(owner, now, self.ttl_s)
            _write_record(fh, record)
            return True

    def refresh(self, owner: str) -> bool:
        return self.try_acquire(owner)

    def read(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            return _load_record(fh.read())

    def is_leader(self, owner: str) -> bool:
        record = self.read()
        return bool(record and record.get("owner") == owner and not _expired(record, time.time()))


def lease_path() -> Path:
    return Path(os.environ.get(LEASE_ENV, str(DEFAULT_LEASE_PATH))).expanduser()


def default_owner() -> str:
    return os.environ.get("NOUS_LEADER_OWNER") or socket.gethostname()


def _validate_owner(owner: str) -> None:
    if not isinstance(owner, str) or not owner.strip():
        raise LeaseError("owner must be a non-empty string")


def _load_record(raw: str) -> dict[str, Any] | None:
    if not raw.strip():
        return None
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LeaseError(f"malformed leader lease: {exc}") from exc
    if not isinstance(record, dict):
        raise LeaseError("malformed leader lease: not an object")
    for key in ("owner", "expires_at"):
        if key not in record:
            raise LeaseError(f"malformed leader lease: missing {key}")
    return record


def _expired(record: dict[str, Any], now: float) -> bool:
    try:
        return float(record["expires_at"]) <= now
    except (TypeError, ValueError) as exc:
        raise LeaseError("malformed leader lease: expires_at is not numeric") from exc


def _new_record(owner: str, now: float, ttl_s: float) -> dict[str, Any]:
    return {
        "owner": owner,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "acquired_at": now,
        "refreshed_at": now,
        "expires_at": now + ttl_s,
        "ttl_s": ttl_s,
    }


def _write_record(fh: Any, record: dict[str, Any]) -> None:
    fh.seek(0)
    fh.truncate()
    fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    fh.flush()
    os.fsync(fh.fileno())


def cmd_try_acquire(args: argparse.Namespace) -> int:
    lease = LeaderLease(Path(args.lease_path), args.ttl)
    ok = lease.try_acquire(args.owner)
    print(f"acquired={ok} owner={args.owner}")
    return 0 if ok else 1


def cmd_status(args: argparse.Namespace) -> int:
    lease = LeaderLease(Path(args.lease_path), args.ttl)
    record = lease.read()
    print(json.dumps(record or {}, sort_keys=True))
    return 0


def cmd_hold(args: argparse.Namespace) -> int:
    lease = LeaderLease(Path(args.lease_path), args.ttl)
    if not lease.try_acquire(args.owner):
        print(f"acquired=False owner={args.owner}")
        return 1
    print(f"acquired=True owner={args.owner}", flush=True)
    alive = True

    def stop(_signum, _frame):
        nonlocal alive
        alive = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while alive:
        time.sleep(args.refresh_interval)
        if alive:
            lease.refresh(args.owner)
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    lease = LeaderLease(Path(args.lease_path), args.ttl)
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if lease.try_acquire(args.owner):
            print(f"acquired=True owner={args.owner}")
            return 0
        time.sleep(args.poll)
    print(f"acquired=False owner={args.owner}")
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="File-backed leader lease.")
    ap.add_argument("--lease-path", default=str(lease_path()))
    ap.add_argument("--ttl", type=float, default=DEFAULT_TTL_S)
    sub = ap.add_subparsers(dest="command", required=True)

    acquire = sub.add_parser("try-acquire")
    acquire.add_argument("--owner", default=default_owner())
    acquire.set_defaults(func=cmd_try_acquire)

    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)

    hold = sub.add_parser("hold")
    hold.add_argument("--owner", default=default_owner())
    hold.add_argument("--refresh-interval", type=float, default=DEFAULT_REFRESH_S)
    hold.set_defaults(func=cmd_hold)

    wait = sub.add_parser("wait")
    wait.add_argument("--owner", default=default_owner())
    wait.add_argument("--timeout", type=float, default=DEFAULT_TTL_S + 5)
    wait.add_argument("--poll", type=float, default=1.0)
    wait.set_defaults(func=cmd_wait)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
