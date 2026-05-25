---
type: skill
title: Automated Session Handoff System
version: 1.0.0
extracted_from: 2026-04-14-16-39-22-every-single-time-i-m-fixing-up-and-writ.md
extracted_by: vps-skill-extractor (2026-04-14)
---

## When to Use
When a user needs to automatically capture and transfer context between AI sessions (e.g., when an assistant starts degrading mid-task), eliminating manual copy-paste handoffs.

## Framework
1. **Identify the manual pain** — User is copy-pasting session state between conversations. Replace with automated pipeline.
2. **Implement dual-trigger architecture:**
   - **On-demand trigger** (e.g., `/handoff` Telegram command) — User fires when they notice the AI slipping. Immediate checkpoint written to shared wiki.
   - **Insurance trigger** (e.g., cron every 2-3 hours) — Auto-checkpoint even if user forgets. Writes `HANDOFF-AUTO-*.md` to progress directory.
3. **Define handoff document structure:** What was done, what's in progress, what needs to be done next, relevant file paths/state.
4. **Wire the sync pipeline:** Wiki → local machine sync → new session reads HANDOFF on startup.
5. **Validate the loop:** New session can resume without any manual context transfer. Zero copy-paste.
