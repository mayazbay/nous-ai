#!/usr/bin/env python3
"""
model_escalator.py — Model escalation logic for the AGaaS factory.

Routes tasks to the appropriate model tier based on consecutive failure history.
Implements the master-doc rule:
  "Routine/bulk work → DeepSeek V4 Flash via OpenRouter. After 2 consecutive
   DeepSeek V4 Flash failures → DeepSeek V4 Pro. Strategic CEO work → Codex
   `/codex` or explicit Opus/Sonnet path, never auto-selected."

State is stored in a small SQLite DB so it persists across process restarts
(important for cron-based callers like telegram_poll.py → run_task.py).

Usage (in run_task.py or command_center.py):
    from model_escalator import ModelEscalator

    esc = ModelEscalator()
    model = esc.pick()          # "deepseek-v4-flash" or "deepseek-v4-pro"
    ...
    esc.record_success(model)   # resets failure counter for this model
    esc.record_failure(model)   # increments; triggers escalation at threshold

Substrate note (session 71 C1, 2026-04-24): this file is the canonical wiki
copy. On Air, /Users/madia/nous-agaas/model_escalator.py is a symlink to
/Users/madia/nous-agaas/wiki/tools/model_escalator.py so future audits and
edits happen under git. See factory-ops SKILL.md AP-28 for history.
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

KZ_TZ = timezone(timedelta(hours=5))

_DDL = """
CREATE TABLE IF NOT EXISTS model_state (
    model       TEXT PRIMARY KEY,
    failures    INTEGER NOT NULL DEFAULT 0,
    last_used   TEXT,
    last_result TEXT
);
"""

# Thresholds
ESCALATION_THRESHOLD = 2   # consecutive DeepSeek V4 Flash failures before switching to DeepSeek V4 Pro
RECOVERY_THRESHOLD   = 3   # consecutive escalation-tier successes before allowing Flash again (reserved)
STALE_HOURS          = 24  # primary failures older than this auto-reset on next pick() — prevents permanent lock-in from transient upstream incidents

# Model tiers (in order of escalation)
TIER_PRIMARY    = "deepseek-v4-flash"
TIER_ESCALATION = "deepseek-v4-pro"
TIER_STRATEGIC  = "opus"     # requires explicit override; /codex is preferred CEO path

DEFAULT_DB = "/Users/madia/nous-agaas/logs/model_state.db"


class ModelEscalator:
    """
    Tracks per-model consecutive failure counts and selects the best model
    for the next task.

    Rules:
    1. Start with DeepSeek V4 Flash (primary cheap worker).
    2. After ESCALATION_THRESHOLD consecutive failures → switch to DeepSeek V4 Pro.
    3. Keep Grok/Sonnet/GLM as LiteLLM fallbacks, not escalator primaries.
    4. Codex/Opus are never auto-selected — they require explicit CEO/high-value routing.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self._db = str(db_path)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        Path(self._db).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_DDL)

    def _get(self, model: str) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM model_state WHERE model=?", (model,)
            ).fetchone()
        if row:
            return dict(row)
        return {"model": model, "failures": 0, "last_used": None, "last_result": None}

    def _set_failures(self, model: str, failures: int, result: str):
        now = datetime.now(KZ_TZ).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO model_state (model, failures, last_used, last_result)
                   VALUES (?,?,?,?)
                   ON CONFLICT(model) DO UPDATE SET
                     failures=excluded.failures,
                     last_used=excluded.last_used,
                     last_result=excluded.last_result""",
                (model, failures, now, result),
            )

    def record_success(self, model: str):
        """Reset failure counter for this model."""
        self._set_failures(model, 0, "success")
        log.info("escalator: %s success — failures reset to 0", model)

    def record_failure(self, model: str):
        """Increment consecutive failure counter."""
        state = self._get(model)
        new_failures = state["failures"] + 1
        self._set_failures(model, new_failures, "failure")
        log.warning(
            "escalator: %s failure #%d (threshold=%d)",
            model, new_failures, ESCALATION_THRESHOLD,
        )

    def failures(self, model: str) -> int:
        """Current consecutive failure count for a model."""
        return self._get(model)["failures"]

    def pick(self) -> str:
        """
        Select the best model for the next task.

        Returns:
            "deepseek-v4-flash" under normal conditions, or when primary-tier failures are stale.
            "deepseek-v4-pro" after ESCALATION_THRESHOLD consecutive Flash failures.

        Recovery path (session 71, 2026-04-24): primary failures older than
        STALE_HOURS auto-reset on next pick(). Prevents the escalator from
        locking onto the escalation tier permanently after a transient upstream incident.

        Never returns "opus" or Codex — those require explicit high-value routing.
        """
        # Stale-failure recovery: if primary last failed >STALE_HOURS ago, reset.
        primary_state = self._get(TIER_PRIMARY)
        if (
            primary_state["failures"] >= ESCALATION_THRESHOLD
            and primary_state["last_used"]
            and primary_state["last_result"] == "failure"
        ):
            try:
                last_used = datetime.fromisoformat(primary_state["last_used"])
                age_hours = (datetime.now(KZ_TZ) - last_used).total_seconds() / 3600
                if age_hours >= STALE_HOURS:
                    log.info(
                        "escalator: %s failures stale (%.1fh old >= %dh) — auto-reset for retry",
                        TIER_PRIMARY,
                        age_hours, STALE_HOURS,
                    )
                    self._set_failures(TIER_PRIMARY, 0, "stale_auto_reset")
            except (ValueError, TypeError) as e:
                log.warning("escalator: could not parse %s last_used %r: %s", TIER_PRIMARY, primary_state["last_used"], e)

        primary_failures = self.failures(TIER_PRIMARY)
        if primary_failures >= ESCALATION_THRESHOLD:
            escalation_failures = self.failures(TIER_ESCALATION)
            if escalation_failures > 0:
                log.warning(
                    "escalator: both %s (%d) and %s (%d) failing — using %s",
                    TIER_PRIMARY, primary_failures, TIER_ESCALATION, escalation_failures, TIER_ESCALATION,
                )
            log.info(
                "escalator: %s failed %d times (>=%d) → escalating to %s",
                TIER_PRIMARY, primary_failures, ESCALATION_THRESHOLD, TIER_ESCALATION,
            )
            return TIER_ESCALATION

        return TIER_PRIMARY

    def reset(self, model: str | None = None):
        """
        Reset failure count. Pass model=None to reset ALL models.
        Used after manual investigation clears the failure root cause.
        """
        if model:
            self._set_failures(model, 0, "manual_reset")
            log.info("escalator: manually reset %s", model)
        else:
            with self._conn() as conn:
                conn.execute("UPDATE model_state SET failures=0, last_result='manual_reset'")
            log.info("escalator: all models reset")

    def status(self) -> dict[str, dict]:
        """Return current state of all tracked models."""
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM model_state").fetchall()
        return {r["model"]: dict(r) for r in rows}
