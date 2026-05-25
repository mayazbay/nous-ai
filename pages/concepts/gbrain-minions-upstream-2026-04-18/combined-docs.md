---
type: note
id: combined-docs
title: "combined docs"
date: 2026-04-30
last_updated: 2026-04-30
status: ingested
---

# Minions shell jobs — move deterministic crons off the gateway

## 30 seconds

```bash
# Run your first shell job:
GBRAIN_ALLOW_SHELL_JOBS=1 gbrain jobs submit shell \
  --params '{"cmd":"echo hello","cwd":"/tmp"}' --follow
# → exit_code: 0, stdout_tail: "hello\n", duration_ms: 43
```

That's it. Your cron scripts now have a home with retry, backoff, DLQ, and
`gbrain jobs list` visibility, without each one booting a full LLM session.

**PGLite users:** `gbrain jobs work` does not run on PGLite (exclusive file
lock). Every crontab invocation must use `--follow` for inline execution.
Postgres users can run a persistent worker; see recipes below.

---

## Why it exists

If your agent runs deterministic scripts from cron (token refresh, API fetch,
scrape + write), each one pays the cost of a full LLM session on the gateway.
Fourteen simultaneous fires on a Series A deployment pin CPU at 100% and block
live messages. None of those scripts need reasoning. They need a shell.

Shell jobs move them to the Minions worker: one deterministic-script execution
per cron, zero LLM tokens, unified visibility and retry.

---

## Security model (read this)

Shell exec is a large blast radius. We ship two independent gates, both must
pass:

1. **MCP boundary.** `submit_job` with `name: 'shell'` is rejected when
   `ctx.remote === true` (MCP callers). Independent of the env flag. Remote
   agents can never submit shell jobs. `MinionQueue.add('shell', ...)` has its
   own guard too, so an in-process handler can't programmatically bypass this.
2. **Env flag.** The worker only registers the shell handler when
   `GBRAIN_ALLOW_SHELL_JOBS=1` is set on the worker process. Default: off. Your
   agent opts in per-host.

**What the env allowlist does AND does not do.** Shell jobs run with a minimal
env: `PATH, HOME, USER, LANG, TZ, NODE_ENV`. Your secrets like `OPENAI_API_KEY`
and `DATABASE_URL` are NOT passed to the child. You opt-in additional keys per
job via `env: { ... }`. This stops accidental `$OPENAI_API_KEY` interpolation in
a user-authored script. It does **not** sandbox filesystem reads: a shell
script can `cat ~/.env` or any file the worker process can read. The operator
picks a safe `cwd`. That is the trust boundary.

**Audit trail, not forensic insurance.** Every submission writes a JSONL line
to `~/.gbrain/audit/shell-jobs-YYYY-Www.jsonl` (ISO-week rotation; override
with `GBRAIN_AUDIT_DIR`). Failures log to stderr and don't block submission, so
a disk-full adversary could silently disable the trail. Good for "what did
this cron submit last Tuesday", not for security-critical forensics.

**The command text is logged as-is.** If you embed a secret in `cmd`
(`curl -H 'Authorization: Bearer ...'`), it shows up in the audit file. Put
secrets in `env:` instead.

---

## Migrate a cron

### Postgres worker (recommended)

On one terminal, start a persistent worker:

```bash
GBRAIN_ALLOW_SHELL_JOBS=1 gbrain jobs work
```

Rewrite crontab to submit shell jobs (no `--follow`):

```cron
# Before (LLM gateway):
#   OpenClaw cron: x-garrytan-unified
# After (Minions worker):
3 13,16,19,22,1,4,7,10 * * * \
  gbrain jobs submit shell \
    --params '{"cmd":"node scripts/x-garrytan-daily.mjs","cwd":"/data/.openclaw/workspace"}' \
    --max-attempts 3 --timeout-ms 300000
```

Worker claims the job on next poll, runs it, records `exit_code` +
`stdout_tail` + `stderr_tail` in the result. Failures retry per
`--max-attempts` with exponential backoff.

### PGLite (inline execution)

PGLite doesn't support the persistent worker daemon. Every crontab invocation
uses `--follow` to run inline:

