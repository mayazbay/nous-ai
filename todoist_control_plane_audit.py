#!/usr/bin/env python3
"""Todoist control-plane audit and guarded hygiene repair.

Default mode is read-only. Use --apply only after reviewing the emitted plan.
The script uses Todoist Sync API for complete state inventory and Todoist REST
API for small deterministic repairs: labels, priorities, section creation, and
moving root tasks into an intake section.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests


TODOIST_BASE = "https://api.todoist.com/api/v1"
SYNC_URL = f"{TODOIST_BASE}/sync"
RESOURCE_TYPES = ["projects", "sections", "labels", "items", "notes"]
OWNER_PREFIXES = ("исполнитель:", "owner:", "assignee:")
DEPT_PREFIXES = ("отдел:", "dept:", "department:")
INTAKE_SECTION = "📥 Входящие / Разбор"
INTAKE_SECTION_ALIASES = (INTAKE_SECTION, "📥 Intake / Triage", "Intake / Triage")
SATORY_TODOIST_PROJECT_ID = "6gJ5j8PRVVCWpgCq"
SATORY_PROJECT_NAMES = {"Satory VKO Factory", "Фабрика Satory ВКО"}
PROJECT_LABEL_ALIASES = {
    "Satory VKO Factory": {"проект:Satory-VKO-Factory", "проект:Фабрика-Satory-ВКО"},
    "Фабрика Satory ВКО": {"проект:Satory-VKO-Factory", "проект:Фабрика-Satory-ВКО"},
}


class AuditError(RuntimeError):
    pass


def load_env(path: Path | None) -> dict[str, str]:
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


def token_from_env(env_file: Path | None) -> str:
    token = os.environ.get("SATORY_TODOIST_TOKEN") or os.environ.get("TODOIST_API_TOKEN")
    if token:
        return token
    values = load_env(env_file)
    token = values.get("SATORY_TODOIST_TOKEN") or values.get("TODOIST_API_TOKEN")
    if token:
        return token
    raise AuditError("SATORY_TODOIST_TOKEN / TODOIST_API_TOKEN not found")


class Todoist:
    def __init__(self, token: str) -> None:
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def sync(self) -> dict[str, Any]:
        response = requests.post(
            SYNC_URL,
            headers={"Authorization": self.headers["Authorization"]},
            data={"sync_token": "*", "resource_types": json.dumps(RESOURCE_TYPES, separators=(",", ":"))},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise AuditError("Todoist sync payload was not an object")
        return payload

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(method, f"{TODOIST_BASE}{path}", headers=self.headers, timeout=30, **kwargs)
        response.raise_for_status()
        if response.text.strip():
            return response.json()
        return None

    def create_section(self, name: str, project_id: str) -> dict[str, Any]:
        payload = self.request("POST", "/sections", json={"name": name, "project_id": project_id})
        if not isinstance(payload, dict) or not payload.get("id"):
            raise AuditError(f"section create returned unexpected payload for project {project_id}")
        return payload

    def update_task(self, task_id: str, body: dict[str, Any]) -> None:
        self.request("POST", f"/tasks/{task_id}", json=body)

    def move_task_to_section(self, task_id: str, section_id: str) -> None:
        self.request("POST", f"/tasks/{task_id}/move", json={"section_id": section_id})


def active_project(project: dict[str, Any]) -> bool:
    return not project.get("is_deleted") and not project.get("is_archived")


def active_section(section: dict[str, Any]) -> bool:
    return not section.get("is_deleted") and not section.get("is_archived")


def active_item(item: dict[str, Any]) -> bool:
    return not item.get("is_deleted") and not item.get("checked") and not item.get("completed_at")


def is_satory_project(project: dict[str, Any]) -> bool:
    return str(project.get("id") or "") == SATORY_TODOIST_PROJECT_ID or str(project.get("name") or "") in SATORY_PROJECT_NAMES


def satory_project_ids(sync: dict[str, Any]) -> set[str]:
    return {
        str(project.get("id"))
        for project in sync.get("projects", [])
        if isinstance(project, dict) and active_project(project) and is_satory_project(project)
    }


def is_satory_item(item: dict[str, Any], allowed_project_ids: set[str] | None = None) -> bool:
    project_ids = allowed_project_ids if allowed_project_ids is not None else {SATORY_TODOIST_PROJECT_ID}
    return str(item.get("project_id") or "") in project_ids


def filter_satory_sync(sync: dict[str, Any]) -> dict[str, Any]:
    """Return a Satory-only Todoist Sync payload.

    Todoist labels are global, so mutation planners must only see labels already
    attached to Satory tasks. This prevents clean-up jobs from renaming personal
    projects, labels, sections, or comments.
    """
    allowed_project_ids = satory_project_ids(sync) or {SATORY_TODOIST_PROJECT_ID}
    allowed_items = [
        item
        for item in sync.get("items", [])
        if isinstance(item, dict) and str(item.get("project_id") or "") in allowed_project_ids
    ]
    allowed_item_ids = {str(item.get("id")) for item in allowed_items}
    used_labels = {label for item in allowed_items for label in labels_for(item)}
    payload = dict(sync)
    payload["projects"] = [
        project
        for project in sync.get("projects", [])
        if isinstance(project, dict) and str(project.get("id") or "") in allowed_project_ids
    ]
    payload["sections"] = [
        section
        for section in sync.get("sections", [])
        if isinstance(section, dict) and str(section.get("project_id") or "") in allowed_project_ids
    ]
    payload["items"] = allowed_items
    payload["notes"] = [
        note
        for note in sync.get("notes", [])
        if isinstance(note, dict)
        and str(note.get("item_id") or note.get("task_id") or note.get("parent_id") or "") in allowed_item_ids
    ]
    payload["labels"] = [
        label
        for label in sync.get("labels", [])
        if isinstance(label, dict) and str(label.get("name") or "") in used_labels
    ]
    return payload


def labels_for(item: dict[str, Any]) -> list[str]:
    labels = item.get("labels") or []
    return [str(label) for label in labels] if isinstance(labels, list) else []


def has_prefix(labels: list[str], prefixes: tuple[str, ...]) -> bool:
    return any(any(label.startswith(prefix) for prefix in prefixes) for label in labels)


def clean_label_token(value: str) -> str:
    value = re.sub(r"[^\wА-Яа-яЁё]+", "-", value, flags=re.UNICODE).strip("-")
    return value[:40] or "General"


def normalize_board_project_labels(labels: list[str], project_name: str, project_label: str) -> list[str]:
    aliases = set(PROJECT_LABEL_ALIASES.get(project_name, set()))
    aliases.add(project_label)
    result: list[str] = []
    found = False
    for label in labels:
        if label.startswith("проект:") and label in aliases:
            if not found:
                result.append(project_label)
                found = True
            continue
        result.append(label)
    if not found:
        result.append(project_label)
    return result


def text_blob(item: dict[str, Any], project: dict[str, Any] | None, section: dict[str, Any] | None) -> str:
    parts = [
        str(item.get("content") or ""),
        str(item.get("description") or ""),
        str(project.get("name") if project else ""),
        str(section.get("name") if section else ""),
        " ".join(labels_for(item)),
    ]
    return " ".join(parts).casefold()


def department_for(item: dict[str, Any], project: dict[str, Any] | None, section: dict[str, Any] | None) -> str:
    blob = text_blob(item, project, section)
    if any(s in blob for s in ["keona", "spectra", "maru", "commercial", "pipeline", "revenue"]):
        return "отдел:Продажи"
    if any(s in blob for s in ["erap", "ncanode", "апк", "mergen", "мерген", "дп", "asyl", "асыл", "police"]):
        return "отдел:Доставка"
    if any(s in blob for s in ["contract", "legal", "law", "договор", "юрист", "compliance"]):
        return "отдел:Юристы"
    if any(s in blob for s in ["invoice", "payment", "budget", "finance", "бухгалтер", "оплата"]):
        return "отдел:Финансы"
    if any(s in blob for s in ["gbrain", "openclaw", "factory", "codex", "claude", "goal", "telegram", "litellm", "notion", "todoist"]):
        return "отдел:AI-фабрика"
    if project and str(project.get("inbox_project")).lower() == "true":
        return "отдел:Личные-операции"
    return "отдел:Операции"


def owner_for(department: str) -> str:
    if department in {
        "отдел:Revenue",
        "отдел:Delivery",
        "отдел:Operations",
        "отдел:Personal Ops",
        "отдел:Продажи",
        "отдел:Доставка",
        "отдел:Операции",
        "отдел:Личные-операции",
    }:
        return "исполнитель:Мади"
    if department in {"отдел:Finance", "отдел:Финансы"}:
        return "исполнитель:Бухгалтер"
    if department in {"отдел:Legal", "отдел:Юристы"}:
        return "исполнитель:Юристы"
    return "исполнитель:AI-фабрика"


def priority_for(item: dict[str, Any], department: str) -> int:
    blob = text_blob(item, None, None)
    if any(s in blob for s in ["urgent", "срочно", "critical", "blocker", "блокер", "today", "today"]):
        return 4
    if department in {"отдел:Revenue", "отдел:Delivery", "отдел:Продажи", "отдел:Доставка"}:
        return 3
    if department in {"отдел:AI Factory", "отдел:Legal", "отдел:Finance", "отдел:AI-фабрика", "отдел:Юристы", "отдел:Финансы"}:
        return 2
    return 2


def is_intake_section_name(name: str) -> bool:
    folded = str(name or "").casefold()
    return any(folded == alias.casefold() for alias in INTAKE_SECTION_ALIASES)


def build_audit(sync: dict[str, Any]) -> dict[str, Any]:
    sync = filter_satory_sync(sync)
    projects = [p for p in sync.get("projects", []) if isinstance(p, dict) and active_project(p)]
    sections = [s for s in sync.get("sections", []) if isinstance(s, dict) and active_section(s)]
    items = [i for i in sync.get("items", []) if isinstance(i, dict) and active_item(i)]
    notes = [n for n in sync.get("notes", []) if isinstance(n, dict) and not n.get("is_deleted")]
    labels = [l for l in sync.get("labels", []) if isinstance(l, dict) and not l.get("is_deleted")]

    project_by_id = {str(p.get("id")): p for p in projects}
    section_by_id = {str(s.get("id")): s for s in sections}
    sections_by_project: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for section in sections:
        sections_by_project[str(section.get("project_id"))].append(section)

    active_root_items = [item for item in items if not item.get("parent_id")]
    missing_project = [item for item in items if str(item.get("project_id") or "") not in project_by_id]
    invalid_section = [
        item for item in items if item.get("section_id") and str(item.get("section_id")) not in section_by_id
    ]
    root_no_section = [item for item in active_root_items if not item.get("section_id")]
    subtask_no_section = [item for item in items if item.get("parent_id") and not item.get("section_id")]
    missing_owner = [item for item in items if not item.get("responsible_uid") and not has_prefix(labels_for(item), OWNER_PREFIXES)]
    missing_department = [item for item in items if not has_prefix(labels_for(item), DEPT_PREFIXES)]
    missing_labels = [item for item in items if not labels_for(item)]
    default_priority = [item for item in items if int(item.get("priority") or 1) <= 1]
    no_context = [
        item
        for item in items
        if not str(item.get("description") or "").strip() and int(item.get("note_count") or 0) == 0
    ]

    project_counts = collections.Counter(str(item.get("project_id") or "") for item in items)
    section_counts = collections.Counter(str(item.get("section_id") or "NO_SECTION") for item in items)
    priority_counts = collections.Counter(str(item.get("priority") or 1) for item in items)
    label_counts = collections.Counter(label for item in items for label in labels_for(item))
    note_attachment_count = sum(1 for note in notes if note.get("file_attachment"))

    return {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "counts": {
            "projects": len(projects),
            "sections": len(sections),
            "labels": len(labels),
            "active_tasks": len(items),
            "active_root_tasks": len(active_root_items),
            "active_subtasks": len(items) - len(active_root_items),
            "notes": len(notes),
            "note_file_attachments": note_attachment_count,
        },
        "projects": [
            {
                "id": project_id,
                "name": project_by_id[project_id].get("name"),
                "is_shared": project_by_id[project_id].get("is_shared"),
                "section_count": len(sections_by_project.get(project_id, [])),
                "active_task_count": project_counts.get(project_id, 0),
            }
            for project_id in sorted(project_by_id, key=lambda pid: str(project_by_id[pid].get("name") or ""))
        ],
        "risk_counts": {
            "missing_project": len(missing_project),
            "invalid_section": len(invalid_section),
            "root_no_section": len(root_no_section),
            "subtask_no_section_inherited": len(subtask_no_section),
            "missing_owner": len(missing_owner),
            "missing_department": len(missing_department),
            "missing_labels": len(missing_labels),
            "default_priority": len(default_priority),
            "no_description_or_note": len(no_context),
        },
        "distributions": {
            "priority_counts": sorted(priority_counts.items()),
            "top_labels": label_counts.most_common(30),
            "top_sections": section_counts.most_common(30),
        },
        "samples": {
            "root_no_section": sample_tasks(root_no_section, project_by_id, section_by_id),
            "missing_owner": sample_tasks(missing_owner, project_by_id, section_by_id),
            "missing_department": sample_tasks(missing_department, project_by_id, section_by_id),
            "default_priority": sample_tasks(default_priority, project_by_id, section_by_id),
            "missing_labels": sample_tasks(missing_labels, project_by_id, section_by_id),
        },
        "_objects": {
            "projects": projects,
            "sections": sections,
            "items": items,
        },
    }


def sample_tasks(
    items: list[dict[str, Any]],
    projects: dict[str, dict[str, Any]],
    sections: dict[str, dict[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:
    result = []
    for item in items[:limit]:
        project = projects.get(str(item.get("project_id") or ""))
        section = sections.get(str(item.get("section_id") or ""))
        result.append(
            {
                "id": item.get("id"),
                "content": str(item.get("content") or "")[:120],
                "project": project.get("name") if project else None,
                "section": section.get("name") if section else None,
                "labels": labels_for(item),
                "priority": item.get("priority"),
                "parent_id": item.get("parent_id"),
            }
        )
    return result


def build_plan(audit: dict[str, Any]) -> list[dict[str, Any]]:
    projects = {str(p.get("id")): p for p in audit["_objects"]["projects"]}
    sections = {str(s.get("id")): s for s in audit["_objects"]["sections"]}
    intake_by_project = {
        str(s.get("project_id")): s
        for s in audit["_objects"]["sections"]
        if is_intake_section_name(str(s.get("name") or ""))
    }
    plan: list[dict[str, Any]] = []
    sectionless_projects = {
        str(item.get("project_id"))
        for item in audit["_objects"]["items"]
        if not item.get("parent_id") and not item.get("section_id") and item.get("project_id")
    }
    for project_id in sorted(sectionless_projects):
        if project_id not in intake_by_project:
            project = projects.get(project_id)
            plan.append(
                {
                    "action": "create_section",
                    "project_id": project_id,
                    "project_name": project.get("name") if project else None,
                    "name": INTAKE_SECTION,
                }
            )

    for item in audit["_objects"]["items"]:
        task_id = str(item.get("id") or "")
        if not task_id:
            continue
        project = projects.get(str(item.get("project_id") or ""))
        section = sections.get(str(item.get("section_id") or ""))
        labels = labels_for(item)
        desired = list(labels)

        project_name = str(project.get("name") if project else "Unknown")
        project_label = f"проект:{clean_label_token(project_name)}"
        department = department_for(item, project, section)
        owner = owner_for(department)
        desired = normalize_board_project_labels(desired, project_name, project_label)
        if not has_prefix(labels, DEPT_PREFIXES) and department not in desired:
            desired.append(department)
        if not item.get("responsible_uid") and not has_prefix(labels, OWNER_PREFIXES) and owner not in desired:
            desired.append(owner)

        update: dict[str, Any] = {}
        if desired != labels:
            update["labels"] = desired
        current_priority = int(item.get("priority") or 1)
        inferred_priority = priority_for(item, department)
        if current_priority <= 1 and inferred_priority != current_priority:
            update["priority"] = inferred_priority
        if update:
            plan.append(
                {
                    "action": "update_task",
                    "task_id": task_id,
                    "content": str(item.get("content") or "")[:160],
                    "update": update,
                }
            )

        if not item.get("parent_id") and not item.get("section_id") and item.get("project_id"):
            plan.append(
                {
                    "action": "move_root_task_to_intake",
                    "task_id": task_id,
                    "content": str(item.get("content") or "")[:160],
                    "project_id": str(item.get("project_id")),
                    "section_name": INTAKE_SECTION,
                }
            )
    return plan


def apply_plan(client: Todoist, plan: list[dict[str, Any]], sleep: float) -> dict[str, Any]:
    created_sections: dict[str, str] = {}
    applied = collections.Counter()
    for item in plan:
        action = item["action"]
        if action == "create_section":
            section = client.create_section(item["name"], item["project_id"])
            created_sections[item["project_id"]] = str(section["id"])
            applied[action] += 1
            time.sleep(sleep)
        elif action == "update_task":
            client.update_task(item["task_id"], item["update"])
            applied[action] += 1
            time.sleep(sleep)
        elif action == "move_root_task_to_intake":
            section_id = created_sections.get(item["project_id"]) or item.get("section_id")
            if not section_id:
                # A fresh sync is needed to discover a pre-existing intake section.
                raise AuditError(f"missing target section id for project {item['project_id']}")
            client.move_task_to_section(item["task_id"], section_id)
            applied[action] += 1
            time.sleep(sleep)
    return dict(applied)


def render_markdown(audit: dict[str, Any], plan: list[dict[str, Any]], applied: dict[str, Any] | None) -> str:
    lines = [
        "# Todoist Control-Plane Audit",
        "",
        f"Captured UTC: `{audit['captured_at']}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in audit["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Risk Counts", ""])
    for key, value in audit["risk_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Projects", ""])
    for project in audit["projects"]:
        lines.append(
            f"- `{project['name']}` id=`{project['id']}` shared=`{project['is_shared']}` "
            f"sections=`{project['section_count']}` active_tasks=`{project['active_task_count']}`"
        )
    lines.extend(["", "## Top Labels", ""])
    for label, count in audit["distributions"]["top_labels"]:
        lines.append(f"- `{label}`: `{count}`")
    lines.extend(["", "## Plan Summary", ""])
    counts = collections.Counter(item["action"] for item in plan)
    if counts:
        for action, count in sorted(counts.items()):
            lines.append(f"- `{action}`: `{count}`")
    else:
        lines.append("- no deterministic hygiene actions needed")
    if applied is not None:
        lines.extend(["", "## Applied", ""])
        if applied:
            for action, count in sorted(applied.items()):
                lines.append(f"- `{action}`: `{count}`")
        else:
            lines.append("- none")
    lines.extend(["", "## Samples", ""])
    for name, rows in audit["samples"].items():
        lines.append(f"### {name}")
        if not rows:
            lines.append("- none")
        for row in rows[:10]:
            lines.append(
                f"- `{row['id']}` p=`{row['project']}` s=`{row['section']}` "
                f"prio=`{row['priority']}` labels=`{row['labels']}` — {row['content']}"
            )
    return "\n".join(lines) + "\n"


def serializable_audit(audit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in audit.items() if key != "_objects"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.25)
    args = parser.parse_args(argv)

    client = Todoist(token_from_env(args.env_file))
    audit = build_audit(client.sync())
    plan = build_plan(audit)
    applied = None
    if args.apply:
        # Apply section creates first, then refetch so pre-existing and newly-created
        # intake section IDs are both available for move operations.
        create_plan = [item for item in plan if item["action"] == "create_section"]
        update_plan = [item for item in plan if item["action"] == "update_task"]
        first_applied = apply_plan(client, create_plan + update_plan, args.sleep)
        audit_after_create = build_audit(client.sync())
        projects = {str(p.get("id")): p for p in audit_after_create["_objects"]["projects"]}
        intake_by_project = {
            str(s.get("project_id")): str(s.get("id"))
            for s in audit_after_create["_objects"]["sections"]
            if is_intake_section_name(str(s.get("name") or ""))
        }
        move_plan = []
        for item in build_plan(audit_after_create):
            if item["action"] == "move_root_task_to_intake":
                item["section_id"] = intake_by_project.get(item["project_id"])
                if item["project_id"] not in projects:
                    raise AuditError(f"task move references missing project {item['project_id']}")
                move_plan.append(item)
        second_applied = apply_plan(client, move_plan, args.sleep)
        applied_counter = collections.Counter(first_applied)
        applied_counter.update(second_applied)
        applied = dict(applied_counter)
        audit = build_audit(client.sync())
        plan = build_plan(audit)

    payload = {"audit": serializable_audit(audit), "plan": plan, "applied": applied}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(audit, plan, applied))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
