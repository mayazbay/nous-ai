from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import control_plane_sync_loop as loop


def test_preflight_skips_are_non_blocking_and_visible() -> None:
    cycle = {"steps": []}

    loop.append_preflight_skips(cycle)

    statuses = {step["status"] for step in cycle["steps"]}
    names = {step["name"] for step in cycle["steps"]}
    assert statuses == {"skipped_preflight"}
    assert "todoist_control_plane" in names
    assert "notion_sync" in names
    assert "satory_todoist_deep_audit" in names
    assert loop.status_rank("skipped_preflight") == 0


def test_control_plane_git_sync_uses_exact_oid_rebase_not_pull() -> None:
    source = (TOOLS / "control_plane_sync_loop.py").read_text(encoding="utf-8")

    assert "git\", \"pull\", \"--rebase" not in source
    assert "main:refs/remotes/{remote}/main" in source
    assert '"rebase", target' in source


def test_canonical_remote_falls_back_to_vps_when_origin_missing(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["git", "remote", "get-url"]:
            return {"ok": cmd[-1] == "vps", "stdout": "", "stderr": "", "returncode": 0}
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.delenv(loop.CANONICAL_REMOTE_ENV, raising=False)
    monkeypatch.setattr(loop, "run", fake_run)

    assert loop.resolve_canonical_remote(Path(".")) == "vps"


def test_canonical_remote_env_override(monkeypatch) -> None:
    monkeypatch.setenv(loop.CANONICAL_REMOTE_ENV, "mirror")

    assert loop.resolve_canonical_remote(Path(".")) == "mirror"
