---
type: spec
id: SPEC-SESSION-54-DEEP-AUDIT-J2-OPUS47-2026-04-20
title: "Session-54 design — deep-dive audit + J2 OpenClaw→Opus-4.7 execution"
tags: [spec, session-54, deep-audit, j2, opus-4.7, factory-ops, ap-25, 2026-04-20]
date: 2026-04-20
source_count: 6
status: draft
last_updated: 2026-04-20
related:
  - HANDOFF-AUTO-2026-04-20-session-51-MASTER-final
  - HANDOFF-AUTO-2026-04-20-session-52-MASTER-close-satory-meeting
  - session-operating-contract
  - factory-ops
  - audit
  - mistake-to-skill
---

# Session-54 — Deep-dive audit + J2 OpenClaw→Opus-4.7 execution

## 1. Context

Three sessions closed 2026-04-20 (51 Mac-interactive infra, 52 Nous-GPU + Satory meeting absorption, 53 Netvision letter drafting in parallel). SOAO at session-54 open = GOLDEN at 4-way HEAD `623a30e9`, gbrain 90/100 zero-missing-embeddings, 129 LESSONs frozen. Session-operating-contract v1.4.0 is runtime doctrine.

User directive at session open: *"use your superskills first to plan all, then do 1 by 1, quality matters 100% or stop… all must be saved and sync to everywhere… deep dive audit so nothing is missing… no lie, no bs, no cheating… think like Musk + Karpathy + Tan + billion-dollar-solopreneur."*

Musk step-2 applied on the initial plan: new "meta-standard skill" DELETED (AP-1 risk — SOC v1.4.0 already codifies the standard in Rule 9 + Rule 10 + RULE ZERO). J3/J4 DELETED from scope (only execute if J2 leaves budget — no half-finished work). What remains compounds.

## 2. Scope

**In scope (this session):**
- Phase 1: Deep-dive audit — four concrete probes beyond SOAO.
- Phase 2: Gap closure — each finding absorbed into the relevant `SKILL.md` via RULE ZERO 3-edit ritual + gbrain timeline entry.
- Phase 3: J2 — `factory-ops` AP-25 5-task research path to unblock OpenClaw factory-agent → Opus 4.7 (LiteLLM `opus` alias already verified shippable; factory layer reverts after `docker restart`).
- Phase 4: Absorption (bump `factory-ops` v1.8 on success / v1.7.1 on honest-dead-end) + MASTER handoff + MEMORY top-block prepend + 4-way push.

**Out of scope (explicit, Musk step-2):**
- Any new meta-skill ("billion-dollar-solopreneur-operating-model" or similar). SOC v1.4.0 is sufficient. AP-1 tripwire active.
- J3 (MCP wiring gbrain + wiki-qmd → OpenClaw). Only if Phase 3 lands with >45min budget remaining.
- J4 (live E2E Telegram `/ask` semantic-search-requiring query). Same gate as J3.
- Phase-0 Satory camera displacement execution — externally blocked on Denis's 4 answers.
- Nous-GPU Tailscale ACL work — externally blocked on Asyl or Madi click.
- Any new LESSON file (RULE ZERO; hook rejects).

## 3. Phase 1 — Deep-dive audit (four probes)

Each probe has: input, check, pass-condition, fail→action. Run sequentially; pass → continue, fail → log finding for Phase 2.

### 3.1 Probe A — gbrain ingestion of session-52/53 new pages
**Input:** 9 new Wave-B entity pages (vlad, azamat-bdl, cerebro, roman-cerebro, madi-program + updates to denis, daniyar, nous-gpu) + session-53 artifacts (netvision-remediation-plan, netvision-monitoring-whitelabel-analysis v2, letter-to-saken-aga-netvision-v3).

**Check:** `mcp__gbrain__get_page slug=pages/entities/<slug>` for each; `mcp__gbrain__get_page slug=pages/specs/<slug>` for the three session-53 artifacts. Confirm each returns `{ok: true}` with `last_updated: 2026-04-20`.

**Pass condition:** all 12 pages indexed with 2026-04-20 timestamp and non-empty content_hash.