```cron
# Each cron tick spawns a short-lived worker that runs the job inline.
3 13,16,19,22,1,4,7,10 * * * \
  GBRAIN_ALLOW_SHELL_JOBS=1 gbrain jobs submit shell \
    --params '{"cmd":"node scripts/x-garrytan-daily.mjs","cwd":"/data/.openclaw/workspace"}' \
    --follow --timeout-ms 300000
```

Note: `--follow` blocks the crontab slot until the job finishes. If 14 shell
crons land at the same minute and each takes 30s, they serialize through
crontab's spawning limits. Postgres + persistent worker scales better.

### Submitting with `argv` (no shell interpolation)

For programmatic callers assembling commands from JSON, use `argv` instead of
`cmd`. No shell, no injection surface:

```bash
gbrain jobs submit shell \
  --params '{"argv":["node","scripts/fetch.mjs","--date","2026-04-19"],"cwd":"/data"}' \
  --follow
```

---

## Debug a failed job

```bash
# List dead shell jobs
gbrain jobs list --status dead

# Inspect one
gbrain jobs get 42
# → error_text, stacktrace, result.stdout_tail, result.stderr_tail

# Submission audit log (operator trail, not forensic)
cat ~/.gbrain/audit/shell-jobs-*.jsonl | jq '.'

# First-time failure mode: submitted without env flag on the worker
gbrain jobs list --status waiting --name shell
# If rows pile up here, no worker with GBRAIN_ALLOW_SHELL_JOBS=1 is running.
```

---

## Limitations

- **Filesystem reads are not sandboxed.** See "Security model" above. Don't
  point `cwd` at a directory full of secrets.
- **Audit log is advisory.** Disk-full or EACCES silently disables it.
- **Cancel latency is lock-renewal-bounded** (~7-15 s by default). A cancelled
  child keeps running until the next lock-renewal tick fails.
- **`--follow` claim order** is by priority/created_at. If another job is
  waiting in the same queue at the time of `--follow`, that one runs first.
- **`cwd` symlink TOCTOU.** The absolute-path check doesn't guard against
  symlinks pointing elsewhere at execution time. Operator-scope concern.

---

## Errors {#errors}

| Error | What it means | Fix |
|---|---|---|
| `shell: specify exactly one of cmd or argv` | `cmd` and `argv` are mutually exclusive. Both absent is also invalid. | Choose one. `cmd` for shell-interpolated strings; `argv` for structured args. |
| `shell: cwd is required and must be an absolute path` | `cwd` must be a string starting with `/`. | Set `cwd` in `--params` to an absolute path. |
| `shell: argv must be an array of strings` | `argv` has a non-string entry or isn't an array. | Pass `argv: ["bin","arg1","arg2"]`. |
| `shell: env values must all be strings` | `env` has a number/bool/object value. | Stringify: `"env":{"COUNT":"3"}` not `"env":{"COUNT":3}`. |
| `permission_denied: shell jobs cannot be submitted over MCP` | An MCP client tried to submit a shell job. By design CLI-only. | Submit from CLI or via a trusted operation handler (`ctx.remote === false`). |
| `protected job name 'shell' requires CLI or operation-local submitter` | A caller invoked `MinionQueue.add('shell', ...)` without the `trusted` opt-in. | Pass `{ allowProtectedSubmit: true }` as the 4th arg. CLI and `submit_job` do this automatically. |
| `aborted: timeout` / `aborted: cancel` / `aborted: shutdown` / `aborted: lock-lost` | The worker's abort signal fired mid-execution. Child got SIGTERM, 5s grace, then SIGKILL. | Expected: timeout / user cancel / deploy restart / stall. Inspect `gbrain jobs get` to see which. |
| `exit N: <stderr_tail_500>` | Script exited non-zero. | Read `stderr_tail` in `gbrain jobs get`. |
# Minions fix — repairing a half-migrated install

**tl;dr:** on v0.11.1+ everything should self-heal. If Minions is partially
set up (no `~/.gbrain/preferences.json`, autopilot still inline, cron jobs
still on `agentTurn`), run:

```bash
gbrain apply-migrations --yes
```

