---
type: lesson
id: LESSON-101
title: "OpenClaw session accumulates indefinitely — burns tokens until compaction or balance exhaustion"
tags: [openclaw, zai, litellm, tokens, session, cost, infrastructure]
date: 2026-04-15
source_count: 0
status: absorbed
absorbed_at: 2026-04-16
last_updated: 2026-04-15
related: [LESSON-099, LESSON-100, skills/audit/SKILL, skills/infrastructure/SKILL]
integrated_into: infrastructure
absorbed_into: audit
---

# LESSON-101 — OpenClaw Session Accumulation Burns ZAI Tokens

## Root Cause

OpenClaw maintains a **persistent session file** per agent (`/home/node/.openclaw/agents/nous/sessions/<uuid>.jsonl`). Every task call appends to this session. The session grows indefinitely across ALL tasks until:
- OpenClaw triggers auto-compaction (at ~114K token budget), OR
- The model's context window is exceeded

By session 22 (2 days of heavy development), the session file had grown to **920KB / 127K tokens**. At GLM-5.1 pricing ($1.40/1M input), each call cost **$0.18 in input alone** — before any output, before any context injection.

Combined with `context_injector` sending 141K chars (~35K tokens) per call in sessions 7-12 (before the 50K cap), the accumulated cost exhausted the ZAI account balance over 2 days.

## Evidence

```
/home/node/.openclaw/agents/nous/sessions/00518026-8f21-4e40-ad2f-eb0a96e1c61d.jsonl
  Size: 920,184 bytes
  
Docker log 2026-04-15T12:10:
  [context-overflow-precheck] estimatedPromptTokens=127301
  context overflow detected (attempt 1/3); attempting auto-compaction
  auto-compaction succeeded for litellm/glm-5.1 (2026-04-15T12:13)
```

## What Happened

1. Sessions 7-12: `context_injector` sent 35K tokens per call (no cap yet)
2. OpenClaw session grew with each call's history: user prompt + tool outputs + agent responses
3. By session 22: session = 127K tokens, $0.18 per call input
4. ZAI balance exhausted (error 1113: "Insufficient balance or no resource package")
5. Auto-compaction fired but too late — balance already at zero

## ZAI Error 1113 Clarification

Error 1113 = **"Insufficient balance OR no resource package"**

- **Account balance**: Wallet credits topped up via payment. Works with international cards (on OpenRouter) or Chinese payment (on bigmodel.cn directly).
- **Resource package (资源包)**: Token bundle specific to a model tier. China-payment only on bigmodel.cn.

**For international users: use OpenRouter (`openrouter.ai`) to access GLM-5.1** — same model, cheaper pricing ($0.95/M input vs $1.40/M direct), international Visa/Mastercard.

## Fixes Applied

### 1. LiteLLM fallback (LESSON-099, already done)

`fallbacks: [{glm-5.1: [glm-4.5-flash]}]` in `~/nous-agaas/litellm/config.yaml` — when GLM-5.1 fails, factory continues on free tier.

### 2. Context injector cap (session 13, already done)

`MAX_CONTEXT_CHARS=50K` in `context_injector.py` — limits injected wiki context per call.

### 3. Daily session rotation (new — session 23)

Cron on Air clears the OpenClaw session file daily at 3:45 AM Almaty. Agent loses in-session conversation history but retains all project knowledge via wiki + gbrain. New session starts at near-zero tokens.

```bash
# /etc/cron or launchd: runs daily 3:45 AM
docker exec openclaw sh -c 'ls /home/node/.openclaw/agents/nous/sessions/*.jsonl 2>/dev/null | while read f; do echo "[] # rotated $(date)" > "$f"; done' 2>/dev/null || true
```

### 4. Switch to OpenRouter for GLM-5.1 (new — session 23)

```yaml
# litellm/config.yaml — replace ZAI direct with OpenRouter
- model_name: "glm-5.1"
  litellm_params:
    model: "openrouter/z-ai/glm-5.1"
    api_key: "os.environ/OPENROUTER_API_KEY"
    max_tokens: 8192
    timeout: 120
```

## Prevention Rules

1. **Always monitor OpenClaw session file size** — `/audit openclaw` now checks this. >500KB = warning. >1MB = action required.
2. **Rotate sessions daily** — start each day at zero accumulated context. Session memory is not needed; wiki + gbrain handle persistent knowledge.
3. **Watch total daily token count** — `run_task.log` has `input_tokens` + `output_tokens` per call. Sum them weekly. At current GLM-5.1 rates, $20 = ~20M tokens input.
4. **Use OpenRouter for GLM-5.1 internationally** — better pricing, international payment, no resource package complications.

## See also

- [[LESSON-099-zai-balance-exhausted-litellm-fallback]] — fallback configuration
- [[LESSON-100-write-back-pull-rebase-before-push]] — concurrent git writers
- [[audit]] v1.1.0 — AP-1 through AP-4 cover these failure modes
- [[infrastructure]] — AP-9 covers session rotation
