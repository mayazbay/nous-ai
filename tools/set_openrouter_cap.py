#!/usr/bin/env python3
"""Set a hard spend cap on the active OpenRouter API key via the Management API.

Usage:
  python3 tools/set_openrouter_cap.py [--limit 5.0] [--env-file .env]

Requires OPENROUTER_MANAGEMENT_KEY in env or env file.
Finds the key whose hash prefix matches OPENROUTER_API_KEY and sets limit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_LIMIT = 5.0


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


def resolve_keys(env_file: Path) -> tuple[str, str]:
    env = {**load_env_file(env_file), **os.environ}
    mgmt = env.get("OPENROUTER_MANAGEMENT_KEY", "").strip()
    api = env.get("OPENROUTER_API_KEY", "").strip()
    if not mgmt:
        raise RuntimeError("OPENROUTER_MANAGEMENT_KEY not found in env or env file")
    if not api:
        raise RuntimeError("OPENROUTER_API_KEY not found — needed to identify which key to cap")
    return mgmt, api


def list_keys(mgmt_key: str) -> list[dict]:
    r = requests.get(
        f"{OPENROUTER_BASE}/keys",
        headers={"Authorization": f"Bearer {mgmt_key}"},
        timeout=30,
    )
    if r.status_code == 401:
        raise RuntimeError(f"Management key rejected (401). Body: {r.text[:300]}")
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    return data.get("data", data.get("keys", []))


def find_matching_key(keys: list[dict], api_key: str, target_name: str | None = None) -> dict | None:
    """Match by label (key prefix...suffix shown by OpenRouter) or by name.

    OpenRouter's `label` field is "sk-or-v1-{first8}...{last3}". The `hash` is
    a SHA of the key, NOT the key itself, so prefix-matching on hash will fail.
    """
    if target_name:
        for k in keys:
            if k.get("name", "").lower() == target_name.lower():
                return k

    prefix = api_key[:11]  # e.g., "sk-or-v1-18"
    suffix = api_key[-3:]
    for k in keys:
        label = k.get("label", "")
        if label.startswith(prefix) and label.endswith(suffix):
            return k

    if len(keys) == 1:
        return keys[0]
    return None


def set_limit(mgmt_key: str, key_id: str, limit: float, limit_reset: str = "daily") -> dict:
    """Set per-key limit. limit_reset='daily' means $limit is a DAILY cap, not lifetime.

    Without limit_reset, OpenRouter treats `limit` as a lifetime cap on top of
    existing usage — easy to accidentally block the key if usage > limit.
    """
    r = requests.patch(
        f"{OPENROUTER_BASE}/keys/{key_id}",
        headers={
            "Authorization": f"Bearer {mgmt_key}",
            "Content-Type": "application/json",
        },
        json={"limit": limit, "limit_reset": limit_reset},
        timeout=30,
    )
    if r.status_code == 401:
        raise RuntimeError(f"Management key rejected on PATCH (401). Body: {r.text[:300]}")
    r.raise_for_status()
    return r.json()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=float, default=DEFAULT_LIMIT, help="Daily spend cap in USD")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("/Users/madia/Documents/Projects/Nous AGaaS/.env"),
    )
    parser.add_argument("--dry-run", action="store_true", help="List keys, do not set limit")
    parser.add_argument("--name", default="Nous AGaaS", help="Key name to target (matches by name first)")
    parser.add_argument("--limit-reset", default="daily", choices=["daily", "weekly", "monthly", "never"],
                        help="Reset cadence. 'daily' makes --limit a DAILY cap.")
    args = parser.parse_args(argv)

    try:
        mgmt_key, api_key = resolve_keys(args.env_file)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Management key loaded (id prefix: {mgmt_key[:8]}...)")
    print(f"API key to match (prefix: {api_key[:8]}...)")

    try:
        keys = list_keys(mgmt_key)
    except RuntimeError as e:
        print(f"ERROR listing keys: {e}", file=sys.stderr)
        return 1

    print(f"Found {len(keys)} key(s) on OpenRouter account:")
    for k in keys:
        kid = k.get("id") or k.get("hash") or "?"
        name = k.get("name", "")
        limit = k.get("limit")
        usage = k.get("usage") or k.get("limit_remaining")
        print(f"  id={kid} name={name!r} limit={limit} usage={usage}")

    if args.dry_run:
        print("Dry-run: not setting limit.")
        return 0

    target = find_matching_key(keys, api_key, target_name=args.name)
    if not target:
        print(f"ERROR: Could not match key name={args.name!r} or API key prefix.", file=sys.stderr)
        print("Keys available:", [k.get("name") for k in keys], file=sys.stderr)
        return 1

    key_id = target.get("hash") or target.get("id")
    key_name = target.get("name", "")
    current_limit = target.get("limit")
    current_reset = target.get("limit_reset")
    print(f"\nTarget key: name={key_name!r} current_limit={current_limit} current_reset={current_reset}")

    try:
        result = set_limit(mgmt_key, key_id, args.limit, limit_reset=args.limit_reset)
    except RuntimeError as e:
        print(f"ERROR setting limit: {e}", file=sys.stderr)
        return 1

    data = result.get("data", result)
    new_limit = data.get("limit")
    new_reset = data.get("limit_reset")
    remaining = data.get("limit_remaining")
    print(f"\nCap set: ${args.limit:.2f} / {args.limit_reset}")
    print(f"Response: limit={new_limit} limit_reset={new_reset} limit_remaining={remaining}")
    if new_limit is None:
        print("WARNING: limit still null — OpenRouter rejected the value.")
        return 1
    print(f"SUCCESS: ${new_limit}/{new_reset} cap active. ${remaining} remaining for current period.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
