#!/bin/bash
# test_musk_step_2_hook_wired.sh — session 82, 2026-04-29
#
# Guard against "doctrine exists, hook absent" drift for musk-algorithm AP-1.
# The live hooks and tracked canonical hook templates must both invoke the
# Step-2 detector, otherwise future SKILL.md bumps can silently skip deletion.

set -u

VAULT="${VAULT:-$(cd "$(dirname "$0")/.." && pwd)}"
FAIL=0

need_hook() {
    local file="$1"
    local mode="$2"

    if [ ! -f "$file" ]; then
        echo "FAIL missing hook: $file"
        FAIL=1
        return
    fi

    if ! grep -Fq 'test_musk_step_2.sh' "$file"; then
        echo "FAIL $file does not invoke test_musk_step_2.sh"
        FAIL=1
    fi

    if [ "$mode" = "commit-msg" ]; then
        if ! grep -Fq -- '--commit-msg "$MSG_FILE"' "$file"; then
            echo "FAIL $file does not pass --commit-msg \"\$MSG_FILE\""
            FAIL=1
        fi
    fi
}

need_hook "$VAULT/.git/hooks/pre-commit" "pre-commit"
need_hook "$VAULT/tools/pre-commit-hook-tan-pattern.sh" "pre-commit"
need_hook "$VAULT/.git/hooks/commit-msg" "commit-msg"
need_hook "$VAULT/tools/commit-msg-hook.sh" "commit-msg"

if [ "$FAIL" -eq 0 ]; then
    echo "OK: musk step-2 detector wired into live and canonical hooks"
fi

exit "$FAIL"
