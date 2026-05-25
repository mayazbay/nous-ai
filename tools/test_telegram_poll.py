"""Tests for telegram_poll.py — focusing on the implicit /ask routing logic."""
import sys
import os
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Wire the module search path so telegram_poll imports succeed.
TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, "/opt/nous-agaas")
sys.path.insert(0, "/root/nous-agaas/tools")
sys.path.insert(0, str(TOOLS_DIR))

# Stub the dotenv import so the module loads without a real .env file.
import importlib
import types
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *a, **kw: None
sys.modules.setdefault("dotenv", dotenv_stub)
command_center_stub = types.ModuleType("command_center")
command_center_stub.__file__ = str(TOOLS_DIR / "command_center.py")
command_center_stub.is_command = lambda text: False
command_center_stub.handle = lambda *a, **kw: False
sys.modules.setdefault("command_center", command_center_stub)

# Set required env vars before importing the module.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "1234567890")
os.environ["TELEGRAM_INGEST_PERSIST"] = "0"

import telegram_poll as tp


ALLOWED = tp.ALLOWED_CHAT_ID  # 1234567890
OTHER   = 9999999999
GROUP   = -1001234567890


def _msg(text, chat_id=ALLOWED, msg_id=42, chat_type="private", username=None):
    if chat_id < 0 and chat_type == "private":
        chat_type = "supergroup"
    msg = {"text": text, "chat": {"id": chat_id, "type": chat_type}, "message_id": msg_id}
    if username:
        msg["from"] = {"username": username}
    return msg


def _photo_msg(chat_id=GROUP, msg_id=43, username="madi_ayazbay"):
    return {
        "chat": {"id": chat_id, "type": "supergroup"},
        "message_id": msg_id,
        "from": {"username": username},
        "photo": [
            {"file_id": "small", "file_size": 10},
            {"file_id": "large", "file_size": 100},
        ],
    }


class TestImplicitAsk(unittest.TestCase):
    """Plain text from the authorized chat must route to OpenClaw (implicit /ask)."""

    def setUp(self):
        # Patch file-system writes and Telegram ACK so no real I/O occurs.
        self._pending_patcher = patch.object(Path, "write_text", return_value=None)
        self._mkdir_patcher   = patch.object(Path, "mkdir",      return_value=None)
        self._pending_patcher.start()
        self._mkdir_patcher.start()

    def tearDown(self):
        self._pending_patcher.stop()
        self._mkdir_patcher.stop()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_plain_text_from_authorized_routes_to_openclaw(self, mock_is_cmd, mock_handle, mock_ack):
        """Plain text from ALLOWED chat → natural command forwarded to handle()."""
        result = tp.process_message(_msg("What is the status of NIT VPN?"))
        self.assertEqual(result, (True, "command", ""))
        mock_handle.assert_called_once()
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/status")
        # No vault capture ACK
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_forwarded_message_from_authorized_routes_to_openclaw(self, mock_is_cmd, mock_handle, mock_ack):
        """Forwarded plain text (no /ask prefix) from ALLOWED chat routes to OpenClaw."""
        fwd = _msg("Asyl says the VPN form was submitted last Tuesday")
        result = tp.process_message(fwd)
        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertTrue(passed_text.startswith("/ask "))
        self.assertIn("VPN form", passed_text)

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_private_natural_goal_routes_to_goal(self, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("цель: prove no slash Telegram interface"))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/goal prove no slash Telegram interface")

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_private_natural_codex_routes_to_codex(self, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("use gpt 5.5 to audit OpenClaw routing"))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/codex audit OpenClaw routing")

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_private_top_tier_second_brain_routes_to_codex(self, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("I need the top tier GPT second brain to audit OpenClaw"))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/codex I need the top tier GPT second brain to audit OpenClaw")

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_private_top_tier_cto_ceo_routes_to_codex(self, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("What would a top-tier CTO/CEO do with the factory?"))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/codex What would a top-tier CTO/CEO do with the factory?")

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_unknown_slash_command_from_authorized_goes_to_vault(self, mock_is_cmd, mock_handle, mock_ack):
        """/unknown from ALLOWED chat must NOT be implicit /ask — goes to vault."""
        result = tp.process_message(_msg("/nous capture this note"))
        # Should fall through to vault capture (not a command, starts with /)
        # handle() should NOT be called via the implicit branch
        for c in mock_handle.call_args_list:
            args = c[0]
            if len(args) >= 4:
                self.assertFalse(args[3].startswith("/ask "),
                    "Unexpected implicit /ask for /nous message")

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=False)
    @patch("telegram_poll.command_center.is_command", return_value=True)
    def test_unknown_slash_audit_filename_is_flat(self, mock_is_cmd, mock_handle, mock_ack):
        """/audit fallback capture must not embed slash in the filename."""
        result = tp.process_message(_msg("/audit deep dive"))
        self.assertTrue(result[0])
        self.assertEqual(result[1], "text")
        filename = result[2]
        self.assertNotIn("/", filename)
        self.assertIn("audit", filename)

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_plain_text_from_unauthorized_goes_to_vault(self, mock_is_cmd, mock_handle, mock_ack):
        """Plain text from an UNAUTHORIZED chat must go to vault, not OpenClaw."""
        # Non-allowed chat → process_message returns (False, 'denied', '')
        result = tp.process_message(_msg("hack me", chat_id=OTHER))
        self.assertEqual(result[1], "denied")
        mock_handle.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_whitespace_only_does_not_route(self, mock_is_cmd, mock_handle, mock_ack):
        """Whitespace-only messages must not be sent to OpenClaw."""
        tp.process_message(_msg("   "))
        # handle() may not be called from the implicit branch for empty text
        for c in mock_handle.call_args_list:
            args = c[0]
            if len(args) >= 4 and args[3].startswith("/ask"):
                query = args[3][4:].strip()
                self.assertTrue(query, "Empty query must not reach OpenClaw via implicit /ask")


