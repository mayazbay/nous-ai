#!/usr/bin/env bash
# qmd_real_freshness.sh — cross-stack QMD freshness check.
#
# Works around upstream @tobilu/qmd `status.lastUpdated` drift: the endpoint
# reports stale timestamps even when the nightly cron successfully re-indexed
# and re-embedded. Authoritative truth = mtime of the cron's embed log on VPS.
#
# Session 49 artifact. See pages/skills/gbrain-ops/SKILL.md AP-19
# upstream-freshness-lies and the Evidence trail for rationale.
#
# Usage:
#   bash tools/qmd_real_freshness.sh              # human output
#   bash tools/qmd_real_freshness.sh --json       # machine output
#   VPS_HOST="" bash tools/qmd_real_freshness.sh  # local filesystem (on VPS)
#
# Environment:
#   VPS_HOST       — ssh target (default: root@65.108.215.200). Empty = local.
#   QMD_EMBED_LOG  — path to embed log (default: /root/nous-agaas/logs/qmd-embed.log)
#   STALE_HOURS    — threshold before crying stale (default: 30, = daily + 6h skew)
#
# Exit codes:
#   0 — fresh (within threshold)
#   1 — stale (exceeds threshold)
#   2 — unknown (could not read log)

set -euo pipefail

SCRIPT_NAME="qmd_real_freshness"
VERSION="1.0.0"
VPS_HOST="${VPS_HOST-root@65.108.215.200}"
QMD_EMBED_LOG="${QMD_EMBED_LOG:-/root/nous-agaas/logs/qmd-embed.log}"
STALE_HOURS="${STALE_HOURS:-30}"

OUTPUT_JSON=0
[[ "${1:-}" == "--json" ]] && OUTPUT_JSON=1

local_mtime() {
  python3 -c 'import os, sys; print(int(os.path.getmtime(sys.argv[1])))' "$1" 2>/dev/null || echo 0
}

if [[ -z "$VPS_HOST" ]] || [[ "$VPS_HOST" == "localhost" ]]; then
  cron_epoch=$(local_mtime "$QMD_EMBED_LOG")
else
  cron_epoch=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$VPS_HOST" \
    "stat -c '%Y' '$QMD_EMBED_LOG' 2>/dev/null" 2>/dev/null || echo 0)
fi

now_epoch=$(date +%s)
age_hours=0
status="unknown"
reason="init"
exit_code=2

if [[ "${cron_epoch:-0}" -eq 0 ]]; then
  status="unknown"
  reason="cannot stat ${QMD_EMBED_LOG} on ${VPS_HOST:-local}"
  exit_code=2
else
  age_seconds=$((now_epoch - cron_epoch))
  age_hours=$((age_seconds / 3600))
  if [[ $age_hours -le $STALE_HOURS ]]; then
    status="fresh"
    reason="last qmd embed ${age_hours}h ago (threshold ${STALE_HOURS}h)"
    exit_code=0
  else
    status="stale"
    reason="last qmd embed ${age_hours}h ago exceeds threshold ${STALE_HOURS}h — cron may be failing"
    exit_code=1
  fi
fi

if [[ $OUTPUT_JSON -eq 1 ]]; then
  printf '{"tool":"%s","version":"%s","status":"%s","age_hours":%d,"threshold_hours":%d,"cron_log_epoch":%d,"reason":"%s"}\n' \
    "$SCRIPT_NAME" "$VERSION" "$status" "$age_hours" "$STALE_HOURS" "${cron_epoch:-0}" "$reason"
else
  upper_status=$(printf '%s' "$status" | tr '[:lower:]' '[:upper:]')
  printf '[%s v%s] %s — %s\n' "$SCRIPT_NAME" "$VERSION" "$upper_status" "$reason"
fi

exit $exit_code
