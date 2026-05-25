---
tier: 2
type: skill
name: operator-boundaries
version: 1.1.0
last_updated: 2026-04-27
status: active
description: "Use when deciding whether an always-on agent should answer, hold, queue, or escalate based on Madi's schedule, quiet hours, health goals, family goals, urgency, and revenue-critical context. Prevents OpenClaw/Telegram from becoming a sleep-destroying loop while preserving urgent business execution. v1.1.0 adds command-center code enforcement."
triggers:
  - quiet hours
  - after midnight
  - health goals
  - bedtime
  - refuse after 12:30am
  - schedule boundary
  - should the agent respond now
  - queue for morning
tools: [Bash, Read, Grep]
mutating: true
related: [collaborative-reading, cron-scheduler, command-center, daily-task-prep, ceo-hierarchy]
tags: [skill, operator, health, schedule, telegram, openclaw, boundaries]
title: "operator-boundaries v1.1.0"
---

# operator-boundaries v1.1.0

## Purpose

The factory exists to give Madi more leverage and more life, not to pull him into infinite late-night loops. This skill decides when the agent should respond now, hold for morning, or escalate because the work is genuinely urgent.

## Contract

**Inputs:** user request, current local time, urgency signals, known schedule/health preferences, project criticality.

**Outputs:** `respond_now`, `hold_for_morning`, or `escalate_urgent`, with a short reason and a saved queue item when held.

**Invariants:**
- Do not moralize, shame, or lecture.
- Do not block urgent production, family, safety, legal, or revenue-critical work.
- Do not use hard-coded health rules without a source page. Read `pages/personal/operator-boundaries.md` when present.
- A held request is not lost: save it with source, timestamp, and next review time.

## Current Policy

Source page: `pages/personal/operator-boundaries.md`.

Default active-soft gate:

- Timezone: `Asia/Almaty`.
- Quiet window: `00:30-08:00`.
- During quiet window, hold non-urgent ideation, reading, research, browsing, UI polish, and speculative planning.
- Bypass quiet window for: urgent, broke, prod, demo, critical, now, asap, crisis, family, safety, legal deadline, paid-client incident, Satory live incident, Telegram command explicitly marked override.
- If held, answer briefly: "I saved this for morning" plus the queue path. No long discussion.

## Decision Procedure

1. Get local time:
   ```bash
   TZ=Asia/Almaty date '+%Y-%m-%d %H:%M %Z'
   ```
2. Read `pages/personal/operator-boundaries.md`.
3. Classify request:
   - `urgent`: production/client/family/safety/legal/revenue-critical or explicit override.
   - `important_nonurgent`: strategy, reading, planning, research, task cleanup.
   - `low_value`: loops, duplicate asks, non-actionable browsing.
4. Decide:
   - Outside quiet window: respond normally.
   - Quiet window + urgent: respond now, record override.
   - Quiet window + important_nonurgent: save queue item, hold for morning.
   - Quiet window + low_value: save only if it contains new information; otherwise decline briefly.
5. If the request is held, create or append:
   `pages/personal/boundary-queue-YYYY-MM-DD.md`.

## Output Format

```markdown
Boundary decision: {respond_now|hold_for_morning|escalate_urgent}
Reason: {one sentence}
Saved: {path or none}
Next: {time/action}
```

## Anti-Patterns

### AP-1 -- Pretending health boundaries are active code

Do not claim Telegram/OpenClaw physically refuses after 00:30 unless the command-center code path is actually enforcing it. Skill doctrine is a rule agents must follow; code enforcement is a separate implementation proof.

### AP-2 -- Blocking real emergencies

The boundary is for health and focus, not bureaucracy. Urgent client, family, safety, legal, or revenue work bypasses immediately.

### AP-3 -- Long bedtime speeches

If holding a request, be short. Save the thought and release Madi from needing to manage the queue.

### AP-4 -- Doctrine without command-center enforcement is not a boundary

The boundary is only real when the Telegram command path checks it before LLM work starts. `command_center.py` must gate non-urgent `/ask`, implicit `/ask`, `/ask-direct`, `/code`, and `/codex` during `00:30-08:00 Asia/Almaty`; held requests must be written to `pages/personal/boundary-queue-YYYY-MM-DD.md` with source/message id and next review time. Urgent/override terms bypass. Status/health/report/help/trace stay available because they are operational checks.

## Timeline

- **2026-04-27** | v1.0.0 -- Created from Madi's Gary Tan/OpenClaw/GBrain note about an agent knowing schedule and health goals well enough to refuse non-urgent late-night work. Codifies a soft quiet-hours gate with urgent bypass and durable queueing. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.0.0 → v1.1.0 -- Promoted from soft doctrine to command-center enforcement. Added deterministic quiet-hours helpers, vault queue persistence, urgent bypass logging, and regression tests. No new LESSON (RULE ZERO).
