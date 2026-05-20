#!/usr/bin/env python3
"""
context_injector_v2.py — Progressive-disclosure context injection.

Replaces the v1 context_injector that dumps ~21 KB per task (full MEMORY.md +
full HANDOFF + 7 qmd pages). v2 uses:

  1. Skill catalog  (~200 tokens) — one-line-per-skill from RESOLVER.md
  2. Top-2 skills   (~2-3 KB each) — matched by task keywords against triggers
  3. HANDOFF summary (~500 tokens) — first 30 lines of latest HANDOFF

Target: ~5-8 KB total (≥60% reduction from v1's ~21 KB).

Activate via env var CONTEXT_INJECTOR_V2=1 in run_task.py.

Usage:
    from context_injector_v2 import get_context_v2

    enriched = get_context_v2("Check the camera health")
    # Returns: "--- FACTORY CONTEXT ---\\n...skills + handoff...\\n--- END CONTEXT ---\\n\\n## TASK\\nCheck..."
"""

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_SKILLS_ROOT = Path("/Users/madia/nous-agaas/skills")
RESOLVER_REL = "_gbrain/RESOLVER.md"           # relative to skills_root
WIKI_SKILLS_REL = "pages/skills"               # skill bodies live in wiki tree
HANDOFF_DIR_REL = "pages/progress"
MEMORY_REL = "pages/progress/claude-memory/MEMORY.md"

MAX_CONTEXT_CHARS_V2 = 7_500  # G4 threshold: final output + wrapper + task must be <8192 bytes; tuned 8000->7500
MAX_SKILL_CATALOG_CHARS = 1_600  # Real resolver has 60+ skills; catalog cannot consume the whole 8KB budget
MAX_SKILL_CHARS = 1_700        # Per-skill body cap; leaves room for handoff + memory packet
MAX_HANDOFF_LINES = 30         # Truncate HANDOFF to first N lines
MAX_MEMORY_PACKET_CHARS = 900   # Latest MEMORY top-block salience packet, not a full dump
TOP_N_SKILLS = 2               # How many full skill bodies to include

CONTEXT_HEADER = "--- FACTORY CONTEXT (injected v2) ---\n"
CONTEXT_FOOTER = "\n--- END CONTEXT ---\n\n## TASK\n"

MEMORY_SALIENCE_PATTERNS = (
    r"\bdirective\b",
    r"\bnow context\b",
    r"\bcurrent live substrate\b",
    r"\bproof probes?\b",
    r"\bhonest red/yellow\b",
    r"\bred/yellow\b",
    r"\bcarryover\b",
    r"\bblocked?\b",
    r"\bnot done\b",
    r"\bdeferred\b",
    r"\brule zero\b",
    r"\blaw-015\b",
    r"\blaw-017\b",
    r"\bopen\b",
    r"\bnext\b",
)
MEMORY_SALIENCE_RE = re.compile("|".join(MEMORY_SALIENCE_PATTERNS), re.IGNORECASE)


def _parse_resolver(skills_root: Path) -> list[dict]:
    """Parse RESOLVER.md and extract skill entries with trigger keywords.

    Returns list of dicts: [{"name": "camera-management", "triggers": ["camera", "ISAPI", ...], "path": "skills/camera-management/SKILL.md"}, ...]

    Args:
        skills_root: Path to skills directory (contains _gbrain/RESOLVER.md).
    """
    resolver_path = skills_root / RESOLVER_REL
    if not resolver_path.is_file():
        log.debug("context_injector_v2: RESOLVER.md not found at %s", resolver_path)
        return []

    try:
        text = resolver_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        log.debug("context_injector_v2: cannot read RESOLVER.md: %s", exc)
        return []

    entries = []
    # Match table rows: | trigger text | `skills/name/SKILL.md` |
    for match in re.finditer(
        r'\|\s*(.+?)\s*\|\s*`skills/(.+?)/SKILL\.md`\s*\|',
        text
    ):
        trigger_text = match.group(1).strip()
        skill_name = match.group(2).strip()

        # Skip header row
        if trigger_text.startswith("---") or trigger_text.lower() == "trigger":
            continue

        # Split triggers on commas and clean
        triggers = [t.strip().lower() for t in trigger_text.split(",") if t.strip()]
        # Also split multi-word triggers into individual words for matching
        trigger_words = set()
        for t in triggers:
            for word in re.findall(r'\b[\w/-]+\b', t):
                if len(word) > 2:  # Skip tiny words
                    trigger_words.add(word)

        entries.append({
            "name": skill_name,
            "triggers": triggers,
            "trigger_words": trigger_words,
            "path": f"skills/{skill_name}/SKILL.md",
        })

    return entries


