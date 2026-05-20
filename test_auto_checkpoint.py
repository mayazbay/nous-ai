import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import auto_checkpoint


def _git_result(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["git", *args], returncode, stdout, stderr)


def _write_task_result(root, name, task, mtime):
    path = root / name
    path.write_text(
        "---\ntype: task-result\ndate: 2026-04-30\n---\n\n"
        f"## Task\n\n{task}\n\n## Response\n\nok\n",
        encoding="utf-8",
    )
    os.utime(path, (mtime, mtime))
    return path


def test_recent_task_results_prioritizes_real_work_over_daily_noise(monkeypatch, tmp_path):
    monkeypatch.setattr(auto_checkpoint, "TASK_RESULTS_DIR", tmp_path)

    _write_task_result(
        tmp_path,
        "2026-04-30-03-00-26-reply-with-exactly-daily-0300-ok.md",
        "Reply with exactly: DAILY_0300_OK",
        100,
    )
    _write_task_result(
        tmp_path,
        "2026-04-30-07-00-00-inspect-openclaw-routing.md",
        "Inspect OpenClaw routing",
        200,
    )
    _write_task_result(
        tmp_path,
        "2026-04-30-08-00-00-compose-sync-audit.md",
        "Compose sync audit",
        300,
    )
    for idx, hour in enumerate(range(9, 14), start=1):
        _write_task_result(
            tmp_path,
            f"2026-04-30-{hour:02d}-00-0{idx}-reply-with-exactly-daily-0300-ok.md",
            "Reply with exactly: DAILY_0300_OK",
            300 + idx,
        )

    recent = auto_checkpoint._recent_task_results(n=3)

    assert "inspect-openclaw-routing.md" in recent
    assert "compose-sync-audit.md" in recent
    assert recent.count("reply-with-exactly-daily-0300-ok.md") <= 1
    assert "DAILY_0300_OK anomaly" in recent
    assert "5 non-03:00" in recent


def test_post_checkpoint_sync_pushes_origin_when_github_remote_missing(monkeypatch):
    calls = []

    def fake_git(args, timeout=60):
        calls.append(tuple(args))
        if args == ["remote", "get-url", "github"]:
            return _git_result(args, returncode=2)
        return _git_result(args)

    notices = []
    monkeypatch.setattr(auto_checkpoint, "_git", fake_git)
    monkeypatch.setattr(auto_checkpoint, "_telegram_notify", notices.append)

    auto_checkpoint._post_checkpoint_sync("2026-05-12-18-00")

    assert ("fetch", "origin", "main") in calls
    assert ("pull", "--rebase", "--autostash", "origin", "main") in calls
    assert ("push", "origin", "main") in calls
    assert ("push", "github", "main") not in calls
    assert notices == []


def test_post_checkpoint_sync_rebases_on_github_main_before_pushing(monkeypatch):
    calls = []

    def fake_git(args, timeout=60):
        calls.append(tuple(args))
        if args == ["remote", "get-url", "github"]:
            return _git_result(args, stdout="https://example.invalid/repo.git\n")
        if args == ["merge-base", "--is-ancestor", "github/main", "HEAD"]:
            return _git_result(args, returncode=1)
        return _git_result(args)

    monkeypatch.setattr(auto_checkpoint, "_git", fake_git)
    monkeypatch.setattr(auto_checkpoint, "_telegram_notify", lambda text: None)

    auto_checkpoint._post_checkpoint_sync("2026-05-12-18-00")

    rebase_index = calls.index(("rebase", "github/main"))
    push_origin_index = calls.index(("push", "origin", "main"))
    push_github_index = calls.index(("push", "github", "main"))
    assert rebase_index < push_origin_index < push_github_index
