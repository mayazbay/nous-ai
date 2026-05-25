#!/bin/bash
# Test harness for tools/pre_commit_lane_check.sh
# Each test creates a fresh tmp git repo, populates lane-locks.json directly,
# stages files, runs the hook, asserts the exit code.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$REPO_ROOT/tools/pre_commit_lane_check.sh"
LANE_LOCK="$REPO_ROOT/tools/lane_lock.py"

FAILS=0
PASSES=0

assert_exit() {
  local expected="$1"
  local actual="$2"
  local label="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  ✓ $label"
    PASSES=$((PASSES+1))
  else
    echo "  ✗ $label — expected exit $expected, got $actual"
    FAILS=$((FAILS+1))
  fi
}

mk_repo() {
  local d="$1"
  rm -rf "$d"
  mkdir -p "$d/tools" "$d/pages/systems" "$d/logs"
  cd "$d"
  git init -q
  git config user.email t@e
  git config user.name t
  # Symlink the tools we need
  ln -s "$LANE_LOCK" tools/lane_lock.py 2>/dev/null || true
  cp "$LANE_LOCK" tools/lane_lock.py 2>/dev/null || true
  echo "test" > a.txt
  git add a.txt
  git commit -qm initial
}

echo "=== test 1: no staged files → exit 0 ==="
TMP=$(mktemp -d); mk_repo "$TMP"
(cd "$TMP" && bash "$HOOK"; echo $? > exit)
assert_exit "0" "$(cat $TMP/exit)" "no staged files"
rm -rf "$TMP"

echo "=== test 2: lane_lock.py missing → exit 0 (graceful Ship-2 rollout) ==="
TMP=$(mktemp -d); mk_repo "$TMP"
rm "$TMP/tools/lane_lock.py"
echo "x" > "$TMP/staged.txt"
(cd "$TMP" && git add staged.txt && bash "$HOOK"; echo $? > exit)
assert_exit "0" "$(cat $TMP/exit)" "lane_lock missing → pass"
rm -rf "$TMP"

echo "=== test 3: NOUS_LANE unset + no active locks → exit 0 (single-agent mode) ==="
TMP=$(mktemp -d); mk_repo "$TMP"
echo "x" > "$TMP/staged.txt"
(cd "$TMP" && git add staged.txt && unset NOUS_LANE; bash "$HOOK"; echo $? > exit)
assert_exit "0" "$(cat $TMP/exit)" "no lane + no active locks"
rm -rf "$TMP"

echo "=== test 4: lane set but no token for lane → exit 7 ==="
TMP=$(mktemp -d); mk_repo "$TMP"
echo "x" > "$TMP/staged.txt"
(cd "$TMP" && git add staged.txt && NOUS_LANE=claude bash "$HOOK"; echo $? > exit)
assert_exit "7" "$(cat $TMP/exit)" "lane set, no token → exit 7"
rm -rf "$TMP"

echo "=== test 5: invalid lane name → exit 7 ==="
TMP=$(mktemp -d); mk_repo "$TMP"
echo "x" > "$TMP/staged.txt"
(cd "$TMP" && git add staged.txt && NOUS_LANE=bogus bash "$HOOK"; echo $? > exit)
assert_exit "7" "$(cat $TMP/exit)" "invalid lane → exit 7"
rm -rf "$TMP"

echo "=== test 6: lane has lock for matching scope → exit 0 ==="
TMP=$(mktemp -d); mk_repo "$TMP"
echo "x" > "$TMP/tools/something.py"
(cd "$TMP" && \
  python3 tools/lane_lock.py acquire --lane claude --scope 'tools/*' --ttl-sec 600 > tok.txt && \
  git add tools/something.py && \
  NOUS_LANE=claude bash "$HOOK"; echo $? > exit)
assert_exit "0" "$(cat $TMP/exit)" "lane with matching scope → exit 0"
rm -rf "$TMP"

echo "=== test 7: lane has lock but scope MISMATCH → exit 7 ==="
TMP=$(mktemp -d); mk_repo "$TMP"
echo "x" > "$TMP/tools/something.py"
echo "y" > "$TMP/pages/audits/foo.md"
mkdir -p "$TMP/pages/audits"
(cd "$TMP" && \
  python3 tools/lane_lock.py acquire --lane claude --scope 'tools/*' --ttl-sec 600 > tok.txt && \
  git add tools/something.py pages/audits/foo.md && \
  NOUS_LANE=claude bash "$HOOK"; echo $? > exit)
assert_exit "7" "$(cat $TMP/exit)" "scope mismatch → exit 7"
rm -rf "$TMP"

echo ""
echo "=== summary: $PASSES passed, $FAILS failed ==="
[ "$FAILS" -eq 0 ]