class TestSplitMentionRecovery(unittest.TestCase):
    """Telegram visually groups consecutive same-sender msgs but the API delivers
    them separately. When the second is just `@nousAGaaSbot`, the bot must still
    route the prior message's body. AP-6 (air-ssh-access v2.5.0, 2026-05-18)."""

    def setUp(self):
        self._mkdir_patcher = patch.object(Path, "mkdir", return_value=None)
        self._allowed_patcher = patch.object(tp, "ALLOWED_CHAT_IDS", {ALLOWED, GROUP})
        self._mkdir_patcher.start()
        self._allowed_patcher.start()

    def tearDown(self):
        self._mkdir_patcher.stop()
        self._allowed_patcher.stop()

    def _write_inbox_message(
        self,
        wiki_root: Path,
        *,
        msg_id: int,
        sender: str,
        body: str,
        ingested_at: datetime,
        chat_id: int = GROUP,
    ) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        path = wiki_root / "pages" / "inbox" / today / f"{msg_id}-unknown.md"
        os.makedirs(path.parent, exist_ok=True)
        path.write_text(
            f"""---
type: "inbox"
ingested_at: "{ingested_at.isoformat()}"
chat_id: {chat_id}
msg_id: {msg_id}
sender: "{sender}"
---

# Original message

{body}

# Classifier rationale

pending
""",
            encoding="utf-8",
        )

    def test_recover_split_mention_body_reads_recent_same_sender_inbox(self):
        """The real inbox parser must recover the prior message, not just the
        process_message mock seam."""
        body = "Теперь объясни простым языком что нужно сделать"
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            self._write_inbox_message(
                wiki_root,
                msg_id=98,
                sender="@aliakbar_asylbek",
                body=body,
                ingested_at=datetime.now(timezone.utc),
            )
            with patch.object(tp, "WIKI", wiki_root):
                recovered = tp._recover_split_mention_body(
                    GROUP,
                    "@aliakbar_asylbek",
                    exclude_msg_id=99,
                    max_age_seconds=60,
                )
        self.assertEqual(recovered, body)

    def test_recover_split_mention_body_ignores_stale_inbox_message(self):
        """Mention-only recovery must not resurrect old context."""
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            self._write_inbox_message(
                wiki_root,
                msg_id=97,
                sender="@aliakbar_asylbek",
                body="Старый вопрос не должен ожить",
                ingested_at=datetime.now(timezone.utc) - timedelta(seconds=120),
            )
            with patch.object(tp, "WIKI", wiki_root):
                recovered = tp._recover_split_mention_body(
                    GROUP,
                    "@aliakbar_asylbek",
                    exclude_msg_id=99,
                    max_age_seconds=60,
                )
        self.assertEqual(recovered, "")

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll._recover_split_mention_body",
           return_value="Объясни простым языком что нужно сделать")
    def test_mention_only_recovers_prior_body(
        self, mock_recover, mock_is_cmd, mock_handle, mock_ack
    ):
        """A standalone `@nousAGaaSbot` msg must trigger split-mention recovery
        and route the prior body as a /ask request."""
        msg = _msg(
            "@nousAGaaSbot",
            chat_id=GROUP,
            msg_id=99,
            chat_type="supergroup",
            username="aliakbar_asylbek",
        )
        tp.process_message(msg)
        mock_recover.assert_called_once()
        routed_calls = [
            c for c in mock_handle.call_args_list
            if len(c[0]) >= 4 and c[0][3].startswith("/ask ")
        ]
        self.assertTrue(routed_calls, "split-mention recovery must route to /ask")
        routed_text = routed_calls[0][0][3]
        self.assertIn("Объясни простым языком", routed_text)

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=False)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll._recover_split_mention_body", return_value="")
    def test_mention_only_no_prior_stays_observe_only(
        self, mock_recover, mock_is_cmd, mock_handle, mock_ack
    ):
        """If lookback finds nothing, standalone mention must not invent a request."""
        msg = _msg(
            "@nousAGaaSbot",
            chat_id=GROUP,
            msg_id=100,
            chat_type="supergroup",
            username="aliakbar_asylbek",
        )
        tp.process_message(msg)
        routed_calls = [
            c for c in mock_handle.call_args_list
            if len(c[0]) >= 4 and c[0][3].startswith("/ask ")
        ]
        self.assertFalse(routed_calls,
                         "no prior message means no fabricated /ask routing")

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_mention_then_payload_routes_current_body(
        self, mock_is_cmd, mock_handle, mock_ack
    ):
        """If the bot mention comes first and the payload follows, route payload."""
        payload = (
            "test: ExampleTestSecret_123!\n"
            "prod: ExampleProdSecret_456!\n"
            "Public IP: 65.108.215.200\n"
            "Порт: 443\n"
            "Протокол: HTTPS\n"
            "Чекбокс: ☑ вне ЕТС ГО\n\n"
            "нужно точно также, но уже не для теста и продуктивная среда"
        )
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            self._write_inbox_message(
                wiki_root,
                msg_id=1766,
                sender="@madi_ayazbay",
                body="@nousAGaaSbot",
                ingested_at=datetime.now(timezone.utc),
            )
            with patch.object(tp, "WIKI", wiki_root), patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
                result = tp.process_message(
                    _msg(payload, chat_id=GROUP, msg_id=1767, username="madi_ayazbay")
                )

        self.assertEqual(result, (True, "command", ""))
        routed_calls = [
            c for c in mock_handle.call_args_list
            if len(c[0]) >= 4 and c[0][3].startswith("/ask ")
        ]
        self.assertTrue(routed_calls, "mention-then-payload must route to /ask")
        routed_text = routed_calls[0][0][3]
        self.assertIn("Public IP: 65.108.215.200", routed_text)
        self.assertIn("продуктивная среда", routed_text)
        self.assertIn("test: [REDACTED]", routed_text)
        self.assertIn("prod: [REDACTED]", routed_text)
        self.assertNotIn("ExampleTestSecret_123!", routed_text)
        self.assertNotIn("ExampleProdSecret_456!", routed_text)

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    def test_mention_then_payload_ignores_different_sender(self, mock_is_cmd, mock_handle, mock_ack):
        """A standalone mention from one sender must not latch another sender."""
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            self._write_inbox_message(
                wiki_root,
                msg_id=1766,
                sender="@madi_ayazbay",
                body="@nousAGaaSbot",
                ingested_at=datetime.now(timezone.utc),
            )
            with patch.object(tp, "WIKI", wiki_root), patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
                result = tp.process_message(
                    _msg("это оно", chat_id=GROUP, msg_id=1767, username="other_user")
                )

        self.assertNotEqual(result, (True, "command", ""))
        routed_calls = [
            c for c in mock_handle.call_args_list
            if len(c[0]) >= 4 and c[0][3].startswith("/ask ")
        ]
        self.assertFalse(routed_calls, "mention latch must be scoped by sender")

    def test_recent_standalone_mention_ignores_stale_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            self._write_inbox_message(
                wiki_root,
                msg_id=1766,
                sender="@madi_ayazbay",
                body="@nousAGaaSbot",
                ingested_at=datetime.now(timezone.utc) - timedelta(seconds=180),
            )
            with patch.object(tp, "WIKI", wiki_root):
                self.assertFalse(
                    tp._has_recent_standalone_bot_mention(
                        GROUP,
                        "@madi_ayazbay",
                        exclude_msg_id=1767,
                        max_age_seconds=120,
                    )
                )


