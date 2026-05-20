#!/bin/bash
# test_audit_probes_e2e.sh — sibling test for `audit` AP-20.
#
# AP-20 codifies: every subsystem probe must be E2E-verified against a
# running target before ship. This test is the mechanical enforcement.
#
# For each subsystem probe in `pages/skills/audit/SKILL.md`, it verifies:
#   (a) the probe command RUNS — no `command not found`, `MODULE_NOT_FOUND`,
#       SyntaxError, or similar "probe-itself-broken" signals (AP-16 rule 6).
#   (b) the probe produces NON-EMPTY output — not silent-empty (which caused
#       `/audit gbrain` to false-negative for multiple sessions — session 51).
#   (c) the probe output contains an EXPECTED MARKER for that subsystem —
#       ensures we're reading output that comes from the probe target,
#       not a generic error the script swallowed.
#
# What this test does NOT do:
#   - It does NOT check subsystem HEALTH (that's what `/audit SUBSYSTEM` does).
#   - A subsystem can be red/degraded and still pass this test, as long as
#     the probe's OUTPUT SHAPE proves the probe code works.
#
# Exit codes:
#   0 — every probe verified runs cleanly + emits expected shape
#   1 — at least one probe is BROKEN (silent-empty or command error)
#
# Usage:
#   bash tools/test_audit_probes_e2e.sh           # human output
#   bash tools/test_audit_probes_e2e.sh --quiet   # exit code only

set -u
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

log() { [ "$QUIET" -eq 1 ] || echo "$@"; }

BROKEN=0

# Probe runner: $1 = subsystem label, $2 = expected-marker regex, $3... = command
# Captures stdout+stderr, checks for probe-broken signals + expected marker.
run_probe() {
  local label="$1"; shift
  local marker="$1"; shift
  local out rc
  out=$("$@" 2>&1)
  rc=$?

  # Probe-broken signals — these indicate the probe CODE is wrong, not the target.
  if echo "$out" | grep -qE 'command not found|MODULE_NOT_FOUND|SyntaxError|No such file or directory' ; then
    log "❌ $label: PROBE BROKEN — shell/python error signal in output"
    log "   first line: $(echo "$out" | head -1)"
    log "   fix: update the probe command in pages/skills/audit/SKILL.md"
    BROKEN=$((BROKEN+1))
    return
  fi

  # Silent-empty — the AP-20 root-cause failure mode.
  if [ -z "$out" ]; then
    log "❌ $label: PROBE BROKEN — silent-empty output (exit=$rc)"
    log "   a silent-empty probe produces false-negatives; see audit AP-20"
    BROKEN=$((BROKEN+1))
    return
  fi

  # Expected marker — confirms output came from the target, not a swallowed error.
  if [ -n "$marker" ] && ! echo "$out" | grep -qE "$marker"; then
    log "❌ $label: PROBE BROKEN — expected marker /$marker/ not found"
    log "   first line: $(echo "$out" | head -1)"
    log "   fix: either the regex is wrong (case-sensitivity bug?) or target output changed"
    BROKEN=$((BROKEN+1))
    return
  fi

  log "✅ $label: probe runs cleanly; marker /$marker/ present"
}

log "=== test_audit_probes_e2e @ $(date '+%Y-%m-%d %H:%M:%S') ==="
log ""

# -- openclaw: container health via `docker inspect` (AP-1: don't use HTTP on WS port)
log "-- openclaw --"
run_probe "openclaw.docker-inspect" "healthy|starting|unhealthy|none" \
  ssh -o ConnectTimeout=10 air "docker inspect openclaw --format '{{.State.Health.Status}}'"
run_probe "openclaw.tcp-port" "succeeded!|open" \
  ssh -o ConnectTimeout=10 air "nc -zv localhost 18789"

# -- litellm: launchctl + authed /health
log ""
log "-- litellm --"
run_probe "litellm.launchctl" "com.nous.litellm" \
  ssh -o ConnectTimeout=10 air "launchctl list | grep com.nous.litellm"
# /health requires auth per AP-2; we check that the status returns a known HTTP code.
run_probe "litellm.port-http-code" "^[0-9]{3}$" \
  ssh -o ConnectTimeout=10 air 'source ~/nous-agaas/litellm/.env 2>/dev/null; curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://localhost:4000/health'

# -- gbrain: the probe that was silently broken for multiple sessions (AP-20 root case)
log ""
log "-- gbrain (AP-20 regression guard) --"
run_probe "gbrain.doctor-health-score" "Health score: [0-9]+" \
  ssh -o ConnectTimeout=15 root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain doctor"
run_probe "gbrain.list-count" "pages/|^[0-9]+ pages|Connected" \
  ssh -o ConnectTimeout=15 root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain list | head -5"

# -- telegram: API reachability
log ""
log "-- telegram --"
run_probe "telegram.launchctl" "com.nous.telegram-poll" \
  ssh -o ConnectTimeout=10 air "launchctl list | grep com.nous.telegram-poll"
# Token comes from Air's .env; we check getMe returns a username field.
run_probe "telegram.api-getme" '"username"' \
  ssh -o ConnectTimeout=10 air 'TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/nous-agaas/.env 2>/dev/null | cut -d= -f2); curl -s "https://api.telegram.org/bot${TOKEN}/getMe"'

# -- wiki-sync: git log reachable
log ""
log "-- wiki-sync --"
run_probe "wiki-sync.git-log" "auto-sync|session|commit" \
  ssh -o ConnectTimeout=10 air "cd ~/nous-agaas/wiki && git log --oneline -3"

# -- /code: claude CLI presence on Air (not Mac — Mac runs claude directly here)
log ""
log "-- /code --"
run_probe "/code.claude-cli" "^[0-9]+\.[0-9]+" \
  ssh -o ConnectTimeout=10 air "/usr/local/bin/claude --version 2>&1 || which claude"

# -- Summary
log ""
log "=== SUMMARY ==="
if [ "$BROKEN" -eq 0 ]; then
  log "✅ all probes pass — every audit subsystem probe runs cleanly + emits expected shape"
  exit 0
else
  log "❌ $BROKEN probe(s) BROKEN — fix before shipping future /audit changes (see audit AP-20)"
  exit 1
fi
