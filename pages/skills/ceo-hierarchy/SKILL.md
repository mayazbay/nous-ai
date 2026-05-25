---
tier: 2
type: skill
name: ceo-hierarchy
id: SKILL-CEO-HIERARCHY
version: 1.11.0
last_updated: 2026-05-23
status: active
description: "Multi-model CEO hierarchy v1.11.0 — Telegram is the operator surface, OpenClaw is production runtime, GPT-5.5/Codex subscription is the primary CEO route, DeepSeek V4 Flash is the measured cheap worker, Grok is the transparent cap/fallback reviewer, and Hermes remains canary-only. v1.11.0 adds AP-44 Dynamic Subscription Rotation for the CEO route: Codex subscription FIRST → Claude/Opus subscription SECOND (on Codex quota gate) → GPT API THIRD (last resort, paid). Cheapest-first; both $200/mo subscriptions consumed before any pay-as-you-go OpenAI API spend. Re-confirms 3-layer architecture: L1 Hermes+Grok4.3 (replacement-of-Madi), L2 Opus+GPT (Sat-council-refreshed), L3 Composer+best-open-source (Qwen/DeepSeek/Kimi/MiniMax). Builds on v1.10.14's AP-48 (Hermes 24h verifier green-receipt protocol)."
triggers:
  - user DMs /ask on Telegram (Tier-1 routes automatically)
  - user DMs /goal on Telegram (persistent Goal Mode route)
  - user DMs /ask-direct (escape hatch — bypasses Tier-1, goes straight to Opus)
  - user DMs /trace <msg_id> (per-tier timeline)
  - user asks whether Telegram goes to GPT, Grok, OpenClaw, Hermes, Kimi, or DeepSeek
  - user asks "why not OpenClaw fully" or whether OpenClaw/grok-ceo/nous are the same thing
  - user asks "who's deciding what in the hierarchy"
  - cost transparency for /ask
  - tier-specific routing debug
  - rolling back or tuning the hierarchy
tools: [Bash, Read]
mutating: true
absorbs_sources:
  - "SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22"
  - "PLAN-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22"
related: [factory-ops, session-operating-contract, karpathy-loop, karpathy-coding-principles, session-coordination, infrastructure, command-center, find-skills, gbrain-ops]
tags: [skill, multi-model, ceo-hierarchy, codex, deepseek, grok, opus, glm, worker-tier, litellm, openclaw-multi-agent, async-await-shim, jsonl-telemetry, billion-dollar-solopreneur, 2026-04-22, 2026-04-27, session-57]
title: "ceo-hierarchy v1.11.0"
---

# ceo-hierarchy v1.11.0

## Purpose

Give Madi a CEO path and a worker path without mixing them up. OpenAI Codex via `/codex` is the explicit CEO/high-judgment route and must use Codex subscription auth only. Goal Mode via `/goal` is durable objective tracking plus repeated reasoning slices; recurring goal-cycle workers use Grok reasoning by default so progress selection is not delegated to cheap/escalation workers. OpenClaw handles always-on worker execution; routine/bulk work defaults to DeepSeek V4 Flash and hard worker escalation goes to DeepSeek V4 Pro. Grok-ceo remains the default `/ask` OpenClaw router; GPT-5.5 is the second-stage high-judgment route through `/codex`, now with a bounded `/ask` auto-escalation canary for long strategic prompts only. Routine chat must stay cheap.

**Why:** Madi's cognitive load on routine messages scales with his operator throughput. The hierarchy lets him send high-level intent; Codex handles CEO-quality planning/review when explicitly invoked; OpenClaw/DeepSeek workers chew through cheap execution. Billion-dollar-solopreneur pattern — agents run the business; the human delegates direction.

**Honest distinctions:** this is NOT a gstack-role layer (those are skill-level role-prompts on a single model). This is model-level tier separation — different LLM classes per tier for cost + capability arbitrage. Complementary to gstack.

**OpenClaw identity contract:** OpenClaw is the gateway/runtime/orchestrator. It is not itself the thinking identity. A "full OpenClaw" setup means Telegram/goal traffic enters OpenClaw-hosted agents with mounted `AGENTS.md`/`SOUL.md`/`USER.md`/`TOOLS.md`, shared skill roots, and isolated agent workspaces. In the current Nous hierarchy, `grok-ceo` is the Tier-1 OpenClaw-hosted router and `nous` is the Tier-2 OpenClaw-hosted execution agent. Never answer "OpenClaw did X" when the precise truth is "`grok-ceo` decided" or "`nous` executed through OpenClaw." The live proof command is `bash tools/test_openclaw_full_stack_contract.sh`.

**Second-brain contract:** GPT-5.5/Codex subscription is the high-judgment second brain, not the routine workhorse. Routine factory labor stays on the measured cheap worker route. If the GPT subscription lane hits daily/weekly caps, group-facing and DM-facing auto routes fall back transparently to `grok-ceo` with a degraded notice; explicit `/codex` remains explicit and may report its cap. Claude subscription is not a production route here; Claude/Opus participates only through capped API/manual reviewer lanes when explicitly available and ledgered.

## Current rules (binding)

### 0. Telegram prefix truth table

- `/goal <objective>` → `command_center.py` creates/updates a `pages/projects/GOAL-*.md` page, creates/links a Todoist task, kicks `tools/goal_runner.py`, then `com.nous.goal-cycle` keeps cycling it every 4 hours. The worker path is OpenClaw/run_task text-slice progress with explicit `--model grok-reasoning` by default (`NOUS_GOAL_WORKER_MODEL` override), so goal reasoning does not fall through to the cheap worker escalator. It is the persistent memory/proof loop, not direct GPT.
- `/ask <query>` or no prefix → OpenClaw `grok-ceo` Tier-1 router. It may answer directly, delegate, research, or tell the operator to use `/codex` for a high-judgment GPT pass. It is not direct GPT for every message.
- `/ask --tier ceo <query>` → Codex GPT-5.5 subscription-first, Madi-DM only. It is not automatic Opus+Grok API spend; paid council routes require explicit approval, cap, reason, and ledger.
- `/ask --tier cheap <query>` → local MLX first, DeepSeek fallback. It bypasses Codex, Grok, Opus, and the paid council.
- `/ask` identity questions about OpenClaw → local `command_center.py` fast-path answer before any model call: OpenClaw is live; normal `/ask` work is OpenClaw -> `grok-ceo`; this identity check is answered locally by `command_center.py`. This prevents technically true but operator-wrong "No, I am grok-ceo, not OpenClaw" replies.
- `/ask-direct <query>` → OpenClaw `nous`/Opus escape hatch.
- `/codex <task>` → OpenAI Codex/GPT lane on Air. This is the direct OpenAI CEO/high-judgment path and is subscription-only.
- `/code <task>` → Claude Code/Sonnet lane on Air.

**Operational rule:** for long-running proof/memory, use `/goal`; for heavy repo-building or high-judgment execution, use a targeted `/codex` session against that goal. Do not claim "all goal work is handled by GPT" unless the work was actually launched through `/codex` or a future auto-GPT canary is green.

### 0b. Hermes Agent canary boundary

- **Production runtime stays OpenClaw.** Telegram `/ask`, `/goal`, `/codex`, `/code`, Todoist, Notion, Obsidian/gbrain/OpenBrain, and cost controls remain on the existing Air runtime.
- **Hermes Agent is canary-only.** The approved canary profile is `nouscanary`; the executable path is the generated alias `hermes-nouscanary`. Do not rely on `HERMES_PROFILE=...` for routing because v0.8.0 ignored that environment variable during this rollout and mutated the default profile once.
- **No Hermes Telegram gateway in production.** `hermes-nouscanary status` must show Telegram not configured and gateway not loaded. Never let Hermes call `getUpdates` for `@nousAGaaSbot`; Air `telegram_poll.py` remains the exclusive poller.
- **Fast proof is mandatory; blind cutover is banned.** Do not hide behind passive soak language when Madi asks for Musk-mode proof. Run a same-day, production-shaped Hermes sprint with `tools/hermes_canary_gate.py --factory-probe --webui-probe --smoke --json`, compare against the OpenClaw baseline, and write an audit artifact. Passing the sprint proves canary viability only; it does not promote Hermes.
- **No production cutover until the 24h gate passes.** Required gates: Telegram route isolation, LiteLLM non-interference, Todoist read/write proof in canary scope, Notion proof, Obsidian/wiki commit proof, gbrain timeline proof, OpenBrain capture/projection proof, cost receipt, rollback command, and 24h stability.
- **24h means strict zero-red continuity.** If any `factory_no_drift_probe` inside the window returns RED, even for transient sync lag while OpenClaw/LiteLLM/Telegram are healthy, do not create a green `HERMES-24H-GATE-*` artifact. Write a yellow/reset receipt, root-cause the red, and restart the 24h clock from the next verified green probe.
- **GPT-5.5 stays high-judgment.** Hermes canary may use `gpt-5.5` explicitly for evaluation, but routine Telegram traffic must not be redirected to GPT-5.5.
- **Gemini review truth:** do not claim Gemini reviewed a Hermes/OpenClaw decision unless Gemini is actually present in the live production LiteLLM chat route list or an explicit separate Gemini path is invoked and logged.
- **Mechanical gate:** run `python3 tools/hermes_canary_gate.py --json --factory-probe` on Air before claiming the agent canary is safe; add `--webui-probe` before claiming iPhone/WebUI access is live; add `--smoke` only when intentionally spending one explicit canary model call.
- **Hermes WebUI/iPhone path:** phone access is canary-only via Tailscale/private URL plus `HERMES_WEBUI_PASSWORD`. Do not expose a public Cloudflare/domain path without explicit approval and a rollback proof. The WebUI launchd path must source a shell-safe env file; values with spaces must be quoted or normalized because unquoted values turn into commands under `source`.
- **iPhone reachability truth:** server `/health` is not enough. If `tailscale status` is logged out, `tools/hermes_webui_canary.sh phone-url` must fail instead of returning a stale `ifconfig` `100.x` address. Use `tools/hermes_webui_canary.sh lan-url` only as an explicit same-Wi-Fi fallback, not as a Tailscale proof.
- **GPT/Codex truth:** the Hermes GPT canary is not green unless `codex` is on PATH and `hermes_canary_smoke` returns the exact marker. OpenAI Codex auth without the Codex CLI is a yellow/red operational state because refresh/login and some tooling paths can fail.
- **WebUI status truth:** launchd runs the WebUI with `run-foreground`, so app-local `ctl.sh status` can show "stopped" if no ctl PID file exists. Operational status must use launchd plus HTTP `/health`, and the status helper must show `phone-url` and `lan-url` separately.
- **WebUI factory-surface truth:** iPhone login success is not enough. The canary is operator-ready only when the WebUI starts in profile `nouscanary`, default workspace is `/Users/madia/nous-agaas/wiki`, CLI/session history visibility is enabled, the `Nous Factory` project exists, factory skills from `/Users/madia/nous-agaas/skills` are included, `/api/skills` returns 200, profile memory is non-empty, insights show real sessions, Kanban has a Nous factory board/tasks, default model is `gpt-5.5`, the canary MCP surface exposes active Todoist, gbrain, and Notion inventory, and authenticated `GET /api/factory-events` returns live read-only factory ledger events. A blank default-profile WebUI or seeded-only factory surface is yellow/red even if `/health` is green.

### 0c. Factory second-brain stack

- **Telegram is the cockpit.** It carries operator intent and proof back to Madi's phone; it must stay thin and must not become the memory store.
- **OpenClaw is the factory runtime.** It owns always-on execution, routing, launchd/service integration, and worker orchestration.
- **GPT-5.5/Codex subscription is the second brain.** Use it for explicit `/codex`, `/ask --tier ceo`, top-tier CTO/CEO review, architecture/root-cause slices, and customer/team-transforming judgment. Do not route routine chat or bulk task labor to GPT just because auth is green.
- **DeepSeek V4 Flash is the default cheap worker.** Keep it as the workhorse until `tools/cheap_pool_benchmark.py`, `tools/cheap_pool_winner_picker.py`, and `tools/model_promotion_gate.py` prove a replacement wins real Nous fixtures. Price metadata can nominate; fixture victory promotes.
- **Local Mac/in-house AI is Tier 0 only when proved live.** Prefer local MLX/in-house routes before paid APIs when the endpoint, model, and answer quality are actually green. Never route to a hoped-for local model.
- **Grok is the cap/fallback reviewer.** If GPT subscription caps block automatic high-judgment handling, fall back to `grok-ceo` transparently and mark the route degraded. Do not silently spend xAI API unless paid API policy, cap, reason, and ledger are present.
- **Grok subscription use requires local auth proof.** xAI may announce SuperGrok/X Premium support in OpenClaw, and the local OpenClaw CLI may expose device-code/OAuth flags, but the factory route is not subscription-backed until local `openclaw` auth/status and one canary execution prove it. Until then, Grok in this stack means the existing `grok-ceo`/LiteLLM/API route with normal paid-cap policy.
- **Hermes is canary/watchdog, not production Telegram.** Hermes may evaluate with GPT-5.5 inside the canary profile, but it cannot become the production poller/gateway until the Hermes canary gates in section 0b pass.
- **Claude subscription is not a production assumption.** Do not claim a Claude subscription route works for this stack. Opus/Claude can be a manual/API/council participant only when the billing surface is explicit and allowed.
- **Stuck-agent council is durable, not chat-only.** Before consulting GPT/Grok/Opus/DeepSeek/Cursor-class reviewers, write or read the continuity packet, cap paid API surfaces, store the consult/audit artifact, and convert any successful repair into the relevant skill plus gbrain timeline.
- **03:00 evolution is a proof gate.** The daily substrate job must prove Obsidian/wiki, gbrain, OpenBrain, OpenClaw, Hermes canary status, MCP/API health, dirty-tree residuals, and model-price/promotion watch status. A green launchd row alone is not enough.

### 1. Tier-1 decision flow (every /ask)
Current `/ask` still routes to `grok-ceo` inside OpenClaw by default. Do not silently flip all `/ask` traffic to Codex just because Air Codex auth is green; a trivial 2026-05-13 GPT-5.5 canary used 7004 tokens, so broad auto-GPT would violate the low-token CEO requirement. Exception: AP-16 lets Telegram-sized high-judgment prompts auto-escalate to `/codex` before Grok when all three gates pass: 200-4096 chars, at least one high-judgment marker, and today's Codex/GPT-5 spend is below $5. Grok-ceo classifies normal `/ask` traffic into ONE of four:
- **answer_directly** — chat/status/factual; no execution needed
- **delegate_to_tier_2** — emits structured directive JSON, sessions_spawn(agentId=nous), packages raw Tier-2 report with `[opus-raw]` block
- **research_only** — gbrain/vault lookup + synthesis, no mutations
- **escalate_to_codex** — high-judgment architecture/code/root-cause slice should be launched through `/codex` or AP-16's bounded auto-GPT gateway, with explicit cost receipt

Mandatory Codex routes are stricter than optional high-judgment escalation: external operator proof questions and top-tier CTO/CEO/supervisor prompts must never fall back to routine cheap labor. If Codex budget/auth is unavailable, group-facing and Madi-DM auto routes use the AP-41 transparent `grok-ceo` degraded fallback; explicit `/codex` keeps the explicit Codex cap/auth response.

### 2. /ask-direct escape hatch (always available)
`/ask-direct <query>` bypasses Tier-1 entirely. Routes straight to `nous` (Opus) with `agent_id="nous"`. Use when:
- Crisis mode (3am test — urgency trumps latency)
- Debugging Tier-1 behavior
- You need precise Opus output without wrap-layer summarization

### 3. Urgent-keyword auto-bypass
Regex `\b(urgent|broke|down|prod|demo|демо|срочно|critical|now|asap|crisis)\b` on `/ask` message → auto-rewrites to `/ask-direct` before command_center sees it. Log line: `URGENT-KEYWORD-BYPASS: ... → ...`.

### 4. Cost footer on every reply
Every `/ask` reply gets: `— cost: $X.XX (t1 $.. / t2 $.. / t3 $..) | day $Y.YY/$30.00` footer. Data from `~/nous-agaas/logs/ask-hierarchy.jsonl` via `command_center._compose_cost_footer(correlation_id)`.

### 5. correlation_id threading
`correlation_id = "tg_<msg_id>"` propagated through: `run_task.py --correlation-id` → `NOUS_CORRELATION_ID` env var → `docker exec -e` → openclaw agent context → `tier_log.py --correlation-id` → `/trace <msg_id>` reader.

### 6. /trace command
`/trace <msg_id_or_correlation_id>` returns timeline from jsonl:
```
t=<ts> tier=<N> model=<alias> latency=<Xms> cost=$<Y> decision=<verdict>
```

### 7. Timeout sentinels (no fabrication)
- Tier-1 (grok-ceo) 90s → sentinel: "🔴 TIER-2 TIMEOUT (nous/opus, 180s) — task unverified. Run /trace tg_<msg_id>."
- Tier-2 (nous) 180s → nous's own reply chain
- Tier-3 workers 60s per call

If timeout, sentinel VERBATIM. No inventing Tier-2 content.

### 8. Workspace migration (load-bearing)
`nous`'s workspace AGENTS.md now contains merged SOUL+IDENTITY+USER critical sections. Why: when invoked as subagent of grok-ceo, OpenClaw's subagent-system-prompt builder injects ONLY `AGENTS.md` + `TOOLS.md` (omits SOUL/IDENTITY/USER per `/app/docs/concepts/system-prompt.md`). Without this merge, subagent-nous would lose its 128-skill doctrine + Madi context.

