#!/usr/bin/env python3
"""Guarded Todoist hygiene migration for the Satory VKO Factory project."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

import log_event
from audit_satory_todoist_state import (
    ALLOWED_PROJECT_ID,
    OWNER_LABEL_PREFIXES,
    PERSONAL_PROJECT_IDS,
    labels_for,
    token_from_env,
)


TODOIST_BASE = "https://api.todoist.com/api/v1"
DEFAULT_OWNER_LABEL = "исполнитель:AI Factory"
CORRELATION_ID = f"todoist-hygiene:{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
TITLE_OWNER_LABELS = {
    "ai factory": DEFAULT_OWNER_LABEL,
    "madi": "исполнитель:Мади",
    "мади": "исполнитель:Мади",
    "accountant": "исполнитель:Бухгалтер",
    "бухгалтер": "исполнитель:Бухгалтер",
    "nazel": "исполнитель:Назель",
    "назель": "исполнитель:Назель",
    "roza": "исполнитель:Роза",
    "роза": "исполнитель:Роза",
    "assyl": "исполнитель:Асыл",
    "asyl": "исполнитель:Асыл",
    "асыл": "исполнитель:Асыл",
    "dk": "исполнитель:DK",
    "gr": "исполнитель:Роза",
    "counsel": "исполнитель:Назель",
    "tech": DEFAULT_OWNER_LABEL,
    "infrastructure": DEFAULT_OWNER_LABEL,
}


class HygieneError(RuntimeError):
    """Raised when the migration cannot safely proceed."""


class TodoistClient:
    def __init__(self, token: str) -> None:
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(
            method,
            f"{TODOIST_BASE}{path}",
            headers=self.headers,
            timeout=30,
            **kwargs,
        )
        response.raise_for_status()
        if response.text.strip():
            return response.json()
        return None

    def project(self, project_id: str) -> dict[str, Any]:
        payload = self.request("GET", f"/projects/{project_id}")
        if not isinstance(payload, dict):
            raise HygieneError("Todoist project response was not an object")
        return payload

    def tasks_for_project(self, project_id: str) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        cursor: str | None = None
        seen: set[str] = set()
        while True:
            params = {"project_id": project_id}
            if cursor:
                params["cursor"] = cursor
            payload = self.request("GET", "/tasks", params=params)
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                raise HygieneError("Todoist tasks response was not a paginated object")
            tasks.extend(task for task in payload["results"] if isinstance(task, dict))
            next_cursor = payload.get("next_cursor")
            if not next_cursor:
                return tasks
            cursor = str(next_cursor)
            if cursor in seen:
                raise HygieneError(f"Todoist pagination cursor loop detected: {cursor}")
            seen.add(cursor)

    def update_task(self, task_id: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = self.request("POST", f"/tasks/{task_id}", json=body)
        if not isinstance(payload, dict):
            raise HygieneError(f"Todoist update response for {task_id} was not an object")
        return payload

    def close_task(self, task_id: str) -> None:
        self.request("POST", f"/tasks/{task_id}/close")


def verify_allowed_project(project: dict[str, Any], project_id: str) -> None:
    if project_id in PERSONAL_PROJECT_IDS:
        raise HygieneError(f"refusing personal Todoist project {project_id}")
    if project_id != ALLOWED_PROJECT_ID:
        raise HygieneError(f"project {project_id} is not allowlisted {ALLOWED_PROJECT_ID}")
    if not project.get("is_shared"):
        raise HygieneError(f"project {project_id} is not shared")


def first_owner_label(labels: list[str]) -> str | None:
    for label in labels:
        if label.startswith(OWNER_LABEL_PREFIXES):
            return label
    return None


def title_owner_labels(task: dict[str, Any]) -> list[str]:
    content = str(task.get("content") or "")
    if not content:
        return []

    owner_segment = content
    colon_parts = content.split(":", 2)
    if len(colon_parts) == 3:
        owner_segment = colon_parts[2]
    elif len(colon_parts) == 2:
        owner_segment = colon_parts[0]
    if "—" in owner_segment:
        owner_segment = owner_segment.split("—", 1)[0]
    if content.startswith("KEONA/Infrastructure"):
        owner_segment = f"{owner_segment}/Infrastructure"

    labels: list[str] = []
    for token in re.split(r"[/,+&]", owner_segment):
        normalized = token.strip().casefold()
        label = TITLE_OWNER_LABELS.get(normalized)
        if label and label not in labels:
            labels.append(label)
    return labels


def task_priority(task: dict[str, Any]) -> int:
    try:
        return int(task.get("priority") or 1)
    except (TypeError, ValueError):
        return 1


def is_status_receipt(task: dict[str, Any]) -> bool:
    content = str(task.get("content") or "")
    labels = set(labels_for(task))
    return content.startswith("AI Factory D0:") and {"factory", "ИИ-предложено"}.issubset(labels)


def infer_priority(task: dict[str, Any]) -> int:
    content = str(task.get("content") or "").lower()
    labels = set(labels_for(task))
    if "data residency" in content or "data residency" in labels:
        return 4
    if "cerebro" in {label.lower() for label in labels}:
        return 3
    if "factory" in labels:
        return 3
    return 2


def planned_owner_label(
    task: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    memo: dict[str, str],
) -> str:
    task_id = str(task.get("id") or "")
    if task_id in memo:
        return memo[task_id]

    existing = first_owner_label(labels_for(task))
    if existing:
        memo[task_id] = existing
        return existing

    parent_id = task.get("parent_id")
    parent = by_id.get(str(parent_id)) if parent_id else None
    if parent:
        owner = planned_owner_label(parent, by_id, memo)
    else:
        owner = DEFAULT_OWNER_LABEL
    memo[task_id] = owner
    return owner


def build_plan(tasks: list[dict[str, Any]], project_id: str) -> list[dict[str, Any]]:
    by_id = {str(task.get("id")): task for task in tasks if task.get("id")}
    owner_memo: dict[str, str] = {}
    plan: list[dict[str, Any]] = []

    for task in tasks:
        task_id = str(task.get("id") or "")
        if not task_id:
            continue
        if str(task.get("project_id") or "") != project_id:
            raise HygieneError(f"task {task_id} is outside allowlisted project")

        labels = labels_for(task)
        new_labels = list(labels)
        owner_added: list[str] = []
        if not first_owner_label(labels) and not task.get("assignee_id") and not task.get("responsible_uid"):
            planned_labels = title_owner_labels(task) or [planned_owner_label(task, by_id, owner_memo)]
            for planned_label in planned_labels:
                if planned_label not in new_labels:
                    new_labels.append(planned_label)
                    owner_added.append(planned_label)

        priority = task_priority(task)
        new_priority: int | None = None
        close = False
        if priority <= 1:
            if is_status_receipt(task):
                close = True
            else:
                new_priority = infer_priority(task)

        update_body: dict[str, Any] = {}
        if new_labels != labels:
            update_body["labels"] = new_labels
        if new_priority is not None and new_priority != priority:
            update_body["priority"] = new_priority

        if update_body or close:
            plan.append(
                {
                    "task_id": task_id,
                    "content": task.get("content", ""),
                    "parent_id": task.get("parent_id"),
                    "before": {"labels": labels, "priority": priority},
                    "update": update_body,
                    "close": close,
                    "owner_added": owner_added,
                }
            )

    return plan


def apply_plan(client: TodoistClient, plan: list[dict[str, Any]], *, actor: str, sleep_s: float) -> None:
    for item in plan:
        task_id = item["task_id"]
        if item["update"]:
            updated = client.update_task(task_id, item["update"])
            log_event.append_event(
                "todoist_hygiene",
                f"task:{task_id}",
                actor,
                {
                    "action": "update",
                    "idempotency_key": f"todoist-hygiene:update:{task_id}:{log_event.payload_hash(item['update'])}",
                    "planned": item,
                    "result": {"id": updated.get("id")},
                },
                CORRELATION_ID,
            )
            time.sleep(sleep_s)
        if item["close"]:
            client.close_task(task_id)
            log_event.append_event(
                "todoist_hygiene",
                f"task:{task_id}",
                actor,
                {
                    "action": "close",
                    "idempotency_key": f"todoist-hygiene:close:{task_id}",
                    "planned": item,
                },
                CORRELATION_ID,
            )
            time.sleep(sleep_s)


def summarize(plan: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "updates": len([item for item in plan if item["update"]]),
        "closes": len([item for item in plan if item["close"]]),
        "owner_labels_added": len([item for item in plan if item.get("owner_added")]),
        "priority_updates": len([item for item in plan if "priority" in item["update"]]),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--project-id", default=ALLOWED_PROJECT_ID)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--actor", default="codex-pane2")
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args(argv)

    token = token_from_env(args.env_file)
    client = TodoistClient(token)
    project = client.project(args.project_id)
    verify_allowed_project(project, args.project_id)
    tasks = client.tasks_for_project(args.project_id)
    plan = build_plan(tasks, args.project_id)
    payload = {
        "apply": args.apply,
        "project": {"id": args.project_id, "name": project.get("name"), "is_shared": project.get("is_shared")},
        "summary": summarize(plan),
        "plan": plan,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if args.apply:
        apply_plan(client, plan, actor=args.actor, sleep_s=args.sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
