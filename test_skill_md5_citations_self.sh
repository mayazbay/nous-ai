#!/usr/bin/env bash
# Self-test for tools/test_skill_md5_citations.sh (infrastructure AP-44 scanner).
# Exercises REJECT + ACCEPT + vacuous paths via sandbox SKILL.md files.
#
# TEST 1: CLEAN baseline — real repo scan must exit 0 (after we fix any
#          real drifts found in initial run; post-fix this should always pass).
# TEST 2: DRIFT — sandbox SKILL.md with fabricated MD5 citation against a real file → exit 2.
# TEST 3: NO-CITATIONS — vacuous SKILL.md (no hex tokens) → exit 0.
# TEST 4: TRANSITION — citation in arrow context (X → Y) must be SKIPPED → exit 0.
# TEST 5: AIR-ONLY-PATH — citation with Air-only path (unverifiable from vault) must be SKIPPED → exit 0.

set -u
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo .)
cd "$REPO_ROOT"

SCANNER="tools/test_skill_md5_citations.sh"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

PASS=0
FAIL=0

# ---------- TEST 1: CLEAN ----------
if bash "$SCANNER" >/dev/null 2>&1; then
  echo "TEST 1 CLEAN:          PASS (real SKILL.md set has no drift)"
  PASS=$((PASS+1))
else
  echo "TEST 1 CLEAN:          FAIL — scanner flagged drift in real repo. Run:"
  echo "                             bash $SCANNER"
  echo "                             (fix each drift, then re-run this test)"
  FAIL=$((FAIL+1))
fi

# ---------- TEST 2: DRIFT ----------
cat > "$TMPDIR/fake-drift.md" <<'EOF'
---
name: fake-drift
version: 0.0.1
---

# fake-drift v0.0.1

Pre-commit hook MD5 is `ffffffffffffffffffffffffffffffff` for tools/pre-commit-hook-tan-pattern.sh.
EOF

SCAN_GLOB="$TMPDIR/fake-drift.md" bash "$SCANNER" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 2 ]; then
  echo "TEST 2 DRIFT:          PASS (scanner rejected fabricated citation with exit 2)"
  PASS=$((PASS+1))
else
  echo "TEST 2 DRIFT:          FAIL — scanner did NOT reject fabricated citation (rc=$rc)"
  FAIL=$((FAIL+1))
fi

# ---------- TEST 3: NO-CITATIONS ----------
cat > "$TMPDIR/nocite.md" <<'EOF'
---
name: nocite
version: 0.0.1
---

# nocite v0.0.1

This skill has no MD5 citations at all. Just prose.
EOF

if SCAN_GLOB="$TMPDIR/nocite.md" bash "$SCANNER" >/dev/null 2>&1; then
  echo "TEST 3 NO-CITATIONS:   PASS (vacuous SKILL.md accepted)"
  PASS=$((PASS+1))
else
  echo "TEST 3 NO-CITATIONS:   FAIL — scanner rejected vacuous case"
  FAIL=$((FAIL+1))
fi

# ---------- TEST 4: TRANSITION ----------
cat > "$TMPDIR/transition.md" <<'EOF'
---
name: transition
version: 0.0.1
---

# transition v0.0.1

Timeline: Mac hook MD5 went from `ffffffffffffffffffffffffffffffff` → `eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` at tools/pre-commit-hook-tan-pattern.sh during session 0.
EOF

if SCAN_GLOB="$TMPDIR/transition.md" bash "$SCANNER" >/dev/null 2>&1; then
  echo "TEST 4 TRANSITION:     PASS (arrow-context citation skipped as historical)"
  PASS=$((PASS+1))
else
  echo "TEST 4 TRANSITION:     FAIL — scanner did not skip transition citation"
  FAIL=$((FAIL+1))
fi

# ---------- TEST 5: AIR-ONLY-PATH ----------
cat > "$TMPDIR/aironly.md" <<'EOF'
---
name: aironly
version: 0.0.1
---

# aironly v0.0.1

Air runtime hook MD5 `ffffffffffffffffffffffffffffffff` at /opt/nous-agaas/tools/runtime-only.sh.
EOF

if SCAN_GLOB="$TMPDIR/aironly.md" bash "$SCANNER" >/dev/null 2>&1; then
  echo "TEST 5 AIR-ONLY-PATH:  PASS (unverifiable Air-only path skipped)"
  PASS=$((PASS+1))
else
  echo "TEST 5 AIR-ONLY-PATH:  FAIL — scanner should skip non-vault paths"
  FAIL=$((FAIL+1))
fi

echo ""
echo "----- SELF-TEST SUMMARY -----"
echo "PASS: $PASS"
echo "FAIL: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "ALL TESTS PASS"
exit 0
