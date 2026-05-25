#!/usr/bin/env python3
"""
validate_supersession.py — AP-61 Phase-0 deliverable.

Validates the supersession.v1.json contract on a wiki page or all pages:
- All 3 required fields present when ANY are present (rejects partial state)
- `superseded_by:` wikilinks resolve to existing pages
- Transitive chain resolution: no cycles, max depth 2
- `superseded_at:` is valid ISO date
- `superseded_reason:` ≤140 chars, no shell-injectable chars

Usage:
    tools/validate_supersession.py                         # scan all pages
    tools/validate_supersession.py --staged                # validate staged files only (pre-commit mode)
    tools/validate_supersession.py pages/specs/foo.md      # validate one file
    tools/validate_supersession.py --json                  # machine-readable output

Exits 0 on all-pass, non-zero on any violation.

Designed to be wired into the existing pre-commit hook
(tools/pre-commit-hook-tan-pattern.sh) BEFORE the Tier-A1 library scanners
but AFTER MD5 parity check, per autoplan v1 Codex Eng F3 ordering rule.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date as date_cls, datetime
from pathlib import Path

VAULT = Path(os.environ.get("VAULT", Path(__file__).resolve().parent.parent))
REASON_MAX = 140
MAX_CHAIN_DEPTH = 2
SHELL_INJECT_CHARS = re.compile(r"[`$\\\n\r]")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
REQUIRED_FIELDS = ("superseded_by", "superseded_at", "superseded_reason")


def parse_frontmatter(text: str) -> dict[str, list[str] | str] | None:
    """Minimal YAML frontmatter parser — handles the subset AP-61 needs."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm: dict[str, list[str] | str] = {}
    cur_key: str | None = None
    cur_list: list[str] = []
    cur_scalar: list[str] = []
    is_list = False

    def flush():
        nonlocal cur_key, cur_list, cur_scalar, is_list
        if cur_key is None:
            return
        if is_list:
            fm[cur_key] = cur_list
        else:
            v = "\n".join(cur_scalar).strip()
            fm[cur_key] = v
        cur_key = None
        cur_list = []
        cur_scalar = []
        is_list = False

    for line in m.group(1).splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*:", line):
            flush()
            cur_key, _, val = line.partition(":")
            cur_key = cur_key.strip()
            val = val.strip()
            if val:
                cur_scalar = [val]
        elif line.lstrip().startswith("- ") and cur_key is not None:
            is_list = True
            item = line.lstrip()[2:].strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            cur_list.append(item)
        elif cur_key is not None:
            cur_scalar.append(line.strip())
    flush()
    return fm


def resolve_wikilink(target: str) -> Path | None:
    """Try to resolve a wikilink slug to an actual file in the vault."""
    target = target.strip().removeprefix("[[").removesuffix("]]")
    candidates = [
        VAULT / "pages" / f"{target}.md",
        VAULT / "pages" / target / "SKILL.md",
        VAULT / "pages" / "skills" / target / "SKILL.md",
        VAULT / "pages" / "skills" / target.removeprefix("skills/").removesuffix("/skill") / "SKILL.md" if target.startswith("skills/") else None,
    ]
    for c in candidates:
        if c and c.is_file():
            return c
    return None


