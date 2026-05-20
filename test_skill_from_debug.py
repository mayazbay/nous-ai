"""Test: skill_from_debug.py creates draft skills from LESSON files."""
import tempfile, os, pathlib, sys, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCRIPT = pathlib.Path(__file__).parent / "skill_from_debug.py"


def _make_lesson(wiki: pathlib.Path, num: int = 99, slug: str = "test-lesson") -> pathlib.Path:
    """Create a minimal fake LESSON file and return its path."""
    lessons_dir = wiki / "pages" / "lessons" / "individual"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    lesson_path = lessons_dir / f"LESSON-{num:03d}-{slug}.md"
    lesson_path.write_text(
        f"---\n"
        f"lesson_id: LESSON-{num:03d}\n"
        f"date: 2026-04-01\n"
        f"status: unabsorbed\n"
        f"---\n\n"
        f"# Test lesson {num}\n\n"
        f"Root cause: something went wrong.\n"
        f"Prevention: do it right next time.\n"
    )
    return lesson_path


def test_creates_draft_skill_under_extracted():
    """Given a LESSON file, creates draft SKILL.md under pages/skills/extracted/<slug>/."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = pathlib.Path(tmp)
        lesson_path = _make_lesson(wiki, num=99, slug="test-lesson")

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--lesson", str(lesson_path), "--wiki", tmp],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        draft_path = wiki / "pages" / "skills" / "extracted" / "test-lesson" / "SKILL.md"
        assert draft_path.exists(), f"Draft SKILL.md not found at {draft_path}"
        print(f"PASS: draft created at {draft_path}")


def test_draft_has_draft_true_in_frontmatter():
    """Draft SKILL.md must have 'draft: true' in its YAML frontmatter."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = pathlib.Path(tmp)
        lesson_path = _make_lesson(wiki, num=42, slug="another-lesson")

        subprocess.run(
            [sys.executable, str(SCRIPT), "--lesson", str(lesson_path), "--wiki", tmp],
            capture_output=True,
            text=True,
            check=True,
        )

        draft_path = wiki / "pages" / "skills" / "extracted" / "another-lesson" / "SKILL.md"
        content = draft_path.read_text()
        assert "draft: true" in content, (
            f"'draft: true' not found in frontmatter:\n{content[:500]}"
        )
        assert content.startswith("---"), "Must start with YAML frontmatter"
        print("PASS: draft: true in frontmatter")


def test_does_not_write_to_existing_skills():
    """Draft must NOT write to pages/skills/<name>/SKILL.md (only to extracted/)."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = pathlib.Path(tmp)
        lesson_path = _make_lesson(wiki, num=55, slug="gbrain-ops")

        # Create a fake existing skill
        existing_skill_dir = wiki / "pages" / "skills" / "gbrain-ops"
        existing_skill_dir.mkdir(parents=True)
        existing_skill = existing_skill_dir / "SKILL.md"
        original_content = "# EXISTING SKILL — must not be modified\n"
        existing_skill.write_text(original_content)

        subprocess.run(
            [sys.executable, str(SCRIPT), "--lesson", str(lesson_path), "--wiki", tmp],
            capture_output=True,
            text=True,
            check=True,
        )

        # Existing skill must be untouched
        assert existing_skill.read_text() == original_content, (
            "Existing skill was modified — must be read-only from skill_from_debug.py"
        )

        # Draft must go to extracted/
        draft_path = wiki / "pages" / "skills" / "extracted" / "gbrain-ops" / "SKILL.md"
        assert draft_path.exists(), f"Draft not created at {draft_path}"
        print("PASS: existing skill untouched, draft in extracted/")


def test_source_lesson_in_frontmatter():
    """Draft frontmatter must reference the source LESSON ID."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = pathlib.Path(tmp)
        lesson_path = _make_lesson(wiki, num=77, slug="my-bug-fix")

        subprocess.run(
            [sys.executable, str(SCRIPT), "--lesson", str(lesson_path), "--wiki", tmp],
            capture_output=True,
            text=True,
            check=True,
        )

        draft_path = wiki / "pages" / "skills" / "extracted" / "my-bug-fix" / "SKILL.md"
        content = draft_path.read_text()
        assert "LESSON-077" in content, f"LESSON-077 reference not found in draft:\n{content[:500]}"
        assert "source_lesson:" in content, "source_lesson field missing"
        print("PASS: source_lesson LESSON-077 in draft frontmatter")


def test_exits_nonzero_on_missing_lesson():
    """Script must exit non-zero if lesson file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--lesson",
                "pages/lessons/individual/LESSON-999-nonexistent.md",
                "--wiki",
                tmp,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"Expected non-zero exit for missing lesson, got {result.returncode}"
        )
        print(f"PASS: exits non-zero for missing lesson (code {result.returncode})")


if __name__ == "__main__":
    test_creates_draft_skill_under_extracted()
    test_draft_has_draft_true_in_frontmatter()
    test_does_not_write_to_existing_skills()
    test_source_lesson_in_frontmatter()
    test_exits_nonzero_on_missing_lesson()
    print("\nAll tests passed!")
