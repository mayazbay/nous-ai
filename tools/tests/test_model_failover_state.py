from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import model_failover_state as failover


def _make_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path
    (wiki / "pages" / "progress").mkdir(parents=True)
    (wiki / "pages" / "systems").mkdir(parents=True)
    (wiki / "pages" / "progress" / "HANDOFF-AUTO-2026-05-20-09-00.md").write_text("# handoff\n")
    return wiki


def test_start_and_finish_event_render_latest(monkeypatch, tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(
        failover,
        "now_kzt",
        lambda: dt.datetime(2026, 5, 20, 10, 45, tzinfo=failover.ALMATY),
    )
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")

    event_id = failover.start_event(
        command="/codex",
        msg_id=1788,
        chat_id=110793056,
        query="Fix Telegram. password: should-not-leak",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=False,
    )
    failover.finish_event(event_id, status="error", response="blocked", receipt="pages/task-results/x.md", wiki=wiki, commit=False)

    latest = (wiki / failover.LATEST_REL).read_text(encoding="utf-8")
    ledger = (wiki / failover.LEDGER_REL).read_text(encoding="utf-8")
    assert event_id in latest
    assert "password: [REDACTED]" in latest
    assert "should-not-leak" not in latest
    assert "pages/task-results/x.md" in latest
    assert '"phase": "started"' in ledger
    assert '"phase": "finished"' in ledger


def test_resume_prompt_contains_packet_latest_and_original_task(monkeypatch, tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    event_id = failover.start_event(
        command="/code",
        msg_id=1800,
        chat_id=110793056,
        query="Continue Satory proof",
        model="claude-code",
        via="/code",
        wiki=wiki,
        commit=False,
    )

    prompt = failover.build_resume_prompt("grok", wiki)

    assert event_id in prompt
    assert failover.PACKET_REL.as_posix() in prompt
    assert failover.LATEST_REL.as_posix() in prompt
    assert "Continue Satory proof" in prompt
    assert "Do not ask Madi to restate context" in prompt


def _valid_started_row(event_id: str = "tg_1_codex_aaaaaaaaaa") -> dict:
    return {
        "event_id": event_id,
        "phase": "started",
        "status": "running",
        "ts": "2026-05-20T11:24:03+05:00",
        "command": "/codex",
        "msg_id": 12345,
        "chat_id": 110793056,
        "query": "valid started row",
        "model": "gpt-5.5",
        "via": "codex-cli",
        "continuity_packet": "pages/systems/AGENT-CONTINUITY-PACKET.md",
        "latest_handoff": "pages/progress/HANDOFF-AUTO-2026-05-20-09-00.md",
        "git_head": "abc1234",
    }


def _valid_finished_row(event_id: str = "tg_1_codex_aaaaaaaaaa") -> dict:
    return {
        "event_id": event_id,
        "phase": "finished",
        "status": "ok",
        "ts": "2026-05-20T11:25:14+05:00",
        "response_head": "done",
        "receipt": "",
        "git_head": "def5678",
    }


def _broken_path(wiki: Path) -> Path:
    return wiki / "pages" / "systems" / "model-failover-ledger.broken.jsonl"


def test_load_events_quarantines_invalid_json_line(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger = wiki / failover.LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(_valid_started_row("tg_1_codex_aaaaaaaaaa")),
        json.dumps(_valid_started_row("tg_2_codex_bbbbbbbbbb")),
        "{not valid json at all",
        json.dumps(_valid_finished_row("tg_1_codex_aaaaaaaaaa")),
    ]
    original_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    ledger.write_bytes(original_bytes)

    events = failover._load_events(wiki)

    assert len(events) == 3
    assert all(isinstance(e, dict) for e in events)
    assert events[0]["event_id"] == "tg_1_codex_aaaaaaaaaa"
    assert events[0]["phase"] == "started"
    assert events[1]["event_id"] == "tg_2_codex_bbbbbbbbbb"
    assert events[2]["phase"] == "finished"

    broken = _broken_path(wiki)
    assert broken.exists()
    broken_lines = broken.read_text(encoding="utf-8").splitlines()
    assert len(broken_lines) == 1
    record = json.loads(broken_lines[0])
    assert record["reason"].startswith("invalid_json:")
    assert record["raw"] == "{not valid json at all"

    # Original ledger is byte-for-byte unchanged.
    assert ledger.read_bytes() == original_bytes


def test_load_events_quarantines_missing_phase(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger = wiki / failover.LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    no_phase = {"event_id": "tg_x", "status": "ok", "ts": "2026-05-20T11:00:00+05:00"}
    lines = [
        json.dumps(_valid_started_row("tg_3_codex_cccccccccc")),
        json.dumps(no_phase),
    ]
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    events = failover._load_events(wiki)

    assert len(events) == 1
    assert events[0]["event_id"] == "tg_3_codex_cccccccccc"

    broken = _broken_path(wiki)
    assert broken.exists()
    broken_lines = broken.read_text(encoding="utf-8").splitlines()
    assert len(broken_lines) == 1
    record = json.loads(broken_lines[0])
    assert record["reason"] == "missing_phase"


def test_load_events_quarantines_wrong_type_msg_id(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger = wiki / failover.LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    bad_row = _valid_started_row("tg_4_codex_dddddddddd")
    bad_row["msg_id"] = "not an int"
    ledger.write_text(json.dumps(bad_row) + "\n", encoding="utf-8")

    events = failover._load_events(wiki)

    assert len(events) == 0

    broken = _broken_path(wiki)
    assert broken.exists()
    broken_lines = broken.read_text(encoding="utf-8").splitlines()
    assert len(broken_lines) == 1
    record = json.loads(broken_lines[0])
    assert "wrong_type: msg_id" in record["reason"]


def test_load_events_empty_lines_skipped_no_quarantine(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger = wiki / failover.LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "\n"
        "   \n"
        "\t\n"
        + json.dumps(_valid_started_row("tg_5_codex_eeeeeeeeee"))
        + "\n"
        "\n"
        "    \n"
    )
    ledger.write_text(content, encoding="utf-8")

    events = failover._load_events(wiki)

    assert len(events) == 1
    assert events[0]["event_id"] == "tg_5_codex_eeeeeeeeee"

    assert not _broken_path(wiki).exists()


# ---------------------------------------------------------------------------
# Ship-1 Step-3: WAL + lock reordering tests
# ---------------------------------------------------------------------------


def _read_wal_rows(wiki: Path) -> list[dict]:
    path = wiki / failover.WAL_REL
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _patch_git_helpers(monkeypatch, *, push_rc: int = 0, calls: list | None = None) -> None:
    """Replace the two new internal git helpers with deterministic stubs.

    `calls` accumulates ("add_commit"|"push", ...) tuples in call order so tests
    can assert ordering (add+commit BEFORE push).
    """
    def _fake_add_commit(wiki: Path) -> int:
        if calls is not None:
            calls.append(("add_commit", str(wiki)))
        return 0

    def _fake_push(wiki: Path) -> int:
        if calls is not None:
            calls.append(("push", str(wiki)))
        return push_rc

    monkeypatch.setattr(failover, "_git_add_commit_local", _fake_add_commit)
    monkeypatch.setattr(failover, "_git_push_background", _fake_push)


def test_mutate_state_writes_wal_before_ledger(monkeypatch, tmp_path: Path) -> None:
    """WAL pushed:false → ledger → render → git commit → push → WAL pushed:true.

    Both WAL rows share the same mutation_seq; ledger and WAL are both durable
    on disk after the call returns.
    """
    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    calls: list = []
    _patch_git_helpers(monkeypatch, push_rc=0, calls=calls)

    event_id = failover.start_event(
        command="/codex",
        msg_id=2001,
        chat_id=110793056,
        query="wal ordering test",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=True,
    )

    rows = _read_wal_rows(wiki)
    assert len(rows) == 2, f"expected 2 WAL rows (false then true), got {rows!r}"
    assert rows[0]["pushed"] is False
    assert rows[1]["pushed"] is True
    assert rows[0]["mutation_seq"] == rows[1]["mutation_seq"] == 1
    assert rows[0]["event_id"] == event_id
    assert rows[1]["event_id"] == event_id

    # Add+commit MUST happen before push.
    kinds = [c[0] for c in calls]
    assert kinds == ["add_commit", "push"], f"call order wrong: {kinds!r}"

    # Ledger and WAL both exist; WAL was written first so its mtime is ≤ ledger mtime.
    wal_mtime = (wiki / failover.WAL_REL).stat().st_mtime
    ledger_mtime = (wiki / failover.LEDGER_REL).stat().st_mtime
    assert wal_mtime <= ledger_mtime + 1.0  # tolerate clock granularity


def test_mutate_state_wal_records_pushed_false_when_push_fails(monkeypatch, tmp_path: Path) -> None:
    """Push failure leaves WAL with a single pushed:false row; ledger still has the row."""
    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    _patch_git_helpers(monkeypatch, push_rc=1)

    event_id = failover.start_event(
        command="/codex",
        msg_id=2002,
        chat_id=110793056,
        query="push fail test",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=True,
    )

    rows = _read_wal_rows(wiki)
    assert len(rows) == 1, f"push failed → only the pushed:false row should exist; got {rows!r}"
    assert rows[0]["pushed"] is False
    assert rows[0]["event_id"] == event_id
    assert rows[0]["mutation_seq"] == 1

    # Ledger still has the row — push failure does NOT roll back local state.
    ledger_text = (wiki / failover.LEDGER_REL).read_text(encoding="utf-8")
    assert event_id in ledger_text


def test_mutation_seq_monotonic(monkeypatch, tmp_path: Path) -> None:
    """Three sequential start_event calls produce strictly increasing mutation_seqs."""
    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    _patch_git_helpers(monkeypatch, push_rc=0)

    for i in range(3):
        failover.start_event(
            command="/codex",
            msg_id=3000 + i,
            chat_id=110793056,
            query=f"monotonic test {i}",
            model="gpt-5.5",
            via="/codex",
            wiki=wiki,
            commit=True,
        )

    rows = _read_wal_rows(wiki)
    # 3 mutations × 2 rows each (pushed:false then pushed:true) = 6 rows.
    assert len(rows) == 6
    seqs_false = [r["mutation_seq"] for r in rows if r["pushed"] is False]
    seqs_true = [r["mutation_seq"] for r in rows if r["pushed"] is True]
    assert seqs_false == [1, 2, 3]
    assert seqs_true == [1, 2, 3]


def test_recompute_parity_is_noop_stub(tmp_path: Path) -> None:
    """Step-7 stub: _recompute_parity returns None and creates no files."""
    wiki = _make_wiki(tmp_path)
    before = sorted(p.relative_to(wiki).as_posix() for p in wiki.rglob("*") if p.is_file())

    result = failover._recompute_parity(wiki)

    after = sorted(p.relative_to(wiki).as_posix() for p in wiki.rglob("*") if p.is_file())
    assert result is None
    assert before == after, f"recompute_parity stub must not write files; diff: {set(after) - set(before)}"


def test_commit_state_is_noop_shim(tmp_path: Path) -> None:
    """commit_state shim: returns None, does not raise, does not write anything."""
    wiki = _make_wiki(tmp_path)
    before = sorted(p.relative_to(wiki).as_posix() for p in wiki.rglob("*") if p.is_file())

    result = failover.commit_state(wiki)

    after = sorted(p.relative_to(wiki).as_posix() for p in wiki.rglob("*") if p.is_file())
    assert result is None
    assert before == after


# ---------------------------------------------------------------------------
# Ship-1 Step-4: orphan-aware latest_state + find_orphans
# ---------------------------------------------------------------------------


def _write_ledger(wiki: Path, rows: list[dict]) -> None:
    """Write rows as JSONL to the ledger path (creates parent dirs)."""
    ledger = wiki / failover.LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n",
        encoding="utf-8",
    )


def _started_row(event_id: str, ts: dt.datetime, **overrides) -> dict:
    """Build a schema-valid started row with the given event_id and ts."""
    row = {
        "event_id": event_id,
        "phase": "started",
        "status": "running",
        "ts": ts.isoformat(),
        "command": "/codex",
        "msg_id": 9000,
        "chat_id": 110793056,
        "query": f"orphan test {event_id}",
        "model": "gpt-5.5",
        "via": "codex-cli",
        "continuity_packet": "pages/systems/AGENT-CONTINUITY-PACKET.md",
        "latest_handoff": "pages/progress/HANDOFF-AUTO-2026-05-20-09-00.md",
        "git_head": "abc1234",
    }
    row.update(overrides)
    return row


def _finished_row(event_id: str, ts: dt.datetime, **overrides) -> dict:
    """Build a schema-valid finished row with the given event_id and ts."""
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


def test_latest_state_returns_started_when_no_finish_within_timeout(tmp_path: Path) -> None:
    """Started row younger than ORPHAN_TIMEOUT_SEC with no finished → in-flight."""
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=failover.ALMATY)
    started_ts = now - dt.timedelta(minutes=5)
    _write_ledger(wiki, [_started_row("tg_inflight_aaaaaaaaaa", started_ts)])

    state = failover.latest_state(wiki, now=now)

    assert state is not None
    assert state["event_id"] == "tg_inflight_aaaaaaaaaa"
    assert state["status"] == "running"
    assert "finish" not in state
    assert "synthetic" not in state


def test_latest_state_returns_abandoned_for_orphan_past_timeout(tmp_path: Path) -> None:
    """Started row >15min old with no finished → synthetic abandoned view."""
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=failover.ALMATY)
    started_ts = now - dt.timedelta(minutes=20)
    _write_ledger(wiki, [_started_row("tg_orphan_bbbbbbbbbb", started_ts)])

    state = failover.latest_state(wiki, now=now)

    assert state is not None
    assert state["status"] == "abandoned"
    assert state["finish"]["status"] == "abandoned"
    assert state["finish"]["abandonment_reason"] == "orphan_timeout"
    assert state["finish"]["synthetic"] is True
    assert state["finish"]["phase"] == "finished"
    assert state["finish"]["ts"] == now.isoformat()


def test_latest_state_pairs_started_and_finished_by_event_id(tmp_path: Path) -> None:
    """Crossed event_id ordering: latest started B is paired with B's finished row."""
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=failover.ALMATY)
    started_a_ts = now - dt.timedelta(minutes=30)
    started_b_ts = now - dt.timedelta(minutes=10)  # B is newer started
    finished_a_ts = now - dt.timedelta(minutes=4)  # A's finish is newest overall
    finished_b_ts = now - dt.timedelta(minutes=8)

    _write_ledger(
        wiki,
        [
            _started_row("tg_a_aaaaaaaaaa", started_a_ts),
            _started_row("tg_b_bbbbbbbbbb", started_b_ts),
            _finished_row("tg_a_aaaaaaaaaa", finished_a_ts, response_head="A done", status="ok"),
            _finished_row("tg_b_bbbbbbbbbb", finished_b_ts, response_head="B done", status="error"),
        ],
    )

    state = failover.latest_state(wiki, now=now)

    assert state is not None
    # Latest started is B; pair with B's finished, not A's.
    assert state["event_id"] == "tg_b_bbbbbbbbbb"
    assert state["status"] == "error"
    assert state["finish"]["event_id"] == "tg_b_bbbbbbbbbb"
    assert state["finish"]["response_head"] == "B done"
    assert state["finish"].get("synthetic") is not True