It's idempotent. On v0.11.1 installs that already migrated it's a cheap
no-op.

## Context

v0.11.0 shipped the Minions schema, queue, worker, and migration skill —
but the migration skill itself never fired on upgrade. `runPostUpgrade`
printed the feature pitch and stopped. v0.11.0 was never released
publicly; v0.11.1 is the first public Minions ship and fixes the
mega-bug (migration fires automatically on `gbrain upgrade` and via
the `postinstall` hook).

If you're on a pre-v0.11.1 branch build (e.g. running the
`minions-jobs` branch before v0.11.1 tagged), Minions may be installed
but not wired: schema is v7, but no `~/.gbrain/preferences.json`,
autopilot still runs inline, cron jobs still call `agentTurn`.

This guide covers both paths: the canonical v0.11.1+ fix, and the
stopgap for pre-v0.11.1 binaries that don't have `apply-migrations`.

## Detecting the half-migrated state

```bash
gbrain doctor
```

If the install is half-migrated, you'll see:

```
[FAIL] minions_migration: MINIONS HALF-INSTALLED (partial migration: 0.11.0). Run: gbrain apply-migrations --yes
```

or

```
[FAIL] minions_config: MINIONS HALF-INSTALLED (schema v7+ but no ~/.gbrain/preferences.json). Run: gbrain apply-migrations --yes
```

For a machine-readable report (cron-friendly):

```bash
gbrain skillpack-check --quiet && echo healthy || echo needs_action
gbrain skillpack-check | jq -r '.actions[]'    # prints the exact commands to run
```

## The fix (v0.11.1 or later)

```bash
gbrain apply-migrations --yes
```

Reads `~/.gbrain/migrations/completed.jsonl`, diffs against the TS
migration registry, runs whatever's pending. Seven phases:

```
A. Schema        gbrain init --migrate-only
B. Smoke         gbrain jobs smoke
C. Mode          prompt (or --yes default pain_triggered)
D. Prefs         write ~/.gbrain/preferences.json
E. Host          AGENTS.md marker injection + cron rewrites for gbrain
                 builtins; JSONL TODOs for host-specific handlers
F. Install       gbrain autopilot --install (env-aware)
G. Record        append completed.jsonl status:"complete"
```

If Phase E emits TODOs for host-specific handlers (e.g. Wintermute's
~29 non-gbrain crons), the migration finishes with `status: "partial"`.
Your host agent walks the TODOs using `skills/migrations/v0.11.0.md` +
`docs/guides/plugin-handlers.md`, ships handler registrations in the
host repo, then re-runs `gbrain apply-migrations --yes`. Newly
registerable cron entries get rewritten and the JSONL rows mark
`status: "complete"`.

## The stopgap (pre-v0.11.1 binary, no apply-migrations yet)

If you're stuck on a branch build that doesn't have `apply-migrations`:

```bash
curl -fsSL https://raw.githubusercontent.com/garrytan/gbrain/v0.11.1/scripts/fix-v0.11.0.sh | bash
```

This bash script does what apply-migrations does from a shell environment:

1. `gbrain init --migrate-only` — schema v7.
2. `gbrain jobs smoke` — verify Minions health.
3. Prompt for `minion_mode` (defaults `pain_triggered` on non-TTY).
4. Write `~/.gbrain/preferences.json` atomically.
5. Append `~/.gbrain/migrations/completed.jsonl` with `status: "partial"`
   and `apply_migrations_pending: true`. That partial record is the
   signal to v0.11.1's `apply-migrations` to pick up remaining phases
   after the user upgrades.
6. Detect host agent repos and PRINT rewrite instructions (never
   auto-edits from a curl-piped script).
7. Print the next step: `Run: gbrain autopilot --install`.

