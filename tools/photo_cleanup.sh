#!/bin/bash
# Photo rotation — keep 30 days (ERAP legal requirement), delete older
PHOTO_DIR="/opt/nous-agaas/erap/data/events/photos"
LOG="/root/nous-agaas/logs/photo_cleanup.log"

BEFORE=$(du -sh "$PHOTO_DIR" | cut -f1)
COUNT_BEFORE=$(find "$PHOTO_DIR" -type f | wc -l)

# Delete photos older than 35 days (5-day buffer over 30-day legal minimum)
find "$PHOTO_DIR" -type f -mtime +35 -delete 2>/dev/null

AFTER=$(du -sh "$PHOTO_DIR" | cut -f1)
COUNT_AFTER=$(find "$PHOTO_DIR" -type f | wc -l)
DELETED=$((COUNT_BEFORE - COUNT_AFTER))

echo "[$(date "+%Y-%m-%d %H:%M")] Photos: ${COUNT_BEFORE}->${COUNT_AFTER} (deleted ${DELETED}), Size: ${BEFORE}->${AFTER}" >> "$LOG"

# Alert if disk > 80%
DISK_PCT=$(df / | tail -1 | awk "{print \$5}" | tr -d "%")
if [ "$DISK_PCT" -gt 80 ]; then
    echo "[$(date "+%Y-%m-%d %H:%M")] WARNING: Disk at ${DISK_PCT}%!" >> "$LOG"
fi
