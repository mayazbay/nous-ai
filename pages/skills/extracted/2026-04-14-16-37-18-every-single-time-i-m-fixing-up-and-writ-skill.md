---
type: skill
title: Automated Session Handoff via Shared Wiki
version: 1.0.0
extracted_from: 2026-04-14-16-37-18-every-single-time-i-m-fixing-up-and-writ.md
extracted_by: vps-skill-extractor (2026-04-14)
---

## When to Use
When you need to preserve context between AI sessions (same tool or different tools) and want to eliminate manual copy-paste handoffs. Especially useful when one session degrades and you need to seamlessly continue in another.

## Framework
1. **Recognize the wiki IS the bridge** — Don't try to connect sessions directly. Both tools read from the same wiki; write handoffs there and the next session finds them automatically.

2. **Set up periodic auto-handoff (insurance policy)** — Cron job every N hours that reads MEMORY.md + recent task-results + current state, writes a timestamped handoff file to wiki, and updates MEMORY.md if anything critical occurred.

3. **Approximate "slipping" detection** — You can't observe another session's context window directly, so use proxies: message count thresholds (e.g., 40+ messages triggers a mid-session checkpoint), explicit user signals ("starting new session"), or heartbeat checks for quality degradation mentions.

4. **Eliminate manual steps** — No more "write a handoff" instructions, no copy-paste, no lost context. Handoffs live in wiki, always current, always readable by any session.