Once v0.11.1 is installed, re-run `gbrain apply-migrations --yes` to
finish the remaining phases (host rewrites + autopilot install). The
stopgap's `status: "partial"` record is designed to resume cleanly
(it doesn't poison the permanent migration path).

## Verify the fix landed

```bash
# 1. Preferences exist and are readable
cat ~/.gbrain/preferences.json

# 2. Migration recorded
cat ~/.gbrain/migrations/completed.jsonl

# 3. Autopilot is supervising a Minions worker child
gbrain autopilot --status
ps aux | grep 'jobs work'

# 4. Jobs show up in the queue
gbrain jobs list

# 5. Any host-specific TODOs still pending
cat ~/.gbrain/migrations/pending-host-work.jsonl 2>/dev/null || echo "(none — all host work is done)"

# 6. Doctor + skillpack-check should both be clean
gbrain doctor
gbrain skillpack-check --quiet && echo ok
```

## If the fix fails

Each phase is idempotent. Re-running is safe. Common failure modes:

- **Phase B smoke fails:** the schema didn't apply. Check
  `~/.gbrain/config.json` has a valid `database_url` (or `database_path`
  for PGLite). Run `gbrain init --migrate-only` directly and look at
  the error.
- **Phase F install fails:** your host environment doesn't match any
  detected target. Pass `--target <macos|linux-systemd|ephemeral-container|linux-cron>`
  explicitly.
- **Pending host work never clears:** your host agent hasn't shipped
  handler registrations yet. Read
  `~/.gbrain/migrations/pending-host-work.jsonl`, open
  `skills/migrations/v0.11.0.md`, and follow the host-agent instruction
  manual.

## Related

- `skills/migrations/v0.11.0.md` — full migration skill for host agents.
- `skills/skillpack-check/SKILL.md` — when and how to run the health check.
- `docs/guides/plugin-handlers.md` — plugin contract for host-specific
  handlers.
- `skills/conventions/cron-via-minions.md` — the canonical cron rewrite
  pattern.
# Minions vs OpenClaw Subagents Benchmark

**Date:** 2026-04-18
**Branch:** garrytan/minions-jobs
**Suite:** `test/e2e/bench-vs-openclaw/`
**Minions:** v0.11.0 (PR #130)
**OpenClaw:** 2026.4.10 (44e5b62)
**Model:** anthropic/claude-haiku-4-5

## Why this benchmark exists

Minions is GBrain's new background job queue, pitched as a durable, cheap
substitute for spawning OpenClaw subagents via `openclaw agent --local`.
"Durable" and "cheap" are easy to claim and hard to prove. So we put
numbers on four specific claims a Minions user would actually care about:

1. **Durability** — when the orchestrator crashes mid-dispatch, does the
   in-flight work survive?
2. **Throughput** — how much wall-clock overhead does each system add on
   top of the underlying LLM call?
3. **Fan-out** — parent dispatches 10 children in parallel. How fast and
   how reliable is each side?
4. **Memory** — what does it cost to keep 10 subagents in flight at once?

Methodology: both sides call the **same** LLM
(`anthropic/claude-haiku-4-5`) with the **same** trivial prompt
(`"Reply with just: OK. No other text."`). The delta is the
queue+dispatch+process-cost on top of identical LLM work.

## Honest caveats up front

- **We do NOT benchmark OpenClaw's gateway multi-agent fan-out.** That
  requires a custom WebSocket client + an LLM-backed parent agent, ~5×
  the complexity of this harness. We benchmark `openclaw agent --local`
  (embedded mode) because that's what users actually script against
  today when they want "run an agent and get a reply back."
- **All numbers are point measurements on Garry's laptop** (macOS, Apple
  Silicon, local Postgres 16 + pgvector in Docker). Not a cluster
  benchmark. Not an adversarial load test. Reproducible via the files
  in `test/e2e/bench-vs-openclaw/`.
- **OpenClaw `--local` is a fire-and-forget process.** If you SIGKILL
  it mid-dispatch, the reply is gone. This isn't a bug, it's the design.
  What we're measuring is how much that design choice costs users who
  need durability.
- **Small sample sizes** (10 jobs × 3 runs for fan-out, 20 serial for
  throughput, 10 in-flight for memory). Enough to show order-of-magnitude
  deltas, not enough to prove tight tails.

## Results

### 1. Durability (SIGKILL mid-flight, 10 jobs)

| System | Delivered | Wall time | p50 per job | p95 per job |
|--------|-----------|-----------|-------------|-------------|
| **Minions** | **10 / 10** | 458ms total | 257ms | 410ms |
| OpenClaw `--local` | **0 / 10** | 22989ms (all SIGKILLed at 500ms) | n/a | n/a |

Setup: Minions side seeds 10 jobs in state `active` with an expired
`lock_until` (exactly the state a SIGKILLed worker leaves behind). A
rescue worker starts. It picks up all 10 via `handleStalled` and
completes them.

OpenClaw side spawns 10 `openclaw agent --local` processes in parallel
and SIGKILLs each at 500ms. Zero of them managed to emit any output
before being killed.

**The number that matters: Minions rescued 10 out of 10 stranded
jobs in under half a second.** OpenClaw has no persistence layer, so
anything in flight when the process dies is lost. Users can retry by
re-running the prompt, but the context is gone — they're starting over.

Source: `test/e2e/bench-vs-openclaw/durability.bench.ts`

### 2. Throughput (20 serial dispatches, same LLM call)

| System | p50 | p95 | p99 | Mean | Min | Max | Success |
|--------|-----|-----|-----|------|-----|-----|---------|
| **Minions** | **778ms** | **1931ms** | **1931ms** | **911ms** | 639ms | 1931ms | 20/20 |
| OpenClaw `--local` | 8086ms | 10094ms | 10094ms | 8335ms | 7405ms | 10094ms | 20/20 |
| **Ratio** | **10.4×** | **5.2×** | **5.2×** | **9.2×** | 11.6× | 5.2× | — |

Setup: both sides call claude-haiku-4-5 with the same prompt. Minions
goes through `queue.add` → worker claims → handler calls Anthropic SDK
directly. OpenClaw spawns a fresh `openclaw agent --local` process per
dispatch.

The ~7 seconds of overhead per OC dispatch isn't the LLM. It's the
process boot: loading the agent runtime, auth, plugins, MCP servers.
Every dispatch pays that cost again. The Minions worker stays warm, so
the overhead is `add` + `claim` + returning the result — roughly 100ms
on top of the LLM latency itself.

Source: `test/e2e/bench-vs-openclaw/throughput.bench.ts`

### 3. Fan-out (3 runs × 10 children in parallel)

| System | Completed | Mean wall time | Runs (ok/N) | Wall times (ms) |
|--------|-----------|----------------|-------------|-----------------|
| **Minions** (concurrency=10) | **30 / 30** | **1090ms** | 10/10, 10/10, 10/10 | 890, 1135, 1245 |
| OpenClaw (10 parallel spawns) | 17 / 30 | 22598ms | 6/10, 5/10, 6/10 | 22204, 22505, 23084 |
| **Ratio (wall time)** | — | **~21×** | — | — |

Setup: parent dispatches 10 children concurrently, waits for all.
Minions uses one worker process with `concurrency=10`. OpenClaw scripts
10 parallel `openclaw agent --local` spawns — what a user would do today
without Minions.

Two findings, not one:

1. **Wall time: Minions completes 10 in ~1 second. OC parallel spawn
   takes ~22 seconds.** The gap scales with the warmup cost: one warm
   worker amortizes, 10 cold processes pay the bill 10 times.
2. **OC parallel spawn fails 43% of the time at 10-wide.** Error
   samples show a mix of LLM rate-limit hits and spawn saturation. We
   didn't tune this. That's the point — a user who tries to fan out with
   `--local` without a queue runs into this with no obvious remediation.

Source: `test/e2e/bench-vs-openclaw/fanout.bench.ts`

### 4. Memory (10 in-flight subagents)

| System | Baseline RSS | Peak with 10 in flight | Delta | Processes |
|--------|--------------|------------------------|-------|-----------|
| **Minions** | 84 MB | **86 MB** | **+2 MB** | 1 |
| OpenClaw | n/a | 814 MB (summed across 10) | — | 10 |
| **Ratio** | — | **~407×** | — | — |

Setup: both sides keep 10 subagents in flight simultaneously. Minions
side uses one worker with concurrency=10 and handlers that park on a
Promise. OpenClaw side spawns 10 parallel `openclaw agent --local`
processes and sums their RSS via `ps -o rss=`.

Handlers are intentionally cheap sleeps — we measure harness memory,
not LLM client state. The LLM client state would be comparable on both
sides.

**Minions costs 2 MB to keep 10 subagents in flight. OpenClaw costs
814 MB. At scale, this difference decides whether you can run 10
subagents or 100 on the same machine.**

Source: `test/e2e/bench-vs-openclaw/memory.bench.ts`

## What this means for a Minions user

If you have a script today that spawns `openclaw agent --local` N times,
every one of these numbers gets better when you move to Minions:

- **Crash and your work doesn't vanish.** Worker dies, PG keeps the
  row, another worker picks it up. Zero extra code on your side.
- **Per-dispatch wall time drops ~10×** because the worker stays warm.
  Process startup is where your time was going, not the LLM.
- **Fan-out scales past 10-wide without you hand-tuning concurrency.**
  Worker does the throttling; the queue does the durability. OC
  parallel spawn hits a 40% failure wall around 10-wide on this hardware.
- **Memory stops being the bottleneck.** 2 MB per in-flight job vs
  ~80 MB per process changes what "10 concurrent subagents" costs you
  on a box.

## What this doesn't say

- We didn't test OpenClaw's gateway multi-agent mode. If you run the
  gateway, you get persistent agent state across turns, real multi-agent
  routing, and different cost characteristics. The gateway is OC's
  production mode, and we're not claiming Minions beats it at what it
  does. We're saying: if your pattern is "dispatch a subagent, get a
  reply, maybe do this 10 times," the `--local` CLI is what you're
  reaching for, and Minions beats it by ~10-400× depending on the axis.
- We didn't run under load (100s of concurrent jobs, hours of sustained
  work). These are observational point measurements, not a stress test.
