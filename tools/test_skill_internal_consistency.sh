#!/bin/bash
# test_skill_internal_consistency.sh — detect SKILL.md frontmatter metadata vs H1 version drift
#
# Pattern source: ceo-hierarchy AP-5. When a SKILL.md is bumped to a new
# version that inverts a binding rule, the `description:` field is the surface
# most often forgotten. The bump triple (frontmatter version + H1 + Timeline
# entry) updates the version field but not the description prose, so the
# description or title proclaims the OLD policy at vN-K while the rest of the
# page is at vN.
#
# This probe scans every SKILL.md and surfaces drift between:
#   - H1 version: `# <skill-name> vX.Y.Z`
#   - First version mentioned in `description:` field
#   - Version mentioned in `title:` field, when present
#
# A mismatch means top-level metadata is stale and may proclaim an old binding
# rule. Future agents reading frontmatter/top-down will absorb the wrong rule.
#
# Default: scan staged SKILL.md (intended for pre-commit RULE 10 wiring).
# Flag --all: scan every SKILL.md in pages/skills/.
#
# v1.0.0 — session s108 (2026-04-30/05-01)

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || exit 1

mode="staged"
[ "${1:-}" = "--all" ] && mode="all"

if [ "$mode" = "staged" ]; then
  files=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | grep -E '^pages/skills/[^/]+/SKILL\.md$' || true)
else
  files=$(find pages/skills -maxdepth 2 -name SKILL.md -type f 2>/dev/null | grep -v '^pages/skills/_' | sort)
fi

[ -z "$files" ] && { echo "no skills to scan"; exit 0; }

violations=0
checked=0

while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ -f "$f" ] || continue
  checked=$((checked + 1))

  h1_ver=$(grep -oE '^# [a-z0-9_-]+ v[0-9]+\.[0-9]+\.[0-9]+' "$f" 2>/dev/null | head -1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')

  # Pull description: field (single-line OR multi-line YAML scalar)
  desc=$(awk '
    /^description:/ { flag=1; sub(/^description:[[:space:]]*/, ""); print; next }
    flag {
      if (/^[a-z_]+:/) { exit }
      print
    }
  ' "$f" 2>/dev/null)

  # First version mentioned in description (if any)
  fm_first_ver=$(echo "$desc" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  title_ver=$(grep -oE '^title:[[:space:]]*"?[^"]* v[0-9]+\.[0-9]+\.[0-9]+' "$f" 2>/dev/null | head -1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')

  if [ -n "$h1_ver" ] && [ -n "$fm_first_ver" ] && [ "$h1_ver" != "$fm_first_ver" ]; then
    echo "🔴 $f"
    echo "   H1 version:           $h1_ver"
    echo "   description starts:   $fm_first_ver"
    echo "   description text (first 200 chars):"
    echo "   $(echo "$desc" | head -c 200 | tr '\n' ' ')..."
    violations=$((violations + 1))
  fi

  if [ -n "$h1_ver" ] && [ -n "$title_ver" ] && [ "$h1_ver" != "$title_ver" ]; then
    echo "🔴 $f"
    echo "   H1 version:           $h1_ver"
    echo "   title version:        $title_ver"
    violations=$((violations + 1))
  fi
done <<< "$files"

echo ""
echo "test_skill_internal_consistency: scanned $checked SKILL.md, $violations violation(s)"

if [ "$violations" -eq 0 ]; then
  echo "✅ all skills internally consistent"
  exit 0
fi

echo ""
echo "Fix path: rewrite stale title/description metadata to the current version + binding policy."
echo "Pattern source: pages/skills/ceo-hierarchy/SKILL.md AP-5"
exit 1
