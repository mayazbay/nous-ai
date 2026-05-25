---
type: spec
id: SPEC-2026-05-20-ask-tier-toggle-design
title: "/ask --tier ceo|cheap toggle — Telegram tier override for iPad-only mode"
date: 2026-05-20
status: implemented-local-tests
owner: codex
priority: p1-ipad-only-day-4
tags: [spec-kit, telegram, /ask, tier, ceo-hierarchy, command-center, ipad-only, day-4]
related:
  - [[HANDSHAKE-2026-05-20-ipad-only-presidential-7-day-plan-0820]]
  - [[skills/ceo-hierarchy]]
  - [[2026-05-19-multi-model-consult-skill-design]]
  - [[2026-05-20-telegram-consult-command-design]]
---

# /ask --tier toggle spec

Day 4 of the 7-day iPad-only ladder. Codex lane impl (`tools/command_center.py`). Opus drop-in spec.

## Constitution

Madi 2026-05-19 ~18:20 KZT: "CEO tier (judgment, external-facing): Opus + Codex gpt-5.5 + Grok. Cheap tier (routine, internal): DeepSeek V4 Flash + Tier-0 MLX local. Routing: AP-44 + AP-45 already route Satory operator messages through the right tier. Extension needed: explicit `/ask --tier ceo` vs `/ask --tier cheap` toggle on Telegram so Madi can override."

Today's default routing per `skills/ceo-hierarchy` v1.10.2:
- `/ask` → grok-ceo Tier-1 → OpenClaw worker chain (cheap-pool: local-mlx-coder → deepseek-v4-flash → grok-reasoning)
- `/codex` → explicit GPT-5.5 (CEO tier)
- `/code` → Claude Code Sonnet 4.6 (mid-tier)

**Gap**: no way to escalate a single `/ask` to full CEO tier from iPad without remembering to type `/codex`. And no way to force cheap-only when Madi wants minimum-cost answer to a routine question.

**2026-05-20 subscription-first amendment:** CEO tier must not mean automatic Opus/xAI API spend. Codex/GPT-5.5 subscription is the first brain. Grok is treated as `xai_api` unless a subscription-backed route is separately proven. Opus API is disabled by default unless explicitly approved per run. Every paid model path must record `billing_surface` and fail closed unless a cap and reason are visible.

## Specify

Two new optional flags on the existing `/ask` command:

```
/ask --tier ceo <question>     → Madi-DM only; routes Codex GPT-5.5 subscription-first. Paid council disabled by default.
/ask --tier cheap <question>   → routes to Tier-0 MLX local-mlx-coder first, else deepseek-v4-flash. Skips paid council entirely. Cost target ≤ $0.001.
/ask <question>                → unchanged: current grok-ceo Tier-1 → OpenClaw worker chain (no behavior change).
```

The flag is positional-aware. Anywhere before the question text:
```
/ask --tier ceo "the question"
/ask --tier cheap "the question"
```

## Clarify (Madi-decision items)

1. **Default behavior unchanged?** Confirm `/ask <question>` (no flag) = current AP-44/45 routing. Recommend **yes** — non-breaking change.
2. **Cost-cap on --tier ceo**: old `$0.05` multi-model default is superseded. Codex subscription is first; paid Grok/Opus council requires explicit per-run paid approval, ledger, cap, and reason.
3. **Allowlist**: `--tier ceo` is **Madi DM only** initially (chat_id=110793056); Satory group stays AP-45 routing.
4. **Fallback**: if `--tier ceo` fails, it does not silently downgrade to cheap-tier. It returns the Codex subscription/auth/quota failure visibly.

## Musk delete/reduce

What this **deletes**:
- The Madi-side cognitive load of "should I type /ask or /codex for this?" — replaced with `--tier ceo`
- The need to manually pick cheap-tier for routine questions — replaced with `--tier cheap`

What this **adds**:
- 2 CLI flag parse cases in command_center
- 2 routing branches in the `/ask` dispatch
- 1 line in `/help` reply

**Net**: −2 cognitive choices on Madi's side, +~30 LOC in command_center. Acceptable.

## Plan

### Hook location
`tools/command_center.py` — inside the existing `/ask` handler. Add a flag-parse step BEFORE the question text is captured.

### ~40-line patch shape

```python
# tools/command_center.py — inside handle_ask

import shlex
import time
from pathlib import Path

ASK_TIER_CEO_COST_CAP_USD = 0.05
ASK_TIER_CHEAP_TIMEOUT_S = 30

def _parse_ask_tier(text: str) -> tuple[str | None, str]:
    """Returns (tier, remaining_text). tier in {'ceo', 'cheap', None}."""
    parts = shlex.split(text, posix=True)
    if len(parts) >= 2 and parts[0] == "--tier" and parts[1] in {"ceo", "cheap"}:
        return parts[1], " ".join(parts[2:]).strip()
    return None, text.strip()


async def handle_ask(chat_id: int, msg_id: int, sender: str, text: str) -> None:
    tier, question = _parse_ask_tier(text)
    if not question:
        await _send_telegram_message(
            chat_id, "Usage: /ask [--tier ceo|cheap] <question>", reply_to=msg_id
        )
        return

    if tier == "ceo":
        # Allowlist check
        if chat_id != MADI_DM_CHAT_ID:
            await _send_telegram_message(
                chat_id, "❌ /ask --tier ceo: Madi DM only", reply_to=msg_id
            )
            return
        await _send_telegram_message(chat_id, "🧠 CEO tier (Codex subscription-first)…", reply_to=msg_id)
        # Codex-first. Paid multi-model council requires explicit approval.
        await _route_codex(chat_id, msg_id, sender, question)
        return

    if tier == "cheap":
        await _send_telegram_message(chat_id, "💰 cheap tier (MLX/DeepSeek)…", reply_to=msg_id)
        # Direct LiteLLM call to local-mlx-coder OR deepseek-v4-flash
        await _route_cheap_tier(chat_id, msg_id, sender, question)
        return

    # Default: unchanged AP-44/45 routing
    await _route_default_ask(chat_id, msg_id, sender, question)
```

