---
tier: 2
type: skill
name: goal-mode
id: SKILL-GOAL-MODE
version: 1.0.14
last_updated: 2026-05-22
status: active
description: "Goal Mode v1 — persistent goal execution layer above all backends. /goal creates an Obsidian GOAL page + Todoist task, then immediately kicks com.nous.goal-cycle; launchd continues goal_runner.py every 4 hours; each cycle dispatches one run_task.py worker per active goal, and goal_runner.py itself appends the durable progress entry to the GOAL page. v1 scope: Obsidian canonical → gbrain → Todoist. No Postgres in v1. AP-1: one slice per cycle, not full completion. AP-2: worker must read GOAL page before acting. AP-3: /goal-done not automated in v1 — edit status field in wiki page directly. AP-6: /goal handlers must land in tracked tools/command_center.py before Air runtime deploy. AP-7: /goal must visibly start or schedule the durable runner. AP-8: goal_runner owns GOAL page writes. AP-9: overlapping goal-cycle kicks are locked out. AP-10: /goal deadline parsing must accept inline 'by YYYY-MM-DD' before punctuation, not only terminal dates. AP-11: goal_runner git write-back must retry stale index locks. AP-12: stale-lock ownership check must be lock-file scoped. AP-13: read-only lock readers are not lock owners. AP-14: automated goal commits must bypass git hooks. AP-15: dead recorded cycle-lock PIDs are stale immediately. AP-16: the full automated goal git sequence bypasses hooks. AP-17: runner must inline bounded GOAL page context because direct model workers may not have filesystem tools. AP-18: goal-cycle workers use grok-reasoning by default for reasoning-heavy progress slices and show the route in Telegram; GPT-5.5 remains the explicit /codex escalation lane. AP-19: classify burst alerts by unique goal source before calling them retrigger loops. AP-20: unattended goal write-back must use exact-OID fetch/rebase, not compound git pull."
triggers:
  - "/goal (Telegram command)"
  - "user asks about persistent goals"
  - "goal-cycle launchd fires"
  - "goal_runner.py cycle"
  - "how do I set a persistent goal"
tools: [Bash, Read, Edit, mcp__gbrain__*]
mutating: true
absorbs_lessons: []
related: [ceo-hierarchy, factory-ops, session-operating-contract, command-center]
tags: [skill, goal-mode, persistent, automation, telegram, launchd, todoist, 2026-05-10]
title: "goal-mode v1.0.14"
date: 2026-05-12
source_count: 0
---

# goal-mode v1.0.14

## Purpose

Madi sets a goal once via `/goal "X [by YYYY-MM-DD]"` → agent revisits the goal every 4 hours, makes one slice of progress, reports back via Telegram. Until done. No re-prompting needed. Based on Vincent/OpenClaw `/goal` constraint-workflow pattern.

**v1 scope (s108-mac, 2026-05-10):** Obsidian canonical + Todoist + launchd. No Postgres in v1.

## Architecture

```
/goal "X by DATE"
  ↓ command_center.py handle()
  ↓ _create_goal_page()  → wiki/pages/projects/GOAL-YYYYMMDD-HHMMSS-<slug>.md
  ↓ _create_todoist_task() → Todoist API v1
  ↓ _kick_goal_cycle() → launchctl kickstart gui/$UID/com.nous.goal-cycle
  ↓ Telegram confirm

immediately after /goal + every 4 hours: com.nous.goal-cycle (launchd, Air)
  ↓ goal_runner.py
  ↓ _load_active_goals() → scan wiki/pages/projects/GOAL-*.md (status: active)
  ↓ for each goal: _dispatch_worker() → run_task.py with progress prompt
  ↓ goal_runner.py appends ## Progress log entry + updates last_progress_at + git commit
  ↓ goal_runner.py: exact fetch/rebase + git push + Telegram digest
```

## Key files

| File | Location | Purpose |
|---|---|---|
| `tools/command_center.py` | Vault + Air runtime `~/nous-agaas/command_center.py` | `/goal` and `/goal-list` handlers |
| `goal_runner.py` | Air `~/nous-agaas/` + vault `tools/` | 4hr cycle engine |
| `tools/launchd/com.nous.goal-cycle.plist` | Vault canonical + Air `~/Library/LaunchAgents/` | launchd 14400s interval |
| `pages/projects/GOAL-*.md` | wiki | One page per goal (canonical state) |

