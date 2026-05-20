#!/usr/bin/env python3
"""Receipt-backed rollback for accidental non-Satory Todoist mutations.

Default mode is dry-run. The script reads saved Todoist Russianization audit
plans, finds rows that were applied outside the Satory VKO Factory project, and
builds a reverse plan from recorded `before` values only.
"""

from __future__ import annotations

import argparse
import collections
import json
import time
import uuid
from pathlib import Path
from typing import Any

import requests

from todoist_control_plane_audit import SATORY_TODOIST_PROJECT_ID, SYNC_URL, Todoist, labels_for, satory_project_ids, token_from_env

FACTORY_LABEL_PREFIXES = ("исполнитель:", "отдел:", "проект:", "owner:", "department:", "project:")
TRANSIENT_HTTP_STATUSES = {429, 502, 503, 504}


class RevertError(RuntimeError):
    pass


def load_applied_rows(audit_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("todoist-russianization-plan-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not payload.get("applied"):
            continue
        for index, row in enumerate(payload.get("plan") or []):
            if isinstance(row, dict):
                item = dict(row)
                item["_source_plan"] = str(path)
                item["_source_index"] = index
                rows.append(item)
    return rows


def live_maps(sync: dict[str, Any]) -> dict[str, Any]:
    projects = {str(row.get("id")): row for row in sync.get("projects", []) if isinstance(row, dict)}
    sections = {str(row.get("id")): row for row in sync.get("sections", []) if isinstance(row, dict)}
    items = {str(row.get("id")): row for row in sync.get("items", []) if isinstance(row, dict)}
    notes = {
        str(row.get("id")): row
        for row in sync.get("notes", [])
        if isinstance(row, dict) and not row.get("is_deleted")
    }
    labels = {str(row.get("id")): row for row in sync.get("labels", []) if isinstance(row, dict)}
    allowed_projects = satory_project_ids(sync) or {SATORY_TODOIST_PROJECT_ID}
    satory_label_names = {
        label
        for item in items.values()
        if str(item.get("project_id") or "") in allowed_projects
        for label in labels_for(item)
    }
    return {
        "projects": projects,
        "sections": sections,
        "items": items,
        "notes": notes,
        "labels": labels,
        "allowed_projects": allowed_projects,
        "satory_label_names": satory_label_names,
    }


def _first_field(target: dict[str, Any], key: str, value: Any) -> None:
    if key not in target:
        target[key] = value


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        return sorted(map(str, left)) == sorted(map(str, right))
    return left == right


def _needs_field_revert(current: dict[str, Any], before: dict[str, Any]) -> bool:
    return any(not _same_value(current.get(key), value) for key, value in before.items())


def _factory_metadata_label(label: Any) -> bool:
    text = str(label)
    return any(text.startswith(prefix) for prefix in FACTORY_LABEL_PREFIXES)


def _target_task_fields(current: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    target = dict(before)
    labels = target.get("labels")
    if isinstance(labels, list):
        # Factory labels are global Todoist labels. If they were added to
        # non-Satory tasks, remove them instead of trying to rename shared
        # label objects that Satory still needs.
        target["labels"] = [label for label in labels if not _factory_metadata_label(label)]
    return target


def sync_update_tasks_batch(client: Todoist, updates: list[tuple[str, dict[str, Any]]], chunk_size: int = 50) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for start in range(0, len(updates), chunk_size):
        chunk = updates[start : start + chunk_size]
        command_to_task: dict[str, str] = {}
        commands = []
        for task_id, fields in chunk:
            command_id = str(uuid.uuid4())
            command_to_task[command_id] = task_id
            args = {"id": task_id, **fields}
            if isinstance(args.get("labels"), list):
                args["labels"] = list(map(str, args["labels"]))
            commands.append(
                {
                    "type": "item_update",
                    "uuid": command_id,
                    "args": args,
                }
            )
        try:
            response = todoist_sync_post_with_retry(
                client,
                data={"commands": json.dumps(commands, ensure_ascii=False, separators=(",", ":"))},
            )
        except requests.HTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            for task_id in command_to_task.values():
                errors.append({"action": "update_task", "id": task_id, "status": status, "error": str(exc)[:500]})
            continue
        payload = response.json()
        statuses = payload.get("sync_status") or {}
        for command_id, task_id in command_to_task.items():
            status = statuses.get(command_id)
            if status != "ok":
                errors.append({"action": "update_task", "id": task_id, "error": "sync_status", "detail": repr(status)[:500]})
    return errors


def retry_after_seconds(response: requests.Response | None, fallback: float) -> float:
    if response is None:
        return fallback
    raw = response.headers.get("Retry-After")
    try:
        return max(float(raw), fallback) if raw else fallback
    except ValueError:
        return fallback


def todoist_sync_post_with_retry(client: Todoist, data: dict[str, Any], attempts: int = 4) -> requests.Response:
    delay = 15.0
    for attempt in range(attempts):
        response = requests.post(
            SYNC_URL,
            headers={"Authorization": client.headers["Authorization"]},
            data=data,
            timeout=30,
        )
        try:
            response.raise_for_status()
            return response
        except requests.HTTPError as exc:
            status = getattr(response, "status_code", None)
            if status not in TRANSIENT_HTTP_STATUSES or attempt == attempts - 1:
                raise exc
            time.sleep(retry_after_seconds(response, delay))
            delay *= 2
    raise RevertError("Todoist Sync API retry loop exhausted")


def todoist_sync_with_retry(client: Todoist, attempts: int = 4) -> dict[str, Any]:
    delay = 15.0
    for attempt in range(attempts):
        try:
            return client.sync()
        except requests.HTTPError as exc:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            if status not in TRANSIENT_HTTP_STATUSES or attempt == attempts - 1:
                raise
            time.sleep(retry_after_seconds(response, delay))
            delay *= 2
    raise RevertError("Todoist sync retry loop exhausted")


def build_revert_plan(rows: list[dict[str, Any]], sync: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    maps = live_maps(sync)
    project_reverts: dict[str, dict[str, Any]] = {}
    section_reverts: dict[str, dict[str, Any]] = {}
    task_reverts: dict[str, dict[str, Any]] = {}
    note_reverts: dict[str, dict[str, Any]] = {}
    label_reverts: dict[str, dict[str, Any]] = {}
    skipped: list[dict[str, Any]] = []

    for row in rows:
        action = row.get("action")
        row_id = str(row.get("id") or row.get("task_id") or "")
        if not row_id:
            continue

        if action == "update_project":
            if row_id in maps["allowed_projects"]:
                skipped.append({"action": action, "id": row_id, "reason": "satory project"})
                continue
            current = maps["projects"].get(row_id)
            if not current:
                skipped.append({"action": action, "id": row_id, "reason": "project missing"})
                continue
            if current.get("name") == row.get("before"):
                skipped.append({"action": action, "id": row_id, "reason": "already reverted"})
                continue
            project_reverts.setdefault(row_id, {"action": "update_project", "id": row_id, "before": row.get("before"), "current": current.get("name")})

        elif action == "update_section":
            section = maps["sections"].get(row_id)
            if not section:
                skipped.append({"action": action, "id": row_id, "reason": "section missing"})
                continue
            if str(section.get("project_id") or "") in maps["allowed_projects"]:
                skipped.append({"action": action, "id": row_id, "reason": "satory section"})
                continue
            if section.get("name") == row.get("before"):
                skipped.append({"action": action, "id": row_id, "reason": "already reverted"})
                continue
            section_reverts.setdefault(row_id, {"action": "update_section", "id": row_id, "before": row.get("before"), "current": section.get("name")})

        elif action == "update_task":
            item = maps["items"].get(row_id)
            if not item:
                skipped.append({"action": action, "id": row_id, "reason": "task missing or completed"})
                continue
            if str(item.get("project_id") or "") in maps["allowed_projects"]:
                skipped.append({"action": action, "id": row_id, "reason": "satory task"})
                continue
            before = row.get("before") if isinstance(row.get("before"), dict) else {}
            before = _target_task_fields(item, before)
            target = task_reverts.setdefault(row_id, {"action": "update_task", "id": row_id, "before": {}, "current_project_id": item.get("project_id")})
            for key, value in before.items():
                _first_field(target["before"], key, value)

        elif action == "update_note":
            note = maps["notes"].get(row_id)
            if not note:
                skipped.append({"action": action, "id": row_id, "reason": "note missing"})
                continue
            item_id = str(note.get("item_id") or note.get("task_id") or note.get("parent_id") or row.get("item_id") or "")
            item = maps["items"].get(item_id)
            if item and str(item.get("project_id") or "") in maps["allowed_projects"]:
                skipped.append({"action": action, "id": row_id, "reason": "satory note"})
                continue
            if note.get("content") == row.get("before"):
                skipped.append({"action": action, "id": row_id, "reason": "already reverted"})
                continue
            note_reverts.setdefault(row_id, {"action": "update_note", "id": row_id, "before": row.get("before"), "item_id": item_id})

        elif action == "update_label":
            label = maps["labels"].get(row_id)
            after = str(row.get("after") or "")
            if after in maps["satory_label_names"]:
                skipped.append({"action": action, "id": row_id, "reason": "label used by Satory task", "label": after})
                continue
            if not label:
                skipped.append({"action": action, "id": row_id, "reason": "label missing"})
                continue
            if label.get("name") == row.get("before"):
                skipped.append({"action": action, "id": row_id, "reason": "already reverted"})
                continue
            label_reverts.setdefault(row_id, {"action": "update_label", "id": row_id, "before": row.get("before"), "current": label.get("name")})

    plan = list(project_reverts.values()) + list(section_reverts.values()) + list(label_reverts.values())
    for row in task_reverts.values():
        item = maps["items"].get(str(row.get("id")))
        if not row.get("before") or (item and not _needs_field_revert(item, row["before"])):
            skipped.append({"action": "update_task", "id": row.get("id"), "reason": "already reverted"})
            continue
        plan.append(row)
    plan += list(note_reverts.values())
    return plan, skipped


def apply_revert_plan(client: Todoist, plan: list[dict[str, Any]], sleep: float) -> dict[str, Any]:
    counts: collections.Counter[str] = collections.Counter()
    errors: list[dict[str, Any]] = []
    pending_task_updates: list[tuple[str, dict[str, Any]]] = []
    for row in plan:
        try:
            action = row["action"]
            if action == "update_project":
                client.request("POST", f"/projects/{row['id']}", json={"name": row["before"]})
            elif action == "update_section":
                client.request("POST", f"/sections/{row['id']}", json={"name": row["before"]})
            elif action == "update_label":
                client.request("POST", f"/labels/{row['id']}", json={"name": row["before"]})
            elif action == "update_task":
                pending_task_updates.append((row["id"], dict(row["before"])))
                continue
            elif action == "update_note":
                client.request("POST", f"/comments/{row['id']}", json={"content": row["before"]})
            else:
                raise RevertError(f"unknown action: {action}")
            counts[action] += 1
            time.sleep(sleep)
        except requests.HTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            errors.append({"action": row.get("action"), "id": row.get("id"), "status": status, "error": str(exc)[:500]})
        except Exception as exc:  # noqa: BLE001 - rollback must report every row, not crash on first API miss.
            errors.append({"action": row.get("action"), "id": row.get("id"), "error": exc.__class__.__name__, "detail": str(exc)[:500]})
    if pending_task_updates:
        batch_errors = sync_update_tasks_batch(client, pending_task_updates)
        errors.extend(batch_errors)
        counts["update_task"] += len(pending_task_updates) - len(batch_errors)
    return {"counts": dict(counts), "errors": errors}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, default=Path("pages/audits"))
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    client = Todoist(token_from_env(args.env_file))
    rows = load_applied_rows(args.audit_dir)
    plan, skipped = build_revert_plan(rows, todoist_sync_with_retry(client))
    applied = {"counts": {}, "errors": []}
    if args.apply:
        applied = apply_revert_plan(client, plan, args.sleep)
    payload = {
        "dry_run": not args.apply,
        "source_rows": len(rows),
        "revert_count": len(plan),
        "plan": plan,
        "skipped_count": len(skipped),
        "skipped_samples": skipped[:80],
        "applied": applied,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    else:
        print(f"todoist_scope_revert dry_run={not args.apply} revert_count={len(plan)} errors={len(applied['errors'])}")
    return 0 if not applied["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
