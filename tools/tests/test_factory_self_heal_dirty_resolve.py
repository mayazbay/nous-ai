"""Tests for auto_resolve_transient_dirty() — factory_self_heal dirty-WT classifier.

Covers: clean WT, all-transient auto-commit, real-WIP skip, mixed skip,
untracked transient file, and commit failure path.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import factory_self_heal as heal


def _args(tmp_path: Path, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        wiki=tmp_path,
        ledger=tmp_path / "logs/factory-self-heal.jsonl",
        state=tmp_path / "state/factory-self-heal-state.json",
        status_page=Path("pages/systems/factory-self-healing-supervisor-status.md"),
        source="test",
        stdin_probe_json=False,
        stdin_light_changes=False,
        notify=False,
        write_status=False,
        dry_run=dry_run,
        json=True,
        max_attempts=1,
        probe_timeout=10,
        notification_ttl_seconds=3600,
    )


# ---------------------------------------------------------------------------
# 1. Fully clean worktree → (True, [])
# ---------------------------------------------------------------------------

def test_fully_clean_wt_returns_true_empty_list(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    monkeypatch.setattr(
        heal, "run",
        lambda cmd, **kwargs: {"ok": True, "returncode": 0, "stdout": "", "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0},
    )
    ok, paths = heal.auto_resolve_transient_dirty(args)
    assert ok is True
    assert paths == []


# ---------------------------------------------------------------------------
# 2. All dirty files are transient → auto-stage + commit → (True, [paths])
# ---------------------------------------------------------------------------

def test_all_transient_paths_auto_committed(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    calls: list[list[str]] = []

    transient_output = (
        " M pages/mercury/sync.jsonl\n"
        "?? pages/systems/factory-self-heal-2026.jsonl\n"
        " M .obsidian/workspace.json\n"
    )

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[1:3] == ["status", "--porcelain"]:
            return {"ok": True, "returncode": 0, "stdout": transient_output, "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}

    monkeypatch.setattr(heal, "run", fake_run)

    ok, cleared = heal.auto_resolve_transient_dirty(args)

    assert ok is True
    assert sorted(cleared) == sorted([
        "pages/mercury/sync.jsonl",
        "pages/systems/factory-self-heal-2026.jsonl",
        ".obsidian/workspace.json",
    ])

    # git add must have been called with the transient paths
    add_calls = [c for c in calls if c[:2] == ["git", "add"]]
    assert add_calls, "git add was never called"
    add_paths = add_calls[0][3:]  # skip ["git", "add", "-A"]
    assert "pages/mercury/sync.jsonl" in add_paths

    # git commit must have been called
    commit_calls = [c for c in calls if c[:2] == ["git", "commit"]]
    assert commit_calls, "git commit was never called"
    assert "auto-sync: factory_self_heal cleared transient churn" in " ".join(commit_calls[0])


# ---------------------------------------------------------------------------
# 3. Real WIP file present → skip, no commit → (False, [real paths])
# ---------------------------------------------------------------------------

def test_real_lane_wip_skips_no_commit(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    calls: list[list[str]] = []

    dirty_output = " M tools/foo.py\n"

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[1:3] == ["status", "--porcelain"]:
            return {"ok": True, "returncode": 0, "stdout": dirty_output, "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}

    monkeypatch.setattr(heal, "run", fake_run)

    ok, real_paths = heal.auto_resolve_transient_dirty(args)

    assert ok is False
    assert "tools/foo.py" in real_paths

    # Ensure neither git add nor git commit was called
    mutating = [c for c in calls if c[:2] in (["git", "add"], ["git", "commit"])]
    assert mutating == [], f"Unexpected mutating git commands: {mutating}"


# ---------------------------------------------------------------------------
# 4. Mixed: transient + real → skip, no commit → (False, [real paths])
# ---------------------------------------------------------------------------

def test_mixed_transient_plus_real_skips_no_commit(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    calls: list[list[str]] = []

    dirty_output = (
        " M pages/mercury/sync.jsonl\n"
        " M tools/important_script.py\n"
    )

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[1:3] == ["status", "--porcelain"]:
            return {"ok": True, "returncode": 0, "stdout": dirty_output, "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}

    monkeypatch.setattr(heal, "run", fake_run)

    ok, real_paths = heal.auto_resolve_transient_dirty(args)

    assert ok is False
    assert "tools/important_script.py" in real_paths
    assert "pages/mercury/sync.jsonl" not in real_paths

    mutating = [c for c in calls if c[:2] in (["git", "add"], ["git", "commit"])]
    assert mutating == [], f"Unexpected mutating git commands: {mutating}"


# ---------------------------------------------------------------------------
# 5. Untracked transient path (?? marker) → also included in auto-commit
# ---------------------------------------------------------------------------

def test_untracked_transient_path_also_committed(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)
    calls: list[list[str]] = []

    dirty_output = "?? pages/systems/notification-digest-queue.jsonl\n"

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[1:3] == ["status", "--porcelain"]:
            return {"ok": True, "returncode": 0, "stdout": dirty_output, "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}

    monkeypatch.setattr(heal, "run", fake_run)

    ok, cleared = heal.auto_resolve_transient_dirty(args)

    assert ok is True
    assert "pages/systems/notification-digest-queue.jsonl" in cleared

    commit_calls = [c for c in calls if c[:2] == ["git", "commit"]]
    assert commit_calls, "git commit was never called for untracked transient file"


# ---------------------------------------------------------------------------
# 6. git commit failure → return (False, [])
# ---------------------------------------------------------------------------

def test_commit_failure_returns_false(monkeypatch, tmp_path: Path) -> None:
    args = _args(tmp_path)

    transient_output = " M pages/dashboards/status.md\n"

    def fake_run(cmd, **kwargs):
        if cmd[1:3] == ["status", "--porcelain"]:
            return {"ok": True, "returncode": 0, "stdout": transient_output, "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}
        if "add" in cmd:
            return {"ok": True, "returncode": 0, "stdout": "", "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}
        if "commit" in cmd:
            return {"ok": False, "returncode": 1, "stdout": "", "stderr": "error: nothing to commit", "cmd": " ".join(cmd), "duration_ms": 0}
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": "", "cmd": " ".join(cmd), "duration_ms": 0}

    monkeypatch.setattr(heal, "run", fake_run)

    ok, paths = heal.auto_resolve_transient_dirty(args)

    assert ok is False
    assert paths == []
