#!/usr/bin/env python3
"""Compute 5 weekly evolution-loop health metrics and write a dashboard.

Metrics:
  1. unabsorbed_count  — lessons with status=unabsorbed and age >= 7d (ghosts)
  2. skill_count       — skill directories in pages/skills/ (excl. extracted/, _gbrain/)
  3. lesson_count      — LESSON-*.md files in pages/lessons/individual/
  4. resolver_exists   — bool: pages/skills/_gbrain/RESOLVER.md present
  5. context_bytes     — "N/A" (measured at LiteLLM runtime, not from files)

Exits 1 if unabsorbed_count > 2 (alert threshold).

Usage:
    python3 ghost_debt_dashboard.py [--wiki PATH] [--format {md,text}]

Part of GOD_PROMPT v1.0 automation (Phase P4 task 3/5).
"""
import argparse
import datetime
import os
import pathlib
import sys

# Reuse scan_lessons from lesson_absorption_watcher (same tools/ dir)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from lesson_absorption_watcher import scan_lessons
except ImportError as exc:
    print(f"ERROR: cannot import lesson_absorption_watcher: {exc}", file=sys.stderr)
    sys.exit(2)


GHOST_ALERT_THRESHOLD = 2  # exit 1 if unabsorbed_count > this


def compute_metrics(
    wiki: pathlib.Path,
    today: datetime.date | None = None,
    sla_days: int = 7,
) -> dict:
    """Compute the 5 evolution-loop health metrics.

    Args:
        wiki:      path to wiki root (contains pages/)
        today:     reference date for ghost age (default: datetime.date.today())
        sla_days:  absorption SLA in days (default 7)

    Returns:
        dict with keys: unabsorbed_count, skill_count, lesson_count,
                        resolver_exists, context_bytes
    """
    if today is None:
        today = datetime.date.today()

    # 1. unabsorbed_count — delegate to scan_lessons (same as lesson_absorption_watcher)
    lessons_dir = wiki / "pages" / "lessons" / "individual"
    if lessons_dir.exists():
        ghosts = scan_lessons(lessons_dir, today=today, sla_days=sla_days)
        unabsorbed_count = len(ghosts)
    else:
        unabsorbed_count = 0

    # 2. skill_count — count skill dirs, exclude extracted/ and _gbrain/
    skills_dir = wiki / "pages" / "skills"
    excluded = {"extracted", "_gbrain"}
    if skills_dir.exists():
        skill_count = sum(
            1
            for d in skills_dir.iterdir()
            if d.is_dir() and d.name not in excluded
        )
    else:
        skill_count = 0

    # 3. lesson_count — all LESSON-*.md files
    if lessons_dir.exists():
        lesson_count = len(list(lessons_dir.glob("LESSON-*.md")))
    else:
        lesson_count = 0

    # 4. resolver_exists — check for RESOLVER.md in _gbrain/
    resolver_path = wiki / "pages" / "skills" / "_gbrain" / "RESOLVER.md"
    resolver_exists = resolver_path.exists()

    # 5. context_bytes — measured at LiteLLM runtime by context_injector.py,
    #    not derivable from static files. Stub with "N/A" per spec.
    context_bytes = "N/A"

    return {
        "unabsorbed_count": unabsorbed_count,
        "skill_count": skill_count,
        "lesson_count": lesson_count,
        "resolver_exists": resolver_exists,
        "context_bytes": context_bytes,
    }


