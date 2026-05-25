#!/bin/bash
# tools/test_session_coordination_e2e.sh — sibling test for session-coordination registry v1.
# Per session-coordination spec cut-over criterion #4. Runs locally on Mac (calls Air over SSH).
# Exit 0 = all pass. Exit 1 = one or more fail.
set -u
PASS=0
FAIL=0
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="session-coordination-e2e"
SID_FILE="/tmp/test-session-id-$$"
SID_DIR="/tmp/test-session-active-$$"
TEST_REGISTRY="/Users/madia/nous-agaas/state/test-active-sessions-$SUITE-$$.jsonl"
export SESSION_REGISTRY_PATH="$TEST_REGISTRY"
export SESSION_ID_FILE="$SID_FILE"
export SESSION_ID_DIR="$SID_DIR"
export SESSION_SCAN_FILTER_DEAD_LOCAL_PID=0

on_air() { hostname 2>/dev/null | grep -qi 'air'; }

air_cmd() {
  if on_air; then
    bash -lc "$1"
  else
    ssh -o ConnectTimeout=3 air "$1"
  fi
}

air_run_stdin() {
  if on_air; then
    SESSION_REGISTRY_PATH="$TEST_REGISTRY" bash -s
  else
    ssh -o ConnectTimeout=3 air "SESSION_REGISTRY_PATH=\"$TEST_REGISTRY\" bash -s"
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

init_test_registry() {
  mkdir -p "$SID_DIR"
  air_cmd "mkdir -p \"$(dirname "$TEST_REGISTRY")\" && : > \"$TEST_REGISTRY\"" 2>/dev/null
}

cleanup_test_registry() {
  air_cmd "rm -f \"$TEST_REGISTRY\"" 2>/dev/null
  rm -rf "$SID_FILE" "$SID_DIR" 2>/dev/null
}
trap cleanup_test_registry EXIT

echo "=== $SUITE ==="
init_test_registry  # isolate tests from the live production registry

# Helper to get scan length (precompute to avoid eval-with-spaces issue)
scan_count() { bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length'; }

# 1. fresh-state — empty registry, register session A → 1 active
SESSION_A=$(SESSION_NUM=99 SESSION_PID=98001 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-A" --scope "fileA.md" 2>/dev/null)
assert "1a. fresh-state: register returns session_id" "[ -n '$SESSION_A' ]"
COUNT1=$(scan_count)
assert "1b. fresh-state: 1 active record" "[ '$COUNT1' = '1' ]"

# 2. double-session — register session B → 2 active
SESSION_B=$(SESSION_NUM=99 SESSION_PID=98002 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-B" --scope "fileB.md,fileA.md" 2>/dev/null)
COUNT2=$(scan_count)
assert "2.  double-session: 2 active records" "[ '$COUNT2' = '2' ]"

# 3. overlap detect — A scope=fileA, B scope=fileA+fileB → scan with --overlap-with fileA finds both
OVERLAP_COUNT=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "fileA.md" --json 2>/dev/null | jq 'length')
assert "3.  overlap detect: --overlap-with fileA finds 2 sessions" "[ '$OVERLAP_COUNT' = '2' ]"

# 3b. normalized prefix overlap — Nous/ prefix and parent directory scopes still intersect
SESSION_C=$(SESSION_NUM=99 SESSION_PID=98003 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-C" --scope "Nous/pages/skills" 2>/dev/null)
PREFIX_OVERLAP_COUNT=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "pages/skills/session-coordination/SKILL.md" --json 2>/dev/null | jq 'length')
assert "3b. normalized prefix overlap: Nous/pages/skills matches pages/skills/session-coordination/SKILL.md" "[ '$PREFIX_OVERLAP_COUNT' = '1' ]"
echo "$SESSION_C" > "$SID_FILE"
bash "$TOOLS_DIR/session_close.sh" 2>/dev/null

# 3c. glob overlap — declared glob scopes must intersect exact files, not only exact/glob queries
SESSION_D=$(SESSION_NUM=99 SESSION_PID=98004 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-D" --scope "tools/session_*.sh,pages/skills/*/SKILL.md" 2>/dev/null)
GLOB_TOOL_OVERLAP_COUNT=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "tools/session_scan.sh" --json 2>/dev/null | jq 'length')
GLOB_SKILL_OVERLAP_COUNT=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "pages/skills/session-coordination/SKILL.md" --json 2>/dev/null | jq 'length')
GLOB_QUERY_OVERLAP_COUNT=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "tools/session_*.sh" --json 2>/dev/null | jq 'length')
assert "3c1. glob scope overlap: tools/session_*.sh matches tools/session_scan.sh" "[ '$GLOB_TOOL_OVERLAP_COUNT' = '1' ]"
assert "3c2. glob scope overlap: pages/skills/*/SKILL.md matches concrete skill file" "[ '$GLOB_SKILL_OVERLAP_COUNT' = '1' ]"
assert "3c3. glob query overlap: exact glob still finds matching glob owner" "[ '$GLOB_QUERY_OVERLAP_COUNT' = '1' ]"
echo "$SESSION_D" > "$SID_FILE"
bash "$TOOLS_DIR/session_close.sh" 2>/dev/null

# 4. heartbeat — register A, sleep 2s, heartbeat A → last-activity timestamp moved
echo "$SESSION_A" > "$SID_FILE"
TS_BEFORE=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq -r ".[] | select(.session_id==\"$SESSION_A\") | .last_activity")
sleep 2
bash "$TOOLS_DIR/session_heartbeat.sh" 2>/dev/null
TS_AFTER=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq -r ".[] | select(.session_id==\"$SESSION_A\") | .last_activity")
assert "4.  heartbeat: last_activity advanced" "[ '$TS_AFTER' -gt '$TS_BEFORE' ]"

# 4b. stale active/*.id files with dead local PIDs must not be refreshed into active sessions
STALE_SID="s99-mac-999998-20260512T0000"
air_cmd "printf '%s\n' '{\"op\":\"register\",\"session_id\":\"$STALE_SID\",\"host\":\"mac\",\"started_at\":\"2026-04-19T01:00:00+05:00\",\"intent\":\"stale-pid-test\",\"declared_scope\":[\"stale.md\"]}' >> \"$TEST_REGISTRY\""
echo "$STALE_SID" > "$SID_DIR/$STALE_SID.id"
bash "$TOOLS_DIR/session_heartbeat.sh" 2>/dev/null
STALE_ACTIVE=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq "[.[] | select(.session_id==\"$STALE_SID\")] | length")
assert "4b. heartbeat: dead-PID active ID is not refreshed" "[ '$STALE_ACTIVE' = '0' ]"
rm -f "$SID_DIR/$STALE_SID.id"

# 5. close — A close → active-set drops to 1
bash "$TOOLS_DIR/session_close.sh" 2>/dev/null
COUNT5=$(scan_count)
assert "5.  close: active drops to 1" "[ '$COUNT5' = '1' ]"

# 6. stale-cleanup — backdate remaining records to 2 days ago, run cleanup, B archived
air_cmd "perl -i -pe 's|\"started_at\":\"[^\"]+\"|\"started_at\":\"2026-04-19T01:00:00+05:00\"|g; s|\"ts\":\"[^\"]+\"|\"ts\":\"2026-04-19T01:00:00+05:00\"|g' \"$TEST_REGISTRY\" 2>/dev/null"
air_run_stdin < "$TOOLS_DIR/cron_session_cleanup.sh" 2>/dev/null
ACTIVE_AFTER_CLEANUP=$(scan_count)
assert "6.  stale-cleanup: active=0 after backdate+cleanup" "[ '$ACTIVE_AFTER_CLEANUP' = '0' ]"

# 6b. four-session handshake — controller + three helper lanes are visible, scoped, and clear cleanly
SESSION_CTRL=$(SESSION_NUM=99 SESSION_PID=98100 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-controller" --scope "lane-controller.md" 2>/dev/null)
SESSION_H1=$(SESSION_NUM=99 SESSION_PID=98101 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-helper-1" --scope "lane-helper-1.md" 2>/dev/null)
SESSION_H2=$(SESSION_NUM=99 SESSION_PID=98102 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-helper-2" --scope "lane-helper-2.md" 2>/dev/null)
SESSION_H3=$(SESSION_NUM=99 SESSION_PID=98103 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-helper-3" --scope "lane-helper-3.md" 2>/dev/null)
COUNT6B=$(scan_count)
assert "6b1. four-session handshake: controller + 3 helpers visible" "[ '$COUNT6B' = '4' ]"
H2_OVERLAP=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "lane-helper-2.md" --json 2>/dev/null | jq 'length')
assert "6b2. four-session handshake: overlap finds intended helper only" "[ '$H2_OVERLAP' = '1' ]"
UNRELATED_OVERLAP=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "unowned-file.md" --json 2>/dev/null | jq 'length')
assert "6b3. four-session handshake: unrelated scope is clear" "[ '$UNRELATED_OVERLAP' = '0' ]"
for sid in "$SESSION_CTRL" "$SESSION_H1" "$SESSION_H2" "$SESSION_H3"; do
  bash "$TOOLS_DIR/session_close.sh" --session-id "$sid" 2>/dev/null
done
COUNT6B_CLOSED=$(scan_count)
assert "6b4. four-session handshake: all lanes closed" "[ '$COUNT6B_CLOSED' = '0' ]"

# 7. corrupt-row and orphan-heartbeat tolerance — bad rows do not blind live scan/cleanup
SESSION_C=$(SESSION_NUM=99 SESSION_PID=98003 bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-C" --scope "fileC.md" 2>/dev/null)
air_cmd "printf '%s\n' '{\"op\":\"close\",\"session_id\":\"bad\",\"ts\":\"2026-04-29T11:00:00+\\\\1:\\\\2\"' >> \"$TEST_REGISTRY\""
COUNT7=$(scan_count)
assert "7a. corrupt-row: scanner keeps valid record" "[ '$COUNT7' = '1' ]"
air_cmd "printf '%s\n' '{\"op\":\"heartbeat\",\"session_id\":\"orphan\",\"ts\":\"2026-04-29T11:00:00+05:00\"}' >> \"$TEST_REGISTRY\""
air_run_stdin < "$TOOLS_DIR/cron_session_cleanup.sh" 2>/dev/null
STRICT_AFTER_CORRUPT=$(air_cmd "jq -c . \"$TEST_REGISTRY\" >/dev/null; echo \$?" 2>/dev/null)
COUNT_AFTER_CORRUPT=$(scan_count)
ORPHAN_AFTER_CORRUPT=$(air_cmd "grep -c '\"session_id\":\"orphan\"' \"$TEST_REGISTRY\" 2>/dev/null || true")
assert "7b. corrupt-row: cleanup restores strict JSONL" "[ '$STRICT_AFTER_CORRUPT' = '0' ]"
assert "7c. orphan-heartbeat: cleanup archives no-register records" "[ '$ORPHAN_AFTER_CORRUPT' = '0' ]"
assert "7d. corrupt-row: valid active record remains" "[ '$COUNT_AFTER_CORRUPT' = '1' ]"

# 8. Air-unreachable degradation — scanner must not print a false green.
FAKE_BIN="$(mktemp -d)"
cat > "$FAKE_BIN/ssh" <<'SH'
#!/bin/bash
exit 255
SH
chmod +x "$FAKE_BIN/ssh"
set +e
SCAN_UNREACHABLE=$(SESSION_FORCE_REMOTE=1 PATH="$FAKE_BIN:$PATH" bash "$TOOLS_DIR/session_scan.sh" 2>&1)
SCAN_UNREACHABLE_RC=$?
set -e
rm -rf "$FAKE_BIN"
assert "8a. Air-unreachable scan exits nonzero" "[ '$SCAN_UNREACHABLE_RC' != '0' ]"
assert "8b. Air-unreachable scan is yellow, not false green" "echo '$SCAN_UNREACHABLE' | grep -q 'registry unavailable' && ! echo '$SCAN_UNREACHABLE' | grep -q '✅ no other active sessions'"

echo "=== $SUITE: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
