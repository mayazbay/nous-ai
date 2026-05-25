---
type: spec
id: SPEC-2026-05-19-multi-model-consult-skill-design
title: "Multi-model consult skill (Opus + GPT-5.5 + Grok) — Spec-Kit /specify"
date: 2026-05-19
status: draft
owner: claude-opus-4-7
priority: p0
tags: [spec-kit, multi-model, consult, opus, gpt, codex, grok, x-search, deepseek, arbitrator, ship-and-learn, mission-2026-05-19]
related:
  - [[MISSION-2026-05-19-always-on-satory-ai-factory]]
  - [[skills/ceo-hierarchy]]
  - [[skills/karpathy-loop]]
  - [[skills/musk-algorithm]]
  - [[PLAN-30-DAY-SATORY-BDL-APK-ERAP-2026-05-19]]
---

# SPEC — Multi-Model Consult skill

> "Finding an answer is a new skill, so you keep evolving." — Madi 2026-05-19 14:25 KZT, MISSION delivery.

Spec-Kit shape. **Do not implement until Madi approves this spec.**

## Constitution (rules this spec inherits)

- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` — self-healing, bounded retries, no Madi-babysitting.
- `[[skills/ceo-hierarchy]]` v1.9.0 — model routing tiers, AP-25 worker chain benchmark validation, AP-37 mandatory Codex for external operator proof.
- `[[skills/karpathy-loop]]` v1.12.0 — 6-axis scorecard; AP-12 Council escalation when plan hits IR/retrieval, novel cost/latency, security/billing isolation, single-ablation evidence, or lock-in risk.
- `[[skills/musk-algorithm]]` v1.3.0 — 5-step (req → delete → simplify → accelerate → automate).
- RULE ZERO — skill update + gbrain timeline, no LESSON files.
- AP-21 — Hermes stays canary-only; no silent promotion.

## Specify (what we're building)

A reusable skill — `multi-model-consult` — that any agent/lane invokes when it hits an unknown that exceeds its single-model judgment. The skill spawns three models in parallel, runs an arbitration pass, returns a structured answer with confidence + dissent.

**Three primary models** (no silent promotions; benchmark-validated per ceo-hierarchy AP-25):
- **Opus 4.7** (`claude-opus-4-7[1m]`) — deep-reasoning lane; long context, careful analysis
- **GPT-5.5 via Codex** — top-tier judgment; external-operator proof; CEO/CTO architecture
- **Grok latest via Grok-API (x.com search)** — current-events; live web research; "what happened today"

**One arbitrator** — fourth pass — picks winner with rationale, or surfaces dissent unresolved:
- Default arbitrator: `deepseek-v4-flash` (cheap, fast, benchmark-winner per `[[CHEAP-POOL-BENCHMARK-2026-05-18]]`).
- Fallback: Opus when arbitrator unsure.

**When this fires (trigger conditions)**:
1. A lane (Opus, Codex, OpenClaw, Hermes) hits a question outside its training/scope: "I don't know what GStack is", "what's the latest on Telegram bot-to-bot", "is library X safe to upgrade", etc.
2. A canary fails with ambiguous cause: routine self-repair tried, didn't converge.
3. A factory worker can't decide between routes: AP-37 says route to Codex, but the question is genuinely unclear which lane fits.
4. Madi asks an open question in Telegram: the system auto-consults three models before replying so the answer is calibrated.

**What it returns** (canonical schema):

```json
{
  "consult_id": "consult_2026-05-19T15:00:00Z_<sha8>",
  "question": "string",
  "context_slug": "pages/... or empty",
  "answers": [
    {"model": "opus-4-7", "answer": "...", "confidence": 0.85, "tokens": 1234, "latency_ms": 5400, "cost_usd": 0.012},
    {"model": "codex-gpt-5.5", "answer": "...", "confidence": 0.90, "tokens": 980, "latency_ms": 8200, "cost_usd": 0.00},
    {"model": "grok-latest-with-x-search", "answer": "...", "confidence": 0.78, "tokens": 1100, "latency_ms": 12400, "cost_usd": 0.003}
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
  "skill_update_proposal": "if all 3 agreed on a new pattern, propose AP for which skill"
}
```

The arbitration is **the new skill being built**, not just consensus: it picks the answer most grounded in real evidence (file paths, live commands, citations) over confident-sounding-but-untestable.

## Clarify (open questions for Madi)

1. **Grok-API credentials.** Today's `hermes-nouscanary` shows API keys configured: Anthropic only. Grok needs separate xAI API key. Do you want me to defer Grok integration until you provide a key (Madi-credential gate), or do you have one to drop into `~/nous-agaas/.env`?
2. **x.com search depth.** Grok-via-xAI has built-in x.com search. Should the consult include "search depth": shallow (Grok's default) or deep (explicit `x_search_max_results=20`)? Trade-off: depth costs latency + dollars.
3. **Cost cap per consult.** Default cap: $0.50/consult, $20/day across all consults. Increase if needed for high-value APK/ERAP proof questions. Confirm.
4. **Concurrency.** Spawn all 3 models in parallel (faster, costlier) or sequential (cheaper, slower)? **Recommend: parallel by default**; the latency saved is worth more than $0.05/consult.
5. **When NOT to consult.** Low-risk routine work (e.g., a single Telegram message edit, a typo fix) should NOT trigger a 3-model spend. **Recommend: skill is invoked explicitly via `/consult` slash command + auto-fired on AP-12 Council triggers (lock-in risk, IR/retrieval, novel cost/latency, security, single-ablation evidence).** Confirm the auto-fire trigger list.
6. **Telegram surface.** Should consult results post back to the Telegram group, or only land in vault audits + gbrain? **Recommend: vault audit only by default; Telegram only when Madi explicitly tags `/consult` in his message.** Confirm.

## Plan (architecture)

```
┌────────────────────────────────────────────────────────────────┐
│  tools/multi_model_consult.py                                  │
│  (CLI + Python lib; both invocations supported)                │
│                                                                 │
│  consult(question, context_slug=None, models=None) -> Result   │
│    ├─ launch_opus(...)    ─┐                                   │
│    ├─ launch_codex(...)   ─┼─ asyncio.gather (parallel)        │
│    ├─ launch_grok(...)    ─┘                                   │
│    ├─ arbitrate(answers) → deepseek-v4-flash → Result          │
│    ├─ write_audit(pages/audits/CONSULT-<id>.md)                │
│    ├─ gbrain.timeline-add(<context_slug>, summary)             │
│    └─ openbrain.capture_thought(answers[winner])               │
└────────────────────────────────────────────────────────────────┘
```

### Files

- **New:** `tools/multi_model_consult.py` (~250 lines).
- **New:** `tools/multi_model_consult_adapters/` — one module per model (`opus.py`, `codex.py`, `grok.py`, `deepseek_arbitrator.py`). Each adapter exposes `async def call(question: str, context: str | None) -> Answer`.
- **New:** `tools/tests/test_multi_model_consult.py` — fixture-based tests; no live model calls in CI.
- **New:** `pages/skills/multi-model-consult/SKILL.md` — runtime doctrine, AP table, trigger conditions, cost guardrails.
- **Modify:** `pages/skills/_gbrain/RESOLVER.md` — register new skill.
- **Modify:** `~/nous-agaas/.env` — add `XAI_API_KEY` (Madi to provide).
- **Modify:** `pages/skills/karpathy-loop/SKILL.md` — AP-12 references `multi-model-consult` as the implementation of Council escalation when triggered.
- **Modify:** `pages/skills/ceo-hierarchy/SKILL.md` — AP-N references this skill as the "I don't know" auto-spawn path.

### Deletion (Musk step 2 first)

Before adding 3 new adapter modules, audit existing single-model invocation paths in `tools/`:
- `tools/run_task.py` — already calls OpenClaw workers; reuse its env+timeout patterns, do not duplicate.
- `tools/cheap_pool_benchmark.py` + `tools/cheap_pool_winner_picker.py` — fold the multi-model spawn pattern from these tools, do not write a parallel spawner from scratch.
- Hand-rolled `codex exec` invocations in `tools/satory_ai_factory_queue.py` — refactor to call `multi_model_consult` when the worker hits `ROUTE_GROK_DECISION` (per `factory_orchestration_policy.py`).

Net: 3 new files + 4 modules; should be able to delete or fold at least 2 existing one-off scripts. **Acceptance: tool LOC flat or down after ship.**

## Tasks (Spec-Kit ordered)

- [ ] **T1** — Madi answers Clarify Q1 (Grok API key) + Q2-Q6.
- [ ] **T2** — Spec-Kit `/clarify` pass: collect open Qs from Codex's lane review.
- [ ] **T3** — Author 3 adapter modules with fake-mode (no live calls) + 1 arbitrator module.
- [ ] **T4** — Author `tools/multi_model_consult.py` CLI + Python lib with cost cap enforcement.
- [ ] **T5** — Regression test suite: 6 cases (3 agree, 2-1 dissent, all-disagree, cost cap hit, missing key fallback, arbitrator unsure → falls back to Opus).
- [ ] **T6** — Skill page `pages/skills/multi-model-consult/SKILL.md` v1.0.0 (RULE ZERO 3-edit ritual).
- [ ] **T7** — Canary: invoke skill explicitly for 3 real questions over 24h, measure latency + cost + agreement rate.
- [ ] **T8** — Wire into `factory-orchestration-policy.py`: when classifier returns `ROUTE_GROK_DECISION`, auto-spawn the consult.
- [ ] **T9** — Wire into `karpathy-loop` AP-12 plan-review triggers: when AP-12 fires, the Council IS this skill.
- [ ] **T10** — Promote: load to production after 24h canary green + zero Madi escalation drift.

## Implement (execution log — append as work happens)

(empty until Madi approves spec)

## Acceptance criteria (binding, falsifiable)

1. **Three-model parallel call works** — `consult("What is GStack?")` returns 3 answers in <30s on warm cache, with `winner_model` set.
2. **Arbitrator correctness on fixture** — labeled fixture of 10 questions where ground truth is known; arbitrator picks the grounded answer in ≥8/10.
3. **Cost cap enforced** — fixture test where one model goes runaway; cap fires at $0.50, returns partial answer + cap warning.
4. **No silent failure** — if Grok API is down, consult continues with Opus + Codex + fallback arbitrator; result has `model_unavailable: ["grok"]` in metadata.
5. **MISSION self-healing rule applies** — when consult itself fails (e.g., all 3 models error), it auto-spawns a `/consult` retry with backoff; only escalates to Madi if 3 retries fail.
6. **Tool LOC flat or down** after merge: `wc -l tools/*.py` total ≤ pre-merge + 250 (the new consult module) − (deletions). If broken, Musk step 2 failed.

## Rollback path

- Unload any launchd job that auto-triggers consult.
- Comment out the AP-12 wiring; AP-12 Council escalation reverts to manual `Skill(plan-ceo-review)` etc.
- Adapters and arbitrator remain in `tools/` but unused.
- No data loss; consult audits in `pages/audits/CONSULT-*.md` are evidence trail only.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| xAI API key not yet provided | High | Blocks Grok lane | Defer Grok adapter until Madi commits key; consult runs with Opus+Codex only until then (already 2/3) |
| 3-model latency exceeds attention budget | Med | UX | Parallel calls + 30s timeout per model + return partials |
| Cost runaway on deep x.com searches | Med | Med | Cap per consult + daily cap + circuit breaker |
| Arbitrator over-weights one model | Med | High | Labeled fixture in CI; arbitrator must score ≥8/10 before promotion |
| Codex spawn slow on Air (8-12s typical) | Low | Low | Already observed; acceptable for non-realtime use |
| Hermes promotion gate confusion (Hermes stays canary; this skill does NOT route through Hermes) | Low | Low | Explicit doctrine in SKILL.md: Hermes is observer/escalation, not a model in the consult pool |

## See also

- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` — mission this skill serves
- `[[skills/ceo-hierarchy]]` v1.9.0 — worker tier routing
- `[[skills/karpathy-loop]]` v1.12.0 — AP-12 Council triggers
- `[[skills/musk-algorithm]]` v1.3.0 — 5-step doctrine
- `[[CHEAP-POOL-BENCHMARK-2026-05-18]]` — deepseek-v4-flash winner for cheap arbitration
- `[[skills/karpathy-coding-principles]]` v1.1.0 — Think Before Coding (this skill IS the Think layer for ambiguous questions)

## Timeline

- **2026-05-19 14:25 KZT** — Madi: "Finding an answer is a new skill, so you keep evolving."
- **2026-05-19 15:00 KZT** — This spec authored by Claude Opus 4.7 lane. Awaiting Madi review.
