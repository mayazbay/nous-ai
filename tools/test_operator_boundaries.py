import os
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(ROOT))

cost_tracker_stub = types.ModuleType("cost_tracker")
cost_tracker_stub.daily_report = lambda: {}
cost_tracker_stub.format_report = lambda report: "report"
sys.modules.setdefault("cost_tracker", cost_tracker_stub)

factory_health_stub = types.ModuleType("factory_health")
factory_health_stub.run_checks = lambda: []
factory_health_stub._load_extra_envs = lambda: None
sys.modules.setdefault("factory_health", factory_health_stub)

# test_telegram_poll.py installs a lightweight command_center stub for poller
# import tests. Pytest collection can import that module before this one, so
# remove the stub here before these tests assert the real command router.
_existing_command_center = sys.modules.get("command_center")
if _existing_command_center is not None and not hasattr(_existing_command_center, "_run_codex"):
    sys.modules.pop("command_center", None)

import command_center as cc


ALMATY = ZoneInfo("Asia/Almaty")
_FAILOVER_PATCHERS = []


def setUpModule():
    # These tests exercise Telegram routing decisions. They must never write the
    # production model-failover ledger just because command_center starts an
    # /ask failover event around the mocked worker call.
    for patcher in (
        patch("command_center._failover_start", return_value="test-failover-event"),
        patch("command_center._failover_finish", return_value=None),
    ):
        patcher.start()
        _FAILOVER_PATCHERS.append(patcher)


def tearDownModule():
    while _FAILOVER_PATCHERS:
        _FAILOVER_PATCHERS.pop().stop()


class GroupAddresseeGuardTests(unittest.TestCase):
    def test_group_sender_context_is_extracted_from_prompt(self):
        text = (
            "/ask Telegram group sender @aliakbar_asylbek: if you greet anyone, greet @aliakbar_asylbek "
            "or use Коллеги; do not greet another person from surrounding context. Message: ты видишь камеру?"
        )

        self.assertEqual(cc._extract_group_sender_context(text), "@aliakbar_asylbek")

    def test_stale_group_salutation_is_neutralized(self):
        old_sender = cc._CURRENT_GROUP_SENDER
        try:
            cc._CURRENT_GROUP_SENDER = "@aliakbar_asylbek"

            text = cc._neutralize_stale_group_salutation(-100123, "Денис, приняли. Endpoint ниже.")

            self.assertEqual(text, "Коллеги, приняли. Endpoint ниже.")
        finally:
            cc._CURRENT_GROUP_SENDER = old_sender

    def test_current_group_sender_salutation_is_allowed(self):
        old_sender = cc._CURRENT_GROUP_SENDER
        try:
            cc._CURRENT_GROUP_SENDER = "@aliakbar_asylbek"

            text = cc._neutralize_stale_group_salutation(-100123, "Асылбек, проверяем доступ.")

            self.assertEqual(text, "Асылбек, проверяем доступ.")
        finally:
            cc._CURRENT_GROUP_SENDER = old_sender

    @patch.dict(os.environ, {"AUTONOMY_BYPASS": "1"})
    @patch("command_center.urllib.request.urlopen")
    def test_tg_send_neutralizes_stale_group_salutation_before_api(self, mock_urlopen):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"ok": true, "result": {"message_id": 123}}'

        old_sender = cc._CURRENT_GROUP_SENDER
        mock_urlopen.return_value = FakeResponse()
        try:
            cc._CURRENT_GROUP_SENDER = "@aliakbar_asylbek"

            sent = cc._tg_send("token", -100123, "Денис, приняли. Endpoint ниже.", reply_to=1750)

            self.assertTrue(sent)
            req = mock_urlopen.call_args[0][0]
            payload = cc.urllib.parse.parse_qs(req.data.decode("utf-8"))
            self.assertEqual(payload["text"], ["Коллеги, приняли. Endpoint ниже."])
            self.assertEqual(payload["reply_to_message_id"], ["1750"])
        finally:
            cc._CURRENT_GROUP_SENDER = old_sender


class OperatorBoundaryDecisionTests(unittest.TestCase):
    def test_quiet_hours_hold_nonurgent_llm_work(self):
        now = datetime(2026, 4, 27, 1, 0, tzinfo=ALMATY)
        decision, reason = cc._operator_boundary_decision("/ask plan content calendar", now=now)
        self.assertEqual(decision, "hold_for_morning")
        self.assertIn("quiet hours", reason)

    def test_quiet_hours_bypass_for_urgent_work(self):
        now = datetime(2026, 4, 27, 1, 0, tzinfo=ALMATY)
        decision, reason = cc._operator_boundary_decision("/ask prod camera path is down now", now=now)
        self.assertEqual(decision, "escalate_urgent")
        self.assertIn("urgent", reason)

    def test_daytime_responds_normally(self):
        now = datetime(2026, 4, 27, 10, 0, tzinfo=ALMATY)
        decision, reason = cc._operator_boundary_decision("/ask plan content calendar", now=now)
        self.assertEqual(decision, "respond_now")
        self.assertIn("outside", reason)


