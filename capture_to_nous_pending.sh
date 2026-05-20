#!/bin/bash
# Copies new files from iCloud Capture/Nous → Nous wiki raw/pending/
# Triggered by macOS Folder Action OR LaunchAgent on file change

CAPTURE_DIR="/Users/madia/Library/Mobile Documents/com~apple~CloudDocs/Capture/Nous"
RAW_PENDING="/Users/madia/Documents/Projects/Nous AGaaS/Nous/raw/pending"
LOG="/tmp/capture_to_nous.log"

mkdir -p "$RAW_PENDING"

for f in "$CAPTURE_DIR"/*; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    # Avoid Apple's iCloud placeholder files
    [[ "$base" == .* ]] && continue
    [[ "$base" == *.icloud ]] && continue

    # Build a clean target filename with timestamp prefix
    ts=$(date '+%Y-%m-%d_%H%M%S')
    safe_base=$(echo "$base" | tr ' ' '_' | tr -dc 'A-Za-z0-9._-')
    target="$RAW_PENDING/${ts}_${safe_base}"

    if cp "$f" "$target" 2>>"$LOG"; then
        rm -f "$f"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] copied $base → $(basename $target)" >> "$LOG"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAILED $base" >> "$LOG"
    fi
done