**Fail → action:** record missing pages in Phase-2 gap list. Candidate root cause: autopilot 5-min cycle did not pick up a commit, or page missing from commit entirely.

### 3.2 Probe B — Mac-root CLAUDE.md ↔ vault CLAUDE.md drift
**Input:** `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` (Mac-root, NOT vault-synced — read by Claude Code at session open) vs `/Users/madia/Documents/Projects/Nous AGaaS/Nous/CLAUDE.md` (vault root, synced 4-way).

**Check:** initial `diff` already confirms they diverge structurally — Mac-root has the full rule-zero + hard-rules + architecture-quickref + telegram-routing-model + SOC-reference block; vault-root is the wiki-schema doc. This is BY DESIGN (Mac-root = runtime agent instruction; vault-root = wiki-schema for human + agent nav). **But** session-51's HARD RULE 1 narrowing (Telegram MCP token-specific) + session-52's Nous-GPU row + session-53's routing-model update live in Mac-root only and MUST reach the vault for agent-continuity across hosts (Air factory-agent reads vault-root, not Mac-root).

**Pass condition:** vault has an architecture-quickref + hard-rules snapshot that any Air-side agent can read to know the same operational truth Mac-side Claude Code knows.

**Fail → action:** extract Mac-root operational content (hard rules, architecture quickref, telegram routing model, SOC reference) into a new vault page `pages/systems/architecture-quickref.md` referenced from BOTH `CLAUDE.md` files. Log as Phase-2 skill bump candidate on `infrastructure` or `session-operating-contract`.

### 3.3 Probe C — MEMORY.md bloat + topic-file extraction
**Input:** `/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md` currently 1747 lines / 220KB. System reminder at session open: *"WARNING: MEMORY.md is 1736 lines and 220.7KB. Only part of it was loaded. Keep index entries to one line under ~200 chars; move detail into topic files."*

**Check:** count lines, measure bytes, enumerate top-block sizes.

**Pass condition:** MEMORY.md ≤ 400 lines, each index entry ≤ 200 chars, detailed session blocks moved to `memory/sessions/session-NN-YYYY-MM-DD.md` topic files.

**Fail → action:** extract session-51 + session-52 Wave A + session-52 Wave B top-blocks into three topic files under `memory/sessions/`; replace in-MEMORY with one-line pointers. Bump `auto-memory` skill (if exists) or absorb into SOC as AP for index-vs-detail discipline.

### 3.4 Probe D — Cross-session skill-version race (SOC v1.3 / v1.4 merge consistency)
**Input:** session-operating-contract current file (Mac + Air + VPS-bare + VPS-wiki). Evidence trail shows v1.4 (Rule 7 narrowing, Mac-interactive session-51 track) and v1.3 (Rule 13 outbound, session-53 business-dev track) both dated 2026-04-20. v1.4 must include Rule 13 content (v1.4 is later chronologically), or we have a lost-update.

**Check:** grep `version:` in SKILL.md frontmatter (expect `1.4.0`), grep `Rule 13` section (must exist), grep both `v1.3.0 — Session 53` and `v1.4.0 — Session 51` in Evidence trail (must both exist — v1.4 does NOT rescind v1.3).

**Pass condition:** SKILL.md contains Rule 13 section AND Rules 11/12 AND all three v1.1/v1.2/v1.3/v1.4 entries in Evidence trail.

**Fail → action:** the later bump overwrote the earlier. Manually merge using git log to recover both sets of content. Bump to v1.5.0 with consolidation note. Absorb the merge-race failure mode into `mistake-to-skill` AP-11 (3-edit ritual already exists; add "check for concurrent bump before editing" clause).

## 4. Phase 2 — Gap closure (RULE ZERO)

