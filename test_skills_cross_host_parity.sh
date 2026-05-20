#!/usr/bin/env bash
# Hard invariant: every active SKILL.md in pages/skills/<name>/ MUST have
# byte-identical content (MD5) across all four substrate hosts:
#   1. Mac vault         pages/skills/<name>/SKILL.md
#   2. Air working copy  ~/nous-agaas/wiki/pages/skills/<name>/SKILL.md
#   3. Air runtime       /Users/madia/nous-agaas/skills/<name>/SKILL.md
#   4. OpenClaw container /opt/nous-agaas/skills/<name>/SKILL.md (bind-mount of #3)
#
# Excluded: pages/skills/_gbrain/ (resolver index) and pages/skills/extracted/ (drafts).
#
# Background — codified by audit/SKILL.md AP-42:
# wiki-to-runtime-rsync.sh + Air auto-checkpoint + 3-way wiki git sync
# already converge these substrates in production, but no automated test
# pinned the invariant. This test pins it. Run from any host that has SSH
# access to Air (typically Mac dev sessions or VPS).
#
# Usage:
#   bash tools/test_skills_cross_host_parity.sh
#   # exit 0 if all hashes match, exit 1 otherwise
#
# Env overrides:
#   AIR_HOST=air                 SSH alias for Air (default: air)
#   OPENCLAW_NAME=openclaw       docker container name (default: openclaw)
#   SKIP_CONTAINER=1             skip container check (when docker not reachable)

set -uo pipefail

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
AIR_HOST="${AIR_HOST:-air}"
OPENCLAW_NAME="${OPENCLAW_NAME:-openclaw}"

cd "$VAULT"

SKILLS=$(ls pages/skills/ 2>/dev/null | grep -v '\.md$' | grep -v '^_' | grep -v '^extracted$')
TOTAL=0
DRIFT=0
DRIFT_LINES=""

for s in $SKILLS; do
  MAC_FILE="pages/skills/$s/SKILL.md"
  [ ! -f "$MAC_FILE" ] && continue
  TOTAL=$((TOTAL + 1))

  MAC_HASH=$(md5 -q "$MAC_FILE" 2>/dev/null || md5sum "$MAC_FILE" 2>/dev/null | cut -d' ' -f1)
  WIKI_HASH=$(ssh -o BatchMode=yes "$AIR_HOST" "md5 -q ~/nous-agaas/wiki/pages/skills/$s/SKILL.md 2>/dev/null || md5sum ~/nous-agaas/wiki/pages/skills/$s/SKILL.md 2>/dev/null | cut -d' ' -f1" 2>/dev/null)
  RUN_HASH=$(ssh -o BatchMode=yes "$AIR_HOST" "md5 -q /Users/madia/nous-agaas/skills/$s/SKILL.md 2>/dev/null || md5sum /Users/madia/nous-agaas/skills/$s/SKILL.md 2>/dev/null | cut -d' ' -f1" 2>/dev/null)

  CTR_HASH=""
  if [ "${SKIP_CONTAINER:-0}" != "1" ]; then
    CTR_HASH=$(ssh -o BatchMode=yes "$AIR_HOST" "docker exec $OPENCLAW_NAME md5sum /opt/nous-agaas/skills/$s/SKILL.md 2>/dev/null | cut -d' ' -f1" 2>/dev/null)
  fi

  drift_for_skill=0
  if [ "$MAC_HASH" != "$WIKI_HASH" ]; then drift_for_skill=1; fi
  if [ "$MAC_HASH" != "$RUN_HASH" ]; then drift_for_skill=1; fi
  if [ "${SKIP_CONTAINER:-0}" != "1" ] && [ "$MAC_HASH" != "$CTR_HASH" ]; then drift_for_skill=1; fi

  if [ "$drift_for_skill" = "1" ]; then
    DRIFT=$((DRIFT + 1))
    DRIFT_LINES="$DRIFT_LINES
  $s: mac=$MAC_HASH wiki=$WIKI_HASH run=$RUN_HASH ctr=$CTR_HASH"
  fi
done

echo "test_skills_cross_host_parity: total=$TOTAL drift=$DRIFT"
if [ "$DRIFT" -gt 0 ]; then
  echo "Divergent skills:$DRIFT_LINES"
  echo "FAIL: skill content drifted across substrate hosts"
  exit 1
fi

echo "OK: all $TOTAL active skills have byte-identical SKILL.md across Mac vault, Air wiki, Air runtime mirror, and OpenClaw container"
