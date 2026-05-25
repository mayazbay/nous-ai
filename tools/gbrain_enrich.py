#!/usr/bin/env python3
"""
GBrain Enrichment Write-Back — writes enriched pages INTO the Obsidian vault.

Architecture (LAW-005 compliant):
  1. GBrain is READ-ONLY (query for context, detect existing pages)
  2. All WRITES go to the vault as markdown files
  3. Existing wiki_to_bare.sh git sync propagates changes
  4. GBrain's 5-min sync cron re-indexes the updated pages

Usage:
  # Create/update an entity page
  python3 gbrain_enrich.py entity "Keon-A" --type org \
    --facts "Signed MOU on 2026-04-10" \
    --source "meeting-notes-2026-04-10"

  # Enrich from JSON stdin (batch mode)
  echo '[{"slug":"keon-a","type":"org","facts":["Signed MOU"],"source":"mtg"}]' | \
    python3 gbrain_enrich.py --batch

  # Append timeline entry to existing page
  python3 gbrain_enrich.py timeline "keona-it" \
    --date 2026-04-10 --text "MOU signed in Seoul" --source "mtg-notes"

Writes to: /root/nous-agaas/wiki/pages/entities/ (or other dirs based on type)
Format: Compiled truth + timeline (GBrain SKILLPACK Section 6)
"""

import os
import sys
import re
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime, date

WIKI = Path("/root/nous-agaas/wiki")
GBRAIN = "/opt/nous-agaas/gbrain/bin/gbrain"
LOG_FILE = WIKI / "log.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("gbrain_enrich")


# --- Helpers ---

def slugify(name: str) -> str:
    """Convert entity name to filesystem-safe slug."""
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", name.lower())
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60].strip("-") or "untitled"


