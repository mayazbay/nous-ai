#!/bin/bash
# test_bdl_cerebro_skill_state_freshness.sh — detect skill-doctrine drift vs live gate state
#
# Enforces bdl-cerebro-replacement-gate v1.2.0 AP-6: gate-check state transitions
# must land in skill Timeline same-session. Runs the live gate, parses per-check
# status, then asserts that for each check whose status != GREEN in the live run,
# the skill's most-recent Timeline entry (within last 14d window) either names
# that check explicitly OR explicitly states "no transitions" / "state stable".
#
# Classifier-AP, NOT hard-gate. Exit 0 always (does not block commits). Output:
# - GREEN: all non-GREEN gate checks are reflected in recent Timeline
# - YELLOW: one or more non-GREEN checks have no matching Timeline entry within 14d window
#
# v1.0.0 — session s0952 (2026-05-25) Mission 3 slice 3.1
# Cross-ref: pages/skills/bdl-cerebro-replacement-gate/SKILL.md AP-6.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || exit 1

SKILL_FILE="pages/skills/bdl-cerebro-replacement-gate/SKILL.md"
GATE_SCRIPT="tools/bdl_cerebro_replacement_gate.py"

[ -f "$SKILL_FILE" ] || { echo "🔴 skill file missing: $SKILL_FILE"; exit 0; }
[ -f "$GATE_SCRIPT" ] || { echo "🔴 gate script missing: $GATE_SCRIPT"; exit 0; }

# Run live gate. Note: gate exits 1 when overall=RED (not failure, just state)
# — only treat empty output as actual run failure.
gate_json=$(python3 "$GATE_SCRIPT" --json 2>/dev/null || true)
if [ -z "$gate_json" ]; then
    echo "🟡 gate produced no output; cannot check freshness"
    exit 0
fi

# Parse non-GREEN checks. Skip the two derived rollups (bdl_replacement,
# cerebro_replacement) — they're meta-states (`= all upstream GREEN`), not
# standalone state, so they don't need their own Timeline narration.
non_green=$(echo "$gate_json" | python3 -c "
import json, sys
ROLLUPS = {'bdl_replacement', 'cerebro_replacement'}
d = json.load(sys.stdin)
for c in d.get('checks', []):
    if c.get('status') != 'GREEN' and c['check'] not in ROLLUPS:
        print(c['check'])
" 2>/dev/null)

if [ -z "$non_green" ]; then
    echo "✅ all gate checks GREEN; nothing to reflect in skill Timeline"
    exit 0
fi

# Extract Timeline entries from last 14d
cutoff_date=$(python3 -c "import datetime; print((datetime.date.today() - datetime.timedelta(days=14)).isoformat())" 2>/dev/null)
recent_timeline=$(awk '/^## Timeline/{flag=1; next} /^## /{flag=0} flag' "$SKILL_FILE" | \
                  awk -v cutoff="$cutoff_date" '
                  /^- \*\*[0-9]{4}-[0-9]{2}-[0-9]{2}\*\*/ {
                      match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}/)
                      d = substr($0, RSTART, RLENGTH)
                      if (d >= cutoff) {
                          in_recent = 1
                      } else {
                          in_recent = 0
                      }
                  }
                  in_recent { print }
                  ')

yellows=0
checked=0
echo "Live gate non-GREEN checks (vs $SKILL_FILE Timeline last 14d):"
while IFS= read -r check; do
    [ -z "$check" ] && continue
    checked=$((checked + 1))
    if echo "$recent_timeline" | grep -qiE "$check|no transitions|state stable"; then
        echo "  ✅ $check — reflected in Timeline"
    else
        echo "  🟡 $check — NOT reflected in last 14d Timeline"
        yellows=$((yellows + 1))
    fi
done <<< "$non_green"

echo
if [ "$yellows" -eq 0 ]; then
    echo "✅ $checked check(s) inspected, all reflected"
else
    echo "🟡 $yellows of $checked check(s) not reflected — add Timeline entry per AP-6"
fi

# Always exit 0 (classifier, not hard gate)
exit 0
