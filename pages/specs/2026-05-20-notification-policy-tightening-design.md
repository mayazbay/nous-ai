---
type: spec
id: SPEC-2026-05-20-notification-policy-tightening
title: "Notification Policy Tightening — iPad-only mode, ≤5 actionable pings/day"
date: 2026-05-20
status: draft
owner: claude-sonnet-4-6
priority: p0-today
tags: [notification, policy, telegram, ipad, musk-algorithm, factory, self-heal, morning-brief, digest]
related:
  - [[MISSION-2026-05-19-always-on-satory-ai-factory]]
  - [[SPEC-2026-05-19-nous-operating-loop-design]]
  - [[session-operating-contract]]
  - [[musk-algorithm]]
  - [[factory-self-healing-supervisor]]
---

# Notification Policy Tightening — iPad-only mode, ≤5 actionable pings/day

## Constitution (step 1)

Madi verbatim directive (MISSION-2026-05-19-always-on-satory-ai-factory, compressed timeline 2026-05-20):

> "GREEN = no message to Madi. Repaired YELLOW/RED = daily compact digest only.
> Unrepaired after retries = ping with exact decision. Credential/login = ping with exact link."

Current pain: Madi receives 12+ Telegram messages per day from the factory
(control-plane sync, AMD-003 sync, morning heartbeat, morning update, goal cycle, factory
drift, supervisor escalation, factory-self-heal pings). iPad-only mode requires ≤5
actionable pings per day to stay operational without laptop.

This spec locks in the three-category policy, impl module, and wiring proof.

## Specify (step 2) — three notification categories

### SUPPRESS (zero ping — ledger only)

All routine cron output that is not a human decision point. Output goes to
`logs/*.jsonl` ledger; never Telegram.

| Event name | Current caller | Trigger condition |
|---|---|---|
| `auto-checkpoint` | auto_checkpoint.py (launchd 8×/day) | Every smart-skip or successful checkpoint |
| `queue-timestamp` | satory_ai_factory_queue.py | Every queue checkpoint |
| `goal-cycle` | goal_runner.py (launchd) | Every goal cycle tick, including GREEN |
| `amd003-sync` | control_plane_sync_loop.py | Every AMD-003 sync run |
| `control-plane-sync` | control_plane_sync_loop.py | Every successful sync |
| `openbrain-projection` | openbrain_project_to_wiki.py (launchd) | Every successful projection |
| `gbrain-doctor` | morning-brief.sh / gbrain_enrich.py | Every successful doctor run |
| `telegram-poll-cycle` | telegram_poll.py | Every successful poll cycle |
| `wiki-sync` | wiki-sync-launch.sh (launchd) | Every successful sync |
| `auto-sync-commit` | session_safe_sync.sh | Every auto-commit with no human change |
| `heartbeat-green` | morning-brief.sh, session_heartbeat.sh | Morning heartbeat when all GREEN |
| `morning-update-ok` | morning-update-apply.sh | Successful auto-update applied |
| `factory-probe-green` | factory_no_drift_probe.sh | Every GREEN probe run |
| `docker-prune-ok` | docker_prune_daily.sh | Successful prune |
| `docker-audit-ok` | docker_image_audit_weekly.sh | No new images found |

### DIGEST (compact 1×/day at 09:00 KZT alongside morning brief)

Accumulated in `pages/systems/notification-digest-queue.jsonl`.
Flushed and sent as single compact message by `morning-brief.sh` calling
`notification_policy.flush_daily_digest()`.

| Event name | What to include in digest |
|---|---|
| `yellow-autorepaired` | YELLOW events that auto-repaired (count + names) |
| `version-update-applied` | Version updates auto-applied (pkg + version) |
| `red-green-flip` | RED→GREEN flips (check name + duration) |
| `factory-probe-summary` | Daily factory probe summary (GREEN count vs total) |
| `gbrain-pages-delta` | gbrain pages count delta vs yesterday |
| `openbrain-capture-delta` | OpenBrain capture count delta vs yesterday |
| `cost-daily-summary` | Daily LiteLLM cost (if under alarm threshold) |

### IMMEDIATE (real-time ping — no delay)

These fire immediately via `tg_send.sh`. Must carry exact decision or link.

| Event name | Trigger condition | Required message content |
|---|---|---|
| `credential-needed` | Login/auth required for any service | Exact service URL + what credential needed |
| `supervisor-escalation` | 2+ failed auto-repairs on same check | Exact check name + last 3 repair attempts |
| `red-at-canary-gate` | Unresolved RED at canary promotion gate | Exact failing gate + canary diff link |
| `budget-cap-reached` | LiteLLM cost alarm triggered | Current spend + cap + exact stop command |
| `madi-decision-required` | Merge conflict, destructive action, ambiguous signal | Exact binary choice with recommended option |
| `security-incident` | AP-39 credential leak attempt or auth anomaly | Exact incident type + affected service |

## Clarify (step 3 — open questions, default-yes recommendations)

1. **morning-brief heartbeat when GREEN?** Currently morning-brief.sh always sends a Telegram
   message (GREEN heartbeat or RED alert). Recommend: suppress GREEN heartbeat entirely; only
   send if FAILS>0. The digest at 09:00 KZT covers the delta summary. Default: **suppress GREEN**.

2. **Cost-daily-summary: DIGEST or SUPPRESS?** If cost is under alarm threshold it's info-only.
   Recommend: **DIGEST** (included in morning digest as one line "Cost yesterday: $X.XX").
   Only if cost > threshold does it become IMMEDIATE.

