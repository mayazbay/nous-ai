---
type: lesson
id: LESSON-087
title: "LESSON-087: Never use Telegram MCP tools in Claude Code sessions (narrowed session 51)"
tags: [lessons, telegram, mcp, dual-agent, 409-conflict, hard-rule, drift-annotated-session-51]
date: 2026-04-14
source_count: 0
status: narrowed-session-51
absorbed_into: [command-center, session-operating-contract]
absorbed_at: 2026-04-16
last_updated: 2026-04-20
related: [LESSON-088, LESSON-086]
session: 17
severity: P0
integrated_into: command-center
---

# LESSON-087: Never use Telegram MCP tools in Claude Code sessions

> **⚠️ DRIFT CORRECTION — session 51, 2026-04-20:** The rule below was over-scoped. The
> real risk is **same-token polling**, not the tool class. CC-MCP plugin's
> `~/.claude/channels/telegram/.env` holds a DIFFERENT bot token (id `8613073660`) than
> `@nousAGaaSbot` (id `8799328101`) — so the plugin is SAFE when the tokens differ. See
> `CLAUDE.md` HARD RULE 1 (narrowed) + `session-operating-contract` v1.4 Rule 7 for the
> current authoritative phrasing + mechanical pre-flight check. This LESSON is preserved
> for historical accuracy; do not act on the class-wide ban below without reading the
> narrowed rule first.

## Rule (historical — session 17; narrowed session 51)

**NEVER call `mcp__plugin_telegram_telegram__*` tools from a Claude Code session.**

Banned tools:
```
mcp__plugin_telegram_telegram__reply
mcp__plugin_telegram_telegram__edit_message
mcp__plugin_telegram_telegram__react
mcp__plugin_telegram_telegram__download_attachment
```

## What happened

Claude Code used `mcp__plugin_telegram_telegram__reply` to send a Telegram message.
Meanwhile, `telegram_poll.py` was already running on VPS (cron every 1 minute), polling the same bot token.

Telegram's Bot API prohibits two concurrent consumers on one token:
- HTTP 409 Conflict on both processes
- Messages duplicated 4× (each process retried on conflict)
- VPS poller crashed → cron spawned new instance → duplicate processing loop

This caused a dual-agent situation: both Claude Code AND GLM-5.1 (via the VPS factory) were responding to Madi simultaneously with different answers.

## Root Cause

`telegram_poll.py` on VPS holds the bot token. Any other process calling the same Telegram bot API endpoint causes 409 Conflict. Claude Code's Telegram MCP uses the same token → immediate conflict.

## Prevention

**Never use Telegram MCP from Claude Code.** Claude Code communicates via Claude Code chat only.

If you need to send a message to Madi:
1. Do NOT use Telegram MCP
2. Communicate here in the Claude Code chat
3. If truly needed, SSH to VPS and use `telegram_poll.py`'s messaging functions directly

## This is now a HARD RULE in CLAUDE.md

Added to `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` as Rule #1.

## See also

- [[LESSON-088-atomic-state-write-polling-loops]] — atomic state write (the fix for the duplicate processing)
- [[LESSON-086-polling-dedup-save-state-before-slow-handler]] — save state before slow handler (related polling fix)
- [[progress/CLAUDE-project-rules]] — CLAUDE.md in wiki