### Dispatch table
No new entry — flag is parsed inside existing `/ask` handler.

### `/help` reply update
```
/ask <q>             — default AP-44/45 routing
/ask --tier ceo <q>  — Codex GPT-5.5 subscription-first (Madi DM only; paid council requires approval)
/ask --tier cheap <q>— MLX/DeepSeek only, fastest + cheapest
```

## Tasks (Spec-Kit ordered)

- [x] **T1** — Madi answers Clarify Q1-Q4 via subscription-first amendment
- [x] **T2** — Codex applies the router patch to `tools/command_center.py`
- [x] **T3** — Codex adds tests in `tools/test_operator_boundaries.py`:
  - `test_ask_tier_ceo_is_codex_first_and_not_openclaw`
  - `test_ask_tier_ceo_rejects_non_madi`
  - `test_ask_tier_cheap_uses_local_mlx_route_and_never_codex_grok_or_opus`
- [x] **T4** — Codex bumps `pages/skills/command-center/SKILL.md` with tier-override doctrine
- [ ] **T5** — Madi runs canary: `/ask --tier cheap What is 2+2?` from iPhone DM → expects MLX/DeepSeek reply within 5s
- [ ] **T6** — Madi runs canary: `/ask --tier ceo What is the smallest iPad-only action to prove the system works?` → expects Codex subscription reply or visible subscription failure; no paid API call
- [x] **T7** — Codex counter-check: focused tests prove paid-model guard defaults fail closed and ledger records `billing_surface`

## Canary

T5 + T6 from Madi DM only (chat_id=110793056). NOT Satory group.

## Proof (falsifiable gates pre-T4)

- ✅ `/ask --tier cheap "Q"` routes MLX first, DeepSeek fallback, and never calls Codex/Grok/Opus in unit tests
- ✅ `/ask --tier ceo "Q"` routes Codex subscription-first and never calls OpenClaw in unit tests
- ✅ `multi_model_consult` records `billing_surface` and blocks Opus/Grok/OpenRouter paid calls by default before key lookup
- ✅ `/ask "Q"` (no flag) unchanged from current AP-44/45 routing — regression tests pass
- ✅ Non-Madi sender on `--tier ceo` rejected without firing any model

## Skill/gbrain/OpenBrain sync (at T4)

- `pages/skills/command-center/SKILL.md` AP-52 fold (Codex's lane)
- `pages/skills/ceo-hierarchy/SKILL.md` cross-ref AP-34/AP-44/AP-45 → AP-52
- gbrain timeline entry via VPS substrate-CLI
- OpenBrain capture: this spec URL

## Acceptance criteria (binding, falsifiable)

1. `/ask --tier cheap` from Madi DM returns within 5s, cost < $0.001
2. `/ask --tier ceo` from Madi DM returns through Codex subscription or visible subscription failure; no paid API fallback
3. `/ask` (no flag) unchanged — regression test passes
4. Non-Madi `--tier ceo` rejected without firing any model
5. 5+ daily uses → route receipts and ledgers capture billing surface; cheap-tier average ≤ $0.0005

## Rollback path

Remove the `_parse_ask_tier` call from `handle_ask` → flag is ignored, original routing restored. No data loss; ledger entries persist.

## See also

- `[[HANDSHAKE-2026-05-20-ipad-only-presidential-7-day-plan-0820]]` — parent ladder (Day 4)
- `[[2026-05-20-telegram-consult-command-design]]` — sibling consult spec; paid council remains explicit-approval only
- `[[skills/ceo-hierarchy]]` v1.10.2 — current AP-34/AP-44/AP-45 routing; this spec extends with AP-52
- `[[2026-05-19-multi-model-consult-skill-design]]` — parent skill being wrapped on `--tier ceo` path
- `[[skills/command-center]]` — Codex's impl scope target

## Timeline

- **2026-05-19 18:20 KZT** — Madi articulated CEO/cheap tier split in `ce5b43f4` (Day 4 of ladder)
- **2026-05-20 10:18 KZT** — Opus accidentally created placeholder garbage file in pre-plan-mode race
- **2026-05-20 10:30 KZT** — Opus replaces placeholder with full spec via Plan Mode + post-approval execution
- **2026-05-20 11:55 KZT** — Codex implements subscription-first amendment: `/ask --tier ceo` is Codex-first, `/ask --tier cheap` is MLX/DeepSeek only, and `multi_model_consult` paid APIs fail closed without cap+reason.
