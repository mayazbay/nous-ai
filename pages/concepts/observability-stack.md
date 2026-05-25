---
type: concept
id: observability-stack
title: "Observability Stack"
tags: [concept, observability, langsmith, langfuse, telemetry]
date: 2026-05-12
---

# Observability Stack

## Current contract

The canonical operational truth remains local and replayable:

1. `~/nous-agaas/logs/ask-hierarchy.jsonl` — per-tier `/ask` cost and route telemetry.
2. `~/nous-agaas/logs/run_task.log` — one JSON line per factory worker execution.
3. `~/nous-agaas/logs/goal-runner.log` — durable Goal Mode cycles.
4. `pages/task-results/*.md` and `pages/projects/GOAL-*.md` — Obsidian-readable evidence.
5. gbrain sync/embed — retrieval layer over the evidence.

LangSmith is now the dashboard/trace mirror for the Telegram/OpenClaw control plane, not the source of truth. If LangSmith is down, missing credentials, or the SDK is not installed, the system still writes local JSONL and continues.

## LangSmith project

- Project: `nous-agaas-control-plane`
- Workspace: `ddcd0e90-d971-48eb-bdb1-185fce6491c4`
- Runtime module: `tools/langsmith_observer.py`
- Local fallback log: `~/nous-agaas/logs/langsmith-observer.jsonl`

The old root-level LangGraph scaffold used `LANGCHAIN_PROJECT=satory-vko-agents`. That project is legacy and must not be silently reused for the production control plane.

## Instrumented paths

| Path | Event name | Notes |
|---|---|---|
| `tools/run_task.py` | `nous.run_task` | Records selected model, executed model, tokens, source, status, and correlation id without raw secret leakage. |
| `tools/command_center.py` | `nous.telegram.command` | Records `/ask`, `/ask-direct`, `/code`, `/codex`, `/goal`, and `/goal-list` outcomes. |
| `tools/goal_runner.py` | `nous.goal.cycle`, `nous.goal.worker` | Records cycle start/finish and one event per active goal worker. |

## Environment

Preferred variables:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<redacted>
LANGSMITH_WORKSPACE_ID=ddcd0e90-d971-48eb-bdb1-185fce6491c4
NOUS_LANGSMITH_PROJECT=nous-agaas-control-plane
```

Legacy compatibility:

- `LANGCHAIN_TRACING_V2=true` is accepted as tracing-enabled.
- `LANGCHAIN_API_KEY` is accepted as the API key.
- `LANGCHAIN_PROJECT=satory-vko-agents` is intentionally ignored unless `LANGSMITH_PROJECT` or `NOUS_LANGSMITH_PROJECT` explicitly sets a project.

## Verification

```bash
python3 tools/langsmith_observer.py --config
python3 tools/langsmith_observer.py --smoke
tail -1 ~/nous-agaas/logs/langsmith-observer.jsonl | jq .
```

Expected behavior:

- If SDK/key are present, `--smoke` creates or updates the LangSmith project and writes a smoke trace.
- If SDK/key are missing, `--config` and local JSONL still work, and Telegram/OpenClaw continue.

## Design rule

Observability may decorate the factory; it may not gate the factory. Never put a synchronous external dashboard dependency on Telegram polling, Goal Mode, or OpenClaw dispatch.
