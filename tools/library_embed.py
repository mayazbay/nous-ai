#!/usr/bin/env python3
"""Library-embed chunker skeleton (Ship 3 wave 1b).

Markdown-aware chunker + EmbedderStub interface. Stdlib only. The real
sqlite-vec + voyage-3-lite / all-MiniLM-L6-v2 embedder lands in Ship 3 wave 2;
this file defines the pipeline that wave 2 will wire against.

Pipeline:
    strip_frontmatter -> split_on_headings (H2/H3-aware) -> for each section,
    if estimate_tokens(text) > max_tokens: sliding_window; else: emit single chunk.
    Each chunk carries chunk_idx (0-based across doc), heading_path (">"-joined
    H2/H3 trail), text, content_hash (sha256:<hex> of normalize_chunk_text(text)).

CLI:
    python3 tools/library_embed.py <path>                  # human-readable list
    python3 tools/library_embed.py <path> --json           # JSON list of chunks
    python3 tools/library_embed.py <path> --embed --json   # chunks + stub vectors
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# Rough chars-per-token estimate; tightened by tokenizer once installed.
CHARS_PER_TOKEN = 4
DEFAULT_MAX_CHUNK_TOKENS = 512
DEFAULT_WINDOW_OVERLAP_TOKENS = 64

# Frontmatter: leading `---\n ... \n---\n` block at start of file.
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
# Collapse runs of >=2 blank lines into a single blank line.
_BLANK_RUN_RE = re.compile(r"\n[ \t]*\n[ \t\n]*")
# H2/H3 detection: line starts with `## ` or `### ` (exactly 2 or 3 hashes).
_H2_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$")
_H3_RE = re.compile(r"^###[ \t]+(.+?)[ \t]*$")


@dataclasses.dataclass(frozen=True)
class Chunk:
    """A single chunk of a markdown doc.

    Attributes:
        chunk_idx:    0-based index across the whole document.
        heading_path: ">"-joined trail of open H2/H3 headings; "" for preamble.
        text:         Chunk body text (raw, not normalized).
        content_hash: sha256:<hex> of normalize_chunk_text(text).
    """

    chunk_idx: int
    heading_path: str
    text: str
    content_hash: str

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def strip_frontmatter(md: str) -> str:
    """Strip a leading `---\\n ... \\n---\\n` block. No frontmatter -> unchanged."""
    return _FRONTMATTER_RE.sub("", md, count=1)


def normalize_chunk_text(text: str) -> str:
    """Normalize for hashing: strip outer whitespace, collapse blank-line runs."""
    stripped = text.strip()
    if not stripped:
        return ""
    return _BLANK_RUN_RE.sub("\n\n", stripped)


def estimate_tokens(text: str) -> int:
    """Rough estimate via char count // CHARS_PER_TOKEN."""
    return len(text) // CHARS_PER_TOKEN


def _heading_path(h2: str, h3: str) -> str:
    parts = [p for p in (h2, h3) if p]
    return " > ".join(parts)


def split_on_headings(body: str) -> list[tuple[str, str]]:
    """Split body on H2/H3 lines.

    Returns list of (heading_path, section_text) tuples. heading_path is the
    ">"-joined trail of currently-open H2/H3 levels. Text BEFORE any H2/H3
    becomes a "preamble" section with heading_path == "" if non-empty (else
    dropped). H2 resets the H3 trail; H3 only updates the H3 level.
    """
    sections: list[tuple[str, str]] = []
    current_h2 = ""
    current_h3 = ""
    current_path = ""
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        text = "\n".join(buf).strip("\n")
        # Drop trailing-whitespace-only sections but keep semantically-empty
        # ones if they had non-whitespace content (we strip newlines not spaces).
        if text.strip() == "" and current_path == "":
            buf.clear()
            return
        sections.append((current_path, text))
        buf.clear()

    for line in body.splitlines():
        m2 = _H2_RE.match(line)
        m3 = _H3_RE.match(line)
        if m2:
            flush()
            current_h2 = m2.group(1).strip()
            current_h3 = ""
            current_path = _heading_path(current_h2, current_h3)
            continue
        if m3:
            flush()
            current_h3 = m3.group(1).strip()
            current_path = _heading_path(current_h2, current_h3)
            continue
        buf.append(line)

    flush()
    return sections


