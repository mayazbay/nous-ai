#!/bin/bash
# docker_prune_daily.sh — daily Docker dangling-layer + image-cache prune.
# Runs 03:30 Almaty via launchd com.nous.docker-prune-daily, before morning-brief 04:00.
# Codified by infrastructure SKILL AP-72: manual prune is not idempotent on a live
# OpenClaw host because container churn regenerates dangling layers continuously.
# This script handles only dangling/cache reclaim. Tagged-but-unused image rmi is
# a SEPARATE weekly job (operator-approved) per AP-72 rule 3.
# Location on Air: /Users/madia/nous-agaas/tools/docker_prune_daily.sh

set -u
STATE_DIR=/Users/madia/nous-agaas/state
LOG_DIR=/Users/madia/nous-agaas/logs
STATE="$STATE_DIR/docker-prune-daily.json"
LOG="$LOG_DIR/docker-prune-daily.log"
TG_SCRIPT=/Users/madia/nous-agaas/tools/tg_send.sh
TS=$(date +%Y-%m-%dT%H:%M:%S%z)

mkdir -p "$STATE_DIR" "$LOG_DIR"

echo "=== $TS docker_prune_daily ===" >>"$LOG"

# Capture df + docker df before
DF_BEFORE=$(df -h /System/Volumes/Data | awk 'NR==2 {print $4" free / "$5" used"}')
DOCKER_BEFORE=$(docker system df --format '{{.Type}}\t{{.Reclaimable}}' 2>/dev/null | head -4 | tr '\n' '|')

# Run prune. -f for non-interactive; --force-yes-equivalent.
BUILDER_OUT=$(docker builder prune -af -f 2>&1 || true)
IMAGE_OUT=$(docker image prune -f 2>&1 || true)

# Extract bytes reclaimed (very rough; docker output format varies)
BUILDER_BYTES=$(echo "$BUILDER_OUT" | grep -iE "Total reclaimed space" | awk '{print $NF}' | tr -d '\n')
IMAGE_BYTES=$(echo "$IMAGE_OUT" | grep -iE "Total reclaimed space" | awk '{print $NF}' | tr -d '\n')

DF_AFTER=$(df -h /System/Volumes/Data | awk 'NR==2 {print $4" free / "$5" used"}')
FREE_AFTER_GB=$(df -g /System/Volumes/Data | awk 'NR==2 {print $4}')

# State file: track consecutive zero-recovery runs for Δ-failure alerting
PREV_ZERO=0
if [ -f "$STATE" ]; then
  PREV_ZERO=$(grep -oE '"consecutive_zero":[[:space:]]*[0-9]+' "$STATE" 2>/dev/null | awk -F: '{print $2}' | tr -d ' ' || echo 0)
  PREV_ZERO=${PREV_ZERO:-0}
fi

# Heuristic: zero-recovery if both prune outputs reclaimed 0B (or empty / unparseable)
ZERO=0
if [ "${BUILDER_BYTES:-0B}" = "0B" ] && [ "${IMAGE_BYTES:-0B}" = "0B" ]; then
  ZERO=1
fi

if [ "$ZERO" = "1" ]; then
  CONSECUTIVE=$((PREV_ZERO + 1))
else
  CONSECUTIVE=0
fi

# Write state JSON (handcrafted; no jq dependency)
cat >"$STATE" <<JSON
{
  "last_run": "$TS",
  "df_before": "$DF_BEFORE",
  "df_after": "$DF_AFTER",
  "free_after_gb": $FREE_AFTER_GB,
  "builder_bytes": "$BUILDER_BYTES",
  "image_bytes": "$IMAGE_BYTES",
  "zero_recovery": $ZERO,
  "consecutive_zero": $CONSECUTIVE
}
JSON

echo "  before: $DF_BEFORE" >>"$LOG"
echo "  after:  $DF_AFTER" >>"$LOG"
echo "  builder reclaimed: ${BUILDER_BYTES:-0}" >>"$LOG"
echo "  image reclaimed:   ${IMAGE_BYTES:-0}" >>"$LOG"
echo "  zero_recovery=$ZERO  consecutive=$CONSECUTIVE" >>"$LOG"

# Δ-failure alert: 3 consecutive zero-recovery runs OR free space < 20GB
ALERT=""
if [ "$CONSECUTIVE" -ge 3 ]; then
  ALERT="🟡 docker-prune-daily: 3 consecutive zero-recovery runs. Tagged-image audit needed (AP-72 rule 3). Free: $DF_AFTER"
elif [ "$FREE_AFTER_GB" -lt 20 ]; then
  ALERT="🔴 Air disk critical: $DF_AFTER after prune. Manual rmi of stale tagged images required."
fi

if [ -n "$ALERT" ] && [ -x "$TG_SCRIPT" ]; then
  bash "$TG_SCRIPT" "$ALERT" 2>>"$LOG" || echo "  tg_send failed" >>"$LOG"
  echo "  alerted: $ALERT" >>"$LOG"
fi

echo "=== done ===" >>"$LOG"
