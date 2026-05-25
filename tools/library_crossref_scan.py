#!/usr/bin/env python3
"""
Library cross-reference resolution scan (s82u Step 4).

Four checks:
  1. Every [[wikilink]] in any pages/**/*.md must resolve to an existing page
     (case-insensitive filename match; honors aliases via target field).
  2. Every prose-form `<skill-name> AP-N` reference must resolve to:
     - existing pages/skills/<skill-name>/SKILL.md
     - that file containing `### AP-N` heading
  3. Every [[LAW-NNN-...]] reference must resolve to a real LAW file.
  4. Every [[HANDOFF-AUTO-...]] reference must resolve to a real HANDOFF file.

Gates (s82u handoff):
  - Broken [[wikilinks]]   : 0
  - Broken prose AP refs    : <=5

Usage:
  python3 tools/library_crossref_scan.py
  python3 tools/library_crossref_scan.py --json
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
EXCLUDE_DIRS = {"archive", "task-results", "raw"}

# Self-referential audit receipts list broken refs in their bodies as
# documentation. Counting those listings would inflate the gate against the
# audit's own findings (parity with reachability scanner). Mirrors the
# self_audit_exclusions pattern in tools/library_reachability_scan.py.
SELF_AUDIT_EXCLUSIONS = {
    "pages/audits/AUDIT-LIBRARY-REACHABILITY-2026-04-30.md",
    "pages/audits/AUDIT-LIBRARY-CANONICAL-2026-04-30.md",
    "pages/audits/AUDIT-LIBRARY-CROSSREFS-2026-04-30.md",
    "pages/audits/AUDIT-LIBRARY-CROSSREF-2026-04-30.md",
}

# Reuse classifier so gates honor AUDIT-061 Tier policy. Wikilink/prose AP
# integrity gates apply to Tier A1 stable docs (skills, laws, systems,
# entities, projects, canonical concepts, tenant skill docs, and root doctrine).
# Tier B/C report/import/legacy receipts may legitimately contain broken refs to
# migrated/deleted upstream files; we report those informationally.
sys.path.insert(0, str(ROOT / "tools"))
from library_quality_scan import classify as classify_tier  # noqa: E402

TIMESERIES_RES = (
    re.compile(r"^pages/progress/HANDOFF.+\.md$"),
    re.compile(r"^pages/dashboards/.+\.md$"),           # defensive fallback: dashboards are Tier B in the
                                                        # shared classifier and must stay informational.
                                                        # s1526, 2026-04-30 - AP-74 in gbrain-ops.
    re.compile(r"^pages/progress/daily-factory-analysis-\d{4}-\d{2}-\d{2}\.md$"),
    re.compile(r"^pages/progress/commit-review-\d{4}-\d{2}-\d{2}\.md$"),
)


def subtier_for(path):
    # Top-level vault doctrine files (CLAUDE.md, MEMORY.md, log.md, index.md)
    # are entry-point doctrine — classify as Tier A1 regardless of what
    # library_quality_scan.classify() returns. README.md stays at C (developer
    # doc, not runtime doctrine). gbrain-ops AP-73 (s2127, 2026-04-30) — closes
    # blind spot where CLAUDE.md wikilinks were never scanned.
    if path.lower() in ("claude.md", "memory.md", "log.md", "index.md"):
        return "A1"
    tier = classify_tier(path)
    if tier != "A":
        return tier
    return "A2" if any(r.match(path) for r in TIMESERIES_RES) else "A1"


GATE_BROKEN_WIKILINKS_TIER_A1 = 0
GATE_BROKEN_PROSE_AP_TIER_A1 = 5

WIKILINK_RE = re.compile(r"\[\[([^\]\n]+?)\]\]")
PROSE_AP_RE = re.compile(
    r"(?<![A-Za-z0-9_-])([a-z][a-z0-9-]+)\s+AP-(\d+)(?![A-Za-z0-9])"
)


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
            fm[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
    return fm


def collect_pages():
    """Index every page by lowercased path stem and lowercased full path."""
    pages = []
    by_basename = defaultdict(list)   # basename (lower) -> [path]
    by_full_path = {}                 # lowercased relative path (with and without .md) -> path
    by_id = {}                        # frontmatter id (lower) -> path
    by_prefix = defaultdict(list)     # prefix like "law-016" -> [path]  for shortform refs
    aliases_by_name = {}              # alias name (lower) -> resolved target (lower)
    skills_with_aps = {}              # skill_name (lower) -> set of AP numbers

    # Walk pages/ AND vault-root doctrine files AND laws/. CLAUDE.md and
    # MEMORY.md are entry-point doctrine (read-by-every-agent); laws/ holds
    # LAW + AMENDMENT files referenced as [[wikilinks]] from many places.
    # Indexing only pages/ caused broken pointers like [[library-grade-audit]]
    # in CLAUDE.md and [[AMENDMENT-001-circuit-breaker]] in index.md to go
    # uncaught (gbrain-ops AP-73, s2127, 2026-04-30).
    candidates = list(PAGES.rglob("*.md"))
    laws_dir = ROOT / "laws"
    if laws_dir.is_dir():
        candidates.extend(laws_dir.rglob("*.md"))
    for top in ("CLAUDE.md", "MEMORY.md", "log.md", "index.md"):
        top_path = ROOT / top
        if top_path.exists():
            candidates.append(top_path)

    for p in candidates:
        rel = p.relative_to(ROOT)
        if any(d in rel.parts for d in EXCLUDE_DIRS):
            continue
        rel_str = str(rel)
        rel_lower = rel_str.lower()
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        basename = p.stem.lower()
        pages.append({
            "path": rel_str,
            "basename": basename,
            "type": (fm.get("type") or "").strip().lower(),
            "alias_target": (fm.get("target") or "").strip(),
        })
        by_basename[basename].append(rel_str)
        by_full_path[rel_lower] = rel_str
        by_full_path[rel_lower[:-3]] = rel_str

        # Index by frontmatter id (lowercased) for [[SYS-WIKI-SCHEMA-DETAIL]]-style refs
        page_id = (fm.get("id") or "").strip().lower()
        if page_id:
            by_id[page_id] = rel_str

        # Index by hyphen-prefix (LAW-016-foo.md -> "law-016") so [[LAW-016]] resolves
        # to LAW-016-satory-frontend-lock.md, etc.
        prefix_match = re.match(r"^((?:law|amendment|amd|audit|spec|plan|handoff)-\d+)-", basename, re.IGNORECASE)
        if prefix_match:
            by_prefix[prefix_match.group(1).lower()].append(rel_str)

        if fm.get("type", "").strip().lower() == "alias":
            target = (fm.get("target") or "").strip().lower()
            if target:
                aliases_by_name[basename] = target

        # Track AP definitions in SKILL.md. Conventions vary across skills:
        #   ### AP-N — ...                (most skills)
        #   **Anti-pattern: AP-N — ...**  (audit, others)
        #   - **AP-N** ...                (some)
        # Permissive approach: any AP-N token in the SKILL body (after
        # frontmatter) counts as defined. This admits some cross-skill refs as
        # noise but eliminates structural-format-divergence false negatives.
        if rel.name == "SKILL.md" and rel.parent.parent.name == "skills":
            skill_name = rel.parent.name.lower()
            ap_set = set()
            # Strip frontmatter so YAML lines listing APs in description don't
            # contaminate, but allow body to count any AP-N occurrence.
            body = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
            for m in re.finditer(r"AP-(\d+)\b", body):
                ap_set.add(int(m.group(1)))
            skills_with_aps[skill_name] = ap_set

    return pages, by_basename, by_full_path, by_id, by_prefix, aliases_by_name, skills_with_aps


def resolve_wikilink(target, by_basename, by_full_path, aliases_by_name, skill_names, by_id=None, by_prefix=None):
    """Return resolved real path or None."""
    target = target.strip().lower()
    if not target:
        return None
    target = target.split("|", 1)[0].split("#", 1)[0].strip()
    if not target:
        return None
    # Top-level vault files (CLAUDE.md, MEMORY.md, log.md, index.md, README.md)
    base = target.rsplit("/", 1)[-1]
    if base in TOP_LEVEL_FILES:
        return f"./{base}"  # synthetic path for top-of-vault files
    # Direct full-path match (with or without .md)
    if target in by_full_path:
        return by_full_path[target]
    # Strip explicit /SKILL.md or /skill.md suffix
    if target.endswith("/skill.md"):
        target = target[:-len(".md")]
    elif target.endswith(".md"):
        target_no_ext = target[:-3]
        if target_no_ext in by_full_path:
            return by_full_path[target_no_ext]
    # Project convention: [[skill-name]] resolves to pages/skills/<name>/SKILL.md
    if base in skill_names:
        candidate = f"pages/skills/{base}/skill"
        if candidate in by_full_path:
            return by_full_path[candidate]
    # [[skills/<name>/skill]] or [[skills/<name>]] explicit form
    if target.startswith("skills/"):
        if "/" not in target[len("skills/"):]:
            inner = target[len("skills/"):]
            candidate = f"pages/skills/{inner}/skill"
            if candidate in by_full_path:
                return by_full_path[candidate]
        if target.endswith("/skill"):
            candidate = f"pages/{target}"
            if candidate in by_full_path:
                return by_full_path[candidate]
    # [[<skill>/SKILL.md]] or [[<skill>/skill]] (skill as prefix)
    if "/" in target and (target.endswith("/skill") or target.endswith("/skill.md")):
        skill_root = target.split("/", 1)[0]
        if skill_root in skill_names:
            candidate = f"pages/skills/{skill_root}/skill"
            if candidate in by_full_path:
                return by_full_path[candidate]
    # [[pages/tenants/satory/skills/<name>]] -> pages/tenants/satory/skills/<name>/SKILL.md
    if target.startswith("pages/tenants/") and "/skills/" in target and not target.endswith("/skill"):
        candidate = f"{target}/skill"
        if candidate in by_full_path:
            return by_full_path[candidate]
    # [[tenants/<tenant>/skills/<name>]] (without pages/ prefix)
    if target.startswith("tenants/") and "/skills/" in target:
        candidate = f"pages/{target}"
        if candidate in by_full_path:
            return by_full_path[candidate]
        candidate = f"pages/{target}/skill"
        if candidate in by_full_path:
            return by_full_path[candidate]
    # [[AMD-NNN-...]] -> [[AMENDMENT-NNN-...]] convention rename
    if target.startswith("amd-"):
        renamed = "amendment-" + target[len("amd-"):]
        if renamed in by_basename:
            return by_basename[renamed][0]
    # Basename-only match (any file with this stem)
    if base in by_basename:
        return by_basename[base][0]
    # Frontmatter id match (e.g. [[SYS-WIKI-SCHEMA-DETAIL]] resolves via id field)
    if by_id and target in by_id:
        return by_id[target]
    if by_id and base in by_id:
        return by_id[base]
    # Hyphen-prefix shortform match (e.g. [[LAW-016]] -> LAW-016-satory-frontend-lock.md)
    if by_prefix:
        for cand in (target, base):
            if cand in by_prefix and by_prefix[cand]:
                return by_prefix[cand][0]
    # Alias resolution
    if base in aliases_by_name:
        alias_target = aliases_by_name[base]
        return resolve_wikilink(alias_target, by_basename, by_full_path, aliases_by_name, skill_names, by_id, by_prefix) or "(via-alias)"
    return None


PLACEHOLDER_LINKS = {
    "wikilink", "law-nnn-...", "handoff-auto-...", "skill-name",
    "audit-name", "lesson-nnn-...", "spec-name", "law-nnn",
    "lesson-nnn", "handoff-auto-yyyy-mm-dd",
    "x", "<x>", "y", "<y>", "z", "<z>", "<inner>", "<outer>",
    "[<inner>", "<n>", "<num>", "<name>", "<id>",
    "skill-slug", "skill-z", "skill-name", "skill-a", "skill-b", "skill-c",
}

TERMINAL_HOST_TYPES = {"task-result", "alias", "raw-source", "lint"}

# Pattern that catches bash code accidentally captured by wikilink regex
BASH_LIKE_RE = re.compile(r'["$\\=]|^\s|\s$')


def is_placeholder(link: str) -> bool:
    norm = link.strip().lower()
    if norm in PLACEHOLDER_LINKS:
        return True
    if "..." in norm:
        return True
    if re.search(r"\b(yyyy|mm|dd|nnn|xxx)\b", norm):
        return True
    return False


def is_bash_artifact(link: str) -> bool:
    """Detect [[ "$(uname -s)" == "Darwin" ]] and similar bash double-bracket
    expressions captured by the wikilink regex."""
    if "$(" in link or '$' in link or '\\' in link:
        return True
    if link.strip().startswith('"') or '==' in link:
        return True
    # Leading whitespace inside the brackets is unusual for real wikilinks
    if link != link.strip():
        return True
    return False


def is_legacy_lesson(link: str) -> bool:
    """Old LESSON-NNN refs from before RULE ZERO migration are by-design legacy."""
    return bool(re.match(r"^lesson-\d+", link.strip().lower()))


# Top-level files referenced by wikilink (vault root, not under pages/).
# Both .md-suffixed and bare forms are honored.
TOP_LEVEL_FILES = {
    "claude.md", "memory.md", "log.md", "index.md", "readme.md",
    "claude", "memory", "log", "index", "readme",
}


def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks and inline code spans so wikilinks inside
    them are not treated as real cross-refs."""
    # Fenced ``` and ~~~ blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.DOTALL)
    # Inline `code`
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def scan_wikilinks(pages, by_basename, by_full_path, aliases_by_name, skill_names, by_id, by_prefix):
    broken = []
    total = 0
    seen_per_file = defaultdict(set)
    for p in pages:
        if p["type"] in TERMINAL_HOST_TYPES:
            continue
        full = (ROOT / p["path"])
        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        text = strip_code_blocks(text)
        host_subtier = subtier_for(p["path"])
        for m in WIKILINK_RE.finditer(text):
            link = m.group(1)
            if link in seen_per_file[p["path"]]:
                continue
            seen_per_file[p["path"]].add(link)
            total += 1
            if is_placeholder(link) or is_legacy_lesson(link) or is_bash_artifact(link):
                continue
            resolved = resolve_wikilink(link, by_basename, by_full_path, aliases_by_name, skill_names, by_id, by_prefix)
            if not resolved:
                broken.append({
                    "in_file": p["path"],
                    "host_subtier": host_subtier,
                    "link": link,
                })
    return total, broken


