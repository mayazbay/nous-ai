"""Voyage AI embedder + local MiniLM fallback for Ship 3 library graph.

Voyage: https://docs.voyageai.com/ — stdlib urllib, no SDK dep.
Local fallback: requires `pip install sentence-transformers` at install time;
                guarded by try/except so module loads without the dep.

Voyage key install:
    mkdir -p ~/.nous/secrets
    echo 'VOYAGE_API_KEY=<paste>' > ~/.nous/secrets/voyage.env
    chmod 600 ~/.nous/secrets/voyage.env

Local fallback install (optional):
    pip install sentence-transformers
"""
from __future__ import annotations

import dataclasses
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

try:
    from library_embed import Chunk, EmbeddingResult
except ImportError:
    from tools.library_embed import Chunk, EmbeddingResult


VOYAGE_ENDPOINT = "https://api.voyageai.com/v1/embeddings"
VOYAGE_DEFAULT_MODEL = "voyage-3-lite"
VOYAGE_DIM = 512
VOYAGE_BATCH_SIZE = int(os.environ.get("VOYAGE_BATCH_SIZE", "8"))
VOYAGE_MAX_BATCH_CHARS = int(os.environ.get("VOYAGE_MAX_BATCH_CHARS", "6000"))
VOYAGE_MIN_REQUEST_INTERVAL_SEC = float(
    os.environ.get("VOYAGE_MIN_REQUEST_INTERVAL_SEC", "21")
)
VOYAGE_TIMEOUT_SEC = 30
VOYAGE_KEY_PATH = Path.home() / ".nous" / "secrets" / "voyage.env"


