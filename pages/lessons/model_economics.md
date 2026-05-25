---
type: reference
id: MODEL-ECONOMICS
title: "Factory Model Lineup and Costs"
tags: [reference, models, costs, factory]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# Factory Model Lineup — ACTUAL (April 6, 2026)
Source of truth: config.py + graph.py on VPS

## Active Models

| Role | Model | Provider | Cost (M tokens) | Notes |
|------|-------|----------|-----------------|-------|
| CEO | Claude Opus 4.6 | Anthropic | $15/$75 | RULE 1: Must always be Opus. Runtime assert enforced. |
| Coder | Claude Sonnet 4.6 | Anthropic | $3/$15 | Best code writer. 1M context. |
| Validator | Gemini 2.5 Pro | Google AI | ~$1.25/$10 | Called directly via genai module, not via get_llm(). |
| Researcher | Gemini 2.5 Flash | Google AI | ~$0.30/$2 | Web search + wiki context. Only on retry #2. |

## Estimated Daily Cost
- Budget cap: $30/day (BUDGET_DAY in graph.py)
- Typical: $12-18/day with 12 cycles
- CEO is the most expensive call (~$2-5 per cycle with full wiki context)

## NOT in active factory (config entries exist but unused by graph.py)
- Debugger (MiniMax M2.5) — not in the graph flow
- Data Specialist (Qwen 3.5 Plus) — not in the graph flow
- Reporter (Qwen 3.5 Plus) — not in the graph flow

## Key: config.py has entries for 7 models but graph.py only uses 4.

## See also
- [[LAW-001-evolution|LAW-001]]
- [[LAW-003-continuous-audit|LAW-003]]
- [[LAW-005-obsidian-master|LAW-005]]
- [[LAW-007-hub-and-spoke|LAW-007]]
- [[LAW-008-anti-hallucination|LAW-008]]
