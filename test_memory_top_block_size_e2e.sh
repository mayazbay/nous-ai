#!/bin/bash
# tools/test_memory_top_block_size_e2e.sh — regression coverage for legacy and
# Mercury MEMORY.md top-block formats.

set -u

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$TOOLS_DIR/test_memory_top_block_size.sh"
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

LEGACY="$TMP_DIR/legacy-memory.md"
cat > "$LEGACY" <<'EOF'
# Memory — updated 2026-04-29
- one
- two

# Memory — updated 2026-04-28
- older
EOF

OUT_LEGACY=$(MEMFILE_OVERRIDE="$LEGACY" bash "$SCRIPT" 2>&1)
RC_LEGACY=$?
if [ "$RC_LEGACY" -ne 0 ]; then
  fail "legacy format failed: $OUT_LEGACY"
fi
echo "$OUT_LEGACY" | grep -q 'legacy top-block: 4 lines' || {
  fail "legacy output did not report expected top-block size: $OUT_LEGACY"
}

MERCURY="$TMP_DIR/mercury-memory.md"
cat > "$MERCURY" <<'EOF'
# Now context (live, regenerated per session-start)
- date: 2026-04-29
- session-id: s-test
- HEAD: abc123

# Mercury fact-block (top-K selective injection)

## Active carryover
- none
EOF

OUT_MERCURY=$(MEMFILE_OVERRIDE="$MERCURY" bash "$SCRIPT" 2>&1)
RC_MERCURY=$?
if [ "$RC_MERCURY" -ne 0 ]; then
  fail "Mercury format failed: $OUT_MERCURY"
fi
echo "$OUT_MERCURY" | grep -q 'mercury top-block: 5 lines' || {
  fail "Mercury output did not report expected top-block size: $OUT_MERCURY"
}

UNKNOWN="$TMP_DIR/unknown-memory.md"
printf '%s\n' '# Some other memory shape' '- no recognized live block' > "$UNKNOWN"

OUT_UNKNOWN=$(MEMFILE_OVERRIDE="$UNKNOWN" bash "$SCRIPT" 2>&1)
RC_UNKNOWN=$?
if [ "$RC_UNKNOWN" -eq 0 ]; then
  fail "unknown format passed unexpectedly: $OUT_UNKNOWN"
fi

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi

echo "OK: memory top-block legacy/Mercury regressions covered"
