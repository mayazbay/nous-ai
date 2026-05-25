import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import keona_telegram_package as keona_pkg  # noqa: E402


class KeonaTelegramPackageTests(unittest.TestCase):
    def test_default_message_is_russian_facing_and_keona_topic_bound(self):
        text = keona_pkg.default_message()
        self.assertEqual(keona_pkg.validate_keona_message(text), [])
        command = keona_pkg.build_sender_command(
            [Path("/tmp/Cabinet_heater.pdf"), Path("/tmp/KeonA_Residency_Certificate.pdf")],
            text=text,
            dry_run=False,
        )
        self.assertIn("--topic", command)
        self.assertIn(keona_pkg.TOPIC_ID, command)
        self.assertIn("--require-cyrillic", command)
        self.assertEqual(command.count("--file"), 2)

    def test_banned_english_operator_phrases_fail(self):
        errors = keona_pkg.validate_keona_message("Что делаем:\nNext: revised contract + site prep")
        self.assertIn("message contains banned English operator phrase: next:", errors)
        self.assertIn("message contains banned English operator phrase: revised contract", errors)
        self.assertIn("message contains banned English operator phrase: site prep", errors)


if __name__ == "__main__":
    unittest.main()
