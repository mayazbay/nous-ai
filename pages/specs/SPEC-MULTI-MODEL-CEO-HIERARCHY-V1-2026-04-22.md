---
type: spec
id: SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22
title: "Multi-model CEO hierarchy v1 — Grok-4.20-reasoning president + Opus 4.7 executive + GLM-5.1/Grok-code workers, with 3-tier LiteLLM fallbacks, operator discipline, and workspace migration"
tags: [spec, multi-model, ceo-hierarchy, grok, opus, glm, worker-tier, litellm, openclaw-multi-agent, billion-dollar-solopreneur, 2026-04-22, session-57]
date: 2026-04-22
status: draft
last_updated: 2026-04-22
related:
  - "[[factory-ops]]"
  - "[[session-operating-contract]]"
  - "[[karpathy-loop]]"
  - "[[karpathy-coding-principles]]"
  - "[[session-coordination]]"
  - "[[infrastructure]]"
  - "[[command-center]]"
  - "[[find-skills]]"
  - "[[gbrain-ops]]"
---

# Multi-model CEO hierarchy v1 — Grok president + Opus executive + workers

**Authoring standard (Madi, 2026-04-22):** think like Elon Musk's CTO combined with Gary Tan + Karpathy. Billion-dollar-solopreneur with 1-2 humans + agents running everything. Long-term evolving. Musk 5-step elimination. Everything saved to Obsidian + gbrain + karpathy substrate. 100% bulletproof or honest STOP with handoff.

## Goal

Replace Madi as the human cognitive top-of-stack with **Grok-4.20-reasoning (lowest-hallucination reasoner)** that reads persistent substrate (handoff + MEMORY + gbrain + karpathy-loop + karpathy-coding-principles + session-coordination registry) and decides: answer directly, or delegate to **Opus 4.7 (digital CEO, full skill pack)**, or trigger research. Opus delegates narrow subtasks to **worker tier (Grok-code-fast-1 for coding, GLM-5.1 for bulk, GLM-4.5-flash for free-tier fallback)** to avoid burning Opus tokens on deterministic labor.

Every layer inherits the compounding substrate the factory already has: 79/125 skills loaded, gbrain 1118+ pages, karpathy-loop v1.0 + karpathy-coding-principles v1.0 + SOC v1.9 + gstack + find-skills. Nothing starts from nothing.

## Inputs consumed (what the 4-review process produced)

1. **CEO review** — Grok-on-top is a 3-star dress; 10-star is substrate + Langfuse evals. Risks flagged: Langfuse unshipped → no eval truth; Phase-0 is the revenue path.
2. **Engineering review** — "config change only" is false: `nous`-as-subagent loses `SOUL.md` + `IDENTITY.md` + `USER.md`. `sessions_spawn` has no schema enforcement + no loop detection + best-effort announce. Must reframe: 2-tier first, workspace migration, explicit timeouts.
3. **DevEx review** — 2× latency, 1.75–2.5× cost; hallucination surface at Grok-wrap layer; `/ask-direct` escape hatch mandatory day 1; urgent keyword auto-bypass; cost footer per reply; correlation_id + `/trace`; editMessageText progress updates (not new messages); hard timeouts with sentinel replies.
4. **OpenClaw deep-dive** — all primitives live: `sessions_spawn` tool + per-agent `model` + per-agent workspace + per-agent `systemPromptOverride` + LiteLLM per-model routing; ACP bundled. Deployment recipe has 8 concrete steps; blockers enumerated.

