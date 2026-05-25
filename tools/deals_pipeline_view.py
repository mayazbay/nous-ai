#!/usr/bin/env python3
"""deals_pipeline_view.py — gbrain-native CRM aggregator.

Reads pages/deals/DEAL-*.md, parses YAML frontmatter, groups by stage,
writes:
  - pages/deals/_index.md (full pipeline table, by stage, sorted by deadline+value)
  - pages/progress/pipeline-digest-YYYY-MM-DD.md (daily Telegram-friendly summary)
  - optionally a Russian weekly digest body suitable for tg_send.sh

CLI:
  python3 tools/deals_pipeline_view.py                              # write _index + daily digest
  python3 tools/deals_pipeline_view.py --weekly                     # also write the Sat weekly digest body to stdout
  python3 tools/deals_pipeline_view.py --weekly --tg-send           # also push the weekly digest via tg_send.sh
  python3 tools/deals_pipeline_view.py --dry-run                    # parse only, no writes

Doctrine: P5.1 council verdict (COUNCIL-2026-05-23-business-tooling.md).
RULE ZERO: bumps to the gbrain-deals skill require SKILL.md + gbrain timeline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ALMATY = dt.timezone(dt.timedelta(hours=5))

DEALS_DIR_REL = Path("pages/deals")
DEAL_FILE_GLOB = "DEAL-*.md"
INDEX_FILE_REL = DEALS_DIR_REL / "_index.md"
PROGRESS_DIR_REL = Path("pages/progress")
TG_SEND_REL = Path("tools/tg_send.sh")

# Stage definitions (Russian primary, English alias for query)
STAGES_RU = [
    "ведущий",
    "квалифицированный",
    "предложение",
    "переговоры",
    "выигран",
    "проигран",
]
STAGE_EN = {
    "ведущий": "lead",
    "квалифицированный": "qualified",
    "предложение": "proposal",
    "переговоры": "negotiation",
    "выигран": "won",
    "проигран": "lost",
}
STAGE_ALIASES = {  # English → Russian canonical
    "lead": "ведущий",
    "qualified": "квалифицированный",
    "proposal": "предложение",
    "negotiation": "переговоры",
    "won": "выигран",
    "lost": "проигран",
}
ACTIVE_STAGES = {"ведущий", "квалифицированный", "предложение", "переговоры"}


def _vault_root() -> Path:
    env = sys.modules.get("os").environ.get("NOUS_WIKI") if "os" in sys.modules else None
    import os
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    tool_root = Path(__file__).resolve().parents[1]
    if (tool_root / "pages").exists():
        return tool_root
    return Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")


YAML_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
# Strip trailing inline `# comment` from scalar values, but not from inside quoted strings.
INLINE_COMMENT_RE = re.compile(r"\s+#(?:(?!['\"]).)*$")


def _strip_inline_comment(val: str) -> str:
    """Remove a trailing inline YAML comment from a scalar value.

    Conservative: only strips when the # is preceded by whitespace and the value
    is not inside quotes. Defensive against the kind of inline doc Madi might
    add (per gbrain-deals AP guidance the comment should go in a sibling field,
    but we tolerate inline for ergonomics).
    """
    if not val:
        return val
    if val.startswith(('"', "'")):
        # Quoted string — find matching close-quote then strip after it
        q = val[0]
        end = val.find(q, 1)
        if end != -1:
            tail = val[end + 1:]
            stripped = INLINE_COMMENT_RE.sub("", tail).rstrip()
            return val[:end + 1] + stripped
        return val
    # Unquoted: strip inline comment
    return INLINE_COMMENT_RE.sub("", val).rstrip()


def parse_yaml_block(text: str) -> dict[str, Any] | None:
    """Light YAML parser sufficient for our deal frontmatter (no anchors, no nested)."""
    m = YAML_FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    out: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in block.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            current_list_key = None
            continue
        if raw_line.startswith(" ") and current_list_key is not None and raw_line.lstrip().startswith("- "):
            item = _strip_inline_comment(raw_line.lstrip()[2:].strip())
            out.setdefault(current_list_key, []).append(item.strip('"').strip("'"))
            continue
        current_list_key = None
        if ":" not in raw_line:
            continue
        key, _, val = raw_line.partition(":")
        key = key.strip()
        val = _strip_inline_comment(val.strip())
        if not val:
            current_list_key = key
            out[key] = []
            continue
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            items = [s.strip().strip('"').strip("'") for s in inner.split(",")] if inner else []
            out[key] = items
            continue
        try:
            if "." not in val:
                out[key] = int(val)
                continue
        except ValueError:
            pass
        out[key] = val.strip('"').strip("'")
    return out


def canon_stage(s: str) -> str:
    s = (s or "").strip().lower()
    return STAGE_ALIASES.get(s, s)


def load_deals(deals_dir: Path) -> list[dict[str, Any]]:
    deals: list[dict[str, Any]] = []
    if not deals_dir.exists():
        return deals
    for p in sorted(deals_dir.glob(DEAL_FILE_GLOB)):
        try:
            body = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = parse_yaml_block(body)
        if not fm:
            continue
        fm["__file__"] = str(p.relative_to(deals_dir.parent.parent))
        fm["__title__"] = fm.get("title", p.stem)
        fm["__stage__"] = canon_stage(fm.get("status", "ведущий"))
        fm["__value_kzt__"] = int(fm.get("value_kzt", 0) or 0)
        fm["__deadline__"] = fm.get("deadline", "rolling") or "rolling"
        fm["__last_touched__"] = fm.get("last_touched", fm.get("date", "")) or ""
        fm["__owner__"] = fm.get("owner", "") or "unassigned"
        deals.append(fm)
    return deals


def group_by_stage(deals: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in deals:
        groups[d["__stage__"]].append(d)
    return groups


def stage_table_md(groups: dict[str, list[dict[str, Any]]]) -> str:
    rows = ["| Stage (Russian) | Stage (English) | Count | Total value (₸) | Earliest deadline |",
            "|---|---|---|---|---|"]
    for stage in STAGES_RU:
        items = groups.get(stage, [])
        count = len(items)
        total = sum(d["__value_kzt__"] for d in items)
        deadlines = sorted([d["__deadline__"] for d in items if d["__deadline__"] not in ("rolling", "")])
        earliest = deadlines[0] if deadlines else "—"
        rows.append(f"| {stage} | {STAGE_EN[stage]} | {count} | {total:,} | {earliest} |")
    return "\n".join(rows)


def per_stage_detail_md(groups: dict[str, list[dict[str, Any]]]) -> str:
    sections: list[str] = []
    for stage in STAGES_RU:
        items = groups.get(stage, [])
        if not items:
            continue
        items_sorted = sorted(items, key=lambda d: (d["__deadline__"] or "9999-99-99", -d["__value_kzt__"]))
        lines = [f"### {stage} ({STAGE_EN[stage]}) — {len(items)} deals · ₸{sum(d['__value_kzt__'] for d in items):,}"]
        lines.append("")
        lines.append("| Deal | Owner | Dept | Value (₸) | Prob % | Deadline | Last touched |")
        lines.append("|---|---|---|---|---|---|---|")
        for d in items_sorted:
            title = d["__title__"]
            file_rel = d["__file__"]
            link = f"[{title}]({Path(file_rel).name})"
            lines.append(
                f"| {link} | {d['__owner__']} | {d.get('department','')} | {d['__value_kzt__']:,} "
                f"| {d.get('probability_pct',0)} | {d['__deadline__']} | {d['__last_touched__']} |"
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections) if sections else "_(no deals seeded yet)_"


def accountability_md(deals: list[dict[str, Any]]) -> str:
    by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in deals:
        if d["__stage__"] in ACTIVE_STAGES:
            by_owner[d["__owner__"]].append(d)
    if not by_owner:
        return "_(no active deals; nothing to attribute)_"
    lines = ["| Owner | Active deals | Total active value (₸) | Stuck (>14d no touch) |",
             "|---|---|---|---|"]
    today = dt.datetime.now(ALMATY).date()
    for owner, items in sorted(by_owner.items(), key=lambda kv: -sum(d["__value_kzt__"] for d in kv[1])):
        total = sum(d["__value_kzt__"] for d in items)
        stuck = 0
        for d in items:
            try:
                lt = dt.datetime.strptime(d["__last_touched__"], "%Y-%m-%d").date()
                if (today - lt).days > 14:
                    stuck += 1
            except (ValueError, TypeError):
                stuck += 1  # missing last_touched also counts as stuck
        lines.append(f"| {owner} | {len(items)} | {total:,} | {stuck} |")
    return "\n".join(lines)


def recent_activity_md(deals: list[dict[str, Any]], days: int = 7) -> str:
    today = dt.datetime.now(ALMATY).date()
    cutoff = today - dt.timedelta(days=days)
    recent: list[dict[str, Any]] = []
    for d in deals:
        try:
            lt = dt.datetime.strptime(d["__last_touched__"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if lt >= cutoff:
            recent.append(d)
    if not recent:
        return f"_(no deal activity in the last {days} days)_"
    lines = ["| Date | Deal | Stage | Owner | Value (₸) |", "|---|---|---|---|---|"]
    for d in sorted(recent, key=lambda d: d["__last_touched__"], reverse=True):
        lines.append(
            f"| {d['__last_touched__']} | [{d['__title__']}]({Path(d['__file__']).name}) "
            f"| {d['__stage__']} | {d['__owner__']} | {d['__value_kzt__']:,} |"
        )
    return "\n".join(lines)


def render_index(deals: list[dict[str, Any]]) -> str:
    today = dt.datetime.now(ALMATY).strftime("%Y-%m-%d")
    groups = group_by_stage(deals)
    return f"""---