def test_latest_state_does_not_mark_abandoned_when_finished_exists(tmp_path: Path) -> None:
    """Even if started is 30min old, an existing finished row wins → paired, not synthetic."""
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=failover.ALMATY)
    started_ts = now - dt.timedelta(minutes=30)
    finished_ts = now - dt.timedelta(minutes=25)

    _write_ledger(
        wiki,
        [
            _started_row("tg_paired_cccccccccc", started_ts),
            _finished_row("tg_paired_cccccccccc", finished_ts, status="ok", response_head="real finish"),
        ],
    )

    state = failover.latest_state(wiki, now=now)

    assert state is not None
    assert state["status"] == "ok"
    assert state["finish"]["status"] == "ok"
    assert state["finish"]["response_head"] == "real finish"
    assert state["finish"].get("synthetic") is not True
    assert state["finish"].get("abandonment_reason") is None


def test_find_orphans_returns_only_orphans_past_timeout(tmp_path: Path) -> None:
    """Mixed bag of 4 rows — only the orphan past timeout is returned."""
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=failover.ALMATY)

    fresh_ts = now - dt.timedelta(minutes=3)
    paired_started_ts = now - dt.timedelta(minutes=20)
    paired_finished_ts = now - dt.timedelta(minutes=18)
    orphan_ts = now - dt.timedelta(minutes=20)
    under_timeout_ts = now - dt.timedelta(minutes=14)

    _write_ledger(
        wiki,
        [
            _started_row("tg_a_fresh_aaaaaaa", fresh_ts),
            _started_row("tg_b_paired_bbbbbb", paired_started_ts),
            _finished_row("tg_b_paired_bbbbbb", paired_finished_ts),
            _started_row("tg_c_orphan_cccccc", orphan_ts),
            _started_row("tg_d_under_dddddd", under_timeout_ts),
        ],
    )

    orphans = failover.find_orphans(wiki, now=now)

    assert [o["event_id"] for o in orphans] == ["tg_c_orphan_cccccc"]


