#!/bin/bash
# pre-receive hook — RULE ZERO / AP-32 server-side CI guard
# Rejects pushes that add any canonical LESSON file, and rejects count growth beyond 129.
# Catches bypasses of the local pre-commit hook (e.g. --no-verify, rename-from-outside-canonical).
# Installed 2026-04-17 session 45 per MEMORY.md carryover item.
#
# Escape hatch: add "LESSON-EXEMPT" to any commit message in the push range to allow.

set -u
FROZEN_COUNT=129
EXEMPT_TAG="LESSON-EXEMPT"
ZERO_SHA="0000000000000000000000000000000000000000"

has_exempt_commit() {
  local old_sha="$1"
  local new_sha="$2"

  if [ "$old_sha" = "$ZERO_SHA" ]; then
    git show --format=%B -s "$new_sha" 2>/dev/null | grep -q "$EXEMPT_TAG"
    return $?
  fi

  for c in $(git rev-list "$old_sha..$new_sha"); do
    if git show --format=%B -s "$c" 2>/dev/null | grep -q "$EXEMPT_TAG"; then
      return 0
    fi
  done
  return 1
}

while read old_sha new_sha ref_name; do
  [ "$new_sha" = "$ZERO_SHA" ] && continue
  [ "$ref_name" != "refs/heads/main" ] && continue

  if [ "$old_sha" = "$ZERO_SHA" ]; then
    DIFF_OLD="$(git hash-object -t tree /dev/null)"
  else
    DIFF_OLD="$old_sha"
  fi

  NEW_LESSON_PATHS=$(git diff --name-status --diff-filter=ACR "$DIFF_OLD" "$new_sha" -- pages/lessons/individual/ 2>/dev/null \
    | awk '{ if ($1 ~ /^[RC]/) print $3; else print $2 }' \
    | grep -E '^pages/lessons/individual/LESSON-[0-9]+-.*\.md$' || true)

  if [ -n "$NEW_LESSON_PATHS" ] && ! has_exempt_commit "$old_sha" "$new_sha"; then
    echo "" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    echo "RULE ZERO (AP-32 CI guard) — push REJECTED" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    echo "Push adds canonical LESSON file(s), which is forbidden even when" >&2
    echo "the current filesystem count is below ${FROZEN_COUNT} after migration:" >&2
    echo "$NEW_LESSON_PATHS" >&2
    echo "" >&2
    echo "Correct path: update pages/skills/<skill>/SKILL.md and add a" >&2
    echo "gbrain timeline entry. Do not create new LESSON-NNN files." >&2
    echo "" >&2
    echo "Exceptional override: add LESSON-EXEMPT to commit message." >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    exit 1
  fi

  NEW_COUNT=$(git ls-tree -r "$new_sha" pages/lessons/individual/ 2>/dev/null | grep -c "LESSON-[0-9][0-9]*-" || echo 0)
  NEW_COUNT=${NEW_COUNT:-0}

  if [ "$NEW_COUNT" -gt "$FROZEN_COUNT" ]; then
    if ! has_exempt_commit "$old_sha" "$new_sha"; then
      echo "" >&2
      echo "═══════════════════════════════════════════════════════════════" >&2
      echo "RULE ZERO (AP-32 CI guard) — push REJECTED" >&2
      echo "═══════════════════════════════════════════════════════════════" >&2
      echo "LESSON count would grow from ${FROZEN_COUNT} to ${NEW_COUNT}." >&2
      echo "" >&2
      echo "The pre-commit hook on working copies should block new LESSONs," >&2
      echo "but this server-side guard catches bypasses (--no-verify, rename-" >&2
      echo "from-outside-canonical, push from a wiki without the hook)." >&2
      echo "" >&2
      echo "To update the SKILL instead (the correct path per RULE ZERO):" >&2
      echo "  1. Update pages/skills/<skill>/SKILL.md with new AP/rule" >&2
      echo "  2. Bump skill version, append ## Timeline entry" >&2
      echo "  3. Call mcp__gbrain__add_timeline_entry" >&2
      echo "  4. Revert the LESSON addition from your commits" >&2
      echo "" >&2
      echo "Exceptional override: add LESSON-EXEMPT to commit message." >&2
      echo "═══════════════════════════════════════════════════════════════" >&2
      exit 1
    fi
  fi
done

exit 0
