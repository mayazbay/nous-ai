#!/usr/bin/env python3
"""Create a draft skill from a lesson file. Manual /skill-capture command.

Usage:
    python3 skill_from_debug.py --lesson pages/lessons/individual/LESSON-NNN-slug.md
    python3 skill_from_debug.py --lesson /abs/path/to/LESSON-NNN-slug.md [--wiki PATH]

The draft is written to:
    pages/skills/extracted/<slug>/SKILL.md

Next steps printed on stdout guide the user to:
  1. Review and extract rules
  2. Either absorb into an existing skill or promote to a new one
  3. Commit both lesson + skill in a single commit

IMPORTANT: This script NEVER writes to pages/skills/<name>/SKILL.md (existing skills).
It only writes drafts to pages/skills/extracted/.

Part of GOD_PROMPT v1.0 automation (Phase P4 task 4/5).
"""
import argparse
import os
import pathlib
import re
import sys
from datetime import date


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Create draft skill from LESSON file (/skill-capture command)"
    )
    ap.add_argument("--lesson", required=True, help="Path to LESSON-NNN-slug.md")
    ap.add_argument(
        "--wiki",
        default=os.path.expanduser("~/nous-agaas/wiki"),
        help="Path to wiki root (default: ~/nous-agaas/wiki)",
    )
    args = ap.parse_args()

    wiki = pathlib.Path(args.wiki)
    lesson_path = pathlib.Path(args.lesson)

    # Resolve path: try absolute, then relative to wiki
    if not lesson_path.is_absolute() and not lesson_path.exists():
        lesson_path = wiki / args.lesson

    if not lesson_path.exists():
        sys.exit(f"NOT FOUND: {args.lesson}")

    content = lesson_path.read_text(errors="replace")

    # Extract lesson number and slug from filename: LESSON-NNN-slug.md
    match = re.search(r"LESSON-(\d+)-(.+)\.md$", lesson_path.name)
    if not match:
        sys.exit(f"Cannot parse lesson ID from filename: {lesson_path.name!r}\n"
                 f"Expected format: LESSON-NNN-slug.md")

    lesson_num = match.group(1)
    slug = match.group(2)

    # Draft goes to extracted/ — NEVER to pages/skills/<slug>/
    draft_dir = wiki / "pages" / "skills" / "extracted" / slug
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "SKILL.md"

    # Extract title from lesson h1 if present
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else slug

    today = date.today().isoformat()
    lesson_ref = f"LESSON-{lesson_num}-{slug}"

    draft_content = (
        "---\n"
        f"name: {slug}\n"
        f'description: "DRAFT — created from LESSON-{lesson_num}. Review and promote or absorb into existing skill."\n'
        "type: skill\n"
        f"id: SKILL-DRAFT-{slug.upper().replace('-', '_')}\n"
        "version: 0.1.0\n"
        "status: draft\n"
        "draft: true\n"
        f"source_lesson: LESSON-{lesson_num}-{slug}\n"
        f"absorbs_lessons: [LESSON-{lesson_num}]\n"
        f"tags: [skill, draft, extracted, {today}]\n"
        f"date: {today}\n"
        "source_count: 1\n"
        f"last_updated: {today}\n"
        "related: [mistake-to-skill]\n"
        "---\n"
        "\n"
        f"# {slug} (DRAFT)\n"
        "\n"
        f"**Source:** [[{lesson_ref}]]\n"
        "\n"
        "## Current rules (compiled truth)\n"
        "\n"
        "TODO: Extract actionable rules from the lesson below. Each rule should be:\n"
        "- One sentence imperative\n"
        "- One sentence why\n"
        "- File:line reference where possible\n"
        "\n"
        "## Original lesson content\n"
        "\n"
        f"{content}\n"
        "\n"
        "---\n"
        "\n"
        "## Evidence trail (append-only)\n"
        "\n"
        f"- **{today}** | v0.1.0 draft created by `/skill-capture` from [[{lesson_ref}]].\n"
        "\n"
        "## See also\n"
        "\n"
        "- [[mistake-to-skill]]\n"
        f"- [[{lesson_ref}]]\n"
    )

    draft_path.write_text(draft_content)

    print(f"Draft skill created: {draft_path}")
    print(f"Next steps:")
    print(f"  1. Review the draft at {draft_path}")
    print(f"  2. Extract rules from the lesson content into ## Current rules")
    print(f"  3. Either:")
    print(f"     a. ABSORB into existing skill: copy rules → target skill, bump version")
    print(f"     b. PROMOTE to new skill: mv {draft_dir} → {wiki / 'pages' / 'skills' / slug}/")
    print(f"  4. Update LESSON frontmatter: status=absorbed, absorbed_into=[skill-slug]")
    print(f"  5. Commit both (lesson + skill) in one commit")


if __name__ == "__main__":
    main()
