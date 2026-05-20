#!/usr/bin/env bash
# Classify skill back-link state per gbrain-ops AP-50 / AP-52.
#
# Purpose:
#   CLAUDE.md `BRAIN-FIRST RULE` "Iron law back-linking" was amended in s85 to
#   accept BOTH `[[wikilink]]` and prose cross-refs. This detector enforces the
#   amended semantics by classifying every skill into:
#
#     class (a) — zero references anywhere in the substrate (real orphan, BAD)
#     class (b) — has prose-form references but gbrain extractor blind (tooling
#                 gap, ACCEPTABLE per AP-52)
#     fully-linked — has [[wikilink]] form references (gbrain-discoverable)
#
# Class (a) is the only violation under the amended doctrine.
#
# Algorithm (purely local — no gbrain API dependency):
#   For each pages/skills/<name>/SKILL.md:
#     1. Extract <name> from path
#     2. Grep all of pages/ for occurrences of <name> EXCLUDING the skill's own page
#     3. Count hits in {[[<name>]] or [[skills/<name>]]} (wikilink form)
#        and in plain prose (any other occurrence)
#     4. Classify:
#        - 0 wikilink + 0 prose → class (a) ORPHAN
#        - 0 wikilink + ≥1 prose → class (b) tooling gap
#        - ≥1 wikilink → fully-linked
#
# Exit codes:
#   0 = class (a) within threshold (default ≤5% of total skills)
#   2 = class (a) exceeds threshold (real doctrine violation)
#
# Cross-ref:
#   - gbrain-ops AP-50 (the finding)
#   - gbrain-ops AP-52 (the doctrine amendment + this detector's spec)
#   - CLAUDE.md BRAIN-FIRST RULE (amended in s85, 2026-04-29)
#
# Usage:
#   bash tools/test_backlink_iron_law_classification.sh
#   ORPHAN_PCT_MAX=10 bash tools/test_backlink_iron_law_classification.sh
#   VERBOSE=1 bash tools/test_backlink_iron_law_classification.sh
#
# Author: session-85 s85-mac-42034-20260429T1534

set -u

# Resolve repo root (script lives at tools/test_*.sh; vault root is parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/pages/skills"
PAGES_DIR="$REPO_ROOT/pages"

ORPHAN_PCT_MAX="${ORPHAN_PCT_MAX:-5}"   # max % of skills allowed to be class (a)
VERBOSE="${VERBOSE:-0}"

if [ ! -d "$SKILLS_DIR" ]; then
  echo "test_backlink_iron_law: skills dir not found at $SKILLS_DIR" >&2
  exit 2
fi

class_a=()    # real orphans (BAD)
class_b=()    # prose-only (OK, tooling gap)
fully_linked=()
total=0

# Iterate all skill SKILL.md files
while IFS= read -r skill_md; do
  total=$((total + 1))
  # Extract skill name (parent dir name)
  skill_name="$(basename "$(dirname "$skill_md")")"
  [ -z "$skill_name" ] && continue
  [ "$skill_name" = "_gbrain" ] && continue   # resolver, not a skill
  [ "$skill_name" = "extracted" ] && continue # extracted-stash, not active

  # Count wikilink-form references across pages/, EXCLUDING the skill's own dir
  # Patterns: [[<name>]], [[skills/<name>]], [[<name>/skill]], [[<name>/SKILL]]
  wikilink_count=$(grep -rE "\[\[(skills/)?${skill_name}(/(skill|SKILL))?\]\]" "$PAGES_DIR" \
    --include='*.md' \
    --exclude-dir="$skill_name" \
    2>/dev/null | wc -l | tr -d ' ')

  # Count prose-form references: skill name as a word, not inside [[ ]]
  # Use word-boundary match; exclude the skill's own dir
  # Filter out [[ ... ]] lines to avoid double-counting wikilinks
  prose_count=$(grep -rwE "${skill_name}" "$PAGES_DIR" \
    --include='*.md' \
    --exclude-dir="$skill_name" \
    2>/dev/null \
    | grep -vE "\[\[.*${skill_name}.*\]\]" \
    | wc -l | tr -d ' ')

  if [ "$wikilink_count" -gt 0 ]; then
    fully_linked+=("$skill_name")
    [ "$VERBOSE" = "1" ] && printf '  fully-linked  %-40s wiki=%d prose=%d\n' "$skill_name" "$wikilink_count" "$prose_count"
  elif [ "$prose_count" -gt 0 ]; then
    class_b+=("$skill_name")
    [ "$VERBOSE" = "1" ] && printf '  class-b       %-40s wiki=0  prose=%d\n' "$skill_name" "$prose_count"
  else
    class_a+=("$skill_name")
    [ "$VERBOSE" = "1" ] && printf '  CLASS-A       %-40s NO REFS ANYWHERE\n' "$skill_name"
  fi
done < <(find "$SKILLS_DIR" -mindepth 2 -maxdepth 2 -name 'SKILL.md' 2>/dev/null | sort)

# Adjust total (subtract excluded dirs that incremented total but were skipped)
real_total=$((${#class_a[@]} + ${#class_b[@]} + ${#fully_linked[@]}))

if [ "$real_total" -eq 0 ]; then
  echo "test_backlink_iron_law: no skills found in $SKILLS_DIR" >&2
  exit 2
fi

orphan_pct=$(( ${#class_a[@]} * 100 / real_total ))

echo "=== iron-law back-link classification ==="
echo "  total skills:    $real_total"
echo "  fully-linked:    ${#fully_linked[@]} ([[wikilink]] form)"
echo "  class (b):       ${#class_b[@]} (prose-only — gbrain v0.10.1 blind, but doctrine-OK per AP-52)"
echo "  class (a):       ${#class_a[@]} (REAL ORPHANS — no refs anywhere)"
echo "  orphan_pct:      ${orphan_pct}% (threshold ≤${ORPHAN_PCT_MAX}%)"

if [ "${#class_a[@]}" -gt 0 ]; then
  echo ""
  echo "Class (a) skills (need at least one reference somewhere):"
  for s in "${class_a[@]}"; do
    echo "  - $s"
  done
fi

if [ "$orphan_pct" -gt "$ORPHAN_PCT_MAX" ]; then
  echo ""
  echo "FAIL: class (a) ${orphan_pct}% exceeds threshold ${ORPHAN_PCT_MAX}%"
  echo "Fix: add at least one cross-reference (prose or [[wikilink]]) for each class (a) skill from a related skill, handoff, or audit."
  echo "Doctrine: CLAUDE.md BRAIN-FIRST RULE + gbrain-ops AP-52."
  exit 2
fi

echo ""
echo "OK: iron-law back-linking within bounds (class (a) ${orphan_pct}% ≤ ${ORPHAN_PCT_MAX}%)"
exit 0
