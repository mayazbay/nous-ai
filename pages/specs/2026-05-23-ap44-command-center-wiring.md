---
type: spec
id: SPEC-2026-05-23-ap44-command-center-wiring
title: "AP-44 wiring: subscription-rotation in command_center.py (Codex-owned)"
tags: [spec, ap-44, command-center, subscription-rotation, ceo-hierarchy, codex-owned, moonlit-pnueli]
date: 2026-05-23
source_count: 3
status: ready-for-codex
last_updated: 2026-05-23
related:
  - "[[ceo-hierarchy]]"
  - "[[SPEC-2026-05-23-moonlit-pnueli-execution]]"
---

# AP-44 wiring: subscription-rotation in command_center.py

> **Status:** READY for Codex. Owner: Codex (touches PROD `tools/command_center.py` on Air launchd `com.nous.telegram-poll`). Madi's Stage 4 directive codified in `ceo-hierarchy` v1.11.0 AP-44; rotation chain implementation shipped in `tools/subscription_rotation.py`. This spec wires it into the actual runtime.

## What's done

- `tools/subscription_rotation.py` ships with `rotate_codex_to_fallback(query, ...)` returning `{tier, model, billing_surface, answer|error, cost_usd, latency_ms, chain_trace}`.
- Probe mode + CLI for manual testing.
- 3 tiers: `claude-opus-subscription` (Anthropic Console $200/mo) → `openai-gpt-api` (pay-as-you-go, NOUS_PAID_API_* gated).
- Worker tier (DeepSeek V4 Flash via OpenClaw) is untouched.

## What's NOT done (this spec)

Wiring the rotation into `tools/command_center.py` so it fires from the `_codex_daily_budget_ok` blocked-paths. Currently those paths fall through to **grok-ceo** (AP-41 fallback). AP-44 says they should try **Claude → OpenAI** first, then grok-ceo as floor.

## Target sites in command_center.py

Identified Codex-blocked branches that today fall to grok-ceo:

| Line ~ | Path | Current behavior |
|---|---|---|
| 2636 | `_requires_codex_verification_route(query)` → checks `_codex_daily_budget_ok()` → if blocked, grok-ceo | falls to grok-ceo |
| 2766 | `/ask` auto-escalation → `_codex_daily_budget_ok()` → if blocked, grok-ceo | falls to grok-ceo |
| 2872 | mandatory-codex dispatcher → if blocked, grok-ceo with Russian/EN notice | falls to grok-ceo |

All three need to chain through `rotate_codex_to_fallback()` BEFORE grok-ceo.

## Implementation pattern (Codex starting point)

```python
# top of command_center.py with the other imports
try:
    from subscription_rotation import rotate_codex_to_fallback  # AP-44
except ImportError:
    rotate_codex_to_fallback = None

# new feature flag (default: False so prod behavior unchanged until explicitly flipped)
NOUS_AP44_ROTATION_ENABLED = os.environ.get("NOUS_AP44_ROTATION_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}

def _codex_blocked_fallback(query: str, chat_id: int, msg_id: int, today_spend: float) -> tuple[bool, dict]:
    """AP-44 rotation: try Claude subscription → OpenAI API → return False to let caller use grok-ceo.

    Returns (handled, telemetry). When handled=True, the caller posts the rotation
    result. When handled=False, the existing grok-ceo path runs.
    """
    if not NOUS_AP44_ROTATION_ENABLED or rotate_codex_to_fallback is None:
        return (False, {"reason": "ap44_flag_off_or_module_missing"})

    # Optional: pass through NOUS_PAID_API_REASON to scope the OpenAI fallback
    os.environ.setdefault("NOUS_PAID_API_REASON",
        f"ap44 rotation; codex blocked; chat={chat_id} msg={msg_id} today_spend=${today_spend:.2f}")

    result = rotate_codex_to_fallback(query, skip_openai=False)
    if not result.get("ok"):
        return (False, {"reason": "ap44_rotation_failed", "chain_trace": result.get("chain_trace", [])})

    # Successful rotation; send the answer
    answer = result["answer"]
    tier = result["tier"]
    cost_note = f"\n\n_via {tier}, ${result.get('cost_usd', 0):.4f}_"
    send_text(chat_id, answer + cost_note, reply_to=msg_id)
    _log_to_ask_hierarchy_jsonl({
        "ts": now_utc_iso(),
        "model": result["model"],
        "tier": tier,
        "billing_surface": result["billing_surface"],
        "cost_est": result["cost_usd"],
        "chat_id": chat_id,
        "msg_id": msg_id,
        "rotation_source": "ap44",
    })
    return (True, {"reason": "ap44_handled", "tier": tier})

# Then at each of the 3 sites (lines 2636, 2766, 2872), BEFORE falling to grok-ceo:
handled, telemetry = _codex_blocked_fallback(query, chat_id, msg_id, today_spend)
if handled:
    return  # rotation succeeded; don't continue to grok-ceo
# else: existing grok-ceo fallback runs as today
```

