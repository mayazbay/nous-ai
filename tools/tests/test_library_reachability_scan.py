"""Unit tests for tools/library_reachability_scan.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent

_MOD_PATH = TOOLS_DIR / "library_reachability_scan.py"
_spec = importlib.util.spec_from_file_location("tools_library_reachability_scan", _MOD_PATH)
assert _spec is not None and _spec.loader is not None
scan = importlib.util.module_from_spec(_spec)
sys.modules["tools_library_reachability_scan"] = scan
_spec.loader.exec_module(scan)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_collect_prose_hits_streams_files_without_joining_corpus(tmp_path: Path, monkeypatch) -> None:
    """Prose reachability should be computed as term hits, not a giant corpus."""

    monkeypatch.setattr(scan, "ROOT", tmp_path)

    _write(
        tmp_path / "pages" / "skills" / "router" / "SKILL.md",
        "This skill links the alpha-page concept and nothing else.\n",
    )
    _write(
        tmp_path / "pages" / "audits" / "self-audit.md",
        "The beta-page mention is self-referential and excluded.\n",
    )

    hits = scan.collect_prose_hits(
        ("pages/skills", "pages/audits"),
        {"alpha-page", "beta-page", "missing-page"},
        exclude_paths={"pages/audits/self-audit.md"},
    )

    assert hits == {"alpha-page"}
