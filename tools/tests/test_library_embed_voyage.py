"""Tests for tools/library_embed_voyage.py (Ship 3 wave 2)."""
from __future__ import annotations

import io
import pathlib
import socket
import sys
import urllib.error
from unittest import mock

import pytest

# Make tools/ importable when running pytest from any cwd.
TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import library_embed_voyage as lv  # noqa: E402
from library_embed import Chunk, EmbedderStub, EmbeddingResult  # noqa: E402


# --- helpers ---------------------------------------------------------------


def _chunks(n: int) -> list[Chunk]:
    return [
        Chunk(chunk_idx=i, heading_path="", text=f"text-{i}", content_hash=f"sha256:fake{i}")
        for i in range(n)
    ]


class _FakeResponse:
    """urllib-style context manager wrapping a bytes body."""

    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


def _voyage_response(n: int, dim: int = 512) -> _FakeResponse:
    import json as _json
    embeddings = [{"embedding": [0.001 * i for _ in range(dim)]} for i in range(n)]
    return _FakeResponse(_json.dumps({"data": embeddings}).encode())


# --- _read_voyage_key ------------------------------------------------------


def test_read_voyage_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    assert lv._read_voyage_key() == "test-key"


def test_read_voyage_key_from_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    key_file = tmp_path / "voyage.env"
    key_file.write_text("VOYAGE_API_KEY=file-key\n")
    monkeypatch.setattr(lv, "VOYAGE_KEY_PATH", key_file)
    assert lv._read_voyage_key() == "file-key"


def test_read_voyage_key_strips_quotes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    key_file = tmp_path / "voyage.env"
    key_file.write_text('VOYAGE_API_KEY="abc"\n')
    monkeypatch.setattr(lv, "VOYAGE_KEY_PATH", key_file)
    assert lv._read_voyage_key() == "abc"


