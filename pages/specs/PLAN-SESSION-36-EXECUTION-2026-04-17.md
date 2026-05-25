---
id: PLAN-SESSION-36-EXECUTION-2026-04-17
type: spec
title: "Session 36 Execution Plan — Atomic Audit + Root-Cause Fixes + Handoff"
status: in-progress
date: 2026-04-17
last_updated: 2026-04-17
owner: claude-code-mac
related:
  - SPEC-SESSION-36-ATOMIC-AUDIT-2026-04-17
  - LAW-015
  - LAW-016
  - AMD-005
  - CLAUDE.md#RULE-ZERO
tags: [plan, session-36, atomic-audit, root-cause, karpathy, 100-percent-bar]
---

# Session 36 — Execution Plan (Mac Pro, 2026-04-17)

**Goal:** Root-cause every anomaly surfaced today (Telegram flap alerts, LESSON-130 hook concern, morning update items), absorb the 11 UNMATCHED dream-cycle lessons into skills, run the 11-check atomic audit, and either finish at 100% or stop and write a clean handoff for session 37. No cheating, no papering over.

**Architecture principle:** RULE ZERO (Tan/Karpathy/Finn). Every rule lands in `pages/skills/<skill>/SKILL.md` + a `mcp__gbrain__add_timeline_entry`. **Zero new `LESSON-NNN-*.md` files** — the pre-commit hook enforces this physically.

**Tech stack:** git + pre-commit hook, gbrain MCP (`mcp__gbrain__*`), QMD (`mcp__nous-wiki-qmd__*`), Obsidian vault, launchd on Air, Docker (OpenClaw), LiteLLM, Tailscale SSH.

---

## Phase 0 — Pre-flight gates (MANDATORY, from CLAUDE.md)

- [ ] **G-1** Website lock: `curl satory.nousagaas.com` → `index-BSiWURaO.js` expected
- [ ] **G-2** No `code/satory/` trap directory in vault
- [ ] **G-3** Memory symlink intact (`~/.claude/.../memory` → `pages/progress/claude-memory/`)
- [ ] **G-4** Air SSH reachability via Tailscale (`ssh air hostname`); if DOWN → Phase 2 deploy items route through VPS (not blocker for most of plan, but flag in handoff)

Any gate red → STOP and fix before proceeding.

---

## Phase 1 — Root-cause: LESSON-130 hook concern (from commit-review-2026-04-17)

**Hypothesis (evidence from git + MEMORY.md):** LESSON-130 was created at 21:58 on 2026-04-16 and deleted at 22:03 — **both events during session 35 itself**. Session-35 memory says "LESSON-130 created and immediately retired (after Madi correction). Rule moved to mistake-to-skill v1.3.0 AP-7." Phase B of session 35 (pre-commit hook deploy) happened LATER in the same session. So the 21:58 commit landed BEFORE the hook existed — a timing artifact, not a hook bypass.

- [ ] **1.1** Confirm hook install timestamp vs LESSON-130 commit: `stat .git/hooks/pre-commit` vs `git log -1 --format=%ai 656f4024`. If hook mtime > commit time → timing confirmed.
- [ ] **1.2** Verify hook still works NOW: create `pages/lessons/individual/LESSON-131-dummy.md`, `git add`, `git commit` → expect exit 1 with "LESSON-file rule" block. Clean up dummy (unstage + delete).
- [ ] **1.3** Verify auto-sync (`nous-obsidian-sync.sh`) does NOT use `--no-verify`: grep script → no matches (already confirmed via Grep: no matches).
- [ ] **1.4** **Decision point:**
  - If timing confirmed (expected) → no bug. Update `commit-review-2026-04-17.md` with "RESOLVED: timing artifact, not a bypass. Hook verified live."
  - If hook actually bypassable → **stop everything**, update `infrastructure` skill with new AP (hook bypass vector), bump version, gbrain timeline, fix at source.
- [ ] **1.5** Commit commit-review update.

## Phase 2 — Deploy light-probe.sh fix to Air (silences ZAI flap noise)

