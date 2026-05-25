---
title: "Agent Harness Ownership"
date: 2026-04-12
type: concept
status: decided
related:
  - "[[nous-ai]]"
  - "[[openclaw]]"
  - "[[gbrain-garrytan]]"
  - "[[skills-not-agents]]"
---

# Agent Harness Ownership — Memory IS the Harness

## The Principle

If your memory dies when your harness dies, you built the harness too thick. Memory is markdown. Skills are markdown. Brain is a git repo. The harness is a thin conductor — it reads the files, it doesn't own them.

## Why This Matters for AGaaS

Nous AGaaS stores ALL knowledge in:
- **Obsidian vault** (250+ markdown pages, git-synced, human-readable)
- **GBrain** (Postgres + pgvector, syncs from Obsidian every 5 min)

The harness (OpenClaw / Claude Code / any future tool) is REPLACEABLE. The brain is NOT. If OpenClaw dies tomorrow, the vault and GBrain remain. A new harness reads the same files and continues.

## Open vs Closed Harnesses

| Feature | Open (OpenClaw, Deep Agents, OpenCode) | Closed (Claude Agent SDK, OpenAI Codex) |
|---------|-------|--------|
| Memory ownership | You own it (files, git) | Provider owns it (server-side) |
| Model switching | Config change | Locked to provider |
| Memory portability | Copy files | Export API (if exists) |
| Transparency | Read the code | Black box |
| Lock-in | None | High |

## Nous AGaaS Position

We use BOTH open and closed:
- **OpenClaw** (open) — gateway, skills, crons
- **Claude Agent SDK** (closed) — sandboxed workers for task execution
- **Obsidian + GBrain** (open) — the BRAIN, where all knowledge lives

This is fine because knowledge lives in the open layer. Workers are disposable. If Anthropic changes pricing or terms, we swap workers to GLM-5.1 or Qwen 3. Zero knowledge lost.

## Source

Harrison Chase (LangChain CEO), "Agent Harnesses and Memory Ownership" blog post, April 2026. Sarah Wooders (Letta CTO), "Memory isn't a plugin, it's the harness." Garry Tan, GBrain README: "If your memory dies when your harness dies, you built the harness too thick."
