---
type: spec
id: SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15
title: "SPEC: GOD_PROMPT v1.0 — Evolution Loop Architecture for Nous AGaaS Factory"
tags: [spec, god-prompt, architecture, evolution, skills, gbrain, karpathy, garry-tan, openclaw, bulletproof, 2026-04-15]
date: 2026-04-15
source_count: 0
status: draft
last_updated: 2026-04-15
related: [nous-ai, openclaw, gbrain-garrytan, skills-not-agents, agent-harness-ownership, hybrid-model-routing, LAW-005-obsidian-master, LAW-015-root-cause-evolution, LESSON-079-one-agent-not-sixteen, LESSON-095-gbrain-0.4.1-to-0.10.1-upgrade, LESSON-103-satory-dashboard-lies-when-data-stale, LESSON-104-litellm-router-dual-provider-cooldown-crash, HANDOFF-2026-04-11-architecture-audit]
author: "Madi Ayazbay + Claude Code session 26"
version: 1.0
---

# GOD_PROMPT v1.0 — Evolution Loop Architecture

**Status:** Design spec awaiting Madi approval. Do not begin implementation until user reviews this file.

**One-sentence purpose:** Replace the current manual, lesson-heavy, system-prompt-less factory with an automated, skills-first, layered evolution loop aligned with Karpathy (System Prompt Learning), Garry Tan (gstack + GBrain), and Anthropic (Agent Skills Standard).

---

## The Problem We're Solving

Three real bugs confirmed by three parallel audits on 2026-04-15:

1. **Factory agent has no system prompt.** OpenClaw `nous` agent on Air has empty `SOUL.md`, `AGENTS.md`, `HEARTBEAT.md`. The agent reconstructs its identity from 21 KB of user-turn context on every task. This is why it sometimes hallucinates its own file paths.

2. **Lesson → skill → runtime is MANUAL.** CLAUDE.md Rule-6 is aspirational. No cron, no launchd, no git hook closes the loop. Madi rsyncs by hand. Latency: minutes to days. ~30 lessons out of 121 currently unabsorbed.

3. **Lesson-heavy, skill-light architecture.** Research consensus (Karpathy, Tan, Anthropic, NASA lessons-DB, Mem^p 2025) says **skills are the evolution substrate, lessons are the audit trail**. Our current ratio (121 lessons / 10 skills) is inverted.

## The Research Consensus (2026)

| Source | Principle |
|---|---|
| Karpathy "System Prompt Learning" (Oct 2025 X) | "A large section of the LLM system prompt could be written via system prompt learning — the LLM writing a book for itself on how to solve problems." |
| Karpathy LLM Wiki (Apr 2026) | Markdown wiki compiled by the LLM; no RAG. "You rarely ever write or edit the wiki manually; it's the domain of the LLM." |
| Garry Tan gstack (71.6K stars) | "Without a process, ten agents is ten sources of chaos. With a process — think, plan, build, review, test, ship — each agent knows exactly what to do and when to stop." |
| Garry Tan GBrain (14,700 files, Apr 2026) | Three layers: Git brain repo (canonical) + PostgreSQL/pgvector (search) + MCP skills (tools). Compiled truth above separator, append-only evidence below. |
| Anthropic Agent Skills (26+ platforms, Dec 2025) | Three-level progressive disclosure: metadata (~100 tokens) → SKILL.md body (<500 lines) → bundled resources. "Keep the prompt lean." |
| Mem^p (Zhejiang / Alibaba 2025) | Procedural memory transfers from stronger to weaker models. Skills generalize across Opus→Sonnet→GLM-5.1. |
| NASA lessons-DB (2001 GAO) | Useful <25% of the time. 58% couldn't retrieve the right lesson. JPL fix: embed lessons into executable design principles. |

**Convergent truth: knowledge that tells an agent *what to do step-by-step* compounds; knowledge that tells an agent *what to remember* decays.**

---

## Target Architecture — 6 Layers

