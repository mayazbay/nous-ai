from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import pytest

import todoist_hygiene_migrate as hygiene


def test_subtasks_inherit_planned_parent_owner_label() -> None:
    tasks = [
        {
            "id": "parent",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "Parent task",
            "labels": [],
            "priority": 2,
        },
        {
            "id": "child",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "Child task",
            "labels": [],
            "priority": 2,
            "parent_id": "parent",
        },
    ]

    plan = {item["task_id"]: item for item in hygiene.build_plan(tasks, hygiene.ALLOWED_PROJECT_ID)}

    assert plan["parent"]["update"]["labels"] == [hygiene.DEFAULT_OWNER_LABEL]
    assert plan["child"]["update"]["labels"] == [hygiene.DEFAULT_OWNER_LABEL]


def test_explicit_keona_title_owners_become_owner_labels() -> None:
    tasks = [
        {
            "id": "money",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "KEONA 12:00: Madi/accountant — провести advance payment path",
            "labels": ["keona"],
            "priority": 4,
        },
        {
            "id": "legal",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "KEONA 12:00: Nazel/Roza — подготовить юридические вопросы",
            "labels": ["keona"],
            "priority": 4,
        },
        {
            "id": "infra",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "KEONA/Infrastructure: обновить GStack после защиты dirty local skill tree",
            "labels": ["keona"],
            "priority": 3,
        },
    ]

    plan = {item["task_id"]: item for item in hygiene.build_plan(tasks, hygiene.ALLOWED_PROJECT_ID)}

    assert plan["money"]["update"]["labels"] == ["keona", "исполнитель:Мади", "исполнитель:Бухгалтер"]
    assert plan["legal"]["update"]["labels"] == ["keona", "исполнитель:Назель", "исполнитель:Роза"]
    assert plan["infra"]["update"]["labels"] == ["keona", hygiene.DEFAULT_OWNER_LABEL]


def test_default_priority_status_receipts_are_closed_not_reprioritized() -> None:
    tasks = [
        {
            "id": "receipt",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "AI Factory D0: Pane 1 (Sonnet) 4 slices done",
            "labels": ["factory", "ИИ-предложено"],
            "priority": 1,
        }
    ]

    plan = hygiene.build_plan(tasks, hygiene.ALLOWED_PROJECT_ID)

    assert plan[0]["close"] is True
    assert "priority" not in plan[0]["update"]


def test_default_priority_work_items_get_inferred_priority() -> None:
    tasks = [
        {
            "id": "data",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "Data residency КЗ",
            "labels": ["factory"],
            "priority": 1,
        },
        {
            "id": "cerebro",
            "project_id": hygiene.ALLOWED_PROJECT_ID,
            "content": "Поиск ТС",
            "labels": ["Cerebro"],
            "priority": 1,
        },
    ]

    plan = {item["task_id"]: item for item in hygiene.build_plan(tasks, hygiene.ALLOWED_PROJECT_ID)}

    assert plan["data"]["update"]["priority"] == 4
    assert plan["cerebro"]["update"]["priority"] == 3


def test_build_plan_refuses_tasks_outside_allowlisted_project() -> None:
    tasks = [
        {
            "id": "wrong",
            "project_id": "personal-project",
            "content": "Wrong project task",
            "labels": [],
            "priority": 1,
        }
    ]

    with pytest.raises(hygiene.HygieneError, match="outside allowlisted project"):
        hygiene.build_plan(tasks, hygiene.ALLOWED_PROJECT_ID)
