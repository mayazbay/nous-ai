---
type: spec
id: SPEC-AUDIT-026-PHASE-2-TO-5-EXEC-PLAN
title: "AUDIT-026 Phase 2-5 consolidated execution plan — what's ready, what's blocked, what needs Madi"
date: 2026-04-08
tags: [spec, audit-026, phase-2, phase-3, phase-4, phase-5, telegram, scheduled-tasks, agent-teams, execution-plan]
source_count: 0
status: reviewed
last_updated: 2026-04-08
priority: p1
related: [AUDIT-026-six-feature-strategic-fit, AUDIT-028-bulletproof-post-fda-and-physical-enforcement-gaps, phase-3-bdl-replacement-reqs-2026-04-08]
---

# AUDIT-026 Phase 2-5 execution plan

## Context

[[AUDIT-026-six-feature-strategic-fit]] (2026-04-07) laid out 5 phases of strategic work. Phase 1 (extended TaskCompleted hook with LAW-005 gates) shipped same-day. Phase 2-5 are pending. This doc consolidates what each phase needs, who owns it, and what's executable this week.

## Phase 2 — Native Telegram channel activation

### What it is
Claude Code has a native `/channels` feature that lets an agent receive real-time DMs from a Telegram bot without polling. Unlike our current `telegram_poll.py` (cron every 60s), the native channel is push-based — Claude Code listens on a WebSocket and reacts instantly when a message arrives.

### Current state
- `telegram_poll.py` running, healthy, captures Madi's DMs to `raw/telegram/` every minute (AUDIT-024 symlink enforces storage inside the vault)
- Native channel NOT yet activated
- Second Telegram bot `@nous_home_bot` (or similar) exists for the native channel, token in `.env`

### What's needed
1. Madi runs **once** in a fresh terminal: `claude --channels plugin:telegram@claude-plugins-official`
2. Claude Code auto-registers the channel, saves auth to `~/.claude/channels/telegram/`
3. Madi DMs the new bot once to test
4. Claude Code writes a `ChannelMessage` hook in `~/.claude/hooks/channel-message.sh` that archives incoming DMs to `raw/telegram/channel-<date>-<id>.md` so LAW-005 is respected (current native channel only stores in `~/.claude/channels/telegram/inbox/`, NOT in vault)

### Blocker
- Madi's manual terminal command (1 minute of his time)

### Not blocked on
- Anthropic credits (channel activation is free, per-message cost only)
- Network (bot already registered)

### Do NOT retire telegram_poll.py
telegram_poll.py stays as the ASYNC capture bot (`@nousAGaaSbot`). Native channel is a SEPARATE, REAL-TIME path. Both bots coexist with different tokens and roles. Per memory: "Both bots coexist cleanly (different tokens, different API connections)."

## Phase 3 — Scheduled tasks migration (replace 3 cron jobs)

### What it is
Claude Code has `mcp__scheduled-tasks__create_scheduled_task` — a first-class way to schedule recurring Claude runs that survive session close. Unlike `/loop` (which only runs while a session is active), scheduled tasks run autonomously via the Claude Code harness.

### Plan — 3 cron jobs to migrate

#### Morning digest (runs 09:00 Almaty daily)

```
mcp__scheduled-tasks__create_scheduled_task:
  taskId: morning_digest
  description: "Daily morning digest — read today.md + yesterday's log + active blockers, write summary to pages/progress/digest-YYYY-MM-DD.md, send to Madi via Telegram"
  cronExpression: "0 9 * * *"  # 09:00 local time (Almaty)
  prompt: |
    Read pages/progress/today.md, the last 24h of log.md, and pages/dashboards/active-blockers.md.
    Write a concise digest to pages/progress/digest-YYYY-MM-DD.md:
    - What shipped yesterday
    - Active blockers + who owns each
    - Top 3 things to do today
    - Anything that needs Madi's explicit attention
    Then send a 500-char Russian summary to Madi's chat 110793056 via @nousAGaaSbot.
```

Currently: `memory_sync.py` runs twice daily at 04:00 + 13:00 via cron. Overlap with morning_digest is fine — memory_sync does a different thing (sync wiki state + lint check).

#### Blocker dashboard (runs hourly at :30)

```
mcp__scheduled-tasks__create_scheduled_task:
  taskId: blocker_dashboard
  description: "Hourly — verify every open blocker in bdl-replacement-state + personal-action-items has moved forward"
  cronExpression: "30 * * * *"  # every hour at :30 to avoid colliding with :00 cron
  prompt: |
    Read pages/progress/bdl-replacement-state-2026-04-07.md and
    pages/progress/madi-personal-action-items-2026-04-08.md. For each blocker
    with a status marker, verify the status is still accurate by checking
    log.md and recent commits. If stale (no update in 24h+), flag in a
    pages/progress/stale-blockers-YYYY-MM-DD.md page.
```

#### Weekly deep audit (Mondays 04:00 Almaty)

```
mcp__scheduled-tasks__create_scheduled_task:
  taskId: weekly_deep_audit
  description: "Mondays 04:00 — full wiki_lint + cross-reference audit + handoff freshness check"
  cronExpression: "0 4 * * 1"  # Monday 04:00 local
  prompt: |
    Run tools/wiki_lint.py to get the health report. If lint score < 8/10,
    investigate + fix the issues via surgical Edit/Write calls. Verify all
    HANDOFFs from the last week are linked from index.md. Check that every
    new LESSON has at least one inbound wikilink. Write results to
    pages/audits/weekly-YYYY-MM-DD.md.
```

