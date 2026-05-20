"""Unit tests for ``tools/library_openbrain_sync.py`` (Ship 3 wave 4).

Each test uses ``tmp_path`` as the wiki root (set via the ``wiki`` kwarg or
``NOUS_WIKI`` env var for the CLI subprocess test). All MCP shell-outs are
monkey-patched — these tests are pure unit tests, no real MCP daemon is
launched. The contract under test is:

* ``sync_up`` queues new/changed files via ``_mcp_capture_thought`` and skips
  unchanged ones by comparing ``content_hash`` against the registry.
* ``sync_down`` materializes NEW OpenBrain thoughts (tagged
  ``nous-vault-inbox``) into ``pages/inbox/openbrain/<date>-<id>.md``.
* MCP failures NEVER raise.
* The CLI emits valid JSON under ``--json --dry-run``.
"""

from __future__ import annotations

import datetime as dt
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

# Load by file path so we never collide with any top-level ``tools`` package.
_MOD_PATH = TOOLS_DIR / "library_openbrain_sync.py"
_spec = importlib.util.spec_from_file_location(
    "tools_library_openbrain_sync", _MOD_PATH
)
assert _spec is not None and _spec.loader is not None
sync_mod = importlib.util.module_from_spec(_spec)
sys.modules["tools_library_openbrain_sync"] = sync_mod
_spec.loader.exec_module(sync_mod)

reg = sync_mod.registry  # the canonical_registry module the sync module imported


KZT = dt.timezone(dt.timedelta(hours=5))


def _write_md(wiki: Path, rel: str, body: str) -> Path:
    p = wiki / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. Empty vault
# ---------------------------------------------------------------------------

def test_sync_up_empty_vault_returns_zero(tmp_path: Path) -> None:
    # No SYNC_DIRS at all → queued=0, no errors, no files.
    result = sync_mod.sync_up(tmp_path)
    assert result["queued"] == 0
    assert result["skipped_unchanged"] == 0
    assert result["errors"] == 0
    assert result["files"] == []


# ---------------------------------------------------------------------------
# 2. New files queue capture_thought
# ---------------------------------------------------------------------------

def test_sync_up_queues_new_files_via_popen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_md(tmp_path, "pages/systems/a.md", "# Alpha\n\nhello world\n")

    calls: list[dict] = []

    def fake_capture(payload, log_path):
        calls.append({"payload": payload, "log_path": Path(log_path)})
        return "queued"

    monkeypatch.setattr(sync_mod, "_mcp_capture_thought", fake_capture)

    result = sync_mod.sync_up(tmp_path)
    assert result["queued"] == 1
    assert result["errors"] == 0
    assert len(calls) == 1
    payload = calls[0]["payload"]
    assert payload["type"] == "nous-vault"
    assert "nous-vault" in payload["tags"]
    assert "systems" in payload["tags"]
    assert any(t.startswith("canonical:") for t in payload["tags"])
    assert payload["source_path"] == "pages/systems/a.md"


# ---------------------------------------------------------------------------
# 3. Unchanged files are skipped
# ---------------------------------------------------------------------------

def test_sync_up_skips_unchanged_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_md(tmp_path, "pages/systems/b.md", "# Beta\n\nstable content\n")

    monkeypatch.setattr(
        sync_mod, "_mcp_capture_thought", lambda payload, log_path: "queued"
    )

    first = sync_mod.sync_up(tmp_path)
    assert first["queued"] == 1
    assert first["skipped_unchanged"] == 0

    # Same content, second pass — should now be a no-op.
    second = sync_mod.sync_up(tmp_path)
    assert second["queued"] == 0
    assert second["skipped_unchanged"] == 1
    assert second["errors"] == 0


# ---------------------------------------------------------------------------
# 4. Dry run never invokes Popen
# ---------------------------------------------------------------------------

def test_sync_up_dry_run_no_popen_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_md(tmp_path, "pages/skills/foo/SKILL.md", "# Foo skill\n")

    calls: list[dict] = []

    def fake_capture(payload, log_path):
        calls.append(payload)
        return "queued"

    monkeypatch.setattr(sync_mod, "_mcp_capture_thought", fake_capture)

    result = sync_mod.sync_up(tmp_path, dry_run=True)
    # dry-run still records "would-queue" but does NOT shell out.
    assert result["queued"] >= 1
    assert calls == []


# ---------------------------------------------------------------------------
# 5. sync_down materializes inbox files
# ---------------------------------------------------------------------------

def test_sync_down_creates_inbox_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_thoughts = [
        {"thought_id": "tid-001", "title": "First", "body": "Body one."},
        {"thought_id": "tid-002", "title": "Second", "body": "Body two."},
    ]
    monkeypatch.setattr(
        sync_mod,
        "_mcp_search_thoughts",
        lambda query, log_path: list(fake_thoughts),
    )

    result = sync_mod.sync_down(tmp_path)
    assert result["materialized"] == 2
    assert result["skipped_existing"] == 0

    inbox = tmp_path / sync_mod.INBOX_REL
    files = sorted(inbox.glob("*.md"))
    assert len(files) == 2
    contents = [f.read_text(encoding="utf-8") for f in files]
    assert all("status: needs-promotion" in c for c in contents)
    assert all("type: openbrain-inbox" in c for c in contents)
    assert any("Body one." in c for c in contents)
    assert any("Body two." in c for c in contents)


