#!/bin/bash
# tools/session_heartbeat.sh — append heartbeat records to Air session registry.
# Reads session ids from $SESSION_ID_FILE plus per-session files in $SESSION_ID_DIR.
# Idempotent: silent no-op if no session ids exist.
set -u
SESSION_ID_FILE="${SESSION_ID_FILE:-$HOME/.claude/sessions/current_session_id}"
SESSION_ID_DIR="${SESSION_ID_DIR:-$HOME/.claude/sessions/active}"
SESSION_PENDING_DIR="${SESSION_PENDING_DIR:-$HOME/.claude/sessions}"
LOCAL_REGISTRY="${SESSION_REGISTRY_PATH:-$HOME/nous-agaas/state/active-sessions.jsonl}"
REMOTE_REGISTRY="${SESSION_REGISTRY_PATH:-\$HOME/nous-agaas/state/active-sessions.jsonl}"
AIR_LOCAL=0
if [ "${SESSION_FORCE_AIR_LOCAL:-0}" = "1" ] || hostname 2>/dev/null | grep -qi 'air'; then
  AIR_LOCAL=1
fi

sid_has_dead_local_pid() {
  local sid="$1" pid=""
  case "$sid" in
    s*-mac-[0-9]*-*)
      pid=$(printf '%s' "$sid" | awk -F- '{print $3}')
      [ -n "$pid" ] || return 1
      ps -p "$pid" >/dev/null 2>&1 && return 1
      return 0
      ;;
  esac
  return 1
}

IDS=$(
  {
    [ -f "$SESSION_ID_FILE" ] && cat "$SESSION_ID_FILE" 2>/dev/null
    if [ -d "$SESSION_ID_DIR" ]; then
      for f in "$SESSION_ID_DIR"/*.id; do
        [ -e "$f" ] || continue
        sid=$(cat "$f" 2>/dev/null || true)
        [ -n "$sid" ] || continue
        if sid_has_dead_local_pid "$sid"; then
          continue
        fi
        printf '%s\n' "$sid"
      done
    fi
  } | sed '/^$/d' | sort -u
)
[ -n "$IDS" ] || exit 0

NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z | sed -E 's/([0-9]{2})([0-9]{2})$/\1:\2/')
RECORDS=$(printf '%s\n' "$IDS" | while IFS= read -r sid; do
  jq -nc --arg sid "$sid" --arg ts "$NOW_ISO" '{op:"heartbeat", session_id:$sid, ts:$ts}'
done)

drain_pending_queues() {
  for q in "$SESSION_PENDING_DIR/pending-heartbeats.jsonl" "$SESSION_PENDING_DIR/pending-registers.jsonl"; do
    [ -s "$q" ] || continue
    if [ "$AIR_LOCAL" -eq 1 ]; then
      if cat "$q" >> "$LOCAL_REGISTRY"; then
        : > "$q"
      fi
    elif ssh -o ConnectTimeout=5 -o BatchMode=yes air \
         "mkdir -p \"\$(dirname \"$REMOTE_REGISTRY\")\"; cat >> \"$REMOTE_REGISTRY\"" < "$q" 2>/dev/null; then
      : > "$q"
    fi
  done
}

if [ "$AIR_LOCAL" -eq 1 ]; then
  mkdir -p "$(dirname "$LOCAL_REGISTRY")"
  printf '%s\n' "$RECORDS" >> "$LOCAL_REGISTRY"
  drain_pending_queues
  exit 0
fi

if printf '%s\n' "$RECORDS" | ssh -o ConnectTimeout=5 -o BatchMode=yes air \
     "mkdir -p \"\$(dirname \"$REMOTE_REGISTRY\")\"; cat >> \"$REMOTE_REGISTRY\"" 2>/dev/null; then
  # Air reachable: opportunistically drain BOTH pending queues that AP-13 doctrine
  # claims this heartbeat flushes. Lane K (s82f, 2026-04-29) found the drain code
  # was missing — doctrine asserted a recovery path that didn't exist. Fix here.
  drain_pending_queues
  exit 0
fi

# Air unreachable → enqueue locally
PENDING="$SESSION_PENDING_DIR/pending-heartbeats.jsonl"
mkdir -p "$(dirname "$PENDING")"
printf '%s\n' "$RECORDS" >> "$PENDING"
exit 0
