#!/usr/bin/env python3
"""
gbrain_link_builder.py — Parse [[wikilinks]] from vault and register them in GBrain's link graph.

Unlocks GBrain's backlinks and graph traversal features.
Safe to re-run: deduplicates against existing links.

Usage:
    python3 gbrain_link_builder.py [--dry-run] [--verbose]
"""

import os
import re
import subprocess
import sys
from collections import defaultdict

WIKI_DIR = "/root/nous-agaas/wiki"
GBRAIN_BIN = "/opt/nous-agaas/gbrain/bin/gbrain"
DB_HOST = "localhost"
DB_NAME = "gbrain"
DB_USER = "gbrain"
DB_PASS = "gbrain2026"

WIKILINK_RE = re.compile(r'\[\[([^\[\]]+?)\]\]')
SKIP_PATTERNS = {'node_modules', '.obsidian', '.git', '.trash', '__pycache__'}
TYPE_PREFIXES = ['entity-', 'source-', 'project-', 'synthesis-', 'audit-', 'lesson-', 'concept-']
SKIP_TARGETS = {'source-slug', 'source-a', 'source-b', 'meeting-notes', 'wikilinks',
                'wikilink', 'id-1', 'id-2', 'page-name'}
MEDIA_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.mp3', '.mp4', '.webp', '.wav', '.m4a'}


def _db_env():
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASS
    return env


def get_slugs():
    r = subprocess.run(
        ['psql', '-U', DB_USER, '-h', DB_HOST, '-d', DB_NAME, '-t', '-A',
         '-c', 'SELECT slug FROM pages;'],
        capture_output=True, text=True, timeout=30, env=_db_env()
    )
    return set(l.strip() for l in r.stdout.strip().split('\n') if l.strip())


def get_existing_links():
    r = subprocess.run(
        ['psql', '-U', DB_USER, '-h', DB_HOST, '-d', DB_NAME, '-t', '-A',
         '-c', """SELECT p1.slug || '|' || p2.slug
                  FROM links l
                  JOIN pages p1 ON l.from_page_id = p1.id
                  JOIN pages p2 ON l.to_page_id = p2.id;"""],
        capture_output=True, text=True, timeout=30, env=_db_env()
    )
    return set(l.strip() for l in r.stdout.strip().split('\n') if l.strip())


def build_index(slugs):
    idx = defaultdict(list)
    for s in slugs:
        idx[s.rsplit('/', 1)[-1]].append(s)
    return idx


def _strip_skill_suffix(text):
    text = text.strip('/')
    for suffix in ('/skill.md', '/skill'):
        if text.endswith(suffix):
            return text[:-len(suffix)].strip('/')
    return text


def alias_candidates(link_text):
    """Return deterministic slug aliases for common Obsidian link idioms."""
    if '|' in link_text:
        link_text = link_text.split('|')[0]
    if '#' in link_text:
        link_text = link_text.split('#')[0]
    text = link_text.strip().lower().strip('/')
    if text.endswith('.md'):
        text = text[:-3]

    out = []

    def add(candidate):
        candidate = candidate.strip('/').lower()
        if candidate and candidate not in out:
            out.append(candidate)

    add(text)
    if text.startswith('pages/'):
        add(text[len('pages/'):])
    else:
        add('pages/' + text)

    for prefix in ('skills/', 'pages/skills/'):
        if text.startswith(prefix):
            rest = _strip_skill_suffix(text[len(prefix):])
            if rest:
                add('pages/skills/' + rest)
                add('pages/skills/' + rest + '/skill')

    if '/skills/' in text:
        before, rest = text.split('/skills/', 1)
        before = before.removeprefix('pages/').strip('/')
        rest = _strip_skill_suffix(rest)
        if before and rest:
            add('pages/' + before + '/skills/' + rest)
            add('pages/' + before + '/skills/' + rest + '/skill')

    if '/' not in text:
        add('pages/skills/' + text + '/skill')

    return out


