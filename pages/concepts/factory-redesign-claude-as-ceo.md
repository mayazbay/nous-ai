---
type: concept
id: CONCEPT-FACTORY-REDESIGN
title: "Factory redesign proposal: Claude Code as CEO, Sonnet CTO, Gemini everything else"
tags: [concept, factory, architecture, proposal, cost, autonomy]
date: 2026-04-07
related: [AUDIT-020, AUDIT-021, LESSON-054, CONCEPT-VAULT-MODEL]
status: proposal
last_updated: 2026-04-07
source_count: 1
---
# Factory Redesign — Claude Code as CEO

## Madi's proposal (2026-04-07 evening)
> "If you replace the CEO, everything else I think will work. The CEO right now, I think, is the dumb version. If you become the CEO and then you have the CTO as a sonnet, and everything else is done by Gemini, I think we will work. What do you think about that? I need to make it as autonomous as possible."

## Honest answer: YES, but with a caveat that changes the design.

The instinct is correct. The current factory CEO is **Opus 4.6 one-shot** with a rigid prompt template, no memory between cycles beyond what's in the wiki, no tool-use loop, no self-correction. That's the "dumb version" Madi is identifying.

**Claude Code as CEO** would be a qualitatively different thing: a full agentic loop with file I/O, bash, long-running thinking, memory across turns, and the ability to actually read + understand + act on the wiki. It would be 10x more capable than the current one-shot Opus call.

**But there is a catch that breaks the design as proposed.** Read on.

## Current architecture
```
CEO (Opus 4.6 one-shot)  →  Coder (Sonnet one-shot)  →  Test  →  Validator (Gemini)  →  Deploy
```
- CEO: $1/task average (~1k in, ~500 out)
- Coder: $0.70/task (~5k in, ~2k out)
- Validator: $0.30/task (Gemini 2.5 Pro)
- Test + Deploy: $0
- **Total: ~$2.00/task**, observed ~$2.30/task in practice

## Proposed architecture
```
CEO (Claude Code agentic loop)  →  Coder (Sonnet one-shot)  →  Test  →  Validator (Gemini)  →  Deploy
```

## Why it CAN work
1. **Better task selection.** Current CEO blindly reads specs and spits out 3 JSON tasks. An agentic CEO can read the wiki, check git history, look at what's currently broken in prod, prioritize based on the business context (e.g. "we're about to ship ERAP, frontend polish is lower priority than fixing the PATCH bug"), and pick tasks that matter.
2. **Self-correction.** Current CEO has no idea if the tasks it created last cycle succeeded or failed. An agentic CEO can read `logs/`, see failures, generate a lesson, and avoid the same class of task next cycle.
3. **Lesson learning.** An agentic CEO can READ the existing LESSON-xxx files before every cycle and actively apply them. The current prompt just dumps a laws blob and hopes.
4. **Human-in-the-loop integration.** Agentic CEO can READ Madi's Telegram messages via `getUpdates` and respond with "what should I prioritize today?" — this is the autonomy Madi wants.

## Why it CAN'T work as stated (the catch)
**Claude Code is an interactive tool, not an unattended service.** It's designed to run in a terminal with a human in the loop. There is no "Claude Code daemon" that runs in a systemd service on the VPS and spawns every 5 minutes. The Claude Code binary expects:
- A TTY
- A user typing
- stdin/stdout streaming
- Browser for auth refresh in some cases

So the LITERAL proposal — replace the current CEO call with a `claude-code` invocation in graph.py — doesn't work out of the box. The binary will either hang waiting for input or fail without a TTY.

## Three realistic ways to get the SPIRIT of Madi's proposal working

### Option A: Claude Code SDK via the Anthropic API (possible today)
Anthropic's own `anthropic` Python SDK supports tool use with a loop. We write a CEO that:
1. Uses Claude Opus 4.6 via API
2. Has tools: `read_file`, `grep_wiki`, `list_pending_tasks`, `read_telegram_inbox`, `create_task`, `read_logs`, `lint_wiki`
3. Runs in a loop: "think → call tool → observe → think → call tool → ... → done"
4. Stops after N tool calls or when it says "I have a plan"

**Cost:** higher per cycle (~$2-5 for the CEO alone, because agentic loops use more tokens). **Quality:** dramatically higher. **Build effort:** 4-8 hours.

