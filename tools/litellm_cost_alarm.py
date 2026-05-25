#!/usr/bin/env python3
"""
litellm_cost_alarm.py — daily cost heuristic alarm for LiteLLM on Air

LiteLLM on Air runs without a DB connection (see session-55 deep audit) so the
built-in `max_budget: 30.0` / `budget_duration: "1d"` in config.yaml does NOT
actually enforce anything. This script is the external fallback alarm.

Heuristic (v2: model-aware where the factory gives us model data):
  - Tails LiteLLM HTTP access log `~/nous-agaas/logs/litellm.log`
  - Counts `POST /chat/completions` lines (optionally filtered by today's date)
  - Estimates attributed daily spend from `logs/run_task.log` using actual
    `model`, `input_tokens`, and `output_tokens`
  - Reports access-log calls not represented in run_task.log as opaque volume
    instead of multiplying them by a fake Opus-heavy per-call price
  - Compares to 4 thresholds: 50%/80%/100%/150% of DAILY_BUDGET
  - Pushes Telegram alert if threshold crossed since last check (state file
    tracks last-triggered threshold to avoid spam)

Runs every 30 min via `com.nous.litellm-cost-alarm` launchd on Air.

Honest limits (codified so we fix with data, not speculation):
  1. HTTP access log has no model. The attributed estimate is only for calls
     that also land in run_task.log. Opaque calls are loudly reported but not
     priced as Opus by default.
  2. Per-model price table must be kept aligned with LiteLLM config/provider
     pricing. It is still an estimate until LiteLLM success_callback/Langfuse
     is wired.
  3. No request-duration correlation — 636 health checks don't mean 636 billed
     calls. The script filters /chat/completions specifically.
  4. Log rotation loses history; script resets estimate on log-rotate. OK for
     day-boundary reset, not OK for mid-day rotate. Future work: parse rotated
     logs too.

Codified in: `factory-ops` AP-26 (session-55 follow-on). NOT in session-51 G1
because session-55 discovered LiteLLM DB-not-connected during audit.
"""

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

LOG_PATH = Path.home() / "nous-agaas" / "logs" / "litellm.log"
RUN_TASK_LOG_PATH = Path.home() / "nous-agaas" / "logs" / "run_task.log"
STATE_PATH = Path.home() / "nous-agaas" / "state" / "litellm_alarm_last.json"
TG_SEND = Path.home() / "nous-agaas" / "wiki" / "tools" / "tg_send.sh"

