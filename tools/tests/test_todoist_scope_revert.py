from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import todoist_scope_revert as revert


SATORY_ID = "6gJ5j8PRVVCWpgCq"


def _sync() -> dict:
    return {
        "projects": [
            {"id": SATORY_ID, "name": "Фабрика Satory ВКО", "is_deleted": False, "is_archived": False},
            {"id": "personal", "name": "Личное", "is_deleted": False, "is_archived": False},
        ],
        "sections": [
            {"id": "satory-section", "project_id": SATORY_ID, "name": "В работе", "is_deleted": False},
            {"id": "personal-section", "project_id": "personal", "name": "Входящие", "is_deleted": False},
        ],
        "items": [
            {"id": "satory-task", "project_id": SATORY_ID, "labels": ["исполнитель:Мади"]},
            {"id": "personal-task", "project_id": "personal", "labels": ["Зере", "отдел:Операции", "проект:Личное"], "content": "Купить книгу"},
        ],
        "notes": [
            {"id": "satory-note", "item_id": "satory-task", "content": "Русский"},
            {"id": "personal-note", "item_id": "personal-task", "content": "Русский"},
        ],
        "labels": [
            {"id": "label-personal", "name": "Зере"},
            {"id": "label-satory", "name": "исполнитель:Мади"},
        ],
    }


def test_revert_plan_excludes_satory_and_restores_personal_rows() -> None:
    rows = [
        {"action": "update_project", "id": SATORY_ID, "before": "Satory VKO Factory", "after": "Фабрика Satory ВКО"},
        {"action": "update_project", "id": "personal", "before": "Personal", "after": "Личное"},
        {"action": "update_section", "id": "personal-section", "before": "Intake / Triage", "after": "Входящие"},
        {"action": "update_task", "id": "satory-task", "before": {"content": "Satory"}, "after": {"content": "Сатори"}},
        {"action": "update_task", "id": "personal-task", "before": {"content": "Buy the book"}, "after": {"content": "Купить книгу"}},
        {"action": "update_note", "id": "personal-note", "before": "If blocked, write blocker.", "after": "Если заблокировано, напишите блокер."},
        {"action": "update_label", "id": "label-personal", "before": "Zere", "after": "Зере"},
    ]

    plan, skipped = revert.build_revert_plan(rows, _sync())

    by_action = {(row["action"], row["id"]): row for row in plan}
    assert ("update_project", "personal") in by_action
    assert ("update_section", "personal-section") in by_action
    assert by_action[("update_task", "personal-task")]["before"] == {"content": "Buy the book"}
    assert ("update_note", "personal-note") in by_action
    assert ("update_label", "label-personal") in by_action
    assert ("update_project", SATORY_ID) not in by_action
    assert ("update_task", "satory-task") not in by_action
    assert any(row["reason"] == "satory task" for row in skipped)


def test_revert_plan_is_idempotent_after_receipt_backed_apply() -> None:
    rows = [
        {"action": "update_project", "id": "personal", "before": "Personal", "after": "Личное"},
        {"action": "update_section", "id": "personal-section", "before": "Intake / Triage", "after": "Входящие"},
        {"action": "update_task", "id": "personal-task", "before": {"content": "Buy the book", "labels": ["Zere"]}},
        {"action": "update_note", "id": "personal-note", "before": "If blocked, write blocker."},
        {"action": "update_label", "id": "label-personal", "before": "Zere", "after": "Зере"},
    ]
    sync = _sync()
    sync["projects"][1]["name"] = "Personal"
    sync["sections"][1]["name"] = "Intake / Triage"
    sync["items"][1]["content"] = "Buy the book"
    sync["items"][1]["labels"] = ["Zere"]
    sync["notes"][1]["content"] = "If blocked, write blocker."
    sync["labels"][0]["name"] = "Zere"

    plan, skipped = revert.build_revert_plan(rows, sync)

    assert plan == []
    assert {row["reason"] for row in skipped} == {"already reverted"}


def test_revert_plan_strips_factory_labels_from_non_satory_tasks() -> None:
    rows = [
        {
            "action": "update_task",
            "id": "personal-task",
            "before": {"labels": ["Zere", "исполнитель:Мади", "отдел:Operations", "проект:Personal"]},
        },
    ]

    plan, skipped = revert.build_revert_plan(rows, _sync())

    assert skipped == []
    assert plan == [
        {
            "action": "update_task",
            "id": "personal-task",
            "before": {"labels": ["Zere"]},
            "current_project_id": "personal",
        }
    ]


def test_revert_plan_stays_clean_after_factory_labels_are_stripped() -> None:
    rows = [
        {
            "action": "update_task",
            "id": "personal-task",
            "before": {"labels": ["Zere", "исполнитель:Мади", "отдел:Operations", "проект:Personal"]},
        },
    ]
    sync = _sync()
    sync["items"][1]["labels"] = ["Zere"]

    plan, skipped = revert.build_revert_plan(rows, sync)

    assert plan == []
    assert skipped == [{"action": "update_task", "id": "personal-task", "reason": "already reverted"}]


def test_revert_plan_uses_earliest_before_value_for_conflicting_receipts() -> None:
    rows = [
        {"action": "update_task", "id": "personal-task", "before": {"content": "Original English"}},
        {"action": "update_task", "id": "personal-task", "before": {"content": "Later Russian"}},
    ]
    sync = _sync()
    sync["items"][1]["content"] = "Later Russian"

    plan, _ = revert.build_revert_plan(rows, sync)

    assert plan == [
        {
            "action": "update_task",
            "id": "personal-task",
            "before": {"content": "Original English"},
            "current_project_id": "personal",
        }
    ]


def test_apply_uses_sync_api_for_task_label_updates(monkeypatch) -> None:
    calls: list[dict] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"sync_status": {next(iter(calls[-1]["commands"])): "ok"}}

    def fake_post(url, headers=None, data=None, timeout=None):  # noqa: ANN001
        commands = __import__("json").loads(data["commands"])
        calls.append({"url": url, "headers": headers, "commands": {commands[0]["uuid"]: commands[0]}})
        return Response()

    monkeypatch.setattr(revert.requests, "post", fake_post)
    client = SimpleNamespace(headers={"Authorization": "Bearer test"}, update_task=lambda *args, **kwargs: None)

    result = revert.apply_revert_plan(client, [{"action": "update_task", "id": "personal-task", "before": {"labels": ["Zere"]}}], 0)

    assert result == {"counts": {"update_task": 1}, "errors": []}
    command = next(iter(calls[0]["commands"].values()))
    assert command["type"] == "item_update"
    assert command["args"] == {"id": "personal-task", "labels": ["Zere"]}
