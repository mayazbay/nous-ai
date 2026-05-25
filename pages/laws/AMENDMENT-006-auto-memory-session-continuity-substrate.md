---
type: law
id: AMENDMENT-006-auto-memory-session-continuity-substrate
title: "AMENDMENT-006: Auto-memory as session-continuity substrate"
tags: [law, amendment, auto-memory, session-continuity, substrate, mercury]
date: 2026-04-18
status: active
related:
  - "[[skills/karpathy-loop/skill]]"
  - "[[skills/session-operating-contract/skill]]"
  - "[[skills/session-coordination/skill]]"
  - "[[AMENDMENT-005-skill-first-evolution]]"
  - "[[LAW-005-obsidian-master]]"
---

# AMENDMENT-006: Auto-memory as session-continuity substrate

## Rule

Claude Code's auto-memory (`memory/MEMORY.md` symlinked into the vault under `pages/progress/claude-memory/`) is treated as a **first-class substrate component**, not a transient session log. It is:

1. The continuity substrate that lets ephemeral CLI sessions hand off to one another without re-reading every handoff
2. A top-block-prepend channel where each session adds compounding facts (laws, AP pointers, current-state markers)
3. Subject to the same RULE ZERO discipline as SKILL.md files (no LESSON files; bumps go via prepended top-block)

Top-block-prepend semantics means the most recent context is at the top, and decayed context falls off naturally as the file rotates. Mercury Phase 3 (2026-04-29) replaced raw MEMORY.md with `MEMORY-mercury.md` — a 90.8%-token-reduced curated subset injected at session-start.

## Why

Sessions are ephemeral by design (Mac terminal Claude Code, Air `/code`, Codex, factory worker spawns — all die on disconnect). The substrate is what compounds across sessions. Without auto-memory as a substrate component:
- Each session re-loads from raw HANDOFF-AUTO-* files, paying token cost N times
- Recent context (current-session SID, in-flight Stream-A claims, today's HEAD, AP carryovers) gets re-discovered every turn
- Cross-session handshakes (same-day parallel lanes) lose the shared "what just happened" channel

With auto-memory as substrate:
- Mercury Phase 3 injects ~1500 tokens of high-signal context at session-start
- Top-block-prepend compounds new facts at the head while old facts rotate off
- Substrate-IS-the-handshake: ephemeral sessions die, MEMORY persists, next session reads the head and continues

## How to apply

- Every session-close: prepend a current-state block (HEAD, SID, deferred carryovers, axis-1 weak findings) to `MEMORY.md` via the auto-memory mechanism.
- Mercury Phase 3 (`tools/mercury_phase3_regen.sh`) regenerates `MEMORY-mercury.md` periodically; treat its output as authoritative for next-session injection.
- Do not write new substrate-level rules into MEMORY.md — those still go to `SKILL.md` + gbrain timeline per AMENDMENT-005 and RULE ZERO.

## Compounding

Referenced from:
- `pages/skills/karpathy-loop/SKILL.md` (absorbs_laws)
- `pages/skills/session-operating-contract/SKILL.md` (absorbs_laws)
- `pages/specs/SPEC-B-ALPHA-PRE-EDIT-COMPLIANCE-HOOK-V1-2026-04-18.md`
- `pages/specs/SPEC-SESSION-47-V1-2026-04-18.md`
- `pages/mercury/` (Mercury Phase 1/2/3 doctrine)

## Timeline

- **2026-04-18** | Conceived during session 47 brainstorm (`SPEC-SESSION-47-V1`). MEMORY.md was already used informally; this amendment formalized it as substrate.
- **2026-04-29** | Mercury Phase 3 LIVE — `MEMORY-mercury.md` token-reduced curated subset replaces raw injection.
- **2026-04-30** (s104) | Created proper AMENDMENT-006 page during AUDIT-LIBRARY-CROSSREFS-2026-04-30 to close 5 Tier-A1 broken wikilinks pointing at `[[AMENDMENT-006-auto-memory-session-continuity-substrate]]` and `[[AMD-006-...]]`. No new LESSON file (RULE ZERO).
