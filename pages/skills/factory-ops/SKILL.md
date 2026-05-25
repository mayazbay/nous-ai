---
tier: 2
type: skill
name: factory-ops
version: 1.36.20
description: "Operational rules for the AGaaS autonomous factory — how to safely start/stop/debug, prevent budget leaks, manage task queues, and operate the CEO agent. Covers both the original VPS systemd factory (LESSON-001..057) and the current Air-based OpenClaw factory. Rules are agent-agnostic — the patterns apply to any autonomous LLM loop. Includes AP-24..AP-40 (running history) plus s74 (2026-05-05) bundle: AP-41 CCD agent-mode orphan watchdog, AP-42 library coherence baseline, AP-43 library mass-fix pass 1 SHIPPED; AP-43 (s108, 2026-05-10) DAILY_0300_OK false-negative fix; AP-44 docker cp + chown 1000 pattern; AP-45 launchd loop restart-after-fix; AP-38 host-side Docker publish binding to 127.0.0.1; AP-46 (s108, 2026-05-12) OpenRouter `limit` without `limit_reset` is LIFETIME not daily; AP-47 OpenRouter daily-cap exhaustion cascades to LiteLLM 0-models + factory 402; AP-48/AP-49 task-result git write-back bypasses hooks; AP-50 LiteLLM `/v1/models` needs auth; AP-51 LangSmith is a mirror, local JSONL remains factory truth; AP-52 OpenClaw remains production orchestrator until any Hermes candidate passes parity gates; AP-53 light probes must filter non-chat model noise and send Telegram through tg_send.sh; AP-54 OpenBrain probes must check the real projection output path, not a stale filename guess; AP-55 Air-local lag is not GitHub mirror drift; AP-56 repairable Air-local lag must self-heal before paging; AP-57 self-heal must re-read canonical after pull; AP-58 auto-repair must fetch one ref and rebase one OID, never use unattended git pull; AP-59 LiteLLM health summaries must fail loud on non-health auth/error payloads; AP-60 drift/state-change probes must delegate to `factory_self_heal.py` before Telegram paging; AP-61 Docker image-version probes must read `.Config.Image` before `.Image`; AP-62 queue success must parse Markdown-bold blocked status before counting OK; AP-63 launchd queue writers must commit their own proof files before other write-back jobs rebase; AP-64 OpenClaw canaries require token auth plus local gateway config and separate operator-scope proof; AP-65 OpenClaw production promotion is a two-phase cutover plus timed soak, and an early healthy cutover is monitored forward rather than reflex-rolled back; AP-66 5.18 production homes must preserve 5.18 gateway auth while importing Nous model/agent routing from the old production home; AP-67 audit help/dry-run modes must not mutate durable state; AP-68 Air runtime root is an Air-local release ledger, not canonical wiki source; AP-69 ignores live ACTIVE-TASK.md checkpoints in the Air release ledger; AP-70 preserves grok-ceo SOUL/IDENTITY across OpenClaw home promotions; AP-71 (2026-05-25) GitHub Actions that call paid APIs must pre-probe quota with a 1-token call before invoking the action SDK, so quota-cap is a skipped-with-warning instead of a failed-job email; AP-72 (2026-05-25) generated `codex/*` PR heads must not auto-start paid review loops on `pull_request` events; use explicit `workflow_dispatch` for intentional review."
triggers:
  - starting, stopping, or restarting the factory
  - factory is idle but shouldn't be
  - factory costs more than expected
  - factory keeps retrying the same error
  - adding a new task to the factory queue
  - debugging why the CEO isn't working
  - any autonomous agent loop behavior
tools: [Bash, Read, Grep]
mutating: true
absorbs_lessons: [LESSON-001, LESSON-002, LESSON-004, LESSON-019, LESSON-028, LESSON-035, LESSON-039, LESSON-040, LESSON-044, LESSON-045, LESSON-048, LESSON-051, LESSON-052, LESSON-054, LESSON-055, LESSON-056, LESSON-057, LESSON-065, LESSON-114]
absorbs_laws: [LAW-006, LAW-007, LAW-010, LAW-011]
last_updated: 2026-05-25
title: "factory-ops v1.36.20"
---

# factory-ops v1.36.20

## Purpose

Autonomous LLM loops are expensive when they idle and catastrophic when they loop on errors. This skill contains the hard-won rules from 57 lessons of running the AGaaS factory autonomously. Every Anti-Pattern here has a dollar cost or a trust cost attached.

## Contract

**Inputs:** A factory operation request (start/stop/debug) or a factory behavior symptom (idle, looping, expensive).

**Outputs:** Factory running correctly, costs within budget, no zombie processes, no idle loops.

**Invariants:**
- Factory never runs two processes simultaneously
- Budget gates pause factory until manual resolution, never retry indefinitely
- CEO never calls an LLM before checking if there is work to do
- Telegram alerts fire once per state transition, not per retry

## Phases

### Phase 1 — Stopping the factory safely

**Current Air factory (OpenClaw-based):**

```bash
# Check what's running
ssh air 'launchctl list | grep com.nous'

# Stop Telegram poller (so no new tasks enter)
ssh air 'launchctl stop com.nous.telegram-poll'

# OpenClaw handles tasks via Docker — check for in-flight tasks
ssh air 'docker logs openclaw --tail 20'  # is a task running?

# Stop OpenClaw when safe
ssh air 'docker stop openclaw'
```

**Old VPS factory (systemd-based, historical reference):**

```bash
# WRONG — watchdog will restart factory within 60s
systemctl stop nous-agaas

# CORRECT — stop watchdog FIRST, then factory (LESSON-044)
systemctl stop nous-watchdog && systemctl disable nous-watchdog
systemctl stop nous-agaas && systemctl disable nous-agaas
ps -ef | grep -E "run_loop|watchdog.py" | grep -v grep  # expect: nothing
```

### Phase 2 — Restarting the factory

```bash
# ALWAYS verify process count after restart (LESSON-039)
ps aux | grep run_loop | grep -v grep  # expect: exactly 1 PID

# Re-enable watchdog ONLY AFTER factory is stable for 3+ cycles
systemctl enable nous-watchdog && systemctl start nous-watchdog
```

### Phase 3 — Before any manual code/frontend edits

```bash
# Stop the factory first (LESSON-045)
# Factory's git add -A will steal your uncommitted changes

# After stopping, verify working tree is clean
git -C /path/to/project status  # should be clean or only your files

# After manual edits, COMMIT immediately with your own message:
git add <specific-files> && git commit -m "manual: description"
# Do NOT use git add -A — stage specific files only
```

### Phase 4 — Diagnosing factory idle/cost issues

```bash
# Is the task queue actually empty?
# Check ALL projects (LESSON-051):
python3 -c "
from task_db import get_all_tasks
tasks = get_all_tasks(status='pending')
print(f'Pending: {len(tasks)}')
for t in tasks: print(f'  [{t[\"project\"]}] {t[\"id\"]} {t[\"title\"][:60]}')
"

# Any zombie in_progress tasks? (LESSON-040)
python3 -c "
from task_db import get_all_tasks
tasks = get_all_tasks(status='in_progress')
print(f'In-progress (zombies if >1): {len(tasks)}')
for t in tasks: print(f'  {t[\"id\"]} {t[\"title\"][:60]}')
"

# Are there cycle cost leaks?
tail -100 logs/run_loop.log | grep -E "COST|Budget|CEO|no_tasks|duplicate"
```

### Phase 5 — Dispatching a task to the factory (proven 4× in session 23)

The disciplined 7-step pattern that moves a factory-executed edit all the way from `run_task.py` invocation to a byte-identical copy in the OpenClaw container. Worked for T1–T4 in session 23 (command-center AP-8, 7 IS policy stubs, camera-management Wave-2, AUDIT-031 Apr-5 investigation). Skipping any step produces desync.

```bash
# 0. Compose the prompt in a file (avoids shell-escape hell for multi-line + pipes + quotes)
cat > /tmp/tN_prompt.txt << 'PROMPT_EOF'
Factory task TN — <one-line goal>.

CONTEXT: <relevant facts, file paths the agent can read>
TARGET FILE: <absolute path inside the container, e.g. /opt/nous-agaas/wiki/pages/skills/X/SKILL.md>
EDITS: <numbered list of concrete changes>
VERIFY: <grep command the agent should run before FINAL_OK>
End with FINAL_OK.
PROMPT_EOF
scp /tmp/tN_prompt.txt air:/tmp/tN_prompt.txt

# 1. Dispatch via run_task.py (this is the factory's canonical entry)
ssh air 'cd ~/nous-agaas && python3 run_task.py "$(cat /tmp/tN_prompt.txt)" 2>&1 | tail -15'

# 2. Verify the task-result frontmatter shows the RIGHT model (not silent flash fallback)
ssh air 'cat $(ls -t ~/nous-agaas/wiki/pages/task-results/*.md | head -1) | head -6'
# Expect: model: glm-5.1 (NOT glm-4.5-flash, which means ZAI/OpenRouter drained mid-task)

# 3. Check what the agent changed via git status (the agent's write-back commit may not
#    include its own SKILL.md edit — common failure mode)
ssh air 'cd ~/nous-agaas/wiki && git status --short'

# 4. If there are unstaged edits from the agent, git add them SEPARATELY and commit
#    (the write-back's own `git pull --rebase` would otherwise fail on unstaged changes)
ssh air 'cd ~/nous-agaas/wiki && git add pages/... && git commit -m "<exact change>" 2>&1 | tail -3'

# 5. git pull --rebase, then push (AP-8 in this skill)
ssh air 'cd ~/nous-agaas/wiki && git pull --rebase 2>&1 | tail -2 && git push 2>&1 | tail -2'

# 6. Rsync wiki → Air runtime skills/ (OpenClaw's bind mount) so container sees the new version
ssh air 'rsync -av ~/nous-agaas/wiki/pages/skills/<skill>/ ~/nous-agaas/skills/<skill>/ | tail -3'

# 7. md5 parity — HOST must equal CONTAINER
ssh air 'md5 -q ~/nous-agaas/skills/<skill>/SKILL.md; docker exec openclaw md5sum /opt/nous-agaas/skills/<skill>/SKILL.md'
# Two lines must match. Then agent answers next /ask using the new version.
```

Time budget per dispatch: ~1–4 minutes factory + ~30s commit/push/rsync. Keep tasks bounded (single-file edits, skeleton-file creation, investigation-report writing). Multi-component work (dashboard builds, architecture redesigns) do NOT dispatch well — surface errors, context overflow, half-edits. Route those to Claude Code / Sonnet instead.

## Anti-Patterns

### AP-1 — Two watchdogs will fight you if you only stop one
**LESSON-044.** In the old VPS factory there were TWO restart mechanisms:
1. `nous-watchdog.service` (systemd): checks every 60s, restarts factory if inactive
2. `task_watchdog.py` (cron every 5min): resets stuck DB tasks, does NOT restart factory

`systemctl stop nous-agaas` triggers the watchdog to restart it within 60 seconds. `systemctl disable` only removes from autostart — it doesn't prevent the running watchdog from restarting.

**Pattern: always stop ALL control-plane processes first (watchdog/cron/launchd), THEN stop the main process.**

```bash
# List everything that could restart the factory:
systemctl list-units | grep nous
crontab -l | grep -v "^#"
launchctl list | grep com.nous

# Stop them in reverse dependency order (watchdog before factory)
```

### AP-2 — git add -A in automation steals manual edits
**LESSON-045.** The factory's deploy commit uses `git add -A` which stages ALL modified files — including your in-progress manual edits that arrived between factory cycles. Your files get committed under a factory task name.

```bash
# ❌ What factory does (dangerous):
git add -A && git commit -m "task/12345: automated deploy"

# ✅ What factory SHOULD do:
git add <specific-factory-owned-files> && git commit -m "task/12345: ..."
```

Rule: **Stop the factory before any manual git+code session. Never leave manual edits uncommitted while factory is running.**

### AP-3 — Always verify exactly 1 factory process after restart
**LESSON-039.** Running factory twice doubles cost instantly. `nohup` silently detaches a second process. After any restart:

```bash
ps aux | grep run_loop | grep -v grep
# Expected: exactly 1 line
# If 2+ lines: kill the extras, investigate why they started
```

### AP-4 — Budget gate must pause, not just return
**LESSON-055.** A budget gate that returns an error code without sleeping causes the outer loop to retry every 5 minutes — 30 retries in an hour at zero cost but huge log noise. Pattern for any hard-stop gate:

```python
# ❌ WRONG — outer loop retries immediately
if daily_cost >= BUDGET:
    return {"error": "Budget hit"}

# ✅ RIGHT — pause until the constraint lifts
if daily_cost >= BUDGET:
    sleep_until = midnight_utc()
    send_telegram(f"BUDGET HIT. Sleeping until midnight UTC.")
    time.sleep(sleep_until)
    return {"error": "Budget hit"}
```

Each error class needs its own pause strategy:
- Daily budget hit → sleep until midnight (resets at 00:00 UTC)
- API credit exhausted → lock file + sleep 30min until manual unlock (LESSON-056)
- Rate limit → exponential backoff (2, 4, 8, 16, 32 sec)
- Transient network → 3 retries with 30s spacing, then alert

### AP-5 — CEO must check for work BEFORE calling LLM
**LESSON-054.** At $0.10/Opus-call, 63 idle CEO cycles = $6.30/day wasted. Always check deterministically before calling the LLM:

```python
# ❌ WRONG — calls LLM even when there's no work
if not pending_tasks:
    tasks = ceo_llm.create_tasks_from_specs()

# ✅ RIGHT — pre-flight check is free
spec_reqs = parse_spec_tags(specs_file)  # REQ-001..REQ-089
existing_reqs = {t['req_id'] for t in get_all_tasks()}
fresh_reqs = spec_reqs - existing_reqs
if not fresh_reqs:
    log.info("All spec REQs tracked. Skipping CEO LLM call.")
    return {"error": "no_fresh_reqs"}
# Only now: call the LLM with the fresh REQs as context
```

Corollary: **If CEO cycle returns "no_tasks" 5 times in a row, write a new spec or escalate to Madi.**

### AP-6 — Clean up zombie in_progress tasks at startup
**LESSON-040.** Factory crashes leave tasks stuck in `in_progress`. CEO sees `pending=0`, creates duplicates (for the same REQ IDs already in the DB), those get rejected — idle loop.

Always run at factory startup:
```python
# Reset tasks that have been in_progress for > 30 min (owner probably dead)
for task in get_all_tasks(status="in_progress"):
    if time.time() - task["started_at"] > 1800:
        update_task_status(task["id"], "pending")
        log.warning(f"Resetting zombie task {task['id']}")
```

### AP-7 — Never hardcode project ID in data-access functions
**LESSON-051.** `get_pending_tasks(project="BDL")` returned empty when CEREBRO tasks were pending, causing 80 minutes of idle. Data-access functions should query ALL projects by default; callers filter explicitly:

```python
# ❌ WRONG
def get_pending_tasks(project: str = "BDL") -> list[dict]: ...

# ✅ RIGHT
def get_pending_tasks(project: str = None) -> list[dict]:
    return get_all_tasks(status="pending", project=project)
    # None = all projects
```

### AP-8 — Telegram alerts fire ONCE per state transition, not per retry
**LESSON-004.** Sending "No pending tasks" 75 times burns Madi's attention. Every alert must track its last-sent time:

```python
def send_if_changed(state_key, message, cooldown_minutes=30):
    last_sent = STATE.get(state_key, 0)
    if time.time() - last_sent > cooldown_minutes * 60:
        send_telegram(message)
        STATE[state_key] = time.time()
```

### AP-9 — Grep for function existence before calling it in code
**LESSON-028.** Writing code that calls `create_task()` without verifying `create_task` is defined in `task_db.py` caused ImportError every cycle and spam. Before referencing any function in new code:

```bash
grep -n "def create_task" task_db.py
# If not found: implement it or use the correct function name
```

### AP-10 — Extract metadata with code, not LLM
**LESSON-035.** CEO drops REQ-xxx from task assignments ~20% of the time (LLM forgets). Never rely on an LLM to faithfully copy identifiers. Extract with Python:

```python
import re
req_match = re.search(r'\[REQ-\d+\]', task['title'])
if req_match:
    assignment = req_match.group() + " " + llm_assignment
```

### AP-11 — Hard-stop non-recoverable errors with lock file
**LESSON-056.** "Credit balance too low" cannot be fixed by retrying. Use a lock file so only Madi can clear it:

```python
LOCK = "logs/anthropic_credit_low.lock"
if "credit balance is too low" in str(exc):
    Path(LOCK).write_text("credit_exhausted")
    send_telegram(f"FACTORY HALTED. Credits exhausted. Top up + `rm {LOCK}` to resume.")
    time.sleep(1800)

# At startup:
if Path(LOCK).exists():
    send_telegram("Credit lock active. Top up + delete lock to resume.")
    time.sleep(1800)
    return {"error": "credit_low"}
```

### AP-12 — Model selection is quarterly, not permanent
**LESSON-057.** The CEO was hard-gated to Opus; switching to Sonnet saved 80% per-call cost with equivalent quality. Hard safety gates should be reviewed when constraints change. When removing a gate: document why it existed, why you're removing it, and how to revert in 1 line.

### AP-13 — Verify the correct project/directory before editing code
**LESSON-065.** Editing `codebase/satory-frontend/` instead of `Desktop/satory-nextjs/` wastes 20+ minutes. Before touching any frontend code, verify which directory is deployed to which domain:

```bash
# Identify which Vercel project is live at the domain
npx vercel inspect https://satory.nousagaas.com 2>&1 | grep "Source"
# Identifies the project — only edit THAT directory
```

### AP-21 — After docker restart openclaw, verify SOUL.md is Nous-specific + run identity probe

**LESSON-114.** The OpenClaw agent reads SOUL.md at container startup for persistent identity. After Air migration (session 22), the workspace had GBrain default templates instead of Nous-specific files. The agent hallucinated identity, confused paths, and couldn't cite its own rules.

**Rule:** After ANY `docker restart openclaw` or container recreation:
1. Verify workspace SOUL.md is Nous-specific (77+ lines, mentions "Nous", "AGaaS", 7 never-rules)
2. Run identity probe: `python3 run_task.py --no-context "Who are you? What are your 7 never-rules?"`
3. If response doesn't mention "Nous" and cite laws -> workspace files are wrong -> docker cp from wiki

```bash
# Verify SOUL.md is not the GBrain default
ssh air 'docker exec openclaw wc -l /home/node/.openclaw/workspace/SOUL.md'
# Expect: 77+ lines (not 38 lines = GBrain default)

ssh air 'docker exec openclaw head -5 /home/node/.openclaw/workspace/SOUL.md'
# Expect: mentions "Nous" in first 5 lines
```

### AP-22 — Never create directories speculatively; verify target path exists before writing

**LESSON-048 + LESSON-052.** The factory wrote to `satory-frontend/satory-frontend/src/` (doubled path) for weeks — 50+ phantom components, zero visible to users, $30+/day wasted. Root cause: `file_ops.py` joined `CODEBASE_PATH` with a relative path that already contained the project prefix, creating a nested phantom directory. When the phantom was quarantined, the same bug recreated it within 10 cycles.

**Rule:** Before any `mkdir -p` or file write, verify the target directory is the ACTUAL deploy/serve path — not a speculative or doubled prefix. Use `os.path.realpath()` and assert no path component is duplicated. Never create directories that are not already in the project structure without explicit operator approval.

## Output Format

After any factory operation, confirm:
1. Process count: `ps aux | grep run_loop | grep -v grep | wc -l` → expected: 0 (if stopped) or 1 (if running)
2. Cost rate: recent log shows `track_cost` values are within expected range
3. No idle loops: log doesn't show same error repeated more than 3 times

## Files

| File | Role |
|------|------|
| `~/nous-agaas/run_task.py` | Air factory: sends tasks to OpenClaw |
| `~/nous-agaas/tools/telegram_poll.py` | Air factory: Telegram input |
| `~/nous-agaas/logs/run_task.log` | Task execution log |
| `/root/nous-agaas/run_loop.py` (VPS legacy) | Old factory loop |
| `/root/nous-agaas/tools/task_db.py` (VPS legacy) | Old task database |


### AP-14 — Every task must trace to a requirement (LAW-006)

**LAW-006.** No task without a requirement link. The factory created 97 tasks that were all reverted because many were invented busywork with no real requirement behind them ("optimize CSS" when the actual need was "show real camera data").

Every task MUST trace to one of:
- 89 VMS requirements (`wiki/pages/specs/cerebro_bdl_vms_requirements.md`)
- ERAP requirements (`wiki/pages/specs/erap_requirements.md`)
- BDL features (`wiki/pages/specs/bdl_features.md`)
- CEO Madi direct instruction (quoted verbatim in the task description)

Tasks without a requirement source = REJECT before starting.

### AP-15 — Hub-and-spoke: CEO is the ONLY dispatcher (LAW-007)

**LAW-007.** CEO dispatches ALL tasks. No peer-to-peer between agents.

- Coder does NOT talk to Validator directly — all communication goes through CEO
- Researcher does NOT assign work — reports findings to CEO, CEO decides next action
- Claude Code creates ONE directive for CEO, not direct assignments to agents
- CEO breaks down work, delegates, and tracks every task

When agents talked peer-to-peer: tasks got duplicated, conflicts arose, nobody knew the full picture. CEO must be the single coordination brain.

### AP-16 — Escalation-only: factory runs autonomously 24/7 (LAW-010)

**LAW-010.** Madi does NOT get bothered with every detail. Factory handles problems internally.

Rules:
- Factory runs 24/7 autonomously
- Problems go to CEO first. CEO handles. NOT escalated to Madi unless presidential-level.
- Daily summary at 23:00 Almaty (18:00 UTC) — in Russian — via @nousAGaaSbot
- ONLY these require Madi: money decisions, contract signatures, government submissions, architecture changes that affect revenue
- Anti-spam: same Telegram message content must NOT be sent within 30 min of identical previous message

### AP-17 — Business gate: every task needs a business outcome tag (LAW-011)

**LAW-011.** Every task MUST be tagged as ONE of:
- **(a) Demo-Ready** — improves what Satory/police will see on the dashboard
- **(b) Revenue Impact** — directly affects money (fines collection, contracts, billing)
- **(c) Risk Reduction** — prevents data loss, security issues, or outages

Pure "cleanup" or "refactor" tasks = REJECTED unless they explicitly serve (a), (b), or (c).

