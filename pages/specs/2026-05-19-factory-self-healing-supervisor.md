---
type: spec
id: SPEC-2026-05-19-factory-self-healing-supervisor
title: "Factory self-healing supervisor slice"
date: 2026-05-19
status: specified
owner: codex
tags: [spec-kit, factory, self-healing, telegram, openclaw, launchd, satory]
related:
  - [[MISSION-2026-05-19-always-on-satory-ai-factory]]
  - [[skills/factory-ops]]
---

# Factory Self-Healing Supervisor Slice

## What this deletes / replaces

- Deletes direct `Factory drift` Telegram pages from `factory_no_drift_probe.sh` when a repair supervisor is available.
- Deletes raw `light-probe` state-change pages as the first response to routine infrastructure flaps.
- Does not replace OpenClaw, Hermes canary, Goal Mode, or the Satory queue runner.

## Constitution

- Repair before paging Madi.
- Bounded repair only: no destructive git commands, no force push, no credential mutation, no silent model/default promotion.
- GREEN and auto-repaired failures stay quiet except for logs/status receipts.
- Madi is paged only when the failure is unrepaired or requires credentials, money, legal/business approval, physical access, or destructive approval.
- Every recurring failure class that survives this gate must become a `SKILL.md` rule plus gbrain/OpenBrain receipt.

## Specify

Add a production-safe `tools/factory_self_heal.py` supervisor. It consumes probe JSON from existing checks or runs `factory_no_drift_probe.sh --no-telegram`, classifies RED checks, attempts a small known repair playbook, reruns the probe, writes a JSONL ledger/status page, and only sends Telegram when repair is still not green or Madi is explicitly required.

## Clarify

- This is the first production slice, not the whole always-on mission.
- GPT/Codex, Opus, Grok, RMS, Todoist comments, and 03:00 update cycle remain separate follow-up slices.
- `light-probe.sh` remains a cheap detector, but it delegates alert decisions to this supervisor.

## Plan

- Create `tools/factory_self_heal.py` with pure helpers for classification, repair, rerun, notification dedupe, and status rendering.
- Add tests for quiet-green, repair-then-silent, unresolved notify-once, and shell delegation.
- Patch `factory_no_drift_probe.sh` to delegate RED notifications to the supervisor.
- Patch `light-probe.sh` to delegate state-change notifications to the supervisor.
- Update `factory-ops` with the durable rule.

## Tasks

- [ ] Add the supervisor and unit tests.
- [ ] Patch drift/light probes to delegate alerting.
- [ ] Run local tests and shell syntax checks.
- [ ] Deploy to Air runtime through wiki sync/copy and run dry-run/live proof.
- [ ] Commit and sync Mac/Air/VPS/GitHub.

## Implement

Implementation starts after this spec. Acceptance for this slice: a simulated RED becomes either repaired without Telegram or unresolved with a single deduped escalation; no direct raw `Factory drift` page is sent when supervisor exists.