def sliding_window(text: str, *, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split long text into overlapping windows of <= max_tokens (estimated).

    Each window advances by (max_tokens - overlap_tokens) tokens. Boundaries
    snap to nearest preceding whitespace when possible. Short text -> [text].
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be > 0")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be in [0, max_tokens)")

    if estimate_tokens(text) <= max_tokens:
        return [text]

    max_chars = max_tokens * CHARS_PER_TOKEN
    step_chars = (max_tokens - overlap_tokens) * CHARS_PER_TOKEN
    if step_chars <= 0:
        step_chars = max_chars  # defensive; covered by guard above

    windows: list[str] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + max_chars, n)
        # Snap end backwards to a whitespace boundary if we're mid-word and
        # not at the very end of the text.
        if end < n:
            snap = text.rfind(" ", start, end)
            # Only snap if it doesn't shrink window to <50% of target — keeps
            # behavior bounded if no whitespace is found.
            if snap > start and (end - snap) < (max_chars // 2):
                end = snap
        windows.append(text[start:end])
        if end >= n:
            break
        start = start + step_chars
        # Snap start to next whitespace for cleaner window starts where possible.
        if start < n:
            snap = text.find(" ", start)
            if snap != -1 and (snap - start) < (step_chars // 4):
                start = snap + 1
    return windows


def _hash_text(text: str) -> str:
    normalized = normalize_chunk_text(text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def chunk_markdown(
    md: str,
    *,
    max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_WINDOW_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Chunk a markdown document into Chunk dataclasses with stable hashes."""
    body = strip_frontmatter(md)
    sections = split_on_headings(body)
    chunks: list[Chunk] = []
    idx = 0
    for heading_path, section_text in sections:
        if not section_text.strip():
            continue
        if estimate_tokens(section_text) > max_tokens:
            windows = sliding_window(
                section_text, max_tokens=max_tokens, overlap_tokens=overlap_tokens
            )
        else:
            windows = [section_text]
        for w in windows:
            chunks.append(
                Chunk(
                    chunk_idx=idx,
                    heading_path=heading_path,
                    text=w,
                    content_hash=_hash_text(w),
                )
            )
            idx += 1
    return chunks


def chunk_file(
    path: Path,
    *,
    max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_WINDOW_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Read file, chunk_markdown its contents. Empty list if file missing."""
    p = Path(path)
    if not p.is_file():
        return []
    md = p.read_text(encoding="utf-8")
    return chunk_markdown(md, max_tokens=max_tokens, overlap_tokens=overlap_tokens)


# ---------------------------------------------------------------------------
# Stub embedder interface — Ship 3 wave 2 replaces with sqlite-vec + real model
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class EmbeddingResult:
    """One chunk's embedding output."""

    chunk_idx: int
    vector: list[float]
    dim: int
    model: str
    error: str = ""


class EmbedderStub:
    """Deterministic synthetic embedder for tests.

    Derives a 32-dim float vector from sha256(text). Wave 2 replaces this with
    sqlite-vec + voyage-3-lite / all-MiniLM-L6-v2.
    """

    name = "stub"
    dim = 32

    def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        results: list[EmbeddingResult] = []
        for chunk in chunks:
            digest = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            # 32 dims × 4 hex chars/dim = 128 hex chars. sha256 hex is 64 chars,
            # so we hash twice and concat for full 128 chars of determinism.
            digest2 = hashlib.sha256(digest.encode("utf-8")).hexdigest()
            hex_pool = (digest + digest2)[: self.dim * 4]
            vector = [
                int(hex_pool[i : i + 4], 16) / 65535.0
                for i in range(0, self.dim * 4, 4)
            ]
            results.append(
                EmbeddingResult(
                    chunk_idx=chunk.chunk_idx,
                    vector=vector,
                    dim=self.dim,
                    model=self.name,
                )
            )
        return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chunk a markdown file (skeleton; wave 2 wires embedder)"
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_CHUNK_TOKENS)
    parser.add_argument(
        "--overlap-tokens", type=int, default=DEFAULT_WINDOW_OVERLAP_TOKENS
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Run the stub embedder + emit vectors",
    )
    args = parser.parse_args(argv)

    chunks = chunk_file(
        args.path,
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap_tokens,
    )

    if args.embed:
        embedder = EmbedderStub()
        results = embedder.embed(chunks)
        if args.json:
            payload = {
                "chunks": [c.as_dict() for c in chunks],
                "embeddings": [dataclasses.asdict(r) for r in results],
            }
            print(json.dumps(payload, ensure_ascii=False))
        else:
            for c, r in zip(chunks, results):
                print(
                    f"#{c.chunk_idx}  {c.heading_path}  "
                    f"hash={c.content_hash[:20]}  dim={r.dim}"
                )
    else:
        if args.json:
            print(json.dumps([c.as_dict() for c in chunks], ensure_ascii=False))
        else:
            for c in chunks:
                print(
                    f"#{c.chunk_idx}  '{c.heading_path}'  "
                    f"({len(c.text)} chars, hash={c.content_hash[:20]})"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
