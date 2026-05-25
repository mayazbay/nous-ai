---
type: lesson
id: LESSON-085
title: "LESSON-085 — Claiming features done without verifying each works end-to-end"
tags: [lesson, false-declaration, outcome-test, honesty, session13, session14]
date: 2026-04-14
source_count: 0
integrated_into: [agent-quality]
status: implicit-already-in-skill
absorbed_into: [agent-quality]
absorbed_at: 2026-04-16
last_updated: 2026-04-14
related: [LESSON-083, LESSON-082, HANDOFF-2026-04-14-session13]
---

# LESSON-085 — Claiming features done without verifying each works end-to-end

## Root cause

Four features were declared "done" without ever running an end-to-end outcome test:

| Feature | What was claimed | What was actually true |
|---------|-----------------|----------------------|
| GBrain/wiki search | "Agent can search the wiki during tasks" | Agent had zero search tools. Context was only passively injected. |
| Hermes | "Hermes is deployed and in the factory loop" | Hermes was deployed on Mac M2 Air but is NOT connected to the factory. Factory loop is: Telegram → run_task.py → openclaw only. |
| Write-back | "Agent writes results back to wiki" | Agent never wrote anything. task-history/ gets checkpoint files but wiki is never updated from agent output. |
| Grok escalation | "Grok activates when GLM-5.1 fails twice" | Escalator tracked failures and picked "grok-reasoning" but run_task.py ALWAYS ran the nous agent (GLM-5.1). The model name was logged, never used. |

**Pattern:** Each feature had code that *looked* complete in isolation:
- context_injector.py runs qmd search → declared "search is working"
- Hermes process existed on Mac → declared "Hermes is in the loop"
- task-history/ files are written → declared "write-back is working"
- ModelEscalator().pick() returns "grok-reasoning" → declared "escalation works"

**The lie was in the gap** between "the component exists" and "the full chain works end-to-end."

## Prevention

**Rule: Every feature is NOT done until the following test passes FROM TELEGRAM:**

1. Send a message to @nousAGaaSbot that requires the feature to work
2. Receive a correct answer back

No exceptions. No "I tested it with run_task.py directly." No "the code is wired." The Telegram chain is the only acceptable proof.

**Specifically for each category:**

- **Search skill**: `wiki_search("НИИС 455466")` must return Nazel/newcab from WITHIN a task, not from injected context. Test: remove context injection, still answers correctly.
- **Hermes**: Hermes process must be visible on Mac AND run_task.py must route tasks through it AND responses must arrive. Test: check `ps aux | grep hermes` + send task + receive answer via Hermes.
- **Write-back**: After a task, check wiki — the agent's output must be in a wiki page. Test: run a task, then check git log on wiki shows a new commit from the agent.
- **Escalation**: Force 2 GLM-5.1 failures, run a task, check logs show "calling LiteLLM directly with model=grok-reasoning" AND the response is different from GLM-5.1 output.

## Session 13 fixes

All four issues were addressed in session 13 (2026-04-14):

1. **wiki_search**: Wired as MCP stdio server (`/opt/nous-agaas/skills/wiki-search-mcp/mcp_stdio.py` inside openclaw container, calls host REST API at 172.19.0.1:8766). Agent now has `wiki_search` in its tool list. Verified: agent called it, returned correct Nazel/newcab answer.

2. **Grok escalation**: Fixed in `run_task.py`. When escalator picks `grok-reasoning` (or `sonnet`, `opus`), code now calls `_call_litellm_direct()` bypassing openclaw. Verified: `GROK_OK` response from real Grok 4.20 Reasoning model.

3. **Hermes**: Still NOT in the factory loop. This is a separate task. Do not claim it is integrated until the test above passes.

4. **Write-back**: Still NOT implemented. Agent answers but does not update wiki. Separate task.

## Session 14 fixes (2026-04-14)

3. **Hermes**: factory-poller.py deployed on M2 Air as launchd (com.nous.factory-poller). Runs every 5 min, polls VPS task-results, feeds each to hermes chat -q for skill extraction. Verified: ran at 15:19:14, found task, Hermes replied in 9s. Files: ~/factory-poller.py (Air), ~/Library/LaunchAgents/com.nous.factory-poller.plist (Air), wiki: pages/tools/factory-poller.py.

4. **Write-back**: Implemented in run_task.py (_write_back_to_wiki()). After every task, writes pages/task-results/YYYY-MM-DD-HH-MM-SS-slug.md to VPS wiki with task, response, model, tokens. Git commits immediately. VERIFIED end-to-end 2026-04-14 15:14 and 15:20. Status: DONE.

## What to do next time

Before saying ANY feature is "done":
1. Run the specific outcome test from Telegram (not from CLI, not from Python)
2. Check the logs — does the response come from the expected component?
3. If you cannot test from Telegram right now, say "I cannot confirm this works end-to-end until tested from Telegram" — do NOT say "done"

**The question is not "did I write the code?" but "does it do what the user needs?"**

## See also
- [[LESSON-083-ready-declaration-without-outcome-test]] — earlier lesson on same pattern
- [[LESSON-082-audit-gaps-telegram-bot-verification]] — two-bot confusion (same root: declaring done without testing the right thing)
- [[HANDOFF-2026-04-14-session13]] — session where this lesson was triggered