This is the RIGHT answer if we want autonomy.

### Option B: Cheap-CEO mode (Sonnet 4.6 or Haiku 4.5)
Drop Opus entirely for the CEO slot. Sonnet 4.6 costs ~$3/M input vs Opus ~$15/M input — 5x cheaper with 80% of the quality for structured tasks like "pick a task from the queue." Haiku 4.5 is another 5x cheaper for true one-shot prompts.

**Cost:** ~$0.20/task instead of $1. **Quality:** slightly lower on ambiguous decisions. **Build effort:** 10 minutes (change `config.py::MODELS["ceo"]`). Requires removing the hard gate that says CEO MUST be Opus.

This is the RIGHT answer if we want lower cost NOW and architectural changes later.

### Option C: Hybrid — Sonnet CEO for routine, Claude Code SDK for hard decisions
Default CEO is Sonnet 4.6 cheap one-shot. But when a cycle hits 3 consecutive failures OR the queue is empty OR a new source doc appears in `raw/pending/`, escalate to a full Claude Code SDK agentic loop for one "thinking" cycle that creates a plan, writes lessons, and seeds new tasks.

**Cost:** ~$0.30/task baseline + ~$3 every 20 cycles for thinking. **Quality:** adaptive. **Build effort:** 8-12 hours.

This is the RIGHT answer if we want to be truly clever. Also the most fragile.

## What I recommend
**Option B first, then Option A.**

Start with the 10-minute change: drop CEO to Sonnet, verify cost drops from $2.30 to ~$1.40 per task, run for 1 week, confirm quality is still acceptable. Then, when we have headroom and the April ship is done, invest 4-8 hours in Option A (agentic CEO via SDK).

Do NOT try to jump straight to Option A this week. We have more pressing work (ERAP ship).

## Subtopic: Madi mentioned MemPalace, OpenClaw, Karpathy memory

### MemPalace (milla-jovovich/mempalace)
Local memory system for LLMs. Claims 100% on LongMemEval benchmark, 92.9% ConvoMem. MIT license. Runs locally (no cloud).

**Our fit:** LOW for the factory itself. MemPalace is designed for conversation memory (chat with an LLM over months, have it remember your family, preferences, contradictions). Our factory's memory need is different: it's structured task state (what's in progress, what failed, what deployed) + the wiki (structured facts about Satory/Spectra/BDL). We don't have an open-ended conversation problem.

**Our fit:** HIGH for the personal Brain vault. If Madi wants his Brain vault to be queryable by an LLM that remembers his personal context across sessions, MemPalace is worth a look. NOT for Nous work.

### OpenClaw (we already have it)
From `ls /Users/madia/Desktop/nous ai`: `openclaw.py` + `safety/nemoclaw.py` exist. This is our internal safety + action framework. It's wired into `mission_control.py`. Already integrated. No new work.

### Karpathy LLM Wiki
Already implemented. This whole conversation is built on it. AUDIT-016/017/018 are the adoption + bulletproofing. Our current wiki structure IS the Karpathy pattern.

**Conclusion on memory systems:** We're already using the best-fit memory for this project (structured wiki + YAML frontmatter + wikilinks + monthly lint). MemPalace is a nice-to-have for the personal Brain vault, not a game-changer for the factory. Don't get distracted by hype from X.

## Trust rebuild
After today's $15.57 / 40% waste, the factory should:
1. NOT run unattended until Phase 3 ERAP ship is done
2. Run ONLY for small frontend polish tasks when Madi explicitly says "factory go"
3. Have the $15/day cap (applied today)
4. Have the phantom guard + credit lock guard + REQ exhaustion check (all applied today)
5. Eventually move to Option B (Sonnet CEO) after ERAP ships

## Action items
- [ ] Skip factory redesign until ERAP ships (priority 1 = ERAP, not factory)
- [ ] After ERAP ships, implement Option B (10 min work)
- [ ] After ERAP runs for a week, evaluate Option A (4-8h work)
- [ ] Document this decision in Obsidian ✓ (this file)

## See also
- [[AUDIT-020-factory-cost-leak-audit]]
- [[AUDIT-021-strategic-reset-vpn-myth-factory-redesign]]
- [[vault-model-decision]]
- [[LESSON-054-ceo-empty-queue-burns-money]]
