#!/bin/bash
# test_musk_step_2.sh — session 64, 2026-04-22
#
# Mechanical enforcement of musk-algorithm AP-1 (optimize-before-delete):
# "Every SKILL.md bump (or plan commit >N lines) must demonstrate that
# Musk step 2 — 'try very hard to delete the part or process' — was
# explicitly attempted, not silently skipped."
#
# Root-cause class: humans and LLM agents default to Step 3 (simplify)
# because deletion feels wasteful and simplification feels productive.
# Sessions ship ever-larger skills and plans with zero deletion pass.
# This script makes Step-2 evidence REQUIRED before any SKILL.md bump
# or large plan commit can pass.
#
# The Algorithm (verbatim, The Book of Elon §324-329):
#   1. Make your requirements less dumb.
#   2. Try very hard to delete the part or process.   <-- this script
#   3. Simplify or optimize.
#   4. Accelerate cycle time.
#   5. Automate.
#
# Rule: if you're not adding deleted things back in 10% of the time,
# you clearly aren't deleting enough.
#
# What this script does:
#   1. If run with --commit-msg <file>: reads the proposed commit msg.
#      Passes if msg contains any of: "musk-step-2:", "delete:", "deleted:",
#      "removed:", "dropped:", "culled:", "pruned:".
#   2. If staged SKILL.md files exist AND no Step-2 token present AND
#      net diff on those files is net-positive (lines-added >> lines-deleted):
#        WARN (soft) at <=50 lines added with no deletion.
#        FAIL (hard, exit 1) at >200 lines added with zero deletion anywhere.
#   3. Without --commit-msg: runs in standalone "check current state" mode.
#
# Usage:
#   tools/test_musk_step_2.sh                           # standalone check (staged files)
#   tools/test_musk_step_2.sh --commit-msg .git/COMMIT_EDITMSG   # pre-commit hook use
#   tools/test_musk_step_2.sh --self-test               # run unit tests (positive + negative)
#
# Exit codes:
#   0 = green (Step-2 evidence present, or no SKILL.md bump staged)
#   1 = red (hard-fail: big bump with zero Step-2 evidence anywhere)
#   2 = usage / setup error
#
# Environment overrides:
#   VAULT=<path>           vault root (default: 2-up from this script)
#   HARD_FAIL_LINES=200    lines-added threshold for hard-fail (default 200)
#   WARN_LINES=50          lines-added threshold for soft-warn (default 50)
#
# Sister detectors:
#   tools/test_skill_version_parity.sh       (AP-11 fm/H1 drift)
#   tools/test_no_duplicate_skill_headers.sh (session-coordination AP-4 dup)
#   tools/test_memory_top_block_size.sh      (mistake-to-skill AP-7 50-line cap)

set -u

VAULT="${VAULT:-$(cd "$(dirname "$0")/.." && pwd)}"
HARD_FAIL_LINES="${HARD_FAIL_LINES:-200}"
WARN_LINES="${WARN_LINES:-50}"

# --- regex for Step-2 evidence tokens (explicit annotation format only) ---
# Matches TOKEN: as a line-initial annotation (in commit msg OR diff annotation).
# Deliberately strict: the word "deleted" appearing anywhere in added content does
# NOT count — we want operators to OPT-IN with an explicit token, not hit by accident.
# Accepted forms:
#   musk-step-2: <rationale>
#   delete-considered: <what + why>
#   delete: <what>
#   step-2: <rationale>
#   deleted-candidates: <list>
#   net-negative: <justification>
STEP2_TOKENS='(musk-step-2|delete-considered|delete|deleted-candidates|step-2|net-negative):'
# Commit-msg scan: match TOKEN: at line start OR after whitespace (allow indented bodies)
COMMIT_STEP2_REGEX="(^|[[:space:]])${STEP2_TOKENS}"
# Diff-annotation scan: require TOKEN: at start of an ADDED line (after the '+')
DIFF_STEP2_REGEX="^\\+[[:space:]]*${STEP2_TOKENS}"

usage() {
    cat <<EOF
Usage: $0 [--commit-msg <file> | --self-test]
  (no args)               scan staged SKILL.md changes
  --commit-msg <file>     also scan a proposed commit message
  --self-test             run positive + negative dogfood cases
Exit: 0 green, 1 red, 2 usage error
EOF
}