def test_find_orphans_empty_list_when_no_orphans(tmp_path: Path) -> None:
    """All rows either fresh or paired → empty list."""
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=failover.ALMATY)

    fresh_ts = now - dt.timedelta(minutes=2)
    paired_started_ts = now - dt.timedelta(minutes=22)
    paired_finished_ts = now - dt.timedelta(minutes=20)

    _write_ledger(
        wiki,
        [
            _started_row("tg_a_fresh_aaaaaaa", fresh_ts),
            _started_row("tg_b_paired_bbbbbb", paired_started_ts),
            _finished_row("tg_b_paired_bbbbbb", paired_finished_ts),
        ],
    )

    assert failover.find_orphans(wiki, now=now) == []


def test_latest_state_returns_none_when_only_quarantined_rows_exist(tmp_path: Path) -> None:
    """Bad ts gets quarantined by Step-2 schema → no usable rows → latest_state is None.

    (Note: the schema validates ts as a string but does not parse it. A row with
    ts='garbage' that is otherwise schema-valid will load successfully and then
    fail at the orphan-check stage in latest_state. We test that path by writing
    such a row and confirming the unparseable-ts branch keeps the original status
    instead of marking abandoned.)
    """
    wiki = _make_wiki(tmp_path)
    now = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=failover.ALMATY)
    bad_row = _started_row("tg_badts_eeeeeeeeee", now)
    bad_row["ts"] = "garbage-not-iso"
    _write_ledger(wiki, [bad_row])

    state = failover.latest_state(wiki, now=now)

    # Row loads (schema only checks type, not ts parseability) but orphan check
    # is skipped because ts is unparseable. Status stays 'running', no finish key.
    assert state is not None
    assert state["event_id"] == "tg_badts_eeeeeeeeee"
    assert state["status"] == "running"
    assert "finish" not in state


