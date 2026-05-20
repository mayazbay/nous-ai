#!/bin/bash
# credentials_drift_check.sh — daily Air watchdog for secrets-manifest drift.
#
# Runs the credentials discovery audit against Air+VPS runtime env files and
# alerts Madi via tg_send.sh if any undocumented key appears or a declared env
# file cannot be read. Values are never printed by the audit path.

set -u

ROOT="${NOUS_WIKI_ROOT:-$HOME/nous-agaas/wiki}"
STATE_DIR="${NOUS_STATE_DIR:-$HOME/nous-agaas/state}"
LOG_DIR="${NOUS_LOG_DIR:-$HOME/nous-agaas/logs}"
TG_SEND="${CREDENTIALS_DRIFT_TG_SEND:-$ROOT/tools/tg_send.sh}"
PYTHON="${PYTHON:-python3}"
TODAY="$(date +%Y-%m-%d)"

mkdir -p "$STATE_DIR" "$LOG_DIR"

OUT="$(mktemp /tmp/credentials-drift-out.XXXXXX)"
ERR="$(mktemp /tmp/credentials-drift-err.XXXXXX)"
cleanup() { rm -f "$OUT" "$ERR"; }
trap cleanup EXIT

CMD=("$PYTHON" "$ROOT/tools/credentials_discovery.py" audit --strict --hosts air,vps --no-staged)

"${CMD[@]}" >"$OUT" 2>"$ERR"
RC=$?
if [ "$RC" -eq 0 ]; then
  echo "[$TODAY] OK: credentials manifest drift check clean" >> "$LOG_DIR/credentials-drift.log"
  echo "$TODAY" > "$STATE_DIR/credentials-drift.last-ok"
  exit 0
fi

SUMMARY="$(cat "$ERR")"
if [ -z "$SUMMARY" ]; then
  SUMMARY="credentials_discovery.py audit failed with exit $RC"
fi

MESSAGE="🔴 Credentials manifest drift detected

$SUMMARY

Command:
python3 tools/credentials_discovery.py audit --strict --hosts air,vps --no-staged

No secret values were printed. Fix pages/secrets-manifest.md v2 or the runtime env drift."

if [ -f "$TG_SEND" ]; then
  bash "$TG_SEND" "$MESSAGE" >/dev/null 2>&1
  echo "[$TODAY] ALERT_SENT rc=$RC" >> "$LOG_DIR/credentials-drift.log"
else
  echo "[$TODAY] ALERT_FAILED tg_send_missing=$TG_SEND rc=$RC" >> "$LOG_DIR/credentials-drift.log"
fi

cat "$OUT" >> "$LOG_DIR/credentials-drift.log"
cat "$ERR" >> "$LOG_DIR/credentials-drift.log"
exit "$RC"