# ----------------------------------------------------------------------
# self-test mode (positive + negative dogfood)
# ----------------------------------------------------------------------
self_test() {
    # Resolve $0 BEFORE changing cwd so recursive invocations work regardless
    # of whether the script was called by relative or absolute path.
    local self_abs
    self_abs="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
    local tmp
    tmp="$(mktemp -d)"
    # set -u safe trap: use default-empty expansion on cleanup so exit-path is robust
    trap 'rm -rf "${tmp:-}"' EXIT
    cd "$tmp" || exit 2
    git init -q
    git config user.email test@nous
    git config user.name test
    mkdir -p pages/skills/fakeskill
    cat > pages/skills/fakeskill/SKILL.md <<'FAKE'
---
type: skill
version: 1.0.0
---
# fakeskill v1.0.0
first line.
FAKE
    git add -A
    git commit -qm "init"

    # Positive case: bump version + add a few lines + commit msg has musk-step-2
    sed -i.bak 's/1\.0\.0/1.1.0/g' pages/skills/fakeskill/SKILL.md
    rm -f pages/skills/fakeskill/SKILL.md.bak
    for i in $(seq 1 5); do echo "line $i" >> pages/skills/fakeskill/SKILL.md; done
    git add -A
    local posmsg; posmsg="$tmp/posmsg"
    echo "skill bump w/ musk-step-2: considered deleting AP-N, kept with trimmed body" > "$posmsg"
    VAULT="$tmp" "$self_abs" --commit-msg "$posmsg" > "$tmp/pos.out" 2>&1
    local pos_exit=$?
    if [ $pos_exit -eq 0 ]; then
        echo "✅ self-test POSITIVE: Step-2 token in commit msg → exit 0"
    else
        echo "❌ self-test POSITIVE FAILED (exit=$pos_exit):"
        cat "$tmp/pos.out"
        return 1
    fi
    git commit -qm "positive case"

    # Negative case: bump version + add MANY lines + commit msg has NO Step-2 token
    sed -i.bak 's/1\.1\.0/1.2.0/g' pages/skills/fakeskill/SKILL.md
    rm -f pages/skills/fakeskill/SKILL.md.bak
    for i in $(seq 1 $((HARD_FAIL_LINES + 10))); do echo "fluff line $i that nobody deleted" >> pages/skills/fakeskill/SKILL.md; done
    git add -A
    local negmsg; negmsg="$tmp/negmsg"
    echo "skill bump but no evidence of step-2 deletion discipline" > "$negmsg"
    VAULT="$tmp" "$self_abs" --commit-msg "$negmsg" > "$tmp/neg.out" 2>&1
    local neg_exit=$?
    if [ $neg_exit -eq 1 ]; then
        echo "✅ self-test NEGATIVE: big bump + no token → exit 1"
        return 0
    else
        echo "❌ self-test NEGATIVE FAILED (exit=$neg_exit, expected 1):"
        cat "$tmp/neg.out"
        return 1
    fi
}