- We ran claude-haiku-4-5. For slower/larger models the absolute
  numbers shift but the ratios stay roughly the same — the overhead
  is process boot and persistence, not model size.

## Reproducing

```bash
# 1. Start a test Postgres
docker run -d --name gbrain-test-pg \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=gbrain_test \
  -p 5436:5432 pgvector/pgvector:pg16

# 2. Set env
export DATABASE_URL=postgresql://postgres:postgres@localhost:5436/gbrain_test
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run each bench (durability + memory are free; throughput + fan-out
#    cost ~$0.25 in claude-haiku-4-5 tokens total)
bun test ./test/e2e/bench-vs-openclaw/durability.bench.ts
bun test ./test/e2e/bench-vs-openclaw/throughput.bench.ts
bun test ./test/e2e/bench-vs-openclaw/fanout.bench.ts
bun test ./test/e2e/bench-vs-openclaw/memory.bench.ts

# 4. Tear down
docker stop gbrain-test-pg && docker rm gbrain-test-pg
```

## One-line summary

Minions rescues 10/10 jobs from a crash in under half a second while
OpenClaw `--local` loses all of them; it delivers each dispatch ~10×
faster, fans out 10-wide in ~1 second vs ~22 seconds at 43% OC failure
rate, and holds 10 in-flight subagents in 2 MB vs 814 MB.
# Production Benchmark: Minions vs OpenClaw Sub-agents (Real Deployment)

