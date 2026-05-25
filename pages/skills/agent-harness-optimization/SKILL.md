---
tier: 2
type: skill
name: agent-harness-optimization
id: SKILL-AGENT-HARNESS-OPTIMIZATION
version: 1.0.0
last_updated: 2026-05-05
status: active
description: "v1.0.0 — codifies Ahmad Awais (CommandCodeAI CEO) thread: open models like Kimi K2.6 and DeepSeek V4 Pro near-tie or beat Claude Opus 4.7 on coding/agentic evals when 4 specific harness fixes are applied. Closed models hide the messy stuff server-side; open models expose every harness flaw. The 4 fixes: (1) session pinning for prefix-cache hits — TTFT drops from 6-8s to <1s, (2) canonical model IDs for clean routing + invisible fallbacks across providers, (3) smart capability flags that only request what current providers support, (4) disable thinking mode on DeepSeek to fix multi-turn crashes. Practical impact: near-Opus performance at 10-50x cheaper using OpenRouter/CommandCodeAI gateway. Source: Ahmad Awais X thread + CommandCodeAI internal evals (Kimi 5/10, DeepSeek 6/10 vs Opus). Apply when LiteLLM router shows poor performance on open-model paths, when multi-turn agent loops crash, or when prefix-cache miss costs are high."
triggers:
  - LiteLLM router shows poor performance on DeepSeek / Kimi / open-model paths
  - multi-turn agent loop crashes mid-conversation
  - prefix-cache miss latency >2s on repeated similar requests
  - cost spike from over-using closed models for tasks open models could do
  - new open model added to LiteLLM config (apply checklist before routing prod traffic)
  - debug session: user reports "open model is broken" — verify harness first before blaming model
tools: [Bash, Read, Edit]
mutating: true
related: [ceo-hierarchy, factory-ops, gbrain-ops, session-coordination]
tags: [skill, harness, litellm, open-models, deepseek, kimi, openrouter, commandcodeai, performance, cost-optimization]
title: "agent-harness-optimization v1.0.0"
---

# agent-harness-optimization v1.0.0

## Purpose

Capture the four harness fixes that turn open models (DeepSeek V4 Pro, Kimi K2.6, etc.) from "looks worse than Opus" into "ties or beats Opus on coding tasks at 10-50× cheaper." The model didn't get smarter; the harness stopped sabotaging it.

Most "open models suck at tools/coding" complaints are harness bugs, not model bugs. Closed models (Anthropic/OpenAI) hide the messy parts server-side: perfect prefix caching, forgiving tool contracts, consistent provider routing. Open models expose every flaw the agent wrapper has.

## When this skill loads

- LiteLLM router config changes
- Adding a new open model (DeepSeek, Kimi, Qwen, GLM) to the routing table
- Debug: agent loop crashes mid-conversation
- Cost optimization pass on the model spend dashboard

## The 4 Fixes

### Fix 1 — Session pinning for prefix-cache hits

**Problem:** Every new request from the same agent session lands on a different upstream worker. Prefix cache cold-misses every time. TTFT (time-to-first-token) is 6-8 seconds. Multi-turn loops compound this — by turn 5 the agent looks "slow," but it's actually re-priming context every time.

**Fix:** Stable session ID stamped on every request from the same agent session. Router pins requests to the worker that has that session's prefix cached. Revival on cache miss is instant for warm caches (<1s).

**Implementation in LiteLLM:**
- Set `litellm_settings.cache.prefix.enabled: true`
- Add `metadata.session_id` to every request (use Claude Code session ID, Codex CLI session ID, factory worker job ID, etc.)
- Provider router config: `routing_strategy: "session-pinned"`

**Test:** measure TTFT on turn 2 vs turn 1 of the same session. If turn 2 isn't 5x+ faster than turn 1, pinning isn't working.

### Fix 2 — Canonical model IDs

**Problem:** Different providers use different IDs for the same model: `deepseek-v4-pro`, `deepseek-ai/deepseek-v4-pro`, `deepseek/v4-pro-instruct`. Routing logic that switches providers (e.g., on outage) breaks because the request specifies provider-A's ID and lands on provider-B which doesn't recognize it.

**Fix:** Define canonical model IDs at the LiteLLM router level (e.g., `worker-pro` → maps to whichever provider is available). Agents request the canonical ID, router resolves to current best provider, fallback to next provider on outage is invisible.

**Implementation in LiteLLM:**
- `model_list` defines canonical aliases
- Each alias has a list of `model_provider` entries with ordered fallback
- Health-checks demote bad providers transparently

**Test:** kill primary provider, confirm fallback fires within 30s without agent code changes.