# ----------------------------------------------------------------------
# real-run mode: scan staged SKILL.md changes + optional commit msg
# ----------------------------------------------------------------------
run_check() {
    local commit_msg_file="${1:-}"

    cd "$VAULT" || { echo "setup error: VAULT=$VAULT not cd-able" >&2; exit 2; }

    # Is there a git repo here?
    git rev-parse --is-inside-work-tree > /dev/null 2>&1 || {
        echo "✅ test_musk_step_2 — not in a git repo ($VAULT); nothing to check"
        return 0
    }

    # Find staged SKILL.md modifications (modifications + additions)
    local staged_skills
    staged_skills=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep -E 'pages/(skills|tenants/[^/]+/skills)/[^/]+/SKILL\.md$' || true)

    if [ -z "$staged_skills" ]; then
        echo "✅ test_musk_step_2 — no SKILL.md bumps staged; Step-2 check not required"
        return 0
    fi

    # Compute net-added lines across staged SKILL.md
    local lines_added lines_deleted net
    lines_added=$(git diff --cached --numstat -- $staged_skills 2>/dev/null | awk '{a+=$1} END {print a+0}')
    lines_deleted=$(git diff --cached --numstat -- $staged_skills 2>/dev/null | awk '{d+=$2} END {print d+0}')
    net=$((lines_added - lines_deleted))

    # Check for Step-2 evidence — in commit msg if provided, else in diff content
    local evidence_source="" has_evidence=0
    if [ -n "$commit_msg_file" ] && [ -r "$commit_msg_file" ]; then
        if grep -iqE "$COMMIT_STEP2_REGEX" "$commit_msg_file"; then
            has_evidence=1
            evidence_source="commit message ($commit_msg_file)"
        fi
    fi

    # Fallback: check if the staged diff itself contains a line-initial Step-2 annotation
    # (strict: must be '+<TOKEN>:' at line-initial position of an added line, not just the
    # word "deleted" happening to appear in fluff content)
    if [ $has_evidence -eq 0 ]; then
        if git diff --cached -- $staged_skills 2>/dev/null | grep -iqE "$DIFF_STEP2_REGEX"; then
            has_evidence=1
            evidence_source="diff annotation"
        fi
    fi

    # Also count net-negative diff as implicit evidence (you deleted more than added)
    if [ $has_evidence -eq 0 ] && [ $net -lt 0 ]; then
        has_evidence=1
        evidence_source="net-negative diff ($lines_added added, $lines_deleted deleted)"
    fi

    echo "test_musk_step_2 — staged SKILL.md bumps:"
    echo "$staged_skills" | sed 's/^/    /'
    echo "    lines added:   $lines_added"
    echo "    lines deleted: $lines_deleted"
    echo "    net delta:     $net"

    if [ $has_evidence -eq 1 ]; then
        echo "✅ Step-2 evidence present ($evidence_source)"
        return 0
    fi

    # No evidence — gate on size
    if [ $lines_added -ge $HARD_FAIL_LINES ]; then
        cat <<EOF

============================================================
  🔴 MUSK-STEP-2 VIOLATION (musk-algorithm AP-1)
============================================================

  Staged SKILL.md bump adds ${lines_added} lines (threshold: ${HARD_FAIL_LINES})
  with ZERO evidence that Musk Step 2 (delete) was attempted:
    - no 'musk-step-2:' or 'delete:' token in commit msg
    - no '+delete:' annotation inside the diff
    - diff is net-positive (${net})

  The Algorithm (Book of Elon §324-329):
    1. Make requirements less dumb.
    2. Try very hard to delete the part or process.   <-- this step
    3. Simplify or optimize.  <-- you jumped to this one
    4. Accelerate cycle time.
    5. Automate.

  10% add-back rule: if you never need to put anything back
  after deletion, you're not deleting hard enough.

  Fix — pick one:
    (a) Add 'musk-step-2: <what you considered deleting + why kept>'
        to the commit message.
    (b) Actually delete something. Make the diff closer to net-neutral
        or net-negative.
    (c) Annotate the diff with 'delete-considered: X; rejected because Y'.

  Pattern source: pages/skills/musk-algorithm/SKILL.md AP-1
============================================================

EOF
        return 1
    fi

    if [ $lines_added -ge $WARN_LINES ]; then
        cat <<EOF

⚠️  MUSK-STEP-2 SOFT-WARN (musk-algorithm AP-1)
    Staged SKILL.md bump adds ${lines_added} lines (warn ≥${WARN_LINES}, fail ≥${HARD_FAIL_LINES})
    with no Step-2 evidence in commit msg or diff annotation.
    Consider adding 'musk-step-2: <considered deleting X>' to the commit message.
    (This is a soft warning; commit not blocked.)

EOF
        # Soft warn, don't block
        return 0
    fi

    echo "✅ test_musk_step_2 — small bump (${lines_added} lines); Step-2 check not enforced"
    return 0
}

# ----------------------------------------------------------------------
# entry
# ----------------------------------------------------------------------
case "${1:-}" in
    --self-test)
        self_test
        exit $?
        ;;
    --commit-msg)
        if [ -z "${2:-}" ]; then
            usage >&2
            exit 2
        fi
        run_check "$2"
        exit $?
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    "")
        run_check ""
        exit $?
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
