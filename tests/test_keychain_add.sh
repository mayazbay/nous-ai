#!/bin/bash
# Test secrets-keychain-add.swift — add a throwaway secret via stdin,
# read it back via security CLI, verify value matches, then delete.
set -euo pipefail

[[ "$(uname -s)" == "Darwin" ]] || { echo "SKIP: Mac-only"; exit 0; }

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/secrets-keychain-add.swift"
[ -f "$SCRIPT" ] || { echo "FAIL: $SCRIPT not found"; exit 1; }
[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

TEST_KEY="nous-agaas-test/t-$$-$(date +%s)"
TEST_VALUE="secret-$$-$(openssl rand -hex 8)"

# Cleanup on exit regardless of outcome
trap 'security delete-generic-password -s "$TEST_KEY" -a nous 2>/dev/null; true' EXIT

# Add via stdin (local-only; --icloud tested separately)
echo -n "$TEST_VALUE" | "$SCRIPT" "$TEST_KEY"

# Read back via standard security CLI
READ_BACK=$(security find-generic-password -s "$TEST_KEY" -a nous -w 2>/dev/null || echo "NOTFOUND")

if [ "$READ_BACK" = "$TEST_VALUE" ]; then
  echo "OK: add + read match"
  exit 0
else
  echo "FAIL: got '$READ_BACK' expected '$TEST_VALUE'"
  exit 1
fi
