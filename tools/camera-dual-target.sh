#!/usr/bin/env bash
# camera-dual-target.sh — Run from inside Satory network (10.235.* reachable).
# Adds 65.108.215.200:9080 as a SECOND notification target on each ЛУ camera
# while PRESERVING the existing target (10.141.0.104:8581 or other).
#
# B-step-2 of the two-step ladder defined in satory-dashboard SKILL AP-12.
# Run B-step-1 (egress probe) FIRST: curl -v http://65.108.215.200:9080/health
# Only run this script if the probe returned HTTP 200.
#
# Usage:
#   bash camera-dual-target.sh --dry-run --limit 1   # preview against 1 camera, no PUT
#   bash camera-dual-target.sh --dry-run             # preview against ALL cameras, no PUT
#   bash camera-dual-target.sh                       # commit changes (adds id=N = OUR_IP)
#   bash camera-dual-target.sh --add-target DP_IP:DP_PORT  # add a DIFFERENT target (e.g. ДП id=3)
#   bash camera-dual-target.sh --add-target 10.99.1.1:8080 --dry-run  # preview ДП id=3 without PUT
#
# B-step-3 (revenue-blockers.md, Madi directive 2026-05-12, BOTH A+B coexist):
# After running with default OUR_IP for id=2 (our VPS), re-run with --add-target DP_IP:DP_PORT
# so cameras push to id=1 БДЛ + id=2 our VPS + id=3 ДП in parallel. Script preserves existing
# entries and adds new ones at next available id (script's existing add-not-replace logic).
#
# Env overrides:
#   CAMERA_LU_USER, CAMERA_LU_PASS — camera credentials (REQUIRED; see camera-management SKILL)
#   OUR_IP, OUR_PORT, OUR_PATH     — endpoint (default 65.108.215.200:9080/events/camera/hxml)
#   --add-target IP:PORT           — overrides OUR_IP+OUR_PORT for this run (OUR_PATH preserved)

set -uo pipefail

DRY_RUN=0
LIMIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)  DRY_RUN=1 ;;
    --limit)    LIMIT="${2:-1}"; shift ;;
    --add-target)
      target="${2:-}"
      if [ -z "$target" ] || ! echo "$target" | grep -qE '^[^:]+:[0-9]+$'; then
        echo "ERROR: --add-target requires IP:PORT format (e.g. 10.99.1.1:8080)" >&2
        exit 2
      fi
      OUR_IP="${target%:*}"
      OUR_PORT="${target##*:}"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--dry-run] [--limit N] [--add-target IP:PORT]"
      echo "  --dry-run             GET each camera config, print what would change, do NOT PUT"
      echo "  --limit N             Process only first N cameras (useful with --dry-run)"
      echo "  --add-target IP:PORT  Add a DIFFERENT endpoint (e.g. ДП id=3) instead of default OUR_IP"
      echo
      echo "Two-pass ДП deployment (B-step-3, revenue-blockers.md):"
      echo "  1. bash $0                              # adds our VPS as id=2"
      echo "  2. bash $0 --add-target DP_IP:DP_PORT   # adds ДП as id=3"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

CAMERA_USER="${CAMERA_LU_USER:-oper}"
CAMERA_PASS="${CAMERA_LU_PASS:-}"
if [ -z "$CAMERA_PASS" ]; then
  echo "ERROR: CAMERA_LU_PASS not set" >&2
  echo "  export CAMERA_LU_PASS='<camera-password>'  # see camera-management/SKILL.md or pages/legal/credentials/" >&2
  echo "  Or load from env file:  set -a && source ~/.camera-creds && set +a" >&2
  exit 3
fi
OUR_IP="${OUR_IP:-65.108.215.200}"
OUR_PORT="${OUR_PORT:-9080}"
OUR_PATH="${OUR_PATH:-/events/camera/hxml}"

