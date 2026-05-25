#!/usr/bin/env python3
"""Summarize LiteLLM /health output for operator alerts.

LiteLLM /health is useful, but it checks every configured endpoint with the
same probe shape. That makes some entries noisy for the Nous control plane:
subscription-only Codex aliases and embedding routes should not make the
factory's chat-model alert red.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


DEFAULT_IGNORED_MODELS = {
    "gpt-5.5",
    "gemini/gemini-embedding-001",
}


def ignored_models() -> set[str]:
    raw = os.environ.get("MODEL_HEALTH_IGNORED_MODELS", "")
    if not raw.strip():
        return set(DEFAULT_IGNORED_MODELS)
    return {part.strip() for part in raw.split(",") if part.strip()}


def _model_name(endpoint: dict[str, Any]) -> str:
    return str(endpoint.get("model") or "unknown-model")


def summarize(payload: dict[str, Any], ignored: set[str]) -> tuple[int, int, str]:
    health_keys = {
        "healthy_endpoints",
        "unhealthy_endpoints",
        "healthy_count",
        "unhealthy_count",
        "dead_models",
    }
    if not any(key in payload for key in health_keys):
        raise ValueError("payload is not LiteLLM /health output")

    healthy = [
        item
        for item in payload.get("healthy_endpoints", [])
        if isinstance(item, dict) and _model_name(item) not in ignored
    ]
    unhealthy = [
        item
        for item in payload.get("unhealthy_endpoints", [])
        if isinstance(item, dict) and _model_name(item) not in ignored
    ]

    if healthy or unhealthy:
        dead = ",".join(_model_name(item) for item in unhealthy) or "none"
        return len(healthy), len(unhealthy), dead

    dead = str(payload.get("dead_models") or "none")
    return int(payload.get("healthy_count") or 0), int(payload.get("unhealthy_count") or 0), dead


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        healthy, unhealthy, dead = summarize(payload, ignored_models())
    except Exception:
        return 1
    print(f"{healthy}\t{unhealthy}\t{dead}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