```
╔══════════════════════════════════════════════════════════════════════╗
║ LAYER 1 — IDENTITY (SOUL.md convention)                              ║
║   Source: pages/systems/nous-agent-soul.md          [~50 lines]      ║
║   Runtime: /opt/nous-agaas/agents/SOUL.md           [auto-rsynced]   ║
║   Contents: who I am, hard limits, tone, escalation triggers.        ║
║   NO operational rules — those live in skills.                       ║
╠══════════════════════════════════════════════════════════════════════╣
║ LAYER 2 — PROCEDURE POINTER (AGENTS.md convention)                   ║
║   Source: pages/systems/nous-agent-procedures.md    [~150 lines]     ║
║   Runtime: /opt/nous-agaas/agents/AGENTS.md         [auto-rsynced]   ║
║   Contents: every-session checklist, intent routing via RESOLVER.md, ║
║   handoff protocol. Points at skills — never duplicates them.        ║
╠══════════════════════════════════════════════════════════════════════╣
║ LAYER 3 — SKILLS (fat, compiled-truth, <500 lines each)              ║
║   Source: pages/skills/<name>/SKILL.md (edit ONLY here)              ║
║   Runtime: /opt/nous-agaas/skills/<name>/SKILL.md   [auto-rsynced]   ║
║   Current: 10 active | Target: 15 at v1.0, 20-25 steady state        ║
║   Format: compiled-truth (## Current rules / ## Evidence trail)      ║
╠══════════════════════════════════════════════════════════════════════╣
║ LAYER 4 — CRON/SCHEDULE (HEARTBEAT.md convention)                    ║
║   Source: pages/systems/nous-agent-heartbeat.md     [~80 lines]      ║
║   Runtime: /opt/nous-agaas/agents/HEARTBEAT.md      [auto-rsynced]   ║
║   Contents: catalog of scheduled tasks + launchd mapping.            ║
║   Not loaded in hot path — reference doc only.                       ║
╠══════════════════════════════════════════════════════════════════════╣
║ LAYER 5 — KNOWLEDGE (unchanged — works)                              ║
║   Obsidian wiki: pages/entities/, pages/concepts/, pages/progress/   ║
║   gbrain v0.10.1: Postgres + pgvector, HNSW, autopilot every 5 min   ║
╠══════════════════════════════════════════════════════════════════════╣
║ LAYER 6 — AUDIT TRAIL (append-only, SLA-enforced)                    ║
║   pages/lessons/individual/LESSON-NNN-*.md (postmortems)             ║
║   pages/laws/LAW-*.md (constitutional constraints)                   ║
║   pages/progress/HANDOFF-*.md (session state)                        ║
║   NEW SLA: Unabsorbed lesson ≥7 days → Telegram alert.               ║
╚══════════════════════════════════════════════════════════════════════╝
```

**"Obsidian + gbrain + Karpathy evolving together"** means: every write lands in three places automatically — wiki (source), gbrain (index), runtime (agent). Zero manual rsync after rollout.

---

## Component Breakdown

### A. New wiki source files (Layers 1, 2, 4)

| File | Lines | Purpose |
|---|---|---|
| `pages/systems/nous-agent-soul.md` | ~50 | Identity — who nous is, hard limits, escalation triggers |
| `pages/systems/nous-agent-procedures.md` | ~150 | Procedural pointer — session checklist + RESOLVER routing |
| `pages/systems/nous-agent-heartbeat.md` | ~80 | Cron catalog (maps to Air launchd jobs) |

### B. New skills (5) — compiled-truth template

| Skill | Absorbs from GOD_PROMPT + research |
|---|---|
| `planning-discipline` | §1 Iron Laws + §2 Musk 5-step filter + §10 mental checklist. Triggers BEFORE any task. |
| `error-classification` | §7 (L0 noise, L1 self-heal, L2 root-cause, L3 architecture, L4 legal/gov) |
| `mistake-to-skill` | §4 Karpathy learning loop + Tan's `/review` pattern + JPL embed-into-procedures fix. Manual trigger: `/skill-capture`. |
| `kazakhstan-regulatory` | §9 KZ rules — МРП 4,325₸, Ст. 591-601, ERAP BIN, GOST 34.10-2015 |
| `evidence-verification` | §6 anti-slop + LESSON-103/104 data_freshness envelope + Anthropic superpowers:verification-before-completion |

### C. Existing skills extended (4) — version bumps

| Skill | Change | Version |
|---|---|---|
| `command-center` | Add rigid HANDOFF-AUTO format (§5) | 2.3.0 → 2.4.0 |
| `gbrain-ops` | Add dream cycle + compiled-truth template | 1.4.0 → 1.5.0 |
| `agent-quality` | Adopt compiled-truth template (reference implementation) | 1.1.0 → 1.2.0 |
| `audit` | Add `audit evolution` sub-audit | 1.1.0 → 1.2.0 |

