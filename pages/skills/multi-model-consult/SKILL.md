---
type: skill
id: multi-model-consult
title: "Multi-model consult skill (subscription-first council with paid API guard)"
version: 1.5.0
tier: 2
date: 2026-05-20
last_updated: 2026-05-23
status: active
owner: claude-opus-4-7
tags: [multi-model, consult, opus, gpt, codex, grok, deepseek, arbitrator, ceo-tier, ship-and-learn]
tools: [Bash, Read, "mcp__gbrain__*"]
triggers:
  - "I don't know"
  - "what is the latest"
  - "current best practice for"
  - "compare X vs Y"
  - "research before deciding"
  - "/consult"
  - "I need a second opinion"
  - "ask all three models"
  - "multi-model this"
related:
  - skills/ceo-hierarchy
  - skills/karpathy-loop
  - skills/musk-algorithm
  - SPEC-2026-05-19-multi-model-consult-skill-design
---

# multi-model-consult v1.5.0

> "Finding an answer is a new skill, so you keep evolving." — Madi 2026-05-19 14:25 KZT, MISSION delivery.

## Purpose

Any agent or lane invokes this skill when it hits an unknown that exceeds single-model judgment. The skill spawns three CEO-tier models in parallel, runs an arbitration pass with DeepSeek, and returns a structured answer with confidence + dissent paper trail.

The arbitration IS the new skill: it picks the answer most grounded in real evidence (file paths, live commands, citations) over confident-sounding-but-untestable.

