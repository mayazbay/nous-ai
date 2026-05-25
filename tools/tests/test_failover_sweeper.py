from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import failover_sweeper as sweeper  # noqa: E402
import model_failover_state as mfs  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path
    (wiki / "pages" / "progress").mkdir(parents=True)
    (wiki / "pages" / "systems").mkdir(parents=True)
    (wiki / "logs").mkdir(parents=True, exist_ok=True)
    (wiki / "pages" / "progress" / "HANDOFF-AUTO-2026-05-20-09-00.md").write_text("# handoff\n")
    return wiki


def _started_row(event_id: str, ts: dt.datetime, **overrides) -> dict:
    row = {
        "event_id": event_id,
        "phase": "started",
        "status": "running",
        "ts": ts.isoformat(),
        "command": "/codex",
        "msg_id": 9000,
        "chat_id": 110793056,
        "query": f"sweeper test {event_id}",
        "model": "gpt-5.5",
        "via": "codex-cli",
        "continuity_packet": "pages/systems/AGENT-CONTINUITY-PACKET.md",
        "latest_handoff": "pages/progress/HANDOFF-AUTO-2026-05-20-09-00.md",
        "git_head": "abc1234",
    }
    row.update(overrides)
    return row


def _finished_row(event_id: str, ts: dt.datetime, **overrides) -> dict:
    row = {
        "event_id": event_id,
        "phase": "finished",
        "status": "ok",
        "ts": ts.isoformat(),
        "response_head": "",
        "receipt": "",
        "git_head": "def5678",
    }
    row.update(overrides)
    return row


def _write_ledger(wiki: Path, rows: list[dict]) -> None:
    ledger = wiki / mfs.LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n",
        encoding="utf-8",
    )


def _read_ledger(wiki: Path) -> list[dict]:
    path = wiki / mfs.LEDGER_REL
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_wal(wiki: Path, rows: list[dict]) -> None:
    path = wiki / mfs.WAL_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n",
        encoding="utf-8",
    )


def _read_wal(wiki: Path) -> list[dict]:
    path = wiki / mfs.WAL_REL
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------------------
# Test 1: orphan materialization writes synthetic abandoned row
# ---------------------------------------------------------------------------


def test_sweep_orphans_materializes_synthetic_abandonment(
    monkeypatch, tmp_path: Path,
) -> None:
    wiki = _make_wiki(tmp_path)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(mfs, "git_head", lambda wiki: "abc1234")
    monkeypatch.setattr(sweeper.mfs, "git_head", lambda wiki: "abc1234")

    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=mfs.ALMATY)
    started_ts = now - dt.timedelta(minutes=20)
    _write_ledger(wiki, [_started_row("tg_orphan_aaaaaaaa", started_ts)])

    result = sweeper.sweep_orphans(wiki, now=now)

    assert result == ["tg_orphan_aaaaaaaa"]

    rows = _read_ledger(wiki)
    assert len(rows) == 2

    finished = [r for r in rows if r.get("phase") == "finished"]
    assert len(finished) == 1
    fin = finished[0]
    assert fin["event_id"] == "tg_orphan_aaaaaaaa"
    assert fin["status"] == "abandoned"
    assert fin["abandonment_reason"] == "orphan_timeout"
    assert fin["ts"] == now.isoformat()


# ---------------------------------------------------------------------------
# Test 2: idempotent — re-running with the orphan already materialized is a no-op
# ---------------------------------------------------------------------------


def test_sweep_orphans_idempotent(monkeypatch, tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(mfs, "git_head", lambda wiki: "abc1234")
    monkeypatch.setattr(sweeper.mfs, "git_head", lambda wiki: "abc1234")

    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=mfs.ALMATY)
    started_ts = now - dt.timedelta(minutes=20)
    _write_ledger(wiki, [_started_row("tg_orphan_bbbbbbbb", started_ts)])

    first = sweeper.sweep_orphans(wiki, now=now)
    assert first == ["tg_orphan_bbbbbbbb"]

    # Advance now by 5s so a fresh sweep wouldn't accidentally see the synthetic
    # finished row as also expired (it isn't expired since it has a finished pair).
    second = sweeper.sweep_orphans(wiki, now=now + dt.timedelta(seconds=5))
    assert second == []

    rows = _read_ledger(wiki)
    assert len(rows) == 2  # started + finished, no duplicates


# ---------------------------------------------------------------------------
# Test 3: paired events are not touched
# ---------------------------------------------------------------------------


def test_sweep_orphans_does_not_touch_paired_events(
    monkeypatch, tmp_path: Path,
) -> None:
    wiki = _make_wiki(tmp_path)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(mfs, "git_head", lambda wiki: "abc1234")
    monkeypatch.setattr(sweeper.mfs, "git_head", lambda wiki: "abc1234")

    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=mfs.ALMATY)
    started_ts = now - dt.timedelta(minutes=20)
    finished_ts = now - dt.timedelta(minutes=18)
    _write_ledger(
        wiki,
        [
            _started_row("tg_paired_cccccccc", started_ts),
            _finished_row("tg_paired_cccccccc", finished_ts, status="ok"),
        ],
    )

    before = (wiki / mfs.LEDGER_REL).read_text(encoding="utf-8")
    result = sweeper.sweep_orphans(wiki, now=now)
    after = (wiki / mfs.LEDGER_REL).read_text(encoding="utf-8")

    assert result == []
    assert before == after


# ---------------------------------------------------------------------------
# Test 4: WAL push retry replays old unpushed mutations
# ---------------------------------------------------------------------------


