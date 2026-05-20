#!/usr/bin/env python3
"""
Library canonical-location scan (s82u Step 3).

Three checks:
  1. Duplicate titles  : frontmatter `title:` value appearing in 2+ files
  2. Duplicate content : MD5 of body (frontmatter stripped) appearing in 2+ paths
  3. Broken aliases    : pages with `type: alias` whose `target:` field doesn't
                         resolve to an existing page

Gates (s82u handoff):
  - Duplicate titles: <=2
  - Duplicate-content body MD5s: <=2
  - Broken aliases: 0

Usage:
  python3 tools/library_canonical_scan.py
  python3 tools/library_canonical_scan.py --json
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
EXCLUDE_DIRS = {"archive", "task-results", "raw"}

# Reuse classifier from the canonical library scanner so this audit honors the
# user-signed AUDIT-061 Tier contract. Dup-title and dup-content gates apply
# to Tier A only — Tier B (sources/imports/upstream) and Tier C (legacy
# receipts) often legitimately duplicate by design (Cyrillic↔Latin
# transliteration pairs, ingest re-runs, by-design substrate copies like
# MEMORY ≡ MEMORY-mercury).
sys.path.insert(0, str(ROOT / "tools"))
from library_quality_scan import classify as classify_tier  # noqa: E402

GATE_DUP_TITLES_TIER_A = 2
GATE_DUP_CONTENT_TIER_A = 2
GATE_BROKEN_ALIASES = 0


def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return {}
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if mm:
            v = mm.group(2).strip().strip('"').strip("'")
            fm[mm.group(1)] = v
    return fm


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    m = re.match(r"^---\n.*?\n---\n?", text, re.DOTALL)
    if m:
        return text[m.end():]
    return text


def normalize_title(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip().casefold())


def collect_pages():
    out = []
    for p in PAGES.rglob("*.md"):
        rel = p.relative_to(ROOT)
        if any(d in rel.parts for d in EXCLUDE_DIRS):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        body = strip_frontmatter(text).strip()
        body_md5 = hashlib.md5(body.encode("utf-8", errors="replace")).hexdigest()
        out.append({
            "path": str(rel),
            "title": fm.get("title", "").strip(),
            "type": (fm.get("type") or "").strip().lower(),
            "alias_target": (fm.get("target") or "").strip(),
            "body_md5": body_md5,
            "body_len": len(body),
            "tier": classify_tier(str(rel)),
        })
    return out


def find_duplicate_titles(pages):
    by_title = defaultdict(list)
    for p in pages:
        if not p["title"]:
            continue
        key = normalize_title(p["title"])
        if not key:
            continue
        by_title[key].append(p)
    dups = []
    for key, plist in by_title.items():
        if len(plist) >= 2:
            dups.append({
                "title_normalized": key,
                "title_canonical": plist[0]["title"],
                "count": len(plist),
                "paths": [p["path"] for p in plist],
            })
    return dups


def find_duplicate_content(pages, min_body_len=200):
    """Find pages with identical body MD5 (excluding very small bodies, which
    cause noise from boilerplate stubs)."""
    by_md5 = defaultdict(list)
    for p in pages:
        if p["body_len"] < min_body_len:
            continue
        by_md5[p["body_md5"]].append(p)
    dups = []
    for md5, plist in by_md5.items():
        if len(plist) >= 2:
            dups.append({
                "md5": md5,
                "body_len": plist[0]["body_len"],
                "count": len(plist),
                "paths": [p["path"] for p in plist],
            })
    return dups


def resolve_alias_target(target: str, all_paths_set: set) -> bool:
    """Check whether an alias `target:` field resolves to a real page.

    Handles Obsidian-style wiki paths (target without `.md`), case-insensitive
    SKILL.md filename (target `skills/audit/skill` -> `pages/skills/audit/SKILL.md`),
    and explicit absolute paths.
    """
    if not target:
        return False
    target = target.strip().strip("[").strip("]").strip()
    if not target:
        return False
    candidates = [
        target,
        f"pages/{target}",
        f"pages/{target}.md",
        f"{target}.md",
    ]
    base = target.rsplit("/", 1)[-1]
    candidates.append(f"pages/{base}.md")
    for cand in candidates:
        if cand in all_paths_set:
            return True
    # Case-insensitive filename match (handles SKILL.md vs skill etc.)
    target_norm = target.lower()
    for path in all_paths_set:
        path_norm = path.lower()
        if path_norm == f"pages/{target_norm}.md" or path_norm == f"{target_norm}.md":
            return True
        if path_norm == f"pages/{target_norm}":
            return True
        if path_norm.endswith(f"/{base.lower()}.md"):
            return True
    return False


def find_broken_aliases(pages):
    aliases = [p for p in pages if p["type"] == "alias"]
    all_paths = {p["path"] for p in pages}
    broken = []
    for p in aliases:
        if not resolve_alias_target(p["alias_target"], all_paths):
            broken.append({
                "path": p["path"],
                "target_field": p["alias_target"],
            })
    return aliases, broken


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    pages = collect_pages()
    dup_titles_all = find_duplicate_titles(pages)
    dup_content_all = find_duplicate_content(pages)
    aliases, broken_aliases = find_broken_aliases(pages)

    # Tier A scoping: a duplicate counts against the gate only if at least one
    # path in the cluster is Tier A. Tier-B/C-only clusters are imports/legacy
    # by design.
    tier_by_path = {p["path"]: p["tier"] for p in pages}

    def cluster_touches_tier_a(paths):
        return any(tier_by_path.get(pp) == "A" for pp in paths)

    dup_titles_tier_a = [d for d in dup_titles_all if cluster_touches_tier_a(d["paths"])]
    dup_content_tier_a = [d for d in dup_content_all if cluster_touches_tier_a(d["paths"])]

    gate_titles = len(dup_titles_tier_a) <= GATE_DUP_TITLES_TIER_A
    gate_content = len(dup_content_tier_a) <= GATE_DUP_CONTENT_TIER_A
    gate_aliases = len(broken_aliases) <= GATE_BROKEN_ALIASES
    all_pass = gate_titles and gate_content and gate_aliases

    payload = {
        "total_pages": len(pages),
        "alias_pages": len(aliases),
        "duplicate_titles_count_total": len(dup_titles_all),
        "duplicate_titles_count_tier_a": len(dup_titles_tier_a),
        "duplicate_content_count_total": len(dup_content_all),
        "duplicate_content_count_tier_a": len(dup_content_tier_a),
        "broken_aliases_count": len(broken_aliases),
        "gates": {
            "duplicate_titles_tier_a": {"value": len(dup_titles_tier_a), "threshold": GATE_DUP_TITLES_TIER_A, "pass": gate_titles},
            "duplicate_content_tier_a": {"value": len(dup_content_tier_a), "threshold": GATE_DUP_CONTENT_TIER_A, "pass": gate_content},
            "broken_aliases": {"value": len(broken_aliases), "threshold": GATE_BROKEN_ALIASES, "pass": gate_aliases},
            "overall_pass": all_pass,
        },
        "duplicate_titles_tier_a": dup_titles_tier_a,
        "duplicate_titles_all": dup_titles_all,
        "duplicate_content_tier_a": dup_content_tier_a,
        "duplicate_content_all": dup_content_all,
        "broken_aliases": broken_aliases,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Total pages: {payload['total_pages']}")
        print(f"  alias-type pages: {payload['alias_pages']}")
        print()
        print(f"Duplicate titles  Tier A : {len(dup_titles_tier_a):4d}  (gate <= {GATE_DUP_TITLES_TIER_A})  -> {'PASS' if gate_titles else 'FAIL'}     [total all-tier: {len(dup_titles_all)}]")
        print(f"Duplicate content Tier A : {len(dup_content_tier_a):4d}  (gate <= {GATE_DUP_CONTENT_TIER_A})  -> {'PASS' if gate_content else 'FAIL'}     [total all-tier: {len(dup_content_all)}]")
        print(f"Broken aliases           : {len(broken_aliases):4d}  (gate <= {GATE_BROKEN_ALIASES})  -> {'PASS' if gate_aliases else 'FAIL'}")
        print()
        print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
        print()
        if dup_titles_tier_a:
            print(f"Tier-A duplicate titles ({len(dup_titles_tier_a)}):")
            for d in dup_titles_tier_a:
                print(f"  '{d['title_canonical']}' ({d['count']}x):")
                for p in d["paths"]:
                    print(f"    [{tier_by_path.get(p,'?')}] {p}")
        if dup_content_tier_a:
            print(f"Tier-A duplicate content MD5 ({len(dup_content_tier_a)}):")
            for d in dup_content_tier_a:
                print(f"  md5={d['md5'][:12]} body_len={d['body_len']} ({d['count']}x):")
                for p in d["paths"]:
                    print(f"    [{tier_by_path.get(p,'?')}] {p}")
        if broken_aliases:
            print("Broken aliases:")
            for d in broken_aliases:
                print(f"  {d['path']}  -> target='{d['target_field']}'  (UNRESOLVED)")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
