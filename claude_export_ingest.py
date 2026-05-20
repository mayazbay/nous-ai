#!/usr/bin/env python3
"""
claude_export_ingest.py — ingest a Claude.ai data-export bundle into the Obsidian vault.

Reads conversations.json (JSON array of conversations) and produces Karpathy-compliant
source pages under pages/sources/claude-history/.

No LLM calls — purely rule-based extraction, categorization, and summarization.
Designed to run in the current credit-frozen environment.

Usage:
    python3 tools/claude_export_ingest.py --source ~/Downloads/data-2026-04-09-08-06-40-batch-0000 \
                                          --vault /Users/madia/Documents/Projects/Nous\ AGaaS/Nous \
                                          [--dry-run]

Output:
    pages/sources/claude-history/
        index-2026-04-09.md         — master chronological catalog of all conversations
        topic-work-vms.md           — conversations about Satory/VMS/ERAP/BDL/Spectra
        topic-nous-factory.md       — conversations about the Nous AI factory / Paperclip
        topic-commodity-trading.md  — TDC Trading / phosphate / steel / cement
        topic-restaurant-app.md     — Kazakhstan restaurant superapp
        topic-family-personal.md    — family / children / health / travel
        topic-travel.md             — Seoul, Phuket, Belek, travel planning
        topic-deals-investments.md  — helium, gas turbine, water PPP, Saken-aga pipeline
        topic-claude-code.md        — Claude Code, agents, Claude.ai tool usage
        topic-other.md              — everything else
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Categorization keyword rules (case-insensitive substring match on name+text)
# ---------------------------------------------------------------------------
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "work-vms": [
        "satory", "spectra", "erap", "bdl", "bigdatalab", "cerebro", "vms",
        "smartbridge", "шэп", "вшэп", "камер", "camera", "vko", "вко",
        "mergen", "мерген", "apk", "апк", "hikvision", "dahua", "ids-2cd",
        "isapi", "koap", "коап", "мрп", "kazakhstan traffic", "safe city",
        "ст.592", "nousagaas", "daniyar", "асылбек", "айдана", "назель",
        "roza", "рoza", "sadyrova", "ruslan", "руслан", "kalkancrypt",
        "coram ai", "keyhorse", "keona", "scylla", "sergek", "korkem",
        "presight", "targetai", "targeteye", "netline", "датчик", "радар",
    ],
    "nous-factory": [
        "paperclip", "cos team", "cos agent", "forge agent", "alpha agent",
        "nova agent", "echo agent", "lens agent", "polymarket", "openclaw",
        "polyclaw", "nous ai factory", "hetzner", "nous-ai-01", "ceo agent",
        "cto agent", "auditor agent", "frontend lead", "gemini 2.5 flash",
        "claude code", "claude max", "claude.ai", "agent team", "autonomous agent",
        "agents as a service", "agaas",
    ],
    "commodity-trading": [
        "tdc trading", "dmcc", "phosphate", "cement", "steel", "limestone",
        "phosagro", "acron", "kazphosphate", "dgc gypsum", "duc giang",
        "cam pha", "vinachem", "src ", "freight broker", "emeric", "p₂o₅",
        "thermal coal", "black sea", "anti-dumping", "kotra", "tradekorea",
        "korea build week", "syrian phosphate",
    ],
    "restaurant-app": [
        "restaurant", "tablet hell", "wolt", "glovo", "yandex eda",
        "chocofood", "iiko", "poster", "r-keeper", "kwaaka", "getorder",
        "kkm", "ккм", "protocol 2.0.2", "jacub", "ресторан",
    ],
    "family-personal": [
        "akmarzhan", "акмаржан", "tamerlan", "тамерлан", "kis ", "kazakhstan international school",
        "shona", "шона", "baby brezza", "kabrita", "fleur alpine",
        "vitamin d", "pediatrician", "formula pro", "infant",
        "intermittent fasting", "fasted workout", "sports research", "iherb",
        "hermès", "saint laurent", "menswear", "alpine ski", "smatay",
    ],
    "travel": [
        "seoul", "pullman ambassador", "air astana", "keona information technology",
        "phuket", "thailand", "belek", "turkey", "vacation", "hotel",
        "business class", "trip", "travel agent", "tour", "resort",
        "путешеств", "отель", "zere", "ainur", "sari",
    ],
    "deals-investments": [
        "helium", "sozak", "гелий", "gas turbine", "280 mw", "atyrau",
        "water ppp", "€160m", "water infrastructure", "enegix",
        "ekibastuz", "data center valley", "distressed mining",
        "grapheneos", "pixel 10", "simplex chat", "saken-aga", "saken aga",
        "saken orazalin", "saken rayo", "investment deal", "due diligence",
        "be brave", "honeywell", "swiss partner",
    ],
    "claude-code": [
        "claude code", "claude max", "claude.ai", "anthropic api",
        "remote control", "auto mode", "bypass permissions", "headless",
        "tmux", "mcp server", "model context protocol", "skill tool",
        "hooks", "slash command", "cli vs desktop", "claude agent sdk",
    ],
    "satory-gas": [
        "satory gas", "satory-gas", "tulpar gaz", "tulpar gas", "lp gaz",
        "tengizchevroil", "tco ", "turkestan", "lpg", "гнс", "propane",
        "corken pump", "gas cylinder",
    ],
}

# Priority order — if a conversation matches multiple topics, the first match wins
TOPIC_PRIORITY = [
    "work-vms",
    "nous-factory",
    "satory-gas",
    "commodity-trading",
    "restaurant-app",
    "deals-investments",
    "travel",
    "family-personal",
    "claude-code",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    """Turn a conversation name into a safe filename fragment."""
    s = re.sub(r"[^\w\s-]", "", text or "untitled", flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s.lower()[:80] or "untitled"


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        # Python 3.11+ handles Z directly
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def extract_first_user_message(msgs: list[dict]) -> str:
    for m in msgs:
        if m.get("sender") == "human" or m.get("role") == "user":
            text = m.get("text") or ""
            if not text and isinstance(m.get("content"), list):
                for c in m["content"]:
                    if isinstance(c, dict) and c.get("type") == "text":
                        text = c.get("text", "")
                        break
            return text[:300].replace("\n", " ").strip()
    return ""


def count_messages(msgs: list[dict]) -> tuple[int, int]:
    """Returns (human_count, assistant_count)."""
    h = sum(1 for m in msgs if m.get("sender") == "human" or m.get("role") == "user")
    a = sum(1 for m in msgs if m.get("sender") == "assistant" or m.get("role") == "assistant")
    return h, a


def categorize(name: str, first_msg: str) -> str:
    """Return the top-priority topic for a conversation."""
    haystack = (name + " " + first_msg).lower()
    for topic in TOPIC_PRIORITY:
        for kw in TOPIC_KEYWORDS[topic]:
            if kw.lower() in haystack:
                return topic
    return "other"


def yaml_escape(s: str) -> str:
    """Escape a string for YAML scalar use."""
    return s.replace('"', '\\"')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def load_conversations(path: Path) -> list[dict]:
    """Load conversations.json. Uses straight json.load — fine up to a few GB on a modern Mac."""
    print(f"[load] reading {path} ({path.stat().st_size / 1024 / 1024:.1f} MB)")
    with path.open() as f:
        data = json.load(f)
    print(f"[load] parsed {len(data)} conversations")
    return data


def extract_metadata(conv: dict) -> dict[str, Any]:
    """Pull the fields we care about for a single conversation."""
    msgs = conv.get("chat_messages") or conv.get("messages") or []
    first_user = extract_first_user_message(msgs)
    name = conv.get("name") or "(untitled)"
    category = categorize(name, first_user)
    h, a = count_messages(msgs)
    return {
        "uuid": conv.get("uuid"),
        "name": name,
        "created_at": conv.get("created_at"),
        "updated_at": conv.get("updated_at"),
        "message_count": len(msgs),
        "human_count": h,
        "assistant_count": a,
        "first_user_snippet": first_user,
        "category": category,
        "slug": slugify(name),
    }


def write_index_page(
    out_dir: Path,
    metas: list[dict],
    export_date: str,
    total_size_mb: float,
) -> Path:
    """Write the master index page with a chronological table of all conversations."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"index-{export_date}.md"

    # Sort by created_at descending (newest first)
    sorted_metas = sorted(
        metas,
        key=lambda m: parse_iso(m["created_at"]) or datetime.min.replace(tzinfo=None),
        reverse=True,
    )

    # Per-topic counts
    counts: dict[str, int] = defaultdict(int)
    for m in metas:
        counts[m["category"]] += 1

    with path.open("w") as f:
        f.write("---\n")
        f.write("type: source\n")
        f.write(f"id: SOURCE-CLAUDE-HISTORY-INDEX-{export_date}\n")
        f.write(f'title: "Claude.ai Conversations Index — {export_date} ({len(metas)} conversations)"\n')
        f.write("tags: [source, claude-ai, export, conversations, index, claude-history]\n")
        f.write(f"date: {export_date}\n")
        f.write("source_count: 1\n")
        f.write("status: reviewed\n")
        f.write(f"last_updated: {export_date}\n")
        f.write("related: [SOURCE-CLAUDE-EXPORT-MEMORIES-2026-04-09]\n")
        f.write("---\n\n")

        f.write(f"# Claude.ai Conversations Index — {export_date}\n\n")
        f.write(
            f"Full index of **{len(metas)} conversations** extracted from the Claude.ai Data Export "
            f"(`conversations.json`, {total_size_mb:.1f} MB). "
            f"Companion to [[source-claude-export-memories-2026-04-09]] which covers "
            "the curated memory + project descriptions.\n\n"
        )
        f.write(
            "This is a **rule-based metadata extract** — no LLM calls, no content "
            "summarization, no PII cleanup. It exists so that future sessions (and the "
            "factory, once credits are restored) can selectively deep-ingest specific "
            "high-value conversations into full Karpathy source pages.\n\n"
        )

        # Topic breakdown
        f.write("## Topic breakdown\n\n")
        f.write("| Topic | Count | Topic page |\n")
        f.write("|---|---:|---|\n")
        for topic in TOPIC_PRIORITY + ["other"]:
            count = counts.get(topic, 0)
            if count:
                f.write(f"| {topic} | {count} | [[topic-{topic}]] |\n")
        f.write("\n")

        # Chronological table
        f.write("## All conversations (newest first)\n\n")
        f.write("| Date | Topic | Name | Msgs (H/A) | UUID |\n")
        f.write("|---|---|---|---|---|\n")
        for m in sorted_metas:
            dt = parse_iso(m["created_at"])
            date_s = dt.strftime("%Y-%m-%d") if dt else "????-??-??"
            name = (m["name"] or "(untitled)").replace("|", "\\|")[:80]
            f.write(
                f"| {date_s} | {m['category']} | {name} | "
                f"{m['human_count']}/{m['assistant_count']} | "
                f"`{m['uuid'][:8]}…` |\n"
            )
        f.write("\n")

        f.write("## See also\n")
        f.write("- [[source-claude-export-memories-2026-04-09]] — companion (memories.json + projects.json)\n")
        for topic in TOPIC_PRIORITY + ["other"]:
            if counts.get(topic, 0):
                f.write(f"- [[topic-{topic}]] — {counts[topic]} conversations\n")
        f.write("\n")

    return path


