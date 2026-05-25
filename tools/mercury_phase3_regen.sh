#!/bin/bash
# tools/mercury_phase3_regen.sh — regenerate MEMORY-mercury.md from current facts.
#
# Phase 3 made `pages/progress/claude-memory/MEMORY.md` a symlink to
# `MEMORY-mercury.md`. The Claude Code auto-memory harness occasionally writes
# THROUGH the symlink (overwrites MEMORY-mercury.md content with prepended
# narrative). When that happens, this script regenerates the Mercury block.
#
# Usage:
#   bash tools/mercury_phase3_regen.sh                  # regenerate
#   bash tools/mercury_phase3_regen.sh --rollback       # restore original MEMORY
#   bash tools/mercury_phase3_regen.sh --status         # show current state
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
MEM_DIR="$VAULT/pages/progress/claude-memory"
MEM="$MEM_DIR/MEMORY.md"
ARCHIVE="$MEM_DIR/MEMORY-archive.md"
MERCURY="$MEM_DIR/MEMORY-mercury.md"
PYTHON="$VAULT/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

ACTION="${1:-regen}"

case "$ACTION" in
  --status|status)
    if [ -L "$MEM" ]; then
      echo "✅ Phase 3 LIVE: MEMORY.md -> $(readlink "$MEM")"
      ls -la "$MEM" "$ARCHIVE" "$MERCURY" 2>/dev/null | head -3
    else
      echo "🟡 Phase 3 NOT live: MEMORY.md is a regular file ($(wc -lc < "$MEM" 2>/dev/null) bytes)"
    fi
    ;;
  --rollback|rollback)
    if [ ! -e "$ARCHIVE" ]; then
      echo "🔴 cannot rollback: $ARCHIVE missing"; exit 1
    fi
    ln -nfs MEMORY-archive.md "$MEM"
    echo "✅ rolled back: MEMORY.md -> MEMORY-archive.md ($(wc -lc < "$ARCHIVE") bytes)"
    ;;
  --regen|regen|"")
    # Auto-recover from harness clobber: if MEMORY.md is a regular file but
    # MEMORY-archive.md exists, Phase 3 was active and the harness replaced
    # the symlink (unlink+rename pattern). Re-flip automatically per Lane U.
    if [ ! -L "$MEM" ] && [ -e "$ARCHIVE" ]; then
      echo "🟡 MEMORY.md is a regular file but MEMORY-archive.md exists — harness clobbered symlink, auto-recovering"
      mv "$MEM" "$MERCURY"
      ln -nfs MEMORY-mercury.md "$MEM"
      echo "✅ symlink restored: MEMORY.md -> MEMORY-mercury.md (clobbered content preserved as new MEMORY-mercury.md)"
    fi
    if [ ! -L "$MEM" ]; then
      echo "🔴 MEMORY.md is not a symlink AND no MEMORY-archive.md present — Phase 3 not flipped"
      echo "   To flip: cd $MEM_DIR && mv MEMORY.md MEMORY-archive.md && python3 ../../../tools/mercury_inject.py --emit > MEMORY-mercury.md && ln -nfs MEMORY-mercury.md MEMORY.md"
      exit 2
    fi
    TMP=$(mktemp "${MERCURY}.tmp.XXXXXX")
    trap 'rm -f "$TMP"' EXIT
    if [ "${MERCURY_LIVE_CONTEXT:-0}" = "1" ]; then
      "$PYTHON" "$VAULT/tools/mercury_inject.py" --emit --live-context > "$TMP"
    else
      "$PYTHON" "$VAULT/tools/mercury_inject.py" --emit > "$TMP"
    fi
    if [ -f "$MERCURY" ] && cmp -s "$TMP" "$MERCURY"; then
      rm -f "$TMP"
      trap - EXIT
      echo "✅ unchanged $MERCURY ($(wc -lc < "$MERCURY") bytes)"
    else
      mv "$TMP" "$MERCURY"
      trap - EXIT
      echo "✅ regenerated $MERCURY ($(wc -lc < "$MERCURY") bytes)"
    fi
    ;;
  *)
    echo "usage: $0 [--status | --regen | --rollback]" >&2; exit 2 ;;
esac
