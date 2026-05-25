---
type: spec
id: SPEC-2026-05-23-p1-4-telegram-grok-routing
title: "P1.4 — Telegram /grok-image + /grok-video routing into telegram_poll.py"
tags: [spec, p1-4, telegram, grok, xai, moonlit-pnueli, codex-owned]
date: 2026-05-23
source_count: 3
status: ready-for-codex
last_updated: 2026-05-23
related:
  - "[[SPEC-2026-05-23-moonlit-pnueli-execution]]"
  - "[[xai-premium-tools]]"
---

# P1.4 — Telegram /grok-image + /grok-video routing

> **Status:** READY for Codex implementation. Owner: Codex (per moonlit-pnueli D2). Touches `tools/telegram_poll.py` (1074 LOC, PROD on Air launchd `com.nous.telegram-poll`) — must dry-run on Air before going live.

## Goal

User DMs `@nousAGaaSbot`:
- `/grok-image <prompt>` → factory invokes `tools/grok_image_gen.py --prompt "<prompt>"`, replies to chat with image URL or attached file
- `/grok-video <prompt>` → factory invokes `tools/grok_video_gen.py --prompt "<prompt>"`, replies to chat with video URL (async, may take up to 10 min — send "working..." ack immediately)
- Russian aliases `/грок-картинка` and `/грок-видео` map to same handlers (per xai-premium-tools AP-7)

## Constraints

- Cost gate already enforced inside grok_image_gen.py and grok_video_gen.py — no need to duplicate
- Per xai-premium-tools AP-6, subprocess invocation must export `NOUS_PAID_API_ALLOWED=1 + NOUS_PAID_API_CAP_USD=5.00 + NOUS_PAID_API_REASON="telegram /grok-image|video from chat=<id>"` for the child process
- `x_post_search` is NOT in xAI public API (AP-5). Do NOT ship `/x-search` until X API auth provisioned.
- Telegram message split: if generated URL or file path is long, send as separate message; if image file is local b64, decode + send as photo attachment (Telegram bot API `sendPhoto`)

## Touch points in tools/telegram_poll.py

Functions to modify (line numbers approximate; locate via grep before editing):
1. `natural_command()` (line ~521) — add `/grok-image` and `/grok-video` recognition
2. `normalize_bot_command()` (line ~445) — handle `/grok-image@nousAGaaSbot` group form
3. Whatever dispatch loop calls handlers — add subprocess invocation of the new tools
4. Add Russian command aliases via lookup table

## Implementation pattern (recommended)

```python
GROK_TOOL_COMMANDS = {
    "/grok-image": "tools/grok_image_gen.py",
    "/грок-картинка": "tools/grok_image_gen.py",
    "/grok-video": "tools/grok_video_gen.py",
    "/грок-видео": "tools/grok_video_gen.py",
}

def handle_grok_tool(cmd: str, prompt: str, chat_id: int, msg_id: int) -> None:
    tool_path = GROK_TOOL_COMMANDS[cmd]
    is_video = "video" in tool_path

    # Immediate ack so user knows it's working
    send_text(chat_id, f"⏳ Generating {'video (up to 10 min)' if is_video else 'image'}...", reply_to=msg_id)

    env = os.environ.copy()
    env["NOUS_PAID_API_ALLOWED"] = "1"
    env["NOUS_PAID_API_CAP_USD"] = "5.00"
    env["NOUS_PAID_API_REASON"] = f"telegram {cmd} from chat={chat_id}"

    cmd_list = ["python3", tool_path, "--prompt", prompt, "--json"]
    result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=900 if is_video else 120, env=env)

    if result.returncode != 0:
        send_text(chat_id, f"🔴 {cmd} failed: {result.stderr[:300]}", reply_to=msg_id)
        return

    payload = json.loads(result.stdout)
    if not payload.get("ok"):
        send_text(chat_id, f"🔴 {cmd}: {payload.get('error','unknown error')}", reply_to=msg_id)
        return

    if is_video:
        url = payload.get("video_url") or "(no url)"
        send_text(chat_id, f"✅ Video ready: {url}\nLocal: {payload.get('artifact')}\nCost: ${payload.get('cost_usd_est',0):.4f}", reply_to=msg_id)
    else:
        artifacts = payload.get("artifacts", [])
        if artifacts and artifacts[0].endswith(".png"):
            # Local b64 saved; send as photo via sendPhoto
            send_photo(chat_id, VAULT / artifacts[0], reply_to=msg_id, caption=f"Cost: ${payload.get('cost_usd_est',0):.4f}")
        else:
            # URL response
            send_text(chat_id, f"✅ Image: {artifacts[0] if artifacts else '(no artifact)'}\nCost: ${payload.get('cost_usd_est',0):.4f}", reply_to=msg_id)
```

`send_photo` likely needs to be added (use Telegram bot API `sendPhoto` with multipart form). If the existing `telegram_api()` helper at line ~170 supports it, route through there.

## Dry-run plan (do this BEFORE deploying to Air)

1. On Air, snapshot current telegram_poll.py: `ssh air 'cp ~/nous-agaas/wiki/tools/telegram_poll.py ~/nous-agaas/wiki/tools/telegram_poll.py.backup-$(date +%Y%m%d-%H%M)'`
2. Implement changes on Mac vault, commit, push
3. Air auto-pulls
4. Run telegram_poll.py in foreground with a TEST chat (not Madi's main chat) for 5 min, verify routing
5. If green, restart com.nous.telegram-poll launchd job
6. Verify Madi sends `/grok-image test` and gets a reply

## Rollback

```bash
ssh air 'cp ~/nous-agaas/wiki/tools/telegram_poll.py.backup-* ~/nous-agaas/wiki/tools/telegram_poll.py && launchctl kickstart -k gui/501/com.nous.telegram-poll'
```

## Exit gate

- `/grok-image test` sent from Madi's chat returns a real image artifact within 60s
- `/grok-video test` returns "working..." ack within 5s + real video URL within 10 min
- Russian aliases route to same handlers (one test each)
- Cost-alarm digest includes the calls in daily total
- telegram-poll launchd `com.nous.telegram-poll` stays GREEN throughout

## Timeline

- **2026-05-23** | Spec authored by Opus during Stage 2 of moonlit-pnueli execution. Deferred from Stage 1 because telegram_poll.py is 1074 LOC PROD code requiring careful change-management. Owner: Codex.