For each finding in Phase 1:
1. Identify the correct skill (existing first; `infrastructure` / `session-operating-contract` / `auto-memory` / `mistake-to-skill` / `audit` are likely targets).
2. Apply 3-edit ritual from `mistake-to-skill` AP-11: frontmatter `version:` bump + H1 version bump + `## Evidence trail` entry.
3. Add the rule itself as a new AP or extend existing AP.
4. Push `mcp__gbrain__add_timeline_entry slug=pages/skills/<skill>/skill date=2026-04-20 summary="…"`.
5. Commit with explicit REQ-mapping if product, or `[risk] [infrastructure]` tag if infra (per SOC Rule 12 / AP-3).
6. 4-way push (`git push` → VPS bare, then Air + VPS-wiki pull, then Air `wiki-to-runtime-rsync`).

**No new LESSON file under any circumstance.**

## 5. Phase 3 — J2 execution (factory-ops AP-25 5-task path)

Per [[HANDOFF-AUTO-2026-04-20-session-51-MASTER-final]] and `factory-ops` AP-25 v1.7. Factory (OpenClaw) agent-layer switch from `litellm/glm-5.1` to `litellm/opus` did NOT stick after `docker restart` — 2 round-trips of `openclaw.json` + `sessions.json` edits reverted. Hypothesis: `--allow-unconfigured` launch flag triggers bootstrap-from-defaults, regenerating config from code-embedded defaults.

Execute the 5 tasks in order; stop at the first one that unblocks.

### 5.1 Task J2-a — OpenClaw internal docs
`docker exec openclaw ls /app/docs/`; read any `agent-config`, `model-override`, `reconfigure`, or `cli` docs found. Look for the canonical procedure to change a running factory's model target.

### 5.2 Task J2-b — CLI help
`docker exec openclaw node openclaw.mjs --help` + `docker exec openclaw node openclaw.mjs agent --help`. Look for `--set-model`, `--reconfigure`, or model-override flags exposed at the CLI.

### 5.3 Task J2-c — Gateway HTTP API probe
Read `openclaw.json` for `gateway.auth.token`. `curl http://localhost:<port>/api/agents/<id>/model -X PATCH -H "Authorization: Bearer <token>" -d '{"model":"litellm/opus"}'` (exact path TBD from J2-a/b or from grep of OpenClaw source). A management API that edits config WITHOUT `docker restart` would survive the bootstrap-from-defaults issue.

### 5.4 Task J2-d — Source-level env-var grep
`docker exec openclaw grep -r "process.env.OPENCLAW_" /app/src/ 2>/dev/null` + `docker exec openclaw grep -r "DEFAULT_MODEL\|defaultModel" /app/src/`. Identify env-var knobs that override code-embedded defaults, if any. Env vars survive `docker restart` (set in container environment).

### 5.5 Task J2-e — Non-`--allow-unconfigured` launch
Last resort. Inspect Air `launchctl` / `docker-compose.yml` for the OpenClaw launch command. Remove `--allow-unconfigured` flag, relaunch container, see if the edits to `openclaw.json` + `sessions.json` now persist across restart. **Pre-condition:** must be safe to restart factory mid-session; if any active `/ask` traffic, schedule for off-hours.

### 5.6 J2 success criteria
Telegram `/ask` through factory returns a response where the model trace shows `opus` (or Anthropic Opus-4.7 marker). Verify via:
1. Send `/ask what model are you?` via `tools/tg_send.sh` OR direct `curl localhost:18789/chat`.
2. Read Air `/var/log/openclaw/*.log` or `docker logs openclaw --tail 100` for the model attribution line.
3. Screenshot or paste the attribution line into the DONE-protocol output.

### 5.7 J2 failure criteria (honest-dead-end)
After all 5 tasks exhausted, if factory still reverts on restart AND no management API path exists AND no env-var override works: document the hypothesis that was disproved, log the observed behavior in `factory-ops` v1.7.1 Evidence trail, flag the upstream OpenClaw design choice as an Open Question, and propose two forward paths for a later session: (a) fork + patch OpenClaw to respect `openclaw.json` model override, (b) route `/ask` through LiteLLM directly, bypassing factory-agent model selection.

## 6. Phase 4 — Absorption + handoff

