#!/bin/bash
# test_auto_sync_authorial_guard.sh — AP-59 static regression check.
#
# Ensures every generic auto-sync writer refuses to commit authorial-class files
# under generic messages (`auto-sync`, `air-sync`, `vps auto-sync`).

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SCRIPTS=(
  "tools/nous-obsidian-sync.sh"
  "tools/wiki-sync-launch.sh"
  "tools/wiki_to_bare.sh"
)

REQUIRED_PATTERNS=(
  "authorial_dirty"
  "authorial-class dirty path"
  "pages/skills/*/SKILL.md"
  "pages/tenants/*/skills/*/SKILL.md"
  "tenants/*"
  "pages/audits/*.md"
  "pages/plans/*.md"
  "pages/progress/HANDOFF-*.md"
  "pages/progress/claude-memory/MEMORY.md"
  "laws/*.md"
  "tools/*.sh|tools/*.py|tools/*.plist"
  "AGENTS.md|CLAUDE.md"
)

fail=0

for rel in "${SCRIPTS[@]}"; do
  file="$ROOT/$rel"
  if [ ! -f "$file" ]; then
    echo "missing script: $rel"
    fail=1
    continue
  fi

  for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if ! grep -Fq "$pattern" "$file"; then
      echo "missing guard pattern in $rel: $pattern"
      fail=1
    fi
  done
done

AIR_SCRIPT="$ROOT/tools/wiki-sync-launch.sh"
AIR_SKIP_BLOCK="$(sed -n '/AUTHORIAL_DIRTY=$(authorial_dirty)/,/^fi$/p' "$AIR_SCRIPT")"
if printf '%s\n' "$AIR_SKIP_BLOCK" | grep -Fq "git pull"; then
  echo "Air guard still pulls while authorial files are dirty"
  fail=1
fi

if grep -R "authorial_dirty" "$ROOT/tools" -n | grep -E 'test_|bak|pre-' >/dev/null; then
  : # okay: tests/backups may mention it; this branch documents intentional no-op
fi

if [ "$fail" -ne 0 ]; then
  echo "FAIL: auto-sync authorial guard drift"
  exit 1
fi

echo "OK: auto-sync authorial guard present on Mac, Air, and VPS writers"
