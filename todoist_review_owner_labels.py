#!/usr/bin/env python3
"""Read-only review of Satory Todoist tasks missing an owner signal.

Usage:
  python3 tools/todoist_review_owner_labels.py [--env-file .env]

Prints a table of active tasks without owner:*, assignee:*, or исполнитель:* labels
and without an assignee_id. No writes are made.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

TODOIST_BASE = "https://api.todoist.com/api/v1"
ALLOWED_PROJECT_ID = "6gJ5j8PRVVCWpgCq"
OWNER_LABEL_PREFIXES = ("исполнитель:", "owner:", "assignee:")


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def get_token(env_file: Path) -> str:
    env = {**load_env_file(env_file), **os.environ}
    token = env.get("SATORY_TODOIST_TOKEN") or env.get("TODOIST_API_TOKEN")
    if not token:
        raise RuntimeError("SATORY_TODOIST_TOKEN / TODOIST_API_TOKEN not found")
    return token


def get_tasks(token: str, project_id: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    tasks: list[dict] = []
    cursor = None
    while True:
        params: dict = {"project_id": project_id}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{TODOIST_BASE}/tasks", headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        tasks.extend(data.get("results", []))
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return tasks


def has_owner(task: dict) -> bool:
    if task.get("assignee_id") or task.get("responsible_uid"):
        return True
    labels = task.get("labels") or []
    return any(str(label).startswith(OWNER_LABEL_PREFIXES) for label in labels)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("/Users/madia/Documents/Projects/Nous AGaaS/.env"),
    )
    parser.add_argument(
        "--alt-env",
        type=Path,
        default=Path.home() / "nous-agaas" / ".env",
        help="Fallback env file (Air-side .env synced to Mac)",
    )
    args = parser.parse_args(argv)

    candidates = [args.env_file, args.alt_env]
    token = None
    env_file_used = None
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            token = get_token(candidate)
            env_file_used = candidate
            break
        except RuntimeError:
            continue
    if not token:
        print(f"ERROR: no Todoist token found in any of: {candidates}", file=sys.stderr)
        return 1

    print(f"Token loaded from {env_file_used}")
    print(f"Fetching tasks from project {ALLOWED_PROJECT_ID}...")

    try:
        tasks = get_tasks(token, ALLOWED_PROJECT_ID)
    except requests.HTTPError as e:
        print(f"ERROR fetching tasks: {e}", file=sys.stderr)
        return 1

    missing = [t for t in tasks if not has_owner(t)]
    print(f"\nTotal active tasks: {len(tasks)}")
    print(f"Tasks missing owner signal: {len(missing)}\n")

    if not missing:
        print("All tasks have owner signals. Nothing to fix.")
        return 0

    print(f"{'ID':<20} {'Labels':<40} {'Content'}")
    print("-" * 100)
    for task in missing:
        tid = str(task.get("id", ""))
        labels = ", ".join(task.get("labels") or []) or "(none)"
        content = str(task.get("content", ""))[:55]
        print(f"{tid:<20} {labels:<40} {content}")

    print(f"\n→ {len(missing)} tasks need owner label.")
    print("Reply with: fix all with owner:madi  OR  skip  OR  list specific IDs to fix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
