"""Tests for tools/library_embed.py (Ship 3 wave 1b)."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

# Make tools/ importable when running pytest from any cwd.
TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

from library_embed import (  # noqa: E402
    CHARS_PER_TOKEN,
    Chunk,
    EmbedderStub,
    chunk_file,
    chunk_markdown,
    estimate_tokens,
    normalize_chunk_text,
    sliding_window,
    split_on_headings,
    strip_frontmatter,
)


SCRIPT = TOOLS_DIR / "library_embed.py"


# --- frontmatter -----------------------------------------------------------


def test_strip_frontmatter_basic() -> None:
    md = "---\ntitle: x\n---\n# H\nbody"
    assert strip_frontmatter(md) == "# H\nbody"


def test_strip_frontmatter_no_frontmatter_unchanged() -> None:
    md = "# H\nbody"
    assert strip_frontmatter(md) == md


# --- normalize -------------------------------------------------------------


def test_normalize_chunk_text_strips_and_collapses() -> None:
    raw = "  \n\nfoo\n\n\nbar  \n"
    assert normalize_chunk_text(raw) == "foo\n\nbar"


# --- token estimate --------------------------------------------------------


def test_estimate_tokens() -> None:
    assert CHARS_PER_TOKEN == 4
    assert estimate_tokens("a" * 400) == 100


# --- heading split ---------------------------------------------------------


def test_split_on_headings_h2_h3() -> None:
    md = (
        "## H2\n"
        "intro under H2\n"
        "### H3a\n"
        "alpha body\n"
        "### H3b\n"
        "beta body\n"
    )
    sections = split_on_headings(md)
    paths = [p for p, _ in sections]
    assert paths == ["H2", "H2 > H3a", "H2 > H3b"]
    # Bodies non-empty.
    for _, text in sections:
        assert text.strip()


def test_split_on_headings_preamble() -> None:
    md = "preamble text\nmore preamble\n## First H2\nbody"
    sections = split_on_headings(md)
    assert sections[0][0] == ""
    assert "preamble" in sections[0][1]
    assert sections[1][0] == "First H2"


# --- sliding window --------------------------------------------------------


def test_sliding_window_under_max_returns_single() -> None:
    text = "short text"
    out = sliding_window(text, max_tokens=128, overlap_tokens=32)
    assert out == [text]


def test_sliding_window_long_text_creates_overlap() -> None:
    # 2000 chars => ~500 estimated tokens. max_tokens=128 (=512 chars window),
    # overlap=32 (=128 chars overlap). Should produce >=2 windows that share text.
    text = ("word " * 400).strip()  # ~2000 chars of " "-separated tokens
    assert len(text) >= 1500
    windows = sliding_window(text, max_tokens=128, overlap_tokens=32)
    assert len(windows) >= 2, f"expected >=2 windows, got {len(windows)}"
    # Consecutive windows must share content (the overlap region).
    # We verify by checking that the tail of window[i] appears somewhere in
    # window[i+1] (since sliding overlap re-emits the trailing text).
    for i in range(len(windows) - 1):
        tail = windows[i][-40:].strip()
        assert tail and tail in windows[i + 1], (
            f"overlap missing between windows {i} and {i + 1}"
        )


# --- chunk_markdown --------------------------------------------------------


def test_chunk_markdown_emits_unique_hashes_per_chunk() -> None:
    md = (
        "## Section One\n"
        "Apple banana cherry.\n"
        "## Section Two\n"
        "Dingo elephant fox.\n"
        "## Section Three\n"
        "Goat hippo iguana.\n"
    )
    chunks = chunk_markdown(md)
    assert len(chunks) == 3
    hashes = {c.content_hash for c in chunks}
    assert len(hashes) == 3
    for c in chunks:
        assert c.content_hash.startswith("sha256:")


def test_chunk_markdown_idx_monotonic() -> None:
    md = (
        "## A\nfirst\n"
        "## B\nsecond\n"
        "## C\nthird\n"
        "## D\nfourth\n"
    )
    chunks = chunk_markdown(md)
    idxs = [c.chunk_idx for c in chunks]
    assert idxs == list(range(len(chunks)))


# --- chunk_file ------------------------------------------------------------


def test_chunk_file_missing_returns_empty(tmp_path: pathlib.Path) -> None:
    missing = tmp_path / "nope.md"
    assert chunk_file(missing) == []


# --- EmbedderStub ----------------------------------------------------------


def test_embedder_stub_deterministic() -> None:
    chunk = Chunk(
        chunk_idx=0,
        heading_path="H",
        text="determinism test text",
        content_hash="sha256:deadbeef",
    )
    e = EmbedderStub()
    r1 = e.embed([chunk])
    r2 = e.embed([chunk])
    assert r1[0].vector == r2[0].vector  # bit-exact across calls


def test_embedder_stub_vector_length_equals_dim() -> None:
    chunk = Chunk(
        chunk_idx=0,
        heading_path="",
        text="any text",
        content_hash="sha256:x",
    )
    e = EmbedderStub()
    [r] = e.embed([chunk])
    assert r.dim == 32
    assert len(r.vector) == 32
    # All floats in [0, 1).
    for v in r.vector:
        assert 0.0 <= v < 1.0


# --- CLI -------------------------------------------------------------------


def test_main_cli_json_output(tmp_path: pathlib.Path) -> None:
    md_path = tmp_path / "doc.md"
    md_path.write_text(
        "## One\nalpha body text.\n## Two\nbeta body text.\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(md_path), "--json"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert payload[0]["heading_path"] == "One"
    assert payload[1]["heading_path"] == "Two"
    for entry in payload:
        assert "chunk_idx" in entry
        assert "text" in entry
        assert entry["content_hash"].startswith("sha256:")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
