#!/bin/bash
# pre-commit hook: TAN-PATTERN ENFORCEMENT (session 35, 2026-04-16; session 43 RENAME-bypass fix, 2026-04-17; session 46 AP-11 parity gate, 2026-04-18; session 47 RULE 5 MD5 citation gate, 2026-04-18; session 48 RULE 6 .env block, 2026-04-18)
#
# Rule set (hardcoded; bypassing requires editing this file on disk):
#   1a. BLOCK any commit that ADDS a new file matching
#       pages/lessons/individual/LESSON-[0-9]+-*.md
#       (Tan/Karpathy: rules belong in SKILL.md, evidence belongs in gbrain
#       timelines — NEVER a fresh LESSON file.)
#   1b. (session 43) BLOCK any RENAME or COPY whose DESTINATION matches
#       pages/lessons/individual/LESSON-[0-9]+-*.md when the SOURCE is OUTSIDE
#       pages/lessons/individual/. Without this, renaming an off-canonical
#       LESSON file (e.g. pages/lessons/LESSON-080-...) into the canonical
#       directory bypasses RULE ZERO via git rename detection
#       (--diff-filter=A misses rename targets).
#       (Renames WITHIN pages/lessons/individual/ are still allowed for
#       slug normalization.)
#   2.  ALLOW modifications and deletions of existing LESSON files
#       (for bookkeeping, slug normalization within the canonical dir,
#       or historical correction).
#   3.  BLOCK any lesson-id / title / H1 drift inside the staged LESSON
#       changes (an absorbed historical LESSON edit cannot ship with a
#       wrong id / title / H1 triple).
#   4.  (session 46) BLOCK any commit that touches a SKILL.md with
#       frontmatter/H1 version drift (mistake-to-skill AP-11). Every bump
#       requires frontmatter `version:` + H1 `# <name> vX.Y.Z` + Timeline
#       entry — if any of the trio is stale, the commit is rejected.
#       Scanner: tools/test_skill_version_parity.sh. Session 46 deep
#       audit found 7 drifts that accumulated silently under AP-10's
#       per-commit check; this rule makes AP-14 cross-cut rot mechanical,
#       matching AP-35 pre-push parity's compounding pattern.
#   5.  (session 47) BLOCK any commit that touches a SKILL.md whose prose
#       cites an MD5 that no longer matches the cited file.
#       Scanner: tools/test_skill_md5_citations.sh.
#   6a. (session 2026-05-05) If any real `.env` file OR
#       pages/secrets-manifest.md is staged, run
#       `python3 tools/credentials_discovery.py audit --strict` first.
#       This catches undocumented runtime keys with an exact missing-key list
#       before the generic .env block fires.
#   6b. (session 48) BLOCK any commit that adds/modifies a `*.env` file
#       in the vault. Secrets don't live in git-tracked wiki paths.
#       Exclusions: `.env.example`, `.env.template`, `.env.sample` (template
#       forms with no real values). Paired with `secrets-management` AP-11
#       (runtime .env MUST be 0600 — enforced by nightly scanner).
#
# Supersedes the prior skill-first co-commit rule (AMD-005). The prior rule
# required LESSON + SKILL pairing, which in practice *forced* agents to
# write LESSONs. The Tan pattern removes that trap by forbidding new
# LESSONs outright — the rule now lives in SKILL.md; the timeline lives
# in gbrain.
#
# Escape hatch: `git commit --no-verify` bypasses hooks at the operator's
# own risk. No in-repo flag unsets this rule.
#
# Evidence trail for this hook lives in:
#   - pages/skills/mistake-to-skill/SKILL.md AP-8 (Tan pattern rule)
#   - pages/skills/infrastructure/SKILL.md   (timeline entry)
#   - gbrain timeline entries on both skill pages above
#   - laws/LAW-015 (amended to drop the LESSON-file requirement)

set -eu

REPO_ROOT="$(git rev-parse --show-toplevel)"

# ---------- RULE 0: no merge conflict markers in staged files ----------
# Session 91 / session-coordination AP-20: auto-sync stash-pop conflicts can
# leave literal conflict markers in hot wiki files. Catch them directly before
# YAML or parity gates produce noisier failures.
if [ -x "$REPO_ROOT/tools/test_no_merge_markers.sh" ]; then
  (cd "$REPO_ROOT" && bash tools/test_no_merge_markers.sh --staged) || exit 1
