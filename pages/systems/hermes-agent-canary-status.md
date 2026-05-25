---
type: system
id: hermes-agent-canary-status
title: "Hermes Agent Canary Status"
date: 2026-05-15
last_updated: 2026-05-22
status: canary-green-webui-honesty-overlay-promotion-blocked-24h-reset
tags: [hermes, openclaw, telegram, canary, ceo-hierarchy]
related: [hermes-agent, hermes, ceo-hierarchy, hermes-factory-watchdog-status]
---

# Hermes Agent Canary Status

## Current Decision

OpenClaw remains the production runtime. Hermes Agent is an isolated canary only.

No production cutover is allowed until Hermes passes the same Telegram, LiteLLM, Todoist, Notion, Obsidian/wiki, gbrain, OpenBrain, cost, rollback, and factory-health gates for 24 hours.

## Promotion Attempt 2026-05-22

Madi approved continuing the Hermes promotion workstream. The live promotion runner reached 9/10 GREEN, but did not promote because `factory_green_24h` remained RED.

The blocker is strict, not cosmetic: `CONTROL-PLANE-SYNC-2026-05-22-033439` recorded `factory_no_drift_probe` RED on `air_sync_lag` while the Air worktree had 7 dirty generated paths. Runtime health was green and later probes are green, but the 24h promotion gate requires zero-red no-drift continuity.

Reset receipt: [[HERMES-24H-GATE-RESET-2026-05-22]].

Earliest next strict 24h gate, if no further red appears: `2026-05-23 03:45 KZT`.

## Live Canary Shape

| Component | Current state |
|---|---|
| Production Telegram runtime | OpenClaw via Air `telegram_poll.py` |
| Production `/ask` | OpenClaw `grok-ceo` |
| Production high-judgment | `/codex` GPT-5.5, explicit or bounded auto-escalation only |
| Hermes profile | `nouscanary` |
| Hermes invocation | `hermes-nouscanary` |
| Hermes model | `gpt-5.5` via OpenAI Codex |
| Hermes honesty overlay | Canonical vault copy: [[hermes-nouscanary-soul]]; installed in Air `~/.hermes/profiles/nouscanary/SOUL.md`; live readback required before claiming active behavior |
| Hermes Telegram gateway | Not configured |
| Hermes gateway service | Not loaded |
| Hermes scheduled jobs | 0 |
| Hermes WebUI canary | `com.nous.hermes-webui-canary` |
| Hermes WebUI URL | Tailscale URL blocked until Air logs back into Tailscale |
| Hermes WebUI LAN fallback | `http://192.168.1.197:8787` on same Wi-Fi |
| Hermes WebUI auth | Password enabled via Air-only `~/nous-agaas/secrets/hermes-webui.env` |
| Gemini review | Not claimed; Gemini is not in the current production LiteLLM chat route list |

## Evidence 2026-05-15 09:30 KZT

Commands run on Air:

```bash
hermes profile show nouscanary
hermes-nouscanary status
command -v hermes-nouscanary
curl -fsS http://127.0.0.1:18789/health
curl -fsS http://127.0.0.1:4000/health/readiness
```

Key output:

```text
Profile: nouscanary
Model:   gpt-5.5 (openai-codex)
Gateway: stopped
.env:    exists

Model:        gpt-5.5
Provider:     OpenAI Codex
Telegram      ✗ not configured
Status:       ✗ not loaded

/Users/madia/.local/bin/hermes-nouscanary
Hermes Agent v0.8.0 (2026.4.8)
Update available: 199 commits behind

OpenClaw health: {"ok":true,"status":"live"}
LiteLLM readiness: {"status":"healthy", ... "cache":"local", "litellm_version":"1.83.7"}
```

Canary smoke already ran once:

```text
hermes-nouscanary chat -Q --max-turns 1 -q "Reply exactly HERMES_CANARY_PROFILE_OK and nothing else."
stdout: HERMES_CANARY_PROFILE_OK
session_id: 20260515_092751_75f3a3
```

