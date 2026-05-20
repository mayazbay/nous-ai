#!/bin/bash
# tools/test_pre_commit_index_scope.sh v0.1 — session-coordination AP-5 surveillance detector
#
# POST-HOC scanner for cross-session stage-bleed (AP-5, session 68, 2026-04-23).
# Pattern: Session A stages files; Session B's `git commit` sweeps A's staged
# files into B's commit because `.git/index` is shared across sessions in one
# working tree. Fix: agents use `git commit -o <paths>` to bypass the shared
# index. This scanner detects commits where the rule was violated.
#
# Heuristic (v0.1, registry-free):
#   For each commit in the last LOOKBACK commits:
#     - Skip auto-sync / vps auto-sync / air-sync / Merge commits (covered by AP-54)
#     - Read commit subject; extract declared-scope hint (first ≤3 files in message)
#     - Check if actual diff files are a subset of the subject-hinted scope
#     - If diff has files NOT hinted in the subject AND subject suggests a narrow
#       scope (mentions specific file/path) → flag as potential stage-bleed
#
# v1.0 (DEFERRED until recurrence): registry-coupled detection using
# ~/nous-agaas/state/active-sessions.jsonl — match commit author time to
# session register/close intervals; compare diff paths to declared_scope globs.
# Requires Air SSH; adds complexity. Not shipped until N>=2 incidents justify.
#
# Ship date: session 72, 2026-04-24
# Cross-ref: session-coordination AP-5, AP-54 test_authorial_commits.sh (sibling
# surveillance tool for auto-sync attribution drift).
#
# Usage:
#   bash tools/test_pre_commit_index_scope.sh                    # scan last 20
#   LOOKBACK=50 bash tools/test_pre_commit_index_scope.sh        # scan last 50
#   bash tools/test_pre_commit_index_scope.sh --commit abc123    # single commit
#
# Exit: 0 clean, 1 at least one candidate surfaced (non-blocking; warn-only).

set -u
LOOKBACK="${LOOKBACK:-20}"
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$VAULT"

SINGLE_COMMIT=""
if [ "${1:-}" = "--commit" ]; then
    SINGLE_COMMIT="${2:-HEAD}"
fi

# Heuristic matchers
is_excluded_commit() {
    local subj="$1"
    case "$subj" in
        auto-sync\ *|vps\ auto-sync\ *|air-sync\ *|Merge\ branch*|Merge\ remote*|session-close*|handoff*|Initial\ commit)
            return 0 ;;
    esac
    return 1
}

# Extract path hints from commit subject line (paths + backtick-quoted words)
subject_path_hints() {
    local subj="$1"
    # quick extraction of path-like tokens (contains / and .)
    echo "$subj" | grep -oE '[A-Za-z0-9_./-]+\.(md|sh|py|yaml|yml|json|js|ts|sql|conf)' | sort -u
    echo "$subj" | grep -oE '\b(tools|pages|laws|docs|scripts)/[A-Za-z0-9_./-]+' | sort -u
}

# A commit is "narrow-scoped in subject" if subject mentions 1-3 specific paths
is_narrow_subject() {
    local hints="$1"
    local count
    count=$(echo "$hints" | grep -c . || true)
    [ "$count" -ge 1 ] && [ "$count" -le 3 ]
}

# Check if any diff files are outside the hinted scope prefixes
diff_files_outside_hints() {
    local sha="$1"
    local hints="$2"
    local files
    files=$(git show --name-only --pretty=format: "$sha" 2>/dev/null | grep -v '^$' || true)
    [ -z "$files" ] && return 1
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        local matched=0
        while IFS= read -r h; do
            [ -z "$h" ] && continue
            # Match if diff-file path CONTAINS hint (e.g., hint=SKILL.md matches pages/skills/foo/SKILL.md)
            if [ "$f" = "$h" ] || echo "$f" | grep -qF "$h"; then
                matched=1
                break
            fi
            # Hint is a dir prefix like "tools/" — match by prefix
            if [ "${h: -1}" = "/" ] && echo "$f" | grep -qE "^${h}"; then
                matched=1
                break
            fi
        done <<< "$hints"
        if [ "$matched" = "0" ]; then
            echo "$f"
        fi
    done <<< "$files"
}

surface_commit() {
    local sha="$1"
    local subj
    subj=$(git log -1 --pretty=format:"%s" "$sha" 2>/dev/null)
    if is_excluded_commit "$subj"; then
        return 0
    fi
    local hints
    hints=$(subject_path_hints "$subj")
    if [ -z "$hints" ]; then
        return 0  # no narrow subject hint; can't surveil
    fi
    if ! is_narrow_subject "$hints"; then
        return 0
    fi
    local foreign
    foreign=$(diff_files_outside_hints "$sha" "$hints")
    if [ -n "$foreign" ]; then
        echo "🟡 CANDIDATE: $sha"
        echo "   subject: $subj"
        echo "   hinted scope: $(echo "$hints" | tr '\n' ' ')"
        echo "   diff files OUTSIDE hint:"
        echo "$foreign" | sed 's/^/     - /'
        echo ""
        return 2
    fi
    return 0
}

CANDIDATES=0
if [ -n "$SINGLE_COMMIT" ]; then
    surface_commit "$SINGLE_COMMIT" && true
    rc=$?
    [ "$rc" = "2" ] && CANDIDATES=1
else
    while IFS= read -r sha; do
        surface_commit "$sha" && true
        rc=$?
        [ "$rc" = "2" ] && CANDIDATES=$((CANDIDATES + 1))
    done < <(git log --pretty=format:"%H" -n "$LOOKBACK")
fi

if [ "$CANDIDATES" -gt 0 ]; then
    echo "═════════════════════════════════════════════════════════════"
    echo "🟡 $CANDIDATES candidate(s) surfaced — review manually."
    echo "   Rule: AP-5 (session-coordination) — use 'git commit -o <paths>'"
    echo "   for authorial commits on shared working tree."
    echo "   False positives expected: bundled logical commits, refactors,"
    echo "   multi-path atomic edits. Non-blocking."
    exit 1
fi

echo "✅ test_pre_commit_index_scope: 0 candidates in last $LOOKBACK commits"
exit 0
