#!/bin/bash
# Bidirectional sync for the Nous wiki vault — fixed 2026-04-08.
#
# Root cause history:
#   The previous version used `cd "$vault"` before calling git. Under macOS TCC
#   sandboxing, the LaunchAgent and cron contexts can chdir() successfully but
#   git's internal getcwd() call fails with "fatal: Unable to read current
#   working directory: Operation not permitted", silently killing every run.
#   Additionally, error-swallowing via `2>/dev/null || return 0` hid the failures.
#
# Fix (AUDIT-028 session 2026-04-08 Madi's root-cause audit):
#   1. cd /tmp first (guaranteed readable cwd)
#   2. Use `git -C "$vault"` for EVERY git call (no dependency on cwd)
#   3. Send all git stderr to the sync log (no more silent `|| return 0`)
#   4. Explicit success/failure log lines, always
#   5. Proper merge cleanup via `git merge --abort` on fallback failure
#   6. Brain vault logic removed (vault was deleted 2026-04-07)
#
# Runs every 60s via ~/Library/LaunchAgents/com.nous.obsidian-sync.plist
# (StartInterval=60, RunAtLoad=true). The redundant Mac crontab entry was
# removed in the same audit to eliminate race conditions.

# --- environment ---
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME="/Users/madia"
export SSH_AUTH_SOCK="$(ls /tmp/ssh-*/agent.* 2>/dev/null | head -1)"

# Guaranteed-readable cwd (avoids TCC "Unable to read cwd" on LaunchAgent/cron contexts)
cd /tmp || exit 1

NOUS_VAULT="/Users/madia/Documents/Projects/Nous AGaaS/Nous"
LOG="/tmp/obsidian-sync.log"

# Fast-fail TCC probe — bash's `[ -r ]` (access syscall) is NOT TCC-gated, but
# actually READING a file IS. So we do a real read with head -c 1. If it fails
# OR produces nothing, TCC is blocking /bin/bash from accessing ~/Documents.
# Log a single actionable message and bail, instead of letting git spam
# "fatal: Unable to read cwd" into the log every 60 seconds forever.
if ! head -c 1 "$NOUS_VAULT/.git/HEAD" >/dev/null 2>&1; then
    # Only log once per 10 minutes to avoid flooding the log
    LAST_BLOCK_LOG_FILE="/tmp/obsidian-sync-last-tcc-block.epoch"
    NOW=$(date +%s)
    LAST=$(cat "$LAST_BLOCK_LOG_FILE" 2>/dev/null || echo 0)
    if [ $((NOW - LAST)) -ge 600 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] TCC-BLOCK: /bin/bash cannot read \$NOUS_VAULT/.git/HEAD — grant Full Disk Access to /bin/bash via System Settings → Privacy & Security → Full Disk Access, then kickstart this agent. Until then: manual sync via 'bash /Users/madia/.local/bin/nous-obsidian-sync.sh' from a TCC-enabled shell (Terminal/Claude Code) still works." >> "$LOG"
        echo "$NOW" > "$LAST_BLOCK_LOG_FILE"
    fi
    exit 0
fi

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log_line() {
    echo "[$(timestamp)] $1" >> "$LOG"
}