def _read_voyage_key() -> str:
    """Read VOYAGE_API_KEY env var, else parse ~/.nous/secrets/voyage.env file.

    Returns empty string if neither source available (caller decides what to do).
    """
    env = os.environ.get("VOYAGE_API_KEY", "").strip()
    if env:
        return env
    if VOYAGE_KEY_PATH.exists():
        try:
            for line in VOYAGE_KEY_PATH.read_text().splitlines():
                if line.startswith("VOYAGE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    return ""


def _ssl_context() -> ssl.SSLContext | None:
    """Return a certifi-backed TLS context when certifi is installed.

    macOS framework Python can miss system CA roots under launchd. Certifi is
    already present in the project venv/Homebrew Python, so prefer it when
    available and fall back to urllib's default behavior otherwise.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


class VoyageEmbedder:
    """Voyage AI embedder. Batches up to 128 chunks per request.

    Constructor takes the API key explicitly (or reads from env / ~/.nous/secrets/voyage.env).
    """

    name = "voyage-3-lite"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = VOYAGE_DEFAULT_MODEL,
        timeout_sec: int = VOYAGE_TIMEOUT_SEC,
    ):
        self.api_key = api_key if api_key is not None else _read_voyage_key()
        self.model = model
        self.timeout_sec = timeout_sec
        self.dim = VOYAGE_DIM
        self._last_request_monotonic: float | None = None

    def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        """Embed all chunks. Returns parallel list of EmbeddingResult.

        If api_key is empty: returns EmbeddingResult(error='auth_missing') for each.
        On HTTP error: per-chunk EmbeddingResult(error='http_<code>') for that batch.
        On network timeout: error='timeout'.
        On any other exception: error='error: <detail>'.

        Batches of up to 128 chunks per HTTP request. Sleeps 100ms between batches
        to stay under default rate limits.
        """
        results: list[EmbeddingResult] = []
        if not chunks:
            return results
        if not self.api_key:
            return [
                EmbeddingResult(chunk_idx=c.chunk_idx, vector=[], dim=0, model=self.name, error="auth_missing")
                for c in chunks
            ]
        for batch in _chunk_batches(chunks):
            self._pace_request()
            batch_results = self._embed_batch(batch)
            results.extend(batch_results)
        return results

    def _pace_request(self) -> None:
        """Throttle Voyage requests for free-tier 3 RPM / 10K TPM accounts.

        The interval is configurable so paid accounts can raise throughput via
        environment without code changes.
        """
        if VOYAGE_MIN_REQUEST_INTERVAL_SEC <= 0:
            return
        now = time.monotonic()
        if self._last_request_monotonic is not None:
            elapsed = now - self._last_request_monotonic
            remaining = VOYAGE_MIN_REQUEST_INTERVAL_SEC - elapsed
            if remaining > 0:
                time.sleep(remaining)
                now = time.monotonic()
        self._last_request_monotonic = now

    def _embed_batch(self, batch: list[Chunk]) -> list[EmbeddingResult]:
        payload = json.dumps({
            "input": [c.text for c in batch],
            "model": self.model,
            "input_type": "document",
        }).encode()
        req = urllib.request.Request(
            VOYAGE_ENDPOINT,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            ctx = _ssl_context()
            kwargs = {"timeout": self.timeout_sec}
            if ctx is not None:
                kwargs["context"] = ctx
            with urllib.request.urlopen(req, **kwargs) as resp:
                body = json.loads(resp.read())
                data = body.get("data", [])
                if len(data) != len(batch):
                    return [
                        EmbeddingResult(chunk_idx=c.chunk_idx, vector=[], dim=0, model=self.name,
                                        error=f"length_mismatch: got {len(data)} of {len(batch)}")
                        for c in batch
                    ]
                return [
                    EmbeddingResult(
                        chunk_idx=batch[i].chunk_idx,
                        vector=list(data[i].get("embedding", [])),
                        dim=len(data[i].get("embedding", [])),
                        model=self.name,
                        error="",
                    )
                    for i in range(len(batch))
                ]
        except urllib.error.HTTPError as e:
            return [EmbeddingResult(chunk_idx=c.chunk_idx, vector=[], dim=0, model=self.name,
                                    error=f"http_{e.code}") for c in batch]
        except socket.timeout:
            return [EmbeddingResult(chunk_idx=c.chunk_idx, vector=[], dim=0, model=self.name,
                                    error="timeout") for c in batch]
        except Exception as e:
            return [EmbeddingResult(chunk_idx=c.chunk_idx, vector=[], dim=0, model=self.name,
                                    error=f"error: {e}") for c in batch]


def _chunk_batches(chunks: list[Chunk]) -> list[list[Chunk]]:
    """Split chunks by count and rough character budget."""
    batches: list[list[Chunk]] = []
    current: list[Chunk] = []
    current_chars = 0
    max_count = max(1, VOYAGE_BATCH_SIZE)
    max_chars = max(1, VOYAGE_MAX_BATCH_CHARS)
    for chunk in chunks:
        chunk_chars = len(chunk.text)
        would_exceed_count = len(current) >= max_count
        would_exceed_chars = current and current_chars + chunk_chars > max_chars
        if would_exceed_count or would_exceed_chars:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(chunk)
        current_chars += chunk_chars
    if current:
        batches.append(current)
    return batches


class LocalMiniLMEmbedder:
    """Local all-MiniLM-L6-v2 fallback. Requires sentence-transformers.

    Install: pip install sentence-transformers
    Loads 384-dim CPU model. ~25min for 3,043 vault files on M2 Air.
    """
    name = "all-MiniLM-L6-v2"
    dim = 384

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._available = True
        except ImportError:
            self._model = None
            self._available = False
        except Exception:
            # Model load failure (no network, corrupt cache, etc) → degrade gracefully.
            self._model = None
            self._available = False

    def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        if not self._available:
            return [
                EmbeddingResult(chunk_idx=c.chunk_idx, vector=[], dim=0, model=self.name,
                                error="sentence_transformers_not_installed")
                for c in chunks
            ]
        if not chunks:
            return []
        try:
            vectors = self._model.encode([c.text for c in chunks], convert_to_numpy=False)
            return [
                EmbeddingResult(
                    chunk_idx=chunks[i].chunk_idx,
                    vector=list(vectors[i]),
                    dim=self.dim,
                    model=self.name,
                    error="",
                )
                for i in range(len(chunks))
            ]
        except Exception as e:
            return [
                EmbeddingResult(chunk_idx=c.chunk_idx, vector=[], dim=0, model=self.name, error=f"error: {e}")
                for c in chunks
            ]


def make_embedder(*, prefer: str = "voyage") -> object:
    """Factory: returns VoyageEmbedder if key is present, else LocalMiniLMEmbedder, else EmbedderStub.

    prefer='voyage' or 'local' or 'stub'.
    """
    try:
        from library_embed import EmbedderStub
    except ImportError:
        from tools.library_embed import EmbedderStub

    if prefer == "stub":
        return EmbedderStub()
    if prefer == "voyage":
        if _read_voyage_key():
            return VoyageEmbedder()
        if os.environ.get("NOUS_EMBED_FALLBACK_LOCAL", "1") == "1":
            local = LocalMiniLMEmbedder()
            if local._available:
                return local
        return EmbedderStub()
    if prefer == "local":
        local = LocalMiniLMEmbedder()
        if local._available:
            return local
        return EmbedderStub()
    raise ValueError(f"Unknown prefer: {prefer}")