Madi's explicit directives after reviews:
- "I want the Grok (smaller model, grok-4.20 reasoning or whatever latest) telling to Opus 4.7, and then Opus delegates for the module that does the labor work." — 3 tiers, not 2.
- "Grok since it has the lowest hallucination rate. The smartest is Opus, and that is why I want them to handle it like a team and then manual work will be done with cheaper module never with Opus — too expensive for tokens. Maybe Grok coding or GLM-5.1."
- Fallback chain: Grok → Sonnet-4.5-thinking → GLM-4.6 → Haiku-4.5 (from Madi's fallback analysis paste).

## Non-goals (Musk step-2 — what this spec explicitly does NOT ship)

- **Langfuse wiring.** DELETED from v1 after 5-lens analysis (Musk/Karpathy/Tan/Stanford-hacker/billion-dollar-solopreneur — all 5 said ship-now). Replaced with `tools/tier_log.py` — a ~50-line JSONL appender invoked by each tier. One JSON line per call: `{correlation_id, tier, model, tokens_in, tokens_out, latency_ms, cost_est, decision}`. All tiers append to `~/nous-agaas/logs/ask-hierarchy.jsonl`. `/trace` reads via jq. Cost alarm coefficient update reads via jq. gbrain autopilot ingests daily. **Logs are truth; dashboards decorate.** Langfuse becomes a v2 consideration only if we outgrow file-based truth — which happens at 10,000+ queries/day (we're at ~30).
- **Minions runtime upgrade** (gbrain v0.11.1+). Deferred — blocked on local fork divergence per earlier audit. Tier 3 delegation uses `sessions_spawn` not Minions queue for v1.
- **Conductor Mac app** (Tan's paid parallel-worktree tool). Not adopting; `superpowers:dispatching-parallel-agents` + git-worktrees already cover our use case.
- **A/B eval harness.** Defer to v2. Ship the router; measure via JSONL + manual review for 7 days before eval infrastructure.
- **Replacing Opus as executor.** Tier 2 stays Opus. This is NOT a migration; it's an *addition* of a top tier + a worker tier.

## Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║  Madi (human)  →  Telegram DM @nousAGaaSbot                      ║
╚══════════════════════════════════════════════════════════════════╝
                              │
                              ▼ inbound message
╔══════════════════════════════════════════════════════════════════╗
║  URGENT-KEYWORD BYPASS (pre-Tier-1)                              ║
║    regex: urgent|broke|down|prod|демо|срочно|critical|now        ║
║    → routes to /ask-direct path (Tier 2 only)                    ║
╚══════════════════════════════════════════════════════════════════╝
               │ (no keyword match)                │ (match)
               ▼                                   │
╔══════════════════════════════════════════════════════════════════╗
║  TIER 1 — PRESIDENT / CEO PROXY                                  ║
║  Agent: `grok-ceo` (new OpenClaw agent)                          ║
║  Workspace: /home/node/.openclaw/workspaces/grok-ceo/            ║
║    own SOUL.md + AGENTS.md + IDENTITY.md (CEO persona +          ║
║    delegation contract)                                          ║
║  Model: litellm/grok-reasoning → grok-4.20-0309-reasoning         ║
║  Fallback chain: sonnet-4-5-thinking → glm-5.1 → haiku-4-5        ║
║  maxSpawnDepth: 2, subagents.allowAgents: ["nous"]               ║
║  runTimeoutSeconds: 90 (hard) — if timeout, sentinel reply       ║
║  Job: read TG msg + handoff + MEMORY + session-coord + gbrain    ║
║       search. Output ONE of 3 verdicts:                          ║
║    (i)  answer_directly → compose reply → return                 ║
║    (ii) delegate_to_tier_2 → emit structured directive JSON      ║
║         → sessions_spawn({agentId:"nous", task:<directive>,      ║
║           runTimeoutSeconds:180})                                ║
║    (iii) research_only → gbrain search → compose reply           ║
║  Tools: Read (vault), Bash (limited to gbrain CLI + session_scan)║
║    NOT: Edit, Write, shell mutations, file creation.             ║
╚══════════════════════════════════════════════════════════════════╝
               │                                   │
               │ (i) answer                        │ (ii) delegate
               │ (iii) research                    │ structured JSON
               ▼                                   ▼
    [TG response composer]        ╔══════════════════════════════════════════════════╗
                                  ║  TIER 2 — EXECUTIVE (DIGITAL CEO)               ║
                                  ║  Agent: `nous` (existing, unchanged agent ID)    ║
                                  ║  Workspace: /home/node/.openclaw/workspace/      ║
                                  ║    (MIGRATED: SOUL/IDENTITY/USER content         ║
                                  ║     moved into AGENTS.md so subagent context     ║
                                  ║     doesn't lose the 128-skill doctrine)         ║
                                  ║  Model: litellm/opus → claude-opus-4-7            ║
                                  ║  Fallback: sonnet-4-6 → glm-5.1                   ║
                                  ║  runTimeoutSeconds: 180 (hard)                    ║
                                  ║  Job: parse Tier-1 structured directive,         ║
                                  ║       plan, execute using full skill pack,       ║
                                  ║       delegate narrow subtasks to Tier 3,        ║
                                  ║       return structured report JSON to Tier 1.   ║
                                  ║  Tools: Full factory surface (Edit, Write, Bash, ║
                                  ║       skills, gbrain MCP, sessions_spawn for     ║
                                  ║       Tier 3).                                    ║
                                  ╚══════════════════════════════════════════════════╝
                                                  │
                                                  ▼ sessions_spawn per worker-need
                                  ╔══════════════════════════════════════════════════╗
                                  ║  TIER 3 — WORKERS                                ║
                                  ║  Routed via sessions_spawn from `nous` with      ║
                                  ║  `model` override per task:                       ║
                                  ║    • coding → litellm/grok-code-fast             ║
                                  ║      (new LiteLLM alias → grok-code-fast-1)      ║
                                  ║    • bulk/long-context → litellm/glm-5.1         ║
                                  ║    • free-tier/cheap polls → litellm/glm-4.5-    ║
                                  ║      flash                                        ║
                                  ║  runTimeoutSeconds: 60 per worker call            ║
                                  ║  Job: narrow deterministic task. No planning.    ║
                                  ║       Returns to Tier 2.                          ║
                                  ╚══════════════════════════════════════════════════╝
                                                  │
                                                  ▼ results bubble up
                                  ╔══════════════════════════════════════════════════╗
                                  ║  TIER 2 composes structured report:              ║
                                  ║    { status, verified[], unverified[],           ║
                                  ║      artifacts[], next }                          ║
                                  ║  Returns to Tier 1 via sessions_spawn announce.  ║
                                  ╚══════════════════════════════════════════════════╝
                                                  │
                                                  ▼
                                  ╔══════════════════════════════════════════════════╗
                                  ║  TIER 1 composes Madi-facing reply:              ║
                                  ║    [grok-summary] <1-3 paragraphs>               ║
                                  ║    [opus-raw] <Tier 2's structured report>       ║
                                  ║    [cost-footer] — cost: $X.XX (t1 $../t2 $../  ║
                                  ║      t3 $..) | day-total: $Y.YY/$30.00           ║
                                  ║    [trace-id] — msg_id=<tg_msg_id>               ║
                                  ║  → Telegram delivery via tg_send.sh              ║
                                  ╚══════════════════════════════════════════════════╝
```

## Model inventory + LiteLLM aliases (source of truth for config)

| Alias | Target | Role | Cost per M tok (in/out) | Timeout |
|---|---|---|---|---|
| `litellm/grok-reasoning` | xAI `grok-4.20-0309-reasoning` | Tier 1 primary | ~$3/$15 | 90s |
| `litellm/sonnet-4-5-thinking` | Anthropic `claude-sonnet-4-5` thinking-mode | Tier 1 fallback | $3/$15 | 90s |
| `litellm/opus` | Anthropic `claude-opus-4-7` | Tier 2 primary | $15/$75 | 180s |
| `litellm/sonnet` | Anthropic `claude-sonnet-4-6` | Tier 2 fallback | $3/$15 | 180s |
| `litellm/grok-code-fast` | xAI `grok-code-fast-1` | Tier 3 (coding) | $0.20/$1.50 | 60s |
| `litellm/glm-5.1` | OpenRouter `z-ai/glm-5.1` | Tier 3 (bulk) | ~$0.50/$2 | 60s |
| `litellm/glm-4.5-flash` | ZAI free tier | Tier 3 (polls) | $0 | 60s |
| `litellm/haiku-4-5` | Anthropic `claude-haiku-4-5-20251001` | Availability floor | $1/$5 | 60s |

**LiteLLM fallback chains (config.yaml `router_settings.fallbacks`):**
```yaml
fallbacks:
  - grok-reasoning: [sonnet-4-5-thinking, glm-5.1, haiku-4-5]
  - opus: [sonnet, glm-5.1]
  - sonnet-4-5-thinking: [opus, sonnet, glm-5.1]
  - grok-code-fast: [glm-5.1, grok-reasoning]
  - glm-5.1: [glm-4.5-flash, grok-reasoning, sonnet]
  - glm-4.5-flash: [glm-5.1, grok-reasoning]
```

## Handoff protocols (structured JSON between tiers)

### Tier-1 → Tier-2 structured directive

```json
{
  "tier": 1,
  "correlation_id": "tg_<msg_id>",
  "intent": "<one-sentence user intent>",
  "delegation": "execute_via_tier_2",
  "success_criteria": [
    "<criterion 1 — verifiable>",
    "<criterion 2 — verifiable>"
  ],
  "response_shape": "deliverable" | "status" | "explanation",
  "context_refs": ["<wikilink or file path>", ...],
  "budget_hint": "~N Opus calls + M worker calls",
  "timeout_seconds": 180,
  "escape_hatches": {
    "if_blocked": "return partial + next-session-task",
    "if_over_budget": "return partial + cost-remaining"
  }
}
```

### Tier-2 → Tier-1 structured report

```json
{
  "tier": 2,
  "correlation_id": "tg_<msg_id>",
  "status": "done" | "partial" | "blocked" | "timeout",
  "verified": [
    {"claim": "...", "evidence": "command + output"}
  ],
  "unverified": [
    {"claim": "...", "reason": "..."}
  ],
  "artifacts": [
    {"type": "file"|"commit"|"tg_msg"|"launchd", "ref": "..."}
  ],
  "tier_3_calls": [
    {"model": "grok-code-fast|glm-5.1|...", "purpose": "...", "cost_est": 0.001}
  ],
  "next": "<exact command or task for future session>",
  "elapsed_seconds": 120,
  "cost_est_usd": 0.08
}
```

Tier 1 MUST include the raw Tier-2 report as `[opus-raw]` verbatim block below its `[grok-summary]` in the Madi-facing reply. No summarization of the structured report — prevents hallucination-wrap.

## Operator discipline (ship BEFORE routing production traffic)

### 1. `/ask-direct <query>` escape hatch (ships FIRST, day-1)
- Command handler in `command_center.py`: on `/ask-direct`, call `run_task.py` with `AGENT_ID=nous` and skip Tier-1 entirely.
- Reason: crisis mode (3am test) needs Opus-direct latency, not 2× round-trip. Also: debugging Tier-1 itself.

### 2. Urgent-keyword auto-bypass
- Regex at Telegram poller layer: `urgent|broke|down|prod|демо|срочно|critical|now|asap`
- Any match → auto-route to `/ask-direct` path (still Tier 2, skips Tier 1).
- Log the bypass decision: `"auto-bypass: matched 'urgent' keyword"`.

### 3. Cost footer on every reply
- Format: `— cost: $X.XX (t1 $.. / t2 $.. / t3 $..) | day-total: $Y.YY/$30.00`
- Implementation: Tier 1 reads LiteLLM response headers OR uses heuristic (`$0.08 × call-count per tier`).
- Alarm threshold tiers stay at existing `tools/litellm_cost_alarm.py`; update heuristic coefficients to reflect multi-tier call volume (session-55 coefficient underestimates when multi-tier is live).

### 4. `correlation_id` threading
- `correlation_id = "tg_<msg_id>"` attached to every subprocess call + openclaw agent invocation + gbrain timeline entry.
- Implementation: `run_task.py` accepts `--correlation-id`; `_run_openclaw` in `command_center.py` passes it; Tier-1 and Tier-2 both write it into their structured JSON.

### 5. `/trace <msg_id>` command
- New command handler. Reads logs across tiers, reconstructs timeline:
  ```
  t=0.0s  tier-1 received correlation_id=tg_12345
  t=0.3s  tier-1 decision: delegate_to_tier_2
  t=0.4s  tier-1 sessions_spawn(nous) with timeout=180s
  t=8.2s  tier-2 completed: status=done, 3 artifacts
  t=10.1s tier-1 composed reply with [grok-summary] + [opus-raw]
  t=10.3s tg_send delivered to chat_id=110793056 msg_id=<new>
  ```
- Source: openclaw session logs + tg_send.sh log + litellm access logs; joined by `correlation_id`.

### 6. `editMessageText` progress updates (not new messages)
- Telegram ack message: `⏳ Tier-1 analyzing...`
- Edit to: `🟡 Delegating to Tier-2 (nous/opus, ~8s est)`
- Edit to: `🔵 Tier-3 worker grok-code-fast processing 3 files`
- Final: NEW message with full reply + cost footer + [opus-raw] block.
- Prevents notification spam; gives operator trust via visibility.

### 7. Hard timeouts with sentinel replies
- Tier 1: 90s. On timeout: `🔴 TIER-1 TIMEOUT (grok-reasoning, 90s) — falling back to Tier 2 direct.`
- Tier 2: 180s. On timeout: `🔴 TIER-2 TIMEOUT (nous/opus, 180s) — task unverified. Run /trace tg_<msg_id>.`
- Tier 3: 60s. Tier 2 handles worker timeout internally; escalates to own retry or fallback model.
- NO hallucination-on-timeout. Tier 1 system prompt explicitly: "If Tier 2 does not return within timeout, reply with sentinel text VERBATIM. Do not invent content."

### 8. Loop-break guardrails
- `maxSpawnDepth: 2` globally — Tier 1 → Tier 2 → Tier 3 is maximum.
- `nous` has `subagents.allowAgents: ["*"]` with `maxChildrenPerAgent: 5` — Opus can spawn workers but not re-spawn grok-ceo.
- grok-ceo has `subagents.allowAgents: ["nous"]` — cannot spawn anything else.

## Workspace migration (mandatory — the "config-only change is false" eng finding)

Current `nous` workspace `/home/node/.openclaw/workspace/` has SOUL.md + IDENTITY.md + USER.md + AGENTS.md + TOOLS.md + MEMORY.md. When `nous` runs as subagent of `grok-ceo`, OpenClaw's subagent system prompt builder injects ONLY `AGENTS.md` + `TOOLS.md` (per `/app/docs/concepts/system-prompt.md`).

**Migration:** merge the critical parts of SOUL.md + IDENTITY.md + USER.md into AGENTS.md so subagent-invoked `nous` preserves the 128-skill doctrine + Madi context + CEO persona.

Sections to merge from SOUL.md into AGENTS.md:
- Persona voice + tone
- Non-negotiables (RULE ZERO, DONE protocol, 4 principles)

Sections from IDENTITY.md:
- Agent name + role
- Current project context

Sections from USER.md:
- Madi's preferences + communication style
- Hot project state (Phase-0, Satory, Spectra)

Do NOT delete the original SOUL.md/IDENTITY.md/USER.md files — they still work in depth-0 invocation of `nous`. Only ADD their critical content into AGENTS.md. Doctrine is duplicated across 2 surfaces; both paths work.

## Rollback plan

**One-command revert:**
```bash
ssh air 'docker exec openclaw openclaw config set "telegram.ask_target_agent" "nous"'
# OR edit run_task.py: AGENT_ID = "nous"
```

Reverts `/ask` routing to pre-hierarchy Opus-direct. `grok-ceo` agent + workspace remain but receive zero traffic. Full cleanup (delete workspace + agent) is a separate `openclaw agents remove grok-ceo` call.

**Risk window:** ~1 min between config-set and graceful container flush. Acceptable.

## Cost envelope

Pre-hierarchy (current Opus-direct):
- ~$0.08 per `/ask` × 30 calls/day = $2.40/day

Post-hierarchy (estimate):
- Tier-1 Grok: ~$0.04 per call × 30 = $1.20
- Tier-2 Opus: ~$0.08 per call × 18 (60% delegation rate) = $1.44
- Tier-3 workers: ~$0.002 per call × 12 (Opus-to-worker rate) = $0.02
- Per-`/ask` average: $0.09 (only 12% more than Opus-alone, because Tier-1 absorbs 40% of queries without Tier-2)
- Day total: ~$2.60 (+8%)

If Tier-1 over-delegates (hits 100% delegation rate):
- Per `/ask`: $0.04 + $0.08 + $0.002 = $0.12 (+50%)
- Day total: ~$3.60

Both within $30/day cap. Real measurement during 7-day observation window determines final numbers.

## Testing

### Unit tests (ship before production traffic)
- `tools/test_ceo_hierarchy_unit.sh`: 4 scenarios
  1. Tier-1-answer-directly: send simple factual query, assert Tier-2 not invoked
  2. Tier-1-delegate: send code-change query, assert Tier-2 invoked with structured directive
  3. Tier-1-research: send vault-query, assert gbrain CLI invoked, no Tier-2
  4. Tier-1-timeout: mock xAI timeout, assert fallback to `sonnet-4-5-thinking` via LiteLLM
- `tools/test_ceo_hierarchy_e2e.sh`: 1 real Telegram test from Mac (simulated) — full round-trip
- `tools/test_ask_direct_bypass.sh`: assert `/ask-direct` skips Tier-1 entirely
- `tools/test_urgent_keyword_bypass.sh`: assert `urgent` in message triggers direct path

### Integration tests (7-day observation)
- Log every `/ask` with `correlation_id`, per-tier token counts, per-tier latency, final cost.
- Manual review of 50 real queries: did Tier-1 route correctly? Did Tier-2 execute correctly? Any hallucination-wrap?
- Cost alarm heuristic updated with multi-tier coefficients.

### Cut-over criteria (all 6 GREEN before full routing)

1. `/ask-direct` shipped + 3 successful tests.
2. Urgent-keyword bypass shipped + 3 tests.
3. `correlation_id` + `/trace` shipped + visible timeline on 1 real call.
4. Cost footer on every reply.
5. Workspace migration done (nous AGENTS.md includes SOUL+IDENTITY+USER critical sections).
6. grok-ceo agent live + 10 successful synthetic `/ask` runs + 0 fabrication-on-timeout observed.

## Components to ship (atomic task list preview)

| # | Component | Effort | Dependency |
|---|---|---|---|
| 1 | LiteLLM config update: add Sonnet-4.5-thinking + Grok-code-fast aliases + update fallback chains | S | none |
| 2 | LiteLLM restart + verify each alias responds via curl | XS | 1 |
| 3 | `/ask-direct` command handler in `command_center.py` | S | none |
| 4 | Urgent-keyword regex at telegram_poll.py layer | XS | none |
| 5 | `correlation_id` threading: `run_task.py --correlation-id`, pass through all subprocess calls | M | none |
| 6 | `/trace <msg_id>` command handler (log joiner) | M | 5 |
| 7 | Cost footer formatter in reply composer | S | none |
| 8 | editMessageText progress updates | M | none |
| 9 | Create `grok-ceo` workspace dir on Air + populate SOUL/AGENTS/IDENTITY | S | none |
| 10 | `openclaw agents add grok-ceo --workspace ... --model litellm/grok-reasoning` | XS | 9 |
| 11 | Set `agents.list[grok-ceo].subagents.allowAgents=["nous"]` + `maxSpawnDepth=2` + `runTimeoutSeconds=90` | XS | 10 |
| 12 | Workspace migration: merge SOUL+IDENTITY+USER critical sections into `nous` AGENTS.md | M | none |
| 13 | Hard-timeout + sentinel reply handling in Tier-1 system prompt | S | 9 |
| 14 | Update `AGENT_ID` logic in `run_task.py` to accept parameter (default `grok-ceo`, bypass to `nous` on `/ask-direct`) | M | 3,10 |
| 15 | Unit tests (4 scripts in `tools/test_ceo_*`) | M | 1-14 |
| 16 | E2E test: real Telegram `/ask` from Mac | S | 15 |
| 17 | `tools/tier_log.py` — JSONL appender for per-tier telemetry. Each tier calls `tier_log.append(correlation_id, tier, model, tokens_in, tokens_out, latency_ms, cost_est, decision)`. Output: `~/nous-agaas/logs/ask-hierarchy.jsonl`. Replaces Langfuse. | S | 5 |
| 18 | Update `tools/litellm_cost_alarm.py` coefficients for multi-tier — reads `tier_log.py` JSONL for real delta | S | 17 |
| 19 | Gbrain timeline + vault wrapper skill `pages/skills/ceo-hierarchy/SKILL.md` + RESOLVER row + CLAUDE.md pointers | S | 16 |
| 20 | 7-day observation window: `tier_log.jsonl` accumulates + manual review 50 queries via `jq` | ongoing | 19 |
| 21 | Post-observation: decide keep / tune / rollback | — | 20 |

## Open questions (dogfooded per SOC Rule 17 phrasing test — these are real unknowns, not tactical re-asks)

- **[open-question]** Does `litellm/sonnet-4-5-thinking` alias work today, or does LiteLLM need an update to expose thinking-mode routing? Verify in Task 1.
- **[open-question]** Does OpenClaw's `sessions_spawn` honor per-spawn `model:` param correctly when the agent has its own `agents.list[i].model`? Needs 1 test before relying on it for Tier-3 dispatch.
- **[weak-edge]** Tier-1 system prompt engineering determines whether Grok actually emits valid JSON directives. First shipped version will need iteration.
- **[dependency-risk-RESOLVED]** Earlier draft deferred Langfuse; 5-lens analysis (2026-04-22) deleted Langfuse from v1 entirely, replaced with `tier_log.py` JSONL. File-based truth compounds at our query volume; Langfuse is v2-only-if-needed.
- **[model-drift]** Sonnet-4-5 availability is assumed; if Anthropic rate-limits or the `-thinking` variant isn't exposed, fallback chain loses its peer-tier layer and drops to GLM directly.

## Success criteria (measured, not asserted)

After 7 days of production routing:

1. ≥80% of `/ask` queries Tier-1 routed correctly (answer-directly for chat; delegate for execution).
2. 0 fabrication-on-timeout incidents (Tier-1 never invents Opus output when delegation fails).
3. Per-`/ask` cost increase ≤+20% vs Opus-direct baseline.
4. Tier-1 latency ≤12s p95; Tier-2 latency ≤25s p95 (serial through hierarchy).
5. Cost alarm heuristic tracks real spend within 30% accuracy.
6. 0 container-restart-related orphan subagent sessions.

If any 3 of 6 miss → rollback + iterate on system prompts + retry.

## See also

- [[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]] — sibling infra layer (session awareness)
- [[PHASE-0-COLLECTOR-DEPLOYMENT-2026-04-21]] — the revenue path this architecture serves
- [[factory-ops]] — will absorb new APs from this spec (likely AP-27+ post-ship)
- [[karpathy-loop]] — 6-axis scorecard applied at session-close
- [[karpathy-coding-principles]] — code-behavior discipline for every tier's work
- [[session-operating-contract]] — Rule 15/17 + AP-9 (no re-asking); this spec honors both
- [[find-skills]] — the meta-layer that helps Tier 1 / Tier 2 discover skills when needed
- [[gbrain-minions]] — if runtime upgrades to v0.11.1+, Tier 3 migrates from sessions_spawn to Minions jobs
- Research sources: [vercel-labs/skills](https://github.com/vercel-labs/skills) · [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) · [garrytan/gbrain](https://github.com/garrytan/gbrain) · [garrytan/gstack](https://github.com/garrytan/gstack) · 4 parallel review reports from session 56
