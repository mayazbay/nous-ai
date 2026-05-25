#!/usr/bin/env python3
"""
ingest_openbrain_to_skills.py — link orphan OpenBrain captures to nearest skills.

Closes the OpenBrain learning loop. OpenBrain captures (created via
mcp__claude_ai_Open_Brain__capture_thought) project to
pages/inbox/openbrain/YYYY-MM-DD/openbrain-<uuid>.md but historically had no
backlinks. gbrain skips orphaned pages (orphan rule per library-grade-audit
AP-5), so captures didn't compound into the substrate.

This script finds every orphan, runs a gbrain semantic search for the body,
picks the highest-scoring SKILL.md page(s) above gates, and appends a single
evidence-trail entry to each target skill plus a last_updated bump.

Gates (revised after eng-review):
  - top-1 score >= 0.75 (absolute floor)
  - top-1 - top-2 margin >= 0.15 for single-skill link, OR
  - multi-skill link if 2-3 results within 0.05 of top-1 (dense captures)
  - else deferred (idempotent next run will retry)

Per-file safety rails:
  - frontmatter YAML round-trip parse before AND after the edit
  - exactly +1 line added (evidence) plus last_updated swap (same line count)
  - evidence-line appears exactly once in the new text
  - last_updated equals today
  - bounded character delta to catch regex misfires

Usage:
  python3 tools/ingest_openbrain_to_skills.py [--dry-run] [--limit N]

Exit codes:
  0 success, 1 errors (any validation failure short-circuited that file), 2 no orphans.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
ORPHAN_GLOB = "pages/inbox/openbrain/*/openbrain-*.md"
SKILL_GLOB = "pages/skills/*/SKILL.md"
GBRAIN_SSH = "root@65.108.215.200"
GBRAIN_BIN = "/opt/nous-agaas/gbrain/bin/gbrain"

# Keyword-match gates (deterministic — gbrain FTS gave high scores to captures
# themselves, not to the parent SKILL.md pages; using local keyword frequency
# against the skill registry instead).
TOP1_FLOOR_HITS = 2  # top-1 skill must have >= this many keyword hits
MARGIN_HITS = 1       # top1 - top2 >= this for single-skill link
MULTI_SKILL_DELTA = 0  # multi-link if top results are tied exactly (delta=0)
# Generic words that match too many skills — exclude from skill keyword set
STOPWORDS = {
    "skill", "skills", "the", "and", "for", "with", "from", "ops", "operator",
    "audit", "agent", "agents", "ai", "core", "live", "test", "mode", "loop",
    "open", "brain", "code", "card", "data", "files", "node", "page", "pages",
    "list", "info", "name", "value", "build", "level", "type", "step", "steps",
    "ru", "kz", "en", "v1", "v2", "v3",
}


def parse_frontmatter(text: str):
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, None
    try:
        import yaml
        return yaml.safe_load(parts[1]) or {}, parts[2]
    except Exception:
        return None, None


def yaml_safe(text: str) -> bool:
    fm, _ = parse_frontmatter(text)
    return fm is not None


def load_orphan(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    fm, body = parse_frontmatter(text)
    if fm is None:
        return None
    uuid = path.stem.replace("openbrain-", "")
    return uuid, fm, body.strip()


def already_linked(uuid: str) -> bool:
    pattern = f"[[openbrain-{uuid}]]"
    for skill_md in VAULT.glob(SKILL_GLOB):
        try:
            if pattern in skill_md.read_text(encoding="utf-8"):
                return True
        except Exception:
            continue
    return False


def list_skills():
    """Return [(skill_path, skill_name, keyword_set), ...] for every SKILL.md."""
    out = []
    for skill_md in sorted(VAULT.glob(SKILL_GLOB)):
        name = skill_md.parent.name
        if name.startswith("_") or name == "extracted":
            continue
        keywords = set()
        # Skill name itself + name-split
        keywords.add(name.lower())
        for part in name.lower().replace("_", "-").split("-"):
            if len(part) >= 4 and part not in STOPWORDS:
                keywords.add(part)
        # Also pull a couple of distinctive tokens from frontmatter title/description
        try:
            text = skill_md.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            if len(parts) >= 3:
                import yaml
                fm = yaml.safe_load(parts[1]) or {}
                # Pull capitalized words / hyphenated identifiers from title
                title = str(fm.get("title", ""))
                for tok in re.findall(r"\b([A-Z][A-Za-z0-9]+|[a-z]+-[a-z0-9-]+)\b", title):
                    t = tok.lower()
                    if len(t) >= 4 and t not in STOPWORDS:
                        keywords.add(t)
        except Exception:
            pass
        out.append((skill_md, name, keywords))
    return out


def keyword_match(orphan_text: str, skill_registry):
    """Return [(skill_path, skill_name, hits), ...] sorted by hits desc."""
    lower = orphan_text.lower()
    # Tokenize once for word-boundary protection
    tokens = set(re.findall(r"[a-z][a-z0-9]+(?:-[a-z0-9]+)*", lower))
    out = []
    for skill_path, skill_name, keywords in skill_registry:
        hits = 0
        for kw in keywords:
            if " " in kw or "-" in kw:
                # multi-word/hyphen tokens: match substring
                if kw in lower:
                    hits += 2  # full kebab-case hit is high signal
            else:
                if kw in tokens:
                    hits += 1
        if hits > 0:
            out.append((skill_path, skill_name, hits))
    out.sort(key=lambda x: -x[2])
    return out


def decide_targets(ranked):
    """Apply 3-gate rule on keyword-hit-ranked skill list."""
    if not ranked:
        return "deferred:no_keyword_matches", []
    top1_hits = ranked[0][2]
    if top1_hits < TOP1_FLOOR_HITS:
        return f"deferred:top1_hits_below_floor_{top1_hits}", []
    # multi-skill: all results tied at top
    multi = [r for r in ranked if (top1_hits - r[2]) <= MULTI_SKILL_DELTA]
    if len(multi) >= 2:
        multi = multi[:3]
        return f"multi_linked:{len(multi)}", multi
    if len(ranked) == 1 or (ranked[0][2] - ranked[1][2]) >= MARGIN_HITS:
        return "linked:single", [ranked[0]]
    return f"deferred:margin_hits_below_{MARGIN_HITS}", []


def detect_heading(text: str):
    for h in ("## Evidence trail", "## Timeline"):
        if re.search(rf"^{re.escape(h)}\s*$", text, re.MULTILINE):
            return h
    return None


def clean_body(body: str) -> str:
    """Strip markdown noise without truncating."""
    text = re.sub(r"^#+\s*", "", body, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_openbrain_chrome(body: str) -> str:
    """Remove the boilerplate OpenBrain capture preamble + Projection metadata
    section so keyword matching focuses on the actual SUBJECT content, not
    the OpenBrain housekeeping prefix that's identical across every capture."""
    text = body
    # Drop the standard "# OpenBrain Capture - YYYY-MM-DD" header line
    text = re.sub(r"^#\s*OpenBrain Capture[^\n]*\n", "", text, count=1)
    # Drop the "## Projection" section and everything after it (UUID/hash/timestamps)
    text = re.split(r"\n##\s+Projection\s*\n", text, maxsplit=1)[0]
    # Drop standalone "OpenBrain MCP" trailer mentions
    text = re.sub(r"OpenBrain MCP", "", text, flags=re.IGNORECASE)
    return text.strip()