### Blocker
- Anthropic credits (scheduled tasks invoke Claude Code = cost tokens per run)
- Cost estimate: ~$0.50 per morning_digest, ~$0.10 per blocker_dashboard = $2.40/day from blocker + $0.50/day from digest = ~$3/day. Under the $15/day cap from AUDIT-020.

### Not blocked on
- Any infrastructure — the scheduled-tasks MCP is already wired into Claude Code
- Madi's manual action (I can create the tasks via the MCP when ready)

### When to execute
After Madi tops up Anthropic credit AND approves the $3/day additional spend.

## Phase 4 — Agent teams vs custom factory decision

### What it is
Anthropic published an "Agent Teams" spec (AUDIT-026 mentioned it as a comparison target). The question: should we retire our custom `/root/nous-agaas/graph.py` factory and migrate to the official Agent Teams framework? Or keep custom + borrow ideas?

### What AUDIT-026 said
> "Principle: Official bones, custom muscle. Use official features for generic work (channels, scheduled tasks, batches) but keep the custom factory where it has our domain logic (REQ-xxx tags, business gates, TaskCompleted hook)."

### What's needed
1. Read the Anthropic Agent Teams spec in full (AUDIT-026 said "Madi will fetch" — not done yet)
2. Write AUDIT-030 comparing:
   - Budget gating (AUDIT-020's $15/day cap — does Agent Teams have this built-in?)
   - File-based state (Karpathy LLM Wiki — do Agent Teams agents read state from vault automatically?)
   - Headless VPS operation (can Agent Teams run as a systemd service without a live Mac session?)
3. If all three YES → migration plan
4. If any NO → keep custom factory + borrow specific mechanisms from Agent Teams

### Blocker
- Madi's action: fetch the Agent Teams spec OR I fetch via WebFetch (can do, but Madi's context on which spec + which version is clearer)
- 2-4 hours research time
- Anthropic credits for the research session (low — file reads only)

### Recommendation
This is **NOT urgent** compared to shipping ERAP. Defer to a future session where we have 2-3 hours uninterrupted. Mid-April earliest.

## Phase 5 — Full workflow exercise (integration test)

### What it is
Once Phases 1-4 are in place, do a full end-to-end test:
1. Madi drops a new requirement via Telegram (native channel from Phase 2)
2. Claude Code ingests it, writes a spec page, creates task entries (Phase 1 hook enforces LAW-005)
3. Scheduled morning digest (Phase 3) picks it up, summarizes
4. Factory CEO (custom or Agent Teams from Phase 4) executes
5. Result syncs back via Mac↔VPS (AUDIT-024 symlink + LESSON-066 fix + FDA grant)
6. Madi gets a Telegram notification when done
7. Weekly deep audit (Phase 3) catches any regression

### Blocker
- All of Phase 1-4 must be complete
- Anthropic credits restored
- Factory restarted

### Not blocked on
- Anything external — this is pure integration testing once prerequisites are met

### When to execute
After Phase 3 scheduled tasks are running clean for 7 days + Phase 4 agent-teams decision is made. ~2-3 weeks out from today.

## Consolidated timeline

| Phase | Earliest executable date | Blocked on | Effort | Cost |
|---|---|---|---|---|
| Phase 1 | ✅ DONE 2026-04-08 | — | — | Sunk cost |
| Phase 2 (Telegram channel) | Tonight | Madi's 1-min terminal command | 5 min Madi + 30 min Claude | ~$0 |
| Phase 3 (scheduled-tasks) | After credit top-up | Anthropic credits ($3/day) | 30 min Claude to configure | ~$3/day ongoing |
| Phase 4 (Agent Teams audit) | Mid-April when free | Research time + credits | 2-3 hours | ~$1 for research session |
| Phase 5 (full exercise) | Late April | Phase 1-4 done + credits | 2-4 hours | ~$5 for full run |

## What I (Claude Code) did in this autonomous run vs what's pending

**Done today (2026-04-08 autonomous session):**
- ✅ Phase 1 was already shipped earlier today
- ✅ Phase 3 **spec** (this file) documented so future session knows exactly what to configure
- ✅ Phase 4 **plan** outlined, not executed

**Pending Madi's manual actions:**
- Phase 2: run `claude --channels plugin:telegram@claude-plugins-official` in a fresh terminal (5 min)
- Phase 3: top up Anthropic credit + approve $3/day additional cost
- Phase 4: no action needed until we're ready for the research session

**Pending my action in next session:**
- Phase 3: `mcp__scheduled-tasks__create_scheduled_task` calls for the 3 jobs above (once credits restored)
- Phase 4: WebFetch the Anthropic Agent Teams spec + write AUDIT-030
- Phase 5: integration test after all prereqs

## See also
- [[AUDIT-026-six-feature-strategic-fit]] — the strategic audit this is executing
- [[AUDIT-028-bulletproof-post-fda-and-physical-enforcement-gaps]] — foundation layer for all phases
- [[phase-3-bdl-replacement-reqs-2026-04-08]] — the factory work phases 2-5 support
- [[madi-personal-action-items-2026-04-08]] — human-factor actions that unblock Phase 5