### D. Compiled-truth template (universal skill format)

Every SKILL.md uses this structure (from GBrain convention):

```markdown
---
name: <skill-name>
description: <pushy description per Anthropic guidance — trigger words>
version: X.Y.Z
status: active
absorbs_lessons: [LESSON-NNN, LESSON-MMM]
absorbs_laws: [LAW-NNN]
---

# <Skill Name>

## Current rules (compiled truth — edit freely, bump version)

1. <rule> — why this matters
2. <rule> — ...

## Phases / procedures (what to do step-by-step)

### P1 — <phase name>
1. Step
2. Step

### P2 — ...

## Anti-patterns (AP-N)

### AP-1: <name>
What went wrong. How to avoid.

## Evidence trail (APPEND-ONLY — never delete, never edit)

- 2026-04-15 | LESSON-103 absorbed: rule #3 added after dashboard-lies-when-stale incident
- 2026-04-14 | LAW-002 absorbed: rule #1 added per Smatay directive
- ...

## Timeline

- 2026-04-15 v1.0.0: initial version
```

### E. Automation scripts on Air

| Script | Trigger | What it does |
|---|---|---|
| `wiki-to-runtime-rsync.sh` | launchd WatchPath on `~/nous-agaas/wiki/pages/skills/` | Rsync wiki skills → `/opt/nous-agaas/skills/`. Excludes `_gbrain/`, `extracted/`. NEVER uses `--delete`. Uses `flock`. Logs to `pages/progress/rsync-log-*.md`. |
| `lesson-absorption-watcher.py` | launchd every 6h | Scans lessons, flags unabsorbed ≥7d, writes `pages/dashboards/lesson-absorption-debt.md`. |
| `ghost-debt-dashboard.py` | nightly-audit cron | Computes: unabsorbed lesson count, skill coverage %, RESOLVER hit rate %, tokens/task, unused skills. Telegram alert on worsening metric. |
| `skill-from-debug.py` | Manual `/skill-capture` command | Creates `pages/skills/extracted/<slug>/SKILL.md` with `draft: true`. Madi reviews and promotes. |
| `context_injector.py` (rewrite) | Called by `run_task.py` | **Progressive disclosure:** inject ~500-token skill catalog + top-2 full SKILL bodies (via RESOLVER + gbrain hybrid search). Replaces 21 KB blob. |

### F. New launchd jobs on Air

| Plist | Schedule | Purpose |
|---|---|---|
| `com.nous.wiki-to-runtime-rsync` | WatchPath on `pages/skills/` | Auto-rsync on any skill change |
| `com.nous.lesson-absorption` | Every 6h | Ghost lesson detection |
| `com.nous.dream-cycle` | Daily 03:15 | Nightly compounding (READ-ONLY — proposes, never mutates skills) |

### G. Files modified (not recreated)

| File | Change |
|---|---|
| `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` | Trim to ~120 lines; add pointer to SOUL.md. Hold <200 (Anthropic guidance). |
| `Nous/CLAUDE.md` (vault root) | Add "Agent layers" section pointing at Layer 1-6 |
| `MEMORY.md` | Strip to architecture ground-truth table + skill version matrix + blockers (95 → ~50 lines) |
| `openclaw.json` on Air | Add `systemPromptFile: "/opt/nous-agaas/agents/SOUL.md"` if upstream schema supports |

### H. Unchanged (already works — don't touch)

gbrain v0.10.1 autopilot, wiki 3-way git sync, LiteLLM 3-tier fallback, auto-checkpoint, session rotation, nightly-audit, morning-brief, staleness probe, 10 existing skills, Telegram poller, NCAnode, gbrain pgvector+HNSW schema.

---

## The Evolution Loop (Stage-by-Stage)

```
       MADI              AGENT              AUDIT
       │                 │                  │
Stage 1 BIRTH            │                  │
─────── bug found ──► LESSON-NNN written    │
       │                 │                  │
Stage 2 CAPTURE          │                  │
─────── /skill-capture ─► mistake-to-skill ─► draft skill delta
       │                 │                  │
       │ review+commit   │                  │
       ▼                 │                  │
Stage 3 DISTRIBUTE       │                  │
─────── git push ──► VPS bare ──► Air pull ─► launchd WatchPath
                                              ▼
                                     wiki-to-runtime-rsync.sh
                                              ▼
                                     /opt/nous-agaas/skills/
       │                 │                  │
Stage 4 CONSUME          ▼                  │
                   RESOLVER route → full SKILL in ctx → task done
       │                 │                  │
Stage 5 COMPOUND         │                  ▼
                                       Dream cycle 03:15
                                       • unabsorbed ≥7d → ALERT
                                       • skill never used → REVIEW
                                       • RESOLVER drift → FIX
                                              │
                                              ▼
                                   Next day, smarter.
```

