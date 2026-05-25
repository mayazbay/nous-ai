#!/usr/bin/env python3
"""
tools/test_ask_grader.py — unit tests for ask_grader.py.

Covers (per spec section 2 + Lane-2 quality bar):
  T1.  Sampling math: 100% Tier-3
  T2.  Sampling math: 100% urgent-keyword (any tier)
  T3.  Sampling math: 100% Tier-2 (gbrain research path)
  T4.  Sampling math: Tier-1 ~10% within +/-3pp at N=1000 (deterministic hash)
  T5.  Sampling math: deterministic — same correlation_id always same side
  T6.  Sampling math: unknown tier → fail loud
  T7.  Sampling math: missing tier → fail loud
  T8.  Schema: valid verdict round-trips
  T9.  Schema: missing required field → SchemaError
  T10. Schema: bad category enum → SchemaError
  T11. Schema: bad quality enum → SchemaError
  T12. Schema: bad issue enum → SchemaError
  T13. Schema: confidence > 1 → SchemaError
  T14. Schema: empty reasoning → SchemaError
  T15. Cost throttle: under ceiling — no raise
  T16. Cost throttle: over ceiling — ThrottleError
  T17. Cost throttle: outside 7-day window ignored
  T18. Dedup: load_already_graded picks up existing correlation_ids
  T19. Pending: ignores turns without final_response_text
  T20. Pending: ignores already-graded turns
  T21. Pending: ignores turns outside lookback window
  T22. Pending: folds duplicate correlation_id to latest ts
  T23. End-to-end: run_once with mocked judge writes valid record
  T24. End-to-end: run_once with judge schema-error writes failure sentinel
  T25. Persistence: failure sentinel has type=judge_failure
  T26. Real LiteLLM call (only if LITELLM_MASTER_KEY env set)

Run: `python3 tools/test_ask_grader.py`
"""
from __future__ import annotations

import datetime as _dt
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import Any
from unittest import mock

