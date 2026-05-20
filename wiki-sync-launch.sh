#!/bin/bash
# wiki-sync-launch.sh — Air wiki auto-sync runner (session 47 M4, D3-INLINE extraction)
#
# Extracted from com.nous.wiki-sync.plist ProgramArguments inline-bash (session 47 M4).
# Runs every 300 s via launchd. Stages any local edits, commits if there are
# staged changes, pulls from VPS bare, pushes back.
#
# Air runtime path: /Users/madia/nous-agaas/tools/wiki-sync-launch.sh
# Plist label:      com.nous.wiki-sync
# Schedule:         every 300 s
#
# Rollback: if this script breaks, restore the pre-M4 plist backup at
#   ~/Library/LaunchAgents/com.nous.wiki-sync.plist.pre-m4-2026-04-18
# and `launchctl bootout` + `bootstrap`.

set -u
REPO="/Users/madia/nous-agaas/wiki"
LOG="/Users/madia/nous-agaas/logs/wiki-sync.log"

authorial_dirty() {
  git -C "$REPO" status --porcelain --untracked-files=all 2>/dev/null | while IFS= read -r line; do
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

cd "$REPO"
AUTHORIAL_DIRTY=$(authorial_dirty)
if [ -n "$AUTHORIAL_DIRTY" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] air-sync skip: authorial-class dirty path ($AUTHORIAL_DIRTY) — waiting for explicit authorial commit" >> "$LOG"
  exit 0
fi
git add -A
git diff --staged --quiet || git commit -m "air-sync $(date +%Y-%m-%dT%H:%M:%S)"
git pull origin main --no-edit
if git remote get-url github >/dev/null 2>&1; then
  git fetch github main -q
  git rebase github/main -q || {
    git rebase --abort >/dev/null 2>&1 || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] air-sync FAIL: rebase github/main before mirror push failed" >> "$LOG"
    exit 1
  }
fi
git push origin main
if git remote get-url github >/dev/null 2>&1; then
  git push github main
fi
