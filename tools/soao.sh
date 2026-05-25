#!/bin/bash
# soao.sh — Session-Open Atomic Opener
#
# Bundles the invariant session-open protocol from `audit` AP-18 + AP-17 into
# one command. Runs 8 points in order; prints ✅/🟡/🔴 per point; never aborts
# on a failed probe (AP-17: "run all checks, report all results").
#
#   0. AP-18 bash cwd probe — `.git/HEAD` readable (session 49-bis 2026-04-19)
#   1. 3 local gates (CLAUDE.md HARD RULES): website lock, code/satory trap, memory symlink
#   2. 4-way HEAD parity: Mac wiki = VPS bare = VPS wiki = Air wiki
#   3. 5 hook MD5s: pre-commit 4-target + pre-push + pre-receive + TaskCompleted
#   4. 3 structural scanners: version parity + md5 citations + LESSON=129
#   5. Factory skillsSnapshot: version + skills count
#   6. gbrain health: embed coverage + missing + dead links + brain score
#   7. (session-51+: AP-19 two-tier Open-Questions scan — deferred pending BS8 ship)
#
# Exit codes:
#   0 = all green
#   1 = yellow (non-blocking warnings only)
#   2 = red (blocking failure — do NOT proceed with work before fixing)
#
# Usage:
#   bash tools/soao.sh              # full report
#   bash tools/soao.sh --quiet      # exit code only
#   bash tools/soao.sh --skip-ssh   # skip remote probes (Air/VPS unreachable)
#
# Source: codified in `audit` SKILL.md AP-17 (session 49) + AP-18 (session 49-bis, revised session 50).

set -u
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
QUIET=0
SKIP_SSH=0
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=1 ;;
    --skip-ssh) SKIP_SSH=1 ;;
  esac
done
AIR_LOCAL=0
if [ "${SESSION_FORCE_AIR_LOCAL:-0}" = "1" ] || { hostname 2>/dev/null | grep -qi 'air' && [ "${SESSION_FORCE_REMOTE:-0}" != "1" ]; }; then
  AIR_LOCAL=1
fi

RED=0
YELLOW=0

log() { [ "$QUIET" -eq 1 ] || echo "$@"; }

log "=== SOAO @ $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
log "VAULT: $VAULT"
log ""

# --- 0. AP-18 bash cwd probe ---
log "--- 0. AP-18 bash cwd probe ---"
if [ -r "$VAULT/.git/HEAD" ]; then
  log "✅ bash alive; vault .git/HEAD readable"
else
  log "🔴 AP-18 FAIL: $VAULT/.git/HEAD unreadable. Bash may be sandboxed, cwd stale, or vault broken."
  log "   Verify with: Glob '$VAULT/*' (zero matches = really gone) + Read '$VAULT/CLAUDE.md' (access denied vs missing)."
  log "   Restart command: cd '$VAULT' && claude"
  RED=$((RED+1))
fi

# --- 1. 3 local gates ---
log ""
log "--- 1. 3 local gates (CLAUDE.md HARD RULES) ---"
CURRENT_JS=$(curl -s -m 10 "https://satory.nousagaas.com/" 2>/dev/null | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1)
if [ "$CURRENT_JS" = "index-BSiWURaO.js" ]; then
  log "✅ website lock: index-BSiWURaO.js (LAW-016)"
else
  log "🔴 website lock FAIL: $CURRENT_JS — restore: npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com"
  RED=$((RED+1))
fi

if [ ! -d "$VAULT/code/satory" ]; then
  log "✅ no code/satory trap (LESSON-076)"
else
  log "🔴 code/satory trap present — DELETE: rm -rf '$VAULT/code/satory'"
  RED=$((RED+1))
fi

SYMLINK=$(readlink "$HOME/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory" 2>/dev/null)
if echo "$SYMLINK" | grep -q "claude-memory"; then
  log "✅ memory symlink intact (LAW-005)"
else
  log "🔴 memory symlink broken: $SYMLINK"
  RED=$((RED+1))
fi

