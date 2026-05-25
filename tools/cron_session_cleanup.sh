#!/bin/bash
# tools/cron_session_cleanup.sh — runs on Air every 60s via launchd.
# 1. Read ~/nous-agaas/state/active-sessions.jsonl.
# 2. Per session_id: compute last_activity (max of register/heartbeat ts), check for close record.
# 3. Move (a) closed sessions and (b) stale (>30min last_activity) records to monthly archive.
# 4. Rewrite active file with only fresh-active records using temp+atomic-rename.
set -u
REGISTRY="${SESSION_REGISTRY_PATH:-$HOME/nous-agaas/state/active-sessions.jsonl}"
ARCHIVE_DIR="$HOME/nous-agaas/state/archive"
mkdir -p "$ARCHIVE_DIR"
ARCHIVE_MONTH="$ARCHIVE_DIR/active-sessions-$(date +%Y-%m).jsonl"
INVALID_MONTH="$ARCHIVE_DIR/active-sessions-invalid-$(date +%Y-%m).jsonl"

[ -f "$REGISTRY" ] || exit 0
[ -s "$REGISTRY" ] || exit 0

NOW_EPOCH=$(date +%s)
STALE_CUTOFF=$((NOW_EPOCH - 1800))
TMP_ACTIVE=$(mktemp "$REGISTRY.XXXXXX")
TMP_ARCHIVE=$(mktemp "$ARCHIVE_MONTH.XXXXXX")

# Compute per-session classification using jq
RAW=$(cat "$REGISTRY")
CLEAN=$(printf '%s\n' "$RAW" | jq -Rrc 'fromjson? | select(type=="object" and .session_id? and .op?)' 2>/dev/null || true)
INVALID=$(printf '%s\n' "$RAW" | jq -Rr 'select((fromjson? | type) != "object")' 2>/dev/null || true)
if [ -n "$INVALID" ]; then
  printf '%s\n' "$INVALID" >> "$INVALID_MONTH"
fi
if [ -z "$CLEAN" ]; then
  if [ -n "$INVALID" ]; then
    : > "$REGISTRY"
  fi
  rm -f "$TMP_ACTIVE" "$TMP_ARCHIVE"
  exit 0
fi

# Build a session-id → state map: { closed: bool, last_activity: epoch, records: [...] }
CLASSIFIED=$(printf '%s\n' "$CLEAN" | jq -s --argjson cutoff "$STALE_CUTOFF" '
  group_by(.session_id) | map({
    session_id: .[0].session_id,
    records: .,
    has_register: (any(.[]?; .op=="register")),
    closed: (any(.[]?; .op=="close")),
    last_activity: (
      (map(select(.op=="register" or .op=="heartbeat")) | sort_by(.ts // .started_at) | last // null)
      | if . == null then 0
        else
          (.ts // .started_at)
          | sub(":(?<m>[0-9]{2})$"; "\(.m)")
          | strptime("%Y-%m-%dT%H:%M:%S%z") | mktime
        end
    )
  })
' 2>/dev/null)

if [ -z "$CLASSIFIED" ] || [ "$CLASSIFIED" = "null" ]; then
  rm -f "$TMP_ACTIVE" "$TMP_ARCHIVE"
  exit 0
fi

# Active records (keep): non-closed AND last_activity > cutoff
echo "$CLASSIFIED" | jq -c --argjson cutoff "$STALE_CUTOFF" '
  .[] | select(.has_register == true and .closed == false and .last_activity > $cutoff) | .records[]
' >> "$TMP_ACTIVE" 2>/dev/null

# Archive records: closed, stale, or orphaned heartbeats without a register record.
echo "$CLASSIFIED" | jq -c --argjson cutoff "$STALE_CUTOFF" '
  .[] | select(.has_register == false or .closed == true or .last_activity <= $cutoff) | .records[]
' >> "$TMP_ARCHIVE" 2>/dev/null

# If anything to archive, append + atomic rename of active
if [ -s "$TMP_ARCHIVE" ] || [ -n "$INVALID" ]; then
  cat "$TMP_ARCHIVE" >> "$ARCHIVE_MONTH"
  mv "$TMP_ACTIVE" "$REGISTRY"
else
  rm -f "$TMP_ACTIVE"
fi
rm -f "$TMP_ARCHIVE"
exit 0