fi

added=$(git diff --cached --name-only --diff-filter=A 2>/dev/null || true)
modified=$(git diff --cached --name-only --diff-filter=M 2>/dev/null || true)

# Renames + copies into the canonical LESSON dir from OUTSIDE that dir
# (session 43 fix: closes the rename-bypass that let LESSON-080 through 2026-04-17 14:01:53)
renames_into_canonical=$(git diff --cached --name-status --diff-filter=RC 2>/dev/null | awk '
    {
        # Output format: "R<score>\tSRC\tDST"  or  "C<score>\tSRC\tDST"
        src=$2; dst=$3;
        if (dst ~ /^pages\/lessons\/individual\/LESSON-[0-9]+-.*\.md$/ &&
            src !~ /^pages\/lessons\/individual\//) {
            print dst;
        }
    }' || true)

# ---------- RULE 1: no new LESSON files (Adds + Rename/Copy targets) ----------
direct_adds=$(echo "$added" | grep -E '^pages/lessons/individual/LESSON-[0-9]+-.*\.md$' || true)
new_lessons=$(printf "%s\n%s\n" "$direct_adds" "$renames_into_canonical" | grep -v '^$' | sort -u || true)
if [ -n "$new_lessons" ]; then
    cat >&2 <<EOF

============================================================
  BLOCKED: TAN-PATTERN ENFORCEMENT (session 35)
============================================================

  You are adding NEW LESSON file(s):
$(echo "$new_lessons" | sed 's/^/    /')

  The Tan/Karpathy pattern forbids creating new LESSON files.
  Rules belong in SKILL.md. Evidence belongs in gbrain timelines.
  A fresh LESSON-NNN file decays — skills compound.

  What to do instead:
    1. Add the rule to pages/skills/<target>/SKILL.md (new AP or phase).
    2. Bump the skill version; append a Timeline entry.
    3. Append a gbrain timeline entry via mcp__gbrain__add_timeline_entry
       on the skill's page (slug: pages/skills/<target>/skill).
    4. Commit the SKILL.md change only. No LESSON file needed.

  Historical LESSONs may still be EDITED or DELETED.
  See pages/skills/mistake-to-skill/SKILL.md AP-8.
============================================================

EOF
    exit 1
fi

# ---------- RULE 3: drift-scan on any LESSON file in the commit ----------
all_lesson_edits=$(printf "%s\n%s\n" "$added" "$modified" | grep -E '^pages/lessons/individual/LESSON-[0-9]+-.*\.md$' || true)
if [ -n "$all_lesson_edits" ]; then
    drift_found=0
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        [ -f "$f" ] || continue
        id=$(grep -E '^id: ' "$f" | head -1 | awk '{print $2}')
        name=$(grep -E '^name: ' "$f" | head -1 | awk '{print $2}')
        title_id=$(grep -E '^title: ' "$f" | head -1 | grep -oE 'LESSON-[0-9]+[a-z]?' | head -1)
        h1_id=$(grep -E '^# LESSON-' "$f" | head -1 | grep -oE 'LESSON-[0-9]+[a-z]?' | head -1)

        if [ -z "$id" ] && [ -z "$name" ]; then
            echo "DRIFT: $f has neither 'id:' nor 'name:' in frontmatter" >&2
            drift_found=1
        fi
        eff_id="${id:-$name}"
        if [ -n "$title_id" ] && [ -n "$eff_id" ] && [ "$title_id" != "$eff_id" ]; then
            echo "DRIFT: $f title=$title_id but id=$eff_id" >&2
            drift_found=1
        fi
        if [ -n "$h1_id" ] && [ -n "$eff_id" ] && [ "$h1_id" != "$eff_id" ]; then
            echo "DRIFT: $f H1=$h1_id but id=$eff_id" >&2
            drift_found=1
        fi
    done <<< "$all_lesson_edits"

    if [ "$drift_found" = "1" ]; then
        cat >&2 <<EOF

============================================================
  BLOCKED: LESSON id / title / H1 drift (mistake-to-skill AP-7)
============================================================
  Fix the DRIFT lines above, re-stage, retry.
============================================================

EOF
        exit 1
    fi
fi

# ---------- RULE 4: SKILL.md frontmatter/H1/Timeline parity (session 46 AP-11) ----------
staged_skills=$(printf "%s\n%s\n" "$added" "$modified" | grep -E '^pages/skills/[^/]+/SKILL\.md$' || true)
renamed_skills=$(git diff --cached --name-status --diff-filter=RC 2>/dev/null | awk '
    { dst=$3; if (dst ~ /^pages\/skills\/[^\/]+\/SKILL\.md$/) print dst; }' || true)
touched_skills=$(printf "%s\n%s\n" "$staged_skills" "$renamed_skills" | grep -v '^$' | sort -u || true)
if [ -n "$touched_skills" ]; then
    scanner="$(git rev-parse --show-toplevel)/tools/test_skill_version_parity.sh"
    if [ -x "$scanner" ]; then
        drift_log="$(mktemp)"
        if ! "$scanner" >/dev/null 2>"$drift_log"; then
            cat >&2 <<EOF

============================================================
  BLOCKED: SKILL.md version parity drift (mistake-to-skill AP-11)
============================================================

$(cat "$drift_log")

  Every SKILL.md bump requires THREE edits together:
    1. frontmatter  version: X.Y.Z
    2. H1 header    # <skill-name> vX.Y.Z
    3. new Timeline entry

  Agents habitually update #1 and #3, skip the boring #2.
  That drift compounds silently across sessions.
  See mistake-to-skill AP-11 + audit AP-14 (session 46 deep audit).

  Fix the DRIFT line(s) above, re-stage, retry.
  Escape hatch: \`git commit --no-verify\` (emergency only).
============================================================

EOF
            rm -f "$drift_log"
            exit 1
        fi
        rm -f "$drift_log"
    fi
fi

# ---------- RULE 5: SKILL.md MD5 citation ↔ reality (session 47 AP-44) ----------
# Every SKILL.md that cites a file MD5 in prose must match the file it claims to
# represent. Historical citations in Timeline blocks are skipped (append-only by
# architecture); transition-form citations (X → Y) are skipped (both historical).
# Scanner: tools/test_skill_md5_citations.sh.
# Sibling of RULE 4 (SKILL version parity, AP-43) and pre-push AP-35 (hook-parity).
if [ -n "$touched_skills" ]; then
    md5_scanner="$(git rev-parse --show-toplevel)/tools/test_skill_md5_citations.sh"
    if [ -x "$md5_scanner" ]; then
        md5_log="$(mktemp)"
        if ! "$md5_scanner" >"$md5_log" 2>&1; then
            cat >&2 <<EOF

============================================================
  BLOCKED: SKILL.md MD5 citation ↔ reality drift (infrastructure AP-44)
============================================================

$(cat "$md5_log")

  SKILL.md prose cites file MD5s. If the cited file drifts without the
  citation updating, the doctrine silently lies. This gate rejects such
  drift at commit time.

  Fix one of:
    (a) Citation is stale — update the SKILL.md prose with the current MD5.
    (b) File drifted unexpectedly — investigate why (check AP-35 hook parity).
    (c) Citation is historical — rewrite with arrow form (X → Y) or move into
        the Timeline block (which this scanner skips by design).

  Escape hatch: \`git commit --no-verify\` (emergency only).
============================================================

EOF
            rm -f "$md5_log"
            exit 1
        fi
        rm -f "$md5_log"
    fi
fi

# ---------- RULE 6: no .env files in vault (session 48 infrastructure AP-45) ----------
# Grep pattern: any path ending with literal ".env" (not .env.example/.template/.sample
# because those end with a further extension and $-anchor rejects them).
env_direct=$(printf "%s\n%s\n" "$added" "$modified" | grep -E '(^|/)[^/]*\.env$' || true)
env_renames_into=$(git diff --cached --name-status --diff-filter=RC 2>/dev/null | cut -f3 | grep -E '(^|/)[^/]*\.env$' || true)
env_paths=$(printf "%s\n%s\n" "$env_direct" "$env_renames_into" | grep -v '^$' | sort -u || true)
manifest_staged=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | grep -E '^pages/secrets-manifest\.md$' || true)
credentials_gate_trigger=$(printf "%s\n%s\n" "$env_paths" "$manifest_staged" | grep -v '^$' | sort -u || true)
if [ -n "$credentials_gate_trigger" ]; then
    credentials_tool="$REPO_ROOT/tools/credentials_discovery.py"
    manifest_file="$REPO_ROOT/pages/secrets-manifest.md"
    if [ -x "$credentials_tool" ] && [ -f "$manifest_file" ]; then
        audit_out="$(mktemp /tmp/credentials-discovery-audit-out.XXXXXX)"
        audit_err="$(mktemp /tmp/credentials-discovery-audit-err.XXXXXX)"
        if ! (cd "$REPO_ROOT" && python3 tools/credentials_discovery.py audit --strict >"$audit_out" 2>"$audit_err"); then
            cat >&2 <<EOF

============================================================
  BLOCKED: credentials manifest drift (credentials-discovery)
============================================================

$(cat "$audit_err")

  Staged trigger(s):
$(echo "$credentials_gate_trigger" | sed 's/^/    /')

  Fix: add missing key rows to pages/secrets-manifest.md v2,
  re-stage, and retry. Do not ask Madi to paste credentials.
============================================================

EOF
            rm -f "$audit_out" "$audit_err"
            exit 1
        fi
        rm -f "$audit_out" "$audit_err"
    fi
fi
if [ -n "$env_paths" ]; then
    cat >&2 <<EOF

============================================================
  BLOCKED: .env file in vault (infrastructure AP-45)
============================================================

  You are trying to commit \`.env\` file(s):
$(echo "$env_paths" | sed 's/^/    /')

  Secrets don't live in the vault. If this is a template with no real
  values, rename it to one of the accepted template forms:
    mv path/.env path/.env.example
    mv path/.env.local path/.env.template
    mv path/secret.env path/secret.env.sample

  Real secrets live in:
    - macOS Keychain (Mac master source — see skills/secrets-management).
    - Runtime \`.env\` files on the target host at 0600 perms
      (secrets-management AP-11, scanned via tools/test_secret_perms.sh).

  See:
    - skills/secrets-management/SKILL.md (AP-11, v1.4 session 48)
    - skills/infrastructure/SKILL.md (AP-45 pre-commit RULE 6)

  Escape hatch: \`git commit --no-verify\` (emergency only).
============================================================

EOF
    exit 1
fi

# ───────────────────────────────────────────────────────────────
# RULE 7 (session 68p, 2026-04-23) — agent-autonomy (musk-algorithm AP-4)
# BLOCK commits where staged HANDOFF-*.md / MEMORY.md contain red-flag
# deference phrases ("optional:", "whenever ready", "your call", etc.)
# without matching hall-pass markers.
# Bypass: git commit --no-verify (operator risk).
# ───────────────────────────────────────────────────────────────
if [ -x "$REPO_ROOT/tools/test_musk_step_2.sh" ]; then
  (cd "$REPO_ROOT" && bash tools/test_musk_step_2.sh) || exit 1
fi

if [ -x "$REPO_ROOT/tools/test_agent_autonomy.sh" ]; then
  (cd "$REPO_ROOT" && bash tools/test_agent_autonomy.sh --staged) || exit 1
fi

# ───────────────────────────────────────────────────────────────
# RULE 8 (session 105, 2026-04-30) — library-grade Tier-A1 gate
#   Block commits that regress library-grade gates. Only fires when staged
#   paths intersect core Tier-A1 territory (skills, laws, systems, entities,
#   projects, concepts, aliases, library_*.py, audits_index_generate.py).
#   Report streams such as audits/specs/plans/handoffs/dashboards are Tier B
#   and do not trigger the heavy gate by themselves. Substrate baseline: all 3
#   scanners exit 0 per gbrain-ops AP-67/AP-76.
#   Bypass: git commit --no-verify (operator risk).
# ───────────────────────────────────────────────────────────────
TIER_A1_RE='^(laws/|pages/(skills|laws|systems|entities|projects|concepts|aliases)/|tools/(library_|audits_index_generate))'
STAGED_TIER_A1=$(git diff --cached --name-only --diff-filter=ACMR | grep -E "$TIER_A1_RE" || true)
if [ -n "$STAGED_TIER_A1" ]; then
  for SCANNER in library_reachability_scan.py library_canonical_scan.py library_crossref_scan.py; do
    if ! (cd "$REPO_ROOT" && python3 "tools/$SCANNER" >/dev/null 2>&1); then
      echo "🔴 RULE 8 FAIL: tools/$SCANNER regressed library-grade gate."
      echo "   Run: python3 tools/$SCANNER     (without redirect, for details)"
      echo "   Bypass (emergency only): git commit --no-verify"
      exit 1
    fi
  done
fi

# ───────────────────────────────────────────────────────────────
# RULE 9 (session s2148, 2026-04-30) — phantom-skill detector
#   Block commits that ship CLAUDE.md / _gbrain/RESOLVER.md changes which
#   reference [[wikilinks]] pointing at non-existent files. Pattern source:
#   library-grade-audit AP-5 — peer session shipped doctrine pointers without
#   the SKILL.md companion landing in any branch (commit aedc3952 referenced
#   "companion 8aa5aa54" which did not exist).
#   Fires when CLAUDE.md, RESOLVER.md, or any SKILL.md is staged.
#   Bypass: git commit --no-verify (operator risk).
# ───────────────────────────────────────────────────────────────
PHANTOM_TRIGGER=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '^(CLAUDE\.md$|pages/skills/_gbrain/RESOLVER\.md$|pages/skills/[^/]+/SKILL\.md$)' || true)
if [ -n "$PHANTOM_TRIGGER" ] && [ -x "$REPO_ROOT/tools/test_claude_md_skill_pointers.sh" ]; then
  if ! (cd "$REPO_ROOT" && bash tools/test_claude_md_skill_pointers.sh >/dev/null 2>&1); then
    echo "🔴 RULE 9 FAIL: phantom skill/page reference in CLAUDE.md or RESOLVER."
    echo "   Run: bash tools/test_claude_md_skill_pointers.sh    (for details)"
    echo "   Pattern: pages/skills/library-grade-audit/SKILL.md AP-5"
    echo "   Bypass (emergency only): git commit --no-verify"
    exit 1
  fi
fi

# ───────────────────────────────────────────────────────────────
# RULE 10 (session s108, 2026-05-01) — SKILL.md internal consistency
#   Block commits where any staged SKILL.md has a frontmatter
#   `description:` whose first version reference doesn't match the H1 version.
#   Pattern source: ceo-hierarchy AP-5 — when a binding rule is inverted in
#   a version bump, the description prose at the top of the page often gets
#   forgotten and proclaims the OLD policy at vN-K while H1 says vN.
#   Fires when ANY SKILL.md is staged.
#   Bypass: git commit --no-verify (operator risk).
# ───────────────────────────────────────────────────────────────
SKILL_TRIGGER=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '^pages/skills/[^/]+/SKILL\.md$' || true)
if [ -n "$SKILL_TRIGGER" ] && [ -x "$REPO_ROOT/tools/test_skill_internal_consistency.sh" ]; then
  if ! (cd "$REPO_ROOT" && bash tools/test_skill_internal_consistency.sh >/dev/null 2>&1); then
    echo "🔴 RULE 10 FAIL: SKILL.md description/H1 version drift."
    echo "   Run: bash tools/test_skill_internal_consistency.sh    (for details)"
    echo "   Pattern: pages/skills/ceo-hierarchy/SKILL.md AP-5"
    echo "   Bypass (emergency only): git commit --no-verify"
    exit 1
  fi
fi

# ───────────────────────────────────────────────────────────────
# RULE 11 (substrate-v2 Phase 0.7, 2026-05-04) — Skill tier classification gate
#   Block commits where any staged pages/skills/<name>/SKILL.md is missing
#   a valid `tier:` frontmatter field (must be 1, 2, or 3).
#   Pattern source: Nate B Jones "Skills Are Infrastructure" (20260324-kyk).
#   Tier convention documented in pages/skills/_gbrain/TIER-CONVENTION.md.
#     1 = standards (auto-load every session)
#     2 = methodology (load by domain)
#     3 = personal/per-task
#   Bypass: git commit --no-verify (operator risk).
# ───────────────────────────────────────────────────────────────
TIER_TRIGGER=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '^pages/skills/[^/_][^/]*/SKILL\.md$' || true)
if [ -n "$TIER_TRIGGER" ]; then
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    tier=$(grep -m1 "^tier:" "$REPO_ROOT/$f" 2>/dev/null | awk '{print $2}')
    case "$tier" in
      1|2|3) ;;
      *)
        echo "🔴 RULE 11 FAIL: $f missing or invalid 'tier:' frontmatter (got: '${tier:-<empty>}')"
        echo "   Required: tier: 1 | 2 | 3"
        echo "   Convention: pages/skills/_gbrain/TIER-CONVENTION.md"
        echo "   Bypass (emergency only): git commit --no-verify"
        exit 1
        ;;
    esac
  done <<< "$TIER_TRIGGER"
fi

exit 0
