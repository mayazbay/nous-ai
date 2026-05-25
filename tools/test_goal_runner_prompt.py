import importlib.util
from pathlib import Path


def _load_goal_runner():
    path = Path(__file__).with_name("goal_runner.py")
    spec = importlib.util.spec_from_file_location("goal_runner_for_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_worker_prompt_inlines_goal_page_context():
    goal_runner = _load_goal_runner()
    goal = {
        "title": "Keep a real goal moving",
        "deadline": "2026-05-19",
        "last_progress_at": "2026-05-12 19:21",
        "rel_path": "pages/projects/GOAL-test.md",
        "id": "GOAL-test",
        "text": "# Keep a real goal moving\n\n## Progress log\n\n- prior slice marker",
    }

    prompt = goal_runner._build_worker_prompt(goal, "2026-05-12 20:40 KZT")

    assert "## GOAL page context (inline source of truth)" in prompt
    assert "prior slice marker" in prompt
    assert "may not have filesystem tools" in prompt
    assert "Do not claim you read files" in prompt


def test_worker_prompt_truncates_large_goal_context(monkeypatch):
    goal_runner = _load_goal_runner()
    monkeypatch.setattr(goal_runner, "MAX_GOAL_CONTEXT_CHARS", 30)
    goal = {
        "title": "Large goal",
        "deadline": "none",
        "last_progress_at": "null",
        "rel_path": "pages/projects/GOAL-large.md",
        "id": "GOAL-large",
        "text": "old context " * 20 + "RECENT-SLICE-MARKER",
    }

    prompt = goal_runner._build_worker_prompt(goal, "2026-05-12 20:40 KZT")

    assert "[truncated to last 30 chars" in prompt
    assert "RECENT-SLICE-MARKER" in prompt


def test_goal_worker_command_uses_grok_reasoning_by_default():
    goal_runner = _load_goal_runner()
    goal = {"id": "GOAL-test"}

    cmd = goal_runner._worker_command(goal, "do one slice")

    assert "--source" in cmd
    assert "goal-cycle:GOAL-test" in cmd
    assert "--model" in cmd
    assert "grok-reasoning" in cmd
    assert cmd[-1] == "do one slice"