## GOAL page schema

```yaml
---
type: project
id: GOAL-YYYYMMDD-HHMMSS
title: "<goal text>"
status: active | paused | done | abandoned
deadline: YYYY-MM-DD  (or "none")
created_at: YYYY-MM-DD HH:MM
last_progress_at: YYYY-MM-DD HH:MM  (or null)
---

# <goal text>

## Success criteria

## Progress log
- **YYYY-MM-DD HH:MM KZT** — <what worker did + outcome>

## Status
<current state summary>
```

## Todoist integration

- API endpoint: `https://api.todoist.com/api/v1/tasks` (v2 deprecated, use v1)
- Auth: `TODOIST_API_TOKEN` in `~/nous-agaas/.env`
- Project: `TODOIST_PROJECT_ID` in `~/nous-agaas/.env` (Satory AI project)
- Task format: `🎯 <goal text>` + due_date if deadline provided

## Telegram commands

| Command | Action |
|---|---|
| `/goal "X [by YYYY-MM-DD]"` | Create goal + Obsidian page + Todoist task |
| `/goal-list` | Show active goals |
| `/goal-done` | v1.1 deferred — edit wiki page status field manually |
| `/goal-pause` | v1.1 deferred — edit wiki page status field manually |

## Anti-Patterns

### AP-1 — One slice per cycle, not full completion (v1.0.0)
Never instruct the goal worker to "complete the entire goal this cycle." Each cycle = one concrete deliverable. Steady drip > heroic single-session sprint. Reason: agent loops exceeding 600s time out; single-session completion of multi-day goals creates all-or-nothing failure mode.

### AP-2 — Worker must read GOAL page before acting (v1.0.0)
Always inject the full GOAL page path in the worker prompt. Worker must read the ## Progress log section before taking action to avoid duplicating prior work. Reason: without context, workers repeat the same first slice every cycle.

### AP-3 — /goal-done not automated in v1 (v1.0.0)
In v1, set `status: done` directly in the wiki GOAL page. Do not build automation to detect goal completion in v1 — it creates false-positive completion risk. Reason: goal completion criteria are fuzzy; Madi should own the declaration.

### AP-4 — Todoist REST v2 is deprecated (v1.0.0)
Use `/api/v1/` endpoints, not `/rest/v2/`. The v2 endpoint returns a CloudFront deprecation page. Reason: discovered during v1 build; v2 routes return error HTML, not JSON.

### AP-5 — goal_runner.py dispatches via run_task.py, not /code CLI (v1.0.0)
Always use `run_task.py` for the goal worker dispatch (not subprocess of `claude --no-interactive`). run_task.py handles ACTIVE-TASK checkpoint + 15-iteration kill switch + write-back to wiki. Reason: /code CLI in subprocess requires session auth; run_task.py uses LiteLLM directly.

### AP-6 — Goal handlers must be tracked before runtime deploy (v1.0.1)
Do not patch Air-local `~/nous-agaas/command_center.py` as the only source of `/goal` truth. The canonical change must land in vault `tools/command_center.py`, include a regression test proving `is_command('/goal')` and `is_command('/goal-list')`, then deploy byte-equal to Air runtime. Reason: the 2026-05-11 audit found `goal_runner.py` and the skill page were present, but `/goal` was false on Air because the handler was never in tracked `tools/command_center.py` and was overwritten by a later canonical command-center deploy.

### AP-7 — /goal must kick or visibly schedule the durable runner (v1.0.2)
Creating a GOAL page is not enough. After `_create_goal_page()` and Todoist creation, `/goal` must call `_kick_goal_cycle()` and include `Runner: ...` in the Telegram reply. Preferred path: `launchctl kickstart -k gui/$UID/com.nous.goal-cycle`. Fallback: start `/Users/madia/nous-agaas/goal_runner.py` directly if the launchd kick fails and the runner exists. If both fail, reply `Runner not started: <root cause>`; never make the operator wait 4 hours without saying so. Keep the 4-hour launchd interval as the durable continuation loop.

### AP-8 — goal_runner owns GOAL page writes (v1.0.3)
Do not rely on the worker model to edit the GOAL page, update `last_progress_at`, commit, or push. `run_task.py` may choose a direct LiteLLM model route, and direct model routes can only return text plus a task-result write-back; they do not have shell/editor tools. The runner must append the worker result to `## Progress log`, update `last_progress_at`, update `## Status`, commit the GOAL page, rebase, and push. Worker prompts must not claim the worker will edit files.

