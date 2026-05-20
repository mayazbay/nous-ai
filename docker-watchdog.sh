#!/bin/bash
# docker-watchdog.sh — auto-recover Docker Desktop on Air after reboot or crash.
#
# Codified as `factory-ops` AP-24 compounding gate (session 51, 2026-04-20).
# Root cause: macOS Docker Desktop is a GUI app, not a launchd daemon; SSH-only
# logins never trigger its auto-start, so Air reboots silently kill the factory.
#
# This script is run by `com.nous.docker-desktop-watchdog` LaunchAgent every 5 min.
# On each run:
#   1. If docker socket responds → log "healthy" (sparse), exit 0.
#   2. If socket dead AND Docker Desktop GUI process alive → log "starting", exit 0.
#      (Docker Desktop takes ~30s-2min to come up; don't race it.)
#   3. If socket dead AND Docker Desktop GUI not running → log "recovering",
#      run `open -a "Docker Desktop"`, exit 0. Next run will see it starting or up.
#
# Rate limiting:
#   - State file tracks last-open timestamp; skip re-open if < 5 min ago.
#     (Prevents thrash if Docker Desktop is stuck in a crashloop.)
#   - "healthy" log line emits at most once per hour (no spam).
#
# Never kills Docker if alive. Never touches openclaw container directly.
#
# Usage:
#   bash tools/docker-watchdog.sh           # one-shot run
#   DRY_RUN=1 bash tools/docker-watchdog.sh # don't actually `open -a`, just log intent
#
# Exit codes:
#   0 — checked (healthy / starting / recovery initiated)
#   1 — unexpected error (log + proceed, don't block launchd)

set -u

LOG_FILE="${DOCKER_WATCHDOG_LOG:-$HOME/nous-agaas/logs/docker-watchdog.log}"
STATE_FILE="${DOCKER_WATCHDOG_STATE:-$HOME/nous-agaas/logs/docker-watchdog.state}"
DOCKER_SOCK="/Users/madia/.docker/run/docker.sock"
OPEN_COOLDOWN_SEC=300   # 5 min between `open -a` attempts
HEALTH_LOG_EVERY_SEC=3600  # 1h between "healthy" log lines
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE" "$STATE_FILE" 2>/dev/null || true

NOW=$(date +%s)
NOW_ISO=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$NOW_ISO] $*" >> "$LOG_FILE"; }

# State file schema: KEY=VALUE lines, parse-safe.
get_state() {
  [ -r "$STATE_FILE" ] || { echo ""; return; }
  grep -E "^$1=" "$STATE_FILE" 2>/dev/null | tail -1 | cut -d= -f2-
}
set_state() {
  local key="$1" val="$2"
  if [ -r "$STATE_FILE" ]; then
    grep -vE "^$key=" "$STATE_FILE" > "$STATE_FILE.tmp" 2>/dev/null || true
    mv "$STATE_FILE.tmp" "$STATE_FILE"
  fi
  echo "$key=$val" >> "$STATE_FILE"
}

# --- probe 1: is the socket responding to a docker API call? ---
DOCKER_HOST="unix://$DOCKER_SOCK" docker version --format '{{.Server.Version}}' >/dev/null 2>&1
SOCKET_OK=$?

if [ $SOCKET_OK -eq 0 ]; then
  LAST_HEALTHY=$(get_state LAST_HEALTHY_LOG)
  LAST_HEALTHY="${LAST_HEALTHY:-0}"
  if [ $((NOW - LAST_HEALTHY)) -ge "$HEALTH_LOG_EVERY_SEC" ]; then
    log "healthy — docker socket responding"
    set_state LAST_HEALTHY_LOG "$NOW"
  fi
  exit 0
fi

# Socket dead. Check if Docker Desktop GUI is running.
# Use pgrep with full-path match to avoid false-positives on `docker` CLI.
DD_PROC_COUNT=$(pgrep -f '/Applications/Docker.app/Contents/MacOS/Docker Desktop' 2>/dev/null | wc -l | tr -d ' ')

if [ "${DD_PROC_COUNT:-0}" -gt 0 ]; then
  log "starting — Docker Desktop GUI running (${DD_PROC_COUNT} procs) but socket not ready yet; wait"
  exit 0
fi

# Socket dead AND GUI not running. Rate-limit the recovery attempt.
LAST_OPEN=$(get_state LAST_OPEN_ATTEMPT)
LAST_OPEN="${LAST_OPEN:-0}"
ELAPSED=$((NOW - LAST_OPEN))

if [ "$ELAPSED" -lt "$OPEN_COOLDOWN_SEC" ]; then
  log "cooldown — socket dead, GUI not running, but last open attempt was ${ELAPSED}s ago (< ${OPEN_COOLDOWN_SEC}s). Skipping."
  exit 0
fi

log "recovering — socket dead, no GUI running, ${ELAPSED}s since last attempt; running \`open -a 'Docker Desktop'\`"
set_state LAST_OPEN_ATTEMPT "$NOW"

if [ "$DRY_RUN" = "1" ]; then
  log "DRY_RUN=1 — skipped actual open -a"
  exit 0
fi

if open -a "Docker Desktop" 2>>"$LOG_FILE"; then
  log "recovery-initiated — open -a succeeded; next watchdog run should see 'starting' or 'healthy'"
  exit 0
else
  log "recovery-FAILED — open -a exited non-zero; check Docker Desktop installation"
  exit 1
fi
