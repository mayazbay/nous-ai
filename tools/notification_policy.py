#!/usr/bin/env python3
"""notification_policy.py — central gate for all Nous factory Telegram notifications.

Three categories:
  SUPPRESS  — ledger only, zero ping. Routine cron output.
  DIGEST    — accumulated to digest-queue.jsonl, flushed 1×/day at 09:00 KZT.
  IMMEDIATE — real-time ping via tg_send.sh (human-required only).

Usage:
    from notification_policy import should_ping, flush_daily_digest

    if should_ping("supervisor-escalation", "critical", dedup_key="fp-abc123"):
        subprocess.run(["bash", "tools/tg_send.sh", message], ...)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Central registry — maps event name → category
# ---------------------------------------------------------------------------

SUPPRESS = "SUPPRESS"
DIGEST = "DIGEST"
IMMEDIATE = "IMMEDIATE"

EVENT_CLASS_REGISTRY: dict[str, str] = {
    # SUPPRESS — routine cron output, never ping Madi
    "auto-checkpoint": SUPPRESS,
    "queue-timestamp": SUPPRESS,
    "goal-cycle": SUPPRESS,
    "amd003-sync": SUPPRESS,
    "control-plane-sync": SUPPRESS,
    "openbrain-projection": SUPPRESS,
    "gbrain-doctor": SUPPRESS,
    "telegram-poll-cycle": SUPPRESS,
    "wiki-sync": SUPPRESS,
    "auto-sync-commit": SUPPRESS,
    "heartbeat-green": SUPPRESS,
    "morning-update-ok": SUPPRESS,
    "factory-probe-green": SUPPRESS,
    "docker-prune-ok": SUPPRESS,
    "docker-audit-ok": SUPPRESS,
    # DIGEST — aggregated 1×/day at 09:00 KZT alongside morning brief
    "yellow-autorepaired": DIGEST,
    "version-update-applied": DIGEST,
    "red-green-flip": DIGEST,
    "factory-probe-summary": DIGEST,
    "gbrain-pages-delta": DIGEST,
    "openbrain-capture-delta": DIGEST,
    "cost-daily-summary": DIGEST,
    # IMMEDIATE — real-time ping, human decision required
    "credential-needed": IMMEDIATE,
    "supervisor-escalation": IMMEDIATE,
    "red-at-canary-gate": IMMEDIATE,
    "budget-cap-reached": IMMEDIATE,
    "madi-decision-required": IMMEDIATE,
    "security-incident": IMMEDIATE,
}

# ---------------------------------------------------------------------------
# Paths (overridable in tests)
# ---------------------------------------------------------------------------

DEFAULT_DIGEST_QUEUE = Path("pages/systems/notification-digest-queue.jsonl")
DEFAULT_DEDUP_STATE = Path("pages/systems/notification-dedup.json")

# In-memory dedup cache: dedup_key → epoch_sent
_DEDUP_CACHE: dict[str, float] = {}

DEDUP_TTL_SECONDS = 4 * 3600  # 4h, matches factory_self_heal.py


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def should_ping(
    event_class: str,
    severity: str,
    dedup_key: Optional[str] = None,
    *,
    digest_queue: Path = DEFAULT_DIGEST_QUEUE,
    dedup_state: Path = DEFAULT_DEDUP_STATE,
    _now: Optional[float] = None,
) -> bool:
    """Return True only if this event warrants an immediate Telegram ping.

    SUPPRESS → always False (ledger only)
    DIGEST   → append to digest-queue.jsonl, return False
    IMMEDIATE → check 4h dedup, return True if not deduped

    Unknown event_class → treated as IMMEDIATE (fail-open for new events).
    """
    category = EVENT_CLASS_REGISTRY.get(event_class, IMMEDIATE)
    now = _now if _now is not None else time.time()

    if category == SUPPRESS:
        return False

    if category == DIGEST:
        _append_digest(event_class, severity, digest_queue, now)
        return False

    # IMMEDIATE — check dedup
    if dedup_key:
        if _is_deduped(dedup_key, now, dedup_state):
            return False
        _record_dedup(dedup_key, now, dedup_state)

    return True


def flush_daily_digest(
    *,
    digest_queue: Path = DEFAULT_DIGEST_QUEUE,
    _now: Optional[float] = None,
) -> Optional[str]:
    """Read digest queue, build compact text, clear queue. Returns None if empty.

    Called by morning-brief.sh at 09:00 KZT.
    """
    if not digest_queue.exists():
        return None

    lines = digest_queue.read_text(encoding="utf-8").strip().splitlines()
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    if not events:
        return None

    # Group by event_class
    grouped: dict[str, list[dict]] = {}
    for ev in events:
        key = ev.get("event_class", "unknown")
        grouped.setdefault(key, []).append(ev)

    parts = ["Daily digest:"]
    for event_class, items in sorted(grouped.items()):
        count = len(items)
        parts.append(f"  {event_class}: {count}x")

    # Clear the queue after flush
    digest_queue.write_text("", encoding="utf-8")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _append_digest(
    event_class: str,
    severity: str,
    queue_path: Path,
    now: float,
) -> None:
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    record = json.dumps(
        {"event_class": event_class, "severity": severity, "ts": now},
        ensure_ascii=False,
    )
    with queue_path.open("a", encoding="utf-8") as fh:
        fh.write(record + "\n")


def _is_deduped(dedup_key: str, now: float, state_path: Path) -> bool:
    # Check in-memory first
    last = _DEDUP_CACHE.get(dedup_key)
    if last is not None and now - last < DEDUP_TTL_SECONDS:
        return True
    # Check on-disk
    disk = _load_dedup_state(state_path)
    last_disk = disk.get(dedup_key)
    if last_disk is not None and now - float(last_disk) < DEDUP_TTL_SECONDS:
        _DEDUP_CACHE[dedup_key] = float(last_disk)
        return True
    return False


def _record_dedup(dedup_key: str, now: float, state_path: Path) -> None:
    _DEDUP_CACHE[dedup_key] = now
    disk = _load_dedup_state(state_path)
    disk[dedup_key] = now
    # Prune expired entries to keep file small
    cutoff = now - DEDUP_TTL_SECONDS
    disk = {k: v for k, v in disk.items() if float(v) > cutoff}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(disk, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_dedup_state(state_path: Path) -> dict[str, float]:
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