DAILY_BUDGET_USD = 30.0
SCHEMA_VERSION = 2
MODEL_PRICES_PER_M_TOKENS = {
    "opus": (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku-4-5": (0.8, 4.0),
    "grok-reasoning": (2.0, 6.0),
    "grok-code-fast": (0.2, 1.5),
    "glm-5.1": (1.4, 4.4),
    "glm-4.5-flash": (0.0, 0.0),
}
THRESHOLDS = [0.50, 0.80, 1.00, 1.50]  # 50%, 80%, 100% (cap), 150% (runaway)
THRESHOLD_LABELS = ["WARN", "CRITICAL", "AT_CAP", "RUNAWAY"]

# Promo-expiry watch: alert when a model's promotional pricing window ends
# so we can re-evaluate per-tier routing in `ceo-hierarchy` skill.
# Codified in PLAN-2026-04-30-deepseek-promo-expiry-watch + gbrain-ops AP-72.
# Idempotent: state file tracks last-alerted dates per model.
MODEL_PROMO_WATCH = {
    "deepseek-v4-pro": {
        "promo_name": "DeepSeek V4 Pro 75%-off launch promo",
        "expires": "2026-05-31",          # last day of promo (inclusive)
        "expected_jump_factor": 4.0,       # output-token cost jumps ~4x post-expiry
        "doctrine_skill": "ceo-hierarchy",
        "next_step": "Re-run gbrain-ops AP-72 playbook: WebSearch latest DeepSeek pricing, "
                      "compare to alternatives (GLM, Grok, Haiku), Musk step-2 the urge to flip, "
                      "update ceo-hierarchy if tier rationale changes.",
    },
}


def check_promo_expiry(state):
    """Emit Telegram alerts when a watched model's promo enters T-1, T-0,
    or T+1 day window. Idempotent via state['promo_alerts'][model] = last_date.
    Returns list of alert messages (caller pushes via TG_SEND).
    """
    today = date.today().isoformat()
    alerts = state.setdefault("promo_alerts", {})
    out = []
    for model, info in MODEL_PROMO_WATCH.items():
        expires = info.get("expires")
        if not expires:
            continue
        try:
            from datetime import datetime, timedelta
            exp_d = datetime.fromisoformat(expires).date()
            today_d = datetime.fromisoformat(today).date()
            delta_days = (exp_d - today_d).days
        except Exception:
            continue
        last_alerted = alerts.get(model, "")
        msg = None
        if delta_days == 1 and last_alerted != f"{today}-pre1":
            msg = (f"⏰ {info['promo_name']} ends TOMORROW ({expires}). "
                   f"Output-token cost jumps {info['expected_jump_factor']}x. "
                   f"Re-evaluate routing in [[skills/{info['doctrine_skill']}]]. "
                   f"Run: gbrain-ops AP-72 playbook.")
            alerts[model] = f"{today}-pre1"
        elif delta_days == 0 and last_alerted != f"{today}-day0":
            msg = (f"⏰ {info['promo_name']} ENDS TODAY ({expires}). "
                   f"Cost jumps {info['expected_jump_factor']}x at midnight UTC. "
                   f"Action: gbrain-ops AP-72 playbook NOW.")
            alerts[model] = f"{today}-day0"
        elif delta_days == -1 and last_alerted != f"{today}-post1":
            msg = (f"⚠️  {info['promo_name']} ENDED yesterday ({expires}). "
                   f"Verify per-tier $/token in production telemetry. "
                   f"If observed cost ≥ {info['expected_jump_factor']}x baseline, "
                   f"flip ceo-hierarchy default to cheaper tier.")
            alerts[model] = f"{today}-post1"
        if msg:
            out.append(msg)
    return out


def count_todays_calls():
    """Count successful chat/completions lines in LiteLLM log from today only.

    Session 73 (2026-04-25): widened path match to include `/v1/chat/completions`
    (LiteLLM dual-mounts both); widened status match to include the new JSON
    log shape `"... HTTP/1.1\" 200"` which dropped the trailing `OK` substring.
    Pre-fix the alarm reported 0 calls/day vs ~121 actual on 2026-04-25 (56%
    of traffic was on `/v1/...` and 100% of new lines lack `200 OK`). Codified
    as factory-ops AP-29 (cost-alarm regex drift on LiteLLM upgrade).
    """
    if not LOG_PATH.exists():
        return 0

    count = 0
    with LOG_PATH.open() as fh:
        for line in fh:
            if 'POST /chat/completions' not in line and 'POST /v1/chat/completions' not in line:
                continue
            if '200 OK' in line or '" 200' in line or '\\" 200' in line:
                count += 1
    return count


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"schema_version": SCHEMA_VERSION, "date": "", "last_threshold_hit": -1, "start_of_day_count": None}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def notify_telegram(msg):
    """Push message via tg_send.sh. Returns True on success."""
    if not TG_SEND.exists():
        print(f"WARN: {TG_SEND} missing; skipping Telegram", file=sys.stderr)
        return False
    result = subprocess.run(
        ["bash", str(TG_SEND), msg],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"WARN: tg_send failed: {result.stderr}", file=sys.stderr)
        return False
    return True


def estimate_run_task_spend(today: str) -> dict:
    """Estimate spend from run_task.log entries for today's KZ date."""
    summary = {
        "entries": 0,
        "priced_entries": 0,
        "unknown_entries": 0,
        "spend": 0.0,
        "by_model": {},
    }
    if not RUN_TASK_LOG_PATH.exists():
        return summary

    with RUN_TASK_LOG_PATH.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            ts = str(entry.get("ts", ""))
            if not ts.startswith(today):
                continue
            model = str(entry.get("model", "") or "")
            if not model:
                continue
            summary["entries"] += 1
            try:
                input_tokens = int(entry.get("input_tokens") or 0)
                output_tokens = int(entry.get("output_tokens") or 0)
            except (TypeError, ValueError):
                input_tokens = 0
                output_tokens = 0

            prices = MODEL_PRICES_PER_M_TOKENS.get(model)
            model_bucket = summary["by_model"].setdefault(
                model,
                {"entries": 0, "input_tokens": 0, "output_tokens": 0, "spend": 0.0},
            )
            model_bucket["entries"] += 1
            model_bucket["input_tokens"] += input_tokens
            model_bucket["output_tokens"] += output_tokens

            if not prices:
                summary["unknown_entries"] += 1
                continue
            input_price, output_price = prices
            cost = ((input_tokens * input_price) + (output_tokens * output_price)) / 1_000_000
            summary["priced_entries"] += 1
            summary["spend"] += cost
            model_bucket["spend"] += cost
    return summary


