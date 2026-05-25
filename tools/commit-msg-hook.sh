#!/bin/bash
# commit-msg hook — hybrid enforcement layer (session-68p, 2026-04-23)
#
# Runs AFTER commit message is written, BEFORE commit finalizes.
# Has access to message via $1 (path to COMMIT_EDITMSG).
#
# Invokes detectors that need message content:
#   1. test_skill_bump_requires_gbrain_timeline.sh
#        — every SKILL.md version bump MUST cite gbrain timeline evidence.
#
# Bypass: git commit --no-verify
#
# Evidence trail: pages/skills/mistake-to-skill (AP-11 3-edit ritual enforcement
# at git layer) + pages/skills/musk-algorithm (AP-3 physically-impossible-violated).
# gbrain entry id: filed same-session via test detector's own commit.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
MSG_FILE="$1"

if [ -x "$REPO_ROOT/tools/test_skill_bump_requires_gbrain_timeline.sh" ]; then
  "$REPO_ROOT/tools/test_skill_bump_requires_gbrain_timeline.sh" "$MSG_FILE"
fi

# Musk Step-2 gate (musk-algorithm AP-1): any SKILL.md bump / large
# doctrine addition must show delete-before-optimize evidence in the message
# or staged diff.
if [ -x "$REPO_ROOT/tools/test_musk_step_2.sh" ]; then
  "$REPO_ROOT/tools/test_musk_step_2.sh" --commit-msg "$MSG_FILE"
fi

# Agent-autonomy gate (musk-algorithm AP-4): block commit messages with
# deference-dressed-as-autonomy phrases. Scans the message via stdin mode.
if [ -x "$REPO_ROOT/tools/test_agent_autonomy.sh" ]; then
  if ! (cd "$REPO_ROOT" && cat "$MSG_FILE" | bash tools/test_agent_autonomy.sh --stdin); then
    echo "" >&2
    echo "🔴 Commit message contains agent-autonomy (AP-4) red-flag phrases." >&2
    echo "   Remove them (decide autonomously) OR add a hall-pass marker near the line." >&2
    echo "   Bypass: git commit --no-verify" >&2
    exit 1
  fi
fi

exit 0
