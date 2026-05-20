#!/bin/bash
# docker_image_audit_weekly.sh — Sunday 03:15 Almaty audit per infrastructure AP-72 rule 3.
#
# Purpose:
#   AP-72 rule 1-2 ship docker_prune_daily.sh (handles dangling-layer + cache).
#   AP-72 rule 3 explicitly says: "Tagged-image audit is a SEPARATE weekly job:
#   list docker images, identify any image not referenced by docker ps, log to
#   ~/nous-agaas/state/docker-stale-images-YYYY-WW.log, and require operator
#   approval before rmi (because misidentifying a paused-but-needed image
#   causes a re-pull cost)."
#
# This script: logs candidates. Does NOT delete. Operator reviews + runs rmi.
#
# Telegram alert fires when total candidate size > AUDIT_ALERT_GB threshold
# (default 5 GB) — that's the "stuff worth telling operator about" cutoff.
#
# Location on Air: /Users/madia/nous-agaas/tools/docker_image_audit_weekly.sh
# Schedule: Sunday 03:15 Almaty via launchd com.nous.docker-image-audit-weekly
# State: ~/nous-agaas/state/docker-stale-images-<YYYY-WW>.log
#
# Cross-ref:
#   - infrastructure AP-72 rule 3 (this script's spec)
#   - tools/docker_prune_daily.sh (rule 1-2 sibling)
#   - tools/log-rotate.sh (similar Sunday-cadence pattern)

set -u
STATE_DIR=/Users/madia/nous-agaas/state
LOG_DIR=/Users/madia/nous-agaas/logs
TG_SCRIPT=/Users/madia/nous-agaas/tools/tg_send.sh

YYYY_WW=$(date +%Y-%V)
STATE="$STATE_DIR/docker-stale-images-${YYYY_WW}.log"
META_LOG="$LOG_DIR/docker-image-audit.log"
TS=$(date +%Y-%m-%dT%H:%M:%S%z)
AUDIT_ALERT_GB="${AUDIT_ALERT_GB:-5}"

mkdir -p "$STATE_DIR" "$LOG_DIR"

echo "=== $TS docker_image_audit_weekly ===" >>"$META_LOG"

# Running images (protected — never list as candidates)
running_images=$(docker ps --format '{{.Image}}' 2>/dev/null | sort -u)
running_count=$(echo "$running_images" | grep -c .)

# All images, with size in bytes
# Format: ID<TAB>Repo:Tag<TAB>SizeBytes<TAB>CreatedSince
all_images=$(docker images --format '{{.ID}}\t{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}' 2>/dev/null)

# Identify candidates (not in running)
candidates=""
total_bytes=0
candidate_count=0

while IFS=$'\t' read -r id repo_tag size_str created; do
  [ -z "$id" ] && continue
  # Skip if this image is currently running
  if echo "$running_images" | grep -qF "$repo_tag"; then
    continue
  fi
  # Skip <none>:<none> dangling (handled by docker_prune_daily)
  if [ "$repo_tag" = "<none>:<none>" ]; then
    continue
  fi
  # Convert size string (e.g. "4.57GB", "228MB") to bytes.
  # Use printf "%.0f" to force fixed-point output (default print uses
  # %.6g which emits scientific notation for ≥10^7, mangling bash math).
  size_bytes=$(echo "$size_str" | awk '
    /GB$/ { sub("GB",""); printf "%.0f", $1 * 1024 * 1024 * 1024; exit }
    /MB$/ { sub("MB",""); printf "%.0f", $1 * 1024 * 1024; exit }
    /KB$/ { sub("KB",""); printf "%.0f", $1 * 1024; exit }
    /B$/  { sub("B",""); printf "%.0f", $1; exit }
    { printf "0" }
  ')
  total_bytes=$((total_bytes + ${size_bytes:-0}))
  candidate_count=$((candidate_count + 1))
  candidates="${candidates}${id}	${repo_tag}	${size_str}	${created}
"
done <<< "$all_images"

# Format threshold: 5GB = 5368709120 bytes
threshold_bytes=$((AUDIT_ALERT_GB * 1024 * 1024 * 1024))
total_gb=$((total_bytes / 1024 / 1024 / 1024))

# Write state file (append-only across the week; one run per Sunday so single block)
{
  echo "# Docker stale-image audit — week $YYYY_WW — run $TS"
  echo "# Running images (protected, $running_count):"
  echo "$running_images" | sed 's/^/#   /'
  echo "# Candidates ($candidate_count, total ~${total_gb} GB):"
  echo "$candidates" | sed '/^$/d'
  echo "# Threshold for Telegram alert: ${AUDIT_ALERT_GB} GB"
  echo "# Recommended rmi command (operator review required):"
  echo "$candidates" | awk -F'\t' 'NF>=2 {print "#   docker rmi "$1"  # "$2" "$3}'
  echo ""
} > "$STATE"

echo "  state: $STATE" >>"$META_LOG"
echo "  candidates: $candidate_count, total: ${total_gb} GB" >>"$META_LOG"

# Telegram alert if over threshold
if [ "$total_bytes" -gt "$threshold_bytes" ]; then
  ALERT="🟡 docker-image-audit-weekly: ${candidate_count} stale images on Air, ~${total_gb} GB reclaimable. Review: ${STATE}"
  if [ -x "$TG_SCRIPT" ]; then
    bash "$TG_SCRIPT" "$ALERT" 2>>"$META_LOG" || echo "  tg_send failed" >>"$META_LOG"
    echo "  alerted: total ${total_gb}GB > threshold ${AUDIT_ALERT_GB}GB" >>"$META_LOG"
  fi
fi

echo "=== done ===" >>"$META_LOG"
