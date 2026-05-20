#!/usr/bin/env python3
"""
Find prose drift-correction markers in the wiki — AP-61 Phase 3 deliverable.

Implements the opt-in audit from
pages/specs/2026-04-30-ap61-supersession-metadata-stub.md Decision D6:
"Ship `tools/find_drift_corrections.py` that scans wiki for prose drift-
correction headers and reports candidates. Output is a list, not a mutation.
Madi or an agent reviews each candidate, decides if it's truly superseded,
and applies frontmatter manually via tools/mark_superseded.sh."

NO AUTO-MUTATION. This script only READS files and PRINTS candidates.

Usage:
    python3 tools/find_drift_corrections.py
    python3 tools/find_drift_corrections.py --json
    python3 tools/find_drift_corrections.py --include "lessons/" --exclude "progress/"

Falsifiability per AP-61 spec: "runs on current wiki, reports a finite list
of candidates Madi can spot-check."
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Markers that indicate prose-style drift annotation (vs structured frontmatter).
# Each pattern matches a single line; we capture the line number and the
# surrounding 1-line context.
#
# Tightened per autoplan v1 (full 6-voice, 2026-04-30):
# - Dropped `header_supersede` pattern (## Historical/Archived/... fired on every
#   spec with a "Historical context" section — pure FP)
# - Dropped `bold_correction` pattern (**Correction:** fires on inline corrections
#   like "Correction (afternoon): the meeting was 2-way not 3-way" — not supersession)
# - Restricted scanning to FIRST 30 LINES of each file (header zone) — drift
#   markers belong near the top, not buried in body discussion
# - Excluded `type: spec` pages by default — specs DOCUMENT supersession patterns,
#   they aren't themselves the subjects
# - Excluded pages already marked superseded (presence of `superseded_by:` field)
DRIFT_PATTERNS = [
    # Original signal from gbrain-ops AP-50 / Mercury thesis
    (re.compile(r">\s*⚠️\s*DRIFT\s*CORRECTION", re.IGNORECASE), "drift_correction_warning"),
    # Variations: ⚠️ + explicit supersede word (high precision)
    (re.compile(r">\s*⚠️.*\b(superseded|deprecated|outdated|replaced)\b", re.IGNORECASE), "warning_supersede_word"),
    # Bold supersession declarations (high precision)
    (re.compile(r"^>?\s*\*\*\s*(superseded|deprecated|obsolete|replaced)\s+by\b", re.IGNORECASE), "bold_superseded_by"),
    # Bold UPDATE-with-date markers (medium precision; usually means correction)
    (re.compile(r"^>?\s*\*\*UPDATE\s+\d{4}-\d{2}-\d{2}\*\*", re.IGNORECASE), "bold_update_date"),
]

# Restrict to first N lines (header zone). Drift markers in body discussion
# (e.g. a spec's prose explanation of supersession) are not flags-on-this-page.
HEADER_ZONE_LINES = 30

# Skip these directories — auto-generated chronologicals where "drift correction"
# terminology is part of normal handoff content, not a marker.
DEFAULT_EXCLUDE_DIRS = {
    "pages/progress/",
    "pages/task-results/",
    "pages/progress/claude-memory/",
    "pages/skills/extracted/",
    "pages/audits/",  # audits often discuss drift; not themselves superseded
    "pages/schemas/",  # JSON schemas don't have drift markers
}


def scan_file(path: Path, include_root: Path) -> list[dict]:
    """Scan a single .md file for drift markers (HEADER ZONE only). Returns list of hits."""
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return hits

    # Skip files already marked superseded in frontmatter (presence of `superseded_by:`)
    # Per AP-61 v1 schema (no `status:` field, signal by presence)
    if re.search(r"^superseded_by:\s*$", text, re.MULTILINE):
        return hits

    # Skip `type: spec` pages — specs DOCUMENT supersession, aren't subjects
    if re.search(r"^type:\s*spec\s*$", text, re.MULTILINE):
        return hits

    rel = path.relative_to(include_root)
    for ln, line in enumerate(text.splitlines()[:HEADER_ZONE_LINES], 1):
        for pat, label in DRIFT_PATTERNS:
            if pat.search(line):
                hits.append({
                    "slug": str(rel).replace(".md", ""),
                    "path": str(rel),
                    "line": ln,
                    "marker": label,
                    "context": line.strip()[:120],
                })
                break  # one hit per line is enough
    return hits


def find_candidates(
    vault_root: Path,
    include_globs: list[str] | None,
    exclude_dirs: set[str],
) -> list[dict]:
    """Walk the wiki, find candidate drift-correction pages."""
    pages_root = vault_root / "pages"
    if not pages_root.is_dir():
        sys.stderr.write(f"ERROR: {pages_root} not a directory\n")
        sys.exit(2)

    candidates: list[dict] = []
    for md in pages_root.rglob("*.md"):
        rel = md.relative_to(vault_root)
        rel_str = str(rel)
        # Exclude default + user dirs
        if any(rel_str.startswith(ex) for ex in exclude_dirs):
            continue
        # Include filter (optional): only scan paths matching at least one glob
        if include_globs:
            if not any(g in rel_str for g in include_globs):
                continue
        hits = scan_file(md, vault_root)
        candidates.extend(hits)

    return candidates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("--vault", default=str(Path(__file__).resolve().parent.parent),
                    help="Wiki vault root (default: parent of this script)")
    ap.add_argument("--include", action="append", default=[],
                    help="Include only paths containing this substring (repeatable)")
    ap.add_argument("--exclude", action="append", default=[],
                    help="Add to default-exclude dirs (repeatable)")
    ap.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")
    ap.add_argument("--limit", type=int, default=0, help="Max candidates to print (0 = no limit)")
    args = ap.parse_args()

    vault_root = Path(args.vault).resolve()
    exclude = DEFAULT_EXCLUDE_DIRS | set(args.exclude)

    candidates = find_candidates(vault_root, args.include or None, exclude)

    if args.limit > 0:
        candidates = candidates[: args.limit]

    if args.json:
        print(json.dumps({
            "vault": str(vault_root),
            "include_filters": args.include or [],
            "excluded_dirs": sorted(exclude),
            "candidate_count": len(candidates),
            "candidates": candidates,
        }, indent=2, ensure_ascii=False))
        return 0

    # Human-readable
    if not candidates:
        print(f"✅ No drift-correction candidates found in {vault_root}/pages/")
        print(f"   (excluded dirs: {sorted(exclude)})")
        return 0

    print(f"Found {len(candidates)} drift-correction candidate line(s) across {len({c['path'] for c in candidates})} pages:\n")
    last_path = None
    for c in candidates:
        if c["path"] != last_path:
            print(f"\n📄 {c['path']}")
            last_path = c["path"]
        print(f"   line {c['line']:>4} [{c['marker']:>26}] {c['context']}")

    print(f"\n--- Next step (per AP-61 spec D6) ---")
    print(f"Review each candidate. If genuinely superseded, run:")
    print(f"  tools/mark_superseded.sh <old-slug> <new-canonical-slug>")
    print(f"to write structured frontmatter (status: superseded, superseded_by:, superseded_at:, superseded_reason:)")
    print(f"NO AUTO-MUTATION from this scanner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
