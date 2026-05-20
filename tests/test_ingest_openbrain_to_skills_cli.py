#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "ingest_openbrain_to_skills.py"


class IngestOpenBrainCliTests(unittest.TestCase):
    def test_json_flag_is_accepted_for_automation_compatibility(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--dry-run", "--json", "--limit", "1"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 2, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("dry_run", payload)


if __name__ == "__main__":
    unittest.main()
