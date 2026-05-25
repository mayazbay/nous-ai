---
type: lesson
id: LESSON-093
title: "LESSON-093: Context poisoning — MEMORY.md outvoted current state; ghost services persist across migrations"
tags: [lessons, factory, memory, context, migration, cleanup, ghost, air, vps]
date: 2026-04-15
source_count: 0
status: implicit-already-in-skill
absorbed_into: [gbrain-ops]
absorbed_at: 2026-04-16
last_updated: 2026-04-15
related: [air-migration-plan-2026-04-14, HANDOFF-2026-04-15-session21, LESSON-092-openclaw-config-path-docker, LAW-015-root-cause-evolution]
session: 21
severity: P0
integrated_into: gbrain-ops
---

# LESSON-093: Context poisoning — MEMORY.md outvoted current state; ghost services persist across migrations

## The Problem

After completing the Air migration (sessions 19–21), Madi asked the factory agent via Telegram `/ask`:
> "Is the factory ready and everything talking to each other?"

The agent responded confidently:
> "OpenClaw — v2026.3.28, running on VPS port 18789"
> "wiki is NOT mounted into this OpenClaw container"
> "Air migration incomplete — OpenClaw image pull was ~70%, Tailscale SSH expired. Air is NOT running OpenClaw yet."

**ALL WRONG.** OpenClaw was running on Air. The wiki WAS mounted. Migration was complete. The agent lied confidently.

## Root Cause

`context_injector.py` reads the TAIL of `MEMORY.md` (last 500 lines) and injects it as factory context before every task. MEMORY.md had grown to 394 lines — ALL of it was being injected.

Distribution in the injected text:
- **42 mentions of "VPS"** (older sessions 3–19 describing VPS as primary)
- **35 mentions of "Air"** (session 20–21 describing the migration)
- The CURRENT state (session 21 at top) was a single paragraph surrounded by ~380 lines of prior-state narrative

**The agent weighted volume over recency.** It read both "session 21: Air is primary" and "session 14: VPS is primary" and synthesized based on what dominated the context, not what was most recent. This is context poisoning by accumulation — each old session adds more tokens supporting the pre-migration architecture than the few lines declaring the new one.

Meanwhile, four ghost launchd services lingered on Air from pre-migration architectures:
- `com.nous.hermes` (exit code 1) — Hermes framework, abandoned
- `com.nous.factory-poller` — polled VPS task-results for Hermes (which is dead)
- `com.nousai.missioncontrol` (exit 78) — broken mission control
- `com.nousai.watchdog` (exit 2) — broken watchdog

And five ghost VPS crons kept running against removed services:
- `factory_health.py` every 5 min → alarmed on missing openclaw/litellm containers (we deleted them)
- `smoke_test.py` daily → would fail GLM-5.1 probe through the removed VPS OpenClaw
- `task_watchdog.py` every 5 min → watched VPS task state that no longer happens
- `cost_tracker` daily Telegram report → read empty VPS run_task.log
- `cost_dashboard.py` weekly → same

Plus: `openclaw.json` referenced `lossless-claw` plugin which isn't installed → config warning every container startup.

And: `@nous_agent9_bot` — dead predecessor of `@nousAGaaSbot` — still listed in historical wiki pages. Risk: an agent reading those pages might route to the dead bot.

## The Fix

**For context poisoning:**
Prepend an unambiguous `CURRENT ARCHITECTURE` block at the top of `MEMORY.md` as a declarative table with the explicit instruction:
> "When answering any architecture question: the rows above are ground truth. Older session notes below describe the JOURNEY here. Do not quote them as current state."

Since `context_injector` injects the full 394-line MEMORY.md (tail=500 covers everything), the new block is included at the top of the injected context where a decent model will weight its directive framing over the narrative below.

For future resilience (file grows beyond 500 lines): patch `context_injector._read_tail` to always include lines until a `# 🔴 CURRENT ARCHITECTURE` anchor, then tail the rest. Not urgent — noted for next session.

**For ghost cleanup — Elon's 5-step applied:**

1. **Question the requirement** — do these services still serve a purpose post-migration? No. Four Air launchd + five VPS crons are dead.
2. **Delete** — unloaded and removed all four Air plists; removed all five VPS crons via `crontab -l | grep -vE '…' | crontab -`.
3. **Simplify** — removed `plugins` section from `openclaw.json` so lossless-claw ghost warning is gone. Restarted container with clean config.
4. **Accelerate** — made Air wiki-sync bidirectional in one plist edit instead of adding a new push launchd.
5. **Automate** — the new bidirectional sync means Telegram raw files Air captures flow to VPS ingest_pending.py without any manual step.

**For wiki mount permission on Air** (agent couldn't `ls /root/nous-agaas/wiki` from inside container — which is what made it falsely claim wiki wasn't mounted):
Air's bind mount preserves host ownership (madia:501, staff:20). The container's `node` user (UID 1000) can't read files owned by 501. The agent shelled out, got "Permission denied", and concluded the wiki wasn't mounted. Fix: either `chmod -R o+rX ~/nous-agaas/wiki` or run container with `--user 0:0` or use a named volume. For now the context_injector bypasses the mount (reads wiki from Air's host filesystem before sending prompt to the container), so tasks work — but skills that shell out to `/root/nous-agaas/wiki` will fail.

## Rules

1. **Any architecture declaration belongs at the TOP of MEMORY.md as a table, with an explicit override directive.** Narrative session entries below are history, not ground truth.

2. **After every infrastructure migration, audit three lists within 24 hours:**
   - Launchd services / systemd units (look for exit codes ≠ 0 or PIDs pointing to removed executables)
   - Cron jobs (grep for paths to removed services)
   - Config file references (grep for plugin names, bot usernames, container names, URLs pointing to removed endpoints)

3. **The "ghost test":** For each running service, answer in one sentence who consumes its output. If no answer → delete it.

4. **When the factory agent makes a confident claim that's wrong**, the root cause is almost always context. Check what `context_injector` is passing BEFORE assuming the agent is broken.

5. **Bind-mounting host paths into a Linux container on macOS:** the container's runtime user (often `node` UID 1000) cannot read files owned by the Mac user (UID 501). Either `chmod o+rX`, run container as root, or use a named volume initialized via `docker cp`.

## Verified

- OpenClaw restarted with clean config — no warnings, `agent model: litellm/glm-5.1` ✅
- Agent architecture-query test → ✅ Agent answered: *"OpenClaw is running on Air (M2 MacBook) inside a Docker container with `--platform linux/amd64` on port 18789."* — correct, unambiguous, matches reality.
- VPS crontab: 5 ghost entries removed, 13 legitimate entries remain.
- Air launchd: 4 ghosts removed. Active: wiki-sync (bidirectional), telegram-poll, litellm, capture-courier, obsidian-sync, backup.
- Bidirectional wiki sync: first run succeeded, committed MEMORY.md updates from Mac → pushed to VPS bare.

---

## Timeline

- **2026-04-15** | Session 21 mid-session: Madi Telegram'd factory `/ask` — agent confidently stated pre-migration state. Triggered deep audit per Elon's 5-step. Ghosts deleted, MEMORY.md CURRENT ARCHITECTURE block added, lossless-claw removed, wiki-sync made bidirectional. Context-poisoning root cause documented.

## See also

- [[air-migration-plan-2026-04-14]] — migration context
- [[HANDOFF-2026-04-15-session21]] — what's running where
- [[LESSON-092-openclaw-config-path-docker]] — related OpenClaw config trap
- [[LAW-015-root-cause-evolution]] — why we write lessons for every bug