def test_sweep_wal_push_retries_unpushed_old_mutations(
    monkeypatch, tmp_path: Path,
) -> None:
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=mfs.ALMATY)
    old_ts = now - dt.timedelta(minutes=2)  # > 60s threshold

    _write_wal(
        wiki,
        [
            {
                "mutation_seq": 1,
                "event_id": "tg_event_dddddddd",
                "ts": old_ts.isoformat(),
                "pushed": False,
            },
        ],
    )

    pushes: list[Path] = []

    def fake_push(wiki_arg: Path) -> int:
        pushes.append(Path(wiki_arg))
        return 0

    monkeypatch.setattr(sweeper, "_git_push", fake_push)
    # Pin now_kzt so the appended WAL row carries a deterministic ts.
    monkeypatch.setattr(mfs, "now_kzt", lambda: now)

    result = sweeper.sweep_wal_push(wiki, now=now)

    assert result == [1]
    assert pushes == [wiki]

    wal = _read_wal(wiki)
    # Original false row + new true row = 2 rows
    assert len(wal) == 2
    assert wal[0]["pushed"] is False
    assert wal[1]["pushed"] is True
    assert wal[1]["mutation_seq"] == 1
    assert wal[1]["event_id"] == "tg_event_dddddddd"


# ---------------------------------------------------------------------------
# Test 5: WAL push skips rows younger than 60s
# ---------------------------------------------------------------------------


def test_sweep_wal_push_skips_recent_unpushed(monkeypatch, tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=mfs.ALMATY)
    recent_ts = now - dt.timedelta(seconds=30)  # under 60s threshold

    _write_wal(
        wiki,
        [
            {
                "mutation_seq": 1,
                "event_id": "tg_event_eeeeeeee",
                "ts": recent_ts.isoformat(),
                "pushed": False,
            },
        ],
    )

    pushes: list[Path] = []

    def fake_push(wiki_arg: Path) -> int:
        pushes.append(Path(wiki_arg))
        return 0

    monkeypatch.setattr(sweeper, "_git_push", fake_push)

    before = (wiki / mfs.WAL_REL).read_text(encoding="utf-8")
    result = sweeper.sweep_wal_push(wiki, now=now)
    after = (wiki / mfs.WAL_REL).read_text(encoding="utf-8")

    assert result == []
    assert pushes == []
    assert before == after


# ---------------------------------------------------------------------------
# Test 6: WAL push skips mutations whose LATEST row is already pushed=true
# ---------------------------------------------------------------------------


def test_sweep_wal_push_skips_already_pushed(monkeypatch, tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=mfs.ALMATY)
    old_ts = now - dt.timedelta(minutes=2)
    later_ts = now - dt.timedelta(minutes=1, seconds=30)

    _write_wal(
        wiki,
        [
            {
                "mutation_seq": 1,
                "event_id": "tg_event_ffffffff",
                "ts": old_ts.isoformat(),
                "pushed": False,
            },
            {
                "mutation_seq": 1,
                "event_id": "tg_event_ffffffff",
                "ts": later_ts.isoformat(),
                "pushed": True,
            },
        ],
    )

    pushes: list[Path] = []

    def fake_push(wiki_arg: Path) -> int:
        pushes.append(Path(wiki_arg))
        return 0

    monkeypatch.setattr(sweeper, "_git_push", fake_push)

    before = (wiki / mfs.WAL_REL).read_text(encoding="utf-8")
    result = sweeper.sweep_wal_push(wiki, now=now)
    after = (wiki / mfs.WAL_REL).read_text(encoding="utf-8")

    assert result == []
    assert pushes == []
    assert before == after


# ---------------------------------------------------------------------------
# Test 7: sweep_all runs both branches
# ---------------------------------------------------------------------------


def test_sweep_all_runs_both(monkeypatch, tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(mfs, "git_head", lambda wiki: "abc1234")
    monkeypatch.setattr(sweeper.mfs, "git_head", lambda wiki: "abc1234")

    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=mfs.ALMATY)
    started_ts = now - dt.timedelta(minutes=20)
    _write_ledger(wiki, [_started_row("tg_orphan_gggggggg", started_ts)])

    # Seed WAL with a separate old unpushed mutation_seq.
    old_ts = now - dt.timedelta(minutes=2)
    _write_wal(
        wiki,
        [
            {
                "mutation_seq": 7,
                "event_id": "tg_event_hhhhhhhh",
                "ts": old_ts.isoformat(),
                "pushed": False,
            },
        ],
    )

    monkeypatch.setattr(sweeper, "_git_push", lambda wiki_arg: 0)
    monkeypatch.setattr(mfs, "now_kzt", lambda: now)

    result = sweeper.sweep_all(wiki, now=now)

    assert "orphans" in result
    assert "pushed" in result
    assert "tg_orphan_gggggggg" in result["orphans"]
    assert 7 in result["pushed"]


# ---------------------------------------------------------------------------
# Test 8: CLI emits JSON
# ---------------------------------------------------------------------------


def test_main_cli_emits_json(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    # Empty wiki — both sweeps return empty lists, but JSON contract must hold.
    env = os.environ.copy()
    env["NOUS_FAILOVER_STATE_COMMIT"] = "0"

    sweeper_path = TOOLS / "failover_sweeper.py"
    proc = subprocess.run(
        [sys.executable, str(sweeper_path), "--wiki", str(wiki), "--orphans-only"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    payload = json.loads(proc.stdout.strip())
    assert "orphans" in payload
    assert "pushed" in payload
    assert payload["orphans"] == []
    assert payload["pushed"] == []