### AP-9 — goal-cycle kickstarts must not overlap (v1.0.3)
Every immediate `/goal` kick and every 4-hour launchd interval must acquire a process lock before scanning active goals. If another cycle is running, log and exit. Without a lock, rapid creation of multiple goals can start overlapping cycles that all process the same first active goal, generate duplicate task-results, and leave git in a dirty or locked state.

### AP-10 — Deadline parser must handle inline date clauses (v1.0.4)
Do not require `/goal` deadlines to appear only at the end of the command. Operators naturally write long goals as `... by YYYY-MM-DD: deliver A, B, C`; the parser must extract that date before punctuation/continuation text and preserve the rest of the goal body. If the parser misses this, the GOAL page gets `deadline: none` and Todoist is created without a due date even though the operator specified one.

### AP-11 — Git write-back must tolerate stale index locks (v1.0.5)
The runner must not silently drop progress when `git add` hits `.git/index.lock`. Air auto-sync, manual sessions, and goal-cycle write-back can briefly overlap. `goal_runner.py` should retry git commands, remove stale index locks only when no `git` process is running, log stderr/stdout for failures, and preserve dirty GOAL page edits for manual recovery if all retries fail.

### AP-12 — Stale-lock ownership checks are lock-file scoped (v1.0.6)
Do not block stale `.git/index.lock` cleanup just because any `git` process exists on the host. Air can have unrelated long-running git commands in other working copies. Before deleting a stale wiki index lock, check whether the lock file itself is held, for example with `lsof -t <wiki>/.git/index.lock`; unrelated git processes must not prevent recovery.

### AP-13 — Read-only lock readers are not lock owners (v1.0.7)
macOS indexers can hold `.git/index.lock` open as read-only after the writer is gone. A read-only `lsof` holder is not an active git write. Stale-lock recovery should block only on writer/update file descriptors (`w` or `u` in the `lsof` FD column); read-only holders must not stop unlinking a stale lock.

### AP-14 — Automated goal commits must bypass git hooks (v1.0.8)
`git commit --no-verify` skips pre-commit hooks but still runs `prepare-commit-msg`. Goal-cycle write-back is already machine-authored and time-bounded; it must not hang on attribution hooks. Use `git -c core.hooksPath=/dev/null commit --no-verify ...` for runner-owned commits, then rely on the surrounding GOAL page, task-result, launchd logs, and git SHA for attribution.

### AP-15 — Dead cycle-lock PIDs are stale immediately (v1.0.9)
The goal-cycle process lock records `pid=<pid>`. If the lock file exists but that PID no longer exists, the lock is stale even when it is younger than the normal age threshold. Remove it and proceed; otherwise a killed or crashed runner blocks launchd proof cycles for up to 30 minutes after the real process is gone.

### AP-16 — Full automated goal git sequence bypasses hooks (v1.0.10)
Disabling hooks only on the `commit` subprocess is not enough. `git pull --rebase` can also invoke commit-message hooks when it replays local automated commits over a moving remote. `goal_runner.py` must run every git subprocess through `git -c core.hooksPath=/dev/null ...` for runner-owned add/diff/commit/pull/push operations. Human/session commits still use normal hooks.

### AP-17 — Inline GOAL page context for direct model workers (v1.0.11)
Do not assume the worker behind `run_task.py` has filesystem or editor tools. Cheap/direct model routes can return one text slice but cannot read `/Users/madia/nous-agaas/wiki/...` even when the prompt includes the path. `goal_runner.py` must inject a bounded copy of the GOAL page content into the worker prompt, including the `## Progress log`, and tell the worker to use that inline context as the source of truth. Path-only prompts are insufficient and produce fake "cannot read file" or repeated first-slice outputs.

### AP-18 — Goal-cycle reasoning route must not fall through to cheap/escalation workers (v1.0.12)
Goal-cycle progress selection is reasoning work: it decides what one slice matters next, what evidence is real, and what should be surfaced to Madi. `goal_runner.py` must pass an explicit model to `run_task.py` instead of letting `ModelEscalator.pick()` choose a cheap or failure-escalation worker. Default route: `NOUS_GOAL_WORKER_MODEL=grok-reasoning`. Setting `NOUS_GOAL_WORKER_MODEL=""` is the only allowed way to return to model-escalator behavior for a controlled bakeoff.