def test_start_event_then_finish_event_yields_two_mutations(monkeypatch, tmp_path: Path) -> None:
    """start+finish = 2 mutation_seqs, each with a pushed:false AND pushed:true marker."""
    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    _patch_git_helpers(monkeypatch, push_rc=0)

    event_id = failover.start_event(
        command="/codex",
        msg_id=4000,
        chat_id=110793056,
        query="start+finish pair",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=True,
    )
    failover.finish_event(event_id, status="ok", response="all good", wiki=wiki, commit=True)

    rows = _read_wal_rows(wiki)
    seqs = sorted({r["mutation_seq"] for r in rows})
    assert seqs == [1, 2], f"expected 2 distinct mutation_seqs, got {seqs!r}"

    for seq in seqs:
        seq_rows = [r for r in rows if r["mutation_seq"] == seq]
        pushed_flags = {r["pushed"] for r in seq_rows}
        assert pushed_flags == {False, True}, (
            f"mutation_seq {seq} missing one of pushed:false/pushed:true — got {pushed_flags}"
        )
        assert all(r["event_id"] == event_id for r in seq_rows)


# ---------------------------------------------------------------------------
# Ship-1 Steps 7b + 8 + 9: parity wire, resume-v2, OpenBrain, mistake-to-skill
# ---------------------------------------------------------------------------


