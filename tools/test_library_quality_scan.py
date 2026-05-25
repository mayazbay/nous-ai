"""Tests for library_quality_scan.py."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile


SCRIPT = pathlib.Path(__file__).parent / "library_quality_scan.py"


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_scan(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--json", *args],
        capture_output=True,
        text=True,
    )


def git(root: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def payload(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout, f"expected json stdout, stderr={result.stderr}"
    return json.loads(result.stdout)


def exception_manifest_line(target: str, *, pattern: bool = False) -> str:
    prefix = "pattern: " if pattern else ""
    return f"- {prefix}`{target}` - reason: test fixture; owner: substrate; review: 2026-07-31\n"


def test_skill_name_plus_h1_is_valid_tier_a_title() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "skills" / "audit" / "SKILL.md",
            "---\ntype: skill\nname: audit\nversion: 1.0.0\n---\n\n# audit v1.0.0\n",
        )
        write(
            root / "pages" / "skills" / "_gbrain" / "RESOLVER.md",
            "---\ntype: system\ntitle: Resolver\n---\n\n# Resolver\n\n- [[skills/audit/SKILL.md]]\n",
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["tiers"]["A"]["page_count"] == 1
        assert data["blocking_count"] == 0


def test_skill_name_without_h1_still_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "skills" / "audit" / "SKILL.md",
            "---\ntype: skill\nname: audit\nversion: 1.0.0\n---\n\nbody only\n",
        )
        write(
            root / "pages" / "skills" / "_gbrain" / "RESOLVER.md",
            "---\ntype: system\ntitle: Resolver\n---\n\n# Resolver\n\n- [[skills/audit/SKILL.md]]\n",
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 1
        assert data["blocking_count"] == 1
        assert [issue["code"] for issue in data["issues"]] == ["missing_h1"]


def test_tier_a_core_page_missing_frontmatter_title_and_h1_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "entities" / "camera-node.md", "body only\n")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 1
        assert data["blocking_count"] == 3
        assert {
            issue["code"] for issue in data["issues"] if issue["path"] == "pages/entities/camera-node.md"
        } == {"missing_frontmatter", "missing_title", "missing_h1"}


def test_frontmatter_id_does_not_count_as_catalog_title() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "entities" / "camera-node.md",
            "---\ntype: entity\nid: camera-node\n---\n\n# Camera Node\n",
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 1
        assert data["blocking_count"] == 1
        assert [issue["code"] for issue in data["issues"]] == ["missing_title"]


def test_laws_and_pages_laws_are_tier_a_pages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "laws" / "LAW-999-test.md", "# Law Without Frontmatter\n")
        write(root / "pages" / "laws" / "LAW-998-test.md", "# Page Law Without Frontmatter\n")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 1
        assert data["page_count"] == 2
        assert data["tiers"]["A"]["page_count"] == 2
        assert {
            issue["code"]
            for issue in data["issues"]
            if issue["path"] in {"laws/LAW-999-test.md", "pages/laws/LAW-998-test.md"}
        } == {"missing_frontmatter", "missing_title"}


def test_report_streams_are_tier_b_warning_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "audits" / "AUDIT-999.md", "body only\n")
        write(root / "pages" / "specs" / "SPEC-999.md", "body only\n")
        write(root / "pages" / "plans" / "PLAN-999.md", "body only\n")
        write(root / "pages" / "progress" / "plans" / "PLAN-999.md", "body only\n")
        write(root / "pages" / "dashboards" / "dashboard.md", "body only\n")
        write(root / "pages" / "progress" / "HANDOFF-AUTO-test.md", "body only\n")
        write(root / "pages" / "task-results" / "result.md", "body only\n")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["blocking_count"] == 0
        assert data["tiers"]["B"]["page_count"] == 7
        assert data["tiers"]["B"]["issue_count"] == 21


def test_tier_b_audit_is_warning_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "audits" / "AUDIT-999.md", "body only\n")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["blocking_count"] == 0
        assert data["tiers"]["B"]["page_count"] == 1
        assert {issue["code"] for issue in data["issues"]} == {
            "missing_frontmatter",
            "missing_title",
            "missing_h1",
        }


def test_tier_b_exception_does_not_block() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "sources" / "vendor-dump.md", "raw imported text\n")
        write(
            root / "pages" / "systems" / "library-quality-exceptions.md",
            "---\ntype: system\ntitle: Library quality exceptions\n---\n\n"
            "# Library quality exceptions\n\n"
            + exception_manifest_line("pages/sources/vendor-dump.md"),
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["blocking_count"] == 0
        assert data["tiers"]["B"]["exception_count"] == 1
        assert all(issue["excepted"] for issue in data["issues"])


def test_pattern_exception_classifies_legacy_archive_pages() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "progress" / "claude-memory" / "MEMORY.md", "memory dump\n")
        write(
            root / "pages" / "systems" / "library-quality-exceptions.md",
            "---\ntype: system\ntitle: Library quality exceptions\n---\n\n"
            "# Library quality exceptions\n\n"
            + exception_manifest_line("pages/progress/claude-memory/*.md", pattern=True),
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["blocking_count"] == 0
        assert data["tiers"]["C"]["exception_count"] == 1


def test_malformed_exception_metadata_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "sources" / "vendor-dump.md", "raw imported text\n")
        write(
            root / "pages" / "systems" / "library-quality-exceptions.md",
            "---\ntype: system\ntitle: Library quality exceptions\n---\n\n"
            "# Library quality exceptions\n\n"
            "- `pages/sources/vendor-dump.md` - reason: missing owner and review\n",
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 1
        assert data["invalid_exception_count"] == 1
        assert any(issue["code"] == "invalid_exception" for issue in data["issues"])


def test_duplicate_tier_a_titles_block() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in ("alpha.md", "beta.md"):
            write(
                root / "pages" / "entities" / name,
                "---\ntype: entity\ntitle: Same Title\n---\n\n# Same Title\n",
            )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 1
        assert data["blocking_count"] == 2
        assert [i["code"] for i in data["issues"]].count("duplicate_title") == 2


def test_duplicate_exception_allowlist_can_make_duplicates_non_blocking() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in ("alpha.md", "beta.md"):
            write(
                root / "pages" / "entities" / name,
                "---\ntype: entity\ntitle: Same Title\n---\n\n# Same Title\n",
            )
        write(
            root / "pages" / "systems" / "library-quality-exceptions.md",
            "---\ntype: system\ntitle: Library quality exceptions\n---\n\n"
            "# Library quality exceptions\n\n"
            + exception_manifest_line("pages/entities/alpha.md")
            + exception_manifest_line("pages/entities/beta.md"),
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["blocking_count"] == 0
        assert [i["code"] for i in data["issues"]].count("duplicate_title") == 2
        assert all(i["excepted"] for i in data["issues"])


def test_git_worktree_ignores_untracked_filesystem_ghosts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "entities" / "good-entity.md",
            "---\ntype: entity\ntitle: Good Entity\n---\n\n# Good Entity\n",
        )
        write(root / "pages" / "entities" / "UNTRACKED.md", "body only\n")
        git(root, "init")
        git(root, "add", "pages/entities/good-entity.md")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["include_untracked"] is False
        assert data["page_count"] == 1
        assert data["blocking_count"] == 0


def test_git_worktree_include_untracked_is_explicit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "entities" / "camera-node.md",
            "---\ntype: entity\ntitle: Camera Node\n---\n\n# Camera Node\n",
        )
        write(root / "pages" / "entities" / "camera-node 2.md", "filesystem ghost\n")
        git(root, "init")
        git(root, "add", "pages/entities/camera-node.md")

        result = run_scan(root, "--include-untracked")
        data = payload(result)

        assert result.returncode == 1
        assert data["include_untracked"] is True
        assert data["page_count"] == 2
        assert any(issue["path"].endswith(" 2.md") and issue["blocking"] for issue in data["issues"])


def test_git_worktree_uses_nul_safe_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        tracked = root / "pages" / "entities" / "entity-non-ascii-\u00e9.md"
        write(tracked, "---\ntype: entity\ntitle: Entity Accent\n---\n\n# Entity Accent\n")
        git(root, "init")
        git(root, "add", "pages/entities")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["page_count"] == 1
        assert data["blocking_count"] == 0


def test_tenant_skill_docs_are_tier_a_but_tenant_notes_are_tier_b() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "tenants" / "satory" / "skills" / "owner-routing" / "SKILL.md",
            "---\ntype: skill\nname: owner-routing\nversion: 1.0.0\n---\n\n# owner-routing v1.0.0\n",
        )
        write(root / "pages" / "tenants" / "satory" / "notes" / "raw.md", "body only\n")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["tiers"]["A"]["page_count"] == 1
        assert data["tiers"]["B"]["page_count"] == 1
        assert data["blocking_count"] == 0


def test_legacy_receipts_are_tier_c_non_blocking() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "progress" / "claude-memory" / "MEMORY.md", "memory dump\n")
        write(root / "pages" / "lessons" / "individual" / "LESSON-001-old.md", "old receipt\n")
        write(root / "pages" / "skills" / "extracted" / "draft.md", "draft\n")

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 0
        assert data["blocking_count"] == 0
        assert data["tiers"]["C"]["page_count"] == 3


def test_resolver_missing_skill_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "skills" / "audit" / "SKILL.md",
            "---\ntype: skill\nname: audit\nversion: 1.0.0\n---\n\n# audit v1.0.0\n",
        )
        write(
            root / "pages" / "skills" / "_gbrain" / "RESOLVER.md",
            "---\ntype: system\ntitle: Resolver\n---\n\n# Resolver\n\n",
        )

        result = run_scan(root)
        data = payload(result)

        assert result.returncode == 1
        assert any(
            issue["code"] == "resolver_missing_skill"
            and issue["path"] == "pages/skills/audit/SKILL.md"
            for issue in data["issues"]
        )


def test_valid_tier_a_and_retrieval_proof_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(
            root / "pages" / "entities" / "audit-one.md",
            "---\ntype: entity\ntitle: Audit One\n---\n\n# Audit One\n",
        )
        proof = root / "proof.json"
        proof.write_text(
            json.dumps(
                {
                    "checks": [
                        {
                            "query": "audit one",
                            "expected": ["pages/entities/audit-one"],
                            "returned": ["pages/entities/audit-one"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = run_scan(root, "--retrieval-proof", str(proof))
        data = payload(result)

        assert result.returncode == 0
        assert data["blocking_count"] == 0
        assert data["retrieval"]["missing_count"] == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS: {name}")
    print("All library quality scan tests passed.")
