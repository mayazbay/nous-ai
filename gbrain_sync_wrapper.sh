#!/bin/bash
# gbrain_sync_wrapper.sh — Sync wiki to GBrain + maintain links + clean junk
# Called by cron every 5 minutes.

set -euo pipefail

export PATH="/root/.bun/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export DATABASE_URL="${DATABASE_URL:-postgresql://gbrain:gbrain2026@localhost:5432/gbrain}"

load_openai_compatible_proxy() {
  local proxy_env="${GBRAIN_OPENAI_COMPAT_ENV:-/root/.gbrain/openai-compatible.env}"
  if [ -f "$proxy_env" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$proxy_env"
    set +a
  fi
}

load_openai_key() {
  if [ -n "${OPENAI_API_KEY:-}" ]; then
    return 0
  fi

  local key=""
  if [ -f /root/.config/codex/auth.json ]; then
    key="$(python3 - <<'PY' 2>/dev/null || true
import json
from pathlib import Path

path = Path("/root/.config/codex/auth.json")
data = json.loads(path.read_text())
print(data.get("OPENAI_API_KEY", ""))
PY
)"
  fi

  if [ -z "$key" ] && [ -f /root/nous-agaas/.env ]; then
    key="$(grep -E '^OPENAI_API_KEY=' /root/nous-agaas/.env 2>/dev/null | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true)"
  fi

  if [ -n "$key" ]; then
    export OPENAI_API_KEY="$key"
  fi
}

load_openai_compatible_proxy
load_openai_key
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] gbrain sync wrapper: OPENAI_API_KEY missing; refusing to create embed ghosts" >&2
  exit 2
fi

if [ "${GBRAIN_SYNC_WRAPPER_DRY_RUN:-0}" = "1" ]; then
  echo "gbrain sync wrapper dry-run: key_loaded len=${#OPENAI_API_KEY}"
  exit 0
fi

GBRAIN="/opt/nous-agaas/gbrain/bin/gbrain"
WIKI="/root/nous-agaas/wiki"
TOOLS="${GBRAIN_TOOLS_DIR:-$WIKI/tools}"
LOG="/var/log/gbrain-sync.log"

# 1. Sync wiki to GBrain (incremental — only re-embeds changed files)
# AP-99 wiring: tee sync output through tools/test_no_lying_logs.py; on violation fire tg_send.sh.
# AP-100 P3-fix: sweep stale sync tmps left from prior signals/crashes.
find /tmp -maxdepth 1 -name 'gbrain-sync.*.log' -mmin +30 -delete 2>/dev/null || true
SYNC_TMP="$(mktemp /tmp/gbrain-sync.XXXXXX.log)"
trap 'rm -f "$SYNC_TMP"' EXIT
# AP-100 P2-fix: capture rc, log unconditionally, then evaluate. Previous code
# died at $GBRAIN sync non-zero under set -e BEFORE appending to $LOG — failed
# syncs went invisible. Now: log first (observability), then handle rc + gate.
SYNC_RC=0
$GBRAIN sync "$WIKI" >"$SYNC_TMP" 2>&1 || SYNC_RC=$?
cat "$SYNC_TMP" >> "$LOG"
if [ "$SYNC_RC" -ne 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] gbrain sync exited rc=$SYNC_RC; running gate before bailing" >> "$LOG"
fi
if ! python3 "$TOOLS/test_no_lying_logs.py" --input "$SYNC_TMP" >> "$LOG" 2>&1; then
  FAIL_COUNT="$(grep -c 'embedding failed' "$SYNC_TMP" || true)"
  TAIL_SNIP="$(tail -5 "$SYNC_TMP" | tr '\n' ' ' | head -c 240)"
  # AP-101 P3-2 (codex council): tg_send fallback — if Telegram delivery fails
  # (network/token/rate-limit), record JSONL + stderr signal so the failure is
  # observable beyond just the cycle return code.
  if ! bash "$TOOLS/tg_send.sh" "🔴 gbrain sync lying-log violation on $(hostname) at $(date '+%FT%TZ'). ${FAIL_COUNT} 'embedding failed' lines + positive 'pages embedded' summary. tail: ${TAIL_SNIP}" >> "$LOG" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] AP-101 ALERT tg_send_failed context=manual-sync fail_count=$FAIL_COUNT" >> "$LOG"
    echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"event\":\"tg_send_failed\",\"context\":\"manual-sync\",\"fail_count\":$FAIL_COUNT,\"host\":\"$(hostname)\"}" >> "${GBRAIN_ALERT_FALLBACK_LOG:-/root/.gbrain/alerts-fallback.jsonl}" 2>/dev/null || true
  fi
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] AP-99 ALERT: gbrain sync lying-log gate exit 1" >> "$LOG"
  exit 1
fi
if [ "$SYNC_RC" -ne 0 ]; then
  exit "$SYNC_RC"
fi

# 2. Clean junk pages (node_modules, etc.)
PGPASSWORD=gbrain2026 psql -U gbrain -h localhost -d gbrain -t -A \
  -c "DELETE FROM content_chunks WHERE page_id IN (SELECT id FROM pages WHERE slug LIKE 'raw/presentations/node_modules%');
      DELETE FROM links WHERE from_page_id IN (SELECT id FROM pages WHERE slug LIKE 'raw/presentations/node_modules%') OR to_page_id IN (SELECT id FROM pages WHERE slug LIKE 'raw/presentations/node_modules%');
      DELETE FROM pages WHERE slug LIKE 'raw/presentations/node_modules%';" >> "$LOG" 2>&1

# 3. Update link graph (idempotent — only registers new links)
cd "$WIKI" && python3 "$TOOLS/gbrain_link_builder.py" >> "$LOG" 2>&1

# 4. Update timeline entries (idempotent — only registers new entries)
cd "$WIKI" && python3 "$TOOLS/gbrain_timeline_builder.py" >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Full sync cycle done" >> "$LOG"
