#!/bin/bash
# test_no_duplicate_skill_headers.sh — session 63, 2026-04-22
#
# Mechanical enforcement of session-coordination AP-4 post-close gate:
# "every body-rewrite on a doctrine SKILL.md must not produce duplicate
# ### AP-N / ### Rule N. / ### N. headers."
#
# Root-cause class: session-60 and session-57 both received the same Madi
# global directive and byte-identically codified SOC Rule 18 at different line
# ranges (lines 245-265 + 267-287), producing a duplicate block that NO
# mechanical gate caught (valid markdown, valid MD5, valid YAML, valid
# frontmatter/H1/Timeline parity — silent substrate drift). Session-58-ext
# caught it manually and deduped (commit 7d7b2623). This script ensures
# recurrence is impossible.
#
# Scope: scans ALL SKILL.md files under pages/skills/*/ and
# pages/tenants/*/skills/*/ for duplicate `###` headers within the same file.
# Ignores duplicates that appear in different skills (different files).
#
# Exit codes:
#   0 = no duplicates (green)
#   1 = at least one duplicate detected (red) — print offending skill(s) + header text
#   2 = usage error / setup failure

set -u
VAULT="${VAULT:-$(cd "$(dirname "$0")/.." && pwd)}"

FOUND=0
REPORT=""

# Normalize header: lowercase, collapse whitespace, strip trailing punctuation
# (so `### AP-4 — ...` vs `### AP-4 — ...  ` both normalize to the same key)
norm() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[[:space:]]+/ /g; s/[[:space:]]+$//; s/^###[[:space:]]+//'
}

# Iterate all SKILL.md under pages/skills/* (2-deep) and pages/tenants/*/skills/* (3-deep)
while IFS= read -r -d '' f; do
  # Extract ### headings, count duplicate normalized forms
  dup=$(grep -nE "^### " "$f" 2>/dev/null \
      | awk -F: '{$1=""; print substr($0,2)}' \
      | while read -r line; do norm "$line"; done \
      | sort | uniq -c | awk '$1>1 {$1=""; print}')

  if [ -n "$dup" ]; then
    FOUND=$((FOUND+1))
    REPORT+="🔴 DUPLICATE HEADINGS in $f:"$'\n'
    while IFS= read -r d; do
      REPORT+="    $d"$'\n'
    done <<< "$dup"
  fi
done < <(find "$VAULT/pages/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -print0 2>/dev/null; \
         find "$VAULT/pages/tenants" -mindepth 4 -maxdepth 4 -name SKILL.md -print0 2>/dev/null)

if [ "$FOUND" -eq 0 ]; then
  echo "✅ test_no_duplicate_skill_headers — 0 duplicate ### headings across all SKILL.md"
  exit 0
else
  echo "$REPORT"
  echo
  echo "🔴 $FOUND skill(s) have duplicate ### headings"
  echo "   (root-cause class: session-coordination AP-4 duplicate-from-shared-directive)"
  echo "   Fix: dedupe the offending blocks; keep the authoritative version (usually lower-line-range)."
  exit 1
fi
