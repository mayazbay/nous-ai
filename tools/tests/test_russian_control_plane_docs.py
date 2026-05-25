from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import check_russian_control_plane_docs as gate
import control_plane_sync_loop as sync


def test_gate_accepts_russian_operator_docs(tmp_path: Path) -> None:
    (tmp_path / "pages/systems").mkdir(parents=True)
    (tmp_path / "pages/skills/todoist-control-plane").mkdir(parents=True)
    (tmp_path / "pages/systems/todoist-control-plane-register.md").write_text(
        "# Реестр контрольной плоскости Todoist\n\n## Счётчики статусов\n\n## Реестр активных задач\n",
        encoding="utf-8",
    )
    (tmp_path / "pages/systems/todoist-context-enrichment-queue.md").write_text(
        "# Очередь обогащения контекста Todoist\n\n## Как выполнять каждую задачу\n\n## Критерий готовности\n",
        encoding="utf-8",
    )
    (tmp_path / "pages/systems/control-plane-sync-status.md").write_text(
        "# Статус синхронизации контрольной плоскости\n\n## Матрица статусов\n\n## Правила блокировок\n",
        encoding="utf-8",
    )
    (tmp_path / "pages/skills/todoist-control-plane/SKILL.md").write_text(
        "# todoist-control-plane v1.3.0\n\n## Russian Documentation Sync Gate\n\n`tools/check_russian_control_plane_docs.py`\n",
        encoding="utf-8",
    )

    result = gate.run_check(tmp_path)

    assert result["status"] == "done"
    assert result["failures"] == 0


def test_gate_rejects_english_operator_headings(tmp_path: Path) -> None:
    (tmp_path / "pages/systems").mkdir(parents=True)
    (tmp_path / "pages/skills/todoist-control-plane").mkdir(parents=True)
    (tmp_path / "pages/systems/todoist-control-plane-register.md").write_text(
        "# Todoist Control Plane Register\n",
        encoding="utf-8",
    )
    (tmp_path / "pages/systems/todoist-context-enrichment-queue.md").write_text(
        "# Todoist Context Enrichment Queue\nCaptured:\n",
        encoding="utf-8",
    )
    (tmp_path / "pages/systems/control-plane-sync-status.md").write_text(
        "# Control Plane Sync Status\n## Status Matrix\n",
        encoding="utf-8",
    )
    (tmp_path / "pages/skills/todoist-control-plane/SKILL.md").write_text(
        "# todoist-control-plane v1.2.0\n",
        encoding="utf-8",
    )

    result = gate.run_check(tmp_path)

    assert result["status"] == "blocked"
    assert result["failures"] == 4


def test_control_plane_status_page_is_russian_facing() -> None:
    text = sync.render_status_page(
        {
            "cycle_id": "2026-05-13-150000",
            "started_at": "2026-05-13T15:00:00+05:00",
            "finished_at": "2026-05-13T15:01:00+05:00",
            "dry_run": False,
            "overall_status": "done",
            "steps": [{"name": "todoist_control_plane", "status": "done", "summary": "hard_gates=0"}],
        }
    )

    assert "# Статус синхронизации контрольной плоскости" in text
    assert "## Матрица статусов" in text
    assert "## Правила блокировок" in text
    assert "## Status Matrix" not in text
    assert "Dry run:" not in text
