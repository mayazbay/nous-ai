#!/bin/bash
# TaskCompleted hook — deploy gate of last resort
#
# Enforces (ORIGINAL 4 gates, for product work):
#   GATE 1: LAW-006 — REQ-xxx mapping required
#   GATE 2: LAW-011 — business outcome tag required
#   GATE 3: App.tsx component wiring (for frontend tasks)
#   GATE 4: TSC baseline not exceeded (for frontend tasks)
#
# Enforces (NEW 4 gates 2026-04-08, for vault work, per AUDIT-026):
#   GATE 5: LAW-005 — vault committed (no unstaged/staged changes blocking sync)
#   GATE 6: LAW-005 — Mac HEAD linearly compatible with VPS HEAD (no divergent histories)
#   GATE 7: LAW-005 — log.md has an entry for today
#   GATE 8: LAW-015 (session-35 RULE ZERO) — bug-fix tasks require a SKILL.md update
#          or gbrain timeline entry in last 24h. New LESSON files FORBIDDEN since 2026-04-16.
#
# Exit 0 = allow, exit 2 = block (stderr msg shown to Claude)
#
# Task type detection:
#   PRODUCT_TASK  — implementation of VMS/ERAP/BDL features (fires Gates 1-4)
#   VAULT_TASK    — audit/lesson/doc/handoff/wiki/tool work (fires Gates 5-8)
#   BOTH          — a task can be both; gates are additive

set -u
INPUT=$(cat)

# Try jq, fall back to grep
if command -v jq >/dev/null 2>&1; then
  TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject // empty')
  TASK_DESC=$(echo "$INPUT"   | jq -r '.task_description // empty')
  TASK_ID=$(echo "$INPUT"     | jq -r '.task_id // empty')
else
  TASK_SUBJECT=$(echo "$INPUT" | grep -o '"task_subject":"[^"]*"' | head -1 | sed 's/.*"task_subject":"\(.*\)"/\1/')
  TASK_DESC=$(echo "$INPUT"    | grep -o '"task_description":"[^"]*"' | head -1 | sed 's/.*"task_description":"\(.*\)"/\1/')
  TASK_ID=$(echo "$INPUT"      | grep -o '"task_id":"[^"]*"' | head -1 | sed 's/.*"task_id":"\(.*\)"/\1/')
fi

ALL_TEXT="${TASK_SUBJECT} ${TASK_DESC}"
FAILURES=()
WARNINGS=()

# Vault location (Mac side)
VAULT_MAC="/Users/madia/Documents/Projects/Nous AGaaS/Nous"
VAULT_VPS_HOST="root@65.108.215.200"
VAULT_VPS_PATH="/root/nous-agaas/wiki"

# Task-type detection
IS_PRODUCT_TASK=false
IS_VAULT_TASK=false
IS_BUGFIX_TASK=false
IS_INFRASTRUCTURE_TASK=false

# ═══════════════════════════════════════════════════════════════
# INFRASTRUCTURE-CLASS OVERRIDE (session 51, 2026-04-20)
# ═══════════════════════════════════════════════════════════════
# Session-hygiene / carryover / skill-bump / hook-work / launchd tasks
# never have REQ-xxx + business tags — those are product-layer fields.
# Shape-based detection (task-id prefix, phase markers, infra keywords)
# takes precedence over word-level product/vault regex below, so a task
# like "C1: Backfill gbrain timeline for camera-management" doesn't get
# wrongly product-gated just because "camera" is in the subject.
#
# Skips Gates 1-4 (product). Keeps Gate 5 (LAW-005 committed),
# Gate 8 (bugfix→skill), Gate 9 (gbrain).
if echo "$TASK_SUBJECT" | grep -qiE '^(Phase\s+[A-Z0-9]+|[A-Z]+-?[A-Z0-9]+):' \
  || echo "$ALL_TEXT" | grep -qiE '\b(carryover|SOAO|session[- ][0-9]+[- ](open|close|handoff)|skill[- ]?bump|MEMORY[- ]?prepend|launchd|watchdog|sibling[- ]?test|task[- ]?hygiene|hook[- ]?install|mechanical[- ]?gate|preamble|routing model|context injection)\b' \
  || echo "$TASK_SUBJECT" | grep -qiE '\b(ship\s+tools/|install\s+~?/\.claude|bump_openclaw|skillsSnapshot|4-way|4-target|handoff|narrow HARD RULE|document.*CLAUDE\.md|/code.*inject)\b' \
  || echo "$ALL_TEXT" | grep -qiE '\b(musk[- ]?step|musk[- ]?algorithm|gap[- ]?list|hybrid[- ]?enforcement|recursive[- ]?musk|substrate[- ]?hygiene|Karpathy[- ]?6[- ]?axis|DONE[- ]?protocol|10%[- ]?add[- ]?back|AP-[0-9]+[- ]?codification|scorecard|lint|orphan|broken[- ]?link|wikilink|linter|wiki[- ]?health|FP[- ]?(rate|analysis)|peer[- ]?scope|coordination[- ]?narrow|gbrain[- ]?upgrade|substrate[- ]?awareness|wiki[- ]?lint)\b' ; then
  IS_INFRASTRUCTURE_TASK=true
