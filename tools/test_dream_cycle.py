#!/usr/bin/env python3
"""
test_dream_cycle.py — TDD tests for dream_cycle.py nightly pass.

Tests:
  1. Scans lessons correctly
  2. Detects unabsorbed lessons >= 7 days
  3. Skips fresh lessons (< 7 days)
  4. Writes proposal page
  5. Suggests target skills
  6. Handles empty lessons/skills gracefully

Run: python3 test_dream_cycle.py
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0
KZ_TZ = timezone(timedelta(hours=5))


def assert_true(condition, label):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}")


def _build_test_env(tmp: Path):
    """Create minimal wiki with lessons + skills."""
    import dream_cycle as dc

    lessons_dir = tmp / "pages" / "lessons" / "individual"
    lessons_dir.mkdir(parents=True)
    skills_dir = tmp / "pages" / "skills"
    dashboards_dir = tmp / "pages" / "dashboards"
    dashboards_dir.mkdir(parents=True)

    # Old unabsorbed lesson (30 days old)
    old_date = (datetime.now(KZ_TZ) - timedelta(days=30)).strftime("%Y-%m-%d")
    (lessons_dir / "LESSON-042-old-bug.md").write_text(f"""---
type: lesson
id: LESSON-042
title: "Old unabsorbed bug"
date: {old_date}
status: reviewed
---
# Old bug
Root cause: something broke.
""")

    # Fresh lesson (2 days old — should be skipped)
    fresh_date = (datetime.now(KZ_TZ) - timedelta(days=2)).strftime("%Y-%m-%d")
    (lessons_dir / "LESSON-100-fresh.md").write_text(f"""---
type: lesson
id: LESSON-100
title: "Fresh lesson"
date: {fresh_date}
status: draft
---
# Fresh
Just happened.
""")

    # Absorbed lesson (10 days old but already absorbed)
    absorbed_date = (datetime.now(KZ_TZ) - timedelta(days=10)).strftime("%Y-%m-%d")
    (lessons_dir / "LESSON-050-absorbed.md").write_text(f"""---
type: lesson
id: LESSON-050
title: "Already absorbed lesson"
date: {absorbed_date}
status: reviewed
---
# Absorbed
This was fixed.
""")

    # Skill that absorbed LESSON-050
    camera_dir = skills_dir / "camera-management"
    camera_dir.mkdir(parents=True)
    (camera_dir / "SKILL.md").write_text("""---
name: camera-management
absorbs_lessons: [LESSON-050]
---
# Camera Management
## Evidence trail
- LESSON-050 absorbed: rule added.
""")

    # Another skill
    infra_dir = skills_dir / "infrastructure"
    infra_dir.mkdir(parents=True)
    (infra_dir / "SKILL.md").write_text("""---
name: infrastructure
absorbs_lessons: [LESSON-030]
---
# Infrastructure
""")

    # Patch module paths
    dc.WIKI_ROOT = tmp
    dc.LESSONS_DIR = lessons_dir
    dc.SKILLS_DIR = skills_dir
    dc.DASHBOARDS_DIR = dashboards_dir

    return tmp


def test_scan_lessons():
    """Scans all lessons correctly."""
    import dream_cycle as dc

    with tempfile.TemporaryDirectory() as tmp:
        _build_test_env(Path(tmp))
        lessons = dc._scan_lessons()
        assert_true(len(lessons) == 3, f"Found 3 lessons (got {len(lessons)})")
        names = [l["file"] for l in lessons]
        assert_true("LESSON-042-old-bug.md" in names, "LESSON-042 found")


def test_unabsorbed_detection():
    """Detects unabsorbed lessons >= 7 days."""
    import dream_cycle as dc

    with tempfile.TemporaryDirectory() as tmp:
        _build_test_env(Path(tmp))
        lessons = dc._scan_lessons()
        skills = dc._scan_skills()
        unabsorbed = dc._find_unabsorbed(lessons, skills)
        ids = [u["lesson_id"] for u in unabsorbed]
        assert_true("LESSON-042" in ids, "LESSON-042 (old, unabsorbed) detected")
        assert_true("LESSON-100" not in ids, "LESSON-100 (fresh) NOT detected")
        assert_true("LESSON-050" not in ids, "LESSON-050 (absorbed) NOT detected")


def test_proposal_written():
    """Writes proposal page."""
    import dream_cycle as dc

    with tempfile.TemporaryDirectory() as tmp:
        _build_test_env(Path(tmp))
        lessons = dc._scan_lessons()
        skills = dc._scan_skills()
        unabsorbed = dc._find_unabsorbed(lessons, skills)
        filepath = dc._write_proposal(unabsorbed, skills, len(lessons))
        assert_true(filepath.is_file(), "Proposal file created")
        content = filepath.read_text()
        assert_true("LESSON-042" in content, "Proposal mentions unabsorbed lesson")
        assert_true("READ-ONLY" in content, "Proposal states READ-ONLY")


def test_skill_suggestion():
    """Suggests target skill correctly."""
    import dream_cycle as dc

    with tempfile.TemporaryDirectory() as tmp:
        _build_test_env(Path(tmp))
        skills = dc._scan_skills()
        camera_lesson = {"title": "Camera ISAPI timeout fix", "file": "LESSON-042-camera.md"}
        suggestion = dc._suggest_target_skill(camera_lesson, skills)
        assert_true(suggestion == "camera-management", f"Suggested camera-management (got {suggestion})")


def test_empty_graceful():
    """Handles empty state gracefully."""
    import dream_cycle as dc

    with tempfile.TemporaryDirectory() as tmp:
        dc.WIKI_ROOT = Path(tmp)
        dc.LESSONS_DIR = Path(tmp) / "pages" / "lessons" / "individual"
        dc.SKILLS_DIR = Path(tmp) / "pages" / "skills"
        dc.DASHBOARDS_DIR = Path(tmp) / "pages" / "dashboards"
        dc.DASHBOARDS_DIR.mkdir(parents=True)

        lessons = dc._scan_lessons()
        skills = dc._scan_skills()
        assert_true(len(lessons) == 0, "Empty lessons OK")
        assert_true(len(skills) == 0, "Empty skills OK")
        filepath = dc._write_proposal([], skills, 0)
        assert_true("ALL CLEAR" in filepath.read_text(), "Empty state = ALL CLEAR")


if __name__ == "__main__":
    print("=== dream_cycle TDD tests ===\n")

    print("Test 1: Scan lessons")
    test_scan_lessons()

    print("\nTest 2: Unabsorbed detection")
    test_unabsorbed_detection()

    print("\nTest 3: Proposal written")
    test_proposal_written()

    print("\nTest 4: Skill suggestion")
    test_skill_suggestion()

    print("\nTest 5: Empty graceful")
    test_empty_graceful()

    print(f"\n{'=' * 40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED ✅")
