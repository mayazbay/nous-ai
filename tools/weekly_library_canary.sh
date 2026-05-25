#!/bin/bash
# weekly_library_canary.sh — Air-side launchd canary for library-grade gate.
#
# Runs the 3 library scanners + SOAO §4c output. On red, posts a Telegram
# alert via tg_send.sh AND writes a HANDOFF-AUTO with diagnostic. On green,
# posts a single-line success Telegram so you know the canary itself is alive.
#
# Doctrine: gbrain-ops AP-67/AP-76 (core Tier-A1 scoping) + AUDIT-061.
# Wired by: ~/Library/LaunchAgents/com.nous.weekly-library-canary.plist (Air).
# Source-of-truth: tools/launchd/com.nous.weekly-library-canary.plist (vault).
#
# Exit codes:
#   0 = all green (3 ✅, success Telegram posted)
#   1 = red (some scanner failed; alert + handoff written)
#   2 = config error (vault path unreachable, scanners missing, etc.)
#
# Idempotent. Safe to run manually: `bash tools/weekly_library_canary.sh`

set -u

# ---- config (Air-side defaults; override via env) ----
VAULT="${LIBRARY_CANARY_VAULT:-$HOME/nous-agaas/wiki}"
LOG_DIR="${LIBRARY_CANARY_LOG_DIR:-$HOME/nous-agaas/logs/canary}"
HANDOFF_DIR="${LIBRARY_CANARY_HANDOFF_DIR:-$VAULT/pages/progress}"
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
DATE_LOCAL="$(date '+%Y-%m-%d %H:%M:%S %Z')"
HOST="$(hostname -s 2>/dev/null || hostname)"
LOG="$LOG_DIR/canary-$TS.log"

mkdir -p "$LOG_DIR"

# ---- pre-flight ----
if [ ! -d "$VAULT" ]; then
  echo "🔴 config error: VAULT=$VAULT not a directory" | tee -a "$LOG"
  exit 2
fi
cd "$VAULT" || exit 2
for SCANNER in library_reachability_scan.py library_canonical_scan.py library_crossref_scan.py; do
  if [ ! -f "tools/$SCANNER" ]; then
    echo "🔴 config error: missing tools/$SCANNER in $VAULT" | tee -a "$LOG"
    exit 2
  fi
done

# ---- run scanners ----
HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
RED=0
declare -a FAILED=()
declare -a SCANNER_OUTPUT=()

run_scanner() {
  local name="$1"
  local script="tools/$name"
  local label="$2"
  local out
  out="$(python3 "$script" 2>&1)"
  local rc=$?
  echo "--- $name (exit=$rc) ---" >> "$LOG"
  echo "$out" >> "$LOG"
  if [ "$rc" -ne 0 ]; then
    RED=$((RED+1))
    FAILED+=("$label")
    SCANNER_OUTPUT+=("$out")
  fi
}

run_scanner library_reachability_scan.py "reachability"
run_scanner library_canonical_scan.py "canonical"
run_scanner library_crossref_scan.py "crossref"

# ---- SOAO §4c snapshot (informational) ----
SOAO_4C=""
if [ -x "tools/soao.sh" ] || [ -f "tools/soao.sh" ]; then
  SOAO_4C="$(bash tools/soao.sh --skip-ssh 2>&1 | grep -A4 '4c\.' || true)"
fi

# ---- success path ----
if [ "$RED" -eq 0 ]; then
  MSG="🟢 weekly library canary GREEN @ $DATE_LOCAL ($HOST, HEAD $HEAD_SHA)
3/3 scanners exit 0 (reachability + canonical + crossref).
Core Tier-A1 stable per AUDIT-061. Log: $LOG"
  if [ -f "$VAULT/tools/tg_send.sh" ]; then
    bash "$VAULT/tools/tg_send.sh" "$MSG" >> "$LOG" 2>&1 || true
  fi
  echo "$MSG" | tee -a "$LOG"
  exit 0
fi

# ---- red path: alert FIRST (so a handoff-write bug never silences the alert), then handoff ----
ALERT="🔴 weekly library canary RED @ $DATE_LOCAL ($HOST, HEAD $HEAD_SHA)
${RED}/3 scanners failed: ${FAILED[*]}
Log: $LOG"
if [ -f "$VAULT/tools/tg_send.sh" ]; then
  bash "$VAULT/tools/tg_send.sh" "$ALERT" >> "$LOG" 2>&1 || true
fi
echo "$ALERT" | tee -a "$LOG"

HANDOFF="$HANDOFF_DIR/HANDOFF-AUTO-$(date -u +%Y-%m-%d)-canary-RED-$HOST.md"
{
  echo "---"
  echo "type: progress"
  echo "id: HANDOFF-AUTO-$(date -u +%Y-%m-%d)-canary-RED-$HOST"
  echo "title: \"Weekly library canary RED — $RED/3 scanners failed @ $DATE_LOCAL ($HOST)\""
  echo "date: $(date -u +%Y-%m-%d)"
  echo "status: red"
  echo "tags: [handoff, canary, library-grade, red, gbrain-ops, ap-67]"
  echo "session: weekly-library-canary-$TS"
  echo "related:"
  echo "  - \"[[skills/gbrain-ops/skill]]\""
  echo "  - \"[[AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30]]\""
  echo "---"
  echo ""
  echo "# Weekly library canary RED — $HOST @ $DATE_LOCAL"
  echo ""
  echo "Failed scanners ($RED): ${FAILED[*]}"
  echo "HEAD: $HEAD_SHA"
  echo "Log: $LOG"
  echo ""
  echo "## Failing scanner output"
  echo ""
  for i in "${!FAILED[@]}"; do
    echo "### ${FAILED[$i]}"
    echo ""
    echo '```'
    echo "${SCANNER_OUTPUT[$i]}"
    echo '```'
    echo ""
  done
  echo "## Repro"
  echo '```bash'
  echo "cd \"$VAULT\""
  echo "python3 tools/library_reachability_scan.py"
  echo "python3 tools/library_canonical_scan.py"
  echo "python3 tools/library_crossref_scan.py"
  echo '```'
} > "$HANDOFF"

if [ -f "$VAULT/tools/tg_send.sh" ]; then
  bash "$VAULT/tools/tg_send.sh" "Canary handoff written: $HANDOFF" >> "$LOG" 2>&1 || true
fi
exit 1
