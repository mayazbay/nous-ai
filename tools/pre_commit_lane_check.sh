#!/bin/bash
# RULE 7 — lane lock match enforcement.
#
# Designed to be sourced by tools/pre-commit-hook-tan-pattern.sh after its existing rules.
# Exits 0 (pass) when:
#   - NOUS_LANE_BYPASS=1 (NOT honored — see below) — actually never; the bypass is --no-verify on git commit.
#   - No files staged (nothing to check).
#   - NOUS_LANE env unset AND no active locks exist (e.g., one-off hot-fix; warns but passes).
#   - Every staged path matches a glob from a currently-held lock token owned by $NOUS_LANE.
#
# Exits 7 (fail, magic number 7 = RULE 7) when:
#   - NOUS_LANE is set but no active token for that lane.
#   - A staged path doesn't match any of the lane's lock globs.
#
# Hint output: tells the user how to acquire a lock for the missing scope.

set -uo pipefail

# Resolve repo root and tools dir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LANE_LOCK="$REPO_ROOT/tools/lane_lock.py"

# Are we even in a commit?
STAGED_FILES=$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null || echo "")
if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

LANE="${NOUS_LANE:-}"

# If lane_lock.py doesn't exist yet, skip the check (graceful for staged Ship-2 rollout).
if [ ! -f "$LANE_LOCK" ]; then
  echo "RULE 7: tools/lane_lock.py not present; skipping lane-mismatch check (Ship 2 not yet deployed)" >&2
  exit 0
fi

if [ -z "$LANE" ]; then
  # Best-effort: if there are NO active locks at all, allow (single-agent dev).
  ACTIVE=$(python3 "$LANE_LOCK" list-active --json 2>/dev/null || echo "[]")
  COUNT=$(echo "$ACTIVE" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
  if [ "$COUNT" = "0" ]; then
    echo "RULE 7: NOUS_LANE unset + no active locks; allowing commit (single-agent mode)" >&2
    exit 0
  fi
  echo "RULE 7 FAIL: NOUS_LANE not set, but $COUNT active lane lock(s) exist." >&2
  echo "  Set NOUS_LANE=<claude|codex|grok|opus> before committing, OR --no-verify if you understand the risk." >&2
  exit 7
fi

# Validate lane name
case "$LANE" in
  claude|codex|grok|opus)
    ;;
  *)
    echo "RULE 7 FAIL: NOUS_LANE='$LANE' is not one of {claude,codex,grok,opus}." >&2
    exit 7
    ;;
esac

# Check we have at least one active token for this lane
LANE_TOKENS=$(python3 "$LANE_LOCK" list-active --lane "$LANE" --json 2>/dev/null || echo "[]")
TOKEN_COUNT=$(echo "$LANE_TOKENS" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$TOKEN_COUNT" = "0" ]; then
  echo "RULE 7 FAIL: NOUS_LANE='$LANE' but no active lock token for this lane." >&2
  echo "  Acquire one first:" >&2
  echo "    python3 tools/lane_lock.py acquire --lane $LANE --scope '<glob>' --ttl-sec 600" >&2
  echo "  Then retry the commit." >&2
  exit 7
fi

# For each staged file, verify it matches at least one of the lane's lock globs
OFFENDERS=""
while IFS= read -r path; do
  [ -z "$path" ] && continue
  if ! python3 "$LANE_LOCK" match --path "$path" --lane "$LANE" --quiet 2>/dev/null; then
    OFFENDERS="$OFFENDERS
  $path"
  fi
done <<< "$STAGED_FILES"

if [ -n "$OFFENDERS" ]; then
  echo "RULE 7 FAIL — lane mismatch for NOUS_LANE='$LANE'. Offending paths:$OFFENDERS" >&2
  echo "" >&2
  echo "Current lane locks for $LANE:" >&2
  python3 "$LANE_LOCK" list-active --lane "$LANE" >&2 || true
  echo "" >&2
  echo "Fix: either acquire a lock covering these paths, or move them to a different commit." >&2
  exit 7
fi

exit 0