def build_summary(body: str, max_chars: int = 80) -> str:
    """Short display summary for the evidence-trail line."""
    text = clean_body(body)
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def build_search_query(body: str, title: str = "", max_chars: int = 350) -> str:
    """Longer query for semantic search — uses title + body, no truncation mid-word."""
    base = (title.strip() + " " + clean_body(body)).strip()
    if len(base) <= max_chars:
        return base
    # Truncate at last whitespace before max_chars
    cut = base[:max_chars].rsplit(" ", 1)[0]
    return cut.strip()


def insert_evidence_line(text: str, heading: str, line: str):
    pattern = re.compile(rf"^({re.escape(heading)}\s*\n)", re.MULTILINE)
    if not pattern.search(text):
        return None
    return pattern.sub(lambda m: m.group(1) + line + "\n", text, count=1)


def bump_last_updated(text: str, today: str) -> str:
    return re.sub(
        r"^(last_updated:\s*)[\d\-]+\s*$",
        lambda m: f"{m.group(1)}{today}",
        text,
        count=1,
        flags=re.MULTILINE,
    )


def mark_deferred(orphan_path: Path, reason: str, today: str, dry_run: bool):
    """Stamp `status: deferred` + `deferred_reason` + `deferred_at` into an
    OpenBrain capture's frontmatter. Idempotent — skips if status is already
    `deferred`. Closes the openbrain-projection AP-6 SLO loop: a capture that
    the auto-linker decides not to link must be explicitly marked deferred in
    its own file so library-grade-audit Gate 7.1 sees a closed substrate
    rather than a doctrine-orphan."""
    try:
        text = orphan_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"defer_read_fail:{e}"
    fm, _body = parse_frontmatter(text)
    if fm is None:
        return False, "defer_yaml_parse_fail_before"
    if str(fm.get("status", "")).strip() == "deferred":
        return True, "already_deferred"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False, "no_frontmatter"
    fm_text = parts[1]
    if re.search(r"^status:\s*\S+\s*$", fm_text, re.MULTILINE):
        new_fm = re.sub(r"^status:\s*\S+\s*$", "status: deferred",
                        fm_text, count=1, flags=re.MULTILINE)
    else:
        new_fm = fm_text.rstrip("\n") + "\nstatus: deferred\n"
    if not re.search(r"^deferred_reason:", new_fm, re.MULTILINE):
        new_fm = new_fm.rstrip("\n") + f"\ndeferred_reason: {reason}\n"
    if not re.search(r"^deferred_at:", new_fm, re.MULTILINE):
        new_fm = new_fm.rstrip("\n") + f"\ndeferred_at: {today}\n"
    new_text = "---" + new_fm + "---" + parts[2]
    new_fm_parsed, _ = parse_frontmatter(new_text)
    if new_fm_parsed is None:
        return False, "defer_yaml_parse_fail_after"
    if new_fm_parsed.get("status") != "deferred":
        return False, "defer_status_not_set"
    char_delta = len(new_text) - len(text)
    if char_delta < 0 or char_delta > 200:
        return False, f"defer_char_delta_unbounded:{char_delta}"
    if not dry_run:
        orphan_path.write_text(new_text, encoding="utf-8")
    return True, "marked"


