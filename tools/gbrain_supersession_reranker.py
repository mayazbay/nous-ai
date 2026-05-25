#!/usr/bin/env python3
"""
gbrain_supersession_reranker.py — AP-61 Phase-2 deliverable.

Local Nous-controlled post-retrieval reranker that demotes superseded pages
in gbrain query results. Implements the AP-61 v1 schema (per spec D1+D2,
accepted-with-defaults T2-A: local-shim NOT garrytan/gbrain v0.23 dependency).

Reads `superseded_by:` field from each candidate page's frontmatter at query
time. If present, multiplies relevance score by `SUPERSESSION_DEMOTION`
(default 0.3, configurable via env). Reversible by setting demotion to 1.0.

Usage as a module:
    from gbrain_supersession_reranker import rerank
    results = rerank(gbrain_results, vault_root=Path("..."))
    # results: same shape, with superseded pages demoted

Usage as a CLI (for testing):
    python3 tools/gbrain_supersession_reranker.py --query "test query" --json

Falsifiability per AP-61 spec D2:
- Sweep `SUPERSESSION_DEMOTION` in {0.0, 0.1, 0.3, 0.5, 0.7, 1.0} on
  lane-D's 6 retrieval probes; pick smallest demotion that flips 2/6 fails
  to 0/6 without false demotion of useful history.

Privacy: reads only frontmatter; never reads page body. No PII surface.
Anti-dependency: no upstream gbrain code change required. Wraps existing
gbrain query results post-hoc. Drop-in for any consumer.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

VAULT = Path(os.environ.get("VAULT", Path(__file__).resolve().parent.parent))
DEMOTION = float(os.environ.get("SUPERSESSION_DEMOTION", "0.3"))
ARCHIVED_FACTOR = float(os.environ.get("SUPERSESSION_ARCHIVED", "0.0"))
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def page_supersession_state(slug_or_path: str) -> dict[str, Any]:
    """Returns {'superseded': bool, 'archived': bool, 'targets': [...]}.
    Per AP-61 v1: presence of `superseded_by:` IS the supersession signal.
    No `status:` field (collision with 782 existing pages).
    """
    state: dict[str, Any] = {"superseded": False, "archived": False, "targets": []}
    candidates = [
        VAULT / slug_or_path,
        VAULT / f"{slug_or_path}.md",
        VAULT / "pages" / f"{slug_or_path}.md",
        VAULT / "pages" / slug_or_path / "SKILL.md",
        VAULT / "pages" / "skills" / slug_or_path / "SKILL.md",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return state

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return state

    m = FRONTMATTER_RE.match(text)
    if not m:
        return state
    fm_text = m.group(1)

    # Look for superseded_by: list — both inline and block forms
    sb_match = re.search(r"^superseded_by:\s*(.*?)(?=^[a-zA-Z_]|\Z)", fm_text, re.MULTILINE | re.DOTALL)
    if sb_match:
        state["superseded"] = True
        # Extract wikilinks from the block
        targets = re.findall(r"\[\[([^\[\]]+)\]\]", sb_match.group(1))
        state["targets"] = targets

    # Optional v2 field: archived status (page is dead-stop, no redirect)
    if re.search(r"^archived_at:\s*\d{4}-\d{2}-\d{2}\s*$", fm_text, re.MULTILINE):
        state["archived"] = True

    return state


def rerank(
    results: Iterable[dict[str, Any]],
    score_field: str = "score",
    slug_field: str = "slug",
    demotion: float | None = None,
    archived_factor: float | None = None,
) -> list[dict[str, Any]]:
    """Apply supersession demotion to a list of gbrain-shaped results.

    Each result must be a dict with `slug` and `score` fields (configurable).
    Returns a NEW list (does not mutate input). Adds `_supersession_state`
    field for transparency/debugging.

    Demotion rules (per AP-61 D2):
      - `archived: true` (v2-only)         -> score *= ARCHIVED_FACTOR (default 0.0; excludes)
      - `superseded_by:` field present     -> score *= DEMOTION       (default 0.3)
      - neither                            -> score unchanged
    """
    d = demotion if demotion is not None else DEMOTION
    a = archived_factor if archived_factor is not None else ARCHIVED_FACTOR

    out: list[dict[str, Any]] = []
    for r in results:
        new_r = dict(r)
        slug = r.get(slug_field) or ""
        state = page_supersession_state(slug)
        if state["archived"]:
            new_r[score_field] = r.get(score_field, 0.0) * a
        elif state["superseded"]:
            new_r[score_field] = r.get(score_field, 0.0) * d
        new_r["_supersession_state"] = state
        out.append(new_r)
    # Re-sort by score descending (post-rerank order)
    out.sort(key=lambda x: x.get(score_field, 0.0), reverse=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="AP-61 Phase-2 supersession reranker")
    ap.add_argument("--query", help="Demo: simulate a query result and rerank it")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--demotion", type=float, default=None, help="Demotion factor (default $SUPERSESSION_DEMOTION or 0.3)")
    ap.add_argument("--probe", action="store_true", help="Run lane-D's 6-probe self-test")
    args = ap.parse_args()

    if args.probe:
        # Lane-D's 6 retrieval-probe slugs (per AUDIT-062 Mercury thesis evidence)
        probes = [
            ("LESSON-087-telegram-mcp-token-scoped-ban", 1.0),
            ("architecture-quickref", 0.95),
            ("feedback_musk_5_steps", 0.9),
            ("musk-algorithm", 0.85),
            ("session-operating-contract", 0.8),
            ("karpathy-loop", 0.75),
        ]
        results = [{"slug": slug, "score": score} for slug, score in probes]
        out = rerank(results, demotion=args.demotion)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"AP-61 Phase-2 reranker probe (DEMOTION={args.demotion or DEMOTION})")
            print("=" * 60)
            for r in out:
                state = r["_supersession_state"]
                marker = "🟡 superseded" if state["superseded"] else "⚪ archived" if state["archived"] else "✅ current"
                print(f"  {r['score']:.3f}  {marker:20s}  {r['slug']}")
                if state["targets"]:
                    print(f"           targets: {state['targets']}")
        return 0

    if args.query:
        # Demo: 3 synthetic results with varied state
        sample = [
            {"slug": "vpn-erap-deployment-checklist", "score": 0.95},
            {"slug": "skills/factory-ops/skill", "score": 0.90},
            {"slug": "skills/karpathy-loop/skill", "score": 0.85},
        ]
        out = rerank(sample, demotion=args.demotion)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"Demo rerank (DEMOTION={args.demotion or DEMOTION}):")
            for r in out:
                state = r["_supersession_state"]
                marker = "🟡" if state["superseded"] else "⚪" if state["archived"] else "✅"
                print(f"  {r['score']:.3f}  {marker}  {r['slug']}")
        return 0

    ap.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
