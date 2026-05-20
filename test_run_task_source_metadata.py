import pathlib
import sys
import threading
import time
from datetime import datetime
from types import SimpleNamespace
from types import ModuleType

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

active_task = ModuleType("active_task")
active_task.ActiveTask = object
context_injector = ModuleType("context_injector")
context_injector.get_context = lambda message, inject=True: message
model_escalator = ModuleType("model_escalator")
model_escalator.ModelEscalator = object
sys.modules.setdefault("active_task", active_task)
sys.modules.setdefault("context_injector", context_injector)
sys.modules.setdefault("model_escalator", model_escalator)

import run_task


def _prepare_wiki(monkeypatch, tmp_path):
    wiki = tmp_path / "wiki"
    (wiki / ".git").mkdir(parents=True)
    monkeypatch.setattr(run_task, "WIKI_PATH", str(wiki))
    monkeypatch.setattr(run_task, "TASK_RESULTS_DIR", str(wiki / "pages" / "task-results"))
    return wiki


def test_write_back_records_source_metadata(monkeypatch, tmp_path):
    wiki = _prepare_wiki(monkeypatch, tmp_path)
    monkeypatch.setattr(
        run_task.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b"", stderr=b""),
    )

    run_task._write_back_to_wiki(
        "Reply exactly SOURCE_OK",
        "SOURCE_OK",
        datetime(2026, 4, 30, 10, 0, 0, tzinfo=run_task.KZ_TZ),
        "deepseek-v4-flash",
        12,
        3,
        source="daily_0300_substrate_sync",
    )

    [result] = (wiki / "pages" / "task-results").glob("*.md")
    text = result.read_text(encoding="utf-8")

    assert 'source: "daily_0300_substrate_sync"' in text


def test_write_back_commits_only_its_task_result(monkeypatch, tmp_path):
    wiki = _prepare_wiki(monkeypatch, tmp_path)
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(run_task.subprocess, "run", fake_run)

    run_task._write_back_to_wiki(
        "Reply exactly ONLY_OK",
        "ONLY_OK",
        datetime(2026, 4, 30, 10, 1, 0, tzinfo=run_task.KZ_TZ),
        "deepseek-v4-flash",
        12,
        3,
        source="codex_test",
    )

    commit_cmds = [cmd for cmd in calls if cmd[:3] == ["git", "-C", str(wiki)] and "commit" in cmd]
    assert len(commit_cmds) == 1
    commit_cmd = commit_cmds[0]
    assert "-c" in commit_cmd
    assert "core.hooksPath=/dev/null" in commit_cmd
    assert "--no-verify" in commit_cmd
    assert "-o" in commit_cmd
    assert "pages/task-results/2026-04-30-10-01-00-reply-exactly-only-ok.md" in commit_cmd
    pull_cmds = [cmd for cmd in calls if cmd[:3] == ["git", "-C", str(wiki)] and "pull" in cmd]
    assert len(pull_cmds) == 1
    assert "core.hooksPath=/dev/null" in pull_cmds[0]


def test_write_back_waits_for_existing_lock(monkeypatch, tmp_path):
    wiki = _prepare_wiki(monkeypatch, tmp_path)
    lock_path = wiki / ".git" / "run_task_writeback.lock"
    lock_path.write_text("held by another run_task\n", encoding="utf-8")
    first_git_at = []

    def fake_run(cmd, *args, **kwargs):
        if not first_git_at:
            first_git_at.append(time.monotonic())
        assert "held by another" not in lock_path.read_text(encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(run_task.subprocess, "run", fake_run)

    def release_lock():
        time.sleep(0.2)
        lock_path.unlink()

    releaser = threading.Thread(target=release_lock)
    releaser.start()
    started = time.monotonic()

    run_task._write_back_to_wiki(
        "Reply exactly LOCK_OK",
        "LOCK_OK",
        datetime(2026, 4, 30, 10, 2, 0, tzinfo=run_task.KZ_TZ),
        "deepseek-v4-flash",
        12,
        3,
        source="codex_test",
    )

    releaser.join(timeout=1)
    assert first_git_at
    assert first_git_at[0] - started >= 0.15
    assert not lock_path.exists()
