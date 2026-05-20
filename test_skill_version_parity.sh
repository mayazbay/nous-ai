#!/bin/bash
# test_skill_version_parity.sh — scan all SKILL.md files for structural frontmatter drift.
#
# Invariant 1 (AP-11, session 46 round-1): every pages/skills/<name>/SKILL.md must have
#   frontmatter `version: X.Y.Z`  ==  H1 `# <name> vX.Y.Z`  ==  latest `## Timeline` entry vX.Y.Z
#
# Invariant 2 (AP-12, session 46 round-3 2026-04-18): the YAML frontmatter block must be
#   parseable by `yaml.safe_load`. Session 46 Mac-interactive created a new skill where
#   `related: [[name1]], [[name2]]` passed the version-parity grep check AND passed pre-commit
#   RULE 4 — but the `[[` sequence is YAML-invalid (malformed nested-sequence start), so gbrain's
#   ingester silently dropped the page with no error surface. See mistake-to-skill AP-12.
#
# Session 46 round-1 audit (2026-04-18) exposed 7 stale H1s (2 session-46 + 5 multi-session drift),
# including infrastructure at H1 v2.29.0 while frontmatter was v2.32.0 (out by 3 bumps).
# This drift class fools gbrain into serving stale chunk_index=0 content even after re-sync, because
# the file itself contradicts its own frontmatter.
#
# Exit 0 = all clean. Exit 2 = drift found. stderr lists each drift.
#
# Usage: bash tools/test_skill_version_parity.sh              # prints report + exits
#        bash tools/test_skill_version_parity.sh --quiet      # exit code only

set -u
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$VAULT/pages/skills"
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

FAILED=0
for skill_dir in "$SKILLS_DIR"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_file="${skill_dir}SKILL.md"
  [ -f "$skill_file" ] || continue

  name=$(basename "$skill_dir")
  case "$name" in
    _gbrain|extracted) continue ;;
  esac

  fm_ver=$(grep '^version:' "$skill_file" | head -1 | sed 's/version: *//' | tr -d ' "')
  h1_raw=$(grep "^# $name " "$skill_file" | head -1 | sed "s/^# $name //")
  h1_clean=$(echo "$h1_raw" | sed 's/^v//' | tr -d ' ')

  if [ -z "$fm_ver" ]; then
    [ "$QUIET" = "0" ] && echo "DRIFT $name: frontmatter missing 'version:'" >&2
    FAILED=1
    continue
  fi

  if [ -z "$h1_clean" ]; then
    [ "$QUIET" = "0" ] && echo "DRIFT $name: H1 header missing version (fm=$fm_ver)" >&2
    FAILED=1
    continue
  fi

  if [ "$fm_ver" != "$h1_clean" ]; then
    [ "$QUIET" = "0" ] && echo "DRIFT $name: frontmatter=$fm_ver  H1=$h1_raw" >&2
    FAILED=1
  fi

  # AP-12 check: YAML-validity of frontmatter block (session 46 round-3 2026-04-18)
  # Extract everything between the first two `---` lines and feed to yaml.safe_load.
  # Catches [[wikilink]] syntax in list values, unquoted colons in string values, bad
  # indentation, and other YAML-structural bugs invisible to grep. See mistake-to-skill AP-12.
  if command -v python3 >/dev/null 2>&1; then
    yaml_err=$(awk '/^---$/{c++; next} c==1' "$skill_file" \
        | python3 -c "import sys,yaml
try:
    yaml.safe_load(sys.stdin.read())
except Exception as e:
    sys.stderr.write(str(e).replace(chr(10), ' | '))
    sys.exit(1)" 2>&1)
    if [ -n "$yaml_err" ]; then
      [ "$QUIET" = "0" ] && echo "DRIFT $name: YAML-invalid frontmatter — ${yaml_err} (see mistake-to-skill AP-12)" >&2
      FAILED=1
    fi
  fi

  # AP-48 check: Timeline↔AP-bullet parity (session 48 deep-audit, 2026-04-18)
  # Mechanically enforces mistake-to-skill AP-11 v1.9 4th check: every "added/extended/
  # absorbed AP-N" claim in the Timeline (or Evidence trail) section MUST have a matching
  # bullet ("### AP-N" or "- **AP-N:" or "- **AP-N —" or "**AP-N:") anywhere in the file.
  # Session 48 deep-audit found 2 real orphans (infrastructure AP-45, secrets-management AP-10)
  # accumulated across 1-2 sessions while AP-11 v1.9 4th check was manual-only.
  if command -v python3 >/dev/null 2>&1; then
    orphans=$(python3 -c "
import re, sys
body = open('$skill_file').read()
tl_match = re.search(r'^## (Timeline|Evidence trail)\s*\$(.*?)(?=^## |\Z)', body, re.M|re.S)
if not tl_match: sys.exit(0)
tl = tl_match.group(2)
claims = set()
for pat in [r'\*\*AP-(\d+)\*\*', r'\\badded\s+(?:\*\*)?AP-(\d+)', r'\\bextended\s+(?:\*\*)?AP-(\d+)', r'\\babsorbed\s+(?:\*\*)?AP-(\d+)', r'\\babsorbs\s+(?:\*\*)?AP-(\d+)']:
    claims.update(re.findall(pat, tl, re.I))
existing = set()
existing.update(re.findall(r'^###\s*AP-(\d+)', body, re.M))
existing.update(re.findall(r'^-\s*\*\*AP-(\d+)[:\s\u2014]', body, re.M))
existing.update(re.findall(r'^\*\*AP-(\d+)[:\s\u2014]', body, re.M))
orph = sorted({n for n in claims if n and n not in existing}, key=int)
if orph: print(','.join(orph))
")
    if [ -n "$orphans" ]; then
      [ "$QUIET" = "0" ] && echo "DRIFT $name: Timeline claims AP-${orphans} but no matching bullet in file (see mistake-to-skill AP-11 v1.9 4th check + infrastructure AP-48)" >&2
      FAILED=1
    fi
  fi
done

if [ "$FAILED" = "0" ]; then
  [ "$QUIET" = "0" ] && echo "OK: all skill frontmatter <-> H1 versions match"
  exit 0
else
  [ "$QUIET" = "0" ] && echo "FAIL: version drift found — fix with Edit on the H1 line, or bump frontmatter version" >&2
  exit 2
fi
