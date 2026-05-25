#!/usr/bin/env python3
"""test_run_task_resilient.py — regression test for run_task_resilient + OpenClawInfraFailure.

Locks the contract:
  - infra-class RuntimeErrors ("exited 137", "timed out after", "exited 139/143")
    trigger ONE retry after retry_delay seconds
  - if retry succeeds, return result
  - if retry also fails with infra-class error → raise OpenClawInfraFailure
  - non-infra RuntimeErrors propagate immediately (no retry)
  - successful first call → no retry, return immediately

Run: python3 tools/test_run_task_resilient.py
Exits 0 on all-pass.
"""
from __future__ import annotations

import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# Stub Air-only deps so we can import run_task in CI/Mac without the runtime tree.
for mod_name in ("active_task", "context_injector_v2", "model_escalator", "tier_log"):
    if mod_name not in sys.modules:
        m = types.ModuleType(mod_name)
        if mod_name == "active_task":
            class _AT:
                def __init__(self, *a, **kw): pass
                def fail(self, *a, **kw): pass
                def complete(self, *a, **kw): pass
            m.ActiveTask = _AT
        elif mod_name == "context_injector_v2":
            m.inject_context = lambda msg, **kw: msg
            m.get_context_v2 = lambda *a, **kw: ""
            m.ContextInjector = type("_CI", (), {"__init__": lambda s, *a, **kw: None,
                                                  "inject": lambda s, msg, **kw: msg})
        elif mod_name == "model_escalator":
            class _ME:
                def __init__(self, *a, **kw): pass
                def pick_model(self, *a, **kw): return "deepseek-v4-flash"
                def record_success(self, *a, **kw): pass
                def record_failure(self, *a, **kw): pass
            m.ModelEscalator = _ME
        elif mod_name == "tier_log":
            m.log_tier = lambda *a, **kw: None
        sys.modules[mod_name] = m

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_task as rt


class _FakeHTTPResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._body


class _EscalatorDouble:
    def __init__(self, next_model="deepseek-v4-pro"):
        self.failures = []
        self.successes = []
        self.next_model = next_model

    def record_failure(self, model):
        self.failures.append(model)

    def record_success(self, model):
        self.successes.append(model)

    def pick(self):
        return self.next_model


