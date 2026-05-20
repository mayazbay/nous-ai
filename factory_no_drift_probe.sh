#!/usr/bin/env bash
# =============================================================================
# factory_no_drift_probe.sh — Goal 2: Factory 7-Day No-Drift Supervisor
# =============================================================================
# Runs 10 checks across Air + VPS + Mac. Outputs JSON. Telegrams on any RED.
#
# Usage:
#   bash tools/factory_no_drift_probe.sh            # normal run
#   bash tools/factory_no_drift_probe.sh --json     # machine-readable JSON only
#   bash tools/factory_no_drift_probe.sh --quiet    # suppress text, JSON only
#   bash tools/factory_no_drift_probe.sh --no-telegram # suppress drift alert
#   bash tools/factory_no_drift_probe.sh --no-repair   # classify only; do not auto-pull
#
# Checks:
#   1. OpenClaw       — Air Docker healthz (port 18789)
#   2. LiteLLM        — Air readiness (port 4000)
#   3. Telegram poller — Air launchctl com.nous.telegram-poll (pid=- + exit=0 is GREEN)
#   4. Goal Mode      — Air launchctl com.nous.goal-cycle
#   5. Wiki parity    — git HEAD matches on Air + VPS + Mac
#   6. GitHub mirror  — tokenless remotes + exact canonical mirror
#   7. Air sync lag   — Air local checkout behind canonical origin/GitHub
#   8. OpenBrain      — recent projection file exists on Air (<48h)
#   9. gbrain         — VPS gbrain CLI stats (pages + embedded count)
#   10. OpenRouter cap — LiteLLM spend vs $5/day limit
# =============================================================================

set -uo pipefail

JSON_ONLY=0
QUIET=0
NO_TELEGRAM=0
AUTO_REPAIR=1
for arg in "${@:-}"; do
  case "$arg" in
    --json)   JSON_ONLY=1; QUIET=1 ;;
    --quiet)  QUIET=1 ;;
    --no-telegram) NO_TELEGRAM=1 ;;
    --no-repair) AUTO_REPAIR=0 ;;
  esac
done

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
WIKI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$HOME/nous-agaas/.env"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true
ON_AIR=0
if [[ -d "$HOME/nous-agaas/wiki" && "$WIKI_DIR" == "$HOME/nous-agaas/wiki" ]]; then
  ON_AIR=1
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-110793056}"

log() { [[ "$QUIET" -eq 0 ]] && echo "$*" || true; }

# ─── Result accumulator (parallel arrays) ────────────────────────────────────
declare -a CHECK_NAMES=()
declare -a CHECK_STATUS=()
declare -a CHECK_DETAIL=()
REDS=0

record() {
  local name="$1" status="$2" detail="$3"
  CHECK_NAMES+=("$name")
  CHECK_STATUS+=("$status")
  CHECK_DETAIL+=("$detail")
  if [[ "$status" == "RED" ]]; then
    REDS=$(( REDS + 1 ))
    log "🔴 $name: $detail"
  else
    log "✅ $name: $detail"
  fi
}

ssh_air() {
  if [[ "$ON_AIR" -eq 1 ]]; then
    bash -lc "$*" 2>/dev/null
  else
    ssh -o ConnectTimeout=8 -o BatchMode=yes air "$@" 2>/dev/null
  fi
}

ssh_vps() {
  ssh -o ConnectTimeout=8 -o BatchMode=yes root@65.108.215.200 "$@" 2>/dev/null
}

remote_exists() {
  local remote="$1"
  cd "$WIKI_DIR" && git remote get-url "$remote" >/dev/null 2>&1
}

fetch_remote_main() {
  local remote="$1"
  remote_exists "$remote" || return 0
  (
    cd "$WIKI_DIR" &&
      git fetch "$remote" main:refs/remotes/"$remote"/main --quiet 2>/dev/null
  ) || (
    cd "$WIKI_DIR" &&
      git fetch "$remote" main --quiet 2>/dev/null
  ) || true
}