# ---------------------------------------------------------------------------
# 6. sync_down deduplicates already-materialized thoughts
# ---------------------------------------------------------------------------

def test_sync_down_skips_existing_inbox_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inbox = tmp_path / sync_mod.INBOX_REL
    inbox.mkdir(parents=True, exist_ok=True)
    # Pre-create a file matching the thought_id pattern *-<tid>.md
    pre = inbox / "2026-05-20-tid-existing.md"
    pre.write_text("---\nstatus: needs-promotion\n---\nalready here\n", encoding="utf-8")

    fake_thoughts = [
        {"thought_id": "tid-existing", "title": "Dup", "body": "should skip"},
        {"thought_id": "tid-new", "title": "New", "body": "should land"},
    ]
    monkeypatch.setattr(
        sync_mod,
        "_mcp_search_thoughts",
        lambda query, log_path: list(fake_thoughts),
    )

    result = sync_mod.sync_down(tmp_path)
    # The pre-existing tid-existing must NOT be re-materialized.
    assert result["materialized"] == 1
    assert result["skipped_existing"] == 1


# ---------------------------------------------------------------------------
# 7. _mcp_capture_thought is fail-soft on Popen errors
# ---------------------------------------------------------------------------

def test_mcp_capture_thought_never_raises_on_popen_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "logs" / "openbrain-sync.log"

    def boom(*args, **kwargs):
        raise OSError("mcp binary not installed")

    monkeypatch.setattr(sync_mod.subprocess, "Popen", boom)

    # Must not raise.
    status = sync_mod._mcp_capture_thought({"type": "x"}, log_path)
    assert status == "failed"
    # An error line must have landed in the log.
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "capture_thought Popen failed" in text


# ---------------------------------------------------------------------------
# 8. _mcp_search_thoughts returns [] on timeout
# ---------------------------------------------------------------------------

def test_mcp_search_thoughts_returns_empty_on_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "logs" / "openbrain-sync.log"

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="mcp", timeout=10)

    monkeypatch.setattr(sync_mod.subprocess, "run", fake_run)

    out = sync_mod._mcp_search_thoughts("tag:nous-vault-inbox", log_path)
    assert out == []
    assert log_path.exists()
    assert "search_thoughts timed out" in log_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 9. detect_conflicts returns a list (and writes a report when non-empty)
# ---------------------------------------------------------------------------

def test_detect_conflicts_returns_list(tmp_path: Path) -> None:
    # Seed a file + register it.
    _write_md(tmp_path, "pages/systems/c.md", "# Gamma\n\noriginal body\n")
    uid = reg.add("pages/systems/c.md", wiki=tmp_path)
    # Stamp the registry as if OpenBrain has stored a thought_id for it.
    assert reg.update_field(
        uid, "openbrain_thought_ids", ["tid-c-1"], wiki=tmp_path
    )

    # Same content → no drift → empty list.
    flat = sync_mod.detect_conflicts(tmp_path)
    assert isinstance(flat, list)
    assert flat == []

    # Now drift the file. The registry still records the old hash, so
    # detect_conflicts should surface this entry.
    _write_md(tmp_path, "pages/systems/c.md", "# Gamma v2\n\nbody changed\n")
    drifted = sync_mod.detect_conflicts(tmp_path)
    assert isinstance(drifted, list)
    assert len(drifted) == 1
    assert drifted[0]["obsidian_path"] == "pages/systems/c.md"
    assert drifted[0]["openbrain_thought_ids"] == ["tid-c-1"]
    # A conflicts report must have been written.
    today = dt.datetime.now(KZT).strftime("%Y-%m-%d")
    report = tmp_path / sync_mod.CONFLICT_DIR_REL / f"openbrain-conflicts-{today}.md"
    assert report.exists()


# ---------------------------------------------------------------------------
# 10. CLI emits JSON under --dry-run --json
# ---------------------------------------------------------------------------

def test_main_cli_json_output(tmp_path: Path) -> None:
    # Empty wiki — should still parse cleanly.
    env = dict(os.environ)
    env["NOUS_WIKI"] = str(tmp_path)
    # Avoid accidentally inheriting PYTHONPATH pointing at vendored deps.
    proc = subprocess.run(
        [
            sys.executable,
            str(_MOD_PATH),
            "--dry-run",
            "--json",
            "--wiki",
            str(tmp_path),
            "--direction",
            "both",
        ],
        env=env,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    payload = json.loads(proc.stdout.decode("utf-8"))
    assert set(payload.keys()) == {"up", "down", "conflicts"}
    assert isinstance(payload["up"], dict)
    assert isinstance(payload["down"], dict)
    assert isinstance(payload["conflicts"], list)
