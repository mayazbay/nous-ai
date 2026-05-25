#!/bin/bash
# test_authorial_commits.sh — detect SOC Rule 19 attribution-drift class
#
# RULE: substantive agent work (SKILL.md bumps, HANDOFF/MEMORY prepends, tools/
# edits) MUST land as AUTHORIAL commits with explicit messages. If such work
# gets picked up by `nous-obsidian-sync.sh` or `auto-sync` cron BEFORE the agent
# explicitly commits, the commit lands with a generic `auto-sync YYYY-MM-DD
# HH:MM:SS` / `vps auto-sync ...` / `air-sync ...` message — attribution LOST,
# rationale LOST, rollback audit trail LOST. Per SOC v1.12 Rule 19 (session 64-late)
# and karpathy-loop AP-4 (write-negative-first), this is a real substrate-integrity
# violation even though the content reaches the bare repo.
#
# Occurrences observed (3 sessions of evidence, SOC Rule 18 recurrence-gate cleared):
#   - session 59 (3 HEREDOC authorial messages rewritten as `auto-sync` via
#     `com.nous.obsidian-sync` every-60s race — fixed via AP-51 index-lock guard)
#   - session 66 (s66 staged close work auto-sync'd as `vps auto-sync 13:18:01`)
#   - session 67 (s67's RESOLVER.md + trigger_eval.py changes auto-sync'd with
#     generic prefixes over 5+ commits — flagged in s66 handoff)
#   - session 68p (MEMORY top-block grabbed as auto-sync after manual Edit)
#   - session 70 (wiki-to-runtime-rsync.sh extension grabbed as `1cd9198e
#     air-sync 2026-04-23T18:11:00` — the commit that DOCUMENTS this detector
#     itself almost got eaten)
#
# What this detector checks (on DEMAND or from audit / SOAO):
#   For each commit in the LOOKBACK window with a generic message prefix
#   (`auto-sync ` | `vps auto-sync ` | `air-sync `), inspect the diff — if it
#   touches files in the AUTHORIAL_CLASS (SKILL.md, HANDOFF-*.md, MEMORY.md,
#   tools/*.sh, tools/*.py, .git/hooks/*), FLAG as drift.
#
# Exit codes:
#   0 — no drift detected in window
#   1 — drift detected (substrate-integrity warning, not a hard commit block
#       — git history is immutable; this detector is surveillance / post-audit)
#
# Usage:
#   tools/test_authorial_commits.sh                   → scan last 50 commits
#   tools/test_authorial_commits.sh LOOKBACK=100      → scan last 100 commits
#   tools/test_authorial_commits.sh SINCE=2.hours.ago → scan by time window
#
# Integration candidates (session-71+ work):
#   - Append to SOAO audit every session-open (surfaces drift across last N
#     commits as context for next agent to react — NOT fix retroactively).
#   - Nightly launchd job that posts Telegram alert when daily drift ratio
#     >20% of authorial-class commits.
#   - Pre-push hook extension: if outgoing range contains >3 attribution-drift
#     commits, warn (not block, because you can't fix already-committed
#     history without rewrite, which is more destructive than the drift itself).

set -u

LOOKBACK="${LOOKBACK:-50}"
SINCE="${SINCE:-}"

# Find git root (assume we're inside the wiki repo)
if ! REPO=$(git rev-parse --show-toplevel 2>/dev/null); then
  echo "🔴 not in a git repo" >&2
  exit 1
fi
cd "$REPO" || exit 1

# Authorial-class path globs — these paths SHOULD only see authorial commits
AUTHORIAL_CLASS=(
  'pages/skills/.*/SKILL\.md$'
  'pages/tenants/.*/skills/.*/SKILL\.md$'
  'pages/progress/HANDOFF-.*\.md$'
  'pages/progress/claude-memory/MEMORY\.md$'
  'pages/progress/PLAN-.*\.md$'
  '^tools/.*\.(sh|py)$'
  '\.git/hooks/'
)

# Generic auto-sync message patterns
GENERIC_REGEX='^(auto-sync |vps auto-sync |air-sync |Merge branch .main. of )'

# Build git log range args
if [ -n "$SINCE" ]; then
  RANGE_ARGS="--since=$SINCE"
else
  RANGE_ARGS="-n $LOOKBACK"
fi

DRIFT_COUNT=0
DRIFT_COMMITS=()

while IFS=$'\t' read -r sha subject; do
  [ -z "$sha" ] && continue
  # Is subject generic?
  if ! echo "$subject" | grep -qE "$GENERIC_REGEX"; then
    continue
  fi
  # Does commit touch any authorial-class file?
  touched_files=$(git show --name-only --format="" "$sha" 2>/dev/null)
  [ -z "$touched_files" ] && continue

  matched=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    for pattern in "${AUTHORIAL_CLASS[@]}"; do
      if echo "$f" | grep -qE "$pattern"; then
        matched="${matched}${f}"$'\n'
        break
      fi
    done
  done <<< "$touched_files"

  if [ -n "$matched" ]; then
    DRIFT_COMMITS+=("$sha")
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
    echo "⚠️  drift: $sha  [$subject]"
    echo "$matched" | sed 's/^/       /' | head -5
  fi
done < <(git log $RANGE_ARGS --format="%H%x09%s")

echo ""
echo "=========================================="
if [ "$DRIFT_COUNT" -eq 0 ]; then
  echo "✅ no attribution-drift commits in window (examined $LOOKBACK commits)"
  exit 0
else
  echo "🔴 $DRIFT_COUNT attribution-drift commits in window"
  echo ""
  echo "These commits have generic auto-sync subjects but touched authorial-class"
  echo "files (SKILL.md / HANDOFF / MEMORY / tools / hooks). Root cause per SOC"
  echo "Rule 19: the authoring agent staged work but did not commit authorially"
  echo "before auto-sync cron (every-60s) picked it up."
  echo ""
  echo "Cannot retroactively fix — git history is immutable without destructive"
  echo "rewrite. The mitigation is FORWARD-facing:"
  echo "  (a) agents commit own substantive work IMMEDIATELY after Edit / Write,"
  echo "      not in session-close batches"
  echo "  (b) use 'git commit -o <paths>' to scope commits tight + beat auto-sync"
  echo "  (c) if session-close batch required, stage + commit atomically same turn"
  echo ""
  echo "Cross-ref: session-operating-contract v1.12 Rule 19, infrastructure"
  echo "AP-51 (auto-sync race guard, 15s→30s mtime extension), musk-algorithm"
  echo "AP-4 (agent-autonomy — commit is part of execution, not post-work hygiene)."
  exit 1
fi
