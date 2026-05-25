#!/bin/bash
# mark_superseded.sh — AP-61 Phase-1 deliverable
#
# Marks an old wiki page as superseded by a new canonical page.
# Implements the v1 frontmatter contract from
# pages/specs/2026-04-30-ap61-supersession-metadata-stub.md Decision D1:
#
#   status: superseded
#   superseded_by: [<wikilink>, ...]
#   superseded_at: YYYY-MM-DD
#   superseded_reason: "<1-line, ≤140 chars>"
#
# Usage:
#   tools/mark_superseded.sh <old-page-slug-or-path> <new-canonical-slug-or-path>
#
# Examples:
#   tools/mark_superseded.sh pages/lessons/individual/LESSON-055-budget-hit-retry-loop.md skills/factory-ops/skill
#   tools/mark_superseded.sh lesson-055 skills/factory-ops/skill
#
# Behavior:
#   - Validates BOTH old and new pages exist (resolves slug via $VAULT/pages/**)
#   - Idempotent: if old page already has `status: superseded`, prints message and exits 0
#   - Writes 4 frontmatter fields atomically via temp file + rename
#   - Prompts for `superseded_reason` (≤140 chars enforced)
#   - Does NOT auto-commit; operator runs git commit after reviewing the diff
#
# Privacy: no PII handling needed (operates only on wiki frontmatter)
# Anti-collision: writes to a SINGLE file; combine with `git commit -o <path>`
#   per session-coordination AP-5 when peer lanes active.

set -euo pipefail

VAULT="${VAULT:-$(cd "$(dirname "$0")/.." && pwd)}"

if [ "$#" -lt 2 ]; then
  cat <<EOF
Usage: $0 <old-slug> <new-canonical-slug>

Examples:
  $0 pages/lessons/individual/LESSON-055-budget-hit-retry-loop.md skills/factory-ops/skill
  $0 lesson-055 skills/factory-ops/skill
EOF
  exit 2
fi

OLD_INPUT="$1"
NEW_INPUT="$2"

# Resolve OLD path: try as literal path first, then as slug suffix match
resolve_path() {
  local input="$1"
  # Strip leading pages/ if present (we'll prefix it back)
  local stripped="${input#pages/}"
  stripped="${stripped%.md}"

  # Try literal full path
  if [ -f "$VAULT/$input" ]; then
    echo "$VAULT/$input"
    return 0
  fi
  # Try with .md suffix
  if [ -f "$VAULT/$input.md" ]; then
    echo "$VAULT/$input.md"
    return 0
  fi
  # Try with pages/ prefix
  if [ -f "$VAULT/pages/$stripped.md" ]; then
    echo "$VAULT/pages/$stripped.md"
    return 0
  fi
  # Glob match (last resort) — find unique match in pages/
  local matches
  matches=$(find "$VAULT/pages" -name "*${stripped}*.md" -type f 2>/dev/null)
  local count
  count=$(echo "$matches" | grep -c '^.' || true)
  if [ "$count" = "1" ]; then
    echo "$matches"
    return 0
  elif [ "$count" -gt "1" ]; then
    echo "ERROR: ambiguous match for '$input' — $count files match:" >&2
    echo "$matches" >&2
    return 1
  fi
  return 1
}

OLD_PATH="$(resolve_path "$OLD_INPUT")" || {
  echo "ERROR: could not resolve old page: '$OLD_INPUT'" >&2
  exit 1
}

# NEW slug — verify it resolves but don't need its filesystem path for the wikilink
# Just check that pages/<slug>.md exists or skills/<slug>.md or anywhere under pages/
verify_new() {
  local slug="$1"
  local stripped="${slug#pages/}"
  stripped="${stripped%.md}"

  if [ -f "$VAULT/pages/$stripped.md" ]; then return 0; fi
  if [ -f "$VAULT/pages/$stripped/SKILL.md" ]; then return 0; fi
  if [ -f "$VAULT/pages/skills/$stripped/SKILL.md" ]; then return 0; fi
  # Fuzzy: any file matching
  local matches
  matches=$(find "$VAULT/pages" -path "*${stripped}*" -type f 2>/dev/null | head -3)
  if [ -n "$matches" ]; then return 0; fi
  return 1
}