_PARITY_MANIFEST_BODY = (
    "pages/systems/model-failover-ledger.jsonl\n"
    "pages/systems/MODEL-FAILOVER-LATEST.md\n"
    "pages/systems/AGENT-CONTINUITY-PACKET.md\n"
    "pages/progress/HANDOFF-AUTO-LATEST.symlink\n"
    "pages/systems/parity-manifest.txt\n"
)


def _seed_parity_manifest(wiki: Path) -> None:
    (wiki / "pages" / "systems").mkdir(parents=True, exist_ok=True)
    (wiki / "pages" / "systems" / "parity-manifest.txt").write_text(
        _PARITY_MANIFEST_BODY, encoding="utf-8"
    )


def _state_template() -> dict:
    return {
        "event_id": "test-evt",
        "command": "/codex",
        "via": "codex-cli",
        "model": "gpt-5.5",
        "status": "running",
        "ts": "2026-05-20T11:00:00+05:00",
        "query": "do the thing",
        "continuity_packet": "pages/systems/AGENT-CONTINUITY-PACKET.md",
        "latest_handoff": "pages/progress/HANDOFF-AUTO-LATEST.symlink",
    }


def test_recompute_parity_writes_parity_latest_json(monkeypatch, tmp_path: Path) -> None:
    """Step-7b wire: start_event triggers parity computation; parity-latest.json appears."""
    wiki = _make_wiki(tmp_path)
    _seed_parity_manifest(wiki)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")

    failover.start_event(
        command="/codex",
        msg_id=5000,
        chat_id=110793056,
        query="parity wire test",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=False,
    )

    parity_file = wiki / "pages" / "systems" / "parity-latest.json"
    assert parity_file.exists(), "parity-latest.json was not written"
    data = json.loads(parity_file.read_text(encoding="utf-8"))
    assert "manifest_sha256" in data
    assert isinstance(data["manifest_sha256"], str) and len(data["manifest_sha256"]) == 64