class StatusCommandTests(unittest.TestCase):
    @patch("command_center.shutil.which", return_value=None)
    @patch("platform.system", return_value="Darwin")
    @patch("command_center.subprocess.run")
    def test_status_uses_absolute_macos_memory_tools_when_launchd_path_is_minimal(self, mock_run, _mock_system, _mock_which):
        def fake_run(args, **_kwargs):
            if args[0] == "docker":
                return types.SimpleNamespace(returncode=0, stdout="openclaw\tUp 2 days\n", stderr="")
            if args[0] == "/bin/df":
                return types.SimpleNamespace(
                    returncode=0,
                    stdout="Filesystem Size Used Avail Capacity iused ifree %iused Mounted on\n/dev/disk 460Gi 12Gi 448Gi 3% 0 0 0% /\n",
                    stderr="",
                )
            if args[0] == "/usr/sbin/sysctl":
                return types.SimpleNamespace(returncode=0, stdout="25769803776\n", stderr="")
            if args[0] == "/usr/bin/vm_stat":
                return types.SimpleNamespace(
                    returncode=0,
                    stdout=(
                        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
                        "Pages active: 10.\n"
                        "Pages inactive: 5.\n"
                        "Pages wired down: 20.\n"
                    ),
                    stderr="",
                )
            raise AssertionError(f"unexpected command: {args}")

        mock_run.side_effect = fake_run

        text = cc._run_status()

        self.assertIn("Memory:", text)
        self.assertNotIn("memory error", text)
        commands = [call_args[0][0][0] for call_args in mock_run.call_args_list]
        self.assertIn("/usr/sbin/sysctl", commands)
        self.assertIn("/usr/bin/vm_stat", commands)

    @patch("command_center._run_status", return_value="ok")
    @patch("command_center._tg_send", return_value=True)
    def test_status_waiting_message_names_factory_not_vps(self, mock_send, _mock_status):
        handled = cc.handle("token", 110793056, 77, "/status")

        self.assertTrue(handled)
        first_text = mock_send.call_args_list[0][0][2]
        self.assertIn("factory health", first_text)
        self.assertNotIn("VPS health", first_text)