if ! verify_new "$NEW_INPUT"; then
  echo "ERROR: could not resolve new canonical page: '$NEW_INPUT'" >&2
  echo "  Looked in: $VAULT/pages/$NEW_INPUT.md, $VAULT/pages/$NEW_INPUT/SKILL.md, $VAULT/pages/skills/$NEW_INPUT/SKILL.md" >&2
  exit 1
fi

# Idempotency check
if grep -q '^status: superseded$' "$OLD_PATH"; then
  echo "OK: $OLD_PATH already marked superseded (idempotent no-op)" >&2
  grep -E '^(status|superseded_by|superseded_at|superseded_reason):' "$OLD_PATH" >&2
  exit 0
fi

# Prompt for reason (skip if SUPERSEDED_REASON env var set, for scriptability)
REASON="${SUPERSEDED_REASON:-}"
if [ -z "$REASON" ]; then
  if [ -t 0 ]; then
    printf "Enter superseded_reason (≤140 chars, 1 line): " >&2
    IFS= read -r REASON
  else
    echo "ERROR: SUPERSEDED_REASON env var required when stdin is not a TTY" >&2
    exit 1
  fi
fi

# Validate reason length (≤140 chars per D1 schema)
REASON_LEN="${#REASON}"
if [ "$REASON_LEN" -eq 0 ]; then
  echo "ERROR: superseded_reason cannot be empty" >&2
  exit 1
fi
if [ "$REASON_LEN" -gt 140 ]; then
  echo "ERROR: superseded_reason is $REASON_LEN chars; must be ≤140" >&2
  exit 1
fi

# Today's date in ISO format
TODAY="$(date -u +%Y-%m-%d)"

# Build the wikilink form for superseded_by:
NEW_SLUG="${NEW_INPUT#pages/}"
NEW_SLUG="${NEW_SLUG%.md}"

# Atomic edit via temp file + rename
TMP="$(mktemp "${TMPDIR:-/tmp}/mark_superseded.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

# Insert the 4 fields right after the opening "---" of the frontmatter.
# Strategy: read until the first "---" (frontmatter open), emit it, then emit
# the new fields, then emit the rest as-is.
awk -v tag="status: superseded" \
    -v by="superseded_by:\n  - \"[[${NEW_SLUG}]]\"" \
    -v at="superseded_at: ${TODAY}" \
    -v reason="superseded_reason: \"${REASON//\"/\\\"}\"" '
BEGIN { in_fm=0; printed_fields=0 }
/^---$/ {
  if (in_fm == 0) { in_fm=1; print; next }
  if (printed_fields == 0) {
    print tag
    print by
    print at
    print reason
    printed_fields=1
  }
  print
  in_fm=0
  next
}
{ print }
' "$OLD_PATH" > "$TMP"

# Sanity check: ensure all 4 fields landed
if ! grep -q '^status: superseded$' "$TMP"; then
  echo "ERROR: failed to inject 'status: superseded' into $OLD_PATH" >&2
  exit 1
fi

mv "$TMP" "$OLD_PATH"
trap - EXIT

echo "✅ marked superseded:" >&2
echo "  file: $OLD_PATH" >&2
echo "  status: superseded" >&2
echo "  superseded_by: [[${NEW_SLUG}]]" >&2
echo "  superseded_at: ${TODAY}" >&2
echo "  superseded_reason: \"${REASON}\"" >&2
echo "" >&2
echo "Next: review the diff and commit:" >&2
echo "  git diff '$OLD_PATH'" >&2
echo "  git commit -o '$OLD_PATH' -m 'mark <slug> superseded by ${NEW_SLUG}'" >&2
