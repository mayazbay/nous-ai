---
type: skill
id: xai-premium-tools
title: "xAI Premium Tools (Imagine + Voice via api.x.ai)"
version: 1.0.0
tier: 3
tags: [skill, xai, grok, image-gen, video-gen, voice, openclaw, p1, moonlit-pnueli]
date: 2026-05-23
status: active
source_count: 4
last_updated: 2026-05-23
related:
  - "[[ceo-hierarchy]]"
  - "[[secrets-manifest]]"
  - "[[SPEC-2026-05-23-moonlit-pnueli-execution]]"
---

# xai-premium-tools v1.0.0

> **Purpose:** thin, cost-gated wrappers around xAI's Imagine API (image gen + video gen + edit + extend) and Voice API (TTS + STT) so OpenClaw factory + Telegram cockpit can invoke them with provenance, cost accounting, and falsifiable artifacts. **Auth:** `XAI_API_KEY` from `~/nous-agaas/.env` on Air (already provisioned per `secrets-manifest`). **NOT covered here:** X/Twitter post search — not in xAI public API, requires separate X API auth, flagged.
> **Version:** v1.0.0 · **Owner:** factory · **Cost gates:** $0.10/image, $0.50/video pre-flight pending Madi billing confirmation.

## Why this exists

Madi 2026-05-23: "Starting today, use your Grok or X Premium subscription in @openclaw. Chat with your agent, generate images and videos, or search for X posts." Grok chat was already wired via LiteLLM (ceo-hierarchy v1.10.14). What was missing: image, video, voice. This skill is P1 of the moonlit-pnueli plan.

## API surface (verified 2026-05-23 from docs.x.ai)

| Capability | Endpoint | Model | Async? | Adapter |
|---|---|---|---|---|
| Image generation | `POST https://api.x.ai/v1/images/generations` | `grok-imagine-image-quality` | sync | `tools/grok_image_gen.py` |
| Image editing | `POST https://api.x.ai/v1/images/edits` (assumed parity) | `grok-imagine-image-quality` | sync | TBD |
| Video gen (text-to-video) | `POST https://api.x.ai/v1/videos/generations` | `grok-imagine-video` | async | `tools/grok_video_gen.py` |
| Video gen (image-to-video) | same endpoint, `image` param | `grok-imagine-video` | async | `tools/grok_video_gen.py --image` |
| Video edit | `POST https://api.x.ai/v1/videos/edits` | `grok-imagine-video` | async | TBD |
| Video extend | `POST https://api.x.ai/v1/videos/extensions` | `grok-imagine-video` | async | TBD |
| Video poll | `GET https://api.x.ai/v1/videos/{request_id}` | — | — | shared helper |
| Voice TTS | Voice API | TBD | sync | TBD (P1.6) |
| Voice STT | Voice API | TBD | sync | TBD (P1.6) |

**Deprecation alarm:** `grok-imagine-image-pro` was deprecated 2026-05-15. NEVER use that model id — fail loud if anyone tries.

## Anti-patterns (do NOT do this)

### AP-1 — Calling without cost-gate
Every image/video call MUST check `XAI_DAILY_CAP_USD` (default $5/day) before firing. If today's spend + this call's *worst-case* would exceed cap, refuse and write a HALT row in the ledger.

### AP-2 — Hardcoding `grok-imagine-image-pro`
Deprecated 2026-05-15. Adapters MUST default to `grok-imagine-image-quality` and reject `-pro` with a loud error referencing this AP.

### AP-3 — Sync-polling video without timeout
Video gen is async (poll `GET /v1/videos/{id}` every 5s). Wallclock cap = 10 min default. NEVER poll indefinitely; refuse to block forever even if the API says `pending`.

### AP-4 — Saving artifacts outside the vault
All generated images/videos land under `pages/inbox/grok-images/YYYY-MM-DD/` or `pages/inbox/grok-videos/YYYY-MM-DD/`. Filename = sha256-of-prompt-truncated-8 + ext. Manifest line written to ledger so artifacts are discoverable.

### AP-5 — Claiming X post search works
xAI public API does NOT expose X post search as of 2026-05-23. Any adapter that pretends to MUST stub with a loud `NotImplementedError("X post search requires separate X API auth, flagged P1.1")` until Madi provisions X API.

### AP-6 — Forgetting Subscription-First amendment
Even though xAI calls are paid API, the env-gating pattern is the same: `NOUS_PAID_API_ALLOWED=1 + NOUS_PAID_API_CAP_USD=X + NOUS_PAID_API_REASON=...` must be exported in the launchd/calling env. Adapters fail-closed if `NOUS_PAID_API_ALLOWED != "1"`.

## Adapters

### `tools/grok_image_gen.py`
- CLI: `python3 tools/grok_image_gen.py --prompt "<text>" [--aspect 16:9] [--resolution 1024x1024] [--n 1] [--out pages/inbox/grok-images/]`
- Returns: JSON `{"request_id":..., "files":[...], "cost_usd": ..., "model":...}`
- Cost gate: refuses if today's xAI spend + est cost > `XAI_DAILY_CAP_USD`

### `tools/grok_video_gen.py`
- CLI: `python3 tools/grok_video_gen.py --prompt "<text>" [--image <url|path>] [--duration 10] [--aspect 16:9] [--resolution 720p]`
- Async polling: 5s interval, 10min wallclock cap
- Returns: JSON `{"request_id":..., "video_url":..., "cost_usd":..., "model":...}`
- Cost gate: refuses if estimated $/video > `XAI_VIDEO_PER_CALL_CAP` (default $0.50)

## Telegram wiring (deferred — P1.4)

Once `tools/telegram_poll.py` is extended to route `/grok-image <prompt>`, `/grok-video <prompt>`, the user-facing UX is one Telegram message → adapter → artifact saved to vault → URL/file replied to Madi. Russian aliases `/грок-картинка`, `/грок-видео` map to same handlers (per AP-7).

### AP-7 — Bilingual Telegram commands
Russian operator surface gets the same xAI tools. Every new /<verb> command added to `telegram_poll.py` MUST also register a Russian alias.

## Ledger

`pages/systems/xai-premium-ledger.jsonl` — one row per call:
```json
{"ts":"2026-05-23T12:34:56+05:00","tool":"grok_image_gen","model":"grok-imagine-image-quality","prompt_hash":"...","cost_usd":0.04,"latency_ms":2300,"artifact":"pages/inbox/grok-images/2026-05-23/abc12345.png","ok":true}
```

Daily spend = sum of `cost_usd` where `ts` is today (Almaty TZ). Cost gate reads this before each call.

## Acceptance criteria (P1 EXIT per moonlit-pnueli)

- `/grok-image` and `/grok-video` each produce one real artifact from Madi's Telegram in test
- Daily xAI cost report under `$5/day` cap visible in cost-alarm digest
- This skill registered in `pages/skills/_gbrain/RESOLVER.md`
- gbrain timeline entry per RULE ZERO

## Timeline

- **2026-05-23** | v1.0.0 created by Opus from moonlit-pnueli P1.2. API surface verified 2026-05-23 from docs.x.ai (P1.1 spike). Adapters drafted same session: `tools/grok_image_gen.py` and `tools/grok_video_gen.py`. Voice TTS/STT adapter and Telegram wiring deferred to P1.4/P1.6.
