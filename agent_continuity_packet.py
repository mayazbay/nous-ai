#!/usr/bin/env python3
"""Build the shared Claude/GPT/Grok continuity packet.

This is deliberately a vault artifact, not a daemon. Ephemeral model sessions
can die; the packet gives the next model the same current state without relying
on the dead session's chat history.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from pathlib import Path

ALMATY = dt.timezone(dt.timedelta(hours=5))
def default_wiki() -> Path:
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    tool_root = Path(__file__).resolve().parents[1]
    if (tool_root / "pages").exists():
        return tool_root
    if (tool_root / "wiki" / "pages").exists():
        return tool_root / "wiki"
    return tool_root


DEFAULT_WIKI = default_wiki()
DEFAULT_OUTPUT_REL = Path("pages/systems/AGENT-CONTINUITY-PACKET.md")
EXCERPT_CHARS = 2200

PINNED_SOURCES = [
    "pages/plans/PLAN-MODEL-FAILOVER-CONTINUITY-2026-05-20.md",
    "pages/plans/PLAN-MODEL-FAILOVER-RESUME-LEDGER-2026-05-20.md",
    "pages/plans/PLAN-TELEGRAM-PRESIDENTIAL-CONTROL-PLANE-2026-05-20.md",
    "pages/audits/AUDIT-telegram-presidential-control-plane-2026-05-20.md",
    "pages/audits/GROK-DIRECT-STRUCTURE-CONSULT-2026-05-20.md",
    "pages/systems/MODEL-FAILOVER-LATEST.md",
    "pages/systems/model-failover-ledger.jsonl",
    "pages/skills/multi-model-consult/SKILL.md",
    "pages/skills/ceo-hierarchy/SKILL.md",
    "pages/skills/session-operating-contract/SKILL.md",
]


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def latest_handoff(wiki: Path) -> Path | None:
    handoffs = sorted(
        (wiki / "pages" / "progress").glob("HANDOFF-AUTO-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return handoffs[0] if handoffs else None


def read_excerpt(path: Path, limit: int = EXCERPT_CHARS) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        return f"(unreadable: {exc})"
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n...(excerpt truncated)"


def source_table(wiki: Path) -> str:
    rows = []
    for rel in PINNED_SOURCES:
        path = wiki / rel
        rows.append(f"- `{rel}`: {'present' if path.exists() else 'missing'}")
    return "\n".join(rows)


def build_packet(wiki: Path, generated_at: dt.datetime | None = None) -> str:
    wiki = wiki.resolve()
    generated_at = generated_at or now_kzt()
    handoff = latest_handoff(wiki)
    handoff_rel = handoff.relative_to(wiki).as_posix() if handoff else ""
    handoff_excerpt = read_excerpt(handoff) if handoff else "(no HANDOFF-AUTO file found)"

    return f"""---
title: Agent Continuity Packet
date: {generated_at.date().isoformat()}
status: active
type: system
generated_at: {generated_at.isoformat()}
---

# Agent Continuity Packet

## Contract

This is the shared continuity source for Claude, GPT/Codex, Grok, OpenClaw, Obsidian, gbrain, and QMD. If one model lane dies, the next lane reads this packet first and continues from the durable substrate instead of asking Madi to restate context.

## First 60 Seconds For Any Replacement Model

1. Read this file.
2. Read the latest handoff listed below.
3. Check `git status --short` before editing.
4. If doing code work, run `bash tools/session_scan.sh --overlap-with "<scope>"`.
5. Write results back to Obsidian under `pages/audits/`, `pages/progress/`, or the relevant `pages/skills/*/SKILL.md`; never rely on chat memory as the only record.

## Instant Switch Commands

- Claude lane: `/code <task>`
- GPT/Codex lane: `/codex <task>`
- Grok/OpenClaw lane: `/ask <task>` or plain Telegram text to `@nousAGaaSbot`
- Opus direct lane: `/ask-direct <task>`
- Instant switch lane: `/resume`, `/resume gpt`, `/resume grok`, `/resume claude`, `/resume opus`
- Council lane: `python3 tools/multi_model_consult.py --question "<question>"`

Every lane must treat this file plus the latest handoff plus `pages/systems/MODEL-FAILOVER-LATEST.md` as the continuity handshake.

## Current Route Shape

- Telegram is the presidential interface.
- Air is the 24/7 runtime.
- `/code` is Claude Code with tools.
- `/codex` is OpenAI Codex/GPT-5.5 with tools.
- `/ask` routes through OpenClaw/grok-ceo and cheap worker tiers.
- `/resume` reads the durable failover ledger and replays the latest captured task through the selected replacement lane.
- Direct Grok consults use `tools/multi_model_consult.py` or xAI API calls with this packet injected.
- Obsidian, gbrain, OpenBrain, and QMD are the durable memory/retrieval substrate.

## Latest Handoff

- path: `{handoff_rel or "missing"}`

```markdown
{handoff_excerpt}
```

## Pinned Continuity Sources

{source_table(wiki)}

## Git State

Dynamic Git state is intentionally not stored in this committed packet because the commit that saves the packet would make that value stale. Any replacement model must run:

```bash
git rev-parse --short HEAD
git status --short
```

## Do Not Build Yet

- No new Telegram polling process.
- No production Hermes gateway.
- No new mobile app or wrapper.
- No new MCP transport layer just to solve continuity.
- No private model-specific memory that bypasses Obsidian/gbrain/OpenBrain.
"""


def write_packet(wiki: Path, output_rel: Path = DEFAULT_OUTPUT_REL) -> Path:
    output_path = wiki / output_rel
    output_path.parent.mkdir(parents=True, exist_ok=True)
    packet = build_packet(wiki)
    if output_path.exists():
        old = output_path.read_text(encoding="utf-8", errors="replace")
        if comparable_packet(old) == comparable_packet(packet):
            return output_path
    output_path.write_text(packet, encoding="utf-8")
    return output_path


def comparable_packet(text: str) -> str:
    """Ignore timestamp-only refreshes so handoff reads do not dirty the repo."""
    return re.sub(r"^generated_at: .*$", "generated_at: <ignored>", text, flags=re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_REL)
    parser.add_argument("--print", action="store_true", help="Print packet after writing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = write_packet(args.wiki, args.output)
    if args.print:
        print(path.read_text(encoding="utf-8"))
    else:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