## Activation steps (when Codex implements + Madi green-lights)

1. Codex implements the helper + 3 call-site additions above.
2. Codex adds unit tests (mock `rotate_codex_to_fallback` to return synthetic Claude/OpenAI dicts, verify call-site picks up handled=True).
3. Madi approves a smoke test: `ssh air "NOUS_AP44_ROTATION_ENABLED=1 NOUS_PAID_API_ALLOWED=1 NOUS_PAID_API_CAP_USD=1.00 NOUS_PAID_API_REASON='ap44 smoke' python3 -c 'from tools.subscription_rotation import rotate_codex_to_fallback; print(rotate_codex_to_fallback(\"two-sentence ack of AP-44 wiring smoke\"))"`
4. After smoke green, flip `NOUS_AP44_ROTATION_ENABLED=1` in the `com.nous.telegram-poll` launchd env block.
5. Force Codex quota exhaustion for 1 cycle (or wait for natural cap) to verify Claude actually picks up.
6. Document the actual cutover in a `pages/audits/RECEIPT-ap44-runtime-cutover-*.md`.

## Rollback

Single env var: `NOUS_AP44_ROTATION_ENABLED=0` (or unset). The flag-off branch returns `(False, ...)` which preserves the existing grok-ceo fallback exactly.

## Exit gate

- `NOUS_AP44_ROTATION_ENABLED=1` in com.nous.telegram-poll launchd env
- First successful Claude-subscription Codex-blocked rotation logged in ask-hierarchy.jsonl
- First successful OpenAI-API last-resort rotation logged (forced via Claude quota exhaustion test, or natural)
- AP-44 receipt audit doc landed with timestamps + tier transitions

## Open questions (for Codex / Madi)

1. **Per-tier spend caps in command_center.py:** subscription_rotation.py uses NOUS_PAID_API_CAP_USD as the OpenAI cap. command_center.py may want its own daily Claude/OpenAI caps separate from Codex's CODEX_DAILY_CAP_*. Recommendation: add `CLAUDE_DAILY_CAP_USD` and `OPENAI_DAILY_CAP_USD` env vars with same JSONL-tally logic as `_codex_daily_budget_ok`.
2. **gbrain timeline entries for tier transitions:** every Claude → OpenAI step is a meaningful cost event. Worth a structured row in ask-hierarchy.jsonl with `transition=true` marker for retrospective analysis.
3. **User-facing rotation note:** should the Telegram reply include "_via Claude subscription_" footer? Madi may want it for transparency, OR may find it noisy. Default in spec = include; flag to suppress = `NOUS_AP44_HIDE_TIER_FOOTER=1`.

## Timeline

- **2026-05-23** | Spec authored by Opus during Stage 6 of moonlit-pnueli execution. Standalone rotation module (`tools/subscription_rotation.py`) shipped same commit. Wiring deferred to Codex because `command_center.py` is 130KB PROD code on Air `com.nous.telegram-poll` runtime; surgical change-mgmt is Codex's specialty. Feature-flag default OFF preserves current behavior.
