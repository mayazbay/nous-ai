#!/usr/bin/env python3
"""Seed the Hermes WebUI canary with the Nous factory surface.

This is intentionally idempotent. It fills only empty/missing canary state:
profile memory, WebUI-readable session insight snapshots, a Nous Factory
Kanban board, and a read-only MCP inventory cache for the WebUI panel.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def _json_read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _parse_ts(value: Any, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text).timestamp()
        except ValueError:
            return fallback
    return fallback


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return " ".join(parts).strip()
    return str(content).strip() if content else ""


def _title_from_messages(messages: list[Any], fallback: str) -> str:
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            text = _message_text(message)
            if text:
                return text[:64]
    return fallback


def seed_webui_state(state_dir: Path, profile: str, workspace: str) -> None:
    settings_path = state_dir / "settings.json"
    settings = _json_read(settings_path, {})
    if not isinstance(settings, dict):
        settings = {}
    settings.update(
        {
            "show_cli_sessions": True,
            "show_previous_messaging_sessions": True,
            "onboarding_completed": True,
            "default_workspace": workspace,
            "default_model": "gpt-5.5",
        }
    )
    _json_write(settings_path, settings)

    projects_path = state_dir / "projects.json"
    projects = _json_read(projects_path, [])
    if not isinstance(projects, list):
        projects = []
    if not any(
        isinstance(project, dict)
        and project.get("name") == "Nous Factory"
        and (project.get("profile") or "default") == profile
        for project in projects
    ):
        projects.append(
            {
                "project_id": uuid.uuid4().hex[:12],
                "name": "Nous Factory",
                "color": "#2f855a",
                "profile": profile,
                "created_at": time.time(),
            }
        )
    _json_write(projects_path, projects)


def seed_profile_memory(profile_home: Path) -> None:
    mem_dir = profile_home / "memories"
    mem_dir.mkdir(parents=True, exist_ok=True)
    memory_path = mem_dir / "MEMORY.md"
    user_path = mem_dir / "USER.md"

    if not memory_path.exists() or not memory_path.read_text(encoding="utf-8").strip():
        memory_path.write_text(
            "\n".join(
                [
                    "Nous factory canary profile for Hermes WebUI on Air.",
                    "Workspace/vault: /Users/madia/nous-agaas/wiki, mirrored from the Obsidian Nous vault.",
                    "Production OpenClaw/Telegram remains untouched; Hermes WebUI is canary-first until rollback and 24h proof are explicit.",
                    "Core external systems to keep visible: gbrain semantic memory, Todoist task ops, Notion knowledge/projects, Obsidian vault skills/handoffs.",
                    "Default model route for this profile: openai-codex:gpt-5.5 with xhigh reasoning for high-judgment factory work.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    if not user_path.exists() or not user_path.read_text(encoding="utf-8").strip():
        user_path.write_text(
            "\n".join(
                [
                    "Madi expects proof over prose: exact commands, outputs, git state, and residual risk.",
                    "Prefer concise, direct status. Do not call work green when any live surface is still yellow.",
                    "Keep Nous factory tasks source-backed. Never fabricate Todoist/Notion/gbrain content to make dashboards look full.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )


def seed_session_insights(profile_home: Path, state_dir: Path, profile: str, workspace: str) -> None:
    source_dir = profile_home / "sessions"
    target_dir = state_dir / "sessions"
    target_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []

    for source in sorted(source_dir.glob("session_*.json")):
        raw = _json_read(source, {})
        if not isinstance(raw, dict):
            continue
        sid = str(raw.get("session_id") or source.stem.replace("session_", "", 1)).strip()
        if not sid or any(ch not in "0123456789abcdefghijklmnopqrstuvwxyz_" for ch in sid):
            continue
        messages = raw.get("messages")
        if not isinstance(messages, list):
            messages = []
        fallback_ts = source.stat().st_mtime
        created_at = _parse_ts(raw.get("session_start") or raw.get("created_at"), fallback_ts)
        updated_at = _parse_ts(raw.get("last_updated") or raw.get("updated_at"), fallback_ts)
        title = _title_from_messages(messages, f"Hermes CLI {sid}")
        payload = {
            "session_id": sid,
            "title": title,
            "workspace": workspace,
            "model": raw.get("model") or "gpt-5.5",
            "model_provider": raw.get("model_provider") or "openai-codex",
            "created_at": created_at,
            "updated_at": updated_at,
            "pinned": False,
            "archived": False,
            "project_id": None,
            "profile": profile,
            "input_tokens": int(raw.get("input_tokens") or 0),
            "output_tokens": int(raw.get("output_tokens") or 0),
            "estimated_cost": raw.get("estimated_cost") or 0,
            "cache_read_tokens": int(raw.get("cache_read_tokens") or 0),
            "cache_write_tokens": int(raw.get("cache_write_tokens") or 0),
            "personality": None,
            "active_stream_id": None,
            "pending_user_message": None,
            "pending_attachments": [],
            "pending_started_at": None,
            "compression_anchor_visible_idx": None,
            "compression_anchor_message_key": None,
            "compression_anchor_summary": None,
            "pre_compression_snapshot": False,
            "context_length": None,
            "threshold_tokens": None,
            "last_prompt_tokens": None,
            "gateway_routing": None,
            "gateway_routing_history": [],
            "llm_title_generated": False,
            "parent_session_id": None,
            "worktree_path": None,
            "worktree_branch": None,
            "worktree_repo_root": None,
            "worktree_created_at": None,
            "is_cli_session": True,
            "source_tag": "hermes-cli",
            "raw_source": str(source),
            "session_source": "Hermes CLI canary",
            "source_label": "Hermes CLI",
            "read_only": True,
            "enabled_toolsets": None,
            "composer_draft": {},
            "messages": messages,
            "tool_calls": raw.get("tool_calls") if isinstance(raw.get("tool_calls"), list) else [],
        }
        _json_write(target_dir / f"{sid}.json", payload)
        entries.append(
            {
                "session_id": sid,
                "title": title,
                "workspace": workspace,
                "model": payload["model"],
                "model_provider": payload["model_provider"],
                "message_count": int(raw.get("message_count") or len(messages)),
                "created_at": created_at,
                "updated_at": updated_at,
                "last_message_at": updated_at,
                "pinned": False,
                "archived": False,
                "project_id": None,
                "profile": profile,
                "input_tokens": payload["input_tokens"],
                "output_tokens": payload["output_tokens"],
                "estimated_cost": payload["estimated_cost"],
                "cache_read_tokens": payload["cache_read_tokens"],
                "cache_write_tokens": payload["cache_write_tokens"],
                "personality": None,
                "active_stream_id": None,
                "pending_user_message": None,
                "has_pending_user_message": False,
                "is_cli_session": True,
                "source_tag": "hermes-cli",
                "raw_source": str(source),
                "session_source": "Hermes CLI canary",
                "source_label": "Hermes CLI",
                "read_only": True,
                "enabled_toolsets": None,
                "composer_draft": {},
                "user_message_count": sum(
                    1 for message in messages if isinstance(message, dict) and message.get("role") == "user"
                ),
            }
        )

    entries.sort(key=lambda entry: entry.get("updated_at", 0), reverse=True)
    if entries:
        _json_write(target_dir / "_index.json", entries)


def seed_kanban(profile_home: Path, workspace: str) -> None:
    sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))
    from hermes_cli import kanban_db

    board = "nous-factory"
    kanban_db.create_board(
        board,
        name="Nous Factory",
        description="Canary board for the Hermes WebUI factory surface: Obsidian, gbrain, Todoist, Notion, skills, and live proof.",
        color="#2f855a",
        default_workdir=workspace,
    )
    kanban_db.set_current_board(board)
    conn = kanban_db.connect(board=board)
    cards = [
        {
            "title": "Keep Hermes WebUI factory surface green",
            "body": "Canary gate: profile nouscanary, workspace /Users/madia/nous-agaas/wiki, memory non-empty, insights non-empty, Kanban non-empty, skills visible, MCP inventory visible. Production OpenClaw remains untouched.",
            "priority": 90,
            "status": "running",
            "key": "hermes-webui-surface-green",
        },
        {
            "title": "Repair Tailscale phone URL on Air",
            "body": "Current residual: tailscale-ip-unavailable; LAN fallback is http://192.168.1.197:8787. Run tailscale up on Air when remote phone access must leave the LAN.",
            "priority": 80,
            "status": "blocked",
            "key": "hermes-webui-tailscale-phone-url",
        },
        {
            "title": "Map Todoist, Notion, gbrain, and Obsidian into Hermes playbooks",
            "body": "The MCP servers are configured and probed in canary. Next step is source-backed operator playbooks that read/write the existing systems without fabricating project/task data.",
            "priority": 70,
            "status": "running",
            "key": "hermes-factory-playbooks",
        },
    ]
    for card in cards:
        kanban_db.create_task(
            conn,
            title=card["title"],
            body=card["body"],
            assignee="nouscanary",
            created_by="codex-canary-seed",
            workspace_kind="dir",
            workspace_path=workspace,
            tenant="nous",
            priority=card["priority"],
            idempotency_key=card["key"],
            initial_status=card["status"],
            board=board,
        )
    conn.close()


def seed_mcp_inventory(state_dir: Path) -> None:
    cache_path = state_dir / "mcp_inventory.json"
    now = time.time()
    existing = _json_read(cache_path, {})
    if isinstance(existing, dict) and now - float(existing.get("probed_at", 0) or 0) < 900:
        return

    sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))
    try:
        from tools.mcp_tool import probe_mcp_server_tools

        probed = probe_mcp_server_tools()
    except Exception as exc:
        _json_write(cache_path, {"probed_at": now, "error": str(exc), "servers": {}})
        return

    servers: dict[str, dict[str, Any]] = {}
    for name, tools in probed.items():
        schemas = [
            {
                "name": tool_name,
                "description": description or "",
                "inputSchema": {"type": "object", "properties": {}},
            }
            for tool_name, description in tools
        ]
        servers[name] = {
            "name": name,
            "transport": "stdio",
            "connected": True,
            "tools": len(schemas),
            "tool_schemas": schemas,
        }
    _json_write(cache_path, {"probed_at": now, "servers": servers})


def main() -> int:
    state_dir = Path(os.environ["HERMES_WEBUI_STATE_DIR"]).expanduser()
    base_home = Path(os.environ.get("HERMES_BASE_HOME", str(Path.home() / ".hermes"))).expanduser()
    profile = os.environ.get("HERMES_WEBUI_PROFILE", "nouscanary")
    workspace = os.environ.get("HERMES_WEBUI_DEFAULT_WORKSPACE", str(Path.home() / "nous-agaas/wiki"))
    profile_home = base_home if profile == "default" else base_home / "profiles" / profile

    seed_webui_state(state_dir, profile, workspace)
    seed_profile_memory(profile_home)
    seed_session_insights(profile_home, state_dir, profile, workspace)
    seed_kanban(profile_home, workspace)
    seed_mcp_inventory(state_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
