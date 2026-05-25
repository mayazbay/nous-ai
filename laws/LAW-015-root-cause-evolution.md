---
type: law
id: LAW-015
title: "Every mistake must have root cause + fix + learning"
status: permanent
enforcement: process
tags: [evolution, root-cause, learning, mandatory]
related: [LAW-001, LAW-009, LAW-013]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-015: EVERY MISTAKE = ROOT CAUSE + FIX + LEARNING

## The Law
When ANYTHING goes wrong — for ANY agent, including Claude Code — the lesson MUST contain:

1. **WHAT HAPPENED** — the exact symptom, not vague description
2. **ROOT CAUSE** — WHY it happened. Ask "why" 5 times. Not the symptom, the CAUSE.
3. **HOW WE FIXED IT** — exact code change, file, line number
4. **HOW WE CAME UP WITH THE FIX** — the reasoning, so others can solve similar problems
5. **WHAT EVERYONE LEARNS** — the general principle, not just this specific case

## What is NOT acceptable
- "Fixed the bug" — WHERE? HOW? WHY did it happen?
- "Task failed" — WHY? What was the root cause?
- Just listing mistakes without analysis
- Saving symptoms without causes

## Template for every lesson

### What happened
[exact symptom with task ID, file name, error message]

### Root cause
[WHY it happened — trace back to the real cause]

### How we fixed it
[exact change — file, line, what was changed]

### How we came up with the fix
[the reasoning — what led us to this solution]

### What everyone learns
[general principle that applies beyond this one case]

## Applies to
- CEO, Coder, Validator, Researcher — ALL factory agents
- Claude Code (me) — every session
- Watchdog — crash diagnosis reports
- Every error lesson in store_error_lesson()

## Why
This is HOW the team evolves. Mistakes without root cause analysis are wasted pain.
Same mistake never twice is LAW-001 rule 3. But you cant prevent a mistake you dont understand.

## See also
- [[LAW-001-evolution|LAW-001]]
- [[LAW-009-self-evolution|LAW-009]]
- [[LAW-013-truth|LAW-013]]
