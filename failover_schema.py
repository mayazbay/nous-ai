"""Schema validation for the model failover ledger (pages/systems/model-failover-ledger.jsonl).

Parses JSONL rows written by tools/model_failover_state.py into typed, frozen dataclasses.
Malformed rows are returned as BrokenRow so callers can quarantine them without losing data.
"""

from __future__ import annotations

import datetime as dt
import fcntl
import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

ALMATY = dt.timezone(dt.timedelta(hours=5))
BROKEN_REL = Path("pages/systems/model-failover-ledger.broken.jsonl")


@dataclass(frozen=True)
class StartedRow:
    event_id: str
    phase: str
    status: str
    ts: str
    command: str
    msg_id: int
    chat_id: int
    query: str
    model: str
    via: str
    continuity_packet: str
    latest_handoff: str
    git_head: str

    def as_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass(frozen=True)
class FinishedRow:
    event_id: str
    phase: str
    status: str
    ts: str
    response_head: str
    receipt: str
    git_head: str

    def as_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass(frozen=True)
class BrokenRow:
    raw_line: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


_STARTED_SPEC: tuple[tuple[str, type], ...] = (
    ("event_id", str),
    ("phase", str),
    ("status", str),
    ("ts", str),
    ("command", str),
    ("msg_id", int),
    ("chat_id", int),
    ("query", str),
    ("model", str),
    ("via", str),
    ("continuity_packet", str),
    ("latest_handoff", str),
    ("git_head", str),
)

_FINISHED_SPEC: tuple[tuple[str, type], ...] = (
    ("event_id", str),
    ("phase", str),
    ("status", str),
    ("ts", str),
    ("response_head", str),
    ("receipt", str),
    ("git_head", str),
)


def _type_name(t: type) -> str:
    return t.__name__


def _validate(
    data: dict[str, Any],
    spec: tuple[tuple[str, type], ...],
    raw_line: str,
) -> tuple[dict[str, Any] | None, BrokenRow | None]:
    for name, expected in spec:
        if name not in data:
            return None, BrokenRow(raw_line=raw_line, reason=f"missing_field: {name}")
        value = data[name]
        # bool is a subclass of int — reject bools where int is required to avoid silent coercion
        if expected is int and isinstance(value, bool):
            return None, BrokenRow(
                raw_line=raw_line,
                reason=f"wrong_type: {name} expected {_type_name(expected)}",
            )
        if not isinstance(value, expected):
            return None, BrokenRow(
                raw_line=raw_line,
                reason=f"wrong_type: {name} expected {_type_name(expected)}",
            )
    return data, None


def parse_row(
    line: str,
) -> tuple[StartedRow | FinishedRow | None, BrokenRow | None]:
    """Parse a single JSONL line into a typed row or BrokenRow.

    Empty/whitespace-only lines return (None, None) so callers can skip them silently.
    """
    if not line or not line.strip():
        return None, None

    raw_line = line.rstrip("\n")

    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        return None, BrokenRow(raw_line=raw_line, reason=f"invalid_json: {exc}")

    if not isinstance(data, dict):
        return None, BrokenRow(raw_line=raw_line, reason="invalid_json: not an object")

    if "phase" not in data:
        return None, BrokenRow(raw_line=raw_line, reason="missing_phase")

    phase = data["phase"]
    if phase == "started":
        validated, broken = _validate(data, _STARTED_SPEC, raw_line)
        if broken is not None:
            return None, broken
        assert validated is not None
        return (
            StartedRow(
                event_id=validated["event_id"],
                phase=validated["phase"],
                status=validated["status"],
                ts=validated["ts"],
                command=validated["command"],
                msg_id=validated["msg_id"],
                chat_id=validated["chat_id"],
                query=validated["query"],
                model=validated["model"],
                via=validated["via"],
                continuity_packet=validated["continuity_packet"],
                latest_handoff=validated["latest_handoff"],
                git_head=validated["git_head"],
            ),
            None,
        )
    if phase == "finished":
        validated, broken = _validate(data, _FINISHED_SPEC, raw_line)
        if broken is not None:
            return None, broken
        assert validated is not None
        return (
            FinishedRow(
                event_id=validated["event_id"],
                phase=validated["phase"],
                status=validated["status"],
                ts=validated["ts"],
                response_head=validated["response_head"],
                receipt=validated["receipt"],
                git_head=validated["git_head"],
            ),
            None,
        )
    return None, BrokenRow(raw_line=raw_line, reason=f"unknown_phase: {phase}")


def quarantine_broken(wiki_path: Path | str, broken_rows: list[BrokenRow]) -> int:
    """Append broken rows to pages/systems/model-failover-ledger.broken.jsonl under wiki_path.

    Uses fcntl.LOCK_EX for cross-process safety; multiple writers append without interleave.
    """
    if not broken_rows:
        return 0

    wiki = Path(wiki_path)
    target = wiki / BROKEN_REL
    target.parent.mkdir(parents=True, exist_ok=True)

    ts = dt.datetime.now(ALMATY).isoformat()

    with target.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            count = 0
            for broken in broken_rows:
                record = {
                    "reason": broken.reason,
                    "raw": broken.raw_line,
                    "quarantined_ts": ts,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    return count
