"""Test: lesson-absorption-watcher detects unabsorbed lessons >= 7d old."""
import tempfile, os, pathlib, datetime, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_detects_old_unabsorbed():
    from lesson_absorption_watcher import scan_lessons

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)

        # Fresh unabsorbed — OK (< 7d)
        (p / "LESSON-001-fresh.md").write_text(
            "---\n"
            "lesson_id: LESSON-001\n"
            "date: 2026-04-15\n"
            "status: unabsorbed\n"
            "absorbed_into: null\n"
            "---\n"
            "fresh lesson\n"
        )

        # Old unabsorbed — GHOST (>= 7d)
        (p / "LESSON-002-old.md").write_text(
            "---\n"
            "lesson_id: LESSON-002\n"
            "date: 2026-04-01\n"
            "status: unabsorbed\n"
            "absorbed_into: null\n"
            "---\n"
            "old lesson\n"
        )

        # Already absorbed — OK
        (p / "LESSON-003-absorbed.md").write_text(
            "---\n"
            "lesson_id: LESSON-003\n"
            "date: 2026-04-01\n"
            "status: absorbed\n"
            "absorbed_into: [some-skill]\n"
            "absorbed_at: 2026-04-05\n"
            "---\n"
            "absorbed lesson\n"
        )

        ghosts = scan_lessons(p, today=datetime.date(2026, 4, 16), sla_days=7)

        assert len(ghosts) == 1, f"Expected 1 ghost, got {len(ghosts)}"
        assert ghosts[0].lesson_id == "LESSON-002", f"Wrong ghost: {ghosts[0].lesson_id}"
        assert ghosts[0].age_days == 15, f"Wrong age: {ghosts[0].age_days}"

    print("PASS: all assertions green")


if __name__ == "__main__":
    test_detects_old_unabsorbed()