**Date:** 2026-04-18
**Environment:** Wintermute on Render (ephemeral container, Supabase Postgres)
**GBrain:** v0.11.0 (minions-jobs branch)
**OpenClaw:** 2026.4.10
**Brain:** 45,798 pages, 98K chunks, 25K links, 79K timeline entries
**Task:** Pull and ingest one month of social posts from an external API into the brain

## Context

This is a **production benchmark**, not a lab test. The existing lab benchmark
([2026-04-18-minions-vs-openclaw-subagents.md](2026-04-18-minions-vs-openclaw-subagents.md))
uses trivial prompts on localhost Postgres. This benchmark uses a real 45K-page
brain on Supabase, pulling real social posts from an external API, and writing
real brain pages.

## The Task

Pull a month (May 2020) of my social posts from an external API, parse them
into a structured brain page with frontmatter, engagement metrics, and
links, commit to the brain repo, and submit a sync job to gbrain.

## Method 1: Minions (deterministic pipeline)

```bash
# 1. Pull posts from the external API (curl → JSON)
curl -s -H "Authorization: Bearer $API_BEARER_TOKEN" \
  "$SOCIAL_API_URL?from=my_account&start=2020-05-01&end=2020-06-01" \
  > /tmp/bench-posts.json

# 2. Parse + write brain page (python)
python3 parse_and_write.py

# 3. Git commit
cd /data/brain && git add media/social/2020-05.md && git commit -m "archive: 2020-05"

# 4. Submit sync to Minions
gbrain jobs submit sync --params '{"repo":"/data/brain","noPull":true}'
```

