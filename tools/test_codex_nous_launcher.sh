#!/bin/bash
# tools/test_codex_nous_launcher.sh — prove local Codex launcher self-registers before exec.
set -u
PASS=0
FAIL=0
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="codex-nous-launcher"
TMP_DIR=$(mktemp -d "/tmp/$SUITE-XXXXXX")
SID_FILE="$TMP_DIR/session-id"
SID_DIR="$TMP_DIR/session-active"
FAKE_CODEX="$TMP_DIR/codex"
FAKE_LOG="$TMP_DIR/fake-codex.log"
TEST_REGISTRY="/Users/madia/nous-agaas/state/test-active-sessions-$SUITE-$$.jsonl"

export SESSION_REGISTRY_PATH="$TEST_REGISTRY"
export SESSION_ID_FILE="$SID_FILE"
export SESSION_ID_DIR="$SID_DIR"
export CODEX_BIN="$FAKE_CODEX"
export CODEX_SESSION_INTENT="local interactive Codex test"
export CODEX_SESSION_SCOPE="tools/codex-nous.sh"
export SESSION_SCAN_FILTER_DEAD_LOCAL_PID=0

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

cat > "$FAKE_CODEX" <<'SH'
#!/bin/bash
echo "fake-codex:$*" >> "$FAKE_LOG"
exit 0
SH
chmod +x "$FAKE_CODEX"

echo "=== $SUITE ==="
mkdir -p "$SID_DIR"
air_cmd "mkdir -p \"$(dirname "$TEST_REGISTRY")\" && : > \"$TEST_REGISTRY\"" 2>/dev/null

OUT=$(SESSION_NUM=83 SESSION_PID=99101 FAKE_LOG="$FAKE_LOG" bash "$TOOLS_DIR/codex-nous.sh" --smoke 2>&1)
RC=$?
SID=$(cat "$SID_FILE" 2>/dev/null || true)
COUNT=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
INTENT=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq -r '.[0].register.intent // empty')
SCOPE=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq -r '.[0].register.declared_scope[0] // empty')

assert "1a. launcher exits with codex process status" "[ '$RC' = '0' ]"
assert "1b. launcher writes session id file" "echo '$SID' | grep -q '^s83-'"
assert "1c. launcher creates one active registry record" "[ '$COUNT' = '1' ]"
assert "1d. launcher uses Codex intent" "[ '$INTENT' = 'local interactive Codex test' ]"
assert "1e. launcher preserves declared scope" "[ '$SCOPE' = 'tools/codex-nous.sh' ]"
assert "1f. launcher execs configured Codex binary with args" "grep -q '^fake-codex:--smoke$' '$FAKE_LOG'"
assert "1g. launcher reports registration before Codex exec" "echo '$OUT' | grep -q 'registered:'"

bash "$TOOLS_DIR/session_close.sh" --session-id "$SID" 2>/dev/null
COUNT2=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
assert "2. fixture session closes cleanly" "[ '$COUNT2' = '0' ]"

echo "=== $SUITE: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
