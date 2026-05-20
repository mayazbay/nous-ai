"""test_skill_tier_index — TDD test for substrate-v2 Phase 0.8 skill loader.

Verifies tools/skill_tier_index.py emits a valid JSON index of all canonical
Nous skills grouped by tier (1, 2, 3), excluding _gbrain sub-skills.
"""
import json
import pathlib
import subprocess

WIKI_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = WIKI_ROOT / "tools" / "skill_tier_index.py"
SKILLS_DIR = WIKI_ROOT / "pages" / "skills"


def run_index() -> dict:
    out = subprocess.check_output(["python3", str(SCRIPT)])
    return json.loads(out)


def run_counts() -> dict:
    out = subprocess.check_output(["python3", str(SCRIPT), "--counts"])
    return json.loads(out)


def test_script_exists_and_executable():
    assert SCRIPT.exists(), f"{SCRIPT} not created yet"


def test_returns_three_tiers():
    idx = run_index()
    assert set(idx.keys()) == {"1", "2", "3"}, f"unexpected keys: {idx.keys()}"


def test_total_count_matches_filesystem():
    idx = run_index()
    total = sum(len(v) for v in idx.values())
    fs_count = sum(
        1 for d in SKILLS_DIR.iterdir()
        if d.is_dir() and d.name not in {"_gbrain", "extracted"}
        and (d / "SKILL.md").exists()
    )
    assert total == fs_count, f"index has {total} skills, filesystem has {fs_count}"


def test_tier_1_includes_known_standards():
    idx = run_index()
    names = {s["name"] for s in idx["1"]}
    expected = {
        "agent-quality",
        "autonomous-build-manager",
        "evidence-verification",
        "error-classification",
        "karpathy-coding-principles",
        "session-operating-contract",
    }
    assert expected <= names, f"tier-1 missing: {expected - names}"


def test_tier_2_includes_known_methodology():
    idx = run_index()
    names = {s["name"] for s in idx["2"]}
    must_include = {
        "audit",
        "karpathy-loop",
        "library-grade-audit",
        "musk-algorithm",
        "satory-daily-operator-brief",
    }
    assert must_include <= names, f"tier-2 missing: {must_include - names}"


def test_counts_mode_matches_index_and_is_nonzero():
    idx = run_index()
    counts = run_counts()
    assert counts == {
        "tier_1": len(idx["1"]),
        "tier_2": len(idx["2"]),
        "tier_3": len(idx["3"]),
        "total": sum(len(v) for v in idx.values()),
    }
    assert counts["tier_1"] > 0
    assert counts["tier_2"] > 0
    assert counts["tier_3"] > 0


def test_each_entry_has_required_fields():
    idx = run_index()
    for tier, entries in idx.items():
        for entry in entries:
            assert "name" in entry
            assert "path" in entry
            assert "title" in entry
            assert entry["path"].startswith("pages/skills/")
            assert entry["path"].endswith("/SKILL.md")


def test_excludes_gbrain_subskills():
    idx = run_index()
    for tier, entries in idx.items():
        for entry in entries:
            assert "_gbrain" not in entry["path"], f"_gbrain leaked into tier {tier}: {entry}"
            assert "extracted" not in entry["path"], f"extracted/ leaked into tier {tier}: {entry}"


def test_runs_under_one_second():
    """Index generation must be fast enough for session-start."""
    import time
    start = time.time()
    run_index()
    elapsed = time.time() - start
    assert elapsed < 1.0, f"index took {elapsed:.2f}s, target <1.0s"
