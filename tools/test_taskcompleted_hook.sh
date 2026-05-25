#!/bin/bash
# Smoke-test battery for ~/.claude/hooks/task-completed-enforce.sh
#
# Run this any time the hook is modified. Each test case has a known expected
# result. Non-zero exit from this script = regression.
#
# Usage:
#   ./tools/test_taskcompleted_hook.sh
#
# Reference: AUDIT-026 Phase 1 deliverable.

set -u
HOOK="$HOME/.claude/hooks/task-completed-enforce.sh"

if [ ! -x "$HOOK" ]; then
  echo "FAIL: hook not found or not executable at $HOOK"
  exit 1
fi

PASSED=0
FAILED=0

run_test() {
  local name="$1"
  local expected_exit="$2"
  local input="$3"
  local expected_pattern="${4:-}"

  local output
  output=$(echo "$input" | "$HOOK" 2>&1)
  local actual_exit=$?

  if [ "$actual_exit" = "$expected_exit" ]; then
    if [ -z "$expected_pattern" ] || echo "$output" | grep -q "$expected_pattern"; then
      echo "PASS: $name"
      PASSED=$((PASSED + 1))
    else
      echo "FAIL: $name — exit ok but pattern '$expected_pattern' not found in output:"
      echo "$output" | sed 's/^/  /'
      FAILED=$((FAILED + 1))
    fi
  else
    echo "FAIL: $name — expected exit $expected_exit, got $actual_exit:"
    echo "$output" | sed 's/^/  /'
    FAILED=$((FAILED + 1))
  fi
}

# Test 1: Vault task, clean state → PASS
run_test "vault-task-clean" 0 \
  '{"task_subject":"write audit-xxx documentation","task_description":"lesson and audit work","task_id":"t1"}'

# Test 2: Product task missing REQ + business tag → BLOCK Gates 1+2
run_test "product-task-missing-req" 2 \
  '{"task_subject":"implement camera registry page","task_description":"build the camera list frontend","task_id":"t2"}' \
  "GATE 1"

# Test 3: Product task with REQ-xxx + business tag → PASS
run_test "product-task-with-req-and-tag" 0 \
  '{"task_subject":"implement REQ-042 camera registry","task_description":"build the camera list [risk]","task_id":"t3"}'

# Test 4: Bug-fix task with recent LESSONs in git history → PASS
run_test "bugfix-with-recent-lessons" 0 \
  '{"task_subject":"fix a bug in telegram_poll","task_description":"root cause resolved silent failure","task_id":"t4"}'

# Test 5: Vault task with sync keyword → PASS (or WARN on temporal lag, not block)
run_test "vault-sync-task" 0 \
  '{"task_subject":"audit task with sync check","task_description":"audit something and push commit","task_id":"t5"}'

# Test 6: Bug-fix task but task text says the fix is still WIP → allows through
# (because recent LESSONs exist in history; Gate 8 is "any lesson in 24h" not "matching lesson")
run_test "bugfix-wip" 0 \
  '{"task_subject":"debug regression in ingest","task_description":"need to find root cause","task_id":"t6"}'

echo ""
echo "─────────────────────────────"
echo "Smoke tests: $PASSED passed, $FAILED failed"
if [ "$FAILED" -gt 0 ]; then
  exit 1
fi
exit 0
