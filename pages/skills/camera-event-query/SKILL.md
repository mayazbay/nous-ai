---
type: skill
id: camera-event-query
title: "Camera event query — Telegram /last-plate, /last-photo"
version: 1.0.0
date: 2026-05-20
last_updated: 2026-05-20
status: active
tier: 2
tags: [skill, camera, satory, hikvision, telegram, query, intake]
related:
  - "[[openclaw-probe-isolation]]"
  - "[[mistake-to-skill]]"
  - "[[model-failover]]"
  - "[[lane-lock]]"
---

# camera-event-query v1.0.0

## Why this exists

Camera/VAR events flow into `65.108.215.200:9080/events/camera/hxml` (Hikvision ISAPI multipart: XML + photo). The intake parses plate, speed, limit, violation flag, camera ID, event timestamp, and scene/plate photo into a backend ledger.

Before this skill, the system was intake-only — no Telegram-side query to surface the last recognized plate or photo. When `@aliakbar_asylbek` asked the bot for both on 2026-05-20, the routing fell back to `/ask` → OpenClaw, which returned a worker-health sentinel (see `[[openclaw-probe-isolation]]` for that bug).

The fix is two new Telegram commands: `/last-plate` and `/last-photo`. Both query a fail-soft HTTP chain and reply in Russian with the actual event data — or a clear "data not yet available" message when the read API isn't reachable.

## Current rules

- Implementation: `tools/satory_camera_query.py`. Public functions: `fetch_last_event()`, `extract_fields()`, `format_last_plate_ru()`, `format_last_photo_ru()`, `get_last_plate_reply()`, `get_last_photo_reply()`.
- Endpoint chain (tried in order, first 200 wins):
  1. `http://65.108.215.200:9080/events/camera/last` — guess of a read companion to the existing intake POST.
  2. `https://api.nousagaas.com/api/cameras/last` — extension of the existing API surface.
  3. `https://api.nousagaas.com/api/cameras/events?limit=1` — generic events list.
- All HTTP calls are fail-soft: timeout, HTTP error, JSON parse error → return `None`. The handler shows a graceful fallback message; the bot never crashes.
- Cache the last successful response for `SATORY_CAMERA_QUERY_CACHE_TTL=30` seconds (env-tunable) to avoid hammering the intake when a customer repeats the question.
- Replies are Russian-first (Kazakh customers, Russian product language). Format includes plate, speed, limit, excess, camera, violation flag, event timestamp, and photo URL.
- Telegram wiring: `tools/command_center.py` `handle()` dispatches `/last-plate` and `/last-photo` BEFORE `/trace`, both reading from `satory_camera_query` and replying via `_tg_send`.

## Anti-Patterns

**AP-1: Claim a plate/photo that the API didn't return.** When `fetch_last_event` returns `None`, the reply MUST say "Не удалось получить" (couldn't fetch) — never invent a value. The customer would rather see "API not yet wired" than a hallucinated plate. The audit's "no lies" rule applies here.

**AP-2: Skip the 30s cache.** Repeated `/last-plate` calls in rapid succession (e.g., customer panicking and asking 5 times) MUST NOT hammer the intake. Cache TTL bounded by `CACHE_TTL_SECONDS` (default 30s, env-tunable).

**AP-3: Drop the freshness timestamp from the reply.** The reply MUST include the event's own `ts` field so the operator can immediately tell if the data is stale (e.g., from yesterday's last event) vs fresh. A reply without a timestamp is operationally ambiguous.

## Timeline

- 2026-05-20 v1.0.0 — Created in response to the Assylbek incident. Companion to `[[openclaw-probe-isolation]]` v1.0.0. First deployment will probe the 3 endpoints; whichever returns first becomes the de facto contract. Backend team needs to confirm/build the corresponding read endpoint on VPS.

## See also

- `[[openclaw-probe-isolation]]` — the sibling fix that ensures probe sentinels don't replace this query's response.
- `[[mistake-to-skill]]` — query failures (all endpoints 5xx) log here for the weekly absorption digest.
- `[[model-failover]]` Ship 1 — fail-soft pattern adopted from there.
- `[[lane-lock]]` Ship 2 — lane-tagged commits ensure this skill's edits don't collide with peer sessions.
