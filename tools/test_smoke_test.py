#!/usr/bin/env python3
"""Tests for smoke_test.py"""

import json
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/nous-agaas")

from smoke_test import (
    EXPECTED_MARKER,
    build_probe_message,
    format_result,
    run_outcome_probe,
    run_probe,
    run_smoke_test,
    send_telegram,
)

KZ_TZ = timezone(timedelta(hours=5))


# ── build_probe_message ───────────────────────────────────────────────────────

class TestBuildProbeMessage:
    def test_contains_marker(self):
        msg = build_probe_message()
        assert EXPECTED_MARKER in msg

    def test_contains_today_date(self):
        ts = datetime(2026, 4, 14, 10, 0, tzinfo=KZ_TZ)
        msg = build_probe_message(ts)
        assert "2026-04-14" in msg

    def test_different_dates_produce_different_messages(self):
        ts1 = datetime(2026, 4, 14, 10, 0, tzinfo=KZ_TZ)
        ts2 = datetime(2026, 4, 15, 10, 0, tzinfo=KZ_TZ)
        assert build_probe_message(ts1) != build_probe_message(ts2)

    def test_message_is_string(self):
        assert isinstance(build_probe_message(), str)

    def test_message_not_empty(self):
        assert len(build_probe_message()) > 10


# ── run_probe ─────────────────────────────────────────────────────────────────

class TestRunProbe:
    def _make_proc(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    def test_ok_when_marker_in_output(self):
        output = f"{EXPECTED_MARKER}_2026-04-14"
        with patch("subprocess.run", return_value=self._make_proc(stdout=output)):
            ok, detail = run_probe("test probe")
        assert ok is True
        assert EXPECTED_MARKER in detail

    def test_fail_when_marker_missing(self):
        with patch("subprocess.run", return_value=self._make_proc(stdout="some other text")):
            ok, detail = run_probe("test probe")
        assert ok is False
        assert "marker missing" in detail

    def test_fail_on_nonzero_exit(self):
        with patch("subprocess.run", return_value=self._make_proc(returncode=1, stderr="crash")):
            ok, detail = run_probe("test probe")
        assert ok is False
        assert "exit 1" in detail

    def test_fail_on_empty_output(self):
        with patch("subprocess.run", return_value=self._make_proc(stdout="")):
            ok, detail = run_probe("test probe")
        assert ok is False
        assert "empty" in detail

    def test_fail_on_timeout(self):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            ok, detail = run_probe("test probe")
        assert ok is False
        assert "timed out" in detail

    def test_fail_on_file_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
            ok, detail = run_probe("test probe")
        assert ok is False
        assert "not found" in detail.lower()

    def test_fail_on_generic_exception(self):
        with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
            ok, detail = run_probe("test probe")
        assert ok is False
        assert "RuntimeError" in detail

    def test_ok_returns_full_output(self):
        output = f"{EXPECTED_MARKER}_2026-04-14"
        with patch("subprocess.run", return_value=self._make_proc(stdout=output)):
            ok, detail = run_probe("test probe")
        assert detail == output

    def test_timeout_parameter_passed_to_subprocess(self):
        output = f"{EXPECTED_MARKER}_2026-04-14"
        with patch("subprocess.run", return_value=self._make_proc(stdout=output)) as mock_run:
            run_probe("test", timeout=42)
        call_kwargs = mock_run.call_args
        assert call_kwargs[1].get("timeout") == 42 or call_kwargs[0][1] == 42 or \
               any(42 == v for v in call_kwargs[1].values())


# ── format_result ─────────────────────────────────────────────────────────────

class TestFormatResult:
    def test_ok_shows_green_icon(self):
        result = format_result(ok=True, detail="SMOKE_OK_2026-04-14", duration_ms=5000)
        assert "🟢" in result

    def test_fail_shows_red_icon(self):
        result = format_result(ok=False, detail="timed out after 60s", duration_ms=60000)
        assert "🔴" in result

    def test_ok_contains_passed(self):
        result = format_result(ok=True, detail="SMOKE_OK_2026-04-14", duration_ms=5000)
        assert "PASSED" in result

    def test_fail_contains_failed(self):
        result = format_result(ok=False, detail="crash", duration_ms=100)
        assert "FAILED" in result

    def test_ok_shows_agent_reply(self):
        detail = f"{EXPECTED_MARKER}_2026-04-14"
        result = format_result(ok=True, detail=detail, duration_ms=5000)
        assert detail[:80] in result

    def test_fail_shows_reason(self):
        result = format_result(ok=False, detail="marker missing", duration_ms=100)
        assert "marker missing" in result

    def test_duration_shown(self):
        result = format_result(ok=True, detail="ok", duration_ms=3500)
        assert "3500" in result

    def test_returns_string(self):
        assert isinstance(format_result(ok=True, detail="ok", duration_ms=100), str)


# ── send_telegram ─────────────────────────────────────────────────────────────

class TestSendTelegram:
    def _mock_response(self):
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_returns_true_on_success(self):
        with patch("urllib.request.urlopen", return_value=self._mock_response()):
            result = send_telegram("hello", bot_token="TOKEN", chat_id="123")
        assert result is True

    def test_returns_false_on_error(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("refused")):
            result = send_telegram("hello", bot_token="TOKEN", chat_id="123")
        assert result is False

    def test_returns_false_if_no_token(self):
        result = send_telegram("hello", bot_token="", chat_id="123")
        assert result is False

    def test_returns_false_if_no_chat_id(self):
        result = send_telegram("hello", bot_token="TOKEN", chat_id="")
        assert result is False


# ── run_smoke_test ────────────────────────────────────────────────────────────

class TestRunSmokeTest:
    def test_returns_true_on_success(self):
        output = f"{EXPECTED_MARKER}_2026-04-14"
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = output
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc), \
             patch("smoke_test.send_telegram", return_value=True), \
             patch("smoke_test.run_outcome_probe", return_value=(True, "outcome ok")):
            ok, detail = run_smoke_test(bot_token="t", chat_id="c")
        assert ok is True

    def test_returns_false_on_failure(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "wrong output"
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc), \
             patch("smoke_test.send_telegram", return_value=True):
            ok, detail = run_smoke_test(bot_token="t", chat_id="c")
        assert ok is False

    def test_telegram_called_on_success(self):
        output = f"{EXPECTED_MARKER}_2026-04-14"
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = output
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc), \
             patch("smoke_test.send_telegram", return_value=True) as mock_tg, \
             patch("smoke_test.run_outcome_probe", return_value=(True, "outcome ok")):
            run_smoke_test(bot_token="t", chat_id="c")
        mock_tg.assert_called_once()

    def test_telegram_called_on_failure(self):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        proc.stderr = "crash"
        with patch("subprocess.run", return_value=proc), \
             patch("smoke_test.send_telegram", return_value=True) as mock_tg:
            run_smoke_test(bot_token="t", chat_id="c")
        mock_tg.assert_called_once()

    def test_ok_true_message_is_green(self):
        output = f"{EXPECTED_MARKER}_2026-04-14"
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = output
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc), \
             patch("smoke_test.send_telegram", return_value=True) as mock_tg, \
             patch("smoke_test.run_outcome_probe", return_value=(True, "outcome ok")):
            run_smoke_test(bot_token="t", chat_id="c")
        sent_text = mock_tg.call_args[0][0]
        assert "🟢" in sent_text

    def test_fail_message_is_red(self):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        proc.stderr = "crash"
        with patch("subprocess.run", return_value=proc), \
             patch("smoke_test.send_telegram", return_value=True) as mock_tg:
            run_smoke_test(bot_token="t", chat_id="c")
        sent_text = mock_tg.call_args[0][0]
        assert "🔴" in sent_text


