---
type: lesson
id: LESSON-097
title: "LESSON-097: Bulletproof schedule v2 — state-change alerts, smart checkpoint, staleness detector; plus settings.json FileChanged hook cleanup"
tags: [lessons, cron, launchd, schedule, state-change, alerts, settings-json, hooks]
date: 2026-04-15
source_count: 0
status: absorbed
absorbed_at: 2026-04-16
last_updated: 2026-04-15
related: [HANDOFF-2026-04-15-session22, LESSON-093-factory-context-poisoning-and-ghost-cleanup]
session: 22
severity: P2
integrated_into: infrastructure
absorbed_into: audit
---

# LESSON-097: Bulletproof schedule v2 + settings.json hook cleanup

## Part A — Schedule v1 gaps that prompted v2

v1 (deployed earlier session 22):
- 3am launchd: update check
- 4am launchd: full audit
- 8×/day auto-checkpoint (fixed schedule, always runs)

Gaps found on review:
1. No state-change filtering — 4am alert fires every day even when nothing changed. Alert fatigue.
2. 4am is too infrequent — issue at 09:15 waits 18.5h for detection.
3. Auto-checkpoint writes even when no new task-results — wiki clutter + tokens.
4. 3am + 4am are overlapping — same state queries, two Telegram pings.
5. No staleness detector — factory can look "green" while being silently idle during work hours.
6. No log rotation — logs grow unbounded.

## v2 (deployed, running)

| launchd | Interval | Purpose |
|---------|----------|---------|
| `com.nous.light-probe` | 15 min | Fast mechanical check. **Alerts only on state change** (green↔red). State stored in `logs/light-probe-state.json`. No LLM. |
| `com.nous.staleness` | 60 min (gate on 09-22 Almaty) | Checks last task-result mtime; alert if no new work in 6h during working hours. |
| `com.nous.auto-checkpoint` | 8×/day (smart) | **Skips if no new task-results since last checkpoint** (stored in `logs/auto-checkpoint-state.json`). Typical day: 2-3 real writes. |
| `com.nous.morning-brief` | 4am | Merged audit + update-check. Shows state DELTA vs yesterday. One Telegram. Replaces old 3am+4am. |
| `com.nous.log-rotate` | Sunday 03:00 | Truncates `logs/*.log` > 5MB, keeps last 1000 lines. |

## Architecture: tier-based reliability

**Tier 1 — Process resilience** (instant recovery):
- OpenClaw: `--restart unless-stopped` in Docker
- LiteLLM: launchd `KeepAlive=true`
- Telegram-poll: launchd `StartInterval=60` (restarts every minute anyway)

**Tier 2 — Mechanical checks** (fast, cheap, state-change alerts):
- Light-probe every 15 min

**Tier 3 — Intelligent daily** (LLM-powered or expensive):
- Morning brief at 04:00 (end-to-end factory probe, update check, state diff)

**Tier 4 — On-demand** (triggered by new activity):
- Smart auto-checkpoint (skip-on-quiet)

## State-change alert pattern (core trick)

Each cron stores its last run's state in a JSON file. Compares current to previous. Only posts Telegram when they differ. Prevents alarm fatigue while still catching real transitions instantly.

```bash
PREV_STATE=$(cat "$STATE_FILE" 2>/dev/null || echo '{}')
# ... compute current state into CUR ...
for key in openclaw port18789 litellm ...; do
  PREV=$(echo "$PREV_STATE" | jq -r ".$key // \"?\"")
  if [ "$PREV" != "?" ] && [ "$PREV" != "${CUR[$key]}" ]; then
    CHANGES="${CHANGES}$key: $PREV → ${CUR[$key]}\n"
  fi
done
if [ -n "$CHANGES" ]; then
  # alert
fi
echo "$CUR" > "$STATE_FILE"
```

First run = no alerts (no "previous" to compare). Every run after = alert only on transition.

## Part B — settings.json invalid FileChanged hook

Session 22 surfaced this settings error on BOTH Macs:
```
/Users/madia/.claude/settings.json
 └ hooks
   └ FileChanged: Invalid key in record
Files with errors are skipped entirely, not just the invalid settings.
```

**Root cause:** `FileChanged` is not a valid Claude Code hook event. Valid events are: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact, TaskCompleted, Notification, SubagentStop. When Claude Code starts, it validates hooks — any invalid key causes the **entire settings file** to be skipped (not just the bad entry). So ALL hooks, not just the broken one, stop working until fixed.

**Was broken on both Mac Pro and Air** — had to fix in two places.

**Original intent** of the hook: sync `laws/banned_patterns.txt` to VPS when edited. Already redundant because `com.nous.wiki-sync` on Air handles git push every 5 min. Delete was safe.