The Telegram state-change alerts the user saw (04-16 23:47 / 04-17 00:03) are exactly the noise session 35's `KNOWN_FLAPPING_MODELS=zai/glm-4.5-flash` fix suppresses. Fix is on Mac wiki at `tools/light-probe.sh` but NOT YET deployed to Air.

- [ ] **2.1** Pre-flight: `ssh air echo OK`. If FAIL → document in handoff, skip to Phase 3. If OK → proceed.
- [ ] **2.2** Compare Mac `tools/light-probe.sh` vs Air `~/nous-agaas/tools/light-probe.sh`: `md5`. If differ → rsync.
- [ ] **2.3** Run 6 unit tests that session 35 added: `bash tools/test_light_probe.sh` (or equivalent). All 6 must PASS.
- [ ] **2.4** Deploy to Air (rsync or git pull + sync script).
- [ ] **2.5** Verify launchd `com.nous.light-probe` on Air picks up new script (unload/load cycle if needed).
- [ ] **2.6** Observe next 2 probe cycles via `tail -f /tmp/light-probe.log` (on Air) — confirm flap events do NOT page Telegram anymore.
- [ ] **2.7** Append to `pages/skills/infrastructure/SKILL.md` Timeline: "2026-04-17 | v2.20.0 deployed to Air runtime. Flap alert suppressed."
- [ ] **2.8** gbrain: `mcp__gbrain__add_timeline_entry slug=pages/skills/infrastructure/skill date=2026-04-17 summary="light-probe.sh v2.20.0 deployed to Air; flap alerts suppressed"`
- [ ] **2.9** Commit.

## Phase 3 — Morning update items (2026-04-17 05:07 Almaty)

- [ ] **3.1** Claude Code CLI version check: local `claude --version`. If `2.1.71` → check upstream latest via `npm view @anthropic-ai/claude-code version` (or `gh release view --repo anthropics/claude-code`). If new version exists → attempt install (`npm i -g @anthropic-ai/claude-code@latest`) and verify version bump. If install still fails → root-cause (permissions? nvm? PATH?) and document in `pages/skills/infrastructure/SKILL.md` (new AP if non-obvious).
- [ ] **3.2** OpenClaw `:latest` differs check: compare digest of `:latest` on dockerhub/registry vs current Air deployment. `infrastructure/SKILL.md` AP-4 says this is RISKY auto-apply — do NOT auto-apply. Document current `:latest` digest, current-deployed digest, and the delta (changelog if available) in `pages/progress/openclaw-update-review-2026-04-17.md`. Leave decision to Madi.
- [ ] **3.3** Commit if any files touched.

## Phase 4 — Absorb 11 UNMATCHED dream-cycle lessons

From `pages/dashboards/dream-cycle-proposals-2026-04-17.md`: LESSON-011, 016, 018, 021, 024, 029, 032, 042, 049, 053, 074.

For **each** lesson:

- [ ] **4.x.1** Read lesson body (`pages/lessons/individual/LESSON-NNN-*.md`)
- [ ] **4.x.2** Pick target skill: search gbrain for topic + check `pages/skills/_gbrain/RESOLVER.md`. If no fit → create a new skill + register.
- [ ] **4.x.3** Add rule to target `SKILL.md` (new AP / new rule under "Current rules"). Bump version. Append `LESSON-NNN` to `absorbs_lessons:` frontmatter list. Append `## Timeline` entry.
- [ ] **4.x.4** Update lesson frontmatter: `status: absorbed`, `absorbed_into: <skill-slug>`, `absorbed_on: 2026-04-17`. **DO NOT delete or rename** (hook drift-scan will fire on ID/title/H1 mismatches).
- [ ] **4.x.5** `mcp__gbrain__add_timeline_entry` on the skill page.
- [ ] **4.x.6** Commit skill + lesson-frontmatter edits together with message `skill: <name> vX.Y.Z — absorb LESSON-NNN`.

**Acceptance:** at end of Phase 4, all 11 lessons have `status: absorbed` AND a grep for the absorbed rule in target skill succeeds. Zero new LESSON files created.

## Phase 5 — Atomic Phase-A verification (11 checks from SPEC-SESSION-36)

