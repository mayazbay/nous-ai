"""Tests for tools/migrate_ship3.py (Ship 3 wave 8)."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import library_canonical_registry as registry  # noqa: E402
import library_embed_voyage  # noqa: E402
import migrate_ship3  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wiki(tmp_path, monkeypatch):
    """tmp_path acting as the vault root.

    - Creates SYNC_DIRS layout with a handful of fixture pages.
    - Points NOUS_WIKI at it.
    - Clears VOYAGE_API_KEY + redirects VOYAGE_KEY_PATH so the embedder falls
      back to the stub.
    """
    for sub in migrate_ship3.SYNC_DIRS:
        (tmp_path / sub).mkdir(parents=True)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".gbrain").mkdir(parents=True, exist_ok=True)

    # Write small fixture pages spread across SYNC_DIRS.
    (tmp_path / "pages" / "systems" / "alpha.md").write_text(
        "---\ntitle: Alpha\n---\n# Alpha\n\nSome content.\n",
        encoding="utf-8",
    )
    (tmp_path / "pages" / "skills" / "skillone").mkdir(parents=True)
    (tmp_path / "pages" / "skills" / "skillone" / "SKILL.md").write_text(
        "# Skillone\n\nbody\n", encoding="utf-8"
    )
    (tmp_path / "pages" / "audits" / "bravo.md").write_text(
        "# Bravo\n\naudit body\n", encoding="utf-8"
    )
    (tmp_path / "pages" / "plans" / "charlie.md").write_text(
        "# Charlie\n\nplan body\n", encoding="utf-8"
    )
    (tmp_path / "pages" / "laws" / "LAW-XYZ.md").write_text(
        "# Law XYZ\n\nlaw body\n", encoding="utf-8"
    )
    (tmp_path / "pages" / "concepts" / "delta.md").write_text(
        "# Delta\n\nconcept body\n", encoding="utf-8"
    )

    monkeypatch.setenv("NOUS_WIKI", str(tmp_path))
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    bogus = tmp_path / "voyage_missing.env"
    monkeypatch.setattr(library_embed_voyage, "VOYAGE_KEY_PATH", bogus)
    # Discourage local MiniLM fallback in tests to keep them hermetic.
    monkeypatch.setenv("NOUS_EMBED_FALLBACK_LOCAL", "0")
    return tmp_path


# ---------------------------------------------------------------------------
# Step A: archive
# ---------------------------------------------------------------------------


def test_archive_dry_run_does_not_move(tmp_path, wiki):
    """Dry-run reports the would-be move but leaves SRC intact."""
    src = tmp_path / "fake_gbrain" / "skills"
    src.mkdir(parents=True)
    (src / "gstack").mkdir()
    (src / "gstack" / "README.md").write_text("noop", encoding="utf-8")

    result = migrate_ship3.archive_gbrain_shell(src=src, dry_run=True)
    assert result["archived"] is False
    assert result["reason"] == "dry_run"
    assert src.exists()
    assert (src / "gstack").exists(), "dry-run must not move anything"


def test_archive_is_idempotent(tmp_path):
    """Second invocation is a no-op once the stub README is in place."""
    src = tmp_path / "fake_gbrain" / "skills"
    src.mkdir(parents=True)
    (src / "gstack").mkdir()
    (src / "claude").mkdir()

    r1 = migrate_ship3.archive_gbrain_shell(src=src, dry_run=False)
    assert r1["archived"] is True
    assert r1["reason"] == "ok"
    assert src.exists(), "SRC must be recreated as a README-only stub"
    assert (src / "README.md").exists()
    # The original payload directories are gone from SRC.
    assert not (src / "gstack").exists()
    # And present in the archive.
    dest = pathlib.Path(r1["dest"])
    assert dest.exists()
    assert (dest / "gstack").exists()

    r2 = migrate_ship3.archive_gbrain_shell(src=src, dry_run=False)
    assert r2["archived"] is False
    assert r2["reason"] == "already_stub"


def test_archive_missing_src_is_noop(tmp_path):
    src = tmp_path / "never_existed" / "skills"
    result = migrate_ship3.archive_gbrain_shell(src=src, dry_run=False)
    assert result["archived"] is False
    assert result["reason"] == "missing"


# ---------------------------------------------------------------------------
# Step B: registry populate
# ---------------------------------------------------------------------------


def test_populate_registry_adds_all_target_md(wiki):
    result = migrate_ship3.populate_registry(wiki, dry_run=False)
    # Fixture wrote one md file in each of the 6 SYNC_DIRS.
    assert len(result["files"]) == 6
    assert result["added"] == 6
    assert result["existing"] == 0

    # And the registry JSONL exists with those rows.
    rows = registry.list_all(wiki=wiki)
    assert len(rows) == 6
    paths = {r["obsidian_path"] for r in rows}
    assert "pages/systems/alpha.md" in paths
    assert "pages/skills/skillone/SKILL.md" in paths

    # Re-running is idempotent.
    again = migrate_ship3.populate_registry(wiki, dry_run=False)
    assert again["added"] == 0
    assert again["existing"] == 6


def test_populate_registry_dry_run(wiki):
    result = migrate_ship3.populate_registry(wiki, dry_run=True)
    assert result["dry_run"] is True
    assert len(result["files"]) == 6
    # No rows landed.
    assert registry.list_all(wiki=wiki) == []


# ---------------------------------------------------------------------------
# Step C: queue + drain
# ---------------------------------------------------------------------------


def test_queue_all_for_embed_appends(wiki):
    paths = ["pages/systems/alpha.md", "pages/audits/bravo.md"]
    count = migrate_ship3.queue_all_for_embed(wiki, paths, dry_run=False)
    assert count == 2
    queue_path = wiki / migrate_ship3.QUEUE_REL
    lines = [
        json.loads(line)
        for line in queue_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {row["path"] for row in lines} == set(paths)
    assert all(row["event"] == "migrate_ship3" for row in lines)


def test_full_migrate_skip_embed_populates_registry_and_health(wiki):
    """`--skip-embed` runs A/B/D but bypasses Voyage."""
    result = migrate_ship3.migrate(wiki, dry_run=False, skip_embed=True)
    assert result["step_a"]["reason"] in ("missing", "already_stub", "ok")
    assert result["step_b"]["added"] == 6
    assert result["step_c"] == {"skipped": True}
    snapshot = result["step_d"]
    assert snapshot["canonical_registry_size"] == 6
    # Health files were written.
    assert (wiki / "pages" / "systems" / "library-health.json").exists()
    assert (wiki / "pages" / "systems" / "LIBRARY-HEALTH.md").exists()


def test_full_migrate_with_stub_embedder(wiki):
    """End-to-end: A archived (or missing), B populated, C drained with stub, D snapshot."""
    result = migrate_ship3.migrate(
        wiki, dry_run=False, skip_embed=False, prefer="stub"
    )
    assert result["step_b"]["added"] == 6
    step_c = result["step_c"]
    # Stub embedder is deterministic → processed should be 6, errors 0.
    assert step_c.get("queued") == 6
    assert step_c.get("processed", 0) == 6
    assert step_c.get("errors", 0) == 0
    assert step_c.get("auth_missing", 0) == 0
    # Health snapshot picks up the indexed chunks.
    assert result["step_d"]["gbrain_indexed_chunks"] >= 6


def test_dry_run_writes_nothing(wiki):
    result = migrate_ship3.migrate(wiki, dry_run=True, skip_embed=False)
    assert result["step_b"]["dry_run"] is True
    assert result["step_c"]["dry_run"] is True
    # No registry rows; no health files written.
    assert registry.list_all(wiki=wiki) == []
    assert not (wiki / "pages" / "systems" / "library-health.json").exists()
