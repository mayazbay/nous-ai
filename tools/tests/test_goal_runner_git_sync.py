from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"


def test_goal_runner_writeback_uses_exact_oid_rebase_not_pull() -> None:
    source = (TOOLS / "goal_runner.py").read_text(encoding="utf-8")

    assert '"pull", "--rebase"' not in source
    assert "main:refs/remotes/{remote}/main" in source
    assert '["rebase", target]' in source
    assert '["rebase", target2]' in source
    assert "merge-base" in source