Regardless of J2 outcome:
1. Bump `factory-ops` to v1.8 (success) or v1.7.1 (honest-dead-end) per AP-11 3-edit ritual.
2. Push gbrain timeline entry.
3. Write MASTER handoff `pages/progress/HANDOFF-AUTO-2026-04-20-session-54-MASTER-*.md` with:
   - Phase-1 audit findings table (probe / result / action taken)
   - Phase-2 gap-closure list (skill / AP / version-bump / gbrain-push confirmation)
   - Phase-3 J2 outcome (shipped + DONE-protocol artifacts OR honest-dead-end with forward paths)
   - Karpathy scorecard (6 axes from prior sessions' MEMORY blocks)
   - Open questions for session-55
4. MEMORY top-block prepend per AMD-006 Rule 2 — pointer-only, detail in handoff (AP from Probe C).
5. 4-way push + verify HEAD parity across Mac + Air + VPS-bare + VPS-wiki.

## 7. DONE protocol — applied at each phase boundary

Per SOC v1.4.0 Rule 4, type `done/complete/fixed/deployed/ready/готово` ONLY when all four artifacts are in the same message:
- Exact command run (literal, not paraphrased).
- Exact output (truncated only if >50 lines; first + last 10 lines shown).
- Git state: `git rev-parse --short HEAD` + `git status --porcelain`.
- One counter-check actually run, and what happened.

Missing any → write `verified: X. unverified: Y. next: <exact-command>` instead. No exceptions.

## 8. Non-goals (explicit delete list)

- New meta-skill for "billion-dollar-solopreneur-standard" — AP-1 risk, SOC v1.4.0 sufficient.
- J3 MCP wiring, J4 live E2E — only if Phase-3 leaves >45min.
- Phase-0 Satory camera work — externally blocked.
- Tailscale ACL for Nous-GPU — externally blocked.
- Any LESSON-130+ file — RULE ZERO + hook reject.
- Cosmetic refactors beyond what each probe's fix directly requires.

## 9. Success criteria (what "100% done" means for this session)

1. **Phase 1** — all 4 probes executed; findings table committed in handoff.
2. **Phase 2** — every Phase-1 finding has a corresponding skill bump + gbrain timeline entry + 4-way sync confirmation.
3. **Phase 3** — J2 either lands with DONE-protocol proof of Opus-4.7 at factory layer, OR honest-dead-end documented with forward paths in `factory-ops` v1.7.1.
4. **Phase 4** — MASTER handoff committed + 4-way pushed; MEMORY top-block prepended; skillsSnapshot verified.
5. **Zero new LESSON files. Zero persona cosplay. Zero "done" without 4-artifact proof.**

## 10. Open questions (dogfooded per pending open-questions doctrine)

- `[open-question]` Will Probe D reveal a lost-update on SOC, or is the merge already clean? If lost-update, the fix adds new anti-pattern to `mistake-to-skill` for concurrent bump detection.
- `[open-question]` Does J2 have a path to resolution in a single session, or will all 5 tasks in 5.x run to exhaustion? Budget: 90min cap before honest-dead-end.
- `[weak-edge]` Probe C's target of ≤400 lines for MEMORY.md is arbitrary — could be 300, could be 500. Acceptance: whatever number makes the index readable in one terminal screen.
- `[dependency-risk]` J2-e (non-`--allow-unconfigured` launch) restarts factory; if any active `/ask` traffic, blocks on off-hours. Mitigation: check `docker logs` for recent traffic before relaunch.
- `[model-drift]` Assumption that LiteLLM `opus` alias still resolves to Opus-4.7 — verify at J2 time (session 51 shipped this but config could drift).

## See also

- [[HANDOFF-AUTO-2026-04-20-session-51-MASTER-final]]
- [[HANDOFF-AUTO-2026-04-20-session-52-MASTER-close-satory-meeting]]
- [[session-operating-contract]] — v1.4.0 is runtime doctrine
- [[factory-ops]] — AP-25 5-task path source
- [[audit]] — AP-14/AP-15/AP-20 patterns applied
- [[mistake-to-skill]] — AP-11 3-edit ritual used on every Phase-2 bump
- [[infrastructure]] — AP-43 pre-commit RULE 4 enforces AP-11