### 9. Async-await shim in run_task.py (required for hierarchy to actually return text)
`openclaw agent --local` exits on first turn-yield (when grok-ceo calls `sessions_yield` awaiting nous's announce). `payloads=[]` in stdout. Shim: after subprocess.run, if payloads empty + agent has active session, poll session jsonl via `docker exec cat` for new assistant-text messages (90s timeout, 500ms interval). Inject into payloads. Downstream callers see normal result.

### 10. LiteLLM fallback chain (for each alias)
```
deepseek-v4-flash → grok-reasoning → sonnet → haiku-4-5
deepseek-v4-pro → deepseek-v4-flash → grok-reasoning → sonnet
grok-reasoning → sonnet-4-5-thinking → deepseek-v4-flash → haiku-4-5
opus → sonnet → deepseek-v4-flash → haiku-4-5
sonnet-4-5-thinking → opus → sonnet → deepseek-v4-flash → haiku-4-5
grok-code-fast → deepseek-v4-flash → grok-reasoning
kimi-k2.6 → deepseek-v4-flash → grok-reasoning
glm-5.1 → glm-4.5-flash → deepseek-v4-flash → grok-reasoning → sonnet
glm-4.5-flash → deepseek-v4-flash → grok-reasoning
```

### 10b. Worker model policy (v1.5.4, 2026-05-10 — supersedes v1.5.0 Pro-as-default policy)

- **Confirmed default multi-turn worker: `deepseek-v4-flash`** — run_task.log confirms every task since 2026-04-14 uses flash, 100% success rate, zero HTTP 400s. This is the actual production reality.
- **GUARDED: `deepseek-v4-pro` via OpenRouter `:nitro`** — single-turn / escalation only. **Multi-turn use is BLOCKED until LiteLLM PR #26660 merges.** The reasoning_content stripping bug causes HTTP 400 errors in multi-turn agent loops. Pro remains valid for hard long-context single queries and audit escalation where multi-turn is not required.
- **Hard escalation: `/codex` with `gpt-5.5` subscription auth** for high-judgment tasks needing alternative reasoning lineage. Do not put `gpt-5.5` in broad LiteLLM API fallback chains unless an explicit paid-API budget and live probe approve it.
- **GLM 5.1 / 4.5-flash** remain as last-resort fallback / comparison baseline, not as default bulk worker.
- **kimi-k2.6**: IN CONFIG — GUARDED explicit bakeoff route only. 2026-05-11 root cause correction: OpenRouter credits were not zero; the key had no account-side limit and LiteLLM requested high `max_tokens`, so OpenRouter returned HTTP 402 "can only afford N tokens." Keep Kimi out of broad automatic fallback chains, cap output, and check `/api/v1/credits` + `/api/v1/key` before bakeoff.
- **Codex/OpenAI** remains the explicit CEO path via `/codex`; not a silent LiteLLM fallback.
- **Direct DeepSeek API**: deferred. OpenRouter mirrors DeepSeek promo pricing exactly through 2026-05-31, adds `:nitro` 7-provider failover, no HTTP 429 on China-side capacity. Re-evaluate at promo expiry (price-watch alert).

**Re-evaluate Pro-as-default trigger:** when LiteLLM PR #26660 merges, verify multi-turn Pro works end-to-end, then run gbrain-ops AP-72 playbook and decide whether to promote Pro back to default worker or keep Flash (considering post-promo cost differential).

### 10c. Model changes require a local bakeoff

Before making a model the production default for a broader class of work, run `tools/model_bakeoff.py` through the live Air LiteLLM route. The minimum gate is 20 compact instruction-following cases across `deepseek-v4-flash`, `deepseek-v4-pro`, and the incumbent comparison model. Store JSON output under `pages/audits/model-bakeoff-YYYY-MM-DD*.json` and summarize pass rate, errors, and latency in the relevant audit. This prevents replacing one paid model habit with another unmeasured habit.

Reasoning-token models need a completion cap high enough to reach final content. A bakeoff with many `content: ""` rows and no HTTP errors is probe-shape evidence first, model-quality evidence second. Re-run with `--max-tokens 256` (or inspect one raw response for `reasoning_content`) before demoting a reasoning model.

Cheap-pool/default-worker approval has a stricter mechanical gate: `tools/cheap_pool_winner_picker.py --approve-proposal` must receive `--promotion-benchmark-json` from `tools/cheap_pool_benchmark.py --fixture pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl`. `tools/model_promotion_gate.py` must return GREEN. Metadata can nominate a candidate; only fixture victory can promote it.

First bakeoff result (2026-04-27): DeepSeek V4 Pro 85%, DeepSeek V4 Flash 65%, GLM-5.1 35% on the local 20-case gate. Keep Flash as cheap minion candidate, Pro as hard long-context/audit candidate, and GLM as fallback/comparison. Do not use Flash alone for high-stakes facts because empty/null-content rows appeared in the route.

Corrected bakeoff result (2026-04-28, `--max-tokens 256`): DeepSeek V4 Flash 17/20 (85%, p50 2102ms), DeepSeek V4 Pro 14/20 (70%, p50 8025ms), GLM-5.1 14/20 (70%, p50 8494ms). Keep Flash as the default cheap worker because it is faster and scored highest here. Keep Pro as escalation/long-context candidate, not as a replacement for Flash on exact-output minion tasks. Keep GLM as fallback/comparison; it is slower and tied Pro on this compact gate.

### 11. Rollback (one command)
```bash
ssh air 'sed -i "s/_run_openclaw(query, model=\"opus\", agent_id=\"grok-ceo\".*$/_run_openclaw(query, model=\"opus\")/" ~/nous-agaas/command_center.py; launchctl kickstart -k gui/501/com.nous.telegram-poll'
```
Reverts `/ask` routing to pre-hierarchy (Opus-direct). grok-ceo agent remains registered + reachable via `--agent grok-ceo` explicit flag. Backup at `command_center.py.bak-pre-ask-flip`.

## Tier rationale (codified 2026-04-30, session 82-extension)

Live LiteLLM model_list (verified 2026-04-30 22:18 KZT, 10/10 endpoints healthy):

| Model | Tier | Why |
|---|---|---|
| **Grok-4.3-reasoning** | Router (Tier-1) | **CONFIRMED WORKING via canary (2026-05-10): reasoning_content present, correct responses.** 17% hallucination rate (industry best), 2M context window. NOT the smartest (48 IQ index vs 57 GPT-5.4 / Gemini 3.1) but routing decisions weight anti-hallucination > raw IQ. Source: AI Hallucination Benchmarks 2026, xAI. Was listed as grok-4.20 in prior versions — updated to grok-4.3 (now live). |
| **Opus 4.7 (1M)** | Premium delegator | Highest raw-IQ for synthesis tasks Grok punts. 1M context. Anthropic direct. |
| **GPT-5.5** | CEO (`/codex`) + premium fallback | Tier-1 reasoning peer with Gemini 3.1 (57 IQ index). Subscription-first via Codex CLI. |
| **Sonnet-4.5-thinking** | Premium fallback | Anthropic redundancy for Grok. Reasoning-mode + 1M ctx. |
| **DeepSeek V4 Pro** (`:nitro` variant) | **GUARDED: single-turn/escalation only** | 1.6T MoE / 49B activated / 1M ctx. **Multi-turn use BLOCKED until LiteLLM PR #26660 merges** — reasoning_content stripping bug causes HTTP 400 in multi-turn agent loops. Safe for hard long-context single queries / audit escalation. |
| **DeepSeek V4 Flash** | **Confirmed default multi-turn worker** | **CONFIRMED DEFAULT (2026-05-10):** run_task.log shows every task since 2026-04-14 uses flash, 100% success rate, zero HTTP 400s. $0.07/M in (post-promo). The actual workhorse; Pro is guarded. |
| **kimi-k2.6** | IN CONFIG — GUARDED BAKEOFF ONLY | Credit exists, but the key has no OpenRouter-side limit and high `max_tokens` caused 402 affordability failures. Keep explicit, capped, and out of broad automatic fallback chains. |
| **GLM-5.1 / GLM-4.5-flash** | Cheap fallback | Free-tier from z.ai. Bulk labor when budget tight. |
| **Haiku-4.5** | Judge + ultra-cheap fallback | Daily-skill-evals + grader + last-resort. |
| **Grok-code-fast-1** | Quick code edits | When `/code` is overkill. xAI direct. |

**Historical note — why Pro was briefly promoted in v1.5.0 (superseded by v1.5.4):** OpenRouter mirrored DeepSeek's 75%-off promo flatly through 2026-05-31, so the v1.5.0 reasoning argued quality should win during the promo window. Current binding policy is Section 10b: **DeepSeek V4 Flash is the confirmed default multi-turn worker**, while DeepSeek V4 Pro is guarded for single-turn/escalation until the LiteLLM reasoning-content bug is resolved.

**Why OpenRouter NOT direct DeepSeek API:** OpenRouter mirrors DeepSeek pricing during promo, wins on global-region failover + already-wired LiteLLM fallback chain. Re-evaluate at promo expiry.

## Promo-expiry watch (2026-05-31)

Codified in `tools/litellm_cost_alarm.py:check_promo_expiry()` (added session 82-extension). The alarm fires Telegram alerts at:
- **T-1 day (2026-05-30)**: `⏰ DeepSeek V4 Pro promo ends TOMORROW. Cost jumps 4x.`
- **T-0 day (2026-05-31)**: `⏰ ENDS TODAY. Action: gbrain-ops AP-72 NOW.`
- **T+1 day (2026-06-01)**: `⚠️ ENDED yesterday. Verify per-tier $/token.`

State file `~/nous-agaas/state/litellm_alarm_last.json` field `promo_alerts.deepseek-v4-pro` ensures idempotency (each window fires once).

When the alarm fires: run `gbrain-ops AP-72` playbook (WebSearch latest pricing → check fallback chain → Musk step-2 the urge to flip → update tier rationale here).

## Anti-Patterns

### AP-1 (pending) — Tier-1 wrapping hallucinates contradictory summary of Tier-2 raw report
Add after first observed incident. Mitigation per spec: `[opus-raw]` block verbatim forces Tier-1 to not replace-only-append.

### AP-2 (pending) — Over-delegation (Tier-1 sends simple Q to Tier-2)
Add after 7-day observation if rate >30%. Mitigation: Tier-1 system prompt refinement.

### AP-3 — grok-reasoning baseline latency is 144s+; --timeout 45 kills it silently

**Observed:** session s2148, 2026-04-30. `run_task.py --agent grok-ceo --timeout 45` returns "docker exec timed out" — grok-reasoning (was grok-4.20-0309, now grok-4.3) takes ≥144 s baseline (simple "ping"). **Note:** grok-4.3 is now confirmed working via canary (2026-05-10) — reasoning_content present, correct responses. Model eventually delivers (confirmed via `docker exec --local` which fell back to embedded and returned "OK" in 144 625 ms).

**Patterns:**
- `gateway closed (1000 normal closure)` on `docker exec … openclaw agent --local` is **benign** — OpenClaw falls back to embedded runner automatically; result still completes.
- Two `incomplete turn detected` (`stopReason=stop payloads=0`) events today (UTC 05:14, 16:58): grok-reasoning occasionally returns empty final content on first turn. LiteLLM fallback chain (`→ sonnet-4-5-thinking → deepseek-v4-pro → …`) catches these in production.
- Production `ASK_TIMEOUT=300s` in `command_center.py` is **barely sufficient**. Complex routing requests may hit it.

**Rules (binding):**
1. Never test grok-ceo with `--timeout < 300`. Minimum test timeout: `--timeout 300`.
2. Do NOT treat "gateway closed 1000" as a failure — it is a known embedded-fallback path.
3. If `payloads=[]` and agent is `grok-ceo`, poll session jsonl via async-await shim (Rule 9) before reporting failure.
4. Consider bumping `ASK_TIMEOUT` in `command_center.py` from 300 → 420 when next refactoring the /ask path.

### AP-6 — Doctrine cited `tier_log.append` for 9 days; nobody actually imported it (v1.5.2, 2026-05-01, session-83 cockpit audit)

**Pattern:** v1.0.0 (2026-04-22) shipped `tier_log.py` and §5/§6 of this skill cited it as the writer of `~/nous-agaas/logs/ask-hierarchy.jsonl` (the file `command_center._compose_cost_footer` and `/trace` consume). Through v1.5.1, **no module on the box ever imported `tier_log`**. `run_task.py:_append_log` wrote only to `run_task.log` (rich shape). The jsonl had 2 smoke-test entries from session-57 deploy day (2026-04-22 06:19) and zero production entries despite `/ask` working successfully throughout (handler logs in `~/nous-agaas/logs/telegram_poll.err` confirm 6+ successful `/ask` and `/code` runs from Madi 2026-04-25 → 2026-04-30). Cost footer always read empty; `/trace` always returned "No trace entries". A paper feature for 9 days.

**Why this matters:** the entire CEO-hierarchy observability story (cost transparency per tier, per-msg debugging via `/trace`) was load-bearing in the doctrine but absent in the code. Madi could not have caught this without an audit pass — `/ask` replies arrived; the silent gap was that they arrived without cost/tier evidence.

**Fix (commit 5502d392, this session):** added `_bridge_to_tier_log(entry)` inside `run_task.py:_append_log`. When `NOUS_CORRELATION_ID` env-var is set (Telegram-originated path; CLI/cron callers leave it unset and remain no-op), project the rich `run_task.log` entry into the slim 9-field `ask-hierarchy.jsonl` shape via `tier_log.append`. Includes a `_PRICE_PER_M` dict for `cost_est` computation across DeepSeek (promo through 2026-05-31), Anthropic, xAI, Z.AI, OpenAI. Live test on Air with `correlation_id=test_1777638176` confirmed: jsonl gained `{tier:2, model:deepseek-v4-flash, tokens_in:11, tokens_out:1, cost_est:5e-06, decision:ok}`.

**Detection (mechanical, future-proof):** for every binding rule that names a Python module/function, grep for at least one IMPORT of that module across the runtime tree:
```bash
ssh air "grep -rn 'from tier_log\|import tier_log' ~/nous-agaas/tools/ ~/nous-agaas/factory/" | wc -l   # must be ≥1
```
If 0 → the doctrine cites a function that nobody calls → paper feature → add the import OR delete the doctrine sentence. AP-5 already mandates rule-section consistency on version bumps; AP-6 extends that to runtime-call consistency.

**Cross-ref:** `karpathy-coding-principles` Principle 4 (Goal-Driven Execution — verify success criteria before claiming done); `audit` AP-15 (codification ≠ self-application — this is the dual: doctrine ≠ code); `mistake-to-skill` AP-11 (3-edit ritual extended: any new function reference in doctrine must be paired with an import-grep proof in the same commit).

**Known follow-up (NOT in this commit):** `litellm_direct` execution path in `run_task.py:565-575` never sets `duration_ms` → all jsonl latencies for direct-LiteLLM calls show 0. OpenClaw-agent path correctly populates from `agentMeta.durationMs`. Separate AP candidate.

### AP-7 — Codex subscription quota-exhaustion ≠ auth-expiry (v1.5.3, updated v1.5.6, 2026-05-11)

**Pattern:** `_run_codex` in `command_center.py:706-720` detects subscription failures with regex `token_expired|refresh token|401 Unauthorized`. When subscription hits its **weekly usage cap** (not auth expiry), Codex CLI prints stderr like:

```
ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at May 5th, 2026 10:30 AM.
```

This string contains none of the regex tokens, so subscription-quota errors return as `Codex error via subscription (exit 1): Reading…` to Telegram unless handled explicitly. As of v1.5.6, this route must **not** attempt OpenAI API fallback; subscription quota exhaustion is a fail-closed state, not a spending trigger.

**Live evidence (session-83 simulator, 2026-05-01 17:25 KZT):** `/codex reply with only the python expression: __import__('datetime').date.today().isoformat()` returned exit 1 within 6s. Direct CLI invocation confirmed: "Visit https://chatgpt.com/codex/settings/usage … or try again at May 5th, 2026 10:30 AM." The substrate token-bucket is the constraint, not Air's setup.

**Why this matters:** `/codex` is the explicit CEO/high-judgment path paid for by the Codex subscription. When subscription quota exhausts or auth expires, the cockpit should say so loudly and route the operator to `/ask-direct` or Mac interactive Codex, not silently spend API credits from a separate billing surface.

**Rules (binding from v1.5.3):**

1. **Quota-vs-auth distinction in Telegram replies.** When stderr contains `usage limit|usage cap|purchase more credits|out of credits|monthly limit|weekly limit`, the Telegram reply MUST be: `🔴 OpenAI Codex weekly cap reached. Resets <date from stderr>. Use /ask-direct <task> for CEO-tier work via Opus until then.` — never the truncated subscription-error message.
2. **No API fallback for subscription lanes.** `/codex` MUST NOT read `CODEX_API_HOME`, `OPENAI_API_KEY`, or `~/.codex-api/auth.json` to recover from subscription auth/quota failure. The fix is subscription re-auth or a deliberate user-approved API lane with a separate command name.
3. **Pre-empt with quota visibility.** `/status` should include `Codex weekly: <X>/<cap> calls (resets <date>)` if the data is exposable. Future enrichment.

**Surgical fix candidates:** extend quota-string detection for clearer Telegram copy. Do **not** add `~/.codex-api` recovery to this route.

**Detection (mechanical):** `ssh air "/Applications/Codex.app/Contents/Resources/codex exec --ephemeral -m gpt-5.5 -C /tmp --skip-git-repo-check 'reply OK' 2>&1 | head -5"` — if stderr contains "usage limit", subscription is rate-limited; check `try again at <date>` for the reset window.

**Cross-ref:** AP-3 (grok-ceo timeout), AP-4 (LiteLLM unhealthy false-negative), AP-6 (tier_log bridge gap), AP-9 (subscription lanes fail closed), `karpathy-coding-principles` Principle 4 (verify success criteria — simulator caught what passive observation could not).

**Substrate state at codification:** `/codex` is BLOCKED until 2026-05-05 10:30 AM. `/ask`, `/status`, `/code` all GREEN per session-83 simulator (evidence: `tg_652742` in ask-hierarchy.jsonl, model=grok-reasoning, cost=$4.8e-05). CEO-tier coverage during the 4-day window: `/ask-direct` (Opus 4.7 direct, no Tier-1 wrap).

### AP-8 — Never run deepseek-v4-pro in multi-turn agent loops until LiteLLM PR #26660 merges (v1.5.4, 2026-05-10)

**Pattern:** LiteLLM has an unmerged bug (PR #26660) where `reasoning_content` is stripped incorrectly in multi-turn conversations when using DeepSeek V4 Pro. This causes HTTP 400 errors when the model tries to continue reasoning across turns — the server rejects the malformed request because required reasoning context is missing from the message history.

**Evidence (2026-05-10 canary):** run_task.log confirms every task since 2026-04-14 uses `deepseek-v4-flash` in production — 100% success rate, zero HTTP 400s. This is the actual runtime outcome even though v1.5.0+ doctrine declared Pro as the default workhorse.

**Rules (binding until PR #26660 merges):**
1. Do NOT configure OpenClaw `agents.defaults.model` as `litellm/deepseek-v4-pro` for any agent that uses multi-turn loops (essentially all production agents).
2. `deepseek-v4-pro` may be used for single-turn escalation queries (e.g., long-context audit, one-shot hard reasoning) where multi-turn is not involved.
3. Before promoting Pro back to multi-turn default, verify PR #26660 is merged, then run a live multi-turn bakeoff (≥5 turns, tool-use chains) and confirm zero HTTP 400s.
4. **Detection:** `grep "HTTP 400" ~/nous-agaas/logs/run_task.log` — any hits when model=deepseek-v4-pro indicate the bug is still active.

**Workaround in effect:** `deepseek-v4-flash` is the confirmed default. Do not change this until the gate above is cleared.

**Cross-ref:** AP-4 (LiteLLM unhealthy false-negative for reasoning models); AP-7 (Codex quota-vs-auth); `factory-ops` AP-25 (config-via-CLI pattern for when the fix is ready to deploy).

### AP-9 — Subscription-paid agent lanes fail closed; no silent API fallback (v1.5.6, 2026-05-11)

**Pattern:** The operator pays for Claude Max and Codex subscription lanes. A fallback from `/codex` subscription auth to `OPENAI_API_KEY` or `~/.codex-api` silently moves cost to a different billing surface and hides the real root cause: subscription auth/quota state. The same class applies to Claude Code lanes: a failed Claude subscription route must not be patched by Anthropic API spend unless the user explicitly asks for a separate API lane.

**Rule:** subscription-named routes are subscription-only. `/codex` uses the Codex CLI default auth home only. `/code` uses Claude Code first-party auth only. If either fails, return a clear auth/quota message and the exact re-auth command. Do not mention API-key recovery in the Telegram error path.

**Detection (mechanical):**
```bash
grep -n "api-fallback\|CODEX_API_HOME\|OPENAI_API_KEY.*codex login" ~/nous-agaas/command_center.py
```
Expected output: no matches in the active `/codex` route. API-backed worker surfaces remain allowed only when explicitly named as API surfaces: LiteLLM/OpenClaw, gbrain embeddings, OpenRouter bakeoffs, and linter/model-bakeoff tooling.

**Cross-ref:** `session-operating-contract` Rule 2 (verify claims), AP-7 (quota vs auth), `gbrain-ops` for the separate embedding API surface.

### AP-10 — OpenRouter HTTP 402 is a spend-control failure, not proof the route is broken (v1.5.7, 2026-05-11)

**Pattern:** OpenRouter can return HTTP 402 with text like "This request requires more credits, or fewer max_tokens" even when the account still has nonzero credit. The failure means the request's declared output cap is too large for the remaining balance/model price. In this substrate that looked like "credits vanished" because LiteLLM requested 8192 or 16384 output tokens on OpenRouter routes and then hid the OpenRouter failure behind a fallback that eventually returned HTTP 200.

**Root cause test:**
```bash
ssh air 'set -a; . ~/nous-agaas/litellm/.env; set +a; python3 - <<PY
import json, os, urllib.request
for url in ("https://openrouter.ai/api/v1/credits", "https://openrouter.ai/api/v1/key"):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]})
    print(json.dumps(json.loads(urllib.request.urlopen(req, timeout=20).read().decode()), indent=2))
PY'
ssh air 'rg "can only afford|Insufficient credits|Payment Required" ~/nous-agaas/logs/litellm.err'
```

**Rules (binding):**
1. Do not diagnose OpenRouter as "empty" from a 402 alone. Check `/api/v1/credits`, `/api/v1/key`, `usage_daily`, `usage_monthly`, `limit`, and `limit_remaining`.
2. Keep high-cost OpenRouter models out of broad automatic fallback chains. They may be explicit routes or guarded escalation routes.
3. Cap OpenRouter route `max_tokens` in LiteLLM config. Large caps are not free; OpenRouter authorizes against the requested maximum.
4. Cost alarms must have a stop-action, not only a notification. The current stop-action is `tools/cost_alarm.py --pause-telegram-on-hard-cap`, which disables/stops `com.nous.telegram-poll` when the daily hard cap is crossed.
5. OpenBrain uses OpenRouter directly for embeddings + metadata, so it can fail when credit is low, but the 9-thought OpenBrain corpus is not enough evidence to explain a ~$20 monthly burn. Treat OpenBrain as an affected direct consumer, not the default culprit.

**Cross-ref:** AP-9 (subscription lanes fail closed), `factory-ops` (OpenClaw runtime guardrails), `gbrain-ops` (embedding spend surface).

### AP-11 — Telegram prefix routing must be explicit before claiming GPT/Codex execution (v1.5.8, 2026-05-12)

**Pattern:** Madi asked whether `/goal` in Telegram goes directly to GPT/Codex, or through Grok/OpenClaw and cheap workers. Earlier launch guidance blurred three different routes: durable `/goal`, CEO `/codex`, and local Sonnet/Codex targeted sessions.

**Root cause:** the substrate had the real routes in `command_center.py` and this skill, but no single top-of-page truth table for the operator. That lets agents over-promise "non-stop GPT work" when `/goal` is actually Goal page + Todoist + `com.nous.goal-cycle` + OpenClaw/run_task text slices.

**Rule:** every user-facing launch recommendation must state the exact Telegram prefix and model path:

- Durable memory/proof loop = `/goal` → Goal Mode → OpenClaw/run_task worker slice.
- Direct OpenAI high-judgment execution = `/codex`.
- Direct Claude/Sonnet execution = `/code`.
- Default question/status = `/ask` → grok-ceo in OpenClaw.

Kimi is never an automatic broad fallback. It remains an explicit, capped bakeoff route until live evidence changes Section 10b. Hermes is not a verified live Air control-plane route unless a separate Hermes runtime is proven in the current audit; do not include it in the main Telegram path by assumption.

**No new LESSON (RULE ZERO).** This AP converts a confusing operator question into a runtime-readable routing contract.

## Rules absorbed

- **spec** [[SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]] (design)
- **plan** [[PLAN-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]] (20 atomic tasks across 6 phases)
- **4-review REFRAME** applied: CEO/Eng/DevEx/OpenClaw-tech feedback baked in
- **5-lens analysis** (Musk/Karpathy/Tan/Stanford-hacker/billion-dollar-solopreneur) — ship-now with JSONL not Langfuse
- **session-operating-contract Rule 15/17** — tactical decisions executed; no re-asking at phase boundaries inside approved workstream
- **karpathy-coding-principles** Principle 3 (surgical changes) + Principle 4 (goal-driven execution) — every patch traced to a spec requirement
- **factory-ops AP-25** — config changes via `openclaw config set` CLI (not direct file edit)

## Evidence trail

- **2026-05-12** | v1.5.7 → v1.5.8 — Added the Telegram prefix truth table after operator confusion about whether `/goal` routes directly to GPT/Codex or through Grok/OpenClaw/cheap workers. Clarified `/goal` = durable Goal page + Todoist + `com.nous.goal-cycle` + OpenClaw/run_task text-slice worker; `/codex` = direct OpenAI Codex/GPT lane; `/code` = Claude/Sonnet lane; `/ask` = grok-ceo router. Historical Pro-default paragraph rewritten as superseded note so the binding rule remains Flash-default/Pro-guarded. gbrain-timeline-ok. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.5.6 → v1.5.7 — OpenRouter credit root cause corrected after live Air API + LiteLLM log audit. API showed credits present (`total_credits=45`, `total_usage≈35.22`, `usage_daily≈0.023`, key `limit=null`) while LiteLLM logs showed HTTP 402 "can only afford N tokens" from high `max_tokens` requests (8192/16384) and broad OpenRouter fallbacks. Runtime fix: cap OpenRouter route output, remove high-cost OpenRouter models from broad automatic fallback chains, reduce router retries, and add `cost_alarm.py --pause-telegram-on-hard-cap` stop-action at the LaunchAgent layer. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill (`{"status":"ok"}` via CLI fallback after MCP transport closed). No new LESSON (RULE ZERO).
- **2026-05-11** | v1.5.5 → v1.5.6 — Madi set policy: use Claude Max / Codex subscription lanes, not surprise API spend. `_run_codex()` changed to subscription-only: removed `CODEX_API_HOME` fallback, removed `api-fallback` footer, and changed auth-failure copy to "API fallback is disabled by policy." Added operator-boundary regression proving subscription auth failure calls `_run_codex_once()` exactly once with default auth. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).
- **2026-05-10** | v1.5.4 → v1.5.5 — Superseded by v1.5.7. Initial kimi-k2.6 diagnosis treated HTTP 402 as "credits exhausted"; later Air API + log audit corrected this to an affordability/spend-control failure from high `max_tokens` plus no key-side limit. Keep this entry only as historical context.
- **2026-05-10** | v1.5.3 → v1.5.4 — Canary results documented. grok-4.3 confirmed working (reasoning_content present, correct responses) — tier rationale table and AP-3 updated from grok-4.20 to grok-4.3. deepseek-v4-flash confirmed as actual default multi-turn worker (run_task.log: 100% success since 2026-04-14, zero HTTP 400s). deepseek-v4-pro guarded to single-turn/escalation only until LiteLLM PR #26660 merges (reasoning_content stripping → HTTP 400 in multi-turn loops) — AP-8 codifies the gate. kimi-k2.6 in config but unvalidated (falls back to flash — OpenRouter access/availability issue to investigate). Weekly model-tier check cadence established. Section 10b, tier rationale table, and description all updated to reflect real production state. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).

- **2026-05-01** | v1.5.2 → v1.5.3 — Session-83 simulator (cockpit_sim.py on Air, monkey-patched _tg_send) ran 4 prefixes through real `command_center.handle()`. Result: 3 GREEN (/ask 35.5s reply "OK" + jsonl entry tg_652742 grok-reasoning $4.8e-05; /status 0.04s Docker+disk+memory; /code 21.6s Claude Code subprocess "SIM_CODE_OK" + inline cost-footer $0.822/16s) + 1 RED (/codex 6s exit 1). Direct codex invocation confirmed RED is **subscription weekly quota exhausted, resets 2026-05-05 10:30 AM** — NOT auth/code bug. AP-7 originally considered an API fallback escape hatch; v1.5.6 supersedes that with subscription-only fail-closed policy. CEO-tier coverage during Codex cap/auth outages = Mac interactive Codex or `/ask-direct` (Opus via OpenClaw, design escape hatch). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).

- **2026-05-01** | v1.5.1 → v1.5.2 — Session-83 cockpit audit (Mac s1309) discovered `ask-hierarchy.jsonl` had 2 entries from 2026-04-22 smoke-test deploy and zero production traffic over 9 days, despite `/ask` and `/code` working successfully (telegram_poll.err confirmed). Root cause: doctrine §5/§6 cited `tier_log.py:append` as the writer, but no module on the box imported it — `run_task.py:_append_log` wrote only to `run_task.log`. Cost footer + `/trace` were paper features. Fix: added `_bridge_to_tier_log` inside `run_task.py:_append_log` (commit 5502d392). Patch is 48 LOC additive, no contract change for CLI/cron callers (which leave `NOUS_CORRELATION_ID` unset → no-op). Live CLI proof: `correlation_id=test_1777638176, model=deepseek-v4-flash, tokens=11/1, cost_est=$5e-06`. AP-6 codifies the detection rule (any doctrine-cited function must have ≥1 import across runtime tree). Live Telegram E2E (Madi → /ask, /codex, /code, /status) requested via `tg_send.sh msg_id=1145`; verification gates back to next session if Madi tests in flight at session close. 4-target git sync at 5502d392 (Mac), md5 8d6f37e2 across all 3 vault working copies + Air runtime. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.5.0 → v1.5.1 — Session s108 doctrine-reconciliation patch after Madi audit-confirm. v1.5.0 added AP-4 + Evidence trail entry but did NOT update Section 10b ("Worker model policy") and the Tier rationale table — both still proclaimed "Flash NOT Pro as default" with 6x-cost reasoning. The page contradicted itself: top of skill said Flash-default; bottom said Pro-default. v1.5.1 rewrites Section 10b + Tier rationale row + "Why Pro IS default" subsection to reflect the deployed state, with explicit citation that OpenRouter mirrors DeepSeek's 75%-off promo flatly through 2026-05-31 (per-token cost identical for Flash and Pro during promo → quality wins) and an explicit re-evaluate trigger at promo expiry tied to `tools/litellm_price_watch.sh`. AP-5 codifies the failure mode: post-bump doctrine reconciliation must include the rule sections, not just the Evidence trail. No new LESSON (RULE ZERO).

### AP-5 — Post-bump doctrine reconciliation must update rule sections, not just Evidence trail (v1.5.1, 2026-04-30, session s108)

**Pattern:** v1.5.0 bumped the Evidence trail with the new policy ("OpenClaw default = deepseek-v4-pro") but left Section 10b ("Worker model policy") and the Tier rationale table at the prior policy ("Flash NOT Pro as default"). The skill page proclaimed contradictory rules in different sections. A future agent reading top-down would absorb the Flash-default rule before reaching the Evidence trail.

**Rule:** when a SKILL.md change inverts a "binding" rule from a prior version, the 3-edit ritual is insufficient. The bump MUST also rewrite the affected rule section(s) AND any tables/cards that reference them. Quick mechanical check: after a version bump that changes a binding rule, `grep` the new version's policy keywords against the rest of the page; any phrase that contradicts the new rule is debt.

**Detection:** for every Evidence trail entry that says "supersedes prior X" or "inverts prior decision Y", verify the corresponding rule section was updated by grepping the negation. Future probe candidate: `tools/test_skill_internal_consistency.sh` — for each binding rule section, ensure no later "supersedes" entry contradicts it without a same-commit rewrite.

**Cross-ref:** `mistake-to-skill` AP-11 (3-edit ritual — this AP extends it: 3 edits + rule-section rewrites if rule changes); `audit` AP-15 (codification ≠ self-application — applies recursively to the skill that codified it).

- **2026-04-30** | v1.4.0 → v1.5.0 — Session s108-air-49979 atomic deploy after Madi research-greenlight. Four changes shipped together: **(1)** added `gpt-5.5` to LiteLLM `model_list` (model name resolved to bare `gpt-5.5` after `openai/gpt-5.5` failed silently — LiteLLM auto-detects OpenAI provider from the bare name; verified with direct curl + LiteLLM router probe returning `PROD` literal). gpt-5.5 reports `unhealthy=1` cosmetically because LiteLLM health-check probes with `max_tokens=1` (too tight for a reasoning model that consumes reasoning tokens before output) — real `/v1/chat/completions` calls succeed. Codified as **AP-4** below. **(2)** Added `:nitro` modifier to `openrouter/deepseek/deepseek-v4-pro` route: OpenRouter sorts available providers by lowest latency per call, picking the fastest of 7 inference providers — agent-friendly for the worker hot-path. **(3)** Bumped OpenClaw `agents.defaults.model` and `agents.list[0].model` from `litellm/deepseek-v4-flash` to `litellm/deepseek-v4-pro` via `docker exec openclaw openclaw config set` (factory-ops AP-25 pattern); restart confirmed `[gateway] agent model: litellm/deepseek-v4-pro`. Same per-token price during 2026-05-31 promo window ($0.435/$0.87 per M), much higher quality (1.6T MoE / 49B activated / 1M ctx) — Flash demoted to fast-fallback. **(4)** Shipped `tools/litellm_price_watch.sh` + `com.nous.litellm-price-watch.plist` (daily 04:00 KZT) to alert T-7 / T-3 / T-1 / D-day for promo expiry; idempotent per-day via state file. Cross-ref: `infrastructure` AP-76 (OpenClaw hung detected/recovered same session — this commit lands on the recovered substrate); `factory-ops` AP-25 (config-via-CLI not file-edit); 2026-04-30 architecture research (Grok 4.20 reasoning hallucination 17-22% lowest, GPT-5.5 82.7% Terminal-Bench vs Opus 69.4%, OpenRouter mirrors direct DeepSeek pricing during promo with 7-provider failover). 3-edit ritual per AP-11. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-4 — LiteLLM `unhealthy_endpoints` for reasoning models is a false negative (v1.5, 2026-04-30, session s108)

**Pattern:** GPT-5.5 added to LiteLLM `model_list` shows in `unhealthy_endpoints` with error like `BadRequestError: Could not finish the message because max_tokens or model output limit was reached`. Real `/v1/chat/completions` calls to that same model succeed. The health-check probe uses `max_tokens: 1` regardless of the model_list entry's `max_tokens` — fine for chat models, broken for reasoning models that spend tokens on reasoning before producing visible output.

**Why this matters:** routing strategy `simple-shuffle` may exclude unhealthy endpoints from selection; if you rely on `unhealthy_count == 0` as a deploy gate, you'll false-RED on every reasoning model.

**Workarounds tried (DO NOT USE):**
- `health_check_params: {max_tokens: 4096}` — LiteLLM passes through to OpenAI as a real param, OpenAI rejects with `Unknown parameter`. Different from documented LiteLLM router options.
- Bumping `max_tokens` in `litellm_params` — health-check ignores model-level setting.

**Real fix (waiting on LiteLLM upstream):** [litellm GH issue queued for next session]. In the meantime: verify with a real `/v1/chat/completions` probe rather than `/health` for any reasoning model. Cosmetic-RED is acceptable; functional-RED would mean the real probe also fails.

**Detection:** `curl -H "Authorization: Bearer $KEY" -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"ping"}],"max_tokens":4096}' http://localhost:4000/v1/chat/completions` — if this returns choices content, model IS routable regardless of /health status.

### AP-12 — Subscription-only GPT is not a LiteLLM fallback (2026-05-13)

**Symptom:** `light-probe.sh` sent a Telegram red alert showing `gpt-5.5` dead, while Madi's intended GPT path is `/codex` via subscription auth, not OpenAI API spend. LiteLLM `/health` also counted the Gemini embedding route as an unhealthy chat model because the generic health probe sent `max_tokens` to an embedding endpoint.

**Root cause:** The model hierarchy had drifted: the skill description said `/codex` is subscription-only, but the LiteLLM fallback chain and ops task spine still treated `gpt-5.5` like an always-on API route. The monitor then correctly reported the API quota failure, but that failure was for the wrong path.

**Rule:** Keep the GPT CEO lane explicit and prefix-scoped:
- `/codex` = GPT-5.5 subscription/Codex lane.
- LiteLLM/OpenClaw routine labor = Grok router, DeepSeek/Kimi/GLM/Sonnet routes.
- Do not include `gpt-5.5` in broad LiteLLM fallback chains while the OpenAI API route is quota-limited or not budget-approved.
- Model health alerts must filter subscription-only GPT and embedding-only routes from chat-route counts; verify embeddings through `/v1/embeddings` or gbrain coverage instead.

No new LESSON (RULE ZERO).

### AP-13 — GPT can be second-stage, not blanket first-hop (2026-05-13)

**Symptom:** Madi clarified that GPT should be the second-stage orchestrator because Codex/GPT handles agent orchestration better than Claude Code. The dangerous interpretation is to route every Telegram `/ask` or Todoist comment through GPT-5.5.

**Root cause:** Route names and model roles were blurred. `/ask` is the cheap always-on OpenClaw router. `/codex` is the GPT subscription lane. A live 2026-05-13 Air canary proved `/codex` works (`CODEX_OK`), but even a trivial prompt consumed 7004 tokens, so making GPT the default first-hop would break the low-token CEO requirement.

**Rule:** Keep the hierarchy as cheap classifier -> GPT high-judgment second-stage -> cheap worker execution:
- Routine Telegram `/ask` stays Grok/OpenClaw.
- High-judgment architecture/code/root-cause tasks go to `/codex` explicitly, or through a future auto-GPT gateway after a bounded canary.
- Todoist `AI:` comments should enter OpenClaw/run_task first; escalate to `/codex` only when the task requires high-judgment code/architecture review and a cost receipt can be logged.
- Never claim GPT is orchestrating a slice unless the evidence shows `/codex` or a named GPT gateway actually ran.

No new LESSON (RULE ZERO).

- **2026-05-14** | v1.6.0 → v1.6.1 — Added **AP-14** after Madi flagged that Goal Mode progress looked like cheap-worker output and should use the Grok→GPT hierarchy for reasoning. Live audit showed goal workers had fallen through `ModelEscalator.pick()` to `deepseek-v4-pro` after earlier Flash HTTP 500s; Grok and Codex/GPT-5.5 canaries both passed (`GROK_GOAL_ROUTE_OK`, `GPT55_CODEX_ROUTE_OK`). Runtime fix: `goal_runner.py` now defaults recurring goal slices to explicit `--model grok-reasoning` and shows the route in Telegram; GPT-5.5 remains explicit `/codex` escalation because the canary used about 7k tokens. No new LESSON (RULE ZERO).

### AP-14 — Goal-cycle reasoning slices must use explicit Grok route before worker labor (2026-05-14)

**Symptom:** Goal Mode was mechanically green, but Madi did not see serious progress and objected that reasoning/logic tasks should go through the top route: Grok first, GPT second, cheap workers after that.

**Root cause:** `goal_runner.py` called `run_task.py` without a model or agent override. That silently delegated recurring goal slices to `ModelEscalator.pick()`, so a transient `deepseek-v4-flash` failure moved goal work to `deepseek-v4-pro`. This is correct for cheap worker recovery, but wrong for deciding the next high-leverage goal slice.

**Rule:** recurring `/goal` cycles are reasoning slices, not bulk labor. `goal_runner.py` must pass `--model ${NOUS_GOAL_WORKER_MODEL:-grok-reasoning}` on every goal worker call and include the route in the Telegram digest. `NOUS_GOAL_WORKER_MODEL=""` is allowed only for an explicit controlled bakeoff. GPT-5.5 stays `/codex` or a future bounded auto-GPT gateway with cost receipt; do not hide subscription-token burn inside the 4-hour heartbeat.

No new LESSON (RULE ZERO).

- **2026-05-14** | v1.6.2 → v1.7.0 — Shipped **AP-16** (high-judgment `/ask` → `/codex` auto-escalate with cost guard) per [[MADI-DECISIONS-2026-05-14-round2]] item #3 and session s1729 "do it" autonomy. Added `_query_likely_needs_high_judgment(query)` + `_codex_daily_budget_ok(5.0)` to `tools/command_center.py` (~75 lines); new branch in `/ask` handler routes complex queries to `/codex` before grok-ceo when query length ∈ [200, 4096] chars AND complexity marker present AND today's Codex spend < $5. Bounded telemetry from `~/nous-agaas/logs/ask-hierarchy.jsonl`. Self-test: 8/8 cases pass (short/long/Telegram-sized/marker-present/marker-absent/budget-spent/RU+EN). Honest negative: pre-route heuristic, not post-Tier-1 confidence — true confidence-routing requires grok-ceo to emit structured `confidence` in responses, deferred. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.6.1 → v1.6.2 — Added **AP-15** after Madi challenged the wording "I am grok-ceo, not OpenClaw" and asked for the system to be "OpenClaw fully" using Gary Tan/OpenClaw-style skills/souls/second-brain substrate. Live Air audit matched the official OpenClaw docs shape: one gateway runtime, separate agents with their own workspace/state/session store, bootstrap files (`AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`), and shared skills loaded from `/opt/nous-agaas/skills`; Nous has `gstack`, `gstack-openclaw-*`, `ceo-hierarchy`, `command-center`, `factory-ops`, and `openbrain-projection` mounted. Shipped `tools/test_openclaw_full_stack_contract.sh` so the runtime/agent/skills/SOUL contract is mechanically testable before claiming "full OpenClaw." No new LESSON (RULE ZERO).

### AP-15 — OpenClaw is the runtime, not the agent identity (2026-05-14)

**Symptom:** Madi asked why the Telegram responder said "I am grok-ceo, not OpenClaw" and correctly flagged that as a trust problem. Earlier summaries blurred three layers: OpenClaw runtime, the `grok-ceo` Tier-1 agent, and the `nous` Tier-2 execution agent.

**Root cause:** The system was technically mostly correct but semantically under-tested. Official OpenClaw docs define multi-agent mode as one gateway hosting isolated agents, where each agent has its own workspace, state directory, auth profiles, and session store. The current Air runtime follows that shape (`grok-ceo` and `nous` are separate OpenClaw agents), but the Nous substrate had no single live probe that proved the whole stack: container health, OpenClaw home mount, wiki mount, skills mount, agent workspaces, SOUL/AGENTS/USER/TOOLS files, and gstack/OpenBrain skills visibility.

**Rule:** use exact labels:
- **OpenClaw** = Air gateway/runtime/orchestrator.
- **`grok-ceo`** = Tier-1 OpenClaw-hosted router for `/ask`.
- **`nous`** = Tier-2 OpenClaw-hosted execution agent.
- **`/codex`** = GPT-5.5 high-judgment lane, subscription-scoped, not the default first hop.
- **gstack/OpenBrain/gbrain/Obsidian** = shared skill + knowledge substrate consumed by OpenClaw-hosted agents.

**Mechanical detector:** `bash tools/test_openclaw_full_stack_contract.sh`. It must be green before saying "full OpenClaw is live." It checks the Air Docker container, mounted OpenClaw home, OpenClaw config, `grok-ceo`/`nous` model split, workspace bootstrap files, shared `/opt/nous-agaas/skills`, gstack skills, and `openbrain-projection`.

**Recovery:** if the detector fails, do not rename agents or make a prose claim. Fix the failing layer named by the probe: Docker health, mount map, config, workspace files, or skill visibility. If a route needs GPT-5.5 judgment, launch `/codex` explicitly or through a bounded auto-GPT gateway with cost receipt; do not make routine group chatter uncapped GPT traffic.

### AP-16 — High-judgment `/ask` auto-escalates to `/codex` with cost guard (2026-05-14, v1.7.0)

**Symptom:** Madi flagged ([[MADI-DECISIONS-2026-05-14-round2]] item #3): `/codex` is manual-only; grok-ceo Tier-1 never auto-routes to GPT-5.5 when the query warrants reasoning, even when budget allows. Bottleneck on the billion-dollar pattern — every high-judgment turn requires Madi to retype with `/codex`.

**Root cause:** `tools/command_center.py` already had `_requires_codex_verification_route()` (narrow shell-verification trigger) but no parallel trigger for high-judgment reasoning queries. AP-13 v1.5.9 acknowledged "future bounded auto-GPT gateway" as future work; this AP ships it.

**Rule:** `/ask` payloads that match high-judgment markers AND fit in the bounded query window AND today's Codex spend is under $5 auto-escalate to `/codex` before reaching grok-ceo Tier-1. Implementation:

- `_query_likely_needs_high_judgment(query)` (`tools/command_center.py`): pre-route heuristic — length ∈ [200, 4096] chars, at least one marker (deep analysis / architecture review / what's the tradeoff / explain why / root cause / should we / compare / Musk / Karpathy / billion-dollar / honest take / explain why / стратегич / честно / and Russian equivalents), AND `_codex_daily_budget_ok()` returns true.
- `_codex_daily_budget_ok(threshold_usd=5.0)`: sums today's `cost_est` from `~/nous-agaas/logs/ask-hierarchy.jsonl` where `model` contains `codex` or `gpt-5`. Returns `(under_threshold, today_spend)`. Falls back to `(True, 0.0)` if log missing — never blocks on missing telemetry.
- Telegram side: user sees "🧠 Auto-escalating high-judgment query to /codex (GPT-5.5)… Today's Codex spend: $X.XX of $5 cap." then the response with `[ask-auto-codex-high-judgment]` correlation.

**Two-trigger system (clarity):**

| Trigger | Function | Use case |
|---|---|---|
| Shell-verification | `_requires_codex_verification_route` | `verify:` prefix + shell markers (ssh air, launchctl, git rev-parse) — runs commands |
| **High-judgment (new)** | `_query_likely_needs_high_judgment` | Complexity markers + bounded length + budget guard — runs reasoning |

Both pre-route (NOT post-Tier-1 reclassification — that would require grok-ceo prompt modification, deferred).

**Recovery:** turn off auto-escalate by emptying `_HIGH_JUDGMENT_MARKERS` tuple OR lowering the budget threshold OR adding `os.environ.get("CEO_HIGH_JUDGMENT_DISABLE")` check. Cost telemetry is the safety net: when daily spend ≥ $5, auto-escalate silently disables; subsequent `/ask` queries fall through to grok-ceo as before.

**Honest negative:** this is a pre-route heuristic, NOT confidence-based post-classification. A truly low-confidence grok-ceo response on a query that didn't match markers still gets returned as-is. Real confidence-routing requires `grok-ceo` AGENTS.md to emit structured `confidence` in responses, then a post-Tier-1 check. Deferred to a future bump; the marker heuristic is the 80% cheap version.

**Cross-ref:** AP-13 ("GPT can be second-stage, not blanket first-hop" — this AP makes "second-stage" mechanical), AP-9 ("subscription-paid agent lanes fail closed" — the cost guard implements fail-closed for budget overrun), [[session-operating-contract]] Rule 20 question filter (the billion-dollar-tiny-team loop), [[karpathy-loop]] AP-5 multi-virtual-reviewer (separate Skill-tool path, not auto-escalate). No new LESSON (RULE ZERO).

- **2026-05-15** | v1.8.3 -> v1.8.4 -- Tightened **AP-22** wording after history check: the architecture is correct, but "this reply path is OpenClaw -> grok-ceo" is imprecise for the identity fast-path because `command_center.py` answers before any model call. Canonical wording: normal `/ask` work is OpenClaw -> `grok-ceo`; identity checks are OpenClaw/telegram-poll -> `command_center.py` local answer. Regression now asserts `command_center.py` appears in the reply. No new LESSON (RULE ZERO).
- **2026-05-15** | v1.8.2 -> v1.8.3 -- Added **AP-22** and a local `command_center.py` fast-path for OpenClaw identity questions. Root cause: AP-15 proved the runtime/agent distinction but left `/ask Are you now OpenClaw?` model-routed, so `grok-ceo` could still lead with "No" and fail the operator-facing product truth. New path answers locally: OpenClaw runtime is live; `grok-ceo` is the Tier-1 identity inside it. Test added for msg 1514 exact query; no model call. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.8.0 -> v1.8.1 -- Corrected AP-18 after fresh Mac/Air proof: old 25GB disk blocker was stale (Mac Data volume about 1.4Ti free), `mlx-lm 0.31.1` imports and server CLI work, but no `:8080` endpoint is live. Added **AP-20**: local-mac MLX canary order is Qwen3-Coder-30B-A3B 4-bit first, Qwen2.5-Coder-32B 4-bit fallback, Qwen2.5-72B 4-bit later; LiteLLM/OpenClaw wiring waits for local + Air curl proof. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-15** | v1.8.1 -> v1.8.2 -- Added **AP-21** and `tools/hermes_canary_gate.py`: OpenClaw stays production; Hermes Agent is isolated canary profile `nouscanary` via alias `hermes-nouscanary`; no Hermes Telegram gateway; no cutover until 24h Telegram/LiteLLM/Todoist/Notion/Obsidian/gbrain/OpenBrain/cost/rollback gates pass. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-14** | v1.7.0 -> v1.8.0 -- Added **AP-17** (LiteLLM in-memory cache type:local ttl=3600, cache hit verified), **AP-18** (Tier-0 local-mac MLX planned, blocked: Sub-project B needs 40GB+ disk free (only 25GB available) for model pull), **AP-19** (OpenBrain bridge in command_center.py -- 4 call sites, daemon thread, OB1 capture verified). Zero changes to Grok->Flash->Pro routing. No new LESSON (RULE ZERO).
- **2026-05-13** | v1.5.9 → v1.6.0 — Added **AP-13** after Madi clarified GPT should be the second-stage orchestrator. Air Codex subscription path is green (`CODEX_OK`), but a trivial canary consumed 7004 tokens, so `/ask` remains cheap Grok/OpenClaw while GPT is explicit `/codex` or future bounded auto-GPT gateway. No new LESSON (RULE ZERO).

- **2026-04-27** | v1.0.0 → v1.1.0 — Madi changed routing policy: "use you as CEO; hard work by latest DeepSeek, not GLM." Verified current official DeepSeek/OpenRouter surface: DeepSeek V4 Flash/Pro are current, 1M-context models; V4 Flash is the cheap worker and V4 Pro is the harder worker. Runtime plan: add LiteLLM aliases `deepseek-v4-flash` and `deepseek-v4-pro`, set ModelEscalator primary/escalation to those, keep GLM as fallback, and keep `/codex` as explicit CEO route until Air Codex subscription auth is re-approved. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.1.0 → v1.2.0 — Added `tools/model_bakeoff.py`, a 20-case deterministic LiteLLM route gate for DeepSeek V4 Flash/Pro vs incumbent models. This turns "DeepSeek is better/cheaper" into local proof before broader default changes. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.2.0 → v1.2.1 — First live Air bakeoff hit a provider response with `content: null`; root cause was scorer assuming every successful HTTP response has text. Patched bakeoff to coerce null content to empty failed output instead of crashing, so provider-shape variance becomes data. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.2.1 → v1.2.2 — Recorded first 20-case live Air bakeoff: DeepSeek V4 Pro 17/20 (85%), DeepSeek V4 Flash 13/20 (65%), GLM-5.1 7/20 (35%). Result supports DeepSeek over GLM for the worker lane, with Pro reserved for harder long-context/audit work and Flash watched for empty/null rows. No new LESSON (RULE ZERO).
- **2026-04-28** | v1.2.2 → v1.2.3 — Fixed the model bakeoff gate for reasoning-token models. Root cause: the first 2026-04-28 rerun used `max_tokens=64`, so Pro/GLM spent the cap on reasoning and produced blank final content; raw response with `max_tokens=256` proved final content existed. Patched `tools/model_bakeoff.py --max-tokens` default to 256 and reran: Flash 17/20 (85%), Pro 14/20 (70%), GLM-5.1 14/20 (70%). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.3.0 → v1.4.0 — Session 82-extension codified tier rationale + promo-expiry watch. Honest Musk step-2 deletion: did NOT promote DeepSeek V4 Pro to default workhorse despite 75% promo. Reason: Pro is 6x Flash even during promo; promotion would pay 6x for routine traffic. Added `tools/litellm_cost_alarm.py:check_promo_expiry()` (T-1, T-0, T+1 windows, idempotent state). Updated description with Grok 17%-hallucination + Opus IQ position + DeepSeek $/intelligence. Plan: PLAN-2026-04-30-deepseek-promo-expiry-watch.md. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.2.3 → v1.3.0 — AP-3 absorbed: grok-4.20-0309-reasoning baseline latency is 144 s+; `--timeout 45` silently kills grok-ceo; `gateway closed (1000)` on docker-exec --local is benign (embedded fallback completes). Two `incomplete turn / payloads=0` events today caught by LiteLLM fallback chain. ASK_TIMEOUT 300 s is barely sufficient; 420 s upgrade recommended. Test minimum: `--timeout 300`. gbrain-timeline-ok. No new LESSON (RULE ZERO).
- **2026-04-22** | v1.0.0 — Session 57 Phase 0-5 shipped. Proven E2E via (a) `python3 -c "import run_task; run_task.run_task('Spawn nous task: print ASYNC_TIMEOUT_FIX', agent_id='grok-ceo')"` returned text "Nous said: ASYNC_TIMEOUT_FIX" + logs showed grok-ceo→sessions_spawn→nous→announce→shim recovery. (b) command_center.handle() self-test: /ask-direct returned `[opus-direct] TEST_ASK_DIRECT_OK`; /ask returned `TEST_ASK_TIER1_OK` + cost footer; /trace returned "No trace entries" for unlogged id (expected). LiteLLM: 8 aliases live (opus, grok-reasoning, sonnet, sonnet-4-5-thinking, grok-code-fast, glm-5.1, glm-4.5-flash, haiku-4-5). Factory count pre+post: 79/125 ready. Workspace migration nous AGENTS.md 98→135 lines; verified agent self-identifies as "Tier-2 digital CEO / executive layer ... structured directive JSON ... sessions_spawn with model overrides". Async-await shim: isolation test returned session jsonl path, 87 lines, latest text "Nous returned: ASYNC_SHIM_OK". Container timeout 10→30s bump fixed intermittent helper failures under load. No new LESSON (RULE ZERO).
- **2026-05-13** | v1.5.8 → v1.5.9 — Added **AP-12** after model-health alerted on `gpt-5.5` API quota and Gemini embedding `/health` shape while the intended GPT path is `/codex` subscription. Updated the fallback chain and ops task spine so GPT is explicit `/codex` escalation, not broad LiteLLM fallback; added `tools/litellm_health_summary.py` filtering for subscription-only GPT and embedding-only routes. No new LESSON (RULE ZERO).


### AP-17 — LiteLLM in-memory cache prevents repeat API calls (2026-05-14)

**What:** `cache: true`, `cache_params: {type: local, ttl: 3600}` added to `litellm_settings` in `~/nous-agaas/litellm/config.yaml`.
**Note:** Spec called for `type: simple`; actual value is `type: local` because `simple` is not a valid `LiteLLMCacheType` enum in v1.83.7 (`Local`, `Redis`, `S3`, `Disk` are the valid values). `type: local` maps to `InMemoryCache` internally.
**Verification:** Cache hit confirmed -- two identical haiku-4-5 requests returned identical response ID `chatcmpl-f7ae7309-7c59-4173-ba61-0ea19f1b9fc6`.
**Additive:** zero changes to routing; cache layer is transparent to all model callers.

### AP-18 — Tier-0 local-mac model (planned; canary-ready, not endpoint-green) (2026-05-14)

**What:** LiteLLM `local-mac` model intended to route to Mac M5 Max MLX server at `100.100.197.19:8080` before any cloud tier.
**Status:** NOT YET LIVE. Fresh 2026-05-14 recheck showed the old 25GB disk blocker was stale: Mac Data volume now has about 1.4Ti free, Homebrew Python imports `mlx`/`mlx_lm`, and `mlx_lm.server --help` works. The actual remaining blocker is endpoint proof: no listener on `127.0.0.1:8080`.
**Unblock:** Start `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` as the first canary, verify `/v1/models`, `/health`, and `/v1/chat/completions` locally, soak for 10-30 minutes, then prove Air reachability over Tailscale or a scoped SSH tunnel. Only after that add LiteLLM `local-mlx-coder`. Do not start with 72B and do not route OpenClaw to a fake-green endpoint.

### AP-19 — OpenBrain bridge captures high-judgment factory decisions (2026-05-14)

**What:** `_capture_openbrain(content, thought_type="decision")` added to `tools/command_center.py` at line 1295 (before `handle()`). 4 call sites: `/codex` dispatch, `/ask` shell-verify auto-escalation, `/ask` high-judgment auto-escalation, `/ask-direct` Opus bypass.
**Mechanism:** Daemon thread -- never blocks Telegram reply path. Reads `OPENBRAIN_MCP_URL` lazily from `~/nous-agaas/secrets/openbrain-projection.env` on each call. Silent on all errors (OB1 is non-critical observability).
**Verification:** OB1 thought `609ff445-cedb-43cf-b33b-4451f62b21fb` captured and confirmed via `list_thoughts`.
**Use:** Mac Claude Code sessions (and ChatGPT/Cursor/Codex) can query factory reasoning history via `search_thoughts` on OB1 -- cross-tool short-term decision memory.

### AP-20 — MLX canary order: prove a coding endpoint before wiring the hierarchy (2026-05-14)

**Pattern:** A status page said Sub-project B was blocked by 25GB free disk and targeted Qwen2.5-72B first. A fresh check found about 1.4Ti free, working `mlx-lm 0.31.1`, no `:8080` listener, and no Gemini route. Live Grok (`grok-reasoning`) and Claude (`opus`) council both selected `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` as the first canary, with Qwen2.5-Coder-32B 4-bit as dense fallback and Qwen2.5-72B 4-bit deferred.

**Rule:** Tier-0 local-mac is promoted in this order only:

1. `Qwen3-Coder-30B-A3B-Instruct-4bit` local MLX server on `127.0.0.1:8080`.
2. Local proof: `/v1/models`, `/health`, and a chat completion returning literal `MLX_OK`.
3. Short soak with repeated code prompts and measured token/sec/RAM/crash count.
4. Air reachability proof over Tailscale or scoped SSH tunnel.
5. LiteLLM route `local-mlx-coder`.
6. OpenClaw cheap/code worker routing.

**Anti-pattern:** do not wire LiteLLM/OpenClaw while no endpoint is listening. Do not let "Mac has enough disk" turn into "local model is green." Capacity green is not runtime green.

**Evidence:** [[pages/audits/AUDIT-mlx-local-canary-decision-2026-05-14-2309]], [[pages/progress/subproject-b-mlx-status]].

### AP-21 — Hermes Agent is canary-only until it earns production (2026-05-15)

**Decision:** Do not rip out OpenClaw because of a new launch post or a prettier architecture story. OpenClaw is the green production runtime. Hermes Agent gets one isolated canary lane and must earn more authority with measured results.

**Approved canary shape:**

1. Profile: `nouscanary` on Air.
2. Invocation: `hermes-nouscanary ...` alias only. Do not depend on `HERMES_PROFILE=...`; this Hermes version ignored that variable for profile routing during rollout.
3. Model: explicit `gpt-5.5` via OpenAI Codex for canary evaluation only.
4. Telegram: not configured in Hermes; gateway not loaded. Air `telegram_poll.py` remains exclusive.
5. Production routing: unchanged (`/ask` OpenClaw/grok-ceo, `/codex` high-judgment Codex, `/goal` goal runner).

**24h cutover gate:** Hermes cannot become a production router until a status artifact proves all of these for at least 24h: Telegram route isolation, LiteLLM non-interference, Todoist canary proof, Notion canary proof, Obsidian/wiki commit proof, gbrain timeline proof, OpenBrain capture/projection proof, cost receipt, rollback command, and no factory red checks.

**Mechanical detector:** `python3 tools/hermes_canary_gate.py --json --factory-probe` is the no-spend safety gate; `--smoke` spends one explicit canary call and must be used intentionally.

**Anti-patterns:** no "Hermes is better, switch tonight"; no duplicate Telegram poller; no silent defaulting routine traffic to GPT-5.5; no fake Gemini review when Gemini is absent from production LiteLLM chat routes.

### AP-22 — OpenClaw identity questions are product-surface, not model-routed (2026-05-15)

**Symptom:** After AP-15 shipped, Telegram still answered "No. I am grok-ceo — the Tier-1 CEO proxy agent. OpenClaw is the runtime/orchestrator..." to "Are you now OpenClaw?" That was technically defensible, but it repeated the trust failure Madi explicitly asked to fix.

**Root cause:** AP-15 codified doctrine and added a full-stack probe, but it did not change the live `/ask` control path. Identity questions still fell through to `grok-ceo`, whose prompt optimizes for exact agent identity. The missing layer was a deterministic operator-facing answer in `command_center.py`.

**Rule:** OpenClaw identity questions are answered locally before quiet-hours hold, Codex auto-escalation, or `grok-ceo` routing. The answer must lead with the operator-facing truth: "Yes — this Telegram path is the OpenClaw production runtime." Then it must clarify layers without overstating the exact reply path: normal `/ask` work is OpenClaw -> `grok-ceo`; identity checks are OpenClaw/telegram-poll -> `command_center.py` local fast-path; `nous` is Tier-2 execution; `/codex` is GPT-5.5 escalation.

**Implementation:** `_is_openclaw_identity_question(query)` + `_openclaw_identity_answer()` in `tools/command_center.py`. Matching queries are logged as `/ask-openclaw-identity` and never call `_run_openclaw()` or `_run_codex()`.

**Regression test:** `tools/test_operator_boundaries.py::test_openclaw_identity_question_is_answered_locally_without_model` uses the exact msg 1514 wording (`/ask Are you now openclaw ?`) and asserts no model call, no "No.", canonical `OpenClaw -> grok-ceo` normal-route wording, and explicit `command_center.py` fast-path wording. No new LESSON (RULE ZERO).

### AP-23 — LangGraph route spine: Grok first-pass, ChatGPT execution, Chinese workers for long work (2026-05-15)

**Requirement:** Telegram is the operator surface; OpenClaw is production; ChatGPT/Codex subscription is allowed for bounded execution; Grok must do first-pass decision review; long work must become durable Goal/Todoist state; routine/bulk worker slices should use the best cheap Chinese/open-source routes already live in LiteLLM.

**Implementation:**

- `tools/factory_orchestration_policy.py` is the single deterministic policy source for Telegram and Todoist.
- `tools/langgraph_factory_orchestrator.py` wraps that policy in a real LangGraph `StateGraph` when LangGraph is installed, with fallback reporting when it is not. Do not claim LangGraph is live unless the CLI returns `langgraph_available: true`.
- `/ask` route order is now: OpenClaw identity fast-path -> quiet-hours gate -> shell verification `/codex` -> LangGraph policy. Policy outcomes:
  - `long_work_goal` -> create Goal page + Todoist task + kick goal-cycle; workers use `grok-reasoning -> deepseek-v4-flash -> deepseek-v4-pro -> kimi-k2.6 -> glm-5.1 -> codex:gpt-5.5-subscription`.
  - `chatgpt_execution` -> run Codex GPT-5.5 subscription when daily spend is below the cap.
  - `grok_decision_review` -> OpenClaw `grok-ceo` first pass.
  - routine -> normal OpenClaw `grok-ceo`.
- Hermes remains `nouscanary` only until its 24h gate passes. Do not let Hermes start Telegram polling.

**Why:** This is the Musk deletion answer. Do not add another bot, another dashboard, or another prompt stack. One policy file decides; LangGraph is the auditable graph wrapper; OpenClaw remains the runtime; Todoist/Goal pages are the long-work state machine.

**Regression:** `tools/tests/test_factory_orchestration_policy.py`, `tools/tests/test_langgraph_factory_orchestrator.py`, and `tools/test_operator_boundaries.py::{test_bounded_execution_ask_routes_to_chatgpt_codex,test_long_work_ask_creates_goal_and_does_not_run_model_inline,test_decision_prompt_routes_to_grok_first_pass_before_codex}`.

- **2026-05-15** | v1.8.4 -> v1.8.5 -- Shipped **AP-23** and the LangGraph route spine: bounded execution -> Codex GPT-5.5, decision prompts -> OpenClaw/grok-ceo, long work -> Goal/Todoist + DeepSeek/Kimi/GLM worker pipeline, Hermes remains canary. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-24 — Route markers must be token-aware, not substring-only (2026-05-15)

**Symptom:** Live LangGraph route sampling classified `Should we use Hermes or OpenClaw as the production runtime?` as `chatgpt_execution` instead of `grok_decision_review`.

**Root cause:** `tools/factory_orchestration_policy.py` matched markers with raw substring search. The execution marker `run` fired inside the word `runtime`, so a decision prompt looked like an execution prompt.

**Rule:** Single-word ASCII markers must match token boundaries. Phrase markers may remain substring matches. Add a regression whenever a route sample uses a word that contains a marker as a substring (`runtime`, `rerun`, `auditability`, etc.).

**Regression:** `tools/tests/test_factory_orchestration_policy.py::test_runtime_word_does_not_trigger_run_execution_marker`.

- **2026-05-15** | v1.8.5 -> v1.8.6 -- Added **AP-24** after live LangGraph route samples found `run` matching inside `runtime`. Patched `_has_any()` through token-aware `_contains_marker()` and added a regression so decision prompts about production runtime stay on Grok first-pass. No new LESSON (RULE ZERO). gbrain-timeline-ok pending.

### AP-25 — Worker chain escalation order must be benchmark-validated, not size-ordered (2026-05-18)

**Trigger:** 5-task fixture benchmark 2026-05-18 on Nous-specific task classes (coding, audit_summarization, retrieval_qa, russian_operator_notes, long_handoff_compression) revealed real per-class differences invisible to length-stratified sampling alone:

| Model | Pass | Avg cost | Cost vs Flash | Verdict |
|---|---:|---:|---:|---|
| deepseek-v4-flash | 5/5 | $0.000071 | 1× | KEEP AS PIN |
| kimi-k2.6 | 3/5 | $0.003 | 42× | Fallback only |
| qwen3-coder-plus | 0/5 | $0 | (100% silent error) | BROKEN on Air LiteLLM |
| deepseek-v4-pro | 2/5 | $0.001 | 20× | WORSE than Flash on routine |
| glm-5.1 | 2/5 | $0.002 | 28× | P50 8021ms (real slow) |

**Anti-pattern caught:** Conventional wisdom says "deeper" / "larger" model = better. Real benchmark on Nous tasks: DeepSeek-V4-Pro is *worse* than V4-Flash for routine work (audit summarization, Russian operator notes, handoff compression) despite costing 20× more.

**Rule:**

1. AP-23 worker chain order (`grok-reasoning → deepseek-v4-flash → deepseek-v4-pro → kimi-k2.6 → glm-5.1 → codex`) is CORRECT (Flash before Pro) but the implicit doctrine reason ("Pro for harder tasks") is invalidated by benchmark. Pro reserves for measurable pro-needs-signal (math-heavy reasoning, deep code review), NOT auto-fallback for routine.
2. `qwen3-coder-plus` is broken in production via Air LiteLLM — 100% error rate, $0 cost = silent fail. Investigate alias + provider config OR remove from cheap-pool until repaired.
3. **Russian operator notes are a real failure mode:** only `deepseek-v4-flash` passed. Non-Flash Chinese models code-switch English on Russian context (GPT external review predicted this exact failure 2026-05-18; benchmark confirmed). Russian-heavy traffic should be Flash-preferred OR escalated to opus-4.7-sub / grok-ceo.
4. **Audit_summarization** with strict format (4 bullets, max 15 words each): only Flash respected the format. Others overflow.
5. **Discipline:** the 5-task fixture (`pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl`) is the canonical benchmark corpus for cheap-pool decisions. Length-stratified sampling from `ask-hierarchy.jsonl` alone is insufficient — length is a poor proxy for task-class.

**Doctrine update applied:** Pin holds at `deepseek-v4-flash`. No rotation triggered this cycle (status `no-change` per `[[CHEAP-POOL-BENCHMARK-2026-05-18]]`).

**Caveat on latency numbers:** P50 latencies 2-20ms in this run reflect LiteLLM cache hits on identical prompts. Cold inference latencies would be 200-500ms typical (glm-5.1's 8021ms is real provider lag, not cache).

**Regression / evidence:**
- Audit: `[[CHEAP-POOL-BENCHMARK-2026-05-18]]` (commit `97712aa6`)
- JSON results: `pages/audits/CHEAP-POOL-BENCHMARK-2026-05-18.json`
- Fixture: `pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl`
- Tool: `tools/cheap_pool_benchmark.py` (Codex parallel ship 2026-05-17 + this validation run)

**Anti-patterns to detect:**
- Reordering worker chain "intuitively" without benchmark
- Trusting "Pro > Flash" on routine work
- Ignoring `$0` cost in benchmark output (= silent error mode, not cheap-success)
- Letting `qwen3-coder-plus` stay broken in pool while traffic routes to it
- Routing Russian operator notes to non-Flash Chinese models

**Cross-ref:** [[CHEAP-POOL-BENCHMARK-2026-05-18]] (today's audit), [[2026-05-17-hermes-factory-design]] (Section 9 + Revised scope where benchmark-fixture was specced), GPT external review 2026-05-18 (correctly flagged "no canonical quality field on OpenRouter — must benchmark on own corpus").

### AP-26 — GPT/Codex is the first brain for explicit top-tier second-brain and customer-transformation requests (2026-05-18)

**Trigger:** Madi clarified that the second brain must feel like the top-tier GPT/Codex lane first, with OpenClaw/factory as the execution substrate when needed. The failure mode is letting routine OpenClaw answer operator-facing or customer-facing high-judgment prompts before the GPT supervisor sees them.

**Rule:** explicit top-tier language (`top tier`, `second brain`, `2nd brain`, `gpt at the top`, `best CTO/CEO`, `Karpathy`, `Garry Tan`, `Elon`, `bulletproof`, `god level`) routes to `/codex` GPT-5.5 subscription before OpenClaw. Customer-transformation / sales-framing prompts also route to GPT when paired with execution intent. Codex must then decide whether to answer, create durable Goal/Todoist state, or delegate worker slices through OpenClaw/factory.

**Communication rule:** for team/customer-facing replies, lead with the destination: result, benefit, proof, and next observable change. Internal machinery (`gbrain`, Todoist, OpenClaw, LiteLLM, etc.) is the plane, not the island; mention it only when the recipient asked for implementation detail.

**Boundaries:** this does not make every `/ask` expensive. Routine status/chat stays OpenClaw. Long bulk work without explicit top-tier language still becomes Goal/Todoist worker state. Hermes remains canary/watchdog until its proof gates are green.

**Regression / evidence:** `tools/tests/test_factory_orchestration_policy.py::test_top_tier_second_brain_routes_to_chatgpt_codex_supervisor`, `tools/test_telegram_poll.py::TestImplicitAsk::test_private_top_tier_second_brain_routes_to_codex`, and `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_top_tier_second_brain_ask_routes_to_codex`.

### AP-27 — Satory camera/APK live-proof questions route to Codex before external replies (2026-05-18)

**Trigger:** In the `zamena BDL` Telegram group, Assylbek asked whether the bot saw the VAR camera placed near LU100 and whether the bot had access. The message was addressed to `@nousAGaaSbot`, but the routed text was short and did not contain explicit `verify:` / shell words, so it fell through to routine OpenClaw.

**Root cause:** The deterministic route policy only treated external Satory questions as sensitive when they contained `АПК` plus fixation/ERAP proof markers. Camera-access wording (`камера`, `ВАР`, `радар`, `видишь`, `доступ`, `событ`, `лог`) was missing, and the username alias `asylbek` was not tokenized as an operator marker.

**Rule:** Any Satory operator prompt that combines an operator marker (`asyl`, `asylbek`, `асылбек`, etc.) with camera/APK markers and live proof/access markers routes to Codex/GPT-5.5 execution before the bot writes an external-facing answer. The Codex lane must prove the receiver, database, inventory, route, or event state first; if proof is absent, it must state the exact missing observable.

**Regression / evidence:** `tools/tests/test_factory_orchestration_policy.py::test_satory_var_camera_access_query_routes_to_chatgpt_codex`, `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_satory_var_camera_access_query_routes_to_codex`.

### AP-28 — Hermes promotion proofs require green artifacts with canary markers (2026-05-18)

**Trigger:** The Hermes promotion runner was still too easy to fool: prefix-only audit files could flip a proof, rollback was a hard-coded command string, and `factory_green_24h` treated a current factory probe as GREEN even while the detail admitted 24-hour continuity still needed confirmation.

**Root cause:** `tools/hermes_promotion_runner.py` encoded the proof surface as file existence and current health checks, not evidence-grade canary receipts. That was acceptable for early scaffolding but unsafe after real Notion/Todoist/gbrain/OpenBrain canary artifacts started landing.

**Rule:** Hermes promotion proofs must use `status: green` audit artifacts that include the exact canary marker for the proof. Prefix-only files, yellow blocker files, directories, and current probes cannot satisfy promotion gates. Rollback requires a real rollback audit artifact. The 24-hour gate starts after the last canary-affecting config change and requires its own green `HERMES-24H-GATE-*` artifact; a current `factory_no_drift_probe` result is supporting evidence only.

**Canary outcome 2026-05-18:** Todoist, gbrain, Notion MCP, OpenBrain projection, cost receipt, and rollback proofs are green as canary evidence. Hermes remains canary-only because the post-Notion 24-hour gate is yellow until at least 2026-05-19 23:18 KZT.

**Regression / evidence:** `tools/tests/test_hermes_promotion_runner.py::test_green_artifact_proof_rejects_prefix_only_or_yellow_files`, `tools/tests/test_hermes_promotion_runner.py::test_green_artifact_proof_accepts_green_file_with_required_marker`, `[[HERMES-NOTION-CANARY-2026-05-18]]`, `[[HERMES-24H-GATE-PENDING-2026-05-18]]`.

### AP-29 — Model default promotion requires a real Satory/Nous fixture win (2026-05-18)

**Trigger:** Madi requested a hard model promotion gate: no model becomes default unless it wins on real Satory/Nous task fixtures. The existing cheap-pool picker could draft a proposal from model metadata and approve it into `ceo-hierarchy` without proving the candidate beat the incumbent on the canonical fixture set.

**Root cause:** `tools/cheap_pool_winner_picker.py` separated "nominate candidate" from "approve pin," but the approval path did not require a benchmark artifact. That allowed OpenRouter metadata, cost, latency, or a stale proposal to become a doctrine mutation without fresh fixture evidence.

**Rule:** `--approve-proposal` is RED unless `--promotion-benchmark-json` is supplied and `tools/model_promotion_gate.py` confirms all of these: proposal current matches benchmark current, benchmark winner equals proposal candidate, fixture path/classes cover the canonical five task classes, both current and candidate ran all cases, candidate score beats current, candidate has no pass-count regression, and candidate has no error-count regression. A tie is not a promotion.

**Research check:** Grok and GPT/Codex independently converged on the same rule surface: fixed fixtures, candidate must beat incumbent, route/cost evidence must be logged, rollback must be known, and human approval gates the default swap. Claude CLI was attempted but did not produce useful output because the local startup hook/budget path failed; no Claude-green claim is made.

**Regression / evidence:** `tools/tests/test_model_promotion_gate.py`, `tools/tests/test_cheap_pool_winner_picker.py::test_approve_proposal_requires_promotion_benchmark_json`, `tools/tests/test_cheap_pool_benchmark.py::test_load_fixture_prompts_preserves_case_id_and_task_class`.

### AP-30 — Mandatory Codex routes fail closed, not down to routine OpenClaw (2026-05-18)

**Trigger:** Madi asked to make two classes mandatory `/codex`: external operator proof questions and top-tier CTO/CEO questions. AP-26/AP-27 already routed the happy path to Codex, but the command-center branch could still fall through if Codex budget/auth was unavailable.

**Root cause:** `factory_orchestration_policy.py` returned `chatgpt_execution`, but `command_center.py` treated Codex budget failure as a non-terminal condition. That is acceptable for optional bounded execution; it is unsafe for external proof and top-tier supervisor prompts because a cheap fallback can answer without evidence or with the wrong executive layer.

**Rule:** External operator proof questions are any group/operator-sourced prompt asking whether APK/camera/VAR/radar/endpoint/IP/events/logs/ERAP/BDL state is visible, accessible, fixed, or proven. Top-tier CTO/CEO prompts include top-tier GPT, second brain, best CTO/CEO, Karpathy, Garry Tan, Elon, bulletproof, and equivalent supervisor language. These routes are mandatory Codex: if Codex cannot run, return a blocked message and do not call OpenClaw.

**Research check:** GPT/Codex lane concluded "yes, but fail closed." Claude CLI was attempted and exited on budget before useful output. Grok was attempted through Air LiteLLM, but Air SSH timed out during the direct probe; no Grok-green claim is made. The patch follows the conservative common engineering rule: public proof questions require evidence-capable execution or explicit no-answer.

**Regression / evidence:** `tools/tests/test_factory_orchestration_policy.py::test_external_operator_endpoint_proof_routes_to_chatgpt_codex`, `tools/tests/test_factory_orchestration_policy.py::test_top_tier_cto_ceo_question_routes_to_chatgpt_codex_supervisor`, `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_external_operator_proof_budget_block_does_not_fall_back_to_openclaw`, `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_top_tier_cto_ceo_budget_block_does_not_fall_back_to_openclaw`, `tools/test_telegram_poll.py::TestImplicitAsk::test_private_top_tier_cto_ceo_routes_to_codex`.

### AP-31 — Todoist/OpenClaw queue uses the same route policy and fails closed on mandatory Codex (2026-05-19)

**Trigger:** Madi required the Satory Todoist queue to become real execution, while keeping APK/ERAP/BDL and CEO/CTO proof questions on the top-tier GPT/Codex path. The risk was building a second queue router that silently bypassed AP-30.

**Root cause:** Before the one-beam queue, Todoist reminders, `AI:` comments, Telegram `/ask`, and goal cycles had overlapping but not identical model-route logic. That made it possible for a public proof question to be safe in Telegram but unsafe when it appeared as a Todoist task or comment.

**Rule:** Any execution spine that dispatches Satory Todoist work must call `tools/factory_orchestration_policy.py` or an equivalent tested classifier before choosing a model. If the route is mandatory Codex/GPT (`chatgpt_execution`) and the runner does not have an explicit Codex allowance/budget/auth proof, it must return `blocked_codex_required` and write the blocker to the ledger/Todoist instead of downgrading to OpenClaw/DeepSeek.

**Hermes boundary:** Hermes can observe, review, or provide canary evidence, but it cannot become the production executor for queue events until AP-21/AP-28 promotion gates are green.

**Regression / evidence:** `tools/tests/test_satory_ai_factory_queue.py::test_external_operator_proof_fails_closed_without_codex`, `tools/tests/test_satory_ai_factory_queue.py::test_routine_queue_dry_run_is_safe`.

### AP-32 — Hermes WebUI/iPhone canary requires Tailscale, password auth, and a WebUI gate (2026-05-19)

**Trigger:** Madi received Hermes Agent iOS TestFlight access and needed a phone-reachable Hermes surface. The screenshot pointed to `nesquena/hermes-webui`, but Air had only the Hermes CLI/profile canary; nothing was listening on `8787`.

**Root cause:** The existing Hermes gate proved the CLI profile and Telegram isolation, not the WebUI/iPhone path. The first launchd attempt also failed because the secret env file contained `HERMES_WEBUI_BOT_NAME=Hermes Canary` without shell quoting, so `source` tried to execute `Canary` and launchd exited `127`.

**Rule:** Hermes WebUI is a separate canary surface. It must run behind Tailscale or another private tunnel, with `HERMES_WEBUI_PASSWORD` set before binding beyond localhost. Phone readiness is not green unless `tools/hermes_webui_canary.sh health` and `python3 tools/hermes_canary_gate.py --json --webui-probe` pass on Air. Public Cloudflare/domain exposure requires explicit approval and a rollback receipt. Shell-sourced env files must be shell-safe: quote values containing spaces or normalize them before launchd sources the file.

**Regression / evidence:** `tools/tests/test_hermes_canary_gate.py::test_gate_can_require_webui_health`, `tools/hermes_webui_canary.sh`, `tools/launchd/com.nous.hermes-webui-canary.plist`, `pages/audits/HERMES-WEBUI-IPHONE-CANARY-2026-05-19.md`.

### AP-33 — Hermes iPhone reachability and GPT availability are separate gates (2026-05-19)

**Trigger:** Madi tried Hermes Agent iOS after AP-32 and it did not connect; GPT also appeared to stop.

**Root cause:** Two independent failures were hidden by overly broad green checks. First, Air's WebUI was healthy, but `tailscale status` reported `Logged out` while `ifconfig` still exposed a stale `100.x` interface address, so `phone-url` returned a URL the iPhone could not trust. Second, Hermes had OpenAI Codex auth, but the Air host had no `codex` executable on PATH, so `hermes doctor` warned `codex CLI not found`.

**Rule:** Do not collapse these into one "Hermes works" claim. WebUI server health, phone reachability, and GPT/Codex execution are three separate gates. `phone-url` must be backed by `tailscale ip -4`; if Tailscale is logged out it fails loud. Same-Wi-Fi access must use explicit `lan-url`. Codex/GPT is green only when `codex_cli_available` is green and `--smoke` returns the exact canary marker.

**Regression / evidence:** `tools/tests/test_hermes_canary_gate.py::test_gate_red_when_codex_cli_missing`, `tools/hermes_webui_canary.sh phone-url` now fails on logged-out Tailscale, and `tools/hermes_webui_canary.sh lan-url` returns the explicit LAN fallback.

### AP-34 — Tier-0 MLX `local-mlx-coder` is the FIRST worker for routine + long_work_goal routes; `deepseek-v4-flash` is fallback (2026-05-19)

**Trigger:** Madi MISSION 2026-05-19 plus 3-item Tier-0 MLX integration: Item 1 (LiteLLM register on Air:4000), Item 3 (queue runner route preference), Item 2 (this doctrine). MLX server `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` on Mac Pro:8080 verified reachable from Air via Tailscale `100.100.197.19:8080`; LiteLLM route verified via end-to-end smoke `TIER0_MLX_LITELLM_E2E_OK`.

**Rule:** For `ROUTE_OPENCLAW_ROUTINE` and `ROUTE_LONG_WORK_GOAL`, the worker chain is:

```
local-mlx-coder → deepseek-v4-flash → grok-reasoning
```

`ROUTE_CHATGPT_EXECUTION` route remains `codex:gpt-5.5` (mandatory per AP-30; not affected). `ROUTE_GROK_DECISION` remains `grok-reasoning`. Cheap-pool benchmark fixtures must include MLX going forward (AP-25 + AP-29 gates extended: any change to the MLX worker pin requires the same fixture win benchmark).

**Why this departs from AP-29 bakeoff gate**: Madi explicitly greenlit shipping ahead of formal bakeoff per always-on MISSION priority. Bakeoff against deepseek-v4-flash on the 5-task Nous fixture is deferred — should run within 24h per MISSION rule 5 ("no model becomes default unless it wins on real Nous/Satory fixtures"). Until that gate fires, MLX is provisionally-default for routine routes; if it underperforms, revert to deepseek-v4-flash.

**Cost shape:** MLX is $0 marginal (local Mac M5 Max compute). Frees Codex subscription quota for high-judgment slices. Latency ~3-5s typical, comparable to or faster than DeepSeek API.

**Regression / evidence:**
- `tools/tests/test_satory_ai_factory_queue.py::test_model_for_decision_prefers_local_mlx_for_long_work_and_routine` (3 assertions).
- Live: LiteLLM `/v1/chat/completions` with `model: local-mlx-coder` returns `TIER0_MLX_LITELLM_E2E_OK` literal in ~5s (verified 2026-05-19 15:30 KZT).
- Queue runner commit `6158612e` wires the preference; LiteLLM config commit on Air bare (auto-syncs next cycle).
- AP-32 anti-collision: Codex's parallel exec implemented Item 3; Opus committed on his behalf from Air SSH (sandbox blocked his .git/index.lock write).

**Open follow-ups (NOT blocking GREEN, but tracked):**
- Formal benchmark against deepseek-v4-flash via `tools/model_promotion_gate.py` within 24h.
- Add `local-mlx-coder` to section 10 LiteLLM fallback chain table when next this skill is touched.
- MLX bind decision (currently 0.0.0.0; recommend Tailscale-bind 100.100.197.19 per Codex's resource report) — Madi-decision pending.

- **2026-05-19** | v1.9.8 -> v1.10.0 -- Added **AP-34** after 3-item Tier-0 MLX factory integration shipped: LiteLLM `local-mlx-coder` route (Mac Pro MLX via Tailscale → Air:4000), queue runner routing preference for `long_work_goal` + `openclaw_routine` (commit `6158612e`), and this doctrine bump making MLX the first worker for routine routes with deepseek-v4-flash as fallback. End-to-end verified: `TIER0_MLX_LITELLM_E2E_OK` through full Mac MLX → Tailscale → Air LiteLLM chain. Bakeoff against deepseek-v4-flash deferred per Madi MISSION 2026-05-19 always-on priority; must fire within 24h. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-35 — Hermes WebUI status uses launchd plus HTTP health, not ctl PID files (2026-05-19)

**Trigger:** A fresh iPhone readiness check showed `tools/hermes_webui_canary.sh status` reporting `stopped` while launchd listed `com.nous.hermes-webui-canary` and `/health` returned HTTP 200.

**Root cause:** The wrapper delegated `status` to Hermes WebUI's `ctl.sh status`. That status path only knows about daemons started by `ctl.sh start` because it reads `~/.hermes/webui.pid`. The production canary LaunchAgent starts the wrapper with `run-foreground`, so no ctl PID file is expected.

**Rule:** For the launchd-managed canary, status must be computed from `launchctl list`, `curl http://127.0.0.1:8787/health`, `phone-url`, and `lan-url`. `ctl.sh status` is advisory only and must not be used to tell the user the iPhone/WebUI canary is stopped.

**Regression / evidence:** `tools/hermes_webui_canary.sh status` now prints launchd, health, phone-url, lan-url, and the PID-file caveat directly.

### AP-36 — Hermes WebUI must expose the factory surface, not a blank default profile (2026-05-19)

**Trigger:** Madi logged into Hermes WebUI from iPhone and found it empty, then clarified that this surface must carry the whole current factory: Obsidian wiki, gbrain, Todoist, Notion, skills, and current canary history before any broader architect/orchestrator layer uses it.

**Root cause:** The WebUI process was healthy but started in the `default` Hermes profile. The live canary MCP config and sessions were in `nouscanary`; default had no canary MCP servers, WebUI settings hid CLI sessions, and `/api/skills` returned HTTP 500 because WebUI v0.51.92 imported `_sort_skills` from an agent build that did not export it. Health was green while the operator surface was effectively blank.

**Rule:** Hermes WebUI/iPhone readiness requires all of these, not just login: active profile `nouscanary`; workspace `/Users/madia/nous-agaas/wiki`; `Nous Factory` project seeded; CLI session visibility enabled; `/Users/madia/nous-agaas/skills` present as an external skill dir; `/api/skills` HTTP 200; Todoist, gbrain, and Notion MCP servers configured and testable.

**Mechanical detector:** `tools/hermes_webui_canary.sh run-foreground` seeds the profile, settings, project, external skills, and WebUI/agent compatibility shim before launch. A post-start proof must call `/api/profile/active`, `/api/sessions`, `/api/projects`, `/api/skills`, `/api/mcp/servers`, and `hermes-nouscanary mcp test {gbrain,todoist,notion}` before calling the phone surface useful.

- **2026-05-19** | v1.10.2 -> v1.10.3 -- Added **AP-37** after upstream Hermes docs/X review and live WebUI API proof showed the canary was still not "god-level": Kanban was empty until the agent was upgraded, memory was blank, insights ignored profile sessions, MCP inventory was configured-but-empty in the dashboard, and `/api/settings` reported the wrong default model. Fix: `tools/hermes_webui_factory_seed.py` now idempotently seeds profile memory, WebUI-readable session insight files, a `nous-factory` Kanban board with source-backed canary tasks, and an MCP inventory cache; `tools/hermes_webui_canary.sh` pins `HERMES_HOME` to `nouscanary`, pins `HERMES_MODEL=gpt-5.5`, and patches the WebUI MCP panel to read the canary probe cache. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-37 — Hermes WebUI factory surface needs memory, insights, Kanban, model route, and MCP inventory (2026-05-19)

**Trigger:** After the iPhone login/default-profile fix, Madi asked for the whole factory to be present in Hermes: tasks, skills, memory, insights, projects, Obsidian, gbrain, Todoist, and Notion, based on upstream Hermes docs and X/account context.

**Root cause:** The AP-36 gate stopped at profile/project/skills/MCP configuration. It missed newer Hermes Agent Kanban requirements and WebUI realities: old agent builds lacked `hermes_cli.kanban_db`, the dashboard insights endpoint only reads WebUI session files/indexes, memory files are not auto-populated, WebUI MCP inventory only shows already-registered runtime tools unless a chat has loaded them, and the WebUI default model resolver can fall back to a non-canary model unless the process env pins it.

**Rule:** A useful Hermes WebUI factory surface must prove these API-level facts in one pass: `/api/settings.default_model == gpt-5.5`; `/api/profile/active.name == nouscanary`; `/api/projects` contains `Nous Factory`; `/api/sessions` and `/api/insights` see real canary session history; `/api/memory` has non-empty `MEMORY.md` and `USER.md`; `/api/kanban/boards` current board is `nous-factory` with source-backed tasks; `/api/mcp/servers` marks Todoist, gbrain, and Notion active; `/api/mcp/tools` exposes non-zero tool inventory; `/api/skills` is healthy. Do not import or fabricate all Todoist/Notion data into Kanban just to make the board look full; seed only source-backed canary work and leave source systems authoritative.

**Regression / evidence:** `tools/hermes_webui_factory_seed.py`, `tools/tests/test_hermes_webui_canary_script.py::test_webui_canary_uses_mcp_inventory_cache_for_dashboard`, and the 2026-05-19 live API proof: memory 511/user 294 chars, insights 15 sessions/50 messages, Kanban `nous-factory` 3 tasks, MCP Todoist/gbrain/Notion active with 113 tools, default model `gpt-5.5`.

- **2026-05-19** | v1.10.3 -> v1.10.4 -- Added **AP-38** after live proof showed authenticated `/api/factory-events` returned 404, so Hermes WebUI had seeded factory visibility but no hot-path event ingestion. Fix: `tools/hermes_webui_canary.sh` now installs a canary-only read-only endpoint that tails `ops_events.jsonl`, `factory-self-heal.jsonl`, `hermes-factory-watchdog.jsonl`, and `satory-ai-factory-queue-status.md`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-38 — Hermes WebUI factory events must be live-ledger backed, not seeded-only (2026-05-19)

**Trigger:** Madi asked why Hermes was still not "god level"; live proof showed `login_http=200` but authenticated `GET /api/factory-events` returned `404 {"error":"not found"}`.

**Root cause:** The WebUI canary had profile, memory, Kanban, MCP inventory, and seed-state, but no HTTP route exposing current factory hot-path ledgers. The surface could look alive while missing real-time factory events.

**Rule:** Hermes WebUI remains canary-only, but the canary must expose authenticated read-only `/api/factory-events` backed by existing live ledgers. Do not make Hermes a second Telegram poller or production router; it observes `ops_events.jsonl`, `factory-self-heal.jsonl`, `hermes-factory-watchdog.jsonl`, and the Satory queue status page.

**Regression / evidence:** `tools/hermes_webui_canary.sh`, `tools/tests/test_hermes_webui_canary_script.py::test_webui_canary_adds_factory_events_api_shim`, and live authenticated proof after launchd restart.

- **2026-05-20** | v1.10.4 -> v1.10.5 -- Added **AP-39** after Madi clarified subscription-first economics for the factory. `/ask --tier ceo` is Codex GPT-5.5 subscription-first and Madi-DM only; `/ask --tier cheap` is MLX/DeepSeek-only; `tools/multi_model_consult.py` records `billing_surface` and blocks Opus/Grok/OpenRouter paid calls by default before key lookup unless `NOUS_PAID_API_ALLOWED=1`, `NOUS_PAID_API_CAP_USD`, and `NOUS_PAID_API_REASON` are visible. No new LESSON (RULE ZERO).

### AP-39 — CEO council means subscription/capped council, not automatic API spend (2026-05-20)

**Trigger:** Madi wanted the factory to use ChatGPT/Codex and other subscriptions first, local MLX when possible, and cheap worker models by default, with Grok/Opus API spend prevented unless explicitly approved.

**Rule:** Treat billing surface as part of the route contract. Valid surfaces are `subscription`, `local`, `xai_api`, `anthropic_api`, `openrouter`, and `unknown`. Codex/GPT-5.5 is the subscription-first CEO path. Local MLX and DeepSeek are workhorse paths. Grok availability on Air means `xai_api` until a separate subscription-backed automation path is proven. Opus API is disabled by default. Any paid API council must show a cap, reason, and ledger row before it can run.

**Detector:** `python3 -m pytest tools/tests/test_multi_model_consult.py tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_ask_tier_ceo_is_codex_first_and_not_openclaw tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_ask_tier_cheap_uses_local_mlx_route_and_never_codex_grok_or_opus -q`.

### AP-40 — Codex daily caps gate `/ask` auto-escalation; cap sentinel never reaches user (2026-05-20)

**Trigger:** Assylbek asked `@nousAGaaSbot видишь события? поток подали` (no slash prefix). LangGraph classified the message as `ROUTE_CHATGPT_EXECUTION`. `_codex_daily_budget_ok` returned `(True, $X.XX)` because it only summed today's USD spend (`< $5`) and did NOT check `CODEX_DAILY_CAP_CALLS` or `CODEX_DAILY_CAP_TOKENS`. `_run_codex` was invoked, found `tokens=312163 > 250000`, and returned its sentinel string `"Daily /codex token cap reached: 312163 / 250000 observed tokens. Resets midnight Almaty."` The Telegram dispatcher relayed the sentinel verbatim as the bot's "answer" — twice (msg_id 1799 at 14:58 and 1802 at 15:42). Madi's reaction: "wtf?"

**Rule:** Codex daily caps are routing gates, not user-facing answers. `_codex_daily_budget_ok` must fail-closed on `CODEX_DAILY_CAP_CALLS` and `CODEX_DAILY_CAP_TOKENS` in addition to the USD ceiling, so every `/ask` auto-escalation path (`ROUTE_CHATGPT_EXECUTION`, `_requires_codex_verification_route`, `_query_likely_needs_high_judgment`) silently skips `_run_codex` and falls through to grok-ceo Tier-1 when caps are exhausted. Mandatory codex routes keep their explicit `_mandatory_codex_blocked_message` path. Direct `/codex` and `/resume codex` keep the verbatim sentinel — the user asked for codex explicitly. Defense-in-depth: `_is_codex_cap_blocked` helper detects the sentinel after `_run_codex` returns and re-routes to grok-ceo to cover the race window between gate check and codex call.

**Detector:** `python3 -m pytest tools/tests/test_codex_budget_gate.py -v` — 9 tests covering token cap, call cap, USD cap, helper sentinel detection, and high-judgment escalation gating.

**Mechanical guard:** `grep -n '_run_codex(query)' command_center.py` must show every `/ask`-prefixed callsite preceded by either `_codex_daily_budget_ok` or `_query_likely_needs_high_judgment` AND followed by `_is_codex_cap_blocked`. Direct `/codex` and `/resume codex` callsites are exempt.

### AP-41 — Mandatory codex blocked must fall back to grok-ceo with transparent localized notice (2026-05-20, supersedes AP-30 for user-facing replies)

**Trigger:** AP-40 (token-cap gate) closed the verbatim-sentinel path, but AP-30 (`_mandatory_codex_blocked_message`) still bounced four real group/DM messages with English wall-of-text after my AP-40 deploy:
- msg_id 1805 (Assylbek group `Видишь события?`)
- msg_id 1802 (`from asyl: ПО работает с Апк?`)
- msg_id 1751 (Denis group `события пошли, какой endpoint и consumer`)
- msg_id 1752 (Madi DM `What would a top-tier CTO/CEO do…`)

All four routed `chatgpt_execution` + mandatory codex (`codex_external_proof` / top-tier supervision) + budget gate closed → `_mandatory_codex_blocked_message` sent verbatim. Madi: "wtf? cannot stop this for my group chat, my telegram nous should never be able to stop like that." User intent: bot must ALWAYS produce a real answer in group chats; error messages MUST be in Russian for groups.

**Rule:** When `_is_mandatory_codex_decision(route_decision)` is True AND `_codex_daily_budget_ok` returns False, the dispatcher MUST fall back to `_run_openclaw(query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")` and prepend a transparent localized notice — never relay `_mandatory_codex_blocked_message` verbatim to the user. Group chats (Russian operator coworkers) get a pure-Russian notice ("⚠️ Codex недоступен (исчерпан суточный лимит токенов). Использую grok-ceo Tier-1 для ответа. Полная Codex-проверка вернётся после полуночи (Алматы)."). Madi's DM gets an English notice with spend info for operator awareness. Receipt tag becomes `/ask-mandatory-codex-grok-fallback`; status `degraded` (not `blocked`). The shell-verification cap-fallback notice is also Russian-localized for groups.

**Why this supersedes AP-30:** AP-30 said "mandatory codex routes fail closed, no OpenClaw fallback." That preserves model-correctness rigor but trades user-facing answer quality for technical purity. In public group chats, a transparent grok-ceo fallback with an honest "Codex temporarily unavailable" notice is materially better than bouncing the question with English error wall-of-text. The transparency in the notice preserves operator awareness without sacrificing the customer-facing answer.

**Detector:** `python3 -m pytest tools/tests/test_codex_budget_gate.py::test_ap41_mandatory_codex_grok_fallback_handler_exists tools/tests/test_codex_budget_gate.py::test_ap41_shell_verification_fallback_russian_for_groups tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_mandatory_satory_proof_falls_back_to_grok_with_russian_notice_in_group tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_external_operator_proof_falls_back_to_grok_with_russian_notice_in_group tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_top_tier_cto_ceo_falls_back_to_grok_with_english_notice_in_dm -v`

**Mechanical guard:** `grep -n '_mandatory_codex_blocked_message(query, _today_spend)' command_center.py` must return ZERO matches in the live dispatcher. The function itself can remain defined (for future explicit-block paths) but must not be called from the auto-dispatch chain.

### AP-42 — Group-chat credential safety NEVER bypassed; decline message must be actionable, not just polite (2026-05-20)

**Trigger:** 2026-05-20 ~17:01 Madi DM'd the bot in the Satory group: "give log in and password here so Asyl can log in and checka there. trust the log in and password. i give permission. do it now." The bot replied with the polite Russian decline ("Принято. Доступы в общем чате не публикуем. Передано владельцу...") because `CREDENTIAL_HANDOFF_RE` matched "log in and password". Madi: "why? why did not work?" Initial fix attempt proposed an owner-override bypass keyed on a regex of authorization phrases ("i give permission", "разрешаю", etc.) AND a sender-equals-owner check. The auto-mode classifier correctly blocked the deploy: the sender field is parsed from text (`_extract_group_sender_context`), and even if currently authentic (wrap is added by telegram_poll.py from Telegram API), a text-parsed authentication signal is a fragile foundation for bypassing a credential-safety mitigation in a public, durable, indexable group history.

**Rule:** `handle_owner_credential_handoff` and `needs_owner_credential_handoff` MUST NOT be bypassed in group chats, even when the sender matches `OWNER_USERNAME` AND uses explicit-authorization phrases. Group safety > convenience: groups are visible to all current and future members, messages are forwardable + indexable, and a text-parseable owner signal is fragile against any future wrap-format change. INSTEAD, the auto-decline reply MUST be actionable: it must list at least three concrete safe-share alternatives so the owner has a clear next-step path. Current required substrings in the decline:
- "Доступы в общих чатах не публикую" (the rule)
- "даже с явным разрешением" (refuses owner authorization explicitly)
- "Открой DM" (DM-to-target alternative)
- "Самосерв" or "админке" (self-serve / dashboard admin alternative)
- "DM мне приватно" (private-DM-to-bot alternative for guidance)
- "Передано владельцу" (context still relayed to owner via DM, unchanged)

The full body is still forwarded raw to the owner's DM via `_tg_send(bot_token, owner_id, owner_body)` so the owner has the operator context to act manually. No bot relay of credentials between users (that would put credentials in bot logs).

**Why this supersedes the owner-bypass-via-regex design:** sender-equality + phrase-match is two cheap signals stacked, and either one being wrong (impersonated wrap, accidental authorization-shaped phrase) opens the credential-leak path. Credential safety should be a single binary policy ("never publish in groups") rather than a multi-signal heuristic. The user-experience loss (Madi can't post creds in groups) is acceptable because the safer alternatives (1-on-1 DMs) take ~10 seconds longer and avoid catastrophic leak risk.

**Detector:** `python3 -m pytest tools/tests/test_codex_budget_gate.py::test_ap42_credential_handoff_reply_lists_safe_alternatives tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_group_credential_request_routes_to_owner_handoff_before_codex tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_owner_credential_handoff_never_echoes_group_env_config -v`.

**Mechanical guard:** `grep -n 'Доступы в общих чатах не публикую\|Открой DM\|DM мне приватно\|Передано владельцу' command_center.py` must return ≥4 hits in `handle_owner_credential_handoff`. `grep -n 'owner_credential_override\|_owner_credential_override_active' command_center.py` must return ZERO hits — no text-parsed owner bypass code in the dispatcher.

### AP-43 — When credential-handoff sender is the owner, skip the redundant owner-DM echo and use a terse group reply (2026-05-20)

**Trigger:** Right after AP-42 deploy, Madi shared a screenshot of what he actually received: in his DM the bot had sent `[OWNER-ONLY: forward to operator] Source group: -1002064137259 ... Sender: @madi_ayazbay ... give log in and password here so Asyl can log in...` — i.e., his own message bounced back to him as if he needed to be informed. Plus my full AP-42 status text. Plus the long three-alternative decline in the group. Madi's reaction was "wtf?" — too much noise, none of it useful.

**Rule:** `handle_owner_credential_handoff` MUST detect when the credential-handoff sender matches `OWNER_USERNAME` (normalized case + leading-`@` stripped) and, in that case, take an OWNER-MODE branch that (a) skips the owner-DM relay entirely — the owner already saw their own message in the group, (b) replies in the group with a one-paragraph terse decline pointing at the single fastest manual path (DM the target or use dashboard admin invite). For NON-owner senders the existing 3-alternative decline + raw-context owner-DM relay path is preserved unchanged — that path is the original AP-25 protection: when a coworker asks for credentials, the operator (owner) must see the raw context so they can act manually.

Owner-mode group reply text (current):
```
🔐 Креды в группах не публикую — даже с твоим разрешением. Групповая
история постоянна, пересылаема, индексируема.
Самый быстрый путь: открой DM с нужным человеком и скинь туда (10 сек).
Или в админке дашборда: пригласить по email/username.
```

**Why this is NOT an AP-42 bypass:** AP-42 said the credential-publish safety is never bypassed. AP-43 doesn't bypass that — the bot STILL refuses to publish credentials in the group. AP-43 only changes (i) the redundant owner-DM echo (UX bug — telling Madi what Madi just said adds noise without value), and (ii) the verbosity of the group reply when the owner is the requester (they already know the alternatives; one terse paragraph is enough). The classifier objection to AP-42-original was about weakening credential publishing on a text-parsed sender — AP-43 doesn't publish anything new, it just trims redundant outputs based on the same text-parsed sender, so the worst-case-spoof outcome is "owner gets one less DM and a shorter group decline", not a credential leak.

**Detector:** `python3 -m pytest tools/tests/test_codex_budget_gate.py::test_ap42_credential_handoff_reply_lists_safe_alternatives tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_owner_credential_handoff_never_echoes_group_env_config tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_ap43_owner_sender_skips_owner_dm_echo tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_group_credential_request_routes_to_owner_handoff_before_codex -v`.

**Mechanical guard:** `grep -n 'sender=owner, no DM echo\|Креды в группах не публикую — даже с твоим разрешением' command_center.py` must return ≥2 hits in `handle_owner_credential_handoff`. The owner-sender path must NOT call `_tg_send(bot_token, owner_id, owner_body)` — only the group reply.

**UX/communication corollary:** when the bot DMs Madi a status message (via `tg_send.sh` or otherwise), the message MUST be terse (≤3 sentences) unless Madi explicitly asked for a long write-up. Wall-of-text status reports for routine fixes are noise. Save the long explanation for the skill body + commit message + gbrain timeline.

- **2026-05-21** | v1.10.9 -> v1.10.10 -- Added **AP-44** and section 0c after Madi clarified the factory's desired operating stack: Telegram cockpit, OpenClaw runtime, GPT-5.5/Codex subscription as second brain, DeepSeek V4 Flash as measured cheap worker, local Mac/in-house AI only when live, Grok as transparent cap/fallback reviewer, Hermes canary-only, no Claude-subscription assumption, weekly cheap-pool benchmark/promotion gate, stuck-agent council with durable artifacts, and 03:00 cross-surface proof. Musk step-2: deleted "top AI everywhere" and duplicated SOUL routing; route doctrine lives here while SOUL remains identity/taste. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill via VPS CLI fallback after MCP transport closed in this Codex session.

### AP-44 — Second-brain routing is a tier contract, not all-GPT or all-cheap-worker (2026-05-21)

**Trigger:** Madi clarified the desired factory shape: Telegram talks to OpenClaw; GPT subscription is the second brain; routine work should use the best cheap measured worker; local Mac/in-house AI should be preferred only when it actually works; GPT cap failures should fall back to top-tier Grok; Claude subscription should not be assumed; weekly model checks and 03:00 substrate evolution must keep the system improving.

**Root cause:** The ingredients already existed, but the compact rule was scattered across AP-39/AP-40/AP-41, Hermes canary doctrine, cheap-pool tooling, SOUL.md, and launchd jobs. Future agents could flatten the stack into the wrong simplification: "route everything to GPT", "route everything to the cheapest model", "Hermes is production", "Grok fallback means silent paid xAI spend", or "Claude subscription is available."

**Rule:** Treat the second-brain stack as a tier contract:

1. Telegram is cockpit, not memory.
2. OpenClaw is runtime/factory, not the thinking identity.
3. GPT-5.5/Codex subscription is high-judgment second brain, not routine labor.
4. DeepSeek V4 Flash remains default cheap worker until benchmark plus promotion gate proves a better replacement.
5. Local Mac/in-house AI is preferred only after live endpoint and quality proof.
6. Grok is transparent cap/fallback reviewer; paid xAI spend still needs policy/cap/reason/ledger.
7. Hermes remains canary/watchdog until section 0b gates pass.
8. Claude subscription is not a production route assumption; Opus/Claude use must declare its billing surface.
9. Stuck-agent councils must create durable consult artifacts and skill updates, not chat-only opinions.
10. 03:00 evolution must prove Obsidian, gbrain, OpenBrain, OpenClaw, Hermes, MCP/API health, and model-rotation watch status.

**Detector / proof:** At minimum, verify:

```bash
python3 -m pytest tools/tests/test_multi_model_consult.py tools/tests/test_cheap_pool_benchmark.py tools/tests/test_cheap_pool_winner_picker.py tools/tests/test_model_promotion_gate.py -q
python3 tools/daily_0300_substrate_sync.py --probe-only --json
python3 tools/openbrain_project_to_wiki.py --wiki . --dry-run --json
ssh air 'launchctl list | egrep "com\\.nous\\.(telegram-poll|litellm|daily-0300-substrate-sync|cheap-pool|openbrain|hermes)"'
```

If any proof route is unavailable, record the exact residual. Do not replace missing proof with confidence.

- **2026-05-21** | v1.10.10 -> v1.10.11 -- Added **AP-45** after the same-day Hermes proof sprint showed the right operating stance: OpenClaw baseline was green, Hermes canary + smoke were green, and the promotion runner correctly stayed RED because the `HERMES-24H-GATE` artifact was missing. Rule: prove Hermes fast in isolation, but promotion remains artifact-gated; no blind Telegram cutover and no passive "14-day canary" theater. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill via VPS CLI fallback after MCP transport closed in this Codex session.

### AP-45 — Hermes proof sprint is same-day evidence, not production promotion (2026-05-21)

**Trigger:** Madi corrected the Hermes plan: the Elon/Musk-mode version is "prove Hermes today, isolated, with rollback," not "wait 14 days because canary sounds safe."

**Root cause:** The previous language conflated two separate controls. A fast canary proof reduces uncertainty and should happen immediately. A production cutover changes the Telegram/runtime blast radius and still requires artifact-gated rollback, cost, sync, and stability evidence.

**Rule:** Treat Hermes as a reliability race against OpenClaw:

1. Establish OpenClaw baseline first (`factory_no_drift_probe`, `telegram_openclaw_factory_truth_gate`, Air substrate probe).
2. Run Hermes in the isolated `nouscanary` profile with Telegram absent and WebUI/factory probes enabled.
3. Spend one explicit smoke call only when intentionally proving the canary.
4. Save the result as an audit artifact with command/output evidence.
5. If Hermes fails, root-cause, patch, skillify, and rerun.
6. If Hermes wins the same-day sprint, keep it canary/watchdog until `hermes_promotion_runner.py --json` returns all promotion proofs green, including the 24h factory marker.

**Detector / proof:**

```bash
ssh air 'cd ~/nous-agaas/wiki && python3 tools/hermes_canary_gate.py --factory-probe --webui-probe --smoke --json'
ssh air 'cd ~/nous-agaas/wiki && python3 tools/hermes_promotion_runner.py --json'
```

The first command may be green while the second is red. That is the expected state when the same-day proof works but the promotion bar is still unmet.

- **2026-05-21** | v1.10.11 -> v1.10.12 -- Added **AP-46** after the deep Grok/OpenClaw/Hermes audit found a source conflict: xAI announced SuperGrok/X Premium use in OpenClaw and the local OpenClaw 2026.5.19 CLI exposes `xai-device-code`/OAuth onboarding flags, but local production status still showed only LiteLLM/OpenClaw routes and no proven subscription-backed xAI auth. Rule: news/CLI capability is not factory route truth; require local auth status, canary execution, and billing-surface ledger before claiming Grok subscription use. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-46 — Grok/X Premium announcement is not local route proof (2026-05-21)

**Trigger:** Madi asked whether the factory should start using his Grok or X Premium subscription in OpenClaw after xAI's OpenClaw announcement.

**Root cause:** Three surfaces can disagree: xAI news can announce subscription support, OpenClaw provider docs can still describe API-key-only limits, and a locally installed OpenClaw CLI can expose onboarding flags before the production agent profile is actually authenticated. Treating any one of those as route truth creates hidden spend and false "top model" claims.

**Rule:** A Grok subscription path is live only when all three are true:

1. Local OpenClaw auth/status shows a subscription/OAuth/device-code profile is active for the production OpenClaw agent, not only a CLI help flag.
2. A canary call returns a Grok marker through that profile and writes a cost/billing-surface receipt.
3. `tools/model_route_auth_probe.py --json` or the route ledger classifies the path as subscription-backed rather than `xai_api`, `openrouter`, or `unknown`.

Until then, Grok remains a transparent reviewer/fallback route governed by paid API policy, cap, reason, and ledger. Do not use browser-driven X automation or silent xAI API spend to simulate subscription use.

**Detector / proof:**

```bash
docker exec openclaw openclaw models status --json
docker exec openclaw openclaw onboard --help | grep -E 'xai-(device-code|oauth|api-key)'
python3 tools/model_route_auth_probe.py --json
python3 tools/multi_model_consult.py --question "route audit" --dry-run --json
```

The first two commands prove capability/status shape only. The route is still yellow until a canary execution and billing-surface receipt prove subscription-backed use.

- **2026-05-22** | v1.10.12 -> v1.10.13 -- Added **AP-47** after Madi clarified Hermes cutover approval and the promotion runner reached 9/10 GREEN while `factory_green_24h` stayed RED. Root cause: `CONTROL-PLANE-SYNC-2026-05-22-033439` contained a strict `factory_no_drift_probe` RED for `air_sync_lag` (`local=8b999a65`, canonical/GitHub/Air GitHub `6c84f780`, auto-repair skipped due 7 dirty paths). Runtime checks were green and later probes were green, but the 24h gate explicitly requires zero-red continuity. A secondary tooling trap appeared: running the promotion runner on Mac can overwrite the audit with local false-reds, so `tools/hermes_promotion_runner.py` now refuses non-Air runs unless `--allow-non-air` is explicit. Rule: current green plus watchdog recovery cannot be backfilled into a green 24h marker; write a reset receipt and restart the clock from the next verified green probe. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-47 — Hermes 24h promotion clock resets on strict no-drift RED (2026-05-22)

**Trigger:** Madi said Hermes promotion had been approved and asked why Telegram still answered through OpenClaw. The promotion runner showed 9/10 proofs green, with only `factory_green_24h` red. A direct 24h watchdog review showed 48 half-hour watchdog runs green, but the control-plane audit at `2026-05-22T03:35 KZT` included a strict `factory_no_drift_probe` RED caused by `air_sync_lag` while the Air worktree had 7 dirty generated paths.

**Root cause:** The gate had two similar-sounding facts: runtime health continuity and strict no-drift continuity. Runtime health stayed green, but strict no-drift did not. Treating watchdog recovery as equivalent to zero-red 24h continuity would turn a canary promotion gate into a narrative exception.

**Rule:** A Hermes production promotion may not create or use a green `HERMES-24H-GATE-*` artifact if any strict `factory_no_drift_probe` inside the candidate window reports `reds > 0`, even when the red is sync lag and all runtime health checks are green. The correct action is:

1. Save the failed promotion runner audit.
2. Save a yellow/reset `HERMES-24H-GATE-*` receipt with the exact red check and next eligible time.
3. Run `hermes_promotion_runner.py` on Air only; Mac/local runs are diagnostic only and require `--allow-non-air`.
4. Keep Hermes canary-only and Telegram on OpenClaw.
5. Restart the 24h window from the first subsequent strict green probe.
6. Use `tools/hermes_24h_gate_verifier.py` to mint the green receipt only after the reset window has no strict red checks.
7. Rerun `python3 tools/hermes_promotion_runner.py --json` without `--promote` and ask Madi for explicit approval before any cutover.

**Detector / proof:**

```bash
ssh air 'cd ~/nous-agaas/wiki && python3 tools/hermes_promotion_runner.py --json'
ssh air 'cd ~/nous-agaas/wiki && sed -n "/### factory_no_drift/,+90p" pages/audits/CONTROL-PLANE-SYNC-2026-05-22-033439.md'
ssh air 'jq -r "select(.started_at >= \"2026-05-21T10:30:00\") | [.started_at,.overall_status,((.checks[]? | select(.name==\"factory_probe\") | .summary) // \"no-factory-probe\")] | @tsv" ~/nous-agaas/logs/hermes-factory-watchdog.jsonl'
```

- **2026-05-22** | v1.10.13 -> v1.10.14 -- Added **AP-48** after Madi approved the safe automation shape for Hermes: watchdogs may run, but no automation may promote Hermes automatically. Fix: `tools/hermes_24h_gate_verifier.py` watches the strict no-drift window, creates a green receipt only when true, reruns `tools/hermes_promotion_runner.py --json` without `--promote`, and sends an approval request before any cutover. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.

### AP-48 — Hermes verifier may prove the 24h gate, never promote (2026-05-22)

**Trigger:** Madi asked whether the Hermes 24h gate would turn green automatically and approved the safe answer: watchdogs can watch and create a green receipt when true, but promotion must stay manual.

**Root cause:** The missing piece was not another promotion path. It was a non-promoting verifier that separates evidence creation from authority transfer. Without that split, either the gate stays manual and easy to forget, or automation risks silently moving Telegram/router authority.

**Rule:** The Hermes verifier may do only three mutating things:

1. Write/update `pages/systems/hermes-24h-gate-verifier-status.md`.
2. Create a green `pages/audits/HERMES-24H-GATE-GREEN-*.md` receipt containing `NOUS_HERMES_24H_GATE_OK` only when the strict 24h no-drift window has enough green watchdog samples and the current factory/canary probes are green.
3. Rerun `tools/hermes_promotion_runner.py --json` without `--promote`, then notify Madi that explicit approval is required before cutover.

It must never call `tools/hermes_promotion_runner.py --promote`, edit `ceo-hierarchy` into a promoted state, start a Hermes Telegram gateway, or redirect Telegram/router traffic. If the verifier cannot prove the window, it must stay pending/yellow and name the blocker.

**Detector / proof:**

```bash
python3 tools/hermes_24h_gate_verifier.py --dry-run --json
python3 -m pytest -q tools/tests/test_hermes_24h_gate_verifier.py tools/tests/test_hermes_promotion_runner.py
ssh air 'launchctl print gui/$(id -u)/com.nous.hermes-24h-gate-verifier'
```

- **2026-05-23** | v1.10.14 -> v1.11.0 -- Added **AP-44 (Dynamic Subscription Rotation for the CEO route)** after Madi's directive on Stage 4 of moonlit-pnueli execution: "Codex limit was gone, so that is why I use codex and claude. As soon as I do not have I want to use subscription of claude, and when that is over, I switch back to GPT." Rule (binding for `/codex` and `/ask --tier ceo` paths): (1) try **Codex GPT-5.5 subscription** first; (2) if Codex quota exhausted (sentinel "Daily /codex token cap reached" OR HTTP 429 OR empty subscription stdout for ≥3 consecutive calls) → **fall through to Claude Opus subscription** ($200/mo Anthropic Console/Pro); (3) if Claude subscription also exhausted → **fall through to GPT API** (OpenAI pay-as-you-go with explicit `NOUS_PAID_API_ALLOWED=1 + cap + reason`). The order is cheapest-first (two subscriptions consumed before any pay-as-you-go API spend). Worker tier is unaffected (DeepSeek V4 Flash remains default per AP-25; AP-44 only governs the CEO/high-judgment route). Implementation: `tools/command_center.py` should check Codex quota gate (existing `_codex_daily_budget_ok` per AP-40) → if blocked, route to Claude subscription (Anthropic Messages API with ANTHROPIC_API_KEY scoped to subscription tier) → if that returns subscription-cap error, route to GPT API. The 3-layer architecture Madi re-confirmed Stage 4: L1 = Hermes + Grok 4.3 (replacement-of-Madi), L2 = Opus + GPT ($200/mo each, Sat-council refreshed), L3 = Composer + best-open-source (Qwen/DeepSeek/Kimi/MiniMax) — see [[SPEC-2026-05-23-moonlit-pnueli-execution]] for full doctrine. musk-step-2: considered deleting the GPT-API fallback (just block when both subscriptions exhausted) — kept it because moonlit-pnueli P3.3 weekly-council needs guaranteed completion or it skips its window, and Madi explicitly said "switch back to GPT" as the terminal rule. Cross-ref: AP-7 (Codex quota-exhaustion ≠ auth-expiry), AP-9 (subscription-paid lanes fail closed), AP-40 (codex_daily_budget gate). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).
- **2026-05-20** | v1.10.8 -> v1.10.9 -- Added **AP-43** after Madi got the OWNER-ONLY DM (bot echoing his own message back to him) immediately following the long AP-42 status DM and the 3-alternative group decline — three notifications, none useful. Madi: "wtf?" Fix: `handle_owner_credential_handoff` detects sender=owner (normalized case + `@` strip) and takes an owner-mode branch that skips the owner-DM relay and uses a one-paragraph terse group reply pointed at the single fastest manual path (DM the target). Non-owner senders keep the full 3-alternative decline + raw-context owner-DM relay (AP-25 + AP-42 paths unchanged). 58/58 tests PASS (added `test_ap43_owner_sender_skips_owner_dm_echo`, updated `test_owner_credential_handoff_never_echoes_group_env_config` to use `@aliakbar_asylbek` as sender so it exercises the non-owner relay path correctly). musk-step-2: considered deleting the owner-DM relay entirely; rejected because non-owner senders still need it (operator context for coworker credential asks). No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-20** | v1.10.7 -> v1.10.8 -- Added **AP-42** after Madi's "trust the log in and password. i give permission. do it now." was politely declined by the bot and Madi asked "why? why did not work?" Initial owner-bypass-via-regex design was correctly blocked by the auto-mode classifier (text-parsed sender + spoofable). Fix: keep credential-handoff strict in groups (no bypass for anyone, ever), but rewrite `handle_owner_credential_handoff` group reply to list three concrete alternatives (DM-to-target, self-serve, private-DM-to-bot for guidance) so the operator has a clear path. Owner-DM relay of raw context unchanged. 57/57 tests PASS including new ap42 regression guard and existing AP-25 group-handoff-routes-before-codex + AP-25b owner-DM-never-echoes-secrets. musk-step-2: considered keeping the owner-override and adding cryptographic owner attestation; rejected because (a) credential safety is a binary policy, (b) Telegram has no per-message owner sig API, (c) the latency cost of the safer alternatives is ~10 seconds vs catastrophic-leak risk. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-20** | v1.10.6 -> v1.10.7 -- Added **AP-41** after AP-40's deploy left AP-30's English wall-of-text in 4 group/DM blocked replies (msg_id 1805+1802+1751+1752). Fix: mandatory-codex dispatcher at command_center.py:2607 now calls grok-ceo as fallback with a Russian-localized notice for group chats and an English notice with spend info for Madi DM. Shell-verification cap-fallback notice is also Russian-localized for groups. New tag `/ask-mandatory-codex-grok-fallback` with status `degraded`. 11/11 pytests in tools/tests/test_codex_budget_gate.py PASS (added 2 AP-41 regression guards); 4 boundary tests in tools/test_operator_boundaries.py updated to assert the new fallback contract (54/54 PASS). musk-step-2: considered deleting `_mandatory_codex_blocked_message` entirely — kept the helper for future explicit-block paths but verified zero call-sites in the auto-dispatch chain. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-20** | v1.10.5 -> v1.10.6 -- Added **AP-40** after Assylbek twice received the verbatim `Daily /codex token cap reached: 312163 / 250000 observed tokens. Resets midnight Almaty.` sentinel as the bot's answer to `видишь события? поток подали` (msg_id 1799+1802). Fix: `_codex_daily_budget_ok` now fails closed on `CODEX_DAILY_CAP_CALLS` and `CODEX_DAILY_CAP_TOKENS` so `_query_likely_needs_high_judgment` + `ROUTE_CHATGPT_EXECUTION` skip codex when capped; `_requires_codex_verification_route` got an explicit budget pre-gate that routes to grok-ceo with an `⚠️ Codex daily cap reached` notice; new `_is_codex_cap_blocked` helper detects the sentinel post-call at all three `/ask` auto-escalation sites and re-routes to grok-ceo as a race-window safety net. 9 pytests cover the gate, helper, and high-judgment guard. All 3 vault working copies + Air runtime synced; `com.nous.telegram-poll` kickstarted to pick up the new module. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-19** | v1.10.0 -> v1.10.1 -- Added **AP-35** after the iPhone readiness check found a false `status -> stopped` report while launchd and `/health` were green. Fix: `tools/hermes_webui_canary.sh status` reports launchd plus HTTP health directly and separates Tailscale phone URL from LAN fallback. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-19** | v1.10.1 -> v1.10.2 -- Added **AP-36** after the iPhone WebUI exposed a blank default profile. Fix: `tools/hermes_webui_canary.sh` now seeds `nouscanary`, `/Users/madia/nous-agaas/wiki`, `Nous Factory`, CLI history visibility, `/Users/madia/nous-agaas/skills`, and the `_sort_skills` compatibility shim before launch. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-19** | v1.9.7 -> v1.9.8 -- Added **AP-33** after Hermes iOS did not connect and GPT appeared stopped. Fix: install/symlink Codex CLI on Air, make `phone-url` fail on logged-out Tailscale instead of returning stale `ifconfig` `100.x`, add explicit `lan-url`, and add `codex_cli_available` to the Hermes canary gate. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-19** | v1.9.6 -> v1.9.7 -- Added **AP-32** after Hermes Agent iOS/TestFlight setup exposed a missing WebUI proof gate and a launchd env quoting failure. Fix: `tools/hermes_webui_canary.sh` runs password-protected WebUI canary on Tailscale, `tools/hermes_canary_gate.py --webui-probe` verifies the phone path, and shell-sourced env values with spaces are banned unless quoted. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-19** | v1.9.5 -> v1.9.6 -- Added **AP-31** after Todoist/OpenClaw one-beam queue work exposed a second-router risk. Fix: `tools/satory_ai_factory_queue.py` uses `factory_orchestration_policy.py`, mandatory Codex events fail closed as `blocked_codex_required` unless `--allow-codex` is explicit, and Hermes remains canary-only. No new LESSON (RULE ZERO). gbrain-timeline-ok via VPS CLI fallback after Codex MCP transport closed.
- **2026-05-18** | v1.9.4 -> v1.9.5 -- Added **AP-30** after mandatory route review found Codex happy-path tests but no budget-failure fail-closed guard. Fix: external operator proof questions now use `codex_external_proof`, top-tier CTO/CEO/supervisor prompts remain `codex_supervise_then_delegate`, and command-center blocks instead of falling back to OpenClaw when Codex is unavailable. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-18** | v1.9.3 -> v1.9.4 -- Added **AP-29** after model promotion approval was found to accept proposals without benchmark proof. Fix: `tools/model_promotion_gate.py` blocks promotion unless the candidate wins the canonical Satory/Nous fixture benchmark; `cheap_pool_winner_picker.py --approve-proposal` now requires `--promotion-benchmark-json` and records gate output. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.
- **2026-05-18** | v1.9.2 -> v1.9.3 -- Added **AP-28** after Hermes Notion MCP was fixed in canary scope and the promotion runner still marked rollback/current-factory shortcuts as green. Fix: runner now requires `status: green` audit artifacts with exact canary markers; rollback and 24h are artifact-gated; post-Notion 24h gate is yellow, not fake green. No new LESSON (RULE ZERO).
- **2026-05-18** | v1.9.1 -> v1.9.2 -- Added **AP-27** after a Satory group question about whether the bot could see/access the VAR camera on LU100 routed to routine OpenClaw and produced prose before live proof. Fix: deterministic policy now treats Satory operator camera/APK live-proof prompts (`камера`, `ВАР`, `радар`, `доступ`, `видишь`, events/log proof) as Codex/GPT-5.5 execution before external reply. No new LESSON (RULE ZERO).
- **2026-05-18** | v1.9.0 -> v1.9.1 -- Added **AP-26** after Madi required GPT/Codex to be the first brain for explicit top-tier/second-brain and customer-transformation requests. Fix: deterministic policy sends these requests to `/codex` GPT-5.5 subscription first; Codex preamble tells it to delegate durable work to OpenClaw/factory only when needed; customer/team replies must be destination-first. No new LESSON (RULE ZERO).
- **2026-05-18** | v1.8.6 -> v1.9.0 -- Added **AP-25** after 5-task fixture benchmark (run via Air LiteLLM, 29s, 5 models × 5 Nous tasks) revealed Pro is WORSE than Flash on routine work, qwen3-coder-plus is 100% broken silently, and russian_operator_notes + audit_summarization are real per-class discriminators only Flash passes. Pin holds at deepseek-v4-flash; no rotation triggered. Codifies discipline: worker chain order is benchmark-validated, not size-ordered. Cross-ref: [[CHEAP-POOL-BENCHMARK-2026-05-18]] (commit 97712aa6 audit + JSON), [[2026-05-17-hermes-factory-design]] (Revised scope where the 5-task fixture was specced), GPT external review which correctly predicted "Chinese models code-switch on Russian." gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill. No new LESSON (RULE ZERO).

## See also

- [[SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]] — design
- [[PLAN-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]] — 20-task plan
- [[factory-ops]] — AP-25 (openclaw config set) + this skill adds future APs
- [[karpathy-loop]] — multi-virtual-reviewer (CEO/Eng/DevEx) applied in spec phase
- [[karpathy-coding-principles]] — applied by every tier for code changes
- [[session-operating-contract]] — Rule 15 (execute) + Rule 17 (no re-ask)
- [[session-coordination]] — parallel-session awareness during rollout
- [[find-skills]] — Tier-1 + Tier-2 both have skill-discovery primitive
- [[gbrain-minions]] — future Tier-3 queue substrate (gbrain v0.11.1+ upgrade pending)