def validate_one(path: Path, results: list[dict], visited_chain: set[str] | None = None, depth: int = 0) -> None:
    """Validate a single page's supersession metadata. Recurses transitively for chain check."""
    if visited_chain is None:
        visited_chain = set()
    rel = str(path.relative_to(VAULT))
    if rel in visited_chain:
        results.append({"path": rel, "level": "error", "rule": "chain_cycle",
                        "msg": f"cycle detected at depth {depth}: {' → '.join(list(visited_chain) + [rel])}"})
        return
    if depth > MAX_CHAIN_DEPTH:
        results.append({"path": rel, "level": "error", "rule": "chain_too_deep",
                        "msg": f"chain depth > {MAX_CHAIN_DEPTH} (current: {depth})"})
        return

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        results.append({"path": rel, "level": "error", "rule": "read", "msg": f"cannot read: {e}"})
        return

    fm = parse_frontmatter(text)
    if fm is None:
        return  # No frontmatter — not a supersession candidate, skip
    present = [f for f in REQUIRED_FIELDS if f in fm]
    if not present:
        return  # Not a superseded page, skip silently
    if 0 < len(present) < 3:
        results.append({"path": rel, "level": "error", "rule": "partial_state",
                        "msg": f"partial supersession: present={present}, missing={[f for f in REQUIRED_FIELDS if f not in fm]}"})
        return

    # All 3 present — validate each
    sb = fm["superseded_by"]
    if not isinstance(sb, list) or len(sb) == 0:
        results.append({"path": rel, "level": "error", "rule": "superseded_by_shape",
                        "msg": f"superseded_by must be non-empty list of wikilinks; got {type(sb).__name__}={sb!r}"})
        return

    sa = fm["superseded_at"]
    if not isinstance(sa, str) or not ISO_DATE_RE.match(sa):
        results.append({"path": rel, "level": "error", "rule": "superseded_at_format",
                        "msg": f"superseded_at must be YYYY-MM-DD; got {sa!r}"})
    sr = fm["superseded_reason"]
    if isinstance(sr, str) and sr.startswith('"') and sr.endswith('"'):
        sr = sr[1:-1]
    if not isinstance(sr, str) or not sr.strip():
        results.append({"path": rel, "level": "error", "rule": "superseded_reason_empty",
                        "msg": "superseded_reason cannot be empty"})
    elif len(sr) > REASON_MAX:
        results.append({"path": rel, "level": "error", "rule": "superseded_reason_too_long",
                        "msg": f"superseded_reason is {len(sr)} chars (limit {REASON_MAX})"})
    elif SHELL_INJECT_CHARS.search(sr):
        results.append({"path": rel, "level": "error", "rule": "superseded_reason_injection",
                        "msg": "superseded_reason contains shell-injectable chars (backtick/$/\\/newline)"})

    # Validate each superseded_by target + recurse transitively
    new_visited = visited_chain | {rel}
    for target in sb:
        target_clean = target.strip()
        m = WIKILINK_RE.search(target_clean)
        if not m:
            results.append({"path": rel, "level": "error", "rule": "superseded_by_not_wikilink",
                            "msg": f"superseded_by entry not a wikilink: {target_clean!r}"})
            continue
        slug = m.group(1)
        target_path = resolve_wikilink(slug)
        if target_path is None:
            results.append({"path": rel, "level": "error", "rule": "dangling_wikilink",
                            "msg": f"superseded_by target [[{slug}]] does not resolve to any wiki page"})
            continue
        # Recurse for chain check
        validate_one(target_path, results, visited_chain=new_visited, depth=depth + 1)


def staged_files() -> list[Path]:
    """Return list of files staged for commit (used in pre-commit mode)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached", "--diff-filter=ACM"],
            cwd=VAULT, capture_output=True, text=True, check=True,
        )
        return [VAULT / line for line in result.stdout.splitlines() if line.endswith(".md")]
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="Specific files to validate (default: all pages/)")
    ap.add_argument("--staged", action="store_true", help="Validate only staged files (pre-commit mode)")
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    args = ap.parse_args()

    targets: list[Path]
    if args.staged:
        targets = staged_files()
        if not targets:
            if args.json:
                print(json.dumps({"checked": 0, "errors": [], "ok": True}))
            else:
                print("No staged .md files; nothing to validate.")
            return 0
    elif args.paths:
        targets = [Path(p).resolve() for p in args.paths]
    else:
        targets = list((VAULT / "pages").rglob("*.md"))

    results: list[dict] = []
    for p in targets:
        if not p.is_file():
            continue
        validate_one(p, results)

    errors = [r for r in results if r["level"] == "error"]

    if args.json:
        print(json.dumps({
            "checked": len(targets),
            "errors_count": len(errors),
            "errors": errors,
            "ok": len(errors) == 0,
        }, indent=2))
    else:
        if not errors:
            print(f"✅ supersession-metadata validator: {len(targets)} files checked, 0 errors")
        else:
            print(f"🔴 supersession-metadata validator: {len(targets)} files checked, {len(errors)} errors:")
            for e in errors:
                print(f"  {e['path']}  [{e['rule']}]  {e['msg']}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
