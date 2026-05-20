from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import failover_schema as schema
from failover_schema import (
    BrokenRow,
    FinishedRow,
    StartedRow,
    parse_row,
    quarantine_broken,
)


def _started_payload() -> dict:
    return {
        "event_id": "tg_12345_codex_a1b2c3d4e5",
        "phase": "started",
        "status": "running",
        "ts": "2026-05-20T11:24:03+05:00",
        "command": "/codex",
        "msg_id": 12345,
        "chat_id": 110793056,
        "query": "Audit the failover ledger schema",
        "model": "gpt-5.5",
        "via": "codex-cli",
        "continuity_packet": "pages/systems/AGENT-CONTINUITY-PACKET.md",
        "latest_handoff": "pages/progress/HANDOFF-AUTO-2026-05-20-09-00.md",
        "git_head": "abc1234",
    }


def _finished_payload() -> dict:
    return {
        "event_id": "tg_12345_codex_a1b2c3d4e5",
        "phase": "finished",
        "status": "ok",
        "ts": "2026-05-20T11:25:14+05:00",
        "response_head": "Schema audit complete; 3 fields validated.",
        "receipt": "wrote pages/systems/audit.md",
        "git_head": "def5678",
    }


def test_parse_started_row_happy_path() -> None:
    payload = _started_payload()
    row, broken = parse_row(json.dumps(payload))

    assert broken is None
    assert isinstance(row, StartedRow)
    assert row.event_id == "tg_12345_codex_a1b2c3d4e5"
    assert row.phase == "started"
    assert row.status == "running"
    assert row.ts == "2026-05-20T11:24:03+05:00"
    assert row.command == "/codex"
    assert row.msg_id == 12345
    assert row.chat_id == 110793056
    assert row.query == "Audit the failover ledger schema"
    assert row.model == "gpt-5.5"
    assert row.via == "codex-cli"
    assert row.continuity_packet == "pages/systems/AGENT-CONTINUITY-PACKET.md"
    assert row.latest_handoff == "pages/progress/HANDOFF-AUTO-2026-05-20-09-00.md"
    assert row.git_head == "abc1234"


def test_parse_finished_row_happy_path() -> None:
    payload = _finished_payload()
    row, broken = parse_row(json.dumps(payload))

    assert broken is None
    assert isinstance(row, FinishedRow)
    assert row.event_id == "tg_12345_codex_a1b2c3d4e5"
    assert row.phase == "finished"
    assert row.status == "ok"
    assert row.ts == "2026-05-20T11:25:14+05:00"
    assert row.response_head == "Schema audit complete; 3 fields validated."
    assert row.receipt == "wrote pages/systems/audit.md"
    assert row.git_head == "def5678"


def test_parse_empty_line_returns_none_none() -> None:
    assert parse_row("") == (None, None)
    assert parse_row("   \n") == (None, None)
    assert parse_row("\t\n") == (None, None)


def test_parse_invalid_json_returns_broken() -> None:
    row, broken = parse_row("{not valid json")

    assert row is None
    assert isinstance(broken, BrokenRow)
    assert broken.reason.startswith("invalid_json:")
    assert broken.raw_line == "{not valid json"


def test_parse_missing_phase_returns_broken() -> None:
    payload = {"event_id": "tg_1_x_y", "status": "ok", "ts": "2026-05-20T11:00:00+05:00"}
    row, broken = parse_row(json.dumps(payload))

    assert row is None
    assert isinstance(broken, BrokenRow)
    assert broken.reason == "missing_phase"


def test_parse_unknown_phase_returns_broken() -> None:
    payload = _started_payload()
    payload["phase"] = "abandoned"
    row, broken = parse_row(json.dumps(payload))

    assert row is None
    assert isinstance(broken, BrokenRow)
    assert broken.reason == "unknown_phase: abandoned"


def test_parse_started_missing_event_id_returns_broken() -> None:
    payload = _started_payload()
    payload.pop("event_id")
    row, broken = parse_row(json.dumps(payload))

    assert row is None
    assert isinstance(broken, BrokenRow)
    assert broken.reason == "missing_field: event_id"


def test_parse_started_wrong_type_msg_id_returns_broken() -> None:
    payload = _started_payload()
    payload["msg_id"] = "not an int"
    row, broken = parse_row(json.dumps(payload))

    assert row is None
    assert isinstance(broken, BrokenRow)
    assert broken.reason == "wrong_type: msg_id expected int"


