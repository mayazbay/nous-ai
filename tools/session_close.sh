#!/bin/bash
# tools/session_close.sh — append a 'close' record. Removes current_session_id
# (only when closing the file-tracked session, not a --session-id override).
#
# Usage:
#   bash tools/session_close.sh                          # close the current session (file-tracked)
#   bash tools/session_close.sh ok                       # same, with explicit exit status
#   bash tools/session_close.sh --session-id <SID>       # close a specific session (no file touch)
#   bash tools/session_close.sh --session-id <SID> ok    # with status
#
# Env override: SESSION_REGISTRY_PATH points register/close/scan/heartbeat at a
# test registry instead of live Air state; SESSION_ID_DIR holds per-session ids.
#
# --session-id rationale (session 60, 2026-04-22): previously the script read
# ONLY from $HOME/.claude/sessions/current_session_id, which made it impossible
# to close a stale session (e.g., an old auto-registered s1051 while the user
# had re-registered as s59). Callers had to manually append JSONL to Air via
# direct SSH — error-prone and documented as quirk. The flag makes targeted
# close a first-class operation.

set -u
SESSION_ID_FILE="${SESSION_ID_FILE:-$HOME/.claude/sessions/current_session_id}"
SESSION_ID_DIR="${SESSION_ID_DIR:-$HOME/.claude/sessions/active}"
LOCAL_REGISTRY="${SESSION_REGISTRY_PATH:-$HOME/nous-agaas/state/active-sessions.jsonl}"
REMOTE_REGISTRY="${SESSION_REGISTRY_PATH:-\$HOME/nous-agaas/state/active-sessions.jsonl}"
AIR_LOCAL=0
if hostname 2>/dev/null | grep -qi 'air'; then
    AIR_LOCAL=1
fi

SESSION_ID=""
EXPLICIT_SID=0
EXIT_STATUS="ok"

# Parse args — order-independent
while [ $# -gt 0 ]; do
    case "$1" in
        --session-id)
            shift
            SESSION_ID="${1:-}"
            EXPLICIT_SID=1
            ;;
        --session-id=*)
            SESSION_ID="${1#--session-id=}"
            EXPLICIT_SID=1
            ;;
        -*)
            echo "unknown flag: $1" >&2
            exit 2
            ;;
        *)
            EXIT_STATUS="$1"
            ;;
    esac
    shift
done

# Fall back to file-tracked session if --session-id not given
if [ -z "$SESSION_ID" ]; then
    [ -f "$SESSION_ID_FILE" ] || exit 0
    SESSION_ID=$(cat "$SESSION_ID_FILE")
    [ -z "$SESSION_ID" ] && exit 0
fi

NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z | sed -E 's/([0-9]{2})([0-9]{2})$/\1:\2/')
RECORD=$(jq -nc --arg sid "$SESSION_ID" --arg ts "$NOW_ISO" --arg ex "$EXIT_STATUS" \
  '{op:"close", session_id:$sid, ts:$ts, exit_status:$ex}')

if [ "$AIR_LOCAL" -eq 1 ]; then
    mkdir -p "$(dirname "$LOCAL_REGISTRY")"
    echo "$RECORD" >> "$LOCAL_REGISTRY"
else
    echo "$RECORD" | ssh -o ConnectTimeout=5 -o BatchMode=yes air \
      "mkdir -p \"\$(dirname \"$REMOTE_REGISTRY\")\"; cat >> \"$REMOTE_REGISTRY\"" 2>/dev/null || true
fi

# Only remove the current_session_id file when closing our own session,
# not when closing a targeted --session-id override.
if [ "$EXPLICIT_SID" -eq 0 ]; then
    rm -f "$SESSION_ID_FILE"
fi
rm -f "$SESSION_ID_DIR/$SESSION_ID.id"
exit 0