def _build_skill_catalog(entries: list[dict]) -> str:
    """Build a concise one-line-per-skill catalog string."""
    if not entries:
        return ""

    lines = []
    for e in entries:
        triggers_str = ", ".join(e["triggers"][:3])  # Max 3 trigger phrases
        if len(e["triggers"]) > 3:
            triggers_str += ", ..."
        lines.append(f"- **{e['name']}**: {triggers_str}")

    catalog = "\n".join(lines)
    if len(catalog) <= MAX_SKILL_CATALOG_CHARS:
        return catalog

    kept = []
    used = 0
    for line in lines:
        projected = used + len(line) + 1
        if projected > MAX_SKILL_CATALOG_CHARS:
            break
        kept.append(line)
        used = projected
    kept.append("[... skill catalog truncated]")
    return "\n".join(kept)


def _score_skill(task_lower: str, task_words: set[str], entry: dict) -> float:
    """Score a skill against the task text. Higher = better match."""
    score = 0.0

    # Skill names are also legitimate user-facing handles ("storage retrieval",
    # "gbrain ops"). RESOLVER triggers should not be the only way to reach a
    # skill whose name is already specific.
    skill_name = entry["name"].lower()
    if skill_name in task_lower or skill_name.replace("-", " ") in task_lower:
        score += 2.5
    score += len(task_words & set(skill_name.replace("_", "-").split("-"))) * 0.5

    # Exact phrase matching (strongest signal)
    for trigger_phrase in entry["triggers"]:
        if trigger_phrase in task_lower:
            score += 3.0

    # Word overlap matching
    overlap = task_words & entry["trigger_words"]
    score += len(overlap) * 1.0

    return score


