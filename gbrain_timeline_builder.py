#!/usr/bin/env python3
"""
gbrain_timeline_builder.py — Parse timeline entries from vault and register in GBrain.

Parses two formats:
1. Standard: - **YYYY-MM-DD** | description [[source]]
2. Relaxed:  - **YYYY-MM-DD** — description (used in some existing pages)
3. Range:    - **YYYY-MM → YYYY-MM** — description (uses start date)

Usage:
    python3 gbrain_timeline_builder.py [--dry-run] [--verbose]
"""

import os
import re
import subprocess
import sys

WIKI_DIR = "/root/nous-agaas/wiki"
GBRAIN_BIN = "/opt/nous-agaas/gbrain/bin/gbrain"
DB_PASS = "gbrain2026"

# Match timeline entries with dates
# Format 1: - **2026-04-10** | Event description
# Format 2: - **2026-04-10** — Event description  
# Format 3: - **2025-04 → 2025-05** — Event description (range, use first date)
TIMELINE_RE = re.compile(
    r'^-\s+\*\*(\d{4}-\d{2}(?:-\d{2})?)\s*(?:→.*?)?\*\*\s*[|—–-]\s*(.+)',
    re.MULTILINE
)

SKIP_PATTERNS = {'node_modules', '.obsidian', '.git', '.trash', '__pycache__'}


def file_to_slug(fp):
    rel = os.path.relpath(fp, WIKI_DIR)
    if rel.endswith('.md'):
        rel = rel[:-3]
    return rel.lower()


def get_slugs():
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASS
    r = subprocess.run(
        ['psql', '-U', 'gbrain', '-h', 'localhost', '-d', 'gbrain', '-t', '-A',
         '-c', 'SELECT slug FROM pages;'],
        capture_output=True, text=True, env=env
    )
    return set(l.strip() for l in r.stdout.strip().split('\n') if l.strip())


def get_existing_timeline():
    """Get existing timeline entries to avoid duplicates."""
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASS
    r = subprocess.run(
        ['psql', '-U', 'gbrain', '-h', 'localhost', '-d', 'gbrain', '-t', '-A',
         '-c', """SELECT p.slug || '|' || t.date || '|' || LEFT(t.summary, 40)
                  FROM timeline_entries t
                  JOIN pages p ON t.page_id = p.id;"""],
        capture_output=True, text=True, env=env
    )
    return set(l.strip() for l in r.stdout.strip().split('\n') if l.strip())


def normalize_date(d):
    """Ensure date is YYYY-MM-DD format."""
    if len(d) == 7:  # YYYY-MM
        return d + '-01'
    return d


def truncate(text, max_len=200):
    """Truncate text for timeline entry."""
    # Remove markdown links, bold, etc.
    text = re.sub(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len-3] + '...'
    return text


def main():
    dry_run = '--dry-run' in sys.argv
    verbose = '--verbose' in sys.argv

    if dry_run:
        print("=== DRY RUN ===\n")

    slugs = get_slugs()
    existing = get_existing_timeline()
    print(f"GBrain: {len(slugs)} pages, {len(existing)} existing timeline entries")

    entries = []  # list of (slug, date, text)
    files_with_timeline = 0

    for root, dirs, files in os.walk(WIKI_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS]
        for f in files:
            if not f.endswith('.md'):
                continue
            fp = os.path.join(root, f)
            slug = file_to_slug(fp)
            if slug not in slugs:
                continue
            try:
                content = open(fp, 'r', errors='ignore').read()
            except Exception:
                continue

            matches = list(TIMELINE_RE.finditer(content))
            if not matches:
                continue

            files_with_timeline += 1
            for m in matches:
                date = normalize_date(m.group(1))
                text = truncate(m.group(2))
                # Check for duplicates (use 40-char prefix to match SQL LEFT())
                key = f"{slug}|{date}|{text[:40]}"
                if key not in existing:
                    entries.append((slug, date, text))
                    if verbose:
                        print(f"  {slug} | {date} | {text[:60]}...")

    print(f"\nFiles with timeline entries: {files_with_timeline}")
    print(f"New entries to register: {len(entries)}")

    if not entries:
        print("No new entries.")
        return

    print(f"\nRegistering {len(entries)} timeline entries{'  (DRY RUN)' if dry_run else ''}...")
    ok, fail = 0, 0
    for slug, date, text in entries:
        if dry_run:
            ok += 1
            continue
        r = subprocess.run(
            [GBRAIN_BIN, 'timeline-add', slug, date, text],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            ok += 1
        elif 'duplicate key' in r.stderr or 'unique constraint' in r.stderr:
            ok += 1  # Already exists — not a real failure
            if verbose:
                print(f"  SKIP (exists): {slug} {date}")
        else:
            fail += 1
            if verbose:
                print(f"  FAILED: {slug} {date}: {r.stderr.strip()}")

    print(f"\n=== DONE === Registered: {ok}, Failed: {fail}")

    if not dry_run:
        r = subprocess.run([GBRAIN_BIN, 'stats'],
                           capture_output=True, text=True, timeout=30)
        print(r.stdout)


if __name__ == '__main__':
    main()
