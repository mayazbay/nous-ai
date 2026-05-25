---
type: system
id: litellm-cost-alarm
title: "LiteLLM cost alarm"
tags: [system, litellm, cost-alarm, factory-ops, budget]
related:
  - "[[factory-ops]]"
  - "[[audit]]"
  - "[[PLAN-2026-04-30-deepseek-promo-expiry-watch]]"
---

# LiteLLM cost alarm

The LiteLLM cost alarm is the Air launchd spend-watchdog for Nous AGaaS model traffic. It runs as `com.nous.litellm-cost-alarm`.

Current implementation: `tools/cost_alarm.py` reads VPS Langfuse `/api/public/metrics/daily` over Tailscale and alerts if today's cost exceeds `$40` or `3x` the prior 7-day rolling average. Alerts are deduped by same-day reason class (`rolling`, `hard_cap`) rather than the live dollar amount, so a rising rolling-baseline breach does not send a fresh Telegram alert every interval. The historical heuristic log parser remains in `tools/litellm_cost_alarm.py` for audit trail and fallback context.

Canonical operating doctrine lives in [[factory-ops]], especially AP-26, AP-29, and AP-33. This page exists as the stable library target for plans and audits that need to reference the alarm by name without pointing at a raw tool file.
