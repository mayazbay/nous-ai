#!/usr/bin/env python3
"""skill_tier_index — substrate-v2 Phase 0.8

Emits a JSON index of canonical Nous skills grouped by tier (1, 2, 3).
Reads `tier:` and `title:` from frontmatter of each pages/skills/<name>/SKILL.md.
Excludes pages/skills/_gbrain/ sub-skills and pages/skills/extracted/.

Output shape:
{
  "1": [{"name": "agent-quality", "path": "Nous/pages/skills/agent-quality/SKILL.md", "title": "..."}],
  "2": [...],
  "3": [...]
}

Use `--counts` for operator smoke checks:
{"tier_1": 6, "tier_2": 21, "tier_3": 7, "total": 34}

Used by session-start loaders to mandatorily load Tier-1 skills, by domain to load
Tier-2, and by request to surface Tier-3.

Convention doc: Nous/pages/skills/_gbrain/TIER-CONVENTION.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

WIKI_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = WIKI_ROOT / "pages" / "skills"
EXCLUDED_DIRS = {"_gbrain", "extracted"}


def parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML frontmatter parser — handles quoted strings + simple values."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        end = text.find("\n---", 4)
        if end == -1:
            return {}
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([a-z_][a-z0-9_]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            # Strip surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            fm[key] = val
    return fm


def build_index() -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    if not SKILLS.is_dir():
        raise FileNotFoundError(f"{SKILLS} not found")

    idx: dict[str, list[dict[str, str]]] = {"1": [], "2": [], "3": []}
    skipped: list[str] = []

    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir():
            continue
        if d.name in EXCLUDED_DIRS:
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue

        text = skill_md.read_text()
        fm = parse_frontmatter(text)
        tier = fm.get("tier")
        if tier not in {"1", "2", "3"}:
            skipped.append(f"{d.name}: tier={tier!r}")
            continue
        idx[tier].append(
            {
                "name": d.name,
                "path": str(skill_md.relative_to(WIKI_ROOT)),
                "title": fm.get("title", d.name),
            }
        )
    return idx, skipped


def summarize_counts(idx: dict[str, list[dict[str, str]]]) -> dict[str, int]:
    counts = {f"tier_{tier}": len(idx[tier]) for tier in ("1", "2", "3")}
    counts["total"] = sum(counts.values())
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the Nous skill tier index.")
    parser.add_argument(
        "--counts",
        action="store_true",
        help="emit only tier count summary as {tier_1, tier_2, tier_3, total}",
    )
    args = parser.parse_args(argv)

    try:
        idx, skipped = build_index()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if skipped:
        print(f"WARN: skipped {len(skipped)} skill(s) with invalid tier:", file=sys.stderr)
        for s in skipped:
            print(f"  {s}", file=sys.stderr)

    payload = summarize_counts(idx) if args.counts else idx
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