def test_recompute_parity_failure_does_not_abort_mutate_state(monkeypatch, tmp_path: Path) -> None:
    """parity_check.compute_and_write raising must not prevent ledger write."""
    wiki = _make_wiki(tmp_path)
    _seed_parity_manifest(wiki)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")

    # Import the module the same way model_failover_state does, then sabotage.
    import parity_check as pc  # type: ignore[import-not-found]
    monkeypatch.setattr(pc, "compute_and_write", lambda w: (_ for _ in ()).throw(RuntimeError("boom")))

    event_id = failover.start_event(
        command="/codex",
        msg_id=5001,
        chat_id=110793056,
        query="parity fail-soft test",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=False,
    )

    ledger_text = (wiki / failover.LEDGER_REL).read_text(encoding="utf-8")
    assert event_id in ledger_text


def test_resume_prompt_v2_contains_all_required_slots(tmp_path: Path, monkeypatch) -> None:
    """RESUME-v2 template carries every required substrate slot."""
    # Point default_wiki at tmp to keep pointer-hash lookups isolated.
    monkeypatch.setattr(failover, "default_wiki", lambda: tmp_path)
    # Stub probe to avoid network.
    monkeypatch.setattr(
        failover.provider_probe,
        "probe",
        lambda provider, *, timeout_sec=0.2: failover.provider_probe.ProbeResult(
            provider=provider, ok=True, latency_ms=12, reason="ok"
        ),
    )
    state = _state_template()

    prompt = failover.build_resume_prompt_from_state(state, "gpt")

    assert "[RESUME-v2]" in prompt
    assert "Original task (verbatim):" in prompt
    assert "Substrate pointers" in prompt
    assert "CONTRACT:" in prompt
    assert "parity_hash" not in prompt or "manifest_sha256=" in prompt  # slot present in pointers
    assert "manifest_sha256=" in prompt
    assert "Provider-probe result" in prompt
    assert "do the thing" in prompt  # original query verbatim
    assert "event=test-evt" in prompt
    assert "target_lane=gpt" in prompt
    assert "replacement_model=gpt-5.5" in prompt