def resolve(link_text, slug_index, slugs):
    candidates = alias_candidates(link_text)
    link_text = candidates[0] if candidates else ''

    if not link_text or link_text in SKIP_TARGETS:
        return None
    if any(link_text.endswith(e) for e in MEDIA_EXTS):
        return None

    # 1. Exact slug match
    if link_text in slugs:
        return link_text

    # 2. Basename match
    if link_text in slug_index:
        m = slug_index[link_text]
        if len(m) == 1:
            return m[0]
        for prefix in ['pages/', 'laws/', 'lessons/']:
            for x in m:
                if x.startswith(prefix):
                    return x
        return m[0]

    # 3. Strip type prefixes (entity-X -> X, project-X -> X)
    for pfx in TYPE_PREFIXES:
        if link_text.startswith(pfx):
            stripped = link_text[len(pfx):]
            if stripped in slug_index:
                return slug_index[stripped][0]

    # 4. Try with known directory prefixes
    for prefix in ['pages/entities/', 'pages/concepts/', 'pages/sources/',
                   'pages/specs/', 'pages/systems/', 'pages/audits/',
                   'pages/progress/', 'pages/projects/', 'pages/lessons/individual/',
                   'pages/legal/', 'pages/roadmap/', 'pages/team/',
                   'laws/', 'lessons/']:
        if prefix + link_text in slugs:
            return prefix + link_text

    # 5. Partial match for truncated slugs (only if unambiguous and link is long enough)
    if len(link_text) > 10:
        matches = [s for s in slugs if link_text in s.rsplit('/', 1)[-1]]
        if len(matches) == 1:
            return matches[0]

    # 6. Obsidian/gbrain alias candidates, especially skill namespace links:
    #    [[skills/foo]], [[skills/foo/skill]], [[skills/foo/SKILL.md]], and
    #    tenant variants like [[tenants/satory/skills/foo/SKILL.md]].
    for candidate in candidates[1:]:
        if candidate in slugs:
            return candidate

    return None


def file_to_slug(fp):
    rel = os.path.relpath(fp, WIKI_DIR)
    if rel.endswith('.md'):
        rel = rel[:-3]
    return rel.lower()


def main():
    dry_run = '--dry-run' in sys.argv
    verbose = '--verbose' in sys.argv

    if dry_run:
        print("=== DRY RUN ===\n")

    print("Loading GBrain state...")
    slugs = get_slugs()
    slug_index = build_index(slugs)
    existing = get_existing_links()
    print(f"  {len(slugs)} pages, {len(existing)} existing links")

    print("\nParsing wikilinks from vault...")
    all_links = set()
    unresolved = defaultdict(list)
    files_processed = 0

    for root, dirs, files in os.walk(WIKI_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_PATTERNS]
        for f in files:
            if not f.endswith('.md'):
                continue
            fp = os.path.join(root, f)
            from_slug = file_to_slug(fp)
            if from_slug not in slugs:
                continue
            files_processed += 1
            try:
                content = open(fp, 'r', errors='ignore').read()
            except Exception:
                continue
            for m in WIKILINK_RE.finditer(content):
                to = resolve(m.group(1), slug_index, slugs)
                if to and to != from_slug:
                    all_links.add((from_slug, to))
                elif to is None:
                    raw = m.group(1).split('|')[0].split('#')[0].strip().lower()
                    if raw not in SKIP_TARGETS:
                        unresolved[raw].append(from_slug)

    truly_new = sorted((f, t) for f, t in all_links if f + '|' + t not in existing)

    print(f"\n  Files: {files_processed}")
    print(f"  Total resolved: {len(all_links)}")
    print(f"  Already registered: {len(all_links) - len(truly_new)}")
    print(f"  Truly new: {len(truly_new)}")
    print(f"  Unresolved targets: {len(unresolved)}")

    if unresolved and verbose:
        print("\n  Top 15 unresolved:")
        for target, srcs in sorted(unresolved.items(), key=lambda x: -len(x[1]))[:15]:
            print(f"    [[{target}]] — {len(srcs)} ref(s)")

    if not truly_new:
        print("\nNo new links to register.")
        return

    print(f"\nRegistering {len(truly_new)} new links{'  (DRY RUN)' if dry_run else ''}...")
    ok, fail = 0, 0
    for i, (f, t) in enumerate(truly_new):
        if dry_run:
            if verbose:
                print(f"  {f} -> {t}")
            ok += 1
            continue
        r = subprocess.run([GBRAIN_BIN, 'link', f, t],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            ok += 1
        else:
            fail += 1
        if (i + 1) % 100 == 0:
            print(f"  ... {i + 1}/{len(truly_new)}")

    print(f"\n=== DONE === Registered: {ok}, Failed: {fail}")

    if not dry_run:
        r = subprocess.run([GBRAIN_BIN, 'health'],
                           capture_output=True, text=True, timeout=30)
        print(f"\n{r.stdout}")


if __name__ == '__main__':
    main()
