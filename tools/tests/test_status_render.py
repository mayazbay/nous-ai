"""Unit tests for tools/status_render.py."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


status_render = _load_module("status_render_under_test", TOOLS_DIR / "status_render.py")
queue_mod = status_render._queue_mod
lane_lock = status_render._lane_lock_mod

KZT = dt.timezone(dt.timedelta(hours=5))


def _wiki(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "pages" / "systems").mkdir(parents=True)
    (root / "logs").mkdir()
    return root


def test_render_missing_state_uses_placeholders(tmp_path: Path) -> None:
    wiki = _wiki(tmp_path)
    rendered = status_render.render(
        wiki=wiki,
        now=dt.datetime(2026, 5, 20, 11, 18, tzinfo=KZT),
    )

    assert "# STATUS" in rendered
    assert "| claude | 0 | (idle) |" in rendered
    assert "| claude | (empty) |" in rendered
    assert "- manifest_sha256: missing" in rendered
    assert "No failover event recorded yet." in rendered
    assert not (wiki / "STATUS.md").exists()


def test_render_shows_lane_locks_and_claimed_queue_task(tmp_path: Path) -> None:
    wiki = _wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 11, 18, tzinfo=KZT)
    task_id = queue_mod.add(
        title="Implement status renderer",
        lane="claude",
        scope_paths=["tools/status_render.py"],
        wiki=wiki,
        now=now,
    )
    assert queue_mod.claim(
        id=task_id,
        session_id="s-test-123",
        wiki=wiki,
        now=now + dt.timedelta(seconds=5),
    )
    token = lane_lock.acquire(
        "claude",
        ["tools/status_render.py"],
        session_id="s-test-123",
        wiki=wiki,
        now=now,
    )
    assert token is not None

    rendered = status_render.render(
        wiki=wiki,
        now=now + dt.timedelta(seconds=22),
    )

    assert "| claude | 1 | 22s ago | tools/status_render.py |" in rendered
    assert f"| claude | {task_id} — Implement status renderer | claimed by s-test-123 | tools/status_render.py |" in rendered


def test_render_reads_parity_file(tmp_path: Path) -> None:
    wiki = _wiki(tmp_path)
    parity = {
        "manifest_sha256": "abcdef1234567890",
        "algo": "sha256",
        "host": "mac",
        "ts": "2026-05-20T11:18:00+05:00",
    }
    (wiki / "pages" / "systems" / "parity-latest.json").write_text(
        json.dumps(parity),
        encoding="utf-8",
    )

    rendered = status_render.render(wiki=wiki)

    assert "- manifest_sha256: `abcdef123456...`" in rendered
    assert "- algo: sha256" in rendered
    assert "- host: mac" in rendered
    assert "- last computed: 2026-05-20T11:18:00+05:00" in rendered


def test_render_and_write_creates_status_atomically(tmp_path: Path) -> None:
    wiki = _wiki(tmp_path)

    path = status_render.render_and_write(wiki=wiki)

    assert path == wiki / "STATUS.md"
    assert path.exists()
    assert (wiki / "STATUS.md").read_text(encoding="utf-8").startswith("---\n")
    assert not (wiki / ".STATUS.md.tmp").exists()


def test_cli_stdout_prints_markdown(tmp_path: Path) -> None:
    wiki = _wiki(tmp_path)
    env = os.environ.copy()
    env["NOUS_WIKI"] = str(wiki)

    proc = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "status_render.py"), "--stdout"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert proc.returncode == 0
    assert "# STATUS" in proc.stdout
    assert "## Active lanes" in proc.stdout
    assert not (wiki / "STATUS.md").exists()
