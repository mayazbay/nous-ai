import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from readme_dashboard import build_dashboard


def test_dashboard_includes_core_sections(tmp_path):
    (tmp_path / "pages" / "progress").mkdir(parents=True)
    (tmp_path / "pages" / "task-results").mkdir(parents=True)
    (tmp_path / "pages" / "dashboards").mkdir(parents=True)
    (tmp_path / "pages" / "skills" / "factory-ops").mkdir(parents=True)

    (tmp_path / "pages" / "progress" / "HANDOFF-AUTO-2026-04-27-test.md").write_text("# Handoff Test\n")
    (tmp_path / "pages" / "task-results" / "2026-04-27-test.md").write_text("# Task Test\n")
    (tmp_path / "pages" / "dashboards" / "today.md").write_text("# Today\n")
    (tmp_path / "pages" / "skills" / "factory-ops" / "SKILL.md").write_text("# factory-ops v1.0.0\n")

    now = dt.datetime(2026, 4, 27, 12, 0, tzinfo=dt.timezone.utc)
    content = build_dashboard(tmp_path, now=now)

    assert "# Nous Factory Dashboard" in content
    assert "README is the dashboard" in content
    assert "Task-results today | 1" in content
    assert "Skills | 1" in content
    assert "HANDOFF-AUTO-2026-04-27-test.md" in content
    assert "blacksmith_burst_tests.sh" in content
