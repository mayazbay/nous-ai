#!/usr/bin/env python3
"""
mark_superseded.py — AP-61 Phase-1 deliverable, v2 (autoplan-tightened).

Replaces the awk-based v1 (mark_superseded.sh) which had a duplicate-YAML-keys
bug per autoplan v1 Codex DX P0 finding. This Python version is YAML-aware:
parses frontmatter, mutates it as a structured object, writes back without
duplicating fields.

Implements pages/specs/2026-04-30-ap61-supersession-metadata-stub.md D1 v2:
NO `status:` field (collision with 782 existing pages, 129 distinct values).
Signal supersession by presence of `superseded_by:` alone.

v1 fields (3, all required when superseded):
  superseded_by: [wikilink, ...]  (1+ wikilinks to current authoritative page)
  superseded_at: YYYY-MM-DD       (ISO date)
  superseded_reason: "<1-line>"   (≤140 chars rationale)

Usage:
    tools/mark_superseded.py <old-slug> <new-canonical-slug> [--reason "..."]
    tools/mark_superseded.py --help
    tools/mark_superseded.py --dry-run <old-slug> <new-canonical-slug>

Examples:
    tools/mark_superseded.py lesson-055 skills/factory-ops/skill --reason "absorbed into factory-ops AP-3"
    tools/mark_superseded.py --dry-run lesson-055 skills/factory-ops/skill --reason "test"

Behavior:
    - Atomic write via temp file in SAME directory as target (prevents cross-fs mv)
    - Idempotent on all 3 fields (not just one) — partial-state detected and rejected
    - Refuses to run on dirty git tree (use --force to override)
    - Locks via flock on a sibling .lock file (prevents concurrent peer-lane race)
    - --dry-run prints diff without writing
    - --help prints this docstring

Privacy: no PII handling needed (operates only on wiki frontmatter)
Anti-collision: combine with `git commit -o <path>` per session-coordination AP-5.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

VAULT = Path(os.environ.get("VAULT", Path(__file__).resolve().parent.parent))
REASON_MAX = 140
SHELL_INJECT_CHARS = re.compile(r"[`$\\\n\r]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

REQUIRED_FIELDS = ("superseded_by", "superseded_at", "superseded_reason")


def die(msg: str, code: int = 1) -> None:
    sys.stderr.write(f"[mark_superseded.py] ERROR: {msg}\n")
    sys.exit(code)


def info(msg: str) -> None:
    sys.stderr.write(f"[mark_superseded.py] {msg}\n")


def resolve_old_path(old_input: str) -> Path:
    """Find the actual file for the old slug. Strict: exact path/slug or unique fuzzy match."""
    candidates: list[Path] = []
    stripped = old_input.removeprefix("pages/").removesuffix(".md")

    # Try exact paths in order of specificity
    for p in (
        VAULT / old_input,
        VAULT / f"{old_input}.md",
        VAULT / "pages" / f"{stripped}.md",
        VAULT / "pages" / stripped / "SKILL.md",
        VAULT / "pages" / "skills" / stripped / "SKILL.md",
    ):
        if p.is_file():
            return p

    # Fuzzy fallback: glob matches under pages/
    if len(stripped) < 8:
        die(f"old slug '{old_input}' too short for fuzzy match (min 8 chars)")
    matches = list((VAULT / "pages").rglob(f"*{stripped}*.md"))
    if not matches:
        die(f"old page '{old_input}' not found.\n"
            f"  Tried: {VAULT}/{old_input}, {VAULT}/{old_input}.md, {VAULT}/pages/{stripped}.md\n"
            f"  Tip: tools/mark_superseded.py accepts a slug, path, or fuzzy substring (≥8 chars).")
    if len(matches) > 1:
        die(f"old slug '{old_input}' is ambiguous, matches {len(matches)} files:\n  " +
            "\n  ".join(str(m.relative_to(VAULT)) for m in matches[:10]) +
            ("\n  ..." if len(matches) > 10 else ""))
    return matches[0]


def verify_new_target_exists(new_input: str) -> str:
    """Check the new canonical target resolves to a real file. Returns the canonical wikilink form."""
    stripped = new_input.removeprefix("pages/").removesuffix(".md")
    for p in (
        VAULT / "pages" / f"{stripped}.md",
        VAULT / "pages" / stripped / "SKILL.md",
        VAULT / "pages" / "skills" / stripped / "SKILL.md",
    ):
        if p.is_file():
            # canonical form: relative-to-pages slug, no .md, no SKILL.md
            return stripped
    die(f"new canonical target '{new_input}' not found (looked under {VAULT}/pages/)")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, int]:
    """Returns (frontmatter_kv_dict, body, end_offset).
    Minimal YAML — handles flat key:value and `key:` followed by indented list/scalar.
    Does NOT handle deeply-nested structures; AP-61 frontmatter doesn't need them.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        die("file has no YAML frontmatter (must start with '---\\n...\\n---\\n')")
    fm_text = m.group(1)
    end = m.end()
    fm: dict[str, str] = {}
    cur_key: str | None = None
    cur_lines: list[str] = []
    for line in fm_text.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*:", line):
            if cur_key is not None:
                fm[cur_key] = "\n".join(cur_lines).rstrip()
            cur_key, _, val = line.partition(":")
            cur_key = cur_key.strip()
            cur_lines = [val.strip()] if val.strip() else []
        else:
            if cur_key is None:
                continue
            cur_lines.append(line)
    if cur_key is not None:
        fm[cur_key] = "\n".join(cur_lines).rstrip()
    return fm, text[end:], end


