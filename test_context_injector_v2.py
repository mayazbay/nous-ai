#!/usr/bin/env python3
"""
test_context_injector_v2.py — TDD tests for progressive-disclosure context injector.

Tests:
  1. inject=False returns task unchanged
  2. Skill catalog is included and concise
  3. Top-2 skill matching works (keyword overlap)
  4. HANDOFF summary is truncated (≤30 lines)
  5. Output is ≤12 KB (vs v1's ~21 KB)
  6. Hard cap enforcement at MAX_CONTEXT_CHARS_V2
  7. Feature flag integration (CONTEXT_INJECTOR_V2 env var)

Run: python3 test_context_injector_v2.py
"""

import os
import re
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0


def assert_true(condition, label):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}")


def _build_test_wiki(tmp: Path):
    """Create a minimal wiki tree for testing.

    Returns (wiki_root, skills_root) tuple.
    skills_root contains _gbrain/RESOLVER.md and skill dirs.
    wiki_root contains pages/skills/ skill dirs + pages/progress/ HANDOFFs.
    """

    # Skills root (separate from wiki, like real Air layout)
    skills_root = tmp / "skills"
    resolver_dir = skills_root / "_gbrain"
    resolver_dir.mkdir(parents=True)
    (resolver_dir / "RESOLVER.md").write_text(textwrap.dedent("""\
        # Skill Resolver

        ## AGaaS Factory

        | Trigger | Skill |
        |---------|-------|
        | Camera health check, ISAPI event subscribe, Hikvision | `skills/camera-management/SKILL.md` |
        | Satory dashboard, portal broken, cameras not reflecting | `skills/satory-dashboard/SKILL.md` |
        | Deploy website, satory.nousagaas.com, rollback | `skills/website-deploy/SKILL.md` |
        | Plan, scope a new task, planning | `skills/planning-discipline/SKILL.md` |
        | "What do we know about", "tell me about", "search for" | `skills/_gbrain/query/SKILL.md` |
        | gbrain, wiki, memory hygiene, absorbing lessons | `skills/gbrain-ops/SKILL.md` |
        | Audit, health check, subsystem check | `skills/audit/SKILL.md` |
    """))

    # Skill files — create in wiki pages/skills/ (source of truth)
    for name, body in [
        ("camera-management", "# Camera Management\n\n## Current rules\n\n1. All events to DB\n2. Filter at query\n" + "x\n" * 50),
        ("satory-dashboard", "# Satory Dashboard\n\n## Current rules\n\n1. data_freshness envelope\n2. Never deploy without lock check\n" + "y\n" * 50),
        ("website-deploy", "# Website Deploy\n\n## Current rules\n\n1. 7-gate golden deploy\n2. Rollback procedure\n" + "z\n" * 50),
        ("planning-discipline", "# Planning Discipline\n\n## Current rules\n\n1. Plan before touching\n2. One step at a time\n" + "w\n" * 50),
        ("_gbrain/query", "# GBrain Query\n\n## Current rules\n\n1. Search the brain before external APIs\n2. Return citations\n" + "q\n" * 50),
        ("gbrain-ops", "# GBrain Ops\n\n## Current rules\n\n1. Doctor from gbrain dir\n2. Flock for autopilot\n" + "v\n" * 50),
        ("audit", "# Audit\n\n## Current rules\n\n1. Port 18789 uses nc -z\n2. Parameterized subsystem\n" + "u\n" * 50),
    ]:
        # Wiki path (source of truth — v2 reads skill bodies from here)
        wiki_skill_dir = tmp / "pages" / "skills" / name
        wiki_skill_dir.mkdir(parents=True)
        (wiki_skill_dir / "SKILL.md").write_text(body)

    # HANDOFF file (100 lines — should be truncated to 30)
    progress_dir = tmp / "pages" / "progress"
    progress_dir.mkdir(parents=True)
    handoff_lines = ["---", "type: progress", "title: Test handoff", "---", ""]
    handoff_lines += [f"Line {i}: session state detail" for i in range(1, 96)]
    (progress_dir / "HANDOFF-2026-04-16-test.md").write_text("\n".join(handoff_lines))

    # MEMORY.md (large — should NOT be dumped in v2; only the newest workflow
    # packet may be injected).
    mem_dir = tmp / "pages" / "progress" / "claude-memory"
    mem_dir.mkdir(parents=True)
    (mem_dir / "MEMORY.md").write_text(textwrap.dedent("""\
        # Memory — updated 2026-04-29 session-99 salience-test

        Low-salience shipped narrative that should not survive packet extraction.
        **Proof probes this session:** context-injector tests are the proof surface.
        **Honest red/yellow:** carryover remains for memory workflow packet extraction.
        **Open carryover:** next agent must preserve red/yellow and carryover warnings.
        RULE ZERO upheld: no new LESSON files.

        ---

        # Memory — updated 2026-04-28 older block
        Older memory line that must not enter the newest packet.
    """))

    return tmp, skills_root