**Architecture (Madi's stated design):**
- CEO tier: Opus 4.7 + Codex GPT-5.5 + Grok-4-fast
- Cheap-labor arbitrator: DeepSeek V4 Flash

**Subscription-first amendment (2026-05-20):** direct paid APIs are disabled by default. Codex/GPT-5.5 is `subscription`; local Opus answer is `local`; Grok is `xai_api`; Opus direct is `anthropic_api`; DeepSeek arbitration through LiteLLM/OpenRouter is `openrouter`. Paid surfaces require `NOUS_PAID_API_ALLOWED=1`, `NOUS_PAID_API_CAP_USD`, and `NOUS_PAID_API_REASON` before any key lookup or HTTP call.

## How to Invoke

### CLI (primary path)
```bash
python3 tools/multi_model_consult.py \
  --question "Is library X safe to upgrade to v2?" \
  [--context-slug pages/specs/my-spec.md] \
  [--output-file pages/audits/CONSULT-<consult_id>.json] \
  [--include-local-opus-answer "My existing analysis..."] \
  [--dry-run]
```

### Python library
```python
from tools.multi_model_consult import consult

result = consult(
    question="What is the current best practice for X?",
    context_slug="pages/skills/ceo-hierarchy/SKILL.md",
    local_opus_answer=None,  # or pass the current Opus session's answer
)
```

### When to use (auto-fire conditions per karpathy-loop AP-12)
1. A lane hits a question outside its training/scope: "I don't know what X is"
2. A canary fails with ambiguous cause after routine self-repair failed
3. A factory worker can't decide between routes (AP-37 route ambiguity)
4. Madi asks an open question tagged `/consult` in Telegram
5. Any question hitting karpathy-loop AP-12 predicates: IR/retrieval, novel cost/latency, security/billing isolation, single-ablation evidence, or lock-in risk

### When NOT to use (cost discipline)
- Low-risk routine work: single Telegram message edit, typo fix, known-answer lookups
- Questions answerable from vault search alone (try `mcp__gbrain__search` first)
- Canary tests or smoke checks (use dedicated test tools)

## What It Returns (Canonical Schema)

```json
{
  "consult_id": "consult_2026-05-19T15:00:00Z_<sha8>",
  "question": "string",
  "context_slug": "pages/... or empty",
  "answers": [
    {"model": "opus-4-7", "billing_surface": "anthropic_api", "answer": "...", "confidence": 0.90, "tokens": 1234, "latency_ms": 5400, "cost_usd": 0.012},
    {"model": "codex-gpt-5.5", "billing_surface": "subscription", "answer": "...", "confidence": 0.90, "tokens": 980, "latency_ms": 8200, "cost_usd": 0.00},
    {"model": "grok-latest-with-x-search", "billing_surface": "xai_api", "answer": "...", "confidence": 0.80, "tokens": 1100, "latency_ms": 12400, "cost_usd": 0.003}
  ],
  "arbitration": {
    "winner_model": "codex-gpt-5.5",
    "rationale": "GPT had concrete file paths + live test commands; Opus restated; Grok had stale data.",
    "agree_count": 2,
    "dissent_count": 1,
    "arbitrator_model": "deepseek-v4-flash",
    "billing_surface": "openrouter",
    "arbitrator_cost_usd": 0.0001
  },
  "billing_surfaces": {
    "opus-4-7": "anthropic_api",
    "codex-gpt-5.5": "subscription",
    "grok-latest-with-x-search": "xai_api",
    "deepseek-v4-flash": "openrouter"
  },
  "paid_api_policy": {"allowed": false, "cap_usd": 0.0, "reason": ""},
  "actionable_answer": "string (the winner's answer)",
  "dissent_notes": "string (what the dissenter said, for paper trail)",
  "evidence_paths": ["pages/...", "https://..."],
  "skill_update_proposal": "if all 3 agreed on a new pattern, propose AP for which skill",
  "total_cost_usd": 0.015,
  "model_unavailable": []
}
```

Failed models appear with `"error"` key instead of `"answer"`. Arbitration continues on remaining successful answers (soft-fail design).

## Cost Discipline

| Item | Limit |
|------|-------|
| Per-consult cap | $0.50 USD |
| Daily cap (all consults) | $20.00 USD |
| DeepSeek arbitrator cost | < $0.001 per call |
| Codex GPT-5.5 via subscription | $0.00; no OpenAI API fallback |
| Grok (xAI API) | Disabled by default; requires explicit cap + reason |
| Opus 4.7 API | Disabled by default; local Opus answer allowed via `--include-local-opus-answer` |
| DeepSeek arbitrator via OpenRouter | Disabled by default when it would make a paid call; fallback picks highest-confidence answer |

Cost ledger: `pages/systems/multi-model-consult-ledger.jsonl` (JSONL, one line per consult). Run daily total check:
```bash
python3 -c "import json; lines=[json.loads(l) for l in open('pages/systems/multi-model-consult-ledger.jsonl')]; print(sum(l['total_cost_usd'] for l in lines if l['ts'][:10] == '$(date +%Y-%m-%d)'))"
```

## Failure Modes

| Failure | Behavior |
|---------|----------|
| One model timeout (30s default) | Mark as `error`; arbitrate on remaining 2 |
| Two models fail | Mark both as `error`; arbitrate on remaining 1 (auto-winner) |
| All three models fail | Return `{"model_unavailable": ["opus-4-7", "codex-gpt-5.5", "grok-latest-with-x-search"]}` with no actionable answer |
| Arbitrator (DeepSeek) fails | Fallback: pick highest-confidence successful answer; log `arbitrator_error` |
| xAI key missing from Air | Grok returns `error: Cannot fetch XAI_API_KEY from Air` |
| Paid API guard off | Opus/Grok/OpenRouter return `paid_api_disabled` before fetching keys or calling HTTP |
| Codex subscription cap hit | Codex returns `error: subscription_cap: ...` |
| LiteLLM on Air:4000 unreachable | Arbitrator fallback to highest-confidence |
| Cost cap exceeded | Warning added to result as `cap_warning`; answer still returned |

Per-model timeout: `MODEL_TIMEOUT_S = 30` (configurable via source). Arbitrator timeout: `ARBITRATOR_TIMEOUT_S = 20`.

## Anti-Patterns

### AP-1 — Don't call consult for routine questions
Routine work (Telegram edits, typo fixes, single-model-scope answers) should NOT trigger a 3-model $0.50 spend. Use `mcp__gbrain__search` first.

### AP-2 — Don't embed secrets in code
xAI key is fetched lazily via `ssh air 'grep XAI_API_KEY ~/nous-agaas/.env'`. Never hardcode tokens.

### AP-3 — Don't promote Hermes through consult
Hermes stays canary-only (AP-21). This skill does NOT route through Hermes. Hermes is observer/escalation only.

### AP-4 — Don't treat consult as a write operation
The consult tool is read-only (query → answer). Side effects (Todoist updates, git commits) are the calling lane's responsibility after receiving `actionable_answer`.

### AP-5 — Retry on all-models-fail before escalating to Madi
MISSION self-healing: if all 3 models error, auto-retry once with backoff. Only escalate to Madi after 3 failed retries.

### AP-6 — Default to the shared continuity packet
When `tools/multi_model_consult.py` is called without an explicit `--context-slug`, it must refresh and inject `pages/systems/AGENT-CONTINUITY-PACKET.md`. This is the failover contract: if Claude dies, GPT/Codex or Grok receives the same current operating state without asking Madi to restate context. Explicit `--context-slug` still wins for narrow research questions.

### AP-7 — Direct model HTTP calls must use existing auth and CA contracts
Direct xAI/Grok calls must retry macOS Python `CERTIFICATE_VERIFY_FAILED` with `certifi` before classifying Grok unavailable. Direct Air LiteLLM arbitration must send `Authorization: Bearer $LITELLM_MASTER_KEY`, loaded from env or Air `~/nous-agaas/litellm/.env`; unauthenticated LiteLLM 401 is a probe bug, not a model failure.

### AP-8 — Failover requires pre-model task capture, not only shared context
The continuity packet is necessary but insufficient. Telegram model lanes must write a durable start event before invoking Claude, GPT/Codex, Grok/OpenClaw, or Opus. The canonical files are `pages/systems/model-failover-ledger.jsonl` and `pages/systems/MODEL-FAILOVER-LATEST.md`. `/resume gpt|grok|claude|opus` must build the replacement prompt from that ledger so Madi does not have to restate the task.

### AP-9 — Paid API routes fail closed without visible cap and reason

Default consult mode may call subscription/local routes only. Before direct Opus, direct Grok, or OpenRouter arbitration can spend, the process must have `NOUS_PAID_API_ALLOWED=1`, a positive `NOUS_PAID_API_CAP_USD`, and `NOUS_PAID_API_REASON`. The ledger must record `billing_surface` and `paid_api_policy`. The guard runs before credential fetch, so a disabled paid route cannot leak into a key lookup or HTTP call.

## Cross-References

- `[[skills/ceo-hierarchy]]` v1.9.0 — model routing tiers; this skill IS the "I don't know" auto-spawn path
- `[[skills/karpathy-loop]]` v1.12.0 — AP-12 Council escalation; this skill IS the implementation of Council for AP-12 triggers
- `[[skills/musk-algorithm]]` v1.3.0 — musk-step-2: no MCP server, no new deps, no new framework added
- `[[SPEC-2026-05-19-multi-model-consult-skill-design]]` — original spec (commit 9782bbb0)
- `[[CHEAP-POOL-BENCHMARK-2026-05-18]]` — deepseek-v4-flash benchmark winner for cheap arbitration

## Registered Adapters (tools/multi_model_consult.py)

| Function | Model | Method |
|----------|-------|--------|
| `_call_opus()` | opus-4-7 | Anthropic Messages API or `--include-local-opus-answer` |
| `_call_codex()` | codex-gpt-5.5 | `ssh air codex exec -m gpt-5.5` subprocess |
| `_call_grok()` | grok-4-fast-reasoning | HTTPS POST to api.x.ai with lazy-fetched XAI_API_KEY |
| `_arbitrate()` | deepseek-v4-flash | HTTP POST to LiteLLM air:4000 |

## Failover Continuity

The shared context source is `pages/systems/AGENT-CONTINUITY-PACKET.md`, generated by:

```bash
python3 tools/agent_continuity_packet.py
```

Use it when switching lanes:

- Claude died -> send `/codex <same task>` or run Codex with the packet injected.
- GPT/Codex died -> send `/ask <same task>` or run `multi_model_consult.py`; Grok gets the packet by default.
- Grok/OpenClaw died -> send `/codex <same task>` for tool-capable supervisor work or `/code <same task>` for Claude Code.
- Any lane died after Telegram received the task -> send `/resume gpt`, `/resume grok`, `/resume claude`, or `/resume opus`.

Do not create model-private memory. Write back to Obsidian/gbrain/OpenBrain so every lane can retrieve the same state.

## Timeline

- **2026-05-20** | v1.4.0 added subscription-first paid API guard. Every answer/arbitration result records `billing_surface`; Opus/Grok/OpenRouter paid paths fail closed before key lookup unless cap+reason are visible; CLI accepts `--allow-paid-api`, `--paid-api-cap-usd`, and `--paid-api-reason` for explicit approved canaries. No new LESSON (RULE ZERO).
- **2026-05-19** | Spec authored by Claude Opus 4.7 lane. Handshake `ce5b43f4`. MISSION-2026-05-19 delivery.
- **2026-05-20** | v1.0.0 implemented (T1 tool + T2 skill + T3 tests). xAI key live. Session `agent-multi-model-consult-2026-05-20-T280`.
- **2026-05-20** | v1.1.0 added shared failover-continuity packet default. `tools/multi_model_consult.py` refreshes/injects `pages/systems/AGENT-CONTINUITY-PACKET.md` when no explicit context slug is supplied, while `/code` and `/codex` spawned agents are instructed to refresh/read the same packet first. No new LESSON (RULE ZERO).
- **2026-05-20** | v1.2.0 repaired live continuity smoke failures: xAI direct HTTPS inherited macOS Python's empty CA file and now retries with `certifi`, while DeepSeek arbitration now authenticates to Air LiteLLM using `LITELLM_MASTER_KEY` from runtime env files. No new LESSON (RULE ZERO).
- **2026-05-20** | v1.3.0 added pre-model failover ledger and Telegram `/resume` lane switching. `tools/model_failover_state.py` records model-lane starts before execution and renders `MODEL-FAILOVER-LATEST.md`; `command_center.py` supports `/resume gpt|grok|claude|opus` so replacement lanes continue from the captured event instead of asking Madi to restate context. No new LESSON (RULE ZERO).
- **2026-05-23** | v1.5.0 added 5 council adapters (`_call_gemini`, `_call_deepseek_pro`, `_call_kimi`, `_call_qwen`, `_call_composer`) routing through Air LiteLLM (4000), a generic `_call_via_litellm` helper with COUNCIL_PRICING table, and a `council_run(question, context, models, cap_usd, dry_run, wallclock_cap_s)` function for parallel N-way calls. Drives `tools/weekly_model_council.py` (moonlit-pnueli P3.3) for the Sat 03:00 KZT weekly-model-tier-review routine. Existing 3-model `consult()` API unchanged. No new LESSON (RULE ZERO).