def format_model_breakdown(by_model: dict) -> str:
    parts = []
    for model, data in sorted(by_model.items(), key=lambda kv: kv[1].get("spend", 0), reverse=True):
        parts.append(
            f"{model}:{data.get('entries', 0)}=${data.get('spend', 0.0):.2f}"
        )
    return ", ".join(parts) if parts else "none"


def main():
    today = date.today().isoformat()
    state = load_state()
    total_calls = count_todays_calls()  # cumulative in the current log file
    spend_summary = estimate_run_task_spend(today)

    # Day-boundary: reset snapshot marker to current total
    if state.get("schema_version") != SCHEMA_VERSION or state.get("date") != today:
        state = {
            "schema_version": SCHEMA_VERSION,
            "date": today,
            "last_threshold_hit": -1,
            "start_of_day_count": total_calls,
        }

    # If snapshot is missing (fresh install or state corruption): initialize it
    # WITHOUT firing any alarm. First real measurement will be on next run.
    if state.get("start_of_day_count") is None:
        state["start_of_day_count"] = total_calls
        save_state(state)
        print(f"[{today}] INIT: start_of_day_count={total_calls} (first run of day; no alarm yet)")
        return

    # Handle log rotation: if total_calls < snapshot, the log was truncated/rotated
    # during the day. Reset snapshot to current total and don't alarm this cycle.
    if total_calls < state["start_of_day_count"]:
        state["start_of_day_count"] = total_calls
        save_state(state)
        print(f"[{today}] LOG_ROTATED: reset start_of_day_count={total_calls}")
        return

    calls = total_calls - state["start_of_day_count"]
    estimated_spend = spend_summary["spend"]
    opaque_calls = max(0, calls - spend_summary["entries"])
    pct = estimated_spend / DAILY_BUDGET_USD if DAILY_BUDGET_USD > 0 else 0

    # Find the highest threshold crossed
    current_tier = -1
    for i, thr in enumerate(THRESHOLDS):
        if pct >= thr:
            current_tier = i

    last_tier = state.get("last_threshold_hit", -1)

    print(f"[{today}] calls_today={calls} (total_in_log={total_calls}, "
          f"start_of_day={state['start_of_day_count']}) "
          f"attributed_entries={spend_summary['entries']} "
          f"opaque_calls={opaque_calls} "
          f"model_spend=${estimated_spend:.2f} "
          f"pct={pct*100:.0f}% of ${DAILY_BUDGET_USD:.0f} "
          f"tier={current_tier} last={last_tier} "
          f"models=[{format_model_breakdown(spend_summary['by_model'])}]")

    if current_tier > last_tier:
        label = THRESHOLD_LABELS[current_tier]
        emoji = {"WARN": "🟡", "CRITICAL": "🔴", "AT_CAP": "🚨", "RUNAWAY": "💥"}[label]
        msg = (
            f"{emoji} LiteLLM cost alarm: {label} — attributed model spend ${estimated_spend:.2f} "
            f"({pct*100:.0f}% of ${DAILY_BUDGET_USD:.0f} daily budget) "
            f"from {spend_summary['entries']} run_task entries today; "
            f"{opaque_calls} LiteLLM access-log calls are cost-opaque. "
            f"Models: {format_model_breakdown(spend_summary['by_model'])}. "
            f"If runaway: ssh air 'launchctl stop com.nous.telegram-poll' to pause factory."
        )
        if notify_telegram(msg):
            state["last_threshold_hit"] = current_tier
            save_state(state)
            print(f"Telegram sent: tier {current_tier} ({label})")
    else:
        save_state(state)

    # Promo-expiry watch: independent of cost-tier alarms; runs on every cycle.
    # Fires T-1, T-0, T+1 day windows per model. State idempotency in
    # state['promo_alerts'][model] = "<today>-pre1|day0|post1".
    # Codified in PLAN-2026-04-30-deepseek-promo-expiry-watch + gbrain-ops AP-72.
    promo_msgs = check_promo_expiry(state)
    for pm in promo_msgs:
        if notify_telegram(pm):
            print(f"Promo-expiry alert sent: {pm[:80]}…")
    if promo_msgs:
        save_state(state)


if __name__ == "__main__":
    main()
