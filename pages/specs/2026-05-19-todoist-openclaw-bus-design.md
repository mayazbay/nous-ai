---
type: spec
id: SPEC-2026-05-19-todoist-openclaw-bus-design
title: "Todoist to OpenClaw event bus design"
date: 2026-05-19
status: active
owner: codex
tags: [spec-kit, todoist, openclaw, satory, factory, gpt, hermes, gbrain, openbrain]
related:
  - [[PLAN-ADDENDUM-2026-05-19-todoist-openclaw-substrate-beam-musk-doctrine]]
  - [[skills/todoist-control-plane]]
  - [[skills/ceo-hierarchy]]
---

# Todoist to OpenClaw event bus design

## What this deletes / replaces

- Replaces the dead-letter pattern where `ready_for_ai_factory` is only an audit route and no runner consumes it.
- Replaces repeated generic daily Todoist comments as the primary operator loop.
- Does not delete one-off Todoist migration tools in this slice; those require a separate delete-first audit with receipt checks.

## Constitution

- Scope is only `Фабрика Satory ВКО` unless Madi names another project.
- OpenClaw is the production worker runtime; Hermes remains canary-only.
- GPT/Codex is mandatory for external operator proof and top-tier CTO/CEO routes.
- Every automated task slice must leave proof in Todoist and the vault.
- No fake proof, no task closure without human-checkable evidence.

## Specify

Build a queue runner that turns Satory Todoist audit rows into executable factory events. It must consume AI-owned `ready_for_ai_factory` tasks even when no human wrote `AI:`. It must keep BDL/APK/ERAP first, prevent duplicate execution via a ledger, and write a Russian task comment describing route, status, proof path, and next step.

## Clarify

- Use the existing Todoist Sync API read model and deep audit output as the source of truth.
- Use `tools/run_task.py` as the worker dispatch interface where available.
- In local dry-run/tests, never call Todoist or OpenClaw.
- The first production launchd job should be canary-safe: low limit, idempotent ledger, no task completion.

## Plan

- Extend `tools/satory_todoist_deep_audit.py` with execution metadata fields.
- Add `tools/satory_ai_factory_queue.py` to select queue rows, dispatch bounded factory slices, and write a durable ledger.
- Add launchd plist for periodic canary execution on Air.
- Add regression tests for queue selection, idempotence, priority, and non-closure.

## Tasks

- [ ] Add audit metadata fields: `execution_state`, `queue_reason`, `delete_candidate_reason`, `human_digest_eligible`, `latest_human_signal`, `next_action_compact`.
- [ ] Add queue runner CLI with `--apply`, `--limit`, `--project`, `--priority`, and `--json`.
- [ ] Add ledger at `pages/systems/satory-ai-factory-queue-ledger.json`.
- [ ] Add Todoist comment writeback only after a slice is attempted.
- [ ] Add tests and proof artifact.

## Implement

- 2026-05-19: Spec opened before implementation per Spec-Kit/cognitive-debt guard.