class OperatorBoundaryQueueTests(unittest.TestCase):
    def test_queue_write_is_flat_and_contains_source(self):
        now = datetime(2026, 4, 27, 1, 5, tzinfo=ALMATY)
        with tempfile.TemporaryDirectory() as tmp:
            old_wiki = os.environ.get("NOUS_WIKI")
            old_commit = os.environ.get("NOUS_BOUNDARY_COMMIT")
            os.environ["NOUS_WIKI"] = tmp
            os.environ["NOUS_BOUNDARY_COMMIT"] = "0"
            try:
                rel = cc._append_boundary_queue(
                    "/ask research speculative idea",
                    chat_id=110793056,
                    msg_id=42,
                    reason="quiet hours 00:30-08:00 Asia/Almaty",
                    now=now,
                )
                self.assertEqual(rel, "pages/personal/boundary-queue-2026-04-27.md")
                path = Path(tmp) / rel
                self.assertTrue(path.exists())
                body = path.read_text()
                self.assertIn("telegram chat=110793056 msg=42", body)
                self.assertIn("/ask research speculative idea", body)
            finally:
                if old_wiki is None:
                    os.environ.pop("NOUS_WIKI", None)
                else:
                    os.environ["NOUS_WIKI"] = old_wiki
                if old_commit is None:
                    os.environ.pop("NOUS_BOUNDARY_COMMIT", None)
                else:
                    os.environ["NOUS_BOUNDARY_COMMIT"] = old_commit

    @patch("command_center._run_openclaw")
    @patch("command_center._tg_send", return_value=True)
    def test_handle_holds_nonurgent_ask_without_running_openclaw(self, mock_send, mock_run):
        now = datetime(2026, 4, 27, 1, 15, tzinfo=ALMATY)
        with tempfile.TemporaryDirectory() as tmp:
            old_wiki = os.environ.get("NOUS_WIKI")
            old_commit = os.environ.get("NOUS_BOUNDARY_COMMIT")
            os.environ["NOUS_WIKI"] = tmp
            os.environ["NOUS_BOUNDARY_COMMIT"] = "0"
            try:
                with patch("command_center._now_almaty", return_value=now):
                    handled = cc.handle("token", 110793056, 99, "/ask research three business ideas")
                self.assertTrue(handled)
                mock_run.assert_not_called()
                self.assertTrue(mock_send.called)
                sent_text = mock_send.call_args[0][2]
                self.assertIn("saved this for morning", sent_text)
            finally:
                if old_wiki is None:
                    os.environ.pop("NOUS_WIKI", None)
                else:
                    os.environ["NOUS_WIKI"] = old_wiki
                if old_commit is None:
                    os.environ.pop("NOUS_BOUNDARY_COMMIT", None)
                else:
                    os.environ["NOUS_BOUNDARY_COMMIT"] = old_commit

    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_ask_tier_ceo_rejects_non_madi_without_model_call(
        self, mock_send, mock_codex, mock_openclaw
    ):
        now = datetime(2026, 5, 20, 14, 0, tzinfo=ALMATY)

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", -1002064137259, 1801, "/ask --tier ceo should we spend?")

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        mock_openclaw.assert_not_called()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertTrue(any("Madi DM only" in text for text in sent_texts))

    @patch("command_center._write_telegram_task_result_receipt", return_value="pages/task-results/tg_1802.md")
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex", return_value="codex subscription answer")
    @patch("command_center._tg_send", return_value=True)
    def test_ask_tier_ceo_is_codex_first_and_not_openclaw(
        self, mock_send, mock_codex, mock_openclaw, _mock_receipt
    ):
        now = datetime(2026, 5, 20, 14, 0, tzinfo=ALMATY)

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1802, "/ask --tier ceo decide the architecture")

        self.assertTrue(handled)
        mock_codex.assert_called_once_with("decide the architecture")
        mock_openclaw.assert_not_called()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertTrue(any("Codex GPT-5.5 subscription-first" in text for text in sent_texts))
        self.assertTrue(any("Opus API disabled by default" in text for text in sent_texts))

    @patch("command_center._run_openclaw", return_value="cheap worker answer")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_ask_tier_cheap_uses_local_mlx_route_and_never_codex_grok_or_opus(
        self, mock_send, mock_codex, mock_openclaw
    ):
        now = datetime(2026, 5, 20, 14, 0, tzinfo=ALMATY)

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1803, "/ask --tier cheap summarize inbox")

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        mock_openclaw.assert_called_once()
        args, kwargs = mock_openclaw.call_args
        self.assertEqual(args[0], "summarize inbox")
        self.assertEqual(kwargs.get("model"), "local-mlx-coder")
        self.assertIsNone(kwargs.get("agent_id"))
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        joined = "\n".join(sent_texts)
        self.assertIn("MLX/DeepSeek cheap tier", joined)
        self.assertNotIn("Codex", joined)
        self.assertNotIn("Grok", joined)
        self.assertNotIn("Opus", joined)

    @patch("command_center._fetch_satory_event_intake_snapshot")
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_satory_event_visibility_query_bypasses_models_and_reports_api_snapshot(
        self, mock_send, mock_codex, mock_openclaw, mock_fetch
    ):
        mock_fetch.return_value = (
            {
                "total": 281,
                "online": 0,
                "stale": 38,
                "data_freshness": {
                    "events_last_seen": "2026-05-20T16:37:08.165+05:00",
                    "events_age_seconds": 282,
                    "events_recent_count": 1,
                    "poll_last_run": "2026-05-20T16:40:37.009322",
                },
            },
            "",
        )
        query = (
            "/ask Telegram group sender @aliakbar_asylbek: if you greet anyone, greet @aliakbar_asylbek "
            "or use Коллеги; do not greet another person from surrounding context. "
            "Message: видишь события? поток подали"
        )

        handled = cc.handle("token", -1002064137259, 1802, query)

        self.assertTrue(handled)
        mock_fetch.assert_called_once()
        mock_codex.assert_not_called()
        mock_openclaw.assert_not_called()
        sent_text = mock_send.call_args[0][2]
        self.assertIn("Вижу свежие события", sent_text)
        self.assertIn("events_last_seen=2026-05-20T16:37:08.165+05:00", sent_text)
        self.assertIn("В ЕРАП не отправляю", sent_text)

    @patch("command_center._fetch_satory_event_intake_snapshot")
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_short_satory_event_visibility_question_uses_local_api_not_codex_cap_path(
        self, mock_send, mock_codex, mock_openclaw, mock_fetch
    ):
        mock_fetch.return_value = (
            {
                "total": 281,
                "online": 0,
                "stale": 38,
                "data_freshness": {
                    "events_last_seen": "2026-05-20T16:47:26.762+05:00",
                    "events_age_seconds": 581,
                    "events_recent_count": 1,
                    "poll_last_run": "2026-05-20T16:55:37.231817",
                },
            },
            "",
        )
        query = (
            "/ask Telegram group sender @aliakbar_asylbek: if you greet anyone, "
            "greet @aliakbar_asylbek or use Коллеги; do not greet another person "
            "from surrounding context. Message: Видишь события?"
        )

        handled = cc.handle("token", -1002064137259, 1803, query)

        self.assertTrue(handled)
        mock_fetch.assert_called_once()
        mock_codex.assert_not_called()
        mock_openclaw.assert_not_called()
        sent_text = mock_send.call_args[0][2]
        self.assertIn("Вижу свежие события", sent_text)
        self.assertIn("В ЕРАП не отправляю", sent_text)
        self.assertNotIn("Daily /codex token cap", sent_text)
        self.assertNotIn("mandatory /codex only", sent_text)

    def test_group_internal_codex_error_sanitizer_returns_russian_reply(self):
        text = (
            "🔴 This request is mandatory /codex only.\n"
            "Daily /codex token cap reached: 312163 / 250000 observed tokens.\n"
            "No answer was generated by the cheap worker route."
        )

        sanitized = cc._sanitize_group_internal_error_reply(-1002064137259, text)

        self.assertIn("Коллеги", sanitized)
        self.assertIn("Codex сейчас недоступен", sanitized)
        self.assertNotIn("mandatory /codex only", sanitized)
        self.assertNotIn("No answer was generated", sanitized)

    @patch("command_center._fetch_satory_event_intake_snapshot")
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_satory_route_configured_question_reports_stale_intake_without_openclaw_guess(
        self, mock_send, mock_codex, mock_openclaw, mock_fetch
    ):
        mock_fetch.return_value = (
            {
                "total": 281,
                "online": 0,
                "stale": 38,
                "data_freshness": {
                    "events_last_seen": "2026-04-05T22:08:05.856+05:00",
                    "events_age_seconds": 3880000,
                    "events_recent_count": 0,
                    "poll_last_run": "2026-05-20T14:57:55",
                },
            },
            "",
        )
        query = (
            "/ask Telegram group sender @aliakbar_asylbek: if you greet anyone, greet @aliakbar_asylbek "
            "or use Коллеги; do not greet another person from surrounding context. "
            "Message: Что вилишь? Маршрут настроили"
        )

        handled = cc.handle("token", -1002064137259, 1797, query)

        self.assertTrue(handled)
        mock_fetch.assert_called_once()
        mock_codex.assert_not_called()
        mock_openclaw.assert_not_called()
        sent_text = mock_send.call_args[0][2]
        self.assertIn("Пока не вижу свежих событий", sent_text)
        self.assertIn("2026-04-05T22:08:05.856+05:00", sent_text)
        self.assertNotIn("wg-satory", sent_text)

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 0.0))
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex", return_value="codex verified")
    @patch("command_center._tg_send", return_value=True)
    def test_shell_verification_ask_auto_escalates_to_codex(self, mock_send, mock_codex, mock_openclaw, _mock_budget):
        now = datetime(2026, 5, 14, 15, 20, tzinfo=ALMATY)
        task = (
            "/ask VERIFY:\n"
            "Run exact commands and save outputs:\n"
            "- ssh air reachability and HEAD\n"
            "- launchctl checks\n"
            "- python3 -m pytest tools/test_telegram_poll.py"
        )
        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1451, task)

        self.assertTrue(handled)
        mock_openclaw.assert_not_called()
        mock_codex.assert_called_once()
        self.assertIn("ssh air reachability", mock_codex.call_args[0][0])
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertTrue(any("Auto-escalating" in text and "/codex" in text for text in sent_texts))

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 1.25))
    @patch("command_center._run_openclaw", return_value="grok decision")
    @patch("command_center._run_codex", return_value="codex high judgment")
    @patch("command_center._tg_send", return_value=True)
    def test_decision_prompt_routes_to_grok_first_pass_before_codex(
        self, mock_send, mock_codex, mock_openclaw, _mock_budget
    ):
        now = datetime(2026, 5, 14, 15, 25, tzinfo=ALMATY)
        query = (
            "Before coding, do deep analysis and compare the architecture options "
            "for routing routine work while keeping traffic cheap. "
            * 6
        )
        self.assertGreater(len(query), 500)
        self.assertLess(len(query), 1800)

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1452, "/ask " + query)

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        mock_openclaw.assert_called_once()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertTrue(any("grok-ceo first pass" in text for text in sent_texts))

    @patch("command_center._codex_daily_budget_ok", return_value=(False, 5.01))
    @patch("command_center._run_openclaw", return_value="openclaw response")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_high_judgment_ask_falls_back_to_openclaw_when_codex_budget_spent(
        self, _mock_send, mock_codex, mock_openclaw, _mock_budget
    ):
        now = datetime(2026, 5, 14, 15, 30, tzinfo=ALMATY)
        query = (
            "Do deep analysis and explain why the root cause matters before automation. "
            "Use careful engineering discipline. "
            * 8
        )

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1453, "/ask " + query)

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        mock_openclaw.assert_called_once()

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 0.50))
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex", return_value="codex executed")
    @patch("command_center._tg_send", return_value=True)
    def test_bounded_execution_ask_routes_to_chatgpt_codex(self, mock_send, mock_codex, mock_openclaw, _mock_budget):
        now = datetime(2026, 5, 15, 10, 30, tzinfo=ALMATY)

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1501, "/ask Fix the Todoist source comment audit and verify it.")

        self.assertTrue(handled)
        mock_openclaw.assert_not_called()
        mock_codex.assert_called_once()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertTrue(any("ChatGPT/Codex GPT-5.5 subscription" in text for text in sent_texts))

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 0.00))
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex", return_value="codex drafted apk erap answer")
    @patch("command_center._tg_send", return_value=True)
    def test_short_satory_apk_erap_external_query_routes_to_codex(
        self, mock_send, mock_codex, mock_openclaw, _mock_budget
    ):
        now = datetime(2026, 5, 18, 13, 40, tzinfo=ALMATY)
        query = "from asyl: Мади кстати как у тебя ПО работает с Апк? фиксирует что-то?"

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1655, "/ask " + query)

        self.assertTrue(handled)
        mock_openclaw.assert_not_called()
        mock_codex.assert_called_once()
        self.assertIn("Апк", mock_codex.call_args[0][0])
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertTrue(any("ChatGPT/Codex GPT-5.5 subscription" in text for text in sent_texts))

    @patch("command_center._codex_daily_budget_ok", return_value=(False, 0.00))
    @patch("command_center._run_openclaw", return_value="grok-ceo answered the satory query")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_mandatory_satory_proof_falls_back_to_grok_with_russian_notice_in_group(
        self, mock_send, mock_codex, mock_openclaw, _mock_budget
    ):
        """AP-41 (supersedes AP-30 for user-facing replies): when mandatory
        codex is capped in a GROUP chat, fall back to grok-ceo with a Russian
        notice instead of bouncing English wall-of-text."""
        now = datetime(2026, 5, 20, 15, 43, tzinfo=ALMATY)
        query = "from asyl: Мади кстати как у тебя ПО работает с Апк? фиксирует что-то?"

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", -1002064137259, 1802, "/ask " + query)

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        # AP-41: grok-ceo IS called as fallback
        mock_openclaw.assert_called_once()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        # Russian fallback notice for group chats
        self.assertTrue(any("Codex недоступен" in text for text in sent_texts), sent_texts)
        self.assertTrue(any("Использую grok-ceo Tier-1" in text for text in sent_texts), sent_texts)
        # NEVER relay the old AP-30 English wall-of-text
        self.assertFalse(any("mandatory /codex only" in text for text in sent_texts), sent_texts)
        self.assertFalse(any("No answer was generated" in text for text in sent_texts), sent_texts)

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 0.00))
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex", return_value="codex checked camera access")
    @patch("command_center._tg_react", return_value=True)
    @patch("command_center._tg_send", return_value=True)
    def test_satory_var_camera_access_query_routes_to_codex(
        self, mock_send, mock_react, mock_codex, mock_openclaw, _mock_budget
    ):
        now = datetime(2026, 5, 18, 15, 10, tzinfo=ALMATY)
        query = (
            "Telegram group sender @aliakbar_asylbek: if you greet anyone, greet @aliakbar_asylbek or use Коллеги; "
            "do not greet another person from surrounding context. Message: "
            "стоп, на ЛУ 100 рядом повесили Вар с радаром. "
            "ты видишь эту камеру? есть ли доступ у тебя к этой камере"
        )

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", -1002064137259, 1750, "/ask " + query)

        self.assertTrue(handled)
        mock_openclaw.assert_not_called()
        mock_codex.assert_called_once()
        mock_react.assert_called()
        self.assertIn("видишь эту камеру", mock_codex.call_args[0][0])
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertEqual(sent_texts, ["codex checked camera access"])

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 0.00))
    @patch("command_center._run_openclaw")
    @patch(
        "command_center._run_codex",
        return_value=(
            "Асылбек, логин/пароль не публикую в общий чат. Передайте доступ безопасно ответственному.\n\n"
            "—\nOpenAI Codex gpt-5.5 via subscription | tokens: 123 | today: 1/12 calls | observed tokens: 123/250000"
        ),
    )
    @patch("command_center._tg_react", create=True, return_value=True)
    @patch("command_center._tg_send", return_value=True)
    def test_group_codex_route_uses_reaction_and_hides_internal_footer(
        self, mock_send, mock_react, mock_codex, mock_openclaw, _mock_budget
    ):
        now = datetime(2026, 5, 19, 16, 2, tzinfo=ALMATY)
        query = (
            "Telegram group sender @aliakbar_asylbek: if you greet anyone, greet @aliakbar_asylbek or use Коллеги; "
            "do not greet another person from surrounding context. Message: "
            "стоп, на ЛУ 100 рядом повесили Вар с радаром. ты видишь эту камеру? есть ли доступ у тебя к этой камере"
        )

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", -1002064137259, 1764, "/ask " + query)

        self.assertTrue(handled)
        mock_openclaw.assert_not_called()
        mock_codex.assert_called_once()
        mock_react.assert_called()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertEqual(len(sent_texts), 1)
        self.assertIn("Асылбек", sent_texts[0])
        self.assertNotIn("Routing bounded execution", sent_texts[0])
        self.assertNotIn("OpenAI Codex", sent_texts[0])
        self.assertNotIn("tokens:", sent_texts[0])

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 0.00))
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex")
    @patch("command_center._tg_react", create=True, return_value=True)
    @patch("command_center._tg_send", return_value=True)
    def test_group_credential_request_routes_to_owner_handoff_before_codex(
        self, mock_send, mock_react, mock_codex, mock_openclaw, _mock_budget
    ):
        now = datetime(2026, 5, 19, 16, 2, tzinfo=ALMATY)
        query = (
            "Telegram group sender @aliakbar_asylbek: if you greet anyone, greet @aliakbar_asylbek or use Коллеги; "
            "do not greet another person from surrounding context. Message: "
            "с этой группе можешь писать. дай мне логин и пароль для отправки нарушения в ЕРАП. давно уже давал такую информацию"
        )

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", -1002064137259, 1764, "/ask " + query)

        self.assertTrue(handled)
        mock_openclaw.assert_not_called()
        mock_codex.assert_not_called()
        mock_react.assert_called_once_with("token", -1002064137259, 1764)
        sent = [(call.args[1], call.args[2]) for call in mock_send.call_args_list]
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0][0], -1002064137259)
        self.assertIn("Передано владельцу", sent[0][1])
        self.assertNotIn("кому именно", sent[0][1])
        self.assertEqual(sent[1][0], 110793056)
        self.assertIn("[OWNER-ONLY: forward to operator]", sent[1][1])
        self.assertIn("@aliakbar_asylbek", sent[1][1])
        self.assertIn("логин и пароль", sent[1][1])

    @patch("command_center._tg_react", create=True, return_value=True)
    @patch("command_center._tg_send", return_value=True)
    def test_owner_credential_handoff_never_echoes_group_env_config(self, mock_send, mock_react):
        """Non-owner sender posts credential-shaped text in group:
        group gets sanitized decline, owner gets full raw context to act."""
        body = (
            "test: ExampleTestSecret_123!\n"
            "prod: ExampleProdSecret_456!\n"
            "Public IP: 65.108.215.200\n"
            "Порт: 443\n"
            "Протокол: HTTPS\n"
            "Чекбокс: вне ЕТС ГО\n\n"
            "нужно точно также, но уже не для теста и продуктивная среда"
        )

        handled = cc.handle_owner_credential_handoff(
            "token",
            -1002064137259,
            1767,
            body,
            "@aliakbar_asylbek",  # AP-43: non-owner sender triggers owner-DM relay
            owner_chat_id=110793056,
        )

        self.assertTrue(handled)
        mock_react.assert_called_once_with("token", -1002064137259, 1767)
        group_reply = mock_send.call_args_list[0].args[2]
        owner_dm = mock_send.call_args_list[1].args[2]
        self.assertIn("Передано владельцу", group_reply)
        self.assertNotIn("ExampleTestSecret_123!", group_reply)
        self.assertNotIn("ExampleProdSecret_456!", group_reply)
        self.assertNotIn("Public IP", group_reply)
        self.assertNotIn("Порт", group_reply)
        self.assertIn("ExampleTestSecret_123!", owner_dm)
        self.assertIn("ExampleProdSecret_456!", owner_dm)
        self.assertIn("Public IP: 65.108.215.200", owner_dm)

    @patch("command_center._tg_react", create=True, return_value=True)
    @patch("command_center._tg_send", return_value=True)
    def test_ap43_owner_sender_skips_owner_dm_echo(self, mock_send, mock_react):
        """AP-43: when sender IS the owner, the bot must NOT DM the owner a
        copy of their own message. Group reply still goes out (shorter form).
        """
        handled = cc.handle_owner_credential_handoff(
            "token",
            -1002064137259,
            1811,
            "give log in and password here. i give permission. do it now.",
            "@madi_ayazbay",  # sender is owner — no DM echo
            owner_chat_id=110793056,
        )

        self.assertTrue(handled)
        mock_react.assert_called_once_with("token", -1002064137259, 1811)
        # Exactly one send: the group reply. No owner-DM echo.
        self.assertEqual(mock_send.call_count, 1, mock_send.call_args_list)
        sent_chat_id = mock_send.call_args_list[0].args[1]
        sent_text = mock_send.call_args_list[0].args[2]
        self.assertEqual(sent_chat_id, -1002064137259)
        # Shorter terse owner-mode reply
        self.assertIn("Креды в группах не публикую", sent_text)
        self.assertIn("Самый быстрый путь", sent_text)
        self.assertIn("DM", sent_text)
        # No echo of the owner's message back to the owner
        self.assertNotIn("OWNER-ONLY", sent_text)

    @patch("command_center._codex_daily_budget_ok", return_value=(True, 0.00))
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex", return_value="codex supervised top-tier plan")
    @patch("command_center._tg_send", return_value=True)
    def test_top_tier_second_brain_ask_routes_to_codex(
        self, mock_send, mock_codex, mock_openclaw, _mock_budget
    ):
        now = datetime(2026, 5, 18, 14, 55, tzinfo=ALMATY)
        query = "I need the top tier GPT second brain to make OpenClaw bulletproof."

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1745, "/ask " + query)

        self.assertTrue(handled)
        mock_openclaw.assert_not_called()
        mock_codex.assert_called_once()
        self.assertIn("top tier GPT", mock_codex.call_args[0][0])
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        self.assertTrue(any("ChatGPT/Codex GPT-5.5 subscription" in text for text in sent_texts))

    @patch("command_center._codex_daily_budget_ok", return_value=(False, 5.01))
    @patch("command_center._run_openclaw", return_value="grok-ceo answered the denis events query")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_external_operator_proof_falls_back_to_grok_with_russian_notice_in_group(
        self, mock_send, mock_codex, mock_openclaw, _mock_budget
    ):
        """AP-41: external operator proof (Denis asking about events) in GROUP
        chat falls back to grok-ceo with Russian notice when codex is capped."""
        now = datetime(2026, 5, 18, 15, 12, tzinfo=ALMATY)
        query = (
            "Telegram group sender @denis: Message: события пошли, какой endpoint и consumer, "
            "видите ли логи по событиям?"
        )

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", -1002064137259, 1751, "/ask " + query)

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        # AP-41: grok-ceo IS called as fallback
        mock_openclaw.assert_called_once()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        # Russian fallback notice for group chats
        self.assertTrue(any("Codex недоступен" in text for text in sent_texts), sent_texts)
        self.assertTrue(any("Использую grok-ceo Tier-1" in text for text in sent_texts), sent_texts)
        # No more English wall-of-text
        self.assertFalse(any("mandatory /codex only" in text for text in sent_texts), sent_texts)
        self.assertFalse(any("No answer was generated" in text for text in sent_texts), sent_texts)

    @patch("command_center._codex_daily_budget_ok", return_value=(False, 5.01))
    @patch("command_center._run_openclaw", return_value="grok-ceo answered the CTO query")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_top_tier_cto_ceo_falls_back_to_grok_with_english_notice_in_dm(
        self, mock_send, mock_codex, mock_openclaw, _mock_budget
    ):
        """AP-41: top-tier CTO/CEO question in DM (Madi) falls back to grok-ceo
        with an English notice (operator-facing) when codex is capped."""
        now = datetime(2026, 5, 18, 15, 15, tzinfo=ALMATY)
        query = "What would a top-tier CTO/CEO do with this agent factory?"

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1752, "/ask " + query)

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        # AP-41: grok-ceo IS called as fallback
        mock_openclaw.assert_called_once()
        sent_texts = [call.args[2] for call in mock_send.call_args_list]
        # English notice for DM (Madi operator) with spend info
        self.assertTrue(any("Codex недоступен" in text for text in sent_texts), sent_texts)
        self.assertTrue(any("daily token cap reached" in text for text in sent_texts), sent_texts)
        self.assertTrue(any("$5.01" in text for text in sent_texts), sent_texts)
        self.assertTrue(any("grok-ceo Tier-1" in text for text in sent_texts), sent_texts)
        # No more English wall-of-text
        self.assertFalse(any("mandatory /codex only" in text for text in sent_texts), sent_texts)
        self.assertFalse(any("No answer was generated" in text for text in sent_texts), sent_texts)

    @patch("command_center._kick_goal_cycle", return_value={"ok": True, "message": "kicked com.nous.goal-cycle"})
    @patch("command_center._create_todoist_task", return_value={"ok": True, "id": "task-1"})
    @patch("command_center._create_goal_page", return_value={"rel_path": "pages/projects/GOAL-test.md", "deadline": "none"})
    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_long_work_ask_creates_goal_and_does_not_run_model_inline(
        self, mock_send, mock_codex, mock_openclaw, mock_goal, mock_todoist, mock_kick
    ):
        now = datetime(2026, 5, 15, 10, 35, tzinfo=ALMATY)
        query = (
            "Implement everything step by step, audit the whole factory, create tasks, "
            "orchestrate Todoist, and do not come back until it is 100% done. "
            * 8
        )

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1502, "/ask " + query)

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        mock_openclaw.assert_not_called()
        mock_goal.assert_called_once()
        mock_todoist.assert_called_once()
        mock_kick.assert_called_once()
        sent_text = mock_send.call_args[0][2]
        self.assertIn("Long work converted into durable factory state", sent_text)
        self.assertIn("deepseek-v4-flash", sent_text)

    @patch("command_center._run_openclaw")
    @patch("command_center._run_codex")
    @patch("command_center._tg_send", return_value=True)
    def test_openclaw_identity_question_is_answered_locally_without_model(self, mock_send, mock_codex, mock_openclaw):
        now = datetime(2026, 5, 15, 1, 15, tzinfo=ALMATY)

        with patch("command_center._now_almaty", return_value=now):
            handled = cc.handle("token", 110793056, 1514, "/ask Are you now openclaw ?")

        self.assertTrue(handled)
        mock_codex.assert_not_called()
        mock_openclaw.assert_not_called()
        sent_text = mock_send.call_args[0][2]
        self.assertIn("OpenClaw production runtime", sent_text)
        self.assertIn("OpenClaw → grok-ceo", sent_text)
        self.assertIn("command_center.py", sent_text)
        self.assertNotIn("No.", sent_text)


