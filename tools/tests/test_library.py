"""Unit tests for tools/library.py — Ship 3 wave 3 unified CLI.

Exercises:
  - obsidian_search ripgrep round-trip + fail-soft paths
  - rrf_merge dedup + rank ordering
  - search router system-filter
  - cmd_stub exit code 2 + NOT_IMPLEMENTED message
  - cmd_registry round-trip via subprocess
  - cmd_embed via subprocess with --prefer stub
  - openbrain_search + gbrain_search fail-soft
  - search router never raises when all sub-searches fail

All tests use ``tmp_path`` as an isolated wiki via the ``NOUS_WIKI`` env or
explicit ``wiki=`` kwarg, mirroring the pattern in test_library_canonical_registry.py.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

def _has_rg() -> bool:
    """Detect ripgrep using the same resolver library.py uses."""
    # Import lazily; this file is loaded before library at module top.
    if shutil.which("rg"):
        return True
    fallbacks = [
        "/opt/homebrew/bin/rg",
        "/usr/local/bin/rg",
        "/usr/bin/rg",
        "/opt/homebrew/opt/ripgrep/bin/rg",
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-darwin/rg",
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/x64-darwin/rg",
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/x64-linux/rg",
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-linux/rg",
    ]
    for p in fallbacks:
        if Path(p).is_file() and os.access(p, os.X_OK):
            return True
    return False


_HAS_RG = _has_rg()

THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Load tools/library.py by file path to keep it isolated from any future
# module-name collisions, matching the loading convention used by sibling tests.
_MOD_PATH = TOOLS_DIR / "library.py"
_spec = importlib.util.spec_from_file_location("tools_library", _MOD_PATH)
assert _spec is not None and _spec.loader is not None
library = importlib.util.module_from_spec(_spec)
sys.modules["tools_library"] = library
_spec.loader.exec_module(library)


def _write_markdown(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. obsidian_search finds keyword
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_RG, reason="ripgrep (`rg`) not installed on PATH")
def test_obsidian_search_finds_keyword_in_tmp_vault(tmp_path: Path) -> None:
    _write_markdown(
        tmp_path / "pages" / "a.md",
        "# Note A\n\nThis note talks about Telegram routing and bots.\n",
    )
    _write_markdown(
        tmp_path / "pages" / "b.md",
        "# Note B\n\nThis note is about cameras and Hikvision.\n",
    )
    hits = library.obsidian_search("telegram", wiki=tmp_path)
    assert isinstance(hits, list)
    assert len(hits) >= 1, f"expected >=1 hit, got: {hits!r}"
    paths = [h["path"] for h in hits]
    assert any("a.md" in p for p in paths), f"expected a.md in paths: {paths!r}"
    assert all("rank" in h for h in hits), "every hit must have a rank"
    assert hits[0]["rank"] == 1, "first hit must be rank 1"


# ---------------------------------------------------------------------------
# 2. obsidian_search returns empty when no match
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_RG, reason="ripgrep (`rg`) not installed on PATH")
def test_obsidian_search_returns_empty_when_no_match(tmp_path: Path) -> None:
    _write_markdown(
        tmp_path / "pages" / "a.md",
        "# Note A\n\nNothing relevant here.\n",
    )
    hits = library.obsidian_search("xyzqzz123uncommon", wiki=tmp_path)
    assert hits == []


# ---------------------------------------------------------------------------
# 3. obsidian_search handles rg missing (FileNotFoundError)
# ---------------------------------------------------------------------------


def test_obsidian_search_handles_rg_missing(tmp_path: Path, monkeypatch) -> None:
    _write_markdown(tmp_path / "pages" / "a.md", "# A\ntelegram\n")

    def _raise(*args, **kwargs):
        raise FileNotFoundError("rg not installed")

    monkeypatch.setattr(library.subprocess, "run", _raise)
    hits = library.obsidian_search("telegram", wiki=tmp_path)
    assert hits == []


# ---------------------------------------------------------------------------
# 4. RRF dedup by canonical_uuid
# ---------------------------------------------------------------------------


def test_rrf_merge_deduplicates_by_canonical_uuid(tmp_path: Path) -> None:
    # Seed the registry so the obsidian result resolves to a UUID matching the
    # gbrain result.
    md_rel = "pages/dedup.md"
    _write_markdown(tmp_path / md_rel, "# Dedup\n\ntelegram bot routing\n")
    uid = library.registry.add(md_rel, wiki=tmp_path)

    results_by_system = {
        "obsidian": [
            {"path": md_rel, "snippet": "snippet a", "rank": 1, "match_count": 1},
        ],
        "gbrain": [
            {
                "canonical_uuid": uid,
                "title": "Dedup",
                "obsidian_path": md_rel,
                "snippet": "vector snippet",
                "distance": 0.05,
                "rank": 1,
            },
        ],
    }
    fused = library.rrf_merge(results_by_system, wiki=tmp_path)
    assert len(fused) == 1, f"expected dedup to 1 hit, got: {fused!r}"
    hit = fused[0]
    assert hit.canonical_uuid == uid
    assert set(hit.system_sources) == {"obsidian", "gbrain"}


# ---------------------------------------------------------------------------
# 5. RRF higher rank wins
# ---------------------------------------------------------------------------


def test_rrf_merge_higher_rank_wins(tmp_path: Path) -> None:
    # A is rank 1 in obsidian + rank 2 in gbrain.
    # B is rank 1 in openbrain only.
    # A's RRF score = 1/(60+1) + 1/(60+2); B's = 1/(60+1). A > B.
    md_a = "pages/a.md"
    _write_markdown(tmp_path / md_a, "# A\nbody\n")
    uid_a = library.registry.add(md_a, wiki=tmp_path)

    md_b = "pages/b.md"
    _write_markdown(tmp_path / md_b, "# B\nbody\n")
    uid_b = library.registry.add(md_b, wiki=tmp_path, aliases=["thought-b"])

    results_by_system = {
        "obsidian": [
            {"path": md_a, "snippet": "a", "rank": 1, "match_count": 2},
        ],
        "gbrain": [
            {
                "canonical_uuid": uid_a,
                "title": "A",
                "obsidian_path": md_a,
                "snippet": "a",
                "distance": 0.1,
                "rank": 2,
            },
        ],
        "openbrain": [
            {"thought_id": "thought-b", "title": "B", "snippet": "b", "rank": 1},
        ],
    }
    fused = library.rrf_merge(results_by_system, wiki=tmp_path)
    assert len(fused) == 2
    assert fused[0].canonical_uuid == uid_a, f"expected A first, got: {fused!r}"
    assert fused[1].canonical_uuid == uid_b
    assert fused[0].score > fused[1].score


# ---------------------------------------------------------------------------
# 6. search router system='obsidian' skips other systems
# ---------------------------------------------------------------------------


def test_search_with_system_obsidian_only_skips_others(
    tmp_path: Path, monkeypatch
) -> None:
    calls: dict[str, int] = {"obsidian": 0, "gbrain": 0, "openbrain": 0}

    def _ob(query, *, wiki, top=30):
        calls["obsidian"] += 1
        return []

    def _gb(query, *, wiki, top=30):
        calls["gbrain"] += 1
        return []

    def _op(query, *, top=30):
        calls["openbrain"] += 1
        return []

    monkeypatch.setattr(library, "obsidian_search", _ob)
    monkeypatch.setattr(library, "gbrain_search", _gb)
    monkeypatch.setattr(library, "openbrain_search", _op)

    library.search("anything", wiki=tmp_path, system="obsidian")
    assert calls == {"obsidian": 1, "gbrain": 0, "openbrain": 0}, (
        f"system='obsidian' must only call obsidian_search, saw: {calls!r}"
    )


# ---------------------------------------------------------------------------
# 7. cmd_stub exits 2 with NOT_IMPLEMENTED message
# ---------------------------------------------------------------------------


def test_cmd_stub_exits_2(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["NOUS_WIKI"] = str(tmp_path)
    env["PYTHONPATH"] = str(TOOLS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library.py"), "rebuild"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode == 2, f"expected exit 2, got {proc.returncode}; stderr={proc.stderr!r}"
    assert "NOT_IMPLEMENTED" in proc.stderr, f"missing NOT_IMPLEMENTED in stderr: {proc.stderr!r}"


# ---------------------------------------------------------------------------
# 8. registry add -> get round trip via CLI
# ---------------------------------------------------------------------------


def test_cmd_registry_add_get_round_trip(tmp_path: Path) -> None:
    md_rel = "pages/foo.md"
    _write_markdown(tmp_path / md_rel, "# Foo\nBody.\n")
    env = dict(os.environ)
    env["NOUS_WIKI"] = str(tmp_path)
    env["PYTHONPATH"] = str(TOOLS_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    add_proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library.py"),
         "registry", "add", "--path", md_rel],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert add_proc.returncode == 0, f"add failed: {add_proc.stderr!r}"
    uid = add_proc.stdout.strip()
    assert len(uid) == 26, f"expected ULID, got {uid!r}"

    get_proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library.py"),
         "registry", "get", "--uuid", uid, "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert get_proc.returncode == 0, f"get failed: {get_proc.stderr!r}"
    entry = json.loads(get_proc.stdout)
    assert entry["canonical_uuid"] == uid
    assert entry["obsidian_path"] == md_rel
    for key in ("title", "slug", "aliases", "created", "updated", "content_hash"):
        assert key in entry, f"missing key {key} in entry: {entry!r}"


# ---------------------------------------------------------------------------
# 9. embed via CLI with --prefer stub
# ---------------------------------------------------------------------------


def test_cmd_embed_with_stub_prefer(tmp_path: Path) -> None:
    md_path = tmp_path / "pages" / "note.md"
    _write_markdown(md_path, "# Note\n\n## Section\n\nBody text.\n")
    env = dict(os.environ)
    env["NOUS_WIKI"] = str(tmp_path)
    env["PYTHONPATH"] = str(TOOLS_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library.py"),
         "embed", str(md_path), "--prefer", "stub", "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0, f"embed failed: {proc.stderr!r}"
    payload = json.loads(proc.stdout)
    assert "chunks" in payload, f"missing chunks: {payload!r}"
    assert "embeddings" in payload, f"missing embeddings: {payload!r}"
    assert len(payload["chunks"]) >= 1
    assert len(payload["embeddings"]) == len(payload["chunks"])
    for emb in payload["embeddings"]:
        assert emb.get("error", "") == "", f"unexpected error: {emb!r}"
        assert emb["dim"] > 0


# ---------------------------------------------------------------------------
# 10. openbrain_search handles mcp missing
# ---------------------------------------------------------------------------


def test_openbrain_search_handles_mcp_missing_returns_empty(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise FileNotFoundError("mcp not installed")

    monkeypatch.setattr(library.subprocess, "run", _raise)
    hits = library.openbrain_search("anything")
    assert hits == []


# ---------------------------------------------------------------------------
# 11. gbrain_search returns [] when embedder auth_missing
# ---------------------------------------------------------------------------


def test_gbrain_search_empty_when_auth_missing(tmp_path: Path, monkeypatch) -> None:
    class _AuthMissingEmbedder:
        name = "voyage-3-lite"
        dim = 0

        def embed(self, chunks):
            from library_embed import EmbeddingResult
            return [
                EmbeddingResult(
                    chunk_idx=c.chunk_idx,
                    vector=[],
                    dim=0,
                    model=self.name,
                    error="auth_missing",
                )
                for c in chunks
            ]

    def _make_embedder(*, prefer="voyage"):
        return _AuthMissingEmbedder()

    monkeypatch.setattr(library.embed_voyage, "make_embedder", _make_embedder)
    hits = library.gbrain_search("anything", wiki=tmp_path)
    assert hits == []


# ---------------------------------------------------------------------------
# 12. search router returns [] when every sub-search raises
# ---------------------------------------------------------------------------


def test_search_router_returns_empty_list_when_all_systems_fail(
    tmp_path: Path, monkeypatch
) -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(library, "obsidian_search", _boom)
    monkeypatch.setattr(library, "gbrain_search", _boom)
    monkeypatch.setattr(library, "openbrain_search", _boom)

    # search() itself MUST NOT raise even when all sub-searches blow up.
    hits = library.search("query", wiki=tmp_path, system="all")
    assert hits == []
