from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import todoist_control_plane_export as export

SATORY_ID = "6gJ5j8PRVVCWpgCq"


def _sync_payload() -> dict:
    return {
        "projects": [
            {"id": SATORY_ID, "name": "Фабрика Satory ВКО", "is_deleted": False, "is_archived": False},
            {"id": "personal", "name": "Личное", "is_deleted": False, "is_archived": False},
        ],
        "sections": [
            {"id": "s1", "project_id": SATORY_ID, "name": "Build", "is_deleted": False, "is_archived": False},
            {"id": "sp", "project_id": "personal", "name": "Personal", "is_deleted": False, "is_archived": False},
        ],
        "labels": [
            {"id": "l1", "name": "исполнитель:AI Factory"},
            {"id": "l2", "name": "отдел:AI Factory"},
        ],
        "notes": [{"id": "n1", "item_id": "t2", "content": "source link"}],
        "items": [
            {
                "id": "t1",
                "content": "Blocked thing",
                "project_id": SATORY_ID,
                "section_id": "s1",
                "labels": ["исполнитель:AI Factory", "отдел:AI Factory", "status:blocked"],
                "priority": 4,
                "description": "",
            },
            {
                "id": "t2",
                "content": "Source backed thing",
                "project_id": SATORY_ID,
                "section_id": "s1",
                "labels": ["исполнитель:AI Factory", "отдел:AI Factory"],
                "priority": 3,
                "description": "",
            },
            {
                "id": "personal-task",
                "content": "Do not export this",
                "project_id": "personal",
                "section_id": "sp",
                "labels": ["исполнитель:Мади", "отдел:Личные-операции"],
                "priority": 4,
                "description": "",
            },
        ],
    }


def test_register_preserves_contextless_as_needs_source() -> None:
    register = export.build_register(_sync_payload(), [], None, completed_days=30)

    by_id = {row["task_id"]: row for row in register["active_tasks"]}
    assert by_id["t1"]["status"] == "blocked"
    assert by_id["t1"]["context_state"] == "needs_source"
    assert by_id["t2"]["context_state"] == "source_backed"
    assert "personal-task" not in by_id
    assert register["counts"]["contextless_active_tasks"] == 1


def test_register_includes_recent_done_tasks() -> None:
    completed = [
        {"task_id": "done1", "content": "Finished", "project_id": SATORY_ID, "section_id": "s1", "completed_at": "2026-05-13T00:00:00Z"},
        {"task_id": "done-personal", "content": "Personal", "project_id": "personal", "section_id": "sp", "completed_at": "2026-05-13T00:00:00Z"},
    ]

    register = export.build_register(_sync_payload(), completed, None, completed_days=30)

    assert register["counts"]["recent_completed_tasks"] == 1
    assert register["recent_done_tasks"][0]["status"] == "done"
    assert register["recent_done_tasks"][0]["project"] == "Фабрика Satory ВКО"


def test_write_outputs_creates_markdown_json_csv(tmp_path: Path) -> None:
    register = export.build_register(_sync_payload(), [], None, completed_days=30)
    md = tmp_path / "register.md"
    js = tmp_path / "register.json"
    csv = tmp_path / "register.csv"
    queue = tmp_path / "queue.md"

    export.write_outputs(register, markdown_path=md, json_path=js, csv_path=csv, queue_path=queue)

    assert "# Реестр контрольной плоскости Todoist" in md.read_text(encoding="utf-8")
    assert '"active_tasks"' in js.read_text(encoding="utf-8")
    csv_text = csv.read_text(encoding="utf-8")
    assert "task_id,status,content" in csv_text
    assert "needs_source" in csv_text
    queue_text = queue.read_text(encoding="utf-8")
    assert "# Очередь обогащения контекста Todoist" in queue_text
    assert "Инструкция фабрике" in queue_text
    assert "Не добавляй фейковый контекст" in queue_text
    assert "Captured:" not in queue_text
    assert "Contextless tasks:" not in queue_text