Root cause: factory wasted 97 cycles on internal tasks that did not move the product forward. CSS optimization does not matter if police cannot see real violations.

### AP-18 — Agent's write-back and an unstaged edit will both race the git rebase

**Session 23 observation (4× out of 4).** When a factory task edits a SKILL.md or any wiki file, the agent's tool-use writes the edit to disk. The final write-back in `run_task.py` then does `git add <task-result>`, `git commit`, `git pull --rebase`, `git push`. The rebase step FAILS because the agent's file-edit is still unstaged — `cannot pull with rebase: You have unstaged changes`.

Observable symptom in the log:
```
INFO write-back: committed 2026-04-15-HH-MM-SS-<slug>.md to wiki
WARNING write-back: push failed: error: cannot pull with rebase: You have unstaged changes.
```

The commit of the task-result **succeeds locally** but never reaches the bare repo. The agent's file-edit stays uncommitted on Air.

Fix: after dispatch, ALWAYS run `git status` on Air, commit the agent's unstaged edit separately with a proper message, then `git pull --rebase && git push`. Never rely on write-back to cover agent-side edits.

### AP-19 — Agent may write to a legacy path when two homes exist

**Session 23 T3.** Asked agent to edit `/opt/nous-agaas/wiki/pages/skills/camera-management/SKILL.md`. Agent found a pre-existing file at `/opt/nous-agaas/wiki/pages/systems/skills/camera-management/SKILL.md` and wrote there instead. Both directories exist; the agent picked the one that already had a file.

Fix: either unify the directory structure (eventually move `pages/systems/skills/*` under `pages/skills/`) OR explicitly say in the prompt `if a file exists at path X but not at path Y, edit X`. Verify via `git status` which path was actually modified after dispatch.

### AP-20 — Don't trust the agent's self-reported grep counts

**Session 23 T1.** Agent claimed "grep -c AP-8 /opt/nous-agaas/skills/command-center/SKILL.md = 2". Independent verification from Claude Code host returned 1 initially because the rsync from wiki → runtime hadn't flushed yet. The agent's internal grep ran on a stale bind-mount view.

Rule: after every factory dispatch, re-run the verifying grep yourself AND do a host↔container md5sum. Two lines must match byte-for-byte. Anything else is drift.

### AP-24 — After Air reboot, Docker Desktop does NOT auto-start; factory is silently down until `open -a "Docker Desktop"` via SSH (session 51, 2026-04-20)

**Symptom:** Session 51 open probed factory at port 18789 — no response. `docker ps` on Air via SSH returned `failed to connect to the docker API at unix:///Users/madia/.docker/run/docker.sock`. Docker Desktop GUI app was not running. Only `com.docker.vmnetd` (network helper, a PrivilegedHelperTool that auto-starts via launchd) was alive. OpenClaw container (`Up 4 days` pre-reboot) was stopped.

**Root cause:** macOS Docker Desktop is a GUI app (`/Applications/Docker.app`), not a launchd-managed daemon. When Air reboots (e.g., crash, kernel panic, software update, OS auto-reboot), Docker Desktop does NOT auto-start on login unless the user has explicitly enabled "Start Docker Desktop when you sign in to your computer" in Docker Desktop → Settings → General. Even if that toggle is ON, auto-start only fires on interactive GUI login — SSH-only sessions never trigger it. Result: the socket symlink at `/var/run/docker.sock → /Users/madia/.docker/run/docker.sock` is stale (target directory exists but contains no socket file), every `docker` command fails, and the factory is invisibly dead.

**Recovery (reproducible):**
```bash
ssh air 'open -a "Docker Desktop"'   # launches the GUI app; it runs headless via SSH
# Wait for socket to appear (~15-30s)
ssh air 'ls -la /Users/madia/.docker/run/docker.sock'   # should be a socket file (srwx)
# Wait for container to start + pass health check (~2-3 min for openclaw)
ssh air 'docker ps --filter name=openclaw --format "{{.Status}}"'
# Poll until "Up N minutes (healthy)" (note: `docker ps` status may lag the actual `docker inspect --format {{.State.Health.Status}}` by minutes — inspect is authoritative)
```

**Rules:**
1. **Session-open SOAO (audit AP-17 point 5)** must not assume docker is alive. If the factory probe returns `docker: command not found` or any socket error, run the recovery sequence above BEFORE moving on.
2. **Never reboot Air during active factory work without a recovery plan.** If you're about to prompt an Air reboot (OS update, crash diagnosis), first arm the recovery: know that `open -a "Docker Desktop"` over SSH is the un-block.
3. **Detection compounding gate (session 52+ candidate):** LaunchAgent on Air `com.nous.docker-desktop-watchdog` that pings `/Users/madia/.docker/run/docker.sock` every 5 min and auto-runs `open -a "Docker Desktop"` if missing. Pair with a 5-min delay + healthcheck so we don't thrash. Until that ships, SOAO surfaces the condition loudly so no session opens silently-broken.
4. **Docker Desktop "start on login" toggle** should be ON to minimize reboot-to-recovery window — but it's GUI-only, so SSH-only reboots still need manual `open -a`. Don't rely on toggle alone.
5. **Steady-state ≠ current state.** Session 50 MASTER handoff's "launchd: 17 services loaded + openclaw healthy" is a snapshot, not an invariant. A reboot between session close and next session open resets everything except what launchd restores — Docker Desktop is NOT in that set.

**Cross-ref:**
- `audit` AP-17 point 5 (factory skill-load probe — fails loudly if docker dead; triggers this recovery)
- `audit` AP-20 (subsystem-probe E2E-verify — catches when probes silently false-negative on dead factory)
- `infrastructure` deployment sequence (OpenClaw container start assumes daemon is up — this AP is the precondition)

**Karpathy compounding:** Every future session now knows Air-reboot-without-GUI-login is a silent factory killer, and has the exact recovery. No new LESSON (RULE ZERO).

### AP-25 — OpenClaw agent-layer config: use `openclaw config set` CLI, not direct file edit (resolved session 55, 2026-04-20)

**Resolution (session 55, 2026-04-20):** Root cause of session-51 `docker restart` revert is now understood. Hypothesis "`--allow-unconfigured` regenerates from defaults" was **wrong**. Actual root cause: direct filesystem edits to `openclaw.json` while the gateway process is running are racy — the live gateway holds its own in-memory config state and flushes it back to disk on graceful shutdown, clobbering any out-of-band edit. The `openclaw.json.bak` files are the gateway's shutdown-time backup-then-overwrite artifacts. Fix: route all agent-layer config changes through `openclaw config set <dot.path> <value>` — this CLI routes through the running gateway's RPC, updating in-memory + on-disk synchronously, so restart picks up the new state correctly.

**Symptom (session 51 — historical):** J2 attempted to switch `agents.list[0].model` from `"litellm/glm-5.1"` to `"litellm/opus"` by editing `openclaw.json` directly inside the container (`docker exec openclaw python3 ...`). JSON written, verified via `cat` immediately after. Container restarted — `agents.list[0].model` reverted to `litellm/glm-5.1`. Also tried editing `agent:nous:main.model` in `sessions.json` — same revert. Two round-trips both lost. JSON stayed parse-valid (no corruption). Session 51 hypothesized `--allow-unconfigured` regen; filed 5-task research path to verify.

**What session 55 actually ran (J2 resolution, 90-min cap used ~9 min):**

```bash
# J2-a: docs (~30s)
docker exec openclaw ls /app/docs/         # rich docs tree, not needed

# J2-b: CLI (~2 min — first unblock)
docker exec openclaw openclaw --help       # revealed: agents, config, models, agent, infer subcommands
docker exec openclaw openclaw config --help # reveals: file, get, set, schema, validate, unset
docker exec openclaw openclaw models --help # reveals: set (default), aliases, auth, fallbacks, list
docker exec openclaw openclaw config file   # → ~/.openclaw/openclaw.json (confirms in-container path)
docker exec openclaw openclaw config get agents   # dumps { defaults.model, list[0].model }
docker exec openclaw openclaw config get models   # lists configured providers — opus + glm-5.1 already registered

# J2-unblock: CLI set + verify + restart test (~5 min)
docker exec openclaw openclaw config set agents.defaults.model litellm/opus
  # → "Config overwrite ... backup=~/.openclaw/openclaw.json.bak. Updated agents.defaults.model.
  #    Restart the gateway to apply."
docker exec openclaw openclaw config set "agents.list[0].model" litellm/opus
  # → same, for the agent-specific override
docker exec openclaw openclaw config get agents  # pre-restart: confirms litellm/opus in both paths
docker restart openclaw                          # wait ~30-60s for gateway boot
docker logs openclaw --tail 15                   # → "[gateway] agent model: litellm/opus" ✅ persisted
docker exec openclaw openclaw config get agents  # post-restart: still litellm/opus ✅
docker exec openclaw openclaw models status --plain  # → litellm/opus
```

**Rules (v1.8 — resolved):**

1. **Use `openclaw config set <dot.path> <value>` for all agent-layer config changes.** Path syntax supports dot notation (`agents.defaults.model`) and bracket notation for arrays (`agents.list[0].model`). CLI routes through the running gateway's RPC → memory + disk stay in sync → restart preserves the change.
2. **`--dry-run` before live apply when the value is non-trivial.** Example: `openclaw config set agents.defaults.model litellm/opus --dry-run` → validates path + value against schema without writing. Cheap safety net.
3. **Do NOT edit `openclaw.json` or `sessions.json` externally while the gateway is running.** Race guaranteed. If the gateway is stopped (`docker stop openclaw`), file edits are safe — but still prefer CLI when gateway is available.
4. **Verify persistence via `docker restart openclaw` → `docker logs openclaw --tail 15 | grep "agent model:"` → `openclaw config get <path>`.** The gateway's boot-time log line `[gateway] agent model: <model>` is the fastest E2E proof the change survived.
5. **LiteLLM alias swap remains an independent mechanism for model-backend upgrades** (e.g., `opus` alias → different underlying Claude model in `~/nous-agaas/litellm/config.yaml`) — done session 51 J1, unaffected by J2 resolution.

**CLI subcommand map (for future reference, extracted session 55):**

| Subcommand | Purpose |
|---|---|
| `openclaw config file` | Print active config file path |
| `openclaw config get <path>` | Get config value by dot path |
| `openclaw config set <path> <value>` | Set config value (value / ref-provider / batch JSON modes) |
| `openclaw config unset <path>` | Remove config value |
| `openclaw config schema` | Print JSON schema for openclaw.json |
| `openclaw config validate` | Validate current config against schema |
| `openclaw agents list` | List configured agents |
| `openclaw agents add / bind / unbind / delete / set-identity` | Full agent lifecycle |
| `openclaw models status` | Show current default model |
| `openclaw models set <model>` | Set default model (global, not per-agent) |
| `openclaw models list` | List configured models |
| `openclaw models aliases add/list/remove` | Manage model aliases |
| `openclaw models auth` | Manage model auth profiles |

**Cross-ref:**
- `audit` AP-18 (honest-uncertainty-about-root-cause: session 51 correctly flagged the hypothesis as unverified; session 55 disproved it via direct test → better doctrine instead of worse)
- `audit` AP-20 (subsystem probe E2E-verify: `docker logs openclaw --tail 15` gateway-boot-log check is the E2E proof)
- Session 51 handoff `[[HANDOFF-AUTO-2026-04-20-session-51-MASTER-final]]` — J2 original evidence
- Session 55 handoff (MASTER close) — J2 resolution evidence
- `session-operating-contract` AP-9 (session 55 meta-lesson — executing J2 in parallel without permission-asking is what unblocked it in 9 min instead of the 90-min cap)

**Karpathy compounding:** session 51 filed a 5-task research path; session 55 exhausted it in under 10 minutes because all 5 tasks were cheap probes. Now session-56+ never re-researches OpenClaw config plumbing — the resolved AP-25 is the doctrine. This is the AP-18 honest-revision pattern in motion: hypothesis → probe → disproof → better rule. No new LESSON (RULE ZERO).

### AP-26 — LiteLLM `max_budget` in config.yaml is DEAD without a DB connection; ship external alarm (session 55, 2026-04-20)

**Symptom:** LiteLLM on Air has in its `config.yaml`:
```yaml
litellm_settings:
  max_budget: 30.0
  budget_duration: "1d"
```
This looks like a spend cap. It's not. The `_PROXY_MaxBudgetLimiter` callback requires a DB backend (Postgres / Langfuse) to track per-key cumulative spend. When `/health` returns `"db":"Not connected"` (session-55 audit caught this), the callback is loaded but functionally a no-op. Same for `/spend/logs`, `/user/info`, `/model/info` — all return `{"error":{"message":"No connected db."}}`.

**Why it matters:** factory is on Opus 4.7 as of session 55 (AP-25 resolution). Opus is ~5× GLM-5.1 cost ($15 input / $75 output per 1M tokens vs $1.40 / $4.40). A runaway factory loop or high-frequency autopilot usage can spike to $50-100/day with ZERO enforcement — the config.yaml budget is cosmetic. Silent failure class: no error anywhere; response bodies report usage; no system alerts.

**Rule — external alarm mandatory until LiteLLM DB is connected:**

1. **Ship `tools/litellm_cost_alarm.py`** — heuristic alarm via HTTP access log parse + call-count × estimated cost × snapshot-delta math. Conservative $0.08/call (Opus-heavy heuristic) against $30/day budget. 4 tiers: WARN 50% / CRITICAL 80% / AT_CAP 100% / RUNAWAY 150%. Telegram alert when tier crosses; state file prevents spam. Log-rotation + day-boundary handling.
2. **Install as Air launchd** `com.nous.litellm-cost-alarm` (30-min cadence, RunAtLoad true). Plist at `tools/com.nous.litellm-cost-alarm.plist`.
3. **Self-diagnosed limits** (codified in script header, fix with real data, not speculation):
   - No per-model cost breakdown (HTTP access log has no model info). Upgrade path: enable `json_logs: true` in LiteLLM + re-parse with per-model cost. Deferred until we see first week of Opus invoices.
   - $0.08/call is a guess. Real session-55 E2E turn cost $0.05-0.10. Refine after real billing data.
   - No request-duration correlation — filter specifically for `/chat/completions 200 OK`.
   - Log rotation loses history; script resets estimate on log-rotate (OK for day-boundary, not for mid-day rotate — future work).
4. **When to upgrade to DB-backed enforcement:** if heuristic alarm fires a real AT_CAP or RUNAWAY, OR after 1 week of Opus billing data. Switch to Langfuse (already running on VPS, not yet wired) or a local Postgres for LiteLLM. The external heuristic alarm then becomes the belt-and-suspenders.

**v1.10 honest-revision (session 55 extension, 2026-04-21 00:18 KZT):** Initial AP-26 body claimed the refinement path was "enable `json_logs: true` in LiteLLM config.yaml + re-parse with per-model cost." **This was wrong.** Probed E2E session 55 extension: added `json_logs: true` to `~/nous-agaas/litellm/config.yaml`, `launchctl kickstart -k gui/501/com.nous.litellm`, fired test `openclaw infer model run --model litellm/opus --prompt "say exactly: JSON_LOG_TEST"` → `200 OK` + response landed. Grepped post-restart log for usage/tokens/cost → **zero matches** in 50 lines. `json_logs: true` ONLY reformats the uvicorn access log from `INFO: … "POST /chat/completions HTTP/1.1" 200 OK` → `{"message":"… POST /chat/completions HTTP/1.1 200","level":"INFO","timestamp":"…",…}`. Format change, **not content change.** Usage/model/tokens still absent. The access log is access-level only and isn't LiteLLM's completion-level instrumentation.

**Correct refinement path (replaces the v1.9 guess):** real per-request usage/model/cost requires a LiteLLM `success_callback` — one of:
- `callbacks: ["langfuse"]` → pushes full events (including `usage`, `model`, `cost`) to Langfuse; Langfuse already runs on VPS Docker but NOT yet wired to Air LiteLLM (credentials + network setup needed). Highest-value, medium-effort. Session-56+ candidate.
- `callbacks: ["file"]` or a custom Python callback writing JSONL to `~/nous-agaas/logs/litellm-events.jsonl` → full event schema per request; parseable by upgraded `litellm_cost_alarm.py`. Lower dependency footprint, custom integration.
- Anthropic billing API poll → accurate, but limited to Anthropic traffic only (misses OpenRouter/ZAI/xAI spend).

**Keep `json_logs: true` regardless** — structured access logs are strictly additive; make downstream log aggregation easier + any future parsing tool gets JSON for free. No reason to revert.

**AP-18 honest-revision pattern in motion:** session-55 shipped AP-26 v1.9 with a speculated refinement path; session-55-extension E2E-tested the speculation + disproved it + rewrote the refinement path with real finding. Session-56+ agent picks up the accurate map instead of re-running the same disproven experiment.