type: system
id: deals-index
title: "Deals pipeline index (auto-generated)"
tags: [system, deals, pipeline, index, auto-generated]
date: {today}
status: live
last_updated: {today}
related:
  - "[[deals-README]]"
---

# Deals pipeline index (auto-generated)

> **AUTO-GENERATED** by `tools/deals_pipeline_view.py`. Do not hand-edit — your changes will be overwritten on the next run.
> **Last updated:** {today} (Almaty)
> **Total deals tracked:** {len(deals)} · **Active:** {sum(1 for d in deals if d['__stage__'] in ACTIVE_STAGES)}

## Pipeline by stage

{stage_table_md(groups)}

## Deals by stage (sorted by deadline + value)

{per_stage_detail_md(groups)}

## Accountability by owner (active deals only)

{accountability_md(deals)}

## Recent activity (last 7 days)

{recent_activity_md(deals, days=7)}

---

*Run `python3 tools/deals_pipeline_view.py` to regenerate. Add new deals at `pages/deals/DEAL-<YYYY-MM-DD>-<slug>.md` using `pages/deals/_TEMPLATE.md`.*
"""


def render_daily_digest(deals: list[dict[str, Any]]) -> str:
    today = dt.datetime.now(ALMATY).strftime("%Y-%m-%d")
    groups = group_by_stage(deals)
    active_count = sum(1 for d in deals if d["__stage__"] in ACTIVE_STAGES)
    active_value = sum(d["__value_kzt__"] for d in deals if d["__stage__"] in ACTIVE_STAGES)
    return f"""---