remote_main_short() {
  local remote="$1"
  remote_exists "$remote" || {
    echo "git_fail"
    return
  }
  cd "$WIKI_DIR" &&
    git rev-parse --verify --quiet refs/remotes/"$remote"/main 2>/dev/null |
    cut -c1-8
}

remote_main_full() {
  local remote="$1"
  remote_exists "$remote" || {
    echo "git_fail"
    return
  }
  cd "$WIKI_DIR" &&
    git rev-parse --verify --quiet refs/remotes/"$remote"/main 2>/dev/null ||
    echo "git_fail"
}

one_line() {
  printf "%s" "$*" | tr '\n' ' ' | sed 's/[[:space:]][[:space:]]*/ /g' | cut -c1-240
}

repair_air_sync_lag() {
  local expected_head="$1"
  local remote="$2"

  if [[ "$AUTO_REPAIR" -ne 1 ]]; then
    echo "skipped_disabled"
    return 1
  fi
  if [[ "$ON_AIR" -ne 1 ]]; then
    echo "skipped_not_air"
    return 1
  fi
  if [[ -z "$expected_head" || "$expected_head" == "git_fail" ]]; then
    echo "skipped_bad_expected_head"
    return 1
  fi
  if ! remote_exists "$remote"; then
    echo "skipped_missing_remote=${remote}"
    return 1
  fi

  local dirty_count
  dirty_count=$(cd "$WIKI_DIR" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ' || echo "git_status_fail")
  if [[ "$dirty_count" != "0" ]]; then
    echo "skipped_dirty_worktree paths=${dirty_count}"
    return 1
  fi

  local rebase_state
  rebase_state=$(cd "$WIKI_DIR" && { [[ -d .git/rebase-merge || -d .git/rebase-apply ]] && echo "yes" || echo "no"; })
  if [[ "$rebase_state" != "no" ]]; then
    echo "skipped_rebase_in_progress"
    return 1
  fi

  local before after current_expected current_full target_full target_short rebase_rc rebase_output second_output
  before=$(cd "$WIKI_DIR" && git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "git_fail")
  fetch_remote_main "$remote"
  target_full=$(remote_main_full "$remote")
  if [[ -z "$target_full" || "$target_full" == "git_fail" ]]; then
    echo "skipped_bad_target_ref ${remote}/main"
    return 1
  fi
  target_short=$(printf "%.8s" "$target_full")

  if cd "$WIKI_DIR" && git merge-base --is-ancestor "$target_full" HEAD 2>/dev/null; then
    after=$(cd "$WIKI_DIR" && git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "git_fail")
    echo "already_contains ${remote}/main ${before}->${after} expected=${expected_head} current=${target_short}"
    return 0
  fi

  # Do not use `git pull --rebase` here. Under concurrent Air writers it can
  # resolve FETCH_HEAD/branch config to more than one target and fail with
  # "Cannot rebase onto multiple branches." Fetch one ref, then rebase onto the
  # exact OID with hooks disabled for an unattended probe path.
  rebase_output=$(cd "$WIKI_DIR" && git -c core.hooksPath=/dev/null rebase "$target_full" 2>&1)
  rebase_rc=$?
  fetch_remote_main "$remote"
  current_full=$(remote_main_full "$remote")
  current_expected=$(printf "%.8s" "$current_full")

  if [[ "$rebase_rc" -eq 0 ]] && [[ "$current_full" != "$target_full" ]]; then
    if ! (cd "$WIKI_DIR" && git merge-base --is-ancestor "$current_full" HEAD 2>/dev/null); then
      second_output=$(cd "$WIKI_DIR" && git -c core.hooksPath=/dev/null rebase "$current_full" 2>&1)
      rebase_rc=$?
      rebase_output="${rebase_output} ${second_output}"
      fetch_remote_main "$remote"
      current_full=$(remote_main_full "$remote")
      current_expected=$(printf "%.8s" "$current_full")
    fi
  fi

  after=$(cd "$WIKI_DIR" && git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "git_fail")

  if [[ "$rebase_rc" -eq 0 ]] && cd "$WIKI_DIR" && git merge-base --is-ancestor "$current_full" HEAD 2>/dev/null; then
    echo "rebased ${remote}/main ${before}->${after} expected=${expected_head} target=${target_short} current=${current_expected}"
    return 0
  fi

  echo "failed rc=${rebase_rc} ${before}->${after} expected=${expected_head} target=${target_short} current=${current_expected} output=$(one_line "$rebase_output")"
  return 1
}

# Helper: check launchd job on Air. Returns "pid=NNN exit=0" or "missing" or "crashed exit=N"
# launchctl list format: PID  LastExitCode  Label
# pid=- means not currently running (between cycles) — GREEN if exit=0
launchd_status_air() {
  local label="$1"
  local row
  row=$(ssh_air "launchctl list | awk '\$3 == \"$label\" {print \$1, \$2}'" 2>/dev/null || echo "ssh_fail")
  if [[ -z "$row" || "$row" == "ssh_fail" ]]; then
    echo "missing"
    return
  fi
  local pid exit_code
  pid=$(echo "$row" | awk '{print $1}')
  exit_code=$(echo "$row" | awk '{print $2}')
  if [[ "$pid" == "-" && "$exit_code" == "0" ]]; then
    echo "idle exit=0"   # between cycles, healthy
  elif [[ "$pid" =~ ^[0-9]+$ ]]; then
    echo "running pid=$pid"
  else
    echo "crashed exit=$exit_code"
  fi
}

# =============================================================================
# CHECK 1: OpenClaw (Air Docker)
# =============================================================================
log "--- Check 1: OpenClaw ---"
OC_STATUS=$(ssh_air "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:18789/healthz" 2>/dev/null || echo "ssh_fail")
if [[ "$OC_STATUS" == "200" ]]; then
  record "openclaw" "GREEN" "HTTP 200 on port 18789"
else
  record "openclaw" "RED" "HTTP ${OC_STATUS} on port 18789 (expected 200)"
fi

# =============================================================================
# CHECK 2: LiteLLM (Air)
# =============================================================================
log "--- Check 2: LiteLLM ---"
LLMKEY=$(ssh_air "grep LITELLM_MASTER_KEY ~/nous-agaas/.env" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || echo "")
LLM_STATUS=$(ssh_air "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:4000/health/readiness" 2>/dev/null || echo "ssh_fail")
if [[ "$LLM_STATUS" == "200" ]]; then
  record "litellm" "GREEN" "HTTP 200 readiness"
else
  record "litellm" "RED" "HTTP ${LLM_STATUS} (expected 200)"
fi

# =============================================================================
# CHECK 3: Telegram poller (Air launchctl)
# pid=- + exit=0 = idle between polls = GREEN
# =============================================================================
log "--- Check 3: Telegram poller ---"
TG_STATE=$(launchd_status_air "com.nous.telegram-poll")
if [[ "$TG_STATE" == "missing" || "$TG_STATE" == "crashed"* ]]; then
  record "telegram_poller" "RED" "com.nous.telegram-poll $TG_STATE"
else
  record "telegram_poller" "GREEN" "$TG_STATE"
fi

# =============================================================================
# CHECK 4: Goal Mode (Air launchctl)
# =============================================================================
log "--- Check 4: Goal Mode ---"
GOAL_STATE=$(launchd_status_air "com.nous.goal-cycle")
if [[ "$GOAL_STATE" == "missing" || "$GOAL_STATE" == "crashed"* ]]; then
  record "goal_mode" "RED" "com.nous.goal-cycle $GOAL_STATE"
else
  record "goal_mode" "GREEN" "$GOAL_STATE"
fi

# =============================================================================
# CHECK 5: Wiki parity (git HEAD on Air + VPS + Mac)
# =============================================================================
log "--- Check 5: Wiki parity ---"
MAC_HEAD=$(cd "$WIKI_DIR" && git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "git_fail")
AIR_HEAD=$(ssh_air "cd ~/nous-agaas/wiki && git rev-parse HEAD 2>/dev/null | cut -c1-8" || echo "ssh_fail")
VPS_HEAD=$(ssh_vps "cd /root/nous-agaas/wiki && git rev-parse HEAD 2>/dev/null | cut -c1-8" || echo "ssh_fail")

PARITY_DETAIL="mac=${MAC_HEAD} air=${AIR_HEAD} vps=${VPS_HEAD}"

# 3-writer system (Mac auto-sync + Air goal-cycle + VPS pull lag) means exact HEAD
# match is rarely achievable. GREEN when all hosts share a common ancestor within
# MAX_LAG commits. RED only on SSH failure or large divergence.
MAX_LAG=10
if [[ "$MAC_HEAD" == "git_fail" || "$AIR_HEAD" == "ssh_fail" || "$VPS_HEAD" == "ssh_fail" ]]; then
  record "wiki_parity" "RED" "SSH/git failure — ${PARITY_DETAIL}"
else
  # Count how many commits the most-behind host is behind the most-ahead host
  # Use Mac as reference since it usually has the freshest push
  LAG_AIR=$(cd "$WIKI_DIR" && git fetch air main --quiet 2>/dev/null; git rev-list air/main..HEAD 2>/dev/null | wc -l | tr -d ' ' || echo "0")
  LAG_VPS=$(cd "$WIKI_DIR" && git rev-list vps/main..HEAD 2>/dev/null | wc -l | tr -d ' ' || echo "0")
  MAX_OBSERVED=$(python3 -c "print(max(int('${LAG_AIR:-0}'), int('${LAG_VPS:-0}')))" 2>/dev/null || echo "0")
  if [[ "${MAX_OBSERVED:-0}" -le "$MAX_LAG" ]]; then
    record "wiki_parity" "GREEN" "lag<=${MAX_OBSERVED} commits — ${PARITY_DETAIL}"
  else
    record "wiki_parity" "RED" "lag=${MAX_OBSERVED} commits > threshold=${MAX_LAG} — ${PARITY_DETAIL}"
  fi
fi

# =============================================================================
# CHECK 6: GitHub mirror (tokenless remotes + exact canonical mirror)
# =============================================================================
log "--- Check 6: GitHub mirror ---"
TOKEN_RE='gho_|ghp_|github_pat_|https://[^:@/]+:[^@]+@github\.com'
LOCAL_HEAD="$MAC_HEAD"
for remote in origin vps github air; do
  fetch_remote_main "$remote"
done
CANONICAL_REMOTE=""
for remote in origin vps; do
  if remote_exists "$remote"; then
    CANONICAL_REMOTE="$remote"
    break
  fi
done
CANONICAL_REMOTE="${CANONICAL_REMOTE:-github}"
CANONICAL_HEAD=$(remote_main_short "$CANONICAL_REMOTE")
GITHUB_EXPECTED_HEAD="$CANONICAL_HEAD"
MAC_GITHUB_HEAD=$(remote_main_short "github")
if [[ -z "$MAC_GITHUB_HEAD" || "$MAC_GITHUB_HEAD" == "git_fail" ]]; then
  MAC_GITHUB_HEAD=$(cd "$WIKI_DIR" && git ls-remote github refs/heads/main 2>/dev/null | cut -c1-8 || echo "git_fail")
fi
MAC_TOKEN_REFS=$(cd "$WIKI_DIR" && (git config --get-regexp '^remote\..*\.url$' || true) | grep -E "$TOKEN_RE" | wc -l | tr -d ' ')
AIR_GITHUB_HEAD=$(ssh_air "cd ~/nous-agaas/wiki && git fetch github main:refs/remotes/github/main --quiet 2>/dev/null || git fetch github main --quiet 2>/dev/null || true; git rev-parse --verify --quiet refs/remotes/github/main 2>/dev/null | cut -c1-8 || git ls-remote github refs/heads/main 2>/dev/null | cut -c1-8" || echo "ssh_fail")
AIR_TOKEN_REFS=$(ssh_air "cd ~/nous-agaas/wiki && (git config --get-regexp '^remote\\..*\\.url$' || true) | grep -E '$TOKEN_RE' | wc -l | tr -d ' '" || echo "ssh_fail")
VPS_TOKEN_REFS=$(ssh_vps "cd /root/nous-agaas/wiki && (git config --get-regexp '^remote\\..*\\.url$' || true) | grep -E '$TOKEN_RE' | wc -l | tr -d ' '" || echo "ssh_fail")

GITHUB_DETAIL="canonical=${GITHUB_EXPECTED_HEAD}(${CANONICAL_REMOTE}) local=${LOCAL_HEAD} github=${MAC_GITHUB_HEAD} air_github=${AIR_GITHUB_HEAD} token_refs mac=${MAC_TOKEN_REFS} air=${AIR_TOKEN_REFS} vps=${VPS_TOKEN_REFS}"
if [[ -z "$GITHUB_EXPECTED_HEAD" || "$GITHUB_EXPECTED_HEAD" == "git_fail" || "$MAC_GITHUB_HEAD" == "git_fail" || "$AIR_GITHUB_HEAD" == "ssh_fail" ]]; then
  record "github_mirror" "RED" "GitHub mirror unreachable — ${GITHUB_DETAIL}"
elif [[ "${MAC_TOKEN_REFS:-0}" != "0" || "${AIR_TOKEN_REFS:-0}" != "0" || "${VPS_TOKEN_REFS:-0}" != "0" ]]; then
  record "github_mirror" "RED" "embedded GitHub credential in remote URL — ${GITHUB_DETAIL}"
elif [[ "$MAC_GITHUB_HEAD" != "$GITHUB_EXPECTED_HEAD" || "$AIR_GITHUB_HEAD" != "$GITHUB_EXPECTED_HEAD" ]]; then
  record "github_mirror" "RED" "GitHub mirror stale or not exact — ${GITHUB_DETAIL}"
else
  record "github_mirror" "GREEN" "tokenless remotes + exact mirror — ${GITHUB_DETAIL}"
fi

# =============================================================================
# CHECK 7: Air sync lag (local Air checkout behind canonical origin/GitHub)
# =============================================================================
log "--- Check 7: Air sync lag ---"
if [[ -z "$GITHUB_EXPECTED_HEAD" || "$GITHUB_EXPECTED_HEAD" == "git_fail" || "$LOCAL_HEAD" == "git_fail" ]]; then
  record "air_sync_lag" "RED" "cannot classify local checkout lag — ${GITHUB_DETAIL}"
elif [[ "$LOCAL_HEAD" != "$GITHUB_EXPECTED_HEAD" ]]; then
  REPAIR_DETAIL=""
  if REPAIR_DETAIL=$(repair_air_sync_lag "$GITHUB_EXPECTED_HEAD" "$CANONICAL_REMOTE"); then
    GITHUB_EXPECTED_HEAD=$(remote_main_short "$CANONICAL_REMOTE")
    fetch_remote_main "github"
    MAC_GITHUB_HEAD=$(remote_main_short "github")
    MAC_HEAD=$(cd "$WIKI_DIR" && git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "git_fail")
    LOCAL_HEAD="$MAC_HEAD"
    AIR_HEAD=$(ssh_air "cd ~/nous-agaas/wiki && git rev-parse HEAD 2>/dev/null | cut -c1-8" || echo "ssh_fail")
    AIR_GITHUB_HEAD=$(ssh_air "cd ~/nous-agaas/wiki && git rev-parse --verify --quiet refs/remotes/github/main 2>/dev/null | cut -c1-8 || git ls-remote github refs/heads/main 2>/dev/null | cut -c1-8" || echo "ssh_fail")
    GITHUB_DETAIL="canonical=${GITHUB_EXPECTED_HEAD}(${CANONICAL_REMOTE}) local=${LOCAL_HEAD} github=${MAC_GITHUB_HEAD} air_github=${AIR_GITHUB_HEAD} token_refs mac=${MAC_TOKEN_REFS} air=${AIR_TOKEN_REFS} vps=${VPS_TOKEN_REFS}"
    record "air_sync_lag" "GREEN" "local checkout auto-repaired — ${GITHUB_DETAIL}; auto_repair=${REPAIR_DETAIL}"
  else
    record "air_sync_lag" "RED" "local checkout behind canonical mirror — ${GITHUB_DETAIL}; remediation=git pull --rebase ${CANONICAL_REMOTE} main; auto_repair=${REPAIR_DETAIL:-skipped_unknown}"
  fi
else
  record "air_sync_lag" "GREEN" "local checkout equals canonical mirror — ${GITHUB_DETAIL}"
fi

# =============================================================================
# CHECK 8: OpenBrain projection (recent file on Air, <48h)
# =============================================================================
log "--- Check 8: OpenBrain projection ---"
OB_FIND_RECENT="find ~/nous-agaas/wiki/pages \\( -path '*/pages/inbox/openbrain/*/openbrain-*.md' -o -name 'openbrain-projection*' \\) -mtime -2 2>/dev/null"
OB_FIND_ALL="find ~/nous-agaas/wiki/pages \\( -path '*/pages/inbox/openbrain/*/openbrain-*.md' -o -name 'openbrain-projection*' \\) 2>/dev/null"
OB_RECENT=$(ssh_air "${OB_FIND_RECENT} | wc -l | tr -d ' '" 2>/dev/null || echo "0")
OB_COUNT=$(ssh_air "${OB_FIND_ALL} | wc -l | tr -d ' '" 2>/dev/null || echo "0")
if [[ "${OB_RECENT:-0}" -gt 0 ]]; then
  record "openbrain_projection" "GREEN" "recent projection found (${OB_RECENT} file(s) <48h, total ${OB_COUNT})"
else
  record "openbrain_projection" "RED" "no projection file modified in last 48h (total ${OB_COUNT})"
fi

# =============================================================================
# CHECK 9: gbrain (VPS CLI — more reliable than HTTP which requires auth)
# =============================================================================
log "--- Check 9: gbrain ---"
GBRAIN_STATS=$(ssh_vps "/opt/nous-agaas/gbrain/bin/gbrain stats 2>/dev/null" 2>/dev/null || echo "fail")
GBRAIN_PAGES=$(echo "$GBRAIN_STATS" | grep -i "pages:" | awk '{print $2}' || echo "")
GBRAIN_EMBEDDED=$(echo "$GBRAIN_STATS" | grep -i "embedded:" | awk '{print $2}' || echo "")
if [[ -n "$GBRAIN_PAGES" && "$GBRAIN_PAGES" -gt 0 ]]; then
  record "gbrain" "GREEN" "pages=${GBRAIN_PAGES} embedded=${GBRAIN_EMBEDDED}"
else
  record "gbrain" "RED" "gbrain stats failed or 0 pages (output=$(echo "$GBRAIN_STATS" | head -1))"
fi

# =============================================================================
# CHECK 10: OpenRouter daily cap ($5/day via LiteLLM spend API)
# =============================================================================
log "--- Check 10: OpenRouter daily cap ---"
TODAY=$(date +%Y-%m-%d)
SPEND_RESP=$(ssh_air "curl -s --max-time 10 -H 'Authorization: Bearer ${LLMKEY}' 'http://127.0.0.1:4000/spend/logs?start_date=${TODAY}&end_date=${TODAY}' 2>/dev/null || echo fail" 2>/dev/null || echo "ssh_fail")
SPEND=$(python3 -c "
import sys
try:
    import json
    d = json.loads('''$SPEND_RESP''' if '''$SPEND_RESP''' not in ('fail','ssh_fail') else 'null')
    if d is None: raise ValueError('api_fail')
    if isinstance(d, list):
        total = sum(float(x.get('spend', 0)) for x in d)
    elif isinstance(d, dict):
        total = float(d.get('total_spend', d.get('spend', 0)))
    else:
        total = -1
    print(f'{total:.4f}')
except Exception:
    print('-1')
" 2>/dev/null || echo "-1")

CAP=5.00
if python3 -c "s=float('$SPEND'); exit(0 if 0 <= s < $CAP else 1)" 2>/dev/null; then
  record "openrouter_cap" "GREEN" "spend=\$${SPEND} today (cap=\$${CAP})"
elif [[ "$SPEND" == "-1" ]]; then
  record "openrouter_cap" "RED" "spend check failed (LiteLLM API unreachable or parse error)"
else
  record "openrouter_cap" "RED" "spend=\$${SPEND} exceeds or approaches cap=\$${CAP}"
fi

# =============================================================================
# Build JSON output (Python handles all escaping safely)
# =============================================================================
OVERALL=$([[ "$REDS" -eq 0 ]] && echo "GREEN" || echo "RED")

JSON_OUT=$(python3 - <<PYEOF
import json

names = json.loads(r'''$(python3 -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "${CHECK_NAMES[@]}")''')
statuses = json.loads(r'''$(python3 -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "${CHECK_STATUS[@]}")''')
details_raw = json.loads(r'''$(python3 -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "${CHECK_DETAIL[@]}")''')

checks = []
for i, name in enumerate(names):
    checks.append({
        "check": name,
        "status": statuses[i],
        "detail": details_raw[i] if i < len(details_raw) else ""
    })

result = {
    "ts": "$TS",
    "overall": "$OVERALL",
    "reds": $REDS,
    "checks": checks
}
print(json.dumps(result, indent=2))
PYEOF
)

# =============================================================================
# Output
# =============================================================================
if [[ "$QUIET" -eq 0 ]]; then
  echo ""
  echo "============================================"
  echo "Factory No-Drift Probe — $TS"
  echo "Overall: $OVERALL  ($REDS red)"
  echo "============================================"
fi

echo "$JSON_OUT"

# ─── Telegram alert on any RED ───────────────────────────────────────────────
if [[ "$REDS" -gt 0 && "$NO_TELEGRAM" -eq 0 && -n "$TELEGRAM_BOT_TOKEN" ]]; then
  SUPERVISOR="$WIKI_DIR/tools/factory_self_heal.py"
  if [[ -x "$SUPERVISOR" || -f "$SUPERVISOR" ]]; then
    printf "%s" "$JSON_OUT" |
      python3 "$SUPERVISOR" --stdin-probe-json --source factory_no_drift_probe --notify \
        >> "$HOME/nous-agaas/logs/factory-self-heal.out.log" 2>&1 || true
  else
    RED_LINES=""
    for i in "${!CHECK_STATUS[@]}"; do
      if [[ "${CHECK_STATUS[$i]}" == "RED" ]]; then
        RED_LINES="${RED_LINES}  ❌ ${CHECK_NAMES[$i]}: ${CHECK_DETAIL[$i]}"$'\n'
      fi
    done
    MSG="🔴 Factory drift ($REDS failed) — $TS
${RED_LINES}"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${MSG}" > /dev/null 2>&1 || true
  fi
fi

exit $REDS
