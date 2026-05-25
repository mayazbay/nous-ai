#!/usr/bin/env python3
"""Generate the root README dashboard from vault state.

This is the Nous-native version of the ClawSweeper pattern: the dashboard is
plain markdown in the repo, not a separate app. It is intentionally read-only
with respect to external systems.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from pathlib import Path


def _latest(paths: list[Path]) -> Path | None:
    existing = [p for p in paths if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def _count_today(task_dir: Path, today: dt.date) -> int:
    if not task_dir.exists():
        return 0
    prefix = today.isoformat()
    return sum(1 for p in task_dir.glob(f"{prefix}-*.md") if p.is_file())


def _first_heading(path: Path | None) -> str:
    if path is None or not path.exists():
        return "none"
    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.name


def _skill_count(root: Path) -> int:
    skill_dir = root / "pages" / "skills"
    if not skill_dir.exists():
        return 0
    count = 0
    for child in skill_dir.iterdir():
        if child.name in {"_gbrain", "extracted"}:
            continue
        if (child / "SKILL.md").is_file():
            count += 1
    return count


def _tracked_count(root: Path, pattern: str, fallback_dir: Path) -> int:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", pattern],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        files = [line for line in result.stdout.splitlines() if line.strip()]
        if files:
            return len(files)
    except Exception:
        pass
    if not fallback_dir.exists():
        return 0
    return sum(1 for p in fallback_dir.glob("*.md") if p.is_file())


def build_dashboard(root: Path, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now().astimezone()
    today = now.date()

    handoff = _latest(list((root / "pages" / "progress").glob("HANDOFF-AUTO-*.md")))
    task_results = sorted((root / "pages" / "task-results").glob("*.md")) if (root / "pages" / "task-results").exists() else []
    latest_task = _latest(task_results)
    dashboard_count = _tracked_count(root, "pages/dashboards/*.md", root / "pages" / "dashboards")

    lines = [
        "# Nous Factory Dashboard",
        "",
        f"Last update: {now.isoformat(timespec='seconds')}",
        "",
        "This README is the human/agent front door. Detailed memory stays in Obsidian/gbrain; this page is the fast status surface.",
        "",
        "## Current State",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Skills | {_skill_count(root)} |",
        f"| Task-results today | {_count_today(root / 'pages' / 'task-results', today)} |",
        f"| Dashboards | {dashboard_count} |",
        "",
        "## Latest Signals",
        "",
        "| Signal | File | Summary |",
        "|---|---|---|",
        f"| Handoff | `{handoff.relative_to(root) if handoff else 'none'}` | {_first_heading(handoff)} |",
        f"| Task result | `{latest_task.relative_to(root) if latest_task else 'none'}` | {_first_heading(latest_task)} |",
        "",
        "## Burst Compute",
        "",
        "| Lane | Status | Command |",
        "|---|---|---|",
        "| Blacksmith 32 vCPU portable tests | configured, manual GitHub trigger pending org/app wiring | `bash tools/blacksmith_burst_tests.sh` |",
        "| Local/Air proof | script-first, secret-free | `bash tools/blacksmith_burst_tests.sh` |",
        "",
        "## Sweeper Model",
        "",
        "ClawSweeper pattern adapted for Nous:",
        "",
        "- review lane proposes only",
        "- apply lane is the only writer",
        "- README is the dashboard",
        "- external GitHub issue/PR mutation waits for scoped `gh` auth or a GitHub App token",
        "- Obsidian/gbrain remains the memory substrate",
        "",
        "## Operator Commands",
        "",
        "```bash",
        "python3 tools/readme_dashboard.py",
        "bash tools/blacksmith_burst_tests.sh",
        "```",
        "",
    ]
    return "\n".join(lines)


def _normalize_for_check(content: str) -> str:
    lines = []
    for line in content.splitlines():
        if line.startswith("Last update: "):
            lines.append("Last update: <timestamp>")
        else:
            lines.append(line)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", default="README.md")
    parser.add_argument("--check", action="store_true", help="fail if output is stale")
    args = parser.parse_args()

    root = Path(args.wiki).expanduser().resolve()
    out = root / args.output
    content = build_dashboard(root)

    if args.check:
        current = out.read_text() if out.exists() else ""
        if _normalize_for_check(current) != _normalize_for_check(content):
            print(f"STALE: {out}")
            return 1
        print(f"OK: {out} current")
        return 0

    out.write_text(content)
    print(f"Dashboard written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
