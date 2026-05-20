#!/bin/bash
# tools/session_safe_sync.sh — clean-tree-aware rebase for session-start sync.
#
# Replaces the brittle pattern:
#   git stash push -u && git pull --rebase && git stash pop
#
# When the working tree is dirty AND the remote has new commits AND any of those
# new commits touches a file in the dirty set, `git stash pop` produces inline
# `<<<<<<< Updated upstream` / `>>>>>>> Stashed changes` markers that:
#   - DO NOT show as `git status` UU conflicts (they're modified-with-content)
#   - DO survive into commits if pre-commit hook misses them
#   - CAUSED a 9-file pollution event in s82p (round 14) and recurred in s82q (round 15)
#
# AP-{NEW} (session 82r, 2026-04-29): use this script every session-start instead
# of inline stash-pop. Skips stash entirely when clean (the common case).
#
# Usage:
#   bash tools/session_safe_sync.sh                  # rebase from default remote
#   bash tools/session_safe_sync.sh --remote vps     # explicit remote
#   bash tools/session_safe_sync.sh --no-pull        # check only, don't sync
#
# Exit 0 = synced clean. Exit 1 = dirty + conflict-risk; manual resolution needed.

set -u
REMOTE="vps"
NO_PULL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --remote) REMOTE="$2"; shift 2 ;;
    --no-pull) NO_PULL=1; shift ;;
    *) echo "usage: $0 [--remote <name>] [--no-pull]" >&2; exit 2 ;;
  esac
done

dirty=$(git status --porcelain | head -1)

if [ -z "$dirty" ]; then
  echo "✅ working tree clean — direct rebase (no stash dance)"
  [ "$NO_PULL" -eq 1 ] && { echo "  --no-pull set, skipping"; exit 0; }
  git pull --rebase "$REMOTE" "$(git rev-parse --abbrev-ref HEAD)" 2>&1 | tail -3
  exit 0
fi

echo "🟡 working tree dirty:"
git status --porcelain | sed 's/^/    /'

# Check if any dirty file is touched by remote commits we'd pull in
git fetch -q "$REMOTE" 2>/dev/null
remote_branch="$REMOTE/$(git rev-parse --abbrev-ref HEAD)"
behind=$(git rev-list --count HEAD.."$remote_branch" 2>/dev/null || echo 0)

if [ "$behind" -eq 0 ]; then
  echo "  no upstream commits to pull — staying as-is, no sync needed"
  exit 0
fi

echo "  $behind upstream commit(s) to pull"
dirty_files=$(git status --porcelain | awk '{print $2}')
remote_touched=$(git diff --name-only HEAD.."$remote_branch" 2>/dev/null)
collision=""
while IFS= read -r df; do
  [ -z "$df" ] && continue
  if echo "$remote_touched" | grep -qFx "$df"; then
    collision="$collision  $df\n"
  fi
done <<< "$dirty_files"

if [ -n "$collision" ]; then
  echo "🔴 STASH-POP CONFLICT RISK — these dirty files are also touched by upstream:" >&2
  printf "%b" "$collision" >&2
  echo "" >&2
  echo "  Manual resolution required. Options:" >&2
  echo "    A. git stash push -u + pull + manual conflict-resolve on pop" >&2
  echo "    B. commit dirty work first (preferred), then pull --rebase" >&2
  echo "    C. discard dirty work: git checkout -- <files>" >&2
  exit 1
fi

[ "$NO_PULL" -eq 1 ] && { echo "  --no-pull set, dirty+remote-not-overlapping; skipping"; exit 0; }

echo "  no overlap — safe to stash + pull + pop"
git stash push -u -m "session_safe_sync-$$" >/dev/null
git pull --rebase "$REMOTE" "$(git rev-parse --abbrev-ref HEAD)" 2>&1 | tail -2
git stash pop 2>&1 | tail -2
echo "✅ synced + restored"
exit 0
