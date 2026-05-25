#!/usr/bin/env python3
"""Canonical operations task contract.

This module is intentionally pure: it validates and shapes one task object but
does not call Notion, Todoist, OpenClaw, or memory services.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


SATORY_NOTION_PROJECT_ID = "06c7e5a9-343a-4802-974f-58613a6babaa"
SATORY_SECOND_BRAIN_DATABASE_ID = "3bc876611a44404a84b50bbae6506d72"
SATORY_SECOND_BRAIN_DATA_SOURCE_ID = "e6765cd4-5a4e-4d6e-a5e7-042b395ba120"
SATORY_SECOND_BRAIN_VIEW_ID = "269cb8f8-c69f-80e7-9790-000c2e10b4dc"
SATORY_SECOND_BRAIN_VIEW_URL = (
    "https://www.notion.so/3bc876611a44404a84b50bbae6506d72"
    "?v=269cb8f8c69f80e79790000c2e10b4dc&source=copy_link"
)
SATORY_NOTION_TASKS_DATA_SOURCE_ID = "e731690a-1a78-474f-8764-2b4f170e1f2f"
SATORY_TODOIST_PROJECT_ID = "6gJ5j8PRVVCWpgCq"

DEFAULT_MODEL_PIPELINE = [
    "grok-reasoning",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "kimi-k2.6",
    "glm-5.1",
    "codex:gpt-5.5-subscription",
]
PRIORITY_ALIASES = {
    "urgent": "p1",
    "critical": "p1",
    "high": "p1",
    "p1": "p1",
    "medium": "p2",
    "mid": "p2",
    "normal": "p2",
    "p2": "p2",
    "low": "p3",
    "p3": "p3",
    "later": "p4",
    "p4": "p4",
}
TODOIST_PRIORITY = {"p1": 4, "p2": 3, "p3": 2, "p4": 1}


class TaskSpineError(ValueError):
    """Raised when a task cannot enter the unified ops spine."""


def normalize_task(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one task for the operations spine."""
    if not isinstance(raw, Mapping):
        raise TaskSpineError("task must be a JSON object")

    title = _required_text(raw, "title")
    tenant = _text(raw.get("tenant") or "satory")
    if tenant != "satory":
        raise TaskSpineError("only tenant=satory is supported in this slice")

    project = _required_text(raw, "project")
    subproject = _optional_text(raw.get("subproject"))
    owner = _optional_text(raw.get("owner"))
    team = _optional_text(raw.get("team"))
    if not owner and not team:
        raise TaskSpineError("task must have owner or team assignment")

    priority = _normalize_priority(raw.get("priority"))
    notion_project_id = _required_text(raw, "notion_project_id")
    if _compact_uuid(notion_project_id) != _compact_uuid(SATORY_NOTION_PROJECT_ID):
        raise TaskSpineError("task must be scoped to the verified Satory AI Notion project")
    notion_source_database_id = _optional_text(raw.get("notion_source_database_id")) or SATORY_SECOND_BRAIN_DATABASE_ID
    if _compact_uuid(notion_source_database_id) != _compact_uuid(SATORY_SECOND_BRAIN_DATABASE_ID):
        raise TaskSpineError("task source must be the verified Satory 2nd Brain database")
    notion_source_data_source_id = _required_text(raw, "notion_source_data_source_id")
    if _compact_uuid(notion_source_data_source_id) != _compact_uuid(SATORY_SECOND_BRAIN_DATA_SOURCE_ID):
        raise TaskSpineError("task source must be the verified Satory 2nd Brain data source")
    notion_source_view_id = _optional_text(raw.get("notion_source_view_id")) or SATORY_SECOND_BRAIN_VIEW_ID
    if _compact_uuid(notion_source_view_id) != _compact_uuid(SATORY_SECOND_BRAIN_VIEW_ID):
        raise TaskSpineError("task source must be the verified Satory A.I. 2nd Brain view")
    notion_source_view_url = _optional_text(raw.get("notion_source_view_url")) or SATORY_SECOND_BRAIN_VIEW_URL
    if notion_source_view_url != SATORY_SECOND_BRAIN_VIEW_URL:
        raise TaskSpineError("task source must use the verified Satory A.I. 2nd Brain view URL")
    notion_source_url = _required_text(raw, "notion_source_url")

    todoist_project_id = _required_text(raw, "todoist_project_id")
    if todoist_project_id != SATORY_TODOIST_PROJECT_ID:
        raise TaskSpineError("task must target the shared Satory VKO Factory Todoist project")

    normalized = {
        "title": title,
        "tenant": tenant,
        "project": project,
        "subproject": subproject,
        "owner": owner,
        "team": team,
        "priority": priority,
        "notion_project_id": SATORY_NOTION_PROJECT_ID,
        "notion_source_database_id": SATORY_SECOND_BRAIN_DATABASE_ID,
        "notion_source_data_source_id": SATORY_SECOND_BRAIN_DATA_SOURCE_ID,
        "notion_source_view_id": SATORY_SECOND_BRAIN_VIEW_ID,
        "notion_source_view_url": notion_source_view_url,
        "notion_source_url": notion_source_url,
        "notion_tasks_data_source_id": _optional_text(raw.get("notion_tasks_data_source_id"))
        or SATORY_NOTION_TASKS_DATA_SOURCE_ID,
        "todoist_project_id": todoist_project_id,
        "todoist_section_id": _optional_text(raw.get("todoist_section_id")),
        "todoist_parent_id": _optional_text(raw.get("todoist_parent_id")),
        "todoist_assignee_id": _optional_text(raw.get("todoist_assignee_id")),
        "due_date": _optional_text(raw.get("due_date")),
        "deadline_date": _optional_text(raw.get("deadline_date")),
        "duration": _optional_int(raw.get("duration"), "duration"),
        "duration_unit": _optional_text(raw.get("duration_unit")),
        "source_links": _list_of_mappings(raw.get("source_links"), "source_links"),
        "attachments": _list_of_mappings(raw.get("attachments"), "attachments"),
        "comments": _list_of_text(raw.get("comments"), "comments"),
        "model_pipeline": list(raw.get("model_pipeline") or DEFAULT_MODEL_PIPELINE),
    }
    normalized["idempotency_key"] = _idempotency_key(normalized)
    return normalized


