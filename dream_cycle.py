#!/usr/bin/env python3
"""
dream_cycle.py — Nightly READ-ONLY compounding pass.

Runs at 03:15 daily via launchd. Scans lessons and skills, identifies
unabsorbed lessons ≥7 days old, and writes a proposal page. NEVER
mutates skills directly — all changes go through a proposal that
the human (Madi) or the next interactive session reviews.

Design principle (Karpathy): "The LLM writing a book for itself on
how to solve problems." But we never let the nightly process push
changes to production skills without review.

Output: pages/dashboards/dream-cycle-proposals-YYYY-MM-DD.md
"""

import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

KZ_TZ = timezone(timedelta(hours=5))

WIKI_ROOT = Path("/Users/madia/nous-agaas/wiki")
LESSONS_DIR = WIKI_ROOT / "pages" / "lessons" / "individual"
SKILLS_DIR = WIKI_ROOT / "pages" / "skills"
DASHBOARDS_DIR = WIKI_ROOT / "pages" / "dashboards"
ABSORPTION_THRESHOLD_DAYS = 7

LOG_FILE = Path("/Users/madia/nous-agaas/logs/dream-cycle.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger(__name__)


def _scan_lessons() -> list[dict]:
    """Scan all LESSON files and return metadata."""
    lessons = []
    if not LESSONS_DIR.is_dir():
        return lessons

    for path in sorted(LESSONS_DIR.glob("LESSON-*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Parse frontmatter
        date_match = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
        status_match = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        title_match = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)

        lesson_date = date_match.group(1) if date_match else None
        status = status_match.group(1) if status_match else "unknown"
        title = title_match.group(1) if title_match else path.stem

        lessons.append({
            "file": path.name,
            "path": str(path),
            "date": lesson_date,
            "status": status,
            "title": title,
        })

    return lessons


def _scan_skills() -> dict[str, list[str]]:
    """Scan skills and return {skill_name: [absorbed_lesson_ids]}."""
    skills = {}
    if not SKILLS_DIR.is_dir():
        return skills

    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue

        try:
            text = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Extract absorbed lessons from frontmatter or evidence trail
        absorbed = set()
        # From frontmatter: absorbs_lessons: [LESSON-NNN, ...]
        fm_match = re.search(r"absorbs_lessons:\s*\[([^\]]*)\]", text)
        if fm_match:
            for lesson_ref in re.findall(r"LESSON-\d+", fm_match.group(1)):
                absorbed.add(lesson_ref)

        # From evidence trail
        for m in re.finditer(r"(LESSON-\d+)\s+absorbed", text):
            absorbed.add(m.group(1))

        skills[skill_dir.name] = sorted(absorbed)

    return skills


def _find_unabsorbed(lessons: list[dict], skills: dict[str, list[str]]) -> list[dict]:
    """Find lessons not absorbed by any skill and older than threshold."""
    all_absorbed = set()
    for absorbed_list in skills.values():
        all_absorbed.update(absorbed_list)

    now = datetime.now(KZ_TZ)
    unabsorbed = []

    for lesson in lessons:
        # Extract lesson ID (e.g., LESSON-042)
        id_match = re.match(r"(LESSON-\d+)", lesson["file"])
        if not id_match:
            continue
        lesson_id = id_match.group(1)

        # Skip lessons already triaged (absorbed, archived, or implicit)
        skip_statuses = {"absorbed", "archived-no-absorption-needed", "implicit-already-in-skill"}
        if lesson.get("status", "") in skip_statuses:
            continue

        if lesson_id in all_absorbed:
            continue

        # Check age
        if lesson["date"]:
            try:
                lesson_dt = datetime.strptime(lesson["date"], "%Y-%m-%d").replace(tzinfo=KZ_TZ)
                age_days = (now - lesson_dt).days
                if age_days < ABSORPTION_THRESHOLD_DAYS:
                    continue  # Too fresh — skip
                lesson["age_days"] = age_days
            except ValueError:
                lesson["age_days"] = -1
        else:
            lesson["age_days"] = -1

        lesson["lesson_id"] = lesson_id
        unabsorbed.append(lesson)

    return unabsorbed


def _suggest_target_skill(lesson: dict, skills: dict[str, list[str]]) -> str:
    """Suggest which skill should absorb a given lesson (heuristic)."""
    title = lesson.get("title", "").lower()
    file = lesson.get("file", "").lower()

    # Keyword-to-skill mapping (simplified heuristic)
    mappings = [
        (["camera", "isapi", "hikvision", "event", "violation"], "camera-management"),
        (["satory", "dashboard", "portal", "deploy", "website"], "satory-dashboard"),
        (["gbrain", "wiki", "obsidian", "memory", "rsync", "autopilot"], "gbrain-ops"),
        (["litellm", "docker", "launchd", "ssh", "tailscale", "infra"], "infrastructure"),
        (["telegram", "command", "handoff", "poll"], "command-center"),
        (["factory", "openclaw", "run_task", "agent"], "factory-ops"),
        (["audit", "lint", "health"], "audit"),
        (["quality", "done", "verify", "evidence"], "agent-quality"),
        (["deploy", "vercel", "fingerprint"], "website-deploy"),
        (["erap", "smartbridge", "gost", "ecп"], "smartbridge-soap-client"),
    ]

    combined = title + " " + file
    for keywords, skill in mappings:
        if any(kw in combined for kw in keywords):
            if skill in skills:
                return skill

    return "UNMATCHED — needs manual triage"


def _write_proposal(unabsorbed: list[dict], skills: dict[str, list[str]], total_lessons: int):
    """Write a proposal page to dashboards/."""
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(KZ_TZ)
    date_str = now.strftime("%Y-%m-%d")
    filename = f"dream-cycle-proposals-{date_str}.md"
    filepath = DASHBOARDS_DIR / filename

    absorbed_count = total_lessons - len(unabsorbed)
    absorption_pct = (absorbed_count / total_lessons * 100) if total_lessons > 0 else 0

    lines = [
        "---",
        "type: progress",
        f"id: DREAM-CYCLE-{date_str}",
        f'title: "Dream cycle proposals — {date_str}"',
        f"tags: [dream-cycle, proposals, automation, {date_str}]",
        f"date: {date_str}",
        "source_count: 0",
        "status: draft",
        f"last_updated: {date_str}",
        "related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]",
        "---",
        "",
        f"# Dream Cycle Proposals — {date_str}",
        "",
        f"Generated at {now.strftime('%H:%M %Z')} by `dream_cycle.py`.",
        "**READ-ONLY pass — no skills were mutated.**",
        "",
        "## Metrics",
        "",
        f"- Total lessons: {total_lessons}",
        f"- Absorbed: {absorbed_count} ({absorption_pct:.0f}%)",
        f"- Unabsorbed >= {ABSORPTION_THRESHOLD_DAYS}d: {len(unabsorbed)}",
        f"- Skills on disk: {len(skills)}",
        "",
    ]

    if not unabsorbed:
        lines.append("## Status: ALL CLEAR")
        lines.append("")
        lines.append("No unabsorbed lessons older than 7 days. Evolution loop healthy.")
    else:
        lines.append("## Proposals")
        lines.append("")
        for lesson in sorted(unabsorbed, key=lambda x: x.get("age_days", 0), reverse=True):
            target = _suggest_target_skill(lesson, skills)
            lines.append(f"### {lesson['lesson_id']}: {lesson['title']}")
            lines.append(f"- **Age:** {lesson.get('age_days', '?')} days")
            lines.append(f"- **Suggested skill:** `{target}`")
            lines.append(f"- **File:** `{lesson['file']}`")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## Timeline",
        "",
        f"- **{date_str}** | Dream cycle generated this proposal.",
        "",
        "## See also",
        "",
        "- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]",
        "- [[mistake-to-skill]]",
    ])

    filepath.write_text("\n".join(lines), encoding="utf-8")
    log.info("dream_cycle: wrote %s (%d proposals)", filename, len(unabsorbed))
    return filepath


def main():
    log.info("dream_cycle: starting nightly pass")

    lessons = _scan_lessons()
    log.info("dream_cycle: scanned %d lessons", len(lessons))

    skills = _scan_skills()
    log.info("dream_cycle: scanned %d skills", len(skills))

    unabsorbed = _find_unabsorbed(lessons, skills)
    log.info("dream_cycle: found %d unabsorbed lessons >= %dd", len(unabsorbed), ABSORPTION_THRESHOLD_DAYS)

    filepath = _write_proposal(unabsorbed, skills, len(lessons))
    log.info("dream_cycle: done. Output: %s", filepath)


if __name__ == "__main__":
    main()