def test_read_voyage_key_empty_when_neither(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    monkeypatch.setattr(lv, "VOYAGE_KEY_PATH", tmp_path / "does_not_exist.env")
    assert lv._read_voyage_key() == ""


# --- VoyageEmbedder.embed --------------------------------------------------


def test_voyage_embed_returns_auth_missing_when_no_key() -> None:
    emb = lv.VoyageEmbedder(api_key="")
    results = emb.embed(_chunks(3))
    assert len(results) == 3
    assert all(r.error == "auth_missing" for r in results)
    assert all(r.vector == [] for r in results)


def test_voyage_embed_empty_chunks_returns_empty() -> None:
    emb = lv.VoyageEmbedder(api_key="any-key")
    assert emb.embed([]) == []


def test_voyage_embed_2xx_returns_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    emb = lv.VoyageEmbedder(api_key="real-key")
    monkeypatch.setattr(
        lv.urllib.request, "urlopen", lambda *a, **kw: _voyage_response(2, dim=512)
    )
    results = emb.embed(_chunks(2))
    assert len(results) == 2
    assert all(r.error == "" for r in results)
    assert all(len(r.vector) == 512 for r in results)
    assert all(r.dim == 512 for r in results)
    assert all(r.model == "voyage-3-lite" for r in results)


def test_voyage_embed_uses_certifi_context_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emb = lv.VoyageEmbedder(api_key="real-key")
    seen = {}

    def _fake(*_a, **kw):
        seen.update(kw)
        return _voyage_response(1, dim=512)

    monkeypatch.setattr(lv.urllib.request, "urlopen", _fake)
    results = emb.embed(_chunks(1))
    assert results[0].error == ""
    assert "timeout" in seen
    assert "context" in seen


def test_voyage_embed_http_500_returns_http_500(monkeypatch: pytest.MonkeyPatch) -> None:
    emb = lv.VoyageEmbedder(api_key="real-key")

    def _raise(*_a, **_kw):
        raise urllib.error.HTTPError(
            url=lv.VOYAGE_ENDPOINT, code=500, msg="Internal", hdrs=None, fp=io.BytesIO(b"")
        )

    monkeypatch.setattr(lv.urllib.request, "urlopen", _raise)
    results = emb.embed(_chunks(3))
    assert len(results) == 3
    assert all(r.error == "http_500" for r in results)


def test_voyage_embed_timeout_returns_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    emb = lv.VoyageEmbedder(api_key="real-key")

    def _raise(*_a, **_kw):
        raise socket.timeout()

    monkeypatch.setattr(lv.urllib.request, "urlopen", _raise)
    results = emb.embed(_chunks(2))
    assert len(results) == 2
    assert all(r.error == "timeout" for r in results)


def test_voyage_embed_generic_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    emb = lv.VoyageEmbedder(api_key="real-key")

    def _raise(*_a, **_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(lv.urllib.request, "urlopen", _raise)
    results = emb.embed(_chunks(1))
    assert results[0].error.startswith("error: ")
    assert "boom" in results[0].error


def test_voyage_embed_batches_at_128(monkeypatch: pytest.MonkeyPatch) -> None:
    emb = lv.VoyageEmbedder(api_key="real-key")
    call_count = {"n": 0}

    def _fake(*_a, **_kw):
        call_count["n"] += 1
        # Inspect payload to know batch size.
        req = _a[0]
        import json as _json
        body = _json.loads(req.data)
        return _voyage_response(len(body["input"]), dim=512)

    monkeypatch.setattr(lv.urllib.request, "urlopen", _fake)
    monkeypatch.setattr(lv, "VOYAGE_BATCH_SIZE", 128)
    # Stub sleep to avoid 100ms wait
    monkeypatch.setattr(lv.time, "sleep", lambda _s: None)
    results = emb.embed(_chunks(200))
    assert call_count["n"] == 2
    assert len(results) == 200
    assert all(r.error == "" for r in results)


def test_chunk_batches_respects_character_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lv, "VOYAGE_BATCH_SIZE", 10)
    monkeypatch.setattr(lv, "VOYAGE_MAX_BATCH_CHARS", 5)
    chunks = [
        Chunk(chunk_idx=0, heading_path="", text="aaa", content_hash=""),
        Chunk(chunk_idx=1, heading_path="", text="bb", content_hash=""),
        Chunk(chunk_idx=2, heading_path="", text="cccc", content_hash=""),
    ]
    batches = lv._chunk_batches(chunks)
    assert [[c.chunk_idx for c in batch] for batch in batches] == [[0, 1], [2]]


def test_voyage_embed_length_mismatch_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    emb = lv.VoyageEmbedder(api_key="real-key")
    # Server returns 3 embeddings for 5 inputs.
    monkeypatch.setattr(
        lv.urllib.request, "urlopen", lambda *a, **kw: _voyage_response(3, dim=512)
    )
    results = emb.embed(_chunks(5))
    assert len(results) == 5
    assert all("length_mismatch" in r.error for r in results)


# --- LocalMiniLMEmbedder ---------------------------------------------------


def test_local_minilm_returns_not_installed_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force ImportError for sentence_transformers regardless of whether installed.
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def _fake_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("forced for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _fake_import)
    emb = lv.LocalMiniLMEmbedder()
    assert emb._available is False
    results = emb.embed(_chunks(2))
    assert len(results) == 2
    assert all(r.error == "sentence_transformers_not_installed" for r in results)


# --- make_embedder factory --------------------------------------------------


def test_make_embedder_prefer_stub_returns_stub() -> None:
    e = lv.make_embedder(prefer="stub")
    assert isinstance(e, EmbedderStub)


def test_make_embedder_prefer_voyage_with_no_key_falls_back_to_stub(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    monkeypatch.setattr(lv, "VOYAGE_KEY_PATH", tmp_path / "nope.env")

    # Force LocalMiniLM unavailable too.
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def _fake_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("forced for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _fake_import)
    e = lv.make_embedder(prefer="voyage")
    assert isinstance(e, EmbedderStub)


def test_make_embedder_prefer_voyage_with_key_returns_voyage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOYAGE_API_KEY", "real-key")
    e = lv.make_embedder(prefer="voyage")
    assert isinstance(e, lv.VoyageEmbedder)


def test_make_embedder_unknown_prefer_raises() -> None:
    with pytest.raises(ValueError):
        lv.make_embedder(prefer="bogus")