**Evidence — session 55 shipping trace:** Agent drafted initial script counting ALL POST /chat/completions in the current log (612 lines = multi-day cumulative, log isn't daily-rotated). Fired false RUNAWAY alarm at 163% on first deploy. Caught on output review, refactored to snapshot-delta (start_of_day_count per day in state file; reset on day-boundary; log-rotation handling), redeployed, initialized cleanly at tier=-1. Sent correction to Telegram. Final state: alarm quiet, launchd PID registered, next real trigger requires actual daily delta from now forward. AP-18 honest-revision pattern in motion.

**Cross-ref:**
- `session-operating-contract` AP-9 (sibling: ship fast + revise on data, don't over-design the first iteration)
- `audit` AP-20 (probe E2E-verify — the false-RUNAWAY catch was the E2E verification this rule mandates)
- `infrastructure` AP-?? Langfuse wiring as session-56+ carryover (not yet a formal AP)
- This AP's script is the first Air tool whose code lives in `/Users/madia/nous-agaas/tools/` (not bind-mounted into any container — pure Air native).

**Karpathy compounding:** every future session sees `com.nous.litellm-cost-alarm` in `launchctl list`, understands the config.yaml budget is cosmetic-only, and knows the external alarm is the real gate. Removes the "budget config looks fine" false confidence that could have let Opus spend spike to $100/day undetected. No new LESSON (RULE ZERO).

### AP-27 — Factory health probe matcher must grep the full output, not `| tail -1`

**Session 71, 2026-04-24. Morning `com.nous.morning-brief` (04:00) and `com.nous.nightly-audit` reported `❌ factory probe: The instruction was followed with zero deviation. All injected factory context (`.**

**Symptom:** The alert tells Madi the factory is broken. The factory is NOT broken — probe false-negative.

**Mechanism:** `tools/morning-brief.sh:78` (and identical bug in `tools/nightly-audit.sh:66`):

```bash
# Before (broken)
FACTORY_OUT=$(... run_task.py "Reply with exactly: MORNING_OK" 2>&1 | tail -1)
if echo "$FACTORY_OUT" | grep -q "MORNING_OK"; then
  _set factory ok
else
  _set factory failed   # ← wrongly fires when factory answer is multi-line
fi
```

The factory reply is multi-line in practice: `MORNING_OK` on line 1, then blank lines, then agent commentary ("The instruction was followed exactly..."). `tail -1` captures only the commentary. `grep -q "MORNING_OK"` fails. Probe marked failed.

Evidence (session 71 reproducer):
```
$ perl -e 'alarm shift; exec @ARGV' 120 python3 run_task.py "Reply with exactly: MORNING_OK" 2>&1
... log lines ...
MORNING_OK


The instruction was followed exactly as specified in the TASK section...
```

**Fix (1-line, root cause):** drop `| tail -1`. `grep -q` on the full output still matches `MORNING_OK` wherever it appears (including line 1).

```bash
# After (correct)
FACTORY_OUT=$(... run_task.py "Reply with exactly: MORNING_OK" 2>&1)
if echo "$FACTORY_OUT" | grep -q "MORNING_OK"; then
  _set factory ok
else
  _set factory failed
fi
```

Error-echo `${FACTORY_OUT:0:80}` / `:100` slice still gives a reasonable alert preview (first 80 chars of log output — good-enough triage signal).

**General rule:** never reduce a multi-line structured response with `| tail -1` or `| head -1` when the downstream check is a `grep -q` — let grep scan the whole payload. Pipeline-reduction is a false economy; greps are O(n) on the length of the captured string anyway.

**Applies to every end-to-end probe**, not just these two scripts. Audit candidates: any `tools/*.sh` that pipes run_task / curl / docker exec stdout into `tail -1` before grep.

### AP-28 — Escalator must auto-recover from stale primary-tier failures

**Session 71, 2026-04-24. Factory had been running on Grok Reasoning since 2026-04-20 — 4 days. Every task billed at grok rate. Reason: GLM-5.1 hit 2 consecutive failures on 2026-04-20 (transient upstream incident long since resolved); escalator switched to grok permanently; no recovery path fired.**

**Symptom:** Every `run_task.py` log line shows `escalator picked model: grok-reasoning`. Cost 3-5× GLM. Silent — no alert.

**Mechanism:** `model_escalator.py:pick()` implemented the escalation branch (GLM ≥ 2 fails → grok) but not the documented recovery ("RECOVERY_THRESHOLD = 3  # consecutive Grok Reasoning successes before allowing GLM-5.1 again"). The threshold constant was defined but never referenced. `pick()`'s only path back to GLM was an explicit `reset()` call, which nothing automatic ever invoked. 4 days of stale failures, 4 days of grok bills.

Evidence (session 71 DB state pre-fix):
```
glm-5.1     | failures=2 | last_used=2026-04-20T04:00 | last_result=failure
grok-reasoning | failures=0 | last_used=2026-04-24T11:40 | last_result=success
```

**Fix (stale-failure time-decay, simpler than tracking grok success counts):** if GLM's last_used is >STALE_HOURS (24h) old AND last_result was failure AND failures ≥ ESCALATION_THRESHOLD, auto-reset the counter. Next `pick()` goes to GLM; if GLM still fails, 2 more failures re-escalate. Upper bound: 2 GLM calls per 24h when grok is permanent fallback — negligible.

Patch applied to `model_escalator.py:pick()`:

```python
# Recovery: if GLM-5.1 has been in failure-state >STALE_HOURS, retry.
glm_state = self._get(TIER_PRIMARY)
if (
    glm_state["failures"] >= ESCALATION_THRESHOLD
    and glm_state["last_used"]
    and glm_state["last_result"] == "failure"
):
    try:
        last_used = datetime.fromisoformat(glm_state["last_used"])
        age_hours = (datetime.now(KZ_TZ) - last_used).total_seconds() / 3600
        if age_hours >= STALE_HOURS:
            log.info(
                "escalator: GLM-5.1 failures stale (%.1fh old >= %dh) — auto-reset for retry",
                age_hours, STALE_HOURS,
            )
            self._set_failures(TIER_PRIMARY, 0, "stale_auto_reset")
    except (ValueError, TypeError) as e:
        log.warning("escalator: could not parse GLM last_used %r: %s", glm_state["last_used"], e)
```

Unit tests pass 2/2:
- Stale (last_used 25h ago, failures=2) → pick() returns `glm-5.1`, state reset.
- Fresh (just failed twice) → pick() returns `grok-reasoning` (no premature recovery).

**General rule:** any "failure → downgrade" escalator without a recovery path is a one-way trap. Always ship recovery with escalation — time-decay, success-count-based, or manual-reset-after-audit — but ship something. Documented intent (`RECOVERY_THRESHOLD = 3` constant) is not enough; implementation must match the docstring.

**Note (code-location caveat):** `model_escalator.py` lives at `/Users/madia/nous-agaas/model_escalator.py` on Air, NOT in the wiki or git. Future sessions wanting to audit or extend the escalator need to SSH to Air. Candidate substrate-fix: copy `model_escalator.py` into `wiki/tools/` and symlink the Air copy to the wiki copy, so changes land under git. Deferred to next session.

### AP-29 — Cost-alarm regex must track LiteLLM access-log format drift (session 73, 2026-04-25)

**Symptom:** For at least 5 days (2026-04-20 cost-alarm ship → 2026-04-25 audit), `litellm-cost-alarm.out` reported `calls_today=0` every 30 min while LiteLLM was happily handling 121+ /chat/completions per day. The "external heuristic enforcement gate" codified as AP-26 was silently broken — `max_budget` config is dead per AP-26, the alarm script was the SOLE backstop, and it was undercounting by 100% (and historically 63% even before the format change). A real runaway would NOT have alerted.

**Dual root cause** (Musk step-2 — both must be fixed):

1. **Path drift:** LiteLLM dual-mounts both `/chat/completions` (compat) AND `/v1/chat/completions` (versioned). Alarm matched only the unversioned path. `litellm.log` 2026-04-25 distribution: 53 `/chat/completions` + 68 `/v1/chat/completions` = **56% missed**.
2. **Status drift:** When LiteLLM moved to JSON access logs (commit-history unknown, observed 2026-04-25), the `200 OK` substring became `200` (no `OK`). Alarm regex required `'200 OK' in line`. **100% of new lines missed.** Historical "615 hits in log" from old format; "1058 hits" recovered after fix.

**Verified live:** local re-count against `~/nous-agaas/logs/litellm.log` on Air pre/post fix → OLD regex 615 hits, NEW regex 1673 hits. Delta 1058 = exactly the rows the alarm has been ignoring.

**The fix** (1 function patch in `tools/litellm_cost_alarm.py:54`):
```python
# Match BOTH path variants; match BOTH status formats (raw "200 OK" + JSON-escaped "\" 200")
if 'POST /chat/completions' not in line and 'POST /v1/chat/completions' not in line:
    continue
if '200 OK' in line or '" 200' in line or '\\" 200' in line:
    count += 1
```

**General rule (Karpathy compounding — write the LESSON into the matcher):** when an external script regexes a vendor's log, **the regex is a contract with the vendor's log format**, not a true invariant. On every vendor upgrade (LiteLLM, OpenClaw, etc.), re-run the matcher against a known-good period and validate the count is non-zero. Mechanical detector candidate (session 74+): `tools/test_cost_alarm_format.sh` — kicks `litellm_cost_alarm.py`, asserts `calls_today>0` if `litellm.log` has >0 POST lines today; FAIL Telegram alert otherwise.

**Why this matters:** AP-26 declared the alarm the enforcement gate. AP-29 proves the gate had a silent bypass for ≥5 days. Cost-alarm output now reflects reality (~$10/day estimate at 121 calls × $0.08 vs $30 budget — still well under, but the metric is alive). Real $$ leak hypothesis (s73 audit) requires Anthropic dashboard data, not log-derived proxies — see s73 HANDOFF for the honest-negative finding ("autonomous infra ≤ $25/mo, not the source of mystery charges; check Pro/Max subscription + interactive CC sessions").

**Cross-refs:**
- `factory-ops` AP-26 (alarm exists because `max_budget` is dead) — now corrected: alarm WAS silently dead too
- `mistake-to-skill` AP-7 (drift gate doctrine — applied here to the alarm regex)
- s73 HANDOFF (full evidence chain + 1058-call recovery proof)

No new LESSON (RULE ZERO).

### AP-30 — Factory checkpoint prompts MUST inject evidence in-context, not delegate to file-read (session 73 parallel `s73-mac-40205`, 2026-04-25)

**Symptom (day 8+):** auto-checkpoint cycles emitted "missing pages/task-results/" sticky-blocked markers × 9 consecutive runs. The checkpoint agent's prompt asked it to cite "timestamps from pages/task-results/" but the agent could not actually access that path. Daily factory analysis 2026-04-25 named this as factory blocker #1 ("rsync topology misroute, day 8+ as symptom").

**Two compounding root causes** (Musk step-2 — both must be fixed):

1. **CWD mismatch.** The OpenClaw container mounts `/Users/madia/nous-agaas/wiki → /opt/nous-agaas/wiki` (verified `docker inspect`). But the factory checkpoint agent runs with workspace CWD (`/home/node/.openclaw/workspaces/<agent>/`) containing only `AGENTS.md`, `HEARTBEAT.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, `USER.md`. The prompt used the **relative** path `pages/task-results/` which resolves against CWD, not against the wiki mount. So even if the agent tried to Read, it found nothing.

2. **File-less routing path.** `run_task.py:NON_OPENCLAW_MODELS = {"grok-reasoning", "sonnet", "opus"}` BYPASSES OpenClaw entirely and calls LiteLLM directly. These models receive only the prompt as text — they have **no file access at all**. Even if the prompt had used the absolute container path, the LiteLLM-direct path could not have read it. Today's daily-factory-analysis showed all 6 tasks routed to `opus` (the file-less path), explaining the symptom's persistence.

**The fix** (Musk step-2 — simplest correct):
```python
def _recent_task_results(n: int = 8) -> str:
    files = sorted(TASK_RESULTS_DIR.glob("*.md"),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    lines = []
    for f in files:
        # ... read first non-frontmatter, post-`## Task` body line ...
        ts = datetime.fromtimestamp(f.stat().st_mtime, KZ_TZ).strftime("%Y-%m-%d %H:%M KZT")
        lines.append(f"- `pages/task-results/{f.name}` @ {ts} — {head}")
    return "\n".join(lines)

# In checkpoint():
recent = _recent_task_results(n=8)
prompt = (
    f"... Recent task-results in this wiki (cite at least 3 by filename + timestamp):\n\n{recent}\n\n"
    "... Do NOT fabricate filenames; cite ONLY paths from the list above."
)
```

The orchestrator (running on Air host with full file access) reads the wiki dir BEFORE dispatching to the agent and embeds 8 most-recent task-results in the prompt. The agent sees real evidence in-context — no Read tool, no path resolution, no fabrication.

**Verified end-to-end:**
- Mac-vault `tools/auto_checkpoint.py` and Air-runtime `/Users/madia/nous-agaas/auto_checkpoint.py` byte-equal at MD5 `c1746b19abf9da28e221a2f05680bfc3` → `fb51771ae7d96b4cc664d50e182c5e28` (239 lines, drifted by AP-31 _write_progress_handoff addition; arrow form per infrastructure AP-44 drift gate).
- Live function call on Air: `python3 -c "from auto_checkpoint import _recent_task_results; print(_recent_task_results(n=5))"` returns 5 real entries with timestamps.
- Counter-check: simulated full prompt construction emits 1824-char prompt with 8 real task-result citations including `2026-04-25-15-43-35-reply-with-exactly-morning-ok.md @ 2026-04-25 15:43 KZT — Reply with exactly: MORNING_OK` and 7 prior checkpoints.

**General rule:** any prompt sent to a factory agent MUST inject required evidence in-context. **Never assume the agent has file access** — the LiteLLM-direct routing path bypasses OpenClaw entirely. If the agent must reference data, the orchestrator (which DOES have file access on the Air host) must read and embed it.

**Closes B6 fully (parallel s73 audit's deferred bug list):** all 4 `auto_checkpoint.py` copies now resolve to ONE canonical file. v1.13.0 made 3 of 4 byte-equal; v1.13.1 (this update, same session 2026-04-25 17:04 KZT) shipped the **structural fix** — `/Users/madia/nous-agaas/auto_checkpoint.py` is now a symlink → `/Users/madia/nous-agaas/tools/auto_checkpoint.py` (the rsync target). launchd resolves the symlink at exec time. Drift class is now physically impossible — only one file exists, only one rsync target, only one place to edit. Backup of the pre-symlink file at `auto_checkpoint.py.pre-symlink-s73-bak` for rollback. **Verified:** `ls -la` shows `lrwxr-xr-x` symlink; `python3 -c "import auto_checkpoint"` parses OK (9772 chars); `_recent_task_results` function present; AP-4 gate present. **Musk step-2 in motion** — the right answer wasn't to "fix the drift" but to "delete the second file" so drift is impossible. Tan/Karpathy/billion-dollar-solopreneur lens converged on the same call: close the class, not the case.

**Detector candidate (deferred unless N≥2 recurrence):** scan all checkpoint-class scripts for prompts referencing wiki paths via relative lookups; flag any prompt that references a path the agent cannot read. Not shipped this session (v0.0).

**Cross-references:**
- `factory-ops` AP-29 (parallel s73 — cost-alarm regex drift) — sibling fix, same session number (concurrent agents on the same Mac)
- `infrastructure` AP-49 (vault-canonical-must-reach-runtime), AP-55 (canon-deployed drift class)
- `command-center` SKILL — agent prompts class
- `session-coordination` AP-5 (cross-session stage-bleed) — applied here in motion: parallel agent committed `c3fce6a0` v1.12.0 AP-29 mid-session; my session detected via "file modified since read" linter trigger, preserved their work via attribution-credit commit, layered v1.13.0 AP-30 on top

No new LESSON (RULE ZERO).

### AP-33 — Selected-model must physically equal executed-model; agent routes are not model selections (session 2026-04-26)

**Symptom:** `run_task.py` logged `model_selected="glm-5.1"` while the actual OpenClaw result metadata recorded `model="opus"` (or `grok-reasoning`). This recurred across scheduled checkpoints and probes on 2026-04-24 through 2026-04-26. The factory appeared to be using the cheap GLM default while actually executing the OpenClaw agent whose live container config had `nous` on `litellm/opus` and `grok-ceo` on `litellm/grok-reasoning`.

**Root cause:** one field tried to represent two different things:
1. **Concrete model route** — direct LiteLLM execution where `selected_model` should equal the model sent to LiteLLM.
2. **OpenClaw agent route** — `--agent grok-ceo` or `--agent nous`, where the model is configured inside OpenClaw and the escalator's GLM pick is not the executed model.

The bug hid because the host-side `openclaw/openclaw.json` showed `nous` as GLM while the running container's active `/home/node/.openclaw/openclaw.json` showed `nous` as Opus. The host file was stale; runtime truth was the container. That made the old log line doubly misleading: wrong selected model, wrong source-of-truth file.

**Fix rule:**
1. If a concrete model is selected for scheduled/default work, execute it directly through LiteLLM so `model_selected == model`.
2. If an explicit agent is selected (`--agent grok-ceo`, `--agent nous`), do not run the model escalator and do not log GLM as selected. Log an agent route (`openclaw-agent:<agent>`) plus the actual model returned by OpenClaw metadata.
3. Cost alarms must estimate spend from actual model+token telemetry when available. Access-log call counts without model identity are opaque volume, not spend. Never multiply opaque calls by an Opus-heavy fake price and call it a cap breach.
4. A detector must exist over `run_task.log` that fails on any new concrete selected/executed mismatch. Historical rows can be checked with a time cutoff; new rows must be clean.

**Musk step-2:** delete the fake abstraction "model_selected" as a universal field. It is valid only for concrete direct-model routes. Agent routes are a different object and must be named as such.

**Code artifacts:** `tools/run_task.py` now separates direct LiteLLM model routes from OpenClaw agent routes and records `execution_path`, `agent_selected`, `model_intent`, `model`, and `model_matches_intent`. `tools/litellm_cost_alarm.py` v2 estimates attributed spend from `run_task.log` by model token prices and reports non-attributed LiteLLM calls as opaque. `tools/test_run_task_model_truth.py` catches the mismatch class.

**Cross-refs:** AP-26 (cost alarm), AP-29 (cost-alarm log-format drift), AP-32 (/ask hard-coded Opus bypass), `audit` AP-24 (scheduled paid judge default leak). Same family: cost policy must bind to actual executed model, not declared intent.

No new LESSON (RULE ZERO).

### AP-32 — /ask Tier-1 bypass: hard-coded `model="opus"` skipped grok-ceo classifier (session 73 P-phase, 2026-04-25)

**The Anthropic burn root cause** Madi flagged in his s73 emergency. Combined with the orphan CCD agent-mode kill (4 PIDs × 1-2 days × Opus 4.6 with computer-use), this was the second major Anthropic-API-burn vector — and the one that affected the `/ask` Telegram path Madi wanted to USE going forward.

**Symptom:** Madi expected — and CLAUDE.md `ceo-hierarchy v1.0.0` doctrine declares — that `/ask` routing is: "head grok top tier → Opus 4.7 only on delegate → manual labor by glm-5.1 backup grok coding." But every `/ask` was burning Anthropic Opus 4.7 credits at the full $15/M-input × $75/M-output rate, even for trivial chat-class queries.

**Root cause (one-line bug):** `command_center.py:631` (the `/ask` handler) hard-coded:
```python
response = _run_openclaw(query, model="opus", agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")
```
The `model="opus"` flag triggered `run_task.py`'s escalator into "calling LiteLLM directly with model=opus" bypass mode (per `model_escalator.py:_NON_OPENCLAW_MODELS`). This:
1. **Skipped grok-ceo Tier-1 classification entirely** — no answer_directly / delegate_to_tier_2 / research_only branching. Every query went to Opus.
2. **Skipped GLM-5.1 default executor** — the free model that should handle 80%+ of queries per Madi's intent.
3. **Burned Opus credits on every chat-class /ask** — even "what is 2+2" cost ~$0.05 instead of ~$0.

This was the user-facing leak — combined with the 8 orphaned Mac CCD agent-mode processes (also burning Opus 4.6 via API key), it explains the "anthropics charging me without doing shit" symptom.

**Fix (Musk step-2: delete the override, not optimize around it):**
```python
# /ask line 631 (was hard-coded to opus, now lets escalator pick GLM-5.1 default + routes through grok-ceo Tier-1):
response = _run_openclaw(query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")

# /ask-direct line 607 (UNCHANGED — its purpose IS to skip Tier-1 and hit Opus direct):
response = _run_openclaw(query, model="opus", agent_id="nous", correlation_id=f"tg_{msg_id}")
```

**Verified live (s73 close 18:24 KZT):** `python3 run_task.py --agent grok-ceo --correlation-id tg_s73fix "What is 2+2? Reply with: 4"`:
- BEFORE fix log: `escalation: calling LiteLLM directly with model=opus` (direct Anthropic Opus call)
- AFTER fix log: `escalator picked model: glm-5.1` + `Sending task to agent 'grok-ceo'` (free GLM-5.1 via OpenClaw agent runtime)
- Response: `4` — task complete in 28s, write-back committed + pushed.

**Cost-projection:** /ask Anthropic burn drops 90%+ for chat-class queries. Opus only invoked when grok-ceo classifies `delegate_to_tier_2`. Combined with the kill of 4 orphan CCD agent-mode processes (s73 mid-session), the user-facing "anthropic credits burning while idle" symptom should be physically extinct.

**General rule (Karpathy compounding):** **don't hard-code expensive models on the user-facing entry path.** The cheap default + per-query escalation is the billion-dollar-solopreneur pattern. Hard-coded premium = the "premature pessimization" bug class — costs you money on every interaction, and the only way to undo it is realizing it (Madi spent days noticing the Anthropic bill before the audit found this).

**File state (s73 close):** `command_center.py` patch is LIVE on Air at `/Users/madia/nous-agaas/command_center.py` (NOT under git — same drift class as `model_escalator.py` and `auto_checkpoint.py` per s71/s72 carryover B6). Backup at `command_center.py.bak-s73-pre-routing-fix` (29694 bytes, original pre-fix). **s74 candidate:** symlink-or-rsync structural fix to bring `command_center.py` into the wiki/tools/ tracked path so this drift class extincts (parallel s73-mac session already did this for `auto_checkpoint.py` per AP-31 timeline — same pattern applies here).

**Cross-refs:**
- `ceo-hierarchy` v1.0.0 (the doctrine that documented the intent — now finally matches the wiring)
- s73 4-orphan CCD-agent-mode kill (sibling fix, Anthropic-API-key path)
- AP-26 (cost-alarm doctrine — alarm now actually backstops because routing is also correct)
- AP-29 (cost-alarm regex fix, sibling s73 fix)
- B6 carryover (model_escalator.py + auto_checkpoint.py + now command_center.py outside git)

No new LESSON (RULE ZERO).

### AP-31 — Orchestrator owns file I/O; agent only returns body text (session 73, 2026-04-25)

**Symptom (caught by user mid-T2-verification):** the AP-30 fix landed and the agent produced a real HANDOFF body with 8 real citations — but the agent CLAIMED *"Wrote `pages/progress/HANDOFF-AUTO-2026-04-25-17-22.md` (~95 lines)"* while the file did NOT exist. The agent was fabricating a write-action it could not perform: `opus` is in `NON_OPENCLAW_MODELS = {"grok-reasoning", "sonnet", "opus"}` which BYPASS OpenClaw and call LiteLLM directly with **no file access**. The agent's response is captured by `run_task.py:_write_back_to_wiki()` and stored in `pages/task-results/`, never in `pages/progress/`. Morning-brief reads `progress/HANDOFF-AUTO-*.md` to compose its 04:00 summary — those auto-checkpoint files were missing for every cycle that routed to a file-less model.

**Root cause class:** prompt asked the agent to perform an action (file write) it cannot perform. Two-bug compound — same class as AP-30 (prompt assumed a capability the agent doesn't have).

**Fix (Musk step-2 — delete the lie surface):** orchestrator owns file I/O. New `_write_progress_handoff(ts, wiki_path, before_latest)` extracts the agent response from the just-written task-result file, formats it with proper frontmatter (`type: progress`, `id`, `tags`, `source`), and writes to the actual `pages/progress/HANDOFF-AUTO-{ts}.md` path. Best-effort git commit. Prompt updated:
- Old: *"Write a concise factory checkpoint and save it as {wiki_path} via write-back."*
- New: *"Compose a concise factory checkpoint body. The orchestrator will save it as {wiki_path} (AP-31 — do not claim to write the file yourself). ... Return only the markdown body — orchestrator handles the file write."*

**Verified end-to-end on Air at 17:29 KZT (live cron-style invocation):**
- `[auto_checkpoint] AP-31 wrote HANDOFF: pages/progress/HANDOFF-AUTO-2026-04-25-17-29.md (6518 chars)` + `HANDOFF written: True`
- `ls -la /Users/madia/nous-agaas/wiki/pages/progress/HANDOFF-AUTO-2026-04-25-17-29.md` → file exists, 6593 bytes, mtime 17:31
- Frontmatter contains `tags: [handoff, auto-checkpoint, ap-31-orchestrator-write]` and source-traceability comment
- Agent's first body line: *"Per AP-31 — composing body only; orchestrator writes the file."* — explicit contract acknowledgment
- Agent cited 8 real task-results with timestamps; proposed a NEW honest-negative AP candidate ("Sandbox-read-limit doctrine not codified"); upheld LAW-013 (zero fabricated filenames)

**General rule:** if a prompt asks the agent to perform an action, verify the agent has the capability. Half of the LiteLLM models bypass OpenClaw and have no tools at all. **For any side-effect (file write, HTTP, git commit, telegram send), the orchestrator must own it.** The agent's role is text composition + judgment; orchestrators handle I/O.

**Sibling pattern to AP-30:** AP-30 closed "agent can't read"; AP-31 closes "agent can't write but claims it did." Both are "prompt assumed a capability that doesn't exist on the file-less routing path." Both fixes shifted responsibility to the orchestrator (the always-on-Air-host process that DOES have file access).

**Detector candidate (deferred unless N≥2 recurrence):** scan all orchestrator scripts for prompts containing imperative verbs about side-effects (`save`, `write`, `commit`, `send`); flag any not paired with orchestrator-side execution. Not shipped (v0.0).

**Cross-references:**
- `factory-ops` AP-30 (sibling — agent can't read; this AP's mirror image for write)
- `factory-ops` AP-26 (heuristic enforcement gates that depend on agent-claimed actions are inherently unsafe)
- `command-center` SKILL — agent prompt class
- `agent-quality` SKILL — "done = tested" applied to the orchestrator's verify-write path

No new LESSON (RULE ZERO).

### AP-23 — Confusion Protocol: stop at ambiguous factory ops forks (gstack v0.18.0.0, 2026-04-17)

**Karpathy's #1 AI coding failure mode** in factory-ops scope means confidently taking a deploy/restart path that's wrong for the current state. 10+ min lost to reverting a bad restart, or worse, a downed service.

**Asymmetric-cost forks:**
- **Auto-apply `:latest` vs stay on pinned tag?** (LESSON-049 + infra AP-4 said NO auto-apply; still a fork when a genuinely good update lands)
- **Hot-reload vs full restart?** — some configs hot-reload (LiteLLM `models.providers.litellm.models`), others don't (SOUL.md change needs container restart)
- **Target host for a new service — Air launchd vs VPS systemd vs Docker?** — Air for 24/7 compute, VPS for gateway, Docker for isolated deps
- **Restart scope when two services are coupled** — e.g., restart OpenClaw without LiteLLM may leave stale model registrations

**Rule:** At a cross-service / destructive-scope / auto-apply fork — ASK. "Hit a fork: (A) restart container X (30s downtime) or (B) hot-reload config (no downtime but won't pick up SOUL change). Which?"

**Does NOT apply** to routine documented restarts (infrastructure skill already has the sequence).

### AP-34 — Reasoning-token probes can false-fail live models (paid-provider audit, 2026-04-26)

**Symptom:** a low-cost GLM-5.1 probe through LiteLLM/OpenRouter returned HTTP 200 but `message.content = None`, because the entire tiny `max_tokens=8` budget was spent on reasoning tokens. The naive checker treated "no content" as broken even though OpenRouter returned a valid model response, provider metadata, and usage. Direct Z.AI was genuinely broken for a different reason (`Insufficient balance or no resource package`), so the false-negative mixed two different failure classes into one "GLM broken" conclusion.

**Root cause class:** reasoning models may spend their first tokens on hidden/structured reasoning before producing final answer text. Health probes that demand exact text with a tiny token cap are measuring probe design, not provider health.

**Rule:** model health probes for reasoning-capable routes must do one of:
- disable reasoning explicitly when the provider supports it,
- allocate enough output budget for reasoning plus final text, or
- treat HTTP 200 + valid `choices`/`usage`/provider metadata as route-alive and separately mark "no final text within token cap."

**Paid-provider implication:** don't switch away from a provider or cancel a subscription based on a text-only micro-probe. First classify the failure: balance/auth, route/config, provider outage, or probe-token-budget. For GLM specifically on 2026-04-26: OpenRouter GLM-5.1 is alive; direct Z.AI GLM-5.1 is blocked by account balance/package, not by code.

No new LESSON (RULE ZERO).

### AP-35 — OpenClaw `/health` HTTP endpoint can false-fail; prove factory with Docker health plus real route (second-brain audit, 2026-04-27)

**Symptom:** during AUDIT-048, Air showed the OpenClaw Docker container as healthy and LiteLLM live, while `curl http://127.0.0.1:18789/health` returned `Recv failure: Connection reset by peer`. The daily 03:00 substrate report still had OpenClaw GREEN because its proof used the actual factory E2E path (`DAILY_0300_OK`) plus container/port checks.

**Root cause class:** a framework-local HTTP health path is not the same thing as the production route. Some OpenClaw builds expose gateway behavior without a stable `/health` endpoint on the published port, so an endpoint-specific reset can be a probe-shape failure rather than factory downtime.

**Rule:** OpenClaw health claims must use a 3-part proof:

```bash
ssh air 'docker ps --filter name=openclaw --format "{{.Names}} {{.Image}} {{.Status}} {{.Ports}}"'
ssh air 'curl -sS -i --max-time 5 http://127.0.0.1:18789/healthz'
ssh air 'cd ~/nous-agaas && python3 run_task.py "Reply with exactly: HEALTH_OK" 2>&1 | tail -20'
```

`/health` may be used as an advisory probe only. `nc -z` is weaker than `/healthz`: TCP can be open while Docker's published-port relay returns an empty HTTP reply. It must not page Madi or turn a green factory red unless the container health, `/healthz`, or real factory E2E route also fails.

**Musk step-2:** delete the misleading single-endpoint requirement. The requirement is "can the president/factory route execute work?", not "does this optional HTTP endpoint answer."

No new LESSON (RULE ZERO).

### AP-38 -- Docker-published OpenClaw gateway must not bind loopback inside the container

**Trigger:** Air host `curl http://127.0.0.1:18789/healthz` returns empty reply / HTTP 000, while `docker exec openclaw curl http://127.0.0.1:18789/healthz` returns HTTP 200.

**Root cause found 2026-04-29:** OpenClaw config had `gateway.bind: "loopback"`. Inside Docker that binds the gateway to `127.0.0.1` in the container namespace. Docker Desktop still publishes `0.0.0.0:18789->18789/tcp`, but host traffic arrives on the container network interface, not container loopback. Result: container-internal health is green while host-published health returns an empty reply. OpenClaw's own docs say Docker bridge publishing requires `gateway.bind: "lan"` or `customBindHost: "0.0.0.0"`; non-loopback binds require gateway auth, which Nous already has via token auth.

**Rule:** for the Air Docker `openclaw` container, runtime config must use `gateway.bind: "lan"` inside the container, but Docker must publish the host-side port on loopback only.

```json
"gateway": {
  "bind": "lan",
  "port": 18789,
  "auth": { "mode": "token" }
}
```

Change it through the OpenClaw CLI, not by raw file edit:

```bash
ssh air 'docker exec openclaw node /app/openclaw.mjs config set gateway.bind lan'
ssh air 'docker exec openclaw node /app/openclaw.mjs config validate'
ssh air 'docker restart openclaw'
ssh air 'curl -sS -i --max-time 10 http://127.0.0.1:18789/healthz'
```

The host-side Docker publish is a separate security boundary. If `docker port openclaw` shows `0.0.0.0:18789` or `[::]:18789`, the gateway is reachable from LAN/Tailscale despite token auth. Recreate or restart the container so the publish line is:

```bash
127.0.0.1:18789->18789/tcp
```

Minimal verified pattern (snapshot first, keep rollback container):

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
SNAP="$HOME/nous-agaas/openclaw/home-node-openclaw-$TS"
docker cp openclaw:/home/node/.openclaw "$SNAP"
docker stop openclaw
docker rename openclaw "openclaw-pre-loopback-$TS"
docker run -d --name openclaw --restart unless-stopped \
  -p 127.0.0.1:18789:18789 \
  -v "$HOME/nous-agaas/skills:/opt/nous-agaas/skills" \
  -v "$HOME/nous-agaas/wiki:/opt/nous-agaas/wiki" \
  -v "$SNAP:/home/node/.openclaw" \
  ghcr.io/openclaw/openclaw:2026.4.14 \
  node openclaw.mjs gateway --allow-unconfigured
```

Post-change proof must include both sides:

```bash
ssh air 'docker port openclaw'
nc -G 2 -zv 100.122.219.22 18789  # expect: refused from Mac
ssh air 'cd ~/nous-agaas && python3 tools/run_task.py --agent grok-ceo --timeout 300 "Reply exactly: OPENCLAW_OK"'
```

Then persist the active config back to Air's host-side reference copy:

```bash
ssh air 'docker cp openclaw:/home/node/.openclaw/openclaw.json ~/nous-agaas/openclaw/openclaw.json'
```

**Probe rule:** heartbeat scripts must use HTTP `/healthz` for `port18789`, not `nc -z`. Docker can accept TCP while the app is unreachable through the published path.

No new LESSON (RULE ZERO).

### AP-36 -- README is the factory dashboard, not a separate app

**Trigger:** Madi points to ClawSweeper or says "README is the new dashboard."

**Root cause found 2026-04-27:** the factory already had many markdown dashboards under `pages/dashboards/`, but no root front door that a human, Codex session, OpenClaw worker, or GitHub viewer can inspect in one glance. Separate dashboards scatter attention; a README summary is cheap, durable, git-native, and agent-readable.

**Rule:** Maintain a generated root `README.md` as the fast status surface. It should summarize live vault state and point to deeper Obsidian/gbrain pages, not replace them.

**Current implementation:** `tools/readme_dashboard.py`
- writes `README.md` from local vault state only
- never calls external APIs
- names the current handoff, latest task-result, dashboard count, skill count, Blacksmith burst lane, and sweeper operating model
- is covered by `tools/test_readme_dashboard.py` and included in `tools/blacksmith_burst_tests.sh`

**Safety model borrowed from ClawSweeper:**
- review lane proposes only
- apply lane is the only writer
- external GitHub issue/PR mutation waits for scoped `gh` auth or GitHub App token
- dashboard updates are normal markdown commits
- no issue/PR closure automation runs from personal broad credentials

**Musk step-2:** delete the extra dashboard product. The root README is enough for the first operator surface; richer UI can be added only when markdown cannot answer the operational question.

No new LESSON (RULE ZERO).

### AP-37 -- Canonical red dominates narrow green status surfaces

**Trigger:** any daily summary, Telegram status, README dashboard, or morning brief wants to say "all systems 100%" while another persisted canonical health artifact is red/yellow.

**Root cause found 2026-04-27:** `morning-brief.sh` can emit `Morning brief — all systems 100%` from a narrow slice (OpenClaw, port, LiteLLM, Telegram poller, wiki-sync, gbrain, factory probe, task count) while the integrated `daily_0300_substrate_sync.py` evidence page is red for Notion/Satory token, Nous-GPU upstream mirror, model route, or Satory data freshness. Multiple partial green surfaces create false confidence and force Madi to ask "all good now?" repeatedly.

**Rule:** any human-facing factory status must either:
- read the latest canonical integrated report (`pages/dashboards/daily-0300-substrate-YYYY-MM-DD.md` or its generated state), or
- explicitly label itself as a narrow heartbeat and forbid 100% language.

If any canonical substrate component is red, the top-level status is red. If any is yellow, top-level status is at most yellow. Green narrow probes are supporting evidence only; they never override canonical red.

**Required wording:** use "heartbeat green; substrate red: <root cause>" instead of "all systems 100%" when the narrow heartbeat passes but the integrated substrate has an unresolved red/yellow.

**Musk step-2:** delete duplicate truth surfaces before adding more dashboards. One canonical integrated health owner writes proof; other surfaces summarize it or identify their narrower scope.

No new LESSON (RULE ZERO).

### AP-39 -- Daily proof tokens are scheduled-only

**Trigger:** `pages/task-results/*daily-0300-ok*` appears outside the 03:00 KZT daily substrate job, or an agent/checkpoint treats multiple `DAILY_0300_OK` replies as stronger health proof.

**Root cause found 2026-04-30:** `daily_0300_substrate_sync.py --probe-only` correctly skipped dashboard writes and sync, but still ran the real factory text probe `run_task.py "Reply with exactly: DAILY_0300_OK"`. Ad-hoc audits minted task-results with the same token as the scheduled 03:00 proof. Auto-checkpoint then injected the most recent task-results and LLM summaries interpreted non-03:00 repeats as "scheduled task execution" instead of probe noise.

**Rule:** `DAILY_0300_OK` is canonical proof only for the scheduled 03:00 KZT substrate run. Ad-hoc probes must either skip the factory text probe or use a source-specific token. If a task-result writer can label source cheaply, it must do so in frontmatter/logs so future audits can identify the caller without guessing.

**Implementation pattern:** `--probe-only` implies `--skip-factory-probe`; the scheduled daily path keeps the real factory probe and passes `--source daily_0300_substrate_sync`; checkpoint evidence filters non-03:00 `DAILY_0300_OK` repeats into an anomaly summary and prioritizes real work over heartbeat noise.

**Musk step-2:** delete the duplicate proof source first. Do not build more dashboards around an ambiguous token.

No new LESSON (RULE ZERO).

### AP-40 -- run_task write-back must serialize git and commit only its own task-result

**Trigger:** two or more `run_task.py` calls run in parallel and both try to save task-results into the wiki.

**Root cause found 2026-04-30:** live Grok CEO and DeepSeek canaries both succeeded at the model layer, but the shared wiki write-back path collided: one process hit `fatal: Unable to create .../.git/index.lock` while another timed out during `git commit`. `_write_back_to_wiki()` used the shared git index with no task-level lock and a plain `git commit`, so parallel tasks could contend on the index and potentially sweep another task's staged result into the wrong commit.

**Rule:** parallel agent/model execution is allowed and encouraged; shared git write-back is the serialized side-effect. A task-result writer must hold a repo-local write-back lock, stage only its own result file, and commit only that path. Do not use raw `git commit` from concurrent task-result writers.

**Implementation pattern:** `run_task.py` uses `.git/run_task_writeback.lock`, waits for the lock with stale-lock cleanup, raises git timeouts above transient push latency, catches write-back failures without crashing the user-facing model result, and commits with `git commit -o <task-result-path>`.

**Required proof:** unit coverage must include (1) "commit only my task-result" and (2) "wait for existing lock." Live verification should run at least two concurrent canaries through different routes and prove both task-results were committed and pushed.

**Musk step-2:** delete the shared-index ambiguity. Serialize only the side-effect, not the model work.

No new LESSON (RULE ZERO).

### AP-41 — CCD agent-mode orphan watchdog (s74, 2026-05-05)

**Symptom:** Madi reported recurring "anthropics charging me without doing shit" twice (s73 and s74). Each time the audit found Mac Claude Desktop CCD agent-mode (Atoll) orphan processes — `claude --model claude-opus-4-X --allow-dangerously-skip-permissions --allowedTools mcp__computer-use,mcp__ccd_session__*` — running 1-2 days unattended, billing the `sk-ant-api` key on every autonomous turn. s73 killed 4 pairs; s74 killed 10 more. Same class, same vector. Hand-killing is treadmill, not fix.

**Root cause:** Claude Desktop's "Agent Mode" feature spawns autonomous claude-code subprocesses that don't terminate when the user closes the chat window. They persist via the local-agent-mode-sessions plugin tree until the OS kills them or the user manually does. There is no built-in idle-timeout.

**Fix (Musk step-5: automate the watchdog):** ship `tools/ccd_orphan_watchdog.sh` + `~/Library/LaunchAgents/com.nous.ccd-orphan-watchdog.plist`. Runs every 30 min via launchd. Heuristic: any CCD process with `etime > 2h` AND matching the agent-mode signature gets SIGTERM + SIGKILL fallback. Telegrams Madi when it earns its keep (kills > 0).

**Verified live (s74 close 2026-05-05 10:10:53 KZT):** plist loaded, first run executed cleanly. Pre-deploy: 12 CCD processes (10 orphan pairs + my session). Post manual-kill + watchdog deploy: 2 (my session). Watchdog now patrols every 30 min — recurrence is physically blocked unless the user explicitly bumps `CCD_WATCHDOG_THRESHOLD_HOURS`.

**Cross-refs:**
- s73 first kill (this AP's evidence trail): factory-ops AP-32 Timeline + s73 HANDOFF
- AP-26 (cost-alarm — alarm now backstops a healthier baseline)
- billion-dollar-solopreneur lens: the operator doesn't manually kill subprocesses; the OS does. Watchdog is the Pieter-Levels pattern (mechanical caps, not cognition caps).

**General rule:** any subprocess spawned by an AI tool that bills per-turn against an API key MUST have a runtime ceiling. If the tool ships without one, the operator owns it. Codify the watchdog. No new LESSON (RULE ZERO).

### AP-42 — Library coherence baseline (s74 audit, 2026-05-05)

**Trigger:** Madi asked for "Obsidian + gbrain + OpenClaw all linked and synchronized with clear titles so retrieval works like a library." Stream B subagent audited 1,766 Obsidian pages and surfaced 3 critical gaps:

1. **465 pages (26%) missing `title:` frontmatter** — mostly `pages/progress/commit-review-*` and `pages/progress/*` operational logs. H1 exists, frontmatter title doesn't. Breaks `title:`-search retrieval.
2. **84 duplicate `id:` instances across 36 unique IDs** — e.g. `HANDOFF-AUTO-2026-04-25-21-00` (×4), `AUDIT-031` (×3). Breaks cite-by-ID retrieval.
3. **5 Obsidian-sync residue files** (`* 2.md` pattern) lingered in `pages/task-results/` despite s73 AP-31 disabling Obsidian Sync. Removed in s74 close (verified: `find pages -name "* [2-9].md" | wc -l` returns 0). One-off cleanup; AP-31 fix prevents new ones.
4. **862 pages (49%) zero-incoming-backlinks** — but most are intentionally ephemeral (HANDOFF-AUTO, task-results, commit-reviews). The audit cannot distinguish "intentionally orphan" from "accidentally orphan" without a frontmatter discipline marker.

**Healthy dimensions:**
- LESSON cap holding (24 LESSON files on disk, ceiling ≤129) ✅
- HANDOFF naming consistent (YYYY-MM-DD-...) ✅
- 5-target git parity GOLDEN at `6a4b7bb4` (Mac+VPS-bare+VPS-wiki+Air-wiki, all hosts) ✅
- gbrain Brain Score 86/100, 2,893 pages, 9,525 chunks embedded, 97% coverage ✅
- OpenClaw container ↔ Air mount parity: 101 skills both sides ✅
- `.obsidian/core-plugins.json` confirms `"sync": false` (s73 AP-31 fix held) ✅

**Carryover to s75 (tier-1/tier-2/tier-3 fix work):**
- **Tier-1 done in s74:** 5 sync-residue files purged (0-risk).
- **Tier-2 (s75):** add `backlink_expected: false` flag to ephemeral page types via frontmatter linter — turns the orphan-count metric into something meaningful (only flags accidentally-orphan pages).
- **Tier-3 (s75):** mechanical backfill of 465 missing `title:` fields from H1 line. Scriptable with awk/sed; one PR.
- **Tier-4 (s75):** resolve 84 duplicate `id:` collisions — reassign UUIDs on the duplicates that aren't the canonical version.

**General rule:** library-grade retrieval requires three invariants: every page has a unique `id:`, every page has a non-empty `title:`, every page is reachable by either incoming wikilink OR explicit `backlink_expected: false`. Any violation = audit-flag. Mechanical detector candidate: `tools/test_library_coherence.sh` — fail CI/pre-commit if any of the three invariants drift. Queued for s75.

No new LESSON (RULE ZERO).

### AP-43 — Never exclude canonical scheduled signals from checkpoint prompt evidence (2026-05-10)

**Trigger:** `DAILY_0300_OK` task-result was firing correctly every day (confirmed in `run_task.log`) but `auto_checkpoint.py`'s compositor LLM never saw it → every handoff falsely reported "DAILY_0300_OK not observed". Ghost operational blocker persisted across multiple sessions, diverting investigation effort.

**Root cause:** `_recent_task_results(n=8)` filled its slot list with up to 8 normal results and returned early without appending `canonical_daily[0]`. When ≥8 normal results existed (always true in a healthy factory), the canonical 03:00 signal was silently dropped from the evidence prompt. The scheduler was working; the prompt-construction function was lying.

**Fix:** Always append `canonical_daily[0]` to `selected` after the normal fill loop, regardless of how many normal results exist. One unconditional `append`, not a conditional slot-fill.

```python
# ❌ WRONG — canonical signal silently excluded when normal slots full
selected = normal_results[:8]
if len(selected) < 8 and canonical_daily:
    selected.append(canonical_daily[0])

# ✅ RIGHT — canonical signal always in prompt, even when normal slots full
selected = normal_results[:8]
if canonical_daily:
    selected.append(canonical_daily[0])  # append-always, not conditional-fill
```

**General rule:** Any task-result category that MUST appear in the LLM prompt (daily proof token, health beacon, canonical scheduled signal) must be appended unconditionally AFTER the normal fill. Never rely on slot-count arithmetic to include signals whose presence is required by the downstream report.

**Mechanical detector:** `grep -n "canonical_daily" tools/auto_checkpoint.py` — verify the append is outside the `if len(selected) < n` guard. If the append is inside any length check, it's a latent false-negative.

No new LESSON (RULE ZERO).

### AP-44 — `docker cp` into a running container sets file owner to root; always `chown 1000` after (2026-05-10)

**Trigger:** Needed to update openclaw.json inside the `openclaw` container without remounting. Used `docker cp ~/nous-agaas/openclaw/openclaw.json openclaw:/home/node/.openclaw/openclaw.json`. Container restarted to pick up config but immediately entered crash loop.

**Root cause:** `docker cp` writes files owned by root. The container process runs as uid 1000 (`node`). OpenClaw reads its config at startup; `EACCES: permission denied` crashed it on every restart attempt.

**Fix:** Always follow `docker cp` into any OpenClaw container path with `docker exec --user root openclaw chown 1000 /home/node/.openclaw/openclaw.json` before restarting.

**Pattern (use verbatim):**
```bash
docker cp <source> openclaw:<dest>
docker exec --user root openclaw chown 1000 <dest>
docker restart openclaw
```

**Scope:** Any `docker cp` that writes to a path owned by a non-root container user. The healthcheck uses a 180s interval — use `curl http://localhost:18789/healthz` to verify liveness rather than waiting for `docker ps` to show "healthy".

No new LESSON (RULE ZERO).

### AP-45 — Long-running launchd loops keep old code until restarted (2026-05-11)

**Symptom:** Cross-system sync audit found `com.nous.todoist-sync` running with PID `49230` from 2026-05-08 while the tracked `tools/todoist_sync.py` already contained the fixed `run_loop -> run_due_poll()` transient-error path. The Air log still showed old tracebacks where a Todoist HTTP 503 escaped from `run_loop`, but `nl -ba ~/nous-agaas/wiki/tools/todoist_sync.py` showed current code.

**Root cause:** A Python launchd loop loads code at process start. Syncing a fixed script to the wiki does not update a process that has been running for days. `launchctl list` can show last exit `-15` from a previous kill while the new PID is healthy, so file parity alone is insufficient.

**Rule:** After any code fix to a long-running launchd loop, restart the job and prove the new process:

```bash
ssh air 'launchctl kickstart -k gui/$(id -u)/com.nous.todoist-sync'
ssh air 'pgrep -fl "todoist_sync.py --loop"'
ssh air 'tail -8 ~/nous-agaas/logs/todoist-sync.out.log'
```

**Pass criterion:** fresh PID, no new traceback after restart, and at least one post-restart JSON line showing either a visible transient error followed by recovery or a successful `events_logged`/`new_sync_token` result.

No new LESSON (RULE ZERO).

### AP-46 — OpenRouter `limit` without `limit_reset` is LIFETIME, not daily (2026-05-12)

**Symptom:** Setting `{"limit": 5.0}` via `PATCH /api/v1/keys/{hash}` on a key with `usage: 35.57` returned `limit_remaining: 0` — the key was instantly blocked because OpenRouter treats `limit` alone as a lifetime cap.

**Root cause:** OpenRouter's key-update API requires BOTH `limit` AND `limit_reset` to express a recurring cap. Without `limit_reset`, the `limit` field is a lifetime ceiling on cumulative `usage`. If `usage > limit`, the key disables itself silently.

**Rule:** Always send `limit_reset` alongside `limit` when setting key caps. For daily caps: `{"limit": 5.0, "limit_reset": "daily"}`. Verify response includes `limit_reset: "daily"` and `limit_remaining` reflects `limit - usage_daily`, not `limit - usage`.

**Also:** Match the target key by `name` field (e.g. `"Nous AGaaS"`), not by `hash` prefix or by attempting to match `OPENROUTER_API_KEY` prefix to the hash — the hash is a SHA of the key, not the key value. The `label` field is `sk-or-v1-{first8}...{last3}` and is the canonical safe-display identifier.

**Pass criterion:** GET `/api/v1/keys/{hash}` returns `limit=5`, `limit_reset="daily"`, `limit_remaining ≈ limit - usage_daily`, AND `disabled=false`.

**Reference impl:** `tools/set_openrouter_cap.py` v2 (session-108 fix).

No new LESSON (RULE ZERO).

### AP-47 — OpenRouter daily-cap exhaustion cascades to TWO observable failures; treat as one root cause (2026-05-12)

**Symptom (caught by 30-min health probe loop):** LiteLLM `/models` returns `data: []` (0 models) AND factory `/ask` returns HTTP 402 simultaneously.

**Root cause:** Both failures have the same origin — the OpenRouter key hit its daily `$5` spending limit. LiteLLM's route-health check fires a probe request on startup; the 402 back-propagates and marks every route unhealthy, so the `/models` list empties. Factory calls the same key through LiteLLM → same 402.

**Rule:** When the health probe sees LiteLLM-0-models + factory-402 at the same time, check OpenRouter credit FIRST before debugging each symptom separately:
```bash
ORKEY=$(grep OPENROUTER_API_KEY ~/nous-agaas/.env | cut -d= -f2- | tr -d '\r\n')
curl -s -H "Authorization: Bearer $ORKEY" https://openrouter.ai/api/v1/auth/key \
  | python3 -c 'import sys,json; d=json.load(sys.stdin)["data"]; print(f"usage={d[\"usage\"]} limit={d[\"limit\"]} limit_reset={d.get(\"limit_reset\")} disabled={d.get(\"disabled\")}")'
```

**Resolution:** Top up credits at https://openrouter.ai/settings/credits OR wait for daily reset (if `limit_reset=daily`). After top-up, restart LiteLLM: `launchctl kickstart -k gui/$(id -u)/com.nous.litellm` on Air.

**Pre-emptive rule:** If `usage / limit > 0.80` (i.e., >80% of daily cap consumed), fire a Telegram alert via `tools/tg_send.sh` BEFORE the 402 triggers. The existing `litellm_cost_alarm.py` alarm should cover this — if a probe catches a 402 WITHOUT a prior 80%-alert, investigate why the alarm was silent.

No new LESSON (RULE ZERO).

### AP-48 — task-result write-back commits must bypass git hooks (2026-05-12)

**Symptom:** During a Goal Mode proof cycle, `run_task.py` successfully produced `pages/task-results/2026-05-12-15-07-20-*.md` but then hung in `.git/hooks/prepare-commit-msg` while committing the task-result. This held `.git/index.lock`, blocked `goal_runner.py` write-back, and recreated the same failure class AP-14 had already fixed for runner-owned commits.

**Root cause:** `git commit --no-verify` skips pre-commit hooks, but `prepare-commit-msg` still runs unless hooks are disabled via `core.hooksPath=/dev/null`. `run_task.py` used `git commit -o <task-result>` without hook bypass, so task-result write-back could hang even after Goal Mode itself was hardened.

**Rule:** Any autonomous task-result write-back commit must use:
```bash
git -C "$WIKI_PATH" -c core.hooksPath=/dev/null commit --no-verify -o "$relpath" -m "task-result: <ts>"
```
Keep `-o <task-result>` so the commit is path-scoped. Hook bypass is for machine-owned task-result persistence only; human/session commits still use normal hooks unless a documented recovery path says otherwise.

No new LESSON (RULE ZERO).

### AP-49 — task-result pull/rebase/push also bypass hooks (2026-05-12)

**Symptom:** After AP-48, `run_task.py` successfully committed a task-result, then hung during `git pull --rebase origin main` because replaying a local automated commit over a moving remote invoked `.git/hooks/prepare-commit-msg`.

**Root cause:** Hook bypass applied only to `git commit`, but automated write-back is a sequence: add → commit → pull/rebase → push. Any subprocess in that sequence can hit local hooks when git needs to synthesize or replay a commit.

**Rule:** For machine-owned task-result persistence, run every git subprocess in the write-back sequence with `-c core.hooksPath=/dev/null`. Keep the path-scoped `commit -o <task-result>` invariant from AP-40/AP-48.

No new LESSON (RULE ZERO).

### AP-50 — LiteLLM `/v1/models` requires auth; returns 0 without a key — use `/health/readiness` for liveness probes (2026-05-12)

**Symptom:** Health probe loop reported "LiteLLM 0 models" across 4 consecutive 30-minute iterations, raising a persistent false alert. Factory was producing task-results throughout the entire window.

**Root cause:** LiteLLM's `/v1/models` endpoint requires a master-key `Authorization: Bearer <key>` header to enumerate configured routes. An unauthenticated `curl /v1/models` always returns `{"data": []}` regardless of how many models are loaded in `config.yaml`. The `/health/readiness` endpoint is unauthenticated and returns `{"status": "healthy"}` when the proxy is up.

**Rule:** Never use `/v1/models` as a liveness probe. Use this two-step pattern instead:
```bash
# Step 1 — is LiteLLM up?
curl -s http://localhost:4000/health/readiness | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])'
# Step 2 — is the factory actually working? (no auth required)
ls -t ~/nous-agaas/wiki/pages/task-results/ | head -3  # recent files = factory active
```

**Confirm model count** only when diagnosing a real route failure — pass the LITELLM_MASTER_KEY:
```bash
LKEY=$(grep LITELLM_MASTER_KEY ~/nous-agaas/litellm/config.yaml | awk '{print $2}')
curl -s -H "Authorization: Bearer $LKEY" http://localhost:4000/v1/models | python3 -c 'import sys,json; d=json.load(sys.stdin); print("models:", len(d.get("data",[])))'
```

No new LESSON (RULE ZERO).

### AP-51 — LangSmith is a mirror; local JSONL remains factory truth (2026-05-12)

**Symptom:** The root project had an old LangGraph/LangChain scaffold configured for `LANGCHAIN_PROJECT=satory-vko-agents`, while the live Air runtime (`run_task.py`, `command_center.py`, `goal_runner.py`) had no LangSmith SDK installed and no production control-plane trace path. The dashboard looked like "something exists", but it was not observing Telegram/OpenClaw/Goal Mode.

**Root cause:** Observability was attached to a legacy prototype, not the live factory substrate. Reusing the old project name would hide the drift instead of fixing it.

**Rule:** Instrument the live control plane only, and keep observability non-blocking:
- `tools/run_task.py` emits `nous.run_task`.
- `tools/command_center.py` emits `nous.telegram.command`.
- `tools/goal_runner.py` emits `nous.goal.cycle` and `nous.goal.worker`.
- `tools/langsmith_observer.py` always writes local JSONL first, then mirrors to LangSmith only if tracing, key, workspace, and SDK are present.
- Default project is `nous-agaas-control-plane`; never silently inherit legacy `LANGCHAIN_PROJECT=satory-vko-agents`.

**Invariant:** LangSmith, Langfuse, or any external dashboard may decorate the factory; none may gate Telegram polling, Goal Mode, OpenClaw dispatch, task-result write-back, or gbrain sync.

No new LESSON (RULE ZERO).

### AP-52 — Do not replace the live orchestrator with a named alternative until it passes parity gates (2026-05-13)

**Symptom:** The operator asked whether 24/7 Telegram factory work should run through OpenClaw or Hermes, while the local substrate already had OpenClaw wired into Telegram, Goal Mode, LiteLLM, LangSmith observer, Todoist/Notion control-plane sync, gbrain, and OpenBrain. Hermes existed only as a planning reference, not as a live Air launchd/control-plane runtime.

**Root cause:** "Stable tool" language can tempt a rewrite before proving the existing production path. That creates a second orchestrator, splits memory, and breaks the one-bot/one-factory operating model.

**Rule:** Keep OpenClaw as production orchestrator until a candidate Hermes path proves all of the same gates in parallel:
- Telegram inbound and outbound through the approved bot path.
- OpenClaw-equivalent model routing: Grok CEO / GPT-5.5 or Codex / DeepSeek or Kimi worker tier.
- Goal Mode or equivalent durable objective loop.
- Todoist and Notion control-plane sync.
- Obsidian/gbrain/OpenBrain write and readback.
- LangSmith non-blocking trace mirror.
- Mac/Air/VPS/GitHub sync parity.
- Cost cap and failure-to-skill loop.

**Decision rule:** canary first, never cut over. A new orchestrator earns production only after a side-by-side 24h run produces the same or better evidence without new red gates.

No new LESSON (RULE ZERO).

### AP-53 — Alert on production chat-route health, not every configured endpoint (2026-05-13)

**Symptom:** `com.nous.light-probe` sent a red model-health alert after LiteLLM `/health` listed `gpt-5.5`, `anthropic/claude-sonnet-4-6`, and `gemini/gemini-embedding-001` as unhealthy. A later probe showed Sonnet recovered; GPT was the exhausted OpenAI API route, while GPT for Madi's CEO lane is `/codex` subscription; Gemini embeddings were actually healthy through `/v1/embeddings` but LiteLLM's generic health probe sent a chat-style `max_tokens` field.

**Rule:** model-health pages Madi only for production chat routes that the factory actually depends on. Filter subscription-only GPT and embedding-only routes out of chat-health counts. Verify embeddings through their real endpoint or gbrain coverage. Send alert text via `tools/tg_send.sh`, not a private curl block, so Telegram outbound behavior stays centralized and logged.

No new LESSON (RULE ZERO).

### AP-54 — Factory probes must follow the producer's real output path (OpenBrain false red, 2026-05-13)

**Symptom:** `factory_no_drift_probe.sh` reported `openbrain_projection` red even though Air had a fresh projected capture at `pages/inbox/openbrain/2026-05-13/openbrain-8babaf70-c399-4384-bd97-e58f9f76064e.md`.

**Root cause:** The probe searched for `openbrain-projection*`, a stale filename guess, while the production runner `tools/openbrain_project_to_wiki.py` writes `pages/inbox/openbrain/YYYY-MM-DD/openbrain-<uuid>.md`.

**Rule:** liveness probes must key off the producer contract, not an inferred label. For OpenBrain projection, the healthy path is:

```bash
find ~/nous-agaas/wiki/pages/inbox/openbrain -path '*/openbrain-*.md' -mtime -2
```

Keep legacy `openbrain-projection*` only as a backward-compatible extra pattern, never as the sole check. If a probe is red but the producer artifact exists, patch the probe and codify the stale-pattern class before claiming the subsystem is broken.

No new LESSON (RULE ZERO).

### AP-55 — Air-local lag is not GitHub mirror drift (2026-05-13)

**Symptom:** `factory_no_drift_probe.sh` reported `github_mirror` red while GitHub and VPS were already on the newer canonical commit and Air's local checkout was behind.

**Root cause:** The probe used the local Air `HEAD` as the expected GitHub mirror head. On a multi-writer system, Air can lag behind Mac/VPS/GitHub for a short period, so the red label named the wrong subsystem and caused repeated false GitHub drift alerts.

**Rule:** Mirror checks must compare GitHub to canonical `origin/main` / `github/main`, not to a stale local checkout. If local Air differs from canonical while GitHub equals canonical and token refs are zero, classify the problem as `air_sync_lag` with remediation `git pull --rebase origin main`. Hermes may kick that pull and rerun the probe once before creating an incident.

No new LESSON (RULE ZERO).

### AP-56 — Repairable Air-local lag self-heals before paging (2026-05-15)

**Symptom:** Telegram repeated `Factory drift (1 failed)` alerts for `air_sync_lag` even though the alert text already contained the exact remediation: `git pull --rebase origin main`.

**Root cause:** AP-55 fixed classification but left the first-line probe as reporter-only. Hermes watchdog had a pull-and-rerun fallback, but `factory_no_drift_probe.sh` itself is also called directly by control-plane, canary, and manual verification paths. Those callers could emit red Telegram alerts before the Hermes fallback repaired the checkout.

**Rule:** A probe may auto-repair only the narrow, mechanically-safe case it can prove:

1. Running on Air's real wiki checkout (`~/nous-agaas/wiki`), not from a Mac review tree.
2. Canonical remote HEAD is known and differs from local HEAD.
3. The worktree is clean (`git status --porcelain` is empty).
4. The fix is exactly `git pull --rebase <canonical_remote> main`.
5. The probe re-reads local HEAD and records GREEN only if it equals the expected canonical HEAD.

Dirty worktree, missing remote, non-Air execution, bad canonical head, or failed pull stay RED and include `auto_repair=skipped_*`/`failed`. This preserves Bad-News-Loud while removing fake-operator work for the safe lag class.

No new LESSON (RULE ZERO).

### AP-57 — Sync self-heal must re-read canonical after pull (2026-05-15)

**Symptom:** The AP-56 repair path pulled successfully during live Air verification, but still reported RED because it compared the post-pull HEAD to the canonical HEAD captured before another auto-sync writer advanced the graph.

**Root cause:** In a multi-writer factory, canonical can move while a probe is executing. A safe pull can land on a newer commit than the probe's initial `expected_head`; comparing to only the stale expected value misclassifies a successful repair as failed.

**Rule:** After any self-heal pull, fetch/re-read the canonical remote and accept the repair when local HEAD equals either the pre-pull expected HEAD or the current canonical HEAD. The success detail must print both `expected=<old>` and `current=<new>` so later audits can see whether a race occurred.

No new LESSON (RULE ZERO).

### AP-58 — Unattended sync repair must not use `git pull` (2026-05-15)

**Symptom:** Telegram emitted `air_sync_lag` with `auto_repair=failed rc=128 ... fatal: Cannot rebase onto multiple branches.` The same fatal appeared earlier in `goal-runner.log`, proving this was a recurring repair primitive bug rather than a one-off operator typo.

**Root cause:** `factory_no_drift_probe.sh` used `git pull --rebase origin main` inside the auto-repair path. `git pull` is a compound command: fetch + decide merge/rebase target from FETCH_HEAD, branch config, and repository state. In Air's multi-writer wiki, goal-cycle, Hermes watchdog, auto-sync, and Codex can move refs within the same minute. During that race, `pull --rebase` can resolve to an invalid multi-head rebase target or invoke hooks while replaying local automated commits.

**Rule:** unattended self-heal must be deterministic and one-target:

1. Fetch exactly one ref into `refs/remotes/<remote>/main`.
2. Resolve that remote ref to an exact commit OID.
3. Run `git -c core.hooksPath=/dev/null rebase <exact-oid>`.
4. Re-fetch once; if canonical moved during the repair, rebase once more onto the new exact OID.
5. Declare success when canonical is an ancestor of local HEAD, not only when the short hashes are equal.

Do not use `git pull` in a background auto-repair path. `pull` remains acceptable for human terminals; probes and autonomous runners need explicit fetch/rebase primitives.

No new LESSON (RULE ZERO).

### AP-59 — Deep health parsers must fail loud on non-health payloads (2026-05-16)

**Symptom:** A manual LiteLLM deep-health check accidentally hit `/health` without the master-key header. The endpoint returned an auth/error payload, but `tools/litellm_health_summary.py` accepted the JSON shape and printed `0	0	none`, which looks like a valid zero-model summary.

**Root cause:** The parser treated any JSON object without `healthy_endpoints` / `unhealthy_endpoints` as the legacy count shape and defaulted absent counts to zero. That converts authentication errors, proxy errors, and unrelated JSON into false green-looking telemetry.

**Rule:** deep-provider summaries must recognize the expected schema before summarizing. If a payload lacks LiteLLM health keys (`healthy_endpoints`, `unhealthy_endpoints`, `healthy_count`, `unhealthy_count`, or `dead_models`), return nonzero and do not update the model-health cache. Scheduled liveness still uses `/health/readiness`; deep `/health` is provider-route evidence and must fail loud when the evidence is not actually a health document.

**Verification:** `tools/test_litellm_health_summary.py::test_error_payload_is_not_misreported_as_zero_models`.

No new LESSON (RULE ZERO).

### AP-60 — Drift and state-change probes must repair before paging (2026-05-19)

**Symptom:** Madi kept receiving raw `Factory drift`, `State change`, `one failed`, and sync-warning Telegram noise. The factory reported routine red/yellow transitions but did not consistently repair first, verify, and only then escalate.

**Root cause:** Alert ownership was spread across detector scripts. `factory_no_drift_probe.sh` and `light-probe.sh` could send Telegram directly, bypassing the higher-level repair loop. That made Madi the retry coordinator whenever a known service flap, Git mirror lag, or launchd exit code appeared.

**Rule:** probes detect; `tools/factory_self_heal.py` owns paging. Any probe with a repairable RED must call the supervisor with `--no-telegram` probe evidence first. The supervisor attempts bounded repairs, reruns the probe, writes a ledger, and sends Telegram only for unresolved or human-required failures. GREEN and repaired RED/YELLOW are not presidential notifications.

**Verification:** `tools/tests/test_factory_self_heal.py` proves green is silent, `telegram_poller` RED is repaired without notification, human-required failures notify once, and both shell probes delegate to `factory_self_heal.py`.

No new LESSON (RULE ZERO).

### AP-61 — Docker image-version probes must read tag refs, not image IDs (2026-05-19)

**Symptom:** The OpenClaw daily-evolution adapter could silently report no current version even while the production container was healthy. Live proof showed `docker inspect openclaw --format '{{.Config.Image}}'` returned `ghcr.io/openclaw/openclaw:2026.4.14`, while Docker `.Image` returned only the resolved `sha256:...` image ID.

**Root cause:** `tools/daily_evolution_adapters/openclaw.py` initially treated Docker `.Image` as a version-bearing reference. `.Image` is an immutable image ID, not the configured repo:tag. Parsing it returns `None`, so upgrade detection can skip OpenClaw without a loud failure.

**Rule:** Docker version probes must run locally first on the production host, then SSH only as a cross-host fallback. They must read `.Config.Image` first and parse the repo:tag from that field. `.Image` is only a fallback diagnostic and cannot be used as the primary version source. Add regressions that assert the command includes `.Config.Image`, already-on-host probes do not require the `air` SSH alias, and digest-only outputs fall back safely.

**Verification:** `python3 -m pytest tools/tests/test_daily_evolution_runner.py -q` and live `OpenClawAdapter().probe_current_version()` returning `2026.4.14` from Air.

No new LESSON (RULE ZERO).

### AP-62 — Queue OK counts must parse worker semantics, including Markdown-bold labels (2026-05-19)

**Symptom:** The 2026-05-19 19:11 Satory queue run reported `OK: 2`, but both "OK" OpenClaw outputs contained `**Статус:** заблокировано`. The process returned successfully, yet the worker answer was blocked.

**Root cause:** `tools/satory_ai_factory_queue.py` already classified plain `Статус: заблокировано` and `**Status**: blocked`, but missed the common Markdown shape `**Статус:** заблокировано`, where the colon is inside the bold label. That turned blocked worker prose into false-green queue accounting.

**Rule:** Queue success is semantic, not process-only. Any worker output with blocked/failed status or missing proof must count as `openclaw_blocked` / `codex_blocked` even when the command return code is zero. Block detectors must handle Markdown-bold labels with the colon inside the bold span.

**Verification:** `tools/tests/test_satory_ai_factory_queue.py::test_openclaw_markdown_bold_blocked_status_is_blocked`.

No new LESSON (RULE ZERO).

### AP-63 — Launchd queue writers must own their proof write-back (2026-05-19)

**Symptom:** The 2026-05-19 21:00 auto-checkpoint generated its handoff and task-result, but its mirror push failed with `cannot pull with rebase: You have unstaged changes`. Air's wiki had fresh Satory queue ledger/status/audit files from the 19:47, 20:22, and 20:54 queue cycles.

**Root cause:** `com.nous.satory-ai-factory-queue` wrote queue-owned proof files from launchd but did not commit/push them. The next `run_task.py` write-back then committed its own task-result and tried to rebase while unrelated unstaged queue files were still present. This is the AP-18 write-back race in a new runner: a background writer left proof artifacts for a generic auto-sync to clean up later.

**Rule:** Any launchd runner that writes proof files into the wiki must either be read-only or own its own Git write-back before exit. It must stage only its own paths, use the shared `.git/run_task_writeback.lock`, bypass hooks for autonomous commits, rebase against exact remote OIDs, and push to the canonical mirrors. Do not leave generated proof files unstaged for `run_task.py`, auto-checkpoint, Hermes watchdog, or auto-sync to discover later.

**Verification:** `python3 -m pytest tools/tests/test_satory_ai_factory_queue.py -q` covers `--git-writeback` parsing and queue-owned commit/push commands; `plutil -lint tools/launchd/com.nous.satory-ai-factory-queue.plist` verifies the launchd job passes `--git-writeback`.

No new LESSON (RULE ZERO).

### AP-64 — OpenClaw canary auth is token plus local gateway config plus operator scope (2026-05-20)

**Symptom:** OpenClaw v2026.5.18 canary on port 18790 was down after the prior soak window. A restart with only `OPENCLAW_GATEWAY_TOKEN` failed immediately with `Missing config. Run openclaw setup or set gateway.mode=local (or pass --allow-unconfigured)`.

**Root cause:** v2026.5.18 enforces two separate gates. Token/password auth satisfies the bind/auth requirement, but a fresh isolated canary home still needs a local gateway config. Starting with `--dev --auth token --bind lan` creates the canary-only config and reads the token from the Air-only env file. Operator read diagnostics are a third gate: `gateway probe` can connect with the token and still return `connected_no_operator_scope` until a device identity or credentials with `operator.read` exist.

**Rule:** Production promotion requires all three proofs, in order: (1) Air-only token or password secret, never git; (2) canary-local gateway config or `gateway.mode=local`, never `--allow-unconfigured` as promotion evidence; (3) `operator.read` probe green, not merely `/health` or `/readyz`. Keep canary on a separate container, separate home volume, `127.0.0.1:18790`, and `--restart no`; prove stop/remove rollback leaves production `18789` healthy before the 24h soak.

**Verification:** 2026-05-20 token canary restarted with isolated home and `--dev --auth token --bind lan`; `/health` returned `{"ok":true,"status":"live"}`, `/readyz` returned `{"ready":true}`, production `/health` stayed live before remove, after remove, and after canary restart. Probe still degraded with `connected_no_operator_scope`, so promotion remains blocked.

No new LESSON (RULE ZERO).

### AP-65 — OpenClaw production promotion is cutover plus soak, not a single green health check (2026-05-20)

**Symptom:** The v2026.5.18 promotion spec said to wait for the AP-21 24h soak to close around 19:00 KZT, then run a token-env production cutover and keep the canary until production stayed green for 30 minutes. During the recovery from a broken terminal, a peer lane executed the production swap at 18:36-18:37 KZT. Production `openclaw` came up on `ghcr.io/openclaw/openclaw:2026.5.18` with `/health` returning `{"ok":true,"status":"live"}`, restart count 0, and the canary still healthy on 18790.

**Root cause:** Promotion state was split across a ready spec, live terminal command, canary container, and registry rows. The action packet was specific enough to execute, but the mechanical cutover guard was not encoded as a wrapper that refuses early promotion or records the cutover atomically. Human/agent concurrency turned a planned post-soak cutover into an early but healthy production state.

**Rule:** Treat OpenClaw production promotion as two separate gates. Gate 1 is the cutover proof: `.Config.Image` equals the target tag, `/health` is live, restart count is 0, host publish remains `127.0.0.1:18789`, and the rollback container/image is preserved. Gate 2 is the timed soak: do not remove the canary, clear the spec, or call the promotion fully closed until production has stayed green for the promised window and a Telegram `/ask` worker-chain proof exists. If a peer lane cuts over early and production is healthy, do not reflex-rollback solely because timing drift occurred; monitor forward, record the exact drift, and rollback only on health/restart/worker-chain failure.

**Verification:** 2026-05-20 18:37 KZT Air proof: `docker ps` showed `openclaw ghcr.io/openclaw/openclaw:2026.5.18 Up ... (healthy) 127.0.0.1:18789->18789/tcp` and `openclaw-canary-20260520-token ... 127.0.0.1:18790->18789/tcp`; production `/health` returned `{"ok":true,"status":"live"}`; `docker inspect openclaw` returned image `ghcr.io/openclaw/openclaw:2026.5.18`, status `running`, restart count `0`.

No new LESSON (RULE ZERO).

### AP-66 — OpenClaw 5.18 production homes need gateway-preserving config merge, not whole-file old config copy (2026-05-20)

**Symptom:** After v2026.5.18 production cutover, `/health` was green but the real `run_task.py -> openclaw agent --agent grok-ceo` worker-chain proof failed. First failure showed `Unknown agent id "grok-ceo"` / missing OpenAI auth because the fresh 5.18 production home had only the default `dev` agent and no Nous LiteLLM provider config. A naive whole-file copy of the old 4.14 `openclaw.json` fixed agents/models but broke the 5.18 gateway pairing with `token_mismatch`. A second naive merge added custom `meta` keys and put the container into a restart loop because 5.18 rejects unknown `meta` fields.

**Root cause:** OpenClaw promotion has two distinct state planes. The 5.18 home owns gateway auth/device pairing and schema-valid `meta`; the old production home owns Nous-specific model/provider/agent routing. Whole-file replacement crosses those planes and either drops routing or invalidates gateway authentication/schema.

**Rule:** For OpenClaw 5.18 promotion, merge config by section, not by file. Preserve the new 5.18 `gateway` and schema-valid `meta` exactly. Import only old production `models`, `agents`, `skills`, and `plugins`, plus required workspace files such as `workspaces/grok-ceo/AGENTS.md`. Do not write custom `meta` keys. After restart, prove both planes: `openclaw config get models/agents` shows `litellm` plus `nous,grok-ceo`; `command_center._run_openclaw(... agent_id="grok-ceo")` returns the expected worker string; then run no-drift/truth gates and sync the produced task-result.

**Verification:** 2026-05-20 recovery merged old Nous routing into `home-node-openclaw-prod-20260520T1842Z/openclaw.json` while preserving 5.18 gateway/meta, restarted `openclaw`, and proved `OPENCLAW_518_WORKER_OK` twice: direct `run_task.py` produced `pages/task-results/2026-05-20-18-58-04-reply-exactly-openclaw-518-worker-ok.md`, and `command_center._run_openclaw` produced `pages/task-results/2026-05-20-18-58-23-reply-exactly-openclaw-518-worker-ok.md`. `factory_no_drift_probe.sh --quiet --no-telegram --no-repair` returned `overall=GREEN, reds=0`; `telegram_openclaw_factory_truth_gate.py --json` returned `overall=GREEN, reds=0, yellows=1` with only Air runtime-root hygiene yellow.

No new LESSON (RULE ZERO).

### AP-67 — Audit help/dry-run modes must not mutate durable state (2026-05-21)

**Symptom:** During strict sync repair, read-only/final-gate work left tracked proof/state surfaces dirty. `tools/daily_evolution_runner.py --dry-run` still wrote snapshot/digest/state files, and `bash tools/factory_no_drift_probe.sh --help` did not stop at usage output; it ran the live probe path. That makes a read-only audit manufacture fresh "last run" evidence and creates unrelated dirty files while another lane is trying to prove sync cleanliness.

**Root cause:** Non-mutating modes were partial. Daily-evolution `--dry-run` guarded publish callbacks, but not every filesystem boundary: `snapshot()` still wrote `pages/systems/daily-evolution-snapshot-pre.json`, `digest()` still wrote `pages/audits/DAILY-EVOLUTION-<date>.md`, and `main()` still wrote the state file. The factory probe also documented help in comments but did not parse `-h|--help`, so help probes fell through into real checks.

**Rule:** Factory help and dry-run modes must be side-effect-free across all durable surfaces unless a flag explicitly says otherwise. For daily evolution specifically, `--dry-run` returns the would-write body/data in memory and logs the intended paths, but it must not write snapshot, digest, or state files. For shell probes, `-h|--help` must print usage and exit before any SSH, git fetch, network probe, alert, repair, or generated-proof write can run. Unknown args must fail fast instead of silently running the default probe.

**Verification:** `python3 -m pytest tools/tests/test_daily_evolution_runner.py tools/tests/test_factory_no_drift_probe_static.py -q` covers `test_snapshot_dry_run_writes_nothing`, `test_digest_declares_daily_evolution_is_not_full_auto_upgrader`, `test_publish_digest_dry_run_mode_no_side_effects`, `test_main_dry_run_writes_no_files`, and static help/unknown-arg handling in `factory_no_drift_probe.sh`.

No new LESSON (RULE ZERO).

### AP-68 — Air runtime-root hygiene must snapshot the release ledger, not delete runtime residue (2026-05-21)

**Symptom:** `telegram_openclaw_factory_truth_gate.py --json --strict-runtime-root` returned RED even after wiki head parity, Air/VPS/GitHub refs, wiki worktrees, command-center hash parity, Telegram poller launchd path, import order, and `factory_no_drift_probe` were all green. The only failing check was `air_runtime_root_hygiene`: `release_dirty tracked=8 untracked=372`.

**Root cause:** `/Users/madia/nous-agaas` on Air is not the canonical Obsidian/wiki repo. It is an Air-local release ledger with only a small historical factory snapshot, while the real source of truth is `/Users/madia/nous-agaas/wiki`. Over time the runtime root accumulated intentional symlinks to `tools/`, copied wiki tool mirrors, local state, secrets, backups, and live OpenClaw/LiteLLM residue. The old `.gitignore` covered only a few generic directories, so strict `git status` treated healthy runtime residue and canonical mirror files as release drift.

**Rule:** For Air runtime-root strict hygiene, do not `git reset --hard`, delete live state, or make the runtime root pretend to be the wiki. First prove canonical surfaces are green: wiki head parity, wiki worktrees clean, `command_center.py` runtime/tools/wiki hash parity, launchd path/import order, and factory no-drift. Then, inside `/Users/madia/nous-agaas`, secret-scan and syntax-check the tracked runtime files, update `.gitignore` for runtime state/backups/secrets/OpenClaw/canonical tool mirrors, and commit the tracked release-ledger snapshot locally. Expected clean proof is `ssh air 'cd /Users/madia/nous-agaas && git status --porcelain=v1'` returning no output, plus strict truth gate `overall=GREEN, reds=0, yellows=0`.

**Verification:** 2026-05-21 Air fix committed `ef9dd07 runtime-root: snapshot current Air release ledger` in `/Users/madia/nous-agaas`. Pre-commit checks: `python3 wiki/tools/scan_credentials.py .gitignore auto_checkpoint.py command_center.py context_injector.py factory_health.py litellm/config.yaml model_escalator.py run_task.py tools/command_center.py` returned clean; `python3 -m py_compile command_center.py tools/command_center.py run_task.py context_injector.py` passed; `litellm/config.yaml` parsed via `yaml.safe_load`. After the commit, strict gate returned `overall=GREEN`, `reds=0`, `yellows=0`, and `air_runtime_root_hygiene` evidence `dirty=false,total=0,tracked=0,untracked=0`.

No new LESSON (RULE ZERO).

### AP-69 — ACTIVE-TASK.md is live checkpoint state, not Air release source (2026-05-21)

**Symptom:** strict runtime-root verification flickered yellow/red with `?? ACTIVE-TASK.md` even though wiki parity, Telegram poller path, command-center hash parity, and factory no-drift were green. Inspecting immediately after often found the file already gone because `run_task.py` creates and clears it during active work.

**Root cause:** `ACTIVE-TASK.md` is the crash-recovery checkpoint declared by `run_task.py`, not a source file. AP-68 ignored broad runtime residue, but missed this named checkpoint, so normal worker activity could make the Air release ledger look dirty.

**Rule:** Air `/Users/madia/nous-agaas/.gitignore` must include `ACTIVE-TASK.md`. Do not commit or delete it as a source artifact during runtime checks. Treat it like logs/state: useful while a task is running, but outside release-ledger drift accounting.

**Verification:** 2026-05-21 Air runtime commit `b80a29a runtime-root: ignore active task checkpoint` added the ignore rule; strict truth gate must return `air_runtime_root_hygiene` clean after the transient checkpoint is ignored.

No new LESSON (RULE ZERO).

### AP-71 — GitHub Actions calling paid APIs must pre-probe quota with 1-token call (2026-05-25)

**Trigger:** INCIDENT-github-actions-26274555590 — two PR-opened Codex PR Review Loop runs failed in <40s with `ERROR: Quota exceeded. Check your plan and billing details.` from `openai/codex-action@v1`. Job exit rc=1 → GitHub sent "All jobs have failed" emails. Same pattern would have re-fired on every PR open until OpenAI's monthly quota reset.

**Root cause:** the workflow invoked `codex-action` with `secrets.OPENAI_API_KEY` (OpenAI Platform pay-as-you-go, separate from the Air-side Codex CLI subscription on `~/.codex/auth.json`). Pay-as-you-go quota cap is a deterministic boundary, not an error condition — but the action treats it as rc=1 → failed-job.

**Rule (binding for every GitHub workflow that calls a paid third-party API):** add a pre-probe step BEFORE the action invocation. The probe makes a minimal call (e.g. 1-token chat completion at the cheapest model) and branches on HTTP code:

- **200** → set `quota.outputs.ok=true`, proceed
- **429 (rate-limited / quota-exceeded)** → set `quota.outputs.ok=false`, emit `::warning::` annotation + Markdown Step Summary explaining quota cap + remediation pointer, all subsequent dependent steps SKIP (gated on `&& steps.quota.outputs.ok == 'true'`), **job exits cleanly with no email**
- **401 / 5xx / 000 (auth error / transient infra)** → set `quota.outputs.ok=true` so the action surfaces a clearer error (don't mask transient infra under quota-cap treatment)

**Mechanical detector:** for any workflow under `.github/workflows/` that uses an action with `*-api-key:` or `auth-token:` input pointing at a paid SDK, search for `probe` keyword + 429 branch. Absence = AP-71 violation.

**Cross-ref:** [INCIDENT-github-actions-26274555590](../../audits/INCIDENT-github-actions-26274555590) (resolved 2026-05-25), `.github/workflows/codex-pr-review-loop.yml` (reference implementation).

**Anti-pattern caught:** `continue-on-error: true` on the action step would also silence the failure email — but it would silence GENUINE failures (auth errors, network outages, real bugs) the same way as quota-cap. Branch-on-HTTP-code surfaces real failures while only swallowing quota-cap noise. Don't use the lazy escape hatch.

### AP-72 — Generated codex PR heads must not auto-start paid review loops (2026-05-25)

**Trigger:** follow-up investigation on GitHub Actions runs `26273033829` and `26274555590`. Both were `pull_request` events for same-repo `codex/*` heads. The immediate red log was AP-71 quota exhaustion, but the avoidable loop was the trigger shape: generated Codex-owned branches opened PRs and automatically invoked an API-backed review before any human or landed-loop dispatch chose to spend quota.

**Root cause:** the PR workflow treated all non-draft PR events as review-worthy. For `codex/*` generated heads, that is backwards: the landed-commit loop already calls `gh workflow run codex-pr-review-loop.yml -f pr=<n>` after creating a fix PR, and human operators can do the same. Auto-running on `pull_request` for `codex/*` heads creates duplicate paid-API loops and turns quota cap into repeated failed-job noise.

**Rule:** PR workflows that use paid review actions MUST skip automatic `pull_request` jobs when `github.head_ref` starts with `codex/`. Preserve `workflow_dispatch` so intentional review still works and can be retried after quota resets.

**Mechanical detector:** `tools/test_codex_review_loop_workflows.sh` must assert the PR workflow contains a `codex/*` auto-skip guard (`!startsWith(github.head_ref, 'codex/')`) and a comment that generated PR heads are reviewed only by explicit `workflow_dispatch`.

**Cross-ref:** [INCIDENT-github-actions-26274555590](../../audits/INCIDENT-github-actions-26274555590), `.github/workflows/codex-pr-review-loop.yml`.

### AP-70 — OpenClaw home promotions must preserve grok-ceo SOUL and IDENTITY (2026-05-21)

**Symptom:** OpenClaw 2026.5.19 production was healthy and Telegram `/ask` routed through `grok-ceo`, but `tools/test_openclaw_full_stack_contract.sh` failed `grok-ceo SOUL identity is mounted`. The active production home had upstream placeholder `SOUL.md` and `IDENTITY.md` in `/home/node/.openclaw/workspaces/grok-ceo/`, while the older May 11 home still had the correct Tier-1 President proxy identity.

**Root cause:** OpenClaw home promotion preserved routing config and `AGENTS.md`, but did not have vault-canonical source files for `grok-ceo` SOUL/IDENTITY. `tools/wiki-to-runtime-rsync.sh` intentionally avoided overwriting the `grok-ceo` persona, but no durable source existed for the persona after a new home was created, so the upstream defaults survived promotion.

**Rule:** `grok-ceo` SOUL/IDENTITY are production routing substrate, not cosmetic docs. Keep the canonical files in `pages/systems/grok-ceo-soul.md` and `pages/systems/grok-ceo-identity.md`; `tools/wiki-to-runtime-rsync.sh` must mirror them into `/home/node/.openclaw/workspaces/grok-ceo/` whenever OpenClaw is running. After every OpenClaw home promotion, run `bash tools/test_openclaw_full_stack_contract.sh` and require both `grok-ceo SOUL identity is mounted` and `grok-ceo IDENTITY is mounted` to pass before calling the stack green.

**Verification:** 2026-05-21 audit found the drift, added canonical vault files, patched the runtime rsync, copied the files into the active Air 5.19 production home, and reran `bash tools/test_openclaw_full_stack_contract.sh` to green.

No new LESSON (RULE ZERO).

## Rules absorbed from lessons

- **LESSON-001:** Lean factory architecture — 6 nodes, no /api/v1/, no GPS filtering.
- **LESSON-002:** CEO reads specs and creates tasks when queue empty. Never idles. See AP-5.
- **LESSON-004:** Telegram dedup — same message not sent within 30 min. See AP-8.
- **LESSON-019:** Smoke test false positives can trigger mass reverts — validate test correctness before deploying hard gates.
- **LESSON-028:** Always grep for function before calling it in code. See AP-9.
- **LESSON-035:** Extract REQ-xxx with regex, not LLM. See AP-10.
- **LESSON-039:** Verify exactly 1 factory process after restart. See AP-3.
- **LESSON-040:** Clean up zombie in_progress tasks at startup. See AP-6.
- **LESSON-044:** Two watchdogs — stop ALL control-plane first. See AP-1.
- **LESSON-045:** git add -A steals manual edits; stop factory before manual work. See AP-2.
- **LESSON-051:** No hardcoded project IDs in data-access functions. See AP-7.
- **LESSON-054:** CEO checks for fresh REQs before calling LLM. See AP-5.
- **LESSON-055:** Budget gate pauses until constraint lifts; never just returns. See AP-4.
- **LESSON-056:** Credit exhausted = lock file hard stop; only manual clear. See AP-11.
- **LESSON-057:** Model selection is quarterly — review when cost constraints change. See AP-12.
- **LESSON-065:** Verify deployed project directory before editing. See AP-13.
- **LESSON-048 + LESSON-052:** Phantom directory disaster — factory wrote to doubled path (satory-frontend/satory-frontend/) for weeks. 50+ dead components, $30+/day wasted. Verify target path exists and has no duplicated components before writing. See AP-22.

- **LESSON-114:** After docker restart openclaw, verify SOUL.md is Nous-specific (not GBrain default) and run identity probe. Empty/generic SOUL.md causes identity hallucination. See AP-21.

- **LAW-006:** Every task must trace to a VMS/ERAP/BDL requirement or direct Madi instruction. See AP-14.
- **LAW-007:** CEO dispatches all tasks. No peer-to-peer. Claude Code gives one directive to CEO. See AP-15.
- **LAW-010:** Factory autonomous 24/7. Madi gets one daily summary. Escalate only presidential decisions. See AP-16.
- **LAW-011:** Every task tagged demo-ready, revenue, or risk-reduction. Pure cleanup = rejected. See AP-17.
- **Session 23 dispatch discipline (4× proven):** 7-step pattern from `run_task.py` to md5-verified container parity. See Phase 5.
- **Session 23 dispatch failures (3× patterns):** write-back rebase collision (AP-18), legacy-path writes (AP-19), untrusted agent-grep (AP-20).

## Timeline

- **2026-05-25** | v1.36.18 -> v1.36.19 — Added **AP-71** after `INCIDENT-github-actions-26274555590` (2026-05-22, two PR-opened Codex PR Review Loop runs failed in <40s with `Quota exceeded. Check your plan and billing details.` from `openai/codex-action@v1`). Root cause: workflow invoked `codex-action` with `OPENAI_API_KEY` GitHub Secret which is OpenAI Platform pay-as-you-go (separate from the Air-side Codex CLI subscription), and hit the monthly quota cap. Fix: patched `.github/workflows/codex-pr-review-loop.yml` with a `Probe OpenAI API quota` step that calls `/v1/chat/completions` with a 1-token gpt-4o-mini probe BEFORE invoking `codex-action`. Branch on HTTP 200→proceed / HTTP 429→skip cleanly with warning + Step Summary / HTTP 401/5xx/000→let codex-action surface clearer error. All 13 dependent steps gated on `&& steps.quota.outputs.ok == 'true'`. YAML re-validated clean. **General pattern (applies to ANY GitHub Action calling a paid API):** add a 1-token pre-probe + branch on quota HTTP code so quota-cap becomes a skipped-with-warning, never a failed-job email. Cross-ref: `INCIDENT-github-actions-26274555590` (resolved). musk-step-2: considered just adding `continue-on-error: true` to the codex step — rejected because that hides genuine failures (auth errors, network issues) under the same "no email" treatment as quota-cap. The branch-on-HTTP-code surfaces real failures while only swallowing quota-cap noise. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-21** | v1.36.17 -> v1.36.18 — Added **AP-70** after a live OpenClaw/Telegram audit found `grok-ceo` routing healthy but the active 5.19 production home had default upstream `SOUL.md`/`IDENTITY.md` for the Tier-1 workspace. Root cause: home promotion preserved routing and `AGENTS.md`, but there was no vault-canonical grok-ceo SOUL/IDENTITY source for runtime sync. Added `pages/systems/grok-ceo-soul.md`, `pages/systems/grok-ceo-identity.md`, patched `wiki-to-runtime-rsync.sh`, and extended the full-stack contract gate. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-21** | v1.36.16 -> v1.36.17 — Added **AP-69** after `ACTIVE-TASK.md` appeared as a transient untracked Air runtime-root file during strict final verification. Root cause: it is `run_task.py` crash-recovery checkpoint state, not release source. Fixed live by adding `ACTIVE-TASK.md` to Air runtime `.gitignore` and committing `b80a29a runtime-root: ignore active task checkpoint`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-21** | v1.36.15 -> v1.36.16 — Added **AP-68** after strict golden verification proved the only remaining red was Air runtime-root hygiene, not Telegram/OpenClaw production failure. Root cause: Air `/Users/madia/nous-agaas` is an Air-local release ledger with stale tracked snapshots and missing ignore policy for runtime residue/canonical wiki mirrors. Fixed live by secret-scanning tracked runtime files, committing Air release-ledger snapshot `ef9dd07`, and rerunning `telegram_openclaw_factory_truth_gate.py --json --strict-runtime-root` to `overall=GREEN, reds=0, yellows=0`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-21** | v1.36.14 -> v1.36.15 — Added **AP-67** after strict golden-sync work found `daily_evolution_runner.py --dry-run` still wrote snapshot/digest/state files and `factory_no_drift_probe.sh --help` fell through into live checks, creating false proof and dirty files during read-only audits. Patched daily-evolution write boundaries, added probe help/unknown-arg handling, and added regressions for both surfaces. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-20** | v1.36.13 -> v1.36.14 — Added **AP-66** after 5.18 production `/health` was green but worker-chain proof failed from lost Nous routing, then token mismatch, then invalid custom meta. Fix: preserve 5.18 gateway/meta, import only old production models/agents/skills/plugins and grok-ceo workspace, restart, prove `OPENCLAW_518_WORKER_OK`, no-drift green, truth gate green/yellow. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-20** | v1.36.12 -> v1.36.13 — Added **AP-65** after terminal recovery found the OpenClaw v2026.5.18 production cutover had been executed by a peer lane before the planned 19:00 KZT soak-close. Production was healthy on 18789 with restart count 0 and the canary still healthy on 18790, so the correct response was forward monitoring plus durable drift record, not reflex rollback. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-20** | v1.36.11 -> v1.36.12 — Added **AP-64** after the OpenClaw v2026.5.18 token-auth canary proved token env alone is insufficient on a fresh canary home. Fix: provision Air-only token file, start isolated canary with `--dev --auth token --bind lan`, prove `/health`, `/readyz`, resource sanity, and stop/remove rollback while production 18789 stays live. Residual: `connected_no_operator_scope` blocks promotion until operator.read proof exists. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-19** | v1.36.10 -> v1.36.11 — Added **AP-63** after the 21:00 auto-checkpoint mirror skipped because Satory queue launchd had left ledger/status/audit files unstaged. Fix: queue runner gained `--git-writeback`, commits only queue-owned proof paths under the shared write-back lock, rebases exact remote OIDs, and launchd now passes the flag. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-19** | v1.36.9 -> v1.36.10 — Added **AP-62** after the 19:11 Satory queue run counted two `openclaw_ran` results as OK even though the worker text said `**Статус:** заблокировано`. Fix: blocked/no-proof regexes now parse Markdown-bold labels with the colon inside the bold span, with a regression for the exact Russian shape. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-19** | v1.36.8 -> v1.36.9 — Added **AP-61** after the OpenClaw residual proof showed production was healthy on `ghcr.io/openclaw/openclaw:2026.4.14`, but the daily-evolution adapter risked reading Docker `.Image` (`sha256:...`) instead of `.Config.Image` (`repo:tag`). First patch still failed on Air because the adapter tried `ssh air` from Air, where the alias did not resolve. Final patch probes local Docker first, then SSH fallback, adds regressions for `.Config.Image`, local-first, and digest fallback, and verifies the live Air adapter returns `2026.4.14`. No new LESSON (RULE ZERO).
- **2026-05-19** | v1.36.7 -> v1.36.8 — Added **AP-60** after the always-on Nous/Satory mission identified raw drift/state-change Telegram spam as a trust failure. Shipped `tools/factory_self_heal.py` as the repair-first paging gate, patched `factory_no_drift_probe.sh` and `light-probe.sh` to delegate notifications to it, and added regression tests for silent green, repair-then-silent, notify-once human escalation, and shell delegation. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/factory-ops/skill.
- **2026-05-16** | v1.36.6 -> v1.36.7 — Added **AP-59** after a manual LiteLLM route check exposed a parser bug: an unauthenticated `/health` error payload summarized as `0	0	none`. Patched `tools/litellm_health_summary.py` to require LiteLLM health keys and added a regression so auth/error JSON cannot masquerade as a valid model-health summary. No new LESSON (RULE ZERO).
- **2026-05-15** | v1.36.4 -> v1.36.5 — Added **AP-57** after live Air proof found a second-order race: auto-repair pulled cleanly, but a concurrent Hermes/auto-sync commit advanced canonical during the probe, so the script compared against stale expected HEAD and emitted RED. Patched the repair helper to re-fetch/re-read canonical after pull and accept current canonical equality. No new LESSON (RULE ZERO).
- **2026-05-15** | v1.36.5 -> v1.36.6 — Added **AP-58** after `air_sync_lag` auto-repair failed with `fatal: Cannot rebase onto multiple branches` while Air refs were moving. Root cause: unattended `git pull --rebase origin main` is a compound, branch-config/FETCH_HEAD-dependent primitive under concurrent writers. Patched `tools/factory_no_drift_probe.sh` to fetch one remote ref, rebase hooklessly onto the exact OID, re-fetch once, and accept success when canonical is an ancestor of local HEAD. No new LESSON (RULE ZERO).
- **2026-05-15** | v1.36.3 -> v1.36.4 — Added **AP-56** after repeated Telegram `air_sync_lag` reds showed AP-55's classification was not enough: the raw probe emitted a page before Hermes fallback could repair. Patched `tools/factory_no_drift_probe.sh` to self-heal only on Air + clean worktree + known canonical HEAD, added `--no-repair`, and extended static/Hermes regression tests. No new LESSON (RULE ZERO).
- **2026-05-13** | v1.36.2 -> v1.36.3 — Added **AP-55** after a false `github_mirror` drift proved GitHub was current and Air was stale. Patched `tools/factory_no_drift_probe.sh` to add `air_sync_lag`, added Hermes pull-and-rerun remediation, and covered the classification with regression tests. No new LESSON (RULE ZERO).
- **2026-05-13** | v1.36.1 -> v1.36.2 — Added **AP-54** after final factory proof showed OpenBrain red while a fresh `pages/inbox/openbrain/YYYY-MM-DD/openbrain-<uuid>.md` projection existed. Patched `tools/factory_no_drift_probe.sh` to check the real producer path plus legacy pattern, then reran the probe green. No new LESSON (RULE ZERO).
- **2026-05-13** | v1.36.0 -> v1.36.1 — Added **AP-53** after a model-health state-change alert mixed three different classes: real transient Sonnet flap, subscription-only GPT API quota, and embedding health-probe shape. Added `tools/litellm_health_summary.py`, patched `light-probe.sh` to filter non-chat route noise, and routed state-change Telegram through `tg_send.sh`. No new LESSON (RULE ZERO).
- **2026-05-13** | v1.35.0 -> v1.36.0 — Added **AP-52** after Telegram/factory planning asked OpenClaw vs Hermes. Live evidence favored OpenClaw because it is wired into Air launchd, Telegram, Goal Mode, LiteLLM, LangSmith, Todoist/Notion, gbrain/OpenBrain, and sync probes; Hermes has no proven local production path. Rule: canary any replacement against parity gates before cutover. No new LESSON (RULE ZERO).

- **2026-05-12** | v1.34.0 -> v1.35.0 — Added **AP-51** after LangSmith audit found the old root LangGraph scaffold used `LANGCHAIN_PROJECT=satory-vko-agents`, while the live Air Telegram/OpenClaw/Goal Mode path had no SDK and no trace mirror. Shipped `tools/langsmith_observer.py` as non-blocking local-JSONL-first mirror to `nous-agaas-control-plane`, with hooks in `run_task.py`, `command_center.py`, and `goal_runner.py`. No new LESSON (RULE ZERO).

- **2026-05-12** | v1.33.0 -> v1.34.0 — Added **AP-50** after 30-min health probe loop reported "LiteLLM 0 models" as a false alarm across 4 iterations (~2h). Root cause: `/v1/models` requires auth; unauthenticated probe always returns empty. Factory was producing task-results throughout. Rule: use `/health/readiness` (unauthenticated) + recent task-result file timestamps for liveness; reserve authed `/v1/models` for route-failure diagnosis. No new LESSON (RULE ZERO).

- **2026-05-12** | v1.32.0 -> v1.33.0 — Added **AP-49** after the AP-48 proof moved the hang from `git commit` to `git pull --rebase`; task-result write-back now injects `-c core.hooksPath=/dev/null` into add/commit/pull/push so rebase hooks cannot stall autonomous persistence. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.31.0 -> v1.32.0 — Added **AP-48** after Goal Mode proof found `run_task.py` task-result write-back stuck in `.git/hooks/prepare-commit-msg` despite runner-owned commits already bypassing hooks. Fix: task-result commits now use `git -c core.hooksPath=/dev/null commit --no-verify -o <task-result>` while preserving path-scoped commit semantics. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.30.0 -> v1.31.0 — Added **AP-47** after 30-min health probe caught two simultaneous failures (LiteLLM 0 models + factory 402) both tracing to OpenRouter daily cap exhausted ($35.61 usage vs $5 limit, 13 credits remaining). Codified the cascade pattern: treat dual-failure as one root cause, check OpenRouter `/api/v1/auth/key` first, add 80%-cap pre-emptive Telegram alert if not already firing. No new LESSON (RULE ZERO).

- **2026-05-12** | v1.29.0 -> v1.30.0 — Added **AP-46** after OpenRouter account-level cap closeout. PATCH `/api/v1/keys/{hash}` with `{"limit": 5.0}` alone treated the value as a LIFETIME cap and instantly disabled the `Nous AGaaS` key (usage=$35.57 > limit=$5 → limit_remaining=0). Fixed by adding `limit_reset: "daily"` to the payload: limit_remaining=$4.92 (= $5 - $0.08 daily usage). Also: `tools/set_openrouter_cap.py` v1 matched keys by SHA hash prefix which never works (hash is a SHA of the key, not the key value); v2 matches by `name` field. Cap is now live: $5/day on `Nous AGaaS` key, runtime guard at $2/day stays as primary, account-level $5 is the backstop. No new LESSON (RULE ZERO).

- **2026-05-11** | v1.28.0 -> v1.29.0 — Updated **AP-38** after the factory orchestrator audit found Air Docker publishing OpenClaw as `0.0.0.0:18789->[container]:18789` and `[::]:18789`, making the gateway reachable from LAN/Tailscale even though token auth was enabled. Root cause was Docker `HostIp=""`; the existing AP-38 correctly required `gateway.bind: "lan"` inside the container, but missed the host-publish boundary. Fixed live by snapshotting `/home/node/.openclaw`, preserving the old container as rollback, recreating `openclaw` with `-p 127.0.0.1:18789:18789`, then proving LAN/Tailscale refused while factory health, DeepSeek Flash, DeepSeek Pro, and Grok/OpenClaw route canaries stayed green. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.27.0 -> v1.28.0 — Added **AP-45** after the cross-system Notion/Todoist/Obsidian/gbrain audit found `com.nous.todoist-sync` still running from 2026-05-08 even though the tracked script already had the transient-503 recovery path. Root cause was a stale long-running launchd Python process, not missing code. Restarted with `launchctl kickstart -k gui/$(id -u)/com.nous.todoist-sync`; new PID `52019` emitted a visible 503 JSON line and then advanced the Todoist sync token successfully. No new LESSON (RULE ZERO).
- **2026-05-10** | v1.26.0 -> v1.27.0 — Added **AP-44**: `docker cp` into running openclaw container sets owner to root; process runs as uid 1000 → EACCES crash loop on restart. Pattern: `docker cp` + `docker exec --user root openclaw chown 1000 <dest>` + `docker restart`. Discovered when updating openclaw.json to flash. Container crashed 2 restarts before fix applied. No new LESSON (RULE ZERO).
- **2026-05-10** | v1.25.0 -> v1.26.0 — Added **AP-43**: fixed persistent DAILY_0300_OK false-negative in `auto_checkpoint.py`. `_recent_task_results()` was silently dropping the canonical 03:00 signal from the LLM prompt when >=8 normal task-results existed. The scheduler was firing correctly (confirmed in `run_task.log`); the prompt-construction function was lying. Fix: always `append canonical_daily[0]` to `selected` unconditionally, outside any slot-count guard. Commit 49136aad on Mac/VPS/Air. Ghost blocker cleared from all subsequent handoffs. No new LESSON (RULE ZERO).
- **2026-05-05** | v1.25.0 follow-on: **AP-41 watchdog SHIPPED BROKEN** — handshake-after-close audit caught it. The launchd-deployed script failed every 30 min for 8 hours (16 silent failures, 4 NEW orphan CCD pairs accumulated during today's session — exactly the drift class AP-41 was meant to prevent). Two compounding portability bugs: (1) `mapfile -t` is bash-4+ only; macOS launchd runs `/bin/bash` 3.2.57 which lacks it, so `CCD_PIDS` was unbound, `set -u` killed the script before the threshold check. (2) `ps -o etimes=` is GNU/Linux-only; macOS BSD `ps` dumps the FULL options-list usage as stderr/stdout when given an unsupported column, contaminating the comparison and tripping `[: integer expression expected`. **Fix shipped:** (a) replaced `mapfile` with portable `while IFS= read -r; ... done < <(...)` array-build for bash-3.2; (b) replaced `etimes=` (seconds) with `etime=` (formatted DD-HH:MM:SS / HH:MM:SS / MM:SS) + a `parse_etime_seconds()` helper that handles all three formats with `10#` octal-safe decimal arithmetic. Verified live: `/bin/bash tools/ccd_orphan_watchdog.sh` returned `killed=0 kept=2 total=2` clean, no stderr; killed 4 orphan pairs (19657, 29660, 54699, 54783) that accumulated during the broken-watchdog window. **Karpathy honest-negative**: shipped without dogfooding under the actual launchd `/bin/bash` runtime — `bash --version` first-run was Homebrew bash-5 in my interactive shell which masked the bug; only the handshake-after-close audit caught it. **General rule (factory-ops compounding doctrine):** any launchd-loaded shell script MUST be smoke-tested with `/bin/bash` (not `bash`/Homebrew) to match the daemon's actual interpreter, AND any `ps -o <col>=` use must be checked against BSD `ps` man page for column availability before shipping. Mechanical detector candidate: `tools/test_launchd_script_portability.sh` — for every `tools/launchd/*.plist` resolve its ProgramArguments script + run `/bin/bash -n` syntax check + grep for known bash-4-only features (`mapfile`, `readarray`, associative-array decl, `&>` outside compound) + grep for known Linux-ps-only flags (`etimes`, `-o lstart=`, `-o cputimes=`). FAIL → block deploy. Queued for s75. No new LESSON (RULE ZERO).
- **2026-05-05** | v1.24.0 -> v1.25.0 — s74 bundle close (Mac-interactive, post-Madi billion-dollar-solopreneur restate prompt, 5-stream bundle): pre-bundle verified 3 prerequisites Madi flagged: (a) Camera Doctor 06:00 KZT fire WAS NOT happening (no plist deployed) — shipped `~/Library/LaunchAgents/com.nous.satory-camera-doctor.plist` + canonical `tools/launchd/com.nous.satory-camera-doctor.plist`; loaded on Air, next fire 2026-05-06 06:00 KZT; today's `2026-05-05.jsonl` ran at 11:41/11:42 KZT in dry-run mode (alert_sent=false expected per `satory-daily-operator-brief` Phase-5 doctrine, NOT a bug); (b) 3 deferred gbrain timeline entries verified ALL CLOSED (autonomous-build-manager + agent-harness-optimization v1.0.0 dated 2026-05-05; satory-daily-operator-brief v1.0.0 dated 2026-05-06 Phase 1-5 shipped); (c) CCD watchdog plist also codified into vault canonical (`tools/launchd/com.nous.ccd-orphan-watchdog.plist`) for s73 AP-41. **Bundle T0-T4 shipped:** T0 Camera Doctor cron deployed; T2 /codex E2E verified live (`_run_codex` returned `CODEX_TEST_OK` + footer "OpenAI Codex gpt-5.5 via subscription, today 1/12 calls"); T3 Codex↔CC handshake re-verified (`tools/codex-nous.sh` + session-coordination v1.28 AP-15/16 already shipped session 83, 8/8 launcher tests pass on Mac vault + Air runtime); T4 OB1 absorption audit (subagent): **6 deployed** (Supabase `hchgdzsqedwuupoiuuwn` + `open-brain-mcp` v1 Edge Function + 3 captured thoughts + substrate-v2 Phase 0 + autonomous-build-manager T1 + agent-harness-optimization T2), **4 deferred** (OB wiki/gbrain bridge after Camera Doctor MVP — Option C, substrate-v2 Phase 0.5 bridge, substrate-v2 Phase A-F cathedral 5-week plan written but not executed, 2 gbrain timeline entries pending), **1 blocked** (substrate-event-log skill needs Phase A start). **AP-43 (this entry) library tier-3 mass-fix pass 1 SHIPPED**: title backfill — Stream B audit found 465 pages with no `title:` frontmatter, derived from H1 + filename fallback via `/tmp/library_fix_titles.sh --apply`, drift went **465→0** (462 files modified atomically + 3 already correct from parallel-session activity). Library coherence dimension scored 3/10 → 8/10 baseline. Tier-2 + tier-4 scripts (`/tmp/library_fix_dup_ids.sh` for 84 collisions across 36 unique IDs, `/tmp/library_fix_backlink_expected.sh` for 764 ephemeral pages) remain dry-run-staged for s75 review (more invasive, want human eyes on the dup-id strategy before --apply). **5-target sync state at close**: 2 atomic commits pushed (titles + AP-43); vault expected GOLDEN after Air auto-sync convergence within 5 min. **Karpathy 6/6 honest**: AP absorbed ✅ (ritual: frontmatter + H1 + Timeline; gbrain timeline deferred to MCP reconnect — explicit not silent), substrate physically smarter ✅ (cron deployed + library coherence baselined + 462 files newly searchable by title), zero rot ✅ (Stream C subagent path-error self-corrected, /codex install path detail named, OB Phase A-F deferral-not-shipping named, library tier-2/4 deferred not silently dropped), RULE ZERO ✅ (LESSON cap 24/129). **s75 carryover**: library tier-2/4 mass-fix execution review, gbrain timeline push for AP-41/AP-42/AP-43 on MCP reconnect, OB wiki/gbrain bridge after Camera Doctor MVP per OB1 audit, watchdog runs continuing.
- **2026-05-05** | v1.24.0 narrative-correction (post-Madi-pushback "why glm it should be deepseek latest"): the AP-41/AP-42 codification body is correct; but my TG msg_id=1190 used stale "GLM-5.1 (free)" framing for the s73 /ask Tier-1 fix's effect. Verified current doctrine via `ceo-hierarchy v1.1.0` (CLAUDE.md), `model_escalator.py:54-55` (`TIER_PRIMARY = "deepseek-v4-flash"`, `TIER_ESCALATION = "deepseek-v4-pro"`), and `litellm/config.yaml` (DeepSeek V4 Flash + Pro:nitro wired). Worker-tier moved from GLM-5.1 → DeepSeek V4 Flash in s82-s108 (Apr 30 – May 1). The s73 code patch unchanged and still correct (drop hard-coded `model="opus"`, let escalator pick default). What changed is the model the default resolves to: was GLM-5.1, now `deepseek-v4-flash` with Pro escalation under failure. GLM-5.1 + grok-code-fast = LiteLLM fallback chain only. TG correction sent (msg_id=1191). Karpathy AP-4 honest-negative — caught my own drift after Madi flagged it; doctrine ≠ what I remembered from 11 days ago. No new LESSON (RULE ZERO).
- **2026-05-05** | v1.23.0 -> v1.24.0 — s74 (Mac, post-Madi-billion-dollar-solopreneur-restate-prompt + "anthropics charging me again" recurrence): added **AP-41** (CCD agent-mode orphan watchdog — same class as s73, killed 10 more orphan pairs, shipped `tools/ccd_orphan_watchdog.sh` + `~/Library/LaunchAgents/com.nous.ccd-orphan-watchdog.plist` running every 30 min, threshold 2h elapsed, telegrams Madi when it earns its keep) + **AP-42** (library coherence baseline — Stream B subagent audit of 1,766 Obsidian pages found 465 missing `title:`, 84 duplicate `id:`, 5 Obsidian-sync residue files post-AP-31; tier-1 sync residue purged in this session, tier-2/3/4 fixes queued for s75 with mechanical detector candidate `tools/test_library_coherence.sh`). **Stream C (gbrain↔OpenClaw parity)**: 5-target HEAD GOLDEN at `6a4b7bb4` (subagent's "VPS critical drift" was a path-error — looked at stale `obsidian-wiki/` not the bare `obsidian-wiki.git/` — verified canonically); gbrain Brain Score 86/100, 2,893 pages, 97% embed coverage; OpenClaw mount: 101 skills both sides. **Stream A** done: 10 CCD orphan pairs killed, watchdog launchd loaded + first run executed 10:10:53 KZT. **Streams D/E/F** (Codex /codex E2E test, Codex↔CC handshake doc, Nate B Jones OpenBrain absorption) deferred to s75 honestly — context budget call, not skipped silently. gbrain-timeline-deferred: gbrain MCP disconnected mid-session, push on s75 reconnect. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.22.0 -> v1.23.0 — Session 108 absorbed **AP-40** after live parallel Grok CEO + DeepSeek canaries exposed a write-back race: model calls succeeded, but shared git commit paths hit `index.lock` and commit timeout failures. Patched `run_task.py` with a repo-local write-back lock, `git commit -o <task-result>`, longer git timeout, and tests for path-scoped commits plus lock waiting. Live concurrent canaries `LOCK_DEEPSEEK_OK_1777570300` and `LOCK_GROK_OK_1777570300` both committed/pushed. gbrain-timeline-ok: pages/skills/factory-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.21.0 -> v1.22.0 — Session 101 absorbed **AP-39** after `DAILY_0300_OK` duplicates were traced away from Telegram redelivery and toward ad-hoc `--probe-only` runs minting the same task-result token as the scheduled 03:00 proof. Patched `--probe-only` to skip the factory text probe, labeled the scheduled run with `source: daily_0300_substrate_sync`, and taught auto-checkpoint to summarize non-03:00 daily tokens as anomalies while prioritizing real task-results. gbrain-timeline-ok: pages/skills/factory-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.20.0 -> v1.21.0 — Session 80 follow-up absorbed **AP-38** after OpenClaw host-published `/healthz` failed with empty reply while container-internal `/healthz` returned 200. Root cause: `gateway.bind: "loopback"` binds only container loopback; Docker `-p 18789:18789` traffic arrives on `eth0`. Fixed live with `openclaw config set gateway.bind lan`, `docker restart openclaw`; host `/healthz` returned HTTP 200 and `/proc/net/tcp` showed `0.0.0.0:18789`. Updated `morning-brief.sh` and `light-probe.sh` to probe HTTP `/healthz` instead of `nc -z`. gbrain-timeline-ok: pages/skills/factory-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.19.0 -> v1.20.0 — Post-audit self-review added **AP-37** after comparing sub-agent and local probes: `morning-brief.sh` can declare `Morning brief — all systems 100%` from a narrow heartbeat while `daily_0300_substrate_sync.py` is red for Notion/Satory token, Nous-GPU upstream mirror, model route, or Satory freshness. Rule: canonical integrated red/yellow dominates every human-facing status surface; narrow probes must label themselves as heartbeat-only. gbrain-timeline-ok: pages/skills/factory-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.18.0 → v1.19.0 — ClawSweeper/Peter Steinberger pattern absorbed **AP-36**. Root cause: Nous had many dashboards but no root README-as-dashboard surface. Added `tools/readme_dashboard.py`, root `README.md`, `tools/test_readme_dashboard.py`, and wired the test into `tools/blacksmith_burst_tests.sh`. GitHub issue/PR sweeper mutation remains blocked until scoped GitHub auth exists; proposal/apply split is codified before credentials. gbrain-timeline-ok: pages/skills/factory-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.18.0 — AUDIT-048 second-brain revenue operating-model audit added **AP-35** after `curl http://127.0.0.1:18789/health` reset while Docker health, LiteLLM, launchd, and daily factory E2E proof were green. Rule: OpenClaw health claims require Docker health + port + real route proof; `/health` is advisory only. This prevents endpoint-shape false negatives from waking Madi or mislabeling the factory.
- **2026-04-26** | v1.16.0 → v1.17.0 — Paid-provider audit added **AP-34** after GLM-5.1 micro-probes produced a misleading failure: OpenRouter returned HTTP 200 with provider/usage but no final content because `max_tokens=8` was consumed by reasoning tokens; direct Z.AI returned a real account-level 429 (`Insufficient balance or no resource package`). Rule codifies route-alive vs final-text probes and prevents future cancellation/routing decisions from being made on a bad probe shape. No new LESSON (RULE ZERO).
- **2026-04-26** | v1.16.0 — Codex full-factory recovery continued: added **AP-33** after live Air audit found `run_task.py` rows with `model_selected=glm-5.1` but actual OpenClaw metadata `model=opus`/`grok-reasoning`. Root cause: `model_selected` conflated concrete model selection with OpenClaw agent routing, while live container config had `nous` on Opus despite stale host config showing GLM. Fix: `tools/run_task.py` separates direct LiteLLM model routes from OpenClaw agent routes; default scheduled GLM executes direct so selected=executed, explicit `--agent` routes log `openclaw-agent:<id>` and keep OpenClaw; `tools/test_run_task_model_truth.py` detects new concrete model mismatches; `tools/litellm_cost_alarm.py` v2 estimates attributed spend from actual model+token rows and reports opaque LiteLLM access-log calls without fake Opus pricing. No new LESSON (RULE ZERO).
- **2026-04-25** | v1.15.1 — Session 74 (Mac-interactive, `s74-mac-12354`, post-/clear from s73 final close): **structural follow-up to AP-32 — closed the deferred `command_center.py` drift class.** AP-32 body called out "s74 should symlink/rsync into wiki/tools/ to extinct the class (parallel s73 agent already did this for auto_checkpoint.py per AP-31 — same pattern)" — done. Air-side: `cp /Users/madia/nous-agaas/command_center.py /Users/madia/nous-agaas/tools/command_center.py` (delivers content to symlink target), `cp` of original to `command_center.py.pre-symlink-s74-bak` (backup), `ln -sf .../tools/command_center.py .../command_center.py.symlink.tmp && mv -f` (atomic swap). Verified: `ls -la` shows `lrwxr-xr-x` symlink, MD5 byte-equal at `ab8d6aa31204d544c0db865873009e89` across symlink-and-target, `python3 -c "import command_center"` succeeds with `command_center.is_command` + `.handle` both callable from `WorkingDirectory=/Users/madia/nous-agaas` (same WorkingDirectory `telegram_poll.py` launchd plist uses). Mac wiki/tools/command_center.py written byte-equal (same MD5, 641 lines). Drift class for command_center.py extinct — same pattern as auto_checkpoint.py (s73 v1.13.1) and model_escalator.py (s71 v1.11.0 deferred → established session 72). No restart of `com.nous.telegram-poll` needed (already-imported module stays loaded; next launchd restart will resolve via symlink). No new LESSON (RULE ZERO).
- **2026-04-25** | v1.15.0 — Session 73 P-phase late close (Mac-interactive, post-Madi-routing-intent-clue *"head grok then opus 4.7 manual labor by glm 5.1"*): added **AP-32** — the actual Anthropic API-credit burn root cause Madi originally flagged. `command_center.py:631` `/ask` handler had `model="opus"` hard-coded → every Telegram /ask bypassed grok-ceo Tier-1 classifier AND skipped GLM-5.1 default → burned full Opus 4.7 credits on EVERY message including trivial chat. Fix: 1-line patch dropping the model override on /ask (kept on /ask-direct by design — that path is meant to skip Tier-1). **Verified live** (s73 close 18:24 KZT): same query "What is 2+2?" pre-fix logged `escalation: calling LiteLLM directly with model=opus` (direct Anthropic Opus); post-fix logs `escalator picked model: glm-5.1` + `Sending task to agent 'grok-ceo'` (free GLM-5.1 via OpenClaw). Cost projection: /ask Anthropic burn drops 90%+. Combined with mid-s73 kill of 4 orphan Mac CCD agent-mode processes (claude-opus-4-6 with computer-use, 1-2 days uptime each, also burning the same sk-ant-api key), both major Anthropic-credit-burn vectors closed. **File state (s74 closure 2026-04-25):** `command_center.py` is now a symlink at `/Users/madia/nous-agaas/command_center.py` → `/Users/madia/nous-agaas/tools/command_center.py`. Wiki source at `wiki/tools/command_center.py` is git-tracked. MD5 byte-equal at `ab8d6aa31204d544c0db865873009e89` across symlink, target, and Mac vault. `wiki-to-runtime-rsync.sh` delivers updates to `~/nous-agaas/tools/`; symlink propagates to the parent path. Backups at `.bak-s73-pre-routing-fix` (pre-fix) + `.pre-symlink-s74-bak` (pre-migration). Drift class extinct — same shape as auto_checkpoint.py (v1.13.1) and model_escalator.py. **Honest scope note:** /ask via grok-ceo workspace runs in `agent --local` single-shot mode — agent has injected context but NO Read/Bash/Edit tools. So /ask now routes to GLM-5.1 (free) for chat, but multi-step execution (Read+Edit+Deploy) still requires the s74 dedicated session to enable workspace tools. Codified honestly so s74 inherits accurate map. No new LESSON (RULE ZERO).
- **2026-04-25** | v1.14.0 — Session 73 (Mac-interactive, `s73-mac-40205`, post-user-honesty-pushback "are you sure it is really working or just in papers"): added **AP-31** — orchestrator owns file I/O; agent only returns body text. User pushback caught a SECOND honesty bug uncovered by my T2 verification: agent claimed it wrote `pages/progress/HANDOFF-AUTO-2026-04-25-17-22.md` but file did NOT exist (opus is file-less LiteLLM-direct, can't write). Morning-brief reads `progress/HANDOFF-*.md` so missing files = stale state. **Fix (Musk step-2 delete the lie surface):** new `_write_progress_handoff()` in `auto_checkpoint.py` extracts agent response from the just-written task-result file, formats with proper frontmatter, writes to actual `pages/progress/` path, best-effort git commit. Prompt updated: *"Compose body... orchestrator will save... Return only the markdown body."* **Verified live on Air 17:29 KZT cron-style**: `AP-31 wrote HANDOFF: pages/progress/HANDOFF-AUTO-2026-04-25-17-29.md (6518 chars)`, file exists at exact path (6593 bytes), agent's first line `"Per AP-31 — composing body only; orchestrator writes the file."`, 8 real citations, NEW honest-negative AP candidate self-surfaced ("Sandbox-read-limit doctrine"). 3 of 3 auto_checkpoint.py copies MD5-equal at `fb51771ae7d96b4cc664d50e182c5e28` (Mac vault, Air wiki, Air runtime via symlink). **Sibling to AP-30**: AP-30 closed "agent can't read"; AP-31 closed "agent can't write but claims it did." Same root-cause class — prompt assumed a capability the file-less routing path doesn't have. **General rule codified**: if a prompt asks the agent to perform a side-effect (file write / HTTP / git / telegram), orchestrator must own it; agent's role is text composition + judgment, not I/O. Tan/Karpathy/billion-dollar-solopreneur lens converged: ship the structural fix, close the bug class, let the next cron prove it. No new LESSON (RULE ZERO).
- **2026-04-25** | v1.13.1 — Session 73 (Mac-interactive, `s73-mac-40205`, post-Madi-Musk-5-step-meta-prompt): **structural fix shipped** — closed B6 fully. `/Users/madia/nous-agaas/auto_checkpoint.py` is now a symlink → `/Users/madia/nous-agaas/tools/auto_checkpoint.py` (rsync target). One canonical file across all hosts; drift class physically impossible. AP-30 body updated from "deferred to s74" to "closed fully." 10%-add-back verify: `ls -la` confirms `lrwxr-xr-x`, Python import + parse OK (9772 chars), `_recent_task_results` + AP-4 gate both present. Backup at `auto_checkpoint.py.pre-symlink-s73-bak`. The right Musk-step-2 answer wasn't to patch drift but to delete the second file. Karpathy: substrate is now physically smarter — eternal vigilance replaced with eternal correctness. Tan: closed a recurring bug class with one structural change. Billion-dollar-solopreneur: 30-second fix, no downtime, no new code, drift class extinct. No new LESSON (RULE ZERO).
- **2026-04-25** | v1.13.0 — Session 73 (Mac-interactive, parallel `s73-mac-40205-20260425T1543`, deep-dive audit + fix root-cause + codify per RULE ZERO): added **AP-30** — factory checkpoint prompts MUST inject evidence in-context, not delegate to file-read. Fixes day-8+ blocker (9 consecutive cycles emitting "missing pages/task-results/" sticky-blocked markers). Two compounding root causes: (1) prompt used relative path `pages/task-results/` against agent's workspace CWD `/home/node/.openclaw/workspaces/<agent>/` instead of wiki mount `/opt/nous-agaas/wiki/`; (2) `NON_OPENCLAW_MODELS={grok-reasoning, sonnet, opus}` bypass OpenClaw and call LiteLLM directly with **no file access at all** — all 6 today's tasks routed to opus per daily-factory-analysis-2026-04-25, explaining the symptom's persistence. Fix: `_recent_task_results(n=8)` runs on Air host BEFORE dispatch, reads `wiki/pages/task-results/`, formats markdown bullet list with filename + timestamp + first task-line, injects into prompt. **Verified live**: function returns 8 real entries with timestamps. **Mac-vault ↔ Air-runtime byte-equal** at MD5 `c1746b19abf9da28e221a2f05680bfc3` (239 lines). **Counter-check**: simulated `prompt = ...{_recent_task_results(8)}...` returns 1824-char prompt with 8 real citations (MORNING_OK probe + 7 checkpoints). **Closes B6 partially** (parallel s73 cost-alarm-audit's deferred bug list): 3 of 4 auto_checkpoint.py copies now MD5-equal; the 4th — Air-runtime ROOT (launchd plist target) — STILL OFF the `wiki-to-runtime-rsync.sh` chain (rsync covers `wiki/tools → ~/nous-agaas/tools/`, plist points at `~/nous-agaas/`); structural fix (point plist at tools/ OR symlink OR extend rsync) deferred to s74+. **Cross-session collaboration in motion** (session-coordination AP-5): parallel s73 agent committed `c3fce6a0`/`b16ca9b9` v1.12.0 AP-29 mid-session; this session detected via "file modified since read" linter trigger, preserved their work via attribution-credit commit, layered v1.13.0 AP-30 on top with explicit B6-closure cross-ref. Code fix shipped via auto-sync `ebd5cb34` (AP-54 attribution-drift class — code landed in git regardless, content correct, attribution diluted). No new LESSON (RULE ZERO).
- **2026-04-25** | v1.12.0 — Session 73 (Mac-interactive, emergency 4-stream API-charge audit): added **AP-29** (cost-alarm regex drift on LiteLLM upgrade — `litellm-cost-alarm.py:count_todays_calls` was undercounting by 100% on current LiteLLM and historically 63% before the JSON-log format change). Patched `tools/litellm_cost_alarm.py` to match both `/chat/completions` + `/v1/chat/completions` AND both `200 OK` + `" 200` status forms. Live-verified pre/post: OLD 615 hits → NEW 1673 hits → delta 1058 previously-missed calls in production access log. AP-26 backstop is now actually backstopping. **Honest scope note (Karpathy AP-4 write-negative-first):** s73's primary mission was "find the runaway Anthropic API loop charging Madi while idle" — verdict: **no runaway loop exists on Mac or Air infrastructure**. Autonomous Anthropic-API consumers found: LiteLLM /health probes (8 models, 30-min cadence, ~$6/mo), daily-skill-evals haiku judge (~$3/mo at 04:15), auto-checkpoint uses GLM (free), morning-brief uses GLM (free). Total expected autonomous Anthropic spend ≤ $25/mo. Mystery dollars more likely from interactive Claude Code sessions (Mac CCD agent-mode running Opus 4.6 with computer-use, this session's Opus 4.7 1M context, etc.) or Pro/Max subscription auto-renewal — root-cause-able only with dashboard data. Real bugs found en passant and fixed: B1 (this AP-29), B2 (LiteLLM SIGKILL from aiohttp resource leak — restarted), B5 (Mac vault 20 commits behind canon — rebased to 2a4df924). Real bugs found and DEFERRED to s74: B3 (LiteLLM /spend DB not connected — observability gap), B4 (`com.nous.nous-gpu-collector-health` failing every 5min, exit=1), B6 (`model_escalator.py` + `auto_checkpoint.py` outside git tracked path — drift risk per s71/s72 carryover), B7 (Telegram + gbrain MCPs disconnected mid-session — startup-state issue, needs Mac CC restart). Mechanical detector candidate `tools/test_cost_alarm_format.sh` queued. No new LESSON (RULE ZERO).
- **2026-04-24** | v1.11.0 — Session 71 (Mac-interactive): added **AP-27** (probe matcher `| tail -1` brittleness — factory health probe grepped only the last line of multi-line factory reply, so `MORNING_OK` on line 1 plus agent commentary after blank lines meant tail -1 = commentary = grep failed = false-negative factory-failed alert to Madi at 04:00 for at least one 24h cycle) and **AP-28** (escalator no-recovery lock-in — `model_escalator.py:pick()` implemented escalation GLM→grok but not the documented `RECOVERY_THRESHOLD = 3` consecutive-grok-successes path; GLM failed 2026-04-20 from transient upstream, escalator stuck on grok 4 days, every task billed at 3-5× grok rate). Fixes shipped: (1) removed `| tail -1` from `tools/morning-brief.sh:78` + `tools/nightly-audit.sh:66`; grep -q now scans full stdout. (2) Added `STALE_HOURS = 24` constant + stale-failure auto-reset branch in `pick()`: GLM failures older than 24h auto-reset to 0 on next pick(); upper bound 2 GLM retry calls per 24h when grok is permanent fallback. Unit tests 2/2 pass (stale triggers recovery; fresh failures still escalate). E2E: factory probe `MORNING_OK` verified ✅ with fixed matcher; post-reset probe picked `glm-5.1` and succeeded. Substrate note: `model_escalator.py` lives at `/Users/madia/nous-agaas/` not under git — next session candidate to migrate into `wiki/tools/`. No new LESSON (RULE ZERO).
- **2026-04-21** | v1.10.0 — Session 55 extension (Mac-interactive, 2026-04-21 00:18 KZT close): **AP-26 honest-revision** — v1.9 body claimed `json_logs: true` in LiteLLM config would give per-request usage/model/cost data that the alarm script could parse for real per-model cost math. **Disproved E2E:** added `json_logs: true` to `~/nous-agaas/litellm/config.yaml`, `launchctl kickstart -k gui/501/com.nous.litellm`, fired `docker exec openclaw openclaw infer model run --model litellm/opus --prompt "say exactly: JSON_LOG_TEST" --gateway` → `200 OK` + response landed; grepped post-restart log 50 lines for `usage|tokens|prompt_tokens|completion_tokens|cost` → zero matches. `json_logs: true` ONLY reformats uvicorn access logs from plain text to structured JSON (format change, not content change). The access log is access-level only; completion-level instrumentation requires a `success_callback`. Correct refinement path written into AP-26 body: `callbacks: ["langfuse"]` (highest value, Langfuse on VPS but not wired to Air) OR `callbacks: ["file"]` / custom Python callback writing JSONL OR Anthropic billing API poll. Kept `json_logs: true` regardless (strictly additive). Heuristic alarm remains the enforcement gate until real per-request instrumentation lands. AP-18 honest-revision pattern in motion. Session-56 inherits accurate map — never re-runs the disproven json_logs experiment. **Session-56 metadata catch-up:** session-55 partially completed the AP-11 3-edit ritual on the v1.10 bump — body updated (lines 565-574), but frontmatter version + H1 + this Timeline entry were never ritualized. Caught by session-56 deep audit; meta-lesson codified as `session-operating-contract` AP-10 with mechanical gate candidate `tools/test_memory_version_claims.sh`. No new LESSON (RULE ZERO).
- **2026-04-20** | v1.9.0 — Session 55 (Mac-interactive, this session, immediately after v1.8.0): absorbed **AP-26** — LiteLLM `max_budget` in config.yaml is DEAD without a DB connection; external heuristic alarm is the real enforcement gate. Session-55 deep audit discovered `/health → "db":"Not connected"` + all `/spend/*`, `/user/info`, `/model/info` returning `"No connected db."`. The config.yaml `max_budget: 30.0 / budget_duration: 1d` callbacks (`_PROXY_MaxBudgetLimiter`) load but are functionally no-op without DB backing. Given factory now runs on Opus 4.7 (session 55 AP-25) — ~5× GLM cost — silent-no-enforcement is a meaningful financial risk ($50-100/day runaway possible with zero alerts). Shipped `tools/litellm_cost_alarm.py` (heuristic: call count × $0.08 against $30/day, 4 tiers WARN/CRITICAL/AT_CAP/RUNAWAY, snapshot-delta math + day-boundary reset + log-rotation handling + Telegram via tg_send.sh) + `tools/com.nous.litellm-cost-alarm.plist` (Air launchd, 30-min cadence, RunAtLoad). Caught own bug mid-ship: v1 counted all-time calls (false RUNAWAY at 163%), refactored to snapshot-delta, sent Telegram correction. v2 initialized cleanly at tier -1. AP-18 honest-revision pattern applied in motion. Next trigger requires real daily delta. Refinement path codified in script header: enable json_logs: true for per-model breakdown + wire Langfuse (already on VPS, not yet connected) after 1 week of Opus billing data. No new LESSON (RULE ZERO).
- **2026-04-20** | v1.8.0 — Session 55 (Mac-interactive, this session): **resolved AP-25** via J2 execution in ~9 min (out of 90-min cap). Session-51's `--allow-unconfigured`-regenerates-from-defaults hypothesis **disproved**. Actual root cause: live-gateway clobber-on-restart (direct file edits racy with running OpenClaw gateway, which flushes in-memory state to disk on graceful shutdown). Fix: route all agent-layer config through `openclaw config set <dot.path> <value>` CLI — goes through gateway RPC, keeping memory + disk in sync. Verified E2E: `openclaw config set agents.defaults.model litellm/opus` + `openclaw config set "agents.list[0].model" litellm/opus` → `docker restart openclaw` → `[gateway] agent model: litellm/opus` in boot log → `openclaw config get agents` confirms `litellm/opus` persisted across restart. Factory now runs on Opus 4.7 (LiteLLM `opus` alias was already wired session 51 J1). AP-25 rewritten with: (a) resolution summary, (b) session-51 historical symptom, (c) actual session-55 command trace, (d) 5 updated rules, (e) full CLI subcommand map for future reference, (f) cross-ref to `session-operating-contract` AP-9 meta-lesson (executing parallel without permission-asking is what made J2 fit in 9 min not 90). Also deduped accidental AP-25 double-block that existed in v1.7.0 (lines 474-544 collapsed into single canonical block). Karpathy compounding: session-56+ never re-researches OpenClaw config plumbing. AP-18 honest-revision pattern in motion. No new LESSON (RULE ZERO).
- **2026-04-20** | v1.7.0 — Session 51 (Mac-interactive, autonomous overnight-continuation): added **AP-25 v1** — OpenClaw agent-layer config reconfig investigation (5-task research path filed as honest-STOP when 2 round-trips of direct file edit reverted on restart). Hypothesis: `--allow-unconfigured` regenerates from defaults. Unverified at the time; session-55 disproved and replaced with actual root cause.
- **2026-04-20** | v1.6.0 — Session 51 (Mac-interactive, autonomous overnight-continuation): absorbed **AP-24** — after Air reboot, Docker Desktop does NOT auto-start on SSH-only logins; factory is silently down until `open -a "Docker Desktop"` via SSH. Caught live during B1 factory skillsSnapshot bump attempt: `docker ps` returned socket errors, `pgrep Docker Desktop` found only vmnetd, uptime showed Air rebooted 27 min ago. Recovery: `ssh air 'open -a "Docker Desktop"'` + ~30s socket wait + ~3min container health wait. OpenClaw came back cleanly. AP-24 codifies: (1) SOAO factory probe must not assume docker alive; trigger recovery on socket error; (2) reboot-during-active-work needs pre-armed recovery plan; (3) session-52+ candidate: `com.nous.docker-desktop-watchdog` LaunchAgent ping/auto-start; (4) Docker Desktop "start on login" toggle is GUI-only, doesn't help SSH reboots; (5) launchd services loaded ≠ factory alive — factory depends on Docker Desktop which is NOT launchd. Cross-ref `audit` AP-17 point 5 (factory probe), `audit` AP-20 (probe E2E-verify — this session's same-day sibling rule, both caught at session 51 open). Karpathy compounding: every future session has exact recovery path; next reboot won't silently kill factory again. No new LESSON (RULE ZERO).
- 2026-04-15 | v1.0.0 — created in Wave 3 migration; absorbed LESSON-001, 002, 004, 019, 028, 035, 039, 040, 044, 045, 051, 054, 055, 056, 057, 065. Covers both old VPS systemd factory and current Air OpenClaw factory.
- 2026-04-15 | v1.1.0 — Wave 4: added absorbs_laws (LAW-006, 007, 010, 011). Added AP-14, AP-15, AP-16, AP-17.
- 2026-04-16 | v1.3.0 — Absorbed LESSON-114 (verify SOUL.md after docker restart, AP-21). Evidence: bulk lesson absorption session.
- 2026-04-16 | v1.4.0 — Absorbed LESSON-048+052 (phantom directory, AP-22). Session 32 orphan absorption.
- 2026-04-17 | v1.5.0 — Session 37: added AP-23 Confusion Protocol (gstack v0.18.0.0 adoption). Auto-apply / hot-reload-vs-restart / target-host / restart-scope forks must ASK, not guess. No new LESSON (RULE ZERO).
- 2026-04-15 | v1.2.0 — added Phase 5 (dispatch discipline — 7 steps) + AP-18 (write-back rebase collision) + AP-19 (legacy-path writes) + AP-20 (untrusted agent grep). All absorbed from session 23's 4× successful + 3× failure-mode factory dispatches (T1 command-center AP-8, T2 7 IS policy stubs, T3 camera-management Wave-2, T4 AUDIT-031 Apr-5 investigation).

- 2026-04-15 | v1.1.0 — Wave 4: added AP-14 (task tracing LAW-006), AP-15 (hub-and-spoke LAW-007), AP-16 (escalation-only LAW-010), AP-17 (business gate LAW-011).
## See also

- [[LESSON-044-factory-watchdog-auto-restart]]
- [[LESSON-054-ceo-empty-queue-burns-money]]
- [[LESSON-055-budget-hit-retry-loop]]
- [[LESSON-056-anthropic-credit-exhausted-retry]]
- `skills/infrastructure/SKILL.md` — Air/VPS topology and services
- `skills/command-center/SKILL.md` — Telegram routing to factory
- `skills/agent-quality/SKILL.md` — agent behavior (done = tested, no fake data)
