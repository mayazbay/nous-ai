#!/bin/bash
# test_air_live_hook_parity.sh — closes AP-49 drift class (session 54 E1 incident)
#
# Ensures Mac ↔ Air ~/.claude/hooks/*.sh MD5 parity for the hooks that SHOULD
# be canonical on both hosts. Mac has 5 hooks; Air has 3 — the 2 Mac-only
# ones (session-start-soao.sh, session-turn-counter.sh) are intentional (Air
# doesn't run interactive Claude Code sessions, only `/code`-spawned ephemeral
# CLIs + factory docker). Intersection set = 3 files that MUST match by MD5.
#
# Exit codes:
#   0 = all match
#   1 = warning (hook missing on one side; drift candidate)
#   2 = hard drift (file exists both sides but MD5 diverges — E1-class incident)
#
# Usage:
#   bash tools/test_air_live_hook_parity.sh            # full report
#   bash tools/test_air_live_hook_parity.sh --quiet    # exit code only
#
# Source: codified in `infrastructure` SKILL.md AP-49 (session 54, 2026-04-20).
# Wires into SOAO section 4.

set -u
QUIET=0
for arg in "$@"; do
  case "$arg" in --quiet) QUIET=1 ;; esac
done
log() { [ "$QUIET" -eq 1 ] || echo "$@"; }
AIR_LOCAL=0
if [ "${SESSION_FORCE_AIR_LOCAL:-0}" = "1" ] || { hostname 2>/dev/null | grep -qi 'air' && [ "${SESSION_FORCE_REMOTE:-0}" != "1" ]; }; then
  AIR_LOCAL=1
fi

# Canonical shared set — hooks that must exist on BOTH Mac and Air
CANON_HOOKS=(post-session.sh sync-banned-patterns.sh task-completed-enforce.sh)

RED=0
YELLOW=0

for hook in "${CANON_HOOKS[@]}"; do
  MAC_PATH="$HOME/.claude/hooks/$hook"
  MAC_MD5=$(md5 -q "$MAC_PATH" 2>/dev/null || echo missing)
  if [ "$AIR_LOCAL" -eq 1 ]; then
    AIR_MD5="$MAC_MD5"
  else
    AIR_MD5=$(ssh -o ConnectTimeout=10 air "md5 -q ~/.claude/hooks/$hook 2>/dev/null || echo missing" 2>/dev/null)
  fi

  if [ "$MAC_MD5" = "missing" ] || [ "$AIR_MD5" = "missing" ]; then
    log "🟡 $hook: Mac=$MAC_MD5 Air=$AIR_MD5 (missing on one side)"
    YELLOW=$((YELLOW+1))
  elif [ "$MAC_MD5" = "$AIR_MD5" ]; then
    log "✅ $hook: Mac ↔ Air MD5 match ($MAC_MD5)"
  else
    log "🔴 $hook: DRIFT — Mac=$MAC_MD5 Air=$AIR_MD5"
    log "   Fix: scp \"$MAC_PATH\" air:~/.claude/hooks/$hook"
    RED=$((RED+1))
  fi
done

log ""
log "test_air_live_hook_parity: red=$RED yellow=$YELLOW"
[ "$RED" -gt 0 ] && exit 2
[ "$YELLOW" -gt 0 ] && exit 1
exit 0
