#!/bin/bash
# test_secret_perms_self.sh — self-test for test_secret_perms.sh
#
# Creates a sandbox directory with mixed-perm .env fixtures and verifies the
# scanner: (1) passes on all-0600, (2) rejects on 0644, (3) ignores template
# files even when they're 0644, (4) returns exit 3 on missing dir.
#
# Absorbed as AP-36 sibling-test for W2 (session 48).

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCANNER="$SCRIPT_DIR/test_secret_perms.sh"
SANDBOX=$(mktemp -d /tmp/test-secret-perms-XXXXXX)
PASS_COUNT=0
FAIL_COUNT=0

cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

check() {
  local name="$1"
  local expected_exit="$2"
  local actual_exit="$3"
  if [ "$actual_exit" = "$expected_exit" ]; then
    echo "  ✅ $name (exit=$actual_exit)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ❌ $name: expected exit=$expected_exit, got $actual_exit"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

echo "=== TEST 1: all .env files are 0600 → expect exit 0 ==="
mkdir -p "$SANDBOX/t1/codebase"
echo "KEY=value" > "$SANDBOX/t1/.env"
echo "APP_URL=x" > "$SANDBOX/t1/codebase/.env"
chmod 0600 "$SANDBOX/t1/.env" "$SANDBOX/t1/codebase/.env"
bash "$SCANNER" "$SANDBOX/t1" >/dev/null 2>&1
check "TEST 1 all-0600" "0" "$?"

echo "=== TEST 2: one .env is 0644 → expect exit 2 ==="
mkdir -p "$SANDBOX/t2/codebase"
echo "KEY=value" > "$SANDBOX/t2/.env"
echo "APP_URL=x" > "$SANDBOX/t2/codebase/.env"
chmod 0600 "$SANDBOX/t2/.env"
chmod 0644 "$SANDBOX/t2/codebase/.env"
bash "$SCANNER" "$SANDBOX/t2" >/dev/null 2>&1
check "TEST 2 drift-detected" "2" "$?"

echo "=== TEST 3: .env.example 0644 ignored → expect exit 0 ==="
mkdir -p "$SANDBOX/t3"
echo "KEY=value" > "$SANDBOX/t3/.env"
echo "KEY=example" > "$SANDBOX/t3/.env.example"
echo "KEY=tmpl" > "$SANDBOX/t3/.env.template"
chmod 0600 "$SANDBOX/t3/.env"
chmod 0644 "$SANDBOX/t3/.env.example" "$SANDBOX/t3/.env.template"
bash "$SCANNER" "$SANDBOX/t3" >/dev/null 2>&1
check "TEST 3 template-exclusion" "0" "$?"

echo "=== TEST 4: missing dir → expect exit 3 ==="
bash "$SCANNER" "$SANDBOX/nonexistent" >/dev/null 2>&1
check "TEST 4 missing-dir" "3" "$?"

echo ""
echo "=== RESULT: $PASS_COUNT PASS / $FAIL_COUNT FAIL ==="
[ "$FAIL_COUNT" = "0" ]
