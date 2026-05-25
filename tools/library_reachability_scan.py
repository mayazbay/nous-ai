#!/usr/bin/env python3
"""
Library reachability scan (s82u Step 2, aligned to AUDIT-061 Tier policy).

For every page under pages/**/*.md (excluding archive/, task-results/, raw/),
classify reachability via 3 channels:
  1. inbound [[wikilink]] anywhere in pages/
  2. prose-form basename mention in pages/skills/ or pages/laws/
  3. listed in pages/skills/_gbrain/RESOLVER.md

Pages with 0 of 3 = candidate orphans. Channel 4 (gbrain search) is deferred
to manual triage on borderline candidates.

Tier policy is imported from tools/library_quality_scan.py. Tier A is the core
runtime/library catalog (laws, skills, systems, entities, projects, canonical
concepts, tenant skill docs). Tier B is report/import/receipt material (audits,
specs, plans, handoffs, dashboards, task-results, sources, _gbrain mirrors).
Tier C is legacy/archive material (claude-memory, lessons, commit-review,
extracted, fallback).

Gate (s82u handoff, scoped to AUDIT-061): Tier-A orphan rate <= 10%.
Tier B and Tier C orphan counts are reported informationally — those tiers
are terminal-by-design per the user-signed library contract.

Usage:
  python3 tools/library_reachability_scan.py
  python3 tools/library_reachability_scan.py --json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
EXCLUDE_DIRS = {"archive", "task-results", "raw"}
TERMINAL_TYPES = {"task-result", "alias", "raw-source", "lint"}
TIER_A_GATE_PCT = 10.0

# Reuse classifier from the canonical library scanner so this audit honors the
# same user-signed Tier contract codified in pages/audits/AUDIT-061-*.md.
sys.path.insert(0, str(ROOT / "tools"))
from library_quality_scan import classify as classify_tier  # noqa: E402


def read_frontmatter_type(path: Path):
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except Exception:
        return None
    m = re.match(r"^---\n(.*?)\n---", head, re.DOTALL)
    if not m:
        return None
    for line in m.group(1).splitlines():
        s = line.strip()
        if s.startswith("type:"):
            return s.split(":", 1)[1].strip().strip('"').strip("'").lower()
    return None


def collect_pages():
    out = []
    for p in PAGES.rglob("*.md"):
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if any(d in parts for d in EXCLUDE_DIRS):
            continue
        ptype = read_frontmatter_type(p)
        rel_str = str(rel)
        out.append({
            "path": rel_str,
            "slug": rel_str[:-3],
            "basename": p.stem,
            "type": ptype or "(none)",
            "tier": classify_tier(rel_str),
        })
    return out


def collect_wikilink_targets():
    targets = set()
    pattern = re.compile(r"\[\[([^\]\n]+?)\]\]")
    for p in PAGES.rglob("*.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in pattern.finditer(text):
            raw = m.group(1)
            target = raw.split("|", 1)[0].split("#", 1)[0].strip().lower()
            if not target:
                continue
            targets.add(target)
            if "/" in target:
                targets.add(target.rsplit("/", 1)[-1])
    return targets


def iter_corpus_files(*subdirs, exclude_paths=None):
    """Yield markdown files under given subdirs, excluding known self-audits."""
    exclude_paths = exclude_paths or set()
    for d in subdirs:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            rel = str(p.relative_to(ROOT))
            if rel in exclude_paths:
                continue
            yield p


WORD_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
WORD_TOKEN_FULL_RE = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")


def collect_prose_hits(subdirs, terms, exclude_paths=None):
    """Return terms found in corpus files without materializing the corpus.

    The old scanner joined the entire skills/laws/audits/specs/plans/systems/
    dashboards corpus into one giant lowercase string. At current vault size,
    the pre-commit hook can be killed by the OS before it reports a useful
    failure. This function streams files and records only basename hits.
    """
    term_set = {t.lower() for t in terms if t}
    hits = set()
    fast_terms = {t for t in term_set if WORD_TOKEN_FULL_RE.match(t)}
    slow_terms = term_set - fast_terms

    for p in iter_corpus_files(*subdirs, exclude_paths=exclude_paths):
        try:
            text = p.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue
        if fast_terms:
            hits.update(fast_terms.intersection(WORD_TOKEN_RE.findall(text)))
        for term in slow_terms - hits:
            if has_word_match(text, term):
                hits.add(term)
    return hits


def has_word_match(corpus_lower: str, term: str) -> bool:
    if not term:
        return False
    pattern = r"(?<![A-Za-z0-9_-])" + re.escape(term.lower()) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, corpus_lower) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-sample", type=int, default=20)
    args = ap.parse_args()

    pages = collect_pages()
    audit_pages = [p for p in pages if p["type"] not in TERMINAL_TYPES]

    wikilink_targets = collect_wikilink_targets()
    # Channel 2 corpus: top-of-funnel + mid-funnel cross-reference docs.
    # Libraries are reachable via citations across audits/specs/plans/systems/
    # dashboards/concepts, not just from skills/laws. This honors the
    # CLAUDE.md amendment that prose cross-refs are library-grade-compliant.
    # Exclude self-referential audit receipts (this audit + its s100 sibling)
    # so listing orphans in the audit body doesn't auto-validate them.
    self_audit_exclusions = {
        "pages/audits/AUDIT-LIBRARY-REACHABILITY-2026-04-30.md",
        "pages/audits/AUDIT-LIBRARY-CANONICAL-2026-04-30.md",
        "pages/audits/AUDIT-LIBRARY-CROSSREFS-2026-04-30.md",
    }
    prose_hits = collect_prose_hits(
        (
            "pages/skills",
            "pages/laws",
            "pages/audits",
            "pages/specs",
            "pages/plans",
            "pages/systems",
            "pages/dashboards",
            "pages/concepts",
            "pages/progress/plans",
        ),
        {p["basename"].lower() for p in audit_pages},
        exclude_paths=self_audit_exclusions,
    )
    resolver_path = PAGES / "skills" / "_gbrain" / "RESOLVER.md"
    resolver_text = (
        resolver_path.read_text(encoding="utf-8", errors="replace").lower()
        if resolver_path.exists() else ""
    )

    orphans = []
    for p in audit_pages:
        b = p["basename"].lower()
        s = p["slug"].lower()
        in_wl = (b in wikilink_targets) or (s in wikilink_targets)
        in_prose = in_wl or b in prose_hits
        in_resolver = b in resolver_text
        if not (in_wl or in_prose or in_resolver):
            orphans.append(p)

    # Tier A is normally all A1 under the current core-only contract. The A2
    # split remains as a defensive compatibility guard for future dated series
    # that might be promoted into Tier A; current report streams classify as B.
    TIMESERIES_RES = (
        re.compile(r"^pages/progress/HANDOFF.+\.md$"),
        re.compile(r"^pages/dashboards/dream-cycle-proposals-\d{4}-\d{2}-\d{2}\.md$"),
        re.compile(r"^pages/progress/daily-factory-analysis-\d{4}-\d{2}-\d{2}\.md$"),
        re.compile(r"^pages/progress/commit-review-\d{4}-\d{2}-\d{2}\.md$"),
    )

    def subtier(p):
        if p["tier"] != "A":
            return p["tier"]
        return "A2" if any(r.match(p["path"]) for r in TIMESERIES_RES) else "A1"

    by_tier_total = {"A1": 0, "A2": 0, "B": 0, "C": 0}
    by_tier_orphan = {"A1": 0, "A2": 0, "B": 0, "C": 0}
    for p in audit_pages:
        by_tier_total[subtier(p)] += 1
    for o in orphans:
        by_tier_orphan[subtier(o)] += 1

    def rate(o, t):
        return round(100.0 * o / max(t, 1), 2)

    tier_a1_rate = rate(by_tier_orphan["A1"], by_tier_total["A1"])
    tier_a_combined_rate = rate(
        by_tier_orphan["A1"] + by_tier_orphan["A2"],
        by_tier_total["A1"] + by_tier_total["A2"],
    )
    gate_pass = tier_a1_rate <= TIER_A_GATE_PCT

    tier_a1_orphans = [o for o in orphans if subtier(o) == "A1"]
    tier_a2_orphans = [o for o in orphans if subtier(o) == "A2"]
    tier_b_orphans = [o for o in orphans if o["tier"] == "B"]
    tier_c_orphans = [o for o in orphans if o["tier"] == "C"]

    payload = {
        "total_pages_walked": len(pages),
        "terminal_excluded": len(pages) - len(audit_pages),
        "non_terminal_total": len(audit_pages),
        "tier_totals": by_tier_total,
        "tier_orphan_counts": by_tier_orphan,
        "tier_orphan_rates_pct": {
            t: rate(by_tier_orphan[t], by_tier_total[t]) for t in by_tier_total
        },
        "tier_a_combined_rate_pct": tier_a_combined_rate,
        "gate_threshold_tier_a1_pct": TIER_A_GATE_PCT,
        "tier_a1_gate_pass": gate_pass,
        "tier_a1_orphan_count": by_tier_orphan["A1"],
        "tier_a1_orphan_sample": [
            {"type": o["type"], "path": o["path"]} for o in tier_a1_orphans[:args.max_sample]
        ],
        "tier_a2_orphan_sample": [
            {"type": o["type"], "path": o["path"]} for o in tier_a2_orphans[:5]
        ],
        "tier_b_orphan_sample": [
            {"type": o["type"], "path": o["path"]} for o in tier_b_orphans[:5]
        ],
        "tier_c_orphan_sample": [
            {"type": o["type"], "path": o["path"]} for o in tier_c_orphans[:5]
        ],
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Total pages walked: {payload['total_pages_walked']}")
        print(f"  Terminal-excluded (task-result/alias/raw-source/lint): {payload['terminal_excluded']}")
        print(f"  Non-terminal candidates: {payload['non_terminal_total']}")
        print()
        print(f"Tier totals:  A1={by_tier_total['A1']} A2={by_tier_total['A2']} B={by_tier_total['B']} C={by_tier_total['C']}")
        print(f"Orphans:      A1={by_tier_orphan['A1']} A2={by_tier_orphan['A2']} B={by_tier_orphan['B']} C={by_tier_orphan['C']}")
        print(f"Orphan %:     A1={tier_a1_rate}%  A2={rate(by_tier_orphan['A2'], by_tier_total['A2'])}%  B={rate(by_tier_orphan['B'], by_tier_total['B'])}%  C={rate(by_tier_orphan['C'], by_tier_total['C'])}%")
        print(f"  A combined orphan rate: {tier_a_combined_rate}% (informational; gate is A1 only)")
        print()
        print(f"GATE (Tier A1 stable orphan <= {TIER_A_GATE_PCT}%): {'PASS' if gate_pass else 'FAIL'}  -> {tier_a1_rate}%")
        print()
        if tier_a1_orphans:
            print(f"Tier-A1 (stable) orphans ({min(len(tier_a1_orphans), args.max_sample)} of {len(tier_a1_orphans)}):")
            for o in tier_a1_orphans[:args.max_sample]:
                print(f"  {o['type']:18s} {o['path']}")
        else:
            print("Tier-A1 orphans: NONE")
        print()
        if tier_a2_orphans:
            print(f"Tier-A2 (handoff) orphans: {len(tier_a2_orphans)} (informational; time-series receipts are forward-pointing-only)")
        else:
            print("Tier-A2 orphans: NONE")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
