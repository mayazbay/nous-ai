#!/bin/bash
# Functional test harness for tools/pre-push-sanity.sh.
# Exercises 4 canonical scenarios:
#   1. IN-SYNC          live == vault MD5           → exit 0 (pass)
#   2. LIVE-AHEAD       live != vault MD5           → exit 1 (block)
#   3. VAULT-ORPHAN     vault has file, no live     → exit 0 (skip — not drift)
#   4. LIVE-ORPHAN      live has file, no vault     → exit 0 (skip — not tracked)
#
# Run: cd <vault> && bash tools/test_pre_push_sanity.sh
# Prints one PASS/FAIL per scenario + final summary. Exits 0 if all pass, 1 if any fail.

set -u

HOOK="$(git rev-parse --show-toplevel)/tools/pre-push-sanity.sh"
if [ ! -x "$HOOK" ]; then
  echo "FAIL: pre-push-sanity.sh not found or not executable at $HOOK"
  exit 1
fi

# Set up isolated test sandbox
TMPROOT=$(mktemp -d)
trap "rm -rf '$TMPROOT'" EXIT

# Fake HOME for tests — redirects $HOME/.claude/hooks/
export HOME="$TMPROOT/home"
mkdir -p "$HOME/.claude/hooks"

# Fake vault repo with tools/ dir
FAKE_REPO="$TMPROOT/fake_vault"
mkdir -p "$FAKE_REPO/tools"
git -C "$FAKE_REPO" init -q 2>&1 > /dev/null
# Need a commit so rev-parse --show-toplevel works
( cd "$FAKE_REPO" && git commit --allow-empty -q -m init 2>&1 > /dev/null )

cp "$HOOK" "$FAKE_REPO/tools/pre-push-sanity.sh"

PASS=0
FAIL=0
run_scenario() {
  local name="$1"
  local expected_exit="$2"
  local actual_exit

  # Clean sandbox between scenarios
  rm -f "$HOME/.claude/hooks"/*.sh
  rm -f "$FAKE_REPO/tools"/*.sh
  cp "$HOOK" "$FAKE_REPO/tools/pre-push-sanity.sh"

  "$3"  # scenario setup function

  # Run the hook as git would: cwd = repo root, with stdin (pre-push receives refs on stdin)
  ( cd "$FAKE_REPO" && echo "refs/heads/main $(git rev-parse HEAD) refs/heads/main 0000000000000000000000000000000000000000" | bash "$FAKE_REPO/tools/pre-push-sanity.sh" 2>/dev/null )
  actual_exit=$?

  if [ "$actual_exit" = "$expected_exit" ]; then
    echo "PASS: $name  (expected=$expected_exit actual=$actual_exit)"
    PASS=$((PASS+1))
  else
    echo "FAIL: $name  (expected=$expected_exit actual=$actual_exit)"
    FAIL=$((FAIL+1))
  fi
}

# ── Scenario 1: IN-SYNC ──────────────────────────────────
scen1_setup() {
  echo "same content" > "$HOME/.claude/hooks/alpha.sh"
  echo "same content" > "$FAKE_REPO/tools/alpha.sh"
}
run_scenario "1.IN-SYNC (live == vault)" 0 scen1_setup

# ── Scenario 2: LIVE-AHEAD (drift — MUST BLOCK) ─────────
scen2_setup() {
  echo "live is newer" > "$HOME/.claude/hooks/beta.sh"
  echo "vault is older" > "$FAKE_REPO/tools/beta.sh"
}
run_scenario "2.LIVE-AHEAD (drift → block)" 1 scen2_setup

# ── Scenario 3: VAULT-ORPHAN (vault has file, no live) ──
scen3_setup() {
  echo "vault only" > "$FAKE_REPO/tools/gamma.sh"
  # no corresponding live file
}
run_scenario "3.VAULT-ORPHAN (vault only — skip)" 0 scen3_setup

# ── Scenario 4: LIVE-ORPHAN (live has file, no vault) ────
scen4_setup() {
  echo "live only" > "$HOME/.claude/hooks/delta.sh"
  # no corresponding vault file
}
run_scenario "4.LIVE-ORPHAN (live only, not tracked — skip)" 0 scen4_setup

# ── Scenario 5: ESCAPE HATCH (drift + VAULT_PREPUSH_SKIP=1) ─
scen5_setup() {
  echo "live v2" > "$HOME/.claude/hooks/epsilon.sh"
  echo "vault v1" > "$FAKE_REPO/tools/epsilon.sh"
  export VAULT_PREPUSH_SKIP=1
}
scen5_cleanup() {
  unset VAULT_PREPUSH_SKIP
}
run_scenario "5.ESCAPE-HATCH (drift+SKIP=1 → allow)" 0 scen5_setup
scen5_cleanup

# ── Summary ─────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────"
echo "Results: $PASS pass, $FAIL fail"
echo "─────────────────────────────────────────"
[ "$FAIL" -eq 0 ]
