#!/usr/bin/env python3
"""Helpers for Codex review-loop GitHub Actions.

The workflows keep LLM judgment inside Codex, but small deterministic decisions
belong in scripts: classify a review output and enforce the loop ceiling.
"""

from __future__ import annotations

import argparse
from pathlib import Path


NO_FINDINGS_MARKERS = {
    "NO_FINDINGS",
    "No findings.",
    "No actionable findings.",
}


def has_findings(text: str) -> bool:
    body = text.strip()
    if not body:
        return False
    if body in NO_FINDINGS_MARKERS:
        return False
    if body.upper() == "NO_FINDINGS":
        return False
    return "FINDINGS" in body.upper() or body.upper() != "NO_FINDINGS"


def cmd_classify(path: Path) -> int:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    found = has_findings(text)
    print(f"has_findings={'true' if found else 'false'}")
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    print(f"first_line={first_line[:200]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    classify = sub.add_parser("classify")
    classify.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.cmd == "classify":
        return cmd_classify(args.path)
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
