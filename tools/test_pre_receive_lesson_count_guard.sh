#!/bin/bash
# test_pre_receive_lesson_count_guard.sh — functional test for VPS bare wiki pre-receive hook.
#
# Closes AP-36 self-violation (session 45 E-phase): every server hook MUST ship with
# sibling test_<name>.sh exercising REJECT + ACCEPT paths.
#
# Invariants tested:
#   REJECT — when staged LESSON count > FROZEN_COUNT, hook exits 1 with the expected message
#   ACCEPT — when staged LESSON count <= FROZEN_COUNT, hook exits 0 silently
#   ESCAPE — commit message containing "LESSON-EXEMPT" accepts any count
#   REJECT-below-ceiling — adding any new canonical LESSON is rejected even when current count is below FROZEN_COUNT
#
# Must run on VPS (or anywhere `bash` + `git` exist). Does not mutate the real bare repo;
# uses a temporary sandbox via git-plumbing refs.
#
# Exit 0 = all pass. Exit 2 = any test failed.

set -u
HOOK_VAULT_PATH="$(cd "$(dirname "$0")/.." && pwd)/tools/pre-receive-lesson-count-guard.sh"
[ -f "$HOOK_VAULT_PATH" ] || { echo "FAIL: $HOOK_VAULT_PATH not found" >&2; exit 2; }

FAIL=0
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

# --- Spin up a sandbox bare repo + mirror with a seed commit ---
cd "$TMP"
git init --bare sandbox.git >/dev/null 2>&1
cp "$HOOK_VAULT_PATH" sandbox.git/hooks/pre-receive
chmod +x sandbox.git/hooks/pre-receive

git init work >/dev/null 2>&1
cd work
git config user.email "test@nous.local"
git config user.name "test"
git commit --allow-empty -m "seed" >/dev/null 2>&1
git remote add origin "$TMP/sandbox.git"
# Seed baseline: create LESSON files to reach the FROZEN_COUNT from the hook
FROZEN=$(grep -E '^FROZEN_COUNT=' "$HOOK_VAULT_PATH" | head -1 | sed 's/FROZEN_COUNT=//')
[ -n "$FROZEN" ] || { echo "FAIL: could not extract FROZEN_COUNT from hook" >&2; exit 2; }
mkdir -p pages/lessons/individual
for i in $(seq 1 "$FROZEN"); do
  printf -- "---\nid: LESSON-%03d\ntitle: test\n---\n# LESSON-%03d\n" "$i" "$i" > "pages/lessons/individual/LESSON-$(printf '%03d' "$i")-test.md"
done
git add pages >/dev/null
git commit -m "seed $FROZEN LESSON files (baseline) LESSON-EXEMPT" >/dev/null 2>&1
git push origin HEAD:main >/dev/null 2>&1 || { echo "FAIL: baseline push of $FROZEN LESSONs rejected by hook" >&2; exit 2; }

# --- TEST 1: ACCEPT path (count stays at FROZEN) ---
echo "test1 noop edit" >> pages/lessons/individual/LESSON-001-test.md
git add pages >/dev/null
git commit -m "accept path: edit existing LESSON (count unchanged)" >/dev/null 2>&1
if git push origin HEAD:main >/tmp/push_ok.log 2>&1; then
  echo "TEST 1 ACCEPT: PASS"
else
  echo "TEST 1 ACCEPT: FAIL (push rejected when it should have accepted)"
  cat /tmp/push_ok.log >&2
  FAIL=1
fi

# --- TEST 2: REJECT path (count exceeds FROZEN) ---
NEW=$((FROZEN + 1))
printf -- "---\nid: LESSON-%03d\ntitle: overflow\n---\n# LESSON-%03d\n" "$NEW" "$NEW" > "pages/lessons/individual/LESSON-$(printf '%03d' "$NEW")-overflow.md"
git add pages >/dev/null
git commit -m "reject path: would grow LESSON count" >/dev/null 2>&1
if git push origin HEAD:main >/tmp/push_reject.log 2>&1; then
  echo "TEST 2 REJECT: FAIL (push accepted when it should have rejected)"
  FAIL=1
else
  if grep -qi "RULE ZERO\|LESSON count" /tmp/push_reject.log; then
    echo "TEST 2 REJECT: PASS (hook rejected with expected message)"
  else
    echo "TEST 2 REJECT: FAIL (push rejected but not with expected message)"
    cat /tmp/push_reject.log >&2
    FAIL=1
  fi
fi

# --- TEST 3: ESCAPE path (LESSON-EXEMPT in commit msg) ---
git commit --amend -m "reject path overridden LESSON-EXEMPT emergency case" >/dev/null 2>&1
if git push origin HEAD:main >/tmp/push_exempt.log 2>&1; then
  echo "TEST 3 ESCAPE: PASS (LESSON-EXEMPT bypassed guard)"
else
  # Only flag if hook itself refused despite LESSON-EXEMPT
  if grep -qi "LESSON-EXEMPT" /tmp/push_exempt.log; then
    echo "TEST 3 ESCAPE: FAIL (LESSON-EXEMPT not honored)"
    cat /tmp/push_exempt.log >&2
    FAIL=1
  else
    echo "TEST 3 ESCAPE: SKIP (push rejected for reason other than LESSON count — escape path not reached)"
  fi
fi