## Final Gate 2026-05-15 09:37 KZT

Command run on Air at wiki HEAD `1b400252`:

```bash
cd ~/nous-agaas/wiki
python3 tools/hermes_canary_gate.py --json --factory-probe --smoke
```

Result:

```text
overall: GREEN
reds: 0
openclaw_production_health: GREEN
litellm_production_health: GREEN
telegram_poller_production_loaded: GREEN
hermes_canary_alias: GREEN
hermes_canary_profile_isolated: GREEN
hermes_canary_route_config: GREEN
hermes_gateway_not_production: GREEN
factory_no_drift_probe: GREEN (overall=GREEN reds=0)
hermes_canary_smoke: GREEN
session_id: 20260515_093730_6c9fec
```

## Gate

Run this from Air before any claim that Hermes is safe:

```bash
cd ~/nous-agaas/wiki
python3 tools/hermes_canary_gate.py --json --factory-probe
```

Run this before any claim that the iPhone/TestFlight WebUI path is live:

```bash
cd ~/nous-agaas/wiki
python3 tools/hermes_canary_gate.py --json --webui-probe
tools/hermes_webui_canary.sh health
tools/hermes_webui_canary.sh phone-url
tools/hermes_webui_canary.sh lan-url
```

Run this only when intentionally spending one explicit canary GPT-5.5/Codex call:

```bash
cd ~/nous-agaas/wiki
python3 tools/hermes_canary_gate.py --json --factory-probe --smoke
```

## Honesty Overlay 2026-05-21

Madi's Ruben Hassid-inspired "brutally honest AI" instruction set is now a canary requirement for Hermes, not a chat-only preference.

The live Air `nouscanary` `SOUL.md` must include:

- uncertainty labels for unknown or incomplete facts
- no fabricated sources, URLs, studies, reports, legal cases, quotes, or statistics
- number/ranking/date freshness warnings when not verified
- recent-event verification for AI models, product features, laws, leadership, prices, and routing claims
- people/quote attribution caution
- an agreement gate before any simple "yes"
- runtime-proof discipline for factory-critical claims

Canonical profile: [[hermes-nouscanary-soul]].

Installation audit: [[HERMES-BRUTAL-HONESTY-INSTRUCTIONS-2026-05-21]].

Readback command:

```bash
ssh air 'grep -n "Agreement gate\|Recent events\|Never invent sources" ~/.hermes/profiles/nouscanary/SOUL.md'
```

## Cutover Bar

Hermes can receive more authority only after a 24-hour receipt proves:

1. Telegram isolation: Hermes never polls `@nousAGaaSbot`; Air `telegram_poll.py` remains the only poller.
2. LiteLLM non-interference: production routes are unchanged and green.
3. Todoist proof: canary task flow writes proof in a scoped test task only.
4. Notion proof: canary source lookup or write is explicitly logged.
5. Obsidian/wiki proof: canary creates or updates a scoped artifact and commits only that path.
6. gbrain proof: canary writes a timeline entry and retrieval works.
7. OpenBrain proof: canary capture/projection round-trips.
8. Cost proof: GPT-5.5 canary spend is logged and bounded.
9. Rollback proof: one command disables the canary without touching production OpenClaw.
10. Factory proof: `factory_no_drift_probe` stays GREEN with zero red checks.

## Residuals

- Hermes Agent is v0.8.0 and 199 commits behind. Do not update it inside production runtime; update only in the canary after a rollback snapshot.
- Hermes profile routing must use the generated alias `hermes-nouscanary`; `HERMES_PROFILE=...` was not reliable in this rollout.
- No Todoist/Notion/gbrain/OpenBrain production authority has been granted to Hermes yet.
- Hermes WebUI Tailscale URL is blocked if Air `tailscale status` is logged out. In that state, use the explicit LAN fallback only while the iPhone is on the same Wi-Fi. Public Cloudflare/domain exposure is not approved.
- The honesty overlay is profile doctrine. It must not be used as evidence of production promotion; promotion still requires the 10-proof cutover bar above.