3. **human-owner-reminder frequency?** Currently launchd fires periodically. If no task is
   pending for Madi, fire is noise. Recommend: gate on `HUMAN_REQUIRED` items in factory state;
   if none, SUPPRESS. Default: **gate it**.

4. **factory-probe-summary in DIGEST?** Probe runs continuously. Sending every run is noise.
   A once-per-day probe summary (passed/total) is useful. Default: **DIGEST**.

## Musk delete/reduce (step 4)

What this spec DELETES entirely (not gates, not digests — removes the ping):

- **Control-plane-sync routine success ping** — ~3 pings/day gone
- **AMD-003 sync success ping** — ~2 pings/day gone
- **Morning heartbeat when GREEN** — 1 ping/day gone
- **Goal-cycle tick pings** — ~2 pings/day gone
- **Auto-checkpoint mirror confirmations** — ~8 pings/day gone
- **Queue timestamp pings** — ~1 ping/day gone
- **Wiki-sync success ping** — ~1 ping/day gone
- **OpenBrain projection pings** — ~1 ping/day gone
- **gbrain doctor success pings** — ~1 ping/day gone

Net: ~20 routine pings/day removed. Replaced with:
- 1 morning digest at 09:00 KZT (aggregated YELLOW/delta/flips)
- ≤3 IMMEDIATE pings/day (only on true human-required events)

delete-considered: ALL routine cron-output notifications — replaced with ledger-only OR daily digest

## Plan (step 5)

### Architecture

```
tools/notification_policy.py          ← NEW — central policy module
  EVENT_CLASS_REGISTRY                   maps event name → SUPPRESS/DIGEST/IMMEDIATE
  should_ping(event_class, severity,     gate function for all callers
              dedup_key=None) -> bool
  flush_daily_digest() -> str|None       called by morning-brief.sh at 09:00 KZT

pages/systems/notification-digest-queue.jsonl  ← NEW — accumulates DIGEST events

tools/factory_self_heal.py             ← WIRE — wrap send_notification with should_ping
tools/morning-brief.sh                 ← WIRE — call flush_daily_digest, suppress GREEN heartbeat

tools/tests/test_notification_policy.py  ← NEW — 7 tests, all mocked
```

### Data flow

```
Cron / launchd fires any tool
  → tool calls should_ping(event_class, severity, dedup_key)
    → SUPPRESS → return False → tool writes to ledger only
    → DIGEST   → append to digest-queue.jsonl → return False
    → IMMEDIATE → check dedup (4h TTL) → return True → tool calls tg_send.sh
  → 09:00 KZT morning-brief.sh calls flush_daily_digest()
    → reads digest-queue.jsonl → builds compact text → calls tg_send.sh → clears queue
```

### Dedup

In-memory dict + on-disk `pages/systems/notification-dedup.json` (LRU keyed on
`dedup_key`, 4h TTL). Matches factory_self_heal's existing 4h TTL pattern.

### Rollback path

`notification_policy.py` is an opt-in gate. Existing callers without the gate
continue to fire as before. Rollback = remove the `should_ping()` call from
factory_self_heal.py (1-line change). No launchd changes required.

## Tasks (step 6)

- [x] T1 — Audit notification surfaces (grep tg_send, catalog callers)
- [x] T2 — Write this spec
- [x] T3 — Impl `tools/notification_policy.py` (~80 lines)
- [x] T4 — Tests `tools/tests/test_notification_policy.py` (7 tests, all mocked)
- [x] T5 — Wire into `tools/factory_self_heal.py` (gate send_notification)

Deferred (post-canary):
- T6 — Wire `morning-brief.sh` flush + suppress GREEN heartbeat
- T7 — Wire `control_plane_sync_loop.py`
- T8 — Wire `daily_evolution_runner.py`
- T9 — Wire `goal_runner.py`

## Canary (step 7)

Wire to factory_self_heal.py ONLY. Run existing factory_self_heal tests. Observe
1 day of real launchd runs via ledger before expanding to other callers.

Canary gate: `pytest tools/tests/test_factory_self_heal.py tools/tests/test_notification_policy.py -q`
must exit 0. factory_no_drift_probe.sh --quiet must be GREEN.

## Acceptance (step 8 — proof criteria)

- Pytest count ≥ 7 new tests in test_notification_policy.py, all PASS
- Existing test_factory_self_heal.py (5 tests) still PASS (no regression)
- `notification_policy.should_ping("auto-checkpoint", "info")` returns False
- `notification_policy.should_ping("supervisor-escalation", "critical")` returns True
- `notification_policy.should_ping("yellow-autorepaired", "warn")` returns False AND
  appends 1 line to digest-queue.jsonl
- `notification_policy.flush_daily_digest()` on non-empty queue returns non-None string
- `notification_policy.flush_daily_digest()` on empty queue returns None
- Over 24h canary: Madi receives ≤5 Telegram pings from factory sources

## See also

- [[MISSION-2026-05-19-always-on-satory-ai-factory]]
- [[SPEC-2026-05-19-nous-operating-loop-design]]
- [[factory-self-healing-supervisor]]
- [[musk-algorithm]] v1.4.0

---

- **2026-05-20** | Spec written, T1 audit complete, T3-T5 impl shipped — Session-Id: agent-notification-policy-2026-05-20-T290