def scan_prose_ap_refs(pages, skills_with_aps):
    """A prose AP-ref counts only when the prefix word IS a known skill name."""
    broken = []
    total = 0
    seen_per_file = defaultdict(set)
    for p in pages:
        if p["path"] in SELF_AUDIT_EXCLUSIONS:
            continue
        full = (ROOT / p["path"])
        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        host_subtier = subtier_for(p["path"])
        for m in PROSE_AP_RE.finditer(text):
            skill_name = m.group(1).lower()
            ap_num = int(m.group(2))
            if skill_name not in skills_with_aps:
                continue
            key = (skill_name, ap_num)
            if key in seen_per_file[p["path"]]:
                continue
            seen_per_file[p["path"]].add(key)
            total += 1
            ap_set = skills_with_aps[skill_name]
            if ap_num not in ap_set:
                broken.append({
                    "in_file": p["path"],
                    "host_subtier": host_subtier,
                    "skill": skill_name,
                    "ap": ap_num,
                    "reason": f"ap-not-in-skill (skill has APs {sorted(ap_set)[:5]}{'...' if len(ap_set)>5 else ''})",
                })
    return total, broken


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-broken-sample", type=int, default=20)
    args = ap.parse_args()

    pages, by_basename, by_full_path, by_id, by_prefix, aliases_by_name, skills_with_aps = collect_pages()
    skill_names = set(skills_with_aps.keys())
    wl_total, wl_broken = scan_wikilinks(pages, by_basename, by_full_path, aliases_by_name, skill_names, by_id, by_prefix)
    ap_total, ap_broken = scan_prose_ap_refs(pages, skills_with_aps)

    # Tier scoping: gate applies to A1 stable. A2 (time-series) and B/C
    # legacy may legitimately contain stale refs to migrated/deleted files.
    wl_broken_a1 = [b for b in wl_broken if b["host_subtier"] == "A1"]
    ap_broken_a1 = [b for b in ap_broken if b["host_subtier"] == "A1"]

    gate_wl = len(wl_broken_a1) <= GATE_BROKEN_WIKILINKS_TIER_A1
    gate_ap = len(ap_broken_a1) <= GATE_BROKEN_PROSE_AP_TIER_A1
    all_pass = gate_wl and gate_ap

    payload = {
        "total_pages": len(pages),
        "wikilink_total": wl_total,
        "wikilink_broken_total": len(wl_broken),
        "wikilink_broken_tier_a1": len(wl_broken_a1),
        "prose_ap_total": ap_total,
        "prose_ap_broken_total": len(ap_broken),
        "prose_ap_broken_tier_a1": len(ap_broken_a1),
        "skills_indexed": len(skills_with_aps),
        "gates": {
            "broken_wikilinks_tier_a1": {"value": len(wl_broken_a1), "threshold": GATE_BROKEN_WIKILINKS_TIER_A1, "pass": gate_wl},
            "broken_prose_ap_refs_tier_a1": {"value": len(ap_broken_a1), "threshold": GATE_BROKEN_PROSE_AP_TIER_A1, "pass": gate_ap},
            "overall_pass": all_pass,
        },
        "broken_wikilinks_tier_a1_sample": wl_broken_a1[:args.max_broken_sample],
        "broken_wikilinks_all_sample": wl_broken[:args.max_broken_sample],
        "broken_prose_ap_tier_a1_sample": ap_broken_a1[:args.max_broken_sample],
        "broken_prose_ap_all_sample": ap_broken[:args.max_broken_sample],
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Total pages: {payload['total_pages']}, skills indexed: {payload['skills_indexed']}")
        print()
        print(f"Wikilinks: {wl_total} total")
        print(f"  Broken Tier A1 stable : {len(wl_broken_a1):4d}  (gate <= {GATE_BROKEN_WIKILINKS_TIER_A1})  -> {'PASS' if gate_wl else 'FAIL'}     [total all-tier: {len(wl_broken)}]")
        print(f"Prose AP refs: {ap_total} total")
        print(f"  Broken Tier A1 stable : {len(ap_broken_a1):4d}  (gate <= {GATE_BROKEN_PROSE_AP_TIER_A1})  -> {'PASS' if gate_ap else 'FAIL'}     [total all-tier: {len(ap_broken)}]")
        print()
        print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
        print()
        if wl_broken_a1:
            print(f"Broken Tier-A1 wikilinks ({len(wl_broken_a1)}):")
            for b in wl_broken_a1[:args.max_broken_sample]:
                print(f"  in {b['in_file']}")
                print(f"    [[{b['link']}]]")
        if ap_broken_a1:
            print(f"Broken Tier-A1 prose AP refs ({len(ap_broken_a1)}):")
            for b in ap_broken_a1[:args.max_broken_sample]:
                print(f"  in {b['in_file']}")
                print(f"    {b['skill']} AP-{b['ap']}  ({b['reason']})")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