class CodexRouteTests(unittest.TestCase):
    def test_resolve_codex_cmd_uses_first_executable_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "codex"
            exe.write_text("#!/bin/sh\nexit 0\n")
            exe.chmod(0o755)
            with patch.dict(os.environ, {"CODEX_CMD": str(exe)}):
                self.assertEqual(cc._resolve_codex_cmd(), str(exe))

    def test_codex_token_cap_blocks_before_subprocess(self):
        old_token_cap = cc.CODEX_DAILY_CAP_TOKENS
        old_call_cap = cc.CODEX_DAILY_CAP_CALLS
        cc.CODEX_DAILY_CAP_TOKENS = 100
        cc.CODEX_DAILY_CAP_CALLS = 12
        try:
            with patch("command_center._load_codex_usage", return_value={"date": "2026-04-28", "count": 1, "tokens": 100}):
                with patch("command_center._run_codex_once") as mock_run:
                    result = cc._run_codex("reply hi")
            self.assertIn("token cap reached", result)
            mock_run.assert_not_called()
        finally:
            cc.CODEX_DAILY_CAP_TOKENS = old_token_cap
            cc.CODEX_DAILY_CAP_CALLS = old_call_cap

    def test_codex_subscription_auth_failure_does_not_try_api_fallback(self):
        proc = types.SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="401 Unauthorized: token_expired",
        )
        with patch("command_center._load_codex_usage", return_value={"date": "2026-05-11", "count": 0, "tokens": 0}):
            with patch("command_center._register_spawned_session", return_value="sid-codex"):
                with patch("command_center._close_spawned_session") as mock_close:
                    with patch("command_center._run_codex_once", return_value=proc) as mock_run:
                        result = cc._run_codex("reply hi")

        self.assertIn("API fallback is disabled by policy", result)
        mock_run.assert_called_once()
        self.assertIsNone(mock_run.call_args[0][1])
        mock_close.assert_called_once_with("sid-codex", "error")


