"""Test: ghost_debt_dashboard.py produces correct dashboard with YAML frontmatter."""
import tempfile, os, pathlib, datetime, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _make_wiki(d: pathlib.Path, *, unabsorbed_count: int = 0, skill_count: int = 3):
    """Scaffold a minimal fake wiki tree for testing."""
    # lessons/individual/
    lessons_dir = d / "pages" / "lessons" / "individual"
    lessons_dir.mkdir(parents=True)
    for i in range(1, 6):
        status = "unabsorbed" if i <= unabsorbed_count else "absorbed"
        # make old enough to be a ghost
        date_str = "2026-03-01" if i <= unabsorbed_count else "2026-04-10"
        (lessons_dir / f"LESSON-{i:03d}-test.md").write_text(
            f"---\nlesson_id: LESSON-{i:03d}\ndate: {date_str}\nstatus: {status}\n---\n"
        )

    # pages/skills/ (various skill dirs, plus _gbrain/ and extracted/)
    skills_dir = d / "pages" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "_gbrain").mkdir()
    (skills_dir / "extracted").mkdir()
    for j in range(skill_count):
        skill_dir = skills_dir / f"skill-{j}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# skill-{j}\n")

    # RESOLVER.md
    (skills_dir / "_gbrain" / "RESOLVER.md").write_text("# RESOLVER\n")

    # dashboards dir
    (d / "pages" / "dashboards").mkdir(parents=True)

    return d


def test_dashboard_has_yaml_frontmatter():
    """Dashboard file must have YAML frontmatter with required fields."""
    from ghost_debt_dashboard import compute_metrics, write_dashboard

    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(pathlib.Path(tmp))
        metrics = compute_metrics(wiki)
        out = wiki / "pages" / "dashboards" / "ghost-debt-dashboard.md"
        write_dashboard(metrics, out)

        content = out.read_text()
        assert content.startswith("---"), "Dashboard must start with YAML frontmatter"
        assert "type: dashboard" in content, "Must have type: dashboard"
        assert "id: DASH-GHOST-DEBT" in content, "Must have id DASH-GHOST-DEBT"
        assert "date:" in content, "Must have date field"
        assert "last_updated:" in content, "Must have last_updated"
        assert "---" in content[3:], "Must close frontmatter"
        print("PASS: YAML frontmatter correct")


def test_ghost_count_from_scan_lessons():
    """compute_metrics must call scan_lessons and report unabsorbed_count."""
    from ghost_debt_dashboard import compute_metrics

    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(pathlib.Path(tmp), unabsorbed_count=2, skill_count=3)
        metrics = compute_metrics(wiki, today=datetime.date(2026, 4, 16))

        assert metrics["unabsorbed_count"] == 2, (
            f"Expected 2 ghosts, got {metrics['unabsorbed_count']}"
        )
        print(f"PASS: unabsorbed_count == {metrics['unabsorbed_count']}")


def test_skill_count_excludes_extracted_and_gbrain():
    """skill_count must exclude extracted/ and _gbrain/ dirs."""
    from ghost_debt_dashboard import compute_metrics

    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(pathlib.Path(tmp), skill_count=4)
        metrics = compute_metrics(wiki)

        # We created 4 skill dirs + _gbrain + extracted — expect exactly 4
        assert metrics["skill_count"] == 4, (
            f"Expected 4 skills (excluding extracted+_gbrain), got {metrics['skill_count']}"
        )
        print(f"PASS: skill_count == {metrics['skill_count']}")


def test_resolver_exists_flag():
    """resolver_exists must be True when RESOLVER.md is present."""
    from ghost_debt_dashboard import compute_metrics

    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(pathlib.Path(tmp))
        metrics = compute_metrics(wiki)
        assert metrics["resolver_exists"] is True, "RESOLVER.md should be found"

    # Without RESOLVER.md
    with tempfile.TemporaryDirectory() as tmp2:
        wiki2 = _make_wiki(pathlib.Path(tmp2))
        (wiki2 / "pages" / "skills" / "_gbrain" / "RESOLVER.md").unlink()
        metrics2 = compute_metrics(wiki2)
        assert metrics2["resolver_exists"] is False, "RESOLVER.md absent → False"

    print("PASS: resolver_exists correct in both cases")


def test_exits_0_when_healthy():
    """Script exits 0 when unabsorbed_count <= 2."""
    import subprocess, sys

    script = pathlib.Path(__file__).parent / "ghost_debt_dashboard.py"
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(pathlib.Path(tmp), unabsorbed_count=0, skill_count=3)
        result = subprocess.run(
            [sys.executable, str(script), "--wiki", tmp],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        print(f"PASS: exit 0 on healthy metrics (stdout: {result.stdout.strip()!r})")


def test_exits_1_when_too_many_ghosts():
    """Script exits 1 when unabsorbed_count > 2."""
    import subprocess, sys

    script = pathlib.Path(__file__).parent / "ghost_debt_dashboard.py"
    with tempfile.TemporaryDirectory() as tmp:
        wiki = _make_wiki(pathlib.Path(tmp), unabsorbed_count=3, skill_count=3)
        result = subprocess.run(
            [sys.executable, str(script), "--wiki", tmp],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Expected exit 1, got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        print(f"PASS: exit 1 on degraded metrics (stdout: {result.stdout.strip()!r})")


if __name__ == "__main__":
    test_dashboard_has_yaml_frontmatter()
    test_ghost_count_from_scan_lessons()
    test_skill_count_excludes_extracted_and_gbrain()
    test_resolver_exists_flag()
    test_exits_0_when_healthy()
    test_exits_1_when_too_many_ghosts()
    print("\nAll tests passed!")
