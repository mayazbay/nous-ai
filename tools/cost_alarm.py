#!/usr/bin/env python3
"""Langfuse-backed LiteLLM daily cost alarm.

Runs on Air via com.nous.litellm-cost-alarm. Reads Langfuse daily metrics from
the VPS-hosted Langfuse instance and alerts when today's cost exceeds either a
hard cap or a rolling baseline.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_ENV_FILE = Path("/Users/madia/nous-agaas/litellm/.env")
DEFAULT_STATE_PATH = Path("/Users/madia/nous-agaas/state/litellm_langfuse_cost_alarm.json")
DEFAULT_TG_SEND = Path("/Users/madia/nous-agaas/wiki/tools/tg_send.sh")
DEFAULT_HARD_CAP_USD = 40.0
DEFAULT_ROLLING_MULTIPLE = 3.0
DEFAULT_TRACE_NAME = "litellm-acompletion"
DEFAULT_TELEGRAM_SERVICE_LABEL = "com.nous.telegram-poll"


@dataclass(frozen=True)
class CostEvaluation:
    today: str
    today_cost: float
    rolling_avg: float
    hard_cap_usd: float
    rolling_multiple: float
    alert_reasons: tuple[str, ...]
    previous_costs: tuple[float, ...]

    @property
    def should_alert(self) -> bool:
        return bool(self.alert_reasons)


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_state(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"alerts": []}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def fetch_daily_metrics(
    host: str,
    public_key: str,
    secret_key: str,
    *,
    trace_name: str = DEFAULT_TRACE_NAME,
    timeout_s: float = 15,
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"traceName": trace_name}) if trace_name else ""
    url = host.rstrip("/") + "/api/public/metrics/daily"
    if query:
        url += "?" + query
    token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        data = json.loads(response.read().decode("utf-8"))
    rows = data.get("data", [])
    if not isinstance(rows, list):
        raise ValueError("Langfuse metrics response missing data list")
    return rows


def costs_by_date(rows: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        day = str(row.get("date", ""))
        if not day:
            continue
        try:
            cost = float(row.get("totalCost") or 0)
        except (TypeError, ValueError):
            cost = 0.0
        out[day] = out.get(day, 0.0) + cost
    return out


def evaluate_costs(
    costs: dict[str, float],
    *,
    today: date,
    hard_cap_usd: float = DEFAULT_HARD_CAP_USD,
    rolling_multiple: float = DEFAULT_ROLLING_MULTIPLE,
) -> CostEvaluation:
    today_key = today.isoformat()
    today_cost = float(costs.get(today_key, 0.0))
    previous_costs = tuple(
        float(costs.get((today - timedelta(days=offset)).isoformat(), 0.0))
        for offset in range(1, 8)
    )
    rolling_avg = sum(previous_costs) / 7.0
    reasons: list[str] = []
    if today_cost > hard_cap_usd:
        reasons.append(f"hard_cap:{today_cost:.4f}>{hard_cap_usd:.4f}")
    if rolling_avg > 0 and today_cost > (rolling_multiple * rolling_avg):
        reasons.append(f"rolling:{today_cost:.4f}>{rolling_multiple:.2f}x{rolling_avg:.4f}")
    return CostEvaluation(
        today=today_key,
        today_cost=today_cost,
        rolling_avg=rolling_avg,
        hard_cap_usd=hard_cap_usd,
        rolling_multiple=rolling_multiple,
        alert_reasons=tuple(reasons),
        previous_costs=previous_costs,
    )


def alert_reason_types(evaluation: CostEvaluation) -> tuple[str, ...]:
    """Stable alert classes for same-day dedupe.

    `alert_reasons` includes live cost values. Those values drift upward during
    the day, so using the raw string as an idempotency key pages repeatedly for
    the same rolling-baseline condition.
    """
    return tuple(reason.split(":", 1)[0] for reason in evaluation.alert_reasons)


def alert_fingerprint(evaluation: CostEvaluation) -> str:
    return ",".join(alert_reason_types(evaluation))


def recorded_reason_types(item: dict[str, Any]) -> tuple[str, ...]:
    raw = item.get("reason_types")
    if isinstance(raw, list):
        return tuple(str(value) for value in raw)
    reason_key = str(item.get("reason_key", ""))
    return tuple(part.split(":", 1)[0] for part in reason_key.split(",") if part)


def already_alerted(state: dict[str, Any], evaluation: CostEvaluation) -> bool:
    sent = state.get("alerts", [])
    if not isinstance(sent, list):
        return False
    reason_types = alert_reason_types(evaluation)
    return any(
        item.get("date") == evaluation.today and recorded_reason_types(item) == reason_types
        for item in sent
        if isinstance(item, dict)
    )


def record_alert(state: dict[str, Any], evaluation: CostEvaluation) -> None:
    alerts = state.setdefault("alerts", [])
    if not isinstance(alerts, list):
        state["alerts"] = alerts = []
    alerts.append(
        {
            "date": evaluation.today,
            "reason_key": alert_fingerprint(evaluation),
            "reason_types": list(alert_reason_types(evaluation)),
            "reason_details": list(evaluation.alert_reasons),
            "today_cost": evaluation.today_cost,
            "rolling_avg": evaluation.rolling_avg,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
    )


def notify_telegram(tg_send: Path, message: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["bash", str(tg_send), message],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def build_alert_message(evaluation: CostEvaluation) -> str:
    return (
        "🔴 LiteLLM Langfuse cost alarm: "
        f"today=${evaluation.today_cost:.2f}, "
        f"7d_avg=${evaluation.rolling_avg:.2f}, "
        f"hard_cap=${evaluation.hard_cap_usd:.2f}, "
        f"rolling_limit={evaluation.rolling_multiple:.1f}x. "
        f"Reasons: {', '.join(evaluation.alert_reasons)}"
    )


def pause_launchd_service(label: str, *, uid: int | None = None) -> tuple[bool, str]:
    """Disable and stop a launchd service without raising on failure."""
    user_id = os.getuid() if uid is None else uid
    target = f"gui/{user_id}/{label}"
    outputs: list[str] = []
    ok = True
    for command in (
        ["launchctl", "disable", target],
        ["launchctl", "kill", "TERM", target],
    ):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        outputs.append(f"{' '.join(command)} -> rc={result.returncode}" + (f" {output}" if output else ""))
        if result.returncode != 0:
            ok = False
    return ok, " | ".join(outputs)


def parse_today(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Langfuse-backed LiteLLM cost alarm.")
    ap.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    ap.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    ap.add_argument("--tg-send", default=str(DEFAULT_TG_SEND))
    ap.add_argument("--host", default="")
    ap.add_argument("--trace-name", default=DEFAULT_TRACE_NAME)
    ap.add_argument("--hard-cap-usd", type=float, default=DEFAULT_HARD_CAP_USD)
    ap.add_argument("--rolling-multiple", type=float, default=DEFAULT_ROLLING_MULTIPLE)
    ap.add_argument("--today", default="")
    ap.add_argument("--no-alert", action="store_true")
    ap.add_argument("--pause-telegram-on-hard-cap", action="store_true")
    ap.add_argument("--telegram-service-label", default=DEFAULT_TELEGRAM_SERVICE_LABEL)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    env = load_env(Path(args.env_file))
    host = args.host or env.get("LANGFUSE_HOST") or env.get("LANGFUSE_BASE_URL")
    public_key = env.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = env.get("LANGFUSE_SECRET_KEY", "")
    missing = [name for name, value in {
        "LANGFUSE_HOST": host,
        "LANGFUSE_PUBLIC_KEY": public_key,
        "LANGFUSE_SECRET_KEY": secret_key,
    }.items() if not value]
    if missing:
        print("missing_env=" + ",".join(missing), file=sys.stderr)
        return 2

    rows = fetch_daily_metrics(host, public_key, secret_key, trace_name=args.trace_name)
    evaluation = evaluate_costs(
        costs_by_date(rows),
        today=parse_today(args.today),
        hard_cap_usd=args.hard_cap_usd,
        rolling_multiple=args.rolling_multiple,
    )
    state_path = Path(args.state_path)
    state = load_state(state_path)

    alert_sent = False
    alert_output = ""
    pause_attempted = False
    pause_ok = False
    pause_output = ""
    hard_cap_hit = "hard_cap" in alert_reason_types(evaluation)
    if evaluation.should_alert and not already_alerted(state, evaluation) and not args.no_alert:
        alert_sent, alert_output = notify_telegram(Path(args.tg_send), build_alert_message(evaluation))
        if args.pause_telegram_on_hard_cap and hard_cap_hit:
            pause_attempted = True
            pause_ok, pause_output = pause_launchd_service(args.telegram_service_label)
        if alert_sent:
            record_alert(state, evaluation)
            save_state(state_path, state)
    elif evaluation.should_alert and args.no_alert:
        alert_output = "suppressed_by_no_alert"
    else:
        save_state(state_path, state)

    payload = {
        "today": evaluation.today,
        "today_cost": round(evaluation.today_cost, 6),
        "rolling_avg": round(evaluation.rolling_avg, 6),
        "hard_cap_usd": evaluation.hard_cap_usd,
        "rolling_multiple": evaluation.rolling_multiple,
        "alert_reasons": list(evaluation.alert_reasons),
        "alert_sent": alert_sent,
        "alert_output": alert_output,
        "pause_attempted": pause_attempted,
        "pause_ok": pause_ok,
        "pause_output": pause_output,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            f"[{evaluation.today}] today=${evaluation.today_cost:.4f} "
            f"7d_avg=${evaluation.rolling_avg:.4f} "
            f"reasons={','.join(evaluation.alert_reasons) or 'none'} "
            f"alert_sent={alert_sent}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
