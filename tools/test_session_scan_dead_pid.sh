#!/bin/bash
# tools/test_session_scan_dead_pid.sh — local dead-PID rows must not look active.
set -u
PASS=0
FAIL=0
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="session-scan-dead-pid"
SID_FILE="/tmp/test-session-scan-dead-pid-id-$$"
SID_DIR="/tmp/test-session-scan-dead-pid-active-$$"
TEST_REGISTRY="/Users/madia/nous-agaas/state/test-active-sessions-$SUITE-$$.jsonl"
export SESSION_REGISTRY_PATH="$TEST_REGISTRY"
export SESSION_ID_FILE="$SID_FILE"
export SESSION_ID_DIR="$SID_DIR"
export SESSION_SCAN_FILTER_DEAD_LOCAL_PID=1

on_air() { hostname 2>/dev/null | grep -qi 'air'; }

air_cmd() {
  if on_air; then
    bash -lc "$1"
  else
    ssh -o ConnectTimeout=3 air "$1"
  fi
}

assert() {
  local label="$1" cond="$2"
  if eval "$cond"; then
    PASS=$((PASS+1))
    echo "  ✅ $label"
  else
    FAIL=$((FAIL+1))
    echo "  🔴 $label"
    echo "       cond: $cond"
  fi
}

cleanup() {
  air_cmd "rm -f \"$TEST_REGISTRY\"" 2>/dev/null
  rm -rf "$SID_FILE" "$SID_DIR" 2>/dev/null
}
trap cleanup EXIT

normalize_host() {
  local h
  h=$(hostname -s 2>/dev/null | tr '[:upper:]' '[:lower:]' | sed 's/\.local$//')
  case "$h" in
    mac*|*macbook*) echo "mac" ;;
    air|*air*)      echo "air" ;;
    *vps*)          echo "vps" ;;
    *)              echo "${h:-unknown}" ;;
  esac
}

dead_pid() {
  local p=999998
  while ps -p "$p" >/dev/null 2>&1; do
    p=$((p - 1))
  done
  echo "$p"
}

echo "=== $SUITE ==="
mkdir -p "$SID_DIR"
air_cmd "mkdir -p \"$(dirname "$TEST_REGISTRY")\" && : > \"$TEST_REGISTRY\"" 2>/dev/null

HOST_NAME=$(normalize_host)
OTHER_HOST="air"
[ "$HOST_NAME" = "air" ] && OTHER_HOST="mac"
ALIVE_PID=$$
DEAD_PID=$(dead_pid)

ALIVE_SID=$(SESSION_NUM=99 SESSION_PID="$ALIVE_PID" bash "$TOOLS_DIR/session_register.sh" --host "$HOST_NAME" --intent "alive-local-pid" --scope "alive.md" 2>/dev/null)
DEAD_SID=$(SESSION_NUM=99 SESSION_PID="$DEAD_PID" bash "$TOOLS_DIR/session_register.sh" --host "$HOST_NAME" --intent "dead-local-pid" --scope "dead.md" 2>/dev/null)
REMOTE_SID=$(SESSION_NUM=99 SESSION_PID="$DEAD_PID" bash "$TOOLS_DIR/session_register.sh" --host "$OTHER_HOST" --intent "remote-dead-pid-not-local" --scope "remote.md" 2>/dev/null)

SCAN=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null)
COUNT=$(echo "$SCAN" | jq 'length')
ALIVE_COUNT=$(echo "$SCAN" | jq --arg sid "$ALIVE_SID" '[.[] | select(.session_id == $sid)] | length')
DEAD_COUNT=$(echo "$SCAN" | jq --arg sid "$DEAD_SID" '[.[] | select(.session_id == $sid)] | length')
REMOTE_COUNT=$(echo "$SCAN" | jq --arg sid "$REMOTE_SID" '[.[] | select(.session_id == $sid)] | length')

assert "1. alive local PID remains visible" "[ '$ALIVE_COUNT' = '1' ]"
assert "2. dead local PID is filtered immediately" "[ '$DEAD_COUNT' = '0' ]"
assert "3. non-local host PID is not filtered by local ps" "[ '$REMOTE_COUNT' = '1' ]"
assert "4. active count excludes only the local dead PID" "[ '$COUNT' = '2' ]"

echo "=== $SUITE: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
