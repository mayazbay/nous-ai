#!/bin/bash
# test_memory_version_claims.sh — enforces session-operating-contract v1.8.0
# Rule 16 + AP-10 (session-56, 2026-04-21).
#
# The drift this catches:
#   MEMORY top-block (and/or latest HANDOFF-AUTO linkref) claims "<skill> vX.Y.Z"
#   while the on-disk SKILL.md shows an OLDER version in frontmatter / H1 /
#   Timeline top entry. This means the AP-11 3-edit ritual got body-edited
#   but the metadata surfaces were orphaned — Karpathy compounding fails
#   silently (parity probes compare MD5 citations across hosts, not
#   narrative-claim vs disk-version).
#
# Session-55 shipped factory-ops v1.10 in: (a) gbrain timeline, (b) MASTER
# handoff See-also linkref, (c) MEMORY prepend top-block. SKILL.md frontmatter
# stayed `version: 1.9.0`, H1 stayed "v1.9.0", Timeline top entry stayed v1.9.
# Session-56 open caught this; F1 completed the metadata catch-up; THIS
# script prevents the same pattern from shipping again.
#
# Checks (for each skill claimed in MEMORY top-block with an explicit version):
#   1. Disk frontmatter `version:` matches the claim
#   2. Disk H1 line `# <skill> v<X>.<Y>.<Z>` matches
#   3. Disk `## Timeline` or `## Evidence trail` top entry has the claimed version
#
# Exit codes:
#   0 = all claimed versions match disk (or no claims found → degenerate PASS)
#   1 = at least one skill's triplet doesn't match (drift detected)
#   2 = MEMORY.md not found / unreadable / malformed
#
# Usage: bash tools/test_memory_version_claims.sh [--quiet]
#
# Source: session-operating-contract v1.8.0 Rule 16 + AP-10.
# Wires into SOAO section 4b as the 10th structural gate (session-57+ after
# false-positive rate assessed).

set -u
QUIET=0
for arg in "$@"; do
  case "$arg" in --quiet) QUIET=1 ;; esac
done
log() { [ "$QUIET" -eq 1 ] || echo "$@"; }

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
MEMFILE="$VAULT/pages/progress/claude-memory/MEMORY.md"
[ -f "$MEMFILE" ] || MEMFILE="$HOME/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md"

if [ ! -f "$MEMFILE" ]; then
  log "🔴 MEMORY.md not found at vault or symlink path"
  exit 2
fi

# Extract the first top-block: lines 1 through the first stand-alone "---"
# that follows the first "# Memory —" header. Falls back to first 50 lines
# if no terminator found (AP-7's soft cap).
TOP_BLOCK="$(awk '
  /^# Memory — updated / { inblock=1 }
  inblock && /^---$/ && NR > 1 { exit }
  inblock { print }
  !inblock && NR > 50 { exit }
' "$MEMFILE")"

if [ -z "$TOP_BLOCK" ]; then
  log "🟡 could not extract top-block from MEMORY.md — skipping (non-blocking)"
  exit 0
fi

# Skills we actively track for version claims. Explicit allowlist avoids
# false positives on stray "v1.0" strings in prose. Extend when adding a
# skill to active-bump rotation.
SKILLS=(
  "session-operating-contract"
  "factory-ops"
  "gbrain-ops"
  "infrastructure"
  "camera-management"
  "audit"
  "mistake-to-skill"
  "command-center"
  "agent-quality"
  "air-ssh-access"
  "tailscale-stability"
)

FAIL=0
PASS=0
SKIP=0