# ── run_outcome_probe ─────────────────────────────────────────────────────────

class TestRunOutcomeProbe:
    """Unit tests for the outcome probe."""

    def _make_proc(self, stdout="", returncode=0, stderr=""):
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    def test_returns_true_when_nazel_in_output(self):
        with patch("subprocess.run", return_value=self._make_proc(stdout="Lawyer: Nazel Urist")):
            ok, detail = run_outcome_probe()
        assert ok is True
        assert "Nazel" in detail

    def test_returns_true_when_455466_in_output(self):
        with patch("subprocess.run", return_value=self._make_proc(stdout="Application #455466")):
            ok, detail = run_outcome_probe()
        assert ok is True

    def test_returns_true_when_newcab_in_output(self):
        with patch("subprocess.run", return_value=self._make_proc(stdout="forms at newcab.kazpatent.kz")):
            ok, detail = run_outcome_probe()
        assert ok is True

    def test_returns_false_when_no_marker(self):
        with patch("subprocess.run", return_value=self._make_proc(stdout="I have no information")):
            ok, detail = run_outcome_probe()
        assert ok is False
        assert "none of" in detail.lower() or "FAIL" in detail

    def test_returns_false_on_exit_error(self):
        with patch("subprocess.run", return_value=self._make_proc(stdout="", returncode=1, stderr="crash")):
            ok, detail = run_outcome_probe()
        assert ok is False
        assert "exit 1" in detail

    def test_returns_false_on_timeout(self):
        import subprocess as _subprocess
        with patch("subprocess.run", side_effect=_subprocess.TimeoutExpired("cmd", 120)):
            ok, detail = run_outcome_probe()
        assert ok is False
        assert "timed out" in detail

    def test_outcome_failure_causes_run_smoke_test_to_fail(self):
        """When outcome probe fails, run_smoke_test overall result must be False."""
        good_proc = self._make_proc(stdout=f"{EXPECTED_MARKER}_2026-04-14")
        with patch("subprocess.run", return_value=good_proc), \
             patch("smoke_test.send_telegram", return_value=True), \
             patch("smoke_test.run_outcome_probe", return_value=(False, "no Nazel in output")):
            ok, detail = run_smoke_test(bot_token="t", chat_id="c")
        assert ok is False
        assert "outcome FAIL" in detail

