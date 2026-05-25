---
type: spec
id: SPEC-2026-05-19-single-beam-substrate-bus-design
title: "Single-beam substrate bus design"
date: 2026-05-19
status: specified-not-implemented
owner: codex
tags: [spec-kit, substrate, gbrain, openbrain, obsidian, notion, todoist, gstack]
related:
  - [[PLAN-ADDENDUM-2026-05-19-todoist-openclaw-substrate-beam-musk-doctrine]]
---

# Single-beam substrate bus design

## What this deletes / replaces

- Replaces parallel sync claims that report each subsystem separately but do not prove fan-out.
- Does not add a fourth competing sync daemon in this slice.
- Existing `control_plane_sync_loop.py` and `todoist_sync.py` should be folded into the bus before any new broad daemon is promoted.

## Constitution

- Obsidian/vault remains the durable human-readable source.
- gbrain and OpenBrain are retrieval/projection surfaces, not competing sources of truth.
- Every fan-out event carries a chain ID and must be loop-safe.
- No substrate can claim green if it skipped preflight and no later proof repaired it.

## Specify

Design a normalized substrate event bus that records source mutations and fans them out to the right durable surfaces: gbrain timeline, OpenBrain capture/projection, Obsidian sync log, Notion row, Todoist comment, and Git audit.

## Clarify

- GStack meaning remains ambiguous; in this spec it means the installed gstack skill/runtime layer until Madi defines a separate system.
- This slice only specifies the bus and records the interface; full fan-out implementation follows after the Todoist/OpenClaw queue spine is green.

## Plan

- Define one JSONL event shape with `event_id`, `source`, `target_slug`, `summary`, `evidence_path`, `actor`, `timestamp`, and `propagation_chain`.
- Add loop prevention and idempotence keys.
- Make current control-plane sync and Todoist sync consumers/producers of the bus in a later implementation slice.

## Tasks

- [ ] Inventory existing sync producers and consumers.
- [ ] Define the JSONL schema and fixture tests.
- [ ] Wire SKILL.md bump events to gbrain/OpenBrain fan-out.
- [ ] Wire Todoist events to gbrain timeline.
- [ ] Add loop-prevention test.

## Implement

- 2026-05-19: Spec opened before implementation. Implementation intentionally deferred behind Layer 1 queue proof.