### Fix 3 — Smart capability flags

**Problem:** Agent always requests full feature set (tools, vision, JSON mode, thinking, structured outputs) regardless of which provider is current. When fallback hits a provider that doesn't support, say, thinking mode, request crashes.

**Fix:** Capability negotiation layer. Agent declares intent ("I want tool use"); router asks current provider what it supports; only forwards capabilities the current provider has; degrades gracefully (e.g., disables vision if fallback lacks it, with logged downgrade event).

**Implementation:**
- LiteLLM `provider_capabilities` table per provider+model combo
- Pre-flight per request: filter `request.params` against `provider.supported_params`
- Log every capability downgrade as a structured event for visibility

**Test:** force fallback to a provider that lacks thinking mode; verify request succeeds with logged downgrade vs crashes.

### Fix 4 — Disable thinking mode on DeepSeek for multi-turn

**Problem:** DeepSeek V4 with thinking mode enabled crashes on multi-turn conversations after ~3-5 turns. The thinking-mode payload accumulates in the conversation history and exceeds context limits or trips a parser bug upstream.

**Fix:** For DeepSeek paths used in multi-turn agent loops, set `thinking.enabled: false` by default. Only enable for single-shot deep-reasoning calls.

**Implementation in LiteLLM:**
- DeepSeek model_list entries: `extra_params.thinking.enabled: false` for `worker-flash` and `worker-pro` aliases
- Separate alias `worker-pro-thinking` for explicit deep-reasoning single-shot use
- Document the boundary in the model selection skill

**Test:** run a 10-turn agent loop on DeepSeek without thinking. Should complete cleanly. Then enable thinking and reproduce the crash to confirm the fix is needed.

## When to use open models vs closed

| Use case | Best model |
|---|---|
| Multi-turn agent loops, coding, refactoring (cost matters) | DeepSeek V4 Pro (with all 4 fixes) |
| Long-horizon agent work, tool chaining | Kimi K2.6 (with all 4 fixes) |
| Cutting-edge reasoning on novel problem | Opus 4.7 (closed) |
| Customer-facing voice/style critical | Opus 4.7 or 4.6 |
| High-volume batch (summarization, extraction) | DeepSeek V4 Flash |
| Critical correctness, low latency tolerance | Opus 4.7 |

## Anti-Patterns

### AP-1 — "Open models are bad" without checking harness

User reports DeepSeek failing → conclusion is "switch to Opus." Wasted opportunity: usually it's a harness fix away from working.
**Fix:** before blaming model, run all 4 fixes checklist. Often the model was fine.

### AP-2 — Hardcoded provider model IDs in agent code

Agent code references `"openrouter/deepseek/v4-pro"` directly. Provider migration breaks every agent.
**Fix:** agents request canonical aliases from LiteLLM (`worker-pro`, `worker-flash`); router handles provider mapping.

### AP-3 — Cold-cache TTFT measured + accepted

"Yeah, our agent takes 8s to respond" treated as fact of life.
**Fix:** apply session pinning. 8s → 1s. The cost was 5 lines of config.

### AP-4 — Thinking mode default-on everywhere

Thinking enabled globally. Multi-turn loops crash; team blames the model.
**Fix:** thinking off by default for multi-turn paths; explicit opt-in alias for single-shot deep reasoning.

## Implementation order

When applying for the first time:
1. **Fix 4** (disable thinking on multi-turn paths) — easiest, highest immediate impact on stability
2. **Fix 1** (session pinning) — biggest perceived performance jump for users
3. **Fix 2** (canonical IDs) — needed before adding more providers
4. **Fix 3** (capability flags) — needed when 2+ providers per alias

## Timeline

- **2026-05-05** v1.0.0 — Codified from Ahmad Awais (CommandCodeAI CEO) X thread + CommandCodeAI internal evals (Kimi K2.6 5/10, DeepSeek V4 Pro 6/10 vs Claude Opus 4.7 on tool-heavy coding evals, same prompts/checkpoints/temp). Companion to ceo-hierarchy v1.1.0 which already prefers DeepSeek V4 Pro/Flash for worker-tier — but didn't have the harness fixes documented. This skill closes that gap.

## See also

- [[skills/ceo-hierarchy]] — multi-model routing hierarchy (consumer of this skill)
- [[skills/factory-ops]] — factory worker uses LiteLLM-routed open models
- [[skills/gbrain-ops]] — gbrain embedding pipeline uses open-model routing
- External: [Ahmad Awais X thread](https://x.com/ahmadawais) on harness fixes; CommandCodeAI gateway as reference implementation
