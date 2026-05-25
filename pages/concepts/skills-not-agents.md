---
title: "Skills, Not Agents"
date: 2026-04-12
type: concept
status: decided
related:
  - "[[nous-ai]]"
  - "[[openclaw]]"
  - "[[gbrain-garrytan]]"
  - "[[LESSON-079-one-agent-not-sixteen]]"
  - "[[LESSON-080-design-without-deployment]]"
  - "[[hybrid-model-routing]]"
---

# Skills, Not Agents — Why Depth Beats Width

## The Principle

When a task is hard, add a SKILL.md file, not another agent. When a task recurs, put the skill on a cron. Intelligence compounds in skills (persistent, improving), not in agent context windows (ephemeral, lossy).

## Evidence

### Academic (EvoClaw benchmark, arXiv 2603.13428)
- Isolated agent tasks: >80% success
- **Multi-agent continuous coordination: 13.37% success**
- This single number explains all 4 Nous AGaaS factory failures

### Empirical (Nous AGaaS, 4 attempts Nov 2025–Mar 2026)
- Attempt 1: 4 agents → 97 tasks, 30 commits ALL reverted
- Attempt 2: 6 agents → never operationalized
- Attempt 3: 9 agents → 449 messages of design, NEVER RAN
- Attempt 4: 5 agents → self-audited, 6 critical flaws

### Production (Garry Tan / Y Combinator)
- ONE OpenClaw agent + SKILL.md files + GBrain (10K+ files)
- Running for months, compounding
- "If I have to ask twice, you failed. The first time is discovery. The second time means you should have already turned it into a skill on a cron."

## The Pattern

| Instead of... | Do this... |
|--------------|-----------|
| Add a Validator agent | Add pytest + diff checks (code, not AI) |
| Add a Researcher agent | Add a GBrain search skill |
| Add a Frontend agent | Add a frontend SKILL.md with component patterns |
| Add a DevOps agent | Add a deploy SKILL.md with pre/post checks |
| Add a CMO agent | Add a competitor-watch skill on weekly cron |

## MECE Skills (Mutually Exclusive, Collectively Exhaustive)

Every type of work has exactly ONE owner skill. No overlap, no gaps. Before creating a new skill, check if an existing one covers it. If so, extend it.

## Skills Lifecycle (Garry Tan's Cycle)

1. **Concept** — describe the process
2. **Prototype** — run on 3-10 real items, no skill file yet
3. **Evaluate** — review output with Madi, revise
4. **Codify** — write SKILL.md (or extend existing)
5. **Cron** — schedule if recurring
6. **Monitor** — check first runs, iterate

## The Compound Effect

Each completed task potentially produces a reusable skill. After 100 tasks, you have 30-50 skills covering most of your work surface. After 1,000 tasks, the factory handles 90%+ of routine work autonomously. This is how one human + agents scales to multiple clients.
