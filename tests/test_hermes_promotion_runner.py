from __future__ import annotations

from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import hermes_promotion_runner as runner


def _skill(path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\n"
        "type: skill\n"
        "title: \"ceo-hierarchy v1.8.6\"\n"
        "version: 1.8.6\n"
        "---\n\n"
        "# ceo-hierarchy v1.8.6\n\n"
        "## Current rules\n\n"
        "Existing rules.\n\n"
        "## Timeline\n\n"
        "- **2026-05-15** | v1.8.5 -> v1.8.6 -- AP-24.\n",
        encoding="utf-8",
    )


def _results(green_count: int) -> list[dict]:
    return [
        {
            "name": f"proof_{idx}",
            "status": "GREEN" if idx <= green_count else "RED",
            "detail": "ok" if idx <= green_count else "missing",
            "evidence": {},
        }
        for idx in range(1, 11)
    ]


def test_nine_of_ten_proofs_does_not_promote_ceo_hierarchy(tmp_path: Path) -> None:
    skill = tmp_path / "pages/skills/ceo-hierarchy/SKILL.md"
    _skill(skill)

    promoted = runner.maybe_promote_ceo_hierarchy(_results(9), skill, today="2026-05-17")

    assert promoted is False
    text = skill.read_text(encoding="utf-8")
    assert "v1.9.0" not in text
    assert "AP-25" not in text


def test_ten_of_ten_proofs_promotes_ceo_hierarchy_once(tmp_path: Path) -> None:
    skill = tmp_path / "pages/skills/ceo-hierarchy/SKILL.md"
    _skill(skill)

    promoted = runner.maybe_promote_ceo_hierarchy(_results(10), skill, today="2026-05-17")
    promoted_again = runner.maybe_promote_ceo_hierarchy(_results(10), skill, today="2026-05-17")

    text = skill.read_text(encoding="utf-8")
    assert promoted is True
    assert promoted_again is False
    assert "v1.9.0" in text
    assert "AP-25 — Hermes promoted from canary to production" in text
    assert text.count("AP-25") == 2


def test_write_proof_audit_records_all_proofs(tmp_path: Path) -> None:
    path = runner.write_proof_audit(_results(10), tmp_path, today="2026-05-17", promoted=True)

    text = path.read_text(encoding="utf-8")
    assert path.name == "HERMES-PROMOTION-RUNNER-DEPLOY-PROOF-2026-05-17.md"
    assert "overall: GREEN" in text
    assert "proof_10" in text
    assert "ceo_hierarchy_promoted: true" in text


def test_green_artifact_proof_rejects_prefix_only_or_yellow_files(tmp_path: Path) -> None:
    audit_dir = tmp_path / "pages/audits"
    audit_dir.mkdir(parents=True)
    (audit_dir / "HERMES-NOTION-CANARY-BLOCKED-2026-05-18.md").write_text(
        "---\nstatus: yellow\n---\n\nNOUS_HERMES_NOTION_CANARY_OK\n",
        encoding="utf-8",
    )
    (audit_dir / "HERMES-NOTION-CANARY-EMPTY-2026-05-18.md").write_text(
        "---\nstatus: green\n---\n\nmissing marker\n",
        encoding="utf-8",
    )

    result = runner._green_artifact_proof(
        tmp_path,
        "notion_canary_proof",
        "pages/audits/HERMES-NOTION-CANARY",
        marker="NOUS_HERMES_NOTION_CANARY_OK",
    )

    assert result["status"] == "RED"
    assert len(result["evidence"]["ignored"]) == 2


def test_green_artifact_proof_accepts_green_file_with_required_marker(tmp_path: Path) -> None:
    audit_dir = tmp_path / "pages/audits"
    audit_dir.mkdir(parents=True)
    (audit_dir / "HERMES-NOTION-CANARY-2026-05-18.md").write_text(
        "---\nstatus: green\n---\n\nNOUS_HERMES_NOTION_CANARY_OK\n",
        encoding="utf-8",
    )

    result = runner._green_artifact_proof(
        tmp_path,
        "notion_canary_proof",
        "pages/audits/HERMES-NOTION-CANARY",
        marker="NOUS_HERMES_NOTION_CANARY_OK",
    )

    assert result["status"] == "GREEN"
    assert result["evidence"]["matches"] == [str(audit_dir / "HERMES-NOTION-CANARY-2026-05-18.md")]
