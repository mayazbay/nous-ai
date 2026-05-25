---
type: system
id: telegram-openclaw-langgraph-orchestration
title: "Telegram OpenClaw LangGraph Orchestration"
status: active
date: 2026-05-15
tags: [telegram, openclaw, langgraph, codex, grok, todoist, hermes]
---

# Telegram OpenClaw LangGraph Orchestration

## Contract

Telegram is Madi's second-brain surface. OpenClaw remains the production runtime on Air. LangGraph is the routing spine. Hermes stays an isolated canary until it passes the 24h gate.

## Route Table

| Input class | First action | Execution path |
|---|---|---|
| OpenClaw identity question | `command_center.py` local fast-path | no model call |
| Exact shell verification | Codex GPT-5.5 | `/codex` on Air |
| Bounded execution | Codex GPT-5.5 subscription | spend-gated `/ask` auto-route |
| Decision / strategy | Grok first pass | OpenClaw `grok-ceo` |
| Long work | Goal page + Todoist task | goal-cycle workers |
| Todoist `AI:` comment | policy-routed OpenClaw slice | explicit `--model` |

## Worker Pipeline

Long-work tasks use:

```text
grok-reasoning -> deepseek-v4-flash -> deepseek-v4-pro -> kimi-k2.6 -> glm-5.1 -> codex:gpt-5.5-subscription
```

`deepseek-v4-flash` is the cheap/bulk worker. `deepseek-v4-pro` is guarded escalation. `kimi-k2.6` and `glm-5.1` are fallback/comparison Chinese/open-source/open-weight lanes already present in the live LiteLLM config. Codex/GPT-5.5 remains the high-judgment/explicit execution lane, not the hourly Todoist default.

## Implementation

- `tools/factory_orchestration_policy.py` — pure policy source.
- `tools/langgraph_factory_orchestrator.py` — LangGraph `StateGraph` wrapper; reports `langgraph_available`.
- `tools/command_center.py` — Telegram `/ask` integration.
- `tools/human_owner_reminder.py` — Todoist `AI:` comment integration.
- `tools/ops_task_spine.py` — default model pipeline for new operational tasks.

## Verification Commands

```bash
python3 tools/langgraph_factory_orchestrator.py --text "Fix Todoist orchestration and verify it." --json
python3 -m pytest tools/tests/test_factory_orchestration_policy.py tools/tests/test_langgraph_factory_orchestrator.py tools/tests/test_ops_task_spine.py tools/tests/test_human_owner_reminder.py tools/test_operator_boundaries.py -q
```

## Guardrails

- No second Telegram poller.
- No Hermes production gateway.
- No blanket GPT-5.5 default for routine traffic.
- No hidden Todoist comment-sweep Codex spend.
- No fake-green LangGraph claim: `langgraph_available` must be true on Air.