class GoalModeRouteTests(unittest.TestCase):
    def test_goal_commands_are_routable(self):
        self.assertTrue(cc.is_command("/goal ship OpenBrain projection by 2026-05-15"))
        self.assertTrue(cc.is_command("/goal-list"))

    def test_goal_deadline_parser_handles_inline_by_date(self):
        goal, deadline = cc._parse_goal_command(
            "/goal Have a one-command bootstrap pack ready by 2026-05-19: clone wiki and run smoke"
        )
        self.assertEqual(deadline, "2026-05-19")
        self.assertEqual(goal, "Have a one-command bootstrap pack ready: clone wiki and run smoke")

    def test_create_goal_page_uses_wiki_env_and_can_skip_git(self):
        now = datetime(2026, 5, 11, 10, 30, tzinfo=ALMATY)
        with tempfile.TemporaryDirectory() as tmp:
            old_commit = os.environ.get("NOUS_GOAL_COMMIT")
            os.environ["NOUS_GOAL_COMMIT"] = "0"
            try:
                goal = cc._create_goal_page("Ship OpenBrain projection", "2026-05-15", now=now, wiki_root=tmp)
            finally:
                if old_commit is None:
                    os.environ.pop("NOUS_GOAL_COMMIT", None)
                else:
                    os.environ["NOUS_GOAL_COMMIT"] = old_commit

            self.assertEqual(goal["rel_path"], "pages/projects/GOAL-20260511-103000-ship-openbrain-projection.md")
            path = Path(tmp) / goal["rel_path"]
            self.assertTrue(path.exists())
            body = path.read_text()
            self.assertIn("title: \"Ship OpenBrain projection\"", body)
            self.assertIn("deadline: 2026-05-15", body)
            self.assertIn("status: active", body)
            self.assertIn("immediate goal-cycle kick", body)

    def test_goal_cycle_kick_can_be_disabled_for_tests(self):
        old_kick = os.environ.get("NOUS_GOAL_KICK")
        os.environ["NOUS_GOAL_KICK"] = "0"
        try:
            result = cc._kick_goal_cycle()
        finally:
            if old_kick is None:
                os.environ.pop("NOUS_GOAL_KICK", None)
            else:
                os.environ["NOUS_GOAL_KICK"] = old_kick
        self.assertTrue(result["ok"])
        self.assertIn("disabled", result["message"])

    @patch("command_center.subprocess.run")
    def test_goal_cycle_kick_uses_launchd_label(self, mock_run):
        mock_run.return_value = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        result = cc._kick_goal_cycle()
        self.assertTrue(result["ok"])
        self.assertIn("kicked com.nous.goal-cycle", result["message"])
        self.assertEqual(mock_run.call_args[0][0], ["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.nous.goal-cycle"])

    @patch("command_center._kick_goal_cycle", return_value={"ok": True, "message": "kicked com.nous.goal-cycle"})
    @patch("command_center._create_todoist_task", return_value={"ok": False, "error": "TODOIST_PROJECT_ID not found"})
    @patch("command_center._tg_send", return_value=True)
    def test_handle_goal_creates_page_and_surfaces_todoist_failure(self, mock_send, mock_todoist, mock_kick):
        now = datetime(2026, 5, 11, 10, 35, tzinfo=ALMATY)
        with tempfile.TemporaryDirectory() as tmp:
            old_wiki = os.environ.get("NOUS_WIKI")
            old_commit = os.environ.get("NOUS_GOAL_COMMIT")
            os.environ["NOUS_WIKI"] = tmp
            os.environ["NOUS_GOAL_COMMIT"] = "0"
            try:
                with patch("command_center._now_almaty", return_value=now):
                    handled = cc.handle("token", 110793056, 77, "/goal Repair goal mode by 2026-05-15")
            finally:
                if old_wiki is None:
                    os.environ.pop("NOUS_WIKI", None)
                else:
                    os.environ["NOUS_WIKI"] = old_wiki
                if old_commit is None:
                    os.environ.pop("NOUS_GOAL_COMMIT", None)
                else:
                    os.environ["NOUS_GOAL_COMMIT"] = old_commit

        self.assertTrue(handled)
        mock_todoist.assert_called_once()
        mock_kick.assert_called_once()
        reply = mock_send.call_args[0][2]
        self.assertIn("Goal created.", reply)
        self.assertIn("Todoist not created: TODOIST_PROJECT_ID not found", reply)
        self.assertIn("Runner: kicked com.nous.goal-cycle", reply)