def gbrain_query(question: str) -> str:
    """Query GBrain for context. Returns text or empty string."""
    try:
        result = subprocess.run(
            [GBRAIN, "query", question, "--no-expand"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as e:
        log.warning(f"GBrain query failed: {e}")
        return ""


def gbrain_search(term: str) -> str:
    """Keyword search GBrain. Returns text or empty string."""
    try:
        result = subprocess.run(
            [GBRAIN, "search", term],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as e:
        log.warning(f"GBrain search failed: {e}")
        return ""


def find_existing_page(slug: str) -> Path | None:
    """Find existing vault page by slug (searches entities/, concepts/, etc.)."""
    search_dirs = [
        WIKI / "pages" / "entities",
        WIKI / "pages" / "concepts",
        WIKI / "pages" / "projects",
        WIKI / "pages" / "sources",
    ]
    for d in search_dirs:
        candidate = d / f"{slug}.md"
        if candidate.exists():
            return candidate
    # Also try without directory prefix
    for d in search_dirs:
        if d.exists():
            for f in d.iterdir():
                if f.stem == slug:
                    return f
    return None


def today() -> str:
    return date.today().isoformat()


# --- Page Type Mapping ---

TYPE_TO_DIR = {
    "person": "entities",
    "org": "entities",
    "organization": "entities",
    "company": "entities",
    "concept": "concepts",
    "technology": "concepts",
    "project": "projects",
    "source": "sources",
}


def dir_for_type(entity_type: str) -> str:
    return TYPE_TO_DIR.get(entity_type.lower(), "entities")


# --- Compiled Truth + Timeline Format ---

COMPILED_TRUTH_TEMPLATE = """---
type: entity
id: {id}
title: "{title}"
tags: [{tags}]
date: {date}
source_count: 1
status: draft
last_updated: {date}
related: [{related}]
---

# {name}

{compiled_truth}

---

## Timeline

- **{date}** | Created via GBrain enrichment. {initial_fact} [[{source}]]

## See also
{see_also}
"""


def create_entity_page(
    slug: str,
    name: str,
    entity_type: str,
    facts: list[str],
    source: str,
    context: str = "",
) -> Path:
    """Create a new entity page in compiled truth + timeline format."""
    target_dir = WIKI / "pages" / dir_for_type(entity_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{slug}.md"

    entity_id = f"ENTITY-{slug.upper()}"
    tags = f"entity, {entity_type}"
    compiled_truth = "\n".join(f"- {f}" for f in facts) if facts else "*(Thin page — needs enrichment)*"
    initial_fact = facts[0] if facts else "Page created"
    see_also_lines = [f"- [[{source}]]"] if source else []

    content = COMPILED_TRUTH_TEMPLATE.format(
        id=entity_id,
        title=f"{name}",
        tags=tags,
        date=today(),
        related=source if source else "",
        name=name,
        compiled_truth=compiled_truth,
        initial_fact=initial_fact,
        source=source,
        see_also="\n".join(see_also_lines) if see_also_lines else "*(none yet)*",
    )

    target_path.write_text(content.strip() + "\n", encoding="utf-8")
    log.info(f"Created: {target_path.relative_to(WIKI)}")
    return target_path


def append_timeline(page_path: Path, date_str: str, text: str, source: str = "") -> bool:
    """Append a timeline entry to an existing page's Timeline section."""
    content = page_path.read_text(encoding="utf-8")

    # Find the Timeline section
    timeline_marker = "## Timeline"
    if timeline_marker not in content:
        # Add Timeline section before "## See also"
        see_also_idx = content.find("## See also")
        if see_also_idx >= 0:
            insert_at = see_also_idx
        else:
            insert_at = len(content)

        timeline_section = f"\n---\n\n{timeline_marker}\n\n"
        content = content[:insert_at] + timeline_section + content[insert_at:]

    # Build the timeline entry
    source_ref = f" [[{source}]]" if source else ""
    entry = f"- **{date_str}** | {text}{source_ref}\n"

    # Insert after "## Timeline" header (and after existing entries)
    timeline_idx = content.find(timeline_marker)
    # Find the end of the timeline section (next ## or end of file)
    next_section = content.find("\n## ", timeline_idx + len(timeline_marker))
    if next_section < 0:
        next_section = len(content)

    # Insert before the next section
    content = content[:next_section].rstrip() + "\n" + entry + "\n" + content[next_section:]

    # Update last_updated in frontmatter
    content = re.sub(
        r"last_updated:\s*\d{4}-\d{2}-\d{2}",
        f"last_updated: {today()}",
        content,
    )

    # Bump source_count
    match = re.search(r"source_count:\s*(\d+)", content)
    if match:
        old_count = int(match.group(1))
        content = content.replace(match.group(0), f"source_count: {old_count + 1}")

    page_path.write_text(content, encoding="utf-8")
    log.info(f"Timeline appended: {page_path.relative_to(WIKI)}")
    return True


def ensure_backlink(target_slug: str, source_slug: str) -> bool:
    """Iron law back-linking: ensure target page links back to source."""
    target_path = find_existing_page(target_slug)
    if not target_path:
        log.warning(f"Back-link target not found: {target_slug}")
        return False

    content = target_path.read_text(encoding="utf-8")
    if f"[[{source_slug}]]" in content:
        return True  # Already linked

    # Add to See also section
    see_also_idx = content.find("## See also")
    if see_also_idx >= 0:
        # Find end of See also section
        next_section = content.find("\n## ", see_also_idx + 10)
        insert_at = next_section if next_section >= 0 else len(content)
        link_line = f"- [[{source_slug}]]\n"
        content = content[:insert_at].rstrip() + "\n" + link_line + content[insert_at:]
    else:
        content = content.rstrip() + f"\n\n## See also\n- [[{source_slug}]]\n"

    target_path.write_text(content, encoding="utf-8")
    log.info(f"Back-link added: {target_slug} → {source_slug}")
    return True


def append_log(action: str, description: str):
    """Append to wiki log.md."""
    entry = f"\n## [{today()}] {action} | {description}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


# --- Main Entry Points ---

def enrich_entity(
    name: str,
    entity_type: str = "person",
    facts: list[str] | None = None,
    source: str = "",
) -> dict:
    """
    Main enrichment function. Creates or updates an entity page in the vault.
    
    Returns: {"action": "created"|"updated", "path": str, "slug": str}
    """
    slug = slugify(name)
    facts = facts or []
    
    # Step 1: Query GBrain for existing context (brain-first rule)
    context = gbrain_search(name)
    
    # Step 2: Check if vault page exists
    existing = find_existing_page(slug)
    
    if existing:
        # Step 3a: Append to timeline
        fact_text = "; ".join(facts) if facts else "Referenced"
        append_timeline(existing, today(), fact_text, source)
        
        # Step 4: Ensure back-links
        if source:
            ensure_backlink(slug, source)
        
        append_log("enrich", f"Updated {slug} with {len(facts)} facts from {source}")
        return {"action": "updated", "path": str(existing.relative_to(WIKI)), "slug": slug}
    else:
        # Step 3b: Create new page
        new_path = create_entity_page(slug, name, entity_type, facts, source, context)
        
        # Step 4: Ensure back-links
        if source:
            ensure_backlink(slug, source)
        
        append_log("enrich", f"Created {slug} ({entity_type}) from {source}")
        return {"action": "created", "path": str(new_path.relative_to(WIKI)), "slug": slug}


def enrich_timeline(slug: str, date_str: str, text: str, source: str = "") -> dict:
    """Add a timeline entry to an existing page."""
    existing = find_existing_page(slug)
    if not existing:
        return {"error": f"Page not found: {slug}"}
    
    append_timeline(existing, date_str, text, source)
    if source:
        ensure_backlink(slug, source)
    
    append_log("enrich", f"Timeline entry added to {slug}")
    return {"action": "timeline_added", "path": str(existing.relative_to(WIKI)), "slug": slug}


# --- CLI ---

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="GBrain enrichment write-back to vault")
    subparsers = parser.add_subparsers(dest="command")
    
    # entity command
    ep = subparsers.add_parser("entity", help="Create or update an entity page")
    ep.add_argument("name", help="Entity name")
    ep.add_argument("--type", default="person", help="Entity type: person, org, concept, etc.")
    ep.add_argument("--facts", nargs="+", help="Facts about the entity")
    ep.add_argument("--source", default="", help="Source slug for attribution")
    
    # timeline command
    tp = subparsers.add_parser("timeline", help="Add timeline entry to existing page")
    tp.add_argument("slug", help="Page slug")
    tp.add_argument("--date", default=today(), help="Date (YYYY-MM-DD)")
    tp.add_argument("--text", required=True, help="Timeline entry text")
    tp.add_argument("--source", default="", help="Source slug for attribution")
    
    # batch command (JSON from stdin)
    bp = subparsers.add_parser("batch", help="Batch enrich from JSON stdin")
    
    args = parser.parse_args()
    
    if args.command == "entity":
        result = enrich_entity(args.name, args.type, args.facts, args.source)
        print(json.dumps(result, indent=2))
    
    elif args.command == "timeline":
        result = enrich_timeline(args.slug, args.date, args.text, args.source)
        print(json.dumps(result, indent=2))
    
    elif args.command == "batch":
        data = json.load(sys.stdin)
        results = []
        for item in data:
            r = enrich_entity(
                name=item["name"],
                entity_type=item.get("type", "person"),
                facts=item.get("facts", []),
                source=item.get("source", ""),
            )
            results.append(r)
        print(json.dumps(results, indent=2))
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
