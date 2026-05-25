---
type: skill
id: openclaw-probe-isolation
title: "OpenClaw probe isolation — never leak worker sentinels to users"
version: 1.0.0
date: 2026-05-20
last_updated: 2026-05-20
status: active
tier: 2
tags: [skill, openclaw, probe, isolation, sentinel, telegram, customer-facing]
related:
  - "[[model-failover]]"
  - "[[lane-lock]]"
  - "[[mistake-to-skill]]"
  - "[[ceo-hierarchy]]"
  - "[[session-operating-contract]]"
---

# openclaw-probe-isolation v1.0.0

## Why this exists

2026-05-20 18:57 and 18:58 KZT — customer `@aliakbar_asylbek` asked two real questions in a Telegram group: "Закинь сюда фото подтверждение" and "Напиши последний распознанный государственный номерной знак". Both got the literal string `OPENCLAW_518_WORKER_OK` as a reply.

Root cause: a worker-health probe with prompt "Reply exactly OPENCLAW_518_WORKER_OK" was sent through the SAME `run_task.py` → OpenClaw entry point as user `/ask` traffic. The agent obeyed the probe's instruction. The factory cached / surfaced that sentinel into the customer's response stream.

Two task-result artifacts prove it:
- `pages/task-results/2026-05-20-18-57-10-reply-exactly-openclaw-518-worker-ok.md`
- `pages/task-results/2026-05-20-18-58-23-reply-exactly-openclaw-518-worker-ok.md`

The sentinel embarrasses Nous AGaaS in front of a paying customer. It must never reach a Telegram user again.

## Current rules

- Probe messages MUST be tagged with an in-payload header `__PROBE_ONLY__` so the factory dispatcher can route them to a probe-only queue, NOT the same queue as user `/ask`.
- The boundary functions `_run_openclaw()` and `_tg_send()` in `tools/command_center.py` BOTH filter for the sentinel regex `^\s*OPENCLAW_\d+_WORKER_OK\s*$` and replace with a graceful Russian/English fallback message before any Telegram send. Defense in depth: two independent layers.
- Every sentinel-block event is logged at ERROR level and appended to `pages/skills/mistake-to-skill/ledger.jsonl` with `kind="probe_sentinel_leaked"` for the weekly digest absorption.
- Probe-issuing code (factory_self_heal, light_probe, staleness checks, etc.) MUST set a routing hint env var or pass `--probe` to `run_task.py` so the factory can verify the message is a probe before dispatching.
- `_tg_send()` is the LAST line of defense. Any sentinel that reaches it is a routing bug that requires a follow-up commit codifying a new AP here.

## Anti-Patterns

**AP-1: Probe and user traffic share an entrypoint.** `_run_openclaw()` was the single shared path. The fix is regex filtering AT the boundary, plus eventually a separate `_run_openclaw_probe()` for health calls. Until that separation exists, AP-1 enforcement is the regex guard.

**AP-2: Probe payloads carry the same shape as user payloads.** A probe instructing "Reply exactly OPENCLAW_518_WORKER_OK" looks identical to a legitimate user prompt. The fix is a `__PROBE_ONLY__` header at line 0 of the payload, OR an explicit `is_probe=true` envelope field. Code that issues probes MUST attach this marker.

**AP-3: Reuse `run_task.py` entry for probe + user without disambiguation.** The async-await shim in `run_task.py:291-839` polls session JSONL for text — under load this could surface a probe's response for a user's correlation_id if session pinning fails. The fix is `correlation_id` filtering inside the shim (already in code per SPEC-MULTI-MODEL-CEO-HIERARCHY-V1 Phase 3), but probes need their OWN correlation_id namespace (e.g., `probe_<seq>_<ts>` distinct from `tg_<msg_id>`).

**AP-4: Sentinel responses (`^OPENCLAW_\d+_WORKER_OK$`) reach `_tg_send`.** Boundary regex filter blocks this. The fallback message is `OPENCLAW_SENTINEL_FALLBACK_REPLY` at `tools/command_center.py:153`. If a NEW caller bypasses `_run_openclaw` and calls `_tg_send` directly with a sentinel, AP-4 catches it at line 381.

**AP-5: Forget to log the leak.** When a sentinel IS detected at any boundary, `_log_probe_sentinel_leak()` writes to stderr + appends to `pages/skills/mistake-to-skill/ledger.jsonl`. The weekly `dream_cycle.py` digest (Ship 1) absorbs these into version bumps of this skill. Never silently drop without a ledger entry.

## Timeline

- 2026-05-20 v1.0.0 — Created in response to the Assylbek incident. Boundary guards landed in `tools/command_center.py` at lines 152-153 (constants), 381 (`_tg_send`), 984+1045 (`_run_openclaw`). Mistake-to-skill ledger wired via `_log_probe_sentinel_leak`.

## See also

- `[[model-failover]]` v1.0.0 — Ship 1; uses the same `_run_openclaw` entry; this AP layer protects its user-facing path too.
- `[[lane-lock]]` v1.0.0 — Ship 2; lane-aware commit discipline catches RULE 7 violations including probe-vs-user file overlap.
- `[[mistake-to-skill]]` — 7-day SLA absorption; every leak event lands here.
- `[[ceo-hierarchy]]` — multi-model routing; probes should target a separate `probe-only` lane in future versions.
- `[[session-operating-contract]]` — 4-artifact DONE protocol; sentinel-block events MUST include the 4 artifacts when reported in a session-close summary.