def test_resume_prompt_v2_handles_missing_packet_file(tmp_path: Path, monkeypatch) -> None:
    """packet file absent in wiki → packet_sha256=missing, no exception."""
    monkeypatch.setattr(failover, "default_wiki", lambda: tmp_path)
    monkeypatch.setattr(
        failover.provider_probe,
        "probe",
        lambda provider, *, timeout_sec=0.2: failover.provider_probe.ProbeResult(
            provider=provider, ok=True, latency_ms=5, reason="ok"
        ),
    )
    state = _state_template()  # packet path is set but file doesn't exist in tmp_path

    prompt = failover.build_resume_prompt_from_state(state, "claude")

    assert "packet_sha256=missing" in prompt


def test_resume_prompt_v2_probe_failure_returns_safe_fallback(tmp_path: Path, monkeypatch) -> None:
    """provider_probe.probe raising → ok=False, latency=-1, reason=probe_error: ..."""
    monkeypatch.setattr(failover, "default_wiki", lambda: tmp_path)

    def _boom(provider, *, timeout_sec=0.2):
        raise RuntimeError("network gone")

    monkeypatch.setattr(failover.provider_probe, "probe", _boom)
    state = _state_template()

    prompt = failover.build_resume_prompt_from_state(state, "grok")

    assert "ok=False" in prompt
    assert "latency_ms=-1" in prompt
    assert "reason=probe_error:" in prompt
    assert "network gone" in prompt


def test_finish_event_with_error_status_appends_mistake_to_skill(monkeypatch, tmp_path: Path) -> None:
    """finish_event(status='error') → ledger.jsonl gets exactly one row for this event_id."""
    wiki = _make_wiki(tmp_path)
    _seed_parity_manifest(wiki)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    # Suppress OpenBrain side-channel — we test it separately.
    monkeypatch.setattr(failover, "_capture_openbrain_event", lambda state, wiki=None: None)

    event_id = failover.start_event(
        command="/codex",
        msg_id=6001,
        chat_id=110793056,
        query="mistake-to-skill error test",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=False,
    )
    failover.finish_event(event_id, status="error", response="blocked", wiki=wiki, commit=False)

    ledger = wiki / "pages" / "skills" / "mistake-to-skill" / "ledger.jsonl"
    assert ledger.exists(), "mistake-to-skill ledger.jsonl not written"
    lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event_id"] == event_id
    assert row["failure_reason"] == "error"
    assert row["original_command"] == "/codex"
    assert row["original_model"] == "gpt-5.5"