# Force reimport with potentially-overridden env in tests.
if "ask_grader" in sys.modules:
    del sys.modules["ask_grader"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _fresh_module(env_overrides: dict[str, str] | None = None):
    """Import ask_grader with env overrides applied for this test."""
    saved = {}
    overrides = env_overrides or {}
    for k, v in overrides.items():
        saved[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        if "ask_grader" in sys.modules:
            del sys.modules["ask_grader"]
        return importlib.import_module("ask_grader")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _iso(dt: _dt.datetime) -> str:
    return dt.astimezone(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.mod = _fresh_module()

    def test_t1_tier3_always_sampled(self):
        for i in range(100):
            self.assertTrue(
                self.mod.should_sample(
                    tier=3, correlation_id=f"x_{i}", query_text="hello"
                ),
                f"Tier-3 must always sample (i={i})",
            )

    def test_t2_urgent_keyword_any_tier(self):
        for kw in ("urgent", "PROD is DOWN", "demo сейчас", "asap please"):
            for tier in (1, 2, 3):
                self.assertTrue(
                    self.mod.should_sample(
                        tier=tier, correlation_id="urg_1", query_text=kw
                    ),
                    f"urgent kw {kw!r} tier={tier} must sample",
                )

    def test_t3_tier2_50pct_within_3pp(self):
        # Parent decision: Tier-2 default is 50% (was 100%) to keep cost
        # ceiling defensible while still catching Tier-2 quality drift.
        # Override via GRADER_TIER2_PCT env. Deterministic via hash%100.
        N = 1000
        sampled = sum(
            1
            for i in range(N)
            if self.mod.should_sample(
                tier=2, correlation_id=f"t2_{i}", query_text="status?"
            )
        )
        rate = sampled / N
        self.assertGreaterEqual(rate, 0.47, f"Tier-2 rate {rate:.3f} < 47% (-3pp)")
        self.assertLessEqual(rate, 0.53, f"Tier-2 rate {rate:.3f} > 53% (+3pp)")

    def test_t3b_tier2_deterministic(self):
        a = self.mod.should_sample(tier=2, correlation_id="t2_777", query_text="x")
        b = self.mod.should_sample(tier=2, correlation_id="t2_777", query_text="x")
        self.assertEqual(a, b)

    def test_t3c_tier2_urgent_keyword_overrides_to_100pct(self):
        # Even at 50% sampling, urgent keyword forces 100% inclusion.
        for i in range(50):
            self.assertTrue(
                self.mod.should_sample(
                    tier=2, correlation_id=f"t2u_{i}", query_text="urgent fix"
                )
            )

    def test_t4_tier1_10pct_within_3pp(self):
        N = 1000
        sampled = sum(
            1
            for i in range(N)
            if self.mod.should_sample(
                tier=1, correlation_id=f"tg_{i}", query_text="hi"
            )
        )
        rate = sampled / N
        self.assertGreaterEqual(rate, 0.07, f"Tier-1 rate {rate:.3f} < 7% (-3pp)")
        self.assertLessEqual(rate, 0.13, f"Tier-1 rate {rate:.3f} > 13% (+3pp)")

    def test_t5_tier1_deterministic(self):
        a = self.mod.should_sample(tier=1, correlation_id="tg_777", query_text="x")
        b = self.mod.should_sample(tier=1, correlation_id="tg_777", query_text="x")
        self.assertEqual(a, b)

    def test_t6_unknown_tier_raises(self):
        with self.assertRaises(self.mod.GraderError):
            self.mod.should_sample(tier=4, correlation_id="cid", query_text="x")

    def test_t7_missing_tier_raises(self):
        with self.assertRaises(self.mod.GraderError):
            self.mod.should_sample(tier=None, correlation_id="cid", query_text="x")


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.mod = _fresh_module()
        self.good = {
            "category": "coding",
            "quality": "good",
            "issues": [],
            "confidence": 0.85,
            "reasoning": "Clear answer with command + output. Done protocol satisfied.",
        }

    def test_t8_valid_verdict_roundtrips(self):
        v = self.mod.validate_verdict(self.good)
        self.assertEqual(v["category"], "coding")
        self.assertEqual(v["quality"], "good")
        self.assertEqual(v["confidence"], 0.85)

    def test_t9_missing_field_raises(self):
        bad = dict(self.good)
        bad.pop("reasoning")
        with self.assertRaises(self.mod.SchemaError):
            self.mod.validate_verdict(bad)

    def test_t10_bad_category(self):
        bad = dict(self.good, category="philosophy")
        with self.assertRaises(self.mod.SchemaError):
            self.mod.validate_verdict(bad)

    def test_t11_bad_quality(self):
        bad = dict(self.good, quality="meh")
        with self.assertRaises(self.mod.SchemaError):
            self.mod.validate_verdict(bad)

    def test_t12_bad_issue_enum(self):
        bad = dict(self.good, issues=["fabrication"])
        with self.assertRaises(self.mod.SchemaError):
            self.mod.validate_verdict(bad)

    def test_t13_confidence_out_of_range(self):
        bad = dict(self.good, confidence=1.5)
        with self.assertRaises(self.mod.SchemaError):
            self.mod.validate_verdict(bad)

    def test_t14_empty_reasoning(self):
        bad = dict(self.good, reasoning="   ")
        with self.assertRaises(self.mod.SchemaError):
            self.mod.validate_verdict(bad)

    def test_t14b_known_issue_enums_accepted(self):
        ok = dict(self.good, issues=["incomplete", "no_done_protocol"])
        v = self.mod.validate_verdict(ok)
        self.assertIn("incomplete", v["issues"])


class CostThrottleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        self.tmp.close()
        self.mod = _fresh_module({"GRADER_COST_CEILING_7D": "10.50"})

    def tearDown(self):
        os.unlink(self.tmp.name)

    def _write(self, lines):
        with open(self.tmp.name, "w") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")

    def test_t15_under_ceiling_no_raise(self):
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        self._write(
            [
                {"ts": _iso(now), "correlation_id": "a", "grader_cost_est": 1.0},
                {"ts": _iso(now), "correlation_id": "b", "grader_cost_est": 2.0},
            ]
        )
        with mock.patch.object(self.mod, "ASK_GRADER_LOG", self.tmp.name):
            self.mod.assert_within_budget(self.tmp.name)  # no raise

    def test_t16_over_ceiling_raises(self):
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        self._write(
            [
                {"ts": _iso(now), "correlation_id": "a", "grader_cost_est": 6.0},
                {"ts": _iso(now), "correlation_id": "b", "grader_cost_est": 5.0},
            ]
        )
        with self.assertRaises(self.mod.ThrottleError):
            self.mod.assert_within_budget(self.tmp.name)

    def test_t17_outside_7d_window_ignored(self):
        old = _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=10)
        self._write(
            [
                {"ts": _iso(old), "correlation_id": "a", "grader_cost_est": 50.0},
            ]
        )
        # Should not raise — old cost outside window.
        self.mod.assert_within_budget(self.tmp.name)


class DedupAndPendingTests(unittest.TestCase):
    def setUp(self):
        self.mod = _fresh_module()
        self.tmpdir = tempfile.mkdtemp()
        self.hier = os.path.join(self.tmpdir, "ask-hierarchy.jsonl")
        self.grad = os.path.join(self.tmpdir, "ask-grader.jsonl")

    def tearDown(self):
        for p in (self.hier, self.grad):
            if os.path.exists(p):
                os.unlink(p)
        os.rmdir(self.tmpdir)

    def _write(self, path, rows):
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def test_t18_load_already_graded_picks_cids(self):
        self._write(
            self.grad,
            [
                {"correlation_id": "cid_a", "ts": "2026-04-30T10:00:00Z"},
                {"correlation_id": "cid_b", "ts": "2026-04-30T10:01:00Z"},
            ],
        )
        seen = self.mod.load_already_graded(self.grad)
        self.assertEqual(seen, {"cid_a", "cid_b"})

    def test_t19_pending_ignores_no_response(self):
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        self._write(
            self.hier,
            [
                {
                    "ts": _iso(now),
                    "correlation_id": "cid_x",
                    "tier": 1,
                    "query_text": "hi",
                    # no final_response_text
                },
            ],
        )
        pending = self.mod.collect_pending(
            hierarchy_log=self.hier, grader_log=self.grad
        )
        self.assertEqual(pending, [])

    def test_t20_pending_ignores_already_graded(self):
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        self._write(
            self.hier,
            [
                {
                    "ts": _iso(now),
                    "correlation_id": "cid_dup",
                    "tier": 3,
                    "final_response_text": "answer",
                },
            ],
        )
        self._write(
            self.grad,
            [
                {"correlation_id": "cid_dup", "ts": _iso(now), "grader_cost_est": 0.01},
            ],
        )
        pending = self.mod.collect_pending(
            hierarchy_log=self.hier, grader_log=self.grad
        )
        self.assertEqual(pending, [])

    def test_t21_pending_ignores_outside_lookback(self):
        old = _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(hours=2)
        self._write(
            self.hier,
            [
                {
                    "ts": _iso(old),
                    "correlation_id": "cid_old",
                    "tier": 3,
                    "final_response_text": "answer",
                },
            ],
        )
        pending = self.mod.collect_pending(
            hierarchy_log=self.hier, grader_log=self.grad, lookback_minutes=15
        )
        self.assertEqual(pending, [])

    def test_t22_pending_folds_to_latest_ts(self):
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        self._write(
            self.hier,
            [
                {
                    "ts": _iso(now - _dt.timedelta(minutes=10)),
                    "correlation_id": "cid_fold",
                    "tier": 1,
                    "model": "old",
                    "final_response_text": "early",
                },
                {
                    "ts": _iso(now - _dt.timedelta(minutes=2)),
                    "correlation_id": "cid_fold",
                    "tier": 1,
                    "model": "new",
                    "final_response_text": "later",
                },
            ],
        )
        pending = self.mod.collect_pending(
            hierarchy_log=self.hier, grader_log=self.grad
        )
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["model"], "new")


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.mod = _fresh_module({"LITELLM_MASTER_KEY": "test-key"})
        self.tmpdir = tempfile.mkdtemp()
        self.hier = os.path.join(self.tmpdir, "ask-hierarchy.jsonl")
        self.grad = os.path.join(self.tmpdir, "ask-grader.jsonl")
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        with open(self.hier, "w") as f:
            f.write(
                json.dumps(
                    {
                        "ts": _iso(now),
                        "correlation_id": "tg_42",
                        "tier": 3,
                        "model": "opus",
                        "query_text": "What is 2+2?",
                        "final_response_text": "4",
                        "latency_ms": 800,
                        "cost_est": 0.001,
                    }
                )
                + "\n"
            )
        # Repoint module-level constants for this test.
        self.mod.ASK_HIERARCHY_LOG = self.hier
        self.mod.ASK_GRADER_LOG = self.grad

    def tearDown(self):
        for p in (self.hier, self.grad):
            if os.path.exists(p):
                os.unlink(p)
        os.rmdir(self.tmpdir)

    def test_t23_run_once_writes_valid_record(self):
        good_verdict = {
            "category": "research",
            "quality": "good",
            "issues": [],
            "confidence": 0.9,
            "reasoning": "Direct factual answer matching the query.",
        }
        usage = {"prompt_tokens": 100, "completion_tokens": 30}

        def fake_call_judge(turn, **kwargs):
            return good_verdict, usage

        with mock.patch.object(self.mod, "call_judge", side_effect=fake_call_judge):
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(io.StringIO()):
                counters = self.mod.run_once()
        self.assertEqual(counters["graded"], 1)
        self.assertEqual(counters["failed"], 0)
        with open(self.grad) as f:
            rec = json.loads(f.readline())
        self.assertEqual(rec["correlation_id"], "tg_42")
        self.assertEqual(rec["quality_v1"], "good")
        self.assertEqual(rec["category"], "research")
        self.assertEqual(rec["schema"], "grader.v1")
        self.assertEqual(rec["judge_tokens_in"], 100)
        self.assertGreater(rec["grader_cost_est"], 0)

    def test_t24_run_once_writes_failure_on_schema_error(self):
        def fake_bad_call_judge(turn, **kwargs):
            return {"category": "WAT"}, {}

        with mock.patch.object(
            self.mod, "call_judge", side_effect=fake_bad_call_judge
        ):
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(io.StringIO()):
                counters = self.mod.run_once()
        self.assertEqual(counters["graded"], 0)
        self.assertEqual(counters["failed"], 1)
        with open(self.grad) as f:
            rec = json.loads(f.readline())
        self.assertEqual(rec["type"], "judge_failure")
        self.assertEqual(rec["correlation_id"], "tg_42")

    def test_t25_persist_failure_sentinel(self):
        self.mod.persist_failure(
            correlation_id="tg_99",
            reason="explicit test",
            grader_log=self.grad,
        )
        with open(self.grad) as f:
            rec = json.loads(f.readline())
        self.assertEqual(rec["type"], "judge_failure")
        self.assertEqual(rec["correlation_id"], "tg_99")
        self.assertEqual(rec["reason"], "explicit test")
        self.assertEqual(rec["schema"], "grader.v1")


@unittest.skipUnless(
    os.environ.get("LITELLM_MASTER_KEY") and os.environ.get("GRADER_LIVE_E2E"),
    "live e2e disabled (set LITELLM_MASTER_KEY + GRADER_LIVE_E2E=1 to run)",
)
class LiveLiteLLMTest(unittest.TestCase):
    def test_t26_real_judge_call(self):
        mod = _fresh_module()
        turn = {
            "correlation_id": "live_test_1",
            "tier": 3,
            "model": "opus",
            "query_text": "What is 2+2? Reply with just the number.",
            "final_response_text": "4",
        }
        verdict_raw, usage = mod.call_judge(turn)
        v = mod.validate_verdict(verdict_raw)
        self.assertIn(v["quality"], mod.ALLOWED_QUALITY)
        self.assertGreater(usage.get("prompt_tokens", 0), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
