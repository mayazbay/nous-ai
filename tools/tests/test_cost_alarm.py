"""Tests for Langfuse-backed LiteLLM cost alarm."""

from __future__ import annotations

from datetime import date
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import cost_alarm


def test_hard_cap_alerts_above_40():
    ev = cost_alarm.evaluate_costs(
        {"2026-05-05": 40.01},
        today=date(2026, 5, 5),
    )

    assert ev.should_alert is True
    assert ev.alert_reasons == ("hard_cap:40.0100>40.0000",)


def test_rolling_average_alerts_at_more_than_3x():
    costs = {"2026-05-05": 31.0}
    for day in range(28, 31):
        costs[f"2026-04-{day}"] = 10.0
    for day in range(1, 5):
        costs[f"2026-05-0{day}"] = 10.0

    ev = cost_alarm.evaluate_costs(costs, today=date(2026, 5, 5))

    assert ev.rolling_avg == 10.0
    assert ev.alert_reasons == ("rolling:31.0000>3.00x10.0000",)


def test_zero_rolling_average_does_not_alert_for_tiny_first_cost():
    ev = cost_alarm.evaluate_costs(
        {"2026-05-05": 0.001},
        today=date(2026, 5, 5),
    )

    assert ev.rolling_avg == 0.0
    assert ev.alert_reasons == ()


def test_costs_by_date_sums_duplicate_rows_and_ignores_bad_costs():
    rows = [
        {"date": "2026-05-05", "totalCost": 1.25},
        {"date": "2026-05-05", "totalCost": "2.75"},
        {"date": "2026-05-04", "totalCost": "bad"},
        {"totalCost": 9},
    ]

    assert cost_alarm.costs_by_date(rows) == {
        "2026-05-05": 4.0,
        "2026-05-04": 0.0,
    }


def test_idempotency_state_tracks_same_day_same_reason():
    ev = cost_alarm.evaluate_costs(
        {"2026-05-05": 41.0},
        today=date(2026, 5, 5),
    )
    state = {"alerts": []}

    assert cost_alarm.already_alerted(state, ev) is False
    cost_alarm.record_alert(state, ev)
    assert cost_alarm.already_alerted(state, ev) is True


def test_idempotency_ignores_same_day_cost_drift_for_rolling_alarm():
    prior_costs = {}
    for day in range(28, 31):
        prior_costs[f"2026-04-{day}"] = 0.28
    for day in range(1, 5):
        prior_costs[f"2026-05-0{day}"] = 0.28
    first = cost_alarm.evaluate_costs(
        {**prior_costs, "2026-05-05": 0.86},
        today=date(2026, 5, 5),
    )
    later = cost_alarm.evaluate_costs(
        {**prior_costs, "2026-05-05": 1.33},
        today=date(2026, 5, 5),
    )
    state = {"alerts": []}

    assert first.alert_reasons != later.alert_reasons
    cost_alarm.record_alert(state, first)

    assert cost_alarm.already_alerted(state, later) is True


def test_idempotency_preserves_escalation_when_hard_cap_joins_rolling_alarm():
    prior_costs = {}
    for day in range(28, 31):
        prior_costs[f"2026-04-{day}"] = 10.0
    for day in range(1, 5):
        prior_costs[f"2026-05-0{day}"] = 10.0
    rolling = cost_alarm.evaluate_costs(
        {**prior_costs, "2026-05-05": 31.0},
        today=date(2026, 5, 5),
    )
    hard_and_rolling = cost_alarm.evaluate_costs(
        {**prior_costs, "2026-05-05": 41.0},
        today=date(2026, 5, 5),
    )
    state = {"alerts": []}

    cost_alarm.record_alert(state, rolling)

    assert cost_alarm.alert_reason_types(hard_and_rolling) == ("hard_cap", "rolling")
    assert cost_alarm.already_alerted(state, hard_and_rolling) is False


def test_hard_cap_reason_type_is_stable_for_pause_guard():
    ev = cost_alarm.evaluate_costs(
        {"2026-05-05": 41.0},
        today=date(2026, 5, 5),
    )

    assert cost_alarm.alert_reason_types(ev) == ("hard_cap",)
