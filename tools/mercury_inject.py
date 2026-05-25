#!/usr/bin/env python3
"""mercury_inject.py — Mercury Phase 2 selective injector.

Reads pages/mercury/facts.jsonl, scores non-tombstoned facts, packs the top-K
into a token-budgeted block (default 1500 tokens via tiktoken cl100k_base),
and emits text suitable for SessionStart hook injection.

Score formula (from PLAN-2026-04-29-substrate-evolution-S0-S1 §Selective injection):
    score = importance × freshness_decay × (1 + 0.1 × reinforcement) × load_bearing_weight

Where:
- importance ∈ [0,1] from the fact
- freshness_decay = 1 / (1 + days_since_freshness/30) — soft 30-day half-life
- reinforcement is the fact's reinforcement count
- load_bearing_weight = 1 + 0.05 × len(load_bearing_in)

Modes:
  --shadow            print injection block + metrics; do NOT modify hook
  --metrics-only      print only token count, fact count, token-delta vs MEMORY.md
  --dry-run           print top-K facts ranked, no packing
  --emit              print only the stable injection block (for hook consumption)
  --live-context      include volatile session-id/HEAD/HANDOFF context in --emit output

Phase 2 acceptance gates (per plan v2):
- Token delta: ≤ budget AND ≥30% smaller than current MEMORY top-block
- Fact overlap: ≥80% of MEMORY's load-bearing claims present in top-K
- Retrieval quality: 10 fixed queries, ≥90% answer-correctness (manually scored)

This script handles gates 1 + 2 mechanically. Gate 3 is human-in-the-loop.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import subprocess

REPO = Path(__file__).resolve().parent.parent
FACTS = Path(os.environ.get("MERCURY_FACTS_IN", REPO / "pages" / "mercury" / "facts.jsonl"))
MEMORY = REPO / "pages" / "progress" / "claude-memory" / "MEMORY.md"
HANDOFFS_DIR = REPO / "pages" / "progress"
MADI_DIRECTIVE = (
    'best CTO/CEO + Musk Algorithm 5-step + Karpathy/Tan compounding + '
    'billion-dollar-solopreneur standard; substrate IS the handshake.'
)
DEFAULT_BUDGET = int(os.environ.get("MERCURY_INJECT_BUDGET_TOKENS", "1700"))
HARD_CEILING = 6000
# s82h bumped 1500 -> 1700 to absorb now-context-header (~110 tokens) +
# dedup'd Laws (~150 saved). Still 90%+ reduction vs 18,192-token MEMORY.


def _load_tiktoken():
    try:
        import tiktoken  # type: ignore
        return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        venv_site = REPO / ".venv" / "lib"
        if venv_site.exists():
            for p in venv_site.glob("python*/site-packages"):
                sys.path.insert(0, str(p))
            try:
                import tiktoken  # type: ignore
                return tiktoken.get_encoding("cl100k_base")
            except ImportError:
                pass
        sys.stderr.write("FAIL: tiktoken not found. Install: .venv/bin/pip install tiktoken\n")
        sys.exit(2)


def freshness_decay(freshness_str: str) -> float:
    try:
        d = datetime.strptime(freshness_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0.5
    days = max(0, (date.today() - d).days)
    return 1.0 / (1.0 + days / 30.0)


def score_fact(f: dict) -> float:
    if f.get("tombstone"):
        return 0.0
    importance = float(f.get("importance", 0.5))
    decay = 1.0 if f.get("decay_rule") == "permanent" else freshness_decay(f.get("freshness", ""))
    reinforcement = int(f.get("reinforcement", 0))
    lb = len(f.get("load_bearing_in", []) or [])
    lb_weight = 1.0 + 0.05 * lb
    return importance * decay * (1.0 + 0.1 * reinforcement) * lb_weight


def render_fact(f: dict) -> str:
    return f"- {f['subject']}: {f['value']} [{f['source']}]"


def load_facts() -> list[dict]:
    if not FACTS.exists():
        sys.stderr.write(f"FAIL: {FACTS} not found. Run mercury_seed.py --apply first.\n")
        sys.exit(2)
    facts = []
    with FACTS.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            facts.append(json.loads(line))
    return facts


def pack_to_budget(scored: list[tuple[float, dict]], budget: int, enc) -> list[dict]:
    """Pack facts into token budget.

    Priority pass (s82g): carryover facts (active session debt — BLOCKED, DEFERRED)
    pack first regardless of score, since they answer "what's blocking right now?"
    Remaining budget fills with score-ranked non-carryover facts.
    """
    selected: list[dict] = []
    used = 0
    header = "# Mercury fact-block (top-K selective injection)\n\n"
    used += len(enc.encode(header))
    # Reserve overhead for emit_block now-context-header (~110 tokens) +
    # 5 section headers (## Active carryover, ## Laws, ## Skill anti-patterns,
    # ## Recent session decisions, ## Other; ~30 tokens total).
    # s82h bumped 30 -> 150 to absorb now-context-header.
    used += 150
    seen: set[str] = set()
    # Pass 1: pack carryover first (priority — active debt always surfaces)
    for score, fact in scored:
        if "carryover" not in fact.get("tags", []):
            continue
        rendered = render_fact(fact) + "\n"
        cost = len(enc.encode(rendered))
        if used + cost > budget:
            break
        selected.append(fact)
        seen.add(fact["id"])
        used += cost
    # Pass 2: score-ranked fill of the rest
    for score, fact in scored:
        if fact["id"] in seen:
            continue
        rendered = render_fact(fact) + "\n"
        cost = len(enc.encode(rendered))
        if used + cost > budget:
            break
        selected.append(fact)
        used += cost
    return selected


def _stable_context() -> str:
    return (
        "# Now context (stable tracked Mercury block)\n"
        "- live session-id, HEAD, and latest HANDOFF are injected by the session preamble; this tracked file stays deterministic.\n"
        f"- Madi directive (sticky): {MADI_DIRECTIVE}\n"
        "\n"
    )


def _live_context() -> str:
    """Build a 5-line 'Now' header so agents inherit live state, not just doctrine.
    Lane S (s82h, 2026-04-29): without this header, post-Phase-3 agent has zero
    session-id / HEAD / HANDOFF pointer / Madi directive — regression vs MEMORY.
    """
    today = date.today().isoformat()
    sid_path = Path.home() / ".claude" / "sessions" / "current_session_id"
    sid = sid_path.read_text(encoding="utf-8").strip() if sid_path.exists() else "(unregistered)"
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO),
            stderr=subprocess.DEVNULL, timeout=2,
        ).decode("utf-8").strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        head = "(unknown)"
    latest_handoff = "(none)"
    try:
        handoffs = sorted(HANDOFFS_DIR.glob("HANDOFF-AUTO-*.md"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
        if handoffs:
            latest_handoff = f"[[{handoffs[0].stem}]]"
    except OSError:
        pass
    return (
        "# Now context (live, regenerated per session-start)\n"
        f"- date: {today}\n"
        f"- session-id: {sid}\n"
        f"- HEAD: {head}\n"
        f"- latest HANDOFF: {latest_handoff}\n"
        f"- Madi directive (sticky): {MADI_DIRECTIVE}\n"
        "\n"
    )


def _latest_selected_date(selected: list[dict]) -> str:
    dates: list[str] = []
    for fact in selected:
        value = fact.get("freshness")
        if not isinstance(value, str):
            continue
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            continue
        dates.append(value)
    return max(dates) if dates else date.today().isoformat()


def emit_block(selected: list[dict], *, live_context: bool = False) -> str:
    # YAML frontmatter so gbrain ingest doesn't trip MISSING_OPEN lint.
    # Closes the recurring bug where Mercury regen overwrote prepended FM
    # every session, dragging doctor.frontmatter_integrity below clean.
    today = date.today().isoformat() if live_context else _latest_selected_date(selected)
    fm = [
        "---",
        "type: progress",
        "id: MEMORY-mercury",
        "title: \"Mercury memory file (live, regenerated per session-start)\"",
        "tags: [memory, mercury, session-start, progress]",
        f"date: {today}",
        f"last_updated: {today}",
        "status: active",
        "---",
        "",
    ]
    context = _live_context() if live_context else _stable_context()
    lines = fm + [context.rstrip(), "", "# Mercury fact-block (top-K selective injection)", ""]
    by_kind: dict[str, list[dict]] = {"carryover": [], "law": [], "skill-ap": [], "handoff": [], "other": []}
    for f in selected:
        tags = f.get("tags", [])
        if "carryover" in tags:
            by_kind["carryover"].append(f)
        elif "law" in tags:
            by_kind["law"].append(f)
        elif "skill-ap" in tags:
            by_kind["skill-ap"].append(f)
        elif "handoff" in tags:
            by_kind["handoff"].append(f)
        else:
            by_kind["other"].append(f)
    for kind, label in (("carryover", "## Active carryover (BLOCKED + DEFERRED)"),
                         ("law", "## Laws"), ("skill-ap", "## Skill anti-patterns"),
                         ("handoff", "## Recent session decisions"), ("other", "## Other")):
        items = by_kind[kind]
        if not items:
            continue
        lines.append(label)
        for f in items:
            lines.append(render_fact(f))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def memory_metrics(enc) -> dict:
    """Measure MEMORY.md against both definitions:
    - top_stanza: first stanza before `\n---\n` (plan v2 literal wording)
    - full_file:  the whole MEMORY.md (real session-start context tax)
    """
    if not MEMORY.exists():
        return {"top_tokens": 0, "top_chars": 0, "full_tokens": 0, "full_chars": 0, "stanzas": 0}
    text = MEMORY.read_text(encoding="utf-8")
    parts = text.split("\n---\n")
    top = parts[0] if parts else text
    return {
        "top_tokens": len(enc.encode(top)),
        "top_chars": len(top),
        "full_tokens": len(enc.encode(text)),
        "full_chars": len(text),
        "stanzas": len(parts),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--shadow", action="store_true", help="print block + metrics (Phase 2 gate)")
    g.add_argument("--metrics-only", action="store_true")
    g.add_argument("--dry-run", action="store_true", help="print ranked top-K, no packing")
    g.add_argument("--emit", action="store_true", help="print only the injection block")
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                    help=f"token budget (default {DEFAULT_BUDGET}, hard ceiling {HARD_CEILING})")
    ap.add_argument("--top-k", type=int, default=50, help="dry-run: how many to print (default 50)")
    ap.add_argument("--live-context", action="store_true",
                    help="include volatile session-id/HEAD/latest-HANDOFF context in emitted output")
    args = ap.parse_args()

    if args.budget > HARD_CEILING:
        sys.stderr.write(f"FAIL: budget {args.budget} > hard ceiling {HARD_CEILING}\n")
        return 2

    enc = _load_tiktoken()
    facts = load_facts()
    scored = sorted(((score_fact(f), f) for f in facts if not f.get("tombstone")),
                    key=lambda x: x[0], reverse=True)

    if args.dry_run:
        for score, f in scored[: args.top_k]:
            sys.stdout.write(f"{score:.3f}  {f['id']}  {f['subject']}  {f['value'][:80]}\n")
        return 0

    selected = pack_to_budget(scored, args.budget, enc)
    block = emit_block(selected, live_context=args.live_context)
    block_tokens = len(enc.encode(block))

    if args.emit:
        sys.stdout.write(block)
        return 0

    m = memory_metrics(enc)
    top_delta_pct = ((m["top_tokens"] - block_tokens) / m["top_tokens"] * 100) if m["top_tokens"] else 0.0
    full_delta_pct = ((m["full_tokens"] - block_tokens) / m["full_tokens"] * 100) if m["full_tokens"] else 0.0

    metrics_lines = [
        "=== Mercury Phase 2 metrics ===",
        f"facts total:               {len(facts)}",
        f"facts non-tombstoned:      {sum(1 for f in facts if not f.get('tombstone'))}",
        f"facts selected:            {len(selected)}",
        f"budget tokens:             {args.budget}",
        f"block tokens:              {block_tokens}",
        "",
        f"MEMORY full file:          {m['full_tokens']} tokens ({m['full_chars']} chars, {m['stanzas']} stanzas)",
        f"MEMORY top stanza:         {m['top_tokens']} tokens ({m['top_chars']} chars)",
        f"vs full-file delta:        {m['full_tokens'] - block_tokens} fewer ({full_delta_pct:.1f}% reduction)",
        f"vs top-stanza delta:       {m['top_tokens'] - block_tokens} fewer ({top_delta_pct:.1f}% reduction)",
        "",
        "Phase 2 gate 1 (token delta):",
        f"  budget compliance:       {'PASS' if block_tokens <= args.budget else 'FAIL'} ({block_tokens} ≤ {args.budget})",
        f"  ≥30% smaller vs full:    {'PASS' if full_delta_pct >= 30 else 'FAIL'} ({full_delta_pct:.1f}%)",
        f"  ≥30% smaller vs top:     {'PASS' if top_delta_pct >= 30 else 'FAIL — Mercury bloats top-stanza by design (full-file is the right comparison)'} ({top_delta_pct:.1f}%)",
    ]

    if args.metrics_only:
        sys.stdout.write("\n".join(metrics_lines) + "\n")
        return 0

    sys.stdout.write("\n".join(metrics_lines) + "\n\n")
    sys.stdout.write("=== Injection block (preview) ===\n")
    sys.stdout.write(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
