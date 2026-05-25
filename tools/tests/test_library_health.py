"""Unit tests for tools/library_health.py (Ship 3 wave 6).

Each test uses ``tmp_path`` as the wiki root via the ``NOUS_WIKI`` env var
(for the CLI subprocess tests) and explicit ``wiki=`` kwargs (for direct
function calls). The dashboard's atomic temp+rename writes and fail-soft
behavior for missing inputs are exercised in isolation per test.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Load by file path to keep isolated from any future module-name collisions
# (matches the pattern used in test_library_canonical_registry.py).
_MOD_PATH = TOOLS_DIR / "library_health.py"
_spec = importlib.util.spec_from_file_location("tools_library_health", _MOD_PATH)
assert _spec is not None and _spec.loader is not None
lh = importlib.util.module_from_spec(_spec)
sys.modules["tools_library_health"] = lh
_spec.loader.exec_module(lh)


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

def test_count_obsidian_files_empty_returns_zero(tmp_path: Path) -> None:
    # tmp wiki has no pages/ directory at all.
    assert lh.count_obsidian_files(tmp_path) == 0


def test_count_obsidian_files_counts_md_in_pages(tmp_path: Path) -> None:
    (tmp_path / "pages" / "a").mkdir(parents=True)
    (tmp_path / "pages" / "b").mkdir(parents=True)
    (tmp_path / "pages" / "a" / "x.md").write_text("# X\n", encoding="utf-8")
    (tmp_path / "pages" / "b" / "y.md").write_text("# Y\n", encoding="utf-8")
    # A non-.md file should NOT be counted.
    (tmp_path / "pages" / "b" / "ignore.txt").write_text("z", encoding="utf-8")
    assert lh.count_obsidian_files(tmp_path) == 2


def test_count_canonical_registry_empty_returns_zero(tmp_path: Path) -> None:
    # No pages/systems/canonical-registry.jsonl yet.
    assert lh.count_canonical_registry(tmp_path) == 0


def test_count_gbrain_state_no_db(tmp_path: Path) -> None:
    state = lh.count_gbrain_state(tmp_path)
    assert isinstance(state, dict)
    assert state["db_exists"] is False
    assert state["indexed_chunks"] == 0
    assert state["pending_queue"] == 0
    assert state["sqlite_vec_loaded"] is False


def test_parity_hash_empty_when_missing(tmp_path: Path) -> None:
    # No pages/systems/parity-latest.json — returns "".
    assert lh.parity_hash(tmp_path) == ""


# ---------------------------------------------------------------------------
# Snapshot composition
# ---------------------------------------------------------------------------

REQUIRED_KEYS = (
    "ts",
    "host",
    "obsidian_files",
    "canonical_registry_size",
    "gbrain_indexed_chunks",
    "gbrain_pending_queue",
    "gbrain_db_exists",
    "gbrain_sqlite_vec_loaded",
    "broken_links_last_audit",
    "broken_links_count_last_audit",
    "title_drift_last_audit",
    "title_drift_count_last_audit",
    "latest_failover_event_status",
    "parity_manifest_sha256",
)


def test_compute_returns_all_required_keys(tmp_path: Path) -> None:
    snapshot = lh.compute(tmp_path)
    missing = [k for k in REQUIRED_KEYS if k not in snapshot]
    assert missing == [], f"missing keys: {missing}"
    # Sanity: empty wiki -> all counts 0, booleans False, audits None.
    assert snapshot["obsidian_files"] == 0
    assert snapshot["canonical_registry_size"] == 0
    assert snapshot["gbrain_indexed_chunks"] == 0
    assert snapshot["gbrain_pending_queue"] == 0
    assert snapshot["gbrain_db_exists"] is False
    assert snapshot["gbrain_sqlite_vec_loaded"] is False
    assert snapshot["broken_links_last_audit"] is None
    assert snapshot["broken_links_count_last_audit"] == 0
    assert snapshot["title_drift_last_audit"] is None
    assert snapshot["title_drift_count_last_audit"] == 0
    assert snapshot["latest_failover_event_status"] is None
    assert snapshot["parity_manifest_sha256"] == ""


# ---------------------------------------------------------------------------
# Atomic write + markdown
# ---------------------------------------------------------------------------

def test_write_atomic_creates_both_files(tmp_path: Path) -> None:
    snapshot = lh.compute(tmp_path)
    json_path, md_path = lh.write_atomic(tmp_path, snapshot)

    assert json_path == tmp_path / lh.HEALTH_JSON_REL
    assert md_path == tmp_path / lh.HEALTH_MD_REL
    assert json_path.exists()
    assert md_path.exists()

    # No leftover .tmp sidecar files.
    json_tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    md_tmp = md_path.with_suffix(md_path.suffix + ".tmp")
    assert not json_tmp.exists()
    assert not md_tmp.exists()

    # JSON parses + contains required keys.
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    for key in REQUIRED_KEYS:
        assert key in payload


def test_render_markdown_contains_header_and_snapshot_table() -> None:
    fake = {
        "ts": "2026-05-20T18:00:00+05:00",
        "host": "fakehost",
        "obsidian_files": 42,
        "canonical_registry_size": 7,
        "gbrain_indexed_chunks": 0,
        "gbrain_pending_queue": 0,
        "gbrain_db_exists": False,
        "gbrain_sqlite_vec_loaded": False,
        "broken_links_last_audit": None,
        "broken_links_count_last_audit": 0,
        "title_drift_last_audit": None,
        "title_drift_count_last_audit": 0,
        "latest_failover_event_status": None,
        "parity_manifest_sha256": "",
    }
    md = lh.render_markdown(fake)
    assert md.startswith("---\ntype: system\n")
    assert 'title: "LIBRARY-HEALTH"' in md
    assert "date: 2026-05-20" in md
    assert "# LIBRARY-HEALTH" in md
    # The Snapshot table must contain a row for obsidian_files with its value.
    assert "`obsidian_files`" in md
    # The value 42 should be rendered as a backticked cell.
    assert "`42`" in md


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run_cli(wiki: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    """Run library_health.py CLI with NOUS_WIKI set to ``wiki``."""
    env = dict(os.environ)
    env["NOUS_WIKI"] = str(wiki)
    return subprocess.run(
        [sys.executable, str(_MOD_PATH), "--wiki", str(wiki), *extra],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_main_cli_no_write_does_not_create_files(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--no-write", "--json")
    assert result.returncode == 0, result.stderr
    # JSON output parses.
    payload = json.loads(result.stdout)
    assert "obsidian_files" in payload
    # Dashboard files were NOT created.
    assert not (tmp_path / lh.HEALTH_JSON_REL).exists()
    assert not (tmp_path / lh.HEALTH_MD_REL).exists()


def test_main_cli_writes_both_files(tmp_path: Path) -> None:
    result = _run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    json_path = tmp_path / lh.HEALTH_JSON_REL
    md_path = tmp_path / lh.HEALTH_MD_REL
    assert json_path.exists()
    assert md_path.exists()
    # Parses + has required keys.
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    for key in REQUIRED_KEYS:
        assert key in payload
    # Markdown contains frontmatter and the header.
    md = md_path.read_text(encoding="utf-8")
    assert md.startswith("---\ntype: system\n")
    assert "# LIBRARY-HEALTH" in md