def write_topic_page(
    out_dir: Path,
    topic: str,
    metas: list[dict],
    export_date: str,
) -> Path:
    """Write a topic-clustered summary page."""
    path = out_dir / f"topic-{topic}.md"

    sorted_metas = sorted(
        metas,
        key=lambda m: parse_iso(m["created_at"]) or datetime.min.replace(tzinfo=None),
        reverse=True,
    )

    topic_title = {
        "work-vms": "Satory VKO / VMS / ERAP / Spectra / BDL replacement",
        "nous-factory": "Nous AI factory / Paperclip agents / CoS-Forge-Alpha-Nova-Echo-Lens",
        "satory-gas": "Satory Gas / Tulpar Gaz / LP Gaz / LPG business",
        "commodity-trading": "TDC Trading DMCC / phosphate / cement / steel / commodities",
        "restaurant-app": "Kazakhstan restaurant superapp (tablet-hell solution)",
        "deals-investments": "Saken-aga-sourced deals / helium / gas turbine / water PPP / investments",
        "travel": "Travel — Seoul / Phuket / Belek / family vacation planning",
        "family-personal": "Family / personal — Akmarzhan, Tamerlan, Shona, health",
        "claude-code": "Claude Code / Claude.ai tooling / agents / MCP",
        "other": "Uncategorized / miscellaneous",
    }.get(topic, topic)

    with path.open("w") as f:
        f.write("---\n")
        f.write("type: source\n")
        f.write(f"id: SOURCE-CLAUDE-HISTORY-TOPIC-{topic.upper()}\n")
        f.write(f'title: "Claude.ai History — {yaml_escape(topic_title)}"\n')
        f.write(f"tags: [source, claude-ai, export, conversations, topic, {topic}]\n")
        f.write(f"date: {export_date}\n")
        f.write("source_count: 1\n")
        f.write("status: draft\n")
        f.write(f"last_updated: {export_date}\n")
        f.write(
            f"related: [SOURCE-CLAUDE-HISTORY-INDEX-{export_date}, "
            "SOURCE-CLAUDE-EXPORT-MEMORIES-2026-04-09]\n"
        )
        f.write("---\n\n")

        f.write(f"# Claude.ai History — {topic_title}\n\n")
        f.write(
            f"**{len(metas)} conversations** in this topic cluster, extracted from the "
            f"2026-04-09 Claude.ai Data Export (`conversations.json`). "
            f"Rule-based categorization — a conversation lands in this topic if its "
            f"name or first user message contains any of the topic's keywords.\n\n"
        )

        f.write("## Conversations (newest first)\n\n")
        for m in sorted_metas:
            dt = parse_iso(m["created_at"])
            date_s = dt.strftime("%Y-%m-%d") if dt else "????-??-??"
            name = m["name"] or "(untitled)"
            snippet = m["first_user_snippet"] or "(no opening user message)"

            f.write(f"### {date_s} — {name}\n\n")
            f.write(f"- **UUID:** `{m['uuid']}`\n")
            f.write(f"- **Messages:** {m['human_count']} human · {m['assistant_count']} assistant\n")
            f.write(f"- **Created:** `{m['created_at']}`\n")
            if m.get("updated_at") and m["updated_at"] != m["created_at"]:
                f.write(f"- **Updated:** `{m['updated_at']}`\n")
            f.write(f"- **First user message:** {snippet}\n\n")

        f.write("## See also\n")
        f.write(f"- [[index-{export_date}]] — master index of all conversations\n")
        f.write("- [[source-claude-export-memories-2026-04-09]] — companion memories + projects source\n")

    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "Downloads" / "data-2026-04-09-08-06-40-batch-0000",
        help="Path to the unzipped Claude.ai export directory",
    )
    ap.add_argument(
        "--vault",
        type=Path,
        default=Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous"),
        help="Path to the Obsidian vault root",
    )
    ap.add_argument(
        "--export-date",
        default="2026-04-09",
        help="Date tag for the output pages (YYYY-MM-DD)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts + sample entries, do not write any files",
    )
    args = ap.parse_args()

    conv_path = args.source / "conversations.json"
    if not conv_path.exists():
        print(f"[error] {conv_path} not found", file=sys.stderr)
        return 1

    total_size_mb = conv_path.stat().st_size / 1024 / 1024
    conversations = load_conversations(conv_path)

    print(f"[extract] processing {len(conversations)} conversations...")
    metas = [extract_metadata(c) for c in conversations]
    print(f"[extract] done — {len(metas)} metadata records")

    # Topic counts
    counts: dict[str, int] = defaultdict(int)
    for m in metas:
        counts[m["category"]] += 1
    print("\n[topics] conversation counts by category:")
    for topic in TOPIC_PRIORITY + ["other"]:
        c = counts.get(topic, 0)
        if c:
            print(f"  {topic:22s} {c:4d}")

    # Date range
    dates = [parse_iso(m["created_at"]) for m in metas if parse_iso(m["created_at"])]
    if dates:
        dates.sort()
        print(f"\n[range] oldest: {dates[0].strftime('%Y-%m-%d')}")
        print(f"[range] newest: {dates[-1].strftime('%Y-%m-%d')}")

    # Sample
    print("\n[sample] 3 newest conversations:")
    sorted_metas = sorted(
        metas,
        key=lambda m: parse_iso(m["created_at"]) or datetime.min.replace(tzinfo=None),
        reverse=True,
    )
    for m in sorted_metas[:3]:
        print(f"  [{m['category']:15s}] {(m['name'] or '(untitled)')[:60]}")
        if m["first_user_snippet"]:
            print(f"                     ↳ {m['first_user_snippet'][:80]}")

    if args.dry_run:
        print("\n[dry-run] not writing any files. Re-run without --dry-run to commit.")
        return 0

    # Write
    out_dir = args.vault / "pages" / "sources" / "claude-history"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[write] output dir: {out_dir}")

    index_path = write_index_page(out_dir, metas, args.export_date, total_size_mb)
    print(f"[write] {index_path.name}")

    # Group by topic and write topic pages
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for m in metas:
        by_topic[m["category"]].append(m)

    for topic, items in sorted(by_topic.items()):
        if not items:
            continue
        p = write_topic_page(out_dir, topic, items, args.export_date)
        print(f"[write] {p.name}  ({len(items)} conversations)")

    print(f"\n[done] wrote {1 + len(by_topic)} pages to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