def test_inject_false():
    """inject=False returns task unchanged."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("Hello world", wiki_root=wiki, skills_root=skills, inject=False)
        assert_true(result == "Hello world", "inject=False returns task unchanged")


def test_skill_catalog_present():
    """Skill catalog appears in output."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("Check the camera health", wiki_root=wiki, skills_root=skills)
        assert_true("Available skills" in result or "Skill catalog" in result,
                     "Skill catalog section present")
        assert_true("camera-management" in result, "camera-management in catalog")
        assert_true("satory-dashboard" in result, "satory-dashboard in catalog")


def test_top2_skill_matching():
    """Top-2 matched skills are included with full bodies."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("Check the camera health and ISAPI subscribe", wiki_root=wiki, skills_root=skills)
        # camera-management should be top match (ISAPI, camera, health)
        assert_true("Camera Management" in result, "camera-management skill body included")
        assert_true("All events to DB" in result, "camera-management rule content present")


def test_nested_gbrain_skill_matching():
    """Nested skills such as _gbrain/query are parsed and their bodies can be injected."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("search for NIT VPN info", wiki_root=wiki, skills_root=skills)
        assert_true("_gbrain/query" in result, "nested _gbrain/query in catalog or matched section")
        assert_true("GBrain Query" in result, "nested _gbrain/query skill body included")


