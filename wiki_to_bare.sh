#!/bin/bash
# Bidirectional sync between VPS /wiki/ and bare repo.
# Flow: fetch bare → rebase onto it → push own commits back.
# Runs every minute via VPS cron. Partner of Mac nous-obsidian-sync.sh.
export PATH=/usr/local/bin:/usr/bin:/bin
cd /root/nous-agaas/wiki || exit 1

# Configure bare remote once
if ! git remote | grep -q '^bare$'; then
    git remote add bare /root/nous-agaas/obsidian-wiki.git
fi

LOG=/root/nous-agaas/logs/wiki_to_bare.log

authorial_dirty() {
    git status --porcelain --untracked-files=all 2>/dev/null | while IFS= read -r line; do
        path="${line#???}"
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

# 1. Fetch from bare
git fetch bare main -q 2>/dev/null || exit 0

# 2. Rebase local /wiki/ commits on top of bare state.
#    Fall back to theirs-biased merge on conflict.
if ! git rebase bare/main -q 2>/dev/null; then
    git rebase --abort 2>/dev/null
    git merge -X theirs bare/main -q -m "auto-merge $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null
fi

# 3. If there are uncommitted changes, stage + commit them (factory / claude code writes)
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    AUTHORIAL_DIRTY=$(authorial_dirty)
    if [ -n "$AUTHORIAL_DIRTY" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] vps skip: authorial-class dirty path ($AUTHORIAL_DIRTY) — waiting for explicit authorial commit" >> "$LOG"
        exit 0
    fi
    git add -A 2>/dev/null
    git commit -q -m "vps auto-sync $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null
fi

# 4. Push VPS commits to bare
if git push bare main:main -q 2>>"$LOG"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] vps ok: $(git log --oneline -1)" >> "$LOG"
fi