# ЛУ camera IPs (from events.db — known cameras that pushed events before Apr-5)
CAMERA_IPS=(
  10.235.0.3   10.235.0.34  10.235.0.35  10.235.0.36  10.235.0.37  10.235.0.4  10.235.0.5
  10.235.1.2   10.235.1.3   10.235.1.34  10.235.1.35  10.235.1.36  10.235.1.37  10.235.1.4  10.235.1.5
  10.235.8.3   10.235.8.34  10.235.8.35  10.235.8.36  10.235.8.37  10.235.8.4
  10.235.9.2   10.235.9.3   10.235.9.4   10.235.9.34  10.235.9.36  10.235.9.37
  10.235.9.98  10.235.9.99  10.235.9.100 10.235.9.101
  10.235.9.130 10.235.9.131 10.235.9.132 10.235.9.133
  10.235.9.162 10.235.9.163 10.235.9.164 10.235.9.165
  10.235.9.194 10.235.9.195 10.235.9.196 10.235.9.197 10.235.9.228 10.235.9.229
  10.235.10.3  10.235.10.34 10.235.10.35 10.235.10.36 10.235.10.37 10.235.10.5
)

if [ "$LIMIT" -gt 0 ]; then
  CAMERA_IPS=("${CAMERA_IPS[@]:0:$LIMIT}")
fi

if [ "$DRY_RUN" = "1" ]; then
  echo "=== DRY-RUN: ${#CAMERA_IPS[@]} camera(s), no PUT — read + plan only ==="
else
  echo "=== LIVE: ${#CAMERA_IPS[@]} camera(s), will PUT changes ==="
fi
echo "target endpoint: ${OUR_IP}:${OUR_PORT}${OUR_PATH}"
echo ""

ok=0; fail=0; skip=0; would_change=0

for IP in "${CAMERA_IPS[@]}"; do
  current=$(curl -s --connect-timeout 3 -u "${CAMERA_USER}:${CAMERA_PASS}" \
    "http://${IP}/ISAPI/Event/notification/httpHosts" 2>/dev/null)

  if [ -z "$current" ]; then
    echo "SKIP  $IP  (unreachable)"
    skip=$((skip + 1)); continue
  fi

  if echo "$current" | grep -q "${OUR_IP}"; then
    echo "SKIP  $IP  (already has ${OUR_IP})"
    skip=$((skip + 1)); continue
  fi

  max_id=$(echo "$current" | grep -oE '<id>[0-9]+</id>' | grep -oE '[0-9]+' | sort -n | tail -1)
  next_id=$(( ${max_id:-0} + 1 ))

  existing_entries=$(echo "$current" | tr '\n' ' ' | grep -oE '<HttpHostNotification>.*</HttpHostNotification>' || true)

  new_entry="<HttpHostNotification>
<id>${next_id}</id>
<url>${OUR_PATH}</url>
<protocolType>HTTP</protocolType>
<parameterFormatType>XML</parameterFormatType>
<addressingFormatType>ipaddress</addressingFormatType>
<ipAddress>${OUR_IP}</ipAddress>
<portNo>${OUR_PORT}</portNo>
<httpAuthenticationMethod>none</httpAuthenticationMethod>
</HttpHostNotification>"

  combined_xml='<?xml version="1.0" encoding="UTF-8"?><HttpHostNotificationList>'"${existing_entries}${new_entry}"'</HttpHostNotificationList>'

  if [ "$DRY_RUN" = "1" ]; then
    echo "PLAN  $IP  would add ID=${next_id} → ${OUR_IP}:${OUR_PORT}${OUR_PATH}  (current max_id=${max_id:-0})"
    would_change=$((would_change + 1))
    continue
  fi

  result=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 \
    -u "${CAMERA_USER}:${CAMERA_PASS}" \
    -X PUT "http://${IP}/ISAPI/Event/notification/httpHosts" \
    -H "Content-Type: application/xml" \
    --data "${combined_xml}" 2>/dev/null)

  if [ "$result" = "200" ] || [ "$result" = "201" ]; then
    echo "OK    $IP  → added ID ${next_id} → ${OUR_IP}:${OUR_PORT}${OUR_PATH}"
    ok=$((ok + 1))
  else
    echo "FAIL  $IP  HTTP ${result}"
    fail=$((fail + 1))
  fi
done

echo ""
if [ "$DRY_RUN" = "1" ]; then
  echo "=== DRY-RUN summary: WOULD_CHANGE=${would_change} SKIP=${skip} ==="
  echo "Re-run without --dry-run to commit."
else
  echo "=== Summary: OK=${ok} FAIL=${fail} SKIP=${skip} ==="
fi
echo "Run from a machine inside the Satory 10.235.* network."
