#!/bin/bash
# Regression coverage for Mercury carryover seeding. Generated Mercury MEMORY
# must not feed carryover facts back into pages/mercury/facts.jsonl.

set -u

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$VAULT/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"
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

GENERATED="$TMP_DIR/generated-mercury-memory.md"
cat > "$GENERATED" <<'EOF'
# Now context (live, regenerated per session-start)
- date: 2026-04-29

# Mercury fact-block (top-K selective injection)

## Active carryover (BLOCKED + DEFERRED)
- carryover.stanza-0.blocked.blocked-deferred: BLOCKED + DEFERRED [[[claude-memory/MEMORY]]]
EOF

OUT_GENERATED=$(MERCURY_MEMORY_OVERRIDE="$GENERATED" "$PYTHON" "$VAULT/tools/mercury_seed.py" --dry-run 2>&1)
RC_GENERATED=$?
if [ "$RC_GENERATED" -ne 0 ]; then
  fail "generated Mercury fixture failed: $OUT_GENERATED"
fi
echo "$OUT_GENERATED" | grep -q '^carryover:     0$' || {
  fail "generated Mercury memory should not seed carryover: $OUT_GENERATED"
}

LEGACY="$TMP_DIR/legacy-memory.md"
cat > "$LEGACY" <<'EOF'
# Memory — updated 2026-04-29
- BLOCKED root-cause proof needed before retry
- BLOCKED root-cause proof needed before retry
EOF

OUT_LEGACY=$(MERCURY_MEMORY_OVERRIDE="$LEGACY" "$PYTHON" "$VAULT/tools/mercury_seed.py" --dry-run 2>&1)
RC_LEGACY=$?
if [ "$RC_LEGACY" -ne 0 ]; then
  fail "legacy MEMORY fixture failed: $OUT_LEGACY"
fi
echo "$OUT_LEGACY" | grep -q '^carryover:     1$' || {
  fail "legacy duplicate carryover should dedupe to one fact: $OUT_LEGACY"
}

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi

echo "OK: Mercury seeder skips generated memory and dedupes legacy carryover"