fi

# Product-task detection: require DOMAIN-specific anchors (not generic action verbs).
# Generic words like "deploy|build|implement" are too promiscuous — they match operational
# vault work (e.g. "deploy pipeline", "implement skill absorption"). Only domain-specific
# words (VMS/ERAP/BDL/camera/violation/SmartBridge/ISAPI/cerebro/factory-work) qualify.
# AP-31 re-surface fix session-45 2026-04-17.
if echo "$ALL_TEXT" | grep -qiE '\b(VMS|ERAP|BDL|SmartBridge|ISAPI|cerebro|factory-work|police[_ -]?dashboard|violation|camera(s|[_ -](monitoring|event|registry|status|health))?)\b'; then
  IS_PRODUCT_TASK=true
fi

if echo "$ALL_TEXT" | grep -qiE '\b(audit|lesson|doc|handoff|wiki|vault|obsidian|law-|lesson-|audit-|tool|script|page|refactor|migrate|cleanup|tidy|skill|gbrain|pre-flight|phase\s+[0-9A-Z]|session-[0-9]|hook|root-cause|timeline|sync|check|health|service|launchd|status|parity|monitoring|verify|probe|liveness|readiness|heartbeat|MD5|plan|spec|resolver|rsync|ingest|embed|qmd|runtime|cron|gate|mandatory|atomic|symlink|website.lock|memory.symlink|tan.pattern|karpathy|rule.zero|rotate|token|revoke|keychain|credential|secrets?|coordinate|parallel|orchestrate|defer|carryover|close-audit|baseline|absorb|AP-[0-9]|ap-[0-9]|ap[0-9])\b'; then
  IS_VAULT_TASK=true
fi

if echo "$ALL_TEXT" | grep -qiE '\b(bug[- ]?fix|root[- ]?cause|resolved|regression|silent[- ]?failure|data[- ]?loss|fix[- ]a[- ]bug|patch[- ]?the)\b'; then
  IS_BUGFIX_TASK=true
  # Bugfix tasks are also vault tasks (because we always write LESSONs for bugs)
  IS_VAULT_TASK=true
fi

# Default: if unclassified, treat as product (preserves original hook behavior)
if [ "$IS_PRODUCT_TASK" = "false" ] && [ "$IS_VAULT_TASK" = "false" ]; then
  IS_PRODUCT_TASK=true
fi

# Infrastructure override: wins against product regex (but vault-gates still fire).
# Rationale: session 51 discovered C1/D2 etc. matched "camera" → product, wrongly
# firing Gates 1-4 on pure infrastructure work. The task SHAPE (B1:, Phase D, etc.)
# is a stronger signal than the vocabulary it uses.
if [ "$IS_INFRASTRUCTURE_TASK" = "true" ]; then
  IS_PRODUCT_TASK=false
  IS_VAULT_TASK=true
fi

# ═══════════════════════════════════════════════════════════════
# ORIGINAL GATES (Gates 1-4) — fire on product tasks
# ═══════════════════════════════════════════════════════════════