def write_dashboard(metrics: dict, out_path: pathlib.Path) -> None:
    """Write the markdown dashboard to out_path with YAML frontmatter."""
    today = datetime.date.today().isoformat()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        "type: dashboard",
        "id: DASH-GHOST-DEBT",
        f'title: "Ghost debt dashboard — {today}"',
        "tags: [dashboard, ghost-debt, evolution-loop, auto-generated]",
        f"date: {today}",
        "source_count: 0",
        "status: active",
        f"last_updated: {today}",
        "related: [mistake-to-skill, gbrain-ops, lesson-absorption-debt]",
        "---",
        "",
        f"# Ghost debt dashboard — {today}",
        "",
        "Weekly evolution-loop health metrics. Part of GOD_PROMPT v1.0 Phase P4.",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Target | Status |",
        "|---|---|---|---|",
    ]

    def _row(name: str, value, target: str, ok: bool) -> str:
        status = "✅ OK" if ok else "🔴 ALERT"
        return f"| {name} | {value} | {target} | {status} |"

    ghost_ok = metrics["unabsorbed_count"] <= GHOST_ALERT_THRESHOLD
    lines.append(_row("unabsorbed_count (ghosts ≥7d)", metrics["unabsorbed_count"], f"≤{GHOST_ALERT_THRESHOLD}", ghost_ok))
    lines.append(_row("skill_count", metrics["skill_count"], "≥10", metrics["skill_count"] >= 10))
    lines.append(_row("lesson_count", metrics["lesson_count"], "tracked", True))
    lines.append(_row("resolver_exists", metrics["resolver_exists"], "True", metrics["resolver_exists"]))
    lines.append(_row("context_bytes", metrics["context_bytes"], "≤4000", True))

    lines += [
        "",
        "## Notes",
        "",
        "- `unabsorbed_count`: lessons with `status: unabsorbed` and age ≥ 7 days. Source: `lesson_absorption_watcher.scan_lessons()`.",
        "- `skill_count`: directories in `pages/skills/` excluding `extracted/` and `_gbrain/`.",
        "- `lesson_count`: all `LESSON-*.md` files in `pages/lessons/individual/`.",
        "- `resolver_exists`: `pages/skills/_gbrain/RESOLVER.md` present.",
        "- `context_bytes`: measured by `context_injector.py` at runtime — not computable from static files. See Air LiteLLM logs.",
        "",
        "## See also",
        "",
        "- [[lesson-absorption-debt]] — per-lesson ghost detail",
        "- [[mistake-to-skill]] — skill creation procedure",
        "- [[gbrain-ops]] — memory hygiene",
        "",
        "---",
        "",
        "## Timeline",
        "",
        f"- **{today}** | v1.0 generated by `ghost_debt_dashboard.py` (GOD_PROMPT v1.0 Phase P4).",
    ]

    out_path.write_text("\n".join(lines) + "\n")


def print_text_report(metrics: dict) -> None:
    """Print a terminal-readable summary."""
    print("=== Ghost Debt Dashboard ===")
    print(f"  unabsorbed_count : {metrics['unabsorbed_count']} (threshold: ≤{GHOST_ALERT_THRESHOLD})")
    print(f"  skill_count      : {metrics['skill_count']}")
    print(f"  lesson_count     : {metrics['lesson_count']}")
    print(f"  resolver_exists  : {metrics['resolver_exists']}")
    print(f"  context_bytes    : {metrics['context_bytes']}")
    if metrics["unabsorbed_count"] > GHOST_ALERT_THRESHOLD:
        print(f"  STATUS: 🔴 ALERT — {metrics['unabsorbed_count']} ghosts > threshold {GHOST_ALERT_THRESHOLD}")
    else:
        print("  STATUS: ✅ Healthy")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Ghost debt dashboard — evolution-loop health check"
    )
    ap.add_argument(
        "--wiki",
        default=os.path.expanduser("~/nous-agaas/wiki"),
        help="Path to wiki root (default: ~/nous-agaas/wiki)",
    )
    ap.add_argument(
        "--format",
        choices=["md", "text"],
        default="md",
        help="Output format: md writes dashboard file, text prints to terminal (default: md)",
    )
    ap.add_argument(
        "--sla-days",
        type=int,
        default=7,
        help="Ghost SLA threshold in days (default: 7)",
    )
    args = ap.parse_args()

    wiki = pathlib.Path(args.wiki)
    if not wiki.exists():
        print(f"ERROR: wiki not found: {wiki}", file=sys.stderr)
        sys.exit(2)

    metrics = compute_metrics(wiki, sla_days=args.sla_days)

    if args.format == "text":
        print_text_report(metrics)
    else:
        dashboard_path = wiki / "pages" / "dashboards" / "ghost-debt-dashboard.md"
        write_dashboard(metrics, dashboard_path)
        print(f"Dashboard written: {dashboard_path}")
        print_text_report(metrics)

    if metrics["unabsorbed_count"] > GHOST_ALERT_THRESHOLD:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