---

## 6 Failure Modes & Detection

| Failure | Detection | Response |
|---|---|---|
| Lesson never absorbed | `lesson-absorption-watcher.py` every 6h | ≥7d unabsorbed → Telegram alert |
| Wiki edited but Air stale | `rsync-log` mtime check | Skill with wiki-mtime > runtime-mtime + 10min → audit failure |
| Skill cites non-existent LESSON | `ghost-debt-dashboard.py` nightly | Adds to broken-links report |
| RESOLVER miss (agent can't find skill) | task-result contains "I couldn't find a skill for" | >3/week → create missing skill |
| Concurrent edit merge conflict | git post-merge hook | Abort sync, alert Madi |
| Power loss mid-rsync | `flock` + rsync atomic rename | Next run is idempotent recovery |

---

## Migration Plan — 8 Phases (each reversible)

**Golden rule:** any phase <100% → STOP, write `HANDOFF-PHASE-<N>-BLOCKED-YYYY-MM-DD.md`, hand off.

| # | Phase | Risk | Rollback | Save-where |
|---|---|---|---|---|
| **P0** | Pre-flight snapshot | None | N/A | `raw/pre-evolution-snapshot.tgz` on VPS + Air |
| **P1** | Write 3 wiki source files (SOUL/AGENTS/HEARTBEAT) | Low | `git revert` | 4-way (Mac → VPS → Air → gbrain) |
| **P2** | Create 5 new skills | Low | `git revert` | 4-way |
| **P3** | Extend 4 existing skills to compiled-truth | Medium | Revert to prior version | 4-way |
| **P4** | Create automation scripts (not activated) | None | Delete files | Air + wiki mirror |
| **P5** | Activate launchd jobs ONE at a time with probe | Medium | `launchctl bootout` | Air launchd + wiki plist mirror |
| **P6** | Populate OpenClaw SOUL/AGENTS (docker cp, not bind mount — LESSON-092) | Med-High | docker cp empty back | Air runtime + wiki + gbrain |
| **P7** | Rewrite `context_injector.py` + A/B probe 48h | **HIGH** | Revert to v1 injector | Air + wiki + gbrain |
| **P8** | Trim CLAUDE.md + MEMORY.md | Low (after P1-P7 green) | `git revert` | Mac + wiki + gbrain |

---

## 10 Verification Gates

| Gate | Test | Pass criterion |
|---|---|---|
| **G1** Identity stable | 5× `/ask "who are you, what skills, where is knowledge"` | All 5 agree, zero hallucinated paths |
| **G2** Skill reachable | Write LESSON-TEST-001 → `/skill-capture` → check runtime | Rule appears in `/opt/nous-agaas/skills/<target>/` within 10 min |
| **G3** Rsync never deletes | Simulate `_gbrain/` file loss | `_gbrain/` on Air still complete |
| **G4** Progressive disclosure | Measure context bytes old vs new injector on 10 tasks | Median <8KB (was 21KB) |
| **G5** Ghost debt visible | Unabsorbed LESSON + 7d fast-forward | Shows in dashboard + Telegram alert |
| **G6** Dream cycle read-only | Instrument run | Zero writes to `pages/skills/*/SKILL.md` |
| **G7** Crash recovery | Kill rsync mid-transfer, rerun | Runtime = wiki state, idempotent |
| **G8** Concurrent edit safe | Edit same SKILL on Mac + Air simultaneously | Git conflict detected, no silent loss |
| **G9** Agent cites source | Skill-dependent question | Answer cites skill + LESSON/LAW |
| **G10** Agent reads SOUL at startup | `"Quote the first line of your SOUL.md verbatim"` | Exact match |

## Weekly steady-state probe

```bash
ssh air 'cd ~/nous-agaas && python3 tools/ghost-debt-dashboard.py --format=text'
```

**Bulletproof targets:**
- Unabsorbed lesson count: 0-2 (fresh <7d only)
- Skill coverage: ≥95% of week's intents resolved via RESOLVER.md
- RESOLVER hit rate: ≥80%
- Avg context tokens/task: <8000
- Skills never used in 30d: 0 (if >0 → either missing RESOLVER entry or skill is redundant)

Any metric degrades week-over-week → root-cause → fix → fix becomes a lesson → absorbed into skill → loop closes.

---

## What This Is NOT

- **NOT a monolithic GOD_PROMPT.md file.** The GOD_PROMPT v1.0 doc Madi drafted becomes the distributed content across Layer 1 (SOUL.md), Layer 2 (AGENTS.md), Layer 3 (skills). Zero monolith.
- **NOT deleting the lessons folder.** Lessons are the append-only audit log (birth certificate of a rule). LAW-015 requires them. Research (Karpathy SPL, Tan's compiled-truth) backs this: evidence trail below, compiled rules above.
- **NOT deleting MEMORY.md.** Trimmed to ground-truth table (architecture + skill versions + blockers). Session history stays in archive.
- **NOT autonomous self-modification.** Dream cycle PROPOSES, Madi APPROVES, `/skill-capture` COMMITS. No autonomous loops (anti-slop rule).
- **NOT a breaking change to gbrain or wiki git sync.** Both work, both stay. The evolution adds a layer, doesn't replace the foundation.

---

## Open Questions (flag before implementation)

1. **Does `openclaw.json` schema support a `systemPromptFile` field?** If not, Phase P6 needs an upstream patch OR we prepend the system prompt inside `context_injector.py` as the first block. Fallback plan exists either way.

2. **Three-repo pattern (public/private/shared skills)?** Research cites it. At current scale (1 client = Satory, 1 human = Madi), we're effectively private-only. Revisit when onboarding client #2.

3. **Langfuse wire-up to Air LiteLLM?** Observability would help verify progressive-disclosure metrics. Currently Langfuse is on VPS but not wired to Air. Low priority — don't block v1.0 rollout.

---

## Acceptance

Design is approved when Madi:
1. Reads this file in full
2. Confirms the 6 layers, 5 new skills, 8 migration phases, 10 verification gates are right
3. Approves one of: (a) proceed to writing-plans skill for ordered task queue, (b) request changes to this spec

On approval → next step is `superpowers:writing-plans` to generate the ordered 1-by-1 implementation plan. No code is written before the plan is approved.

---

## Timeline

- **2026-04-15** | v1.0 draft written during Claude Code session 26 based on 3 parallel audits (Air/OpenClaw current state, wiki+skill coverage, external benchmarks) + Madi's Claude research on Karpathy SPL + Tan SKILLPACK + Anthropic Agent Skills + NASA lessons-DB failure + Mem^p procedural-memory research. Spec: `pages/specs/god-prompt-v1-design-2026-04-15.md`. Awaiting Madi approval before `superpowers:writing-plans` invocation.

## See also

- [[nous-ai]] — holding company, architecture decisions
- [[openclaw]] — gateway framework (CVEs, single-agent pattern, canonical SOUL/AGENTS/HEARTBEAT spec)
- [[gbrain-garrytan]] — memory layer (Tan's SKILLPACK, compiled-truth convention)
- [[skills-not-agents]] — depth-beats-width principle
- [[agent-harness-ownership]] — memory = harness, if memory dies with harness, harness too thick
- [[hybrid-model-routing]] — 90/10 split GLM-5.1 / Sonnet / Opus
- [[LAW-005-obsidian-master]] — single source of truth, physical symlink enforcement
- [[LAW-015-root-cause-evolution]] — lesson format, root-cause discipline
- [[LESSON-079-one-agent-not-sixteen]] — multi-agent coordination fails at 13.37% (EvoClaw)
- [[LESSON-095-gbrain-0.4.1-to-0.10.1-upgrade]] — current gbrain version context
- [[LESSON-103-satory-dashboard-lies-when-data-stale]] — data_freshness envelope pattern
- [[LESSON-104-litellm-router-dual-provider-cooldown-crash]] — 3-tier fallback chain
- [[HANDOFF-2026-04-11-architecture-audit]] — prior architecture audit + Garry Tan discovery
- [[AUDIT-023-karpathy-llm-wiki-compliance-deep-audit]] — wiki compliance baseline
- [[AUDIT-027-god-level-alignment-vs-trefethen-mempalace-brain]] — god-level alignment audit (context for this spec)