if [ "$IS_PRODUCT_TASK" = "true" ]; then

  # ── GATE 1: LAW-006 — REQ-xxx required ──────────────────────
  if ! echo "$ALL_TEXT" | grep -qiE 'REQ-[0-9]{1,3}'; then
    FAILURES+=("LAW-006 GATE 1: missing REQ-xxx mapping. Every product task must trace to a VMS/ERAP/BDL requirement.")
  fi

  # ── GATE 2: LAW-011 — business outcome tag required ─────────
  if ! echo "$ALL_TEXT" | grep -qiE '\[demo\]|\[revenue\]|\[risk\]|demo-ready|risk-reduction'; then
    FAILURES+=("LAW-011 GATE 2: missing business tag. Add [demo], [revenue], or [risk].")
  fi

  # ── GATE 3: components wired into App.tsx ───────────────────
  APP_TSX=""
  for candidate in \
    "/root/nous-agaas/codebase/satory-frontend/src/App.tsx" \
    "/Users/madia/Documents/Projects/Nous AGaaS/codebase/satory-frontend/src/App.tsx" \
    "/Users/madia/Documents/Projects/Nous AGaaS/satory-frontend/src/App.tsx" \
    "/root/nous-agaas/codebase/satory-frontend/satory-frontend/src/App.tsx" \
    "/Users/madia/Documents/Projects/Nous AGaaS/codebase/satory-frontend/satory-frontend/src/App.tsx"; do
    if [ -f "$candidate" ]; then
      APP_TSX="$candidate"
      break
    fi
  done

  if [ -n "$APP_TSX" ]; then
    COMPONENTS_DIR=$(dirname "$APP_TSX")/components
    if [ -d "$COMPONENTS_DIR" ]; then
      while IFS= read -r comp_file; do
        [ -z "$comp_file" ] && continue
        comp_name=$(basename "$comp_file" .tsx)
        case "$comp_name" in
          App|index|main) continue ;;
        esac
        if ! echo "$comp_name" | grep -qE 'Page$|View$|Modal$'; then
          continue
        fi
        if ! grep -q "$comp_name" "$APP_TSX"; then
          FAILURES+=("GATE 3 WIRING: ${comp_name}.tsx exists but not imported in App.tsx")
        elif ! grep -qE "<${comp_name}[[:space:]>/]" "$APP_TSX"; then
          FAILURES+=("GATE 3 WIRING: ${comp_name} imported but not rendered (no <${comp_name} ...> JSX)")
        fi
      done < <(find "$COMPONENTS_DIR" -maxdepth 2 -name '*.tsx' -mmin -60 2>/dev/null)
    fi
  fi

  # ── GATE 4: TSC baseline not exceeded ───────────────────────
  TSC_BASELINE=""
  for candidate in \
    "/root/nous-agaas/logs/tsc_baseline.txt" \
    "/Users/madia/Documents/Projects/Nous AGaaS/logs/tsc_baseline.txt"; do
    if [ -f "$candidate" ]; then
      TSC_BASELINE=$(cat "$candidate" 2>/dev/null | tr -d '[:space:]')
      break
    fi
  done

  if [ -n "$TSC_BASELINE" ] && [ -n "$APP_TSX" ]; then
    FRONTEND_DIR=$(dirname "$(dirname "$APP_TSX")")
    if [ -d "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ]; then
      CURRENT=$(cd "$FRONTEND_DIR" && timeout 90 npx tsc --noEmit 2>&1 | grep "error TS" | grep -v "__tests__" | wc -l | tr -d ' ')
      if [ -n "$CURRENT" ] && [ "$CURRENT" -gt "$TSC_BASELINE" ] 2>/dev/null; then
        DIFF=$((CURRENT - TSC_BASELINE))
        FAILURES+=("GATE 4 TSC: +${DIFF} new TypeScript errors (baseline=${TSC_BASELINE}, current=${CURRENT})")
      fi
    fi
  fi

fi  # end IS_PRODUCT_TASK

# ═══════════════════════════════════════════════════════════════
# NEW GATES (Gates 5-8) — fire on vault tasks per AUDIT-026
# ═══════════════════════════════════════════════════════════════

if [ "$IS_VAULT_TASK" = "true" ]; then

  # ── GATE 5: LAW-005 — vault committed? ───────────────────────
  # Hard block if vault has uncommitted changes (excluding .obsidian/ UI state
  # and .log files which are noise)
  if [ -d "$VAULT_MAC/.git" ]; then
    UNCOMMITTED=$(git -C "$VAULT_MAC" status --porcelain 2>/dev/null \
      | grep -vE '^\s*[MA?]+\s+\.obsidian/' \
      | grep -vE '^\s*[MA?]+\s+.*\.log$' \
      | grep -vE '^\s*[MA?]+\s+.*/logs?/' \
      | head -10)
    if [ -n "$UNCOMMITTED" ]; then
      FAIL_DETAIL=$(echo "$UNCOMMITTED" | head -5 | sed 's/^/      /')
      FAILURES+=("LAW-005 GATE 5: vault has uncommitted changes blocking sync:
${FAIL_DETAIL}
      Fix: cd \"${VAULT_MAC}\" && git add -A && git commit -m '<msg>' && git push vps main")
    fi
  fi

  # ── GATE 6: LAW-005 — Mac HEAD compatible with VPS HEAD? ────
  # Only fires if Gate 5 passed AND task mentions sync/deploy/push
  #
  # Cross-platform timeout: macOS has no `timeout` by default, so we use
  # perl's alarm() as a portable replacement. Works on both Mac and Linux.
  timeout_ssh() {
    local secs="$1"; shift
    perl -e '
      use strict; use warnings;
      my $secs = shift @ARGV;
      eval {
        local $SIG{ALRM} = sub { die "timeout\n" };
        alarm $secs;
        my $pid = open(my $fh, "-|", @ARGV) or die "fork: $!";
        my $out = do { local $/; <$fh> };
        close($fh);
        alarm 0;
        print $out;
        exit 0;
      };
      if ($@ eq "timeout\n") { exit 124; }
      die $@;
    ' "$secs" "$@" 2>/dev/null
  }

  if [ ${#FAILURES[@]} -eq 0 ] && echo "$ALL_TEXT" | grep -qiE '\b(sync|deploy|push|commit|merge)\b'; then
    MAC_HEAD=$(git -C "$VAULT_MAC" rev-parse HEAD 2>/dev/null || echo "NONE")
    VPS_HEAD=$(timeout_ssh 6 ssh -o ConnectTimeout=4 -o BatchMode=yes "$VAULT_VPS_HOST" "git -C $VAULT_VPS_PATH rev-parse HEAD 2>/dev/null")
    [ -z "$VPS_HEAD" ] && VPS_HEAD="UNREACHABLE"

    if [ "$MAC_HEAD" = "NONE" ]; then
      WARNINGS+=("LAW-005 GATE 6: no Mac vault HEAD found (not a git repo?)")
    elif [ "$VPS_HEAD" = "UNREACHABLE" ]; then
      WARNINGS+=("LAW-005 GATE 6: VPS unreachable (timeout/network). Skipping sync check. Manually verify sync when network returns.")
    elif [ "$MAC_HEAD" = "$VPS_HEAD" ]; then
      : # Pass — identical HEADs
    else
      # Check if one is ancestor of the other (temporal lag, auto-sync will converge)
      if git -C "$VAULT_MAC" merge-base --is-ancestor "$MAC_HEAD" "$VPS_HEAD" 2>/dev/null; then
        WARNINGS+=("LAW-005 GATE 6: Mac (${MAC_HEAD:0:7}) is ancestor of VPS (${VPS_HEAD:0:7}). Temporal lag, auto-sync will converge within 60s.")
      elif git -C "$VAULT_MAC" merge-base --is-ancestor "$VPS_HEAD" "$MAC_HEAD" 2>/dev/null; then
        WARNINGS+=("LAW-005 GATE 6: VPS (${VPS_HEAD:0:7}) is ancestor of Mac (${MAC_HEAD:0:7}). Push required: cd \"${VAULT_MAC}\" && git push vps main")
      else
        FAILURES+=("LAW-005 GATE 6: Mac (${MAC_HEAD:0:7}) and VPS (${VPS_HEAD:0:7}) have DIVERGENT histories. Manual merge required:
      cd \"${VAULT_MAC}\"
      git fetch vps main
      git merge -X theirs vps/main
      git push vps main")
      fi
    fi
  fi

  # ── GATE 7: LAW-005 — log.md entry for today? (WARN only) ───
  # Warn don't block, because not every vault task needs a log entry
  if echo "$ALL_TEXT" | grep -qiE '\b(fix|implement|deploy|audit|lesson|wrote|extend|refactor|migrate)\b'; then
    TODAY=$(date '+%Y-%m-%d')
    if [ -f "$VAULT_MAC/log.md" ]; then
      if ! grep -q "$TODAY" "$VAULT_MAC/log.md"; then
        WARNINGS+=("LAW-005 GATE 7: no log.md entry found for $TODAY. Consider adding:
      ## [$TODAY] <type> | <short summary>")
      fi
    fi
  fi

  # ── GATE 8: LAW-015 + session-35 RULE ZERO — bug-fix requires skill update ──
  # Hard block for explicit bug-fix tasks with no SKILL.md update in last 24h.
  # NEW LESSON files are FORBIDDEN (pre-commit hook rejects them since 2026-04-16).
  # Root cause now captured as: SKILL.md edit + gbrain timeline entry.
  if [ "$IS_BUGFIX_TASK" = "true" ]; then
    if [ -d "$VAULT_MAC/.git" ]; then
      RECENT_SKILL_UPDATES=$(git -C "$VAULT_MAC" log --since="1 day ago" --name-only 2>/dev/null \
        | grep -c 'pages/skills/[^/]*/SKILL\.md')
      if [ "$RECENT_SKILL_UPDATES" -eq 0 ]; then
        FAILURES+=("LAW-015 GATE 8 (session-35 RULE ZERO): bug-fix task requires a SKILL.md update in the last 24h. Update pages/skills/<skill>/SKILL.md (new AP/rule/phase), bump version, append Timeline entry, add mcp__gbrain__add_timeline_entry. DO NOT create new LESSON files — pre-commit hook rejects them.")
      fi
    fi
  fi

fi  # end IS_VAULT_TASK

# ═══════════════════════════════════════════════════════════════
# GATE 9 (ALL tasks): GBrain lesson check — AUDIT-030
# Was GBrain queried for related lessons/mistakes before acting?
# This prevents repeating the same mistake twice.
# ═══════════════════════════════════════════════════════════════

# Check if gbrain is reachable and has related lessons
GBRAIN_AVAILABLE=false
if command -v ssh >/dev/null 2>&1; then
  GBRAIN_CHECK=$(timeout_ssh 8 ssh -o ConnectTimeout=4 -o BatchMode=yes "$VAULT_VPS_HOST" \
    "export DATABASE_URL='postgresql://gbrain:gbrain2026@localhost:5432/gbrain' && /opt/nous-agaas/gbrain/bin/gbrain search 'LESSON ${TASK_SUBJECT}' 2>/dev/null | head -3" 2>/dev/null || echo "")
  if [ -n "$GBRAIN_CHECK" ]; then
    GBRAIN_AVAILABLE=true
    # Check if any lessons were found. grep -c prints "0" AND exits 1 when no
    # matches, so `|| echo 0` would produce "0\n0" and break [ -gt 0 ] downstream.
    # Use head -1 to collapse, strip whitespace, default to 0 if empty.
    LESSON_HITS=$(echo "$GBRAIN_CHECK" | grep -c "lesson" 2>/dev/null | head -1 | tr -d '[:space:]')
    LESSON_HITS=${LESSON_HITS:-0}
    if [ "$LESSON_HITS" -gt 0 ] 2>/dev/null; then
      WARNINGS+=("GATE 9 GBRAIN: Found ${LESSON_HITS} related lesson(s) in GBrain. Make sure you checked them BEFORE acting:
${GBRAIN_CHECK}")
    fi
  else
    WARNINGS+=("GATE 9 GBRAIN: Could not reach GBrain to check for related lessons. Verify manually.")
  fi
fi

# ═══════════════════════════════════════════════════════════════
# Output results
# ═══════════════════════════════════════════════════════════════

# Print warnings even if we're going to pass
if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo "" >&2
  echo "TaskCompleted WARN for task '${TASK_SUBJECT}' (id=${TASK_ID}):" >&2
  for w in "${WARNINGS[@]}"; do
    echo "  ⚠ $w" >&2
  done
fi

# Hard block on failures
if [ ${#FAILURES[@]} -gt 0 ]; then
  echo "" >&2
  echo "TaskCompleted BLOCKED for task '${TASK_SUBJECT}' (id=${TASK_ID})" >&2
  echo "" >&2
  for f in "${FAILURES[@]}"; do
    echo "  ✗ $f" >&2
  done
  echo "" >&2
  echo "Fix the issues above and mark complete again." >&2
  echo "Audit reference: AUDIT-026 (the extended hook spec)" >&2
  exit 2
fi

exit 0