def test_parse_finished_missing_status_returns_broken() -> None:
    payload = _finished_payload()
    payload.pop("status")
    row, broken = parse_row(json.dumps(payload))

    assert row is None
    assert isinstance(broken, BrokenRow)
    assert broken.reason == "missing_field: status"


def test_as_dict_round_trips_started() -> None:
    original = StartedRow(
        event_id="tg_99_codex_xyz",
        phase="started",
        status="running",
        ts="2026-05-20T12:00:00+05:00",
        command="/codex",
        msg_id=99,
        chat_id=110793056,
        query="round-trip test",
        model="gpt-5.5",
        via="codex-cli",
        continuity_packet="pages/systems/AGENT-CONTINUITY-PACKET.md",
        latest_handoff="",
        git_head="abc1234",
    )

    serialized = json.dumps(original.as_dict())
    row, broken = parse_row(serialized)

    assert broken is None
    assert row == original


def test_as_dict_round_trips_finished() -> None:
    original = FinishedRow(
        event_id="tg_99_codex_xyz",
        phase="finished",
        status="ok",
        ts="2026-05-20T12:01:00+05:00",
        response_head="done",
        receipt="",
        git_head="abc1234",
    )

    serialized = json.dumps(original.as_dict())
    row, broken = parse_row(serialized)

    assert broken is None
    assert row == original


def test_quarantine_broken_appends_jsonl_with_reason_and_raw(tmp_path: Path) -> None:
    (tmp_path / "pages" / "systems").mkdir(parents=True)

    rows = [
        BrokenRow(raw_line="{bad json", reason="invalid_json: malformed"),
        BrokenRow(raw_line='{"phase": "weird"}', reason="unknown_phase: weird"),
    ]

    count = quarantine_broken(tmp_path, rows)

    assert count == 2
    broken_file = tmp_path / "pages" / "systems" / "model-failover-ledger.broken.jsonl"
    assert broken_file.exists()

    lines = broken_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["reason"] == "invalid_json: malformed"
    assert first["raw"] == "{bad json"
    assert "quarantined_ts" in first

    second = json.loads(lines[1])
    assert second["reason"] == "unknown_phase: weird"
    assert second["raw"] == '{"phase": "weird"}'
    assert "quarantined_ts" in second


def test_quarantine_broken_creates_parent_dir(tmp_path: Path) -> None:
    # tmp_path has no pages/systems subtree — quarantine must create it.
    assert not (tmp_path / "pages").exists()

    rows = [BrokenRow(raw_line="garbage", reason="invalid_json: x")]
    count = quarantine_broken(tmp_path, rows)

    assert count == 1
    broken_file = tmp_path / "pages" / "systems" / "model-failover-ledger.broken.jsonl"
    assert broken_file.exists()
    record = json.loads(broken_file.read_text(encoding="utf-8").strip())
    assert record["reason"] == "invalid_json: x"
    assert record["raw"] == "garbage"


def test_quarantine_broken_concurrent_writes_no_interleave(tmp_path: Path) -> None:
    # Each thread writes a batch with a unique reason prefix so we can attribute lines.
    per_thread = 25
    n_threads = 4

    def make_batch(thread_idx: int) -> list[BrokenRow]:
        return [
            BrokenRow(raw_line=f"raw_t{thread_idx}_i{i}", reason=f"reason_t{thread_idx}_i{i}")
            for i in range(per_thread)
        ]

    barrier = threading.Barrier(n_threads)

    def worker(thread_idx: int) -> None:
        batch = make_batch(thread_idx)
        barrier.wait()
        quarantine_broken(tmp_path, batch)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    broken_file = tmp_path / "pages" / "systems" / "model-failover-ledger.broken.jsonl"
    lines = broken_file.read_text(encoding="utf-8").splitlines()

    assert len(lines) == per_thread * n_threads

    seen: set[str] = set()
    for line in lines:
        record = json.loads(line)
        assert "reason" in record
        assert "raw" in record
        assert "quarantined_ts" in record
        seen.add(record["reason"])

    expected = {
        f"reason_t{t}_i{i}" for t in range(n_threads) for i in range(per_thread)
    }
    assert seen == expected
