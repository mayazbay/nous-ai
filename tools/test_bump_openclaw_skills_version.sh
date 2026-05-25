#!/bin/bash
# test_bump_openclaw_skills_version.sh — sibling-test for bump_openclaw_skills_version.sh (AP-36)
#
# Validates the bump tool end-to-end on the LIVE factory:
#   TEST 1: tool runs with exit 0
#   TEST 2: backup file created
#   TEST 3: skill count after ≥ skill count before (no regression)
#   TEST 4: factory has the hard-required Nous operating-loop skills after bump
#
# Destructive on factory state (bumps version by 1 and triggers 1 task).
# Safe because: bump is reversible via backup; task token is unique.
#
# Session 48 D7 (2026-04-18) — closes AP-36 drift on W13.
# Note: factory REBUILDS the snapshot when the gate fires; the rebuild writes
# a fresh snapshot back to sessions.json with version=0 (the current live value
# at rebuild time). So "version strictly increased" is NOT a valid assertion.
# The valid invariants are (a) tool exits 0, (b) backup exists, (c) skill count
# doesn't regress, (d) required operating-loop skills are loaded.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRIMARY="$SCRIPT_DIR/bump_openclaw_skills_version.sh"
SSH_HOST="${OPENCLAW_SSH_HOST:-air}"
SESSIONS_JSON_PATH="/home/node/.openclaw/agents/nous/sessions/sessions.json"
AGENT_KEY="agent:nous:main"
PASS_COUNT=0
FAIL_COUNT=0

check() {
  local name="$1"
  local ok="$2"
  local detail="$3"
  if [ "$ok" = "true" ]; then
    echo "  ✅ $name ($detail)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ❌ $name ($detail)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

get_skill_count() {
  ssh "$SSH_HOST" "docker exec openclaw python3 -c 'import json; d=json.load(open(\"$SESSIONS_JSON_PATH\")); print(len(d[\"$AGENT_KEY\"][\"skillsSnapshot\"].get(\"skills\", [])))'" 2>&1 | tail -1
}

get_missing_required_skills() {
  ssh "$SSH_HOST" "docker exec openclaw cat $SESSIONS_JSON_PATH" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
snap = d.get('$AGENT_KEY', {}).get('skillsSnapshot', {})
required = {'ceo-hierarchy','collaborative-reading','find-skills','musk-algorithm','operator-boundaries','session-architecture','gbrain-ops','karpathy-loop','session-coordination','session-operating-contract'}
loaded = set(s.get('name') for s in snap.get('skills', []))
print(','.join(sorted(required - loaded)))
" 2>/dev/null
}

if [ ! -x "$PRIMARY" ]; then
  echo "ERROR: $PRIMARY missing or not executable" >&2
  exit 3
fi

echo "=== capture pre-bump state ==="
COUNT_BEFORE=$(get_skill_count)
echo "  skill count before: $COUNT_BEFORE"

echo "=== TEST 1: invoke primary tool, expect exit 0 ==="
bash "$PRIMARY" >/dev/null 2>&1
EXIT=$?
check "tool exit=0" "$([ "$EXIT" = "0" ] && echo true || echo false)" "got=$EXIT"

echo "=== TEST 2: backup file created ==="
BAK_COUNT=$(ssh "$SSH_HOST" "docker exec openclaw sh -c 'ls ${SESSIONS_JSON_PATH}.bak-* 2>/dev/null | wc -l'" 2>&1 | tail -1 | tr -d ' ')
check "backup files present" "$([ "${BAK_COUNT:-0}" -ge "1" ] && echo true || echo false)" "bak_count=$BAK_COUNT"

echo "=== TEST 3: skill count after ≥ before (no regression) ==="
COUNT_AFTER=$(get_skill_count)
echo "  skill count after: $COUNT_AFTER"
check "no regression" "$([ "${COUNT_AFTER:-0}" -ge "${COUNT_BEFORE:-0}" ] && echo true || echo false)" "before=$COUNT_BEFORE after=$COUNT_AFTER"

echo "=== TEST 4: required operating-loop skills loaded ==="
MISSING_REQUIRED=$(get_missing_required_skills)
check "required skills loaded" "$([ -z "$MISSING_REQUIRED" ] && echo true || echo false)" "missing=${MISSING_REQUIRED:-none}"

echo ""
echo "=== RESULT: $PASS_COUNT PASS / $FAIL_COUNT FAIL ==="
[ "$FAIL_COUNT" = "0" ]
