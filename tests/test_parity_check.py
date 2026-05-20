"""Unit tests for tools/parity_check.py (Ship 1 Step 7).

Covers: manifest parsing, missing/broken-symlink fallback, determinism,
change-detection, atomic write, verify pass/fail, CLI entry.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import parity_check  # noqa: E402


EMPTY_SHA = hashlib.sha256(b"").hexdigest()

# The 5 manifest paths used by Ship 1 (matches pages/systems/parity-manifest.txt).
MANIFEST_PATHS = [
    "pages/systems/model-failover-ledger.jsonl",
    "pages/systems/MODEL-FAILOVER-LATEST.md",
    "pages/systems/AGENT-CONTINUITY-PACKET.md",
    "pages/progress/HANDOFF-AUTO-LATEST.symlink",
    "pages/systems/parity-manifest.txt",
]


def _write_real_manifest(wiki: Path) -> None:
    """Write a manifest mirroring the production parity-manifest.txt."""
    manifest = wiki / "pages" / "systems" / "parity-manifest.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# header comment\n"
        "# another comment\n"
        "\n"
        + "\n".join(MANIFEST_PATHS)
        + "\n"
    )
    manifest.write_text(body, encoding="utf-8")


def _seed_manifest_files(wiki: Path) -> None:
    """Create all 5 manifest target files with stable, non-empty contents."""
    (wiki / "pages" / "systems").mkdir(parents=True, exist_ok=True)
    (wiki / "pages" / "progress").mkdir(parents=True, exist_ok=True)

    (wiki / "pages" / "systems" / "model-failover-ledger.jsonl").write_text(
        '{"row": 1}\n', encoding="utf-8"
    )
    (wiki / "pages" / "systems" / "MODEL-FAILOVER-LATEST.md").write_text(
        "# latest\n", encoding="utf-8"
    )
    (wiki / "pages" / "systems" / "AGENT-CONTINUITY-PACKET.md").write_text(
        "# packet\n", encoding="utf-8"
    )
    (wiki / "pages" / "progress" / "HANDOFF-AUTO-LATEST.symlink").write_text(
        "handoff target placeholder\n", encoding="utf-8"
    )
    _write_real_manifest(wiki)


def test_load_manifest_skips_comments_and_blanks(tmp_path: Path) -> None:
    manifest = tmp_path / "pages" / "systems" / "parity-manifest.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "# leading comment\n"
        "\n"
        "alpha.txt\n"
        "   \n"
        "# mid comment\n"
        "beta/path.md\n"
        "\n"
        "gamma.jsonl\n",
        encoding="utf-8",
    )
    paths = parity_check.load_manifest(tmp_path)
    assert paths == ["alpha.txt", "beta/path.md", "gamma.jsonl"]


def test_file_sha256_empty_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.txt"
    assert parity_check.file_sha256(missing) == EMPTY_SHA


def test_file_sha256_empty_for_broken_symlink(tmp_path: Path) -> None:
    target = tmp_path / "never-existed.txt"
    link = tmp_path / "broken.symlink"
    os.symlink(target, link)
    assert link.is_symlink()
    assert not link.exists()
    assert parity_check.file_sha256(link) == EMPTY_SHA


def test_compute_parity_shape(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    parity = parity_check.compute_parity(tmp_path)
    assert parity["algo"] == "sha256"
    assert isinstance(parity["host"], str) and parity["host"]
    assert isinstance(parity["ts"], str) and "+05:00" in parity["ts"]
    assert len(parity["manifest_sha256"]) == 64
    assert set(parity["files"].keys()) == set(MANIFEST_PATHS)
    # Order in the dict must follow manifest order.
    assert list(parity["files"].keys()) == MANIFEST_PATHS


def test_compute_parity_deterministic(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    first = parity_check.compute_parity(tmp_path)
    second = parity_check.compute_parity(tmp_path)
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert first["files"] == second["files"]


def test_compute_parity_changes_when_file_changes(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    before = parity_check.compute_parity(tmp_path)
    # Mutate one of the manifest target files.
    target = tmp_path / "pages" / "systems" / "MODEL-FAILOVER-LATEST.md"
    target.write_text("# latest CHANGED\n", encoding="utf-8")
    after = parity_check.compute_parity(tmp_path)
    assert before["manifest_sha256"] != after["manifest_sha256"]
    assert before["files"][
        "pages/systems/MODEL-FAILOVER-LATEST.md"
    ] != after["files"]["pages/systems/MODEL-FAILOVER-LATEST.md"]


def test_compute_and_write_is_atomic(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    written = parity_check.compute_and_write(tmp_path)
    assert written.exists()
    assert written == tmp_path / "pages" / "systems" / "parity-latest.json"
    data = json.loads(written.read_text(encoding="utf-8"))
    assert data["algo"] == "sha256"
    assert "manifest_sha256" in data
    # The temp file must not linger after a successful write.
    tmp = written.with_suffix(written.suffix + ".tmp")
    assert not tmp.exists()


def test_verify_passes_when_no_drift(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    parity_check.compute_and_write(tmp_path)
    ok, msg = parity_check.verify(tmp_path)
    assert ok is True
    assert "OK" in msg or "ok" in msg.lower()


def test_verify_fails_when_file_drifted(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    parity_check.compute_and_write(tmp_path)
    drift_target = tmp_path / "pages" / "systems" / "AGENT-CONTINUITY-PACKET.md"
    drift_target.write_text("# packet DRIFTED\n", encoding="utf-8")
    ok, msg = parity_check.verify(tmp_path)
    assert ok is False
    assert "DRIFT" in msg or "drift" in msg.lower()


def test_verify_fails_when_parity_file_missing(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    # Do NOT compute_and_write.
    ok, msg = parity_check.verify(tmp_path)
    assert ok is False
    assert msg == "no parity-latest.json"


def test_main_writes_parity_when_no_args(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    script = REPO_ROOT / "tools" / "parity_check.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--wiki", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    parity_file = tmp_path / "pages" / "systems" / "parity-latest.json"
    assert parity_file.exists()
    data = json.loads(parity_file.read_text(encoding="utf-8"))
    assert data["algo"] == "sha256"


def test_main_verify_exits_1_on_drift(tmp_path: Path) -> None:
    _seed_manifest_files(tmp_path)
    parity_check.compute_and_write(tmp_path)
    # Mutate a manifest target after writing parity.
    (tmp_path / "pages" / "systems" / "model-failover-ledger.jsonl").write_text(
        '{"row": 1}\n{"row": 2}\n', encoding="utf-8"
    )
    script = REPO_ROOT / "tools" / "parity_check.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--wiki", str(tmp_path), "--verify"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    assert "DRIFT" in proc.stdout or "drift" in proc.stdout.lower()


def test_manifest_includes_ship2_spine_paths(tmp_path):
    # Create a fake manifest matching the real one's structure
    manifest = (tmp_path / "pages" / "systems" / "parity-manifest.txt")
    manifest.parent.mkdir(parents=True)
    # Read the REAL manifest to drive the test
    real_manifest = Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/systems/parity-manifest.txt").read_text()
    assert "STATUS.md" in real_manifest
    assert "TASK_QUEUE.md" in real_manifest
    assert "pages/systems/lane-locks.json" in real_manifest
    assert "pages/systems/tasks.jsonl" in real_manifest


def test_parity_compute_handles_missing_ship2_files(tmp_path):
    """Ship-2 files are listed in the manifest but typically don't exist on disk yet.
    parity_check should treat them as empty bytes (matching the broken-symlink fallback)."""
    from tools import parity_check

    wiki = tmp_path
    (wiki / "pages" / "systems").mkdir(parents=True)
    (wiki / "pages" / "progress").mkdir(parents=True)
    manifest_path = wiki / "pages" / "systems" / "parity-manifest.txt"
    manifest_path.write_text(
        "# minimal\n"
        "STATUS.md\n"  # missing
        "pages/systems/lane-locks.json\n"  # missing
        "pages/systems/parity-manifest.txt\n"  # present (self)
    )

    parity = parity_check.compute_parity(wiki)
    assert "manifest_sha256" in parity
    # Both missing files should hash to empty-bytes sha256
    EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert parity["files"]["STATUS.md"] == EMPTY_SHA
    assert parity["files"]["pages/systems/lane-locks.json"] == EMPTY_SHA


def test_parity_hash_changes_when_status_md_appears(tmp_path):
    """When STATUS.md starts existing, the manifest hash must change."""
    from tools import parity_check

    wiki = tmp_path
    (wiki / "pages" / "systems").mkdir(parents=True)
    manifest_path = wiki / "pages" / "systems" / "parity-manifest.txt"
    manifest_path.write_text(
        "STATUS.md\n"
        "pages/systems/parity-manifest.txt\n"
    )

    parity_before = parity_check.compute_parity(wiki)

    # Now create STATUS.md
    (wiki / "STATUS.md").write_text("# STATUS\nactive lanes: claude, codex\n")

    parity_after = parity_check.compute_parity(wiki)

    assert parity_before["manifest_sha256"] != parity_after["manifest_sha256"]


def test_manifest_includes_ship3_library_paths():
    """Ship-3 library spine entries are pinned in the real manifest."""
    real_manifest = Path(
        "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/systems/parity-manifest.txt"
    ).read_text()
    assert "pages/systems/canonical-registry.jsonl" in real_manifest
    assert "pages/systems/library-health.json" in real_manifest
    assert "pages/systems/LIBRARY-HEALTH.md" in real_manifest
    assert ".gbrain/manifest.json" in real_manifest


def test_parity_compute_handles_missing_ship3_files(tmp_path):
    """Ship-3 files are listed but typically don't exist on disk yet (wave 1).
    parity_check should treat them as empty bytes (broken-symlink fallback pattern)."""
    from tools import parity_check

    wiki = tmp_path
    (wiki / "pages" / "systems").mkdir(parents=True)
    manifest_path = wiki / "pages" / "systems" / "parity-manifest.txt"
    manifest_path.write_text(
        "# minimal ship-3 only\n"
        "pages/systems/canonical-registry.jsonl\n"
        ".gbrain/manifest.json\n"
        "pages/systems/parity-manifest.txt\n"
    )

    parity = parity_check.compute_parity(wiki)
    assert "manifest_sha256" in parity
    EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert parity["files"]["pages/systems/canonical-registry.jsonl"] == EMPTY_SHA
    assert parity["files"][".gbrain/manifest.json"] == EMPTY_SHA
