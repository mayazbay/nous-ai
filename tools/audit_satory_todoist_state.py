#!/usr/bin/env python3
"""Read-only Satory Todoist/state.db audit.

This script intentionally performs only GET/read operations. It audits the
allowed Satory VKO Factory project, follows Todoist pagination, and reconciles
state.db proposal links without mutating Todoist or the SQLite database.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import requests


TODOIST_BASE = "https://api.todoist.com/api/v1"
ALLOWED_PROJECT_ID = "6gJ5j8PRVVCWpgCq"
PERSONAL_PROJECT_IDS = {
    "6fhm35CG93P2jff9": "Satory AI personal project",
}
AI_LABEL_RU = "\u0418\u0418-\u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u043e"
AI_LABEL_LEGACY = "ai-proposed"
OWNER_LABEL_PREFIXES = ("исполнитель:", "owner:", "assignee:")


class AuditError(RuntimeError):
    """Raised when the audit cannot safely run."""


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def token_from_env(env_file: Path | None) -> str:
    token = os.environ.get("SATORY_TODOIST_TOKEN") or os.environ.get("TODOIST_API_TOKEN")
    if token:
        return token
    if env_file:
        values = load_env_file(env_file)
        token = values.get("SATORY_TODOIST_TOKEN") or values.get("TODOIST_API_TOKEN")
        if token:
            return token
    raise AuditError("SATORY_TODOIST_TOKEN / TODOIST_API_TOKEN not found")


class TodoistReadOnly:
    def __init__(self, token: str) -> None:
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = requests.get(f"{TODOIST_BASE}{path}", headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise AuditError(f"Todoist {path} returned non-object JSON")
        return payload

    def project(self, project_id: str) -> dict[str, Any]:
        return self.get(f"/projects/{project_id}")

    def tasks_for_project(self, project_id: str) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            params = {"project_id": project_id}
            if cursor:
                params["cursor"] = cursor
            payload = self.get("/tasks", params=params)
            page = payload.get("results", [])
            if not isinstance(page, list):
                raise AuditError("Todoist /tasks response has non-list results")
            tasks.extend(t for t in page if isinstance(t, dict))
            next_cursor = payload.get("next_cursor")
            if not next_cursor:
                return tasks
            if next_cursor in seen_cursors:
                raise AuditError(f"Todoist pagination cursor loop detected: {next_cursor}")
            seen_cursors.add(next_cursor)
            cursor = str(next_cursor)

    def task(self, task_id: str) -> dict[str, Any]:
        return self.get(f"/tasks/{task_id}")


def parse_json_array(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def sqlite_tables(db_path: Path) -> list[str]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [r[0] for r in rows]


def count_table(db_path: Path, table: str) -> int | None:
    if table not in sqlite_tables(db_path):
        return None
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def proposal_rows(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists() or "proposals" not in sqlite_tables(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT proposal_uuid, created_at, source_kind, source_ref, status,
                   todoist_task_ids, length(payload_json) AS payload_bytes
            FROM proposals
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def labels_for(task: dict[str, Any]) -> list[str]:
    labels = task.get("labels") or []
    return [str(label) for label in labels] if isinstance(labels, list) else []


def has_owner_signal(task: dict[str, Any]) -> bool:
    if task.get("assignee_id") or task.get("responsible_uid"):
        return True
    return any(label.startswith(OWNER_LABEL_PREFIXES) for label in labels_for(task))


def task_sample(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task.get("id"),
        "content": task.get("content", ""),
        "labels": labels_for(task),
        "priority": task.get("priority"),
        "parent_id": task.get("parent_id"),
    }


def task_status(task: dict[str, Any]) -> str:
    if task.get("is_deleted"):
        return "deleted"
    if task.get("checked") or task.get("completed_at"):
        return "completed"
    return "active"


def is_test_proposal(proposal: dict[str, Any]) -> bool:
    source_ref = str(proposal.get("source_ref") or "")
    source_kind = str(proposal.get("source_kind") or "")
    return source_kind == "test" or source_ref.startswith("test-")


def classify_proposal_link_risks(proposal_links: list[dict[str, Any]]) -> tuple[list[str], int]:
    missing_links = []
    deleted_links = []
    off_scope_links = []
    ignored_test_links = []

    for proposal in proposal_links:
        test_proposal = is_test_proposal(proposal)
        for link in proposal["linked_tasks"]:
            status = link["status"]
            if test_proposal and (status in {"not_active_in_allowed_project", "deleted"} or link.get("off_scope")):
                ignored_test_links.append(link)
                continue
            if status == "not_active_in_allowed_project":
                missing_links.append(link)
            if status == "deleted":
                deleted_links.append(link)
            if link.get("off_scope"):
                off_scope_links.append(link)

    risks: list[str] = []
    if missing_links:
        risks.append(f"state_linked_tasks_not_active_in_allowed_project:{len(missing_links)}")
    if deleted_links:
        risks.append(f"state_linked_tasks_deleted:{len(deleted_links)}")
    if off_scope_links:
        risks.append(f"state_linked_tasks_off_scope_after_direct_lookup:{len(off_scope_links)}")
    return risks, len(ignored_test_links)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    project_id = args.project_id
    if project_id in PERSONAL_PROJECT_IDS:
        raise AuditError(f"refusing to audit personal project {project_id}: {PERSONAL_PROJECT_IDS[project_id]}")
    if project_id != ALLOWED_PROJECT_ID:
        raise AuditError(f"project {project_id} is not the Satory allowlisted project {ALLOWED_PROJECT_ID}")

    client = TodoistReadOnly(token_from_env(args.env_file))
    project = client.project(project_id)
    if not project.get("is_shared"):
        raise AuditError(f"project {project_id} is_shared={project.get('is_shared')!r}; refusing off-scope audit")

    tasks = client.tasks_for_project(project_id)
    by_id = {str(task.get("id")): task for task in tasks if task.get("id")}
    label_counts = collections.Counter(label for task in tasks for label in labels_for(task))
    ai_ru = [task for task in tasks if AI_LABEL_RU in labels_for(task)]
    ai_legacy = [task for task in tasks if AI_LABEL_LEGACY in labels_for(task)]
    missing_owner = [task for task in tasks if not has_owner_signal(task)]
    default_priority = [task for task in tasks if int(task.get("priority") or 1) <= 1]
    priority_counts = collections.Counter(str(task.get("priority") or 1) for task in tasks)
    subtask_count = sum(1 for task in tasks if task.get("parent_id"))

    tables = sqlite_tables(args.state_db)
    table_counts = {table: count_table(args.state_db, table) for table in tables}
    proposals = proposal_rows(args.state_db)

    proposal_links: list[dict[str, Any]] = []
    for row in proposals:
        task_ids = [str(tid) for tid in parse_json_array(row.get("todoist_task_ids"))]
        linked: list[dict[str, Any]] = []
        for task_id in task_ids:
            if task_id in by_id:
                task = by_id[task_id]
                linked.append(
                    {
                        "task_id": task_id,
                        "lookup": "allowed_project_page",
                        "status": task_status(task),
                        "project_id": task.get("project_id"),
                        "labels": labels_for(task),
                        "content": task.get("content", ""),
                    }
                )
                continue

            item: dict[str, Any] = {
                "task_id": task_id,
                "lookup": "skipped",
                "status": "not_active_in_allowed_project",
                "reason": "direct task lookup disabled to avoid reading outside the allowed project",
            }
            if args.direct_task_lookup:
                task = client.task(task_id)
                task_project = str(task.get("project_id", ""))
                item = {
                    "task_id": task_id,
                    "lookup": "direct_task_get",
                    "status": task_status(task),
                    "project_id": task_project,
                    "off_scope": task_project != project_id,
                    "labels": labels_for(task),
                    "content": task.get("content", ""),
                }
            linked.append(item)
        proposal_links.append(
            {
                "proposal_uuid": row.get("proposal_uuid"),
                "created_at": row.get("created_at"),
                "source_kind": row.get("source_kind"),
                "source_ref": row.get("source_ref"),
                "status": row.get("status"),
                "payload_bytes": row.get("payload_bytes"),
                "task_ids": task_ids,
                "linked_tasks": linked,
            }
        )

    risks: list[str] = []
    if not args.state_db.exists():
        risks.append(f"state_db_missing:{args.state_db}")
    if "todoist_snapshots" not in tables:
        risks.append("todoist_snapshots_table_missing")
    proposal_risks, ignored_test_link_count = classify_proposal_link_risks(proposal_links)
    risks.extend(proposal_risks)
    if missing_owner:
        risks.append(f"active_tasks_missing_owner_signal:{len(missing_owner)}")
    if default_priority:
        risks.append(f"active_tasks_default_priority:{len(default_priority)}")

    return {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "read_only",
        "mutating_methods_used": [],
        "project": {
            "id": project_id,
            "name": project.get("name"),
            "is_shared": project.get("is_shared"),
        },
        "tasks": {
            "active_count": len(tasks),
            "ai_label_ru_count": len(ai_ru),
            "ai_label_legacy_count": len(ai_legacy),
            "subtask_count": subtask_count,
            "owner_signal_missing_count": len(missing_owner),
            "owner_signal_missing_sample": [task_sample(task) for task in missing_owner[:10]],
            "default_priority_count": len(default_priority),
            "default_priority_sample": [task_sample(task) for task in default_priority[:10]],
            "priority_counts": sorted(priority_counts.items()),
            "top_labels": label_counts.most_common(15),
        },
        "state_db": {
            "path": str(args.state_db),
            "exists": args.state_db.exists(),
            "tables": tables,
            "counts": table_counts,
            "proposal_count": len(proposals),
            "ignored_test_link_count": ignored_test_link_count,
        },
        "proposal_links": proposal_links,
        "risks": risks,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Satory Todoist State Audit",
        "",
        f"Captured UTC: `{result['captured_at']}`",
        "",
        "## Scope",
        "",
        f"- Mode: `{result['mode']}`",
        "- Mutating methods used: none",
        f"- Project: `{result['project']['name']}` (`{result['project']['id']}`)",
        f"- Project shared: `{result['project']['is_shared']}`",
        "",
        "## Live Todoist",
        "",
        f"- Active tasks in allowed project: `{result['tasks']['active_count']}`",
        f"- Subtasks in allowed project: `{result['tasks']['subtask_count']}`",
        f"- Active tasks with `{AI_LABEL_RU}`: `{result['tasks']['ai_label_ru_count']}`",
        f"- Active tasks with legacy `{AI_LABEL_LEGACY}`: `{result['tasks']['ai_label_legacy_count']}`",
        f"- Active tasks missing owner signal: `{result['tasks']['owner_signal_missing_count']}`",
        f"- Active tasks at default priority: `{result['tasks']['default_priority_count']}`",
        f"- Priority distribution: `{result['tasks']['priority_counts']}`",
        "- Top labels:",
    ]
    for label, count in result["tasks"]["top_labels"]:
        lines.append(f"  - `{label}`: `{count}`")

    state = result["state_db"]
    lines.extend(
        [
            "",
            "## State DB",
            "",
            f"- Path: `{state['path']}`",
            f"- Exists: `{state['exists']}`",
            f"- Tables: `{', '.join(state['tables']) if state['tables'] else 'none'}`",
            f"- Proposal rows: `{state['proposal_count']}`",
            "- Table counts:",
        ]
    )
    for table, count in state["counts"].items():
        lines.append(f"  - `{table}`: `{count}`")

    lines.extend(["", "## Proposal Links", ""])
    if not result["proposal_links"]:
        lines.append("- No proposal rows found.")
    for proposal in result["proposal_links"]:
        lines.append(
            f"- `{proposal['proposal_uuid']}` status=`{proposal['status']}` source=`{proposal['source_kind']}:{proposal['source_ref']}`"
        )
        if not proposal["task_ids"]:
            lines.append("  - no Todoist task IDs recorded")
        for linked in proposal["linked_tasks"]:
            content = str(linked.get("content") or "").replace("\n", " ")[:100]
            extra = ""
            if linked.get("off_scope"):
                extra = " off_scope=true"
            lines.append(
                f"  - task `{linked['task_id']}` status=`{linked['status']}` lookup=`{linked['lookup']}` project=`{linked.get('project_id', '')}`{extra} {content}"
            )
            if linked.get("reason"):
                lines.append(f"    - reason: {linked['reason']}")

    lines.extend(["", "## Risks", ""])
    if result["risks"]:
        lines.extend(f"- `{risk}`" for risk in result["risks"])
    else:
        lines.append("- none detected")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default=ALLOWED_PROJECT_ID)
    parser.add_argument(
        "--state-db",
        type=Path,
        default=Path.home() / "nous-agaas" / "tenants" / "satory" / "state.db",
    )
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument(
        "--direct-task-lookup",
        action="store_true",
        help="GET state.db-linked task IDs that are not active in the allowed project. Read-only, but may read off-scope historical test tasks.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = audit(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
