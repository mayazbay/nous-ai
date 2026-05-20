#!/usr/bin/env python3
"""mercury_seed.py — Mercury Phase 1 read-only seed emitter.

Parses three durable substrate corpora into pages/mercury/facts.jsonl per
plan v2 schema v1.0.0 (PLAN-2026-04-29-substrate-evolution-S0-S1.md):

  1. pages/skills/<skill>/SKILL.md  → one fact per `### AP-N — title` block
  2. pages/laws/*.md                 → one fact per law (id + title)
  3. pages/progress/HANDOFF-AUTO-*.md (last 10 by mtime) → one fact per session TL;DR

Read-only — no inject, no index sqlite, no decay. Those are Phase 2-4.

Usage:
  python3 tools/mercury_seed.py --dry-run     # count + sample, no write
  python3 tools/mercury_seed.py --apply       # write pages/mercury/facts.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from datetime import date

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "pages" / "skills"
LAWS_DIR = REPO / "pages" / "laws"
HANDOFFS_DIR = REPO / "pages" / "progress"
MEMORY_FILE = Path(os.environ.get(
    "MERCURY_MEMORY_OVERRIDE",
    REPO / "pages" / "progress" / "claude-memory" / "MEMORY.md",
))
OUT = Path(os.environ.get("MERCURY_FACTS_OUT", REPO / "pages" / "mercury" / "facts.jsonl"))

TODAY = date.today().isoformat()
SCHEMA_VERSION = "1.0.0"

AP_RE = re.compile(r"^### (AP-\d+)\s*[—\-]\s*(.+?)$", re.MULTILINE)
HANDOFF_RE = re.compile(r"HANDOFF-AUTO-(\d{4}-\d{2}-\d{2})-session-(\d+)", re.IGNORECASE)
TLDR_RE = re.compile(r"^##\s+TL;?DR\s*\n+(.+?)(?=\n##|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)

# Carryover extraction (Lane L s82g, 2026-04-29) — highest-precision patterns only.
# DEFERRED #1 (95% precision) + HARD-BLOCKED #1 (94%). Other buckets deferred to v2.
CARRYOVER_DEFERRED_RE = re.compile(r"\*\*[^*\n]*deferred\s+to\s+s\d+\+?[^*\n]*\*\*", re.IGNORECASE)
CARRYOVER_BLOCKED_RE = re.compile(r"\b(BLOCKED|STAYS\s+BLOCKED|red-flag\s+BLOCKED)\b[^.\n]{0,120}")
MEMORY_STANZA_SEP = "\n---\n"


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def value_hash(s: str) -> str:
    return "sha256:" + hashlib.sha256(normalize(s).encode("utf-8")).hexdigest()[:16]


def fact(*, fid: str, subject: str, value: str, source: str, tags: list[str],
         decay_rule: str = "normal", importance: float = 0.5, confidence: float = 1.0,
         freshness: str | None = None) -> dict:
    return {
        "id": fid,
        "schema_version": SCHEMA_VERSION,
        "subject": subject,
        "value": value,
        "value_hash": value_hash(value),
        "confidence": confidence,
        "freshness": freshness or TODAY,
        "importance": importance,
        "reinforcement": 0,
        "source": source,
        "conflicts_with": [],
        "load_bearing_in": [],
        "tags": tags,
        "decay_rule": decay_rule,
        "tombstone": False,
        "tombstone_reason": None,
        "tombstone_ts": None,
    }


def parse_skill_aps(facts: list[dict], counter: list[int]):
    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and not p.name.startswith("_"))
    for sd in skill_dirs:
        skill_md = sd / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        skill_name = sd.name
        for m in AP_RE.finditer(text):
            ap_id, title = m.group(1), m.group(2).strip()
            counter[0] += 1
            facts.append(fact(
                fid=f"fact-{counter[0]:05d}",
                subject=f"{skill_name}.{ap_id.lower()}",
                value=title[:300],
                source=f"[[skills/{skill_name}/skill]]",
                tags=["skill-ap", skill_name, ap_id.lower()],
                decay_rule="permanent",
                importance=0.85,
                confidence=1.0,
            ))


def parse_laws(facts: list[dict], counter: list[int]):
    """Dedupe by canonical LAW-NNN id (Lane S s82h, 2026-04-29).
    LAW-016 has 4 amendment files, LAW-013/009/004 have 3 each — keeping the
    canonical numbered law (lexicographically first matching slug) frees ~150
    tokens for now-context-header + carryover diversity.
    """
    seen_ids: set[str] = set()
    for law_md in sorted(LAWS_DIR.glob("LAW-*.md")):
        canonical_m = re.match(r"(LAW-\d+)", law_md.stem)
        canonical = canonical_m.group(1) if canonical_m else law_md.stem
        if canonical in seen_ids:
            continue
        seen_ids.add(canonical)
        text = law_md.read_text(encoding="utf-8", errors="replace")
        title_m = re.search(r'^title:\s*"?(.+?)"?$', text, re.MULTILINE)
        h1_m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = (title_m.group(1).strip() if title_m else
                 (h1_m.group(1).strip() if h1_m else law_md.stem))
        law_id = law_md.stem
        counter[0] += 1
        facts.append(fact(
            fid=f"fact-{counter[0]:05d}",
            subject=f"law.{canonical.lower()}",
            value=title[:300],
            source=f"[[{law_id}]]",
            tags=["law", "doctrine", canonical.lower()],
            decay_rule="permanent",
            importance=0.95,
            confidence=1.0,
        ))


def parse_handoffs(facts: list[dict], counter: list[int], n: int = 10):
    handoffs = sorted(
        HANDOFFS_DIR.glob("HANDOFF-AUTO-*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:n]
    for h in handoffs:
        m = HANDOFF_RE.search(h.name)
        if not m:
            continue
        ho_date, session_num = m.group(1), m.group(2)
        text = h.read_text(encoding="utf-8", errors="replace")
        tldr_m = TLDR_RE.search(text)
        if tldr_m:
            tldr = re.sub(r"\s+", " ", tldr_m.group(1).strip())[:500]
        else:
            # Fallback: first non-empty paragraph after H1 (skip frontmatter + title)
            after_h1 = re.split(r"^#\s+.+$", text, maxsplit=1, flags=re.MULTILINE)
            body = after_h1[1] if len(after_h1) > 1 else text
            paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip() and not p.strip().startswith("#")]
            if not paras:
                continue
            tldr = re.sub(r"\s+", " ", paras[0])[:500]
        counter[0] += 1
        facts.append(fact(
            fid=f"fact-{counter[0]:05d}",
            subject=f"handoff.session-{session_num}.tldr",
            value=tldr,
            source=f"[[{h.stem}]]",
            tags=["handoff", f"session-{session_num}", ho_date],
            decay_rule="normal",
            importance=0.5,
            confidence=1.0,
            freshness=ho_date,
        ))


def parse_carryover(facts: list[dict], counter: list[int], top_n_stanzas: int = 3):
    """Ingest BLOCKED + DEFERRED items from the N newest MEMORY.md stanzas.

    Lane L (s82g, 2026-04-29) — start with highest-precision patterns; decay=session
    (carryover is ephemeral). Top-N stanzas only — older stanzas already shipped to
    handoffs and don't need re-ingestion.
    """
    if not MEMORY_FILE.exists():
        return
    text = MEMORY_FILE.read_text(encoding="utf-8", errors="replace")
    if text.startswith("# Now context"):
        # Mercury MEMORY is generated from facts.jsonl. Reading generated
        # carryover back into facts creates a self-amplifying loop.
        return
    stanzas = text.split(MEMORY_STANZA_SEP)[:top_n_stanzas]
    seen: set[tuple[str, str]] = set()
    for stanza_idx, stanza in enumerate(stanzas):
        # Importance: BLOCKED at law tier (0.95) — active prod risk; DEFERRED at
        # skill-AP tier (0.85) — must surface in next-session top-K so debt visible.
        for kind, pattern, importance in (
            ("blocked", CARRYOVER_BLOCKED_RE, 0.95),
            ("deferred", CARRYOVER_DEFERRED_RE, 0.85),
        ):
            for m in pattern.finditer(stanza):
                # Carryover values are pointers, not paragraphs — keep terse so a
                # handful fit the budget without bloating Mercury's tail.
                snippet = re.sub(r"\s+", " ", m.group(0)).strip("* ").strip()[:120]
                if not snippet:
                    continue
                key = (kind, value_hash(snippet))
                if key in seen:
                    continue
                seen.add(key)
                counter[0] += 1
                slug = re.sub(r"[^\w]+", "-", snippet[:40].lower()).strip("-")
                facts.append(fact(
                    fid=f"fact-{counter[0]:05d}",
                    subject=f"carryover.stanza-{stanza_idx}.{kind}.{slug}",
                    value=snippet,
                    source="[[claude-memory/MEMORY]]",
                    tags=["carryover", kind, "ephemeral"],
                    decay_rule="session",
                    importance=importance,
                    confidence=0.9,
                ))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    facts: list[dict] = []
    counter = [0]
    parse_skill_aps(facts, counter)
    skill_count = counter[0]
    parse_laws(facts, counter)
    law_count = counter[0] - skill_count
    parse_handoffs(facts, counter)
    handoff_count = counter[0] - skill_count - law_count
    parse_carryover(facts, counter)
    carryover_count = counter[0] - skill_count - law_count - handoff_count

    print(f"skill APs:     {skill_count}")
    print(f"laws:          {law_count}")
    print(f"handoff TLDRs: {handoff_count}")
    print(f"carryover:     {carryover_count}")
    print(f"TOTAL facts:   {len(facts)}")

    if args.dry_run:
        print("\n--- sample (3 of each kind) ---")
        for kind, prefix in (("skill-ap", "skill-ap"), ("law", "law"), ("handoff", "handoff")):
            samples = [f for f in facts if prefix in f["tags"]][:3]
            for s in samples:
                print(f"  [{kind}] {s['id']} | {s['subject']} | {s['value'][:80]}")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for fact_obj in facts:
            f.write(json.dumps(fact_obj, ensure_ascii=False) + "\n")
    size_kb = OUT.stat().st_size / 1024
    print(f"\n✅ wrote {len(facts)} facts → {OUT.relative_to(REPO)} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
