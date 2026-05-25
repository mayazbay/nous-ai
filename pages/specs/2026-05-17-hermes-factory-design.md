---
type: spec
id: SPEC-HERMES-FACTORY-2026-05-17
title: "Hermes Agent factory + smart-routing 4-pool model rotation — AMENDED 80% pre-existing"
tags: [spec, hermes, factory, model-rotation, ceo-hierarchy, openclaw, openbrain, grok-router, brainstorm-derived, amended, duplicate-detection-win]
date: 2026-05-17
source_count: 5
status: amended-scope-cut
last_updated: 2026-05-17
related: ["[[ceo-hierarchy]]", "[[command-center]]", "[[session-coordination]]", "[[openbrain-projection]]", "[[musk-algorithm]]", "[[karpathy-loop]]", "[[karpathy-coding-principles]]"]

---

# SPEC — Hermes Agent factory + smart-routing 4-pool model rotation

## ⚠️ REALITY CHECK — 2026-05-17 16:35 KZT (amendment after commit `53e87e9e`)

After committing this spec, I read `pages/skills/ceo-hierarchy/SKILL.md` and discovered **the architecture below is ~80% already shipped**. The handoff doc that triggered this brainstorm cited `ceo-hierarchy` v1.7.0; reality is **v1.8.6** with 24 APs.

**What's already shipped (2026-05-15, two days before this spec):**

| Component proposed | Reality (already shipped) |
|---|---|
| Hermes Agent as factory dispatcher | **AP-21**: Hermes canary on Air, profile `nouscanary`, alias `hermes-nouscanary`, isolated from production Telegram poller. 24h cutover gate at `tools/hermes_canary_gate.py`. |
| LangGraph routing engine (Grok-first-pass / ChatGPT execution / cheap workers) | **AP-23**: `tools/factory_orchestration_policy.py` (236 LOC) + `tools/langgraph_factory_orchestrator.py`. Routes: `long_work_goal` → Goal/Todoist + chain (grok-reasoning → deepseek-v4-flash → deepseek-v4-pro → kimi-k2.6 → glm-5.1 → codex), `chatgpt_execution` → Codex GPT-5.5 sub, `grok_decision_review` → OpenClaw grok-ceo, routine → grok-ceo. |
| Premium pool: GPT-5.5 sub + Opus 4.7 sub | Already in policy as `chatgpt_execution` + `codex:gpt-5.5-subscription` |
| Cheap-Chinese-OS pool: DeepSeek/Qwen/Kimi/GLM | Already in worker fallback chain |
| Token-aware route markers (regression-resistant) | **AP-24**: shipped 2026-05-15 after live sampling caught `run` matching inside `runtime` |
| Tests | `tools/tests/test_factory_orchestration_policy.py`, `tools/tests/test_langgraph_factory_orchestrator.py`, `tools/test_operator_boundaries.py` (3 routing tests) |
| Hermes supervisor process | `tools/hermes_factory_watchdog.py` via launchd |

