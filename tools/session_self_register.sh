#!/bin/bash
# tools/session_self_register.sh — idempotent re-registration for long-running sessions.
#
# The SessionStart hook (~/.claude/hooks/session-start-soao.sh) only fires on a
# fresh Claude Code launch, NOT on /clear, /reset, or conversation continuation.
# Long sessions (multi-hour) may run without ever appearing in
# ~/nous-agaas/state/active-sessions.jsonl on Air → 4-lane registry shows 0 lanes.
#
# Per session-coordination AP-13 (session 82e, 2026-04-29): empty registry ≠
# "no peers active." Long sessions must self-register on demand.
#
# Usage (from any Mac/Air session):
#   bash tools/session_self_register.sh                       # registers if not yet
#   bash tools/session_self_register.sh --intent "..." --scope "path1,path2"
#   bash tools/session_self_register.sh --force               # re-register anyway
#
# Env aliases:
#   SESSION_INTENT / SESSION_SCOPE are canonical.
#   CODEX_SESSION_INTENT / CODEX_SESSION_SCOPE are accepted for callers that
#   share vocabulary with tools/codex-nous.sh.
#
# Exit 0 = centrally registered, already registered, or locally queued with a
# clear "not centrally visible yet" warning. Handshake proof still requires
# `session_scan.sh` to show the lane from Air's registry.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
SID_FILE="${SESSION_ID_FILE:-$HOME/.claude/sessions/current_session_id}"
SID_DIR="${SESSION_ID_DIR:-$HOME/.claude/sessions/active}"
LOCAL_REGISTRY="${SESSION_REGISTRY_PATH:-$HOME/nous-agaas/state/active-sessions.jsonl}"
REMOTE_REGISTRY="${SESSION_REGISTRY_PATH:-\$HOME/nous-agaas/state/active-sessions.jsonl}"
INTENT="${SESSION_INTENT:-${CODEX_SESSION_INTENT:-claude-code session continuation}}"
SCOPE="${SESSION_SCOPE:-${CODEX_SESSION_SCOPE:-*}}"
FORCE=0
AIR_LOCAL=0
if hostname 2>/dev/null | grep -qi 'air'; then
  AIR_LOCAL=1
fi

detect_default_session_pid() {
  if [ -n "${SESSION_PID:-}" ]; then
    printf '%s\n' "$SESSION_PID"
    return 0
  fi

  local self="$$" parent="" parent_cmd="" grand="" grand_cmd=""
  parent=$(ps -o ppid= -p "$self" 2>/dev/null | tr -d ' ')
  if [ -n "$parent" ]; then
    parent_cmd=$(ps -o command= -p "$parent" 2>/dev/null || true)
    case "$parent_cmd" in
      *"codex app-server"*)
        printf '%s\n' "$parent"
        return 0
        ;;
    esac

    grand=$(ps -o ppid= -p "$parent" 2>/dev/null | tr -d ' ')
    if [ -n "$grand" ]; then
      grand_cmd=$(ps -o command= -p "$grand" 2>/dev/null || true)
      case "$grand_cmd" in
        *"codex app-server"*)
          printf '%s\n' "$grand"
          return 0
          ;;
      esac
    fi
  fi

  printf '%s\n' "$self"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --intent) INTENT="$2"; shift 2 ;;
    --scope)  SCOPE="$2"; shift 2 ;;
    --force)  FORCE=1; shift ;;
    *) echo "usage: $0 [--intent <text>] [--scope <paths>] [--force]" >&2; exit 2 ;;
  esac
done

mkdir -p "$(dirname "$SID_FILE")"

# If already registered + freshness check OK, no-op (unless --force)
if [ "$FORCE" -ne 1 ] && [ -s "$SID_FILE" ]; then
  EXISTING_SID=$(cat "$SID_FILE")
  # Confirm Air sees this session as currently active. Raw grep is unsafe here:
  # closed/stale records still contain the same session_id.
  ACTIVE_JSON=$(bash "$VAULT/tools/session_scan.sh" --json 2>/dev/null || echo "[]")
  if echo "$ACTIVE_JSON" | jq -e --arg sid "$EXISTING_SID" 'any(.[]?; .session_id == $sid)' >/dev/null 2>&1; then
    echo "✅ already registered: $EXISTING_SID"
    exit 0
  fi
  echo "🟡 SID file exists ($EXISTING_SID) but Air registry has no active entry — re-registering"
fi

# Register
HOST=$(hostname -s | tr '[:upper:]' '[:lower:]' | sed 's/\.local$//')
case "$HOST" in
  mac*|*macbook*) HOST="mac" ;;
  air|*air*)      HOST="air" ;;
  *vps*)          HOST="vps" ;;
  *)              HOST="${HOST:-unknown}" ;;
esac

SESSION_NUM="${CLAUDE_SESSION_NUM:-${SESSION_NUM:-}}"
REGISTER_PID=$(detect_default_session_pid)
REG_OUT=$(SESSION_NUM="$SESSION_NUM" SESSION_PID="$REGISTER_PID" bash "$VAULT/tools/session_register.sh" \
  --host "$HOST" --intent "$INTENT" --scope "$SCOPE" 2>&1)
RC=$?

if [ $RC -eq 0 ] && echo "$REG_OUT" | grep -qE '^s[0-9]'; then
  SID=$(echo "$REG_OUT" | grep -E '^s[0-9]' | head -1)
  echo "$SID" > "$SID_FILE"
  mkdir -p "$SID_DIR"
  echo "$SID" > "$SID_DIR/$SID.id"
  if echo "$REG_OUT" | grep -qi 'Air unreachable; queued'; then
    echo "🟡 queued: $SID (not centrally visible; heartbeat will flush pending register)"
    exit 0
  fi
  echo "✅ registered: $SID (host=$HOST scope=$SCOPE)"
  exit 0
fi

echo "🔴 registration failed:"
echo "$REG_OUT" | sed 's/^/  /'
echo "  Air may be unreachable; pending-registers.jsonl will retry via heartbeat."
exit 1
