---
type: law
id: LAW-008
title: "Anti-Hallucination — Evidence Chain"
status: permanent
enforcement: code-gate
tags: [hallucination, evidence, verification, coder, banned-patterns]
related: [LAW-003, LAW-013]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-008: ANTI-HALLUCINATION — EVIDENCE CHAIN
Status: PERMANENT
Enforcement: HARD BLOCK in graph.py coder_node. 12 hallucination patterns checked BEFORE commit.
Updated: 2026-04-06

## The Law
Every claim must have evidence. Every number must have a source.

## Rules
- Before reporting ANY number → verify against DB or API
- Before claiming "done" → show curl output or screenshot
- Before using a fact → check wiki or grep codebase
- If unsure → say "I dont know" not make something up
- Research BEFORE guessing. Always.

## Examples of violations
- Said "955 LU cameras" — was 109 (counted Excel rows not unique IDs)
- Said "89% complete" — was 78% (claimed before auditing)
- Said "everything works" — 6 pages had hardcoded data
- Said camera model was wrong — it was correct (from ISAPI response)

## Evidence chain
1. Where does this number come from? (DB query, API response, file)
2. When was it last verified? (timestamp)
3. Can someone else reproduce it? (command to run)

If you cant answer all 3 → dont report the number.

## See also
- [[cameras|Camera Network]]
- [[LAW-003-continuous-audit|LAW-003]]
- [[LAW-013-truth|LAW-013]]
