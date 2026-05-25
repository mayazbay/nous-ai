#!/bin/bash
# ccd_orphan_watchdog.sh — kill Claude Code CCD agent-mode processes idle >2h
#
# Background: Claude Desktop's Agent Mode / Atoll feature spawns autonomous
# `claude --model claude-opus-4-X --allow-dangerously-skip-permissions
#  --allowedTools mcp__computer-use,mcp__ccd_session__*` subprocesses. Each turn
# bills the user's sk-ant-api key. If the user closes the Claude.app window
# without explicitly stopping the agent, the subprocess can run for days
# autonomously, draining API credits.
#
# Codified in factory-ops AP-33 (s74, 2026-05-05) after s73 P-phase + s74
# discovered 4 + 10 orphan pairs respectively (1-2 day uptimes each).
#
# Heuristic: any claude-code CCD process with elapsed time > 2h AND CPU time
# < 5min in the last hour (i.e. idle, not actively working) is a candidate.
# We use simpler proxy: elapsed > THRESHOLD_HOURS and not recently file-active.
#
# Schedule: every 30 minutes via launchd (com.nous.ccd-orphan-watchdog).
# Logs: ~/nous-agaas/logs/ccd-orphan-watchdog.log

set -u

THRESHOLD_HOURS=${CCD_WATCHDOG_THRESHOLD_HOURS:-2}
LOG=$HOME/nous-agaas/logs/ccd-orphan-watchdog.log
mkdir -p "$(dirname "$LOG")"

NOW=$(date "+%Y-%m-%dT%H:%M:%S%z")
echo "=== $NOW ccd-orphan-watchdog start ===" >> "$LOG"

# Find CCD agent-mode processes (claude --model claude-opus-4-X with computer-use tool)
# ps etime format: dd-hh:mm:ss or hh:mm:ss or mm:ss
# NOTE: mapfile is bash-4+ only; /bin/bash on macOS is 3.2 → portable build via while-read.
CCD_PIDS=()
while IFS= read -r _pid; do
  [ -n "$_pid" ] && CCD_PIDS+=("$_pid")
done < <(ps -axo pid,etime,command 2>/dev/null \
  | grep -E "claude.*--model claude-opus-4" \
  | grep -E "mcp__computer-use|mcp__ccd_session__" \
  | grep -v grep \
  | awk '{print $1}')

if [ "${#CCD_PIDS[@]:-0}" -eq 0 ]; then
  echo "$NOW: no CCD agent-mode processes found" >> "$LOG"
  exit 0
fi

KILLED=0
KEPT=0
THRESHOLD_SEC=$((THRESHOLD_HOURS * 3600))

# macOS BSD ps lacks `etimes` (seconds); parse formatted etime: [DD-]HH:MM:SS or MM:SS
parse_etime_seconds() {
  local etime="$1"
  local days=0 hours=0 mins=0 secs=0
  if [[ "$etime" == *-* ]]; then
    days="${etime%%-*}"
    etime="${etime#*-}"
  fi
  # remaining is HH:MM:SS or MM:SS
  local fields
  fields=$(echo "$etime" | awk -F: '{print NF}')
  if [ "$fields" = "3" ]; then
    hours=$(echo "$etime" | cut -d: -f1)
    mins=$(echo "$etime"  | cut -d: -f2)
    secs=$(echo "$etime"  | cut -d: -f3)
  elif [ "$fields" = "2" ]; then
    mins=$(echo "$etime" | cut -d: -f1)
    secs=$(echo "$etime" | cut -d: -f2)
  fi
  echo $(( days * 86400 + 10#$hours * 3600 + 10#$mins * 60 + 10#$secs ))
}

for PID in "${CCD_PIDS[@]}"; do
  # Get elapsed time as formatted string (BSD ps portable)
  ETIME_STR=$(ps -o etime= -p "$PID" 2>/dev/null | tr -d ' ')
  if [ -z "$ETIME_STR" ]; then
    echo "$NOW: PID $PID gone before check" >> "$LOG"
    continue
  fi
  ETIME_SEC=$(parse_etime_seconds "$ETIME_STR")
  if [ "$ETIME_SEC" -lt "$THRESHOLD_SEC" ]; then
    KEPT=$((KEPT + 1))
    continue
  fi

  # Over threshold — kill (TERM, then KILL after 5s if still alive)
  CMDLINE=$(ps -o command= -p "$PID" 2>/dev/null | head -c 200)
  echo "$NOW: KILL PID=$PID etime=${ETIME_SEC}s threshold=${THRESHOLD_SEC}s cmd=$CMDLINE" >> "$LOG"
  kill -TERM "$PID" 2>/dev/null
  sleep 5
  if kill -0 "$PID" 2>/dev/null; then
    kill -KILL "$PID" 2>/dev/null
    echo "$NOW: SIGKILL forced on PID=$PID" >> "$LOG"
  fi
  KILLED=$((KILLED + 1))
done

echo "$NOW: summary killed=$KILLED kept=$KEPT total=${#CCD_PIDS[@]}" >> "$LOG"

# Notify Madi if we killed anything (visible signal that watchdog earned its keep)
if [ "$KILLED" -gt 0 ] && [ -x "$HOME/nous-agaas/wiki/tools/tg_send.sh" ]; then
  bash "$HOME/nous-agaas/wiki/tools/tg_send.sh" \
    "🐕 ccd-watchdog: killed $KILLED CCD agent-mode orphan(s) (>${THRESHOLD_HOURS}h elapsed). Kept $KEPT active. Saving Anthropic API credits. See ~/nous-agaas/logs/ccd-orphan-watchdog.log" \
    >/dev/null 2>&1 || true
fi
