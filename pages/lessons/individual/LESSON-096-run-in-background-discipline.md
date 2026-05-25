---
type: lesson
id: LESSON-096
title: "LESSON-096: Bash run_in_background discipline — ghost tasks accumulate in Claude Code panel"
tags: [lessons, claude-code, background-tasks, ux, meta, discipline]
date: 2026-04-15
source_count: 0
status: absorbed
absorbed_at: 2026-04-16
last_updated: 2026-04-15
related: [HANDOFF-2026-04-15-session22]
session: 22
severity: P2
integrated_into: gbrain-ops
absorbed_into: agent-quality
---

# LESSON-096: Bash `run_in_background` discipline — ghost tasks accumulate in Claude Code panel

## The Problem

During session 22, Claude Code's Tasks panel (right-side UI) filled with ~30 entries all showing "Running" — most for simple SSH checks, greps, and factory probes that completed in seconds. Madi reported: *"On the right side, there are so many things running and nothing is done, so why the hell is that?"*

None were actually running. The processes had finished long ago. The UI showed the tasks as perpetually "Running" because they were spawned with `Bash(run_in_background: true)` and never explicitly reaped.

## Root Cause

Claude Code's background-bash flag creates a persistent task entry in the session UI. The entry stays visible until:
1. TaskStop is called explicitly on the task id, or
2. TaskOutput reads it to completion, or
3. The entire Claude Code session ends

If the agent (me) spawns N background tasks and never reaps them, N entries linger in the UI forever, visually implying the system is busy when it isn't.

I was using `run_in_background: true` reflexively — even for `ssh air 'echo hi'` style calls that return in <1 second. No parallelism was gained; only clutter.

## Rule

**Default to foreground Bash.** Only use `run_in_background: true` when ALL of these apply:

1. The command genuinely takes >30 seconds (Docker pull, big SCP, model call, multi-step probe).
2. I want to do useful work during the wait (read files, write lessons, think).
3. I will actually call TaskOutput later to read the result (not "fire and forget").

**Anti-pattern examples** (saw myself doing these — STOP):
- `ssh vps 'echo ok'` in background → pointless, 200ms command
- `grep` or `ls` in background → finishes instantly, foreground is fine
- `scp` of a small file in background when I'm about to wait for it anyway

**Correct use examples**:
- `docker pull` of a 3GB image → 5-10 min → background, do other work
- `pytest` of 600+ tests → 1 minute → background while drafting docs
- `run_task.py` with a big factory probe → 1-2 min → background, continue parallel reads

## Secondary habit: reap when done

When a background task finishes and I've used its result, mentally "close the ticket." If I accumulate more than ~3 active background tasks, I'm almost certainly using the flag wrong.

## Impact

The UI noise isn't a bug — it's working as designed. The discipline is on the caller (me). Users reading the Tasks panel reasonably assume "Running" means "currently executing right now." If that's false across 20+ entries, user trust in the panel drops — exactly what Madi experienced.

## Related: the "task notification fired for a killed process" confusion

When I DID intentionally kill a background task mid-execution (example: `autopilot-run.sh` at PID 3720824 during patching), the kill signal eventually surfaces as a task-notification. Madi saw that and asked "why failed?" when it was an expected kill. Solution: when killing a background task I spawned, communicate it explicitly in chat rather than letting the async notification speak for itself.

---

## Timeline

- **2026-04-15** | Session 22: Tasks panel accumulated ~30 ghost entries from background flag overuse. Madi flagged it. Lesson written.

## See also

- [[HANDOFF-2026-04-15-session22]]