- [ ] **5.1** Git sync — 3 wiki repos (Mac / VPS / Air if reachable) same HEAD commit
- [ ] **5.2** Skill MD5 parity — 18 domain skills × 4 locations (Mac wiki, VPS wiki, Air wiki, Air runtime `/opt/nous-agaas/skills/`). MD5 identical.
- [ ] **5.3** gbrain DB ↔ filesystem — page count vs `find pages -name '*.md' | wc -l`; spot-check 5 random skills — `content_hash` matches file SHA-256
- [ ] **5.4** QMD — 412 docs, `needsEmbedding=0`, `hasVectorIndex=true`
- [ ] **5.5** launchd on Air — 17 jobs, last exit 0, last-fire within cadence window
- [ ] **5.6** Service health — OpenClaw `:18789/health`, LiteLLM `:4000/health`, Telegram poller last-success < 180s
- [ ] **5.7** Pre-commit hook parity — sha256 of `.git/hooks/pre-commit` identical across Mac/VPS/Air wiki repos
- [ ] **5.8** RESOLVER.md — every `pages/skills/<skill>/` listed; `_gbrain/` listed
- [ ] **5.9** Context injector output contains RULE ZERO phrase + "SKILL.md + gbrain timeline"
- [ ] **5.10** Mac memory symlink — `~/.claude/.../memory/` → `pages/progress/claude-memory/`
- [ ] **5.11** Dream cycle — `pages/dashboards/dream-cycle-proposals-2026-04-17` present in gbrain AND QMD

Any FAIL → Phase 6.

## Phase 6 — Root-cause fix each Phase-5 fail

Follow mistake-to-skill P1 protocol for every fail:
1. Diagnose root cause (not symptom)
2. Fix at source
3. Re-run the Phase-5 check — must PASS
4. Update responsible `pages/skills/<skill>/SKILL.md` (new AP or rule under "Current rules"), bump minor version, append Timeline entry
5. `mcp__gbrain__add_timeline_entry` on skill page
6. **DO NOT** create `pages/lessons/individual/LESSON-*.md`

## Phase 7 — MEMORY.md drift correction

Memory is now ahead of filesystem in a few places (gbrain pages 948 → 956, embed 100%→99.5%, etc.). Correct numbers to current reality and note session-36 changes.

- [ ] **7.1** Update gbrain stats line (pages 956, chunks 2072, embed 99.5%)
- [ ] **7.2** Add "Session 36 (2026-04-17)" section summarizing all phases actually completed
- [ ] **7.3** Update skill version table if Phase 4 absorption bumped any skills

## Phase 8 — Handoff + sync everywhere

- [ ] **8.1** Write `pages/progress/HANDOFF-AUTO-2026-04-17-session-36.md`: phases completed, phases partial, open blockers, exact resume commands for session 37
- [ ] **8.2** `git add -A && git commit` — trigger auto-sync cycle
- [ ] **8.3** Verify sync reached VPS: `ssh root@65.108.215.200 "cd /root/nous-agaas/wiki && git log -1 --oneline"` = local HEAD
- [ ] **8.4** Verify sync reached Air (if reachable): same check on Air
- [ ] **8.5** gbrain pickup: `mcp__gbrain__get_page slug=pages/progress/handoff-auto-2026-04-17-session-36` returns the new file
- [ ] **8.6** If any phase <100% → mark it in the handoff's "blockers" section with exact next steps. **Do not claim "done" for partial phases.**

## Quality Bar (non-negotiable)

- 100% on every check or explicit "DEFERRED — reason: X, resumes session 37" in handoff
- Every rule learned lands in SKILL.md + gbrain timeline (never LESSON-NNN)
- Zero new `LESSON-NNN-*.md` files (enforced by hook; verify with dummy in Phase 1.2)
- Every substantive change synced to Mac + VPS + Air + gbrain before "done"

## See also

- [[SPEC-SESSION-36-ATOMIC-AUDIT-2026-04-17]] — the audit checklist this plan executes
- [[LAW-015-root-cause-evolution]] — root-cause discipline
- [[AMD-005-skill-first-evolution]] — session-35 amended: no new LESSON files
- [[CLAUDE.md#RULE-ZERO]] — Tan/Karpathy pattern
