#!/bin/bash
# tools/test_pending_queue_drain.sh — AP-14 regression: heartbeat drains pending queues.
# Writes only to an isolated Air-side test registry and a temp local pending dir.
set -u
PASS=0
FAIL=0
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="pending-queue-drain"
TMP_DIR="/tmp/test-$SUITE-$$"
SID_FILE="$TMP_DIR/current_session_id"
SID_DIR="$TMP_DIR/active"
PENDING_DIR="$TMP_DIR/pending"
TEST_REGISTRY="/Users/madia/nous-agaas/state/test-active-sessions-$SUITE-$$.jsonl"
export SESSION_REGISTRY_PATH="$TEST_REGISTRY"
export SESSION_ID_FILE="$SID_FILE"
export SESSION_ID_DIR="$SID_DIR"
export SESSION_PENDING_DIR="$PENDING_DIR"

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
  rm -rf "$TMP_DIR" 2>/dev/null
}
trap cleanup EXIT

echo "=== $SUITE ==="
mkdir -p "$SID_DIR" "$PENDING_DIR"
air_cmd "mkdir -p \"$(dirname "$TEST_REGISTRY")\" && : > \"$TEST_REGISTRY\"" 2>/dev/null

LIVE_SID="s83-test-live-heartbeat-$$"
PENDING_REGISTER_SID="s83-test-pending-register-$$"
PENDING_HEARTBEAT_SID="s83-test-pending-heartbeat-$$"
echo "$LIVE_SID" > "$SID_FILE"
echo "$LIVE_SID" > "$SID_DIR/$LIVE_SID.id"

jq -nc --arg sid "$PENDING_REGISTER_SID" \
  '{op:"register", session_id:$sid, host:"mac", pid:99991, started_at:"2026-04-29T15:00:00+05:00", start_head:"test", intent:"pending drain test", declared_scope:["tools/session_heartbeat.sh"], ttl_minutes:180}' \
  > "$PENDING_DIR/pending-registers.jsonl"
jq -nc --arg sid "$PENDING_HEARTBEAT_SID" --arg ts "2026-04-29T15:00:01+05:00" \
  '{op:"heartbeat", session_id:$sid, ts:$ts}' \
  > "$PENDING_DIR/pending-heartbeats.jsonl"

bash "$TOOLS_DIR/session_heartbeat.sh" 2>/dev/null
RC=$?
REGISTRY_RAW=$(air_cmd "cat \"$TEST_REGISTRY\" 2>/dev/null" 2>/dev/null || true)

assert "1. heartbeat exits 0" "[ '$RC' = '0' ]"
assert "2. live heartbeat reached Air test registry" "echo '$REGISTRY_RAW' | grep -q '\"session_id\":\"$LIVE_SID\"'"
assert "3. pending register drained to Air test registry" "echo '$REGISTRY_RAW' | grep -q '\"session_id\":\"$PENDING_REGISTER_SID\"'"
assert "4. pending heartbeat drained to Air test registry" "echo '$REGISTRY_RAW' | grep -q '\"session_id\":\"$PENDING_HEARTBEAT_SID\"'"
assert "5. pending-registers queue truncated" "[ ! -s '$PENDING_DIR/pending-registers.jsonl' ]"
assert "6. pending-heartbeats queue truncated" "[ ! -s '$PENDING_DIR/pending-heartbeats.jsonl' ]"

LOCAL_REGISTRY="$TMP_DIR/local-active-sessions.jsonl"
LOCAL_PENDING_DIR="$TMP_DIR/local-pending"
LOCAL_SID_DIR="$TMP_DIR/local-active"
LOCAL_SID_FILE="$TMP_DIR/local-current-session-id"
LOCAL_LIVE_SID="s83-test-air-local-live-$$"
LOCAL_PENDING_REGISTER_SID="s83-test-air-local-pending-register-$$"
LOCAL_PENDING_HEARTBEAT_SID="s83-test-air-local-pending-heartbeat-$$"
mkdir -p "$LOCAL_PENDING_DIR" "$LOCAL_SID_DIR"
: > "$LOCAL_REGISTRY"
echo "$LOCAL_LIVE_SID" > "$LOCAL_SID_FILE"
echo "$LOCAL_LIVE_SID" > "$LOCAL_SID_DIR/$LOCAL_LIVE_SID.id"

jq -nc --arg sid "$LOCAL_PENDING_REGISTER_SID" \
  '{op:"register", session_id:$sid, host:"air", pid:99992, started_at:"2026-04-29T15:00:00+05:00", start_head:"test", intent:"air-local drain test", declared_scope:["tools/session_heartbeat.sh"], ttl_minutes:180}' \
  > "$LOCAL_PENDING_DIR/pending-registers.jsonl"
jq -nc --arg sid "$LOCAL_PENDING_HEARTBEAT_SID" --arg ts "2026-04-29T15:00:02+05:00" \
  '{op:"heartbeat", session_id:$sid, ts:$ts}' \
  > "$LOCAL_PENDING_DIR/pending-heartbeats.jsonl"

SESSION_FORCE_AIR_LOCAL=1 \
SESSION_REGISTRY_PATH="$LOCAL_REGISTRY" \
SESSION_ID_FILE="$LOCAL_SID_FILE" \
SESSION_ID_DIR="$LOCAL_SID_DIR" \
SESSION_PENDING_DIR="$LOCAL_PENDING_DIR" \
  bash "$TOOLS_DIR/session_heartbeat.sh" 2>/dev/null
LOCAL_RC=$?
LOCAL_REGISTRY_RAW=$(cat "$LOCAL_REGISTRY" 2>/dev/null || true)

assert "7. Air-local heartbeat exits 0" "[ '$LOCAL_RC' = '0' ]"
assert "8. Air-local live heartbeat reached local registry" "echo '$LOCAL_REGISTRY_RAW' | grep -q '\"session_id\":\"$LOCAL_LIVE_SID\"'"
assert "9. Air-local pending register drained" "echo '$LOCAL_REGISTRY_RAW' | grep -q '\"session_id\":\"$LOCAL_PENDING_REGISTER_SID\"'"
assert "10. Air-local pending heartbeat drained" "echo '$LOCAL_REGISTRY_RAW' | grep -q '\"session_id\":\"$LOCAL_PENDING_HEARTBEAT_SID\"'"
assert "11. Air-local pending-registers queue truncated" "[ ! -s '$LOCAL_PENDING_DIR/pending-registers.jsonl' ]"
assert "12. Air-local pending-heartbeats queue truncated" "[ ! -s '$LOCAL_PENDING_DIR/pending-heartbeats.jsonl' ]"

echo "=== $SUITE: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
