from __future__ import annotations

from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "factory_no_drift_probe.sh"


def test_github_mirror_uses_canonical_head_and_classifies_air_lag() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "GITHUB_EXPECTED_HEAD" in text
    assert "CANONICAL_REMOTE" in text
    assert "remote_main_short" in text
    assert 'MAC_GITHUB_HEAD" != "$GITHUB_EXPECTED_HEAD' in text
    assert 'AIR_GITHUB_HEAD" != "$GITHUB_EXPECTED_HEAD' in text
    assert "air_sync_lag" in text
    assert "repair_air_sync_lag" in text
    assert "--no-repair" in text
    assert "-h|--help) usage; exit 0" in text
    assert "unknown arg" in text
    assert "git status --porcelain" in text
    assert 'git pull --rebase "$remote" main' not in text
    assert "remote_main_full" in text
    assert 'refs/remotes/"$remote"/main' in text
    assert 'git -c core.hooksPath=/dev/null rebase "$target_full"' in text
    assert "merge-base --is-ancestor" in text
    assert "skipped_rebase_in_progress" in text
    assert "current_expected" in text
    assert "target_short" in text
    assert "skipped_dirty_worktree" in text
    assert "local checkout auto-repaired" in text
    assert "auto_repair=" in text
    assert "GitHub mirror stale or not exact" in text
    assert "tokenless remotes + exact mirror" in text
