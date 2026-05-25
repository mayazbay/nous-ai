---
type: skill
id: multi-model-consult
title: "Multi-model consult skill (Opus + GPT-5.5 + Grok + DeepSeek arbitrator)"
version: 1.0.0
tier: 2
date: 2026-05-20
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

# multi-model-consult v1.0.0

> "Finding an answer is a new skill, so you keep evolving." — Madi 2026-05-19 14:25 KZT, MISSION delivery.

## Purpose

Any agent or lane invokes this skill when it hits an unknown that exceeds single-model judgment. The skill spawns three CEO-tier models in parallel, runs an arbitration pass with DeepSeek, and returns a structured answer with confidence + dissent paper trail.

The arbitration IS the new skill: it picks the answer most grounded in real evidence (file paths, live commands, citations) over confident-sounding-but-untestable.

**Architecture (Madi's stated design):**
- CEO tier: Opus 4.7 + Codex GPT-5.5 + Grok-4-fast
- Cheap-labor arbitrator: DeepSeek V4 Flash

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
    {"model": "opus-4-7", "answer": "...", "confidence": 0.90, "tokens": 1234, "latency_ms": 5400, "cost_usd": 0.012},
    {"model": "codex-gpt-5.5", "answer": "...", "confidence": 0.90, "tokens": 980, "latency_ms": 8200, "cost_usd": 0.00},
    {"model": "grok-latest-with-x-search", "answer": "...", "confidence": 0.80, "tokens": 1100, "latency_ms": 12400, "cost_usd": 0.003}
  ],
  "arbitration": {
    "winner_model": "codex-gpt-5.5",
    "rationale": "GPT had concrete file paths + live test commands; Opus restated; Grok had stale data.",
    "agree_count": 2,
    "dissent_count": 1,
    "arbitrator_model": "deepseek-v4-flash",
    "arbitrator_cost_usd": 0.0001
  },
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
| Codex GPT-5.5 via subscription | $0.00 (subscription first; API fallback if auth stale) |
| Grok (xAI API) | ~$0.003–0.015 per call at 1K tokens |
| Opus 4.7 | ~$0.012 per call at 1K tokens |

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

## Timeline

- **2026-05-19** | Spec authored by Claude Opus 4.7 lane. Handshake `ce5b43f4`. MISSION-2026-05-19 delivery.
- **2026-05-20** | v1.0.0 implemented (T1 tool + T2 skill + T3 tests). xAI key live. Session `agent-multi-model-consult-2026-05-20-T280`.