# --- 2. 4-way HEAD parity ---
log ""
log "--- 2. 4-way HEAD parity ---"
MAC_HEAD=$(cd "$VAULT" && git rev-parse --short HEAD 2>/dev/null)
log "Mac vault:   $MAC_HEAD"
if [ "$SKIP_SSH" -eq 1 ]; then
  log "🟡 --skip-ssh set; remote probes skipped"
  YELLOW=$((YELLOW+1))
else
  if [ "$AIR_LOCAL" -eq 1 ]; then
    AIR_HEAD="$MAC_HEAD"
  else
    AIR_HEAD=$(ssh -o ConnectTimeout=10 air "cd ~/nous-agaas/wiki && git rev-parse --short HEAD" 2>/dev/null)
  fi
  VPS_BARE=$(ssh -o ConnectTimeout=10 root@65.108.215.200 "cd /root/nous-agaas/obsidian-wiki.git && git rev-parse --short HEAD" 2>/dev/null)
  VPS_WIKI=$(ssh -o ConnectTimeout=10 root@65.108.215.200 "cd /root/nous-agaas/wiki && git rev-parse --short HEAD" 2>/dev/null)
  log "Air wiki:    ${AIR_HEAD:-unreachable}"
  log "VPS bare:    ${VPS_BARE:-unreachable}"
  log "VPS wiki:    ${VPS_WIKI:-unreachable}"
  if [ -n "$MAC_HEAD" ] && [ "$MAC_HEAD" = "$AIR_HEAD" ] && [ "$AIR_HEAD" = "$VPS_BARE" ] && [ "$VPS_BARE" = "$VPS_WIKI" ]; then
    log "✅ 4-way GOLDEN at $MAC_HEAD"
  else
    log "🟡 DRIFT — let auto-sync catch up (≤5 min) or force pull on laggers"
    YELLOW=$((YELLOW+1))
  fi
fi

# --- 3. 5 hook MD5s ---
log ""
log "--- 3. 5 hook MD5s ---"
CANON_MD5=$(md5 -q "$VAULT/tools/pre-commit-hook-tan-pattern.sh" 2>/dev/null)
MAC_PC=$(md5 -q "$VAULT/.git/hooks/pre-commit" 2>/dev/null)
log "pre-commit canon: $CANON_MD5"
log "pre-commit Mac:   $MAC_PC"
if [ -n "$CANON_MD5" ] && [ "$CANON_MD5" = "$MAC_PC" ]; then
  log "✅ pre-commit Mac ↔ canon match"
else
  log "🔴 pre-commit Mac ≠ canon — copy: cp tools/pre-commit-hook-tan-pattern.sh .git/hooks/pre-commit"
  RED=$((RED+1))
fi
if [ "$SKIP_SSH" -eq 0 ]; then
  if [ "$AIR_LOCAL" -eq 1 ]; then
    AIR_PC="$MAC_PC"
  else
    AIR_PC=$(ssh -o ConnectTimeout=10 air "md5 -q ~/nous-agaas/wiki/.git/hooks/pre-commit 2>/dev/null" 2>/dev/null)
  fi
  VPS_PC=$(ssh -o ConnectTimeout=10 root@65.108.215.200 "md5sum /root/nous-agaas/wiki/.git/hooks/pre-commit 2>/dev/null | awk '{print \$1}'" 2>/dev/null)
  log "pre-commit Air:   ${AIR_PC:-unreachable}"
  log "pre-commit VPS:   ${VPS_PC:-unreachable}"
  if [ "$CANON_MD5" = "$AIR_PC" ] && [ "$AIR_PC" = "$VPS_PC" ]; then
    log "✅ pre-commit 4-target GOLDEN"
  else
    log "🔴 pre-commit 4-target DRIFT"
    RED=$((RED+1))
  fi