type: progress
id: pipeline-digest-{today}
title: "Pipeline digest {today}"
tags: [progress, pipeline, daily-digest, auto-generated]
date: {today}
status: auto
---

# Pipeline digest — {today}

**Active deals:** {active_count} · **Active value:** ₸{active_value:,}

## By stage

{stage_table_md(groups)}

## Accountability

{accountability_md(deals)}

## Recent activity

{recent_activity_md(deals, days=2)}

*Full index: [pages/deals/_index.md](../deals/_index.md). Weekly Telegram digest fires Sat 09:00 KZT via `com.nous.pipeline-weekly-digest`.*
"""


def render_weekly_telegram(deals: list[dict[str, Any]]) -> str:
    """Russian-friendly weekly digest body (≤4000 chars for safe Telegram send)."""
    today = dt.datetime.now(ALMATY).strftime("%Y-%m-%d")
    groups = group_by_stage(deals)
    active = [d for d in deals if d["__stage__"] in ACTIVE_STAGES]
    active_value = sum(d["__value_kzt__"] for d in active)

    cutoff = dt.datetime.now(ALMATY).date() - dt.timedelta(days=7)
    recent_touches = []
    for d in deals:
        try:
            if dt.datetime.strptime(d["__last_touched__"], "%Y-%m-%d").date() >= cutoff:
                recent_touches.append(d)
        except (ValueError, TypeError):
            continue

    upcoming_deadlines = []
    one_week = dt.datetime.now(ALMATY).date() + dt.timedelta(days=7)
    for d in active:
        try:
            dl = dt.datetime.strptime(d["__deadline__"], "%Y-%m-%d").date()
            if dl <= one_week:
                upcoming_deadlines.append((dl, d))
        except (ValueError, TypeError):
            continue
    upcoming_deadlines.sort(key=lambda kv: kv[0])

    lines = [
        f"📊 Еженедельный pipeline · {today} (KZT)",
        "",
        f"Активные сделки: {len(active)} · стоимость ₸{active_value:,}",
        "",
        "По стадиям:",
    ]
    for stage in STAGES_RU:
        items = groups.get(stage, [])
        if items or stage in ACTIVE_STAGES:
            total = sum(d["__value_kzt__"] for d in items)
            lines.append(f"  • {stage}: {len(items)} · ₸{total:,}")

    lines.append("")
    if upcoming_deadlines:
        lines.append("⏰ Дедлайны на 7 дней:")
        for dl, d in upcoming_deadlines[:8]:
            lines.append(f"  • {dl} — {d['__title__']} ({d['__owner__']})")
    else:
        lines.append("⏰ Дедлайнов на 7 дней нет.")

    lines.append("")
    if recent_touches:
        lines.append(f"📝 Активность за неделю: {len(recent_touches)} касаний.")
    else:
        lines.append("📝 Активности за неделю не зафиксировано.")

    lines.append("")
    lines.append(f"Полный отчёт: pages/deals/_index.md")
    return "\n".join(lines)


def send_telegram(body: str, vault: Path) -> dict[str, Any]:
    tg = vault / TG_SEND_REL
    if not tg.exists():
        return {"sent": False, "error": f"tg_send.sh missing at {tg}"}
    try:
        result = subprocess.run(
            ["bash", str(tg), body],
            capture_output=True, text=True, timeout=20,
        )
        return {"sent": result.returncode == 0, "stdout": result.stdout[:200],
                "stderr": result.stderr[:200]}
    except subprocess.SubprocessError as exc:
        return {"sent": False, "error": f"{type(exc).__name__}: {exc}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weekly", action="store_true",
                        help="also emit the Russian weekly digest body")
    parser.add_argument("--tg-send", action="store_true",
                        help="when used with --weekly, push the digest via tg_send.sh")
    parser.add_argument("--dry-run", action="store_true",
                        help="parse only; do not write files or send Telegram")
    parser.add_argument("--json", action="store_true",
                        help="print result summary as JSON")
    args = parser.parse_args(argv)

    vault = _vault_root()
    deals_dir = vault / DEALS_DIR_REL
    deals = load_deals(deals_dir)
    today = dt.datetime.now(ALMATY).strftime("%Y-%m-%d")

    result: dict[str, Any] = {
        "ok": True,
        "today": today,
        "deals_count": len(deals),
        "active_count": sum(1 for d in deals if d["__stage__"] in ACTIVE_STAGES),
        "active_value_kzt": sum(d["__value_kzt__"] for d in deals if d["__stage__"] in ACTIVE_STAGES),
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        print(json.dumps(result, indent=2 if args.json else None, ensure_ascii=False))
        return 0

    # Write _index.md
    index_path = vault / INDEX_FILE_REL
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(render_index(deals), encoding="utf-8")
    result["index_path"] = str(index_path.relative_to(vault))

    # Write daily digest
    progress_dir = vault / PROGRESS_DIR_REL
    progress_dir.mkdir(parents=True, exist_ok=True)
    daily_path = progress_dir / f"pipeline-digest-{today}.md"
    daily_path.write_text(render_daily_digest(deals), encoding="utf-8")
    result["daily_digest_path"] = str(daily_path.relative_to(vault))

    if args.weekly:
        body = render_weekly_telegram(deals)
        result["weekly_digest_body"] = body
        if args.tg_send:
            result["telegram"] = send_telegram(body, vault)

    print(json.dumps(result, indent=2 if args.json else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
