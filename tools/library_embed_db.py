"""sqlite-vec backed vector store for Ship 3 library graph.

Install:  pip install sqlite-vec
The wrapper module finds the loadable extension via sqlite_vec.loadable_path().

Schema:
  chunks(canonical_uuid TEXT, chunk_idx INTEGER, heading_path TEXT, text TEXT,
         content_hash TEXT, embed_model TEXT, embed_dim INTEGER,
         PRIMARY KEY (canonical_uuid, chunk_idx))
  vec_chunks_<dim>(rowid INTEGER PRIMARY KEY, embedding FLOAT[<dim>])

One vec_chunks_<dim> table per embedding dim, so multiple models can coexist.
"""
from __future__ import annotations

import dataclasses
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

GBRAIN_REL = Path(".gbrain")
DB_REL = GBRAIN_REL / "index.db"
MANIFEST_REL = GBRAIN_REL / "manifest.json"


def _load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Try to load sqlite-vec extension. Returns True if loaded, False otherwise."""
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except ImportError:
        return False
    except sqlite3.OperationalError:
        return False
    except AttributeError:
        # Some Python builds (e.g. system Python on macOS) compile sqlite3
        # without load-extension support; enable_load_extension is missing.
        return False


def init_db(wiki: Path, *, dim: int) -> Path:
    """Create or open .gbrain/index.db; create schemas if missing. Returns DB path."""
    db_path = wiki / DB_REL
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    has_vec = _load_sqlite_vec(conn)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                canonical_uuid TEXT NOT NULL,
                chunk_idx INTEGER NOT NULL,
                heading_path TEXT,
                text TEXT,
                content_hash TEXT,
                embed_model TEXT,
                embed_dim INTEGER,
                PRIMARY KEY (canonical_uuid, chunk_idx)
            )
        """)
        if has_vec:
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks_{dim} USING vec0(
                    embedding FLOAT[{dim}]
                )
            """)
        conn.commit()
    finally:
        conn.close()
    _write_manifest(wiki, dim=dim, has_vec=has_vec)
    return db_path


def _write_manifest(wiki: Path, *, dim: int, has_vec: bool) -> None:
    """Atomic write of .gbrain/manifest.json."""
    manifest = {
        "version": 1,
        "dim": dim,
        "sqlite_vec_loaded": has_vec,
        "schema": "chunks + vec_chunks_<dim>",
    }
    target = wiki / MANIFEST_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(tmp, target)


@dataclasses.dataclass(frozen=True)
class ChunkInsert:
    canonical_uuid: str
    chunk_idx: int
    heading_path: str
    text: str
    content_hash: str
    vector: list[float]
    embed_model: str
    embed_dim: int


def insert_chunks(wiki: Path, batch: list[ChunkInsert]) -> int:
    """INSERT OR REPLACE batch into chunks + vec_chunks_<dim>. Returns count inserted."""
    if not batch:
        return 0
    dim = batch[0].embed_dim
    db_path = wiki / DB_REL
    conn = sqlite3.connect(db_path)
    has_vec = _load_sqlite_vec(conn)
    try:
        count = 0
        for c in batch:
            conn.execute("""
                INSERT OR REPLACE INTO chunks
                (canonical_uuid, chunk_idx, heading_path, text, content_hash, embed_model, embed_dim)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (c.canonical_uuid, c.chunk_idx, c.heading_path, c.text,
                  c.content_hash, c.embed_model, c.embed_dim))
            if has_vec and c.vector and len(c.vector) == dim:
                rowid = conn.execute("""
                    SELECT rowid FROM chunks WHERE canonical_uuid=? AND chunk_idx=?
                """, (c.canonical_uuid, c.chunk_idx)).fetchone()[0]
                vector_blob = _floats_to_blob(c.vector)
                conn.execute(f"""
                    INSERT OR REPLACE INTO vec_chunks_{dim} (rowid, embedding)
                    VALUES (?, ?)
                """, (rowid, vector_blob))
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def _floats_to_blob(floats: list[float]) -> bytes:
    """Pack floats as little-endian float32 blob (sqlite-vec expects this)."""
    import struct
    return struct.pack(f"<{len(floats)}f", *floats)


def search_vec(
    wiki: Path,
    *,
    query_vector: list[float],
    dim: int,
    k: int = 10,
) -> list[dict[str, Any]]:
    """Top-k nearest chunks by cosine. Returns list of {canonical_uuid, chunk_idx, distance, ...}.

    If sqlite-vec is not loaded, returns []. Falls back gracefully so search router
    can still query Obsidian + OpenBrain.
    """
    db_path = wiki / DB_REL
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    has_vec = _load_sqlite_vec(conn)
    if not has_vec:
        conn.close()
        return []
    try:
        query_blob = _floats_to_blob(query_vector)
        rows = conn.execute(f"""
            SELECT
                c.canonical_uuid,
                c.chunk_idx,
                c.heading_path,
                c.text,
                v.distance
            FROM vec_chunks_{dim} v
            JOIN chunks c ON c.rowid = v.rowid
            WHERE v.embedding MATCH ?
            ORDER BY v.distance
            LIMIT ?
        """, (query_blob, k)).fetchall()
        return [
            {
                "canonical_uuid": r[0],
                "chunk_idx": r[1],
                "heading_path": r[2],
                "text": r[3],
                "distance": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()


def count_chunks(wiki: Path) -> int:
    """Return total chunk row count. 0 if DB doesn't exist."""
    db_path = wiki / DB_REL
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    finally:
        conn.close()
