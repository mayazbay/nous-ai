"""Tests for tools/library_embed_db.py (Ship 3 wave 2)."""
from __future__ import annotations

import json
import pathlib
import sqlite3
import struct
import sys

import pytest

# Make tools/ importable when running pytest from any cwd.
TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import library_embed_db as ldb  # noqa: E402


# --- init_db ---------------------------------------------------------------


def test_init_db_creates_db_and_manifest(tmp_path: pathlib.Path) -> None:
    db_path = ldb.init_db(tmp_path, dim=1024)
    assert db_path == tmp_path / ".gbrain" / "index.db"
    assert db_path.exists()
    manifest_path = tmp_path / ".gbrain" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["dim"] == 1024
    assert manifest["version"] == 1


def test_init_db_idempotent(tmp_path: pathlib.Path) -> None:
    ldb.init_db(tmp_path, dim=4)
    # Should not error on second call.
    ldb.init_db(tmp_path, dim=4)
    # chunks table exists, count = 0
    assert ldb.count_chunks(tmp_path) == 0


def test_manifest_records_sqlite_vec_loaded_state(tmp_path: pathlib.Path) -> None:
    ldb.init_db(tmp_path, dim=8)
    manifest = json.loads((tmp_path / ".gbrain" / "manifest.json").read_text())
    assert "sqlite_vec_loaded" in manifest
    assert isinstance(manifest["sqlite_vec_loaded"], bool)


def test_db_path_under_gbrain_dir(tmp_path: pathlib.Path) -> None:
    db_path = ldb.init_db(tmp_path, dim=4)
    assert db_path.parent.name == ".gbrain"
    assert db_path.name == "index.db"


# --- insert_chunks ---------------------------------------------------------


def test_insert_chunks_metadata_table(tmp_path: pathlib.Path) -> None:
    ldb.init_db(tmp_path, dim=4)
    batch = [
        ldb.ChunkInsert(
            canonical_uuid="uuid-a", chunk_idx=0, heading_path="H > sub",
            text="hello", content_hash="sha256:abc",
            vector=[0.1, 0.2, 0.3, 0.4], embed_model="stub", embed_dim=4,
        ),
        ldb.ChunkInsert(
            canonical_uuid="uuid-a", chunk_idx=1, heading_path="H > sub2",
            text="world", content_hash="sha256:def",
            vector=[0.5, 0.6, 0.7, 0.8], embed_model="stub", embed_dim=4,
        ),
    ]
    inserted = ldb.insert_chunks(tmp_path, batch)
    assert inserted == 2
    assert ldb.count_chunks(tmp_path) == 2
    # Verify metadata columns
    conn = sqlite3.connect(tmp_path / ".gbrain" / "index.db")
    try:
        row = conn.execute(
            "SELECT canonical_uuid, chunk_idx, heading_path, text, content_hash, embed_model, embed_dim "
            "FROM chunks WHERE canonical_uuid=? AND chunk_idx=?",
            ("uuid-a", 0),
        ).fetchone()
        assert row == ("uuid-a", 0, "H > sub", "hello", "sha256:abc", "stub", 4)
    finally:
        conn.close()


def test_insert_chunks_replaces_on_conflict(tmp_path: pathlib.Path) -> None:
    ldb.init_db(tmp_path, dim=4)
    a = ldb.ChunkInsert(
        canonical_uuid="x", chunk_idx=0, heading_path="", text="a",
        content_hash="sha256:1", vector=[0.0, 0.0, 0.0, 0.0],
        embed_model="stub", embed_dim=4,
    )
    b = ldb.ChunkInsert(
        canonical_uuid="x", chunk_idx=0, heading_path="", text="b",
        content_hash="sha256:2", vector=[1.0, 1.0, 1.0, 1.0],
        embed_model="stub", embed_dim=4,
    )
    ldb.insert_chunks(tmp_path, [a])
    ldb.insert_chunks(tmp_path, [b])
    assert ldb.count_chunks(tmp_path) == 1
    conn = sqlite3.connect(tmp_path / ".gbrain" / "index.db")
    try:
        text = conn.execute(
            "SELECT text FROM chunks WHERE canonical_uuid=? AND chunk_idx=?",
            ("x", 0),
        ).fetchone()[0]
        assert text == "b"
    finally:
        conn.close()


def test_insert_chunks_empty_batch_returns_zero(tmp_path: pathlib.Path) -> None:
    ldb.init_db(tmp_path, dim=4)
    assert ldb.insert_chunks(tmp_path, []) == 0


# --- search_vec ------------------------------------------------------------


def test_search_vec_returns_empty_when_db_missing(tmp_path: pathlib.Path) -> None:
    # No init_db call → no DB file.
    results = ldb.search_vec(tmp_path, query_vector=[0.0] * 4, dim=4, k=10)
    assert results == []


def test_search_vec_returns_empty_when_sqlite_vec_not_loaded(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ldb.init_db(tmp_path, dim=4)
    monkeypatch.setattr(ldb, "_load_sqlite_vec", lambda conn: False)
    results = ldb.search_vec(tmp_path, query_vector=[0.0] * 4, dim=4, k=10)
    assert results == []


# --- count_chunks ----------------------------------------------------------


def test_count_chunks_zero_when_db_missing(tmp_path: pathlib.Path) -> None:
    # Point at a nonexistent wiki.
    assert ldb.count_chunks(tmp_path / "nope_wiki") == 0


def test_count_chunks_zero_after_init(tmp_path: pathlib.Path) -> None:
    ldb.init_db(tmp_path, dim=4)
    assert ldb.count_chunks(tmp_path) == 0


# --- _floats_to_blob -------------------------------------------------------


def test_floats_to_blob_round_trips() -> None:
    floats = [0.1, -0.5, 1.0, 3.14]
    blob = ldb._floats_to_blob(floats)
    assert len(blob) == 4 * 4  # 4 floats × 4 bytes
    unpacked = list(struct.unpack(f"<{len(floats)}f", blob))
    for a, b in zip(floats, unpacked):
        assert abs(a - b) < 1e-6


def test_floats_to_blob_empty() -> None:
    assert ldb._floats_to_blob([]) == b""
