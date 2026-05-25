#!/usr/bin/env python3
"""LangSmith observer for the Nous Telegram/OpenClaw control plane.

This module is intentionally best-effort. Observability must never break
Telegram, Goal Mode, or run_task execution. Every event is written locally first;
LangSmith upload is attempted only when credentials and the SDK are available.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PROJECT = "nous-agaas-control-plane"
DEFAULT_WORKSPACE_ID = "ddcd0e90-d971-48eb-bdb1-185fce6491c4"
DEFAULT_LOG = "/Users/madia/nous-agaas/logs/langsmith-observer.jsonl"
DEFAULT_ENV_FILES = (
    "/Users/madia/nous-agaas/.env",
    "/Users/madia/nous-agaas/wiki/.env",
)

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|secret|password|passwd|authorization|bearer|cert|p12|private[_-]?key)",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(lsv2_[A-Za-z0-9_.-]{12,}|ls_[A-Za-z0-9_.-]{12,}|sk-[A-Za-z0-9_.-]{12,}|"
    r"[A-Za-z0-9+/]{80,}={0,2})"
)
SAFE_TOKEN_METRIC_KEYS = {
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "tokens_in",
    "tokens_out",
    "prompt_tokens",
    "completion_tokens",
}


@dataclass
class LangSmithConfig:
    tracing: bool
    api_key_present: bool
    project: str
    endpoint: str
    workspace_id: str
    log_path: str
    sdk_available: bool
    send_enabled: bool
    reason: str


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(path: str) -> None:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_runtime_env(paths: tuple[str, ...] = DEFAULT_ENV_FILES) -> None:
    for path in paths:
        _load_env_file(path)


def _project_from_env() -> str:
    # New control plane should not silently inherit the old satory-vko project.
    return (
        os.environ.get("NOUS_LANGSMITH_PROJECT")
        or os.environ.get("LANGSMITH_PROJECT")
        or DEFAULT_PROJECT
    )


def get_config(load_env: bool = True) -> LangSmithConfig:
    if load_env:
        load_runtime_env()

    legacy_key = os.environ.get("LANGCHAIN_API_KEY", "")
    api_key = os.environ.get("LANGSMITH_API_KEY", "") or legacy_key
    tracing_raw = os.environ.get("LANGSMITH_TRACING", "")
    if not tracing_raw:
        tracing_raw = os.environ.get("LANGCHAIN_TRACING_V2", "")
    tracing = _truthy(tracing_raw)

    endpoint = os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    workspace_id = os.environ.get("LANGSMITH_WORKSPACE_ID", DEFAULT_WORKSPACE_ID)
    log_path = os.environ.get("NOUS_LANGSMITH_LOG", DEFAULT_LOG)
    sdk_available = importlib.util.find_spec("langsmith") is not None
    disabled = _truthy(os.environ.get("NOUS_LANGSMITH_DISABLE", ""))
    send_enabled = bool(tracing and api_key and sdk_available and not disabled)
    if disabled:
        reason = "disabled_by_env"
    elif not tracing:
        reason = "tracing_disabled"
    elif not api_key:
        reason = "api_key_missing"
    elif not sdk_available:
        reason = "sdk_missing"
    else:
        reason = "ready"
    return LangSmithConfig(
        tracing=tracing,
        api_key_present=bool(api_key),
        project=_project_from_env(),
        endpoint=endpoint,
        workspace_id=workspace_id,
        log_path=log_path,
        sdk_available=sdk_available,
        send_enabled=send_enabled,
        reason=reason,
    )


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def text_digest(text: str, preview_chars: int = 500) -> dict[str, Any]:
    compact = " ".join(str(text or "").split())
    return {
        "sha256": _sha(compact),
        "chars": len(str(text or "")),
        "preview": redact(compact[:preview_chars]),
    }


def redact(value: Any, max_string: int = 1200) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in SAFE_TOKEN_METRIC_KEYS:
                out[key_text] = redact(item, max_string=max_string)
            elif SECRET_KEY_RE.search(key_text):
                out[key_text] = "<redacted>"
            else:
                out[key_text] = redact(item, max_string=max_string)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(item, max_string=max_string) for item in value[:50]]
    if isinstance(value, str):
        sanitized = SECRET_VALUE_RE.sub("<redacted>", value)
        if len(sanitized) > max_string:
            return sanitized[:max_string] + f"...<truncated chars={len(sanitized)}>"
        return sanitized
    return value


def _append_local(event: dict[str, Any], config: LangSmithConfig) -> None:
    path = Path(config.log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _post_langsmith(event: dict[str, Any], config: LangSmithConfig) -> None:
    if not config.send_enabled:
        return
    try:
        from langsmith import Client
        from langsmith.run_trees import RunTree

        api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
        client = Client(
            api_url=config.endpoint,
            api_key=api_key,
            workspace_id=config.workspace_id,
            timeout_ms=(2000, 3000),
        )
        run = RunTree(
            name=event["name"],
            run_type=event.get("run_type", "chain"),
            inputs=event.get("inputs") or {},
            project_name=config.project,
            tags=event.get("tags") or [],
            extra={"metadata": event.get("metadata") or {}},
            ls_client=client,
        )
        run.post()
        run.end(outputs=event.get("outputs") or {"status": event.get("status", "unknown")})
        run.patch()
    except Exception:
        # Runtime path is non-blocking; local JSONL remains the truth fallback.
        return


def emit_event(
    name: str,
    *,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    run_type: str = "chain",
    status: str = "ok",
    wait: bool = False,
) -> dict[str, Any]:
    config = get_config(load_env=True)
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "run_type": run_type,
        "status": status,
        "project": config.project,
        "inputs": redact(inputs or {}),
        "outputs": redact(outputs or {}),
        "metadata": redact(metadata or {}),
        "tags": tags or [],
        "langsmith": asdict(config),
    }
    _append_local(event, config)
    if config.send_enabled:
        if wait:
            _post_langsmith(event, config)
        else:
            thread = threading.Thread(
                target=_post_langsmith,
                args=(event, config),
                name="nous-langsmith-observer",
                daemon=True,
            )
            thread.start()
    return event


def _smoke() -> int:
    config = get_config(load_env=True)
    if not config.send_enabled:
        print(json.dumps({"ok": False, "config": asdict(config)}, ensure_ascii=False))
        return 2
    try:
        from langsmith import Client

        api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
        client = Client(
            api_url=config.endpoint,
            api_key=api_key,
            workspace_id=config.workspace_id,
            timeout_ms=(2000, 5000),
        )
        project = client.create_project(
            project_name=config.project,
            description="Nous AGaaS Telegram/OpenClaw control-plane observability",
            metadata={"workspace": "nous-agaas", "source": "tools/langsmith_observer.py"},
            upsert=True,
        )
        event = emit_event(
            "nous.langsmith.smoke",
            inputs={"probe": "langsmith_observer"},
            outputs={"result": "ok"},
            metadata={"project_id": str(getattr(project, "id", ""))},
            tags=["nous", "smoke", "control-plane"],
            wait=True,
        )
        print(json.dumps({"ok": True, "event": event}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}", "config": asdict(config)}, ensure_ascii=False))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Nous LangSmith observer")
    parser.add_argument("--config", action="store_true", help="Print effective redacted config")
    parser.add_argument("--smoke", action="store_true", help="Create/upsert project and emit a smoke trace")
    args = parser.parse_args()
    if args.config:
        print(json.dumps(asdict(get_config()), ensure_ascii=False, indent=2))
        return 0
    if args.smoke:
        return _smoke()
    parser.error("choose --config or --smoke")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
