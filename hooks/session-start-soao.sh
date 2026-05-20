#!/bin/bash
# session-start-soao.sh — auto-run Session-Open Atomic Opener at Claude Code session start.
#
# Fires the `tools/soao.sh` canonical 8-point protocol (AP-18 0-th + AP-17 7-point)
# against the Nous AGaaS vault. Output goes to stdout (visible to the session agent at
# session open) and to ~/.claude/logs/soao-last.log (readable all session).
#
# Exit codes propagate from soao.sh: 0 GOLDEN / 1 yellow / 2 red (blocking).
#
# Timeout budget: 60s soft cap. If soao.sh hangs on ssh (VPS/Air unreachable),
# the hook falls back to `--skip-ssh` (local checks only) to avoid blocking session start.
#
# Rule 6 / AP-17 / AP-18 operational enforcement at the ONLY point that matters:
# session open. Codified session 51, 2026-04-20. Pair of tools/soao.sh (audit v1.19 AP-20).

set -u
VAULT="/Users/madia/Documents/Projects/Nous AGaaS/Nous"
LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/soao-last.log"

mkdir -p "$LOG_DIR"

# Early exit if vault path missing — bash cwd probe failure class (AP-18)
if [ ! -d "$VAULT" ]; then
  echo "[session-start-soao] 🔴 vault not found at $VAULT — AP-18 bash cwd class failure"
  echo "   Verify with: ls -la '$VAULT' (may be TCC-denied, not actually missing)"
  exit 2
fi

# Only run if the SOAO tool exists — skill-layer hasn't shipped yet otherwise
if [ ! -x "$VAULT/tools/soao.sh" ]; then
  echo "[session-start-soao] tools/soao.sh not present or not executable — skipping"
  exit 0
fi

# Portable timeout wrapper — macOS has no `timeout` by default; use perl alarm.
# Returns exit 124 on timeout to mimic GNU coreutils.
run_with_timeout() {
  local secs=$1; shift
  perl -e '$t=shift; $SIG{ALRM}=sub{exit 124}; alarm $t; exec @ARGV' "$secs" "$@"
}

# Try full SOAO with 50s cap; on timeout fall back to --skip-ssh
OUT=$(cd "$VAULT" && run_with_timeout 50 bash tools/soao.sh 2>&1)
RC=$?

if [ $RC -eq 124 ]; then
  echo "[session-start-soao] ⏱️  full SOAO timed out at 50s; retrying local-only (--skip-ssh)"
  OUT=$(cd "$VAULT" && run_with_timeout 15 bash tools/soao.sh --skip-ssh 2>&1)
  RC=$?
fi

# Write full output to log for agent reference
echo "$OUT" > "$LOG_FILE"

# Print summary line + red/yellow items only to session stdout (keep context compact)
if [ $RC -eq 0 ]; then
  echo "[session-start-soao] ✅ GOLDEN — full report: $LOG_FILE"
elif [ $RC -eq 1 ]; then
  echo "[session-start-soao] 🟡 $(echo "$OUT" | grep -cE '^🟡') non-blocking warnings:"
  echo "$OUT" | grep -E '^🟡' | sed 's/^/   /'
  echo "   full report: $LOG_FILE"
elif [ $RC -eq 2 ]; then
  echo "[session-start-soao] 🔴 BLOCKING — $(echo "$OUT" | grep -cE '^🔴') red items:"
  echo "$OUT" | grep -E '^🔴' | sed 's/^/   /'
  echo "   full report: $LOG_FILE"
  echo "   Fix red items before starting work."
else
  echo "[session-start-soao] ⚠️  soao.sh exited $RC unexpectedly; see $LOG_FILE"
fi