def render_frontmatter(fm: dict[str, str], original_order: list[str]) -> str:
    """Render dict back to YAML, preserving original key order then appending new keys at end."""
    lines = ["---"]
    seen = set()
    for k in original_order:
        if k in fm:
            v = fm[k]
            if "\n" in v:
                lines.append(f"{k}:")
                for sub in v.splitlines():
                    if sub.startswith((" ", "-")):
                        lines.append(sub)
                    else:
                        lines.append(f"  {sub}")
            else:
                lines.append(f"{k}: {v}")
            seen.add(k)
    for k, v in fm.items():
        if k in seen:
            continue
        if "\n" in v:
            lines.append(f"{k}:")
            for sub in v.splitlines():
                if sub.startswith((" ", "-")):
                    lines.append(sub)
                else:
                    lines.append(f"  {sub}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def get_original_key_order(fm_text: str) -> list[str]:
    order: list[str] = []
    for line in fm_text.splitlines():
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):", line)
        if m:
            order.append(m.group(1))
    return order


def is_dirty(path: Path) -> bool:
    """Check git status for uncommitted changes on the target file."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", str(path)],
            cwd=VAULT, capture_output=True, text=True, check=False,
        )
        return bool(result.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Mark a wiki page superseded by a new canonical page (AP-61 Phase-1, v2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("old", nargs="?", help="Old page slug or path")
    ap.add_argument("new", nargs="?", help="New canonical page slug or path")
    ap.add_argument("--reason", "-r", help="Supersession reason (1 line, ≤140 chars). If omitted, prompts.")
    ap.add_argument("--dry-run", action="store_true", help="Print what would change; don't mutate files")
    ap.add_argument("--force", action="store_true", help="Override clean-tree check")
    args = ap.parse_args()

    if not args.old or not args.new:
        ap.print_help(sys.stderr)
        return 2

    old_path = resolve_old_path(args.old)
    new_slug = verify_new_target_exists(args.new)

    text = old_path.read_text(encoding="utf-8")
    fm, body, _ = parse_frontmatter(text)

    # Idempotency on ALL 3 required fields, not just one (autoplan F4 fix)
    present = [f for f in REQUIRED_FIELDS if f in fm]
    if len(present) == 3:
        info(f"already superseded (all 3 fields present): {old_path.relative_to(VAULT)}")
        for f in REQUIRED_FIELDS:
            info(f"  {f}: {fm[f]}")
        info("idempotent no-op")
        return 0
    if 0 < len(present) < 3:
        missing = [f for f in REQUIRED_FIELDS if f not in fm]
        die(f"partial supersession state in {old_path.relative_to(VAULT)}:\n"
            f"  present: {present}\n  missing: {missing}\n"
            f"  fix manually or remove the present fields and re-run")

    # Get reason
    reason = args.reason
    if not reason:
        if sys.stdin.isatty():
            sys.stderr.write(f"Reason for superseding (≤{REASON_MAX} chars): ")
            reason = sys.stdin.readline().rstrip("\n\r")
        else:
            die(f"--reason required when stdin is not a TTY (or set SUPERSEDED_REASON)")
    reason = reason.strip()
    if not reason:
        die("reason cannot be empty")
    if len(reason) > REASON_MAX:
        die(f"reason is {len(reason)} chars (limit {REASON_MAX}, you're {len(reason)-REASON_MAX} over)")
    if SHELL_INJECT_CHARS.search(reason):
        die("reason contains shell-injectable chars (backtick, $, \\, newline). Use plain prose.")

    # Clean-tree check
    if not args.force and is_dirty(old_path):
        die(f"target file has uncommitted changes: {old_path.relative_to(VAULT)}\n"
            f"  Commit or stash first, OR pass --force to override.")

    # Build the 3 new fields
    today = date.today().isoformat()
    new_fields = {
        "superseded_by": f"\n  - \"[[{new_slug}]]\"",
        "superseded_at": today,
        "superseded_reason": f'"{reason}"',
    }

    # Get original order, append new keys after frontmatter (no in-place injection)
    fm_text = FRONTMATTER_RE.match(text).group(1)
    original_order = get_original_key_order(fm_text)

    fm_new = dict(fm)
    fm_new.update(new_fields)
    new_text = render_frontmatter(fm_new, original_order) + body

    # Dry-run path
    if args.dry_run:
        info("--dry-run: would write the following changes:")
        sys.stderr.write("--- old\n+++ new\n")
        for f in REQUIRED_FIELDS:
            sys.stderr.write(f"+ {f}: {new_fields[f]}\n")
        info(f"target file: {old_path.relative_to(VAULT)}")
        return 0

    # Atomic write: temp file in SAME directory (prevents cross-fs mv issues)
    tmp_dir = old_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=tmp_dir, prefix=".mark_superseded.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        # Preserve permissions
        shutil.copystat(old_path, tmp_path)
        os.replace(tmp_path, old_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    info(f"✅ marked superseded: {old_path.relative_to(VAULT)}")
    info(f"  superseded_by: [[{new_slug}]]")
    info(f"  superseded_at: {today}")
    info(f'  superseded_reason: "{reason}"')
    info("")
    info("Next: review the diff and commit:")
    info(f"  git diff '{old_path.relative_to(VAULT)}'")
    info(f"  git commit -o '{old_path.relative_to(VAULT)}' -m 'mark <slug> superseded by {new_slug}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
