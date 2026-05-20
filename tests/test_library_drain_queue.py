"""Tests for tools/library_drain_queue.py (Ship 3 wave 7)."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

# Make tools/ importable when running pytest from any cwd.
TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import library_canonical_registry as registry  # noqa: E402
import library_drain_queue as drain  # noqa: E402
import library_embed_voyage  # noqa: E402


SCRIPT = TOOLS_DIR / "library_drain_queue.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wiki(tmp_path, monkeypatch):
    """tmp_path-as-wiki with NOUS_WIKI pointing at it + voyage key cleared."""
    (tmp_path / "pages" / "systems").mkdir(parents=True)
    (tmp_path / "logs").mkdir(parents=True)
    (tmp_path / ".gbrain").mkdir(parents=True)
    monkeypatch.setenv("NOUS_WIKI", str(tmp_path))
    # Default: no Voyage key. Tests that need one set it explicitly.
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    # Force the embed-voyage key reader to ignore the real ~/.nous/secrets file
    # by redirecting it inside the test wiki.
    bogus_key_path = tmp_path / "voyage.env"  # does not exist
    monkeypatch.setattr(library_embed_voyage, "VOYAGE_KEY_PATH", bogus_key_path)
    return tmp_path


def _write_queue(wiki, entries):
    """Helper: write a queue.jsonl file with the given entries."""
    queue_path = wiki / drain.QUEUE_REL
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_path, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


def _write_page(wiki, rel_path, body):
    """Helper: write a page file under wiki root. Returns absolute path."""
    abs_path = wiki / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(body, encoding="utf-8")
    return abs_path


# ---------------------------------------------------------------------------
# 1. test_read_queue_empty_returns_empty
# ---------------------------------------------------------------------------


def test_read_queue_empty_returns_empty(wiki):
    assert drain._read_queue(wiki) == []


# ---------------------------------------------------------------------------
# 2. test_read_queue_dedupes_by_path_latest_wins
# ---------------------------------------------------------------------------


def test_read_queue_dedupes_by_path_latest_wins(wiki):
    _write_queue(wiki, [
        {"path": "pages/systems/A.md", "event": "changed", "ts": "2026-05-20T01:00:00Z"},
        {"path": "pages/systems/A.md", "event": "changed", "ts": "2026-05-20T02:00:00Z"},
        {"path": "pages/systems/B.md", "event": "changed", "ts": "2026-05-20T01:00:00Z"},
    ])
    rows = drain._read_queue(wiki)
    assert len(rows) == 2
    by_path = {r["path"]: r for r in rows}
    assert by_path["pages/systems/A.md"]["ts"] == "2026-05-20T02:00:00Z"
    assert by_path["pages/systems/B.md"]["ts"] == "2026-05-20T01:00:00Z"


# ---------------------------------------------------------------------------
# 3. test_drain_once_no_queue_returns_zero
# ---------------------------------------------------------------------------


def test_drain_once_no_queue_returns_zero(wiki):
    result = drain.drain_once(wiki, prefer_embedder="stub")
    assert result["processed"] == 0
    assert result["skipped_unchanged"] == 0
    assert result["errors"] == 0
    assert result["auth_missing"] == 0


# ---------------------------------------------------------------------------
# 4. test_drain_once_skips_unchanged_files
# ---------------------------------------------------------------------------


def test_drain_once_skips_unchanged_files(wiki):
    rel = "pages/systems/unchanged.md"
    abs_path = _write_page(wiki, rel, "# Unchanged\n\nbody one.\n")
    uid = registry.add(rel, wiki=wiki)
    # registry.add already records the current content_hash on disk; simulate
    # a prior embed by populating embed_dim + gbrain_chunk_ids so the drain
    # treats this entry as "already embedded".
    registry.update_field(uid, "embed_model", "stub", wiki=wiki)
    registry.update_field(uid, "embed_dim", 32, wiki=wiki)
    registry.update_field(uid, "gbrain_chunk_ids", [f"{uid}:0"], wiki=wiki)
    current = registry.get(uuid=uid, wiki=wiki)
    assert current is not None
    expected = registry.file_content_hash(abs_path)
    assert current["content_hash"] == expected
    assert current["embed_dim"] == 32

    _write_queue(wiki, [
        {"path": rel, "event": "changed", "ts": "2026-05-20T03:00:00Z"},
    ])
    result = drain.drain_once(wiki, prefer_embedder="stub")
    assert result["skipped_unchanged"] == 1
    assert result["processed"] == 0
    assert result["errors"] == 0
    assert result["auth_missing"] == 0


# ---------------------------------------------------------------------------
# 5. test_drain_once_processes_changed_file_with_stub_embedder
# ---------------------------------------------------------------------------


def test_drain_once_processes_changed_file_with_stub_embedder(wiki):
    rel = "pages/skills/example.md"
    body = "# Example skill\n\nfirst paragraph.\n\n## Section\n\nmore text.\n"
    abs_path = _write_page(wiki, rel, body)
    _write_queue(wiki, [
        {"path": rel, "event": "changed", "ts": "2026-05-20T04:00:00Z"},
    ])
    result = drain.drain_once(wiki, prefer_embedder="stub")
    assert result["processed"] == 1, result
    assert result["errors"] == 0
    assert result["skipped_unchanged"] == 0
    assert result["auth_missing"] == 0

    # Registry should now have the file's current content_hash.
    entry = registry.get(path=rel, wiki=wiki)
    assert entry is not None
    expected_hash = registry.file_content_hash(abs_path)
    assert entry["content_hash"] == expected_hash
    assert entry["embed_model"] == "stub"
    assert entry["embed_dim"] == 32
    assert isinstance(entry["gbrain_chunk_ids"], list)
    assert len(entry["gbrain_chunk_ids"]) >= 1
    # Chunk-id format: f"{uuid}:{i}".
    assert all(cid.startswith(entry["canonical_uuid"] + ":") for cid in entry["gbrain_chunk_ids"])


# ---------------------------------------------------------------------------
# 6. test_drain_once_records_auth_missing_when_voyage_no_key
# ---------------------------------------------------------------------------


def test_drain_once_records_auth_missing_when_voyage_no_key(wiki, monkeypatch):
    # Clear both env + on-disk key path (wiki fixture does this), then force
    # make_embedder to return a Voyage embedder directly (no LocalMiniLM /
    # stub fallback) so we can exercise the auth_missing path the daemon will
    # actually see in prod when VOYAGE_API_KEY is missing.
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    def fake_make_embedder(*, prefer="voyage"):
        return library_embed_voyage.VoyageEmbedder(api_key="")

    monkeypatch.setattr(drain.library_embed_voyage, "make_embedder", fake_make_embedder)

    rel = "pages/laws/needs-embed.md"
    _write_page(wiki, rel, "# Auth missing path\n\nsome body.\n")
    _write_queue(wiki, [
        {"path": rel, "event": "changed", "ts": "2026-05-20T05:00:00Z"},
    ])
    result = drain.drain_once(wiki, prefer_embedder="voyage")
    assert result["auth_missing"] >= 1, result
    assert result["processed"] == 0

    # Queue must NOT be truncated — retried next pass.
    queue_file = wiki / drain.QUEUE_REL
    assert queue_file.exists()
    raw = queue_file.read_text(encoding="utf-8").strip()
    assert raw != ""
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    assert any(r["path"] == rel for r in rows)


# ---------------------------------------------------------------------------
# 7. test_drain_once_truncates_queue_on_success
# ---------------------------------------------------------------------------


def test_drain_once_truncates_queue_on_success(wiki):
    rel = "pages/concepts/topic.md"
    _write_page(wiki, rel, "# Topic\n\nfresh content.\n")
    _write_queue(wiki, [
        {"path": rel, "event": "changed", "ts": "2026-05-20T06:00:00Z"},
    ])
    result = drain.drain_once(wiki, prefer_embedder="stub")
    assert result["processed"] == 1, result

    queue_file = wiki / drain.QUEUE_REL
    # Truncated → empty file (still exists; just no rows).
    assert queue_file.exists()
    assert queue_file.read_text(encoding="utf-8").strip() == ""


# ---------------------------------------------------------------------------
# 8. test_main_cli_emits_json
# ---------------------------------------------------------------------------


def test_main_cli_emits_json(wiki):
    # No queue → CLI still runs and emits valid JSON.
    env = os.environ.copy()
    env["NOUS_WIKI"] = str(wiki)
    env.pop("VOYAGE_API_KEY", None)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--wiki", str(wiki), "--prefer", "stub", "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip())
    assert "processed" in payload
    assert "skipped_unchanged" in payload
    assert "errors" in payload
    assert "auth_missing" in payload
