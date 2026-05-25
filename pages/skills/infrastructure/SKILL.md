---
tier: 2
type: skill
name: infrastructure
version: 2.90.0
description: Deployment, health monitoring, restart, cron + launchd management for the Nous AGaaS factory stack. Air = primary 24/7, VPS = gateway (gbrain, wiki bare, NCAnode). Covers OpenClaw, LiteLLM, Telegram poller, autopilot, auto-checkpoint, morning-brief, light-probe, staleness, log-rotate, weekly library canary. Recent AP additions tracked in `recent_changes:` below.
recent_changes:
  - {session: 60, ap: 51, summary: "auto-sync user-commit-race guard"}
  - {session: 63, ap: 51, summary: "extended to 30s mtime + tracked-file-mtime check (closes multi-tool-call Edit-sequence race window)"}
  - {session: 75, ap: 58, summary: "live tunnel health probes must classify upstream-data-stop vs collector/filter drift"}
  - {session: 75, ap: 59, summary: "generic auto-sync must refuse authorial-class paths"}
  - {session: 76, ap: 49, summary: "parity extended to Codex AGENTS.md; detector host-aware"}
  - {session: 76, ap: 60, summary: "restart proof must respect Docker healthcheck interval"}
  - {session: 76, ap: 61, summary: "risky manual-review update alerts must be digest state-change deduped"}
  - {session: 77, ap: 62, summary: "SOUL/USER/AGENTS identity files must sync into OpenClaw runtime"}
  - {session: 77, ap: 63, summary: "Blacksmith 32-vCPU burst CI must start as manual, portable, secret-free test substrate"}
  - {session: 77, ap: 64, summary: "fast heartbeats must not deep-probe every model/provider on a 15-minute loop"}
  - {session: 78, ap: 65, summary: "broken deep model probes must omit unknown fields instead of question-mark sentinels"}
  - {session: 78, ap: 66, summary: "probe scripts must use least-privilege container diagnostics instead of embedded host-sudo"}
  - {session: 78, ap: 67, summary: "Air disk pressure cleanup must prune Docker build cache/dangling layers before broad filesystem deletion"}
  - {session: 79, ap: 69, summary: "session rotation must preserve OpenClaw JSONL headers instead of writing invalid `[]`"}
  - {date: "2026-04-29", ap: 70, summary: "CI runner readiness requires actual job assignment, not workflow existence"}
  - {date: "2026-04-29", ap: 71, summary: "pcap truncation/rotation is a baseline reset, not a mirror failure"}
  - {session: 85, ap: 72, summary: "Docker disk pressure recurs <24h; manual prune not idempotent due to OpenClaw churn; needs scheduled daily prune cron"}
  - {session: 102, ap: 73, summary: "notify-only image checks must be registry-read-only"}
  - {session: 102, ap: 74, summary: "context-injector skill caps must spend budget on doctrine, not YAML"}
  - {session: 107, ap: 75, summary: "canary scripts under set -u must not use bare positional args; alert path must precede diagnostic write"}
  - {date: "2026-05-05", ap: 77, summary: "launchd poller health must treat a live PID as healthy even if last-exit is stale"}
  - {date: "2026-05-05", ap: 78, summary: "Caddy Tailscale-only listeners require explicit bind, not just an IP-literal site address"}
  - {date: "2026-05-05", ap: 79, summary: "restart drills need first-seen failure state and ssh -n in stdin-driven harnesses"}
  - {date: "2026-05-05", ap: 80, summary: "Python HTTPS probes on macOS need certifi CA fallback before declaring URL checks broken"}
  - {date: "2026-05-08", ap: 81, summary: "cross-host watchdogs must separate target death from observer SSH transport uncertainty"}
  - {date: "2026-05-08", ap: 82, summary: "long-running pollers must contain transient upstream HTTP failures instead of crash-looping"}
  - {date: "2026-05-09", ap: 83, summary: "Todoist REST v2 410 means migrate operator mutations to unified API v1"}
  - {date: "2026-05-11", ap: 84, summary: "Todoist board writes must include section_id, not project_id only"}
  - {date: "2026-05-12", ap: 85, summary: "auto-checkpoint must safely mirror handoffs to GitHub for external routines"}
  - {date: "2026-05-12", ap: 86, summary: "verification installs in the vault must not let Python package metadata enter git"}
  - {date: "2026-05-13", ap: 87, summary: "GitHub mirror green requires exact live HEAD, not just reachable tokenless remote"}
  - {date: "2026-05-13", ap: 88, summary: "Hermes is the durable supervisor/watchdog layer; OpenClaw remains the worker factory"}
  - {date: "2026-05-13", ap: 89, summary: "watchdogs must dedupe already-recorded incidents instead of staying yellow forever"}
  - {date: "2026-05-13", ap: 90, summary: "watchdog status pages must rewrite when yellow clears to green"}
  - {date: "2026-05-13", ap: 91, summary: "tracked launchd script fixes must be deployed to the live ProgramArguments target"}
  - {date: "2026-05-16", ap: 92, summary: "update checks must scan actual installed skill roots, including .agents"}
  - {date: "2026-05-18", ap: 93, summary: "direct LiteLLM HTTP 200 with null content is a model failure and must trigger same-run escalation"}
  - {date: "2026-05-19", ap: 94, summary: "Hermes WebUI canary green requires authenticated factory-events proof, not health-only reachability"}
  - {date: "2026-05-21", ap: 95, summary: "optional Nous-GPU collector degradation must skip cleanly unless a GPU-bound workload explicitly requires it"}
  - {date: "2026-05-22", ap: 96, summary: "shared launchd wrappers must resolve the host-local vault before scanning or committing"}
triggers:
  - operator wants to deploy/restart/upgrade any stack component
  - a factory component is suspected down or misbehaving
  - planning a new scheduled job (cron/launchd)
  - adding a new Docker container
  - migrating a service between Air and VPS
tools: [Bash, Read, Edit, Write, Grep]
mutating: true
absorbs_lessons: [LESSON-034, LESSON-061, LESSON-066, LESSON-088, LESSON-090, LESSON-091, LESSON-092, LESSON-094, LESSON-097, LESSON-099, LESSON-100, LESSON-101, LESSON-104, LESSON-106, LESSON-108, LESSON-109, LESSON-116, LESSON-120, LESSON-125, LESSON-126, LESSON-127]
absorbs_laws: [LAW-014]
last_updated: 2026-05-22
title: "infrastructure v2.90.0"
---

# infrastructure v2.90.0

## Purpose

Single source of truth for the factory topology and operational rules. Everything in this skill is always-on knowledge — no need to search lessons to know how to deploy, restart, or upgrade.

## Current topology (2026-04-15)

### Air (M2 MacBook, plugged in 24/7, always on)
The factory backbone. Everything that MUST run regardless of Mac Pro sleep lives here.

| Component | Runner | Details |
|-----------|--------|---------|
| OpenClaw | Docker `openclaw` | Image `ghcr.io/openclaw/openclaw:2026.4.14 --platform linux/amd64`. Gateway port 18789 (WebSocket). Browser port 18791. Wiki mount at `/opt/nous-agaas/wiki` (NOT /root — AP-1). |
| LiteLLM | Native launchd `com.nous.litellm` | Port 4000. Routes to ZAI API (GLM-5.1). Native pip install NOT Docker (AP-2). |
| Telegram poller | launchd `com.nous.telegram-poll` | `StartInterval=60`. Owns `@nousAGaaSbot` Bot API (AP-3). |
| Wiki sync | launchd `com.nous.wiki-sync` | Bidirectional every 5min: `git add -A && commit && pull && push origin main` |
| Auto-checkpoint | launchd `com.nous.auto-checkpoint` | 8×/day. SMART-skip if no new task-results since last checkpoint. |
| Morning brief | launchd `com.nous.morning-brief` | 04:00 Almaty. Full audit + update check + state-diff vs yesterday. |
| Light probe | launchd `com.nous.light-probe` | Every 15min. Mechanical health. Telegram only on state CHANGE (AP-4). |
| Staleness | launchd `com.nous.staleness` | Hourly 09-22 Almaty. Alert if no task-results in 6h. |
| Log rotate | launchd `com.nous.log-rotate` | Sunday 03:00. Truncate logs >5MB to last 1000 lines. |
| Session rotate | launchd `com.nous.session-rotate` | Daily 03:45 Almaty. Clears OpenClaw session jsonl to prevent 127K+ token accumulation. (LESSON-101) |

### VPS (Hetzner, gateway only)
- **gbrain** (`/opt/nous-agaas/gbrain/`, v0.10.1) + autopilot cron every 5min
- Wiki bare repo: `root@65.108.215.200:/root/nous-agaas/obsidian-wiki.git`
- NCAnode (KZ crypto для ЭЦП)
- Langfuse (observability, currently idle)
- PostgreSQL (gbrain backing store)
- `memory_sync.py` cron (mem0 integration)
- `ingest_pending.py` cron (processes raw/ files)

### Mac Pro (mobile dev station, sleeps)
- `com.nous.capture-courier` — iCloud → wiki/raw/pending/
- `com.nous.obsidian-sync` — Obsidian vault sync
- `com.nous.backup` — local backups
- **Interactive Claude Code sessions** (this one) + Claude Code Routines (local)
- NO cron jobs (cleaned up 2026-04-15)

## Contract

**Inputs:** a deploy/restart/upgrade request, or a new scheduled-job requirement.

**Outputs:**
- Running service with expected process lifecycle (restart-on-crash, logs rotating, health probeable)
- Updated handoff note; reusable learning goes to SKILL.md + gbrain timeline per RULE ZERO
- If mutating production: one-line summary of what changed + verification command

**Invariants:**
- Air 24/7 components use launchd `KeepAlive` OR `StartInterval` OR Docker `--restart unless-stopped`
- Every scheduled job has a state file + state-change filter to avoid alert spam
- Every Telegram alert is either (a) a state change or (b) a human-actionable issue — no noise
- Logs rotate weekly, no unbounded growth

## Phases

1. **Assess** — what's broken/needed? Read current state from `launchctl list`, `docker ps`, and crontab.
2. **Design** — which node hosts it (Air = always-on, VPS = gateway, Mac Pro = mobile)? What trigger (launchd interval/calendar vs cron)? What state-change filter?
3. **Implement** — write script + plist/cron. Test before loading.
4. **Deploy** — `launchctl load` or `crontab`. Run once manually to verify.
5. **Verify** — trigger the check/probe and confirm expected output.
6. **Document** — if anything surprising is reusable, update the relevant SKILL.md and gbrain timeline per RULE ZERO. Do not create new LESSON files.

## Anti-Patterns

### AP-1 — Don't mount host paths into `/root/` on a non-root-user container
**LESSON-094.** Linux container `/root/` is 700 root:root. Container users like `node` (UID 1000) cannot traverse it, regardless of the mount's contents. Mount into `/opt/`, `/home/<user>/`, `/tmp/`, or `/srv/` instead. Also `chmod -R o+rX` on the host dir so UID-mapped reads work across the host/container UID boundary on macOS Docker.

```bash
# ❌ WRONG (container=node cannot read)
docker run -v ~/nous-agaas/wiki:/root/nous-agaas/wiki ...

# ✅ RIGHT
docker run -v ~/nous-agaas/wiki:/opt/nous-agaas/wiki ...
chmod -R o+rX ~/nous-agaas/wiki
```

### AP-2 — Prefer native pip over Docker for Python services on macOS ARM64
**LESSON-090.** On M2 Air, Docker AMD64 images run under Rosetta 2 emulation (slow, wasteful). If a Python service is already pip-installable (litellm, etc.), deploy native via launchd. Docker is still right for OpenClaw (large image, complex deps). The rule: Python CLI → native. Opaque pre-built image → Docker.

LiteLLM launchd plist env loading trap:
```xml
<string>cd /Users/madia/nous-agaas &amp;&amp; set -a &amp;&amp; source litellm/.env &amp;&amp; set +a &amp;&amp; exec /opt/homebrew/bin/litellm --config litellm/config.yaml --port 4000</string>
```
`set -a` auto-exports every var; `source .env` alone does NOT export to child processes.

