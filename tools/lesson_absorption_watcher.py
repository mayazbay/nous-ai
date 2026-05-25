#!/usr/bin/env python3
"""Scan lessons for unabsorbed >= SLA days. Write dashboard + exit 1 if ghosts found.

Part of GOD_PROMPT v1.0 automation.
"""
import sys
import os
import pathlib
import datetime
import argparse
from dataclasses import dataclass

try:
    import yaml
except ImportError:
    # Minimal YAML parsing fallback (frontmatter only)
    yaml = None


@dataclass
class Ghost:
    lesson_id: str
    path: str
    date: datetime.date
    age_days: int


def _parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter from markdown text."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    if yaml:
        try:
            return yaml.safe_load(parts[1]) or {}
        except Exception:
            return {}
    # Minimal fallback: line-by-line key: value
    result = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def scan_lessons(
    lessons_dir: pathlib.Path,
    today: datetime.date | None = None,
    sla_days: int = 7,
) -> list[Ghost]:
    """Return list of unabsorbed lessons older than sla_days."""
    if today is None:
        today = datetime.date.today()

    ghosts = []
    for p in sorted(lessons_dir.glob("LESSON-*.md")):
        fm = _parse_frontmatter(p.read_text(errors="replace"))
        if fm.get("status") != "unabsorbed":
            continue
        d = fm.get("date")
        if isinstance(d, str):
            try:
                d = datetime.date.fromisoformat(d)
            except ValueError:
                continue
        if not isinstance(d, datetime.date):
            continue
        age = (today - d).days
        if age >= sla_days:
            ghosts.append(Ghost(fm.get("lesson_id", p.stem), str(p), d, age))
    return ghosts


def main():
    ap = argparse.ArgumentParser(description="Lesson absorption ghost detector")
    ap.add_argument("--wiki", default=os.path.expanduser("~/nous-agaas/wiki"))
    ap.add_argument("--sla-days", type=int, default=7)
    ap.add_argument("--dashboard", default=None)
    args = ap.parse_args()

    lessons_dir = pathlib.Path(args.wiki) / "pages" / "lessons" / "individual"
    if not lessons_dir.exists():
        print(f"NOT FOUND: {lessons_dir}", file=sys.stderr)
        sys.exit(2)

    ghosts = scan_lessons(lessons_dir, sla_days=args.sla_days)

    dashboard = args.dashboard or str(
        pathlib.Path(args.wiki) / "pages" / "dashboards" / "lesson-absorption-debt.md"
    )
    pathlib.Path(os.path.dirname(dashboard)).mkdir(parents=True, exist_ok=True)

    today = datetime.date.today()
    with open(dashboard, "w") as f:
        f.write("---\n")
        f.write("type: dashboard\n")
        f.write("id: DASH-LESSON-ABSORPTION-DEBT\n")
        f.write(f'title: "Lesson absorption debt — {today.isoformat()}"\n')
        f.write("tags: [dashboard, lesson-absorption, ghost-debt, auto-generated]\n")
        f.write(f"date: {today.isoformat()}\n")
        f.write("source_count: 0\n")
        f.write("status: active\n")
        f.write(f"last_updated: {today.isoformat()}\n")
        f.write("related: [mistake-to-skill, gbrain-ops]\n")
        f.write("---\n\n")
        f.write(f"# Lesson absorption debt — {today.isoformat()}\n\n")
        f.write(f"SLA: {args.sla_days} days. Unabsorbed lessons older than SLA are ghosts.\n\n")
        f.write(f"**Ghost count: {len(ghosts)}**\n\n")
        if ghosts:
            f.write("| LESSON | Age (days) | Path |\n|---|---|---|\n")
            for g in ghosts:
                f.write(f"| {g.lesson_id} | {g.age_days} | `{g.path}` |\n")
        else:
            f.write("All lessons within SLA.\n")
        f.write("\n## See also\n\n- [[mistake-to-skill]]\n- [[gbrain-ops]]\n")

    print(f"Ghosts: {len(ghosts)}. Dashboard: {dashboard}")
    sys.exit(1 if ghosts else 0)


if __name__ == "__main__":
    main()