def _match_skills(task: str, entries: list[dict], max_skills: int = TOP_N_SKILLS) -> list[tuple[str, str]]:
    """Match task against RESOLVER entries. Returns [(name, ""), ...] for top-N.

    Note: Does NOT read skill bodies — caller does that separately for matched names.
    """
    if not entries:
        return []

    task_lower = task.lower()
    task_words = {w.lower() for w in re.findall(r'\b\w{3,}\b', task)}

    scored = []
    for entry in entries:
        s = _score_skill(task_lower, task_words, entry)
        if s > 0:
            scored.append((s, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(e["name"], e["path"]) for _, e in scored[:max_skills]]


def _strip_yaml_frontmatter(text: str) -> str:
    """Return markdown body without a leading YAML frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text.strip()

    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[idx + 1:]).strip()
    return text.strip()


def _read_skill_body(wiki: Path, skills_root: Path, skill_name: str) -> str:
    """Read a skill's SKILL.md body, truncated to MAX_SKILL_CHARS.

    Searches in two locations:
    1. Wiki tree: wiki/pages/skills/<name>/SKILL.md (source of truth)
    2. Runtime skills: skills_root/<name>/SKILL.md (fallback)
    """
    candidates = [
        wiki / WIKI_SKILLS_REL / skill_name / "SKILL.md",
        skills_root / skill_name / "SKILL.md",
    ]
    for skill_path in candidates:
        if not skill_path.is_file():
            continue
        try:
            body = _strip_yaml_frontmatter(skill_path.read_text(encoding="utf-8"))
            if len(body) > MAX_SKILL_CHARS:
                body = body[:MAX_SKILL_CHARS] + "\n[... skill truncated]"
            return body
        except (OSError, UnicodeDecodeError) as exc:
            log.debug("context_injector_v2: cannot read skill %s: %s", skill_name, exc)
            continue

    log.debug("context_injector_v2: skill not found in wiki or runtime: %s", skill_name)
    return ""


def _handoff_summary(wiki: Path, max_lines: int = MAX_HANDOFF_LINES) -> str:
    """Return first max_lines of the most recently modified HANDOFF-*.md."""
    handoff_dir = wiki / HANDOFF_DIR_REL
    try:
        candidates = sorted(
            handoff_dir.glob("HANDOFF-*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return ""

        latest = candidates[0]
        lines = latest.read_text(encoding="utf-8").splitlines()
        truncated = lines[:max_lines]
        result = "\n".join(truncated)
        if len(lines) > max_lines:
            result += f"\n[... {len(lines) - max_lines} more lines in full HANDOFF]"
        return result
    except (OSError, UnicodeDecodeError) as exc:
        log.debug("context_injector_v2: cannot read handoff: %s", exc)
        return ""


def _memory_top_block(wiki: Path) -> str:
    """Return the newest MEMORY.md stanza only.

    MEMORY.md is reverse-chronological. We never inject the full file; this
    helper gives the salience extractor one bounded stanza to inspect.
    """
    memory_path = wiki / MEMORY_REL
    if not memory_path.is_file():
        return ""

    try:
        lines = memory_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        log.debug("context_injector_v2: cannot read MEMORY.md: %s", exc)
        return ""

    start = None
    is_mercury_block = False
    for idx, line in enumerate(lines):
        if line.startswith("# Memory — updated "):
            start = idx
            break
        if line.startswith("# Now context"):
            start = idx
            is_mercury_block = True
            break
    if start is None:
        return ""

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if is_mercury_block and (lines[idx] == "---" or lines[idx].startswith("# Memory — updated ")):
            end = idx
            break
        if not is_mercury_block and lines[idx].startswith("# Memory — updated "):
            end = idx
            break

    return "\n".join(lines[start:end]).strip()


def _memory_workflow_packet(task: str, top_block: str) -> str:
    """Extract high-salience workflow lines from the newest MEMORY block.

    This mirrors token-retention doctrine at the agent-workflow layer: keep
    warnings, proof surfaces, open carryovers, and RULE ZERO signals; evict
    low-salience shipped narrative.
    """
    if not top_block:
        return ""

    kept = []
    for raw_line in top_block.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue
        if line.startswith("# Memory — updated "):
            header = line.split("**", 1)[0].strip()
            kept.append(header)
            line = line[len(header):].strip()
            if not line:
                continue

        # MEMORY top-blocks often pack many bold-labeled facts into one long
        # line. Split those into retention candidates so low-salience shipped
        # narrative does not crowd out red/yellow and carryover facts.
        segments = re.split(r"(?=\*\*[^*]{1,80}:\*\*)|(?<=[.;])\s+", line)
        for segment in segments:
            segment = segment.strip()
            if segment and MEMORY_SALIENCE_RE.search(segment):
                kept.append(segment)

    if len(kept) <= 1:
        return ""

    if not any("RULE ZERO" in line.upper() for line in kept):
        has_rule_zero_law = any("LAW-015" in line or "LAW-017" in line for line in kept)
        if has_rule_zero_law:
            kept.append("RULE ZERO signal: LAW-015/LAW-017 present — persist learnings in SKILL.md + gbrain timeline, not new LESSON files.")

    packet = "\n".join(kept)
    if len(packet) > MAX_MEMORY_PACKET_CHARS:
        packet = packet[:MAX_MEMORY_PACKET_CHARS].rstrip() + "\n[... memory packet truncated]"
    return packet


def get_context_v2(
    task: str,
    wiki_root: "Path | str | None" = None,
    skills_root: "Path | str | None" = None,
    inject: bool = True,
) -> str:
    """
    Return task prefixed with progressive-disclosure context.

    v2 design: skill catalog + top-2 matched skill bodies + HANDOFF summary.
    No MEMORY.md (identity is in SOUL.md system prompt now).
    No broad qmd search (skills replace the need for it).

    Args:
        task:         Raw task text (from Telegram or CLI).
        wiki_root:    Override wiki path (tests only).
        skills_root:  Override skills path (tests only). Contains _gbrain/RESOLVER.md.
        inject:       False → return task unchanged (health probes).

    Returns:
        Context block + task string, or original task if inject=False.
    """
    if not inject:
        return task

    wiki = Path(wiki_root) if wiki_root is not None else DEFAULT_WIKI
    skills = Path(skills_root) if skills_root is not None else DEFAULT_SKILLS_ROOT
    parts: list[str] = []

    # Step 1: Parse RESOLVER.md for skill entries
    entries = _parse_resolver(skills)

    # Step 2: Build skill catalog (concise, one-line-per-skill)
    catalog = _build_skill_catalog(entries)
    if catalog:
        parts.append(f"### Skill catalog ({len(entries)} skills)\n{catalog}")

    # Step 3: HANDOFF summary (first 30 lines)
    handoff = _handoff_summary(wiki, max_lines=MAX_HANDOFF_LINES)
    if handoff:
        parts.append(f"### Session state (latest HANDOFF)\n{handoff}")

    # Step 4: Latest MEMORY top-block salience packet. This is deliberately
    # small; v2 must not regress to full MEMORY.md injection.
    memory_packet = _memory_workflow_packet(task, _memory_top_block(wiki))
    if memory_packet:
        parts.append(f"### Memory workflow packet\n{memory_packet}")

    # Step 5: Match top-2 skills and include full bodies
    matched = _match_skills(task, entries, max_skills=TOP_N_SKILLS)
    for skill_name, skill_path in matched:
        body = _read_skill_body(wiki, skills, skill_name)
        if body:
            parts.append(f"### Matched skill: {skill_name}\n{body}")

    if not parts:
        log.warning("context_injector_v2: wiki at %s has no usable context — running bare", wiki)
        return task

    # Hard cap enforcement
    raw = "\n\n".join(parts)
    if len(raw) > MAX_CONTEXT_CHARS_V2:
        log.warning(
            "context_injector_v2: raw context %d chars > MAX %d — trimming",
            len(raw), MAX_CONTEXT_CHARS_V2,
        )
        raw = raw[:MAX_CONTEXT_CHARS_V2] + "\n[context trimmed to 7.5 KB]"

    delta = len(CONTEXT_HEADER) + len(raw) + len(CONTEXT_FOOTER)
    log.info("context_injector_v2: injected %d chars of context (v2 progressive)", delta)
    return CONTEXT_HEADER + raw + CONTEXT_FOOTER + task
