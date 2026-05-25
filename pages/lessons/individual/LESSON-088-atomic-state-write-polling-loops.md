---
type: lesson
id: LESSON-088
title: "LESSON-088: Atomic writes for polling state — never use Path.write_text()"
tags: [lessons, polling, state, race-condition, telegram, atomic-write]
date: 2026-04-14
source_count: 0
status: absorbed
absorbed_at: 2026-04-16
last_updated: 2026-04-14
related: [LESSON-086, LESSON-087]
session: 17
severity: P0
integrated_into: infrastructure
absorbed_into: infrastructure
---

# LESSON-088: Atomic writes for polling state — never use Path.write_text()

## What happened

`telegram_poll.py` used `Path.write_text()` to save `last_update_id`.

`Path.write_text()` truncates the file **first**, then writes. A concurrent reader that hits the window between truncate and write sees an empty file, gets a JSON parse error, falls back to `{"last_update_id": 0}`, re-fetches ALL Telegram messages, and processes the same message 4×.

**Proven by stress test:** 46 races in 100 cycles with `write_text()`. 0 races in 1000 cycles with atomic `os.replace()`.

**Verified:** 688 passed, 5 skipped in 354.81s — 2026-04-14 session 17. Commit `3c7ffe1`.

## Root Cause Chain

```
409 Conflict
→ process exits
→ flock released
→ new cron starts immediately
→ reads state mid-write
→ empty file
→ load_state() returns {last_update_id: 0}
→ fetches ALL messages
→ same message processed 4×
```

## The Fix

```python
# CORRECT — atomic write
def save_state(state: dict) -> None:
    """Atomic write — write to .tmp then os.replace() to avoid read-empty-file race.
    os.replace() is atomic on Linux (same filesystem). LESSON-088.
    """
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    import os
    os.replace(str(tmp), str(STATE))  # atomic on same filesystem

# CORRECT — robust read with retry
def load_state() -> dict:
    """Retry 5x with 20ms sleep — outlasts any atomic replace operation."""
    for _attempt in range(5):
        if STATE.exists():
            try:
                data = json.loads(STATE.read_text())
                if isinstance(data.get("last_update_id"), int):
                    return data
            except Exception:
                pass
        import time
        time.sleep(0.02)
    return {"last_update_id": 0}
```

## Rule

**Never use `Path.write_text()` for shared state files in polling loops.**

Always use atomic `os.replace()`. Pattern:
1. Write to `.tmp` file
2. `os.replace(tmp, target)` — atomic on Linux same-filesystem

## Files fixed

- `/opt/nous-agaas/telegram_poll.py` (commit `3c7ffe1`)
- `/root/nous-agaas/tools/telegram_poll.py` (same commit)

## See also

- [[LESSON-086-polling-dedup-save-state-before-slow-handler]] — save state BEFORE slow handler (related polling dedup)
- [[LESSON-087-never-use-telegram-mcp-in-claude-code]] — never use Telegram MCP in Claude Code (the trigger for this)
