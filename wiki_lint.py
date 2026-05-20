#!/usr/bin/env python3
"""
Wiki health linter — runs Karpathy LLM Wiki monthly health check.

Output: wiki/pages/audits/lint-YYYY-MM-DD.md with severity flags 🔴/🟡/🔵.
Checks: contradictions, stale claims, orphan pages, missing source attribution,
missing cross-references, claims without provenance.

Designed to run via cron 0 9 1 * * (1st of each month, 9am Asia/Almaty).
"""
import os
import sys
import json
import datetime
from pathlib import Path

# 2026-04-09: decoupled from /root/nous-agaas/config.py — that module imports
# langchain_openai which isn't installed and isn't needed for linting (text-only).
# Read ANTHROPIC_API_KEY directly from env so the linter works on any host
# (Mac, VPS, fresh container) regardless of factory dependency state.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Resolve WIKI root portably: use $WIKI_ROOT if set, else infer from this file's
# location (tools/wiki_lint.py → parent of tools/ is the wiki root). This makes
# the linter work on Mac at /Users/madia/Documents/Projects/Nous\ AGaaS/Nous/
# AND on VPS at /root/nous-agaas/wiki/ without code changes.
_env_root = os.environ.get("WIKI_ROOT")
if _env_root:
    WIKI = Path(_env_root)
else:
    _here = Path(__file__).resolve()
    # tools/wiki_lint.py → wiki root is parent of tools/
    WIKI = _here.parent.parent
PAGES = WIKI / "pages"
AUDITS = PAGES / "audits"

def collect_pages():
    """Walk the wiki tree and return list of (relpath, content).

    Scans pages/, laws/, and top-level .md files. Skips raw/, .git/, and large files.
    """
    out = []
    scan_dirs = [WIKI / "pages", WIKI / "laws"]
    # Top-level .md files (CLAUDE, index, log)
    for f in WIKI.glob("*.md"):
        try:
            out.append((str(f.relative_to(WIKI)), f.read_text()[:6000]))
        except Exception:
            pass
    for d in scan_dirs:
        if not d.exists():
            continue
        for root, dirs, files in os.walk(d):
            for f in files:
                if not f.endswith(".md"):
                    continue
                full = Path(root) / f
                rel = full.relative_to(WIKI)
                try:
                    out.append((str(rel), full.read_text()[:6000]))
                except Exception:
                    pass
    return out


def find_orphans(pages):
    """Find pages with no incoming wikilinks."""
    all_links = set()
    for _, content in pages:
        # Extract [[wikilink]] targets
        i = 0
        while True:
            j = content.find("[[", i)
            if j < 0:
                break
            k = content.find("]]", j)
            if k < 0:
                break
            target = content[j+2:k].split("|")[0].split("#")[0].strip()
            all_links.add(target)
            i = k + 2

    orphans = []
    for rel, _ in pages:
        stem = Path(rel).stem
        if stem not in all_links and stem != "index" and stem != "log" and stem != "CLAUDE":
            orphans.append(rel)
    return orphans


def find_no_provenance(pages):
    """Find pages without YAML frontmatter or source field."""
    no_meta = []
    for rel, content in pages:
        if not content.strip().startswith("---"):
            no_meta.append(rel)
    return no_meta


def find_broken_wikilinks(pages):
    """Find [[wikilinks]] that point to non-existent files.

    Skips wikilinks that are inside backtick code blocks or inline code,
    so lint reports don'''t flag their own contents.
    """
    from pathlib import Path
    valid_stems = {Path(rel).stem for rel, _ in pages}
    valid_stems.update({"CLAUDE", "index", "log"})
    # Also accept stems by id frontmatter
    import re as _re
    id_aliases = set()
    for rel, content in pages:
        m = _re.search(r"^id:\s*(\S+)", content, _re.MULTILINE)
        if m:
            id_aliases.add(m.group(1).strip().strip('"').strip("'"))
    valid_stems |= id_aliases

    broken = []
    for rel, content in pages:
        # Strip code fences and inline code so we don't false-positive on lint reports
        stripped = _re.sub(r"```.*?```", "", content, flags=_re.DOTALL)
        stripped = _re.sub(r"`[^`]*`", "", stripped)
        i = 0
        while True:
            j = stripped.find("[[", i)
            if j < 0:
                break
            k = stripped.find("]]", j)
            if k < 0:
                break
            target = stripped[j+2:k].split("|")[0].split("#")[0].strip()
            if target and target not in valid_stems:
                broken.append((rel, target))
            i = k + 2
    return broken