fi
MAC_PP=$(md5 -q "$VAULT/.git/hooks/pre-push" 2>/dev/null || echo missing)
MAC_TC=$(md5 -q "$HOME/.claude/hooks/task-completed-enforce.sh" 2>/dev/null || echo missing)
log "pre-push Mac:        $MAC_PP"
log "TaskCompleted hook:  $MAC_TC"
[ "$MAC_PP" = "missing" ] && { log "🟡 pre-push hook missing"; YELLOW=$((YELLOW+1)); }
[ "$MAC_TC" = "missing" ] && { log "🟡 TaskCompleted hook missing"; YELLOW=$((YELLOW+1)); }

# --- 4. 3 structural scanners ---
log ""
log "--- 4. 3 structural scanners ---"
if bash "$VAULT/tools/test_skill_version_parity.sh" --quiet 2>/dev/null; then
  log "✅ test_skill_version_parity (AP-43 + AP-46 + AP-48)"
else
  log "🔴 test_skill_version_parity FAIL — run without --quiet for details"
  RED=$((RED+1))
fi
if bash "$VAULT/tools/test_skill_md5_citations.sh" --quiet 2>/dev/null; then
  log "✅ test_skill_md5_citations (AP-44)"
else
  log "🔴 test_skill_md5_citations FAIL — run without --quiet for details"
  RED=$((RED+1))
fi
LESSON_COUNT=$(ls "$VAULT"/pages/lessons/individual/LESSON-*.md 2>/dev/null | wc -l | tr -d ' ')
# RULE ZERO: 129 is the CEILING (no new LESSONs above 129), not the floor.
# Existing LESSONs may be edited (drift correction) or deleted (migration to
# gbrain timelines). s73-mac-44586 (2026-04-25) fixed this from `==129` to
# `<=129`; bulk deletion at 16:28 surfaced the false-positive class.
LESSON_HIGHEST_ID=$(ls "$VAULT"/pages/lessons/individual/LESSON-*.md 2>/dev/null | sed -E 's/.*LESSON-0*([0-9]+)-.*/\1/' | sort -n | tail -1)
if [ -n "$LESSON_HIGHEST_ID" ] && [ "$LESSON_HIGHEST_ID" -gt 129 ] 2>/dev/null; then
  log "🔴 LESSON id $LESSON_HIGHEST_ID > 129 — RULE ZERO ceiling breach, investigate!"
  RED=$((RED+1))
elif [ "$LESSON_COUNT" -le 129 ] 2>/dev/null; then
  log "✅ LESSON count $LESSON_COUNT ≤ 129 (RULE ZERO ceiling intact)"
else
  log "🔴 LESSON count = $LESSON_COUNT > 129 — RULE ZERO violation, investigate!"
  RED=$((RED+1))
fi

# --- 4c. 3 library-grade scanners (core Tier-A1 gate; gbrain-ops AP-67/AP-76) ---
log ""
log "--- 4c. 3 library-grade scanners (gbrain-ops AP-67/AP-76, core Tier-A1) ---"
if python3 "$VAULT/tools/library_reachability_scan.py" >/dev/null 2>&1; then
  log "✅ library_reachability_scan (Tier-A1 orphan rate ≤10%)"
else
  log "🔴 library_reachability_scan FAIL — run without redirect for details"
  RED=$((RED+1))
fi
if python3 "$VAULT/tools/library_canonical_scan.py" >/dev/null 2>&1; then
  log "✅ library_canonical_scan (Tier-A dup titles ≤2 / dup content ≤2 / aliases 0)"
else
  log "🔴 library_canonical_scan FAIL — run without redirect for details"
  RED=$((RED+1))
fi
if python3 "$VAULT/tools/library_crossref_scan.py" >/dev/null 2>&1; then
  log "✅ library_crossref_scan (Tier-A1 broken wikilinks 0 / broken prose AP ≤5)"
else
  log "🔴 library_crossref_scan FAIL — run without redirect for details"
  RED=$((RED+1))
fi

