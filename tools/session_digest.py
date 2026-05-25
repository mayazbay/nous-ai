#!/usr/bin/env python3
"""
Session digest tool — captures insights from a Claude Code session that
might otherwise live only in chat history.

Usage modes:
  1. Manual: `python session_digest.py "title" "key insight 1" "key insight 2"`
     → writes wiki/pages/progress/session-YYYYMMDD-HHMM-<slug>.md
  2. Stdin pipe: `echo "..." | python session_digest.py --stdin "title"`
     → reads body from stdin
  3. Wrap factory: factory cycle calls this at end-of-cycle to dump cycle summary

Always cheap (no LLM call). Just structured file write + log entry.

This addresses AUDIT-023 P0.5: "Insights from one-shot Madi questions that
I synthesized but didn't file back" — biggest knowledge leak today.
"""
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

WIKI = Path("/root/nous-agaas/wiki")
PROGRESS = WIKI / "pages" / "progress"
LOG = WIKI / "log.md"


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s.lower())
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60].strip("-") or "untitled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title", help="Session title")
    ap.add_argument("insights", nargs="*", help="Key insights as positional args")
    ap.add_argument("--stdin", action="store_true", help="Read body from stdin")
    ap.add_argument("--tags", default="session,digest", help="Comma-separated tags")
    ap.add_argument("--related", default="", help="Comma-separated wikilink stems")
    args = ap.parse_args()

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%d-%H%M")
    slug = slugify(args.title)
    page_id = f"SESSION-{timestamp}"
    out_file = PROGRESS / f"session-{timestamp}-{slug}.md"

    # Build body
    body = ""
    if args.stdin:
        body = sys.stdin.read()
    if args.insights:
        body += "\n## Key insights\n"
        for i, ins in enumerate(args.insights, 1):
            body += f"\n{i}. {ins}\n"

    if not body.strip():
        print("ERROR: no content (stdin empty and no positional insights)")
        return 1

    tag_list = [t.strip() for t in args.tags.split(",") if t.strip()]
    related = [r.strip() for r in args.related.split(",") if r.strip()]

    fm = [
        "---",
        "type: progress",
        f"id: {page_id}",
        f'title: "Session digest: {args.title}"',
        f"tags: [{', '.join(repr(t) for t in tag_list)}]",
        f"date: {date}",
    ]
    if related:
        fm.append(f"related: [{', '.join(related)}]")
    fm.append("---")

    page = "\n".join(fm) + f"\n\n# Session digest: {args.title}\n\n> Captured {now.isoformat()}\n\n{body}\n\n## See also\n- [[index]]\n- [[CLAUDE]]\n"

    PROGRESS.mkdir(parents=True, exist_ok=True)
    out_file.write_text(page)
    print(f"Wrote {out_file}")

    # Append to log.md
    log_line = f"\n## [{date}] session-digest | {args.title}\n"
    with LOG.open("a") as f:
        f.write(log_line)
    print(f"Logged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