class SpawnedAgentPreambleTests(unittest.TestCase):
    def test_code_and_codex_preambles_include_coordination_handshake(self):
        for preamble in (cc.SESSION_CONTEXT_PREAMBLE, cc.CODEX_CONTEXT_PREAMBLE):
            self.assertIn("session-coordination/SKILL.md", preamble)
            self.assertIn("tools/session_register.sh", preamble)
            self.assertIn("tools/session_scan.sh", preamble)
            self.assertIn("git commit -o <paths>", preamble)
            self.assertIn("tools/session_close.sh", preamble)

    def test_code_route_registers_and_closes_outer_session(self):
        proc = types.SimpleNamespace(
            returncode=0,
            stdout='{"result":"CLAUDE_OK","total_cost_usd":0.01,"duration_ms":1000}',
            stderr="",
        )
        with patch("command_center._load_claude_cost", return_value={"date": "2026-04-29", "total_usd": 0.0, "count": 0}):
            with patch("command_center._save_claude_cost"):
                with patch("command_center._register_spawned_session", return_value="sid-code") as mock_register:
                    with patch("command_center._close_spawned_session") as mock_close:
                        with patch("command_center.subprocess.run", return_value=proc) as mock_run:
                            result = cc._run_claude_code("reply hi")

        self.assertIn("CLAUDE_OK", result)
        mock_register.assert_called_once_with("/code", "reply hi")
        mock_close.assert_called_once_with("sid-code", "ok")
        prompt = mock_run.call_args[0][0][2]
        self.assertIn("sid-code", prompt)

    def test_codex_route_registers_and_closes_outer_session(self):
        proc = types.SimpleNamespace(returncode=0, stdout="CODEX_OK\n", stderr="tokens used 7")
        with patch("command_center._load_codex_usage", return_value={"date": "2026-04-29", "count": 0, "tokens": 0}):
            with patch("command_center._save_codex_usage"):
                with patch("command_center._register_spawned_session", return_value="sid-codex") as mock_register:
                    with patch("command_center._close_spawned_session") as mock_close:
                        with patch("command_center._run_codex_once", return_value=proc) as mock_run:
                            result = cc._run_codex("reply hi")

        self.assertIn("CODEX_OK", result)
        mock_register.assert_called_once_with("/codex", "reply hi")
        mock_close.assert_called_once_with("sid-codex", "ok")
        prompt = mock_run.call_args[0][0]
        self.assertIn("sid-codex", prompt)


if __name__ == "__main__":
    unittest.main()
