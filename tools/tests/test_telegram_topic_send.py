import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import telegram_topic_send as topic_send  # noqa: E402


class TelegramTopicSendTests(unittest.TestCase):
    def test_message_fields_omits_empty_topic(self):
        self.assertEqual(topic_send.message_fields("-1001", None), {"chat_id": "-1001"})

    def test_message_fields_includes_forum_topic(self):
        self.assertEqual(
            topic_send.message_fields("-1001", "1357"),
            {"chat_id": "-1001", "message_thread_id": "1357"},
        )

    def test_result_summary_keeps_thread_id(self):
        self.assertEqual(
            topic_send.result_summary(
                {"ok": True, "result": {"message_id": 1842, "message_thread_id": 1357, "date": 1770000000}}
            ),
            {"ok": True, "message_id": 1842, "message_thread_id": 1357, "date": 1770000000},
        )

    def test_cyrillic_guard_rejects_english_only_text(self):
        self.assertEqual(
            topic_send.validate_text("Next: send revised contract", require_cyrillic=True),
            "telegram_topic_send: refusing text without Cyrillic; pass Russian-facing copy",
        )

    def test_cyrillic_guard_accepts_russian_text(self):
        self.assertEqual(topic_send.validate_text("Что делаем: отправить договор", require_cyrillic=True), "")


if __name__ == "__main__":
    unittest.main()