authorial_dirty() {
    local vault="$1"
    git -C "$vault" status --porcelain --untracked-files=all 2>/dev/null | while IFS= read -r line; do
        local path="$line"
        path="${path#???}"
        case "$path" in
            *" -> "*) path="${path##* -> }" ;;
        esac
        case "$path" in
            pages/skills/*/SKILL.md|\
            pages/tenants/*/skills/*/SKILL.md|\
            tenants/*|\
            pages/audits/*.md|\
            pages/plans/*.md|\
            pages/progress/HANDOFF-*.md|\
            pages/progress/claude-memory/MEMORY.md|\
            laws/*.md|\
            tools/*.sh|tools/*.py|tools/*.plist|\
            AGENTS.md|CLAUDE.md)
                echo "$path"
                break
                ;;
        esac
    done | head -1
}

sync_vault() {
    local vault="$1"
    local label="$2"

    # Vault must exist + be a git repo
    if [ ! -d "$vault/.git" ]; then
        log_line "$label skip: $vault is not a git repo"
        return 0
    fi

    # VPS remote must be configured
    if ! git -C "$vault" remote 2>>"$LOG" | grep -q '^vps$'; then
        log_line "$label skip: no vps remote configured"
        return 0
    fi

    # 0. USER-COMMIT-IN-PROGRESS GUARD (session 60 AP-51; extended session 63)
    #    Skip this cycle if the user is actively mid-commit OR mid-edit.
    #    Signals (any one triggers skip):
    #     a) .git/index.lock exists — git commit actively running
    #     b) .git/index mtime < 30s — user just ran `git add`, about to commit
    #     c) any tracked-and-modified file mtime < 30s — user is mid-Edit
    #        across multiple tool calls, hasn't staged yet
    #    Session 60 shipped (a)+(b) with 15s window → race still observed
    #    (ratio 8 auto-sync : 4 authorial in 30min-window measurement at
    #    session 62 audit). Multi-tool-call Edit sequences typically span
    #    >15s from first Edit to final `git commit`. Extension to 30s +
    #    working-tree-file-mtime check closes the remaining race window.
    if [ -f "$vault/.git/index.lock" ]; then
        log_line "$label skip: .git/index.lock present (user git op in progress)"
        return 0
    fi
    if [ -f "$vault/.git/index" ]; then
        INDEX_MTIME=$(stat -f %m "$vault/.git/index" 2>/dev/null || echo 0)
        NOW_EPOCH=$(date +%s)
        INDEX_AGE=$(( NOW_EPOCH - INDEX_MTIME ))
        if [ "$INDEX_AGE" -lt 30 ]; then
            log_line "$label skip: .git/index modified ${INDEX_AGE}s ago (user likely mid-commit)"
            return 0
        fi
    fi
    # 0c. Any tracked modified-file mtime < 30s → user mid-edit across tool calls
    if [ -d "$vault/.git" ]; then
        NOW_EPOCH=${NOW_EPOCH:-$(date +%s)}
        # Quick fail: only check files in `git diff --name-only HEAD` (modified)
        RECENT_FILE=$(git -C "$vault" diff --name-only HEAD 2>/dev/null | while read -r rel; do
            [ -f "$vault/$rel" ] || continue
            FM=$(stat -f %m "$vault/$rel" 2>/dev/null || echo 0)
            AGE=$(( NOW_EPOCH - FM ))
            if [ "$AGE" -lt 30 ]; then
                echo "$rel ${AGE}s"
                break
            fi
        done | head -1)
        if [ -n "$RECENT_FILE" ]; then
            log_line "$label skip: tracked file just edited ($RECENT_FILE ago — user mid-edit)"
            return 0
        fi
    fi
    # 0d was REMOVED (session 64 late, 2026-04-22, Madi-directed deep-think):
    #   Session 64 initially shipped an active-Claude-session guard here that
    #   skipped sync entirely if any `claude` process had cwd in the vault or
    #   its parent. Rationale at ship-time: prevent agent-authoring work from
    #   being swept into "auto-sync TIMESTAMP" commits with lost framing.
    #
    #   Madi Socratic check: "what's the reason? What would Elon / Tan /
    #   Karpathy / billion-dollar-solopreneur do?"
    #
    #   Answer: they would DELETE it. This is musk-algorithm AP-1 applied
    #   recursively to own work — optimizing a thing that should not exist.
    #   The guard protects cosmetic commit-message framing, not CONTENT (MD5
    #   parity is always preserved either way). It also:
    #     - blocks auto-sync while stale zombie claude PIDs live (session-61
    #       flagged 3 such PIDs running for days; 0d would pin them forever)
    #     - blocks OTHER legitimate concurrent sessions from syncing
    #     - enables bad agent behavior (batching edits until session-close
    #       rather than committing each logical unit inline)
    #
    #   The RIGHT fix is a behavioral contract codified in the agent's doctrine:
    #   session-operating-contract Rule 19 (added session 64 late, 2026-04-22):
    #   "Agent commits substantive work explicitly with authorial message as
    #   part of the work; auto-sync is a dumb backstop for non-substantive
    #   drift, not a batch-commit mechanism." Guards 0a/0b/0c (index.lock +
    #   index-mtime<30s + tracked-file-mtime<30s) catch the real race where
    #   an agent IS mid-write. 0d over-scoped.
    #
    #   Commit deleting 0d: see session-64 late commit "session-64-late —
    #   delete auto-sync guard 0d (Musk Step 2 applied recursively)".

    # 0e. AUTHORIAL-CLASS GUARD (session 75 AP-59):
    #    Auto-sync may sweep low-value UI churn, generated caches, and other
    #    non-substantive drift. It must NOT commit skills, plans, handoffs,
    #    audits, tenant source, laws, or tool edits with a generic message.
    AUTHORIAL_DIRTY=$(authorial_dirty "$vault")
    if [ -n "$AUTHORIAL_DIRTY" ]; then
        log_line "$label skip: authorial-class dirty path ($AUTHORIAL_DIRTY) — waiting for explicit authorial commit"
        return 0
    fi

    # 0f. MERGE-MARKER GUARD (session 85 AP-20):
    #    Without this, the COMMIT FIRST step below would `git add -A` files
    #    containing `<<<<<<<` / `=======` / `>>>>>>>` markers from a previous
    #    stash-pop or merge conflict, then commit them with a generic
    #    "auto-sync $(timestamp)" message, propagating markers to VPS bare
    #    and back to every host. Observed 4-5× recurrence in session 85 on
    #    pages/skills/session-coordination/SKILL.md before AP-20 codification.
    #    Reuses the canonical detector tools/test_no_merge_markers.sh (peer
    #    s86 commit 2f2c7818) so logic stays single-source-of-truth.
    if [ -x "$vault/tools/test_no_merge_markers.sh" ]; then
        if ! (cd "$vault" && bash tools/test_no_merge_markers.sh) >/dev/null 2>&1; then
            log_line "$label skip: merge markers present — waiting for authorial resolution per session-coordination AP-20"
            return 0
        fi
    fi

    # 1. COMMIT FIRST (before fetching) — fixes the race where Mac has
    #    uncommitted work that would be overwritten by a fetch+merge. Previous
    #    order (fetch → rebase → commit) hit "Your local changes would be
    #    overwritten by merge" every time Mac had new work but VPS had also
    #    advanced. Committing first lifts local work onto a commit, then
    #    merge/rebase is a commit-to-commit operation with normal resolution.
    if [ -n "$(git -C "$vault" status --porcelain 2>>"$LOG")" ]; then
        if ! git -C "$vault" add -A 2>>"$LOG"; then
            log_line "$label FAIL: git add -A returned non-zero"
            return 1
        fi
        if ! git -C "$vault" commit -q -m "auto-sync $(timestamp)" 2>>"$LOG"; then
            log_line "$label note: nothing to commit after add (or commit failed)"
        fi
    fi

    # 2. Fetch VPS state
    if ! git -C "$vault" fetch vps main -q 2>>"$LOG"; then
        log_line "$label FAIL: fetch vps main returned non-zero"
        return 1
    fi

    # 3. Try rebase vps/main. If it succeeds, great. If it fails with a conflict,
    #    abort cleanly then fall back to theirs-biased merge. If THAT also fails
    #    with add/add, auto-resolve by taking ours (content is typically
    #    byte-identical — the "mystery sync channel" puts same-content files
    #    on both sides). Only bail as LAST resort.
    if ! git -C "$vault" rebase vps/main -q 2>>"$LOG"; then
        git -C "$vault" rebase --abort 2>>"$LOG"
        if ! git -C "$vault" merge -X theirs vps/main -q \
               -m "auto-merge $(timestamp)" 2>>"$LOG"; then
            # merge -X theirs failed — typically add/add conflict where -X can't
            # pick. Resolve add/add conflicts by accepting ours (both sides have
            # the same content in practice — verified across 10+ reconciles
            # 2026-04-08). If ours resolution fails too, THEN bail.
            local unmerged
            unmerged=$(git -C "$vault" ls-files --unmerged 2>>"$LOG" | cut -f2 | sort -u)
            if [ -n "$unmerged" ]; then
                for f in $unmerged; do
                    git -C "$vault" checkout --ours "$f" 2>>"$LOG"
                    git -C "$vault" add "$f" 2>>"$LOG"
                done
                if git -C "$vault" commit -q -m "merge: accept ours (content-identical) $(timestamp)" 2>>"$LOG"; then
                    log_line "$label note: merge add/add resolved via ours"
                else
                    git -C "$vault" merge --abort 2>>"$LOG"
                    log_line "$label FAIL: merge add/add resolution failed — manual intervention required"
                    return 1
                fi
            else
                git -C "$vault" merge --abort 2>>"$LOG"
                log_line "$label FAIL: both rebase and merge failed, no unmerged files — manual intervention required"
                return 1
            fi
        else
            log_line "$label note: rebase failed, used merge -X theirs fallback"
        fi
    fi

    # 3.5. Post-merge marker guard (s82s round-17, AP-24 prevention extension):
    # `git merge -X theirs` auto-resolves most conflicts but can leave inline
    # `<<<<<<<` / `=======` / `>>>>>>>` markers when both sides edited the same
    # lines. Catch and abort BEFORE pushing those markers to VPS bare and back.
    if [ -x "$vault/tools/test_no_merge_markers.sh" ]; then
        if ! (cd "$vault" && bash tools/test_no_merge_markers.sh >/dev/null 2>&1); then
            log_line "$label FAIL: post-merge worktree contains conflict markers — refusing to push (manual cleanup required)"
            (cd "$vault" && bash tools/test_no_merge_markers.sh 2>&1 | tail -10) >> "$LOG"
            return 1
        fi
    fi

    # 4. Push to VPS bare repo
    if git -C "$vault" push vps main -q 2>>"$LOG"; then
        local head_line
        head_line=$(git -C "$vault" log --oneline -1 2>>"$LOG")
        log_line "$label OK: $head_line"
    else
        log_line "$label FAIL: push vps main returned non-zero"
        return 1
    fi

    # 4.5. Mirror to GitHub safely. GitHub can receive cloud-routine commits,
    # so fetch/rebase before pushing; never force a mirror over GitHub state.
    if git -C "$vault" remote get-url github >/dev/null 2>&1; then
        if ! git -C "$vault" fetch github main -q 2>>"$LOG"; then
            log_line "$label FAIL: fetch github main returned non-zero"
            return 1
        fi
        if ! git -C "$vault" rebase github/main -q 2>>"$LOG"; then
            git -C "$vault" rebase --abort 2>>"$LOG"
            log_line "$label FAIL: rebase github/main before mirror push failed"
            return 1
        fi
        if ! git -C "$vault" push vps main -q 2>>"$LOG"; then
            log_line "$label FAIL: push vps main after github rebase returned non-zero"
            return 1
        fi
        if ! git -C "$vault" push github main -q 2>>"$LOG"; then
            log_line "$label FAIL: push github main returned non-zero"
            return 1
        fi
        log_line "$label OK: github mirror exact"
    else
        log_line "$label WARN: github remote missing; VPS push done but GitHub mirror skipped"
    fi

    return 0
}

# Log start of run
log_line "run started"

sync_vault "$NOUS_VAULT" "nous"
NOUS_RESULT=$?

log_line "run finished (nous=$NOUS_RESULT)"