### AP-3 — Don't transfer Docker images via `docker save | ssh | docker load`
**LESSON-091.** For images > 1GB the pipe deadlocks (`docker load`'s buffer fills when Docker VM disk writes lag; ssh blocks on write; network stalls). Use `scp` + `docker load -i` with the tar on disk:
```bash
ssh src 'docker save image:tag -o /tmp/image.tar'
scp src:/tmp/image.tar /tmp/image.tar
docker load -i /tmp/image.tar
rm /tmp/image.tar; ssh src 'rm /tmp/image.tar'
```
Or, if the image is public and destination has good internet, just `docker pull` on the destination.

### AP-4 — Don't bind-mount OpenClaw config file
**LESSON-092.** OpenClaw reads runtime config from `~/.openclaw/openclaw.json` (i.e., `/home/node/.openclaw/openclaw.json` inside the container), NOT `/app/openclaw.json`. Bind-mounting a single FILE into that directory also locks the parent directory for the container user, breaking workspace/canvas dirs. Use `docker cp` AFTER first startup:

```bash
docker run -d --name openclaw \
  --restart unless-stopped -p 18789:18789 --platform linux/amd64 \
  -v ~/nous-agaas/wiki:/opt/nous-agaas/wiki \
  -v ~/nous-agaas/skills:/opt/nous-agaas/skills \
  ghcr.io/openclaw/openclaw:2026.4.14
# wait for "listening" line (~40s on Rosetta), then:
docker cp ~/nous-agaas/openclaw/openclaw.json openclaw:/home/node/.openclaw/openclaw.json
docker restart openclaw
```

### AP-5 — Don't write to state files non-atomically
**LESSON-088.** `Path.write_text(...)` truncates then writes, so a concurrent reader can see an empty file. Use `os.replace(tmp, final)` for atomic rename. This caused 4× message duplication in telegram_poll before the fix.

### AP-6 — Don't fire fixed-schedule alerts on stable systems
**LESSON-097.** Daily alerts at 4am that always send "everything green" create alert fatigue. Use state-change filters: store previous state in a JSON file, compare current to previous, only Telegram on transitions. Morning-brief sends the green brief AND a change diff; light-probe is silent unless state flipped.

Pattern:
```bash
PREV=$(cat "$STATE" 2>/dev/null || echo '{}')
# compute CUR...
for k in ...; do
  p=$(echo "$PREV" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('$k','?'))")
  if [ "$p" != "?" ] && [ "$p" != "${CUR[$k]}" ]; then
    CHANGES="${CHANGES}$k: $p → ${CUR[$k]}\n"
  fi
done
echo "$CUR" > "$STATE"
[ -n "$CHANGES" ] && send_telegram "$CHANGES"
```


### AP-7 — LiteLLM fallback chain MUST end with a "never fails" provider (xAI Grok)
**LESSON-099 + LESSON-104.** When ZAI credits run out OR both primary providers are cooled down simultaneously, factory goes completely down if no guaranteed tail is configured. `RouterRateLimitError` means ALL deployments in the pool are on cooldown — not just one provider.

Always wire a 3-tier fallback in `litellm/config.yaml`:

```yaml
router_settings:
  cooldown_time: 30  # 60s blind window is too long — 30s is safer
  # glm-5.1 (OpenRouter) → glm-4.5-flash (ZAI free) → grok-reasoning (xAI — guaranteed tail)
  fallbacks: [{"glm-5.1": ["glm-4.5-flash", "grok-reasoning"]}, {"glm-4.5-flash": ["grok-reasoning"]}]
```

**Why Grok as last resort:** Better reasoning + cheaper than Anthropic. XAI_API_KEY is always funded. Sonnet/Opus still available as named models for direct calls, but grok-reasoning is the router's guaranteed tail.

**Reasoning model config** (glm-4.5-flash needs 8192 tokens for chain-of-thought):
```yaml
- model_name: "glm-4.5-flash"
  litellm_params:
    model: "zai/glm-4.5-flash"
    max_tokens: 8192
    timeout: 120
```

Restart after config change:
```bash
launchctl kickstart -k gui/$(id -u madia)/com.nous.litellm
# verify:
curl -s http://localhost:4000/health/liveliness
```

### AP-8 — Always git pull --rebase before git push in shared repos
**LESSON-100.** The VPS bare repo has 3 concurrent writers: Air wiki-sync (every 5min), gbrain autopilot (every 5min), and run_task.py write-back (after each task). Any two can overlap, causing push rejection.

Pattern for all write-back git pushes:
```python
subprocess.run(["git", "-C", WIKI_PATH, "commit", ...])
subprocess.run(["git", "-C", WIKI_PATH, "pull", "--rebase", "origin", "main"],
               check=True, capture_output=True, timeout=30)
subprocess.run(["git", "-C", WIKI_PATH, "push", "origin", "main"],
               check=True, capture_output=True, timeout=30)
```

`--rebase` keeps write-back commits at tip, avoids merge commits. Timestamped task-result files never conflict.

### AP-9 — Rotate OpenClaw session daily to prevent token accumulation
**LESSON-101.** OpenClaw maintains a persistent session file per agent. Every task call appends to it — it grew to 920KB / 127K tokens over 2 days, costing $0.18/call in input tokens. At GLM-5.1 pricing this burns $25 in days. OpenClaw triggers auto-compaction at ~114K tokens but it's reactive, not preventive.

Fix: daily rotation via `com.nous.session-rotate` (03:45 AM Almaty, before the 4am nightly-audit):
```bash
# ~/nous-agaas/tools/session_rotate.sh
bash ~/nous-agaas/tools/session_rotate.sh
```

Project knowledge is NOT in the session — it lives in wiki + gbrain. Rotation trims task conversation history while preserving the first OpenClaw JSONL `type=session` header line. Start each day small instead of 900KB.

Monitor session size in `/audit openclaw` (warns at >500KB). Check size:
```bash
docker exec openclaw find /home/node/.openclaw/agents/nous/sessions -name '*.jsonl' ! -name '*.checkpoint.*' \
  -exec wc -c {} \;
```

### AP-10 — Use OpenRouter for international GLM-5.1 access
**LESSON-101.** ZhipuAI direct (`open.bigmodel.cn`) is China-payment focused. International users get error 1113 when balance/resource-package is exhausted and cannot easily recharge.

Alternative: use OpenRouter (`openrouter.ai`) which:
- Accepts international Visa/Mastercard
- Has GLM-5.1 at **$0.95/1M input, $3.15/1M output** (vs ZhipuAI direct: $1.40/$4.40)
- Model ID: `openrouter/z-ai/glm-5.1`

LiteLLM config (switch primary to OpenRouter):
```yaml
# Uncomment and add OPENROUTER_API_KEY to litellm/.env
- model_name: "glm-5.1"
  litellm_params:
    model: "openrouter/z-ai/glm-5.1"
    api_key: "os.environ/OPENROUTER_API_KEY"
    max_tokens: 8192
    timeout: 120
```


### AP-11 — macOS TCC blocks /bin/bash under launchd from reading ~/Documents/
**LESSON-066.** LaunchAgent and cron jobs spawned by launchd run as children of launchd — which does NOT have Full Disk Access (FDA). The bash scripts they spawn cannot read `~/Documents/`, `~/Desktop/`, `~/Downloads/`, or iCloud paths, even though the same script works fine when run manually from Terminal.

Symptoms: script exits 0 (due to `2>/dev/null || return 0` error swallowing), no actual work done.

**Fix options (in order of preference):**
1. **Grant /bin/bash Full Disk Access**: System Settings → Privacy & Security → Full Disk Access → + → type `/bin/bash`
2. **Use Claude Code bash** (inherits Claude Code.app's TCC): run sync manually at end of each session with `bash /path/to/script.sh`
3. **Move the data outside TCC-protected paths** (awkward — breaks Obsidian Sync)

**Prevention rules:**
```bash
# In every script that touches ~/Documents/ or iCloud:
# 1. Probe with a real read (not just access())
if ! head -c 1 "$VAULT/.git/HEAD" >/dev/null 2>&1; then
    log_line "TCC-BLOCK: grant /bin/bash Full Disk Access in System Preferences"
    exit 0
fi

# 2. Use WorkingDirectory=/tmp in LaunchAgent plist (prevents cwd EPERM)
<key>WorkingDirectory</key>
<string>/tmp</string>

# 3. Log start AND finish lines — never swallow errors
log_line "sync started"
# ... work (stderr to log file, NOT /dev/null) ...
log_line "sync finished: $STATUS"
```

Script that works from Terminal but silently fails from launchd: **always suspect TCC first.**


## Output Format

When deploying a new component, leave:
1. A launchd plist or cron entry
2. A sanity-check script that can be run standalone
3. An entry in this skill's topology table
4. A LESSON page if anything surprising was encountered
5. A `last_updated` bump + changelog line in this skill file

## Files

| File | Role |
|------|------|
| `~/Library/LaunchAgents/com.nous.*.plist` | Air service definitions |
| `~/nous-agaas/tools/*.sh` | Cron/launchd scripts |
| `~/nous-agaas/*.py` | Factory Python modules |
| `/opt/nous-agaas/gbrain/bin/gbrain` (VPS) | gbrain CLI |
| `/root/nous-agaas/obsidian-wiki.git` (VPS) | Wiki bare repo |


### AP-12 — macOS SSH public-key auth is silently blocked — use Tailscale SSH instead

**LESSON-089.** macOS ships `100-macos.conf` which sets `UsePAM yes`. PAM's SACL (Service Access Control List) layer silently blocks all public-key SSH attempts — no log entries, no "Server accepts key" message, no error on the client. The remote simply disconnects. Debugging for >2 attempts is wasted time.

**Rule: on any macOS host, use Tailscale SSH (`tailscale up --ssh`) for remote access — never fight the OpenSSH daemon.**

Setup (one-time):
```bash
# On the macOS target (Air/Mac Pro)
tailscale up --ssh              # enables Tailscale SSH proxy (bypasses PAM/sshd)
# On the client
ssh <tailscale-ip>              # connects without PAM, no key-pair needed
```

Connection string for Air: `ssh madia@100.122.219.22` (Tailscale IP, never changes).


### AP-14 — Subprocess wrappers: never truncate stderr from the HEAD (LESSON-108)

**Trap:** `err = result.stderr[:300]` shows INFO/WARNING log prelude, not the real error. Python's `logging` module writes *every* level to stderr, so the first 300 chars of a failing task look identical to a successful one.

**Rules for every subprocess wrapper (auto_checkpoint, hitl, run_task callers, etc.):**

1. **Pattern-match real errors first.** Scan stderr+stdout for `Traceback | Exception | RuntimeError | ERROR | FATAL | status=error | budget_exceeded` and surface those lines. If none match, fall back to stderr[-400:] (TAIL, not head).
2. **Persist full output to disk on every run.** Write `logs/<wrapper>-runs/<ts>.log` containing both stdout and stderr. `[:300]` snippets are not post-mortem artifacts — full logs are.
3. **Catch `subprocess.TimeoutExpired` explicitly.** An uncaught timeout crashes the wrapper itself instead of producing a diagnosable alert. Emit a distinct "TIMEOUT" path.
4. **Distinguish crash (wrapper exception) from failure (child non-zero).** Different alert templates — the root cause is in different places.

Reference implementation: `auto_checkpoint.py v3` (Air, `~/nous-agaas/auto_checkpoint.py`).

### AP-15 — Never string-compare ISO 8601 timestamps (LESSON-109)

**Trap:** `events_last_seen > KNOWN_FROZEN_AT` as a raw string `>` compare is false-positive prone when the two strings differ in millisecond precision or timezone format. Example:

- `"2026-04-05T22:08:05"` vs `"2026-04-05T22:08:05.856+05:00"` — same moment, but Python's lexicographic `>` returns `True` because the second string is longer and all shorter chars match.

A watcher built on this kind of compare fires a false "event resumed" alert, writes a state file, and *retires itself* — so it becomes silently deaf to the real event.

**Rules for any timestamp-based watcher:**

1. **Parse with `datetime.fromisoformat()` (Python ≥ 3.7) before comparing.** Never `>` / `<` raw ISO strings.
2. **Require a minimum forward delta, not strict inequality** — `(lhs - rhs).total_seconds() >= 1.0`. Sub-second noise is not movement.
3. **Add a "stale restore" guard.** If the timestamp advanced but `events_age_seconds > 3600`, it's likely a DB restore, not a real event. Don't fire.
4. **Test with the EXACT baseline** (same precision + same tz format). One unit test catches this at dev time.
5. **Fire-once state files are one-way doors.** A false positive with auto-retire creates silent deafness. Validate the fire condition can't be falsified by any input before installing this pattern.

Reference implementation: `satory_events_watcher.py v2` (Air, `~/nous-agaas/tools/satory_events_watcher.py`).

### AP-16 — Every launchd plist MUST have EnvironmentVariables with PATH (LESSON-115)

**Trap:** macOS launchd runs jobs with minimal PATH (`/usr/bin:/bin:/usr/sbin:/sbin`). This excludes `/opt/homebrew/bin` (Python 3.14) and `/usr/local/bin` (docker). Scripts that work in interactive SSH fail silently from launchd.

**Symptoms:** `FileNotFoundError: docker` (masked by ModelEscalator auto-escalation), `TypeError: unsupported operand type(s) for |: 'type' and 'type'` (Python 3.9.6 loaded instead of 3.14).

**Rules:**

1. **Every `com.nous.*` plist MUST include:**
```xml
<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key>
    <string>/Users/madia</string>
</dict>
```

2. **Scripts should also use full binary paths** as belt-and-suspenders: `/usr/local/bin/docker`, `/opt/homebrew/bin/python3`.

3. **When creating a new plist, copy from `com.nous.telegram-poll.plist`** (known-working template with EnvironmentVariables).

4. **`/audit infrastructure` must check** for missing EnvironmentVariables in all plists.

### AP-17 — Never hardcode /usr/bin/python3 in launchd ProgramArguments (LESSON-116)

**Trap:** Even with AP-16's `EnvironmentVariables PATH` fix, the `PATH` env var has NO effect when the interpreter is an absolute path in `<ProgramArguments>`. `/usr/bin/python3` = macOS system Python 3.9.6 which lacks `str | None` union syntax (Python 3.10+). Scripts fail with `TypeError: unsupported operand type(s) for |: 'type' and 'type'` — or worse, import silently with degraded behavior.

**Rule: Always use `/opt/homebrew/bin/python3` in ProgramArguments.**

Audit check (add to `/audit infrastructure`):
```bash
# Should return ZERO results
grep -l "/usr/bin/python3" ~/Library/LaunchAgents/com.nous.*.plist
```

Two-level launchd PATH mental model:
1. **Bash scripts** → resolved by `PATH` env var (AP-16)
2. **Direct interpreter in ProgramArguments** → absolute path, `PATH` irrelevant (AP-17)

### AP-13 — Watchdog must be independent and self-healing (LAW-014)

**LAW-014.** An independent watchdog MUST monitor factory health at all times. If the factory crashes, the watchdog diagnoses and fixes automatically without human intervention.

Current watchdog on Air:
- `com.nous.nightly-audit` launchd (04:00 Almaty) runs `~/nous-agaas/tools/nightly-audit.sh`
- Checks: OpenClaw running, port 18789 reachable, LiteLLM responding, telegram-poll launchd active, wiki-sync active, gbrain doctor, end-to-end factory probe
- Reports green/red via @nousAGaaSbot

Watchdog scope restrictions (HARD):
- CAN restart services: `docker restart openclaw`, `launchctl stop/start com.nous.litellm`
- CANNOT modify `config.py`, `.env`, or watchdog scripts themselves
- CANNOT make purchases, sign contracts, or send money

Recovery order on factory down:
1. `docker restart openclaw` (most common fix)
2. `launchctl stop com.nous.litellm && launchctl start com.nous.litellm`
3. Check ZAI/OpenRouter balance if factory probe fails (error 1113 = resource package)
4. If wiki-sync dead: `cd ~/nous-agaas/wiki && git pull --rebase bare main`
5. If 5+ restarts fail: escalate to Madi (presidential-level per LAW-010)

## Rules absorbed from lessons

- **LESSON-088:** Atomic state writes with `os.replace()`. See AP-5.
- **LESSON-090:** Native pip over Docker for Python services on macOS ARM64. See AP-2.
- **LESSON-091:** `scp tar + docker load -i`, never pipe. See AP-3.
- **LESSON-092:** OpenClaw config via `docker cp`, never bind-mount. See AP-4.
- **LESSON-094:** Mount host paths into `/opt/`, not `/root/`. `chmod o+rX`. See AP-1.
- **LESSON-097:** State-change alerts; smart-skip quiet crons; tiered reliability (process resilience → mechanical checks → daily intelligent → on-demand). See AP-6.
- **LESSON-099:** Configure LiteLLM fallbacks for every primary model. Reasoning models need max_tokens≥8192. See AP-7.
- **LESSON-100:** Always `git pull --rebase` before push in shared repos. See AP-8.
- **LESSON-101:** Rotate OpenClaw session daily; use OpenRouter for GLM-5.1 internationally. See AP-9, AP-10.
- **LESSON-066:** macOS TCC blocks /bin/bash under launchd — grant FDA or use Claude Code shell. See AP-11.
- **LESSON-089:** macOS SSH public-key auth is silently blocked by PAM/SACL. Use Tailscale SSH (`tailscale up --ssh`). See AP-12.
- **LESSON-108:** Subprocess wrappers must never truncate stderr from the HEAD — first 300 chars are INFO noise. Pattern-match real errors, persist full output, catch TimeoutExpired. See AP-14.
- **LESSON-109:** Never `>` / `<` raw ISO 8601 timestamp strings — millisecond precision and tz format differences cause silent false positives. Parse with `datetime.fromisoformat()`, require ≥1-second forward delta, guard against stale DB restores. See AP-15.
- **LESSON-115:** Every launchd plist MUST have EnvironmentVariables with PATH including `/opt/homebrew/bin:/usr/local/bin`. Scripts should also use full binary paths (`/usr/local/bin/docker`, `/opt/homebrew/bin/python3`). See AP-16.

- **LESSON-034:** Never edit files in a git working copy without committing. Branch operations (checkout, rebase) reset to last commit -- uncommitted edits are ephemeral and silently lost.
- **LESSON-061:** Never `rm` wiki files to resolve git conflicts; use `git stash push -u` or `cp` to `/tmp` first. Deletion of `raw/` or `pages/` files is real data loss that propagates through the bare repo within 60 seconds.
- **LESSON-106:** Every env var used by a launchd-managed service must live in that service's own `.env` file, not only in the project root `.env`. Services do not inherit the parent env -- the plist declares exactly which env file to source.
- **LESSON-116:** Never hardcode `/usr/bin/python3` in launchd `ProgramArguments` -- it resolves to macOS system Python 3.9.6 regardless of PATH. Always use `/opt/homebrew/bin/python3`. See AP-17.

- **LAW-014:** Independent watchdog monitors health. Auto-restarts on crash. Escalate to Madi only after 5 failed restarts. See AP-13.



### AP-18 — When LiteLLM model is unhealthy, test API key with known-good model before blaming key (LESSON-126)

**Trap:** LiteLLM returns  but sessions 29-31 misdiagnosed this as "bad API key" and escalated to Madi. The key was valid — the model ID was wrong ( vs correct ). One curl with  would have proved the key worked.

**Rule:** When LiteLLM marks a model unhealthy:
1. Read the actual error message (not_found vs auth_error vs rate_limit)
2. If  — the model ID is wrong, not the key
3. Test key with  
4. Only escalate "regenerate key" to Madi if auth_error with a known-good model ID


### AP-19 -- macOS command compatibility in automation (LESSON-125)

All shell commands in launchd scripts must work on macOS. Memory: sysctl + vm_stat (not free -h). Version parsing: test actual output format. /status handler must use platform-aware checks.

### AP-20 -- OpenClaw workspace cleanup after boot (LESSON-125)

After container restart, verify workspace has canonical SOUL.md, USER.md, AGENTS.md, and HEARTBEAT.md. Delete BOOTSTRAP.md, IDENTITY.md, and TOOLS.md if empty/template. Delete USER.md only if it is still an empty/template file AND `pages/systems/nous-agent-user.md` is missing; otherwise USER.md is first-class runtime substrate.

### AP-62 -- Agent identity files are runtime substrate, not passive docs

**Trigger:** Madi asks for the three-file agent constitution (`SOUL.md`, `USER.md`, `AGENTS.md`) or audits why OpenClaw sounds generic, forgets Madi, or fails to apply the second-brain operating model.

**Root cause found 2026-04-27:** the vault had `pages/systems/nous-agent-soul.md` and `pages/systems/nous-agent-procedures.md`, and later gained `pages/systems/nous-agent-user.md`, but `tools/wiki-to-runtime-rsync.sh` only synced skills, `_gbrain`, tools, and tenants. The docs claimed SOUL/AGENTS were mirrored into runtime, but the script never copied them. OpenClaw runtime therefore kept an old generic `SOUL.md`, old `AGENTS.md`, and a blank/template `USER.md`.

**Rule:** Treat agent identity files exactly like skills: canonical source in Obsidian, runtime copies mechanically synced, parity tested.

Canonical sources:
- `pages/systems/nous-agent-soul.md` -> OpenClaw `SOUL.md`
- `pages/systems/nous-agent-user.md` -> OpenClaw `USER.md`
- `pages/systems/nous-agent-procedures.md` -> OpenClaw `AGENTS.md`

Runtime targets:
- `/home/node/.openclaw/workspace/{SOUL.md,USER.md,AGENTS.md}`
- `/opt/nous-agaas/agents/{SOUL.md,USER.md,AGENTS.md}`
- `/home/node/.openclaw/workspaces/grok-ceo/USER.md` only; keep grok-ceo's Tier-1-specific SOUL/AGENTS unless deliberately edited.

**Mechanical gate:** `tools/test_agent_identity_runtime_parity.sh`
- Default: skips when Docker/OpenClaw is unavailable so Mac/VPS structural tests remain portable.
- Air production proof: `REQUIRE_OPENCLAW=1 bash tools/test_agent_identity_runtime_parity.sh` must pass.
- Any future change to SOUL/USER/AGENTS must run wiki-to-runtime rsync, then this parity test.

**Anti-pattern:** editing runtime `USER.md` directly inside the OpenClaw container. That change dies on restart or drift. Edit the vault source, sync, test, then let gbrain index it.

### AP-63 -- Burst CI is disposable test substrate, not an always-on factory host

**Trigger:** Madi asks to use Blacksmith / `@useblacksmith` / 32-vCPU runners to reduce local OpenClaw test bottlenecks.

**Root cause found 2026-04-27:** local OpenClaw work is CPU-constrained on Mac/Air, but the vault had no GitHub Actions lane and several tests assumed Mac/Air absolute paths or stale historical doctrine. Moving the whole factory to remote runners would add secret, Telegram, launchd, and state-sync risk. The correct first move is a disposable burst lane that runs only portable structural/unit tests.

**Rule:** Use Blacksmith for fast, stateless CI; keep Air as the 24/7 factory. Initial Blacksmith workflows must be:
- Manual trigger first (`workflow_dispatch`) until a remote green run proves the app/repo wiring.
- Secret-free: no Telegram tokens, no Todoist/Notion tokens, no production LiteLLM keys, no Air SSH keys.
- Portable: tests use repo-relative paths or env overrides, never `/Users/madia/...` or `/Users/madia/nous-agaas/...` unless the test is explicitly Air-only and skipped by default.
- Bash-3.2-safe: local scripts must run under macOS `/bin/bash`; no `mapfile`/`readarray` or Linux-only flags unless guarded.
- Doctrine-current: a CI test may not preserve an obsolete expectation just because it is old; if the runtime rule changed (example: `_gbrain/` syncs additively), update the test to the current skill rule before adding it to burst CI.
- Script-first: workflow YAML calls a local script (`tools/blacksmith_burst_tests.sh`) so the exact suite can run on Mac/Air before remote execution.
- Runner-pinned: Linux burst lane uses `blacksmith-32vcpu-ubuntu-2404` for CPU-heavy parallel syntax/test passes.
- Expand by proof: after one remote green run, add sharded OpenClaw evals; after two stable runs, consider Docker/cache lanes. Do not attach production secrets until a separate policy gate exists.

**Mechanical gate:** `tools/blacksmith_burst_tests.sh` compiles Python in parallel, runs structural shell gates, runs portable Python unit tests, and includes current DeepSeek model-truth fixtures so model-detector allowlists cannot silently stale.

**Anti-pattern:** replacing Air launchd jobs, Telegram poller, or runtime OpenClaw probes with Blacksmith jobs. Blacksmith is burst compute, not the president interface or memory substrate.

### AP-64 -- Fast heartbeats must not deep-probe every model/provider

**Trigger:** Telegram state-change alerts show transient model deaths for OpenRouter/ZAI shared providers while LiteLLM readiness, OpenClaw, Telegram, and task routes recover on the next probe.

**Root cause found 2026-04-27:** `light-probe.sh`, `morning-brief.sh`, and `nightly-audit.sh` used LiteLLM `/health` as a liveness check. `/health` is not just "is LiteLLM alive"; it deep-probes configured model endpoints. Running that on a 15-minute heartbeat hit shared OpenRouter/ZAI provider paths and surfaced transient 429s such as `deepseek/deepseek-v4-flash is temporarily rate-limited upstream`. The monitor was amplifying provider noise and then paging the operator for it.

**Rule:** Split LiteLLM checks by depth:
- Fast heartbeat: `/health/readiness` or `/health/liveliness` with a short timeout.
- Deep model canary: explicit, cached, slower cadence, with root-cause log and known-flap suppression.
- Task-path truth: `run_task.py`/model escalator results and daily evals, not raw provider canary flips.

**Implementation:** `tools/light-probe.sh` now caches deep `/health` model state for four hours, uses readiness for fast LiteLLM liveness, and treats shared OpenRouter DeepSeek V4 Flash/Pro 429s like existing `zai/glm-4.5-flash` monitor-only flaps until BYOK/direct provider routing exists. `tools/morning-brief.sh` and `tools/nightly-audit.sh` now use readiness and no longer print "all systems 100%" from narrow heartbeats.

**Verification gotcha:** with `set -u`, initialize `TS` and `NOW_EPOCH` before model-health cache logic. Air live verification caught an unbound `NOW_EPOCH` abort when the timestamp was initialized only in the later compare block.

**Anti-pattern:** adding more providers and then probing every provider every 15 minutes from a cron. First classify provider role and criticality, then decide whether a failed canary should page, degrade, or only log.

### AP-65 -- Broken deep model probes must not write question-mark sentinels into state

**Trigger:** Nightly review flagged a low-severity `light-probe.sh` concern: when the four-hour cached model-health check missed its cache and the deep LiteLLM `/health` call timed out or returned unparsable data, the fallback chain could write `models_healthy="?"`, `models_unhealthy="?"`, or `dead_models="?"` into `light-probe-state.json`.

**Root cause found 2026-04-28:** AP-64 correctly reduced provider-canary load, but the implementation used `?` as both "field missing" and "unknown value." That made the state file itself carry fake model-health facts when no previous/cache baseline existed.

**Rule:** Health state JSON must contain only observed values or deliberately omit the field. Do not persist placeholder sentinels as if they are facts. If a deep probe is broken and there is no previous/cache baseline, log the probe failure and leave model fields absent for that run; compare logic must skip missing fields instead of generating a state-change alert.

**Implementation:** `tools/light-probe.sh` now reads JSON fields through a helper with explicit defaults, initializes model-health fields to empty strings instead of `?`, writes model-health keys only when all three values are known, and compares state fields with an internal `__missing__` sentinel that is never persisted.

**Verification:** `bash -n tools/light-probe.sh` passes locally. Air live verification must additionally confirm `~/nous-agaas/logs/light-probe-state.json` contains no `?` after a probe run.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-66 -- Probe scripts must use least-privilege container diagnostics

**Trigger:** A Nous-GPU collector audit re-ran `tools/test_nous_gpu_wg0_collector_live.sh` and found the live validator still read WireGuard handshakes through a host-sudo path, while sibling health code already used `docker exec nous-wg wg show wg0 ...`.

**Root cause found 2026-04-28:** The validator was written during the host-WireGuard phase and did not receive the same least-privilege refactor as `tools/nous_gpu_collector_health.sh` after the Docker `nous-wg` pivot. That created needless privilege coupling for a read-only probe and made future rotation/audit work depend on host sudo behavior instead of the actual runtime owner.

**Rule:** Monitoring and validation scripts must read runtime state from the component that owns it. For Dockerized infrastructure, prefer `docker exec <service-container> <read-only command>` over host sudo. Host sudo is allowed only when the runtime state is unavailable through the owning service container, and the script must say why.

**Implementation:** `tools/test_nous_gpu_wg0_collector_live.sh` now reads `wg show wg0 latest-handshakes` through configurable `WG_CONTAINER="${WG_CONTAINER:-nous-wg}"`, matching the health probe pattern.

**Verification:** `rg` must find no host-sudo WireGuard handshake path in live tools, and the Air-side live validator must still reach Check 1 through the container path.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-67 -- Air disk pressure cleanup must prune Docker cache/dangling layers first

**Trigger:** During the AGaaS/DGX Spark substrate audit on 2026-04-28, Air's APFS Data volume was at 97% capacity with only 13 GiB free. A broad `du -xhd 1 /System/Volumes/Data` scan was too heavy for the live host and had to be killed.

**Root cause found 2026-04-28:** The first safe, high-yield deletion target was Docker Desktop state, not the Nous runtime repo. `~/nous-agaas` was only 881 MiB. Docker Desktop storage was 53 GiB, `docker system df -v` showed 14.89 GiB of build cache, and `docker image ls -f dangling=true` showed old dangling OpenClaw-era images. The only running production container was `openclaw` on the pinned `ghcr.io/openclaw/openclaw:2026.4.14` image.

**Rule:** When Air disk pressure is red, inspect Docker Desktop before broad filesystem cleanup:

1. Prove what is running: `docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Size}}'`.
2. Inspect reclaimable Docker state: `docker system df -v` and `docker image ls -f dangling=true`.
3. First prune only build cache and dangling layers: `docker builder prune -af` and `docker image prune -f`.
4. Do not use `docker system prune -a` or volume prune unless a human-approved inventory proves the named images/volumes are dead.
5. Verify both APFS free space and service health afterward: `df -h / /System/Volumes/Data` plus `docker ps` health for `openclaw`.

**Verification:** This session reclaimed enough Docker/APFS space to move Air from 13 GiB free / 97% Data usage to 43 GiB free / 91% Data usage while keeping `openclaw` `Up ... (healthy)`. The build-cache prune reported 14.89 GiB removed; dangling image prune reported 3.98 GiB reclaimed; APFS free space increased by about 30 GiB after Docker Desktop released sparse image blocks.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-21 -- Clean stale branch tracking configs after repo rename (LESSON-127)

When a git repo renames its default branch (e.g., master→main), old `branch.master.remote` / `branch.master.merge` configs persist in `.git/config`. These cause intermittent "Cannot rebase onto multiple branches" errors when `git pull --rebase` runs concurrently with other git processes (e.g., wiki-sync + run_task.py write-back racing). **Fix:** after any branch rename, run `git config --unset branch.<old>.remote && git config --unset branch.<old>.merge` on ALL clones. **Check:** `git config --list | grep branch` should show only the current branch tracking.

### AP-22 -- gbrain autopilot creates junk concept pages from broken wikilinks (LESSON-129)

gbrain autopilot's link extraction resolves `[[wikilinks]]` by creating stub pages for any target that doesn't exist. When a page contains a malformed link (e.g., `[[gbrain_sync_wrapper.sh]]`, `[[-v var]]`, `[[keona-it\]]`), autopilot creates a garbage concept page with an `auto-stub` tag. Session 34 found 11 such junk pages including filenames with backslashes, bash variable names, and script extensions.

**Detection (periodic):**
```bash
find pages/concepts/ -name '*.md' -newer pages/concepts/ -exec grep -l 'auto-stub' {} \;
# Also check for suspicious patterns:
find pages/concepts/ -name '*\\*' -o -name '*var*' -o -name '*.sh.md' -o -name '*.py.md'
```

**Prevention:** gbrain's autopilot should validate link targets before creating stubs. Until a fix lands upstream, run periodic cleanup:
```bash
# Find and delete auto-stub junk pages
grep -rl 'auto-stub' pages/concepts/ | while read f; do
  bytes=$(wc -c < "$f")
  if [ "$bytes" -lt 200 ]; then echo "JUNK: $f ($bytes bytes)"; fi
done
```

### AP-23 -- Known-flapping external model endpoints must NOT page the operator (session 35)

**Symptom:** `light-probe.sh` was paging Madi every 15-30 minutes as `zai/glm-4.5-flash` flapped in and out of the LiteLLM unhealthy list. Session 34 already documented this as a known flap ("ZAI endpoint intermittently degraded … monitor, don't act"), but the alert code had no suppression, so the known-noise flap was waking the operator at night.

**Root cause (5-whys):**
1. Why was Madi paged at 21:28 and 21:44? State-diff alert fired twice for the same model flipping unhealthy → healthy.
2. Why didn't `light-probe.sh` suppress? It treated every transition as alertable.
3. Why did it have no known-flapping list? AP-6 only said "don't fire fixed-schedule alerts" — no rule about externally-caused noise specifically.
4. Why not? The pattern wasn't yet abstracted from the one-off ZAI annotation in MEMORY.md.
5. Why not? Nobody promoted "monitor, don't act" from a prose annotation to a code-enforceable list.

**Rule:** Any model or external endpoint whose instability is known and annotated as "monitor, don't act" MUST be in a code-level `KNOWN_FLAPPING_MODELS` list inside the alerter, AND pair with a per-key debounce (≥ 4h default for model health, ≥ 15min for infra). Transitions that affect only the known-flapping set are logged (for audit) but never paged. If a NEW model also goes unhealthy, the alert fires as normal — known-flap suppression is intersection-safe, not union-silent.

**Implementation (deployed in `tools/light-probe.sh` session 35):**
- `KNOWN_FLAPPING_MODELS="zai/glm-4.5-flash"` near the top of the script
- `is_only_known_flapping()` helper: `symmetric_difference` of dead_models sets, `issubset(KNOWN_FLAPPING_MODELS)` ⇒ suppress
- `check_debounce()` helper: loads `light-probe-alert-history.json`, compares last-alerted-at, drops if inside window
- Separate debounce windows: model-health `DEBOUNCE_MODEL_HEALTH=14400` (4h), infra `DEBOUNCE_INFRA=900` (15min)
- Suppressed transitions logged to the normal `light-probe.log` with `[suppressed]` tag so audit is intact

**Deployment:** update `~/nous-agaas/tools/light-probe.sh` on Air. One-liner when Air SSH is restored:

```bash
# from Mac, after Tailscale reauth on Air, do:
scp "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/light-probe.sh" \
    madia@100.122.219.22:/Users/madia/nous-agaas/tools/light-probe.sh
# then wait for next 15-min cycle; verify with:
tail -30 /Users/madia/nous-agaas/logs/light-probe.log | grep -E 'suppressed|STATE CHANGE'
```

**Verification contract:** after deploy, within one hour, the log MUST contain at least one `[suppressed]` line for glm-4.5-flash, and the Telegram channel MUST have zero new state-change messages for known-flap-only transitions.

**Absorbs:** the MEMORY.md prose annotation "ZAI endpoint intermittently degraded … monitor, don't act" is now code-enforced. If a new model becomes known-flapping, append to `KNOWN_FLAPPING_MODELS` (comma-separated) — do NOT remove without evidence the endpoint has stabilized for ≥48 hours.

Source: session 35 Garry-Tan enforcement audit, 2026-04-16; no LESSON file written — evidence lives in this AP + the Timeline entry below + gbrain timeline on `infrastructure`.

### AP-24 -- TaskCompleted hook stayed on LAW-015 v1 after session-35 RULE ZERO (2026-04-17 session 36)

**Symptom:** Session 36 attempted to complete an audit task and `~/.claude/hooks/task-completed-enforce.sh` blocked with: "LAW-015 GATE 8: explicit bug-fix task but no new LESSON file written in the last 24h. Write it at: pages/lessons/individual/LESSON-XXX-<slug>.md". This contradicts session-35 RULE ZERO (pre-commit hook rejects new LESSON files); any bug-fix task would be impossible to complete.

**Root cause (5-whys):**
1. Why did TaskCompleted demand a LESSON? Gate 8 hardcoded `grep -c 'pages/lessons/individual/LESSON-'` as its evidence check.
2. Why wasn't it updated during session 35? Session 35 touched the pre-commit hook and SKILL.md policy, but missed the enforcement hook living outside the vault at `~/.claude/hooks/`.
3. Why is the hook outside the vault? It's a Claude Code CLI hook (user-scoped), not a git hook — different lifecycle, no pre-commit enforcement on it.
4. Why didn't session-35 verification catch it? Session 35 tested the pre-commit hook with a dummy LESSON commit; it didn't simulate TaskCompleted flow.
5. Why the asymmetry? There was no checklist item "enumerate every enforcement point that references LESSON-file pattern and update all of them simultaneously."

**Rule:** Any session that changes the LESSON/SKILL enforcement policy MUST enumerate and update every enforcement point, not just the nearest one. Enforcement points known 2026-04-17 (updated session 36.5):
- `<vault>/.git/hooks/pre-commit` on Mac/VPS/Air wiki repos
- `~/.claude/hooks/task-completed-enforce.sh` **on EVERY dev machine that runs Claude Code** (Mac Pro, Air, any future laptop). Session 36.5 found Air's copy still had the pre-session-35 broken Gate 8 because session 36 fixed only Mac.
- `mistake-to-skill/SKILL.md` (doctrinal source)
- `CLAUDE.md` (Mac project + wiki)
- `LAW-015`, `AMD-005` (codified)
- `tools/lesson_absorption_watcher.py` (script file — obsolete under RULE ZERO)
- `com.nous.lesson-absorption` Air launchd entry (unloaded + plist archived 2026-04-17 session 36.5; was firing every 6h after session 35 missed it)
- `tools/skill_from_debug.py` — references `pages/lessons/individual/LESSON-NNN-slug.md` as INPUT only (absorption tool); doesn't create new LESSONs. Keep as-is.
- `tools/wiki_lint.py` — references the LESSON path pattern in help/docs only. Not an enforcement point.
- any other code that greps `pages/lessons/individual/LESSON-`

**Concrete fix applied 2026-04-17:**
- `~/.claude/hooks/task-completed-enforce.sh` Gate 8 rewritten: now counts `pages/skills/[^/]*/SKILL\.md` edits in last 24h (skill updates) instead of LESSON adds. Error message tells agents the correct path: SKILL.md edit + gbrain timeline entry.
- Vault-task classifier regex broadened so audit/phase/session/skill/hook/gbrain keywords trigger vault gates (previously "Phase 0 — Pre-flight gates" was misclassified as product).

**Verification contract:** After fix, a task description tagged `[risk] REQ-AUDIT-036 audit/session-36/X` classifies as vault. A session that updates a SKILL.md in the last 24h but writes zero LESSONs passes Gate 8.

**Anti-pattern for future sessions:** when changing any policy, search `grep -r 'pages/lessons/individual/LESSON-'` across `~/.claude/hooks/`, `tools/`, `scripts/`, and both vault + wiki working copies. The enforcement surface is wider than the policy document.

**Why no new LESSON-131 file:** because that is exactly what this AP prohibits. Evidence lives here + gbrain timeline.

### AP-25 — Vault-task classifier regex must cover audit/monitoring vocabulary (session 37, 2026-04-17)

**Symptom:** Session 37 opened audit tasks `Re-run CHECK-5 launchd 17 jobs EXIT=0` and `Re-run CHECK-6 service health`. TaskCompleted hook blocked both with:
- `LAW-006 GATE 1: missing REQ-xxx mapping`
- `LAW-011 GATE 2: missing business tag`

Both tasks are vault/audit work, not product work — should have been classified `IS_VAULT_TASK=true` and skipped Gates 1+2. Classifier regex in `~/.claude/hooks/task-completed-enforce.sh:56` missed `check|health|service|launchd|status|parity|monitoring|verify|probe|liveness|readiness|heartbeat` and the tasks fell into the "unclassified → product" default at line 67.

**Root cause (5-whys):**
1. Why did the hook demand REQ-xxx? Because IS_PRODUCT_TASK defaulted true when neither product nor vault keywords matched.
2. Why didn't vault match? Regex didn't include any of `check|health|service|launchd|status|parity|monitoring`, yet audit tasks routinely use those exact words.
3. Why the gap? Session 36 added `sync|root-cause|timeline|hook` but stopped there; didn't enumerate monitoring vocabulary.
4. Why wasn't it caught by tests? Classifier has no test harness — every session rediscovers gaps by getting blocked at commit time.
5. Why the asymmetric coverage vs AP-24 fix? Session 36 fixed Gate 8's LESSON-demand but didn't audit the classifier end-to-end.

**Rule (amending AP-24):** Whenever a vault-task is misclassified as product because of missing vocabulary, add the missing terms to the regex AND document them here. The classifier must cover the full operational lexicon, not just the last incident's words. Current operational vocabulary added 2026-04-17: `check|health|service|launchd|status|parity|monitoring|verify|probe|liveness|readiness|heartbeat|MD5|plan|spec|resolver|rsync|ingest|embed|qmd|runtime|cron`.

**Concrete fix applied 2026-04-17:** patched Mac `~/.claude/hooks/task-completed-enforce.sh:56` to add the 20 missing terms above. Verified with a dry-run: task subject "Re-run CHECK-5 launchd" now classifies as vault-task (was falling into product default). Pending Air deployment (will rsync hook under AP-24 "EVERY dev machine" rule during session-37 Phase D1).

**Verification contract:** a task subject containing any of `{check, health, service, launchd, status, parity, monitoring, verify, probe, liveness, readiness, heartbeat, MD5, plan, spec, resolver, rsync, ingest, embed, qmd, runtime, cron}` classifies as `IS_VAULT_TASK=true` on both Mac and Air.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-26 — Auto-update scripts must target the npm prefix they install to (session 37, 2026-04-17)

**Symptom:** Morning-brief reported Claude CLI stuck at 2.1.71 on Air for 6+ weeks (Mar 7 → Apr 17), while Mac was already on 2.1.112. Manual `npm install -g @anthropic-ai/claude-code@latest` on Air just changed "3 packages in 1s" — a no-op because user-scope install was already 2.1.112.

**Root cause:** Two parallel Claude CLI installs on Air:
- `/usr/local/bin/claude` → `/usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js` = v2.1.71 (ROOT-owned, from March Homebrew or `sudo npm -g` era, never updated because npm can't write /usr/local as user)
- `/Users/madia/.npm-global/bin/claude` → `~/.npm-global/lib/node_modules/@anthropic-ai/claude-code/cli.js` = v2.1.112 (USER-owned, current)

`~/nous-agaas/tools/morning-update-apply.sh` hardcodes `/usr/local/bin/claude --version` for its CURRENT check, then runs `npm install -g @anthropic-ai/claude-code@latest` which goes to USER prefix (`~/.npm-global`). The script forever sees the stale root install. Fix attempts all "succeed" but never bump `/usr/local/bin/claude`.

Why the asymmetry went unnoticed: the script fires at 05:07 Almaty, telegram report showed "install attempted, version still 2.1.71" as a NOTIFIED line and nobody triaged because there was no actionable error — just a quiet drift.

**Rule:** Update-in-place scripts must verify the SAME binary that `npm install -g` writes to. Two enforcement points:
1. Either pin `CLAUDE_BIN="$HOME/.npm-global/bin/claude"` and use it for both CUR and NEW_VER checks, OR
2. Use `$(command -v claude)` after an explicit `PATH="$HOME/.npm-global/bin:$PATH"` prefix.

Hardcoding any absolute path to `/usr/local/bin/` while npm prefix is `~/.npm-global` (macOS user-scope default after Homebrew node) is a silent-drift bug.

**Concrete fix applied 2026-04-17:** patched `~/nous-agaas/tools/morning-update-apply.sh` on Air (both lines 42 and 49) to use `$HOME/.npm-global/bin/claude`. Backup kept at `.bak-session-37`. Also copied the fixed script into the vault at `tools/morning-update-apply.sh` (was previously Air-only, untracked) for version control. Dry-run verified: script now reports 2.1.112 correctly.

Correction 2026-04-29: the root install at `/usr/local/bin/claude` is NOT safe to call "unreferenced" unless an actual runtime grep proves it. Air `tools/command_center.py` still referenced it for `/code`, so the updater was current while Telegram `/code` stayed stale. The root install may be deleted only after `rg '/usr/local/bin/claude|CLAUDE_CMD' ~/nous-agaas ~/.claude ~/Library/LaunchAgents` proves no runtime caller remains.

**Verification contract:** `ssh air '$HOME/.npm-global/bin/claude --version'` == `npm view @anthropic-ai/claude-code version` within 24h of release. Morning-brief telegram line "Claude CLI: vX.Y.Z" == user-scope install version.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-68 — Runtime router paths must match updater paths (2026-04-29)

**Symptom:** Morning update reported `Claude Code CLI: 2.1.119 -> 2.1.122 (auto-applied)`, but `/usr/local/bin/claude --version` on Air still returned 2.1.71 and Air `/code` routed through `command_center.py` with `CLAUDE_CMD = "/usr/local/bin/claude"`.

**Root cause:** AP-26 fixed the updater path but left a false assumption in doctrine: "the root install is unreferenced." The updater verified `$HOME/.npm-global/bin/claude`, while the production Telegram `/code` router executed `/usr/local/bin/claude`. That split creates a green update report and stale runtime behavior at the same time.

**Rules:**

1. Every CLI auto-updater must name the runtime caller paths it protects, not only the binary it installs.
2. Every command router must default to the same user-scoped binary the updater verifies, or use a shared resolver with the user path first.
3. Morning-update proof must include both `updated_binary_version` and `runtime_binary_version` for routed tools.
4. Never write "unreferenced" for a stale binary unless `rg` has been run across Air runtime, launchd plists, and vault tools.
5. If two versions of a production CLI exist on Air, the older one is a hazard until runtime path parity is proved.

**Fix applied:** Air `~/nous-agaas/tools/command_center.py` now defaults `CLAUDE_CMD` to `/Users/madia/.npm-global/bin/claude`, permits override through `CLAUDE_CMD`, and prepends `/Users/madia/.npm-global/bin` to the minimal Claude env PATH. The `/code` audit default was updated in `audit` AP-36 to check the same user-scoped binary.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-69 — Session rotation must preserve OpenClaw JSONL headers (2026-04-29)

**Symptom:** `com.nous.session-rotate` exited `0` but `session-rotate.err.log` filled with `line 19: /home/node/.openclaw/...jsonl: No such file or directory`, and OpenClaw logs showed invalid session-header repairs. The job was green at launchd level while writing bad session files.

**Root cause:** `SIZE=$(docker exec openclaw wc -c < "$f")` performs `< "$f"` on the Air host shell, not inside the container, so every container path reports missing. The same script then replaced JSONL session files with `[]`, which is not an OpenClaw JSONL session header. A valid file starts with a `{"type":"session",...}` line; deleting that header corrupts the file shape the maintenance job is supposed to protect.

**Rules:**

1. Container file probes that use shell redirection must run the redirection inside `docker exec ... sh -c`, not in the host shell.
2. OpenClaw session rotation may trim history, but must preserve the first `type=session` JSONL header line.
3. If a session file is already invalid or has no session header, skip it and log the skip instead of rewriting it again.
4. Every session-rotation script change needs a fixture test that proves valid headers are preserved and invalid files are not modified.

**Fix applied:** `tools/session_rotate.sh` now measures size inside the container and trims valid files to the first header line. `tools/test_session_rotate_preserves_header.sh` stubs Docker against a fake container filesystem and fails if rotation writes `[]` or drops the header.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-70 — CI runner readiness requires actual job assignment (2026-04-29)

**Symptom:** The private GitHub mirror had an active manual workflow, `.github/workflows/blacksmith-burst-tests.yml`, using `runs-on: blacksmith-32vcpu-ubuntu-2404`. That made the Blacksmith lane look configured, but there were no prior runs and the repo runners API returned `total_count=0`.

**Root cause:** A workflow file is only a request for capacity. It does not prove that the external runner provider or GitHub App is installed for the repo. The first manual proof run stayed `queued`; job `Portable burst suite` had `runnerName=null` and `runnerGroupName=null` after the observation window. The run was cancelled rather than left as dead queue noise.

**Rules:**

1. Never call burst CI "connected" or "ready" from YAML presence alone.
2. Readiness proof requires at least one workflow run whose job leaves `queued` and has a non-null runner assignment.
3. If a proof run stays queued with `runnerName=null`, classify the blocker as runner/app installation, not test-suite failure.
4. Cancel dead proof runs after capturing URL/status evidence, then record the root cause on the tracking issue.

**Verification evidence:** GitHub run `25091836550` for `mayazbay/nous-agaas-private` queued on `blacksmith-32vcpu-ubuntu-2404`, had no runner assignment, and was cancelled. Issue #1 now holds the audit comment and next action: connect Blacksmith to the private repo, then rerun.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-27 — Air `~/nous-agaas/` git repo has `tools/` untracked (risk, session 37, 2026-04-17)

**Symptom:** Fixed `morning-update-apply.sh` on Air and went to commit → `~/nous-agaas/.git` shows entire `tools/` directory UNTRACKED. Existing git history only has root-level `*.py` files (8 factory scripts from session-33 commit). `tools/` is 6 weeks of automation work sitting on one machine's disk.

**Root cause:** Session-33 initial commit covered "8 factory scripts + litellm config" at the repo root, but `tools/` was gitignored or just never `git add`ed. Subsequent sessions dropped scripts there for convenience without realizing they weren't tracked.

**Rule:** Every shell/python automation script on Air must live in a git-tracked path. Two options:
1. Add `~/nous-agaas/tools/` to the Air scripts repo (same origin).
2. Migrate all scripts into the wiki `tools/` directory (vault is the single source of truth, wiki-to-runtime-rsync propagates).

Prefer option 2: the vault is the SSOT per LAW-005. Scripts on Air should be deployed FROM the vault, never authored ON Air. Session 37 started this: copied `morning-update-apply.sh` into vault `tools/`. Session 38 task: audit Air `~/nous-agaas/tools/*` vs vault `tools/*`, move all vault-absent scripts into vault.

**Concrete fix deferred:** not doing the full migration this session — too broad. Logged here + timeline as session-38 work.

**Verification contract:** After migration, `ssh air 'cd ~/nous-agaas && git status tools/' | grep -c "nothing"` == 1 (clean working tree), and every `tools/*.sh` + `tools/*.py` on Air has a matching file in vault `tools/` with the same MD5.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-29 — `wiki-to-runtime-rsync` scope gap: only syncs `pages/skills/`, NOT `wiki/tools/` (session 37.6, 2026-04-17)

**Symptom:** Madi saw Telegram flap alerts for `zai/glm-4.5-flash` at 2026-04-16 23:47 and 2026-04-17 00:03. Both SHOULD have been suppressed by session-35 AP-23's `KNOWN_FLAPPING_MODELS` logic. They weren't.

**Investigation (session 37.6):** `/Users/madia/nous-agaas/tools/light-probe.sh` mtime was `2026-04-17 10:49` on Air runtime. The session-35 fix to `wiki/tools/light-probe.sh` was committed to the vault on 2026-04-16, but it sat in vault for **~18 hours** before a manual `scp` (session 36.5 Phase D.9) put it on the runtime. During that window the stale runtime script paged Telegram twice on genuinely-flapping glm-4.5-flash.

After the manual deploy at 10:49, the suppression works correctly (log shows `[2026-04-17T11:17:39] SUPPRESSED (known-flap or debounce)` and `[2026-04-17T11:32:55] SUPPRESSED`). So the flap ITSELF is now handled — the question is why vault→runtime took 18h.

**Root cause — scope of the watcher:**

```xml
<!-- ~/Library/LaunchAgents/com.nous.wiki-to-runtime-rsync.plist -->
<key>WatchPaths</key>
<array>
  <string>/Users/madia/nous-agaas/wiki/pages/skills</string>
</array>
```

Watcher fires on `pages/skills/` edits only. Edits to `wiki/tools/*.sh` or `wiki/tools/*.py` do NOT trigger rsync. Additionally, the script `wiki-to-runtime-rsync.sh` only rsyncs `WIKI_SKILLS_DIR` → `RUNTIME_SKILLS_DIR`; `wiki/tools/` → `runtime/tools/` is not in scope at all.

**Compounding AP-27 drift discovered:** 3 files drifted vault↔runtime:
- `tools/wiki-to-runtime-rsync.sh` — runtime has session-32 `_gbrain/` sync block; vault does NOT. Vault is STALER.
- `tools/telegram_poll.py` — runtime has Air paths (`/Users/madia/nous-agaas/...`), retry state-load, fcntl lock. Vault has OLD VPS paths (`/root/nous-agaas/...`) from before the Air migration. Vault is STALER.
- `tools/morning-brief.sh` — similar pattern, runtime has later edits.

**Direct rsync without care would DOWNGRADE the live bot** (VPS-era paths in vault telegram_poll.py would break the running Air poller).

**Rule:**
1. Before extending wiki-to-runtime-rsync to sync `wiki/tools/`, **backflow AP-27 drift first** — copy drifted runtime files INTO vault (with verification that runtime versions are what we want), commit with label "AP-27 backflow".
2. Then extend the rsync script to ALSO sync `wiki/tools/*.sh` + `wiki/tools/*.py` → `~/nous-agaas/tools/` using `rsync -av --update` (the `-u` flag is critical — skips files newer on receiver, protects against regression).
3. Extend the launchd plist `WatchPaths` to include `wiki/tools/`.
4. `launchctl unload` + `launchctl load` to pick up plist change.
5. Verify: `md5 -q` parity on ALL shared `wiki/tools/` ↔ `runtime/tools/` files after next scheduled rsync.

**Detection one-liner** (run to catch any drift):

```
ssh air 'for f in $(ls ~/nous-agaas/wiki/tools/); do if [ -f ~/nous-agaas/tools/$f ]; then W=$(md5 -q ~/nous-agaas/wiki/tools/$f); R=$(md5 -q ~/nous-agaas/tools/$f); [ "$W" != "$R" ] && echo "DRIFT: $f"; fi; done'
```

**Concrete fix deferred** (not this session — 30-min backflow needs careful diff-review to avoid regressions; scope too large for end-of-session). Linked to AP-27; session 38 should bundle both.

**Verification contract:** After fix, the session-38 QMD query `mcp__nous-wiki-qmd__query` for the session-35 `light-probe.sh` hash change should take < 15 minutes from vault edit to runtime deploy (one launchd WatchPath fire cycle).

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-28 — Confusion Protocol: stop at ambiguous infrastructure forks (gstack v0.18.0.0, 2026-04-17)

**Karpathy's #1 AI coding failure mode** in infrastructure scope: confidently placing a new service / port / path in the wrong slot → rework, data drift, or worse a cross-machine collision.

**Asymmetric-cost forks:**
- **New service host**: Air launchd vs VPS systemd vs Docker container — wrong pick = moving the service later, with launchd<->systemd semantic mismatches
- **Port binding when multiple free ports exist** — collision only shows up under load or after reboot
- **Git-tracked location**: vault `tools/` vs Air `~/nous-agaas/tools/` (current AP-27 shows this drift cost 6 weeks of untracked work)
- **Deploy path when two homes exist**: `/opt/nous-agaas/` vs `~/nous-agaas/` (AP-1 / AP-19 already lists this footgun — Confusion Protocol applies to new paths too)
- **Hook placement**: vault `.git/hooks/` (per-wiki) vs `~/.claude/hooks/` (per-dev-machine) — wrong scope = physically impossible invariant or policy contradiction

**Rule:** Before creating any new daemon / port binding / hook / git-tracked file — state both interpretations back and ASK. "Hit a fork: (A) Air launchd or (B) VPS systemd. Which?" Not "I'll put it on Air unless you object."

**Does NOT apply** to routine operations (restart, log rotate, deploy to existing path) — established APs already cover those.

### AP-30 — Parallel-agent concurrent write race on same SKILL.md (session 39, 2026-04-17)

**Symptom (session 39 audit):** Mac committed `5710451d` at 12:38:38 bumping `infrastructure` v2.25.0 → v2.26.0 with AP-29. 23 seconds later, VPS committed `c1fb42d4` at 12:39:01 adding AP-29 text to the SAME file, diverging from the same parent `ad0c4784`. Both started from vault state pre-AP-29 and both wrote AP-29 — different bytes, same intent.

**Root cause:** No single-writer convention. Mac had a session absorbing AP-29 (light-probe triage). VPS had a separate writer (unknown agent, author `CTO <cto@paperclip.ing>` = VPS root git identity) concurrently absorbing the same lesson. Both are legitimate absorption events — the architecture has no lock preventing simultaneous writes to the same `pages/skills/<skill>/SKILL.md`.

**Safety net that saved us:** `wiki_to_bare.sh` falls back to `git merge -X theirs bare/main` on rebase conflict. "Theirs" = the side that reached `bare` first (Mac's `5710451d`). VPS's divergent commits (`c1fb42d4`, `937289e1`) replay as empty on top → effectively dropped. Final convergence at `31ae7529` with Mac's content.

**Where this bites:** if VPS's version had a DIFFERENT rule (not same-intent), `merge -X theirs` silently loses it. Only works because both sides captured the same learning.

**Rule:**
1. Before starting an absorption session, `mcp__gbrain__get_page slug="pages/skills/<skill>/skill"` + note `version`. Then `git fetch vps main && git log --oneline vps/main -3` — if there's a commit on the same skill within the last 5 min from a *different* author, WAIT or ASK.
2. For high-frequency skills (`infrastructure`, `gbrain-ops`, `agent-quality`), prefer a "single-writer-per-session" convention: one agent owns edits to that skill for the session, others queue via handoff.
3. Don't rely on `merge -X theirs` to preserve intent — it preserves *bytes*. If two sessions write genuinely different rules to the same file in the same cycle, the later one is lost. Detect post-merge drop with `git log vps/main -p -- pages/skills/<skill>/SKILL.md | grep '^-###'` for AP headers removed in merge commits.

**Detection one-liner** (run at session start):

```
cd "$VAULT" && git fetch vps main -q && git log --since='30 minutes ago' --pretty='%h %an %s' -- pages/skills/ | head -10
```

If >1 author touched the same skill in the last 30 min, pause and reconcile before editing.

**Verification:** this session caught the race during Phase A of the atomic audit — all 3 wikis now at identical MD5 `c944bf27...` for `infrastructure/SKILL.md` at HEAD `31ae7529`, AP-29 intact.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-31 — TaskCompleted classifier regex fails on letter-enumerated phases + missing "gate/mandatory/atomic" vocabulary (session 40, 2026-04-17)

**Symptom (session 40 atomic audit):** TaskCompleted hook blocked task #1 `"Phase A: Mandatory session gates (1, 2, 3)"` with bogus `LAW-006 GATE 1: missing REQ-xxx mapping` + `LAW-011 GATE 2: missing business tag`. Task is clearly audit/vault work — running the 3 mandatory CLAUDE.md session gates (website lock, no code/satory/ trap, memory symlink). No product work involved.

**Root cause (5-whys):**
1. Why demand REQ-xxx? Because `IS_PRODUCT_TASK` defaulted to `true` via the "unclassified → product" fallback at `~/.claude/hooks/task-completed-enforce.sh:70`.
2. Why didn't vault match? Classifier regex at line 56 didn't cover `gate|mandatory|atomic|symlink|website.lock|memory.symlink|tan.pattern|karpathy|rule.zero`.
3. Why didn't `phase\s+[0-9]` help? Because the task uses `Phase A` (letter), not `Phase 1` (digit). Regex required a DIGIT after "phase".
4. Why the gap? Every session extends the regex with words from THAT session's blockers. Session 37 AP-25 added monitoring vocab; no one thought to test letter-enumerated phases or CLAUDE.md-gate vocabulary.
5. Why no harness? Classifier has no test suite — every session rediscovers gaps at commit time.

**Concrete fix applied 2026-04-17 (session 40):**
1. Patched `phase\s+[0-9]` → `phase\s+[0-9A-Z]` (now accepts both `Phase 1` and `Phase A`).
2. Added operational vocabulary: `gate|mandatory|atomic|symlink|website.lock|memory.symlink|tan.pattern|karpathy|rule.zero`.
3. Mac hook MD5 `c2eff41461bd5d06d712189889a8b986` at session 40 → since bumped to current `8cc618d93a65fe51c24acd00e7539ce4` via AP-32/AP-33 through sessions 43-45.
4. scp'd to Air; MD5 parity verified identical.
5. Also copied to vault `tools/task-completed-enforce.sh` for version control (following AP-26 convention).
6. Retried task completion: classifier now correctly sets `IS_VAULT_TASK=true`, firing LEGITIMATE Gate 5 (uncommitted changes) instead of bogus product gates.

**Rule (amends AP-25):** The classifier's `phase\s+[0-9]` was too narrow. Letter-enumerated phases (`Phase A`, `Phase B`, `Phase L`) are the natural shorthand for atomic-audit sessions. Any new regex token must accept both `[0-9]` and `[A-Z]` in identifier positions. Also: whenever a CLAUDE.md section introduces new vocabulary (`RULE ZERO`, `MANDATORY SESSION GATE`, `atomic audit`), the classifier MUST immediately learn it — add the terms to the regex + bump this AP. Do not wait for the next blocker.

**Verification contract:** A task subject `"Phase A: Mandatory session gates"` classifies as `IS_VAULT_TASK=true` on both Mac (`~/.claude/hooks/`) and Air (`~/.claude/hooks/`). Both hosts MD5 `019ffb87b7abfe55e9c52c4ab5e5f15e` (session 52 — `8cc618d93a65fe51c24acd00e7539ce4` → `019ffb87b7abfe55e9c52c4ab5e5f15e` transition from parallel session's `session-operating-contract` v1.2.0 hook patch). Vault backup at `tools/task-completed-enforce.sh` tracks the canonical version. (Version history in Timeline.)

**Detection one-liner (run when new audit vocabulary is coined):**
```
echo "Phase X: mandatory atomic verification check" | grep -qiE '\b(audit|gate|mandatory|atomic|phase\s+[0-9A-Z]|check)\b' && echo "classifier OK" || echo "classifier GAP — extend regex"
```

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-32 — Pre-commit RULE-ZERO hook bypassed by git renames; `--diff-filter=A` misses rename targets (session 43, 2026-04-17)

**Symptom (session 43 atomic audit):** Filesystem LESSON count went 128 → 129 between sessions. AP-10 pt 5 invariant tripped. `git log --diff-filter=A` showed `LESSON-080-design-without-deployment.md` added on 2026-04-17 14:01:53 — AFTER the session-35 hook install (08:58:31 today). Hook live-test confirmed it BLOCKS direct adds. So how did LESSON-080 sneak through?

**Root cause (5-whys):**
1. Why did LESSON-080 commit succeed? `git diff 595166da..235df138 --name-status` shows `R091  pages/lessons/LESSON-080-...md  pages/lessons/individual/LESSON-080-...md` — git detected a 91%-similarity RENAME, not an Add.
2. Why didn't the hook catch the rename? Pre-commit hook checked `git diff --cached --name-only --diff-filter=A` — `--diff-filter=A` returns ADDITIONS only. Renames go to `--diff-filter=R` (and copies to `=C`). The hook never inspected R/C.
3. Why was rename detection on? Git default `diff.renames=true`. Useful for normal workflows; defeats RULE ZERO when pre-existing off-canonical LESSON files are migrated INTO `pages/lessons/individual/`.
4. Why didn't anyone spot this earlier? Direct adds are the common path; rename-into-canonical is a rare migration path. Session-32 slug normalization absorbed most of those before hook install. The remaining trickle (LESSON-080 today) slipped silently — `--diff-filter=A` missed it.
5. Why hadn't I checked the hook for this exact bypass? The hook author's intent (per file comment line 9-10) was: "ALLOW modifications and deletions of existing LESSON files (for bookkeeping, migration, or historical correction)." They didn't realize a RENAME from `pages/lessons/LESSON-X.md` to `pages/lessons/individual/LESSON-X.md` looks like a "migration" but produces a NEW file at the canonical enforced path — so RULE ZERO should still apply at the destination.

**Concrete fix applied 2026-04-17 (session 43):**
1. Added `renames_into_canonical=$(git diff --cached --name-status --diff-filter=RC | awk '$3 ~ /^pages\/lessons\/individual\/LESSON-[0-9]+-.*\.md$/ && $2 !~ /^pages\/lessons\/individual\// {print $3}')` — catches Renames AND Copies whose DESTINATION is the canonical path AND whose SOURCE is OUTSIDE the canonical dir.
2. Combined `direct_adds` + `renames_into_canonical` into a single `new_lessons` set, sorted+unique.
3. Renames WITHIN `pages/lessons/individual/` (slug normalization, e.g. case-fix or typo-fix) STILL ALLOWED — they're not new files at the canonical path, just renames within it.
4. Mac hook MD5: `40aeeae1ff8d8aee070a8e6c7852ebfd` → **`42d22a98d5d8cd54f73a1f480762fd6d`**.
5. scp'd to VPS (`/root/nous-agaas/wiki/.git/hooks/pre-commit`) + Air (`~/nous-agaas/wiki/.git/hooks/pre-commit`); 3-way MD5 parity verified.

**Live verification (session 43):**
- Test 1 — direct add `LESSON-131-direct-add-test.md` → BLOCKED ✅ (existing rule still works).
- Test 2 — stage off-canonical, then `git mv` to canonical (the EXACT bypass that let LESSON-080 through) → BLOCKED ✅ (the new rule catches it).

**Why we did NOT delete LESSON-080:** The lesson was created 2026-04-12 — BEFORE RULE ZERO existed (session-35 install was 2026-04-16 21:58). Today's rename was a legitimate slug normalization migrating a pre-RULE-ZERO file from a non-canonical path into the canonical path. The hook's design intent allowed migrations of HISTORICAL content. The bug wasn't in keeping LESSON-080; the bug was that the SAME mechanism could be abused to introduce FRESH lessons disguised as renames. The patch closes the abuse vector while honoring the historical migration.

**Verification contract:**
- `cd <wiki> && md5 -q .git/hooks/pre-commit` — hook extended session-68p with RULE 7 (agent-autonomy); MD5 transition `40fd8abb03354bb11482ee5d4be5921a` → `f6c873f84ee45f63b8222d68b5eb3318` on Mac, VPS, Air (3-way parity; vault canonical `tools/pre-commit-hook-tan-pattern.sh`). Full drift history in Timeline.
- `git diff --cached --name-status --diff-filter=R` of any commit involving LESSON file movement INTO `pages/lessons/individual/` from outside SHALL be REJECTED.
- Filesystem LESSON count vs gbrain `pages_by_type.lesson` MATCH per AP-10 pt 5 → if a future LESSON sneaks in via any path, this invariant catches it within 1 session.

**Long-term hardening (deferred):** add a CI check that runs `git ls-tree HEAD pages/lessons/individual/ | wc -l` against the previous tag's count — if the count grew, fail CI. This catches even `--no-verify` bypasses. Blocker: no CI yet on the wiki repo. Track separately.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline. The very file documenting this rule violation is, itself, the absorption of the rule violation — exactly the Tan/Karpathy/Finn architecture.

### AP-33 — TaskCompleted product-task detector over-triggers on generic action verbs; require DOMAIN-SPECIFIC anchors (session 45, 2026-04-17)

**Symptom (session 45 close-out):** Task `B3: Rotate APK_BOT_TOKEN via BotFather /revoke` was DEFERRED to a parallel session (operational security work, NOT product work). TaskCompleted hook BLOCKED closure with `LAW-006 GATE 1: missing REQ-xxx` + `LAW-011 GATE 2: missing business tag` — the product-task gates. But rotating a bot token is operational, not a VMS/ERAP/BDL feature.

**Root cause (5-whys):**
1. Why demand REQ-xxx on operational task? `IS_PRODUCT_TASK` was set to `true`.
2. Why? Line-52 product regex matched "deploy" in the task description ("they own the current secrets-management v1.1 deploy pipeline").
3. Why does "deploy" trigger product classification? The original regex (line 52 pre-fix) listed `implement|deploy|build|frontend|backend|camera|violation|ERAP|BDL|VMS|SmartBridge|ISAPI|cerebro|factory-work`. The first five are GENERIC action verbs; the rest are DOMAIN-SPECIFIC. Mixing them in one OR-chain gives action verbs the same trigger weight as domain anchors.
4. Why does session-40 AP-31 not cover this? AP-31 fixed the vault-task regex (line 56) by ADDING vocab. It didn't touch the product regex on line 52. Both regexes over-classify when the wrong word matches.
5. Why this matters: operational/security work (rotate, revoke, coordinate-with-parallel) is increasingly common and genuinely ISN'T product work. Every false-positive forces an agent to craft a fake REQ-xxx + [risk] tag to bypass — which corrupts the audit trail.

**Concrete fix applied 2026-04-17 (session 45):**
1. Stripped generic action verbs from product regex. Now requires domain specificity: `\b(VMS|ERAP|BDL|SmartBridge|ISAPI|cerebro|factory-work|police[_ -]?dashboard|violation|camera(s|[_ -](monitoring|event|registry|status|health))?)\b`.
2. Also extended vault-task regex with operational/security vocab: `rotate|token|revoke|keychain|credential|secrets?|coordinate|parallel|orchestrate|defer|carryover|close-audit|baseline|absorb|AP-[0-9]`.
3. Mac hook MD5 → **`8cc618d93a65fe51c24acd00e7539ce4`**; scp'd to Air; MD5 parity verified.
4. Live-tested: task #8 B3 (subject "Rotate APK_BOT_TOKEN via BotFather /revoke") now classifies as VAULT-only, passes.
5. Product gate still fires correctly on "Deploy new VMS camera feature" and "Implement violation alerting" — the domain words still anchor.

**Rule (amends AP-31):** Product-task classification MUST require a domain-specific word. Generic verbs (deploy, build, implement, frontend, backend) alone MUST NOT trigger product gates — they appear in operational vault work too often. The test: can the verb be used in a genuine operational sentence without any product intent? If yes, it is not sufficient evidence of product work.

**Verification contract:** `echo "Rotate token via BotFather /revoke" | bash task-completed-enforce.sh` should WARN-only (vault gates), NOT BLOCK (no product gates). Conversely `echo "Implement violation alerting for ERAP" | ...` should fire both gate 1 (REQ-xxx) and gate 2 (business tag). Both behaviors verified session 45.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-34 — Parallel Claude Code session detected via <2min commit cadence; defer destructive ops on shared resources (session 45, 2026-04-17)

**Symptom (session 45 Phase B):** Read git log on `apk-status-bot/`, saw HEAD `ea567ae` at 18:18:36. Re-probed 90 seconds later via `git ls-remote origin main`, HEAD was `1a1f071` (new commit). Probed again 84s later, HEAD was `3ee8a901` (another new commit). A parallel Claude Code session on the same Mac was actively executing T22-T33 of PLAN-APK-STATUS-BOT-A, pushing commits every ~1-2 minutes. Simultaneously the VPS clone had untracked files + was 2 commits behind.

**Why destructive actions were almost taken:** Session 44 MEMORY + handoff said "APK bot NOT LIVE (T23-T33 deferred)". Session-45's pre-planned workflow was "invoke subagent-driven-development on PLAN-APK-STATUS-BOT-A starting T22". If I had dispatched my own subagents while the parallel session was already executing T22-T33, we'd produce DIVERGENT COMMITS (race). The parallel session had already:
- Shipped T22 bot_polling.py (9cb5758)
- Shipped T24a systemd unit (ea567ae)
- Shipped T13c aggregator __main__ (3ee8a901)
- Installed systemd unit on VPS + started service (PID 1210153 at 18:20:39)
- Received real user input (madi_ayazbay 'Start' at 18:19:47)
- AP-26 contract flipped to YES/YES/YES WHILE I was still planning.

Also spotted: token leaked into journald 2× before `1a1f071` httpx-silence fix landed — parallel session already absorbed this as their AP-9 (commit message). BotFather /revoke rotation is in their workflow, not mine.

**Root cause (5-whys):**
1. Why didn't I detect the parallel session earlier? My first `git log` showed `ea567ae` at HEAD. I assumed that was the session-44-close state (which MEMORY said was `9c38d12`). I noticed the discrepancy only when re-probing.
2. Why did MEMORY say `9c38d12` if HEAD was `ea567ae`? Session 44 closed at `9c38d12`. The commits advancing HEAD happened AFTER session 44 close and BEFORE my session-45 open — during the window when I was reading the handoff. The parallel session started while I was still orienting.
3. Why was the parallel session invisible? No shared-lock. No status file. Only signal is git ls-remote + commit cadence. Two sibling Claude Code sessions on the same Mac, both advancing the same repo, with no coordination primitive.
4. Why didn't my session-44 MEMORY note flag this risk? Session 44 happened to be single-writer. Session 42 had a parallel addendum (secrets-management) which was coordinated AFTER-the-fact. Pattern is RE-OCCURRING but not yet rule'd.
5. Why is defer-vs-conflict the right call? Two agents writing to the same repo from different sessions WILL eventually produce a merge conflict or a divergent history. Conflict-prevention > conflict-resolution. The cheapest intervention is the one NOT taken.

**Rule:** At session open, AFTER reading the MEMORY/handoff chain and BEFORE dispatching subagents or executing any multi-commit workflow on a repo, run this cadence probe:
```bash
# On the target repo (example: apk-status-bot)
cd <repo> && git fetch origin main --quiet
COMMITS_LAST_5MIN=$(git log --since='5 minutes ago' origin/main --oneline 2>/dev/null | wc -l)
echo "Parallel-session probe: $COMMITS_LAST_5MIN commits in last 5 min on origin/main"
# >=2 commits in 5min => active parallel session => DEFER destructive/parallel work
```
If `COMMITS_LAST_5MIN >= 2`:
- DO NOT dispatch your own subagents (merge-conflict risk).
- DO NOT restart live services (disrupts their test).
- DO NOT rotate shared credentials (invalidates their active session).
- DO finish operational non-conflicting work (hook patches, CI guards on different files, skill absorptions).
- DO document the observed parallel work in your handoff so session N+1 can verify both threads reconciled.

**Verification contract:** every session-start workflow that will commit to a shared repo runs the cadence probe. If it returns `>=2`, explicitly state in the session plan: "Parallel session detected; scope limited to non-conflicting work X, Y, Z." 

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-35 — Pre-push sanity: live hook ↔ vault backup MD5 parity (compounding gate, session 45 addendum, 2026-04-17)

**Symptom (session 45 post-verification, Madi's "are you sure?" challenge):** First-pass close claimed "100% bulletproof." Re-audit caught 2 gaps: (GAP 1) `~/.claude/hooks/task-completed-enforce.sh` patched for AP-33 → MD5 `8cc618d9...`, but vault backup `tools/task-completed-enforce.sh` still at pre-patch MD5 `c2eff414...` for ~40 min. Session-40 AP-31 established the convention "also copy patched hook to vault tools/" but the convention lived only in doctrine — the next agent (me) didn't read session-40 AP-31 before patching, so the convention wasn't applied. (GAP 2 covered by AP-36 below.)

**Root cause (5-whys):**
1. Why did the vault backup go stale? I patched live hooks without the reflex "also cp to vault tools/."
2. Why no reflex? Session-40 AP-31 documented the convention in prose but not in code. Doctrine requires read + remember + apply; I missed the read.
3. Why does this class of gap keep recurring? Same mechanism as AP-31 (vocab-drift-across-sessions) — doctrine-only rules depend on future agent compliance.
4. Why is doctrine insufficient here? Because the convention has NO semantic dependency on context — a hook MD5 either matches or doesn't. That's purely mechanical. Mechanical checks should be coded, not written.
5. Why hadn't this been coded yet? Session 35's RULE-ZERO pre-commit was the pattern; session 43's AP-32 rename-bypass extended it; session 45's AP-32 CI guard added server-side enforcement. All on LESSON count, none on hook parity. The pattern is there; nobody walked it to hooks yet.

**Concrete fix applied 2026-04-17 (session 45 addendum):**
1. Wrote `tools/pre-push-sanity.sh` — runs on every `git push` from any vault working copy. For each `~/.claude/hooks/*.sh`, finds the matching `tools/<name>.sh` in the vault (if tracked) and compares MD5. Any divergence → push REJECTED with exact file paths + MD5 diff + 3 remediation options (sync vault from live, sync live from vault, or use `VAULT_PREPUSH_SKIP=1` escape hatch).
2. Wrote `tools/test_pre_push_sanity.sh` — 5 canned scenarios (in-sync, live-ahead-drift, vault-orphan, live-orphan, escape-hatch). All 5 pass.
3. Installed `.git/hooks/pre-push` (copy of `tools/pre-push-sanity.sh`) on Mac + VPS wiki + Air wiki. 3-wiki MD5 parity at **`2e34402d3c57b2d879aa24fb0c5ba189`** → extended session 73 AP-56 with CHECK B (.git/hooks/* parity) → **`b472ce964a64e3d2adafef9c6c60153a`**.
4. Live-tested REJECT path: appended a whitespace byte to live Mac `~/.claude/hooks/task-completed-enforce.sh` (MD5 → `b08078ae...`), attempted `git push vps main`, hook fired with exact expected message ("HOOK DRIFT DETECTED — push REJECTED"), git returned `error: failed to push some refs`.
5. Live-tested ACCEPT path: restored live hook from vault, re-pushed, auto-sync shipped the commit cleanly.

**Rule:** Every future hook patch MUST either (a) sync the vault backup in the same commit, or (b) `VAULT_PREPUSH_SKIP=1 git push` with rationale in commit message. The hook enforces this mechanically — the agent physically cannot push a vault working copy with diverged hook state.

**Verification contract:** `md5 -q <vault>/tools/pre-push-sanity.sh == md5 -q <wiki>/.git/hooks/pre-push` on all 3 wikis (Mac + VPS + Air). Plus `bash tools/test_pre_push_sanity.sh` exits 0 with "5 pass, 0 fail."

**Why this is the Tan/Karpathy pattern in full.** Skills (SKILL.md) compound KNOWLEDGE. Hooks compound ENFORCEMENT. Doctrine requires read + remember + apply — three compliance points where an agent can fail. Hook assertions require nothing of the agent — they fire automatically. Session 35 RULE-ZERO pre-commit (LESSON create), session 43 AP-32 rename-bypass (LESSON rename), session 45 AP-32 CI guard (LESSON push to bare), and now session-45-addendum AP-35 (hook parity on push) form the progression: every time a class of mistake is caught, it's ABSORBED AS CODE, not just as doctrine. The agent's future self is not trusted — the hook is.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-36 — Server hook functional test required (session 45 addendum, 2026-04-17)

**Symptom (session 45 post-verification GAP 2):** Installed VPS bare `hooks/pre-receive` (LESSON-count guard per AP-32). Claimed "syntax-verified + noop-tested" — which proves the script parses cleanly and handles empty stdin, but does NOT prove the REJECTION path fires when `NEW_COUNT > FROZEN_COUNT`. Under Madi's re-audit challenge, had to set up a contrived test (temporarily lowering `FROZEN_COUNT=128` to force rejection) to verify the actual behavior. The contrivance worked but should've been part of the install protocol, not a post-hoc scramble.

**Root cause:** "Verified" conflated three different rigor levels: (1) parse-safety, (2) happy-path output, (3) adversarial-path blocking. A hook that claims to REJECT must be tested against inputs that SHOULD be rejected.

**Rule:** Every new server-side hook MUST ship with a sibling `tools/test_<hookname>.sh` that exercises BOTH the ACCEPT and REJECT paths. The test script is committed alongside the hook. Example: `tools/pre-receive-lesson-count-guard.sh` ↔ `tools/test_pre_receive_lesson_count_guard.sh` (pending session 46). Until the sibling test exists, the hook is in "provisional" state.

**Concrete application:** `tools/pre-receive-lesson-count-guard.sh` was backed up to vault at session 45 addendum — but its test harness `tools/test_pre_receive_lesson_count_guard.sh` is NOT yet written. Flagged for session 46.

**Verification contract:** `ls tools/pre-receive* tools/test_pre_receive*` returns BOTH files. `bash tools/test_pre_receive_lesson_count_guard.sh` exits 0 with "N pass, 0 fail" covering reject + accept cases.

**Amends:** `evidence-verification` AP-1 (hedge language — "verified" hedge-expands into three rigor levels; specify which).

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### Brain-aware ops (gstack v0.18.0.0, 2026-04-17)

Before any service-level change (restart, port, path, host), `mcp__gbrain__search` with the service name + host — prior incidents on the same service may reveal a gotcha (TCC permissions, launchd env, Docker mount). After change, `mcp__gbrain__add_timeline_entry slug="pages/skills/infrastructure/skill"` with one-line "<service> on <host>: <change>, <outcome>". See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

### AP-37 — Design caps to sit under spec-named thresholds, not at them (session 46, 2026-04-18)

**Symptom:** GOD_PROMPT v1.0 Task 28 v2 cutover blocked at session-46 A/B probe: v2 median injected context = 12,427 bytes, G4 threshold = 8,192 bytes → FAIL. Session-27 deploy (2026-04-16) went live with `CONTEXT_INJECTOR_V2=1` for 1,495 telegram-poll runs before any A/B measurement ran.

**Root cause:** `MAX_CONTEXT_CHARS_V2 = 12_000` at `tools/context_injector_v2.py` line 35 — the design constant itself EXCEEDED the G4 bar. Raw context (catalog ~2 KB + 2 skill bodies × 4 KB each + 30-line HANDOFF ~1.5 KB ≈ 13,626 chars) clamped to 12,000 + wrapper bytes ≈ 12,427 bytes final. The cap was larger than the spec threshold; wrapper overhead (header 38B + trim-marker 28B + footer 20B + task text) added ~385 bytes beyond the raw cap.

**Rule:** Whenever a spec names an absolute output threshold (K bytes / N ms / % coverage / ≤ anything), every design constant that caps that output MUST be chosen ≤ threshold MINUS wrapper bytes MINUS expected task/tail-content bytes.

```
Cap(raw_content) + Wrapper(header+footer+trim_marker) + Appended(task_text) ≤ Spec_Threshold
```

Session-46 tune: `MAX_CONTEXT_CHARS_V2` 12_000 → 7_500 (≤ 8_192 G4 threshold − wrapper ≈ 390B − typical task); `MAX_SKILL_CHARS` 4_000 → 2_500 so 2 skills fit under the new cap.

**How to apply:** (a) When writing a spec, name the WRAPPER bytes explicitly so designers know what budget to target. (b) When writing the component, make the cap a constant and DO NOT set it ≥ the threshold even "temporarily" — pick conservatively and tune UP if unused headroom proves that safe. (c) At ship time, add an assertion in the implementation: `assert len(final_output.encode('utf-8')) <= SPEC_THRESHOLD_BYTES` on a representative input.

**Amends:** none (new AP). **Cross-ref:** `evidence-verification` AP-11 (A/B-probe-at-deploy-time) is the companion rule that would have surfaced this on deploy day rather than session-46.

### AP-38 — Feature-flagged cutover MUST ship with deploy-time A/B probe (session 46, 2026-04-18)

**Symptom:** Plan Task 19 Step 5 named the A/B harness (`context_injector_ab_probe.py`) but deployment of v2 in session 27 shipped the flag WITHOUT the harness. 1,495 telegram-poll runs flowed through v2 before any measurement. The Round-1 G4 FAIL only surfaced in session 46.

**Root cause:** "Ship the feature, write the probe later" slippage. Plan Task 27 was "A/B probe — 48h with real task traffic" — 48h elapsed, far more, but the probe didn't exist to process that traffic.

**Rule:** When a feature-flagged path is deployed, the same commit MUST include the A/B probe/harness that measures the flag's stated goal against real traffic. If the harness is non-trivial to build, make it a BLOCKING task before deploy — not a follow-up.

**How to apply:** Deploy PRs that add a feature flag but NOT its measurement harness are structurally incomplete. Convention: `feat: X + A/B harness` in same commit, OR deploy-gated-by-probe in plan.

**Absorption home partner:** `evidence-verification` AP-11 (same lesson, mirrored for that skill's lens). See also `agent-quality` AP-26 (MVP=running-service — "measured" is a different claim from "running").

### AP-39 — Proof-of-deadness 2-mode gate for delete-with-evidence (session 47 M2, 2026-04-18)

**Symptom:** Accumulated cruft — orphan launchd plists, `.bak-*` backup artifacts, unreferenced scripts on runtime hosts — silently erode auditability. Agents reasonably fear deleting anything because a silent dependency might break production. Result: cruft never gets deleted, AP-27 Air tools migration drags across 9 sessions, substrate gets slower to understand, onboarding gets worse.

**Root cause:** No mechanical gate for "prove this is safe to delete". Without a gate, each deletion decision gets re-debated per-file from scratch. With a gate, the decision is mechanical — run tests, pass all → delete with evidence trail.

**Rule (2-mode proof-of-deadness gate):** before deleting ANY file classified as DEAD-CANDIDATE or ORPHAN on a runtime host:

**Mode A — orphan backup artifact (e.g., `.bak-*`, `.pre-path-fix.*`, `.v1-archived-*`).** Run 4 tests:
1. **Vault code reference:** `grep -r "<exact-plist-label-or-filename>" pages/` — no active procedure references
2. **Runtime registry:** `ssh <host> "launchctl list | grep -i <name>"` on Air / `systemctl list-units | grep <name>` on VPS — not loaded
3. **Cron usage:** `crontab -l` on each user/host — no cron entry references it
4. **Wiki operational-doc reference:** grep `pages/` — matches are historical only (past install/unload in handoffs, archive notes in audits); NO current-operation procedure depends on it

All 4 PASS → safe to delete as an orphan (Mode A). Last-touch age not required because backup artifacts by definition are snapshots of what used to be live — age tells you nothing about whether current ops depend on them.

**Mode B — suspected dead-code script (e.g., an old `.py` or `.sh` in `tools/` that no agent or launchd has touched).** Run Mode A 4 tests PLUS:
5. **Last-touch age:** `git log --all --follow -- <path>` — file's last-touch > 60 days (or `stat -f %m` for untracked runtime scripts — > 60 days since last mtime).

All 5 PASS → safe to delete as dead code (Mode B). Age matters here because a recently-touched script is evidence someone still needs it.

**Per-deletion evidence trail (mandatory):** append an entry to the nearest `pages/audits/AUDIT-*.md` listing: target path, 4 or 5 test results, deletion command + exit code, post-deletion observation (≥5 min; launchd count + OpenClaw/LiteLLM health + launchd error log grep). No evidence trail → no delete.

**How to apply:** first execution 2026-04-18 session 47 M2 on `~/Library/LaunchAgents/com.nous.lesson-absorption.plist.bak-pre-path-fix` (744 B orphan dated 2026-04-16 11:25). Mode A (backup artifact, 2 days old but orphan-type). 4/4 PASS (0 plist-specific code refs; not loaded; no cron; 8+ historical doc mentions of the active unloaded sibling, no current-operation deps). Deleted; 5-min observation: launchd count unchanged at 17, 0 launchd-log errors mentioning lesson-absorption, openclaw + litellm healthy. Evidence in `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18` §5.

**Amends:** extends AP-27 (Air tools migration discipline) with a concrete delete-with-evidence mechanism. Applies to M6 OLD-BACKUPS batch (14× `.bak-pre-path-fix` plists — all eligible for Mode A batch application).

### AP-40 — Host-specific paths in `tools/` are legitimate (session 46-B, 2026-04-18)

**Symptom:** During session 46-B D2-DRIFT reconciliation, all 4 drifted scripts (`morning-brief.sh`, `wiki-to-runtime-rsync.sh`, `auto_checkpoint.py`, `telegram_poll.py`) had Air-authoritative versions containing hardcoded Mac paths: `/opt/homebrew/bin/python3`, `/Users/madia/nous-agaas/logs/...`, `/Users/madia/nous-agaas/wiki`. Vault versions had "portable" versions with bare `python3` + VPS paths (`/opt/nous-agaas/`, `/root/nous-agaas/`). The vault's "portability" looked prettier but was actually stale — the scripts have been running with Air-bound paths for weeks-to-months; vault was a lie.

**Root cause:** Instinct to "make code portable" or "use env vars" is often the wrong instinct for Air-targeted tools. Air is the designated host per CLAUDE.md architecture. Tools in `tools/` that run on Air via launchd are Air-targeted by definition; they don't need to work on VPS or Mac Pro. Abstracting paths = (a) adds indirection no caller uses, (b) introduces PATH-lookup-order fragility, (c) diverges vault from live runtime. The authoritative version is the one that runs, not the one that reads portably.

**Rule:** When a `tools/` script is designated for a specific host (Air, VPS, Mac Pro), the vault version MUST reflect the host-targeted paths exactly. Do NOT "portability-refactor" during sync unless there's a concrete multi-host runtime need. Document the target host in the script header comment: `# Runs on: Air (launchd com.nous.<label>)`. Audit AP-10 pt 2 MD5 parity check applies as-is — Air ↔ vault MD5 must match byte-for-byte, including the Mac-specific paths.

**How to apply during migration/sync:**
1. Identify the designated host (from plist location, launchctl label, or script header).
2. Sync the authoritative version byte-for-byte; don't refactor paths.
3. Add/update the `# Runs on: <host>` header if missing.
4. If true multi-host need emerges later (e.g., script needs to work on Air AND VPS), THAT is when you parameterize — as a deliberate refactor, not a silent portability-pass during a sync.

**Amends:** Nothing; new rule from cross-cutting D2-DRIFT observation. Cross-ref `audit` AP-10 pt 2 (skill MD5 parity) — now extended to tools. Cross-ref `audit` AP-14 (parallel session, deep audit beyond AP-10) — "probe every done claim" applies here: Air ↔ vault MD5 parity is itself the done claim to probe.

### AP-41 — Zero-duplicate rule for gbrain timeline entries on version-bump (session 46-B, 2026-04-18)

**Symptom:** Session 46-B A1 attempted to push gbrain timeline entries for `infrastructure` v2.31, v2.32, `evidence-verification` v1.6, `mistake-to-skill` v1.8 — believing them missing from gbrain (per stale session-45 MEMORY note). In fact, the parallel session-46 GOD_PROMPT thread had already pushed entries for v2.32 / v1.6 / v1.8 between 10:27–10:42 KZT. Session 46-B's pushes landed on top, creating duplicate entries with near-identical summaries (only the credit-metadata in `source` field differed). Net: 3 duplicate entries in gbrain timelines.

**Root cause:** "Push on behalf of another session for honesty" is a valid impulse, but without a pre-push check it creates noise. Duplicate timeline entries dilute search relevance + imply more work happened than did.

**Rule:** Before pushing a gbrain timeline entry attributed to another session's work, run `mcp__gbrain__get_timeline slug=<target>` and confirm the summary is NOT already present. Only push if (a) the other session didn't push for themselves AND (b) the missing entry is a real gap (e.g., MCP disconnect prevented it mid-session). Never push "credit my cross-thread work on their behalf" if they already recorded it.

**How to apply:**
1. Right before `add_timeline_entry` on another session's behalf, call `get_timeline` on the same slug.
2. Scan for the summary text (or key version string like `v2.32.0`).
3. If present: SKIP the push; document in handoff "entry already present, session X pushed it themselves."
4. If missing: push with explicit credit metadata in `source` field.

**Amends:** Nothing; new rule. Cross-ref `evidence-verification` AP-6 (probes MUST be read-only — this is the same family: the "probe" check comes before the "mutation" push).

### AP-43 — Pre-commit RULE 4: SKILL.md version parity gate (session 46, 2026-04-18)

**Symptom:** `mistake-to-skill` AP-11 (session 46 deep audit) codified the doctrine "SKILL.md version bumps require frontmatter + H1 + Timeline all three". Doctrine requires agent compliance — 3 failure points: read, remember, apply. Session 46 deep audit found 7 drifts accumulated silently across 3-5 sessions *after* the doctrine existed.

**Root cause:** Skills compound knowledge, hooks compound enforcement. Without a mechanical gate, AP-11 will be re-violated whenever an agent skims past H1 in a hurry. AP-35 set the precedent (pre-push parity on `~/.claude/hooks/*.sh`). AP-11 needed the same mechanical upgrade on the pre-commit side.

**Rule:** Pre-commit hook RULE 4 (session 46, 2026-04-18): if any `pages/skills/*/SKILL.md` is staged (added, modified, or renamed-in), run `tools/test_skill_version_parity.sh`. If exit 2 (drift found), reject the commit with the exact drift list + remediation instructions. Escape hatch: `git commit --no-verify` for emergency only.

**How to apply:** Installed at `.git/hooks/pre-commit` on Mac vault + Air wiki + VPS wiki + vault canonical `tools/pre-commit-hook-tan-pattern.sh`. Pre-push hook (AP-35) enforces live/vault MD5 parity; AP-44 scanner (session 47 RULE 5) verifies SKILL.md citations in this file keep pace with hook bumps. Session 46 live-tested: intentional H1 drift (v2.33 → v2.29) → commit REJECTED with exact AP-11 message + drift details; restore → commit ACCEPTED. (Current hook MD5 in Verification contract above.)

**Amends:** AP-35 sets the compounding-hook pattern; AP-43 applies it to the pre-commit tier for SKILL.md parity. Cross-ref `mistake-to-skill` AP-11 (doctrine) + `audit` AP-14 (deep audit that surfaced the accumulated rot).

### AP-44 — Pre-commit RULE 5: SKILL.md MD5 citation ↔ reality gate (session 47, 2026-04-18)

**Symptom:** SKILL.md prose cites file MD5s (hooks, `tools/*.sh`) to prove installation/parity. When the cited file drifts without the citation updating, the doctrine silently lies — future agents trust the cited MD5 and don't re-verify. Session 47 opening scan found 4 real drifts accumulated across sessions 40-46: 3× task-completed-enforce.sh (c2eff414 → bumped to 8cc618d9 via AP-32/33) + 1× pre-commit (42d22a98 → bumped to 9a99bdda via AP-43). The pre-existing AP-10 per-commit audit and AP-14 deep-audit did NOT catch these — MD5-citation drift is a 3rd axis of rot orthogonal to version parity (AP-43) and hook-file parity (AP-35).

**Root cause:** Citation-in-prose is a human-readable claim that requires manual upkeep. Whenever a hook file is bumped, SKILL.md prose citing its MD5 should also bump — but agents habitually update the hook + add a Timeline entry without grepping prior prose for the old MD5. Silent compounding rot.

**Rule:** Pre-commit hook RULE 5 (session 47, 2026-04-18): if any `pages/skills/*/SKILL.md` is staged (added, modified, or renamed-in), run `tools/test_skill_md5_citations.sh`. If exit 2 (drift found), reject the commit with drift list (file:line, cited hex, actual hex, resolved file path) + remediation. Scanner design:
- Finds 32-char hex tokens in prose
- Gates on "MD5" / "hook" / "hash" keyword within ±250-char window
- Skips citations in Timeline/History sections (append-only history by architecture)
- Skips citations in transition form `X → Y` (both sides historical)
- Skips citations whose file path is Air-only or non-vault (unverifiable from vault context)
- For verifiable citations: compute actual MD5, compare to cited. Mismatch → report.

**How to apply:** Installed at `.git/hooks/pre-commit` on Mac vault + Air wiki + VPS wiki (sibling of RULE 1-4; 3-way parity + vault canonical `tools/pre-commit-hook-tan-pattern.sh`). Test harness `tools/test_skill_md5_citations_self.sh` ships paired (AP-36): 5/5 PASS (CLEAN baseline + DRIFT reject + NO-CITATIONS vacuous + TRANSITION skip + AIR-ONLY-PATH skip). Session 47 first-execution surfaced 4 real drifts on infrastructure SKILL.md lines 701/708/742/959; fix strategy: transition-form for historical context (line 701), strip historical parenthetical for verification-contract lines (708, 742), Timeline-section skip absorbed the 959 case. Scanner runs in <1 second on 20 SKILL.md files.

**Amends:** AP-35 (pre-push hook-file parity) + AP-43 (pre-commit SKILL version parity) + AP-44 (pre-commit SKILL MD5-citation parity) form the 3rd Tan compounding gate in Karpathy sequence. Cross-ref `mistake-to-skill` AP-11 (doctrine for version parity) + `audit` AP-14 (deep audit cross-cut that this scanner operationalizes for MD5 axis).

### AP-45 — Pre-commit RULE 6: vault `*.env` file block (session 48, 2026-04-18)

**Symptom:** `.env` files staged into the vault can leak real secrets into git history; once committed, rotation is mandatory. Session 48 W1 manual audit missed 3 live 0644-mode `.env` files on runtime hosts that the W2 scanner caught (Air `/Users/madia/nous-agaas/litellm/.env` with `LITELLM_MASTER_KEY`; VPS `/root/nous-agaas/codebase/.env` + `.../satory-frontend/.env` with `GEMINI_API_KEY`).

**Root cause:** Without a commit-time gate, a `.env` with real values can be staged accidentally. Human audit missed 3 real drifts in the same session the scanner caught them.

**Rule:** Pre-commit hook RULE 6 (session 48, 2026-04-18): if any `*.env` file is staged (added, modified, or renamed-in), REJECT the commit. Exclusions: `.env.example`, `.env.template`, `.env.sample` (template forms with placeholder values only).

**How to apply:** Installed at `.git/hooks/pre-commit` on Mac vault + Air wiki + VPS wiki + `tools/pre-commit-hook-tan-pattern.sh`. Hook MD5 bumped `1f02002131ee5b3efa45e869cd21754b` → `40fd8abb03354bb11482ee5d4be5921a`. Live-tested REJECT + ACCEPT. Paired runtime gate: `secrets-management` v1.4 AP-11 — all runtime `*.env` MUST be 0600, scanned via `tools/test_secret_perms.sh` (+ self-test `tools/test_secret_perms_self.sh` 4/4 PASS). Full evidence in Timeline v2.37.0 → v2.38.0 entry. (This `### AP-45` bullet added session 48 Mac-interactive as cross-session corrective action — the v2.38 bump's Timeline described AP-45 but no matching `### AP-45` bullet existed in the Anti-Patterns section, violating `mistake-to-skill` AP-11 v1.9 4th check.)

**Amends:** Completes "skills compound knowledge, hooks compound enforcement" series for the secrets axis (7th compounding gate: AP-35 + AP-36 + AP-43 + AP-44 + pre-receive LESSON guard + TaskCompleted 9-gate + this). Cross-ref `secrets-management` AP-11 (runtime perms side).

### AP-47 — OpenClaw skillsSnapshot.version=0 freeze workaround + schema-completeness requirement (session 48, 2026-04-18)

**Symptom:** Factory runtime (`run_task.py` → OpenClaw) loads only a SUBSET of skills from `/opt/nous-agaas/skills/`, typically the skills present at session creation. New SKILL.md additions are silently invisible to the factory at `/ask` time. Session 48 W11 found 4/21 loaded (should be 21/21).

**Root cause:** OpenClaw 2026.4.14 has a mismatch between its chokidar file-watcher (configured via `skills.load.watch: true`) and its session-level snapshot-refresh gate. The snapshot gate is:
```js
shouldRefreshSnapshotForVersion(cachedVersion, nextVersion) {
  return next === 0 ? cached > 0 : cached < next;
}
```
With `cached = 0` (sessions.json initial) and `next = 0` (in-memory globalVersion never bumped by watcher), the result is always `false` → no refresh. Container restart also doesn't fix it (in-memory resets to 0; stored remains 0; `0 > 0` still false).

**Workaround:** Manually bump `sessions.json.skillsSnapshot.version` 0 → N+1 before the next task. Next `run_task.py` call hits `shouldRefreshSnapshotForVersion(N+1, 0)` → `next === 0 ? cached > 0 : ...` → `N+1 > 0` → TRUE → rebuild snapshot from live filesystem.

**Additional requirement surfaced:** OpenClaw's `loadSingleSkillDirectory` parses SKILL.md frontmatter and reads `frontmatter.name` + `frontmatter.description`. Skills with old schema (`id`+`title` but no `name`+`description`) are silently dropped even if the YAML is valid. Session 48 storage-retrieval was the 21st-skill holdout — added missing fields to close the gap.

**Tool:** `tools/bump_openclaw_skills_version.sh` — invoked from Mac; ssh's to Air + docker execs into openclaw container; backs up sessions.json → bumps version → triggers task → verifies new snapshot. Use after any SKILL.md add/rename that you want visible to factory.

**Upstream candidate:** file issue with OpenClaw (2026.4.14) — chokidar watcher should call `bumpSkillsSnapshotVersion` on new SKILL.md additions. Workaround hides the bug; upstream fix would eliminate the tool.

**Paired with:** AP-46 (YAML frontmatter validity). Together enforce: frontmatter (a) parses as YAML AND (b) contains `name`+`description` AND (c) triggers version bump when added → all three required for factory pickup. Pre-commit RULE 7 candidate: `test_skill_schema_completeness.sh` scanning for required `name`+`description` fields — prevents future silent drops at authoring time.

**Evidence trail:** W11 investigation (read-only), W12 surgical fix (version bump + storage-retrieval frontmatter add), W13 absorption (this AP). Factory 4/21 → 21/21 verified via `docker exec openclaw python3 -c` inspection of sessions.json after each bump. Workaround tool self-tested end-to-end (backup + bump + task + verify, exit 0). Cross-ref `mistake-to-skill` AP-12 (YAML-invalid → silent drop pattern; AP-47 extends to schema-incomplete drops).

### AP-46 — Pre-commit RULE 4 extension: SKILL.md YAML frontmatter validity gate (session 48, 2026-04-18)

**Symptom:** Session 48 Mac-interactive created new skill `session-operating-contract` v1.0.0. Pre-commit RULE 4 (AP-43 version-parity scanner) PASSED. 4-way HEAD parity confirmed at `b4413768`. Air runtime rsync landed the file. But `mcp__gbrain__get_page pages/skills/session-operating-contract/skill` returned `page_not_found` — gbrain never ingested the skill. Two `sync_brain` calls (incremental + `full: true`) both reported `{"status": "synced", "added": 0}` with no error surface. First in-place scan of the extended scanner (this AP) also surfaced a latent second-axis bug: `secrets-management` v1.4 had an unquoted colon inside its unquoted scalar `description:` value (`... AP-11 v1.4: every .env ...`), which YAML parses as a malformed nested mapping.

**Root cause:** Pre-commit RULE 4 invokes `tools/test_skill_version_parity.sh`, which uses **grep-based** comparison (frontmatter `^version:` ↔ H1 `^# <name> v`). It does NOT parse the YAML block. Every structural frontmatter bug class — malformed list values (`[[wikilink]], [[wikilink2]]`), unquoted colons inside unquoted strings, bad indentation, cyclic anchors, Obsidian body constructs inside YAML scalars — slips through the gate. Gbrain's ingester catches the `yaml.safe_load` exception silently and drops the page, preserving the "gbrain is always in sync" illusion without a real error surface. See `mistake-to-skill` AP-12 for the authoritative root-cause + fix doctrine.

**Rule:** Pre-commit RULE 4 is **extended in-place** (not replaced): the same scanner now also runs `yaml.safe_load` on every SKILL.md's frontmatter block (extracted via `awk '/^---$/{c++; next} c==1'`). Any `yaml.safe_load` exception → DRIFT with the actual parser error line/column + remediation pointer. No hook edit needed — scanner wires automatically through the existing RULE 4 invocation path.

**How to apply:** Dependency: `python3` + `PyYAML` (verified present Mac 6.0.3 / VPS 6.0.1 / Air 6.0.3 — all three hosts). Graceful fallback: if `python3` is absent, YAML check skipped with no error (version-parity still enforced). Live-tested POSITIVE (21/21 skills PASS after `secrets-management` inline fix) + NEGATIVE (`/tmp/sovptest-skill/SKILL.md` with `related: [[a]], [[b]]` → REJECT with parser error `"line 4, column 15: expected block end but found ','"` + AP-12 remediation pointer; scanner exit 2).

**Amends:** Extends AP-43 (version parity) with YAML-validity on the same RULE 4 path. Closes `mistake-to-skill` AP-12's "next-session compound gate candidate" — same AP-35 → AP-43 → AP-44 compounding pattern, applied to structural frontmatter integrity. Paired doctrine gate: `mistake-to-skill` AP-12 (authoritative root-cause + bare-identifier fix pattern). AP-48 (below) extends the same RULE 4 path with the 3rd structural check — Timeline↔AP-bullet parity.

### AP-48 — Pre-commit RULE 4 further extension: SKILL.md Timeline↔AP-bullet orphan detection (session 48, 2026-04-18)

**Symptom:** `mistake-to-skill` AP-11 v1.9 codified the 4th check of the version-bump ritual — every `"added/extended/absorbed AP-N"` claim in a Timeline entry MUST have a matching AP-N bullet somewhere in the same SKILL.md — as MANUAL-ONLY with the note "next-session candidate for mechanical enforcement." That candidate status lingered across sessions 46 round-2 → 47 → 48 W-thread → 48 Mac-interactive deep-audit, accumulating real orphans invisibly: (a) `infrastructure` v2.37 → v2.38 Timeline "absorbed **AP-45**" but no matching `### AP-45` bullet in Anti-Patterns (caught + patched earlier in session 48 Mac-interactive); (b) `secrets-management` v1.2 → v1.3 Timeline "added AP-10" but no matching `- **AP-10:**` bullet (caught + patched this round as v1.4 → v1.5). Pre-commit RULE 4 enforced AP-11 checks (1)–(3) via `test_skill_version_parity.sh` grep comparisons + AP-46 YAML-validity but never ran the orphan scan.

**Root cause:** Grep is the wrong tool for structural cross-reference. Timeline claims + AP bullets are free-form markdown with multiple valid shapes (`### AP-N`, `- **AP-N:**`, `- **AP-N —`, `**AP-N:**`). The manual-only note in AP-11 v1.9 placed the burden on the agent to run a cross-reference at every bump — agents habitually skip it, and Madi-triggered DEEP audits are the only reliable catch.

**Rule:** Pre-commit RULE 4 is **further extended in-place**: the same scanner now also scans every SKILL.md's `## Timeline` OR `## Evidence trail` section for `"added AP-N" / "extended AP-N" / "absorbed AP-N" / "absorbs AP-N" / "**AP-N**"` claims, and verifies each AP-N has a matching bullet anywhere in the file in one of the supported forms (`^### AP-N`, `^- **AP-N[:—\s]`, `^**AP-N[:—\s]`). Any orphan → DRIFT with filename + orphan AP numbers + detector pointer. No hook edit needed — wires automatically through existing RULE 4 invocation, alongside version parity (AP-43) + YAML validity (AP-46). All three structural-integrity invariants enforced on the same pre-commit gate.

- - - **2026-04-23** | v2.45.0 → v2.46.0 — Session 68p (Mac-interactive parallel, PID 68667, Madi directive *"hybrid version everywhere, physically impossible to bypass"*): **Absorbed AP-52** (commit-msg hook enforces SKILL↔gbrain-timeline pairing). Shipped `tools/test_skill_bump_requires_gbrain_timeline.sh` (4266B executable) + `.git/hooks/commit-msg` (895B executable) on 3-target parity (Mac vault + VPS wiki + Air wiki). Detector fails on version-bump commits without gbrain evidence token in message; accepts `gbrain-timeline-ok: <slug>` / `{status: ok}` / `gbrain entry id <NNN>` / `gbrain-timeline-deferred: <reason>` (CLI-fallback-down bypass). **Dogfooded same commit** (`bcb8a91a`): task-extraction v0.2.8 → v0.2.9 bump included `gbrain-timeline-ok:` token → detector fired on own commit → passed → pushed. Negative-case synthetic test (`/tmp/detect-test/SKILL.md`, no token): `🔴 BLOCKED` as expected. Closes hybrid-enforcement-gap Madi flagged — previously karpathy-loop 6-axis axis-2 was convention-only (honesty-enforced at session close); now physical (rejected at commit time). Paired doctrine compound: task-extraction v0.2.9 AP-10 (writer end-to-end validated first successful production run in 17+ days) + AP-9 env-bifurcation (session 68p earlier phase). Extension candidates queued session-69+: (a) new-wiki-page writes require gbrain `put_page` token, (b) cross-reference `[[wikilinks]]` require gbrain `add_link` token, (c) pre-push sibling `test_pushed_commits_have_gbrain_evidence.sh` (defense-in-depth vs `--no-verify` bypass). 9th compounding mechanical gate after AP-35 pre-push MD5, AP-36 sibling-test, AP-43 RULE 4 SKILL parity, AP-44 RULE 5 MD5 citation, AP-45 RULE 6 .env block, AP-48 RULE 4 Timeline↔AP-bullet parity, pre-receive LESSON guard, TaskCompleted 9-gate classifier. "Skills compound knowledge, hooks compound enforcement" series now extends to hybrid-layer pairing — Karpathy wiki + OpenBrain-style gbrain physically coupled at git-commit boundary. No new LESSON (RULE ZERO).

**2026-04-23** | v2.45.0 → v2.46.0 — Session 68p (Mac-interactive parallel, PID 68667, Madi directive *"hybrid version everywhere, physically impossible to bypass"*): **Absorbed AP-52** (commit-msg hook enforces SKILL↔gbrain-timeline pairing). Shipped `tools/test_skill_bump_requires_gbrain_timeline.sh` (4266B executable) + `.git/hooks/commit-msg` (895B executable) on 3-target parity (Mac vault + VPS wiki + Air wiki). Detector fails on version-bump commits without gbrain evidence token in message; accepts `gbrain-timeline-ok: <slug>` / `{status: ok}` / `gbrain entry id <NNN>` / `gbrain-timeline-deferred: <reason>` (CLI-fallback-down bypass). **Dogfooded same commit** (`bcb8a91a`): task-extraction v0.2.8 → v0.2.9 bump included `gbrain-timeline-ok:` token → detector fired on own commit → passed → pushed. Negative-case synthetic test (`/tmp/detect-test/SKILL.md`, no token): `🔴 BLOCKED` as expected. Closes hybrid-enforcement-gap Madi flagged — previously karpathy-loop 6-axis axis-2 was convention-only (honesty-enforced at session close); now physical (rejected at commit time). Paired doctrine compound: task-extraction v0.2.9 AP-10 (writer end-to-end validated first successful production run in 17+ days) + AP-9 env-bifurcation (session 68p earlier phase). Extension candidates queued session-69+: (a) new-wiki-page writes require gbrain `put_page` token, (b) cross-reference `[[wikilinks]]` require gbrain `add_link` token, (c) pre-push sibling `test_pushed_commits_have_gbrain_evidence.sh` (defense-in-depth vs `--no-verify` bypass). 9th compounding mechanical gate after AP-35 pre-push MD5, AP-36 sibling-test, AP-43 RULE 4 SKILL parity, AP-44 RULE 5 MD5 citation, AP-45 RULE 6 .env block, AP-48 RULE 4 Timeline↔AP-bullet parity, pre-receive LESSON guard, TaskCompleted 9-gate classifier. "Skills compound knowledge, hooks compound enforcement" series now extends to hybrid-layer pairing — Karpathy wiki + OpenBrain-style gbrain physically coupled at git-commit boundary. No new LESSON (RULE ZERO).

**2026-04-23** | v2.45.0 → v2.46.0 — Session 68p (Mac-interactive parallel, PID 68667, Madi directive *"hybrid version everywhere, physically impossible to bypass"*): **Absorbed AP-52** (commit-msg hook enforces SKILL↔gbrain-timeline pairing). Shipped `tools/test_skill_bump_requires_gbrain_timeline.sh` (4266B executable) + `.git/hooks/commit-msg` (895B executable) on 3-target parity (Mac vault + VPS wiki + Air wiki). Detector fails on version-bump commits without gbrain evidence token in message; accepts `gbrain-timeline-ok: <slug>` / `{status: ok}` / `gbrain entry id <NNN>` / `gbrain-timeline-deferred: <reason>` (CLI-fallback-down bypass). **Dogfooded same commit** (`bcb8a91a`): task-extraction v0.2.8 → v0.2.9 bump included `gbrain-timeline-ok:` token → detector fired on own commit → passed → pushed. Negative-case synthetic test (`/tmp/detect-test/SKILL.md`, no token): `🔴 BLOCKED` as expected. Closes hybrid-enforcement-gap Madi flagged — previously karpathy-loop 6-axis axis-2 was convention-only (honesty-enforced at session close); now physical (rejected at commit time). Paired doctrine compound: task-extraction v0.2.9 AP-10 (writer end-to-end validated first successful production run in 17+ days) + AP-9 env-bifurcation (session 68p earlier phase). Extension candidates queued session-69+: (a) new-wiki-page writes require gbrain `put_page` token, (b) cross-reference `[[wikilinks]]` require gbrain `add_link` token, (c) pre-push sibling `test_pushed_commits_have_gbrain_evidence.sh` (defense-in-depth vs `--no-verify` bypass). 9th compounding mechanical gate after AP-35 pre-push MD5, AP-36 sibling-test, AP-43 RULE 4 SKILL parity, AP-44 RULE 5 MD5 citation, AP-45 RULE 6 .env block, AP-48 RULE 4 Timeline↔AP-bullet parity, pre-receive LESSON guard, TaskCompleted 9-gate classifier. "Skills compound knowledge, hooks compound enforcement" series now extends to hybrid-layer pairing — Karpathy wiki + OpenBrain-style gbrain physically coupled at git-commit boundary. No new LESSON (RULE ZERO).

**How to apply:** Dependency: `python3` (no external libraries — pure re + glob). Graceful fallback: if `python3` is absent, orphan check skipped (version + YAML checks independently enforced). Live-tested: POSITIVE 21/21 skills clean after the 2 orphans were patched (AP-45 infrastructure + AP-10 secrets-management); NEGATIVE — a fabricated `/tmp/orph-test/SKILL.md` whose Timeline contained a synthetic high-number AP claim with no matching bullet returned scanner exit 2 with a DRIFT line naming the orphan AP number. Detection regexes handle `\*\*AP-N\*\*`, absorption verbs (added / extended / absorbed / absorbs) + AP-N (case-insensitive) for CLAIMS; `### AP-N`, `- **AP-N:**`, `**AP-N:**`, em-dash variants for EXISTING bullets.

**Amends:** Closes `mistake-to-skill` AP-11 v1.9's "next-session compound gate candidate" status — 4th check now mechanical, same AP-43 (version parity) + AP-46 (YAML validity) + AP-48 (Timeline↔AP parity) chain on pre-commit RULE 4. Paired doctrine update: `mistake-to-skill` v1.10 → v1.11 marks AP-11 v1.9's 4th check as mechanical (text update, same session). Cross-ref `audit` AP-14 (deep-audit that surfaced the 2 accumulated orphans this session) + `audit` AP-15 (self-compliance meta-pattern — the same "rule codified mid-session but not applied to same-session edits" that AP-15 describes, now mechanically closed for the AP-bullet sub-class).

### AP-50 — Shipped-artifact path coupling: audit all consumers when renaming an output file (session 56-ext, 2026-04-21)

**Symptom:** A pipeline produces an output file at path P1. Monitors (health probes), consumers (rotation scripts), regression tests, analytics — all hardcode P1 somewhere. The pipeline ships a Phase-N+1 change that renames the output to P2 (valid reason: interface change, iface split, per-entity partitioning). The output is now at P2; the old P1 still exists as an empty stub. **Every hardcoded consumer silently continues checking P1 — reports green indefinitely** even though the real state is invisible to them. Worst case: the rotation consumer rotates the stub P1 hourly (empty archives) while P2 grows unbounded until disk fills weeks later.

**Root cause:** Path coupling without rename-audit discipline. Each consumer was written at a time P1 was canonical; nobody re-audited when P1 → P2. The coupling is invisible in code reviews because there's no cross-script reference (each hardcodes independently). Bash doesn't have type-safe paths or compile-time reference checks, so the drift is detected only by (a) noticing the "green" probes while the stream dies, or (b) a disk-fill alert much later.

**Evidence — session 56 ext, 2026-04-21:** Phase-0 collector shipped writing `/home/nous-admin/collector/pcap/collector.pcap` (over `-i tailscale0`). Phase-1 cut-over flipped to `-i wg0` writing `wg0-collector.pcap` — the container spec changed cleanly, but the 24-byte stub of the old name remained. Three consumers silently broke:
1. `tools/nous_gpu_collector_health.sh` — health probe hardcoded `PCAP=/home/nous-admin/collector/pcap/collector.pcap` (line 27). Reported `OK pcap=24 delta=+0` for ~90 minutes of real traffic flowing into a file it wasn't watching.
2. `tools/test_nous_gpu_collector_tzsp.sh` — regression probe hardcoded `PCAP_INSIDE=/pcap/collector.pcap` default + 2 stat calls on the legacy host path. Auto-detect existed in sibling script but not this one.
3. `/usr/local/bin/nous-collector-rotate.sh` — host-side systemd-timer rotation targeted `LIVE_PCAP=${PCAP_DIR}/collector.pcap`. Would have compressed a 24-byte stub hourly while wg0-collector.pcap grew unbounded — at ~230 KB/s = ~40-day horizon before /home filled on a 1 TB disk.

All three found by grep-based 3-host audit (Mac vault + Air + Nous-GPU host scripts). Fixed with two complementary patterns:

**Pattern A — `docker inspect` for container-bound paths:**
```bash
LIVE_PATH=$(docker inspect -f '{{range .Config.Cmd}}{{.}} {{end}}' "${CONTAINER}" \
  | grep -oE '\-w[ ]+[^ ]+' | awk '{print $2}')
```
Authoritative — reads the actual `-w` arg. Falls back to pattern B when container is down or cmd is empty.

**Pattern B — `find -mmin` for file-system-of-truth:**
```bash
LATEST=$(find "${OUT_DIR}" -maxdepth 1 -name '*.pcap' -type f -mmin -${WINDOW} \
  -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
```
Works regardless of container state. Returns empty if no file has been written within the window → health probe fails loudly instead of silently-OK.

**Rule — at every output-path change (artifact rename, interface split, per-entity partitioning), before merging:**

1. **Grep every host for the old path string** (vault tools/, Air tools/, Nous-GPU /usr/local/bin/ + /etc/systemd/ + home). Three-host coverage, one `grep -rn` pass.
2. **Classify each hit:** archive/historical/comment (OK) vs. live-consumer (🔴 FIX).
3. **Fix live-consumers** via Pattern A (container-authoritative) or B (file-system-of-truth). NEVER hardcode another path.
4. **Add a delta-based alarm** to the primary health probe. "File exists" and "file was statable" are not healthy — "file grew by ≥ N bytes in the last probe interval" is. State-track the `(path, size)` tuple so rotations reset cleanly.
5. **Dogfood the fix under live traffic** — not just unit-probe. An auto-detect regex can pass unit-probes and still fail on production shape.

**Mechanical detector (candidate, session-57+):** `tools/test_no_hardcoded_pcap_paths.sh` — greps vault + tools dirs for any hardcoded path matching `*/collector/pcap/*.pcap` that isn't inside a comment, doc, or history-trail section. Fails CI if any live code hardcodes. Batched with other detector scripts (`test_sequencing_value_first.sh` + `test_no_tactical_permission_questions.sh` + `test_no_execution_gate_questions.sh`).

**Cross-ref:** `mistake-to-skill` AP-11 (3-edit ritual used to codify this AP); `audit` AP-20 (probe-E2E-verify — this AP's dogfood-under-live-traffic rule extends AP-20 from "run the probe" to "run the probe WHILE production-state is representative"); `session-operating-contract` Rule 16 + AP-10 (same failure class at the version-metadata layer — each is "narrative claim ran ahead of substrate reality"); `camera-management` AP-19 (preserve-ingestion-contract sibling at the data-layer). No new LESSON (RULE ZERO).

### AP-49 — Vault-substrate-mirror discipline: Mac-canonical files must reach Air-reachable locations mechanically (session 54, 2026-04-20)

**Symptom:** Two same-class findings surfaced in session-54 Phase-1 audit, both of the form "Mac has the right version but the Air-reachable copy is stale because no mechanical sync exists for THAT substrate class":

1. **Probe B — Mac-root session-shim ↔ vault drift.** Session-51 HARD RULE 1 narrowing (Telegram-MCP ban), session-52 Nous-GPU row, session-53 Telegram routing model all landed in `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` ONLY. Air-side OpenClaw factory + `/code`-spawned CLI substrate-read the vault, not Mac-root → three sessions' worth of operational rules invisible to Air-side agents. Fixed session-54 by extracting to `pages/systems/architecture-quickref.md` with reciprocal pointers (`B3` + `B3b` commits). Session-76 extended this class to Codex: `/Users/madia/Documents/Projects/Nous AGaaS/AGENTS.md` is the Codex session-shim and must also point to the same vault mirror.
2. **Probe E1 — Air live hook `task-completed-enforce.sh` stale.** Session-51 shipped `IS_INFRASTRUCTURE_TASK` override in vault `tools/task-completed-enforce.sh` (MD5 `99ea6f87…`). Mac's `~/.claude/hooks/` got the new version via Mac's skill-layer rsync. Air's `~/.claude/hooks/` DID NOT — it kept the Apr-17 version (MD5 `8cc618d9…`) missing the infra-class override. For 2+ days any `/code`-spawned Claude Code CLI on Air ran with the OLD hook, blocking infrastructure tasks on product-class gates. Discovered session-54 when Air's pre-push hook rejected push with `HOOK DRIFT DETECTED` — the system's own mechanical gate caught what every SOAO in between missed (SOAO checks hook parity between vault and Mac-live; does NOT check Air-live).

**Root cause:** Two different substrate classes (Mac-root `CLAUDE.md` for session-start instructions; `~/.claude/hooks/*.sh` for runtime gates) both lack a mechanical "canonical → Air-reachable" sync. The skill-layer has `wiki-to-runtime-rsync.sh` (AP-37) and the Mac-side has `~/.claude/hooks/` watched by the user's own workflow; neither covers (a) Mac-root project-CLAUDE files (which live OUTSIDE any vault, so wiki-to-runtime doesn't see them) or (b) Air's `~/.claude/hooks/` (which lives on the Air M2, reachable only via `ssh air`). The "vault = single source of truth" law holds for vault-tracked files; session-54 surfaced two vault-adjacent classes that fell outside that guarantee.

**Rule:** For every persistent runtime-substrate file class, there MUST be a mechanical "canonical → every runtime copy" sync OR a mechanical "is this drifted?" gate in SOAO / a sibling probe. Classes identified this session:

| Class | Canonical | Runtime copies | Current sync | Session-55+ gate |
|---|---|---|---|---|
| Vault SKILL.md + tools/*.sh | VPS bare | Mac vault, Air wiki, VPS wiki, Air `~/nous-agaas/skills/` (via rsync) | Auto-sync cron bidi + AP-37 rsync | ✅ AP-35 pre-push + AP-43/44/46/48 RULE 4/5 |
| Mac `~/.claude/hooks/*.sh` | Vault `tools/*.sh` | Mac `~/.claude/hooks/`, Air `~/.claude/hooks/` | Manual (Mac); none (Air) | 🔴 `test_air_live_hook_parity.sh` — new sibling probe |
| Mac-root CLAUDE.md / AGENTS.md operational content | Vault `pages/systems/architecture-quickref.md` | Mac-root files + vault substrate | Manual | ✅ `test_claude_md_parity.sh` checks both session shims |
| Air `/Users/madia/nous-agaas/tools/*.sh` | Vault `tools/*.sh` | Air tools dir | AP-37 rsync | ✅ Covered |

**How to apply:**
1. When adding a new persistent runtime-substrate file, classify it into the table above. If it doesn't fit an existing class, add a new row with explicit sync mechanism.
2. Session-54 session-55+ deliverables: build `tools/test_air_live_hook_parity.sh` (md5 per hook file, ssh to Air, compare to vault) + `tools/test_claude_md_parity.sh` (verify Mac-root CLAUDE.md and AGENTS.md point to `pages/systems/architecture-quickref.md` when the Mac project root is locally mounted; on Air/VPS, skip unavailable Mac-root shim files but still require the vault quickref reciprocal pointer). Wire both into SOAO section 3 (structural scanners).
3. Until mechanical gates land: session-start checklist item "run `md5sum ~/.claude/hooks/*.sh` on Mac + Air, compare to vault `tools/*.sh`" — manual discipline, replaces-itself-with-mechanical on session 55.

**Amends:** Extends AP-35 (pre-push parity for Mac-side hooks) with Air-side coverage; extends AP-37 (wiki-to-runtime-rsync) with `~/.claude/hooks/` (currently only covers `~/nous-agaas/tools/`). Related to `audit` AP-20 (probe E2E-verify — same "gate silently wrong because incomplete coverage" failure mode). No new LESSON (RULE ZERO).

### AP-51 — Auto-sync user-commit-race guard: skip if `.git/index` mtime <15s OR `.git/index.lock` present (session 60, 2026-04-22)

**What happened:** Session 59 had 3 commits with carefully-written HEREDOC messages rewritten by `com.nous.obsidian-sync` (every-60s launchd) as generic `"auto-sync YYYY-MM-DD HH:MM:SS"`. Content was preserved in the diff; authorial intent + session attribution + semantic commit message were lost. Root cause: `/Users/madia/.local/bin/nous-obsidian-sync.sh` calls `git status --porcelain` → `git add -A` → `git commit -m "auto-sync $(timestamp)"` without checking if a user-initiated commit is in flight. Race window: user `git add file.md` (index updated, lock released) → [user tool call for commit-message-build] → user `git commit -m "..."`. If the every-60s launchd fires inside that window, it grabs the staged file + any other unstaged-but-modified files via `git add -A` and commits them under its own generic message — the user's subsequent `git commit` then says "nothing to commit, working tree clean."

**Two occurrences satisfy recurrence-gate:** session-59 auto-sync ate commits for (1) `tools/soao.sh` session-59 Phase-2 dynamic-count fix, (2) `pages/tenants/satory/skills/task-extraction/SKILL.md` v0.2.1 bump with AP-1-validation framing + ritual. Both session-59 single-session. AP justified without waiting for session-61 occurrence.

**Fix (SHIPPED session 60, `/Users/madia/.local/bin/nous-obsidian-sync.sh`):** 0-th sync_vault step added BEFORE the `status --porcelain` check:

```bash
if [ -f "$vault/.git/index.lock" ]; then
    log_line "$label skip: .git/index.lock present (user git operation in progress)"
    return 0
fi
if [ -f "$vault/.git/index" ]; then
    INDEX_MTIME=$(stat -f %m "$vault/.git/index")
    NOW_EPOCH=$(date +%s)
    INDEX_AGE=$(( NOW_EPOCH - INDEX_MTIME ))
    if [ "$INDEX_AGE" -lt 15 ]; then
        log_line "$label skip: .git/index modified ${INDEX_AGE}s ago (user likely mid-commit)"
        return 0
    fi
fi
```

Why 15s: `git add` + `git commit` sequence takes <5s typical; 15s is generous enough for the Edit→review→commit loop while short enough that user-abandoned stages flush on the next 60s cycle. `.git/index.lock` is the atomic lock git takes during any index-mutating operation — checking it catches mid-`commit` in addition to the post-`add`-pre-`commit` window.

**Rule (for future launchd + cron authors):**
1. Any automated process that does `git add -A && git commit` on a user-facing vault MUST include this user-mid-commit guard. Non-negotiable.
2. Same pattern applies to `git stash`, `git reset --hard`, any index-mutating automation.
3. Generic solution: launchd jobs that mutate user state must check for recent user activity on the same state (15-30s mtime window or equivalent lock file). Skip the cycle; user's work propagates on the next tick.
4. Test before shipping: `touch $vault/.git/index && bash $(which your-sync-script)` — must log "skip" not "OK: <commit>".

**Compounding gate candidates (session 61+):**
(a) `tools/test_auto_sync_user_commit_guard.sh` — scans all launchd ProgramArguments for scripts that do `git add -A`, ensures each includes an `.git/index` mtime check. Regression guard against this fix being reverted.
(b) Consider extending to Air's sync analogues (if any exist that touch `~/nous-agaas/wiki/.git/` during user work; investigate session 61).
(c) Pre-push hook could also verify commit messages don't match the `auto-sync YYYY-MM-DD HH:MM:SS` regex when author is a real person (but only if this pattern recurs post-fix — deferred).

**Cross-ref:** `session-operating-contract` new Rule 18 (no-defer-on-textbook-bug, session 60 — race conditions are textbook). `audit` AP-21 (pagination textbook — same session-60 codification, same discipline: known-class failure → immediate AP). `mistake-to-skill` AP-11 (3-edit ritual — applied here: frontmatter + H1 + Timeline + this AP bullet). No new LESSON (RULE ZERO).

### AP-52 — Commit-msg hook physically enforces SKILL↔gbrain-timeline pairing (Nate B. Jones hybrid layer, session 68p, 2026-04-23)

**Pattern:** The Tan/Karpathy RULE ZERO enforced "no new LESSON files" physically via pre-commit hook (RULE 1a/1b). The symmetric pattern — "every SKILL bump MUST have matching gbrain timeline push" — was a convention-only rule in `karpathy-loop` axis-2 of the 6-axis scorecard, enforced by session-close honesty (AP-4 write-negative-first), NOT by the git layer. Convention decays. Sessions ship SKILL bumps → forget gbrain timeline → search-evidence chain breaks → future agents can't root-cause via gbrain → hybrid (wiki + OpenBrain-style DB) degrades into wiki-only (flat, unscalable — the exact failure mode Madi flagged in session-68p as "Karpathy thing is not scalable; doesn't store well enough").

**Root cause (Madi session-68p 2026-04-23):** *"We need to have this hybrid version everywhere! It has to be like physically impossible to bypass it."* Mirrors musk-algorithm AP-3 (physically-impossible-violated): any doctrine rule without a mechanical enforcement artifact IS at risk of being drifted past. RULE ZERO is physical; skill↔gbrain-pairing was not.

**Rules:**

1. **Every commit that bumps a `SKILL.md` frontmatter `version:` field MUST include gbrain timeline evidence in the commit message.** Accepted tokens (any one):
   - `gbrain-timeline-ok: <slug-or-skill-name>`
   - `gbrain entry id <NNN>` (from `mcp__gbrain__add_timeline_entry` return)
   - `gbrain timeline {status: ok}` (verbatim status line)
   - `{status: ok}` or `{"status": "ok"}` (bare response)
   - `gbrain-timeline-deferred: <reason>` — explicit bypass for MCP-down + CLI-fallback-down

2. **Enforcement mechanism:** `.git/hooks/commit-msg` invokes `tools/test_skill_bump_requires_gbrain_timeline.sh` which:
   - detects SKILL.md version changes via `git diff --cached`
   - reads commit message from `$1` (hook-provided path)
   - regex-match any accepted token → pass
   - no token → reject with instructions + CLI fallback command

3. **3-target parity:** Mac vault + VPS wiki + Air wiki — same pattern as AP-43 RULE 4 (pre-commit SKILL parity) + AP-44 RULE 5 (MD5 citations) + AP-45 RULE 6 (.env block). Bypass = `git commit --no-verify` (operator-owned risk).

4. **Dogfooded this-session:** the commit that shipped this AP + detector + hook also bumped `task-extraction` v0.2.8 → v0.2.9 and included `gbrain-timeline-ok: pages/tenants/satory/skills/task-extraction/skill` token → detector fired on own commit → passed → pushed. Self-enforcing from first commit forward.

**Evidence:** `tools/test_skill_bump_requires_gbrain_timeline.sh` (4266 bytes, executable Mac + VPS + Air). `.git/hooks/commit-msg` (895 bytes, executable Mac + VPS + Air). Detector negative-case (synthetic `/tmp/detect-test/SKILL.md` with version bump, no token): `🔴 BLOCKED`. Detector positive-case (own commit `bcb8a91a` with token): accepted + pushed.

**Why this closes the hybrid-enforcement gap Madi flagged:**

- Karpathy wiki layer = `SKILL.md` (flat-file, read-at-runtime doctrine) — already physically enforced by AP-11 3-edit ritual + AP-43 parity.
- OpenBrain-style DB layer = gbrain (structured, graph + vector, searchable) — timeline push was convention-only until this AP.
- **Both must land for a compound to survive; either alone decays.** This AP makes the pairing mechanical — the git commit itself won't complete without evidence of BOTH layers touched.

**Compounding extension candidates (session 69+):**

(a) Extend to new wiki page writes: any commit that adds a new `pages/**/` file with YAML frontmatter `id:` must cite gbrain `put_page` evidence. Currently no enforcement — flat-wiki growth can outpace gbrain indexing.

(b) Extend to entity cross-references: any commit that adds a `[[wikilink]]` to a new target must have a matching gbrain `add_link` push (same-class as skill↔timeline pairing, applied to graph edges).

(c) Pre-push hook sibling: `test_pushed_commits_have_gbrain_evidence.sh` scans range being pushed for any SKILL bump without token; catches `--no-verify` bypass at remote-delivery boundary. Defense in depth.

**Cross-ref:** `karpathy-loop` 6-axis scorecard axis-2 (gbrain push) — was honest-convention, now physical; `musk-algorithm` AP-3 (physically-impossible-violated pattern); `gbrain-ops` AP-33 (MCP disconnect → CLI fallback) — detector explicitly accepts fallback via `gbrain-timeline-deferred:` token when both paths fail; `mistake-to-skill` AP-11 3-edit ritual — this AP's own codification dogfooded the ritual (frontmatter v2.45 → v2.46 + H1 implied + Timeline + AP-52 bullet, same commit that ships the detector). No new LESSON (RULE ZERO).

### AP-53 — Hybrid-coverage gap closure: rsync scope extension + periphery Telegram gate (session 68p/70, 2026-04-23)

**Two gaps named in session-68p honest self-audit that session 70 closed this turn (musk-algorithm Step 1-2-3 applied):**

**Gap A — wiki-to-runtime-rsync scope missed `pages/tenants/*/skills/`:**
- Session 47 M5 added `tools/` sync to the rsync script, but tenant-skill trees at `pages/tenants/<tenant>/skills/` were never in scope. Factory agents (extractor.py, writer.py, learner.py) read from `~/nous-agaas/tenants/<tenant>/skills/` — silent drift possible whenever tenant doctrine bumps on Mac/VPS without manual per-tenant rsync. Hit session-68p when task-extraction v0.2.7 → v0.2.9 bumps on Mac didn't reach Air runtime until manual rsync.
- **Fix:** extended `tools/wiki-to-runtime-rsync.sh` with a per-tenant glob-loop (`for tenant_wiki_skills in "$WIKI_TENANTS_DIR"/*/skills/; do ...`) discovering tenants dynamically. Never `--delete`. Excludes `_gbrain/` + `extracted/` same as top-level skill sync. Script size 4564B → 6513B.
- **Also:** narrowed the `tools/` exclusion from `test_*.sh` → `test_*_self.sh` — production detectors like `test_agent_autonomy.sh` / `test_musk_step_2.sh` / `test_skill_bump_requires_gbrain_timeline.sh` are CALLED BY hooks and tg_send at runtime, so they MUST sync. Only self-test harnesses (`*_self.sh`) stay excluded as dev-only.
- **Live-tested (2026-04-23 18:10 KZT):** `bash ~/nous-agaas/tools/wiki-to-runtime-rsync.sh` ran clean, output `OK: tenant/satory/skills/ sync complete`, runtime `grep "^version:" ~/nous-agaas/tenants/satory/skills/task-extraction/SKILL.md` → `0.2.9` ✅.
- **3-target deployed:** Mac + VPS wiki + Air wiki + Air runtime; 4-way MD5 `2329eaa7aa8f6b71b1be657bc87b694c` GOLDEN.

**Gap B — periphery Python sendMessage paths bypassed the AP-4 gate:**
- Session-68p shipped `command_center.py._tg_send` subprocess gate calling `test_agent_autonomy.sh --stdin`. BUT `auto_checkpoint.py._telegram_notify` + `tools/auto_checkpoint.py._telegram_notify` + `factory_health.py.send_telegram` had their own direct `urllib.request` calls bypassing the gate. First AST-sed attempt in session-68p produced syntax errors (bad `return False if "return" in "" else None` expression, insertion at inside-try without enclosing function boundary) → rolled back to backups.
- **Fix (session 70):** Python AST-aware patcher using regex on `^def <name>(...)[return_type]:` signature line + first-body-indent detection; inserts 12-line gate block at function start with `return None` for `-> None` functions and `return False` for `-> bool` functions. Backup files at `<name>.pre-ap4-gate-s70`.
- **Live-tested:** `_telegram_notify("your call on this, whenever ready")` → `[auto_checkpoint] AP-4 BLOCKED: 'your call on this, whenever ready'` + `returned: None` ✅; clean text passed gate, hit Telegram API (expected fail on invalid token).
- **Bypass:** `AUTONOMY_BYPASS=1 env var` (same escape as `tg_send.sh`).
- **All 3 files syntax-clean via `python3 -c "import ast; ast.parse(...)"`**.

**Rule:** any new Python outbound path to Telegram (`api.telegram.org`) MUST either (a) import centralized wrapper OR (b) include the 12-line AP-4 gate block at function start. Queued detector session-71+: `tools/test_telegram_api_direct_callers.sh` — grep `api.telegram.org/bot` across `~/nous-agaas/**/*.py`, verify each caller function has either `AUTONOMY_BYPASS` check or `test_agent_autonomy.sh` subprocess reference.

**Cross-ref:** musk-algorithm AP-4 (agent-autonomy loop doctrine — this AP extends the enforcement surface from 1 Python hot path to 4 Python paths: `command_center._tg_send` + `auto_checkpoint._telegram_notify` (2 copies) + `factory_health.send_telegram`); AP-37 M5 (rsync tools/ extension precedent); AP-49 (Vault-substrate-mirror discipline — same meta-class: substrate class falls outside existing sync, fix via mechanical gate). No new LESSON (RULE ZERO).

### AP-54 — Auto-sync attribution-drift detector (SOC Rule 19 class, session 70+, 2026-04-24)

**Pattern:** Substantive agent work (SKILL.md bumps, HANDOFF/MEMORY prepends, tools/ edits, .git/hooks/ changes) should land as AUTHORIAL commits with explicit HEREDOC messages per SOC v1.12 Rule 19. In practice, `com.nous.obsidian-sync` (every-60s launchd) or `vps auto-sync` / `air-sync` cron repeatedly grabs staged-but-not-committed agent work before the agent's explicit `git commit`, rewriting attribution to generic `auto-sync YYYY-MM-DD HH:MM:SS`. Content lands in bare repo, but authorship + rationale are LOST. Across session-59 + session-66 + session-67 + session-68p + session-70 — 5 sessions of recurrence (SOC Rule 18 occurrence-gate cleared long ago).

**Root cause (named in session-60 AP-51):** race between user-agent `git add` → `git commit` and auto-sync's `git add -A && git commit`. Session-60 shipped `.git/index.lock` + `mtime <15s` guard. Session-63 widened to 30s + working-tree-file mtime check. Both reduce but don't eliminate the race — multi-tool-call Edit sequences spanning >30s still get caught.

**Evidence (THIS session — session-70):** `1cd9198e air-sync 2026-04-23T18:11:00` grabbed my authorial `tools/wiki-to-runtime-rsync.sh` scope-extension before I could commit explicitly. `62ccbea5 vps auto-sync 2026-04-23 18:11:01` is the VPS mirror of same file. Detector below catches both.

**Rule:**

1. **Agents commit own substantive work IMMEDIATELY after Edit / Write.** Don't accumulate into session-close batches. Per musk-algorithm AP-4, the commit IS part of execution, not post-work hygiene.
2. **Use `git commit -o <paths>`** for tight-scope atomic commits that beat the auto-sync window.
3. **When session-close batch is unavoidable:** stage + commit in the SAME tool-call turn (not separate turns), minimizing the exposed-staged-state duration.
4. **Post-facto check:** run `tools/test_authorial_commits.sh` at SOAO / session-open to surface drift from last N commits as INHERITED CONTEXT (not as fix — git history immutable).

**Detector (SHIPPED session 70 this AP):** `tools/test_authorial_commits.sh`
- Scans last N commits (default 50, configurable via `LOOKBACK=` or `SINCE=` env vars).
- For each commit with subject matching `^(auto-sync |vps auto-sync |air-sync |Merge branch)`, checks if diff touched AUTHORIAL_CLASS files: `pages/skills/**/SKILL.md`, `pages/tenants/**/skills/**/SKILL.md`, `pages/progress/HANDOFF-*.md`, `pages/progress/claude-memory/MEMORY.md`, `pages/progress/PLAN-*.md`, `^tools/*.{sh,py}`, `.git/hooks/`.
- Prints drift report with offending commits + file paths. Exit 0 if clean, 1 if drift.
- **Not a hard commit block** — git history is immutable; rewriting is more destructive than the drift itself. This is SURVEILLANCE / post-audit, compatible with SOAO audit pattern.
- Dogfooded: ran against session-70 history, caught `1cd9198e` (air-sync) + `62ccbea5` (vps auto-sync mirror) on the rsync-script extension commit.
- 4-target MD5 parity `bf8d02e878044cffbaad64b91df87229` (Mac vault + VPS wiki + Air wiki + Air runtime).

**Integration candidates (session-71+, compounding):**
(a) Append to SOAO (session-open audit output) so next agent sees drift ratio as INHERITED CONTEXT for whether to use tight-scope `-o` commits.
(b) Nightly launchd job posts Telegram when daily drift ratio exceeds threshold (e.g. 20% of authorial-class commits → generic).
(c) Pre-push hook sibling: warn (not block) if outgoing range contains >3 drift commits.

**Cross-ref:** SOC v1.12 Rule 19 (authorial-commit doctrine); AP-51 (auto-sync race guard, 15s→30s — this AP adds a post-facto surveillance detector on top of the race-window guard); musk-algorithm AP-4 (agent-autonomy — commit is execution, not hygiene); karpathy-loop AP-4 (write-negative-first — this AP's body names every recurrence honestly rather than claiming race was fully fixed). No new LESSON (RULE ZERO).

### AP-55 — `.git/hooks/pre-commit` canon-deployed drift: live hook patches MUST write back to `tools/pre-commit-hook-tan-pattern.sh` in same commit (session 72, 2026-04-24)

**Symptom:** Session-72 SOAO hook section RED: deployed `.git/hooks/pre-commit` MD5 `f6c873f8` disagreed with canon `tools/pre-commit-hook-tan-pattern.sh` MD5 `40fd8abb`. All 3 hosts' deployed hooks agreed with each other (Mac + Air + VPS-wiki all `f6c873f8`). Canon alone was stale — 2026-04-18 mtime vs deployed 2026-04-23 mtime. Diff revealed the deployed hook has a newer `RULE 7 — agent-autonomy` block invoking `tools/test_agent_autonomy.sh`, shipped session 68p (musk-algorithm AP-4 hybrid-enforcement chain); canon was never updated in that session.

**Root cause:** Git doesn't version-control `.git/hooks/`. The canon file `tools/pre-commit-hook-tan-pattern.sh` IS version-controlled, but relies on manual `cp` to/from the deployed hook. When session 68p patched `.git/hooks/pre-commit` directly to add RULE 7, it installed the fix on 3 hosts (Mac, Air, VPS) but didn't `cp` back to canon + commit. SOAO's parity check (`pre-commit canon vs Mac/Air/VPS`) catches drift post-facto but doesn't prevent it. AP-35 covers `~/.claude/hooks/*` ↔ `tools/*` — a DIFFERENT hook class than `.git/hooks/*` ↔ `tools/pre-commit-hook-tan-pattern.sh`, so AP-35's pre-push sanity didn't fire.

**Rule:**

1. **Any edit to `.git/hooks/pre-commit` on ANY host MUST be mirrored to `tools/pre-commit-hook-tan-pattern.sh` + committed in the same turn** (SOC v1.12 Rule 19 authorial-commit pattern).
2. **Fix sequence:** patch deployed hook → test → `cp .git/hooks/pre-commit tools/pre-commit-hook-tan-pattern.sh` → `git commit -o tools/pre-commit-hook-tan-pattern.sh -m "hook canon sync"` → deploy to other hosts.
3. **Detection (SHIPPED):** SOAO Section 3 already prints `pre-commit canon:` MD5 vs `pre-commit Mac/Air/VPS:` MD5 — drift surfaces RED at next SOAO. Session-72 this fire.
4. **Compounding gate candidate (queued session-73+):** extend AP-35's `tools/test_pre_push_hook_parity.sh` to also check `.git/hooks/pre-commit` MD5 against canon. Would have blocked session-68p's un-mirrored patch at push time.

**Evidence (this session, 2026-04-24):** SOAO at 12:29:04 KZT surfaced the drift after s68p's 5 days. Diff showed canon missing 13 lines (RULE 7 block + `REPO_ROOT` helper + test_agent_autonomy.sh exec branch). Fix: `cp .git/hooks/pre-commit tools/pre-commit-hook-tan-pattern.sh` on Mac → MD5 converges to `f6c873f8` across 4 targets. Counter-check: re-run `md5sum tools/pre-commit-hook-tan-pattern.sh .git/hooks/pre-commit` → identical.

**Cross-ref:** AP-35 (pre-push sanity for `~/.claude/hooks/`) — sibling doctrine; this AP extends the pattern to `.git/hooks/*`. AP-52 (commit-msg hook enforces SKILL↔gbrain-timeline pairing, session 68p) — same session as the un-mirrored patch, proves mechanical enforcement matters most on the exact boundary that gets skipped. SOC v1.12 Rule 19 (authorial-commit doctrine) — the mirror-back commit IS part of the authorial chain, not post-work hygiene. musk-algorithm AP-4 (agent-autonomy — commit is execution). No new LESSON (RULE ZERO).

### AP-56 — `.git/hooks/*` ↔ `tools/*-hook-canonical` MD5 parity enforced at `git push` (session 73, 2026-04-24)

**Symptom (the gap AP-55 left open):** AP-55 (session 72) codified the DOCTRINE — any `.git/hooks/*` patch must write back to its `tools/*.sh` canonical + commit. It did NOT install a mechanical gate. A future agent who patches `.git/hooks/pre-commit` without writing back would silently re-open the same 5-day-drift window that surfaced via SOAO only. AP-55 body explicitly flagged this as "compounding gate candidate queued session-73+."

**Root cause:** AP-35 (session 45) shipped `tools/pre-push-sanity.sh` checking `~/.claude/hooks/*.sh` ↔ `tools/*.sh` parity, but that check class does NOT cover `.git/hooks/*` (different hook directory, different canonical-file names). So the pre-push gate that enforces the `~/.claude/hooks/` class let `.git/hooks/` drift through.

**Rule:**

1. `tools/pre-push-sanity.sh` extended with CHECK B: explicit mapping table from `.git/hooks/<name>` to `tools/<canonical>.sh`:
   - `pre-commit` ↔ `tools/pre-commit-hook-tan-pattern.sh`
   - `commit-msg` ↔ `tools/commit-msg-hook.sh` (new canonical, shipped session 73)
   - `pre-push` ↔ `tools/pre-push-sanity.sh`
2. On every `git push` from a vault working copy, MD5 drift between deployed and canonical on any mapped hook → push REJECTED with explicit "which-direction-to-fix" remediation (B-canon-stale vs B-deployed-stale).
3. Escape hatch preserved: `VAULT_PREPUSH_SKIP=1 git push` bypasses both CHECK A and B (documented-in-commit-msg requirement).
4. Adding a new `.git/hooks/<name>` to enforce requires (a) create canonical at `tools/<canonical>.sh`, (b) add row to `GIT_HOOK_MAP` array in `tools/pre-push-sanity.sh`, (c) document in AP-56 body. Missing step (c) hits AP-43 (RULE 4 version-parity scanner) when the next skill bump lands → physically impossible to silently extend enforcement without updating this AP.

**Evidence (this session, 2026-04-24 s1404):**

- Mapping verified at start: all 3 hooks' deployed MD5s match their canonical twins (pre-commit `f6c873f8`, commit-msg `b379505e` new this session, pre-push `2e34402d` → `b472ce96` after this extension).
- Positive test: clean-state `bash tools/pre-push-sanity.sh` → exit 0.
- Negative test: synthetic 1-byte drift on `.git/hooks/pre-commit` (append `# synthetic drift`) → `pre-push-sanity.sh` exit 1 with CHECK B banner + exact deployed/canon MD5 diff + 4-option fix remediation.
- Restore + re-run → exit 0; final MD5 back to `f6c873f8`.
- Canonical MD5 after extension: `tools/pre-push-sanity.sh` = `b472ce96`; `.git/hooks/pre-push` (local deployed) = same.
- 4-target (Mac vault + Air wiki + VPS wiki + Air runtime via auto-sync) parity push in same authorial commit.

**Cross-ref:** AP-35 (pre-push sanity for `~/.claude/hooks/` — the sibling gate this AP extends to `.git/hooks/*`). AP-55 (canon-deployed drift DOCTRINE — this AP is the MECHANICAL enforcement AP-55 queued). AP-43 (pre-commit RULE 4 SKILL version parity — its `GIT_HOOK_MAP` expansion gate is tied to this AP's bullet presence here). SOC v1.12 Rule 19 (authorial-commit doctrine — the skill-bump + detector-deploy commit is itself authorial, not auto-sync-batched). 10th compounding mechanical gate after AP-35 / AP-36 / AP-43 / AP-44 / AP-45 / AP-48 / AP-52 / pre-receive / TaskCompleted / AP-55. No new LESSON (RULE ZERO).

### AP-57 — `raw/presentations/node_modules/` and `pages/progress/claude-memory/*` are protected paths; never `rm` from any agent (session 73, 2026-04-25)

**Symptom:** During s73-mac-44586's audit-only continuation, `git status` repeatedly surfaced 142 → 2607 → 3674 deletions. 37 of those were memory topic files in `pages/progress/claude-memory/` (`MEMORY-ARCHITECTURE.md`, `MEMORY-archive-sessions1-22.md`, all `feedback_*.md`, all `user_*.md`) — wiped at 16:41:52 KZT, 35 min after session-73's main close commit `758a0db5`. The remaining 2640+ were `raw/presentations/node_modules/` files that had been tracked in git despite being build-artifact dependency code.

**Root cause:** Two latent class-failures, both surfaced same session:

1. **Substrate-protect class (memory):** `pages/progress/claude-memory/` is the symlink target for the auto-memory system (`~/.claude/projects/.../memory` → vault path, per LAW-005). 4 Opus-4.6 computer-use agents were running on Mac with `--allow-dangerously-skip-permissions + bypassPermissions` (PIDs 8552, 32542, 68818, 71598, started Fri 1PM-Thu 2PM, all 8h+ runtime). Without a substrate-protect rule, any of them could `rm` memory topic files as part of generic "cleanup" without realizing the path is the active memory store. Forensic at `~/Library/Application Support/Claude/local-agent-mode-sessions/` returned no recent jsonls (last mod Jan-15) → standard transcript path is non-authoritative or silenced; the agent that did the rm cannot be PID-attributed without process-level audit instrumentation.

2. **node_modules tracking class:** `raw/presentations/node_modules/` (~4572 files) was committed during initial slide-rendering setup. `.gitignore` had `*.env` and similar but NO rule for `raw/presentations/node_modules/`. Each session that ran `npm install` or similar partially mutated the tree → `git status` showed hundreds of `D` entries → LAW-005 GATE 5 in `~/.claude/hooks/task-completed-enforce.sh` blocked every TaskUpdate→completed call until "fixed" via `git add -A && git commit`, which would have over-scoped the session's authorial commit.

**Rule:**

1. **`raw/presentations/node_modules/` is now `.gitignore`d + untracked from git index** (this session's commits `8a037991` + follow-up). Files remain on disk but git no longer sees them. Future `npm install` mutations are invisible to GATE 5.
2. **`pages/progress/claude-memory/` is a PROTECTED PATH.** Never `rm`, `git rm`, archive-script-prune, or "cleanup-script" any file under it without explicit Madi consent in the same session. The dir's `MEMORY.md` is the live AMD-006 top-block-prepend target; sibling files (`feedback_*.md`, `user_*.md`, `MEMORY-ARCHITECTURE.md`, `MEMORY-archive-sessions*.md`) are the topic-memory store referenced by LAW-005 and the auto-memory system prompt.
3. **Recovery is git-only:** if the dir gets wiped by a misbehaving agent, `git checkout HEAD -- pages/progress/claude-memory/` restores from the last committed state; do NOT regenerate by re-prompting the auto-memory system, that loses prior content.
4. **Future compounding gate (queued session-74+):** add `tools/test_protected_paths_intact.sh` — a SOAO-section probe that fails 🔴 if `pages/progress/claude-memory/` count < 30 OR if any computer-use agent process has been observed `rm`ing under it (process-audit hook on `rm`/`unlink` syscalls). Until then, the pre-commit hook's RULE 4 family does NOT cover this class — protection is procedural, not mechanical. Honest gap.

**Evidence (this session, 2026-04-25 s73-mac-44586):**

- Disk-level wipe detected: `ls pages/progress/claude-memory/` returned 1 file (only `MEMORY.md`) at audit time vs 38 in HEAD; mod time `16:41:52` post-close.
- Restore: `git checkout HEAD -- pages/progress/claude-memory/` → 38 files back, working tree clean.
- node_modules untrack: `git rm -r --cached raw/presentations/node_modules/` staged 2640 D entries; `git ls-tree -r HEAD raw/presentations/node_modules/ | wc -l` → 0 post-commit; files still on disk per `--cached` semantic.
- Counter-check: `git status` post-commit shows zero `D` entries for `raw/presentations/`; GATE 5 no longer blocks on this path.
- Telegram broadcast preserved cross-session: msg_id=1022 to chat 110793056 with full incident summary (s74 picks up forensic + mechanical-gate work).

**Cross-ref:** LAW-005 (memory symlink integrity — this AP is the substrate-protect extension). LAW-015 (root-cause discipline — naming the wrong-rm-class is the root cause, not the wipe itself). musk-algorithm AP-4 (agent-autonomy-loop — but bounded: agents do NOT have autonomy over substrate-protected paths). SOC v1.12 Rule 7 hard-banned (extended class — substrate-destruction in dangerously-skip-permissions mode). karpathy-coding-principles principle 3 (surgical changes — generic "cleanup" agents must not touch paths whose function is non-obvious from name). 11th compounding rule (procedural this turn; mechanical gate session-74+). No new LESSON (RULE ZERO).

### AP-58 — Live tunnel health probes must classify no-data vs collector/filter drift (session 75, 2026-04-26)

**Symptom:** `com.nous.nous-gpu-collector-health` failed every 5 minutes with the vague reason `no pcap written in last 15 min under /home/nous-admin/collector/pcap`. Prior AP-50 had already removed the hardcoded pcap-path bug, so this message no longer told the operator whether the GPU was dead, the container was wrong, the collector filter drifted, or Denis-side traffic stopped.

**Root cause:** The probe watched only the pcap artifact, not the upstream tunnel counters. Live audit on 2026-04-26 showed the GPU reachable, `nous-collector` running on `-i wg0`, `wg0` handshaking with Denis's peer every few seconds, but WireGuard receive bytes stayed flat over a 20-second observation window and `tcpdump -i wg0` saw zero packets. Last non-empty archive was the 2026-04-24 04:00Z rotation; the live `wg0-collector.pcap` stayed a 24-byte header from 2026-04-24 09:00 Almaty onward. That is upstream-data-stop, not a local collector/container crash.

**Rule:**

1. Any live-tunnel pcap health probe must gather at least two layers of evidence: artifact movement (`pcap` mtime/size/delta) and transport movement (WireGuard latest-handshake age + RX/TX byte deltas, or equivalent tunnel counters).
2. If handshake is fresh and RX delta is zero or keepalive-scale only (currently `<1024B` per 5-min probe), alert as **upstream mirror likely stopped**. Do not ask the operator to restart Docker first; Docker is not the constraint.
3. If handshake is fresh and RX delta is payload-scale (currently `>=1024B`) while pcap delta is zero, alert as **collector filter/path drift**. Then audit interface, BPF filter, output path, rotation, and consumer auto-detection.
4. If handshake is stale, alert as **tunnel down/stale**, then work the WireGuard peer/endpoint path.
5. The alert text must include the measured counters, not only the conclusion, so the next agent can start from evidence instead of re-running the same ambiguous pcap check.

**Evidence (this session, 2026-04-26):**

- `tailscale status` on Air showed `100.70.222.21 nous-gpu... active`; SSH to `nous-gpu` succeeded.
- `docker ps` showed `nous-collector` running `tcpdump -i wg0 -n -U -w /pcap/wg0-collector.pcap udp port 37008`; `nous-wg` was up.
- `docker exec nous-wg wg show wg0` showed latest handshake age under 10s but transfer RX unchanged over a 20s probe; TX moved only by keepalive-scale bytes.
- `timeout 12 docker exec nous-collector tcpdump -i wg0 -nn -c 25` captured zero packets; `udp port 37008` also captured zero.
- Patched `tools/nous_gpu_collector_health.sh` to persist WG RX/TX counters and append `wg_handshake_age`, `wg_rx_delta`, `wg_tx_delta`, and a verdict to failures. Verification: second run emitted `wg_handshake_age=6s wg_rx_delta=0B wg_tx_delta=0B; wg alive, no incoming payload since last probe; upstream mirror likely stopped`. Follow-up self-audit caught keepalive-scale RX (`184B`) being misclassified as payload, so the detector now requires payload-scale RX (`>=1024B`) before naming collector/filter drift.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-71 — Pcap truncation/rotation is a baseline reset, not a mirror failure (2026-04-29)

**Symptom:** The daily substrate probe intermittently marked Nous-GPU RED with `pcap wg0-collector.pcap delta=+-... B` while the same log showed multi-GB pcap growth before and after the failure. WireGuard RX deltas were payload-scale, so the old alert text incorrectly suggested collector filter/path drift.

**Root cause:** `tools/nous_gpu_collector_health.sh` reset delta only when the pcap path changed. The collector writes to the same `wg0-collector.pcap` path and can truncate/recreate it during container restart or rotation; same path + smaller size produced a negative delta and false failure.

**Rule:**

1. If the latest pcap path changes, reset the growth baseline.
2. If the latest pcap path is the same but `curr_size < last_size`, also reset the growth baseline and report `truncated/rotated`.
3. Enforce the normal `MIN_DELTA_BYTES` growth alarm on the next probe after the reset.
4. Do not classify same-path truncation as upstream stop or collector/filter drift unless the following probe also fails to grow.

**Verification:** `bash -n tools/nous_gpu_collector_health.sh`; `bash tools/test_nous_gpu_collector_health_rotation.sh` exits 0 and proves same-path `curr_size < last_size` resets baseline instead of alerting.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-72 — Docker disk pressure recurs at <24h cadence; manual prune is not idempotent (session 85, 2026-04-29)

**Symptom:** AUDIT-057 (2026-04-28) recovered Air `/System/Volumes/Data` from 13 GiB free / 97% to 43 GiB free / 91% by running `docker builder prune -af` + `docker image prune -f`. Within ~24 hours, the same volume was back to 25 GiB free / 95% before any deploy event. Re-running the same prune commands recovered only ~3.3 GiB (28 GiB free / 94%), not the 9 GiB+ that `docker system df` reported as `Reclaimable`.

**Root cause (two compounding):**

1. **Manual prune is not idempotent on a live OpenClaw host.** OpenClaw container churn (image swaps, model fetches, build steps) regenerates dangling layers and build cache continuously. AP-67's "run prune when disk goes red" guidance treats the symptom — the regeneration cadence is shorter than operator response cadence, so disk hits red again before any human re-acts.
2. **`Reclaimable` in `docker system df` is misleading.** It counts tagged-but-unused images (e.g., older `ghcr.io/openclaw/openclaw:2026.3.28` once `2026.4.14` is the live tag) that `docker image prune` will NOT remove because they are not dangling. Recovering that space requires explicit `docker rmi <image-id>` after verifying the running container's image, OR `docker image prune -a` (note `-a` flag) which removes any image not referenced by a running container.

**Rule:**

1. Treat AP-67 as a one-time recovery only. The recurring fix is a scheduled job, not an operator action.
2. Add a daily Docker prune to launchd on Air (proposed `com.nous.docker-prune-daily`, 03:30 Almaty, before morning-brief at 04:00) running `docker builder prune -af -f && docker image prune -f`. State-file the recovered byte count; alert only on Δ-failure (no recovery despite running).
3. Tagged-image audit is a SEPARATE weekly job: list `docker images`, identify any image not referenced by `docker ps --format '{{.Image}}'`, log to `~/nous-agaas/state/docker-stale-images-YYYY-WW.log`, and require operator approval before `rmi` (because misidentifying a paused-but-needed image causes a re-pull cost).
4. Probe `df -h /System/Volumes/Data` after each prune cycle; if free space < 30 GiB, escalate to AP-72-state-change Telegram alert (not noise — only on threshold cross).
5. Honest framing in any alert: "Docker prune recovered Xmb of dangling layers; YGB still in tagged-but-unused images requires manual review" — do not claim full reclaim of `Reclaimable` figure.

**Verification (this session):**

```text
ssh air 'df -h /System/Volumes/Data'  # before: 25Gi free / 95%
ssh air 'docker builder prune -af && docker image prune -f'  # 643MB + 1 image
ssh air 'df -h /System/Volumes/Data'  # after: 28Gi free / 94%
```

**Open / queued for next session:**

- Implement `com.nous.docker-prune-daily` launchd plist + state-file probe script.
- Implement weekly tagged-image audit job.
- Decide whether `docker image prune -a` (auto-removes any non-referenced tagged image) is safe for Air given OpenClaw image-pin discipline.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-59 — Generic auto-sync must refuse authorial-class paths (session 75, 2026-04-26)

**Symptom:** During the Codex self-audit close, auto-sync repeatedly committed authorial-class edits under generic subjects:

- `f7507c2e auto-sync 2026-04-26 18:25:27` and `4e08f426 air-sync 2026-04-26T18:28:17` grabbed `tools/nous_gpu_collector_health.sh`.
- `99ee2eec auto-sync 2026-04-26 19:12:02` grabbed this session's sync-script patch itself before the detector + AP could land authorially.

The existing AP-51/AP-54 mitigations reduced the race but did not make the forbidden outcome physically impossible. A 30s mtime guard cannot cover multi-tool reasoning/edit/test cycles that naturally exceed 30s.

**Root cause:** The auto-sync writers were still authorized to do `git add -A && git commit` on every dirty path. Timing guards are heuristic; the real invariant is path class. Skills, plans, audits, handoffs, laws, tenant source, and tool scripts are authorial substrate. They must never be committed under `auto-sync`, `air-sync`, or `vps auto-sync`, regardless of timing.

**Rule:**

1. Every generic auto-sync writer must compute an `authorial_dirty` path before `git add -A`.
2. If any dirty path is authorial-class, the sync cycle must log and exit before commit, pull, merge, or push.
3. Authorial-class paths currently include:
   - `pages/skills/*/SKILL.md`
   - `pages/tenants/*/skills/*/SKILL.md`
   - `tenants/*`
   - `pages/audits/*.md`
   - `pages/plans/*.md`
   - `pages/progress/HANDOFF-*.md`
   - `pages/progress/claude-memory/MEMORY.md`
   - `laws/*.md`
   - `tools/*.sh`, `tools/*.py`, `tools/*.plist`
   - `AGENTS.md`, `CLAUDE.md`
4. Non-authorial churn such as `.obsidian/workspace.json` may still auto-sync after authorial work is clean.
5. Detector `tools/test_auto_sync_authorial_guard.sh` must stay green on Mac, Air, and VPS sync writers before claiming the guard is present.

**Implementation (this session, 2026-04-26):**

- Patched `tools/nous-obsidian-sync.sh` (Mac vault sync; runtime deployed to `~/.local/bin/nous-obsidian-sync.sh` on Mac + Air).
- Patched `tools/wiki-sync-launch.sh` (Air `com.nous.wiki-sync`; runtime deployed to `~/nous-agaas/tools/wiki-sync-launch.sh`).
- Patched `tools/wiki_to_bare.sh` (VPS cron; runtime deployed to `/root/nous-agaas/tools/wiki_to_bare.sh` + vault copy).
- Added `tools/test_auto_sync_authorial_guard.sh`.

**Evidence:** With untracked `tools/test_auto_sync_authorial_guard.sh` present, `bash ~/.local/bin/nous-obsidian-sync.sh` logged `nous skip: authorial-class dirty path (tools/test_auto_sync_authorial_guard.sh) — waiting for explicit authorial commit` and did not create another generic auto-sync commit. Static regression test also blocks the Air script from running `git pull` inside the authorial-dirty skip block.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-60 — Restart proof must respect Docker healthcheck interval (session 76, 2026-04-27)

**Symptom:** During the Telegram/OpenClaw 24/7 reliability audit, `docker restart openclaw` brought the container back, port `18789` opened, and OpenClaw's internal `/healthz` endpoint returned HTTP 200, but `docker inspect openclaw` still reported `health=starting` after a 120-second wait. A naive audit would have marked OpenClaw restart recovery red even though the service was usable and the healthcheck had not reached its next scheduled pass.

**Root cause:** The OpenClaw image healthcheck interval is `180s` with a `15s` start period and `10s` timeout:

```text
node -e "fetch('http://127.0.0.1:18789/healthz').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
```

The first post-restart Docker healthcheck ran too early and failed/timed out while OpenClaw was still starting. Docker did not mark the container healthy until the next scheduled healthcheck at roughly 180 seconds. Manual probes during the `starting` window showed:

```text
curl http://127.0.0.1:18789/healthz -> {"ok":true,"status":"live"}
run_task.py ... "Reply exactly: OPENCLAW_AFTER_RESTART_OK" -> OPENCLAW_AFTER_RESTART_OK
```

**Rule:**

1. Restart/failure audits for Docker services must read `.Config.Healthcheck.Interval`, `.Config.Healthcheck.StartPeriod`, `.Config.Healthcheck.Timeout`, and `.Config.Healthcheck.Retries` before deciding the wait window.
2. Do not declare restart recovery red before at least one full post-start healthcheck interval has elapsed, unless the process is not running or the service port is closed.
3. During the Docker `starting` window, run a direct internal endpoint probe and one real user-path probe. For OpenClaw this means `/healthz` plus `run_task.py` exact-response.
4. Final proof requires both: Docker health eventually green, and a user-path probe green after restart.
5. If Docker health stays `starting` beyond one full interval plus one timeout while direct probes pass, classify as **healthcheck cadence/drift**, not service outage. The remediation is healthcheck tuning, not restarting the container again.

**Verification (this session):**

- Before restart: `health=healthy running=true restart=unless-stopped`.
- Restart command: `docker restart openclaw`.
- During first 120 seconds: `health=starting running=true`; `nc -z 127.0.0.1 18789` succeeded.
- Manual internal probe: `/healthz` returned `200 true {"ok":true,"status":"live"}`.
- User-path probe: `run_task.py --agent grok-ceo ... "Reply exactly: OPENCLAW_AFTER_RESTART_OK"` returned exact text and wrote/pushed task result.
- After Docker's next interval: `health=healthy`, health log exit `0`.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-61 — Risky manual-review update alerts must be digest state-change deduped (session 76, 2026-04-27)

**Symptom:** `morning-update-apply.sh` sent the same OpenClaw message every morning:

```text
OpenClaw image: :latest differs from current (RISKY auto-apply, manual: see skills/infrastructure/SKILL.md AP-61; review AP-4 before any container config change)
```

The signal was real once, but repeated daily with the same current image and same latest digest.

**Root cause:** The update check had no state-change memory for notify-only risky updates. It treated "current tag differs from latest" as a fresh event on every run, even when the operator had already been notified for that exact `(current tag, current digest, latest digest)` tuple.

**Rule:**

1. Risky update checks remain notify-only; never auto-upgrade OpenClaw, LiteLLM, or gbrain major/minor changes from a morning cron.
2. Notify-only findings must store a state signature containing the current deployed version/digest and the candidate latest version/digest.
3. Repeat notifications are allowed only when that signature changes or the state file is deliberately cleared after a manual review decision.
4. When current catches up to latest, delete the state file so the next future drift can alert once.
5. A repeated identical manual-review alert is noise, not vigilance; it trains the CEO to ignore Telegram.

**Implementation (this session):** `tools/morning-update-apply.sh` now writes `/Users/madia/nous-agaas/state/morning-update-openclaw-image.last` and suppresses duplicate OpenClaw image-drift notifications for the same digest pair.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-73 — Notify-only image checks must be registry-read-only (session 102, 2026-04-30)

**Symptom:** The morning OpenClaw manual-review check said "Don't auto-pull," but still ran:

```text
docker pull --quiet --platform linux/amd64 ghcr.io/openclaw/openclaw:latest
```

That did not replace the running container, but it mutated the local Docker image cache during a notify-only path and made "manual review" less literal than the operator contract.

**Root cause:** AP-61 fixed alert dedupe state but left discovery coupled to `docker pull`. The script used local image IDs for comparison, so it refreshed `:latest` into the Docker cache before it could decide whether to notify.

**Rule:**

1. Risky notify-only checks must be read-only against the running host: no `docker pull`, `docker run`, restart, alias, or container replacement.
2. Image-drift discovery should use `docker manifest inspect --verbose` and select the Linux/amd64 digest when the registry returns a multi-platform list.
3. State signatures should store the deployed image reference, deployed manifest digest, and candidate latest manifest digest.
4. If either registry digest cannot be read, leave the previous state file intact and log the comparison gap; do not clear dedupe state on network/registry failure.

**Implementation (this session):** `tools/morning-update-apply.sh` now reads current/latest OpenClaw manifest digests without pulling, and `tools/test_morning_update_openclaw_manifest.sh` guards that the OpenClaw section contains no `docker pull` and that manifest-list parsing is present.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

### AP-74 — Context-injector skill caps must spend budget on doctrine, not YAML (session 102, 2026-04-30)

**Symptom:** `gbrain-ops` frontmatter parsed cleanly in gbrain and OpenClaw, but the live `context_injector_v2.py` matched-skill path capped raw `SKILL.md` text at 1700 characters. A long YAML frontmatter block could consume the entire matched-skill budget before `# <skill>` or `## Current rules` appeared.

**Root cause:** `_read_skill_body()` applied `MAX_SKILL_CHARS` before separating metadata from runtime doctrine. This made title/body retrieval depend on frontmatter length instead of the skill's actual operational content.

**Rule:**

1. Context injectors must strip leading YAML frontmatter before applying per-skill body caps.
2. The first injected matched-skill bytes should normally include the H1 and actionable rules, not metadata.
3. Long descriptions belong in catalog/search metadata; they must not starve runtime doctrine injection.
4. Regression tests for skill budget must use a frontmatter block longer than `MAX_SKILL_CHARS` and assert the H1 plus doctrine survives.

**Implementation (this session):** `tools/context_injector_v2.py` now strips a leading YAML frontmatter block before truncation. `tools/test_context_injector_v2.py` adds a red/green case proving long frontmatter no longer hides the H1 or rule text.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/infrastructure/skill`.

## Timeline

- **2026-05-22** | v2.89.0 -> v2.90.0 — Added **AP-96** after the Air `com.nous.obsidian-sync` wrapper was found executing with a Mac-only `NOUS_VAULT` path. Symptom: the 60s sync loop skipped on stale merge markers from the wrong checkout while the actual Air wiki was clean, leaving the 5-minute `wiki-sync` loop as the only active writer and forcing closeout proof to wait for quiet windows; live verification also exposed overlapping StartInterval/manual runs causing a transient non-fast-forward push. Patch: `tools/nous-obsidian-sync.sh` now resolves `NOUS_VAULT_OVERRIDE`, then `/Users/madia/nous-agaas/wiki`, then the Mac Documents vault; resolves `vps` or `origin` as the canonical remote; logs the chosen vault at run start; and guards the git section with a `/tmp` single-flight lock. Static regression asserts the Air path precedes the Mac fallback, canonical remote operations use `$CANONICAL_REMOTE`, and the wrapper has a lock. No new LESSON (RULE ZERO).
- **2026-05-21** | v2.88.0 -> v2.89.0 — Added **AP-95** after strict substrate checks found Nous-GPU collector health was blocking green while the shared GPU host was externally offline and no GPU-bound workload was active. Patched `tools/nous_gpu_collector_health.sh` so default runs degrade with `SKIP optional Nous-GPU collector degraded ...` and exit 0, while `NOUS_GPU_REQUIRED=1` keeps the same failure hard-red. Updated `pages/entities/nous-gpu.md` with the current reachability fact and added optional/required regressions to `tools/test_nous_gpu_collector_health_rotation.sh`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/infrastructure/skill.
- **2026-05-19** | v2.87.0 -> v2.88.0 — Added **AP-94** after the Hermes/OpenClaw/iPad audit found that WebUI `/health` and public `/api/factory-events` checks can disagree: unauthenticated factory-events correctly returns 401, while authenticated login plus cookie returns live factory events. Root cause: `tools/hermes_canary_gate.py --webui-probe` only checked `/health`, so a canary promotion could pass on reachability without proving the iOS/TestFlight-observable factory event surface. Patched the gate to log in using Air's sealed `HERMES_WEBUI_PASSWORD` env file and require authenticated `/api/factory-events` JSON with sources + queue status. Regression: `tools/tests/test_hermes_canary_gate.py` adds red/green coverage for the auth event check; live Air gate returned `hermes_webui_factory_events_auth=GREEN`. No new LESSON (RULE ZERO).

- **2026-05-16** | v2.85.0 -> v2.86.0 — Added **AP-92** after the morning updater missed the active GStack upgrade signal because it searched only `.Codex/.codex` skill roots while this machine uses `/Users/madia/.agents/skills/gstack`. Patched `tools/morning-update-apply.sh` to scan `.agents` first, log the checker path, and warn about stale PATH `claude` when `/usr/local/bin/claude` shadows the current npm-global binary. No new LESSON (RULE ZERO).

- **2026-05-13** | v2.84.0 -> v2.85.0 — Control-plane closeout absorbed **AP-91** after exact GitHub mirror probe caught Mac/Air/VPS at `aa178ca7` while GitHub stayed at `7ba86317`. Root cause: launchd ran stale `/Users/madia/.local/bin/nous-obsidian-sync.sh` even though tracked `tools/nous-obsidian-sync.sh` had the GitHub mirror block. Deployed tracked script to live ProgramArguments target, added static/live identity detector, and verified factory probe green. No new LESSON (RULE ZERO).

- **2026-05-12** | v2.79.0 -> v2.80.0 — ERAP verification audit added **AP-86** after `pip install -e .` during a local E2E verification generated `projects/erap-intake/erap_intake.egg-info/` and Mac auto-sync committed it. Root cause: `.gitignore` covered `__pycache__` and `*.pyc` but not Python package metadata directories. Rule added: verification installs must run in temp venvs, and all `*.egg-info/` outputs are ignored/untracked before sync. Fix shipped: `.gitignore` now excludes `*.egg-info/` and the tracked ERAP egg-info files were removed in commit `1022aabc`. No new LESSON (RULE ZERO).
- **2026-05-12** | v2.78.0 -> v2.79.0 — Claude proof-pack routine freshness gap added **AP-85** after Madi pasted a 4h routine that clones GitHub, while Air auto-checkpoint wrote HANDOFF files only to the live Air/VPS wiki path. Root cause: GitHub mirror was an eventually-updated side channel; Air had no `github` remote, and a blind `git push github main` would be unsafe because the routine can push proof-card commits back first. Rule added: after a successful HANDOFF write, auto-checkpoint must sync at the checkpoint boundary by fetch/rebase from `origin`, fetch/rebase from `github/main` when present, then push `origin` and `github` without force; missing GitHub remote is yellow, conflicts notify and skip. Regression proof: `tools/test_auto_checkpoint.py` covers missing-remote origin push and GitHub-ahead rebase-before-push. No new LESSON (RULE ZERO).
- **2026-05-11** | v2.77.0 -> v2.78.0 — KEONA Todoist section repair added **AP-84** after Madi flagged that same-day KEONA tasks were in the shared project but not under `🤝Keona Partnership`. Root cause: writer passed `project_id` without `section_id`. Rule added: Todoist board-section writes must set both; KEONA contract is project `6gJ5j8PRVVCWpgCq`, section `6gXCgHcrqr2HvRqH`, labels `keona`, `spectra`, `проект:KEONA`. Live proof: moved 46 tasks, applied 50 label updates, posted 4 comments, readback `wrong_section_count = 0`, and recorded Madi Gmail sent id `19e16d3787adeffe`. No new LESSON (RULE ZERO).
- **2026-05-09** | v2.76.0 -> v2.77.0 — Satory Mergen ERAP session added **AP-83** after Todoist REST v2 returned HTTP `410 Gone` for task/comment/close calls, while official Todoist API v1 docs and live API v1 calls proved the correct mutation path. Rule added: Todoist operator mutations use unified `/api/v1` endpoints first; legacy REST v2 `410` is platform drift, not evidence that the task is missing. Live proof: API v1 comment returned `200`, close returned `204`, follow-up task GET returned `checked: true` and `completed_at: 2026-05-09T07:24:23.873495Z` for task `6gc5j8qM6X5hgGgH`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-05-08** | v2.75.0 -> v2.76.0 — Todoist sync audit added **AP-82**. Root cause: `todoist_sync.py --loop` treated transient Todoist API `503 Server Error` as an uncaught `requests.HTTPError`, crashing the long-running poller and relying on launchd `KeepAlive` to restart. Rule added: pollers for critical external APIs should contain transient HTTP/request failures inside the loop, emit structured error JSON, and retry after a bounded backoff without advancing state. Regression added in `tools/tests/test_todoist_sync.py::test_loop_poll_cycle_contains_transient_todoist_http_error`; focused suite `tools/tests/test_todoist_sync.py tools/tests/test_air_watchdog.py` passed 11/11. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-05-08** | v2.74.0 -> v2.75.0 — Air watchdog false-red audit added **AP-81**. Root cause: VPS `air_watchdog.py` alerted `🔴 Air poller dead` when the Air HTTP health endpoint was `http_200` but the secondary SSH `launchctl` check timed out; that combination proves observer transport uncertainty, not target death. Rule added: HTTP failure or a successful SSH check proving poller label/exit failure remains red, while HTTP green + SSH transport error is logged as `poller_unknown_ssh_transport:*` and does not page. Regression added in `tools/tests/test_air_watchdog.py::test_http_green_poller_ssh_timeout_is_unknown_not_dead`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-05-05** | v2.73.0 -> v2.74.0 — Pane 2 Day-0 Slice F added **AP-80**. Live citation-verifier smoke showed `curl -I https://example.com` returned `HTTP/2 200`, but Python `urllib` HEAD raised `CERTIFICATE_VERIFY_FAILED` from the local macOS Python CA path. Rule added: HTTPS verifier/probe code should retry with `certifi`'s CA bundle before classifying a URL as broken; do not disable TLS verification. Regression added in `tools/tests/test_citation_verifier.py::test_verify_url_retries_with_certifi_on_local_ca_failure`; final live CLI proof returned `{"kind": "url", "result": "200", "target": "https://example.com"}`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-05-05** | v2.72.0 -> v2.73.0 — Pane 2 Day-0 Slice E absorbed **AP-79**. Root cause: the first `restart_critical.sh` kill drill killed `telegram_poll.py`, but launchd stdout/stderr mtimes stayed old, so the wrapper misclassified a fresh `-15/-9` exit as stale. Second bug: the wrapper's VPS autopilot `ssh` calls lacked `-n`, so when invoked from a heredoc/stdin-driven drill harness they consumed the parent script's remaining respawn-check loop. Rule added: restart guards must maintain their own first-seen failure timestamp for recency and every nested SSH call in a script that might run under stdin must use `ssh -n`. Final proof: kill `com.nous.telegram-poll` PID `84659` with TERM -> `after_kill=-:-15` -> `restart_critical.sh` printed `target=telegram-poll action=restart status=restarted detail=exit_-15 observed_age=0s` -> `respawn_pid=84746` within 30s. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-05-05** | v2.71.0 -> v2.72.0 — Pane 2 Day-0 Slice D absorbed **AP-78**. Root cause: while exposing VPS Langfuse to Air over Tailscale, a Caddy site address written as `http://100.99.24.104:3301` validated but still listened as `*:3301`; the earlier `http://100.99.24.104:3001` form also collided with Docker's `127.0.0.1:3001` bind. Rule added: Tailscale-only Caddy listeners must use a separate port plus explicit `bind <tailscale-ip>` inside the site block, then prove `ss -ltnp` shows the Tailscale IP, not `*`. Final live proof: `LISTEN ... 100.99.24.104:3301 ... caddy` and Air `curl http://100.99.24.104:3301/api/public/health` returned `200 {"status":"OK","version":"2.95.11"}`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-05-05** | v2.70.0 -> v2.71.0 — Pane 2 Day-0 watchdog drill absorbed **AP-77**. Root cause: after `launchctl bootout` / `bootstrap` / `kickstart` on Air, `launchctl list` can show a live numeric PID with a stale negative last-exit/signal field, e.g. `73732 -15 com.nous.telegram-poll`. The first Slice C watchdog implementation treated the stale `-15` as red even though the job was already running. Rule added: poller health parsers must read launchd as label missing = red; numeric PID = green regardless of second field; PID `-` plus exit `0` = green for clean `StartInterval`; PID `-` plus nonzero = red. Regression proof: `tools/tests/test_air_watchdog.py::test_running_poller_pid_overrides_stale_negative_exit_status`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v2.69.0 → v2.70.0 — Session s2148-mac-95617 atomic continuation audit absorbed **AP-76** (Docker reports container "healthy" while gateway HTTP server is hung). Trigger: live incident detected during deep-dive audit — substrate watchdog `port18789: up → down` fired at 22:15 while `docker ps` showed `Up 36 hours (healthy)`. `curl localhost:18789/health` returned HTTP 000 with 5+ sec timeout; CLOSE_WAIT/FIN_WAIT_2 connections piled up; logs went silent for 5h after a 17:14 successful response. Two `[agent/embedded] incomplete turn detected ... stopReason=stop payloads=0` errors at 05:14 and 16:58 were the silent leading indicator (DeepSeek-flash worker returning empty payload, gateway didn't recover the work-loop). Madi's /ask attempts (correlation_id=tg_1123) stalled with `⏳ Routing to OpenClaw…` and `Agent error (exit 2)`, cost $0.00. Recovery: `docker restart openclaw` → 75s boot (config-load → auth → 5-plugin reload → HTTP server → heartbeat) → HTTP 200 confirmed. Codified restart playbook + 90-second wait + boot-order observation. Detection improvement queued: `[agent/embedded] incomplete turn` log-grep alert as earlier indicator. Engineering fix queued: gateway should self-restart affected lane on N consecutive incomplete-turn events. Cross-ref: AP-60 (HTTP 200 not just `up`); AP-75 (alert-first ordering — doctrine validated, watchdog DID alert first); `agent-quality` AP-10 (don't trust mechanism tests alone); `ceo-hierarchy` (the routing chain that surfaced the failure). 3-edit ritual per AP-11: frontmatter v2.70.0 + H1 + this entry. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/infrastructure/skill.

- **2026-04-30** | v2.66.0 -> v2.67.0 — Context-injector audit absorbed **AP-74** after the gbrain-ops truncation concern was narrowed: gbrain/OpenClaw stored the full 1050-char description, but `context_injector_v2._read_skill_body()` capped raw `SKILL.md` before removing YAML, so long frontmatter could hide the H1 and doctrine. Patched the injector to strip leading YAML before `MAX_SKILL_CHARS`; added a regression test with frontmatter longer than the cap. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v2.65.0 -> v2.66.0 — Morning OpenClaw manual-review audit absorbed **AP-73**. Root cause: AP-61 deduped repeated risky image alerts, but the checker still used `docker pull --quiet ...:latest` to refresh the candidate image before comparing digests. Patched `tools/morning-update-apply.sh` to use `docker manifest inspect --verbose` and Linux/amd64 digest parsing instead, leaving notify-only paths read-only against Docker runtime state. Added `tools/test_morning_update_openclaw_manifest.sh`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.64.0 → v2.65.0 — Session 85 absorbed **AP-72** from a same-day recurrence audit. AUDIT-057's morning prune recovered Air to 43 GiB free / 91%; <24h later the volume was back to 25 GiB free / 95% with zero deploy events. Re-running `docker builder prune -af` + `docker image prune -f` recovered only ~3.3 GiB (to 28 GiB free / 94%) because the remaining 9.5 GiB sits in tagged-but-unused images that require explicit `rmi`. Codified the recurrence pattern: AP-67 is a one-time recovery; the durable fix is a scheduled daily prune cron + a weekly tagged-image audit. Manual prune is not idempotent on a live OpenClaw host because container churn regenerates dangling layers continuously. Implementation of `com.nous.docker-prune-daily` queued for next session. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.62.0 -> v2.63.0 — Launch-readiness audit absorbed **AP-70**. Root cause: Blacksmith burst CI had a valid manual workflow file but no runner/app connection; proof run `25091836550` stayed queued with `runnerName=null` and was cancelled after evidence capture. Rule added: CI readiness requires actual job runner assignment, not YAML presence. GitHub issue #1 records the blocker and next action. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.61.0 -> v2.62.0 — Session 79 substrate audit absorbed **AP-69**. Root cause: `session_rotate.sh` measured container paths with host-shell redirection and then rewrote OpenClaw JSONL sessions to invalid `[]` instead of preserving the `type=session` header. Patched rotation to run `wc` inside `docker exec ... sh -c`, trim only to the first valid header line, skip invalid files, and added `tools/test_session_rotate_preserves_header.sh`. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.60.0 -> v2.61.0 — Morning Telegram audit absorbed **AP-68**. Root cause: Claude Code auto-update operated on `$HOME/.npm-global/bin/claude`, but Air `/code` still executed stale `/usr/local/bin/claude` because `command_center.py` had a hardcoded root path and AP-26 incorrectly claimed the stale binary was unreferenced. Patched Air runtime to use the user-scoped binary by default, updated audit doctrine in `audit` AP-36, and corrected AP-26's deletion guidance. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-28** | v2.59.0 -> v2.60.0 — AGaaS/DGX substrate audit absorbed AP-67. Root cause: Air disk pressure was red, but broad volume scans were too heavy and the first safe deletion target was Docker Desktop state, not `~/nous-agaas`. `docker builder prune -af` plus `docker image prune -f` removed build cache/dangling layers, moved APFS Data from 13 GiB free / 97% to 43 GiB free / 91%, and kept OpenClaw healthy. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-28** | v2.57.1 -> v2.58.0 — Morning-review audit absorbed AP-65. Root cause: AP-64's model-health cache fallback reused `?` as both "missing field" and "unknown value," so a broken deep `/health` probe could persist fake `?` model-health facts into `light-probe-state.json`. Patched `tools/light-probe.sh` to omit model fields when there is no previous/cache/parsed baseline and compare with a non-persisted `__missing__` sentinel. Also corrected the OpenClaw image manual-review message to point at AP-61 plus AP-4. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-28** | v2.58.0 -> v2.59.0 — Nous-GPU live-audit absorbed AP-66. Root cause: `tools/test_nous_gpu_wg0_collector_live.sh` still used a host-sudo WireGuard handshake read even though runtime WireGuard state is owned by Docker container `nous-wg`. Patched the validator to use configurable `WG_CONTAINER` plus `docker exec`, preserving the AP-58 upstream-vs-filter diagnostic while deleting needless privilege coupling. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.57.0 -> v2.57.1 — AP-64 verification patch. Air live run caught `tools/light-probe.sh: NOW_EPOCH: unbound variable` because the new model-health cache used the timestamp before the compare block initialized it under `set -u`. Moved `TS`/`NOW_EPOCH` initialization before the cache block and added the AP-64 verification gotcha. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.56.0 -> v2.57.0 — Model-flap incident absorbed **AP-64**. Root cause: scheduled heartbeat scripts used LiteLLM `/health`, a deep all-model provider canary, as a liveness check; OpenRouter DeepSeek V4 and ZAI shared endpoints returned transient 429s and generated Telegram red state-change noise while the core factory remained alive. Patched light-probe to use readiness for fast liveness, cache deep model-health for four hours, and suppress known monitor-only shared-provider flaps; patched morning/nightly scripts to use readiness and remove "all systems 100%" wording. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.63.0 → v2.64.0 — Absorbed **AP-71** from the daily 03:00 retry audit. Root cause: `tools/nous_gpu_collector_health.sh` treated same-path pcap truncation/recreation as a negative growth delta, producing false RED while live logs showed multi-GB collector growth around the event. Patched same-path `curr_size < last_size` to reset the baseline like path rotation; next probe enforces growth. Added `tools/test_nous_gpu_collector_health_rotation.sh`; proof: `collector-health-rotation: 5 pass, 0 fail`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.55.0 -> v2.56.0 — Blacksmith burst-CI lane absorbed **AP-63**. Root cause: local OpenClaw tests were CPU-constrained, but the repo had no GitHub Actions lane and one portable test hardcoded the Mac vault path. Added manual `.github/workflows/blacksmith-burst-tests.yml` on `blacksmith-32vcpu-ubuntu-2404`, added `tools/blacksmith_burst_tests.sh`, fixed `tools/test_wiki_to_runtime_rsync.sh` to resolve the repo root dynamically and expect additive `_gbrain/` sync per current doctrine, removed a same-session Bash-4 `mapfile` portability miss, and extended `test_run_task_model_truth.py` to cover DeepSeek V4 Flash/Pro. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.54.0 → v2.55.0 — Agent constitution runtime-sync gap absorbed **AP-62**. Root cause: `tools/wiki-to-runtime-rsync.sh` never mirrored `pages/systems/nous-agent-{soul,user,procedures}.md` into OpenClaw, so runtime kept stale SOUL/AGENTS and blank USER despite vault docs claiming identity sync. Fixed rsync to copy the canonical triad into OpenClaw workspace + `/opt/nous-agaas/agents`, copy USER into grok-ceo, and added `tools/test_agent_identity_runtime_parity.sh` for Air fail-closed proof. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.53.3 → v2.54.0 — Telegram daily-control repair absorbed **AP-61**. Root cause: `morning-update-apply.sh` warned every day about the same OpenClaw `:latest` vs pinned `2026.4.14` digest difference because notify-only risky updates had no state-change memory. Fixed the script to store `(current tag, current digest, latest digest)` in `/Users/madia/nous-agaas/state/morning-update-openclaw-image.last` and only re-alert when that tuple changes. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.53.2 → v2.53.3 — Telegram/OpenClaw reliability audit absorbed **AP-60**. Root cause: the first OpenClaw restart proof waited 120s, but the Docker healthcheck interval is 180s; OpenClaw was already live (`/healthz` HTTP 200 and `run_task.py` exact-response OK) while Docker still showed `starting`. Rule added: restart proofs must inspect healthcheck cadence, probe the internal endpoint, run one user-path exact-response, and wait at least one full healthcheck interval before marking restart recovery red. Verification: `docker restart openclaw` recovered to `health=healthy`; `OPENCLAW_AFTER_RESTART_OK` returned after restart. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.53.1 → v2.53.2 — Same continuity audit, counter-check on Air found the new AP-49 parity detector failed there because Air's wiki path (`~/nous-agaas/wiki`) has no Mac project-root `CLAUDE.md`/`AGENTS.md` parent. Root cause: the detector encoded a Mac-local invariant as a universal host invariant. Patched `tools/test_claude_md_parity.sh` to require Mac-root shims only when the Mac project root is locally mounted; Air/VPS now skip unavailable Mac-root shim checks while still requiring the vault quickref reciprocal pointer. Verification target: Mac and Air `bash tools/test_claude_md_parity.sh` both return red=0. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.53.0 → v2.53.1 — Continuity audit after user directive "work from here or Claude Code or Telegram, up to date all the time." **Extended AP-49** from Claude-only to Claude+Codex session shims. Root cause: Codex uses Mac-root `AGENTS.md`, but `tools/test_claude_md_parity.sh` only checked Mac-root `CLAUDE.md`; a `/codex` route/documentation update could drift out of Codex startup context while the old parity probe still passed. Patched the detector to require both `CLAUDE.md` and `AGENTS.md` to point to `pages/systems/architecture-quickref.md`, and updated `architecture-quickref` to identify both shims plus `/codex` and `/code` Air routes. Verification: `bash Nous/tools/test_claude_md_parity.sh` returns red=0. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).
- **2026-04-26** | v2.52.1 → v2.53.0 — Same Codex self-audit, **absorbed AP-59**. User challenged "all done?" and the answer was no; re-reading the whole current plan/handoff showed auto-sync attribution drift remained an active blocker. The race recurred in-session: `99ee2eec auto-sync 2026-04-26 19:12:02` grabbed the first sync-script patch. Root cause upgraded from "mtime guard too short" to "generic auto-sync was still authorized to commit authorial-class paths." Patched Mac `nous-obsidian-sync`, Air `wiki-sync-launch`, and VPS `wiki_to_bare` to skip when dirty authorial-class paths exist; added `tools/test_auto_sync_authorial_guard.sh`; deployed runtime copies to Mac/Air/VPS. Live proof: with untracked `tools/test_auto_sync_authorial_guard.sh`, Mac sync logged the skip and created no auto-sync commit. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-04-26** | v2.52.0 → v2.52.1 — Same Codex self-audit, AP-58 correction. Follow-up launchd runs showed `wg_rx_delta=184B` and `wg_tx_delta=744B` with no pcap writes; first AP-58 patch treated any positive RX delta as payload and misclassified keepalive-scale movement as collector/filter drift. Corrected `tools/nous_gpu_collector_health.sh` with `MIN_WG_PAYLOAD_BYTES=1024`: fresh handshake + RX below threshold stays "upstream mirror likely stopped"; only payload-scale RX with pcap silence becomes filter/path drift. This is the same failure→skill loop applied to my own patch in-session. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-04-26** | v2.51.0 → v2.52.0 — Session 75 (Codex self-audit under Madi directive "no bs, no lie, no cheat"). **Absorbed AP-58** — Nous-GPU collector monitor was red for a real reason, but the alert was too vague. Live evidence: Air could reach GPU; `nous-collector` and `nous-wg` were running; WireGuard handshake was fresh; `wg0` RX bytes did not move over 20s; both `tcpdump -i wg0` and `tcpdump udp port 37008` saw zero packets; live pcap remained 24 bytes since 2026-04-24 09:00 Almaty. Root cause is upstream-data-stop (Denis/Satory side not sending mirrored payload), not local Docker crash. Patched `tools/nous_gpu_collector_health.sh` to persist WG RX/TX counters and classify failures as upstream stop vs collector/filter drift vs stale tunnel. Verification: two manual Air runs; first initialized counter state, second emitted `wg_handshake_age=6s wg_rx_delta=0B wg_tx_delta=0B; wg alive, no incoming payload since last probe; upstream mirror likely stopped`; launchd kickstart emitted the enriched failure too. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-04-25** | v2.50.0 → v2.51.0 — Session 73 continuation (s73-mac-44586, Mac-interactive, audit-only post-758a0db5). **Absorbed AP-57** — `raw/presentations/node_modules/` (build-artifact dependency code, ~4572 tracked files, no `.gitignore` rule) + `pages/progress/claude-memory/` (LAW-005 symlink target for live auto-memory store) classified as protected paths. Trigger: this session's audit surfaced 37 memory topic files wiped at 16:41:52 by a 4-strong fleet of Opus-4.6 computer-use agents (`--allow-dangerously-skip-permissions + bypassPermissions`) and 2640 spurious `D` entries blocking LAW-005 GATE 5 every session. Fix: (1) `.gitignore` extended + `git rm -r --cached raw/presentations/node_modules/` (commits `8a037991` + follow-up — 2640 files untracked, on disk preserved); (2) `git checkout HEAD -- pages/progress/claude-memory/` restored 38 files. Procedural rule + compounding-gate-candidate `test_protected_paths_intact.sh` queued session-74+. Forensic gap honestly named: `~/Library/Application Support/Claude/local-agent-mode-sessions/` showed Jan-15 last-mod (transcripts non-authoritative), so the rm-attributing agent PID is unrecoverable from logs alone — process-audit hook on `rm`/`unlink` syscalls deferred to s74+. Telegram broadcast msg_id=1022 preserves the incident across sessions per substrate-broadcast model. 11th compounding rule (procedural this turn; mechanical gate s74+). gbrain-timeline-deferred: pages/skills/infrastructure/skill (MCP gbrain disconnected mid-session; SSH-CLI fallback used). No new LESSON (RULE ZERO).

- **2026-04-24** | v2.49.0 → v2.50.0 — Session 73 (Mac-interactive, s1404 post-/clear) **absorbed AP-56** — mechanical enforcement for the `.git/hooks/*` canon-drift class AP-55 codified as doctrine-only. Extended `tools/pre-push-sanity.sh` with CHECK B: explicit `GIT_HOOK_MAP` mapping (pre-commit ↔ pre-commit-hook-tan-pattern.sh, commit-msg ↔ commit-msg-hook.sh new-this-session, pre-push ↔ pre-push-sanity.sh). Deployed to `.git/hooks/pre-push` on Mac; 4-target parity via auto-sync + manual VPS/Air wiki propagation. Positive test: clean canon → exit 0. Negative test: synthetic 1-byte drift on `.git/hooks/pre-commit` → exit 1 with explicit CHECK B banner + deployed/canon MD5 diff + 4-option remediation. Closes AP-55's "compounding gate candidate queued session-73+" to SHIPPED. Created `tools/commit-msg-hook.sh` as canonical twin for `.git/hooks/commit-msg` (previously had no vault-tracked source — that gap was the AP-55 precondition). 10th compounding mechanical gate. `tools/pre-push-sanity.sh` MD5 `2e34402d` → `b472ce96`. gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-04-24** | v2.48.1 → v2.49.0 — Session 72 (Mac-interactive, post-/clear) **absorbed AP-55** — `.git/hooks/pre-commit` canon-deployed drift doctrine. SOAO RED surfaced: deployed hook MD5 `f6c873f8` (Mac+Air+VPS agree) ≠ canon MD5 `40fd8abb` (`tools/pre-commit-hook-tan-pattern.sh`). Session 68p patched deployed with new RULE 7 `test_agent_autonomy.sh` block but didn't `cp` back to canon — 5-day silent drift visible only via SOAO. Fix: `cp .git/hooks/pre-commit tools/pre-commit-hook-tan-pattern.sh` → 4-target MD5 converges on `f6c873f8`. Codified: any `.git/hooks/*` patch requires canon write-back + same-commit authorial commit per SOC Rule 19. Compounding-gate candidate session-73+: extend AP-35's pre-push parity to cover `.git/hooks/*` in addition to `~/.claude/hooks/*`. Applied musk step 2 (delete the drift, not wrap it in abstraction). gbrain-timeline-ok: pages/skills/infrastructure/skill. No new LESSON (RULE ZERO).

- **2026-04-24** | v2.48.0 → v2.48.1 — Session 72 (Mac-interactive) version-claim audit under Madi directive *"update all that gstack and gbrain and all of the things we have. must be up to date."* **3 findings, no new AP (existing `audit` AP-10 covers the class — doctrine dogfooded):** (1) **gstack current at v1.5.1.0** (verified via `~/.gstack/.last-setup-version` + `~/.claude/skills/gstack/package.json` + `gstack-update-check` exit 0 empty-stdout = no upstream update available). (2) **gbrain is 10 minor versions behind upstream** — local at `v0.10.1` (commit `b7e3005`, 2026-04-15 era), upstream `garrytan/gbrain` on `origin/master` at ≥`v0.20.3` with v0.19.2 / v0.20.0 / v0.20.1 / v0.20.2 / v0.20.3 release chain visible in `git log --all --since='2 weeks ago'`. Upgrade queued for session-73+ with karpathy-loop AP-5 multi-reviewer trigger (cross-system breaking-changes risk → `Skill(plan-eng-review)` + `Skill(plan-devex-review)` mandatory before upgrade execution). (3) **session-70-cont HANDOFF narrative claim "GStack v1.11.0 release 2026-04-24 — /ship stacks VERSIONs + CHANGELOGs atomically for multi-PR landing" was unverified** — ground truth shows ship SKILL.md at v1.0.0 with singular-VERSION/CHANGELOG description, no multi-PR capability present. Exact `audit` AP-10 class (session 38 "sync golden" claim stale at session 39 open, same family). **Fabrication rejected at substrate boundary** — no Timeline entry written claiming v1.11.0 capabilities; this entry names the rejection explicitly so the forward-record is honest. Applied Musk Step-2 (delete unsigned requirement) + Karpathy "think before coding / state assumptions" — HANDOFF claim did not pass evidence gate. Compounding artifact = this honest Timeline entry + session-72 handoff cross-ref; no skill-body rewrite because the catch validated existing doctrine, not a new class. No new LESSON (RULE ZERO).


 **Absorbed AP-54** — auto-sync attribution-drift detector `tools/test_authorial_commits.sh` shipped 4-target MD5 `bf8d02e878044cffbaad64b91df87229` (Mac vault + VPS wiki + Air wiki + Air runtime). SOC Rule 19 class — 5-session recurrence chain (59/66/67/68p/70). Dogfooded: caught `1cd9198e` (air-sync 17:11) + `62ccbea5` (vps auto-sync mirror) on the session-70 rsync-script extension. Not a hard block (git history immutable); surveillance/post-audit integration with SOAO candidate session-71+. Forward-facing mitigation codified: commit own work immediately + `git commit -o` tight scope + same-turn atomic stage+commit. No new LESSON (RULE ZERO).


- **2026-04-24** | v2.47.0 → v2.47.1 — Session 70 follow-up (Madi directive: *"what hook is that? let's work on that"*). Patched `~/.claude/hooks/task-completed-enforce.sh` infrastructure-override keyword list to cover Musk/Karpathy substrate-hygiene task vocabulary: added `musk-step`, `musk-algorithm`, `gap-list`, `hybrid-enforcement`, `recursive-musk`, `substrate-hygiene`, `Karpathy-6-axis`, `DONE-protocol`, `10%-add-back`, `AP-<N>-codification`, `scorecard`. Same-session root cause: task 5 "Musk-step-2 pass on gap list" was falling through to product-default because (a) subject+description had no matching vault/infra regex keywords, (b) description's `REQ-VMS` token trip the product `\bVMS\b` detector. Fix preserves product-enforcement for real VMS/ERAP/BDL work (test 2 on "Implement VMS filter for police_dashboard violation detection" still BLOCKS Gate 1+2). Hook Mac-local (not vault-tracked); backup at `~/.claude/hooks/task-completed-enforce.sh.pre-s70-musk-keywords`. Same enforcement class as AP-43 RULE 4 (pre-commit hooks) but task-completed rather than git-boundary — codified here so future agents know both surfaces exist. No new LESSON (RULE ZERO).


- **2026-04-23** | v2.46.0 → v2.47.0 — Session 70 (Madi directive: "fix, root cause find and fix, then skill, use musk 5 step rule" on the 5 weak gaps I named session-68p honestly). **Absorbed AP-53** — closes 2 of 5 gaps; the other 3 were Musk-step-2 deletions (meta-observation / defensive-no-recurrence / nice-to-have). Gap A = rsync scope missed tenants/; Gap B = periphery Python paths bypassed AP-4 gate. Both fixed + live-tested this session. rsync script 4564B → 6513B; 3 Python files AST-patched (auto_checkpoint.py + tools/auto_checkpoint.py + factory_health.py); 4-way MD5 `2329eaa7aa8f6b71b1be657bc87b694c` GOLDEN. Live test: `_telegram_notify("your call on this")` → BLOCKED, returned None; tenant sync output `OK: tenant/satory/skills/ sync complete`. AP-4 Telegram-boundary coverage extended from 1 Python hot path → 4 Python paths. Musk 5-step applied in order: Step 1 question (3 of 5 gaps weren't real bugs), Step 2 delete (3 deleted), Step 3 simplify (no centralized wrapper — direct AST patch beats abstraction for N=3), Step 4 accelerate (parallel deploy to 3 targets), Step 5 automate (rule + detector queued). No new LESSON (RULE ZERO).

- **2026-04-22** | v2.44.0 → v2.45.0 — Session 63 (Musk-execute extension of session 62 audit): Extended AP-51 auto-sync user-commit-race guard from 15s → 30s mtime + added tracked-file-mtime check (30s on any `git diff --name-only HEAD` file). Session 62 audit measured 8 auto-sync : 4 authorial ratio in 30min window — multi-tool-call Edit sequences span >15s before final `git commit`, so 15s window still absorbed most authorial commits. 30s window + working-tree check catches mid-Edit-sequence state. Dogfooded: touching MEMORY.md triggered skip with "index modified 1s ago" log. Ratio should improve materially next audit. No new AP (this is AP-51 body refinement, not new failure). Amends AP-51 rule 1 from "must include 15s mtime guard" to "must include 30s mtime guard + working-tree-file mtime check." No new LESSON (RULE ZERO).
- **2026-04-22** | v2.43.0 → v2.44.0 — Session 60 (deep-audit extension of session 59): **Absorbed AP-51** (auto-sync user-commit-race guard). 3 of session-59's HEREDOC commits had their messages silently rewritten by `com.nous.obsidian-sync` (every-60s launchd) as generic `auto-sync TIMESTAMP`. Root cause: race between user `git add` → `git commit` and auto-sync's `git add -A && git commit`. Fixed `/Users/madia/.local/bin/nous-obsidian-sync.sh` with 0-th step: skip if `.git/index.lock` present OR `.git/index` mtime <15s. 2 single-session occurrences satisfy recurrence-gate. Cross-ref session-operating-contract new Rule 18 (no-defer-on-textbook-bug, same-session codification). Compounding gate queued: `tools/test_auto_sync_user_commit_guard.sh` regression guard. No new LESSON (RULE ZERO).
- **2026-04-21** | v2.42.0 → v2.43.0 — Session 56 extension (Mac-interactive, same session as collector-live-phase-1-cut-over): absorbed **AP-50** (shipped-artifact path coupling — audit all consumers on rename). Trigger: Phase-0→Phase-1 collector cut-over (flipped `-i tailscale0` → `-i wg0`; output file renamed `collector.pcap` → `wg0-collector.pcap`) silently broke 3 consumers that hardcoded the old filename — health probe false-OK'd `pcap=24 delta=+0` for 90 min of real traffic, regression-probe auto-detect pattern existed in sibling but wasn't applied here, and rotation script would have compressed the 24-byte stub hourly while real pcap grew unbounded toward eventual disk fill (~40-day horizon on 859 GB free). All three caught by same-session 3-host grep audit (Mac vault + Air + Nous-GPU `/usr/local/bin/`) + fixed with `docker inspect -w` auto-detection (Pattern A) and `find -mmin` latest-active lookup (Pattern B). Rule 4 in AP body mandates state-tracked `(path, size)` delta alarm to replace "file stat succeeded = OK" false positives. Meta-class shared with `session-operating-contract` AP-10 (narrative-claim ran ahead of substrate reality) and `audit` AP-20 (probe-E2E-verify) — this AP extends AP-20 from "run the probe" to "run the probe WHILE production shape is representative." Detector `tools/test_no_hardcoded_pcap_paths.sh` batched with AP-8/AP-9/AP-11 detector cluster, ship session-57+. No new LESSON (RULE ZERO).
- **2026-04-20** | v2.41.0 → v2.42.0 — Session 54 Phase-2 absorption: **Absorbed AP-49** (Vault-substrate-mirror discipline). Phase-1 probes revealed 2 same-class drifts: (B) Mac-root `CLAUDE.md` had session-51/52/53 operational updates that never reached the vault → Air factory + /code CLI invisible to 3 sessions of doctrine; fixed by extracting to `pages/systems/architecture-quickref.md` commits `B3` (`2cfcf620`) + `B3b` (`4c8d7fc4`). (E1) Air live hook `task-completed-enforce.sh` MD5 `8cc618d9` vs canonical `99ea6f87` — 2-day-stale, missing session-51 `IS_INFRASTRUCTURE_TASK` override; detected by Air's pre-push hook rejecting `93eaf1a5` push with explicit HOOK DRIFT message; deployed vault→live via `scp` + retry succeeded. Root cause common: two substrate classes fall outside existing mechanical sync (Mac-root is extra-vault; Air `~/.claude/hooks/` isn't covered by AP-37 rsync). AP-49 codifies the class-taxonomy + specifies session-55+ mechanical gates (`test_air_live_hook_parity.sh`, `test_claude_md_parity.sh`). No new LESSON (RULE ZERO).
- **2026-04-18** | v2.40.0 → v2.41.0 — Session 48 Mac-interactive deep-audit (Madi-triggered): **Absorbed AP-48** (Pre-commit RULE 4 further extension: SKILL.md Timeline↔AP-bullet orphan detection) — closes `mistake-to-skill` AP-11 v1.9's "manual-only, next-session candidate" status that had lingered across sessions 46-round-2 → 47 → 48 W-thread → 48 Mac thread accumulating 2 real orphans. Scanner `tools/test_skill_version_parity.sh` gets a 3rd structural check alongside AP-43 (version parity) + AP-46 (YAML validity): for every SKILL.md's `## Timeline` or `## Evidence trail` section, extract `"added/extended/absorbed AP-N" / "**AP-N**"` claims and verify each has a matching bullet (`### AP-N` / `- **AP-N:** / **AP-N —**`) anywhere in the file. **Live-tested:** POSITIVE 21/21 skills clean after this-session orphan patches (infrastructure AP-45, secrets-management AP-10); NEGATIVE — a fabricated `/tmp/orph-test/SKILL.md` whose Timeline contained a synthetic high-number AP claim with no matching bullet → scanner exit 2 with `DRIFT orph-test: Timeline claims AP-N but no matching bullet in file`. Dep: python3 pure stdlib (re + glob), no external libs; graceful-skip if python3 missing. Session evidence chain: deep-audit orphan scanner (inline Python) surfaced 2 orphans → both patched inline → scanner codified into pre-commit RULE 4 path → AP-48 absorbed here. **Paired doctrine update:** `mistake-to-skill` v1.10 → v1.11 updates AP-11 v1.9 4th-check section text from "manual-only" → "mechanical via infrastructure AP-48" (same-session atomic bump). **3 structural invariants** now all mechanical on RULE 4: (1) version parity, (2) YAML validity, (3) Timeline↔AP-bullet parity. **8th compounding mechanical gate** overall (AP-35, AP-36, AP-43, AP-44, AP-45, AP-46, pre-receive, this — plus TaskCompleted 9-gate classifier). Karpathy-primary: the orphan-scanner closes the AP-15 meta-pattern sub-class "mid-session codified rule not applied to same-session edits" for the AP-bullet dimension — the machine now catches what agent memory forgets. No new LESSON (RULE ZERO).
- **2026-04-18** | v2.39.0 → v2.40.0 — Session 48 W11+W12+W13 (main thread, parallel to AP-46 Mac-interactive thread): **Absorbed AP-47** — OpenClaw 2026.4.14 skillsSnapshot.version=0 freeze bug + manual-bump workaround. Evidence: W11 investigation revealed factory runtime loaded only **4 of 21** our skills at `/ask` time (camera-management, infrastructure, metrology-cert-tracker, smartbridge-soap-client) because `sessions.json.skillsSnapshot.version=0` + `getSkillsSnapshotVersion()=0` → `shouldRefreshSnapshotForVersion(0, 0) === false` → chokidar file-watcher never successfully bumps `globalVersion` for new SKILL.md additions. W12 fix: backup sessions.json → edit `skillsSnapshot.version` 0 → N+1 → trigger rebuild via minimal `run_task.py` call → factory rebuilds snapshot from live filesystem → all current skills registered. **Verified 21/21** (was 4/21 at open). Also caught storage-retrieval SKILL.md had old `id`+`title` schema without OpenClaw-required `name`+`description` → frontmatter-schema-completeness requirement (amends AP-46's YAML validity to include field-completeness). **Workaround tool shipped:** `tools/bump_openclaw_skills_version.sh` — backup → version bump → trivial task → verify, all via ssh to Air + docker exec. Runs from Mac. **Future compounding candidates:** (AP-48) Timeline↔AP-bullet parity scanner (4th-check from `mistake-to-skill` AP-11 v1.9) — both parallel thread + this thread identified this as next mechanical gate. (Further) pre-commit RULE 7 candidate: `test_skill_schema_completeness.sh` enforcing `name`+`description` required in skill frontmatter — prevents future storage-retrieval-style silent drops. **Karpathy-primary:** the investigation→fix→absorption loop closed in one session (W11→W12→W13) IS the compounding artifact. Factory is now 5x more capable at `/ask` time (16 new skills unlocked: audit, agent-quality, air-ssh-access, command-center, error-classification, evidence-verification, factory-ops, gbrain-ops, kazakhstan-regulatory, mistake-to-skill, planning-discipline, satory-dashboard, secrets-management, session-operating-contract, tailscale-stability, website-deploy). No new LESSON (RULE ZERO).
- **2026-04-18** | v2.38.0 → v2.39.0 — Session 48 Mac-interactive (parallel to W-thread). **Absorbed AP-46** (Pre-commit RULE 4 extension: SKILL.md YAML frontmatter validity gate) — closes `mistake-to-skill` AP-12's "next-session compound gate candidate." Scanner `tools/test_skill_version_parity.sh` extended with `yaml.safe_load` pass on every SKILL.md frontmatter block (extracted via `awk '/^---$/{c++; next} c==1'`); exception → DRIFT with actual parser line/col + AP-12 pointer. **Live-tested:** POSITIVE 21/21 skills PASS after the extension surfaced + fixed 1 latent drift (`secrets-management` v1.4 unquoted-colon in description — quoted + replaced internal colon with em-dash for defense-in-depth); NEGATIVE `/tmp/sovptest-skill/SKILL.md` with `related: [[a]], [[b]]` → exit 2 with `"line 4, column 15: expected block end but found ','"`. **Cross-session corrective:** also added missing `### AP-45` bullet summarizing session 48 W4's Timeline v2.37→v2.38 entry — orphan rule detected via `mistake-to-skill` AP-11 v1.9 4th-check manual review (Timeline described AP-45 but no matching AP-45 bullet existed in Anti-Patterns). **Deps verified:** Python 3 + PyYAML present Mac 6.0.3 / VPS 6.0.1 / Air 6.0.3; graceful-skip if `python3` missing. **Runtime evidence chain:** new skill `session-operating-contract` v1.0.0 initial commit `6d0a0da6` passed pre-commit RULE 4 (grep parity) but silently dropped by gbrain; YAML-fix commit `ff860f49`; subsequent sync ingested 4 chunks; `get_page` now returns full compiled_truth. **Next-session candidate (AP-47):** extend scanner with Timeline↔AP-bullet parity check to mechanically enforce `mistake-to-skill` AP-11 v1.9 4th check — would have caught AP-45 orphan automatically. `session-operating-contract` rule 6 (failure→skill loop) demonstrated for the first time: its own v1.0.0 deployment failure drove both this AP-46 + `mistake-to-skill` v1.10 AP-12 captures. No new LESSON (RULE ZERO).
- **2026-04-18** | v2.37.0 → v2.38.0 — Session 48 W4 (7th compounding gate): absorbed **AP-45** — Pre-commit RULE 6 BLOCKS any commit that adds/modifies/renames any `*.env` file in the vault. Exclusions: `.env.example`, `.env.template`, `.env.sample` (template forms, no real values). Hook MD5 `1f02002131ee5b3efa45e869cd21754b` → `40fd8abb03354bb11482ee5d4be5921a`; 4-target parity Mac vault + Air wiki + VPS wiki + `tools/pre-commit-hook-tan-pattern.sh`. Live-tested: REJECT path blocked `test-gate.env` with full BLOCKED message + exit 1; ACCEPT path passed `test-gate.env.example` with exit 0. **Paired runtime gate:** `secrets-management` v1.3 → v1.4 AP-11 same session (W2+W3) — all `*.env` files on Mac + Air + VPS runtime paths MUST be 0600, scanned via `tools/test_secret_perms.sh` (+ self-test `tools/test_secret_perms_self.sh` 4/4 PASS). **Evidence:** W1 chmod'd 3 real drifts (Air `/Users/madia/nous-agaas/litellm/.env` at 0644 containing `LITELLM_MASTER_KEY`, VPS `/root/nous-agaas/codebase/.env` + `/root/nous-agaas/codebase/satory-frontend/.env` at 0644 with `GEMINI_API_KEY`) — the W2 scanner caught all 3 that the session-48 manual audit (P-SAFE-06) missed. **7th compounding mechanical gate** after: (1) AP-35 pre-push MD5 parity, (2) AP-36 sibling-test doctrine, (3) AP-43 pre-commit RULE 4 (SKILL version parity), (4) AP-44 pre-commit RULE 5 (SKILL MD5 citation), (5) pre-receive (VPS bare LESSON guard), (6) TaskCompleted 9-gate classifier. "Skills compound knowledge, hooks compound enforcement" series now extends to secrets integrity. Karpathy-primary: the catch itself (eye-scan missed what scanner caught in same audit session) IS the compounding artifact — mechanical gates beat human vigilance. No new LESSON (RULE ZERO).
- **2026-04-18** | v2.36.0 → v2.37.0 — Session 47 M5 (wiki-to-runtime rsync scope extension): extended `tools/wiki-to-runtime-rsync.sh` to cover `tools/` in addition to `pages/skills/`. Vault `tools/` → Air `~/nous-agaas/tools/` (majority of launchd scripts); plus per-file rsync for `capture_to_nous_pending.sh` + `nous-obsidian-sync.sh` → `~/.local/bin/` (historical plist paths from pre-nous-agaas/ era). Exclusions: `test_*.sh/py`, `pre-commit-hook-tan-pattern.sh`, `pre-push-hook-tan-pattern.sh`, `*.bak-*`, `*.v1-archived-*`, `*.pre-m4-*`, `__pycache__/`, `*.pyc`. Still NEVER --delete. Live-test: kickstart synced 326 KB tools/ + 1021 B capture-courier + 6697 B obsidian-sync to correct destinations; MD5 parity verified Air=vault. Closes session 37.6 AP-29 rsync scope gap + session 46 Phase K observed gap. No new AP; this is the mechanical FIX for AP-29's doctrine. No new LESSON (RULE ZERO).
- **2026-04-18** | v2.35.0 → v2.36.0 — Session 47 M2 (D4 FIRST lesson-absorption orphan): absorbed AP-39 — proof-of-deadness 2-mode gate. Mode A (orphan backup artifact, 4 tests: no code ref + no launchd + no cron + no active-doc procedure) validated on `com.nous.lesson-absorption.plist.bak-pre-path-fix` (744 B, 2 days old orphan from 2026-04-16 path-fix event; active sibling `com.nous.lesson-absorption.plist` was unloaded + archived in session 36.5). All 4 PASS → deleted with evidence; 5-min post-observation clean (17 launchd, 0 lesson-absorption errors, openclaw + litellm healthy). Mode B (dead-code, Mode A + last-touch > 60 days) codified for non-backup candidates. Applies to M6 14× `.bak-pre-path-fix` batch. Evidence in `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18` §5. Closes session 46-B SPEC §3's AP-39 DESIGNED-NOT-ABSORBED status with real first-D4 evidence. No new LESSON (RULE ZERO).
- **2026-04-18** | v2.34.0 → v2.35.0 — Session 47 C1 (3rd Tan compounding gate): added AP-44 — Pre-commit RULE 5 mechanically enforces SKILL.md MD5 citation ↔ file-reality parity. Scanner `tools/test_skill_md5_citations.sh` scans SKILL.md prose for 32-char hex tokens near MD5/hook/hash keyword + nearest resolvable vault path, skips Timeline and transition (X → Y) contexts. Test harness `tools/test_skill_md5_citations_self.sh` 5/5 PASS (CLEAN + DRIFT + NO-CIT + TRANSITION + AIR-ONLY-PATH). First execution caught 4 accumulated drifts on this file (lines 701/708/742/959, spanning sessions 40-46); all fixed inline before hook wire-in. Pre-commit hook MD5 `9a99bdda2f6977544e7d5f2d83e24c82` → `1f02002131ee5b3efa45e869cd21754b`; 4-target parity Mac + Air wiki + VPS wiki + `tools/pre-commit-hook-tan-pattern.sh`. Live-tested REJECT (intentional drift rejected on line 948 with readable diff report: cited `aaaa…aaaa` vs actual `1f02002131ee5b3efa45e869cd21754b`) + ACCEPT (this very Timeline entry is the ACCEPT proof — RULE 5 ran + passed). 3rd compounding gate after AP-35 pre-push + AP-43 pre-commit RULE 4 — "skills compound knowledge, hooks compound enforcement" series complete on SKILL.md integrity axis. No new LESSON (RULE ZERO).
- **2026-04-18** | v2.33.0 → v2.34.0 — Session 46 (post-deep-audit compounding gate): added AP-43 — Pre-commit RULE 4 mechanically enforces `mistake-to-skill` AP-11 (SKILL.md frontmatter/H1/Timeline parity). Hook MD5 `9a99bdda2f6977544e7d5f2d83e24c82` parity Mac vault + Air wiki + VPS wiki + `tools/pre-commit-hook-tan-pattern.sh`. Live-tested: intentional H1 drift rejected with exact message; restore accepted. Matches AP-35 pre-push precedent — Tan/Karpathy "skills compound knowledge, hooks compound enforcement". No new LESSON (RULE ZERO).
- **2026-04-18** | v2.32.0 → v2.33.0 — Session 46-B (Air tools migration thread): added AP-40 (host-specific paths in `tools/` are legitimate; do not portability-refactor during sync; Air-targeted tools reflect Air paths verbatim) + AP-41 (zero-duplicate rule for gbrain timeline entries on version-bump — always get_timeline-check before add_timeline_entry on another session's behalf). AP-40 backed by 4/4 D2-DRIFT cases (morning-brief, wiki-to-runtime-rsync, auto_checkpoint, telegram_poll — all Air-authoritative with Mac paths; vault was stale with VPS/portable paths). AP-41 backed by A1 discovery that parallel GOD_PROMPT session had already pushed 3 of 4 entries; session 46-B pushes created duplicates. Evidence: `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18`. AP-39 (proof-of-deadness 5-test gate) DESIGN complete in SPEC but NOT absorbed — no D4 deletion executed this session; defer to session 47 with real evidence. RULE ZERO upheld; zero new LESSON files.
- **2026-04-18** | v2.32.0 — Session 46 (GOD_PROMPT v1.0 completion): added AP-37 (design caps ≤ spec-named thresholds, with wrapper-bytes included; first hit was context_injector_v2 `MAX_CONTEXT_CHARS_V2=12_000` against G4 8_192 threshold — tuned to 7_500) + AP-38 (feature-flagged cutover MUST ship with deploy-time A/B probe; 1,495 v2 runs flowed through before Round-1 probe measured the gap). Evidence: `pages/audits/context-injector-ab-2026-04-18`. Closes Phase P7 Tasks 27+28 of GOD_PROMPT v1.0. No new LESSON (RULE ZERO).
- **2026-04-17** | v2.31.0 — Session 45 addendum (Madi's "are you sure?" challenge produced the compounding gate): added AP-35 (pre-push sanity hook on every vault working copy — `git push` blocked if any `~/.claude/hooks/*.sh` MD5 diverged from `tools/<name>.sh` in vault; codifies session-45 GAP 1 as mechanical enforcement, not doctrine) + AP-36 (every new server-side hook MUST ship with `tools/test_<name>.sh` exercising reject+accept paths; codifies session-45 GAP 2). Canonical pre-push MD5 `2e34402d3c57b2d879aa24fb0c5ba189` Mac+VPS+Air wiki parity. 5-scenario test harness passes. Live-tested drift-reject + drift-fix-accept. AP-35 is the first non-LESSON hook enforcing the Tan/Karpathy architecture — skills compound knowledge, hooks compound enforcement. No new LESSON (RULE ZERO).
- **2026-04-17** | v2.30.0 — Session 45: added AP-33 (TaskCompleted product-task detector over-triggers on generic action verbs; require DOMAIN-specific anchors — strip deploy|build|implement|frontend|backend from product regex, keep only VMS|ERAP|BDL|SmartBridge|ISAPI|cerebro|factory-work|police-dashboard|violation|camera as domain words) + AP-34 (parallel Claude Code session detected via <2min commit cadence — defer destructive ops on shared resources). Hook MD5 `c2eff414...` → `8cc618d9...`; Mac + Air parity verified. AP-33 amends AP-31; AP-34 is a new operational-coordination rule. No new LESSON (RULE ZERO).
- 2026-04-13 | v1.0.0 — initial (VPS era, single-node OpenClaw+LiteLLM+Langfuse on Hetzner)
- 2026-04-15 | v2.0.0 — Air migration complete
- 2026-04-15 | v2.1.0 — Added AP-7 (LiteLLM fallback), AP-8 (git pull before push). Absorbed LESSON-099, LESSON-100.
- 2026-04-15 | v2.2.0 — Added AP-9..
- 2026-04-15 | v2.3.0 — Wave 3: added AP-11 (TCC blocks bash under launchd). Absorbed LESSON-066. (session rotation daily), AP-10 (OpenRouter for international GLM-5.1). Absorbed LESSON-101. Added com.nous.session-rotate launchd to topology.

- 2026-04-15 | v2.4.0 — Wave 4: added AP-13 (watchdog LAW-014). absorbs_laws: [LAW-014].
- 2026-04-15 | v2.5.0 — Session 24: updated AP-7 with 3-tier fallback chain (Sonnet as guaranteed tail). Absorbed LESSON-104 (RouterRateLimitError when all deployments simultaneously cooled). Fixed absorbs_lessons truncation.
- 2026-04-15 | v2.6.0 — Session 25 late: added AP-14 (subprocess wrapper error-reporting discipline — no head-truncation, pattern-match errors, persist full output, catch TimeoutExpired) and AP-15 (never string-compare ISO 8601 timestamps — parse first, require ≥1s delta, guard against stale restore). Absorbed LESSON-108 and LESSON-109. auto_checkpoint.py bumped to v3 and satory_events_watcher.py confirmed at v2 on Air runtime.
- 2026-04-16 | v2.7.0 — Session 29: added AP-16 (every launchd plist MUST have EnvironmentVariables with PATH — LESSON-115). 13/17 plists patched. run_task.py fixed to use /usr/local/bin/docker. telegram_send.sh deployed. Absorbed LESSON-115.
- 2026-04-17 | v2.21.0 — Session 36: added AP-24 (TaskCompleted hook gate 8 still demanded new LESSON files post-session-35 RULE ZERO; fixed at source — gate now checks SKILL.md edit in last 24h). Also broadened vault-task classifier regex (added skill/gbrain/phase N/session-N/hook/root-cause/timeline/sync/pre-flight). Hook lives at `~/.claude/hooks/task-completed-enforce.sh`. No new LESSON file (RULE ZERO compliance).
- 2026-04-17 | v2.22.0 — Session 36.5: AP-24 extended. Found Air's `~/.claude/hooks/task-completed-enforce.sh` still had the pre-session-35 broken Gate 8 (Mac-only fix in session 36 did not propagate). Deployed fixed hook via `scp` — Air md5 `731e5c5d...` now matches Mac. Enforcement points list updated to emphasize "EVERY dev machine", not just the nearest one. Also Air launchd `com.nous.lesson-absorption` unloaded (see gbrain-ops v1.12.0 AP-25).
- 2026-04-17 | v2.23.0 — Session 37: added AP-25 (vault-task classifier regex must cover audit/monitoring vocabulary). Found during session-37 carryover: `Re-run CHECK-5 launchd 17 jobs EXIT=0` and `Re-run CHECK-6 service health` were blocked by Gates 1+2 because classifier regex didn't include `check|health|service|launchd|status|parity|monitoring|verify|probe|liveness|readiness|heartbeat|MD5|plan|spec|resolver|rsync|ingest|embed|qmd|runtime|cron`. Patched Mac hook regex (verified via dry-run). Air hook deployment pending Phase D1. No new LESSON file (RULE ZERO).
- 2026-04-17 | v2.24.0 — Session 37: added AP-26 (auto-update scripts must target the right npm prefix) and AP-27 (Air `~/nous-agaas/tools/` untracked in git — risk). AP-26 root-caused Claude CLI 2.1.71 stuck-on-Air vs 2.1.112 on Mac: `/usr/local/bin/claude` is root-owned stale, `~/.npm-global/bin/claude` is user-owned current; morning-update-apply.sh checked the root path while npm wrote to user path. Fixed script on Air + copied into vault `tools/morning-update-apply.sh` for tracking. AP-27 deferred to session 38. No new LESSON file (RULE ZERO).
- 2026-04-17 | v2.25.0 — Session 37: added AP-28 Confusion Protocol (gstack v0.18.0.0 adoption). Service-host / port-binding / git-tracked-location / deploy-path / hook-placement forks must ASK before choosing. Prevents cross-machine drift and policy contradictions. No new LESSON (RULE ZERO).
- 2026-04-17 | v2.26.0 — Session 37.6 (Telegram-flap triage): added AP-29. Root-caused the 23:47/00:03 glm-4.5-flash Telegram noise to wiki-to-runtime-rsync scope gap (`WatchPaths` only `pages/skills/`, NOT `wiki/tools/`). Session-35 `light-probe.sh` fix sat in vault 18h. Also surfaced AP-27 drift (3 files: wiki-to-runtime-rsync.sh, telegram_poll.py, morning-brief.sh have Air-newer content not in vault — direct rsync would downgrade live bot). Fix deferred to session 38 (needs careful backflow first). Detection one-liner included. No new LESSON (RULE ZERO).
- 2026-04-17 | v2.27.0 — Session 39 (atomic audit): added AP-30 (parallel-agent concurrent write race). Mac + VPS both wrote AP-29 to infrastructure SKILL.md within 23s of each other from the same parent; `wiki_to_bare.sh`'s `merge -X theirs` salvaged via byte-identity (same-intent absorptions), but would silently LOSE a divergent rule. Prevention: pre-edit `git fetch && git log --since='30 min ago' -- pages/skills/`; single-writer-per-session convention for high-frequency skills. Detection + verification one-liners included. No new LESSON (RULE ZERO).
- 2026-04-17 | v2.29.0 — Session 43 (deep audit): added AP-32 — Pre-commit RULE-ZERO hook had a rename-bypass: `--diff-filter=A` only catches direct adds; renames from off-canonical LESSON paths into `pages/lessons/individual/` slipped through (LESSON-080 was migrated this way 2026-04-17 14:01:53). Patched to also catch `--diff-filter=RC` whose destination matches canonical path AND source is OUTSIDE it. Renames WITHIN canonical dir still allowed (slug normalization). Hook MD5 `40aeeae1...` → `42d22a98...` synced 3-way (Mac/VPS/Air). Live tested: direct-add reject ✅ + rename-bypass reject ✅. LESSON-080 kept (pre-RULE-ZERO content, legitimate historical migration). No new LESSON (RULE ZERO).
- 2026-04-17 | v2.28.0 — Session 40 (atomic audit round 2): added AP-31 (TaskCompleted classifier regex fails on letter-enumerated phases). Session 40 task "Phase A: Mandatory session gates" fell through to product-task default, demanded bogus REQ-xxx. Root cause: `phase\s+[0-9]` required a DIGIT; missing operational vocab `gate|mandatory|atomic|symlink|rule.zero|tan.pattern|karpathy`. Patched regex to `phase\s+[0-9A-Z]` + added 8 vault vocab terms. Mac hook MD5 `c2eff41461bd5d06d712189889a8b986` scp'd to Air; vault backup at `tools/task-completed-enforce.sh`. Amends AP-25 (new rule: regex tokens must accept both digits and letters in identifier positions). No new LESSON (RULE ZERO).

- 2026-04-16 | v2.9.0 absorbed LESSON-034/061/106/116 (session 32 triage). Previously absorbed LESSON-088/090/091/092/097/101/104/108 confirmed present.
- 2026-04-16 | v2.17.0 — Session 33 (Claude Code audit): added AP-21 (stale branch tracking after rename causes intermittent rebase errors). Absorbed LESSON-127. Cleaned `branch.master` config on Air wiki. Fixed MEMORY.md 5 stale skill versions.
- 2026-04-16 | v2.19.0 — Session 34 (atomic audit): added AP-22 (gbrain autopilot creates junk concept pages from broken wikilinks). 11 junk files deleted, 17 gbrain orphan pages cleaned, pre-commit hook false positive fixed. Absorbed LESSON-129.
- 2026-04-16 | v2.18.0 — Session 33 (smart router): Opus 4.6 as brain for Telegram (/ask → --model opus via run_task.py). GLM-5.1 stays workhorse for auto-tasks. LiteLLM 5-model config: opus→grok→glm-5.1→glm-4.5-flash→sonnet. Budget raised to $30/day. Verified: OPUS_BRAIN_OK + GLM_WORKHORSE_OK.
- 2026-04-16 | v2.20.0 — Session 35 Garry-Tan enforcement audit: added AP-23 (known-flapping external model endpoints must NOT page the operator). `tools/light-probe.sh` source updated on Mac wiki: `KNOWN_FLAPPING_MODELS="zai/glm-4.5-flash"`, `is_only_known_flapping()` helper (symmetric-diff ⊆ known = suppress), per-key debounce (4h model-health / 15min infra), suppressed transitions logged for audit. Deployment to Air pending Tailscale re-auth (one-liner in AP-23). No LESSON file written — evidence lives in this AP + gbrain timeline on infrastructure page.

## See also

- [[nous-gpu]] — new RTX 5070 compute host (2026-04-20, Assyl/Alex provisioned); future launchd monitoring gate `com.nous.nous-gpu-health` candidate
- [[LESSON-086-polling-dedup-save-state-before-slow-handler]]
- [[LESSON-090-litellm-native-vs-docker-macos]]
- [[LESSON-091-docker-image-transfer-scp-not-pipe]]
- [[LESSON-092-openclaw-config-path-docker]]
- [[LESSON-094-docker-wiki-mount-node-user-traversal]]
- [[LESSON-097-v2-schedule-and-settings-hook-fix]]
- [[LESSON-099-zai-balance-exhausted-litellm-fallback]]
- [[LESSON-100-write-back-pull-rebase-before-push]]
- [[LESSON-108-subprocess-error-reporting-stderr-head-vs-tail]]
- [[LESSON-109-iso-timestamp-string-compare-false-positive]]
- [[air-migration-plan-2026-04-14]]
- `skills/command-center/SKILL.md` — for Telegram-specific infra
- `skills/_gbrain/RESOLVER.md` — skill dispatcher

### LESSON-119 absorption (2026-04-16, session 32 audit)

- **LESSON-119 Rule 1:** LiteLLM fallback chain MUST end with a guaranteed-alive model. As of 2026-04-16: glm-5.1 → glm-4.5-flash → grok-reasoning. Dead models (expired API keys) must be removed from config, not left as phantom entries.
- **LESSON-119 Rule 2:** After any LiteLLM config change, verify `/health` endpoint shows 0 unhealthy. All 3 models must show as healthy_endpoints.
- **LESSON-119 Rule 3:** A git pre-commit hook on all wiki repos enforces AMD-005 skill-first. Any commit with a LESSON file MUST also contain a SKILL.md modification. Hook installed at `.git/hooks/pre-commit` on VPS wiki, Air wiki, Mac vault.
- **LESSON-119 Rule 4:** When diagnosing "container mount stale" reports, use `docker exec ls | grep` not glob expansion — zsh globs fail inside bash-default containers.

### LESSON-120 absorption (2026-04-16, session 32 rsync audit)

- **LESSON-120 Rule 1:** The wiki-to-runtime-rsync.sh script MUST sync _gbrain/ too (additive, no --delete). Excluding _gbrain/ causes the runtime RESOLVER and gbrain skills to go stale. The original session 24 lesson was about --delete wiping _gbrain — the fix is no-delete sync, NOT no sync at all.

### LESSON-126 absorption (2026-04-16, session 32 model ID fix — renumbered from collision with LESSON-120)

- **LESSON-126 Rule 1:** LiteLLM config should have 4-tier chain: glm-5.1 → glm-4.5-flash → grok-reasoning → sonnet (last resort). Grok is the guaranteed tail. Sonnet is backup for when its API key is valid.

### LESSON-121 absorption (2026-04-16, session 32 key audit)

- **LESSON-121 Rule 1:** Anthropic model IDs do NOT use date suffixes. Correct: `claude-sonnet-4-6`. Wrong: `claude-sonnet-4-6-20250514`. Always list models via `GET /v1/models` before configuring.
- **LESSON-121 Rule 2:** API keys MUST be identical across ALL .env files (Air litellm, Air root, VPS root, VPS /opt). One canonical source: `~/nous-agaas/litellm/.env`. After any key change, propagate to all 4 .env locations.
- **LESSON-121 Rule 3:** "not_found_error" from Anthropic means KEY IS VALID but model ID is wrong. "authentication_error" means KEY IS DEAD. These are different errors — read the error message before declaring the key dead.

### LESSON-122 absorption (2026-04-16, session 32 monitoring gap)

- **LESSON-122 Rule 1:** light-probe.sh must check per-model health via LiteLLM `/health` JSON, not just HTTP 200 status. The `/health` endpoint returns 200 even with dead models. Check `unhealthy_count` and `unhealthy_endpoints[].model` to detect dead models.
- **LESSON-122 Rule 2:** Every state-change alert must include the specific model name that died (e.g., "dead_models: anthropic/claude-sonnet-4-6-20250514 → none"), not just a count.
- **LESSON-122 Rule 3 (Garry Tan resolver principle):** Monitoring is a resolver problem. The probe monitors 5 systems but monitored the WRONG thing about LiteLLM (process alive vs all models healthy). When adding a new system to monitor, ask: "what failure mode would be invisible to a boolean alive/dead check?"

- **2026-04-16** | v2.13.0 — fixed 2 lesson files missing status (LESSON-085, LESSON-118-litellm) during final audit
- **2026-04-30** | v2.68.0 — added AP-75 (canary scripts under `set -u` must not use undeclared positional args; alert path must precede diagnostic write so future bugs cannot silence alerts). Caught when first-run weekly_library_canary.sh on Air died at `$3` typo BEFORE Telegram alert fired, silently swallowing a real broken-wikilink regression. Substrate audited me; canary validated itself by exposing a script bug + a real regression in the same shot.
- **2026-04-30** | v2.69.0 — frontmatter `description:` cleanup: split 2371-char accumulated session-summary blob into a one-sentence `description:` + structured `recent_changes:` YAML array (one row per AP add, fields: session/date, ap, summary). 20 entries migrated. No content lost; future agents can grep `recent_changes:` instead of parsing prose. Triggered by s107 carryover #3 (description bloat).

### AP-75 — Canary scripts must alert BEFORE diagnostic write, and must be safe under `set -u` (session 106, 2026-04-30)

**Pattern:** `weekly_library_canary.sh` on Air launchd died with `$3: unbound variable` (typo: meant literal `3`) inside a heredoc that was building an HANDOFF-AUTO file. Because alert-send (`bash tools/tg_send.sh "$ALERT"`) was placed AFTER the heredoc write, the script crashed before reaching the alert and the operator received NO Telegram on a real RED. The canary swallowed its own first regression.

**Root cause:**
1. `set -u` plus an unintentional `$N` reference in a multi-line `echo` chain → script terminates BEFORE side-effect statements that come later.
2. Operator-facing alerts placed AFTER diagnostic-build steps inherit the failure surface of those steps.

**Rule:**
- In any monitoring/alerting wrapper script, the **alert-send call must precede** any non-trivial diagnostic file generation. Diagnostic write becomes a follow-up; if it fails, you still got the alert.
- Under `set -u`, never use bare `$N` for a positional arg you don't actually pass; use literal numerals or guard with `${N:-}`.
- After a script change, **dry-run with `bash -x`** at least once and verify the alert path actually reaches `tg_send.sh` (or equivalent), not just that scanners ran.

**How to apply:**
- Order in `weekly_library_canary.sh`: classify red → assemble `$ALERT` text → `bash tg_send.sh "$ALERT"` → THEN write handoff → secondary `bash tg_send.sh "Handoff: $HANDOFF"` follow-up.
- For new launchd canaries, run them at least twice manually (`launchctl kickstart -p gui/$UID/$LABEL`) — once with green substrate (verify success-path Telegram) and once with synthetically-red substrate (verify failure-path Telegram).

**Detection:** `bash -x tools/<canary>.sh` — line-by-line trace surfaces unbound-var deaths immediately. CI gate idea: grep for `bash tg_send.sh` and `set -u` in any `tools/*canary*` or `tools/*alert*` script; assert the `tg_send.sh` line appears before the `cat <<'EOF' > "$HANDOFF"` line.

**Compounding artifact:** `tools/weekly_library_canary.sh` v2 (HEAD `2e246d70`) — alert-first ordering codified.

**Cross-ref:** `infrastructure` AP-75 (this rule); `agent-quality` AP-7 (silent success on critical paths — symmetric failure mode).

### AP-76 — Docker reports container "healthy" while gateway HTTP server is hung (session s2148, 2026-04-30)

**Pattern:** OpenClaw `docker ps` shows `Up 36 hours (healthy)` but `curl localhost:18789/health` hangs (HTTP 000 with 5+ second timeout). Container is UP at the kernel-level (PID 1 alive, healthcheck still passing) but the inner HTTP gateway is unresponsive — port-listener present, connections accumulate in `CLOSE_WAIT` / `FIN_WAIT_2`. Docker healthcheck is too lenient (likely a TCP-connect, not a 200-response check) so it never alerts.

**Symptoms (in order):**
1. Telegram `/ask` queries time-out: `⏳ Routing to OpenClaw…` followed by silence.
2. Substrate watchdog state-change: `port18789: up → down` (only because the watchdog is HTTP-based).
3. `docker logs openclaw` shows `[agent/embedded] incomplete turn detected ... stopReason=stop payloads=0` 30+ minutes earlier — the leading indicator. Worker model returned empty payload, gateway didn't recover the work-loop.
4. Cost telemetry `$0.00` on subsequent /ask attempts (request never reached LLM).

**Root cause hypotheses (probable):**
- Worker model timeout/empty-payload deadlock in `agent/embedded` runtime.
- Connection pool exhaustion under load (CLOSE_WAIT pile-up).
- Missing recovery path on `incomplete turn` — gateway should self-restart the affected lane, not hang the whole bus.

**Recovery (proven 2026-04-30 by session s2148):**
```bash
ssh air 'docker restart openclaw'
sleep 90   # boot + plugin reload + heartbeat takes 60-90s
ssh air 'curl -s -m 5 -o /dev/null -w "%{http_code}\n" http://localhost:18789/health'
# expect 200; if not, check `docker logs --tail 30 openclaw`
```

Boot order observed:
- `[gateway] loading configuration… resolving authentication… starting...` (~15s)
- `[gateway] agent model: litellm/deepseek-v4-flash` (default agent loads)
- `[gateway] ready (5 plugins; 24.3s)`
- `[gateway] starting HTTP server...`
- `[health-monitor] started (interval: 300s, startup-grace: 60s)`
- `[heartbeat] started` (~75s — full ready)

**Rule:** when `port18789: up → down` fires AND `docker ps` still shows healthy, default action is `docker restart openclaw`. Reversible (~90s downtime, no data loss; sessions live in `~/.openclaw` volume). Watch the next 15min for recurrence — if hangs again within 1h, walk the deeper hypothesis tree (worker model, pool exhaustion, plugin crash).

**Detection (proactive, queued for next session):** the substrate watchdog's `port18789` check is HTTP-based and already fires; sufficient. Optional improvement: add a `[agent/embedded] incomplete turn` log-grep alert as an EARLIER indicator (would have caught this hang at 05:14 instead of at 22:15).

**Why ordering matters:** the `incomplete turn` errors at 05:14 + 16:58 today were the silent leading indicator. The gateway didn't escalate them, didn't recover its work-loop, and 5 hours of degradation later hung completely. **Self-restart on N consecutive incomplete-turn events** is the proper engineering fix; in the meantime the manual restart playbook is the gap.

**Compounding artifact:** this AP-76 + Madi's tg_send.sh recovery confirmation msg_id=1128 (architecture-on-spec assertion grounded against live config).

**Cross-ref:** `infrastructure` AP-60 (restart proof must respect Docker healthcheck interval — use HTTP 200 not just `up`); `infrastructure` AP-75 (alert-first ordering — the watchdog DID alert first this time, doctrine validated); `agent-quality` AP-10 (don't declare "ready" based on mechanism tests alone — `docker ps healthy` is a mechanism test); `ceo-hierarchy` (the routing chain that surfaced the failure to Madi).

### AP-77 — Launchd poller health must treat a live PID as healthy even if last-exit is stale (2026-05-05)

**Pattern:** after `launchctl bootout` / `bootstrap` / `kickstart` on Air, `launchctl list` can report a live job as `73732 -15 com.nous.telegram-poll`: the first field is the current PID, while the second field is the previous terminating signal/status. A naive parser that treats any negative second field as red will false-alert immediately after a successful restart.

**Rule:** parse launchd health in this order:
1. Label missing = red.
2. First field is a numeric PID = green, regardless of the second field.
3. First field is `-` and second field is `0` = green for clean `StartInterval` jobs that exit between scheduled runs.
4. First field is `-` and second field is nonzero = red.

**Regression:** `tools/tests/test_air_watchdog.py::test_running_poller_pid_overrides_stale_negative_exit_status`.

**Cross-ref:** AP-16 (launchd PATH), AP-60 (restart proof must respect real health cadence), AP-75 (alert path must fire only on true red).

### AP-78 — Caddy Tailscale-only listeners require explicit `bind`, not just an IP-literal site address (2026-05-05)

**Pattern:** Caddy can validate an IP-literal site address like `http://100.99.24.104:3301` but still open the listener as `*:3301`. For a localhost-bound Docker service such as Langfuse (`127.0.0.1:3001`), this turns a Tailscale-only intent into a broader listener unless the bind is checked mechanically.

**Rule:** for Tailscale-only Caddy exposure of localhost services:
1. Use a separate port if Docker already owns localhost on the service port.
2. Put `bind <tailscale-ip>` inside the site block.
3. Verify with `ss -ltnp | grep <port>` that the listener is `<tailscale-ip>:<port>`, not `*:<port>`.
4. Verify from the intended peer host over Tailscale, then verify the underlying local service still works.

**Known-good Slice D form:**
```caddy
http://:3301 {
	bind 100.99.24.104
	reverse_proxy 127.0.0.1:3001
}
```

**Cross-ref:** AP-60 (health proof must inspect the real endpoint), AP-75 (alert/monitoring paths should not silently broaden failure surface).

### AP-79 — Restart drills need first-seen failure state and `ssh -n` in stdin-driven harnesses (2026-05-05)

**Pattern:** launchd can record a fresh `-15` or `-9` exit without touching the job's stdout/stderr logs. A restart guard that uses log mtime as "failure recency" will misclassify a just-killed process as stale and skip the restart. Separately, an inner `ssh` call without `-n` can consume the parent script's stdin when the guard is invoked from a heredoc or pipeline, silently skipping the rest of the drill.

**Rule:**
1. For launchd restart recency, maintain guard-owned first-seen failure state (`label + exit detail -> timestamp`) and clear it on OK/restart. Do not infer recency from log mtime.
2. Any nested SSH call in a script that can be invoked from stdin must use `ssh -n`.
3. The proof drill must assert the post-restart PID, not only that the wrapper printed "restarted".

**Cross-ref:** AP-77 (live PID overrides stale exit field), AP-75 (alert/restart scripts must prove the intended side effect).

### AP-80 — Python HTTPS probes need `certifi` CA fallback before declaring URL checks broken (2026-05-05)

**Pattern:** macOS framework Python can have an empty or stale OpenSSL CA path. A valid HTTPS URL may pass `curl -I` while `urllib.request.urlopen(..., method="HEAD")` raises `CERTIFICATE_VERIFY_FAILED`. Treating that as a broken citation creates a false red and hides the real dependency: the verifier's trust store.

**Rule:**
1. For Python HTTPS probes, try the default verified TLS context first.
2. On `ssl.SSLCertVerificationError`, retry with `certifi.where()` when `certifi` is installed.
3. Do not disable certificate verification to make the check green.
4. Keep the URL-status contract coarse (`200`, `2xx`, `3xx`, `4xx`, `5xx`, `invalid`, `error`) so operator alerts do not overfit transient network details.

**Regression:** `tools/tests/test_citation_verifier.py::test_verify_url_retries_with_certifi_on_local_ca_failure`.

**Cross-ref:** AP-75 (alert paths must distinguish real red from probe drift), AP-78 (network exposure checks must verify the actual listener/path).

### AP-81 — Cross-host watchdogs must separate target death from observer SSH transport uncertainty (2026-05-08)

**Pattern:** a VPS watchdog can have two independent views of Air: a primary target health endpoint and a secondary SSH inspection path. If HTTP health is green but SSH times out before launchd can be inspected, the evidence proves "observer transport uncertain", not "Air poller dead". Paging a red alert from that combination creates false alarms while the factory is live.

**Rule:** cross-host watchdogs must classify checks in this order:
1. Primary target health failure = red.
2. Primary target health green + successful secondary inspection proving label missing or nonzero exit = red.
3. Primary target health green + secondary SSH transport error or timeout = degraded/unknown, not dead.
4. Preserve the raw SSH error in state/logs so repeated transport drift remains auditable without paging as service death.

**Regression:** `tools/tests/test_air_watchdog.py::test_http_green_poller_ssh_timeout_is_unknown_not_dead`.

**Cross-ref:** AP-75 (alert path must precede diagnostic write, but only for true red), AP-77 (launchd parser must distinguish real job state from stale fields), AP-80 (probe drift must not masquerade as target failure).

### AP-82 — Long-running pollers must contain transient upstream HTTP failures instead of crash-looping (2026-05-08)

**Pattern:** external APIs can return transient `429`/`5xx`/transport failures. If a long-running launchd poller lets `requests.RequestException` escape the main loop, launchd `KeepAlive` can restart it, but the service still crash-loops, loses in-process cadence, and fills stderr with stack traces for a condition that should be handled as degraded upstream availability.

**Rule:**
1. Keep one-shot/manual commands strict: failed upstream requests should still exit nonzero for operator proof.
2. In `--loop`/daemon mode, catch `requests.RequestException` inside the poll loop.
3. Emit structured error JSON with the exception class and bounded detail.
4. Retry after a bounded error backoff without writing cursors/tokens or pretending a successful poll occurred.

**Regression:** `tools/tests/test_todoist_sync.py::test_loop_poll_cycle_contains_transient_todoist_http_error`.

**Cross-ref:** AP-75 (alert/state ordering), AP-79 (restart guards need first-seen failure state), AP-81 (separate target failure from observer/transport uncertainty).

### AP-83 — Todoist REST v2 410 means migrate operator mutations to unified API v1 (2026-05-09)

**Pattern:** Todoist REST v2 endpoints can now return HTTP `410 Gone` with the body `This endpoint is deprecated` and an instruction to use `/api/v1/` endpoints. Treat that as platform drift, not as a missing task or bad token.

**Rule:**
1. For Todoist operator mutations, use unified API v1 endpoints first:
   - create/list/filter tasks: `https://api.todoist.com/api/v1/tasks...`
   - close task: `POST https://api.todoist.com/api/v1/tasks/{task_id}/close`
   - comments: `POST https://api.todoist.com/api/v1/comments`
2. If a legacy REST v2 probe returns `410`, stop using REST v2 for that flow and re-run through API v1 before declaring the task missing.
3. Expect v1 success codes to differ from REST v2. Example: close can return `204` empty body while follow-up `GET /api/v1/tasks/{task_id}` shows `checked: true` and `completed_at`.
4. Follow v1 cursor pagination for list/filter endpoints; do not regress to single-page counts.

**Verification:** Satory Mergen ERAP lossless task `6gc5j8qM6X5hgGgH` returned `410` on REST v2; API v1 comment returned `200`, close returned `204`, and follow-up `GET /api/v1/tasks/{task_id}` returned `checked: true` with `completed_at: 2026-05-09T07:24:23.873495Z`.

**Cross-ref:** audit AP-26 (Todoist pagination), infrastructure AP-82 (upstream API failures stay contained in pollers), Todoist official API v1 docs (`/api/v1/tasks/{task_id}/close`, `/api/v1/comments`, cursor pagination).

### AP-84 — Todoist board writes must include section_id, not project_id only (2026-05-11)

**Pattern:** A Todoist task can be correctly assigned to the shared project but still appear outside the intended board section if the writer passes only `project_id`. For board-view projects, section placement is a separate write requirement.

**Rule:**
1. When writing to a Todoist board section, always pass both `project_id` and `section_id`.
2. For Satory KEONA work, the contract is:
   - project: `Satory VKO Factory` (`6gJ5j8PRVVCWpgCq`)
   - section: `🤝Keona Partnership` (`6gXCgHcrqr2HvRqH`)
   - labels: `keona`, `spectra`, `проект:KEONA`
3. After bulk writes or moves, run a readback that checks semantic scope and `section_id`, including same-day completed tasks when the user is auditing what happened today.
4. If a completed task belongs in the wrong section, move it by id without reopening it; preserve completion state unless the user explicitly asks to reopen.
5. Add a task comment for business-critical proof events, such as Gmail draft/sent ids, so humans and agents can audit from Todoist without searching Gmail first.

**Verification:** KEONA repair moved `46` active/today-completed tasks into `🤝Keona Partnership`, applied `50` label updates, added `4` comments, and readback returned `wrong_section_count = 0`. Madi's KO/RU email send was recorded with Gmail sent id `19e16d3787adeffe`.

**Cross-ref:** infrastructure AP-83 (Todoist v1 mutation path), audit AP-26 (Todoist pagination), gbrain-ops AP-40 (Todoist owns business tasks; Notion owns docs; Obsidian/gbrain own durable memory).

### AP-85 — External routines need a safe GitHub mirror after checkpoints (2026-05-12)

**Pattern:** Claude Code routines and other external automation may clone GitHub, but live Nous state is written first to Air/VPS. If GitHub is only updated by incidental Mac/VPS pushes, routine inputs can lag behind HANDOFF-AUTO, task-results, audits, and proof artifacts.

**Rule:**
1. Scheduled checkpoint writers that produce routine inputs must mirror immediately after a successful HANDOFF write, not wait for unrelated auto-sync.
2. Never use a blind `git push github main` as the whole fix. GitHub may contain routine-authored commits that are ahead of Air/VPS; fetch and rebase on `github/main` first.
3. Mirror order for auto-checkpoint is: clean-worktree check -> `fetch origin main` -> `pull --rebase --autostash origin main` -> if `github` exists, `fetch github main` -> rebase on `github/main` when needed -> push `origin main` -> push `github main`.
4. Missing `github` remote is yellow, not a checkpoint failure: push `origin` and log the missing mirror. The host operator must configure the remote out-of-band; do not commit OAuth tokens, PATs, or credential URLs into the vault.
5. Rebase conflicts or push failures must notify Telegram and skip the mirror rather than force-pushing over routine output.
6. Git output sent to logs or Telegram must sanitize embedded GitHub credentials.

**Verification:** `tools/test_auto_checkpoint.py` has regressions for (a) missing GitHub remote still pushing `origin`, and (b) GitHub-ahead state rebasing on `github/main` before pushing either remote.

**Cross-ref:** AP-31 (auto-checkpoint orchestrator owns HANDOFF writes), session-operating-contract DONE protocol, gbrain-ops AP-86 (readback warnings can be yellow when current sync/readback is green).

### AP-86 — Verification installs must not commit Python package metadata (2026-05-12)

**Pattern:** Running `pip install -e .` inside a vault subproject can generate `*.egg-info/` directories. If auto-sync fires before cleanup and `.gitignore` does not cover that package-metadata class, generated files can be committed alongside real evidence artifacts.

**Rule:**
1. Prefer temp venvs outside the vault for verification installs, e.g. `/tmp/<project>-verify`.
2. Treat `*.egg-info/` as generated metadata like `__pycache__/` and `*.pyc`; it must not be tracked.
3. If auto-sync already committed `*.egg-info/`, remove it with `git rm -r <path>.egg-info`, add/verify `.gitignore`, and preserve real proof artifacts such as E2E JSON separately.
4. Before pushing a verification cleanup, run `git ls-files '*egg-info*'` and expect zero rows.

**Verification:** ERAP audit cleanup removed tracked `projects/erap-intake/erap_intake.egg-info/*`, added `.gitignore` rules for `*.egg-info/` and `**/*.egg-info/`, and final readback returned `egg_info_tracked=0` on Mac and Air.

**Cross-ref:** AP-51 (auto-sync can race authorial work), AP-56 (repo source-of-truth discipline), session-operating-contract Rule 19 (agent commits own substantive work; auto-sync is dumb backstop).

### AP-87 — GitHub mirror green requires exact live HEAD, not only reachable remote (2026-05-13)

**Pattern:** `tools/factory_no_drift_probe.sh` reported `github_mirror=GREEN` because GitHub was reachable and remotes were tokenless, while GitHub was actually behind the live Mac/Air/VPS wiki HEAD. External routines that clone GitHub then read stale operating memory even though the factory probe says green.

**Rule:**
1. A GitHub mirror probe is green only when the mirror is reachable, tokenless, and exactly matches the expected live wiki HEAD.
2. Mac/Air auto-sync writers must fetch `github/main` and rebase before pushing GitHub. Never force-push over cloud routine output.
3. Control-plane writeback must also fetch/rebase GitHub before pushing `origin` and `github`.
4. If GitHub is stale, report red or not_done immediately; do not hide it under "reachable mirror".
5. Regression tests must cover both the exact-HEAD probe and the rebase-before-push writer contract.

**Verification:** `tools/factory_no_drift_probe.sh --quiet` now reports `github_mirror=GREEN` only with `expected=<HEAD> github=<HEAD> air_github=<HEAD>`. Regression tests: `tools/tests/test_factory_no_drift_probe_static.py` and `tools/tests/test_github_mirror_writers_static.py`.

**Cross-ref:** AP-85 (safe GitHub mirror after checkpoints), control-plane-sync AP-3 (generated commits must not burn GPT review quota), session-coordination AP-24 (auto-sync must fail loud before propagating bad state).

### AP-88 — Hermes is the supervisor layer; OpenClaw remains the worker factory (2026-05-13)

**Pattern:** "Add Hermes" can mean two different things: resurrect the deprecated Nous Research Hermes Agent framework, or add a durable supervisor/queue guard named Hermes around the existing factory. The former already failed as speculative deployment (`com.nous.hermes` exit-code=1, deprecated 2026-04-18). The latter is useful now because the live risks are missed sync cycles, OpenClaw downtime, repeated Todoist/Notion failures, GitHub failure noise, and stale model bakeoffs.

**Rule:**
1. Do not revive the deprecated Hermes Agent framework unless an 8h+ factory run proves OpenClaw + Goal Mode + control-plane loops cannot handle the workload.
2. Keep OpenClaw as the actual worker factory and Telegram/Grok/OpenClaw path.
3. Use `tools/hermes_factory_watchdog.py` as the Hermes supervisor layer:
   - kick `com.nous.control-plane-sync` when the control-plane cycle is stale;
   - restart OpenClaw and notify Telegram when health is red;
   - convert repeated Todoist/Notion sync failures into factory slices;
   - classify GitHub Actions failure noise into incident audits;
   - force model bakeoff when the weekly quality check is stale.
4. Install it through `tools/launchd/com.nous.hermes-factory-watchdog.plist`; do not reuse the old `com.nous.hermes` label.

**Verification:** `tools/tests/test_hermes_factory_watchdog.py` covers stale control-plane kick, repeated sync failure slice creation, and no restart on green OpenClaw.

**Cross-ref:** `pages/entities/hermes-agent.md` deprecated framework record, `pages/entities/hermes-factory-watchdog.md` active supervisor record, control-plane-sync skill.

### AP-89 — Watchdogs must dedupe already-recorded incidents (2026-05-13)

**Pattern:** Hermes correctly classified old GitHub Actions failure emails/runs and created an incident audit, but then kept reporting `not_done` on every probe because the same historical failure runs were still visible in `gh run list`.

**Rule:**
1. First sighting of a real failure creates an incident audit and returns `not_done`.
2. Later sightings of the same failure return `done` if the incident audit already exists.
3. A watchdog should stay yellow only for new unrecorded failures, stale cycles, or currently broken runtime checks.
4. This preserves signal: "known incident recorded" is not the same as "new active breakage."

**Verification:** `tools/tests/test_hermes_factory_watchdog.py::test_known_github_failure_incident_dedupes_to_done`.

### AP-90 — Watchdog status pages must rewrite when yellow clears to green (2026-05-13)

**Pattern:** Hermes deduped an already-recorded GitHub incident and the JSONL run became `overall_status=done`, but the vault status page still showed the previous `not_done` run because the watchdog skipped done-status rewrites to avoid commit noise.

**Rule:**
1. It is valid to skip repeated all-green status page writes to avoid commit churn.
2. It is not valid to skip the first green write after a yellow/red status page.
3. Status page write rule: write on first run, write on active `not_done`/`blocked`, and write when a done run clears an existing non-done page.

**Verification:** `tools/tests/test_hermes_factory_watchdog.py::test_status_page_rewrites_when_done_clears_old_yellow`.

### AP-91 — Tracked launchd script fixes must be deployed to the live ProgramArguments target (2026-05-13)

**Pattern:** `tools/nous-obsidian-sync.sh` was patched to mirror auto-sync commits to GitHub, but Mac launchd still ran `/Users/madia/.local/bin/nous-obsidian-sync.sh`, a stale deployed copy without the GitHub mirror block. Result: Mac/Air/VPS converged at `aa178ca7`, while GitHub remained at `7ba86317`.

**Rule:**
1. When patching a script that has a launchd `ProgramArguments` copy outside the repo, inspect the plist target before claiming the fix is live.
2. Deploy the tracked script to that target with mode preserved, then verify byte identity.
3. For Mac Obsidian sync specifically:
   ```bash
   install -m 755 tools/nous-obsidian-sync.sh /Users/madia/.local/bin/nous-obsidian-sync.sh
   shasum -a 256 tools/nous-obsidian-sync.sh /Users/madia/.local/bin/nous-obsidian-sync.sh
   ```
4. The GitHub mirror check is not green until the live launchd target and tracked script match.

**Detector:** `tools/tests/test_github_mirror_writers_static.py::test_live_mac_obsidian_sync_wrapper_matches_tracked_script_when_present`.

### AP-92 — Update checks must scan the actual installed skill roots (2026-05-16)

**Pattern:** The daily morning updater reported no GStack signal even though the live GStack install at `/Users/madia/.agents/skills/gstack` returned `UPGRADE_AVAILABLE 1.26.0.0 1.39.1.0`. The script only checked `.Codex/skills/gstack` and `.codex/skills/gstack`, so the active install root was invisible.

**Rule:**
1. Update detectors must inspect the real install roots used by the current runtime, not only historical defaults.
2. For GStack, scan in this order: `$HOME/.agents/skills/gstack/bin`, `$HOME/.Codex/skills/gstack/bin`, `$HOME/.codex/skills/gstack/bin`, then `$HOME/.claude/skills/gstack/bin`.
3. If a checker path is found, log the exact checker path before logging the signal.
4. Do not auto-reset a dirty skillpack repo; report the upgrade signal and preserve local modifications unless a dedicated upgrade workflow has cleanly stashed/restored them.

**Verification:** `bash -n tools/morning-update-apply.sh`; live manual check found the `.agents` GStack install dirty, so upgrade execution remains a separate safe-workflow task.

### AP-93 — LiteLLM direct null-content is a model failure, not a successful task (2026-05-18)

**Pattern:** Auto-checkpoint can fail even when LiteLLM returns HTTP 200 if the OpenAI-compatible response contains `choices[0].message.content = null`. Treating that as success lets `run_task.py` crash later in token accounting (`len(text)`), so the alert shows a Python `TypeError` instead of the provider/model boundary failure.

**Rule:**
1. Direct LiteLLM callers must validate that assistant content is a non-empty string before returning it.
2. A null or empty direct response is a model failure and must be recorded in `ModelEscalator`.
3. For automatic, non-explicit direct routes, retry the escalated model in the same run once; do not wait for the next cron interval.
4. For explicit `--model` calls, do not silently change models. Fail loudly with the exact model in the error.
5. Checkpoint wrappers should surface the model-boundary error, not a downstream accounting traceback.

**Verification:** `tools/test_run_task_resilient.py` covers null-content rejection, same-run Flash -> Pro escalation, and no retry for explicit direct model calls.

No new LESSON (RULE ZERO).

### AP-95 — Optional Nous-GPU collector degradation skips cleanly unless GPU is required (2026-05-21)

**Pattern:** The Air 03:00 substrate probe stayed YELLOW because `com.nous.nous-gpu-collector-health` returned red while `nous-gpu` was externally offline in Tailscale (`100.70.222.21` last seen days ago). Core factory surfaces were green, and no GPU-bound workload was active. Treating optional, externally powered-off hardware as a substrate failure makes the daily gate noisy and trains agents to hide or over-fix the wrong thing.

**Rule:**
1. GPU-dependent runs set `NOUS_GPU_REQUIRED=1`; in that mode any collector reachability/container/pcap/delta failure remains a hard failure.
2. Default runs treat Nous-GPU as an optional acceleration lane. If Tailscale, SSH, container, pcap freshness, or pcap growth fails, `tools/nous_gpu_collector_health.sh` logs `SKIP optional Nous-GPU collector degraded ...` and exits 0.
3. The log must include the exact degraded reason and the `NOUS_GPU_REQUIRED=1` escalation hint.
4. Never call this a collector recovery. It is a policy gate: optional offline GPU no longer blocks OpenClaw/Telegram/gbrain/OpenBrain daily substrate green.
5. The entity/status page must still carry the live reachability fact, and GPU promotion requires a fresh live collector proof.

**Verification:** `bash tools/test_nous_gpu_collector_health_rotation.sh` now covers both optional-unreachable exit 0 and required-unreachable nonzero behavior.

No new LESSON (RULE ZERO).

### AP-96 — Shared launchd wrappers must resolve the host-local vault first (2026-05-22)

**Pattern:** A tracked launchd wrapper is copied to more than one host but keeps a single hard-coded vault path. On Air, `~/.local/bin/nous-obsidian-sync.sh` still pointed at the Mac Documents clone (`/Users/madia/Documents/Projects/Nous AGaaS/Nous`) while the live factory clone is `/Users/madia/nous-agaas/wiki`. The 60s sync loop then scanned the wrong checkout, saw stale merge markers, and skipped every run even though the actual Air wiki was clean. The 5-minute `wiki-sync` path kept pushing factory commits, so closeout proof depended on waiting for quiet windows instead of a single authoritative sync loop.

**Rule:**
1. Any launchd/git wrapper deployed on both Mac and Air must resolve the host-local git vault at runtime.
2. Prefer `/Users/madia/nous-agaas/wiki` when it exists as a git repo; fall back to `/Users/madia/Documents/Projects/Nous AGaaS/Nous` for Mac interactive use.
3. Resolve the canonical VPS-bare remote by host-local name: `vps` on Mac, `origin` on Air.
4. Allow an explicit `NOUS_VAULT_OVERRIDE` for tests and emergency recovery.
5. StartInterval git wrappers need a single-flight lock; if the previous run is still active, the next run logs a skip instead of racing rebase/push.
6. A merge-marker or dirty-tree guard must print the path it is guarding or be backed by a test that proves host-local selection.
7. After editing a tracked launchd wrapper, deploy the same content to its live ProgramArguments target and run it once on the host that owns the launchd job.

**Verification:** `tools/nous-obsidian-sync.sh` now uses `resolve_nous_vault()` with `NOUS_VAULT_OVERRIDE`, Air-first path, then Mac fallback, resolves `vps` or `origin` as the canonical remote, logs `run started (vault=...)` before guard checks, and wraps the git section in a `/tmp` single-flight lock. `tools/tests/test_github_mirror_writers_static.py` asserts that host-local selection cannot regress to a Mac-only literal, a Mac-only remote name, or an unlocked StartInterval wrapper. Live Air run after deployment must show the Air wiki path followed by `OK:` or `github mirror exact`, not `skip: merge markers present` from the stale Documents checkout.

No new LESSON (RULE ZERO).

### AP-94 — Hermes WebUI canary requires authenticated factory-events proof (2026-05-19)

**Pattern:** Hermes WebUI `/health` can be green while the control-surface proof that matters for iPad/TestFlight use is still unproven. Public `/api/factory-events` may correctly return `401 Authentication required`; that is not a failure by itself. The proof is an authenticated login followed by `/api/factory-events` returning JSON with factory sources and queue status.

**Rule:**
1. Do not promote Hermes WebUI/iOS from canary based on `/health` alone.
2. A green WebUI canary gate must authenticate using the Air-side sealed WebUI env file and prove `/api/factory-events` returns `ok: true`, a `sources` list, an `events` list, and `queue_status`.
3. Treat unauthenticated `401` as expected when auth is enabled, but treat missing env password, failed login, non-JSON, missing sources, or missing queue status as red.
4. Keep Hermes Telegram/gateway disabled until bot-loop depth, dedupe, rate-limit, and kill-switch proofs exist; Hermes may observe the factory event surface before it becomes a production router.

**Verification:** `python3 -m pytest tools/tests/test_hermes_canary_gate.py -q` covers the auth-event green path and the `401`/auth failure red path. Live Air verification:

```bash
PYTHONPATH=tools python3 tools/hermes_canary_gate.py --factory-probe --webui-probe --json
```

returned `overall=GREEN`, `reds=0`, and `hermes_webui_factory_events_auth: login HTTP 200; events ok=True events=1 sources=3 queue_exists=True`.

No new LESSON (RULE ZERO).
