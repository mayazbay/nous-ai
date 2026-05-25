#!/bin/bash
set -euo pipefail
DEPLOY="$(cd "$(dirname "$0")/.." && pwd)/secrets-deploy.sh"
[ -x "$DEPLOY" ] || { echo "FAIL: $DEPLOY not executable"; exit 1; }

OUT=$("$DEPLOY" --dry-run apk-status-bot vps 2>&1)

echo "$OUT" | grep -q "APK_BOT_TOKEN" || { echo "FAIL: APK_BOT_TOKEN not in plan"; echo "$OUT"; exit 1; }
echo "$OUT" | grep -q "APK_BOT_ADMIN_DM_CHAT_ID" || { echo "FAIL: chat_id not in plan"; echo "$OUT"; exit 1; }
echo "$OUT" | grep -q "65.108.215.200" || { echo "FAIL: target host not in plan"; echo "$OUT"; exit 1; }

if echo "$OUT" | grep -qE '(Host key|Connection|scp:|ssh:)'; then
  echo "FAIL: --dry-run appears to have attempted ssh"
  echo "$OUT"
  exit 1
fi

echo "OK: dry-run prints plan without ssh"
