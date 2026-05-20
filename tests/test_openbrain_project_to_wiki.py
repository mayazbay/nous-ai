#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "openbrain_project_to_wiki.py"
spec = importlib.util.spec_from_file_location("openbrain_project_to_wiki", SCRIPT)
openbrain = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules["openbrain_project_to_wiki"] = openbrain
spec.loader.exec_module(openbrain)


SAMPLE = """2 recent thought(s):

1. [2026-05-11T10:48:58.034Z] id=97bff167-28ef-46dc-a419-d1f4fadef623 (observation - uncategorized, KEONA)
   KEONA / SPECTRA latest email correction, 2026-05-11: Lim email from 2026-05-07 is verified.

2. [2026-05-03T02:43:28.000Z] id=11111111-2222-4333-8444-555555555555 (reference - Open Brain, MCP)
   Successfully set up Open Brain on 2026-05-03. Connected via Claude Code MCP.
"""


class OpenBrainProjectionTests(unittest.TestCase):
    def test_parse_list_output_requires_uuid_and_content(self):
        thoughts = openbrain.parse_list_thoughts(SAMPLE)
        self.assertEqual(len(thoughts), 2)
        self.assertEqual(thoughts[0].openbrain_id, "97bff167-28ef-46dc-a419-d1f4fadef623")
        self.assertEqual(thoughts[0].date, "2026-05-11")
        self.assertEqual(thoughts[0].thought_type, "observation")
        self.assertEqual(thoughts[0].topics, ("uncategorized", "KEONA"))
        self.assertIn("Lim email", thoughts[0].content)

    def test_projection_is_idempotent_and_uses_full_uuid_filename(self):
        thought = openbrain.parse_list_thoughts(SAMPLE)[0]
        with tempfile.TemporaryDirectory() as tmp:
            wiki = pathlib.Path(tmp)
            first = openbrain.project_thought(wiki, thought, dry_run=False, projected_at="2026-05-11T11:00:00Z")
            second = openbrain.project_thought(wiki, thought, dry_run=False, projected_at="2026-05-11T11:01:00Z")
            self.assertEqual(first["status"], "created")
            self.assertEqual(second["status"], "exists")
            self.assertTrue(first["path"].endswith("openbrain-97bff167-28ef-46dc-a419-d1f4fadef623.md"))
            rendered = (wiki / first["path"]).read_text(encoding="utf-8")
            self.assertIn("openbrain_id: \"97bff167-28ef-46dc-a419-d1f4fadef623\"", rendered)
            self.assertIn("content_hash:", rendered)
            self.assertIn("status: projected", rendered)

    def test_existing_file_hash_mismatch_fails_visibly(self):
        thought = openbrain.parse_list_thoughts(SAMPLE)[0]
        with tempfile.TemporaryDirectory() as tmp:
            wiki = pathlib.Path(tmp)
            path = openbrain.projection_path(wiki, thought)
            path.parent.mkdir(parents=True)
            path.write_text("content_hash: \"wrong\"\n", encoding="utf-8")
            with self.assertRaises(openbrain.ProjectionError) as ctx:
                openbrain.project_thought(wiki, thought, dry_run=False, projected_at="2026-05-11T11:00:00Z")
            self.assertIn("projection_failed", str(ctx.exception))

    def test_duplicate_content_hash_does_not_create_second_mirror(self):
        first, second = openbrain.parse_list_thoughts(
            SAMPLE
            + "\n\n3. [2026-05-11T11:10:00.000Z] id=22222222-3333-4444-8555-666666666666 (observation - uncategorized)\n"
            + "   KEONA / SPECTRA latest email correction, 2026-05-11: Lim email from 2026-05-07 is verified.\n"
        )[0::2]
        with tempfile.TemporaryDirectory() as tmp:
            wiki = pathlib.Path(tmp)
            content_hashes = {}
            created = openbrain.project_thought(wiki, first, False, "2026-05-11T11:00:00Z", content_hashes)
            duplicate = openbrain.project_thought(wiki, second, False, "2026-05-11T11:01:00Z", content_hashes)
            self.assertEqual(created["status"], "created")
            self.assertEqual(duplicate["status"], "duplicate_content")
            self.assertEqual(len(list((wiki / "pages/inbox/openbrain").glob("*/*.md"))), 1)

    def test_projection_redacts_camera_credentials(self):
        thought = openbrain.Thought(
            openbrain_id="33333333-4444-4555-8666-777777777777",
            created_at="2026-05-18T15:04:10.000Z",
            content=(
                "ЛУ100: 10.145.1.2 admin CameraPass_2026. "
                "admin/SlashPass_2026 password: other-secret Hikvision pwd ExamplePwd_2026"
            ),
            thought_type="observation",
            topics=("Satory",),
        )
        rendered = openbrain.render_markdown(thought, projected_at="2026-05-18T15:05:00Z")
        self.assertIn("10.145.1.2 admin [REDACTED]", rendered)
        self.assertIn("admin/[REDACTED]", rendered)
        self.assertIn("password=[REDACTED]", rendered)
        self.assertIn("pwd [REDACTED]", rendered)
        self.assertNotIn("CameraPass_2026", rendered)
        self.assertNotIn("SlashPass_2026", rendered)
        self.assertNotIn("other-secret", rendered)
        self.assertNotIn("ExamplePwd_2026", rendered)


if __name__ == "__main__":
    unittest.main()
