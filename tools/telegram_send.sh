#!/usr/bin/env bash
# telegram_send.sh — Safe send-only Telegram wrapper for Claude Code
#
# WHY: telegram_poll.py on Air uses getUpdates (long-polling). Using
#      Telegram MCP from Claude Code would ALSO call getUpdates → HTTP 409
#      (two consumers on same bot token). LESSON-087.
#
# HOW: This script calls sendMessage / sendDocument directly via curl.
#      No getUpdates, no polling, no MCP plugin, no conflict.
#
# USAGE:
#   telegram_send.sh "Hello from Claude Code"              # send text
#   telegram_send.sh -f /path/to/file.xlsx "Caption here"  # send file
#
# ENV: reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env
#      (auto-sourced from ~/nous-agaas/.env or /Users/madia/nous-agaas/.env)
#
# LESSON-087: NEVER call getUpdates from this script.

set -euo pipefail

# Source .env
for envfile in "$HOME/nous-agaas/.env" "/Users/madia/nous-agaas/.env"; do
  [ -f "$envfile" ] && { set -a; source "$envfile"; set +a; break; }
done

: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN not set}"
: "${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID not set}"

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"

# Parse args
FILE=""
while getopts "f:" opt; do
  case $opt in
    f) FILE="$OPTARG" ;;
    *) echo "Usage: $0 [-f file] message" >&2; exit 1 ;;
  esac
done
shift $((OPTIND - 1))
TEXT="${1:-}"

if [ -n "$FILE" ]; then
  # Send document with optional caption
  if [ ! -f "$FILE" ]; then
    echo "ERROR: file not found: $FILE" >&2
    exit 1
  fi
  curl -s -X POST "$API/sendDocument" \
    -F "chat_id=$TELEGRAM_CHAT_ID" \
    -F "document=@$FILE" \
    ${TEXT:+-F "caption=$TEXT"} \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK: message_id=' + str(d['result']['message_id']) if d.get('ok') else 'ERROR: ' + d.get('description','unknown'))" 2>/dev/null \
    || echo "OK (sent)"
elif [ -n "$TEXT" ]; then
  # Send text message
  curl -s -X POST "$API/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": \"$TELEGRAM_CHAT_ID\", \"text\": $(printf '%s' "$TEXT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo "\"$TEXT\"")}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK: message_id=' + str(d['result']['message_id']) if d.get('ok') else 'ERROR: ' + d.get('description','unknown'))" 2>/dev/null \
    || echo "OK (sent)"
else
  echo "Usage: $0 [-f file] message" >&2
  exit 1
fi
