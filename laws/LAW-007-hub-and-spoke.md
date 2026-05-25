---
type: law
id: LAW-007
title: "Hub-and-Spoke — CEO is the Hub"
status: permanent
enforcement: architecture
tags: [ceo, delegation, no-peer-to-peer, graph]
related: ["LAW-004"]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
---
# LAW-007: HUB-AND-SPOKE — CEO IS THE HUB
Status: PERMANENT
Enforcement: Architecture (graph.py node routing)
Updated: 2026-04-06

## The Law
- CEO dispatches ALL tasks. No peer-to-peer between agents.
- Coder does NOT talk to Validator directly — goes through CEO
- Researcher does NOT assign work — reports to CEO
- CEO is the ONLY decision maker

## Rules
- All communication flows: Agent → CEO → Agent
- No agent bypasses CEO
- Claude Code creates ONE directive for CEO, not direct assignments
- CEO breaks down, delegates, tracks

## Why
When agents talked peer-to-peer, tasks got duplicated, conflicts arose, and nobody knew the full picture. CEO must be the single brain coordinating all work.

## See also
- [[LAW-004-5-commandments|LAW-004]]
