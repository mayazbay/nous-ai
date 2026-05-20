#!/bin/bash
# Test tools/secrets-manifest-parse.sh — given (service, target), returns
# rows in "key|type|icloud|value" format (value empty for secrets).
set -euo pipefail
PARSER="$(cd "$(dirname "$0")/.." && pwd)/secrets-manifest-parse.sh"
MANIFEST="$(cd "$(dirname "$0")/../.." && pwd)/pages/secrets-manifest.md"
[ -x "$PARSER" ] || { echo "FAIL: $PARSER not executable"; exit 1; }
[ -f "$MANIFEST" ] || { echo "FAIL: $MANIFEST missing"; exit 1; }

OUT=$("$PARSER" "$MANIFEST" apk-status-bot vps)

N=$(echo "$OUT" | wc -l | tr -d ' ')
[ "$N" -eq 2 ] || { echo "FAIL: expected 2 rows, got $N"; echo "$OUT"; exit 1; }

echo "$OUT" | grep -q '^APK_BOT_TOKEN|secret|no|$' || { echo "FAIL: APK_BOT_TOKEN row (icloud=no per AP-8)"; echo "$OUT"; exit 1; }
echo "$OUT" | grep -q '^APK_BOT_ADMIN_DM_CHAT_ID|constant|n/a|110793056$' || { echo "FAIL: chat_id row"; echo "$OUT"; exit 1; }

echo "OK: parser emits 2 rows matching manifest"