def validate_edit(old: str, new: str, evidence_line: str, today: str):
    if old.count(evidence_line) != 0:
        return f"evidence_line_already_present"
    if new.count(evidence_line) != 1:
        return f"evidence_line_count_unexpected={new.count(evidence_line)}"
    m = re.search(r"^last_updated:\s*([\d\-]+)\s*$", new, re.MULTILINE)
    if not m or m.group(1) != today:
        return f"last_updated_not_today_got={m.group(1) if m else 'none'}"
    if not yaml_safe(new):
        return "yaml_parse_fail"
    line_delta = len(new.splitlines()) - len(old.splitlines())
    if line_delta != 1:
        return f"line_delta_not_1_got={line_delta}"
    char_delta = len(new) - len(old)
    expected = len(evidence_line) + 1
    if char_delta < expected - 5 or char_delta > expected + 30:
        return f"char_delta_unbounded={char_delta}_expected_around={expected}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--json",
        action="store_true",
        help="Accepted for automation compatibility; output is always JSON.",
    )
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    orphans = sorted(VAULT.glob(ORPHAN_GLOB))
    if not orphans:
        print(json.dumps({"status": "no_orphans"}))
        sys.exit(2)
    if args.limit:
        orphans = orphans[: args.limit]
    skill_registry = list_skills()

    today = datetime.now(timezone(timedelta(hours=5))).strftime("%Y-%m-%d")
    summary = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "orphans_scanned": len(orphans),
        "today_kzt": today,
        "linked": 0,
        "multi_linked": 0,
        "deferred": 0,
        "deferred_marked": 0,
        "deferred_already_marked": 0,
        "deferred_mark_failed": 0,
        "skipped_already_linked": 0,
        "errors": 0,
        "yaml_failures": [],
        "validation_failures": [],
        "files_changed": [],
        "processed": [],
    }

    for orphan in orphans:
        rel = str(orphan.relative_to(VAULT))
        parsed = load_orphan(orphan)
        if parsed is None:
            summary["processed"].append({"orphan": rel, "decision": "error:parse_failed"})
            summary["errors"] += 1
            continue
        uuid, fm, body = parsed
        if already_linked(uuid):
            summary["processed"].append({"orphan": rel, "decision": "skipped:already_linked"})
            summary["skipped_already_linked"] += 1
            continue
        body_summary = build_summary(body)
        if not body_summary:
            ok, status = mark_deferred(orphan, "empty_body", today, args.dry_run)
            summary["processed"].append({
                "orphan": rel,
                "decision": "deferred:empty_body",
                "defer_mark": status,
            })
            summary["deferred"] += 1
            if ok and status == "marked":
                summary["deferred_marked"] += 1
            elif ok and status == "already_deferred":
                summary["deferred_already_marked"] += 1
            else:
                summary["deferred_mark_failed"] += 1
            continue
        # Strip OpenBrain chrome so keyword matching looks at the actual subject,
        # not the boilerplate "OpenBrain Capture" header that's identical everywhere.
        subject_body = strip_openbrain_chrome(body)
        match_text = (str(fm.get("title", "")) + " " + clean_body(subject_body))
        ranked = keyword_match(match_text, skill_registry)
        decision, targets = decide_targets(ranked)
        record = {
            "orphan": rel,
            "uuid": uuid,
            "summary": body_summary,
            "decision": decision,
            "candidates": [(name, hits) for (_, name, hits) in ranked[:5]],
            "targets": [name for (_, name, _) in targets],
            "edits": [],
        }
        summary["processed"].append(record)
        if not targets:
            reason = decision.split(":", 1)[1] if ":" in decision else decision
            ok, status = mark_deferred(orphan, reason, today, args.dry_run)
            record["defer_mark"] = status
            summary["deferred"] += 1
            if ok and status == "marked":
                summary["deferred_marked"] += 1
            elif ok and status == "already_deferred":
                summary["deferred_already_marked"] += 1
            else:
                summary["deferred_mark_failed"] += 1
            continue
        if len(targets) > 1:
            summary["multi_linked"] += 1
        else:
            summary["linked"] += 1

        evidence_line = f"- **{today} openbrain** | {body_summary} [[openbrain-{uuid}]]"
        for skill_path, skill_name, _score in targets:
            old_text = skill_path.read_text(encoding="utf-8")
            heading = detect_heading(old_text)
            if heading is None:
                record["edits"].append({"skill": skill_name, "status": "skip:no_heading"})
                continue
            new_text = insert_evidence_line(old_text, heading, evidence_line)
            if new_text is None:
                record["edits"].append({"skill": skill_name, "status": "skip:insert_failed"})
                continue
            new_text = bump_last_updated(new_text, today)
            err = validate_edit(old_text, new_text, evidence_line, today)
            if err is not None:
                record["edits"].append({"skill": skill_name, "status": f"reject:{err}"})
                if "yaml" in err:
                    summary["yaml_failures"].append(str(skill_path))
                else:
                    summary["validation_failures"].append({"skill": skill_name, "error": err})
                summary["errors"] += 1
                continue
            if not args.dry_run:
                skill_path.write_text(new_text, encoding="utf-8")
            record["edits"].append({"skill": skill_name, "status": "ok", "heading": heading})
            summary["files_changed"].append(str(skill_path))

    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
