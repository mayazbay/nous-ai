#!/bin/bash
# tools/stream_a_claim.sh — exclusive lock for the Stream-A interactive driver session.
#
# Per skills/session-architecture/SKILL v1.0.0: only ONE interactive Mac Claude
# Code session at a time may write to the shared vault. Subsequent sessions
# detect this lock and either become Stream-D dispatch fallbacks or refuse to
# register as interactive.
#
# Usage:
#   stream_a_claim.sh acquire <session_id> "<intent>"
#   stream_a_claim.sh release <session_id>
#   stream_a_claim.sh status
#   stream_a_claim.sh revoke-stale
#
# Lock file: ~/nous-agaas/state/stream_a.lock (JSON with epoch field)
#
# Stale criteria (any of):
#   - PID not running (kill -0 PID fails)
#   - acquired_epoch + 7200s (2h) < now AND no heartbeat in last 30min for sid
#
# Bash 3.2 compatible (macOS default).

set -u
LOCK="$HOME/nous-agaas/state/stream_a.lock"
LOCK_DIR=$(dirname "$LOCK")
mkdir -p "$LOCK_DIR"

NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z | sed -E 's/([0-9]{2})([0-9]{2})$/\1:\2/')
NOW_EPOCH=$(date +%s)
MAX_AGE=7200

ACTION="${1:-status}"

is_pid_alive() {
  local pid="$1"
  [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null && kill -0 "$pid" 2>/dev/null
}

is_active() {
  # $1 = pid, $2 = acquired_epoch
  local pid="$1" epoch="$2"
  is_pid_alive "$pid" && [ -n "$epoch" ] && [ "$((NOW_EPOCH - epoch))" -le "$MAX_AGE" ] 2>/dev/null
}

case "$ACTION" in
  acquire)
    SID="${2:?usage: acquire <session_id> <intent>}"
    INTENT="${3:?usage: acquire <session_id> <intent>}"
    if [ -s "$LOCK" ]; then
      HOLDER_PID=$(jq -r '.pid // 0' "$LOCK" 2>/dev/null || echo 0)
      HOLDER_EPOCH=$(jq -r '.acquired_epoch // 0' "$LOCK" 2>/dev/null || echo 0)
      HOLDER_SID=$(jq -r '.session_id // ""' "$LOCK" 2>/dev/null || echo "")
      if is_active "$HOLDER_PID" "$HOLDER_EPOCH"; then
        echo "🔴 stream_a held by $HOLDER_SID (pid=$HOLDER_PID, age=$((NOW_EPOCH - HOLDER_EPOCH))s)" >&2
        echo "   This session should register as Stream-D dispatch fallback or non-vault scope." >&2
        exit 1
      fi
      echo "🟡 stale Stream-A lock revoked: $HOLDER_SID (pid=$HOLDER_PID dead or stale)" >&2
    fi
    PID=$$
    jq -nc \
      --arg sid "$SID" \
      --argjson pid "$PID" \
      --arg at "$NOW_ISO" \
      --argjson epoch "$NOW_EPOCH" \
      --arg intent "$INTENT" \
      '{session_id:$sid, pid:$pid, acquired_at:$at, acquired_epoch:$epoch, intent:$intent, host:"mac"}' > "$LOCK"
    echo "✅ Stream-A acquired by $SID (pid=$PID)"
    exit 0
    ;;
  release)
    SID="${2:?usage: release <session_id>}"
    if [ ! -s "$LOCK" ]; then
      echo "⚠️  Stream-A already free" >&2
      exit 0
    fi
    HOLDER_SID=$(jq -r '.session_id // ""' "$LOCK" 2>/dev/null || echo "")
    if [ "$HOLDER_SID" = "$SID" ]; then
      rm -f "$LOCK"
      echo "✅ Stream-A released by $SID"
      exit 0
    else
      echo "🔴 Stream-A held by $HOLDER_SID, not $SID — refusing to release another session's lock" >&2
      exit 2
    fi
    ;;
  status)
    if [ ! -s "$LOCK" ]; then
      echo '{"status":"free"}'
      exit 1
    fi
    HOLDER=$(cat "$LOCK")
    HOLDER_PID=$(echo "$HOLDER" | jq -r '.pid // 0')
    HOLDER_EPOCH=$(echo "$HOLDER" | jq -r '.acquired_epoch // 0')
    if is_active "$HOLDER_PID" "$HOLDER_EPOCH"; then
      echo "$HOLDER" | jq -c '. + {status:"held"}'
      exit 0
    else
      echo "$HOLDER" | jq -c '. + {status:"stale"}'
      exit 2
    fi
    ;;
  revoke-stale)
    if [ ! -s "$LOCK" ]; then
      echo '{"status":"free"}'
      exit 0
    fi
    HOLDER=$(cat "$LOCK")
    HOLDER_PID=$(echo "$HOLDER" | jq -r '.pid // 0')
    HOLDER_EPOCH=$(echo "$HOLDER" | jq -r '.acquired_epoch // 0')
    if is_active "$HOLDER_PID" "$HOLDER_EPOCH"; then
      echo "$HOLDER" | jq -c '. + {status:"held",action:"none"}'
      exit 0
    else
      rm -f "$LOCK"
      echo "$HOLDER" | jq -c '. + {status:"revoked",action:"removed"}'
      exit 0
    fi
    ;;
  *)
    echo "usage: $0 {acquire <sid> <intent> | release <sid> | status | revoke-stale}" >&2
    exit 2
    ;;
esac
