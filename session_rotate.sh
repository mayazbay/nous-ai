#!/bin/bash
# Daily OpenClaw session rotation — prevents token accumulation (LESSON-101)
# Runs 3:45 AM Almaty (before nightly-audit at 4am)
# Clears session history so each day starts with near-zero context
# Knowledge is preserved in wiki + gbrain, not in session files

LOG="${SESSION_ROTATE_LOG:-/Users/madia/nous-agaas/logs/session-rotate.log}"
DOCKER="${DOCKER:-docker}"
ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "$(ts) session-rotate: starting" >> "$LOG"

# Find and trim session files. Preserve the first OpenClaw session header line:
# replacing a JSONL file with [] creates an invalid session header.
SESSION_FILES=$("$DOCKER" exec openclaw find /home/node/.openclaw/agents/nous/sessions -name '*.jsonl' ! -name '*.checkpoint.*' 2>/dev/null)

if [ -z "$SESSION_FILES" ]; then
    echo "$(ts) session-rotate: no session files found" >> "$LOG"
    exit 0
fi

for f in $SESSION_FILES; do
    SIZE=$("$DOCKER" exec openclaw sh -c 'wc -c < "$1"' sh "$f" 2>/dev/null | tr -d ' ')
    if "$DOCKER" exec openclaw sh -c '
        first=$(head -n 1 "$1" 2>/dev/null || true)
        case "$first" in
          *\"type\":\"session\"*) printf "%s\n" "$first" > "$1" ;;
          *) exit 3 ;;
        esac
    ' sh "$f" 2>/dev/null; then
        echo "$(ts) session-rotate: trimmed $f to header (was ${SIZE:-?} bytes)" >> "$LOG"
    else
        echo "$(ts) session-rotate: skipped $f (invalid or missing session header, size ${SIZE:-?} bytes)" >> "$LOG"
    fi
done

echo "$(ts) session-rotate: done" >> "$LOG"