**Sections 1, 2, 5 ("Component breakdown" #1-2, "ceo-hierarchy v1.7.0→v1.8.0"), 6 ("hermes-factory skill skeleton") below are SUPERSEDED.** The proposed v1.8.0 bump would have REGRESSED v1.8.6 (skill is now further ahead than I proposed). A separate `hermes-factory` skill would duplicate AP-21 doctrine (anti-pattern per `session-coordination` AP-4). **Do not act on those sections.**

**What remains genuinely NEW — the 20% worth shipping (Codex scope):**

1. **Weekly cheap-pool winner-picker** — existing system has a FALLBACK chain (try-then-fail-then-try-next). Proposed adds a winner-PICKER: every Sunday, query OpenRouter rankings + last 7 days `ask-hierarchy.jsonl` stats, pick the best-performing Chinese-OS model, draft proposal to Telegram with `/approve` gate. See **Section 3 below**.

2. **Monthly `/benchmark-models` validation cron** — does not exist. See **Section 4 below**.

3. **Hermes 24h cutover-gate completion runner** (NEW Section 9 below) — gate at `tools/hermes_canary_gate.py` exists; 10 proofs required to promote from canary to production are NOT all done yet. New plan walks the proofs deterministically and produces the production-promotion audit doc.

**Root cause of the near-duplicate:** I trusted the handoff doc's version claim (v1.7.0) instead of reading the actual SKILL.md during warm-context phase. Codified to `session-coordination` Timeline + OpenBrain.

**Two duplicate-prevention wins today (both via system safety nets):**
- 🟢 **AP-32 handshake caught peer's `b307da62` AP-35 fix** before I redid it (~30min saved)
- 🟢 **Reading actual SKILL.md caught the v1.7.0→v1.8.6 staleness** before I overwrote v1.8.6 with v1.8.0 (~45min saved + a regression avoided)

This is what RULE ZERO + AP-32 + `session-coordination` v1.33.0 + the "no duplicate work" memory rule were built for. The system worked.

---

## Compiled truth

A two-layer architecture that keeps OpenClaw + GPT-5.5 subscription as the **presidential interface** (where Madi works, his "second brain") and adds **Hermes Agent by Nous Research** as the **factory dispatcher** that orchestrates composable subagents. A Grok-top-tier model acts as the **router-LLM** that decides per-task whether to send work to a fixed premium pool (GPT-5.5 subscription, Claude Opus 4.7 subscription) or to a weekly-rotating cheap-Chinese-open-source pool. All research goes through the cheap pool to save tokens. Weekly rotation of the cheap slot runs Sunday 03:00 KZT, drafts a proposal to Telegram, requires `/approve` before deploy. Monthly `gstack /benchmark-models` validates the auto-picks against the user's real prompt corpus.

Brand alignment: "Hermes" here is [Hermes Agent](https://github.com/NousResearch/hermes-agent), the open-source MIT-licensed self-improving agent framework from Nous Research — #1 on OpenRouter as of May 2026 (224B daily tokens, surpassing OpenClaw's 186B). Naming aligns with Nous AGaaS.

## Why this design

Brainstorm session 2026-05-17 16:00-16:30 KZT. Five-question convergence:

1. **Rotation trigger** → Hybrid: weekly OpenRouter auto-bump + monthly /benchmark-models validation.
2. **Research entry-point** → Auto-classified via OpenClaw classifier (no new explicit command). Routes to cheap pool, not premium.
3. **Hermes interpretation** → Real product (Hermes Agent by Nous Research), not a 4th model. Sits as dispatcher gateway between OpenClaw and the model router. Confirmed by URL https://hermes-agent.nousresearch.com and GitHub https://github.com/NousResearch/hermes-agent.
4. **Premium pool** → GPT-5.5 subscription + Claude Opus 4.7 subscription (Madi pays $200/mo × 2 = $400/mo fixed).
5. **Cheap pool** → Chinese open-source top model, rotates weekly. Initial pool: DeepSeek V4 Flash/Pro, Qwen-3, Kimi-K2, GLM-5. Winner per week takes the slot.

Five-step Musk elimination applied during brainstorm:
- ❌ Deleted "premium Grok deep research as entry-point" (user clarified: research is cheap, not premium)
- ❌ Deleted "Hermes as 4th model in pool" (user clarified: Hermes is the dispatcher framework)
- ❌ Deleted "auto-deploy weekly bumps without approval" (subscriptions ≠ silent changes)
- ❌ Deleted "build dispatcher from scratch" (Hermes Agent already exists, MIT, #1 on OpenRouter)
- ✅ Kept: 4-pool model, Grok-router as smart-triage, weekly cadence with approval gate

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PRESIDENTIAL LAYER (unchanged — Madi's "second brain")        │
│                                                                 │
│  Madi (Telegram /codex, Mac terminal, Cursor IDE)              │
│       │                                                         │
│       ▼                                                         │
│  OpenClaw + GPT-5.5 subscription  ────► [Madi works here]      │
│       │                                                         │
└───────┼─────────────────────────────────────────────────────────┘
        │ delegates factory tasks
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  FACTORY LAYER (NEW — Hermes orchestrates)                     │
│                                                                 │
│  Hermes Agent (self-hosted on Air, Air:18790)                  │
│   • composable subagents w/ persistent memory                  │
│   • auto-generated skills (closed learning loop)               │
│   • Telegram/Discord/Slack/CLI inputs                          │
│       │                                                         │
│       ▼                                                         │
│  Grok-top-tier router-LLM (e.g., grok-4-fast-reasoning)        │
│   • input: task description + context                          │
│   • output: {"pool": "premium" | "cheap", "model": "...",      │
│              "reason": "..."}                                  │
│       │                                                         │
│       ├──► PREMIUM POOL (fixed):                              │
│       │      • gpt-5.5 (subscription)                          │
│       │      • claude-opus-4-7 (subscription)                  │
│       │      $400/mo, used only when Grok says "hard"          │
│       │                                                         │
│       └──► CHEAP POOL (weekly-rotating):                       │
│              Current week's winner of:                          │
│              • deepseek-v4-flash / -v4-pro                     │
│              • qwen-3-coder-plus                               │
│              • kimi-k2-instruct                                │
│              • glm-5-air                                       │
│              All research routes here regardless of weight     │
└─────────────────────────────────────────────────────────────────┘

OBSERVABILITY:
  - ask-hierarchy.jsonl: every routing decision logged with cost
  - cost cap: $50/day for premium pool (configurable)
  - daily Telegram summary at 04:00 KZT (morning-brief existing)
  - weekly rotation review: Sunday 03:00 KZT proposal → Madi /approve
```

## Decision matrix (Grok-router heuristics)

Grok-top-tier prompted with this matrix per task:

| Signal | Route to |
|---|---|
| Code requires reading >10 files, architectural reasoning, novel design | PREMIUM (Claude Opus 4.7 sub for code/arch; GPT-5.5 sub for general reasoning) |
| Multi-step planning, cross-domain synthesis, high-stakes user-facing output | PREMIUM |
| Bug fix in known module, single-file edit, format conversion | CHEAP |
| Research, summarization, citation extraction, comparison | CHEAP (token-conscious) |
| Code generation from clear spec (<200 LOC), test writing, refactor | CHEAP first, escalate to PREMIUM only if cheap fails twice |
| Urgent + customer-facing | PREMIUM (no cheap retry) |
| Quiet hours (22:00-08:00 KZT) or cost-cap-exceeded today | CHEAP (or queue) |

## Component breakdown

### 1. Hermes Agent installation (Codex scope)

- **Step 1 — Audit first:** `git clone https://github.com/NousResearch/hermes-agent /tmp/hermes-audit`. Review `install.sh`, `LICENSE`, recent 50 commits. Post SHA256 of install.sh + commit-count summary to spec Timeline before any execution.
- **Step 2 — Install isolated:** `curl -fsSL https://hermes-agent.nousresearch.com/install.sh` → save locally → diff against the audited copy → `bash install.sh --prefix /opt/hermes-agent --user hermes` (or whatever isolation flags exist).
- **Step 3 — Port allocation:** Hermes listens on **Air:18790** (OpenClaw is 18789). Verify no conflicts.
- **Step 4 — Config:** `hermes setup` with: OpenRouter API key (existing), Telegram bot token (existing, see CLAUDE.md HARD RULE 1 about bot token identity), persistent memory dir = `/Users/madia/nous-agaas/hermes-memory/`.
- **Step 5 — launchd plist:** `com.nous.hermes-agent` (similar to existing `com.nous.openclaw` plist).
- **Step 6 — Smoke test:** `hermes test` end-to-end before wiring to factory traffic.

### 2. Grok-router (Codex scope: `tools/grok_router.py` ~100 LOC)

Pure function: takes `(task_text, context_dict)`, calls Grok-top-tier via LiteLLM with the decision-matrix prompt, returns `{"pool": ..., "model": ..., "reason": ..., "estimated_cost_usd": ...}`.

Wraps existing `ceo-hierarchy` `tier_log.py` for JSONL telemetry. Adds `routing_decision` event type to `ask-hierarchy.jsonl`.

Failure modes:
- Grok-router timeout (>10s): fall back to cheap pool.
- Grok-router returns invalid JSON: fall back to cheap pool, log warning.
- Cost cap reached: hard-force cheap pool, append `cost_cap_hit=true` to log.

### 3. Cheap-pool weekly rotation (Codex scope: `tools/cheap_model_rotation.py` ~150 LOC)

launchd `com.nous.cheap-model-rotation` runs Sunday 03:00 KZT:
1. Queries OpenRouter `/api/v1/models?category=chinese-os` (or filter client-side by provider).
2. For each candidate: pulls (a) last 30 days OpenRouter price, (b) context length, (c) provider score.
3. Pulls last 7 days of `ask-hierarchy.jsonl` for current cheap-pool model: avg cost/task, avg latency, error rate.
4. Computes composite score per candidate. Weighting:
   - 40% quality signal (OpenRouter's quality/intelligence indicator if exposed; otherwise public benchmark proxy like Artificial Analysis or community ELO from OpenRouter app rankings)
   - 30% cost (inverse of $/M output tokens)
   - 20% latency (inverse of avg P50 response time over last 7 days)
   - 10% reliability (1 − error_rate from `ask-hierarchy.jsonl` if model already in pool, else provider reliability proxy)
   Codex picks the exact OpenRouter field names during implementation and documents them in `cheap_model_rotation.py` docstring.
5. If winner ≠ current pin AND `winner_score > current_score × 1.05` (5% margin to avoid churn):
   - Drafts `pages/progress/MODEL-ROTATION-PROPOSAL-<YYYY-MM-DD>.md` with diff
   - Telegrams Madi via `tools/tg_send.sh`: "🟡 Cheap-pool weekly proposal: bump `<current>` → `<winner>` (composite score `<old>` → `<new>`). Reply `/approve` or `/skip`."
6. On `/approve`:
   - Updates `ceo-hierarchy/SKILL.md` cheap-pool pin
   - Bumps `ceo-hierarchy` minor version
   - Deploys Air runtime (rsync to Air)
   - Replies "✅ Deployed `<winner>`"

Approval gate is **mandatory**. No silent auto-deploy.

### 4. Monthly benchmark validation (Codex scope: `tools/cheap_pool_benchmark.py` ~80 LOC)

launchd `com.nous.cheap-pool-benchmark` runs 1st of month, 04:00 KZT:
1. Pulls last 30 days of `/ask` prompts from `ask-hierarchy.jsonl`, samples 10 representative.
2. Runs each through all 4 candidates in the cheap pool via OpenRouter.
3. Composite score per the same formula as rotation.
4. Telegrams diff vs current pin. If benchmark winner ≠ rotation pin → asks Madi if manual override needed.

This validates the OpenRouter ranker matches Madi's real workload.

### 5. ceo-hierarchy v1.7.0 → v1.8.0 (Claude scope, doctrine only)

New sections to add (NO CODE in skill — code goes in tools/):
- **Architecture diagram** as above
- **Pool definitions** (premium fixed, cheap rotating)
- **Routing decision matrix** as above
- **Approval gate doctrine** (no silent bumps to subs-touching changes)
- **Cost cap doctrine** ($50/day premium cap default, override via `/cost-override`)
- **Research path** (always cheap, no exceptions, write-back to `pages/research/`)
- AP-N (next AP number, count current first): "Cheap-pool rotation must require Madi /approve before any sub-touching deploy"

### 6. hermes-factory v1.0.0 (Claude scope, skeleton)

New skill at `pages/skills/hermes-factory/SKILL.md`. Register in `pages/skills/_gbrain/RESOLVER.md`. Skeleton-only:
- Frontmatter v1.0.0
- H1 + Purpose
- Architecture (links to this spec)
- AP slots empty (Codex fills as ships)
- Timeline with creation entry

### 7. session-coordination Timeline (Claude scope)

Append one-line entry capturing today's AP-32 win (peer's b307da62 caught by handshake, prevented duplicate AP-35 work). RULE ZERO: no new LESSON file. gbrain add_timeline_entry mirror.

### 8. OpenBrain projection wiring

Already integrated per [[SP2-OPENBRAIN-IDENTITY-2026-05-17]]. No new work — verify the existing 5-min projection runner picks up the new skill files (`hermes-factory`, `ceo-hierarchy` v1.8.0, this spec) on its next cycle.

### 9. Hermes 24h cutover-gate completion runner (NEW — 2026-05-17 amendment)

The 10 proofs required by `tools/hermes_canary_gate.py` (per [[ceo-hierarchy]] AP-21) to promote Hermes Agent from `nouscanary` to production:

1. **Telegram route isolation** — prove Hermes never registers as a Telegram poller (no `getUpdates` on @nousAGaaSbot's token).
2. **LiteLLM non-interference** — prove `nouscanary` profile doesn't change LiteLLM port/state.
3. **Todoist canary proof** — end-to-end task creation via `hermes-nouscanary`.
4. **Notion canary proof** — page creation/edit via `hermes-nouscanary`.
5. **Obsidian/wiki commit proof** — Hermes wrote a commit + auto-sync replicated to VPS bare.
6. **gbrain timeline proof** — Hermes added a timeline entry that gbrain ingested.
7. **OpenBrain capture/projection proof** — Hermes captured a thought; OpenBrain 5-min runner picked it up; appeared in projection log.
8. **Cost receipt** — JSONL record with model + token count + USD amount.
9. **Rollback command** — documented one-liner to disable cleanly (`launchctl unload com.nous.hermes-agent` + alias removal + log preserve).
10. **No factory red checks** — `tools/factory_health.py` green for 24 consecutive hours after canary deploy.

**Codex builds `tools/hermes_promotion_runner.py`** (~120 LOC): walks proofs 1-10 in order, captures evidence to `pages/audits/HERMES-PROMOTION-PROOF-<date>.md`, posts to Telegram on each green proof, and on full pass adds AP-25 to `ceo-hierarchy` "Hermes promoted from canary to production" via the 3-edit RULE ZERO ritual (frontmatter version bump + Timeline line + gbrain-timeline-ok marker).

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Hermes install via `curl \| bash` is dangerous | Audit GitHub repo + install.sh SHA256 before execution. /careful skill applies. Manual approval before running. |
| Hermes:18790 conflicts with existing Air port | Pre-flight `lsof -i :18790` check in install plan. Pick alternative if conflict. |
| Hermes consumes OpenClaw memory or breaks telegram-poll | Run Hermes in isolated user (`hermes`), separate config dir, NEVER inherit OpenClaw env. Mirror of `command-center` AP-2 (don't inherit parent env). |
| Grok-router timeout adds latency | 10s hard timeout, fall-back to cheap pool. Total added latency ≤10s P99. |
| Cheap-pool rotation picks a regression | Approval gate. Plus monthly benchmark catches it. Plus rollback = re-apply previous SKILL.md, redeploy. |
| Cost cap reached too aggressively | Configurable, starts at $50/day premium. `/cost-override` to extend. Daily Telegram summary shows current burn. |
| Hermes self-improvement loop writes unwanted state | Persistent memory dir is filesystem; backed up daily; can be wiped. Closed loop reviewed at first weekly retro. |
| Codex misinterprets the spec | Spec is detailed (this doc). HANDSHAKE doc forces scope adherence. Codex must post post-patch proof audit before "done." |

## Acceptance criteria

- [ ] Hermes Agent installed on Air, audited install script, listening Air:18790
- [ ] `hermes test` end-to-end green
- [ ] `tools/grok_router.py` exists, unit-tested, returns valid routing decision JSON for 5 sample tasks
- [ ] `tools/cheap_model_rotation.py` exists, unit-tested, drafts a proposal on dry-run
- [ ] launchd plists registered + verified (`launchctl list | grep hermes`)
- [ ] `ceo-hierarchy` SKILL.md v1.8.0 committed, gbrain timeline entry pushed
- [ ] `pages/skills/hermes-factory/SKILL.md` v1.0.0 committed + registered in RESOLVER.md
- [ ] `session-coordination` Timeline appended with today's AP-32 win
- [ ] First `/approve` cycle test: rotation script proposes, Madi /approves, deploy succeeds
- [ ] First research query: classifier routes to cheap pool, write-back to `pages/research/` succeeds
- [ ] Post-patch proof audit: `pages/audits/HERMES-FACTORY-DEPLOY-PROOF-2026-05-XX.md`
- [ ] 4-way HEAD parity verified (Mac/Air/VPS-bare/GitHub)
- [ ] Telegram E2E: send `/ask <task>` from Madi's phone, observe Hermes-routed reply in <30s

## Implementation split — Claude (me) vs Codex (parallel session)

**Claude — this session (~45 min):**
1. ✅ Write this spec
2. Append `session-coordination` Timeline + gbrain entry (AP-32 win)
3. Bump `ceo-hierarchy` v1.7.0 → v1.8.0 (doctrine only)
4. Create `hermes-factory` v1.0.0 skeleton + register in RESOLVER.md
5. Write HANDSHAKE-2026-05-17-claude-codex-hermes-factory.md
6. Commit each with `git commit -o <path>` (AP-32 anti-collision)
7. Ping Madi via `tools/tg_send.sh` for the AP-35 E2E DM (leftover from earlier session)
8. DONE protocol (4 artifacts)

**Codex — parallel session (~2-3 hours):**
1. Audit `github.com/NousResearch/hermes-agent` (SHA256, recent commits, license)
2. Install Hermes Agent on Air (isolated, port 18790)
3. Build `tools/grok_router.py` + unit tests
4. Build `tools/cheap_model_rotation.py` + unit tests
5. Build `tools/cheap_pool_benchmark.py` + unit tests
6. Register launchd plists (`com.nous.hermes-agent`, `com.nous.cheap-model-rotation`, `com.nous.cheap-pool-benchmark`)
7. Smoke-test: send test `/ask`, observe Hermes-routed reply with cost in `ask-hierarchy.jsonl`
8. Write post-patch proof audit `pages/audits/HERMES-FACTORY-DEPLOY-PROOF-2026-05-XX.md`
9. gbrain add_timeline_entry on `pages/skills/hermes-factory/skill`
10. DONE protocol with 4 artifacts to Madi via tg_send.sh

**Scope guard (AP-32):** Claude does NOT touch `tools/grok_router.py`, `tools/cheap_model_rotation.py`, `tools/cheap_pool_benchmark.py`, any launchd plist, or Hermes install. Codex does NOT touch SKILL.md files or this spec.

## REVISED scope (post-amendment 2026-05-17 16:35 KZT) — actual deliverables

Per the **Reality Check** at the top of this spec, the bulk of the original design is already shipped in `ceo-hierarchy` v1.8.6. The actual deliverables for this session + the parallel Codex session are:

### Claude (this session) — substrate-only, no code (~20 min remaining)

1. ✅ Write this spec (commit `53e87e9e`)
2. ✅ Amend with Reality Check (this section + Sections at top + Section 9)
3. ⏳ Append `session-coordination` Timeline with TWO duplicate-prevention wins today
4. ⏳ Capture both wins to OpenBrain via `mcp__claude_ai_Open_Brain__capture_thought`
5. ⏳ Quick library-grade audit Phase-1 verify (confirm SP1's 8-gate GREEN still holds)
6. ⏳ Write `HANDSHAKE-2026-05-17-claude-codex-hermes-promotion-rotation.md` with the tight 20% scope for Codex
7. ⏳ Push all + verify 4-way HEAD parity (Mac/Air/VPS-bare/GitHub)
8. ⏳ DONE protocol: 4 artifacts + tg_send.sh ping to Madi with AP-35 E2E DM ask

### Codex (parallel session — handshake-coordinated, blocked on Claude's spec + handshake doc)

**Scope is the 20% genuinely-new ONLY:**

1. **`tools/cheap_pool_winner_picker.py`** (~120 LOC, NEW) — Sunday 03:00 KZT launchd. Queries OpenRouter rankings + last 7d `ask-hierarchy.jsonl` stats for the Chinese-OS slot. Composite score per Section 3. Drafts `pages/progress/CHEAP-POOL-PROPOSAL-<date>.md`. Telegrams Madi with `/approve` ask.

2. **`tools/cheap_pool_benchmark.py`** (~80 LOC, NEW) — 1st-of-month 04:00 KZT launchd. Runs `gstack /benchmark-models` on 10 representative `/ask` prompts from last 30 days. Drafts validation note; Telegrams diff vs current rotation pin.

3. **`tools/hermes_promotion_runner.py`** (~120 LOC, NEW) — Walks the 10 proofs in Section 9 above, deterministically. Captures evidence. On full pass, performs the AP-25 RULE ZERO 3-edit ritual on `ceo-hierarchy/SKILL.md`.

4. **launchd plists** (3): `com.nous.cheap-pool-winner-picker.plist`, `com.nous.cheap-pool-benchmark.plist`, `com.nous.hermes-promotion-runner.plist` (this last one is on-demand, not scheduled).

5. **Tests** for all three tools (TDD per `karpathy-coding-principles`).

6. **Post-patch proof audit** at `pages/audits/HERMES-PROMOTION-RUNNER-DEPLOY-PROOF-<date>.md`.

7. **Codex MUST NOT touch:** `pages/skills/ceo-hierarchy/SKILL.md` (the AP-25 addition is performed BY the promotion runner script itself, not by Codex hand-editing). `pages/skills/command-center/SKILL.md`. `tools/run_task.py`. `tools/factory_orchestration_policy.py` (unless adding a `cheap_pool_pin` lookup, which is in scope — but then it's a tiny addition, not a rewrite).

8. **AP-32 collision discipline**: every commit uses `git commit -o <path>`. Pre-action handshake before each file write.

### Revised acceptance criteria (replaces the one below)

- [ ] Reality Check + Section 9 + this Revised Scope section committed to the spec (Claude)
- [ ] `session-coordination` Timeline appended (Claude)
- [ ] OpenBrain capture for both wins (Claude)
- [ ] 4-way HEAD parity post-push (Mac/Air/VPS-bare/GitHub) (Claude)
- [ ] HANDSHAKE-CODEX doc committed (Claude)
- [ ] tg_send.sh ping with AP-35 E2E DM ask to Madi (Claude, end-of-session)
- [ ] `tools/cheap_pool_winner_picker.py` shipped + unit-tested + launchd loaded (Codex)
- [ ] `tools/cheap_pool_benchmark.py` shipped + unit-tested + launchd loaded (Codex)
- [ ] `tools/hermes_promotion_runner.py` shipped + 10 proofs walked + audit doc captured (Codex)
- [ ] On 10/10 proofs green: AP-25 added to ceo-hierarchy via runner-performed RULE ZERO ritual (Codex)
- [ ] Post-patch proof audits committed (Codex)

## Sources

- [Hermes Agent — Nous Research](https://hermes-agent.nousresearch.com)
- [GitHub: NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- [OpenClaw vs Hermes Agent — MarkTechPost 2026-05-10](https://www.marktechpost.com/2026/05/10/openclaw-vs-hermes-agent-why-nous-researchs-self-improving-agent-now-leads-openrouters-global-rankings/)
- [Hermes Agent vs OpenClaw — HackerNoon 2026](https://hackernoon.com/hermes-agent-vs-openclaw-which-ai-agent-framework-wins-in-2026)

## See also

- [[ceo-hierarchy]] v1.7.0 → bumps to v1.8.0 as part of this spec
- [[command-center]] v2.12.5 (AP-35 just shipped by peer — see [[HANDOFF-SESSION-CLOSE-2026-05-17-TO-TERMINAL]])
- [[session-coordination]] v1.33.0 — AP-32 handshake protocol referenced by Implementation Split
- [[openbrain-projection]] v1.3.0 — picks up new skill files automatically
- [[musk-algorithm]] v1.3.0 — five-step elimination applied during brainstorm
- [[karpathy-loop]] v1.12.0 — multi-reviewer Council escalation if this spec hits >3 subsystems trigger
- [[karpathy-coding-principles]] v1.1.0 — surgical, minimum code, no speculative features for Codex implementation

## Timeline

- **2026-05-17 16:30 KZT** | Spec written from brainstorm session (5 questions, 4 design pivots). Approved by Madi. Ready for Claude scope execution + Codex parallel dispatch. [[HANDSHAKE-2026-05-17-claude-codex-hermes-factory]] forthcoming. Commit `53e87e9e`.

- **2026-05-17 16:35 KZT** | **AMENDED.** Reading `pages/skills/ceo-hierarchy/SKILL.md` revealed it's at v1.8.6 (not v1.7.0 as the handoff doc claimed), with AP-21 (Hermes canary), AP-23 (LangGraph route spine), AP-24 (token-aware markers) all already shipped 2026-05-15. The original spec sections 1, 2, 5, 6 are SUPERSEDED. Prepended Reality Check section. Added Section 9 (Hermes 24h gate completion runner — the 10 proofs to promote from canary to production) + Revised scope. Genuinely-new deliverables shrunk from a full factory build to 3 tools: `cheap_pool_winner_picker.py`, `cheap_pool_benchmark.py`, `hermes_promotion_runner.py`. **Two duplicate-prevention wins captured today** (AP-32 caught peer's b307da62 AP-35 fix + reading SKILL.md caught the v1.7→v1.8.6 staleness). System worked as designed per RULE ZERO + session-coordination v1.33.0 + "no duplicate work" memory rule.
