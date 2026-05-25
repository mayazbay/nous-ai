#!/bin/bash
# tools/session_register.sh — append a 'register' record to Air session registry.
# Returns session_id on stdout. Used by SessionStart hook + tests + manual override.
#
# Usage:
#   session_register.sh --host <mac|air|vps|nous-gpu> --intent "<text>" --scope "p1,p2,..."
#
# Env override: SESSION_ID_FILE (default ~/.claude/sessions/current_session_id),
#               SESSION_ID_DIR (default ~/.claude/sessions/active),
#               SESSION_REGISTRY_PATH (default Air: ~/nous-agaas/state/active-sessions.jsonl),
#               SESSION_NUM (auto-detect-next: Air registry → HANDOFF scan → day-of-year),
#               SESSION_PID (default $$)
# AP-55 (s73, 2026-04-24): SESSION_NUM no longer defaults to 56 — caused ghost
# s56 registrations (see s72 handoff). Now auto-derives next sequential from
# the authoritative source chain.
set -u
HOST="" INTENT="" SCOPE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --intent) INTENT="$2"; shift 2 ;;
    --scope) SCOPE="$2"; shift 2 ;;
    *) echo "session_register: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$HOST" ] && { echo "session_register: missing --host" >&2; exit 2; }

PID="${SESSION_PID:-$$}"
NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z | sed -E 's/([0-9]{2})([0-9]{2})$/\1:\2/')
NOW_COMPACT=$(date +%Y%m%dT%H%M)
LOCAL_REGISTRY="${SESSION_REGISTRY_PATH:-$HOME/nous-agaas/state/active-sessions.jsonl}"
REMOTE_REGISTRY="${SESSION_REGISTRY_PATH:-\$HOME/nous-agaas/state/active-sessions.jsonl}"
AIR_LOCAL=0
if hostname 2>/dev/null | grep -qi 'air'; then
  AIR_LOCAL=1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)
VAULT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

# Auto-detect next sequential session number unless caller set SESSION_NUM.
# HANDOFF filenames are the authoritative semantic source (session-N, human-curated).
# Air registry is filtered to ≤3-digit prefixes because SessionStart hook writes
# time-based IDs (sHHMM) that would numerically dominate the real sequence.
# Chain: (1) HANDOFF max + 1 → (2) Air registry s<=999 max + 1 → (3) day-of-year.
if [ -z "${SESSION_NUM:-}" ]; then
  # Derive VAULT_DIR from script location so this works on Mac / Air wiki / VPS wiki.
  NUM_FROM_HANDOFF=$(ls -1 "$VAULT_DIR"/pages/progress/HANDOFF-AUTO-*-session-*.md 2>/dev/null | grep -oE 'session-[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1 || true)
  if [ -n "$NUM_FROM_HANDOFF" ] && [ "$NUM_FROM_HANDOFF" -gt 0 ] 2>/dev/null; then
    SESSION_NUM=$((NUM_FROM_HANDOFF + 1))
  else
    if [ "$AIR_LOCAL" -eq 1 ]; then
      NUM_FROM_AIR=$(grep -hoE '"session_id":"s[0-9]{1,3}-' "$LOCAL_REGISTRY" 2>/dev/null | grep -oE "s[0-9]+" | tr -d s | sort -n | tail -1 || true)
    else
      NUM_FROM_AIR=$(ssh -o ConnectTimeout=3 -o BatchMode=yes air \
        'grep -hoE "\"session_id\":\"s[0-9]{1,3}-" ~/nous-agaas/state/active-sessions.jsonl 2>/dev/null | grep -oE "s[0-9]+" | tr -d s | sort -n | tail -1' 2>/dev/null || true)
    fi
    if [ -n "$NUM_FROM_AIR" ] && [ "$NUM_FROM_AIR" -gt 0 ] 2>/dev/null; then
      SESSION_NUM=$((NUM_FROM_AIR + 1))
    else
      # Last resort: day-of-year (always-increasing within a year, never 56-ghost).
      SESSION_NUM=$(date +%j)
    fi
  fi
fi
SESSION_ID="s${SESSION_NUM}-${HOST}-${PID}-${NOW_COMPACT}"
START_HEAD=$(cd "$VAULT_DIR" 2>/dev/null && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Build JSON record (jq -c for compact single-line)
SCOPE_JSON=$(echo "$SCOPE" | jq -Rc 'split(",") | map(select(length>0))')
RECORD=$(jq -nc \
  --arg sid "$SESSION_ID" \
  --arg host "$HOST" \
  --argjson pid "$PID" \
  --arg started "$NOW_ISO" \
  --arg head "$START_HEAD" \
  --arg intent "$INTENT" \
  --argjson scope "$SCOPE_JSON" \
  '{op:"register", session_id:$sid, host:$host, pid:$pid, started_at:$started, start_head:$head, intent:$intent, declared_scope:$scope, ttl_minutes:180}')

# Append to Air registry. POSIX atomicity for writes < PIPE_BUF (4KB).
# Records must stay < 1KB (current ~400B). flock not available on macOS (Air is M2 MacBook).
# If concurrent writers grow beyond hundreds-per-second, revisit with `mkdir`-based portable lock.
if [ "$AIR_LOCAL" -eq 1 ]; then
  if mkdir -p "$(dirname "$LOCAL_REGISTRY")" && echo "$RECORD" >> "$LOCAL_REGISTRY"; then
    APPEND_OK=1
  else
    APPEND_OK=0
  fi
elif echo "$RECORD" | ssh -o ConnectTimeout=5 -o BatchMode=yes air \
     "mkdir -p \"\$(dirname \"$REMOTE_REGISTRY\")\"; cat >> \"$REMOTE_REGISTRY\""; then
  APPEND_OK=1
else
  APPEND_OK=0
fi

if [ "$APPEND_OK" -eq 1 ]; then
  echo "$SESSION_ID"
  SESSION_ID_FILE="${SESSION_ID_FILE:-$HOME/.claude/sessions/current_session_id}"
  SESSION_ID_DIR="${SESSION_ID_DIR:-$HOME/.claude/sessions/active}"
  mkdir -p "$(dirname "$SESSION_ID_FILE")"
  echo "$SESSION_ID" > "$SESSION_ID_FILE"
  mkdir -p "$SESSION_ID_DIR"
  echo "$SESSION_ID" > "$SESSION_ID_DIR/$SESSION_ID.id"
  exit 0
else
  # Air unreachable — fallback to local pending queue
  PENDING="$HOME/.claude/sessions/pending-registers.jsonl"
  mkdir -p "$(dirname "$PENDING")"
  echo "$RECORD" >> "$PENDING"
  echo "$SESSION_ID"  # still return id so caller proceeds
  echo "🟡 session_register: Air unreachable; queued to $PENDING — heartbeat will flush" >&2
  exit 0
fi
