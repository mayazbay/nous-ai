#!/bin/bash
# test_claude_md_skill_pointers.sh — phantom-skill detector (library-grade-audit AP-5)
#
# Verifies every [[wikilink]] in CLAUDE.md and pages/skills/_gbrain/RESOLVER.md
# resolves to a real artifact on disk. Phantom skills are commits that ship
# doctrine pointers (CLAUDE.md, RESOLVER) without the SKILL.md commit; the
# referenced "companion" hash never lands in any branch.
#
# Failure mode codified 2026-04-30 by session s2148-mac-95617 after deep-dive
# audit found [[library-grade-audit]] referenced from CLAUDE.md + RESOLVER while
# pages/skills/library-grade-audit/SKILL.md existed on no substrate.
#
# Exit 0 → all pointers resolve. Exit 1 → phantom found. Run pre-commit and from
# the canary if desired.
#
# v1.0.0 — session s2148-mac-95617 (2026-04-30)

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

CLAUDE_MD="CLAUDE.md"
RESOLVER="pages/skills/_gbrain/RESOLVER.md"

phantoms=()
checked=0

resolve_target() {
  # Returns 0 if the wikilink target resolves to a real file/page in the wiki.
  # Case-insensitive (Obsidian wikilinks resolve case-insensitively).
  local target="$1"

  # Try direct file matches under pages/, case-insensitive
  if find pages -type f \( -iname "${target}.md" -o -ipath "*/${target}/SKILL.md" -o -ipath "*/${target}/skill.md" \) 2>/dev/null | grep -q .; then
    return 0
  fi

  # Skill shorthand: [[skill-name]] resolves to pages/skills/skill-name/SKILL.md
  if [ -f "pages/skills/${target}/SKILL.md" ]; then
    return 0
  fi

  # Allow root-level docs
  if [ -f "${target}.md" ]; then
    return 0
  fi

  return 1
}

scan_file() {
  local file="$1"
  [ -f "$file" ] || return 0

  # Strip fenced code blocks (```...```) and inline `code` so wikilinks-in-examples
  # like [[wikilink]] or [[source]] used as docs don't false-positive.
  local content
  content=$(awk '
    /^```/ { in_block = !in_block; next }
    !in_block { gsub(/`[^`]*`/, ""); print }
  ' "$file")

  # Extract every [[wikilink]] target — strip the [[]], strip pipe-aliases, dedupe
  local links
  links=$(echo "$content" | grep -oE '\[\[[^]|#]+(\|[^]]+)?\]\]' \
    | sed -E 's/^\[\[//; s/\]\]$//; s/\|.*$//' \
    | sort -u)

  while IFS= read -r target; do
    [ -z "$target" ] && continue
    checked=$((checked + 1))
    if ! resolve_target "$target"; then
      phantoms+=("$file → [[$target]]")
    fi
  done <<< "$links"
}

scan_file "$CLAUDE_MD"
scan_file "$RESOLVER"

echo "test_claude_md_skill_pointers: checked $checked unique wikilink targets across $CLAUDE_MD + $RESOLVER"

if [ ${#phantoms[@]} -eq 0 ]; then
  echo "✅ all pointers resolve"
  exit 0
fi

echo "🔴 PHANTOM SKILL/PAGE references found (${#phantoms[@]}):"
for p in "${phantoms[@]}"; do
  echo "   $p"
done
echo ""
echo "Fix paths:"
echo "  - Restore the missing SKILL.md/page from blob/memory/peer-session, OR"
echo "  - Remove the dangling [[wikilink]] from CLAUDE.md / RESOLVER (Musk step 2)."
echo ""
echo "Pattern source: pages/skills/library-grade-audit/SKILL.md AP-5"
exit 1
