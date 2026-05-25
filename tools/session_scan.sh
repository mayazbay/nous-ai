#!/bin/bash
# tools/session_scan.sh — read Air session registry, filter active (last_activity <30min stale),
# print human table OR --json. --overlap-with intersects scope against caller's paths.
#
# Usage:
#   session_scan.sh                          # human-readable table
#   session_scan.sh --json                   # machine-readable JSON array
#   session_scan.sh --overlap-with "p1,p2"   # filter to records whose declared_scope intersects
set -u
JSON=0
OVERLAP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1; shift ;;
    --overlap-with) OVERLAP="$2"; shift 2 ;;
    *) echo "session_scan: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Pull registry from Air. When already running on Air, avoid ssh-loopback.
LOCAL_REGISTRY="${SESSION_REGISTRY_PATH:-$HOME/nous-agaas/state/active-sessions.jsonl}"
REMOTE_REGISTRY="${SESSION_REGISTRY_PATH:-\$HOME/nous-agaas/state/active-sessions.jsonl}"
FETCH_OK=0
if [ "${SESSION_FORCE_AIR_LOCAL:-0}" = "1" ] || { hostname 2>/dev/null | grep -qi 'air' && [ "${SESSION_FORCE_REMOTE:-0}" != "1" ]; }; then
  RAW=$(cat "$LOCAL_REGISTRY" 2>/dev/null || echo "")
  FETCH_OK=1
else
  if RAW=$(ssh -o ConnectTimeout=5 -o BatchMode=yes air "cat \"$REMOTE_REGISTRY\" 2>/dev/null" 2>/dev/null); then
    FETCH_OK=1
  else
    RAW=""
  fi
fi
if [ "$FETCH_OK" -ne 1 ]; then
  if [ "$JSON" -eq 1 ]; then echo "[]"; else echo "  🟡 session registry unavailable (Air unreachable); cannot prove no other active sessions"; fi
  exit 1
fi
if [ -z "$RAW" ]; then
  if [ "$JSON" -eq 1 ]; then echo "[]"; else echo "  ✅ no other active sessions"; fi
  exit 0
fi
CLEAN=$(printf '%s\n' "$RAW" | jq -Rrc 'fromjson? | select(type=="object" and .session_id? and .op?)' 2>/dev/null || true)
if [ -z "$CLEAN" ]; then
  if [ "$JSON" -eq 1 ]; then echo "[]"; else echo "  ✅ no other active sessions"; fi
  exit 0
fi

NOW_EPOCH=$(date +%s)
STALE_CUTOFF=$((NOW_EPOCH - 1800))  # 30min

# jq pipeline:
# 1. Group records by session_id.
# 2. For each group: extract latest register, max ts of heartbeats, status (closed?), compute last_activity.
# 3. Filter to non-closed AND last_activity > stale_cutoff.
ACTIVE=$(printf '%s\n' "$CLEAN" | jq -s --argjson cutoff "$STALE_CUTOFF" '
  group_by(.session_id) | map(
    {
      session_id: .[0].session_id,
      register: (map(select(.op=="register")) | first),
      last_heartbeat: (map(select(.op=="heartbeat")) | sort_by(.ts) | last),
      closed: (any(.[]?; .op=="close"))
    }
    | select(.closed == false)
    | select(.register != null)
    | . + {
        last_activity: (
          (.last_heartbeat.ts // .register.started_at)
          | sub(":(?<m>[0-9]{2})$"; "\(.m)")
          | strptime("%Y-%m-%dT%H:%M:%S%z") | mktime
        )
      }
    | select(.last_activity > $cutoff)
  )
' 2>/dev/null)

# Local dead-PID rows are coordination noise, not real active lanes. The
# heartbeat skips dead local PID files, but a fresh desktop/CLI registration can
# otherwise remain "active" for the 30 minute TTL even after its process exits.
if [ "${SESSION_SCAN_FILTER_DEAD_LOCAL_PID:-1}" = "1" ]; then
  LOCAL_HOST=$(hostname -s 2>/dev/null | tr '[:upper:]' '[:lower:]' | sed 's/\.local$//')
  case "$LOCAL_HOST" in
    mac*|*macbook*) LOCAL_HOST="mac" ;;
    air|*air*)      LOCAL_HOST="air" ;;
    *vps*)          LOCAL_HOST="vps" ;;
    *)              LOCAL_HOST="${LOCAL_HOST:-unknown}" ;;
  esac
  LIVE_PID_JSON=$(ps -axo pid= 2>/dev/null | awk '{$1=$1; if ($1 != "") print $1}' | jq -Rsc 'split("\n") | map(select(length>0))')
  ACTIVE=$(echo "$ACTIVE" | jq --arg host "$LOCAL_HOST" --argjson live "$LIVE_PID_JSON" '
    map(select(
      (.register.host != $host)
      or (.register.pid == null)
      or ((.register.pid | tostring) as $pid | ($live | index($pid)) != null)
    ))
  ')
fi

# If --overlap-with, filter to sessions whose scope intersects the requested paths
if [ -n "$OVERLAP" ]; then
  OVERLAP_JSON=$(echo "$OVERLAP" | jq -Rc 'split(",") | map(select(length>0))')
  ACTIVE=$(echo "$ACTIVE" | jq --argjson o "$OVERLAP_JSON" '
    def norm: sub("^\\./"; "") | sub("^Nous/"; "") | sub("/+$"; "");
    def has_glob: test("[*?]");
    def glob_to_regex:
      gsub("(?<m>[][.\\\\^$+{}()|])"; "\\" + .m)
      | gsub("\\*"; ".*")
      | gsub("\\?"; ".")
      | "^" + . + "$";
    def overlaps($scope; $path):
      ($scope | norm) as $s |
      ($path | norm) as $p |
      (
        $s == "*" or $p == "*" or
        $s == $p or
        ($s | startswith($p + "/")) or
        ($p | startswith($s + "/")) or
        (($s | has_glob) and ($p | test(($s | glob_to_regex)))) or
        (($p | has_glob) and ($s | test(($p | glob_to_regex))))
      );
    map(select(
      (.register.declared_scope // []) as $scope
      | any($scope[]?; . as $s | any($o[]?; . as $p | overlaps($s; $p)))
    ))
  ')
fi

if [ "$JSON" -eq 1 ]; then
  echo "$ACTIVE"
  exit 0
fi

COUNT=$(echo "$ACTIVE" | jq 'length')
if [ "$COUNT" = "0" ]; then
  echo "  ✅ no other active sessions"
  exit 0
fi
echo "  🟡 PARALLEL: $COUNT active session(s)"
echo "$ACTIVE" | jq -r '.[] | "    • \(.register.session_id) [\(.register.host)] started=\(.register.started_at) intent=\"\(.register.intent)\" scope=\(.register.declared_scope|join(","))"'
exit 0