def test_skill_body_budget_excludes_yaml_frontmatter():
    """Long YAML frontmatter must not consume the matched-skill body budget."""
    from context_injector_v2 import _read_skill_body, MAX_SKILL_CHARS

    with tempfile.TemporaryDirectory() as tmp:
        wiki = Path(tmp)
        skills = wiki / "pages" / "skills"
        skill_dir = wiki / "pages" / "skills" / "gbrain-ops"
        skill_dir.mkdir(parents=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(textwrap.dedent(f"""\
            ---
            type: skill
            name: gbrain-ops
            version: 99.0.0
            description: {"x" * (MAX_SKILL_CHARS + 300)}
            ---

            # GBrain Ops

            ## Current rules

            Critical runtime doctrine survives the cap.
            {"y" * MAX_SKILL_CHARS}
        """))

        result = _read_skill_body(wiki, skills, "gbrain-ops")
        assert_true(result.startswith("# GBrain Ops"), "Skill injection starts at H1 after frontmatter")
        assert_true("Critical runtime doctrine survives the cap" in result, "Skill doctrine survives cap")
        assert_true("description:" not in result[:100], "Frontmatter excluded from skill body budget")


def test_handoff_truncated():
    """HANDOFF summary is ≤30 lines."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("What is the current session state?", wiki_root=wiki, skills_root=skills)
        assert_true("Session state" in result or "HANDOFF" in result.upper(),
                     "HANDOFF section present")
        # The full handoff has 100 lines; v2 should include ≤30
        assert_true("Line 95" not in result, "HANDOFF truncated (line 95 not present)")
        assert_true("Line 1" in result, "HANDOFF includes early lines")


def test_output_size_reduction():
    """v2 output is ≤ G4 threshold (8192 bytes). Enforces GOD_PROMPT gate G4 as a unit invariant."""
    from context_injector_v2 import get_context_v2

    G4_THRESHOLD = 8192  # spec §5 gate G4
    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("Check the camera health", wiki_root=wiki, skills_root=skills)
        size = len(result.encode("utf-8"))
        assert_true(size < G4_THRESHOLD, f"Output ≤ G4 (actual: {size} bytes, threshold: {G4_THRESHOLD})")


def test_no_full_memory_dump_in_v2():
    """v2 does NOT include a full MEMORY.md dump."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("Check the camera health", wiki_root=wiki, skills_root=skills)
        assert_true("Older memory line" not in result, "Older MEMORY.md blocks NOT included in v2")
        assert_true("Low-salience shipped narrative" not in result, "Low-salience MEMORY.md text NOT included")


def test_memory_workflow_packet_keeps_warnings():
    """Latest MEMORY top-block contributes only capped workflow-salient lines."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("gbrain memory hygiene", wiki_root=wiki, skills_root=skills)
        assert_true("Memory workflow packet" in result, "Memory workflow packet section present")
        assert_true("Honest red/yellow" in result, "Memory packet includes red/yellow warnings")
        assert_true("Open carryover" in result, "Memory packet includes carryover")
        assert_true("RULE ZERO upheld" in result, "Memory packet includes RULE ZERO signal")
        assert_true("Low-salience shipped narrative" not in result, "Memory packet excludes low-salience narrative")


def test_memory_workflow_packet_supports_mercury_now_context():
    """Mercury MEMORY format must keep salience without legacy block headers."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        memory_path = wiki / "pages" / "progress" / "claude-memory" / "MEMORY.md"
        memory_path.write_text(textwrap.dedent("""\
            # Now context (live, regenerated per session-start)
            - date: 2026-04-29
            - Madi directive (sticky): best CTO/CEO + Musk Algorithm + Karpathy/Tan compounding.

            # Mercury fact-block (top-K selective injection)

            ## Active carryover (BLOCKED + DEFERRED)
            - carryover.stanza-0.blocked: BLOCKED + DEFERRED work remains.

            ## Laws
            - law.law-015: LAW-015: Root Cause Evolution [[[LAW-015-root-cause-evolution]]]
            - law.law-017: LAW-017: Success Is Skill [[[LAW-017-success-is-skill]]]

            ## Other
            - low.signal: Low-salience shipped narrative that should stay out.
        """))
        result = get_context_v2("gbrain memory hygiene", wiki_root=wiki, skills_root=skills)
        assert_true("Memory workflow packet" in result, "Mercury memory packet section present")
        assert_true("Madi directive" in result, "Mercury packet includes directive")
        assert_true("Active carryover" in result, "Mercury packet includes carryover")
        assert_true("RULE ZERO signal" in result, "Mercury packet normalizes RULE ZERO from laws")
        assert_true("Low-salience shipped narrative" not in result, "Mercury packet excludes low-salience narrative")


def test_live_vault_context_budget():
    """Current live vault context stays under byte and approximate token budget."""
    from context_injector_v2 import get_context_v2

    repo = Path(__file__).resolve().parent.parent
    wiki_root = repo if (repo / "pages" / "skills").is_dir() else repo / "wiki"
    skills_root = wiki_root / "pages" / "skills"
    prompts = [
        "gbrain memory hygiene",
        "factory checkpoint",
        "session operating contract",
        "storage retrieval",
    ]

    for prompt in prompts:
        result = get_context_v2(prompt, wiki_root=wiki_root, skills_root=skills_root)
        byte_size = len(result.encode("utf-8"))
        approx_tokens = len(re.findall(r"\w+|[^\s\w]", result, re.UNICODE))
        assert_true(byte_size < 8192, f"Live context bytes under G4 for {prompt!r}: {byte_size}")
        assert_true(approx_tokens < 2300, f"Live approx tokens under cap for {prompt!r}: {approx_tokens}")
        assert_true("### Matched skill:" in result, f"Live matched skill survives trim for {prompt!r}")

    memory_result = get_context_v2("gbrain memory hygiene", wiki_root=wiki_root, skills_root=skills_root)
    assert_true("### Memory workflow packet" in memory_result, "Live MEMORY workflow packet survives trim")
    assert_true("RULE ZERO" in memory_result, "Live MEMORY workflow packet includes RULE ZERO signal")


def test_rule_zero_no_required_lesson_language():
    """Active skills must not say a LESSON page is required for bug fixes."""
    repo = Path(__file__).resolve().parent.parent
    repo = repo if (repo / "pages" / "skills").is_dir() else repo / "wiki"
    offenders = []
    for skill in (repo / "pages" / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        if "A LESSON page (required for bug fixes" in text:
            offenders.append(str(skill.relative_to(repo)))

    assert_true(not offenders, "No active skill requires new LESSON pages under RULE ZERO")


def test_hard_cap():
    """Hard cap at MAX_CONTEXT_CHARS_V2 is enforced."""
    from context_injector_v2 import get_context_v2, MAX_CONTEXT_CHARS_V2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        # Create oversized skills to trigger cap
        for i in range(20):
            skill_dir = Path(tmp) / "pages" / "skills" / f"big-skill-{i}"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# Big Skill {i}\n" + "x" * 2000)
        result = get_context_v2("big skill", wiki_root=wiki, skills_root=skills)
        size = len(result.encode("utf-8"))
        # Context portion (without task text) should be under cap + some overhead
        assert_true(size < MAX_CONTEXT_CHARS_V2 + 1000, f"Hard cap enforced (size={size})")


def test_context_structure():
    """Output has proper header/footer structure."""
    from context_injector_v2 import get_context_v2

    with tempfile.TemporaryDirectory() as tmp:
        wiki, skills = _build_test_wiki(Path(tmp))
        result = get_context_v2("Plan a new feature", wiki_root=wiki, skills_root=skills)
        assert_true("--- FACTORY CONTEXT" in result, "Context header present")
        assert_true("--- END CONTEXT ---" in result, "Context footer present")
        assert_true("## TASK" in result, "TASK section present")
        assert_true("Plan a new feature" in result, "Original task text preserved")


if __name__ == "__main__":
    print("=== context_injector_v2 TDD tests ===\n")

    print("Test 1: inject=False")
    test_inject_false()

    print("\nTest 2: Skill catalog present")
    test_skill_catalog_present()

    print("\nTest 3: Top-2 skill matching")
    test_top2_skill_matching()

    print("\nTest 4: Nested _gbrain skill matching")
    test_nested_gbrain_skill_matching()

    print("\nTest 5: Skill body frontmatter budget")
    test_skill_body_budget_excludes_yaml_frontmatter()

    print("\nTest 6: HANDOFF truncation")
    test_handoff_truncated()

    print("\nTest 7: Output size reduction")
    test_output_size_reduction()

    print("\nTest 8: No full MEMORY.md dump in v2")
    test_no_full_memory_dump_in_v2()

    print("\nTest 9: Hard cap enforcement")
    test_hard_cap()

    print("\nTest 10: Context structure")
    test_context_structure()

    print("\nTest 11: Memory workflow packet")
    test_memory_workflow_packet_keeps_warnings()

    print("\nTest 12: Mercury MEMORY packet")
    test_memory_workflow_packet_supports_mercury_now_context()

    print("\nTest 13: Live vault context budget")
    test_live_vault_context_budget()

    print("\nTest 14: RULE ZERO doctrine drift")
    test_rule_zero_no_required_lesson_language()

    print(f"\n{'=' * 40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED ✅")
