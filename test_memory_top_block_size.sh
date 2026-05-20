#!/bin/bash
# test_memory_top_block_size.sh — enforces session-operating-contract AP-7 cap
#
# AP-7 (SOC v1.5.0): MEMORY.md top-block prepend (AMD-006 Rule 2) is capped
# at ≤50 lines per session. Total file should stay <400 lines; detail goes to
# topic files in pages/progress/claude-memory/sessions/*.md with wikilinks.
#
# Session 54 Probe C caught this the hard way — MEMORY.md grew 400 → 1747
# lines in 5 days (4× unbounded); system-reminder "Only part loaded" fired
# at session-54 open. This probe flags the regression at session-open via
# SOAO rather than at session-open-failure via truncation.
#
# Checks:
#   1. Most-recent top-block (first "# Memory — updated …" stanza) ≤50 lines
#   2. Total file size ≤400 lines (soft ceiling)
#
# Exit codes:
#   0 = both within limits
#   1 = warn (over soft ceiling OR top-block bloating 51-100 lines)
#   2 = hard drift (top-block >100 lines — write the next prepend WITH the cap)
#
# Usage: bash tools/test_memory_top_block_size.sh [--quiet]
#
# Source: `session-operating-contract` AP-7 (session 54, 2026-04-20).
# Wires into SOAO section 4.

set -u
QUIET=0
for arg in "$@"; do
  case "$arg" in --quiet) QUIET=1 ;; esac
done
log() { [ "$QUIET" -eq 1 ] || echo "$@"; }

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
MEMFILE="${MEMFILE_OVERRIDE:-$VAULT/pages/progress/claude-memory/MEMORY.md}"

if [ ! -f "$MEMFILE" ]; then
  # Fallback: symlink path from LAW-005
  MEMFILE="$HOME/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md"
fi

if [ ! -f "$MEMFILE" ]; then
  log "🔴 MEMORY.md not found at vault or symlink path"
  exit 2
fi

TOTAL_LINES=$(wc -l < "$MEMFILE" | tr -d ' ')

# Legacy MEMORY uses repeated "# Memory — updated …" stanzas. Mercury MEMORY
# uses "# Now context" followed by "# Mercury fact-block"; both are valid live
# memory formats and must be measured instead of treated as warning states.
HEADER_LINES=$(grep -nE '^# Memory — updated ' "$MEMFILE" | head -2 | cut -d: -f1 || true)
FIRST=$(echo "$HEADER_LINES" | head -1)
SECOND=$(echo "$HEADER_LINES" | sed -n '2p')
FORMAT="legacy"

if [ -n "$FIRST" ]; then
  if [ -n "$SECOND" ]; then
    TOP_BLOCK_LINES=$((SECOND - FIRST))
  else
    # Only one header in file — top-block = from FIRST to end.
    TOP_BLOCK_LINES=$((TOTAL_LINES - FIRST + 1))
  fi
elif grep -qE '^# Now context' "$MEMFILE"; then
  FORMAT="mercury"
  FIRST=$(grep -nE '^# Now context' "$MEMFILE" | head -1 | cut -d: -f1)
  SECOND=$(awk -v first="$FIRST" 'NR > first && /^# / { print NR; exit }' "$MEMFILE")
  if [ -n "$SECOND" ]; then
    TOP_BLOCK_LINES=$((SECOND - FIRST))
  else
    TOP_BLOCK_LINES=$((TOTAL_LINES - FIRST + 1))
  fi
else
  log "🟡 no legacy '# Memory — updated …' or Mercury '# Now context' header found in MEMORY.md — can't measure top-block"
  exit 1
fi

log "MEMORY.md: $TOTAL_LINES total lines; $FORMAT top-block: $TOP_BLOCK_LINES lines"

STATUS=0

if [ "$TOP_BLOCK_LINES" -le 50 ]; then
  log "✅ top-block $TOP_BLOCK_LINES ≤ 50 lines (AP-7 cap)"
elif [ "$TOP_BLOCK_LINES" -le 100 ]; then
  log "🟡 top-block $TOP_BLOCK_LINES lines > 50 cap — next prepend should extract detail to pages/progress/claude-memory/sessions/"
  STATUS=1
else
  log "🔴 top-block $TOP_BLOCK_LINES lines > 100 (hard drift) — REFUSE to prepend until extraction done"
  STATUS=2
fi

if [ "$TOTAL_LINES" -le 400 ]; then
  log "✅ total $TOTAL_LINES ≤ 400 lines (soft ceiling)"
elif [ "$TOTAL_LINES" -le 800 ]; then
  log "🟡 total $TOTAL_LINES > 400 — archive older blocks to sessions/archive-*.md"
  [ "$STATUS" -lt 1 ] && STATUS=1
else
  log "🔴 total $TOTAL_LINES > 800 — hard drift, archival required before next session-close"
  STATUS=2
fi

exit $STATUS