class TestRuntimeImportPath(unittest.TestCase):
    def test_tools_command_center_precedes_stale_runtime_root(self):
        tools_dir = str(Path(tp.__file__).resolve().parent)
        runtime_root = "/Users/madia/nous-agaas"

        self.assertEqual(
            Path(tp.command_center.__file__).resolve(),
            Path(tools_dir, "command_center.py").resolve(),
        )
        self.assertIn(runtime_root, sys.path)


class TestGetUpdatesErrorHandling(unittest.TestCase):
    def test_transient_getupdates_timeout_retries_before_launchd_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = [
                TimeoutError("The read operation timed out"),
                {"ok": True, "result": []},
            ]
            with patch.object(tp, "LOCK", Path(tmp) / "telegram_poll.lock"), \
                 patch.object(tp, "load_state", return_value={"last_update_id": 0}), \
                 patch.object(tp, "telegram_api", side_effect=calls) as mock_api, \
                 patch.object(tp.time, "monotonic", side_effect=[0, 1, 2, 3, 51]), \
                 patch.object(tp.time, "sleep", return_value=None):
                self.assertEqual(tp.main(), 0)

        self.assertEqual(mock_api.call_count, 2)

    def test_transient_only_getupdates_cycle_keeps_launchd_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = [
                TimeoutError("The read operation timed out"),
                TimeoutError("The read operation timed out"),
            ]
            with patch.object(tp, "LOCK", Path(tmp) / "telegram_poll.lock"), \
                 patch.object(tp, "load_state", return_value={"last_update_id": 0}), \
                 patch.object(tp, "telegram_api", side_effect=calls) as mock_api, \
                 patch.object(tp.time, "monotonic", side_effect=[0, 1, 2, 3, 51]), \
                 patch.object(tp.time, "sleep", return_value=None):
                self.assertEqual(tp.main(), 0)

        self.assertEqual(mock_api.call_count, 2)

    def test_getupdates_conflict_remains_hard_failure(self):
        conflict = tp.urllib.error.HTTPError(
            "https://api.telegram.org/botTOKEN/getUpdates",
            409,
            "Conflict",
            hdrs=None,
            fp=None,
        )
        self.assertTrue(tp._is_getupdates_conflict_error(conflict))
        self.assertFalse(tp._is_transient_getupdates_error(conflict))