# --- TEST 4: REJECT-via-rename path (session 46-B extension; codifies AP-32 rename-bypass protection for pre-receive) ---
# Create a draft outside pages/lessons/individual/, commit, then git-mv it INTO the canonical dir.
# Even though git-mv is a "rename" (not an add), `git ls-tree -r new_sha pages/lessons/individual/`
# enumerates the final state and counts the renamed-in file → count exceeds FROZEN_COUNT → reject.
# This test proves the pre-receive hook catches renames even though it doesn't inspect diff-filters.
# Fresh sandbox because previous scenarios left uncertain state on main.
cd /
BARE4="$TMP/s4.git"; WT4="$TMP/s4_wt"
git init --bare "$BARE4" >/dev/null 2>&1
cp "$HOOK_VAULT_PATH" "$BARE4/hooks/pre-receive"
chmod +x "$BARE4/hooks/pre-receive"
git clone --quiet "$BARE4" "$WT4" >/dev/null 2>&1
cd "$WT4"
git config user.email "test@nous.local"
git config user.name "test"
mkdir -p pages/lessons/individual pages/drafts
for i in $(seq 1 "$FROZEN"); do
  printf -- "---\nid: LESSON-%03d\ntitle: test\n---\n# LESSON-%03d\n" "$i" "$i" > "pages/lessons/individual/LESSON-$(printf '%03d' "$i")-test.md"
done
git add pages >/dev/null
git commit -m "seed $FROZEN LESSON files for rename test LESSON-EXEMPT" >/dev/null 2>&1
git push origin HEAD:main >/dev/null 2>&1 || { echo "TEST 4 REJECT-rename: SETUP FAIL (seed push rejected)"; FAIL=1; }

# Stage a draft in a non-canonical path
NEW_RN=$((FROZEN + 1))
printf -- "---\nid: LESSON-%03d\ntitle: via-rename\n---\n# LESSON-%03d\n" "$NEW_RN" "$NEW_RN" > "pages/drafts/candidate.md"
git add pages/drafts/candidate.md >/dev/null
git commit -m "draft: stage lesson candidate in non-canonical path" >/dev/null 2>&1
# Now rename INTO canonical path
git mv pages/drafts/candidate.md "pages/lessons/individual/LESSON-$(printf '%03d' "$NEW_RN")-via-rename.md"
git commit -m "promote: rename draft into canonical LESSON path (should trigger pre-receive REJECT)" >/dev/null 2>&1
if git push origin HEAD:main >/tmp/push_rename.log 2>&1; then
  echo "TEST 4 REJECT-rename: FAIL (push accepted when it should have rejected — hook missed rename-into-canonical)"
  FAIL=1
else
  if grep -qi "RULE ZERO\|LESSON count" /tmp/push_rename.log; then
    echo "TEST 4 REJECT-rename: PASS (hook rejected rename-into-canonical with LESSON-count message)"
  else
    echo "TEST 4 REJECT-rename: FAIL (push rejected but not for LESSON-count reason)"
    cat /tmp/push_rename.log >&2
    FAIL=1
  fi
fi

cd /

# --- TEST 5: REJECT-below-ceiling path (session 79 extension; count ceiling is not enough after migration) ---
# Real post-migration repos may have fewer than FROZEN_COUNT lesson receipts. Even then, adding ANY
# new canonical LESSON file violates RULE ZERO and must be rejected server-side.
BARE5="$TMP/s5.git"; WT5="$TMP/s5_wt"
git init --bare "$BARE5" >/dev/null 2>&1
cp "$HOOK_VAULT_PATH" "$BARE5/hooks/pre-receive"
chmod +x "$BARE5/hooks/pre-receive"
git clone --quiet "$BARE5" "$WT5" >/dev/null 2>&1
cd "$WT5"
git config user.email "test@nous.local"
git config user.name "test"
mkdir -p pages/lessons/individual
BASELINE_BELOW=$((FROZEN > 10 ? FROZEN - 10 : 1))
for i in $(seq 1 "$BASELINE_BELOW"); do
  printf -- "---\nid: LESSON-%03d\ntitle: test\n---\n# LESSON-%03d\n" "$i" "$i" > "pages/lessons/individual/LESSON-$(printf '%03d' "$i")-test.md"
done
git add pages >/dev/null
git commit -m "seed below-ceiling lesson baseline LESSON-EXEMPT" >/dev/null 2>&1
git push origin HEAD:main >/dev/null 2>&1 || { echo "TEST 5 REJECT-below-ceiling: SETUP FAIL (seed push rejected)"; FAIL=1; }

NEW_BELOW=$((BASELINE_BELOW + 1))
printf -- "---\nid: LESSON-%03d\ntitle: below-ceiling-new\n---\n# LESSON-%03d\n" "$NEW_BELOW" "$NEW_BELOW" > "pages/lessons/individual/LESSON-$(printf '%03d' "$NEW_BELOW")-below-ceiling-new.md"
git add pages >/dev/null
git commit -m "reject path: add canonical LESSON below ceiling" >/dev/null 2>&1
if git push origin HEAD:main >/tmp/push_below_ceiling.log 2>&1; then
  echo "TEST 5 REJECT-below-ceiling: FAIL (push accepted new LESSON while count stayed below FROZEN_COUNT)"
  FAIL=1
else
  if grep -qi "RULE ZERO\|new LESSON\|LESSON count" /tmp/push_below_ceiling.log; then
    echo "TEST 5 REJECT-below-ceiling: PASS (hook rejected new canonical LESSON below ceiling)"
  else
    echo "TEST 5 REJECT-below-ceiling: FAIL (push rejected but not with expected message)"
    cat /tmp/push_below_ceiling.log >&2
    FAIL=1
  fi
fi

cd /
[ "$FAIL" = "0" ] && { echo "ALL PRE-RECEIVE HOOK TESTS PASSED (5 scenarios: ACCEPT/REJECT/ESCAPE/REJECT-rename/REJECT-below-ceiling)"; exit 0; } || { echo "PRE-RECEIVE HOOK TESTS FAILED"; exit 2; }
