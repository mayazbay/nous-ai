#!/bin/bash
# tools/test_session_self_register.sh — focused regression tests for AP-13 re-registration.
# Runs locally on Mac and writes to an isolated Air-side test registry path.
set -u
PASS=0
FAIL=0
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="session-self-register"
SID_FILE="/tmp/test-session-self-register-id-$$"
SID_DIR="/tmp/test-session-self-register-active-$$"
TEST_REGISTRY="/Users/madia/nous-agaas/state/test-active-sessions-$SUITE-$$.jsonl"
export SESSION_REGISTRY_PATH="$TEST_REGISTRY"
export SESSION_ID_FILE="$SID_FILE"
export SESSION_ID_DIR="$SID_DIR"

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

echo "=== $SUITE ==="
mkdir -p "$SID_DIR"
air_cmd "mkdir -p \"$(dirname "$TEST_REGISTRY")\" && : > \"$TEST_REGISTRY\"" 2>/dev/null

OUT1=$(SESSION_NUM=83 SESSION_PID=99001 bash "$TOOLS_DIR/session_self_register.sh" --intent "self-register-test" --scope "tools/session_self_register.sh" 2>&1)
RC1=$?
SID1=$(cat "$SID_FILE" 2>/dev/null || true)
COUNT1=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
assert "1a. initial run exits 0" "[ '$RC1' = '0' ]"
assert "1b. initial run writes session id file" "echo '$SID1' | grep -q '^s83-'"
assert "1c. initial run creates one active record" "[ '$COUNT1' = '1' ]"
assert "1d. initial run reports registered" "echo '$OUT1' | grep -q 'registered:'"

OUT2=$(SESSION_NUM=83 SESSION_PID=99002 bash "$TOOLS_DIR/session_self_register.sh" --intent "self-register-test-2" --scope "other" 2>&1)
RC2=$?
SID2=$(cat "$SID_FILE" 2>/dev/null || true)
COUNT2=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
assert "2a. idempotent run exits 0" "[ '$RC2' = '0' ]"
assert "2b. idempotent run keeps same session id" "[ '$SID2' = '$SID1' ]"
assert "2c. idempotent run does not add active record" "[ '$COUNT2' = '1' ]"
assert "2d. idempotent run reports already registered" "echo '$OUT2' | grep -q 'already registered:'"

OUT3=$(SESSION_NUM=83 SESSION_PID=99003 bash "$TOOLS_DIR/session_self_register.sh" --force --intent "self-register-forced" --scope "forced" 2>&1)
RC3=$?
SID3=$(cat "$SID_FILE" 2>/dev/null || true)
COUNT3=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
assert "3a. forced run exits 0" "[ '$RC3' = '0' ]"
assert "3b. forced run writes a new session id" "[ '$SID3' != '$SID1' ]"
assert "3c. forced run adds second active record" "[ '$COUNT3' = '2' ]"
assert "3d. forced run reports registered" "echo '$OUT3' | grep -q 'registered:'"

bash "$TOOLS_DIR/session_close.sh" --session-id "$SID1" 2>/dev/null
bash "$TOOLS_DIR/session_close.sh" --session-id "$SID3" 2>/dev/null
COUNT4=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
assert "4. close both self-register fixtures" "[ '$COUNT4' = '0' ]"

echo "$SID3" > "$SID_FILE"
OUT4B=$(SESSION_NUM=83 SESSION_PID=99005 bash "$TOOLS_DIR/session_self_register.sh" --intent "closed-sid-reregister" --scope "closed" 2>&1)
RC4B=$?
SID4B=$(cat "$SID_FILE" 2>/dev/null || true)
COUNT4B=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
assert "4b1. closed sid run exits 0" "[ '$RC4B' = '0' ]"
assert "4b2. closed sid does not suppress re-registration" "[ '$SID4B' != '$SID3' ]"
assert "4b3. closed sid creates an active replacement" "[ '$COUNT4B' = '1' ]"
assert "4b4. closed sid reports re-registering" "echo '$OUT4B' | grep -q 'no active entry'"
bash "$TOOLS_DIR/session_close.sh" --session-id "$SID4B" 2>/dev/null

OUT4C=$(SESSION_NUM=83 SESSION_PID=99006 CODEX_SESSION_INTENT="codex-env-intent" CODEX_SESSION_SCOPE="codex-env-scope" bash "$TOOLS_DIR/session_self_register.sh" --force 2>&1)
RC4C=$?
SID4C=$(cat "$SID_FILE" 2>/dev/null || true)
SCAN4C=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null)
INTENT4C=$(echo "$SCAN4C" | jq -r --arg sid "$SID4C" '.[]? | select(.session_id == $sid) | .register.intent')
SCOPE4C=$(echo "$SCAN4C" | jq -r --arg sid "$SID4C" '.[]? | select(.session_id == $sid) | .register.declared_scope[0]')
assert "4c1. Codex env-alias run exits 0" "[ '$RC4C' = '0' ]"
assert "4c2. Codex env-alias writes session id" "echo '$SID4C' | grep -q '^s83-'"
assert "4c3. Codex env-alias preserves intent" "[ '$INTENT4C' = 'codex-env-intent' ]"
assert "4c4. Codex env-alias preserves scope" "[ '$SCOPE4C' = 'codex-env-scope' ]"
bash "$TOOLS_DIR/session_close.sh" --session-id "$SID4C" 2>/dev/null

FAKE_HOME="/tmp/test-session-self-register-home-$$"
FAKE_BIN="/tmp/test-session-self-register-bin-$$"
QUEUE_SID_FILE="/tmp/test-session-self-register-queued-id-$$"
QUEUE_SID_DIR="/tmp/test-session-self-register-queued-active-$$"
mkdir -p "$FAKE_HOME" "$FAKE_BIN" "$QUEUE_SID_DIR"
cat > "$FAKE_BIN/ssh" <<'SH'
#!/bin/bash
exit 255
SH
chmod +x "$FAKE_BIN/ssh"
OUT5=$(HOME="$FAKE_HOME" PATH="$FAKE_BIN:$PATH" SESSION_REGISTRY_PATH="/dev/null/unreachable-registry-$$.jsonl" SESSION_ID_FILE="$QUEUE_SID_FILE" SESSION_ID_DIR="$QUEUE_SID_DIR" SESSION_NUM=83 SESSION_PID=99004 bash "$TOOLS_DIR/session_self_register.sh" --force --intent "queued-register-test" --scope "queued" 2>&1)
RC5=$?
SID5=$(cat "$QUEUE_SID_FILE" 2>/dev/null || true)
PENDING5="$FAKE_HOME/.claude/sessions/pending-registers.jsonl"
assert "5a. queued run exits 0 for non-blocking degraded mode" "[ '$RC5' = '0' ]"
assert "5b. queued run writes session id for heartbeat drain" "echo '$SID5' | grep -q '^s83-'"
assert "5c. queued run reports not centrally visible" "echo '$OUT5' | grep -q 'not centrally visible'"
assert "5d. queued run does not claim registered" "! echo '$OUT5' | grep -q '✅ registered:'"
assert "5e. queued register lands in pending queue" "[ -s '$PENDING5' ]"
rm -rf "$FAKE_HOME" "$FAKE_BIN" "$QUEUE_SID_FILE" "$QUEUE_SID_DIR" 2>/dev/null

echo "=== $SUITE: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
