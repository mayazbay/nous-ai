#!/bin/bash
# tools/test_no_merge_markers.sh — fail loudly if any tracked file has unresolved
# git merge markers at line start. Mechanical gate per
# pages/progress/plans/PLAN-2026-04-29-conflict-marker-recovery.md Task 2.
#
# Usage:
#   bash tools/test_no_merge_markers.sh           # scan tracked files
#   bash tools/test_no_merge_markers.sh --staged  # scan only staged paths
#
# Exit 0 = clean. Exit 1 = markers found (paths printed to stderr).
#
# Wired into .git/hooks/pre-commit so auto-sync stash-pop conflict markers
# cannot survive a commit silently.

set -u
SCOPE="${1:-tracked}"
SCAN_INDEX=0

if [ "$SCOPE" = "--staged" ]; then
  SCAN_INDEX=1
  files=$(git diff --cached --name-only --diff-filter=ACMR)
else
  files=$(git ls-files)
fi

hits=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  # Skip raw/ archives (may contain literal markers in code samples).
  case "$f" in
    raw/*|*/raw/*) continue ;;
    *.png|*.jpg|*.jpeg|*.gif|*.pdf|*.zip|*.tar.gz|*.bin|*.dump) continue ;;
    *)
      if [ "$SCAN_INDEX" -eq 1 ]; then
        if git show ":$f" 2>/dev/null | grep -qE '^(<{7}|={7}|>{7})( |$)'; then
          hits="$hits$f
"
        fi
      elif [ -f "$f" ] && grep -qE '^(<{7}|={7}|>{7})( |$)' "$f" 2>/dev/null; then
        hits="$hits$f
"
      fi
      ;;
  esac
done <<< "$files"

if [ -n "$hits" ]; then
  echo "🔴 merge conflict markers found in:" >&2
  echo "$hits" | grep -v '^$' | sed 's/^/  - /' >&2
  echo "" >&2
  echo "  Resolve: open each file, remove <<<<<<<, =======, >>>>>>> blocks." >&2
  echo "  Test again: bash tools/test_no_merge_markers.sh" >&2
  exit 1
fi

echo "OK: no merge conflict markers found"
exit 0
