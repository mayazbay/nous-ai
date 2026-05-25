---
type: law
id: LAW-001
title: "The Evolution Law"
status: permanent
enforcement: code-gate
tags: [wiki, mem0, root-cause, evolution, mandatory]
related: [LAW-005, LAW-008, LAW-009]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-001: THE EVOLUTION LAW
Status: PERMANENT. NEVER BYPASS.
Enforcement: Code gate in graph.py (wiki must exist >1KB before cycle starts)
Updated: 2026-04-06

## The 7 Rules

1. **OBSIDIAN WIKI = MANDATORY** — every agent reads wiki BEFORE starting any work. Every agent writes to wiki AFTER completing work or encountering errors. No agent works without consulting wiki first. This prevents hallucination.

2. **ROOT CAUSE on every mistake** — STOP → find ROOT CAUSE → not the symptom. Ask "why" 5 times. Document: what, why, how to prevent.

3. **SAME MISTAKE NEVER TWICE** — After root cause → write lesson to wiki. Validator checks: if Coder violates a stored lesson → auto-FAIL. Same mistake again → escalate to CEO.

4. **CEO SEES EVERY PROBLEM** — Agent pings CEO with problem. CEO delegates to specialist. CEO does NOT fix himself.

5. **RESEARCH → LEARN → EVOLVE** — Unknowns → Researcher investigates → findings go to wiki → ALL agents learn.

6. **EVERY AGENT HAS SPECIAL ABILITIES — USE THEM**
   - CEO (Opus): strategic decisions, task creation, quality control
   - Coder (Sonnet): code writing, implementation
   - Validator (Gemini Pro): code review, lesson enforcement
   - Researcher (Gemini Flash): investigation, analysis
   - Telegram (Sonnet): team communication in Russian

7. **CONTINUOUS EVOLUTION** — Agents get BETTER every cycle. Wiki grows with real lessons. Weekly cleanup removes stale data.

## Why this law exists
Factory looped 75 cycles wasting $40+ because agents didnt read wiki which already had the answer. Same mistakes repeated 14 times. Knowledge existed but nobody used it.

## Code enforcement
- graph.py: `_ceo_context()` reads all wiki files at cycle start
- Required: assert wiki directory has >5 files before cycle proceeds

## See also
- [[LAW-005-obsidian-master|LAW-005]]
- [[LAW-008-anti-hallucination|LAW-008]]
- [[LAW-009-self-evolution|LAW-009]]
