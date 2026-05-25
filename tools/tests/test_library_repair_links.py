"""Unit tests for tools/library_repair_links.py (Ship 3 wave 5b).

Uses ``tmp_path`` as the wiki root, both via explicit ``wiki=`` kwargs
for direct function calls and via ``NOUS_WIKI`` env var for the CLI
subprocess test. Each test stages just the registry rows + markdown
files it needs, so they run in isolation.
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


def _load(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(
        name, TOOLS_DIR / rel_path
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load registry FIRST so library_repair_links can import it under either name.
reg = _load("library_canonical_registry", "library_canonical_registry.py")
# Mirror the bare-import path that tools/library_repair_links.py uses when
# called as a script (it tries `from tools import ...`, then falls back to
# bare `import library_canonical_registry`).
sys.modules.setdefault("library_canonical_registry", reg)
rl = _load("library_repair_links", "library_repair_links.py")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Empty vault → no links
# ---------------------------------------------------------------------------


def test_scan_wikilinks_empty_vault(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    links = rl.scan_wikilinks(tmp_path)
    assert links == []


# ---------------------------------------------------------------------------
# 2. Existing file resolves outright
# ---------------------------------------------------------------------------


def test_scan_wikilinks_resolves_existing_file(tmp_path: Path) -> None:
    _write(tmp_path / "pages" / "a.md", "see [[b]]\n")
    _write(tmp_path / "pages" / "b.md", "# B\n")
    links = rl.scan_wikilinks(tmp_path)
    by_target = {l["target"]: l for l in links}
    assert by_target["b"]["status"] == "resolved"
    assert by_target["b"]["candidates"] == []


# ---------------------------------------------------------------------------
# 3. Missing target → unknown
# ---------------------------------------------------------------------------


def test_scan_wikilinks_finds_unknown(tmp_path: Path) -> None:
    _write(tmp_path / "pages" / "a.md", "see [[does-not-exist]]\n")
    links = rl.scan_wikilinks(tmp_path)
    assert len(links) == 1
    row = links[0]
    assert row["target"] == "does-not-exist"
    assert row["status"] == "unknown"
    assert row["candidates"] == []
    assert row["source_path"] == "pages/a.md"
    assert row["line_num"] == 1


# ---------------------------------------------------------------------------
# 4. Two registry entries share an alias → multi_match
# ---------------------------------------------------------------------------


def test_scan_wikilinks_finds_multi_match_via_aliases(tmp_path: Path) -> None:
    # Both files exist on disk with the SAME stem (different folders), so the
    # file-on-disk lookup alone would also see two matches. We additionally
    # register both in the canonical registry so the alias path is exercised.
    skill = tmp_path / "pages" / "skills" / "factory-ops.md"
    system = tmp_path / "pages" / "systems" / "factory-ops.md"
    _write(skill, "# Skill\n")
    _write(system, "# System\n")
    reg.add(
        "pages/skills/factory-ops.md",
        title="Factory Ops (skill)",
        aliases=["factory-ops"],
        wiki=tmp_path,
    )
    reg.add(
        "pages/systems/factory-ops.md",
        title="Factory Ops (system)",
        aliases=["factory-ops"],
        wiki=tmp_path,
    )
    _write(tmp_path / "pages" / "x.md", "see [[factory-ops]]\n")

    links = rl.scan_wikilinks(tmp_path)
    # Only the wikilink in x.md should be considered. (skill + system pages
    # contain no wikilinks of their own.)
    hits = [l for l in links if l["target"] == "factory-ops"]
    assert len(hits) == 1
    row = hits[0]
    assert row["status"] == "multi_match"
    assert len(row["candidates"]) == 2


# ---------------------------------------------------------------------------
# 5. One registry alias hit → single_match
# ---------------------------------------------------------------------------


def test_scan_wikilinks_finds_single_match_via_alias(tmp_path: Path) -> None:
    # Canonical file lives at pages/skills/session-coordination.md but the
    # wikilink uses the alias 'session-coord'.
    canonical = tmp_path / "pages" / "skills" / "session-coordination.md"
    _write(canonical, "# Session Coordination\n")
    reg.add(
        "pages/skills/session-coordination.md",
        title="Session Coordination",
        aliases=["session-coord"],
        wiki=tmp_path,
    )
    _write(tmp_path / "pages" / "x.md", "see [[session-coord]]\n")

    links = rl.scan_wikilinks(tmp_path)
    hits = [l for l in links if l["target"] == "session-coord"]
    assert len(hits) == 1
    row = hits[0]
    assert row["status"] == "single_match"
    assert len(row["candidates"]) == 1
    assert (
        row["candidates"][0]["obsidian_path"]
        == "pages/skills/session-coordination.md"
    )


# ---------------------------------------------------------------------------
# 6. Empty broken list → "No broken wikilinks detected."
# ---------------------------------------------------------------------------


def test_write_broken_links_empty_message(tmp_path: Path) -> None:
    audit = rl.write_broken_links_audit(tmp_path, [])
    assert audit.exists()
    assert audit.parent == tmp_path / "pages" / "library"
    text = audit.read_text(encoding="utf-8")
    assert "No broken wikilinks detected." in text


# ---------------------------------------------------------------------------
# 7. Mixed broken list → distinct sections per status
# ---------------------------------------------------------------------------


def test_write_broken_links_lists_unknown_and_multi(tmp_path: Path) -> None:
    broken = [
        {
            "source_path": "pages/a.md",
            "line_num": 3,
            "target": "ghost",
            "display": None,
            "status": "unknown",
            "candidates": [],
        },
        {
            "source_path": "pages/b.md",
            "line_num": 7,
            "target": "factory-ops",
            "display": None,
            "status": "multi_match",
            "candidates": [
                {
                    "obsidian_path": "pages/skills/factory-ops.md",
                    "slug": "factory-ops-skill",
                    "title": "Factory Ops (skill)",
                },
                {
                    "obsidian_path": "pages/systems/factory-ops.md",
                    "slug": "factory-ops-system",
                    "title": "Factory Ops (system)",
                },
            ],
        },
    ]
    audit = rl.write_broken_links_audit(tmp_path, broken)
    text = audit.read_text(encoding="utf-8")
    assert "## Unknown targets" in text
    assert "## Multi-match targets" in text
    assert "pages/a.md" in text and "ghost" in text
    assert "pages/b.md" in text and "factory-ops" in text
    # The multi-match candidates list should surface both obsidian paths.
    assert "pages/skills/factory-ops.md" in text
    assert "pages/systems/factory-ops.md" in text


# ---------------------------------------------------------------------------
# 8. auto_repair rewrites single_match links in place
# ---------------------------------------------------------------------------


def test_auto_repair_rewrites_single_match(tmp_path: Path) -> None:
    canonical = tmp_path / "pages" / "skills" / "canonical-slug.md"
    _write(canonical, "# Canonical\n")
    reg.add(
        "pages/skills/canonical-slug.md",
        title="Canonical Slug",
        aliases=["old-alias"],
        wiki=tmp_path,
    )
    source = tmp_path / "pages" / "x.md"
    _write(source, "see [[old-alias]] and [[old-alias|labelled]]\n")

    links = rl.scan_wikilinks(tmp_path)
    rewrites = rl.auto_repair(tmp_path, links)
    assert rewrites >= 2  # one bare + one labelled occurrence

    after = source.read_text(encoding="utf-8")
    assert "[[canonical-slug]]" in after
    assert "[[canonical-slug|labelled]]" in after
    assert "[[old-alias]]" not in after
    assert "[[old-alias|" not in after


# ---------------------------------------------------------------------------
# 9. CLI with --apply --json reports a `rewrites` count
# ---------------------------------------------------------------------------


def test_main_cli_apply_flag_returns_rewrites_count(tmp_path: Path) -> None:
    canonical = tmp_path / "pages" / "skills" / "canonical-slug.md"
    _write(canonical, "# Canonical\n")
    # Use the registry directly with wiki=tmp_path to stage one alias.
    reg.add(
        "pages/skills/canonical-slug.md",
        title="Canonical Slug",
        aliases=["old-alias"],
        wiki=tmp_path,
    )
    _write(tmp_path / "pages" / "x.md", "see [[old-alias]]\n")

    env = os.environ.copy()
    env["NOUS_WIKI"] = str(tmp_path)
    env["PYTHONPATH"] = str(TOOLS_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library_repair_links.py"),
         "--apply", "--json"],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert "summary" in payload
    assert "rewrites" in payload["summary"]
    assert payload["summary"]["rewrites"] >= 1
    assert payload["audit_path"].startswith("pages/library/broken-links-")
