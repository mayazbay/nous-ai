from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import satory_todoist_deep_audit as audit


SATORY_ID = "6gJ5j8PRVVCWpgCq"


def _item(task_id: str, project_id: str = SATORY_ID, **overrides):
    base = {
        "id": task_id,
        "content": "AI task",
        "description": "Notion: https://www.notion.so/source\nDrive: https://drive.google.com/file/d/abc/view",
        "project_id": project_id,
        "section_id": "s1",
        "labels": ["исполнитель:AI-фабрика", "отдел:AI-фабрика", "проект:Фабрика-Satory-ВКО"],
        "priority": 4,
        "checked": False,
        "completed_at": None,
        "is_deleted": False,
        "note_count": 1,
    }
    base.update(overrides)
    return base


def _sync():
    return {
        "projects": [
            {"id": SATORY_ID, "name": "Фабрика Satory ВКО", "is_deleted": False, "is_archived": False},
            {"id": "personal", "name": "Личное", "is_deleted": False, "is_archived": False},
        ],
        "sections": [
            {"id": "s1", "project_id": SATORY_ID, "name": "⚙️ Фабрика", "is_deleted": False, "is_archived": False},
            {"id": "p1", "project_id": "personal", "name": "Private", "is_deleted": False, "is_archived": False},
        ],
        "labels": [],
        "items": [
            _item("t1"),
            _item("t2", description="", note_count=0, labels=["исполнитель:Мади", "отдел:Продажи"]),
            _item("p1", project_id="personal", section_id="p1", content="Do not include personal"),
        ],
        "notes": [
            {
                "id": "n1",
                "item_id": "t1",
                "content": "AI: проверь статус. token=super-secret",
                "posted_at": "2026-05-14T05:00:00Z",
            },
            {
                "id": "n2",
                "item_id": "p1",
                "content": "personal comment",
                "posted_at": "2026-05-14T05:00:00Z",
            },
        ],
    }


def test_deep_audit_is_satory_only_and_includes_comments() -> None:
    report = audit.build_deep_audit(_sync())

    assert report["scope"]["personal_projects_touched"] == 0
    assert report["counts"]["active_tasks"] == 2
    assert report["counts"]["comments"] == 1
    assert {row["task_id"] for row in report["tasks"]} == {"t1", "t2"}
    assert report["comments"][0]["note_id"] == "n1"
    assert "REDACTED" in report["comments"][0]["content"]
    assert "personal" not in {row["task_id"] for row in report["comments"]}


def test_factory_proof_comment_does_not_become_new_ai_request() -> None:
    row = audit.comment_row(
        {
            "id": "proof-note",
            "item_id": "t1",
            "content": "AI-фабрика взяла задачу в one-beam очередь.\nEvent: `todoist-task:t1:abc`\nProof: `pages/audits/SATORY-AI-FACTORY-QUEUE-2026-05-19.md`",
            "posted_at": "2026-05-19T09:44:54Z",
        }
    )

    assert row["intent"] == "context"


def test_deep_audit_routes_ai_ready_and_contextless_tasks() -> None:
    report = audit.build_deep_audit(_sync())
    by_id = {row["task_id"]: row for row in report["tasks"]}

    assert by_id["t1"]["factory_route"] == "ready_for_ai_factory"
    assert by_id["t1"]["proof_flags"]["close_ready"] is True
    assert by_id["t1"]["close_gate"] == "ready_to_close"
    assert by_id["t2"]["factory_route"] == "needs_source_enrichment"
    assert by_id["t2"]["close_gate"] == "do_not_close_missing_notion_or_drive_proof"


def test_markdown_mentions_close_gate_and_every_task(tmp_path: Path) -> None:
    report = audit.build_deep_audit(_sync())
    text = audit.render_markdown(report, tmp_path / "audit.json")

    assert "Не закрывать и не удалять" in text
    assert "Proof-path health" in text
    assert "AI task (`t1`)" in text
    assert "AI task (`t2`)" in text
    assert "Комментарии:" in text


def test_index_is_small_gbrain_friendly_and_links_full_artifacts(tmp_path: Path) -> None:
    report = audit.build_deep_audit(_sync())
    report["status"] = "done"
    text = audit.render_index(report, tmp_path / "audit.json", tmp_path / "audit.md")

    assert "короткий специально" in text
    assert "Полный Markdown-аудит" in text
    assert "Не закрывать и не удалять" in text
    assert "Proof-path health" in text
    assert "`Фабрика Satory ВКО`" in text


def test_drive_path_health_separates_storage_from_active_close_gate() -> None:
    health = audit.drive_proof_path_health({"google_drive": 0, "close_ready": 0})

    assert health["google_drive_storage"] == "approved"
    assert health["active_task_google_drive_count"] == 0
    assert health["active_task_close_ready_count"] == 0
    assert health["interpretation"] == "drive_path_approved_no_active_task_ready_to_close"
