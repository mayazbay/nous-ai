#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TG_SEND="$SCRIPT_DIR/tg_send.sh"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

set +e
AUTONOMY_BYPASS=1 bash "$TG_SEND" --chat -100123 "Денис, приняли endpoint." >"$tmp" 2>&1
rc=$?
set -e
if [ "$rc" -ne 5 ]; then
  echo "expected personal group salutation to be blocked with exit 5, got $rc" >&2
  cat "$tmp" >&2
  exit 1
fi
grep -q "group message starts with a personal salutation" "$tmp"

set +e
TELEGRAM_BOT_TOKEN="test:token" AUTONOMY_BYPASS=1 bash "$TG_SEND" --chat -100123 --allow-named-addressee "Денис, приняли endpoint." >"$tmp" 2>&1
rc=$?
set -e
if [ "$rc" -ne 3 ]; then
  echo "expected allowed named send to reach Telegram API and fail with test token exit 3, got $rc" >&2
  cat "$tmp" >&2
  exit 1
fi

set +e
TELEGRAM_BOT_TOKEN="test:token" AUTONOMY_BYPASS=1 bash "$TG_SEND" --chat -100123 "Коллеги, приняли endpoint." >"$tmp" 2>&1
rc=$?
set -e
if [ "$rc" -ne 3 ]; then
  echo "expected neutral group send to pass guard and fail with test token exit 3, got $rc" >&2
  cat "$tmp" >&2
  exit 1
fi

echo "tg_send manual group addressee guard OK"
