#!/usr/bin/env python3
"""check_resolvable.py — find dark capabilities in the Nous skill graph.

Compares the RESOLVER.md routing table against SKILL.md files on disk.
Reports:
  DARK   — skill exists on disk but is unreachable from RESOLVER.md
  ORPHAN — skill referenced in RESOLVER.md but file does not exist
  OK     — referenced and exists

Garry Tan pattern: dark capabilities rot. If a skill isn't routable,
it might as well not exist.

Exit 0 if everything is OK, exit 1 if any DARK or ORPHAN found.
"""

import argparse
import os
import re
import sys
from pathlib import Path


def parse_resolver(resolver_path: str) -> dict[str, list[int]]:
    """Extract all skill paths from RESOLVER.md.

    Returns a dict mapping normalised relative paths (e.g.
    "skills/_gbrain/query/SKILL.md") to the list of line numbers
    where they appear.
    """
    refs: dict[str, list[int]] = {}
    # Match backtick-quoted paths like `skills/_gbrain/query/SKILL.md`
    # and also bare paths ending in SKILL.md or .md inside table cells.
    pattern = re.compile(r'`(skills/[^`]+/SKILL\.md(?:\s*\([^)]*\))?)`')
    # Secondary: catch paths not in backticks (table cells sometimes omit them)
    bare_pattern = re.compile(r'(?<![`\w])(skills/[^\s|`]+/SKILL\.md)')

    with open(resolver_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            for m in pattern.finditer(line):
                raw = m.group(1).strip()
                # Strip trailing notes like " (extraction sections)"
                clean = re.sub(r'\s*\(.*\)\s*$', '', raw)
                refs.setdefault(clean, []).append(lineno)
            for m in bare_pattern.finditer(line):
                raw = m.group(1).strip()
                clean = re.sub(r'\s*\(.*\)\s*$', '', raw)
                refs.setdefault(clean, []).append(lineno)

    return refs


def find_skill_files(wiki_root: str) -> set[str]:
    """Walk the skills directory and return all SKILL.md relative paths.

    Paths are relative to the wiki pages/ directory so they match
    RESOLVER.md references (e.g. "skills/audit/SKILL.md").
    """
    skills_dir = Path(wiki_root) / "pages" / "skills"
    found: set[str] = set()
    if not skills_dir.is_dir():
        return found

    for skill_md in skills_dir.rglob("SKILL.md"):
        # Build relative path from pages/ parent
        rel = skill_md.relative_to(skills_dir.parent)
        found.add(str(rel))

    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit skill resolvability: find dark and orphan capabilities."
    )
    parser.add_argument(
        "--wiki",
        default="/root/nous-agaas/wiki",
        help="Path to wiki root (default: /root/nous-agaas/wiki)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of human-readable text",
    )
    args = parser.parse_args()

    wiki = Path(args.wiki)
    # Canonical resolver lives at pages/skills/_gbrain/RESOLVER.md (session 67,
    # 2026-04-23: deduped from older pages/skills/_gbrain-RESOLVER.md which was
    # a stale snapshot the audit tools were silently reading while the runtime
    # context_injector_v2 read the canonical file — DRY-failure caused audit-lies).
    resolver_path = wiki / "pages" / "skills" / "_gbrain" / "RESOLVER.md"

    if not resolver_path.is_file():
        # Fallback to legacy path for transitional safety
        legacy = wiki / "pages" / "skills" / "_gbrain-RESOLVER.md"
        if legacy.is_file():
            resolver_path = legacy
        else:
            print(f"ERROR: RESOLVER.md not found at {resolver_path}", file=sys.stderr)
            return 2

    # 1. Parse RESOLVER.md
    resolver_refs = parse_resolver(str(resolver_path))

    # 2. Find all SKILL.md files on disk
    disk_skills = find_skill_files(str(wiki))

    # 3. Normalise resolver keys to match disk paths
    resolver_keys = set(resolver_refs.keys())

    ok = sorted(resolver_keys & disk_skills)
    orphan = sorted(resolver_keys - disk_skills)
    dark = sorted(disk_skills - resolver_keys)

    # 4. Output
    if args.json:
        import json
        report = {
            "ok": ok,
            "dark": dark,
            "orphan": orphan,
            "counts": {
                "ok": len(ok),
                "dark": len(dark),
                "orphan": len(orphan),
                "total_on_disk": len(disk_skills),
                "total_in_resolver": len(resolver_keys),
            },
        }
        print(json.dumps(report, indent=2))
    else:
        w = 60
        print("=" * w)
        print("  SKILL RESOLVABILITY AUDIT")
        print("=" * w)
        print(f"  RESOLVER.md : {resolver_path}")
        print(f"  Skills dir  : {wiki / 'pages' / 'skills'}")
        print(f"  Referenced  : {len(resolver_keys)}")
        print(f"  On disk     : {len(disk_skills)}")
        print("-" * w)

        if dark:
            print(f"\n  DARK ({len(dark)}) — on disk but NOT in RESOLVER:")
            for s in dark:
                print(f"    [-] {s}")
        else:
            print("\n  DARK: none (good)")

        if orphan:
            print(f"\n  ORPHAN ({len(orphan)}) — in RESOLVER but NOT on disk:")
            for s in orphan:
                lines = resolver_refs.get(s, [])
                loc = f" (lines {', '.join(map(str, lines))})"
                print(f"    [!] {s}{loc}")
        else:
            print("\n  ORPHAN: none (good)")

        if ok:
            print(f"\n  OK ({len(ok)}) — referenced and exists:")
            for s in ok:
                print(f"    [+] {s}")
        else:
            print("\n  OK: none")

        print("\n" + "-" * w)
        total_issues = len(dark) + len(orphan)
        if total_issues == 0:
            print("  RESULT: ALL CLEAR — every skill is routable")
        else:
            print(f"  RESULT: {total_issues} issue(s) found")
            if dark:
                print(f"    {len(dark)} dark skill(s) — add to RESOLVER.md or delete")
            if orphan:
                print(f"    {len(orphan)} orphan ref(s) — create the SKILL.md or remove from RESOLVER")
        print("=" * w)

    has_issues = bool(dark or orphan)
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
