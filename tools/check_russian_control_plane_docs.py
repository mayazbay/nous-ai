#!/usr/bin/env python3
"""Gate Russian-facing Todoist/Notion control-plane documentation.

This is a static documentation gate. It does not judge arbitrary task titles;
those are handled by tools/todoist_russianize.py and source-backed factory
translation. This checker blocks the generated operator docs from regressing
back to English headings/instructions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import re


CHECKS = [
    {
        "path": "pages/systems/todoist-control-plane-register.md",
        "require": [
            "# Реестр контрольной плоскости Todoist",
            "## Счётчики статусов",
            "## Реестр активных задач",
        ],
        "forbid": [
            "# Todoist Control Plane Register",
            "## Status Counts",
            "## Active Task Register",
        ],
    },
    {
        "path": "pages/systems/todoist-context-enrichment-queue.md",
        "require": [
            "# Очередь обогащения контекста Todoist",
            "## Как выполнять каждую задачу",
            "## Критерий готовности",
        ],
        "forbid": [
            "# Todoist Context Enrichment Queue",
            "Captured:",
            "Source register:",
            "Contextless tasks:",
            "## DONE критерий",
            "`status:working`",
            "`status:blocked`",
        ],
    },
    {
        "path": "pages/systems/control-plane-sync-status.md",
        "require": [
            "# Статус синхронизации контрольной плоскости",
            "## Матрица статусов",
            "## Правила блокировок",
        ],
        "forbid": [
            "# Control Plane Sync Status",
            "## Status Matrix",
            "## Blocking Rules",
            "Last cycle:",
            "Dry run:",
        ],
    },
    {
        "path": "pages/skills/todoist-control-plane/SKILL.md",
        "require": [
            re.compile(r"^# todoist-control-plane v\d+\.\d+\.\d+$", re.MULTILINE),
            "## Russian Documentation Sync Gate",
            "tools/check_russian_control_plane_docs.py",
        ],
        "forbid": [],
    },
]


def run_check(wiki: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    failures = 0
    for spec in CHECKS:
        path = wiki / spec["path"]
        row: dict[str, Any] = {"path": spec["path"], "status": "done", "missing": [], "forbidden": []}
        if not path.exists():
            row["status"] = "blocked"
            row["missing_file"] = True
            failures += 1
            rows.append(row)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        row["missing"] = [
            needle.pattern if hasattr(needle, "search") else needle
            for needle in spec["require"]
            if not (needle.search(text) if hasattr(needle, "search") else needle in text)
        ]
        row["forbidden"] = [needle for needle in spec["forbid"] if needle in text]
        if row["missing"] or row["forbidden"]:
            row["status"] = "blocked"
            failures += 1
        rows.append(row)
    return {"status": "done" if failures == 0 else "blocked", "failures": failures, "checks": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_check(args.wiki)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status={result['status']} failures={result['failures']}")
        for row in result["checks"]:
            print(f"{row['status']}\t{row['path']}")
            if row.get("missing"):
                print(f"  missing: {row['missing']}")
            if row.get("forbidden"):
                print(f"  forbidden: {row['forbidden']}")
    return 0 if result["status"] == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