**Result: 753ms total.** 99 posts pulled, page written, committed, sync job queued.

Breakdown:
- External API call: ~300ms
- Python parse + write: ~50ms
- Git commit: ~100ms
- gbrain jobs submit: ~300ms

Cost: $0.00 (no LLM tokens)

## Method 2: OpenClaw Sub-agent (sessions_spawn)

```javascript
sessions_spawn({
  task: "Pull my social posts for June 2020 and save as a brain page...",
  model: "anthropic/claude-sonnet-4-20250514",
  mode: "run",
  runTimeoutSeconds: 120
})
```

**Result: GATEWAY TIMEOUT (>10,000ms).** The sub-agent could not even spawn
within the 10-second gateway timeout. On a production Render container running
a 45K-page brain with 19 active cron jobs, the gateway is under enough load
that sub-agent spawning is unreliable.

When sub-agents DO successfully spawn (off-peak), the expected path is:
1. Gateway receives spawn request (~500ms)
2. Create session, load context (~2-3s) — AGENTS.md, SOUL.md, skills, memory
3. Model reads task, plans approach (~2-3s)
4. Model calls `exec` tool for curl (~1s)
5. Model calls `exec` tool for python (~1s)
6. Model calls `exec` tool for git (~1s)
7. Model reports result (~1s)

**Estimated: 10-15s + ~$0.03 in tokens per invocation**

## Comparison

| Metric | Minions | Sub-agent |
|--------|---------|-----------|
| **Wall time** | **753ms** | **>10,000ms** (gateway timeout) |
| **Token cost** | $0.00 | ~$0.03 per run |
| **Success rate** | 100% | 0% (timeout on first attempt) |
| **Survives restart** | Yes (Postgres) | No (dies with process) |
| **Progress tracking** | `gbrain jobs get <id>` | poll sessions_list |
| **Auto-retry** | 3 attempts, exponential backoff | manual re-spawn |
| **Concurrency** | FOR UPDATE SKIP LOCKED | hope-based maxConcurrent |
| **Steerable** | inbox messages | fire and forget |
| **Results persisted** | job record | lost on compaction |
| **Memory** | ~2MB per in-flight job | ~80MB per spawned session |

## The Scaling Story

We pulled 19,240 posts across 36 months (2021-2023) using the Minions
approach in a single bash loop. Total time: ~15 minutes. Cost: $0.00 in
LLM tokens.

The same task via sub-agents would require 36 spawns × ~$0.03 = ~$1.08
in tokens, take 36 × 15s = 9 minutes best-case, and fail on ~40% of
spawns under load (per the fan-out benchmark).

At scale (100+ months of backfill, or 1000+ batch enrichment jobs),
Minions is the only viable path. Sub-agents hit the gateway timeout wall,
burn tokens on deterministic work, and provide no durability.

## When Sub-agents Still Win

Sub-agents are correct for **judgment work**:
- Email triage (LLM decides priority, drafts reply)
- Social radar (LLM assesses severity, decides to alert)
- Meeting prep (LLM synthesizes brain pages into briefing)
- Cold email research (LLM decides notability)

These tasks require an LLM to make decisions. Minions can't do that —
its handlers are code, not models. The routing rule:

> **Deterministic** (same input → same steps → same output) → **Minions**
> **Judgment** (input requires assessment/decision) → **Sub-agents**

## One-Line Summary

Minions completed a production post-ingest pipeline in 753ms for $0.
Sub-agents couldn't even spawn. For deterministic brain-write work,
Minions is not incrementally better — it's categorically different.