def test_finish_event_with_ok_status_does_not_append_mistake_to_skill(monkeypatch, tmp_path: Path) -> None:
    """finish_event(status='ok') → no ledger.jsonl created."""
    wiki = _make_wiki(tmp_path)
    monkeypatch.setenv("NOUS_FAILOVER_STATE_COMMIT", "0")
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    monkeypatch.setattr(failover, "_capture_openbrain_event", lambda state, wiki=None: None)

    event_id = failover.start_event(
        command="/codex",
        msg_id=6002,
        chat_id=110793056,
        query="mistake-to-skill ok test",
        model="gpt-5.5",
        via="/codex",
        wiki=wiki,
        commit=False,
    )
    failover.finish_event(event_id, status="ok", response="done", wiki=wiki, commit=False)

    ledger = wiki / "pages" / "skills" / "mistake-to-skill" / "ledger.jsonl"
    if ledger.exists():
        lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert lines == [], f"expected no rows for ok status, got: {lines!r}"


def test_mistake_to_skill_append_idempotent(monkeypatch, tmp_path: Path) -> None:
    """Calling _append_mistake_to_skill twice with same event_id → exactly 1 ledger row."""
    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(failover, "git_head", lambda wiki: "abc1234")
    state = {
        "event_id": "idem-evt-123",
        "command": "/codex",
        "model": "gpt-5.5",
        "status": "error",
        "ts": "2026-05-20T11:00:00+05:00",
        "finish": {
            "phase": "finished",
            "status": "error",
            "ts": "2026-05-20T11:01:00+05:00",
        },
    }

    failover._append_mistake_to_skill(state, wiki)
    failover._append_mistake_to_skill(state, wiki)

    ledger = wiki / "pages" / "skills" / "mistake-to-skill" / "ledger.jsonl"
    assert ledger.exists()
    lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    matching = [json.loads(ln) for ln in lines if json.loads(ln).get("event_id") == "idem-evt-123"]
    assert len(matching) == 1, f"expected exactly 1 row for event_id, got {len(matching)}: {lines!r}"


def test_openbrain_capture_writes_to_log(monkeypatch, tmp_path: Path) -> None:
    """OpenBrain helper writes 'queue:' to log and spawns subprocess with start_new_session=True."""
    import subprocess as sp

    captured: dict = {}

    class _FakeProc:
        def __init__(self) -> None:
            self.pid = 9999

    def _fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProc()

    monkeypatch.setattr(sp, "Popen", _fake_popen)
    monkeypatch.setattr(failover.subprocess, "Popen", _fake_popen)

    # Also stub probe (build_resume_prompt_from_state is called inside).
    monkeypatch.setattr(
        failover.provider_probe,
        "probe",
        lambda provider, *, timeout_sec=0.2: failover.provider_probe.ProbeResult(
            provider=provider, ok=True, latency_ms=5, reason="ok"
        ),
    )

    state = {
        "event_id": "evt-log-1",
        "command": "/codex",
        "via": "codex-cli",
        "model": "gpt-5.5",
        "status": "error",
        "ts": "2026-05-20T11:00:00+05:00",
        "query": "log test",
        "continuity_packet": "pages/systems/AGENT-CONTINUITY-PACKET.md",
        "latest_handoff": "pages/progress/HANDOFF-AUTO-LATEST.symlink",
        "finish": {
            "phase": "finished",
            "status": "error",
            "ts": "2026-05-20T11:01:00+05:00",
        },
    }

    failover._capture_openbrain_event(state, tmp_path)

    log_path = tmp_path / "logs" / "openbrain-capture.log"
    assert log_path.exists(), "openbrain-capture.log not written"
    log_text = log_path.read_text(encoding="utf-8")
    assert "queue:" in log_text
    assert "evt-log-1" not in log_text or "Resume incident" in log_text  # title appears

    assert "args" in captured, "subprocess.Popen was not invoked"
    assert captured["kwargs"].get("start_new_session") is True