# --- session-coordination v1.28+: auto-register this session ---
# AP-27 (mandatory session-start register) + AP-25 (no silent wildcard scope).
# Re-registers if the SID file is stale (points to a session that's no longer
# in the active Air registry), per AP-27 evidence: session 100 had a stale
# s84-air-79090 SID file and silently skipped registration for the entire
# session, leaving 6 doctrine commits unattributed in the registry.
SID_FILE="$HOME/.claude/sessions/current_session_id"
mkdir -p "$(dirname "$SID_FILE")"

EXISTING_SID=""
[ -s "$SID_FILE" ] && EXISTING_SID=$(cat "$SID_FILE" 2>/dev/null | tr -d '[:space:]')

# Stale-SID detection: if the SID file points to a session not in the active
# Air registry, treat as stale and re-register. Honor offline / Air-unreachable
# by skipping detection (don't churn registrations on flaky network).
NEEDS_REGISTER=1
if [ -n "$EXISTING_SID" ]; then
  ACTIVE_PROBE=$(run_with_timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=3 air \
    "grep -F '\"session_id\":\"$EXISTING_SID\"' ~/nous-agaas/wiki/state/session-registry.jsonl 2>/dev/null | tail -1" 2>/dev/null)
  if [ -n "$ACTIVE_PROBE" ] && ! echo "$ACTIVE_PROBE" | grep -q '"closed_at":'; then
    NEEDS_REGISTER=0
    echo "[session-start-soao] 📝 reusing active session_id=$EXISTING_SID (registry confirmed)"
  fi
fi

if [ "$NEEDS_REGISTER" = "1" ]; then
  HOST=$(hostname -s | tr '[:upper:]' '[:lower:]' | sed 's/\.local$//')
  case "$HOST" in
    mac*|*macbook*) HOST="mac" ;;
    air|*air*) HOST="air" ;;
    *vps*|*hetzner*) HOST="vps" ;;
    *gpu*) HOST="nous-gpu" ;;
  esac
  SESSION_NUM="${CLAUDE_SESSION_NUM:-$(date +%y%m%d%H%M | tail -c5)}"
  INTENT="${CLAUDE_SESSION_INTENT:-claude-code session start}"
  # AP-25 + AP-27: never default to wildcard scope. If env scope is missing
  # or empty or "*", fall back to vault-name as a narrow placeholder and warn.
  # Caller should set CLAUDE_SESSION_SCOPE to actual paths within first 3 turns.
  RAW_SCOPE="${CLAUDE_SESSION_SCOPE:-}"
  if [ -z "$RAW_SCOPE" ] || [ "$RAW_SCOPE" = "*" ]; then
    SCOPE_DEFAULT="pages/progress/claude-memory/"
    echo "[session-start-soao] ⚠️  CLAUDE_SESSION_SCOPE missing or wildcard; defaulting to '$SCOPE_DEFAULT' — agent MUST narrow scope within first 3 turns via session_self_register.sh --intent '...' --scope '<paths>' (AP-27)"
  else
    SCOPE_DEFAULT="$RAW_SCOPE"
  fi
  REG_OUT=$(SESSION_NUM="$SESSION_NUM" SESSION_PID="$$" bash "$VAULT/tools/session_register.sh" \
    --host "$HOST" --intent "$INTENT" --scope "$SCOPE_DEFAULT" 2>&1)
  if echo "$REG_OUT" | grep -qE '^s[0-9]'; then
    SID=$(echo "$REG_OUT" | grep -E '^s[0-9]' | head -1)
    echo "$SID" > "$SID_FILE"
    echo "[session-start-soao] 📝 registered session_id=$SID (host=$HOST scope=$SCOPE_DEFAULT)"
    [ -n "$EXISTING_SID" ] && [ "$EXISTING_SID" != "$SID" ] && \
      echo "[session-start-soao] 🟡 superseded stale SID $EXISTING_SID (not in active registry — AP-27 stale-SID class)"
  else
    echo "[session-start-soao] ⚠️  session-register failed (Air unreachable?) — coordination degraded; first peer-collision-prone edit MUST manually verify with bash tools/session_scan.sh"
  fi
fi

exit $RC