for SKILL in "${SKILLS[@]}"; do
  # Per-skill segment extraction: find occurrences of the skill slug and
  # pair each with the NEAREST following version string, stopping at
  # segment dividers (`;` or `)` after a version). This handles single
  # narrative lines that mention many skills separated by `;` or `)`.
  # Then take the highest version across all such pairs for this skill
  # (handles progression notation like "v1.7→v1.8→v1.9→v1.10" within a
  # segment — the last/highest is the current claim).
  # Match: skill-slug, whitespace, first version, optional chain of
  # "→vN.N[.N]" (progression notation) or " → vN.N". Stops at any token
  # that isn't part of the chain — so "factory-ops v1.10 + gbrain-ops
  # v1.21" only captures v1.10 as the factory-ops claim.
  CLAIMED_VER="$(echo "$TOP_BLOCK" \
    | grep -oE "${SKILL} +v[0-9]+\.[0-9]+(\.[0-9]+)?(( *→ *|→)v[0-9]+\.[0-9]+(\.[0-9]+)?)*" \
    | grep -oE 'v[0-9]+\.[0-9]+(\.[0-9]+)?' \
    | sort -V -u \
    | tail -1)"

  if [ -z "$CLAIMED_VER" ]; then
    SKIP=$((SKIP+1))
    continue
  fi

  # Normalize CLAIMED_VER to X.Y.Z (strip leading v, ensure 3-part)
  CLAIMED_NORM="${CLAIMED_VER#v}"
  case "$(echo "$CLAIMED_NORM" | tr -cd . | wc -c | tr -d ' ')" in
    1) CLAIMED_NORM="${CLAIMED_NORM}.0" ;;
  esac

  SKILL_FILE="$VAULT/pages/skills/$SKILL/SKILL.md"
  if [ ! -f "$SKILL_FILE" ]; then
    log "🟡 $SKILL: claim=$CLAIMED_VER but SKILL.md not found at $SKILL_FILE"
    SKIP=$((SKIP+1))
    continue
  fi

  # Disk frontmatter version
  DISK_FM="$(grep -m1 -E '^version:' "$SKILL_FILE" | awk '{print $2}' | tr -d '"')"

  # Disk H1 version — expects "# <skill> vX.Y.Z" line
  DISK_H1="$(grep -m1 -E "^# $SKILL v[0-9]" "$SKILL_FILE" | grep -oE 'v[0-9]+\.[0-9]+(\.[0-9]+)?' | tr -d 'v')"

  # Disk Timeline/Evidence-trail top entry version — highest version on the
  # entry line (handles "v2.42.0 → v2.43.0" progression notation — session-56
  # ext bug-fix found that `head -1` picked the OLD version; `sort -V | tail -1`
  # matches the top-block extractor's behavior, single-source-of-truth on
  # "latest claim" semantics).
  DISK_TL="$(awk '
    /^## (Timeline|Evidence trail)/ { f=1; next }
    f && /^- \*\*[0-9]{4}-[0-9]{2}-[0-9]{2}\*\*/ { print; exit }
  ' "$SKILL_FILE" | grep -oE 'v[0-9]+\.[0-9]+(\.[0-9]+)?' | sort -V -u | tail -1 | tr -d 'v')"

  # Normalize each to X.Y.Z
  for var in DISK_FM DISK_H1 DISK_TL; do
    val="$(eval echo \$$var)"
    case "$(echo "$val" | tr -cd . | wc -c | tr -d ' ')" in
      1) val="${val}.0"; eval "$var=\"$val\"" ;;
    esac
  done

  if [ "$DISK_FM" = "$CLAIMED_NORM" ] && [ "$DISK_H1" = "$CLAIMED_NORM" ] && [ "$DISK_TL" = "$CLAIMED_NORM" ]; then
    log "✅ $SKILL: claim=v$CLAIMED_NORM matches disk (fm=$DISK_FM h1=$DISK_H1 tl=$DISK_TL)"
    PASS=$((PASS+1))
  else
    log "🔴 $SKILL: MEMORY-claim=v$CLAIMED_NORM  fm=v$DISK_FM  h1=v$DISK_H1  tl=v$DISK_TL"
    log "     → Rule 16 violation. Run AP-11 3-edit ritual to match claim, OR rewrite MEMORY claim to v$DISK_FM."
    FAIL=$((FAIL+1))
  fi
done

log ""
log "test_memory_version_claims: pass=$PASS fail=$FAIL skip=$SKIP"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