GPT-5.5 is the `/codex` high-judgment escalation lane, not an invisible every-4-hour background worker. A live 2026-05-14 Codex canary used about 7k tokens for an exact-response probe, so running every goal heartbeat through GPT would hide quota burn. The runner must show the route in the Telegram digest so the operator can see whether a cycle used Grok, an explicit override, or a future GPT canary path.

### AP-19 — Burst alerts must distinguish fan-out from retrigger loops (v1.0.13)
Do not call a goal-cycle burst a retrigger loop until the audit groups task-results by `source: goal-cycle:<GOAL_ID>`, checks active GOAL count, and confirms the launchd `StartInterval`. One scheduled cycle intentionally dispatches one worker per active goal. Nine task-result files over two minutes can be correct when there are nine active goals and each source appears once.

Real retrigger evidence requires at least one of:

- repeated task-results for the same `goal-cycle:<GOAL_ID>` inside one expected cycle window,
- launchd `StartInterval` not equal to `14400`,
- missing or bypassed `GOAL_CYCLE_LOCK`,
- live lock contention or overlapping `goal_runner.py` PIDs.

If the burst is one-result-per-active-goal, classify the handoff warning as false-positive/yellow, not a runtime red. The real optimization then is goal-count hygiene or per-cycle concurrency/cost policy, not lock repair.

### AP-20 — Unattended write-back uses exact-OID rebase, not compound pull (v1.0.14)
Do not use `git pull --rebase <remote> main` inside `goal_runner.py` or other unattended goal write-back paths. Air's wiki has wildcard fetch refspecs and multiple concurrent writers, so compound pull can resolve to an invalid rebase target and fail with `Cannot rebase onto multiple branches` after the worker already produced a useful result. Fetch exactly one ref with `git fetch <remote> main:refs/remotes/<remote>/main`, resolve `refs/remotes/<remote>/main` to an OID, rebase onto that OID, fetch once more, then push with one non-fast-forward retry. This preserves the worker result and removes branch-config ambiguity.

## v1 deferred (v1.1+)

- `/goal-done` / `/goal-pause` management commands
- Postgres persistence (Air-side) for multi-owner goals
- Weekly goal digest (Saturday 09:00 KZT)
- Goal completion detection via acceptance criteria match
- `/goal-list` with progress %, deadline countdown

## See also

- [[skills/ceo-hierarchy]] — model tier routing for goal workers
- [[skills/factory-ops]] — OpenClaw + run_task.py substrate
- [[skills/command-center]] — Telegram command handler architecture
- [[pages/plans/plan-cockpit-q3-enhancements-2026-05-07]] — Enhancement 2 original design

---

## Timeline

