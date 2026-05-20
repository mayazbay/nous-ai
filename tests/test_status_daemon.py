"""Unit tests for tools/status_daemon.py.

Each test uses a fresh ``tmp_path`` as the wiki root. Tests do not require
launchd — they exercise ``run_pass`` directly and run the CLI as a
subprocess for the JSON-emission test.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Make tools/ importable when running pytest from anywhere.
THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import lane_lock  # noqa: E402
import status_daemon  # noqa: E402


KZT = dt.timezone(dt.timedelta(hours=5))


def _wiki(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "pages" / "systems").mkdir(parents=True)
    (root / "logs").mkdir()
    return root


# ---------------------------------------------------------------------------
# run_pass
# ---------------------------------------------------------------------------

def test_run_pass_renders_status_md(tmp_path: Path):
    wiki = _wiki(tmp_path)
    result = status_daemon.run_pass(wiki)

    assert isinstance(result, dict)
    assert "reaped" in result
    assert "status_written" in result
    assert result["reaped"] == []
    assert result["status_written"].endswith("STATUS.md")
    assert (wiki / "STATUS.md").exists()
    body = (wiki / "STATUS.md").read_text(encoding="utf-8")
    assert "# STATUS" in body


def test_run_pass_reaps_stale_lane_locks(tmp_path: Path):
    wiki = _wiki(tmp_path)
    # Acquire a token with TTL=1s.
    token = lane_lock.acquire(
        "opus",
        ["tools/x.py"],
        session_id="test-sess",
        wiki=wiki,
        ttl_sec=1,
    )
    assert token is not None

    # Sleep past the TTL.
    time.sleep(2)

    result = status_daemon.run_pass(wiki)
    assert token in result["reaped"]
    # STATUS.md still rendered after reaping.
    assert (wiki / "STATUS.md").exists()


def test_run_pass_idempotent(tmp_path: Path):
    wiki = _wiki(tmp_path)
    # Stale token to reap on the first pass.
    token = lane_lock.acquire(
        "opus",
        ["tools/x.py"],
        session_id="test-sess",
        wiki=wiki,
        ttl_sec=1,
    )
    assert token is not None
    time.sleep(2)

    first = status_daemon.run_pass(wiki)
    assert token in first["reaped"]

    second = status_daemon.run_pass(wiki)
    # First pass already cleaned up — second has nothing to reap.
    assert second["reaped"] == []
    assert (wiki / "STATUS.md").exists()


def test_main_single_pass_emits_json(tmp_path: Path):
    wiki = _wiki(tmp_path)
    script = TOOLS_DIR / "status_daemon.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--wiki", str(wiki)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    out = proc.stdout.strip()
    assert out, f"empty stdout; stderr={proc.stderr!r}"
    # Single line JSON.
    payload = json.loads(out.splitlines()[-1])
    assert "reaped" in payload
    assert "status_written" in payload
    assert payload["status_written"].endswith("STATUS.md")
    assert (wiki / "STATUS.md").exists()
