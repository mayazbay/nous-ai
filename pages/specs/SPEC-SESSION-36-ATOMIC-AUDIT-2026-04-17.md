---
id: SPEC-SESSION-36-ATOMIC-AUDIT-2026-04-17
type: spec
title: "Session 36 Atomic Audit + 11 UNMATCHED Lesson Absorption"
status: in-progress
date: 2026-04-17
last_updated: 2026-04-17
owner: claude-code
related:
  - SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15
  - LAW-015
  - CLAUDE.md#RULE-ZERO
tags: [audit, session-36, karpathy, atomic, skill-absorption]
---

# Session 36 — Atomic Audit + 11 UNMATCHED Lesson Absorption

**Goal:** Verify the 4-location skill runtime parity, gbrain ↔ wiki ↔ QMD consistency, and Air-side service health is bulletproof. Root-cause fix anything flagged. Absorb the **11 UNMATCHED lessons** from the 2026-04-17 dream cycle into their target skills — **no new LESSON files** (RULE ZERO). *(Earlier conversation said "10" — recount of dream cycle UNMATCHED entries is 11. Honest correction.)*

**Quality bar:** 100% or handoff. If any phase finishes at <100%, stop and document exact state in the handoff. No papering over.

---

## Phase A — Atomic verification (read-only, 11 checks)

| # | Check | Pass criterion |
|---|-------|----------------|
| 1 | Git sync | All 3 wiki repos (Mac / VPS / Air) at same commit hash |
| 2 | Skill MD5 parity | 18 domain skills × 4 locations (Mac wiki, VPS wiki, Air wiki, Air runtime `/opt/nous-agaas/skills/`) — MD5 identical |
| 3 | gbrain DB ↔ filesystem | Page count matches `.md` count; spot-check 5 random skills — `content_hash` matches file SHA-256 |
| 4 | QMD | 412/412 documents, `needsEmbedding=0`, `hasVectorIndex=true` |
| 5 | launchd on Air | 17 jobs, last exit 0, last-fire within cadence window |
| 6 | Service health | OpenClaw `:18789/health`, LiteLLM `:4000/health`, Telegram poller last-success-ts < 180s |
| 7 | Pre-commit hook parity | sha256 of `.git/hooks/pre-commit` identical across 3 wiki repos |
| 8 | RESOLVER.md | Every skill under `pages/skills/` is listed; `_gbrain` listed |
| 9 | Context injector | Output contains session-35 RULE ZERO phrase + "SKILL.md + gbrain timeline" |
| 10 | Mac memory symlink | `~/.claude/projects/.../memory/` resolves into `pages/progress/claude-memory/` |
| 11 | Dream cycle | `pages/dashboards/dream-cycle-proposals-2026-04-17` present in gbrain + QMD |

Any FAIL → Phase B.

## Phase B — Root-cause fixes

For every Phase-A fail:
1. Diagnose root cause (not just symptom)
2. Fix at source
3. Re-run the Phase-A check — must now PASS
4. Update the responsible `pages/skills/<skill>/SKILL.md` (new AP or rule under "Current rules"), bump minor version, append `## Timeline` entry
5. `mcp__gbrain__add_timeline_entry` on the skill page
6. **DO NOT** create `pages/lessons/individual/LESSON-*.md` (RULE ZERO / pre-commit-enforced)

## Phase C — Absorb 11 UNMATCHED lessons

From `pages/dashboards/dream-cycle-proposals-2026-04-17` (dream cycle, 2026-04-17 03:15 UTC+05):

LESSON-011, 016, 018, 021, 024, 029, 032, 042, 049, 053, 074 — all 11 UNMATCHED entries. Each requires manual skill matching since the auto-matcher couldn't route them. Skip any whose frontmatter shows `absorbed_into:` already set (dream cycle was a READ-ONLY pass — should be none, but verify).

For each:
1. Read lesson body
2. Pick target skill — match to existing 18 domain skills OR create new skill (register in `pages/skills/_gbrain/RESOLVER.md`)
3. Add the rule as an Anti-Pattern (AP-N) or phase bullet in the target SKILL.md
4. Bump minor version (`1.4.0 → 1.5.0`)
5. Append `## Timeline` entry
6. `mcp__gbrain__add_timeline_entry  slug=pages/skills/<skill>/skill  date=2026-04-17  summary="absorbed LESSON-NNN: …"`
7. Edit the lesson's frontmatter: `absorbed_into: <skill>` + `absorbed_date: 2026-04-17`

## Phase D — Sync to 4 locations

Per skill change:
1. Commit on Mac (co-author: Claude Opus 4.7)
2. Push to VPS bare (`65.108.215.200:/root/nous-agaas/obsidian-wiki.git`)
3. Verify Air wiki pulled (auto-sync is 5-min; force-pull if needed)
4. `rsync` skills → Air runtime `/opt/nous-agaas/skills/<skill>/SKILL.md`
5. Verify OpenClaw bind-mount sees latest (`docker exec openclaw cat /opt/nous-agaas/skills/<skill>/SKILL.md | head -3` shows new version)

Final: re-run Phase-A checks #1, #2, #7, #8 — must all PASS.

## Phase E — Declare or handoff

- 100% all phases → write `HANDOFF-AUTO-2026-04-17-session-36.md` with evidence for each check + update MEMORY.md session 36 block
- <100% any item → STOP. Write handoff describing *exactly* what's broken and what's the next step. No fake green.

## Non-goals

- Not creating LESSON-130+ (RULE ZERO, pre-commit enforced)
- Not absorbing the 13 auto-matched lessons (deferred to next dream cycle)
- Not touching `satory.nousagaas.com` (LAW-016 locked)
- Not using Telegram MCP tools in this Claude Code session (HARD RULE 1)
- Not amending commits — every new rule is a NEW commit

## Success evidence required

- [ ] Spec committed (this file)
- [ ] Phase A results table filled (11 PASS/FAIL)
- [ ] Phase B fixes: diagnosis + fix + re-verify + skill version bump + gbrain timeline
- [ ] Phase C: 11 skill commits, 11 gbrain timeline entries, 11 lessons marked absorbed (or fewer, with root-cause explanation if any lesson can't fit any skill and requires a new skill instead)
- [ ] Phase D: final parity re-verify PASSES across 4 locations
- [ ] Phase E: handoff written + MEMORY.md updated + synced VPS
