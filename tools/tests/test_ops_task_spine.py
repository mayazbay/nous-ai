"""Tests for the unified operations task spine."""

from __future__ import annotations

import pathlib
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import ops_task_spine


def _raw_task(**overrides):
    task = {
        "title": "Wire Satory operating system task spine",
        "tenant": "satory",
        "project": "Satory AI",
        "subproject": "Ops Spine",
        "owner": "Asylbek",
        "team": "Integration",
        "priority": "p1",
        "notion_project_id": ops_task_spine.SATORY_NOTION_PROJECT_ID,
        "notion_source_database_id": ops_task_spine.SATORY_SECOND_BRAIN_DATABASE_ID,
        "notion_source_data_source_id": ops_task_spine.SATORY_SECOND_BRAIN_DATA_SOURCE_ID,
        "notion_source_view_id": ops_task_spine.SATORY_SECOND_BRAIN_VIEW_ID,
        "notion_source_view_url": ops_task_spine.SATORY_SECOND_BRAIN_VIEW_URL,
        "notion_source_url": "https://www.notion.so/335cb8f8c69f804c92a0cd2b67dd1547",
        "todoist_project_id": ops_task_spine.SATORY_TODOIST_PROJECT_ID,
        "todoist_section_id": "section-ops",
        "todoist_parent_id": "parent-task",
        "todoist_assignee_id": "todoist-user-1",
        "due_date": "2026-05-07",
        "deadline_date": "2026-05-08",
        "duration": 45,
        "duration_unit": "minute",
        "source_links": [
            {
                "title": "Second Brain source",
                "url": "https://www.notion.so/335cb8f8c69f804c92a0cd2b67dd1547",
            }
        ],
        "attachments": [
            {
                "name": "brief.pdf",
                "url": "https://www.notion.so/attachment/brief.pdf",
            }
        ],
        "comments": ["President intent: one operating surface."],
    }
    task.update(overrides)
    return task


def test_normalize_task_requires_assignment_priority_project_and_second_brain_scope():
    normalized = ops_task_spine.normalize_task(_raw_task())

    assert normalized["project"] == "Satory AI"
    assert normalized["subproject"] == "Ops Spine"
    assert normalized["owner"] == "Asylbek"
    assert normalized["team"] == "Integration"
    assert normalized["priority"] == "p1"
    assert normalized["notion_project_id"] == ops_task_spine.SATORY_NOTION_PROJECT_ID
    assert normalized["notion_source_database_id"] == ops_task_spine.SATORY_SECOND_BRAIN_DATABASE_ID
    assert normalized["notion_source_data_source_id"] == ops_task_spine.SATORY_SECOND_BRAIN_DATA_SOURCE_ID
    assert normalized["notion_source_view_id"] == ops_task_spine.SATORY_SECOND_BRAIN_VIEW_ID
    assert normalized["notion_source_view_url"] == ops_task_spine.SATORY_SECOND_BRAIN_VIEW_URL
    assert normalized["todoist_project_id"] == ops_task_spine.SATORY_TODOIST_PROJECT_ID


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("owner", "", "owner or team"),
        ("team", "", "owner or team"),
        ("priority", "p9", "priority"),
        ("notion_project_id", "other-project", "Satory AI"),
        ("notion_source_database_id", "other-database", "2nd Brain database"),
        ("notion_source_data_source_id", "other-source", "2nd Brain"),
        ("notion_source_view_id", "other-view", "Satory A.I. 2nd Brain view"),
        ("notion_source_view_url", "https://www.notion.so/wrong", "2nd Brain view URL"),
        ("todoist_project_id", "personal-project", "Satory VKO Factory"),
    ],
)
def test_normalize_task_rejects_unscoped_or_unusable_tasks(field, value, message):
    raw = _raw_task(**{field: value})
    if field == "owner":
        raw["team"] = ""
    if field == "team":
        raw["owner"] = ""

    with pytest.raises(ops_task_spine.TaskSpineError, match=message):
        ops_task_spine.normalize_task(raw)


def test_idempotency_key_is_stable_for_same_source_and_title():
    first = ops_task_spine.normalize_task(_raw_task())
    second = ops_task_spine.normalize_task(_raw_task(comments=["Different comment body"]))

    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["idempotency_key"].startswith("ops-task:satory:")


def test_default_model_pipeline_is_grok_to_chinese_workers_then_codex_escalation():
    normalized = ops_task_spine.normalize_task(_raw_task())

    assert normalized["model_pipeline"] == [
        "grok-reasoning",
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "kimi-k2.6",
        "glm-5.1",
        "codex:gpt-5.5-subscription",
    ]


def test_todoist_payload_contains_project_subtask_assignment_priority_and_source_context():
    normalized = ops_task_spine.normalize_task(_raw_task())
    payload = ops_task_spine.todoist_create_payload(normalized)

    assert payload["content"] == "Wire Satory operating system task spine"
    assert payload["project_id"] == ops_task_spine.SATORY_TODOIST_PROJECT_ID
    assert payload["section_id"] == "section-ops"
    assert payload["parent_id"] == "parent-task"
    assert payload["assignee_id"] == "todoist-user-1"
    assert payload["priority"] == 4
    assert payload["due_date"] == "2026-05-07"
    assert payload["deadline_date"] == "2026-05-08"
    assert payload["duration"] == 45
    assert payload["duration_unit"] == "minute"
    assert "Notion: https://www.notion.so/335cb8f8c69f804c92a0cd2b67dd1547" in payload["description"]
    assert f"2nd Brain view: {ops_task_spine.SATORY_SECOND_BRAIN_VIEW_URL}" in payload["description"]
    assert "Execution: grok-reasoning -> deepseek-v4-flash -> deepseek-v4-pro -> kimi-k2.6 -> glm-5.1 -> codex:gpt-5.5-subscription" in payload["description"]
    assert "ИИ-предложено" in payload["labels"]
    assert "проект:Satory AI" in payload["labels"]
    assert "подпроект:Ops Spine" in payload["labels"]
    assert "исполнитель:Asylbek" in payload["labels"]


def test_source_comment_contains_links_attachments_and_human_comments():
    normalized = ops_task_spine.normalize_task(_raw_task())
    comment = ops_task_spine.todoist_source_comment(normalized)

    assert "Second Brain source: https://www.notion.so/335cb8f8c69f804c92a0cd2b67dd1547" in comment
    assert "brief.pdf: https://www.notion.so/attachment/brief.pdf" in comment
    assert "President intent: one operating surface." in comment
