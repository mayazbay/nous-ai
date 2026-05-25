#!/bin/bash
# test_pre_commit_env_block.sh — sibling-test for pre-commit RULE 6 (AP-45)
#
# Validates that the pre-commit hook blocks `.env` file additions to the vault
# while allowing `.env.example` / `.env.template` / `.env.sample` template forms.
#
# Runs 4 scenarios via sandbox git repo (doesn't touch live vault):
#   TEST 1: stage a .env file → hook exits 1 (BLOCKED)
#   TEST 2: stage a .env.example → hook exits 0 (ACCEPTED)
#   TEST 3: stage a .env.template → hook exits 0 (ACCEPTED)
#   TEST 4: stage a weirdly-named secret.env → hook exits 1 (BLOCKED)
#
# Session 48 D7 (2026-04-18) — closes AP-36 drift on W4.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/pre-commit-hook-tan-pattern.sh"
SANDBOX=$(mktemp -d /tmp/test-pre-commit-env-XXXXXX)
PASS_COUNT=0
FAIL_COUNT=0

cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

if [ ! -x "$HOOK" ]; then
  echo "ERROR: $HOOK missing or not executable" >&2
  exit 3
fi

# bootstrap sandbox git repo
cd "$SANDBOX"
git init -q
# match the hook's git diff --cached expectation
git config user.name "test" >/dev/null 2>&1
git config user.email "test@test.local" >/dev/null 2>&1
# minimal initial commit so --cached works
echo "init" > README.md
git add README.md >/dev/null 2>&1
git commit -q -m "init" --allow-empty-message 2>/dev/null || git commit -q -m "init" 2>/dev/null

check() {
  local name="$1"
  local expected_exit="$2"
  local actual_exit="$3"
  if [ "$actual_exit" = "$expected_exit" ]; then
    echo "  ✅ $name (exit=$actual_exit as expected)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ❌ $name (expected=$expected_exit, got=$actual_exit)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

echo "=== TEST 1: stage .env → expect REJECT (exit 1) ==="
echo "KEY=val" > .env
git add -f .env >/dev/null 2>&1
bash "$HOOK" >/dev/null 2>&1
RC=$?
check "TEST 1 .env rejected" "1" "$RC"
git reset -q HEAD .env 2>/dev/null
rm -f .env

echo "=== TEST 2: stage .env.example → expect ACCEPT (exit 0) ==="
echo "KEY=template" > .env.example
git add .env.example >/dev/null 2>&1
bash "$HOOK" >/dev/null 2>&1
RC=$?
check "TEST 2 .env.example accepted" "0" "$RC"
git reset -q HEAD .env.example 2>/dev/null
rm -f .env.example

echo "=== TEST 3: stage .env.template → expect ACCEPT (exit 0) ==="
echo "KEY=template" > .env.template
git add .env.template >/dev/null 2>&1
bash "$HOOK" >/dev/null 2>&1
RC=$?
check "TEST 3 .env.template accepted" "0" "$RC"
git reset -q HEAD .env.template 2>/dev/null
rm -f .env.template

echo "=== TEST 4: stage weirdly-named secret.env → expect REJECT ==="
echo "KEY=secret" > secret.env
git add -f secret.env >/dev/null 2>&1
bash "$HOOK" >/dev/null 2>&1
RC=$?
check "TEST 4 secret.env rejected" "1" "$RC"
git reset -q HEAD secret.env 2>/dev/null
rm -f secret.env

echo ""
echo "=== RESULT: $PASS_COUNT PASS / $FAIL_COUNT FAIL ==="
[ "$FAIL_COUNT" = "0" ]
