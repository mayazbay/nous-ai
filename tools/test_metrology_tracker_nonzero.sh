#!/bin/bash
# test_metrology_tracker_nonzero.sh — detect metrology tracker data-source drift
#
# Enforces metrology-cert-tracker v1.1.0 AP-2: live VPS run of
# MetrologyCertTracker().get_summary() must return total_cameras > 0.
# Zero means the data source is empty (likely camera_registry was wiped) OR
# the tracker is pointed at the wrong table.
#
# Classifier-AP, NOT hard-gate. Exit 0 always. Output:
# - GREEN: total_cameras > 0
# - YELLOW: total_cameras == 0 (matches AP-2's documented broken state — skill
#   already self-documents the issue, this detector confirms it persists)
# - RED: tracker raised an exception (worse than zero — tracker itself broken)
#
# Requires VPS SSH access (root@65.108.215.200) and the OpenClaw container
# mount at /opt/nous-agaas/erap/. Skips with NOTE if SSH unavailable (CI etc).
#
# v1.0.0 — session s0952 (2026-05-25) Mission 3 slice 3.1
# Cross-ref: pages/skills/metrology-cert-tracker/SKILL.md AP-2.

set -u

VPS_HOST="root@65.108.215.200"

# Probe SSH reachability (5s timeout)
if ! ssh -o ConnectTimeout=5 "$VPS_HOST" "true" 2>/dev/null; then
    echo "NOTE: VPS unreachable from this host (5s timeout); skipping live check"
    exit 0
fi

# Run the live tracker summary on VPS
summary=$(ssh "$VPS_HOST" "cd /opt/nous-agaas && python3 -c \"
import sys
sys.path.insert(0, '/opt/nous-agaas')
try:
    from erap.metrology_cert_tracker import MetrologyCertTracker
    t = MetrologyCertTracker()
    s = t.get_summary()
    print('OK', s['total_cameras'], s['expired'], s['valid'], s.get('report_date', ''))
except Exception as e:
    print('ERR', type(e).__name__, str(e)[:200])
\"" 2>&1)

status=$(echo "$summary" | head -1 | cut -d' ' -f1)

if [ "$status" = "OK" ]; then
    total=$(echo "$summary" | head -1 | cut -d' ' -f2)
    expired=$(echo "$summary" | head -1 | cut -d' ' -f3)
    valid=$(echo "$summary" | head -1 | cut -d' ' -f4)
    date=$(echo "$summary" | head -1 | cut -d' ' -f5)

    if [ "$total" -gt 0 ] 2>/dev/null; then
        echo "✅ GREEN — metrology tracker live (total=$total expired=$expired valid=$valid date=$date)"
        exit 0
    else
        echo "🟡 YELLOW — tracker returns 0 total cameras (matches v1.1.0 AP-2 drift)"
        echo "    Investigation pointers per AP-2:"
        echo "    (1) ssh $VPS_HOST 'ls /opt/nous-agaas/erap/data/'"
        echo "    (2) cross-check erap.camera_registry source for table/path"
        echo "    (3) camera_status table has 281 rows (per bdl-cerebro gate fleet_health) — consider re-pointing"
        exit 0
    fi
elif [ "$status" = "ERR" ]; then
    err_type=$(echo "$summary" | head -1 | cut -d' ' -f2)
    err_msg=$(echo "$summary" | head -1 | cut -d' ' -f3-)
    echo "🔴 RED — tracker itself failed: $err_type — $err_msg"
    exit 0
else
    echo "🔴 RED — unexpected output: $summary" | head -3
    exit 0
fi
