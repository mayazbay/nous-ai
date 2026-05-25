---
type: skill
title: Polling deduplication — save state before slow handler
version: 1.0.0
extracted_from: LESSON-086 / telegram_poll.py fix (session 15, 2026-04-14)
extracted_by: claude-session-15
date: 2026-04-14
tags: [polling, cron, telegram, deduplication, concurrency]
---

## When to Use

Any time you write a **polling loop** that:
1. Loads state (offset, cursor, last-seen-id) from disk
2. Processes each item by calling a **slow handler** (>1s: subprocess, HTTP, LLM call)
3. Multiple instances MAY run concurrently (cron, launchd, systemd timer)

## The Rule

**Save the item's ID/offset to disk BEFORE calling the slow handler, not after.**

## Framework

### Step 1: Identify the slow handler
Any call that blocks for >1s: subprocess.run(), requests.post(), API call, LLM inference.

### Step 2: Advance state BEFORE calling it

```python
# ✅ CORRECT
for item in new_items:
    state["last_seen_id"] = item.id
    save_state(state)          # write to disk NOW
    slow_handler(item)         # can block safely — concurrent instances skip this ID

# ❌ WRONG
for item in new_items:
    slow_handler(item)         # blocks → concurrent instance re-reads same ID
state["last_seen_id"] = max_id
save_state(state)              # too late
```

### Step 3: Make handlers idempotent (defense in depth)

Even with the fix, design handlers to be safe to call twice:
- Check if output file already exists before writing
- Use `INSERT OR IGNORE` / upsert in DB writes
- Check skill file existence before extracting (as vps_skill_extractor.py does)

### Step 4: Add lockfile for critical paths (optional)

For extremely slow handlers (>60s) where duplicates cause real cost:
```python
import fcntl
with open("/tmp/my-poller.lock", "w") as lockf:
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("Another instance running — exit")
        sys.exit(0)
    # safe to proceed
```

## Real Example

`telegram_poll.py` — Madi's messages routed 3× to OpenClaw because
`command_center.handle()` blocked 60-300s. Fixed: move `save_state()` inside
the `for upd in updates` loop, before `process_message()`.

Commit: `f919301` in `/opt/nous-agaas`
