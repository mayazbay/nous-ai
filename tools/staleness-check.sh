#!/bin/bash
# staleness-check.sh — every 60 min during working hours (09:00-22:00 Almaty).
# Alert if no task-results in 6h. Factory appears alive but producing nothing.
# Run by launchd via StartCalendarInterval; script itself checks current hour.
# Location on Air: /Users/madia/nous-agaas/tools/staleness-check.sh

set -u
source /Users/madia/nous-agaas/.env 2>/dev/null

# Working hours guard (Almaty = UTC+5)
HOUR=$(TZ=Asia/Almaty date +%H)
if [ "$HOUR" -lt 9 ] || [ "$HOUR" -ge 22 ]; then
  exit 0  # quiet outside working hours
fi

STATE=/Users/madia/nous-agaas/logs/staleness-state.json
LOG=/Users/madia/nous-agaas/logs/staleness-check.log

# Find the most recent task-result file (by mtime)
LATEST=$(ls -t /Users/madia/nous-agaas/wiki/pages/task-results/ 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  exit 0  # no files at all, nothing to compare
fi

# Age in seconds of the latest file
LATEST_MTIME=$(stat -f %m "/Users/madia/nous-agaas/wiki/pages/task-results/$LATEST" 2>/dev/null)
NOW=$(date +%s)
AGE=$((NOW - LATEST_MTIME))
AGE_HOURS=$((AGE / 3600))

# Read previous state to avoid re-alerting every hour
PREV_ALERTED=""
if [ -f "$STATE" ]; then
  PREV_ALERTED=$(python3 -c "import json; print(json.load(open('$STATE')).get('last_alert', ''))" 2>/dev/null)
fi

if [ "$AGE_HOURS" -ge 6 ]; then
  # Stale. Alert if we haven't already alerted about THIS stale file.
  if [ "$PREV_ALERTED" != "$LATEST" ]; then
    TS=$(date +%Y-%m-%dT%H:%M:%S)
    echo "[$TS] STALE: no task-results in ${AGE_HOURS}h. Latest: $LATEST" >> "$LOG"
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
      MSG="⏰ Factory staleness warning

No task-results in ${AGE_HOURS} hours (working hours: 09:00-22:00 Almaty).

Latest: ${LATEST}

Possible causes:
• Telegram bot not receiving /ask
• Factory agent stuck or crashed
• /ask routing broken

Quick check: ssh air 'tail -20 ~/nous-agaas/logs/telegram_poll.err'"
      curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${MSG}" > /dev/null 2>&1
    fi
    echo "{\"last_alert\": \"$LATEST\", \"last_age_hours\": $AGE_HOURS}" > "$STATE"
  fi
else
  # Not stale. Clear any prior alert state so next staleness triggers fresh.
  echo "{\"last_alert\": \"\", \"last_age_hours\": $AGE_HOURS}" > "$STATE"
fi
