#!/usr/bin/env python3
"""
tools/backfill_frontmatter.py — one-shot YAML frontmatter backfill (AUDIT-027 P0.2).

Walks pages/ and laws/ in the vault and, for each .md file with existing frontmatter:
- Adds `last_updated: <git log last commit date>` if missing
- Adds `source_count: N` if missing (default depends on type)
- Adds `status: reviewed` if missing

Idempotent: re-running is a no-op (fields already present are never overwritten).
Git-reversible: one commit per run (commit separately after).

Usage:
    python3 tools/backfill_frontmatter.py --dry-run   # preview only
    python3 tools/backfill_frontmatter.py             # apply edits

Exit code 0 on success, 1 on error.

References:
- AUDIT-027 — audit that asked for this script
- Trefethen production-schema template: source_count / last_updated / status fields
- The fields are mandated by the upgraded CLAUDE.md Wiki Conventions section
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = VAULT_ROOT / "pages"
LAWS_DIR = VAULT_ROOT / "laws"

# Default source_count by page type. Meta/rule pages get 0 (they're not summarizing a source).
# Content pages get 1 (at least one source implicitly).
SOURCE_COUNT_DEFAULTS = {
    "schema": 0,
    "law": 0,
    "audit": 0,
    "amendment": 0,
    "compiled": 0,
    "progress": 0,
    "roadmap": 0,
    "team": 0,
    "lesson": 1,
    "entity": 1,
    "concept": 1,
    "source": 1,
    "spec": 1,
    "system": 1,
    "legal": 1,
    "project": 1,
    "raw-source": 1,
}

# Default status by page type.
STATUS_DEFAULTS = {
    "draft": "draft",  # if type is "draft" (shouldn't happen but just in case)
}
DEFAULT_STATUS = "reviewed"

FALLBACK_DATE = "2026-04-08"  # used when git log returns nothing

# Regex to find a key at the start of a line in the frontmatter block.
FIELD_RE_TEMPLATE = r"^{key}\s*:\s*(.+?)\s*$"


def git_last_date(file_path):
    """Return YYYY-MM-DD of the last git commit that touched this file, or None."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(VAULT_ROOT),
                "log",
                "-1",
                "--format=%cs",
                "--",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def parse_frontmatter(content):
    """
    Return (frontmatter_text, body_text) if file starts with a --- block, else (None, content).

    frontmatter_text does NOT include the surrounding --- markers.
    body_text has no leading newline.
    """
    if not content.startswith("---\n") and not content.startswith("---\r\n"):
        return None, content

    # Strip the opening --- line
    if content.startswith("---\n"):
        rest = content[4:]
    else:
        rest = content[5:]

    # Find the closing --- line (must be on its own line)
    match = re.search(r"^---\s*\r?\n", rest, re.MULTILINE)
    if not match:
        return None, content

    fm_text = rest[: match.start()]
    body = rest[match.end():]
    return fm_text, body


def get_field(fm_text, key):
    """Return the value of `key: value` in the frontmatter, or None if absent."""
    pattern = FIELD_RE_TEMPLATE.format(key=re.escape(key))
    match = re.search(pattern, fm_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def get_type(fm_text):
    """Best-effort extract the `type:` value; default 'unknown'."""
    return get_field(fm_text, "type") or "unknown"


def add_field(fm_text, key, value):
    """
    Append `key: value` to the frontmatter if the key is not already present.
    Returns (new_fm_text, did_change).
    """
    if get_field(fm_text, key) is not None:
        return fm_text, False
    if not fm_text.endswith("\n"):
        fm_text += "\n"
    fm_text += f"{key}: {value}\n"
    return fm_text, True


def serialize_frontmatter(fm_text):
    """Wrap frontmatter text in --- markers, with one trailing newline after closing ---."""
    if not fm_text.endswith("\n"):
        fm_text += "\n"
    return "---\n" + fm_text + "---\n"


def process_file(file_path, dry_run):
    """
    Process a single .md file. Returns (status, actions_list).

    status is one of: "changed", "unchanged", "no-frontmatter", "read-fail"
    actions_list is the list of field additions (for logging).
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        return "read-fail", [f"{type(e).__name__}: {e}"]

    fm_text, body = parse_frontmatter(content)
    if fm_text is None:
        return "no-frontmatter", []

    actions = []
    new_fm = fm_text

    # last_updated
    if get_field(new_fm, "last_updated") is None:
        date = git_last_date(file_path) or FALLBACK_DATE
        new_fm, did = add_field(new_fm, "last_updated", date)
        if did:
            actions.append(f"+last_updated: {date}")

    # source_count
    if get_field(new_fm, "source_count") is None:
        file_type = get_type(new_fm)
        default = SOURCE_COUNT_DEFAULTS.get(file_type, 1)
        new_fm, did = add_field(new_fm, "source_count", default)
        if did:
            actions.append(f"+source_count: {default}")

    # status
    if get_field(new_fm, "status") is None:
        new_fm, did = add_field(new_fm, "status", DEFAULT_STATUS)
        if did:
            actions.append(f"+status: {DEFAULT_STATUS}")

    if not actions:
        return "unchanged", []

    if not dry_run:
        new_content = serialize_frontmatter(new_fm) + body
        file_path.write_text(new_content, encoding="utf-8")

    return "changed", actions


def main():
    parser = argparse.ArgumentParser(
        description="Backfill YAML frontmatter (last_updated, source_count, status) on wiki pages per AUDIT-027 P0.2"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview changes without writing any files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="print every file's status, not just changes",
    )
    args = parser.parse_args()

    # Collect all .md files from pages/ and laws/
    md_files = []
    for root in [PAGES_DIR, LAWS_DIR]:
        if root.exists():
            md_files.extend(root.rglob("*.md"))
    md_files.sort()

    totals = {"changed": 0, "unchanged": 0, "no-frontmatter": 0, "read-fail": 0}

    for file_path in md_files:
        rel = file_path.relative_to(VAULT_ROOT)
        status, actions = process_file(file_path, dry_run=args.dry_run)
        totals[status] = totals.get(status, 0) + 1

        if status == "changed":
            prefix = "DRY " if args.dry_run else "EDIT"
            print(f"{prefix}  {rel}  {', '.join(actions)}")
        elif status == "no-frontmatter" and args.verbose:
            print(f"SKIP  {rel}  (no frontmatter)")
        elif status == "read-fail":
            print(f"FAIL  {rel}  {actions}")
        elif status == "unchanged" and args.verbose:
            print(f"OK    {rel}")

    print()
    print("=== Summary ===")
    print(f"Total .md files scanned:        {sum(totals.values())}")
    print(f"Files changed:                  {totals['changed']}")
    print(f"Files already complete:         {totals['unchanged']}")
    print(f"Files with no frontmatter:      {totals['no-frontmatter']}")
    print(f"Files failed to read:           {totals['read-fail']}")
    print(f"Mode:                           {'DRY RUN (no writes)' if args.dry_run else 'APPLIED'}")

    return 0 if totals["read-fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
