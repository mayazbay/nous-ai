#!/usr/bin/env python3
"""Audit Obsidian/gbrain/OpenClaw library metadata quality.

The vault is the source of truth. This scanner classifies markdown pages into
library tiers, reports metadata violations, checks top-level skill resolver
coverage, and can validate an externally captured gbrain retrieval proof.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


MARKDOWN_ROOTS = ("pages", "laws")

TIER_A_PATTERNS = (
    re.compile(r"^laws/[^/]+\.md$"),
    re.compile(r"^pages/laws/[^/]+\.md$"),
    re.compile(r"^pages/skills/[^/]+/SKILL\.md$"),
    re.compile(r"^pages/tenants/[^/]+/skills/.+/SKILL\.md$"),
    re.compile(r"^pages/systems/.+\.md$"),
    re.compile(r"^pages/entities/.+\.md$"),
    re.compile(r"^pages/projects/.+\.md$"),
    re.compile(r"^pages/concepts/.+\.md$"),
)

TIER_B_PATTERNS = (
    re.compile(r"^pages/audits/.+\.md$"),
    re.compile(r"^pages/specs/.+\.md$"),
    re.compile(r"^pages/plans/.+\.md$"),
    re.compile(r"^pages/progress/plans/.+\.md$"),
    re.compile(r"^pages/dashboards/.+\.md$"),
    re.compile(r"^pages/progress/HANDOFF.+\.md$"),
    re.compile(r"^pages/task-results/.+\.md$"),
    re.compile(r"^pages/tenants/[^/]+/(?!skills/).+\.md$"),
    re.compile(r"^pages/sources/.+\.md$"),
    re.compile(r"^pages/skills/_gbrain/.+\.md$"),
    re.compile(r"^pages/concepts/.+source.+/.+\.md$"),
    re.compile(r"^pages/concepts/.+upstream.+/.+\.md$"),
    re.compile(r"^pages/concepts/gbrain-minions-upstream-.+/.+\.md$"),
)

TIER_C_PATTERNS = (
    re.compile(r"^pages/progress/claude-memory/.+\.md$"),
    re.compile(r"^pages/skills/extracted/.+\.md$"),
    re.compile(r"^pages/lessons/.+\.md$"),
    re.compile(r"^pages/progress/commit-review-.+\.md$"),
)

EXACT_EXCEPTION_RE = re.compile(r"`((?:pages|laws)/[^`]+\.md)`")
PATTERN_EXCEPTION_RE = re.compile(r"pattern:\s*`((?:pages|laws)/[^`]+)`")
REQUIRED_EXCEPTION_FIELDS = ("reason:", "owner:", "review:")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def parse_frontmatter(text: str) -> tuple[dict[str, str], bool]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, False

    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm, True
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            value = match.group(2).strip().strip('"').strip("'")
            fm[match.group(1)] = value
    return fm, False


def first_h1(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def page_title(fm: dict[str, str]) -> str:
    for key in ("title", "name"):
        value = fm.get(key, "").strip()
        if value:
            return value
    return ""


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().casefold())


def classify(path: str) -> str:
    if path.startswith("pages/skills/_gbrain/"):
        return "B"
    if path.startswith("pages/skills/extracted/"):
        return "C"
    if any(pattern.search(path) for pattern in TIER_C_PATTERNS):
        return "C"
    if any(pattern.search(path) for pattern in TIER_B_PATTERNS):
        return "B"
    if any(pattern.search(path) for pattern in TIER_A_PATTERNS):
        return "A"
    return "C"


def load_exceptions(
    root: Path, exception_path: str
) -> tuple[set[str], list[str], list[dict[str, Any]]]:
    path = root / exception_path
    if not path.exists():
        return set(), [], []

    exact: set[str] = set()
    patterns: list[str] = []
    invalid: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    for lineno, line in enumerate(text.splitlines(), start=1):
        pattern_matches = PATTERN_EXCEPTION_RE.findall(line)
        exact_matches = [] if pattern_matches else EXACT_EXCEPTION_RE.findall(line)
        if not pattern_matches and not exact_matches:
            continue

        if not all(field in line for field in REQUIRED_EXCEPTION_FIELDS):
            invalid.append(
                {
                    "line": lineno,
                    "text": line.strip(),
                    "message": "exception row must include reason:, owner:, and review:",
                }
            )

        patterns.extend(pattern_matches)
        exact.update(exact_matches)

    return exact, patterns, invalid


def is_exception(path: str, exact: set[str], patterns: list[str]) -> bool:
    return path in exact or any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def issue(
    issues: list[dict[str, Any]],
    *,
    code: str,
    path: str,
    tier: str,
    message: str,
    exception_exact: set[str],
    exception_patterns: list[str],
    title: str = "",
) -> None:
    excepted = is_exception(path, exception_exact, exception_patterns)
    blocking = tier == "A" and not excepted
    issues.append(
        {
            "code": code,
            "path": path,
            "tier": tier,
            "title": title,
            "message": message,
            "exception": excepted,
            "excepted": excepted,
            "blocking": blocking,
        }
    )


def parse_resolver_refs(root: Path) -> set[str]:
    resolver = root / "pages" / "skills" / "_gbrain" / "RESOLVER.md"
    if not resolver.exists():
        return set()
    text = resolver.read_text(encoding="utf-8", errors="replace")
    refs = set(re.findall(r"skills/[^`\s|]+/SKILL\.md", text))
    return {f"pages/{ref}" for ref in refs}


def scan_resolver(
    root: Path,
    issues: list[dict[str, Any]],
    exception_exact: set[str],
    exception_patterns: list[str],
) -> None:
    refs = parse_resolver_refs(root)
    skills_root = root / "pages" / "skills"
    if not skills_root.exists():
        return

    for skill in sorted(skills_root.glob("*/SKILL.md")):
        path = rel(skill, root)
        if "/_gbrain/" in path or "/extracted/" in path:
            continue
        if path not in refs:
            issue(
                issues,
                code="resolver_missing_skill",
                path=path,
                tier="A",
                message="top-level skill exists but is not referenced from pages/skills/_gbrain/RESOLVER.md",
                exception_exact=exception_exact,
                exception_patterns=exception_patterns,
            )


def scan_pages(
    root: Path,
    exception_path: str,
    *,
    include_untracked: bool = False,
) -> dict[str, Any]:
    exception_exact, exception_patterns, invalid_exceptions = load_exceptions(root, exception_path)
    issues: list[dict[str, Any]] = []
    titles: dict[str, list[dict[str, str]]] = defaultdict(list)
    tier_counts = {
        "A": {"page_count": 0, "issue_count": 0, "blocking_count": 0, "exception_count": 0},
        "B": {"page_count": 0, "issue_count": 0, "blocking_count": 0, "exception_count": 0},
        "C": {"page_count": 0, "issue_count": 0, "blocking_count": 0, "exception_count": 0},
    }

    for invalid in invalid_exceptions:
        issues.append(
            {
                "code": "invalid_exception",
                "path": exception_path,
                "tier": "A",
                "title": "Library quality exceptions",
                "message": f"line {invalid['line']}: {invalid['message']}",
                "exception": False,
                "excepted": False,
                "blocking": True,
            }
        )

    pages = iter_library_markdown(root, include_untracked=include_untracked)
    for page in pages:
        path = rel(page, root)
        tier = classify(path)
        tier_counts[tier]["page_count"] += 1

        text = page.read_text(encoding="utf-8", errors="replace")
        fm, has_fm = parse_frontmatter(text)
        title = page_title(fm)
        h1 = first_h1(text)

        if is_exception(path, exception_exact, exception_patterns):
            tier_counts[tier]["exception_count"] += 1

        if not has_fm:
            issue(
                issues,
                code="missing_frontmatter",
                path=path,
                tier=tier,
                message="page has no YAML frontmatter block",
                exception_exact=exception_exact,
                exception_patterns=exception_patterns,
                title=title,
            )
        if not title:
            issue(
                issues,
                code="missing_title",
                path=path,
                tier=tier,
                message="frontmatter lacks title/name",
                exception_exact=exception_exact,
                exception_patterns=exception_patterns,
            )
        if not h1:
            issue(
                issues,
                code="missing_h1",
                path=path,
                tier=tier,
                message="page has no H1 heading",
                exception_exact=exception_exact,
                exception_patterns=exception_patterns,
                title=title,
            )

        visible_title = title or h1
        if visible_title:
            titles[normalize_title(visible_title)].append(
                {"path": path, "tier": tier, "title": visible_title}
            )

    for entries in titles.values():
        tier_a_entries = [entry for entry in entries if entry["tier"] == "A"]
        if len(tier_a_entries) < 2:
            continue
        title = tier_a_entries[0]["title"]
        paths = [entry["path"] for entry in tier_a_entries]
        for entry in tier_a_entries:
            issue(
                issues,
                code="duplicate_title",
                path=entry["path"],
                tier="A",
                message="Tier A title duplicates: " + ", ".join(paths),
                exception_exact=exception_exact,
                exception_patterns=exception_patterns,
                title=title,
            )

    scan_resolver(root, issues, exception_exact, exception_patterns)

    for item in issues:
        counts = tier_counts[item["tier"]]
        counts["issue_count"] += 1
        if item["blocking"]:
            counts["blocking_count"] += 1

    return {
        "root": str(root),
        "exception_manifest": exception_path,
        "exception_patterns": exception_patterns,
        "exception_exact_count": len(exception_exact),
        "invalid_exception_count": len(invalid_exceptions),
        "include_untracked": include_untracked,
        "page_count": len(pages),
        "tiers": tier_counts,
        "issues": issues,
        "blocking_count": sum(1 for item in issues if item["blocking"]),
    }


def is_git_worktree(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def iter_library_markdown(root: Path, *, include_untracked: bool = False) -> list[Path]:
    """Return the library's markdown universe.

    In the real vault, git is the source of truth. Filesystem-only copies such
    as Finder " 2.md" duplicates must not change audit counts or create false
    retrieval issues. Use --include-untracked only for explicit archaeology.
    """

    if is_git_worktree(root) and not include_untracked:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", *MARKDOWN_ROOTS],
            capture_output=True,
            check=True,
        )
        paths = []
        prefixes = tuple(f"{directory}/" for directory in MARKDOWN_ROOTS)
        for raw in result.stdout.split(b"\0"):
            if not raw:
                continue
            line = raw.decode("utf-8", errors="surrogateescape")
            if not line.endswith(".md") or not line.startswith(prefixes):
                continue
            path = root / line
            if path.exists():
                paths.append(path)
        return sorted(paths)

    paths: list[Path] = []
    for directory in MARKDOWN_ROOTS:
        base = root / directory
        if base.exists():
            paths.extend(base.rglob("*.md"))
    return sorted(paths)


def apply_retrieval_proof(report: dict[str, Any], proof_path: str | None) -> None:
    retrieval = {"check_count": 0, "missing_count": 0, "misses": []}
    if not proof_path:
        report["retrieval"] = retrieval
        return

    proof = json.loads(Path(proof_path).read_text(encoding="utf-8"))
    for check in proof.get("checks", []):
        retrieval["check_count"] += 1
        returned = set(check.get("returned", []))
        for expected in check.get("expected", []):
            if expected not in returned:
                retrieval["missing_count"] += 1
                miss = {
                    "query": check.get("query", ""),
                    "expected": expected,
                    "returned": sorted(returned),
                }
                retrieval["misses"].append(miss)
                report["issues"].append(
                    {
                        "code": "retrieval_miss",
                        "path": expected,
                        "tier": "A",
                        "title": check.get("query", ""),
                        "message": "gbrain retrieval proof did not return expected slug",
                        "exception": False,
                        "excepted": False,
                        "blocking": True,
                    }
                )
                report["tiers"]["A"]["issue_count"] += 1
                report["tiers"]["A"]["blocking_count"] += 1

    report["retrieval"] = retrieval
    report["blocking_count"] = sum(1 for item in report["issues"] if item["blocking"])


def print_human(report: dict[str, Any]) -> None:
    print("LIBRARY QUALITY SCAN")
    print(f"root: {report['root']}")
    print(f"pages: {report['page_count']}")
    print(f"include_untracked: {report['include_untracked']}")
    print(f"blocking: {report['blocking_count']}")
    for tier, counts in report["tiers"].items():
        print(
            f"tier {tier}: pages={counts['page_count']} "
            f"issues={counts['issue_count']} blocking={counts['blocking_count']} "
            f"exceptions={counts['exception_count']}"
        )
    for item in report["issues"][:80]:
        marker = "BLOCK" if item["blocking"] else "WARN"
        print(f"{marker} {item['code']} {item['path']} — {item['message']}")
    if len(report["issues"]) > 80:
        print(f"... {len(report['issues']) - 80} more issues")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Vault root (default: cwd)")
    parser.add_argument("--exception-manifest", default="pages/systems/library-quality-exceptions.md")
    parser.add_argument("--retrieval-proof", help="JSON file with gbrain retrieval proof")
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include untracked/ignored filesystem Markdown for explicit archaeology.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Always exit 0 after reporting; useful for baseline capture",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = scan_pages(
        root,
        args.exception_manifest,
        include_untracked=args.include_untracked,
    )
    apply_retrieval_proof(report, args.retrieval_proof)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)

    if args.no_fail:
        return 0
    return 1 if report["blocking_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
