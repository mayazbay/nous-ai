---
type: lesson
id: LESSON-100
title: "LESSON-100: Write-back git push fails — always pull --rebase before push in shared repos"
tags: [lessons, git, write-back, wiki, factory, run_task, infrastructure]
date: 2026-04-15
status: implicit-already-in-skill
absorbed_into: [audit]
absorbed_at: 2026-04-16
last_updated: 2026-04-15
related: [HANDOFF-2026-04-15-session23, LESSON-086-polling-dedup, skills/infrastructure]
session: 23
severity: P2
integrated_into: infrastructure
---

# LESSON-100: Write-back git push fails — always pull --rebase before push in shared repos

## The Problem

`run_task.py` `_write_back_to_wiki()` intermittently fails to push:

```
error: failed to push some refs to '65.108.215.200:/root/nous-agaas/obsidian-wiki.git'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

Task result committed locally (Air wiki) but NOT pushed to VPS. gbrain autopilot missed the new page.

## Root Cause

Three concurrent writers to the VPS bare repo:
1. **Air wiki-sync** (`com.nous.wiki-sync`) — every 5 min
2. **gbrain autopilot** (VPS) — every 5 min (embedding/link commits)
3. **run_task.py write-back** — after every task

When gbrain autopilot or wiki-sync pushed WHILE a task was processing, the bare repo got ahead of Air's local copy. Write-back pushed without pulling first → rejected.

## The Fix

Add `git pull --rebase` between `git commit` and `git push` in `_write_back_to_wiki()`:

```python
# Before (broken):
subprocess.run(["git", "-C", WIKI_PATH, "commit", ...])
subprocess.run(["git", "-C", WIKI_PATH, "push", "origin", "main"])  # ← fails if remote ahead

# After (fixed):
subprocess.run(["git", "-C", WIKI_PATH, "commit", ...])
subprocess.run(["git", "-C", WIKI_PATH, "pull", "--rebase", "origin", "main"],  # NEW
               check=True, capture_output=True, timeout=30)
subprocess.run(["git", "-C", WIKI_PATH, "push", "origin", "main"])
```

`--rebase` (not merge) keeps write-back commits at tip; no merge commits; timestamped files never conflict.

## Verified

```
write-back: committed 2026-04-15-17-18-11-reply-writeback-pushfix-ok.md to wiki
write-back: pushed 2026-04-15-17-18-11-reply-writeback-pushfix-ok.md to VPS
WRITEBACK_PUSHFIX_OK
```

## Rule

**Any process that writes to a git repo shared by multiple concurrent writers MUST `git pull --rebase` before `git push`.**

Applies to: `run_task.py` write-back, `command_center.py` `/handoff` section, any future write-back logic in the Nous system.

## See also

- [[skills/infrastructure/SKILL.md]]
- [[LESSON-086-polling-dedup-save-state-before-slow-handler]]
- [[LESSON-099-zai-balance-exhausted-litellm-fallback]]
- [[HANDOFF-2026-04-15-session23]]
