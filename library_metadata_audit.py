#!/usr/bin/env python3
"""Report-first compatibility CLI for library metadata audits.

This is the stable public entrypoint requested by the library audit plan. The
implementation delegates to `library_quality_scan.py`, which owns the actual
classification rules and regression tests.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import library_quality_scan


def run_audit(
    wiki: Path,
    *,
    exception_manifest: str = "pages/systems/library-quality-exceptions.md",
    retrieval_proof: str | None = None,
    include_untracked: bool = False,
) -> dict[str, Any]:
    report = library_quality_scan.scan_pages(
        wiki.resolve(),
        exception_manifest,
        include_untracked=include_untracked,
    )
    library_quality_scan.apply_retrieval_proof(report, retrieval_proof)
    report["source_tool"] = "library_quality_scan.py"
    report["mode"] = "report-first"
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Library metadata audit",
        "",
        f"- source_tool: `{report['source_tool']}`",
        f"- page_count: {report['page_count']}",
        f"- blocking_count: {report['blocking_count']}",
        "",
        "## Tiers",
        "",
    ]
    for tier in ("A", "B", "C"):
        counts = report["tiers"].get(tier, {})
        lines.append(
            "- tier {tier}: pages={pages} issues={issues} blocking={blocking} exceptions={exceptions}".format(
                tier=tier,
                pages=counts.get("page_count", 0),
                issues=counts.get("issue_count", 0),
                blocking=counts.get("blocking_count", 0),
                exceptions=counts.get("exception_count", 0),
            )
        )

    blocking = [item for item in report["issues"] if item.get("blocking")]
    lines.extend(["", "## Blocking Issues", ""])
    if not blocking:
        lines.append("None.")
    else:
        for item in blocking[:80]:
            lines.append(
                "- `{path}`: {code} - {message}".format(
                    path=item.get("path", ""),
                    code=item.get("code", ""),
                    message=item.get("message", ""),
                )
            )
        if len(blocking) > 80:
            lines.append(f"- ... {len(blocking) - 80} more")

    retrieval = report.get("retrieval", {})
    if retrieval.get("check_count", 0):
        lines.extend(
            [
                "",
                "## Retrieval Proof",
                "",
                f"- check_count: {retrieval.get('check_count', 0)}",
                f"- missing_count: {retrieval.get('missing_count', 0)}",
            ]
        )

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--format",
        choices=("summary", "json", "markdown"),
        default="summary",
        help="Output format. Default is a compact summary.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 when blocking issues exist.")
    parser.add_argument(
        "--exception-manifest",
        default="pages/systems/library-quality-exceptions.md",
        help="Path relative to --wiki for exception classification.",
    )
    parser.add_argument("--retrieval-proof", help="Optional JSON retrieval proof file.")
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include untracked/ignored filesystem Markdown for explicit archaeology.",
    )
    args = parser.parse_args(argv)

    if not args.wiki.exists() or not args.wiki.is_dir():
        print(f"library_metadata_audit: unreadable wiki path: {args.wiki}", file=sys.stderr)
        return 2

    report = run_audit(
        args.wiki,
        exception_manifest=args.exception_manifest,
        retrieval_proof=args.retrieval_proof,
        include_untracked=args.include_untracked,
    )

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        print(render_markdown(report), end="")
    else:
        print(
            "library_metadata_audit: pages={pages} blocking={blocking} source={source}".format(
                pages=report["page_count"],
                blocking=report["blocking_count"],
                source=report["source_tool"],
            )
        )

    if args.strict and report["blocking_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
