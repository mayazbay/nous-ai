---
type: lesson
id: LESSON-104
title: "LiteLLM RouterRateLimitError when ALL deployments simultaneously cooled down"
tags: [lesson, litellm, router, fallback, openrouter, zai, infrastructure]
date: 2026-04-15
status: absorbed
absorbed_into: infrastructure
absorbed_at: 2026-04-16
last_updated: 2026-04-15
related:
  - pages/systems/skills/infrastructure/SKILL.md
  - pages/progress/HANDOFF-2026-04-15-session24-input
---

# LESSON-104 — LiteLLM RouterRateLimitError: all deployments cooled down simultaneously

## What happened

LiteLLM was crashing with `RouterRateLimitError: No models available` during session 24 health check. The error caused the litellm process to restart (launchd `com.nous.litellm` on Air). Symptom: `/ask` commands failing intermittently; `curl http://localhost:4000/health/liveliness` returning connection refused for ~30-60s after each crash.

## Root cause

LiteLLM's router has a `cooldown_time` setting. When a model deployment fails (rate limit, network error, or any 5xx), the router puts that deployment on "cooldown" — it won't be retried for `cooldown_time` seconds.

The fallback chain was:
```yaml
fallbacks: [{"glm-5.1": ["glm-4.5-flash"]}]
cooldown_time: 60
```

Both providers (OpenRouter/glm-5.1 AND ZAI/glm-4.5-flash) hit errors at approximately the same time. Both were cooled down. The router raised `RouterRateLimitError` because there was no surviving deployment in the fallback chain to try. With `cooldown_time=60`, this dead window lasted up to 60 seconds.

The ZAI balance was also near-zero (depleted 2026-04-15, fixed by switching GLM-5.1 to OpenRouter). But even with both providers healthy, simultaneous cooldowns can happen during a traffic spike or a brief provider outage.

## Fix

Extended the fallback chain to include Anthropic Claude Sonnet as the ultimate fallback. Anthropic API key is always valid, never rate-limited to zero in production.

```yaml
router_settings:
  cooldown_time: 30  # reduced from 60s — faster recovery after provider hiccups
  # Chain: glm-5.1 (OR) → glm-4.5-flash (ZAI) → sonnet (Anthropic — never fails)
  # AP: if both ZAI and OR are down simultaneously, sonnet catches it (LESSON-104)
  fallbacks: [{"glm-5.1": ["glm-4.5-flash", "sonnet"]}, {"glm-4.5-flash": ["sonnet"]}]
```

Two changes:
1. **Added `sonnet` as ultimate fallback** — Anthropic claude-sonnet-4-6 (`claude-sonnet-4-6`). It's more expensive but never returns RouterRateLimitError.
2. **Reduced `cooldown_time` from 60→30s** — shorter dead window before a cooled deployment is retried.

After change: `curl -s http://localhost:4000/health/liveliness` → `"I'm alive!"`  
Restarted with: `launchctl kickstart -k gui/$(id -u madia)/com.nous.litellm`

## What everyone learns

1. **A fallback chain without a guaranteed-available tail can still fail to completion.** Always end your fallback chain with a "never fails" provider. Anthropic Claude is that provider for us — ANTHROPIC_API_KEY is always funded.
2. **`RouterRateLimitError` ≠ rate limit on a single provider.** It means ALL deployments in the model's routing pool are cooled down simultaneously. Check router_settings, not just provider status.
3. **`cooldown_time` creates a blind window.** 60s is too long — during that window every request fails silently. 30s is better; for critical paths consider 15s.
4. **Add glm-4.5-flash explicitly as a fallback for `glm-5.1`** — it's free-tier ZAI, available even when the balance runs out on the paid tier.

## Verification after fix

```bash
# On Air — verify LiteLLM is alive
curl -s http://localhost:4000/health/liveliness
# → "I'm alive!"

# Check fallback chain is configured
grep -A 5 "fallbacks" ~/nous-agaas/litellm/config.yaml
# Should show: sonnet as third in the chain

# Test a real request flows through
curl -s -X POST http://localhost:4000/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-5.1","messages":[{"role":"user","content":"Reply: OK"}]}'
```

## See also

- [[infrastructure/SKILL.md]] — AP-11 documents this rule
- [[LESSON-099-zai-balance-exhausted-litellm-fallback]] — related: ZAI balance depletion
- [[LESSON-101-openclaw-session-accumulation-token-burn]] — related: session size causing cost spikes
