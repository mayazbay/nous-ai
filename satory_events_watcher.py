#!/usr/bin/env python3
"""
satory_events_watcher.py — alert the instant Denis's dual-target fix lands.

Created: 2026-04-15 session 24, after Denis confirmed BDL changed camera push params.
Lives on Air at: ~/nous-agaas/tools/satory_events_watcher.py
Scheduled by: ~/Library/LaunchAgents/com.nous.satory-events-watcher.plist (every 5 min)

What it does:
  - Polls https://api.nousagaas.com/api/cameras
  - Reads data_freshness.events_last_seen
  - If that timestamp > KNOWN_FROZEN_AT (2026-04-05T22:08) → events are flowing again
    → fire ONE Telegram message → write state file so we don't re-alert
  - If state file exists → stay silent (already notified)

Idempotent. Self-disabling after first alert (via state file).
Self-healing: if the frozen timestamp ever freezes at a newer date, update KNOWN_FROZEN_AT.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

# ─────────────────────────── Config ───────────────────────────
API_URL = "https://api.nousagaas.com/api/cameras"
KNOWN_FROZEN_AT = "2026-04-05T22:08:05.856+05:00"  # exact last event ts before BDL re-point
STATE_FILE = Path.home() / "nous-agaas" / "logs" / "satory_events_watcher.state.json"
LOG_FILE = Path.home() / "nous-agaas" / "logs" / "satory_events_watcher.log"

# Telegram — reuse Air's existing bot config
ENV_FILE = Path.home() / "nous-agaas" / ".env"
TG_BOT_TOKEN: str = ""
TG_CHAT_ID: str = ""


def _load_env() -> None:
    """Read TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env."""
    global TG_BOT_TOKEN, TG_CHAT_ID
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            TG_BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("TELEGRAM_CHAT_ID=") or line.startswith("TELEGRAM_CHAT="):
            TG_CHAT_ID = line.split("=", 1)[1].strip().strip('"').strip("'")


def _log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().isoformat(timespec="seconds")
    with LOG_FILE.open("a") as fh:
        fh.write(f"[{ts}] {msg}\n")


def _already_notified() -> bool:
    return STATE_FILE.exists()


def _mark_notified(events_last_seen: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "notified_at": datetime.now().isoformat(timespec="seconds"),
        "events_last_seen_at_notification": events_last_seen,
    }, indent=2))


def _send_telegram(text: str) -> bool:
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        _log("telegram_skip reason=missing_bot_token_or_chat_id")
        return False
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    body = f"chat_id={quote(TG_CHAT_ID)}&text={quote(text)}&parse_mode=Markdown"
    try:
        req = Request(url, data=body.encode(), method="POST",
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(req, timeout=10) as r:
            ok = 200 <= r.status < 300
            _log(f"telegram_send ok={ok} status={r.status}")
            return ok
    except Exception as e:
        _log(f"telegram_send_error: {e}")
        return False


def _fetch_cameras() -> dict:
    req = Request(API_URL, headers={"User-Agent": "satory-events-watcher/1.0"})
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def main() -> int:
    _load_env()

    if _already_notified():
        _log("skip: already_notified — state file exists, watcher retired")
        return 0

    try:
        data = _fetch_cameras()
    except Exception as e:
        _log(f"fetch_error: {e}")
        return 1

    freshness = data.get("data_freshness") or {}
    events_last_seen = freshness.get("events_last_seen") or ""

    if not events_last_seen:
        _log("no_events_last_seen_field — backend may not have envelope; investigate")
        return 2

    # Parse as datetimes (handles millisecond precision + tz correctly — string
    # compare was wrong because "2026-04-05T22:08:05.856" > "2026-04-05T22:08:05").
    def _parse_iso(s: str) -> "datetime | None":
        s = s.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    lhs_dt = _parse_iso(events_last_seen)
    rhs_dt = _parse_iso(KNOWN_FROZEN_AT)
    if lhs_dt is None or rhs_dt is None:
        _log(f"parse_fail events_last_seen={events_last_seen} known_frozen_at={KNOWN_FROZEN_AT}")
        return 4

    # Normalize to naive UTC for comparison (drop tz so aware/naive can compare)
    if lhs_dt.tzinfo is not None:
        lhs_dt = lhs_dt.replace(tzinfo=None)
    if rhs_dt.tzinfo is not None:
        rhs_dt = rhs_dt.replace(tzinfo=None)

    # "Events resumed" = events_last_seen moved FORWARD from the frozen baseline
    # by a meaningful margin (1 second). Exact equality = same frozen record.
    if (lhs_dt - rhs_dt).total_seconds() < 1.0:
        _log(f"still_frozen events_last_seen={events_last_seen} baseline={KNOWN_FROZEN_AT}")
        return 0

    # Extra safety: require events_age_seconds to be recent (< 1 h) so we don't
    # fire on a stale DB restoration from backup.
    age = freshness.get("events_age_seconds")
    if isinstance(age, (int, float)) and age > 3600:
        _log(f"advanced_but_stale events_last_seen={events_last_seen} age={age}s — not firing")
        return 0

    # Events flowing again — fire ONCE.
    total = data.get("total", "?")
    online = data.get("online", "?")
    stale = data.get("stale", "?")
    age_s = freshness.get("events_age_seconds", "?")

    msg = (
        "🟢 *Satory events pipeline RESTORED*\n\n"
        f"`events_last_seen` advanced: `{KNOWN_FROZEN_AT}` → `{events_last_seen}`\n\n"
        f"*Current state:*\n"
        f"• `total={total}` cameras\n"
        f"• `online={online}`  `stale={stale}`\n"
        f"• events age: `{age_s}s`\n\n"
        "Denis's dual-target script evidently landed — "
        "cameras are pushing to our port 9080 again.\n\n"
        "Dashboard `satory.nousagaas.com` will self-heal as poll cron + events stream land. "
        "This watcher retires itself — no further alerts."
    )

    if _send_telegram(msg):
        _mark_notified(events_last_seen)
        _log(f"FIRED first_alert events_last_seen={events_last_seen}")
        return 0
    else:
        _log("send_failed — will retry next tick (state not saved)")
        return 3


if __name__ == "__main__":
    sys.exit(main())
