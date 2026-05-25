#!/usr/bin/env python3
"""Append-only ops event ledger helper.

Runtime ledger path defaults to Air:
`/Users/madia/nous-agaas/state/ops_events.jsonl`.
"""

from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Iterator, Mapping


LEDGER_ENV = "NOUS_OPS_EVENTS_PATH"
DEFAULT_LEDGER = Path("/Users/madia/nous-agaas/state/ops_events.jsonl")
SCHEMA_VERSION = 1
REQUIRED_FIELDS = {
    "ts",
    "source",
    "external_id",
    "actor",
    "version",
    "payload_hash",
    "intent_id",
    "idempotency_key",
    "correlation_id",
}


class EventLedgerError(ValueError):
    """Raised when an event cannot be represented safely in the ledger."""


def ledger_path() -> Path:
    return Path(os.environ.get(LEDGER_ENV, str(DEFAULT_LEDGER))).expanduser()


def payload_hash(payload: Mapping[str, Any]) -> str:
    payload_bytes = _canonical_payload(payload)
    return hashlib.sha256(payload_bytes).hexdigest()


def append_event(
    source: str,
    external_id: str,
    actor: str,
    payload: Mapping[str, Any],
    correlation_id: str,
) -> str:
    """Append one event unless its idempotency key already exists.

    Returns the event intent_id. If the idempotency key was already recorded,
    returns the existing event's intent_id and does not append a duplicate line.
    """

    _validate_text("source", source)
    _validate_text("external_id", external_id)
    _validate_text("actor", actor)
    _validate_text("correlation_id", correlation_id)
    _canonical_payload(payload)

    intent_id = _optional_payload_text(payload, "intent_id") or str(uuid.uuid4())
    idempotency_key = _optional_payload_text(payload, "idempotency_key") or intent_id
    event = {
        "ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": source,
        "external_id": external_id,
        "actor": actor,
        "version": SCHEMA_VERSION,
        "payload_hash": payload_hash(payload),
        "intent_id": intent_id,
        "idempotency_key": idempotency_key,
        "correlation_id": correlation_id,
    }

    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        fh.seek(0)
        for existing in _iter_lines(fh):
            if existing["idempotency_key"] == idempotency_key:
                return str(existing["intent_id"])
        fh.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return intent_id


def check_idempotent(idempotency_key: str) -> bool:
    _validate_text("idempotency_key", idempotency_key)
    path = ledger_path()
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
        return any(event["idempotency_key"] == idempotency_key for event in _iter_lines(fh))


def replay_events() -> list[dict[str, Any]]:
    path = ledger_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
        return list(_iter_lines(fh))


def _canonical_payload(payload: Mapping[str, Any]) -> bytes:
    if not isinstance(payload, Mapping):
        raise EventLedgerError("payload must be a JSON object")
    try:
        return json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EventLedgerError(f"payload is not JSON-serializable: {exc}") from exc


def _optional_payload_text(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise EventLedgerError(f"payload.{key} must be a non-empty string")
    return value


def _validate_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EventLedgerError(f"{name} must be a non-empty string")


def _iter_lines(fh: Any) -> Iterator[dict[str, Any]]:
    for lineno, raw in enumerate(fh, start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventLedgerError(f"malformed ledger JSON at line {lineno}: {exc}") from exc
        if not isinstance(event, dict):
            raise EventLedgerError(f"malformed ledger event at line {lineno}: not an object")
        missing = REQUIRED_FIELDS - set(event)
        if missing:
            raise EventLedgerError(f"malformed ledger event at line {lineno}: missing {sorted(missing)}")
        yield event
