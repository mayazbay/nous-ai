#!/usr/bin/env python3
"""Read-only Todoist Sync API poller."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

import requests

import leader_lease
import log_event


SYNC_URL = "https://api.todoist.com/api/v1/sync"
STATE_ENV = "NOUS_STATE_DIR"
TOKEN_PATH_ENV = "TODOIST_SYNC_TOKEN_PATH"
PENDING_TOKEN_PATH_ENV = "TODOIST_SYNC_PENDING_TOKEN_PATH"
DEFAULT_STATE_DIR = Path("/Users/madia/nous-agaas/state")
DEFAULT_RESOURCE_TYPES = ["items", "projects", "sections", "labels", "notes", "filters"]
METADATA_KEYS = {
    "sync_token",
    "full_sync",
    "full_sync_date_utc",
    "temp_id_mapping",
    "sync_status",
}


class TodoistSyncError(RuntimeError):
    """Raised when read-only sync cannot proceed safely."""


def state_dir() -> Path:
    return Path(os.environ.get(STATE_ENV, str(DEFAULT_STATE_DIR))).expanduser()


def sync_token_path() -> Path:
    return Path(os.environ.get(TOKEN_PATH_ENV, str(state_dir() / "todoist_sync_token"))).expanduser()


def pending_token_path() -> Path:
    return Path(os.environ.get(PENDING_TOKEN_PATH_ENV, str(state_dir() / "todoist_sync_token.pending"))).expanduser()


def load_env_file(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path or not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def token_from_env(env_file: Path | None = None) -> str:
    token = os.environ.get("SATORY_TODOIST_TOKEN") or os.environ.get("TODOIST_API_TOKEN")
    if token:
        return token
    values = load_env_file(env_file)
    token = values.get("SATORY_TODOIST_TOKEN") or values.get("TODOIST_API_TOKEN")
    if token:
        return token
    raise TodoistSyncError("SATORY_TODOIST_TOKEN / TODOIST_API_TOKEN not found")


def read_sync_token(path: Path | None = None) -> str:
    path = path or sync_token_path()
    if not path.exists():
        return "*"
    value = path.read_text(encoding="utf-8").strip()
    return value or "*"


def sync_form(sync_token: str, resource_types: list[str]) -> dict[str, str]:
    return {
        "sync_token": sync_token,
        "resource_types": json.dumps(resource_types, separators=(",", ":")),
    }


def request_sync(api_token: str, sync_token: str, resource_types: list[str]) -> dict[str, Any]:
    response = requests.post(
        SYNC_URL,
        headers={"Authorization": f"Bearer {api_token}"},
        data=sync_form(sync_token, resource_types),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise TodoistSyncError("Todoist sync response was not a JSON object")
    if "sync_token" not in payload:
        raise TodoistSyncError("Todoist sync response missing sync_token")
    return payload


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_pending_token(token: str) -> None:
    write_text_atomic(pending_token_path(), token + "\n")


def commit_pending_token() -> None:
    pending = pending_token_path()
    if not pending.exists():
        return
    token = pending.read_text(encoding="utf-8")
    write_text_atomic(sync_token_path(), token)
    pending.unlink(missing_ok=True)


def iter_deltas(response: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    deltas: list[tuple[str, str, dict[str, Any]]] = []
    for resource, value in response.items():
        if resource in METADATA_KEYS:
            continue
        if isinstance(value, list):
            for idx, item in enumerate(value):
                if not isinstance(item, dict):
                    continue
                external_id = str(item.get("id") or item.get("v2_id") or idx)
                deltas.append((resource, external_id, item))
        elif isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, dict):
                    payload = item
                else:
                    payload = {"value": item}
                deltas.append((resource, str(key), payload))
    return deltas


def log_deltas(response: dict[str, Any], actor: str, correlation_id: str) -> int:
    count = 0
    for resource, external_id, payload in iter_deltas(response):
        event_payload = {
            "resource": resource,
            "delta": payload,
        }
        event_payload["idempotency_key"] = (
            f"todoist-sync:{resource}:{external_id}:{log_event.payload_hash(event_payload)}"
        )
        log_event.append_event(
            "todoist_sync",
            f"{resource}:{external_id}",
            actor,
            event_payload,
            correlation_id,
        )
        count += 1
    return count


def poll_once(
    *,
    api_token: str,
    owner: str,
    resource_types: list[str] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    resource_types = resource_types or DEFAULT_RESOURCE_TYPES
    old_token = read_sync_token()
    response = request_sync(api_token, old_token, resource_types)
    new_token = str(response["sync_token"])
    write_pending_token(new_token)
    events_logged = log_deltas(response, owner, correlation_id or f"todoist-sync:{int(time.time())}")
    commit_pending_token()
    return {
        "old_sync_token": old_token,
        "new_sync_token": new_token,
        "full_sync": bool(response.get("full_sync")),
        "events_logged": events_logged,
    }


def run_due_poll(
    args: argparse.Namespace,
    *,
    api_token: str,
    owner: str,
    resource_types: list[str],
    now: float,
) -> float:
    try:
        result = poll_once(
            api_token=api_token,
            owner=owner,
            resource_types=resource_types,
            correlation_id=f"todoist-sync:{socket.gethostname()}:{int(now)}",
        )
    except requests.RequestException as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": type(exc).__name__,
                    "detail": str(exc)[:500],
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return now + args.error_backoff

    print(json.dumps(result, sort_keys=True), flush=True)
    return now + args.interval


def parse_resource_types(raw: str | None) -> list[str]:
    if not raw:
        return DEFAULT_RESOURCE_TYPES
    raw = raw.strip()
    if raw.startswith("["):
        parsed = json.loads(raw)
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise TodoistSyncError("resource types JSON must be a string array")
        return parsed
    return [part.strip() for part in raw.split(",") if part.strip()]


def run_loop(args: argparse.Namespace) -> int:
    owner = args.owner
    lease = leader_lease.LeaderLease(Path(args.lease_path), args.lease_ttl)
    api_token = token_from_env(Path(args.env_file) if args.env_file else None)
    resource_types = parse_resource_types(args.resource_types)
    next_poll = 0.0
    while True:
        if not lease.try_acquire(owner):
            print(f"standby owner={owner}", flush=True)
            time.sleep(args.standby_poll)
            continue

        now = time.time()
        if now >= next_poll:
            next_poll = run_due_poll(
                args,
                api_token=api_token,
                owner=owner,
                resource_types=resource_types,
                now=now,
            )
        time.sleep(args.lease_refresh_interval)


def run_once(args: argparse.Namespace) -> int:
    owner = args.owner
    lease = leader_lease.LeaderLease(Path(args.lease_path), args.lease_ttl)
    if not lease.try_acquire(owner):
        print(f"standby owner={owner}")
        return 0
    api_token = token_from_env(Path(args.env_file) if args.env_file else None)
    result = poll_once(
        api_token=api_token,
        owner=owner,
        resource_types=parse_resource_types(args.resource_types),
        correlation_id=args.correlation_id,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only Todoist Sync API poller.")
    ap.add_argument("--owner", default=os.environ.get("TODOIST_SYNC_OWNER", socket.gethostname()))
    ap.add_argument("--env-file")
    ap.add_argument("--resource-types", default=os.environ.get("TODOIST_SYNC_RESOURCE_TYPES"))
    ap.add_argument("--lease-path", default=str(leader_lease.lease_path()))
    ap.add_argument("--lease-ttl", type=float, default=90.0)
    ap.add_argument("--lease-refresh-interval", type=float, default=30.0)
    ap.add_argument("--interval", type=float, default=300.0)
    ap.add_argument("--error-backoff", type=float, default=60.0)
    ap.add_argument("--standby-poll", type=float, default=5.0)
    ap.add_argument("--correlation-id", default=None)
    ap.add_argument("--loop", action="store_true")
    args = ap.parse_args(argv)
    if args.loop:
        return run_loop(args)
    return run_once(args)


if __name__ == "__main__":
    sys.exit(main())
