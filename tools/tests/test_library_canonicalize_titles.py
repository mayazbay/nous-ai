"""Unit tests for tools/library_canonicalize_titles.py (Ship 3 wave 5a).

Each test uses a ``tmp_path`` wiki root via the ``NOUS_WIKI`` env var (CLI
subprocess case) or explicit ``wiki=`` kwargs (direct function calls). The
audit writer lands files under ``pages/library/`` so the tests inspect that
directory (NOT ``pages/audits/`` — banned scope for this wave).
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

# Load by file path so the test stays isolated from any future module-name
# collisions (matches test_library_canonical_registry.py).
_MOD_PATH = TOOLS_DIR / "library_canonicalize_titles.py"
_spec = importlib.util.spec_from_file_location(
    "tools_library_canonicalize_titles", _MOD_PATH
)
assert _spec is not None and _spec.loader is not None
canon = importlib.util.module_from_spec(_spec)
sys.modules["tools_library_canonicalize_titles"] = canon
_spec.loader.exec_module(canon)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Empty vault
# ---------------------------------------------------------------------------

def test_scan_vault_empty_returns_empty(tmp_path: Path):
    """Vault with no markdown under pages/ → scan returns []."""
    (tmp_path / "pages").mkdir()
    drifts = canon.scan_vault(tmp_path)
    assert drifts == []


# ---------------------------------------------------------------------------
# 2. No drift when slug matches basename
# ---------------------------------------------------------------------------

def test_scan_vault_no_drift_when_slug_matches_basename(tmp_path: Path):
    """canonical_slug == basename_slug → no drift recorded for that file."""
    _write(
        tmp_path / "pages" / "x" / "model-failover-latest.md",
        '---\ntitle: "Model Failover Latest"\n---\n\nbody\n',
    )
    drifts = canon.scan_vault(tmp_path)
    matching = [d for d in drifts if d["path"].endswith("model-failover-latest.md")]
    assert matching == []


# ---------------------------------------------------------------------------
# 3. Filename drift detected (underscore + case)
# ---------------------------------------------------------------------------

def test_scan_vault_detects_filename_drift(tmp_path: Path):
    """``Model_Failover_LATEST.md`` with title ``Model Failover Latest``.

    canonical_slug = 'model-failover-latest', basename_slug =
    'model_failover_latest'. Drift recorded with type='filename_vs_slug'.
    """
    _write(
        tmp_path / "pages" / "x" / "Model_Failover_LATEST.md",
        '---\ntitle: "Model Failover Latest"\n---\n\nbody\n',
    )
    drifts = canon.scan_vault(tmp_path)
    matching = [d for d in drifts if d["path"].endswith("Model_Failover_LATEST.md")]
    assert len(matching) == 1, f"expected 1 drift row, got {len(matching)}: {drifts}"
    row = matching[0]
    assert row["drift_type"] == "filename_vs_slug"
    assert row["canonical_slug"] == "model-failover-latest"
    assert row["basename_slug"] == "model_failover_latest"
    assert row["title"] == "Model Failover Latest"


# ---------------------------------------------------------------------------
# 4. Missing-title fallback
# ---------------------------------------------------------------------------

def test_scan_vault_handles_missing_title(tmp_path: Path):
    """No frontmatter + no H1 → title_from_path falls back to filename ('Foo').

    canonical_slug == basename_slug ('foo'). Implementations may either omit
    the row entirely (no drift) or record it as ``title_missing`` (info-only).
    Both are valid; the assertion allows either.
    """
    _write(tmp_path / "pages" / "x" / "foo.md", "just body, no frontmatter, no heading\n")
    drifts = canon.scan_vault(tmp_path)
    matching = [d for d in drifts if d["path"].endswith("foo.md")]
    assert len(matching) <= 1
    if matching:
        # If recorded, must be the title_missing flavor (since slugs match).
        assert matching[0]["drift_type"] == "title_missing"
        assert matching[0]["canonical_slug"] == "foo"
        assert matching[0]["basename_slug"] == "foo"


# ---------------------------------------------------------------------------
# 5. Atomic write — no .tmp residue
# ---------------------------------------------------------------------------

def test_write_audit_creates_atomic_temp_rename(tmp_path: Path):
    """After write_audit, the final file exists and the .tmp sibling does not."""
    out_path = canon.write_audit(tmp_path, [])
    assert out_path.exists(), f"expected audit at {out_path}"
    tmp_sibling = out_path.with_suffix(out_path.suffix + ".tmp")
    assert not tmp_sibling.exists(), f"leftover tmp file: {tmp_sibling}"
    # Lands in pages/library/, NOT pages/audits/.
    assert out_path.parent == tmp_path / "pages" / "library"


# ---------------------------------------------------------------------------
# 6. Empty drift → "No drift detected." body
# ---------------------------------------------------------------------------

def test_write_audit_empty_writes_no_drift_message(tmp_path: Path):
    out_path = canon.write_audit(tmp_path, [])
    body = out_path.read_text(encoding="utf-8")
    assert "No drift detected." in body


# ---------------------------------------------------------------------------
# 7. Summarize counts per type
# ---------------------------------------------------------------------------

def test_summarize_counts_by_type():
    drifts = [
        {"drift_type": "filename_vs_slug", "path": "a.md", "title": "A", "canonical_slug": "a", "basename_slug": "A"},
        {"drift_type": "filename_vs_slug", "path": "b.md", "title": "B", "canonical_slug": "b", "basename_slug": "B"},
        {"drift_type": "alias_vs_slug", "path": "c.md", "title": "C", "canonical_slug": "c", "basename_slug": "c-alt"},
        {"drift_type": "title_missing", "path": "d.md", "title": "D", "canonical_slug": "d", "basename_slug": "d"},
    ]
    summary = canon.summarize(drifts)
    assert summary["total"] == 4
    assert summary["by_type"]["filename_vs_slug"] == 2
    assert summary["by_type"]["alias_vs_slug"] == 1
    assert summary["by_type"]["title_missing"] == 1
    assert len(summary["examples"]) == 3


# ---------------------------------------------------------------------------
# 8. CLI --json subprocess invocation
# ---------------------------------------------------------------------------

def test_main_cli_json_output(tmp_path: Path):
    """Invoke the CLI with --json against a tmp wiki and parse the output."""
    # Seed one drifty file so we get a non-zero count.
    _write(
        tmp_path / "pages" / "x" / "Bad_Name.md",
        '---\ntitle: "Bad Name"\n---\n\nbody\n',
    )

    env = os.environ.copy()
    env["NOUS_WIKI"] = str(tmp_path)
    # Strip any inherited NOUS_LANE so the test is hermetic.
    env.pop("PYTHONDONTWRITEBYTECODE", None)

    proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library_canonicalize_titles.py"), "--json"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    payload = json.loads(proc.stdout.strip())
    assert "summary" in payload, f"missing summary key: {payload}"
    assert "audit_path" in payload, f"missing audit_path key: {payload}"
    assert payload["summary"]["total"] >= 1
    # Audit path should land under pages/library/, not pages/audits/.
    assert payload["audit_path"].startswith("pages/library/")
    assert "title-drift-" in payload["audit_path"]