# --- 4b. 5 sibling probes (AP-49 + AP-7 + Rule-16 + top-CTO wiring gates) ---
log ""
log "--- 4b. 5 sibling probes (AP-49 + AP-7 + Rule-16 + top-CTO) ---"
if [ "$SKIP_SSH" -eq 0 ]; then
  if bash "$VAULT/tools/test_air_live_hook_parity.sh" --quiet 2>/dev/null; then
    log "✅ test_air_live_hook_parity (AP-49 — E1-class drift)"
  else
    RC=$?
    if [ "$RC" = "2" ]; then
      log "🔴 test_air_live_hook_parity FAIL — Mac ↔ Air hook MD5 drift; run without --quiet"
      RED=$((RED+1))
    else
      log "🟡 test_air_live_hook_parity warn — hook missing on one side; run without --quiet"
      YELLOW=$((YELLOW+1))
    fi
  fi
else
  log "🟡 --skip-ssh set; Air-hook-parity probe skipped"
  YELLOW=$((YELLOW+1))
fi

if bash "$VAULT/tools/test_claude_md_parity.sh" --quiet 2>/dev/null; then
  log "✅ test_claude_md_parity (AP-49 — Probe-B-class drift)"
else
  log "🔴 test_claude_md_parity FAIL — Mac-root ↔ vault CLAUDE.md pointer drift; run without --quiet"
  RED=$((RED+1))
fi

if bash "$VAULT/tools/test_memory_top_block_size.sh" --quiet 2>/dev/null; then
  log "✅ test_memory_top_block_size (AP-7 — MEMORY.md bounded)"
else
  RC=$?
  if [ "$RC" = "2" ]; then
    log "🔴 test_memory_top_block_size FAIL — top-block >100 lines OR total >800; extract + archive"
    RED=$((RED+1))
  else
    log "🟡 test_memory_top_block_size warn — approaching cap; next prepend should extract"
    YELLOW=$((YELLOW+1))
  fi
fi

# test_memory_version_claims — SOC Rule 16 / AP-10 (session 56). Non-blocking
# YELLOW until ≥5 real MEMORY prepends validate false-positive rate (the
# segment-divider regex is BSD-grep dependent + MEMORY narrative style may
# shift). Graduates to RED after session-61+ if stable.
if bash "$VAULT/tools/test_memory_version_claims.sh" --quiet 2>/dev/null; then
  log "✅ test_memory_version_claims (SOC Rule 16 — MEMORY-claim↔disk)"
else
  log "🟡 test_memory_version_claims warn — MEMORY top-block claims ≠ disk frontmatter/H1/Timeline; run without --quiet for mismatched triplet. Non-blocking while FP rate assessed."
  YELLOW=$((YELLOW+1))
fi

if bash "$VAULT/tools/test_top_cto_loop_wired.sh" >/dev/null 2>&1; then
  log "✅ test_top_cto_loop_wired (SOC Rule 20 + karpathy-loop top-CTO/spec-source + four-session handshake + RESOLVER)"
else
  log "🔴 test_top_cto_loop_wired FAIL — top-CTO doctrine not reachable from SOC/Karpathy/session-coordination/RESOLVER"
  RED=$((RED+1))
fi

# --- 5. Factory skillsSnapshot ---
log ""
log "--- 5. Factory skillsSnapshot ---"
if [ "$SKIP_SSH" -eq 1 ]; then
  log "🟡 --skip-ssh set; factory probe skipped"
  YELLOW=$((YELLOW+1))