class TestResilient(unittest.TestCase):
    def test_first_call_success_no_retry(self):
        with patch.object(rt, "run_task", return_value={"status": "ok"}) as mock:
            result = rt.run_task_resilient("test", retry_delay=0)
            self.assertEqual(result, {"status": "ok"})
            self.assertEqual(mock.call_count, 1)

    def test_infra_failure_retries_then_succeeds(self):
        responses = [RuntimeError("openclaw agent exited 137: "), {"status": "ok-on-retry"}]
        def side(*a, **kw):
            r = responses.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        with patch.object(rt, "run_task", side_effect=side) as mock:
            with patch.object(time, "sleep") as sleep_mock:
                result = rt.run_task_resilient("test", retry_delay=5)
                self.assertEqual(result, {"status": "ok-on-retry"})
                self.assertEqual(mock.call_count, 2)
                sleep_mock.assert_called_once_with(5)

    def test_infra_failure_twice_raises_OpenClawInfraFailure(self):
        with patch.object(rt, "run_task",
                          side_effect=[RuntimeError("openclaw agent exited 137: "),
                                       RuntimeError("docker exec timed out after 75s")]):
            with patch.object(time, "sleep"):
                with self.assertRaises(rt.OpenClawInfraFailure) as ctx:
                    rt.run_task_resilient("test", retry_delay=0)
                msg = str(ctx.exception)
                self.assertIn("exited 137", msg)
                self.assertIn("timed out after", msg)

    def test_non_infra_error_propagates_no_retry(self):
        with patch.object(rt, "run_task",
                          side_effect=RuntimeError("Failed to parse agent JSON output")) as mock:
            with patch.object(time, "sleep") as sleep_mock:
                with self.assertRaises(RuntimeError) as ctx:
                    rt.run_task_resilient("test", retry_delay=0)
                self.assertIn("parse", str(ctx.exception))
                self.assertNotIsInstance(ctx.exception, rt.OpenClawInfraFailure)
                self.assertEqual(mock.call_count, 1)
                sleep_mock.assert_not_called()

    def test_zero_byte_agent_stdout_recovers_from_session_jsonl(self):
        proc = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(rt.subprocess, "run", return_value=proc):
            with patch.object(rt, "_snapshot_agent_session_line_count", return_value=42):
                with patch.object(rt, "_poll_for_async_announce", return_value="RECOVERED_OK") as poll:
                    result = rt.run_task("hello", timeout=1, agent_id="grok-ceo")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["result"]["payloads"][0]["text"], "RECOVERED_OK")
        self.assertEqual(result["result"]["payloads"][0]["source"], "async-await-empty-stdout")
        poll.assert_called_once_with("grok-ceo", since_line=42, max_wait_seconds=90)

    def test_infra_then_non_infra_propagates_second(self):
        # First infra triggers retry; retry's non-infra error must NOT become OpenClawInfraFailure.
        with patch.object(rt, "run_task",
                          side_effect=[RuntimeError("openclaw agent exited 137: "),
                                       RuntimeError("Failed to parse agent JSON output")]) as mock:
            with patch.object(time, "sleep"):
                with self.assertRaises(RuntimeError) as ctx:
                    rt.run_task_resilient("test", retry_delay=0)
                self.assertNotIsInstance(ctx.exception, rt.OpenClawInfraFailure)
                self.assertIn("parse", str(ctx.exception))
                self.assertEqual(mock.call_count, 2)

    def test_all_infra_patterns_caught(self):
        for pat in ["exited 137", "exited 139", "exited 143", "timed out after 75s"]:
            with self.subTest(pattern=pat):
                with patch.object(rt, "run_task",
                                  side_effect=[RuntimeError(pat), RuntimeError(pat)]):
                    with patch.object(time, "sleep"):
                        with self.assertRaises(rt.OpenClawInfraFailure):
                            rt.run_task_resilient("test", retry_delay=0)

    def test_litellm_direct_rejects_null_message_content(self):
        body = '{"choices":[{"message":{"content":null},"finish_reason":"stop"}]}'
        with patch("urllib.request.urlopen", return_value=_FakeHTTPResponse(body)):
            with self.assertRaises(RuntimeError) as ctx:
                rt._call_litellm_direct("hello", "deepseek-v4-flash", timeout=1)

        self.assertIn("empty content", str(ctx.exception))
        self.assertIn("deepseek-v4-flash", str(ctx.exception))

    def test_direct_litellm_retries_escalated_model_after_null_content(self):
        escalator = _EscalatorDouble(next_model="deepseek-v4-pro")
        calls = []

        def fake_call(_message, model, timeout=1):
            calls.append(model)
            if model == "deepseek-v4-flash":
                raise RuntimeError("LiteLLM direct call returned empty content")
            return "CHECKPOINT_OK"

        with patch.object(rt, "_call_litellm_direct", side_effect=fake_call):
            text, model_used = rt._call_litellm_direct_with_escalation(
                "checkpoint",
                "deepseek-v4-flash",
                escalator,
                explicit_model=False,
                timeout=1,
            )

        self.assertEqual(text, "CHECKPOINT_OK")
        self.assertEqual(model_used, "deepseek-v4-pro")
        self.assertEqual(calls, ["deepseek-v4-flash", "deepseek-v4-pro"])
        self.assertEqual(escalator.failures, ["deepseek-v4-flash"])

    def test_explicit_direct_litellm_model_does_not_retry_escalation(self):
        escalator = _EscalatorDouble(next_model="deepseek-v4-pro")
        with patch.object(
            rt,
            "_call_litellm_direct",
            side_effect=RuntimeError("LiteLLM direct call returned empty content"),
        ) as mock_call:
            with self.assertRaises(RuntimeError):
                rt._call_litellm_direct_with_escalation(
                    "checkpoint",
                    "deepseek-v4-flash",
                    escalator,
                    explicit_model=True,
                    timeout=1,
                )

        self.assertEqual(mock_call.call_count, 1)
        self.assertEqual(escalator.failures, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
