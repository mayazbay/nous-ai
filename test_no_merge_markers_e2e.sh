#!/bin/bash
# tools/test_no_merge_markers_e2e.sh — regression tests for staged/index marker scanning.

set -u

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$TOOLS_DIR/test_no_merge_markers.sh"
TMP_DIR="$(mktemp -d)"
FAIL=0

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  FAIL=1
}

cd "$TMP_DIR" || exit 1
git init -q
git config user.email "test@example.invalid"
git config user.name "merge-marker-test"

{
  printf '%s\n' 'ok'
  printf '%s\n' '<<<<<<< ours'
  printf '%s\n' 'bad staged blob'
  printf '%s\n' '======='
  printf '%s\n' 'bad other side'
  printf '%s\n' '>>>>>>> theirs'
} > a.txt
git add a.txt

# Critical regression: the worktree is clean, but the staged blob is still bad.
printf 'ok\n' > a.txt

OUT_BAD=$(bash "$SCRIPT" --staged 2>&1)
RC_BAD=$?
if [ "$RC_BAD" -eq 0 ]; then
  fail "--staged passed even though the index blob still has conflict markers"
fi
echo "$OUT_BAD" | grep -q 'a.txt' || {
  fail "--staged failure did not report the marker-bearing path"
}

git add a.txt
OUT_GOOD=$(bash "$SCRIPT" --staged 2>&1)
RC_GOOD=$?
if [ "$RC_GOOD" -ne 0 ]; then
  fail "--staged failed after the cleaned blob was staged: $OUT_GOOD"
fi

{
  printf '%s\n' '<<<<<<< ours'
  printf '%s\n' 'bad worktree'
  printf '%s\n' '======='
  printf '%s\n' 'bad worktree'
  printf '%s\n' '>>>>>>> theirs'
} > a.txt
OUT_TRACKED=$(bash "$SCRIPT" 2>&1)
RC_TRACKED=$?
if [ "$RC_TRACKED" -eq 0 ]; then
  fail "tracked scan passed even though the worktree has conflict markers"
fi
echo "$OUT_TRACKED" | grep -q 'a.txt' || {
  fail "tracked scan failure did not report the marker-bearing path"
}

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi

echo "OK: no-merge-marker staged/index regression covered"
