from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import mercury_refresh as refresh


def test_parse_status_handles_modified_untracked_and_renames() -> None:
    output = "\n".join(
        [
            " M pages/mercury/facts.jsonl",
            "?? pages/progress/claude-memory/MEMORY-mercury.md",
            "R  old/path.md -> pages/mercury/facts.jsonl",
        ]
    )

    assert refresh.parse_status(output) == [
        "pages/mercury/facts.jsonl",
        "pages/progress/claude-memory/MEMORY-mercury.md",
        "pages/mercury/facts.jsonl",
    ]


def test_split_mercury_dirty_separates_generated_outputs_from_real_wip() -> None:
    mercury, other = refresh.split_mercury_dirty(
        [
            "pages/mercury/facts.jsonl",
            "pages/progress/claude-memory/MEMORY-mercury.md",
            "tools/command_center.py",
            "pages/systems/model-failover-ledger.jsonl",
        ]
    )

    assert mercury == [
        "pages/mercury/facts.jsonl",
        "pages/progress/claude-memory/MEMORY-mercury.md",
    ]
    assert other == [
        "tools/command_center.py",
        "pages/systems/model-failover-ledger.jsonl",
    ]


def test_commit_outputs_skips_when_non_mercury_dirty(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_dirty_paths(repo: Path) -> list[str]:
        return [
            "pages/mercury/facts.jsonl",
            "tools/command_center.py",
        ]

    monkeypatch.setattr(refresh, "dirty_paths", fake_dirty_paths)

    assert refresh.commit_outputs(tmp_path, dry_run=False, no_push=True) == 0
    assert "skip commit" in capsys.readouterr().out
