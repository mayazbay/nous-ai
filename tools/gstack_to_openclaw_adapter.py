#!/usr/bin/env python3
"""
tools/gstack_to_openclaw_adapter.py — convert Garry Tan's gstack SKILL.md files
into OpenClaw-native skill format so the Air factory can load them.

Why: Tan's gstack SKILL.md frontmatter lacks `type: skill` + uses `allowed-tools:`
while OpenClaw expects `type: skill` + `tools:`. Without this adapter, factory
treats the top-level gstack/SKILL.md as one skill and ignores the 23+ subtools.

Design:
- Scan source dir for */SKILL.md (one level deep — each gstack/<tool>/SKILL.md).
- For each, transform frontmatter: add type/status/id/last_updated; rename
  allowed-tools→tools. Keep body untouched.
- Write to target flat dir as <tool>/SKILL.md — factory's extraDir loads each
  direct subdir as a skill.
- Source stays untouched (Tan's repo clean for future upgrades).

Idempotent: running twice is safe (rewrites target files).

Usage:
  python3 tools/gstack_to_openclaw_adapter.py \
    --source ~/nous-agaas/skills/gstack \
    --target ~/nous-agaas/skills \
    --prefix gstack-

--prefix (default "gstack-") namespaces converted skills to avoid name
collisions with OpenClaw-native skills (though session 56 audit confirmed
zero collisions at v1 — prefix kept as safe default).
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

TODAY = datetime.date.today().isoformat()


def parse_frontmatter(text: str):
    """Split a SKILL.md into (frontmatter_dict, body_str). Returns (None, text) if no frontmatter."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    header = text[4:end]
    body = text[end + 5:]
    # Ad-hoc YAML parse — we only need top-level key: value or key: [...] or key: | blocks.
    data = {}
    lines = header.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if line.startswith(" ") or line.startswith("-"):
            i += 1
            continue
        if ":" in line:
            key, rest = line.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            if rest == "|":
                # multi-line block
                block = []
                i += 1
                while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                    block.append(lines[i][2:] if lines[i].startswith("  ") else lines[i])
                    i += 1
                data[key] = "\n".join(block).strip()
                continue
            if rest == "":
                # multi-line list/dict — collect indented continuation
                block = []
                i += 1
                while i < len(lines) and (lines[i].startswith("  ") or lines[i].startswith("- ")):
                    block.append(lines[i])
                    i += 1
                data[key] = ("\n".join(block)).strip()
                continue
            data[key] = rest
        i += 1
    return data, body


def convert(src: Path, tool_name: str, prefix: str):
    """Read src SKILL.md, return (new_skill_name, new_skill_md_content) OR None to skip."""
    text = src.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        return None  # no frontmatter = not a skill
    name = fm.get("name", tool_name)
    version = fm.get("version", "0.0.0")
    description = fm.get("description", f"gstack {tool_name} (imported from Tan's upstream).")
    # Collapse multi-line description to single line for safety (OpenClaw prefers string)
    description = " ".join(description.split())
    # Triggers — reuse if present, else empty list
    triggers_block = fm.get("triggers", "")
    # tools — from allowed-tools if present
    tools_block = fm.get("allowed-tools", fm.get("tools", ""))
    # Namespace the skill
    new_name = f"{prefix}{name}"
    new_id = f"SKILL-{new_name.upper().replace('-', '_')}"

    # Build OpenClaw-native frontmatter
    new_fm_lines = [
        "---",
        "type: skill",
        f"name: {new_name}",
        f"id: {new_id}",
        f"version: {version}",
        f"last_updated: {TODAY}",
        "status: active",
        f'description: "{description.replace(chr(34), chr(39))}"',
    ]
    if triggers_block:
        new_fm_lines.append("triggers:")
        # preserve list format — re-indent any bare lines
        for ln in triggers_block.splitlines():
            ls = ln.strip()
            if not ls:
                continue
            if ls.startswith("- "):
                new_fm_lines.append(f"  {ls}")
            else:
                new_fm_lines.append(f"  - {ls}")
    if tools_block:
        new_fm_lines.append("tools:")
        for ln in tools_block.splitlines():
            ls = ln.strip()
            if not ls:
                continue
            if ls.startswith("- "):
                new_fm_lines.append(f"  {ls}")
            else:
                new_fm_lines.append(f"  - {ls}")
    new_fm_lines.append("mutating: false")
    new_fm_lines.append("source: gstack-upstream")
    new_fm_lines.append(f"upstream_path: gstack/{tool_name}/SKILL.md")
    new_fm_lines.append("---")
    new_fm_lines.append("")
    new_fm_lines.append(f"# {new_name} v{version}")
    new_fm_lines.append("")
    new_fm_lines.append(f"> **Imported from Garry Tan's gstack** — upstream at `gstack/{tool_name}/SKILL.md`. "
                        f"Regenerate via `tools/gstack_to_openclaw_adapter.py`. Do not edit this file directly; "
                        f"edit upstream and re-run the adapter.")
    new_fm_lines.append("")
    # Append original body (unchanged)
    return new_name, "\n".join(new_fm_lines) + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.path.expanduser("~/nous-agaas/skills/gstack"))
    ap.add_argument("--target", default=os.path.expanduser("~/nous-agaas/skills"))
    ap.add_argument("--prefix", default="gstack-")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not source.exists():
        print(f"[adapter] source not found: {source}", file=sys.stderr)
        sys.exit(2)
    target.mkdir(parents=True, exist_ok=True)

    # Find each direct-subdir-with-SKILL.md
    converted = 0
    skipped = 0
    written = []
    for sub in sorted(source.iterdir()):
        if not sub.is_dir():
            continue
        skill_file = sub / "SKILL.md"
        if not skill_file.is_file():
            continue
        tool_name = sub.name
        # Skip top-level non-skill dirs (bin, docs, contrib, extension, etc.)
        # Heuristic: skip if skill_file has no frontmatter OR if dir name is in blocklist
        blocklist = {"bin", "docs", "contrib", "extension", "openclaw",
                     "model-overlays", "hosts", "test", "dist",
                     "benchmark-models", "agents", "design"}
        if tool_name in blocklist:
            skipped += 1
            continue
        result = convert(skill_file, tool_name, args.prefix)
        if result is None:
            skipped += 1
            continue
        new_name, new_content = result
        out_dir = target / new_name
        out_skill = out_dir / "SKILL.md"
        if args.dry_run:
            print(f"[dry-run] would write {out_skill}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_skill.write_text(new_content, encoding="utf-8")
            written.append(new_name)
        converted += 1

    print(f"[adapter] converted={converted} skipped={skipped} source={source} target={target}")
    if written:
        print(f"[adapter] written skills:")
        for n in sorted(written):
            print(f"  - {n}")


if __name__ == "__main__":
    main()
