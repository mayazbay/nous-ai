---
id: SPEC-APK-BOT-INLINE-KEYBOARDS-2026-04-17
type: spec
title: "APK bot UI overhaul — replace typed slash commands with Telegram inline keyboards (menu buttons + back/home navigation)"
date: 2026-04-17
status: draft
last_updated: 2026-04-17
owner: claude-code-mac (Opus 4.7 1M) + Madi
tags: [spec, apk-status-bot, telegram, inline-keyboards, ux, session-42, draft]
related:
  - SPEC-APK-STATUS-BOT-A-2026-04-17
  - PLAN-APK-STATUS-BOT-A-2026-04-17
  - HANDOFF-AUTO-2026-04-17-session-42-addendum-secrets
---

# APK Bot UI Overhaul — Inline Keyboards

## Why

Madi, session 42 (exact words): "I want it very simple, like a menu option and clicking, because I'm going to be sending it to the people. It's going to be hard for me to tell them exactly what to type. There's going to be human error."

Audience: Papa Smatay, Daniyar, Denis. None are command-line literate. Typing `/apk 10.235.9.101` is error-prone — wrong case, wrong slashes, wrong IP format, failed autocorrect.

Goal: everything reachable by tap. No typing required after the first `/start`.

## What it looks like (mockup)

```
  /start  →
  ┌──────────────────────────────────┐
  │ 👋 Привет! Я бот АПК             │
  │                                  │
  │ Выберите действие:               │
  └──────────────────────────────────┘
  [📊 Статус]  [🌅 Сегодня]
  [🔍 Найти АПК] [❓ Помощь]

  Tap [📊 Статус]  →
  ┌──────────────────────────────────┐
  │ ✅ 189/243 работают               │
  │ ⚠️ 54 не работают:                │
  │    • 12 нет скорости              │
  │    • 31 нет номера                │
  │    • 11 молчат                    │
  │ Обновлено: 14:23                  │
  └──────────────────────────────────┘
  [🔴 Не работают] [⚫ Молчат]
  [🔙 Назад] [🏠 Главное меню]

  Tap [🔴 Не работают]  →
  ┌──────────────────────────────────┐
  │ 🔴 АПК с проблемами (54)          │
  │ Страница 1/3                      │
  └──────────────────────────────────┘
  [ЛУ 10.235.9.101 — Абая 145]
  [ЛУ 10.235.9.102 — Абая 200]
  [ЛУ 10.235.9.103 — Абая 300]
  ... (up to 20 per page)
  [◀ Пред] [След ▶]
  [🔙 Назад] [🏠 Главное меню]

  Tap an APK  →
  ┌──────────────────────────────────┐
  │ ЛУ 10.235.9.101 — Абая 145        │
  │ События 24ч: 127                  │
  │ Со скоростью: 15 (12%) — broken   │
  │ С номером: 118 (93%) — ok         │
  │ Silence: ok                       │
  │ Broken since: 2026-04-12 10:00    │
  └──────────────────────────────────┘
  [🔙 Назад к списку] [🏠 Главное меню]
```

## Architecture

Telegram inline keyboards work via two pieces:

1. **`reply_markup`** — JSON attached to `sendMessage`. Array of button rows. Each button has `text` (label) and `callback_data` (opaque ~64-byte payload the bot receives when tapped).
2. **`callback_query`** updates — a new update type delivered when a user taps a button. Bot must `answerCallbackQuery` (optional micro-toast) and typically edits the message via `editMessageText` to show the next screen.

Existing code already polls updates. We just need to extend the update handler to also route `callback_query`, plus build the keyboard JSON payloads.

### New files

```
apk_status_bot/
├── keyboards.py            # Builds the reply_markup JSON for each screen
├── callback_router.py      # Dispatches callback_data → screen function
└── screens/
    ├── __init__.py
    ├── main_menu.py        # 4-button start screen
    ├── status_screen.py    # summary + drill-down buttons
    ├── broken_list.py      # paginated list of broken APKs
    ├── apk_detail.py       # one APK card
    ├── today_screen.py     # today's digest with sections as tappable jumps
    └── help_screen.py
```

### callback_data format

Max 64 bytes. Use URL-safe compact grammar:

```
v1:screen:param1:param2
```

Examples:
- `v1:main` — main menu
- `v1:status` — status summary
- `v1:broken:1` — broken-list page 1
- `v1:apk:10.235.9.101` — apk detail
- `v1:today` — today digest
- `v1:help` — help

If param fits in >64 bytes, use a short lookup key that maps to state in a lightweight `callback_state` table.

### Existing plain-text commands stay

`/start` `/status` `/apk <IP>` `/today` `/help` remain functional for power users + for automated messages / webhooks. The menu is a **parallel** surface, not a replacement.

## Task breakdown (estimate ~3h)

| # | Task | Tests |
|---|---|---|
| K01 | `keyboards.py` — 6 `build_*` functions returning `InlineKeyboardMarkup` dicts | unit: JSON shape + callback_data format |
| K02 | `callback_router.py` — dispatch `callback_data` → screen function | unit: every `v1:*` route resolves |
| K03 | `screens/main_menu.py` | unit: returns text + markup |
| K04 | `screens/status_screen.py` | unit + zero-row guard |
| K05 | `screens/broken_list.py` — paginated; 20 per page; Prev/Next buttons | unit: pagination boundaries |
| K06 | `screens/apk_detail.py` | unit: not-found case returns back-button |
| K07 | `screens/today_screen.py` — reuses `compose_digest` | unit: zero-row guard |
| K08 | `screens/help_screen.py` | trivial |
| K09 | `bot_polling.py` — handle `callback_query` path; call `answerCallbackQuery` + `editMessageText` | integration: mock update → correct edit call |
| K10 | Wire `/start` to post the main menu instead of plain text | round-trip test to admin DM |
| K11 | MarkdownV2 escape regression tests per screen | unit |
| K12 | Round-trip verify every screen via pre-deploy `send_message(TEST_CHAT, ...)` | all must HTTP 200 |

## Dependencies

- Existing: `telegram_client.send_message` works. Needs extension for `edit_message_text` + `answer_callback_query` + `reply_markup` param.
- Existing: `command_handlers.handle_status/apk/help` — screens can call these directly for the text body, add markup separately.
- Existing: `digest.compose_digest` — today screen reuses.

## Zero-row / no-data honesty

Every screen follows **evidence-verification AP-7**: if the underlying data is empty (no registered APKs), show the "⚠️ Нет данных" message + a `[🔄 Обновить]` button + `[🏠 Главное меню]`. Don't render a broken-list screen of 0 APKs.

## Out of scope (for this spec)

- Group-chat behavior (group ID still O2-blocked).
- Per-user authentication / ACL (later — only allowlisted user IDs can tap).
- Charts / images — text-only screens for v1.
- Self-heal agent interaction via callback (maybe v2).

## Next session handoff

Session 43 or 44 picks this up. Estimate: 3h to ship K01-K12 with TDD. Blocking preconds: token rotated, bot is live, `/status`+`/today` known-working (all done session 42).

## See also

- [[SPEC-APK-STATUS-BOT-A-2026-04-17]] — parent spec; §4 mentions commands but not keyboards
- [[PLAN-APK-STATUS-BOT-A-2026-04-17]] — parent plan; this is T34+ (new phase)
- [[evidence-verification]] AP-7 — round-trip verification discipline applies to every screen
- Telegram Bot API: `sendMessage` with `reply_markup`, `answerCallbackQuery`, `editMessageText` — https://core.telegram.org/bots/api#inlinekeyboardmarkup
