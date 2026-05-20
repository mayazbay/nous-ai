#!/bin/bash
# context-injector-regression-check.sh — nightly regression gate for v2 progressive-disclosure injector.
#
# Runs `test_context_injector_v2.py` (16 unit tests, includes G4 8192-byte assertion per AP-37 session-46 tune).
# On FAIL: alerts via Telegram (LESSON-086 pattern — state-change alerts only; don't spam on PASS).
# On PASS: appends to rolling log; emits no external signal.
#
# Companion to:
#   - `infrastructure` AP-37 (design caps ≤ spec-named thresholds — first-hit was this module)
#   - `infrastructure` AP-38 (feature-flagged cutover ships with deploy-time A/B probe)
#   - `infrastructure` AP-43 (pre-commit AP-11 parity gate)
#   - `evidence-verification` AP-11 (feature-flag cutover ships with probe at deploy-time, not N sessions later)
#
# launchd label: com.nous.context-injector-regression (see ~/Library/LaunchAgents/)
# Schedule: 03:30 Almaty daily (just after dream-cycle + morning-brief prep window).

set -u

NOUS_ROOT="/Users/madia/nous-agaas"
TOOLS_DIR="$NOUS_ROOT/tools"
LOG_DIR="$NOUS_ROOT/logs"
LOG_FILE="$LOG_DIR/context-injector-regression.log"
TELEGRAM_SENDER="$TOOLS_DIR/telegram_send.sh"
TEST_SCRIPT="$TOOLS_DIR/test_context_injector_v2.py"

mkdir -p "$LOG_DIR"

TS="$(date -Iseconds 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
{
  echo "===================================================================="
  echo "[$TS] context_injector_v2 regression check starting"
  echo "===================================================================="
} >> "$LOG_FILE"

if [ ! -f "$TEST_SCRIPT" ]; then
  echo "[$TS] FAIL: test script missing at $TEST_SCRIPT" >> "$LOG_FILE"
  if [ -x "$TELEGRAM_SENDER" ]; then
    "$TELEGRAM_SENDER" "🔴 context-injector regression: test script missing at $TEST_SCRIPT" 2>>"$LOG_FILE" || true
  fi
  exit 2
fi

cd "$NOUS_ROOT"
if python3 "$TEST_SCRIPT" >> "$LOG_FILE" 2>&1; then
  echo "[$TS] PASS: context_injector_v2 regression clean" >> "$LOG_FILE"
  exit 0
else
  EXIT=$?
  echo "[$TS] FAIL: context_injector_v2 regression (exit=$EXIT)" >> "$LOG_FILE"
  LAST_FAIL=$(tail -40 "$LOG_FILE" | grep -i "fail\|assertion\|error" | tail -5 | sed 's/^/  /')
  MSG="🔴 context_injector regression FAIL on Air at $TS (exit=$EXIT). Tail:
$LAST_FAIL

Log: $LOG_FILE
Check AP-37 (cap ≤ G4 threshold) + AP-38 (deploy-time probe) + AP-43 (pre-commit parity)."
  if [ -x "$TELEGRAM_SENDER" ]; then
    "$TELEGRAM_SENDER" "$MSG" 2>>"$LOG_FILE" || true
  fi
  exit "$EXIT"
fi
