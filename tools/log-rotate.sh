#!/bin/bash
# log-rotate.sh — weekly log rotation
# Truncates logs > 5MB in ~/nous-agaas/logs/. Keeps last 1000 lines as .tail.
# Runs Sunday 03:00 Almaty via launchd.
# Location on Air: /Users/madia/nous-agaas/tools/log-rotate.sh

set -u
LOG_DIR=/Users/madia/nous-agaas/logs
META_LOG="$LOG_DIR/log-rotate.log"
TS=$(date +%Y-%m-%dT%H:%M:%S)

echo "=== $TS log rotation ===" >> "$META_LOG"

for f in "$LOG_DIR"/*.log "$LOG_DIR"/*.err; do
  [ -f "$f" ] || continue
  [ "$f" = "$META_LOG" ] && continue  # don't rotate self
  SIZE=$(stat -f %z "$f")
  if [ "$SIZE" -gt 5242880 ]; then  # > 5MB
    # Keep last 1000 lines, archive rest
    tail -1000 "$f" > "${f}.rotated" && mv "${f}.rotated" "$f"
    echo "  rotated: $(basename "$f") (was ${SIZE} bytes)" >> "$META_LOG"
  fi
done

echo "=== done ===" >> "$META_LOG"
