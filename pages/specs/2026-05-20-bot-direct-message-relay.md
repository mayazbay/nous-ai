---
type: spec
id: SPEC-BOT-DM-RELAY-2026-05-20
title: "Bot direct-message relay (group-safe credential share)"
tags: [spec, telegram, bot, relay, credentials, ap-43, follow-up]
date: 2026-05-20
source_count: 0
status: draft
last_updated: 2026-05-20
related: ["[[ceo-hierarchy]]", "[[architecture-quickref]]"]

---

# Bot direct-message relay (group-safe credential share)

> **Why this exists.** AP-42 + AP-43 codified that the bot never publishes credentials in group chats, even with explicit owner authorization. Madi's actual need behind that conversation was: "Asyl needs dashboard access; I shouldn't have to manually DM him." Today the bot literally cannot DM @aliakbar_asylbek because Telegram's Bot API does not allow a bot to initiate a DM to a user who has never spoken to it first. This spec describes the minimal addition that solves the underlying need while keeping AP-42's group-safety guarantee intact.

## Owners

| Step | Owner | Status |
|---|---|---|
| 1. Asyl sends `/start` to `@nousAGaaSbot` once | Asyl (one-time human action) | **pending — needs Asyl to do this** |
| 2. Bot persists Asyl's chat_id on first contact | Code (any future session can implement) | not started |
| 3. Madi DMs bot: `relay to @asyl: <creds>` | Madi at use time | gated on #1 + #2 |
| 4. Bot looks up Asyl's chat_id and DMs him the payload (with audit log) | Code (same session that ships #2) | gated on #2 |

If Asyl never sends `/start`, the relay path is impossible and the manual workaround stays: Madi opens his own Telegram DM with Asyl and pastes the credentials (10 seconds). This spec does NOT change that fallback.

## Design

### 1. `/start` handler that captures chat_id

Add to `tools/telegram_poll.py` (or via dispatcher in `command_center.py`). When any user DMs the bot `/start`:

- Persist `{username, chat_id, first_seen_iso}` to `/Users/madia/nous-agaas/state/known_users.json` (atomic write under fcntl).
- Reply: `Привет, @<username>. Запомнил. Мади может пересылать мне сообщения для тебя через DM.`
- If the user is the owner (`@madi_ayazbay`), also remind in the reply that any relay must use the `relay to @<target>:` prefix (see #3).

Schema:
```json
{
  "users": {
    "@aliakbar_asylbek": {
      "chat_id": 123456789,
      "first_seen": "2026-05-21T09:00:00+05:00",
      "last_seen": "2026-05-21T09:00:00+05:00"
    }
  }
}
```

### 2. `relay to @user: <payload>` parser in Madi's DM

In `command_center.handle()`, when `chat_id == OWNER_CHAT_ID` AND text matches `^relay to @(\w+):(.*)$`:

- Extract `target_username` and `payload`.
- Look up `target_username` in `known_users.json`.
- If not found: reply `❌ @<target> ещё не /start-ил бота. Попроси его прислать /start один раз — потом запомню.`
- If found: `_tg_send(bot_token, target_chat_id, f"📨 От @madi_ayazbay:\n\n{payload}")`. Reply to Madi: `✅ Переслано @<target> (chat_id={target_chat_id}).`
- Log every relay to `/Users/madia/nous-agaas/logs/relay.jsonl` with `{ts, sender, target, payload_sha256, bot_msg_id_out}`. Never log the raw payload — only the sha256 — so the audit ledger doesn't become a credential bucket itself.

### 3. Safety constraints (non-negotiable)

- **Owner-only initiator.** Only `OWNER_CHAT_ID` can trigger a relay. Any other sender posting `relay to @x:` gets the AP-42 actionable decline.
- **DM-only initiator.** Owner must use the relay from their own DM with the bot, NOT from a group. (`if _is_group_chat(chat_id): reply AP-42 decline; return`.) This prevents group-context relay confusion.
- **Receipt only, no payload, in the audit log.** Log the sha256 of the payload, not the payload itself.
- **No retry.** If `_tg_send` fails (e.g., the target blocked the bot), report the failure to Madi once; do not retry automatically (avoids spam on permanent failures).

## Tests

Before shipping:
- `test_relay_owner_only_initiator` — non-owner gets AP-42 decline
- `test_relay_dm_only` — owner using `relay to` in a group gets AP-42 decline (not relayed)
- `test_relay_unknown_target` — unknown `@user` returns the actionable error
- `test_relay_known_target_succeeds` — happy path, verifies the target DM is sent and the audit log entry has sha256 (not raw)
- `test_relay_log_never_contains_raw_payload` — read `relay.jsonl`, assert it has `payload_sha256` and never `payload`

## Future hardening (optional, after MVP ships)

- Allow Asyl to revoke (`/forget` removes his entry from `known_users.json`).
- Time-limited relay tokens (Madi sends a one-time `relay to @asyl --once: <payload>` so a buggy script can't loop).
- Self-destructing messages via Telegram secret chat (out of scope for Bot API; native Telegram only).

## Hand-off

Until #1 happens (Asyl sends `/start`), Madi shares credentials manually via his own Telegram DM with Asyl. The 10-second action remains the safe default. This spec is durable substrate; any future session reading `pages/specs/` will see it and can ship the implementation when Asyl's `/start` finally arrives.

## See also

- [[ceo-hierarchy]] AP-42 (credential-handoff strict + actionable)
- [[ceo-hierarchy]] AP-43 (owner-mode skip echo + terse reply)
- [[architecture-quickref]] (Telegram poller is on Air, exclusive)