def call_claude(prompt):
    """Run a single prompt against Claude. Returns text or error."""
    try:
        import anthropic
    except ImportError:
        return "[ERROR] anthropic SDK not installed"
    if not ANTHROPIC_API_KEY:
        return "[ERROR] ANTHROPIC_API_KEY not set"
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def find_raw_top_level_violations():
    """LESSON-059: files at top level of raw/ that aren\'t in the whitelist."""
    import os as _os
    # Use WIKI root resolved at module load — works on Mac and VPS.
    raw = str(WIKI / "raw")
    whitelist = {"README.md"}
    out = []
    if _os.path.isdir(raw):
        for entry in _os.listdir(raw):
            full = _os.path.join(raw, entry)
            if _os.path.isfile(full) and entry not in whitelist and not entry.startswith("."):
                out.append(entry)
    return out


def run_lint():
    today = datetime.date.today().isoformat()
    pages = collect_pages()
    orphans = find_orphans(pages)
    no_meta = find_no_provenance(pages)
    broken_links = find_broken_wikilinks(pages)
    raw_top_level_violations = find_raw_top_level_violations()

    # Build digest — always include critical files first so lint can see definitions
    PRIORITY_FILES = [
        "pages/concepts/glossary.md",
        "CLAUDE.md",
        "index.md",
    ]
    pages_dict = dict(pages)
    digest_lines = []
    seen = set()
    for pf in PRIORITY_FILES:
        if pf in pages_dict:
            content = pages_dict[pf]
            digest_lines.append(f"### {pf} (PRIORITY)\n{content[:5000]}\n")
            seen.add(pf)
    for rel, content in pages:
        if rel in seen:
            continue
        first = content.split("\n", 50)
        head = "\n".join(first[:6])[:400]
        digest_lines.append(f"### {rel}\n{head}\n")
        if len(digest_lines) >= 85:
            break
    digest = "\n".join(digest_lines)

    prompt = f"""You are auditing the Nous AGaaS wiki for health issues.

Below is a digest of {len(pages)} pages. Find:
1. Contradictions between pages (e.g. one page says X, another says not-X)
2. Stale claims (anything that mentions "current" or specific dates that look outdated)
3. Concepts mentioned but never defined (e.g. acronym used in 5 pages with no glossary entry)
4. Claims without source attribution (assertions with no [[link]] or "Source:" reference)
5. Missing cross-references (entities clearly related but not [[linked]])

Output as Markdown with these EXACT sections:

## 🔴 Errors (must fix this month)
- ...

## 🟡 Warnings (should fix soon)
- ...

## 🔵 Info (nice to have)
- ...

Cite the file path for every finding (e.g. `pages/lessons/individual/LESSON-XXX.md`).
Be specific. Cite the actual contradicting strings.
Do NOT make things up — if you can't find issues, say so.

WIKI DIGEST:
{digest}
"""

    try:
        llm_output = call_claude(prompt)
    except Exception as exc:
        msg = str(exc)
        if "credit balance is too low" in msg or "credit_balance" in msg:
            llm_output = "_LLM analysis SKIPPED — Anthropic credits exhausted. Top up to enable._"
        else:
            llm_output = f"_LLM analysis FAILED: {msg[:200]}_"

    # Build the lint report
    report = f"""---
id: LINT-{today}
title: Wiki health check {today}
date: {today}
type: lint
related: [AUDIT-011, AUDIT-016]
---

# Wiki Lint Report — {today}

Generated by `tools/wiki_lint.py` (runs 1st of each month via cron).

**Stats:**
- Total pages: {len(pages)}
- Orphans (no incoming wikilinks): {len(orphans)}
- Pages without YAML frontmatter: {len(no_meta)}\n- Broken wikilinks: {len(broken_links)}\n- raw/ top-level violations (LESSON-059): {len(raw_top_level_violations)}

## Mechanical findings

### Orphans
{chr(10).join(f"- `{p}`" for p in orphans[:30]) if orphans else "_None_"}

### Pages without YAML frontmatter
{chr(10).join(f"- `{p}`" for p in no_meta[:30]) if no_meta else "_None_"}

### Broken wikilinks (target page does not exist)
{chr(10).join(f"- in `{rel}`: `[[{tgt}]]`" for rel, tgt in broken_links[:30]) if broken_links else "_None_"}

### raw/ top-level violations (LESSON-059 — should be auto-routed by tools/raw_hygiene.py)
{chr(10).join(f"- `raw/{f}`" for f in raw_top_level_violations) if raw_top_level_violations else "_None_ (clean)"}

## LLM findings

{llm_output}

---
_End of report. Next run: 1st of next month._
"""
    out_path = AUDITS / f"lint-{today}.md"
    out_path.write_text(report)
    print(f"Wrote {out_path}")
    print(f"Stats: {len(pages)} pages, {len(orphans)} orphans, {len(no_meta)} no-meta, {len(broken_links)} broken links")
    return 0


if __name__ == "__main__":
    sys.exit(run_lint())