class TestFilenameSafety(unittest.TestCase):
    """Path safety regressions must inspect the actual written path, not only basename."""

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=False)
    @patch("telegram_poll.command_center.is_command", return_value=True)
    def test_unknown_slash_audit_writes_direct_pending_child(self, mock_is_cmd, mock_handle, mock_ack):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp)
            with patch.object(tp, "PENDING", pending):
                result = tp.process_message(_msg("/audit deep dive"))

            self.assertTrue(result[0])
            rel_files = [p.relative_to(pending) for p in pending.rglob("*") if p.is_file()]
            self.assertEqual(len(rel_files), 1)
            self.assertEqual(str(rel_files[0]), result[2])
            self.assertEqual(rel_files[0].parent, Path("."))


class TestExplicitCommandsUnchanged(unittest.TestCase):
    """Explicit /ask, /status etc. must still work exactly as before."""

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=True)
    def test_explicit_ask_still_routes(self, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("/ask What's the NIIS status?"))
        self.assertEqual(result, (True, "command", ""))
        # handle() called with the original text, not double-wrapped
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertTrue(passed_text.startswith("/ask ") or passed_text == "/ask What's the NIIS status?")


class TestAllowedGroupRouting(unittest.TestCase):
    """Satory group support must be explicit and non-spammy."""

    def setUp(self):
        self._allowed = patch.object(tp, "ALLOWED_CHAT_IDS", {ALLOWED, GROUP})
        self._allowed.start()

    def tearDown(self):
        self._allowed.stop()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", side_effect=lambda text: text.startswith("/status"))
    @patch("telegram_poll.persist_text_inbox", return_value="")
    def test_group_command_with_bot_suffix_routes(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("/status@nousAGaaSbot", chat_id=GROUP))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/status")
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="")
    def test_group_ai_prefix_routes_to_ask(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("AI: сравни Negizone и KSL", chat_id=GROUP))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/ask сравни Negizone и KSL")
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="")
    def test_group_natural_address_routes_to_ask_without_slash(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("Фабрика, сравни Negizone и KSL", chat_id=GROUP))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/ask сравни Negizone и KSL")
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-18/1736-unknown")
    def test_group_human_mention_is_observed_not_executed(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg("@Riza1207 Nazel", chat_id=GROUP, msg_id=1736))

        self.assertEqual(result, (True, "observed_group", "pages/inbox/2026-05-18/1736-unknown"))
        mock_persist.assert_called_once()
        mock_handle.assert_not_called()
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="")
    def test_group_bot_mention_routes_to_ask(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("@nousAGaaSbot проверь ЛУ100", chat_id=GROUP))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/ask проверь ЛУ100")
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-18/1750-unknown")
    def test_group_trailing_bot_mention_routes_with_sender_context(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg(
                "ты видишь эту камеру? есть ли доступ у тебя к этой камере. @nousAGaaSbot",
                chat_id=GROUP,
                msg_id=1750,
                username="madi_ayazbay",
            ))

        self.assertEqual(result, (True, "command", ""))
        mock_persist.assert_called_once()
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(
            passed_text,
            "/ask Telegram group sender @madi_ayazbay: if you greet anyone, greet @madi_ayazbay or use Коллеги; "
            "do not greet another person from surrounding context. Message: ты видишь эту камеру? есть ли доступ у тебя к этой камере",
        )
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle_owner_credential_handoff", create=True, return_value=True)
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-19/1771-unknown")
    def test_group_forwarding_bot_mention_is_observed_not_executed(self, mock_persist, mock_is_cmd, mock_handle, mock_handoff, mock_ack):
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg(
                "Send it to me and i will forward @nousAGaaSbot",
                chat_id=GROUP,
                msg_id=1771,
                username="madi_ayazbay",
            ))

        self.assertEqual(result, (True, "observed_group", "pages/inbox/2026-05-19/1771-unknown"))
        mock_persist.assert_called_once()
        mock_handoff.assert_not_called()
        mock_handle.assert_not_called()
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle_owner_credential_handoff", create=True, return_value=True)
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-19/1764-unknown")
    def test_satory_credential_request_routes_to_owner_handoff_without_model(self, mock_persist, mock_is_cmd, mock_handle, mock_handoff, mock_ack):
        body = "с этой группе можешь писать. дай мне логин и пароль для отправки нарушения в ЕРАП. давно уже давал такую информацию"
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg(
                body,
                chat_id=GROUP,
                msg_id=1764,
                username="aliakbar_asylbek",
            ))

        self.assertEqual(result, (True, "command", ""))
        mock_persist.assert_called_once()
        mock_handoff.assert_called_once_with(
            tp.BOT_TOKEN,
            GROUP,
            1764,
            body,
            "@aliakbar_asylbek",
            owner_chat_id=ALLOWED,
        )
        mock_handle.assert_not_called()
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-19/1764-unknown")
    def test_satory_operator_action_request_without_credentials_still_routes(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg(
                "проверь заявку ЕРАП и скажи что не хватает",
                chat_id=GROUP,
                msg_id=1764,
                username="aliakbar_asylbek",
            ))

        self.assertEqual(result, (True, "command", ""))
        mock_persist.assert_called_once()
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(
            passed_text,
            "/ask Telegram group sender @aliakbar_asylbek: if you greet anyone, greet @aliakbar_asylbek or use Коллеги; "
            "do not greet another person from surrounding context. Message: проверь заявку ЕРАП и скажи что не хватает",
        )
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle_owner_credential_handoff", create=True, return_value=True)
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-19/1767-unknown")
    def test_satory_production_config_credentials_go_to_owner_handoff_raw(self, mock_persist, mock_is_cmd, mock_handle, mock_handoff, mock_ack):
        body = (
            "test: ExampleTestSecret_123!\n"
            "prod: ExampleProdSecret_456!\n"
            "Public IP: 65.108.215.200\n"
            "Порт: 443\n"
            "Протокол: HTTPS\n"
            "Чекбокс: ☑ вне ЕТС ГО\n\n"
            "нужно точно также, но уже не для теста и продуктивная среда"
        )
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg(body, chat_id=GROUP, msg_id=1767, username="madi_ayazbay"))

        self.assertEqual(result, (True, "command", ""))
        mock_handoff.assert_called_once_with(
            tp.BOT_TOKEN,
            GROUP,
            1767,
            body,
            "@madi_ayazbay",
            owner_chat_id=ALLOWED,
        )
        mock_handle.assert_not_called()
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="")
    def test_group_natural_address_status_routes_to_status(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("Nous, статус фабрики", chat_id=GROUP))

        self.assertEqual(result, (True, "command", ""))
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/status")
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="")
    def test_group_normal_chatter_is_ignored_not_implicit_ask(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        result = tp.process_message(_msg("доброе утро коллеги", chat_id=GROUP))

        self.assertEqual(result, (False, "ignored_group", ""))
        mock_handle.assert_not_called()
        mock_ack.assert_not_called()

    @patch("telegram_poll.download_file", return_value=True)
    @patch("telegram_poll.telegram_api")
    def test_group_photo_capture_acks_with_reaction_not_verbose_message(self, mock_api, mock_download):
        mock_api.return_value = {"ok": True, "result": {"message_id": 999}}

        result = tp.process_message(_photo_msg(chat_id=GROUP, msg_id=1765))

        self.assertEqual(result[0], True)
        self.assertEqual(result[1], "photo")
        methods = [call.args[0] for call in mock_api.call_args_list]
        self.assertIn("setMessageReaction", methods)
        self.assertNotIn("sendMessage", methods)

    @patch("telegram_poll.download_file", return_value=True)
    @patch("telegram_poll.send_reaction", return_value=True)
    @patch("telegram_poll.persist_media_inbox", return_value="pages/inbox/2026-05-19/1765-media-photo.md")
    def test_full_chat_group_photo_gets_retrievable_inbox_note(self, mock_media, mock_react, mock_download):
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_photo_msg(chat_id=GROUP, msg_id=1765, username="madi_ayazbay"))

        self.assertEqual(result[0], True)
        self.assertEqual(result[1], "photo")
        mock_media.assert_called_once()
        self.assertEqual(mock_media.call_args[0][0], GROUP)
        self.assertEqual(mock_media.call_args[0][1], 1765)
        self.assertEqual(mock_media.call_args[0][2], "photo")

    def test_persist_media_inbox_writes_raw_path_and_photo_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tp, "WIKI", Path(tmp)):
                with patch.dict(os.environ, {"TELEGRAM_INGEST_PERSIST": "1"}):
                    rel = tp.persist_media_inbox(
                        GROUP,
                        1765,
                        "photo",
                        "telegram-2026-05-19_160203-photo.jpg",
                        "@madi_ayazbay",
                        "",
                    )

            note = Path(tmp) / rel
            body = note.read_text()
            self.assertIn('raw_path: "raw/pending/telegram-2026-05-19_160203-photo.jpg"', body)
            self.assertIn("![Captured photo](../../../raw/pending/telegram-2026-05-19_160203-photo.jpg)", body)

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", return_value=False)
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-14/5001-unknown")
    def test_full_chat_group_chatter_is_persisted_not_executed(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg("Руслан: камеру поставили рядом с ЛУ", chat_id=GROUP, msg_id=5001))

        self.assertEqual(result, (True, "observed_group", "pages/inbox/2026-05-14/5001-unknown"))
        mock_persist.assert_called_once()
        mock_handle.assert_not_called()
        mock_ack.assert_not_called()

    @patch("telegram_poll.send_ack")
    @patch("telegram_poll.command_center.handle", return_value=True)
    @patch("telegram_poll.command_center.is_command", side_effect=lambda text: text.startswith("/status"))
    @patch("telegram_poll.persist_text_inbox", return_value="pages/inbox/2026-05-14/5002-unknown")
    def test_full_chat_group_command_is_persisted_and_routed(self, mock_persist, mock_is_cmd, mock_handle, mock_ack):
        with patch.object(tp, "FULL_CHAT_CHAT_IDS", {GROUP}):
            result = tp.process_message(_msg("/status@nousAGaaSbot", chat_id=GROUP, msg_id=5002))

        self.assertEqual(result, (True, "command", ""))
        mock_persist.assert_called_once()
        _, _, _, passed_text = mock_handle.call_args[0]
        self.assertEqual(passed_text, "/status")
        mock_ack.assert_not_called()


if __name__ == "__main__":
    unittest.main()
