---
type: concept
id: CONCEPT-GBRAIN-MINIONS
title: "GBrain Minions — Postgres-native durable job queue for agent orchestration (Tan upstream, v0.11.1+)"
tags: [concept, gbrain, minions, garry-tan, job-queue, postgres, deterministic-work, pending-upgrade, 2026-04-21]
date: 2026-04-21
last_updated: 2026-04-21
status: reviewed
source_count: 4
related:
  - "[[gbrain-ops]]"
  - "[[factory-ops]]"
  - "[[karpathy-loop]]"
  - "[[session-coordination]]"
  - "[[infrastructure]]"
---

# GBrain Minions — concept absorbed, runtime pending

## What Minions is (Tan's upstream)

A **Postgres-native durable job queue** built into `garrytan/gbrain` starting v0.11.1 (2026-04-18). Routes **deterministic work** (parse, write, sync, cron, API-fetch) off the LLM gateway entirely. Judgment/reasoning work still goes to LLM sub-agents.

**The rule Tan codified:** *"Deterministic → Minions. Judgment → Sub-agents."*

**Benchmark claims (from upstream, 2026-04-18):**
- 753 ms latency vs 10 s+ for LLM sub-agent spawn
- $0.00 token cost vs ~$0.03/call
- 100% success rate vs 0% (sub-agents time out on deterministic long-running tasks)
- 10× throughput, 21× fan-out, 400× less memory
- SIGKILL-durable (jobs resume on gateway restart; Postgres-backed)

**Example: 19,240 posts / 36 months ingested in ~15 min at $0.**

## Why this matters for Nous AGaaS

Our factory currently runs **4 launchd crons + 2 polling agents** on Air:
- `com.nous.telegram-poll` (60s — @nousAGaaSbot)
- `com.nous.auto-checkpoint` (8× day — HANDOFF-AUTO)
- `com.nous.litellm-cost-alarm` (30 min — spend watchdog)
- `com.nous.docker-desktop-watchdog` (5 min — Docker recovery)
- `com.nous.nous-gpu-collector-health` (5 min — Phase-0 collector probe)
- `com.nous.session-heartbeat` (Mac, 3 min — session-coordination registry)
- `com.nous.session-cleanup` (Air, 60s — session-coordination stale-cleanup)

Each is a separate mechanism (plist files + bash scripts). Minions would **unify all of them behind a single job queue** with:
- Durability (Postgres-backed vs ephemeral launchd state)
- Observability (`gbrain jobs list` vs scattered log tails)
- Steerability (pause/resume/replay/send-message per job)
- Zero token cost (no LLM in the loop)

## Current state at Nous (honest)

| Artifact | Status |
|---|---|
| `pages/skills/gbrain-minion-orchestrator/SKILL.md` on Air runtime | ✅ absorbed 2026-04-21 via `tools/gstack_to_openclaw_adapter.py --source /opt/nous-agaas/gbrain-upstream/v0.14.2/skills --target ~/nous-agaas/skills --prefix gbrain-` |
| Factory (OpenClaw) can see the skill | ✅ `openclaw skills info gbrain-minion-orchestrator` returns "✓ Ready" |
| gbrain **runtime** on VPS | ❌ v0.10.1 — minions introduced v0.11.1 → runtime tools `submit_job`, `get_job`, `list_jobs`, `cancel_job`, `pause_job`, `resume_job`, `replay_job`, `send_job_message`, `get_job_progress`, `get_job_stats` are NOT available |
| Full runtime upgrade planned | ⏳ next session — blocked on resolving local changes to `skills/RESOLVER.md` + `skills/manifest.json` + `src/cli.ts` (we namespaced upstream skills under `_gbrain/` and added Nous-specific skills flat) |
| Upstream sidecar clone | ✅ at `/opt/nous-agaas/gbrain-upstream/v0.14.2/` on VPS for reference |

**The skill tells the agent what to do; the runtime is pending.** When upgrade lands, the existing skill immediately becomes usable.

## Planned migrations once runtime lands (session-57+)

1. Migrate cron jobs OFF launchd INTO minions jobs:
   - `telegram-poll` → minion with 60s schedule
   - `auto-checkpoint` → minion with 3h schedule
   - `litellm-cost-alarm` → minion with 30min schedule
   - `docker-desktop-watchdog` → minion with 5min schedule
   - `nous-gpu-collector-health` → minion with 5min schedule
   - `session-heartbeat` (Mac side) → keep as launchd (not Air)
   - `session-cleanup` (Air) → minion with 60s schedule
2. Every launchd plist that moves → delete + document in `infrastructure` new AP
3. `factory-ops` skill bumps to cover "how to schedule a minion" vs "how to add a launchd plist"
4. Sibling test `tools/test_minions_deployment_e2e.sh` — dogfoods the full flow

## Docs from upstream (archived locally)

Full text combined from Tan's upstream at `pages/concepts/gbrain-minions-upstream-2026-04-18/combined-docs.md`:
- `docs/guides/minions-shell-jobs.md` — how to register shell-command minions
- `docs/guides/minions-fix.md` — troubleshooting (stuck jobs, orphan workers)
- `docs/benchmarks/2026-04-18-minions-vs-openclaw-subagents.md` — performance comparison
- `docs/benchmarks/2026-04-18-minions-vs-openclaw-production.md` — production case study

## See also

- [[gbrain-ops]] — existing skill; will be bumped when runtime lands
- [[factory-ops]] — will absorb "schedule a minion" pattern
- [[infrastructure]] — new AP on launchd → minion migration discipline
- [[karpathy-loop]] — the adapter pattern (convert upstream format → ours) embodies this
- [[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]] — sibling design (substrate-as-coordination; minions is substrate-as-job-queue)
- Upstream: [github.com/garrytan/gbrain/blob/master/skills/minion-orchestrator/SKILL.md](https://github.com/garrytan/gbrain/blob/master/skills/minion-orchestrator/SKILL.md)
- Tan's launch tweet 2026-04-18: [x.com/garrytan/status/2045427231519015089](https://x.com/garrytan/status/2045427231519015089)
