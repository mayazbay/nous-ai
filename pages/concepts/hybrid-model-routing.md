---
title: "Hybrid Model Routing (90/10 Rule)"
date: 2026-04-12
type: concept
status: decided
related:
  - "[[nous-ai]]"
  - "[[glm-5-1]]"
  - "[[openclaw]]"
  - "[[skills-not-agents]]"
  - "[[LESSON-079-one-agent-not-sixteen]]"
---

# Hybrid Model Routing — The 90/10 Rule

## Principle

90% of agent work (routine coding, CRUD, documentation, monitoring) runs on open-source models at 7.5x lower cost. 10% (architecture decisions, complex debugging, strategic planning) escalates to frontier models. Intelligence compounds in the wiki, not in the model.

## Why This Works

1. **GLM-5.1** (Z.ai, April 2026) scores 58.4 SWE-Bench Pro — higher than Opus 4.6 on coding benchmarks
2. **Cost:** GLM-5.1 at $0.50/$2.00 per 1M tokens vs Sonnet at $3/$15. Same task, 7.5x cheaper.
3. **MIT license** — no usage restrictions, can run locally on M2 Air for $0
4. **Frontier models** excel at judgment, nuance, architecture — tasks that are 10% of volume but 90% of impact
5. **Model-agnostic harness** (OpenClaw) means swapping models is a config change, not a rewrite

## Routing Table

| Task Type | Model | Cost/1M tokens | Escalation Trigger |
|-----------|-------|----------------|--------------------|
| Routine coding (endpoints, components) | GLM-5.1 | $0.50/$2.00 | 2 failures → Sonnet |
| Russian business writing | Qwen 3 | $0.60/$2.40 | Quality check fails → Sonnet |
| Complex debugging | Sonnet 4.6 | $3/$15 | 2 failures → Opus |
| Architecture decisions | Opus 4.6 | $15/$75 | Human review always |
| Massive context review | Gemini 2.5 Pro | $1.25/$10 | N/A (context specialist) |

## Escalation Rules

1. **First attempt:** Always open-source (GLM-5.1 or Qwen 3)
2. **Second attempt (same task):** Sonnet 4.6
3. **Third attempt:** Opus 4.6 + human review
4. **Never:** Skip straight to Opus. The cheap model might surprise you.

## Cost Projection

| Scenario | Daily Cost | Monthly |
|----------|-----------|---------|
| 100% Sonnet (old model) | $15 | $450 |
| Hybrid 90/10 | $3-8 | $90-240 |
| 100% open-source | $1-3 | $30-90 |

## Implementation

OpenClaw's SKILL.md system handles routing via model field per skill. GBrain stores which model performed best per task type (compounding optimization).

## Source

Observed pattern from OpenClaw/Hermes community (April 2026). Garry Tan runs GBrain with OpenClaw, community members report 90%+ open-source usage for routine tasks. GLM-5.1 data from Z.ai (z.ai/subscribe), SWE-Bench Pro scores from VentureBeat.