else
  if [ "$AIR_LOCAL" -eq 1 ]; then
    SS_OUT=$(docker exec openclaw python3 -c "
import json
d = json.load(open(\"/home/node/.openclaw/agents/nous/sessions/sessions.json\"))
s = d[\"agent:nous:main\"][\"skillsSnapshot\"]
v = s.get(\"version\"); n = len(s.get(\"skills\", []))
print(\"version:\", v, \"skills:\", n)
" 2>/dev/null)
  else
    SS_OUT=$(ssh -o ConnectTimeout=10 air 'docker exec openclaw python3 -c "
import json
d = json.load(open(\"/home/node/.openclaw/agents/nous/sessions/sessions.json\"))
s = d[\"agent:nous:main\"][\"skillsSnapshot\"]
v = s.get(\"version\"); n = len(s.get(\"skills\", []))
print(\"version:\", v, \"skills:\", n)
" 2>/dev/null' 2>/dev/null)
  fi
  if echo "$SS_OUT" | grep -q "version:"; then
    log "$SS_OUT"
    SS_VER=$(echo "$SS_OUT" | awk '{print $2}')
    SS_N=$(echo "$SS_OUT" | awk '{print $4}')
    # Expected = live count of SKILL.md across Nous-skills + tenant-skills in this vault.
    # Session-59 fix: hardcoded "expected 27" was stale after tenant-skills landed (session-57);
    #   vault is the source of truth; factory ± a small tolerance for in-flight additions.
    VAULT_SKILLS=$(find "$VAULT/pages/skills" "$VAULT"/pages/tenants/*/skills -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    TOLERANCE=3
    MIN_EXPECTED=$((VAULT_SKILLS - TOLERANCE))
    [ "$MIN_EXPECTED" -lt 20 ] && MIN_EXPECTED=20
    if [ "${SS_N:-0}" -lt "$MIN_EXPECTED" ]; then
      log "🔴 skills count ${SS_N} < ${MIN_EXPECTED} (vault=${VAULT_SKILLS} tolerance=${TOLERANCE}) — factory missed rebuild or lost skills"
      RED=$((RED+1))
    elif [ "${SS_N:-0}" -lt "$VAULT_SKILLS" ] && [ "$SS_VER" = "0" ]; then
      log "🟡 skills count = ${SS_N} < vault=${VAULT_SKILLS} (within tolerance ${TOLERANCE}) + version=0 — likely in-flight addition; bump via tools/bump_openclaw_skills_version.sh if this persists"
      YELLOW=$((YELLOW+1))
    else
      log "✅ skillsSnapshot healthy (version=$SS_VER; ${SS_N} skills loaded; vault=${VAULT_SKILLS})"
    fi
  else
    log "🔴 factory unreachable — docker on Air may be down (run: ssh air 'open -a \"Docker Desktop\"'; wait 60s)"
    RED=$((RED+1))
  fi
fi

# --- 6. gbrain health ---
log ""
log "--- 6. gbrain health ---"
if [ "$SKIP_SSH" -eq 1 ]; then
  log "🟡 --skip-ssh set; gbrain probe skipped"
  YELLOW=$((YELLOW+1))
else
  GB_OUT=$(ssh -o ConnectTimeout=15 root@65.108.215.200 "cd /opt/nous-agaas/gbrain && timeout 20 bin/gbrain doctor 2>/dev/null" 2>/dev/null)
  if [ -n "$GB_OUT" ]; then
    SCORE=$(echo "$GB_OUT" | grep -Eo 'Health score: [0-9]+' | grep -Eo '[0-9]+' | head -1)
    PAGES=$(echo "$GB_OUT" | grep -Eo 'Connected, [0-9]+ pages' | grep -Eo '[0-9]+' | head -1)
    MISSING=$(echo "$GB_OUT" | grep -Eo '[0-9]+ missing' | grep -Eo '[0-9]+' | head -1)
    log "pages: ${PAGES:-?} | missing_embeddings: ${MISSING:-?} | health: ${SCORE:-?}/100"
    if [ -n "$SCORE" ] && [ "$SCORE" -ge 80 ]; then
      log "✅ gbrain health ≥ 80"
    else
      log "🟡 gbrain health = ${SCORE:-unknown} (expected ≥ 80)"
      YELLOW=$((YELLOW+1))
    fi
    if [ "${MISSING:-0}" = "0" ]; then
      log "✅ zero missing embeddings"
    else
      log "🟡 ${MISSING} missing embeddings — next autopilot cycle should clear"
      YELLOW=$((YELLOW+1))
    fi
  else
    log "🟡 gbrain doctor unreachable (VPS SSH or gbrain bin issue)"
    YELLOW=$((YELLOW+1))
  fi
fi

# --- 7. AP-19 (deferred, Open-Questions doctrine pending BS8) ---
log ""
log "--- 7. AP-19 (Open-Questions two-tier scan) ---"
log "⏳ deferred: AP-19 awaits BS8 approval on SPEC-OPEN-QUESTIONS-DOCTRINE-V1-2026-04-19 (no warning, planned work)"

# --- 8. Parallel-session scan (session-coordination v1) ---
log ""
log "--- 8. Parallel-session scan (session-coordination v1) ---"
if [ -x "$VAULT/tools/session_scan.sh" ]; then
  SCAN_OUT=$(bash "$VAULT/tools/session_scan.sh" 2>&1 || echo "  ⏭ session_scan failed (Air unreachable?)")
  log "$SCAN_OUT"
  if echo "$SCAN_OUT" | grep -q "🟡"; then
    YELLOW=$((YELLOW+1))
  fi
else
  log "  ⏭ session_scan.sh not yet shipped (session-coordination v1 deferred)"
fi

# --- 9. Revenue freshness (SOC Rule 22 mechanical detector, s108-mac-99667 2026-04-30) ---
# Surfaces today_events / events_stale at session-start so substrate work
# never silently runs while the customer pipe is dead.
# Cached 5min in /tmp to avoid spamming VPS on rapid session-starts.
# Advisory print this iteration; promote to RED gate after validation.
log ""
log "--- 9. Revenue freshness (SOC Rule 22) ---"
FRESH_CACHE="/tmp/nous-revenue-freshness.cache"
FRESH_TTL=300
NOW_TS=$(date +%s)
if [ -f "$FRESH_CACHE" ]; then
  CACHE_TS=$(stat -f %m "$FRESH_CACHE" 2>/dev/null || stat -c %Y "$FRESH_CACHE" 2>/dev/null || echo 0)
  CACHE_AGE=$((NOW_TS - CACHE_TS))
else
  CACHE_AGE=999999
fi
if [ "$CACHE_AGE" -lt "$FRESH_TTL" ]; then
  FRESH_LINE=$(cat "$FRESH_CACHE")
  log "  📂 cached (${CACHE_AGE}s ago): $FRESH_LINE"
else
  FRESH_RAW=$(ssh -o ConnectTimeout=3 -o BatchMode=yes root@65.108.215.200 \
    'curl -sS -m 3 http://localhost:8090/api/health' 2>/dev/null || echo "")
  if [ -n "$FRESH_RAW" ]; then
    FRESH_LINE=$(echo "$FRESH_RAW" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    f = d.get('data_freshness', {})
    today = d.get('today_events', '?')
    stale = f.get('events_stale')
    last = f.get('events_last_seen', '?')
    age = f.get('events_age_seconds', 0) or 0
    days = age // 86400
    icon = '✅' if not stale else ('🔴' if days > 1 else '🟡')
    print(f'{icon} today_events={today} events_stale={stale} last={last} age={days}d')
except Exception as e:
    print(f'🟡 parse_error: {e}')
" 2>/dev/null)
    echo "$FRESH_LINE" > "$FRESH_CACHE"
    log "  $FRESH_LINE"
  else
    FRESH_LINE="🟡 unknown — VPS:8090 unreachable from session-start"
    log "  $FRESH_LINE"
  fi
fi
# Advisory bump only — promote to RED in next iteration after validation
if echo "$FRESH_LINE" | grep -q "🔴"; then
  YELLOW=$((YELLOW+1))
  log "  ⚠️  Rule 22: customer pipe dead. Read pages/dashboards/revenue-blockers.md before substrate work."
fi

# --- Summary ---
log ""
log "=== SOAO COMPLETE ==="
log "🔴 red: $RED | 🟡 yellow: $YELLOW"
if [ "$RED" -gt 0 ]; then
  log "❌ BLOCKING — fix red items before proceeding with work"
  exit 2
elif [ "$YELLOW" -gt 0 ]; then
  log "⚠️  non-blocking warnings — proceed but note above"
  exit 1
else
  log "✅ GOLDEN — proceed with work"
  exit 0
fi
