#!/usr/bin/env python3
"""Fix the 80 frontmatter issues surfaced by gbrain v0.22.16 stricter lint.

Three classes:
  MISSING_OPEN (47): files don't start with --- on line 1
  YAML_PARSE   (17): wikilink-array values like `related: [[a]], [[b]]` confuse YAML
  NESTED_QUOTES (16): nested double quotes need outer-single

Usage:
  python3 tools/frontmatter_fixer_session82.py [--apply] [--code <CODE>]
  Default: dry-run. --apply writes changes.
"""
import os, re, sys, json
from pathlib import Path

VAULT = Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")
ISSUES_FILE = "/tmp/fm_full.json"
APPLY = "--apply" in sys.argv

def load_issues():
    with open(ISSUES_FILE) as f:
        d = json.load(f)
    by_code = {}
    VPS = "/root/nous-agaas/wiki/"
    for r in d.get("results", []):
        for e in r.get("errors", []):
            local = r["path"].replace(VPS, str(VAULT) + "/")
            by_code.setdefault(e["code"], []).append((local, e.get("line", 1)))
    return by_code

def fix_missing_open(path):
    """Prepend minimal frontmatter for files without ---."""
    p = Path(path)
    if not p.exists():
        return False, "file missing"
    content = p.read_text(encoding="utf-8")
    if content.startswith("---\n") or content.startswith("---\r\n"):
        return False, "already has --- (lint may be stale)"
    stem = p.stem
    # Determine type from path
    rel = str(p.relative_to(VAULT))
    if rel.startswith("raw/transcripts"):
        page_type = "raw-transcript"
    elif rel.startswith("raw/meetings"):
        page_type = "raw-meeting"
    elif rel.startswith("raw/satory"):
        page_type = "raw-source"
    elif rel.startswith("raw/"):
        page_type = "raw-source"
    elif rel.startswith("pages/concepts/forrestchang"):
        page_type = "source"
    else:
        page_type = "note"
    # Build readable title from stem
    title = stem.replace("_", " ").replace("-", " ").strip()
    fm = f"""---
type: {page_type}
id: {stem}
title: "{title}"
date: 2026-04-30
last_updated: 2026-04-30
status: ingested
---

"""
    new_content = fm + content
    if APPLY:
        p.write_text(new_content, encoding="utf-8")
    return True, f"prepended frontmatter (type={page_type})"

def fix_yaml_parse(path):
    """Fix `related: [[a]], [[b]]` → `related: ["[[a]]", "[[b]]"]`."""
    p = Path(path)
    if not p.exists():
        return False, "file missing"
    content = p.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "no frontmatter"
    end = content.find("\n---", 4)
    if end < 0:
        return False, "no frontmatter close"
    fm = content[:end]
    rest = content[end:]

    # Pattern: KEY: [[xxx]], [[yyy]], [[zzz]]
    # Match keys: related, aliases, absorbs_lessons, absorbs_laws, supersedes, superseded_by
    keys = r"related|aliases|absorbs_lessons|absorbs_laws|supersedes|superseded_by|see_also"
    pattern = re.compile(
        rf"^(\s*(?:{keys}):\s*)(\[\[[^\]]+\]\](?:\s*,\s*\[\[[^\]]+\]\])*)\s*$",
        re.MULTILINE
    )
    def repl(m):
        prefix = m.group(1)
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", m.group(2))
        quoted = ", ".join(f'"[[{w}]]"' for w in wikilinks)
        return f"{prefix}[{quoted}]"
    new_fm = pattern.sub(repl, fm)
    if new_fm == fm:
        return False, "no wikilink-array pattern matched"
    if APPLY:
        p.write_text(new_fm + rest, encoding="utf-8")
    return True, "fixed wikilink array"

def fix_nested_quotes(path):
    """Fix `key: ["X", "Y", "Z"]` → `key: [X, Y, Z]` (drop inner quotes on simple IDs).
    gbrain v0.22 NESTED_QUOTES: any line with 3+ unescaped double quotes.
    Multi-element flow-sequence arrays of quoted strings trigger this."""
    p = Path(path)
    if not p.exists():
        return False, "file missing"
    content = p.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "no frontmatter"
    end = content.find("\n---", 4)
    if end < 0:
        return False, "no frontmatter close"
    fm = content[:end]
    rest = content[end:]
    fixed_count = 0
    new_lines = []
    for line in fm.split("\n"):
        # Pattern: key: ["X", "Y", "Z"] → key: [X, Y, Z]  (when X/Y/Z are simple IDs)
        m = re.match(r'^(\s*\w+:\s*\[)([^\]]+)(\]\s*)$', line)
        if m:
            inner = m.group(2)
            # Count unescaped double quotes
            dq_count = inner.count('"')
            if dq_count >= 4:  # at least 2 quoted strings
                # Extract quoted IDs and unquote them
                ids = re.findall(r'"([^"]+)"', inner)
                if ids and all(re.match(r'^[A-Za-z0-9_\-./]+$', i) for i in ids):
                    new_line = f"{m.group(1)}{', '.join(ids)}{m.group(3)}"
                    new_lines.append(new_line)
                    fixed_count += 1
                    continue
        # Also: key: "value with "inner" quotes" pattern (separate, less common)
        m2 = re.match(r'^(\s*\w+:\s*)"(.*)"(\s*)$', line)
        if m2 and '"' in m2.group(2) and "'" not in m2.group(2):
            new_line = f"{m2.group(1)}'{m2.group(2)}'{m2.group(3)}"
            new_lines.append(new_line)
            fixed_count += 1
            continue
        new_lines.append(line)
    if fixed_count == 0:
        return False, "no nested-quote pattern matched"
    if APPLY:
        p.write_text("\n".join(new_lines) + rest, encoding="utf-8")
    return True, f"fixed {fixed_count} nested-quote lines"

def main():
    issues = load_issues()
    summary = {"MISSING_OPEN": [0,0], "YAML_PARSE": [0,0], "NESTED_QUOTES": [0,0]}
    for code, files in issues.items():
        if code == "MISSING_OPEN": fn = fix_missing_open
        elif code == "YAML_PARSE": fn = fix_yaml_parse
        elif code == "NESTED_QUOTES": fn = fix_nested_quotes
        else:
            print(f"unhandled code: {code}")
            continue
        seen_paths = set()
        for path, line in files:
            if path in seen_paths: continue
            seen_paths.add(path)
            ok, msg = fn(path)
            summary[code][0 if ok else 1] += 1
            if not ok or not APPLY:
                print(f"  [{code}] {'✓' if ok else '✗'} {os.path.basename(path)}: {msg}")
    print("\n=== SUMMARY ===")
    for code, (ok, fail) in summary.items():
        print(f"  {code}: {ok} fixed / {fail} skipped")
    print(f"\n{'APPLIED' if APPLY else 'DRY-RUN — re-run with --apply to write'}")

if __name__ == "__main__":
    main()
