#!/bin/bash
# Test secrets-keychain-read.sh — must emit the value (no trailing \n) to stdout.
set -euo pipefail
[[ "$(uname -s)" == "Darwin" ]] || { echo "SKIP: Mac-only"; exit 0; }

READER="$(cd "$(dirname "$0")/.." && pwd)/secrets-keychain-read.sh"
ADDER="$(cd "$(dirname "$0")/.." && pwd)/secrets-keychain-add.swift"
[ -x "$READER" ] || { echo "FAIL: $READER not executable"; exit 1; }

TEST_KEY_SHORT="t-$$-$(date +%s)"
TEST_KEY_FULL="nous-agaas/$TEST_KEY_SHORT"
TEST_VALUE="val-$$-$(openssl rand -hex 8)"

trap 'security delete-generic-password -s "$TEST_KEY_FULL" -a nous 2>/dev/null; true' EXIT

echo -n "$TEST_VALUE" | "$ADDER" "$TEST_KEY_FULL"

READ_BACK=$("$READER" "$TEST_KEY_SHORT")

if [ "$READ_BACK" = "$TEST_VALUE" ]; then
  echo "OK: reader returns exact value"
  exit 0
else
  echo "FAIL: got '$READ_BACK' expected '$TEST_VALUE'"
  exit 1
fi
