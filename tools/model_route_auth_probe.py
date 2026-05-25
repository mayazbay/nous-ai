#!/usr/bin/env python3
"""Read-only auth/route probes for Nous model surfaces.

The probes inspect executable/config presence and classify billing surface.
They never send prompts to a model and never validate keys by spending calls.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Mapping, Any


BILLING_SUBSCRIPTION = "subscription"
BILLING_LOCAL = "local"
BILLING_XAI_API = "xai_api"
BILLING_ANTHROPIC_API = "anthropic_api"
BILLING_OPENROUTER = "openrouter"
BILLING_UNKNOWN = "unknown"


def _has_env(env: Mapping[str, str], key: str) -> bool:
    return bool(str(env.get(key, "")).strip())


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _base(route: str, billing_surface: str, route_type: str) -> dict[str, Any]:
    return {
        "route": route,
        "route_type": route_type,
        "billing_surface": billing_surface,
        "auth_present": False,
        "live_model_call": False,
    }


def probe_codex(home: Path | None = None, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    home = home or Path.home()
    env = env or os.environ
    auth_present = _exists(home / ".codex" / "auth.json") or _has_env(env, "CODEX_AUTH_TOKEN")
    result = _base("codex", BILLING_SUBSCRIPTION, "subscription_cli")
    result.update(
        {
            "command_present": bool(shutil.which("codex")),
            "auth_present": auth_present,
            "api_fallback_enabled": False,
            "paid_api_requires_cap": False,
        }
    )
    return result


def probe_grok(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = env or os.environ
    result = _base("grok", BILLING_XAI_API, "api_config")
    result.update(
        {
            "auth_present": _has_env(env, "XAI_API_KEY"),
            "api_fallback_enabled": False,
            "paid_api_requires_cap": True,
        }
    )
    return result


def probe_claude_code(home: Path | None = None, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    home = home or Path.home()
    env = env or os.environ
    auth_present = (
        _exists(home / ".claude")
        or _has_env(env, "ANTHROPIC_AUTH_TOKEN")
        or _has_env(env, "CLAUDE_CODE_OAUTH_TOKEN")
    )
    result = _base("claude_code", BILLING_SUBSCRIPTION, "subscription_cli")
    result.update(
        {
            "command_present": bool(shutil.which("claude")),
            "auth_present": auth_present,
            "api_fallback_enabled": False,
            "paid_api_requires_cap": False,
        }
    )
    return result


def probe_hermes(home: Path | None = None, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    home = home or Path.home()
    env = env or os.environ
    plist = home / "Library" / "LaunchAgents" / "com.nous.hermes-canary.plist"
    result = _base("hermes", BILLING_UNKNOWN, "canary_supervisor")
    result.update(
        {
            "auth_present": _has_env(env, "HERMES_WEBUI_STATE_DIR") or _exists(plist),
            "canary_only": True,
            "paid_api_requires_cap": True,
        }
    )
    return result


def probe_openclaw(home: Path | None = None, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    home = home or Path.home()
    env = env or os.environ
    result = _base("openclaw", BILLING_UNKNOWN, "production_factory")
    result.update(
        {
            "auth_present": _exists(home / "nous-agaas" / ".env") or _has_env(env, "OPENCLAW_HOME"),
            "command_present": bool(shutil.which("openclaw")) or bool(shutil.which("docker")),
            "paid_api_requires_cap": True,
        }
    )
    return result


def probe_litellm(home: Path | None = None, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    home = home or Path.home()
    env = env or os.environ
    result = _base("litellm", BILLING_OPENROUTER, "api_proxy_config")
    result.update(
        {
            "auth_present": _has_env(env, "LITELLM_MASTER_KEY")
            or _exists(home / "nous-agaas" / "litellm" / ".env"),
            "command_present": bool(shutil.which("litellm")),
            "paid_api_requires_cap": True,
        }
    )
    return result


def collect_probes(home: Path | None = None, env: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    home = home or Path.home()
    env = env or os.environ
    return [
        probe_codex(home=home, env=env),
        probe_grok(env=env),
        probe_claude_code(home=home, env=env),
        probe_hermes(home=home, env=env),
        probe_openclaw(home=home, env=env),
        probe_litellm(home=home, env=env),
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = collect_probes(home=args.home)
    text = json.dumps({"probes": results}, indent=2, ensure_ascii=False)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