def todoist_create_payload(task: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Todoist create-task body from a normalized task."""
    normalized = normalize_task(task) if "idempotency_key" not in task else dict(task)
    payload: dict[str, Any] = {
        "content": normalized["title"],
        "project_id": normalized["todoist_project_id"],
        "description": _description(normalized),
        "priority": TODOIST_PRIORITY[normalized["priority"]],
        "labels": _labels(normalized),
    }
    optional_pairs = [
        ("due_date", "due_date"),
        ("deadline_date", "deadline_date"),
        ("duration", "duration"),
        ("duration_unit", "duration_unit"),
        ("todoist_section_id", "section_id"),
        ("todoist_parent_id", "parent_id"),
        ("todoist_assignee_id", "assignee_id"),
    ]
    for source, target in optional_pairs:
        value = normalized.get(source)
        if value:
            payload[target] = value
    return payload


def todoist_source_comment(task: Mapping[str, Any]) -> str:
    """Build the source/context comment that follows the Todoist task."""
    normalized = normalize_task(task) if "idempotency_key" not in task else dict(task)
    lines = [f"Notion: {normalized['notion_source_url']}"]
    if normalized.get("source_links"):
        lines.append("")
        lines.append("Links:")
        for link in normalized["source_links"]:
            lines.append(f"- {_display_name(link)}: {link['url']}")
    if normalized.get("attachments"):
        lines.append("")
        lines.append("Attachments:")
        for attachment in normalized["attachments"]:
            lines.append(f"- {_display_name(attachment)}: {attachment['url']}")
    if normalized.get("comments"):
        lines.append("")
        lines.append("Notes:")
        for comment in normalized["comments"]:
            lines.append(f"- {comment}")
    return "\n".join(lines)


def _description(task: Mapping[str, Any]) -> str:
    lines = [
        f"Project: {task['project']}",
        f"Priority: {task['priority']}",
        f"Notion: {task['notion_source_url']}",
        f"2nd Brain view: {task['notion_source_view_url']}",
        f"Execution: {' -> '.join(task['model_pipeline'])}",
        f"Idempotency: {task['idempotency_key']}",
    ]
    if task.get("subproject"):
        lines.insert(1, f"Subproject: {task['subproject']}")
    if task.get("owner"):
        lines.insert(2, f"Owner: {task['owner']}")
    if task.get("team"):
        lines.insert(3, f"Team: {task['team']}")
    return "\n".join(lines)


def _labels(task: Mapping[str, Any]) -> list[str]:
    labels = ["ИИ-предложено", f"проект:{task['project']}", f"приоритет:{task['priority']}"]
    if task.get("subproject"):
        labels.append(f"подпроект:{task['subproject']}")
    if task.get("owner"):
        labels.append(f"исполнитель:{task['owner']}")
    if task.get("team"):
        labels.append(f"команда:{task['team']}")
    return labels


def _idempotency_key(task: Mapping[str, Any]) -> str:
    stable = {
        "tenant": task["tenant"],
        "project": task["project"],
        "title": task["title"],
        "notion_source_url": task["notion_source_url"],
        "todoist_parent_id": task.get("todoist_parent_id"),
    }
    digest = hashlib.sha256(
        json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"ops-task:{task['tenant']}:{digest}"


def _required_text(raw: Mapping[str, Any], key: str) -> str:
    value = _optional_text(raw.get(key))
    if not value:
        raise TaskSpineError(f"{key} must be a non-empty string")
    return value


def _optional_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TaskSpineError("text fields must be strings")
    return value.strip()


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskSpineError("text value must be a non-empty string")
    return value.strip()


def _normalize_priority(value: Any) -> str:
    raw = _optional_text(value).lower()
    priority = PRIORITY_ALIASES.get(raw)
    if not priority:
        raise TaskSpineError("priority must be one of p1/p2/p3/p4 or high/medium/low")
    return priority


def _optional_int(value: Any, field: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TaskSpineError(f"{field} must be an integer")
    if value <= 0:
        raise TaskSpineError(f"{field} must be positive")
    return value


def _list_of_mappings(value: Any, field: str) -> list[dict[str, str]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise TaskSpineError(f"{field} must be a list")
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TaskSpineError(f"{field} items must be objects")
        url = _required_text(item, "url")
        name = _optional_text(item.get("title") or item.get("name")) or url
        result.append({"title": name, "name": name, "url": url})
    return result


def _list_of_text(value: Any, field: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise TaskSpineError(f"{field} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TaskSpineError(f"{field} items must be non-empty strings")
        result.append(item.strip())
    return result


def _display_name(item: Mapping[str, str]) -> str:
    return item.get("title") or item.get("name") or item["url"]


def _compact_uuid(value: str) -> str:
    return value.replace("-", "").lower()
