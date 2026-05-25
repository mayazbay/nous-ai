#!/usr/bin/env bash
# refresh_satory_fixture.sh — rebuild the Satory VPS golden SQLite fixture
# from production for schema-contract testing of Camera Doctor MVP.
#
# Per PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1 Phase 1 Task 1.1.
# Schedule: weekly via launchd (com.nous.satory-fixture-refresh — to be created
# in a follow-up); for now run manually when production schema may have drifted.
#
# Usage:
#   bash tools/refresh_satory_fixture.sh             # rebuild + diff
#   bash tools/refresh_satory_fixture.sh --commit    # rebuild + commit if changed
#
# Source DBs (production VPS):
#   /opt/nous-agaas/erap/data/events.db        — vehicle_events (event history)
#   /opt/nous-agaas/erap/data/erap_dev.db      — camera_registry (empty as of 2026-04-30)
#   /opt/nous-agaas/erap/data/apk_health.db    — apk_health_current (empty as of 2026-04-30)
#   /opt/nous-agaas/erap/data/camera_health.db — camera_status (281 rows, fleet health)
#
# Honest current schema reality (2026-04-30 audit):
#   vehicle_events:      154,516 rows; MAX(event_time) = 2026-04-05 (25-day stale!)
#   camera_status:       281 rows (real fleet inventory + health source)
#   camera_registry:     0 rows (schema only; do not depend on)
#   apk_health_current:  0 rows (schema only; do not depend on)
#
# Detector mapping:
#   - Detector 1 (Mirrors Stopped) → vehicle_events.MAX(event_time) age check
#   - Detector 2 (VPN/Network Down) → camera_status.last_check freshness + wg handshake
#   - Detector 3 (Fleet Degraded) → camera_status.status='online' percentage

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURE="$REPO_ROOT/tenants/satory/tests/fixtures/satory_vps_snapshot.sqlite"
COMMIT="${1:-}"
TMP="$(mktemp -d)"
trap "rm -rf $TMP" EXIT

mkdir -p "$(dirname "$FIXTURE")"

# Build fresh fixture
{
  ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/events.db '.schema vehicle_events'"
  ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/events.db -cmd '.mode insert vehicle_events' 'SELECT * FROM vehicle_events ORDER BY event_time DESC LIMIT 50;'"
  ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/erap_dev.db '.schema camera_registry'"
  ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/apk_health.db '.schema apk_health_current'"
  ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/camera_health.db '.schema camera_status'"
  ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/camera_health.db -cmd '.mode insert camera_status' 'SELECT * FROM camera_status;'"
} | sqlite3 "$TMP/new.sqlite"

if [ ! -s "$TMP/new.sqlite" ]; then
  echo "ERROR: refresh produced empty fixture" >&2
  exit 2
fi

# Verify required tables + minimum row counts
for tbl in vehicle_events camera_status camera_registry apk_health_current; do
  if ! sqlite3 "$TMP/new.sqlite" ".schema $tbl" 2>/dev/null | grep -q CREATE; then
    echo "ERROR: missing table $tbl in refreshed fixture" >&2
    exit 2
  fi
done

VE_ROWS=$(sqlite3 "$TMP/new.sqlite" "SELECT COUNT(*) FROM vehicle_events;")
CS_ROWS=$(sqlite3 "$TMP/new.sqlite" "SELECT COUNT(*) FROM camera_status;")

if [ "$VE_ROWS" -lt 1 ] || [ "$CS_ROWS" -lt 1 ]; then
  echo "ERROR: fresh fixture has insufficient rows (vehicle_events=$VE_ROWS, camera_status=$CS_ROWS)" >&2
  exit 2
fi

echo "fixture refresh OK:"
echo "  vehicle_events:    $VE_ROWS rows"
echo "  camera_status:     $CS_ROWS rows"
echo "  camera_registry:   $(sqlite3 "$TMP/new.sqlite" "SELECT COUNT(*) FROM camera_registry;") rows (schema only)"
echo "  apk_health_current: $(sqlite3 "$TMP/new.sqlite" "SELECT COUNT(*) FROM apk_health_current;") rows (schema only)"
echo "  last event time:   $(sqlite3 "$TMP/new.sqlite" "SELECT MAX(event_time) FROM vehicle_events;")"

# Diff against existing
if [ -f "$FIXTURE" ] && cmp -s "$TMP/new.sqlite" "$FIXTURE"; then
  echo "no schema/data drift; fixture unchanged"
  exit 0
fi

mv "$TMP/new.sqlite" "$FIXTURE"
echo "fixture updated: $FIXTURE"

if [ "$COMMIT" = "--commit" ]; then
  cd "$REPO_ROOT"
  git add "$FIXTURE"
  git commit -o "$FIXTURE" -m "satory: refresh fixture (vehicle_events=$VE_ROWS camera_status=$CS_ROWS last_event=$(sqlite3 "$FIXTURE" "SELECT MAX(event_time) FROM vehicle_events;"))" || echo "(no changes to commit)"
fi