## Part C — Session 23 audit revealed 3 hidden bugs

Session 23 post-deploy audit (2026-04-15 17:10 Almaty) found that despite launchd showing exit 0 for every v2 service, **two of the daily crons would have failed on first real fire**:

### Bug C1 — `morning-brief.sh` used `declare -A` (bash 4+)
macOS `/bin/bash` is **bash 3.2** (ancient Apple ships only the GPLv2-era version). My v1 morning-brief used associative arrays (`declare -A CUR`) which don't exist in 3.2. Launchd invoked it as `/bin/bash /path/script.sh` → crashed immediately with `declare: -A: invalid option`.

But `launchctl list` showed `LastExitStatus=0` because I had also tested it manually earlier in an SSH shell that probably ran under zsh, which silently ignored the bad `declare`. The 4am cron would have been the first real `/bin/bash` invocation.

**Fix:** Rewrite without associative arrays using helper functions that build a JSON string incrementally. Tested on `/bin/bash` before deploying. Light-probe.sh, staleness-check.sh, log-rotate.sh checked — none use bash-4+ features.

**Rule:** If launchd plist invokes `/bin/bash`, the script MUST be bash 3.2 compatible. No `declare -A`, no `[[ -v var ]]`, no `${var^^}`/`${var,,}`. Test with `/bin/bash your-script.sh` before relying on launchd to run it.

### Bug C2 — `auto-checkpoint.py` timeout too short for slow context injection
run_task.py calls context_injector which injects ~47K chars of MEMORY+HANDOFF+qmd-search context EVERY call, even for trivial "reply X" probes. GLM-5.1 processes all 45K+ input tokens → ~3 minutes per call. auto-checkpoint's 360s timeout expired before completion → silent failure, no state file written, smart-skip never engaged, every scheduled run repeated the same timeout.

**Fix:** Bump `TIMEOUT = 600` in auto_checkpoint.py. Also bumped morning-brief.sh and nightly-audit.sh factory-probe perl alarm from 60s → 300s.

**Root cause still open:** context_injector should have a "lite" mode for health probes (no MEMORY/HANDOFF injection). Queued for Wave 2.

### Bug C3 — Launchd exit 0 lies about actual health
Bugs C1 and C2 both produced `LastExitStatus=0` in `launchctl list`. Why? Because:
- C1: Script ran manually via SSH (zsh) — succeeded. Never tested via `/bin/bash`.
- C2: The Python process itself exited 0 after catching TimeoutExpired. The subprocess.run timed out, but the outer checkpoint() catch clause logged the error and returned 0.

**Rule:** "LastExitStatus=0 in launchctl list" is necessary but NOT sufficient for "cron is working". Always verify the OUTPUT artifact the cron is supposed to produce (log file updated? state file written? handoff page created?). If the artifact is missing, the cron is broken regardless of exit code.

## Rules

1. **State-change alerts over fixed-schedule alerts** for any recurring health check. Silent when stable = much better signal-to-noise.

2. **Smart-skip cron jobs** that would otherwise produce empty outputs. Check "is there new input?" before doing work.

3. **Tier your checks:** process resilience (Tier 1, automatic) > mechanical polling (Tier 2, cheap) > intelligent analysis (Tier 3, daily) > on-demand (Tier 4, triggered).

4. **Claude Code `settings.json` errors are silent killers** — they disable ALL hooks, not just the invalid one. Validate with: `python3 -c "import json; json.load(open('~/.claude/settings.json'))"` after any hand-edit.

5. **Valid Claude Code hooks:** SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact, TaskCompleted, Notification, SubagentStop. There is NO `FileChanged` hook. For "do something when a file changes," use a launchd `WatchPaths` LaunchAgent instead.

## Verified

- Light-probe tested — writes heartbeat to log when no change, Telegram alert expected on state flip.
- Staleness tested — age=0 hours, state file clean.
- Morning-brief: tests next at 04:00 Almaty automatically.
- Smart auto-checkpoint: deployed, tested — writes when new task-results, skips otherwise.
- Settings.json: both Mac Pro + Air validated clean with `python3 -c "import json; json.load(open('...'))"`.

## Timeline

- **2026-04-15 session 22**: Schedule v1 → v2 refactor. settings.json FileChanged hook removed on both Macs.

## See also

- [[HANDOFF-2026-04-15-session22]]
- [[LESSON-098-claude-code-env-var-vs-oauth]] — fixed in same session
- [[LESSON-093-factory-context-poisoning-and-ghost-cleanup]] — related ghost cleanup earlier session