- **2026-05-22** | v1.0.13 -> v1.0.14 — A manual kick of `com.nous.goal-cycle` picked up `GOAL-20260522-133443` and processed 10 active goals, but the new goal's write-back logged `fatal: Cannot rebase onto multiple branches`. Root cause: `goal_runner.py` still used compound `git pull --rebase origin main` in an unattended multi-writer repo. Fix: goal write-back now fetches exactly `main:refs/remotes/origin/main`, rebases onto the resolved OID, fetches once more for races, and retries push after a non-fast-forward. No new LESSON (RULE ZERO).
- **2026-05-21** | v1.0.12 -> v1.0.13 — Deep second-brain audit classified the latest handoff's "8 runs in 2 minutes vs 4h spec" warning. Live Air proof showed `StartInterval=14400`, `_cycle_lock()` present, and 9 task-result files mapped to 9 distinct active GOAL sources with `last_progress_at=2026-05-21 19:26`. Root cause: the warning counted fan-out files, not repeated cycles. Rule: group by `source: goal-cycle:<GOAL_ID>` and active goal count before calling a burst a retrigger loop. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.0.11 → v1.0.12 — Madi flagged that goal-cycle progress looked like cheap-worker text and should use the Grok→GPT hierarchy for reasoning. Root cause: `goal_runner.py` called `run_task.py` without `--model`, so `ModelEscalator.pick()` routed goal workers to DeepSeek V4 Pro after earlier Flash failures. Fix: default goal worker route is now explicit `grok-reasoning`, with Telegram route visibility and GPT-5.5 kept as explicit `/codex` escalation. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.10 → v1.0.11 — 19:21 KZT goal-cycle proof showed the KEONA worker could not read its GOAL page and returned a blocker about missing filesystem access. Root cause: `goal_runner.py` injected only the GOAL page path, while direct LiteLLM worker routes may not have file tools. Fix: worker prompt now includes bounded inline GOAL page context plus a regression proving prior progress appears in the prompt. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.9 → v1.0.10 — Air proof found `git pull --rebase` can still invoke `prepare-commit-msg` after the runner-owned commit itself bypassed hooks. Fix: goal_runner now injects `-c core.hooksPath=/dev/null` into every automated git subprocess, covering add/diff/commit/pull/push. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.8 → v1.0.9 — Air proof kick found `goal-cycle.lock` still recorded dead PID 84981 after the broken runner had been killed, so the patched runner refused to start until the 30-minute age threshold. Fix: cycle-lock recovery now parses `pid=<pid>` and removes locks whose recorded process is no longer alive. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.7 → v1.0.8 — Air proof showed stale-lock cleanup worked, but `git commit --no-verify` still timed out because `prepare-commit-msg` hooks were stuck. Fix: goal_runner-owned commits now use `git -c core.hooksPath=/dev/null commit --no-verify` so the durable runner cannot hang on git hooks. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.6 → v1.0.7 — Air proof showed `.git/index.lock` was held read-only by a `com.apple` process, so the lsof-scoped check still refused cleanup. Fix: stale-lock recovery now treats only writer/update FDs as lock ownership and allows cleanup when the only holders are read-only OS indexers. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.5 → v1.0.6 — First stale-lock retry patch still refused to remove the wiki `.git/index.lock` because an unrelated long-lived git command existed in another working copy. Fix: stale-lock ownership now checks whether the lock file itself is held with `lsof`, instead of checking for any git process on the host. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.4 → v1.0.5 — Launchd proof cycle wrote progress into four GOAL pages but `git add` failed on a stale `.git/index.lock`, leaving durable page edits uncommitted until manual recovery. Fix: goal_runner git write-back now retries index-lock failures, removes stale locks only when no git process is running, and logs stderr/stdout. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.3 → v1.0.4 — Live audit of Madi's АПК bootstrap goal found `/goal` parsed `by 2026-05-19:` as part of the title instead of a deadline because `_parse_goal_command()` only accepted terminal `by YYYY-MM-DD`. Fix: parser now extracts inline date clauses before punctuation, regression test added, and the existing bootstrap GOAL page deadline was corrected. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.0.2 → v1.0.3 — Live audit after four `/goal` creations found the creation path worked, but the execution contract was false: the first cycle used direct `deepseek-v4-flash`, wrote a task-result, did not update the GOAL page, and rapid kickstarts overlapped. Fix: goal_runner now owns GOAL page progress writes/rebase/push and uses a goal-cycle lock so immediate kicks cannot overlap. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.0.1 → v1.0.2 — Root cause of "why did /goal stop": `/goal` only created a GOAL page/Todoist task and waited for the next 4-hour `com.nous.goal-cycle` tick; the active launchd plist also lived only on Air, not in the tracked vault. Fix: `_kick_goal_cycle()` now starts/schedules the durable OpenClaw runner immediately and surfaces the runner result in Telegram; `tools/launchd/com.nous.goal-cycle.plist` is tracked; tests cover launchd kick and visible reply. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.0.0 → v1.0.1 — Audit found Goal Mode was not actually live in the Telegram command path: `is_command('/goal')` and helper existence were false on Air even though `goal_runner.py`, launchd, and docs existed. Root cause: the prior handler lived outside tracked canonical `tools/command_center.py` or was never committed there, then a later canonical deploy overwrote Air runtime. Fix: restored `/goal` + `/goal-list` in tracked `tools/command_center.py`, added regression tests, and documented AP-6. No new LESSON (RULE ZERO).
- **2026-05-10** | v1.0.0 created — Goal Mode v1 built (s108-mac). goal_runner.py, /goal handler in command_center.py, GOAL page schema, launchd com.nous.goal-cycle, Todoist API v1 integration. Tests: _create_goal_page() OK, _create_todoist_task() OK, is_command('/goal') True. launchd loaded on Air.
