#!/bin/bash
# test_gbrain_cli_fallback_pattern.sh — detect stale gbrain-CLI-fallback patterns.
#
# Context: gbrain-ops AP-33 (session-55, 2026-04-20) codified the canonical fallback
# pattern for gbrain writes when MCP is disconnected:
#     ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain <command>"
#
# Session-66 Phase 5 (2026-04-23) discovered learner.py on Air had been using a
# STALE pattern for 17+ days:
#     ssh vps /root/nous-agaas/gbrain/bin/gbrain timeline-add ...
# BOTH wrong — no `vps` SSH alias on Air, and `/root/nous-agaas/gbrain/` doesn't
# exist on VPS (actual path is `/opt/`). Every learner call failed silently →
# Karpathy ratchet dead → 1+ real correction dropped to DLQ → zero learning.
#
# Meta-lesson: skill codification DOES NOT auto-fix pre-existing stale callsites.
# This detector closes that gap by scanning Air + vault + OpenClaw-mounted paths
# for executable code with the broken patterns.
#
# Exits:
#   0 = no drift; all code uses canonical pattern
#   1 = drift found — at least one executable file has stale pattern
#   2 = scanner error (can't reach Air, etc.)
#
# Scope: executable code only (.py, .sh). Telegram notification STRINGS that
# mention "ssh vps" are OK (they're docs for humans, not executed).

set -u

STATUS=0

# Bad patterns (executable, not quoted-for-humans):
#   "ssh", "vps"  — Python list args
#   ssh vps ...   — bash invocation (but must not be inside a printf/echo/notification)
#   /root/nous-agaas/gbrain  — wrong path; canonical is /opt/nous-agaas/gbrain

scan_path() {
  local label="$1"
  local path="$2"
  local remote="$3"  # "local" or "ssh:<host>"

  echo "=== scanning $label ($path) ==="
  local hits=""

  # Exclude patterns: backups + caches + git internals + this detector itself
  # (the detector references the bad strings in its own docstrings/regex bodies).
  local EXCL='pre-s66-fix|\.bak|__pycache__|/node_modules/|/\.git/|test_gbrain_cli_fallback_pattern\.sh'
  local clean=1

  if [ "$remote" = "local" ]; then
    # Look for Python list-form "ssh","vps" — definitely executable
    hits=$(grep -rn --include='*.py' --include='*.sh' \
      -E '"ssh",\s*"vps"' "$path" 2>/dev/null | \
      grep -vE "$EXCL" || true)

    if [ -n "$hits" ]; then
      echo "🔴 DRIFT — 'ssh', 'vps' list-form in executable code:"
      echo "$hits"
      STATUS=1
      clean=0
    fi

    # Look for /root/nous-agaas/gbrain (wrong path) in executable .py/.sh
    hits=$(grep -rn --include='*.py' --include='*.sh' \
      '/root/nous-agaas/gbrain' "$path" 2>/dev/null | \
      grep -vE "$EXCL" || true)

    if [ -n "$hits" ]; then
      echo "🔴 DRIFT — '/root/nous-agaas/gbrain' (wrong path) in executable code:"
      echo "$hits"
      STATUS=1
      clean=0
    fi
  else
    # ssh to remote host
    local host="${remote#ssh:}"
    hits=$(ssh -o ConnectTimeout=5 "$host" "grep -rn --include='*.py' --include='*.sh' -E '\"ssh\",\s*\"vps\"' $path 2>/dev/null | grep -vE '$EXCL' || true" 2>/dev/null || echo "SSH_ERROR")

    if [ "$hits" = "SSH_ERROR" ]; then
      echo "🟡 SSH unreachable — skipping remote scan"
      [ $STATUS -eq 0 ] && STATUS=2
      clean=0
    elif [ -n "$hits" ]; then
      echo "🔴 DRIFT on $host — 'ssh', 'vps' list-form:"
      echo "$hits"
      STATUS=1
      clean=0
    fi

    hits=$(ssh -o ConnectTimeout=5 "$host" "grep -rn --include='*.py' --include='*.sh' '/root/nous-agaas/gbrain' $path 2>/dev/null | grep -vE '$EXCL' || true" 2>/dev/null || echo "SSH_ERROR")

    if [ "$hits" = "SSH_ERROR" ]; then
      : # already logged above
    elif [ -n "$hits" ]; then
      echo "🔴 DRIFT on $host — '/root/nous-agaas/gbrain' (wrong path):"
      echo "$hits"
      STATUS=1
      clean=0
    fi
  fi

  if [ "$clean" -eq 1 ]; then
    echo "✅ clean"
  fi
  return 0
}

# ----- scan the 3 targets -----

VAULT="${VAULT:-$(cd "$(dirname "$0")/.." && pwd)}"
# In testing, VAULT may point to a temp dir with planted fixtures — scan the
# whole dir rather than $VAULT/tools, so negative-dogfood can plant files at
# VAULT root.
if [ -d "$VAULT/tools" ]; then
  scan_path "Mac vault" "$VAULT/tools" "local"
else
  scan_path "local test fixture" "$VAULT" "local"
fi
scan_path "Air tenants+tools" "~/nous-agaas/tenants ~/nous-agaas/tools" "ssh:air"

# OpenClaw container — learner.py isn't mounted there per s66 Phase 8 probe,
# but check skills/wiki/tools paths anyway for completeness
scan_path "OpenClaw (via Air docker exec)" "/opt/nous-agaas/skills /opt/nous-agaas/wiki/tools" "ssh:air"

if [ $STATUS -eq 0 ]; then
  echo ""
  echo "✅ ALL TARGETS CLEAN — gbrain CLI fallback pattern uniformly canonical"
  echo "   (per gbrain-ops AP-33: ssh root@65.108.215.200 /opt/nous-agaas/gbrain/bin/gbrain)"
elif [ $STATUS -eq 1 ]; then
  echo ""
  echo "🔴 DRIFT DETECTED — fix callsites to match gbrain-ops AP-33 canonical pattern."
  echo "   Canonical: ssh root@65.108.215.200 /opt/nous-agaas/gbrain/bin/gbrain <cmd>"
  echo "   If the offending file is a .bak or pre-fix backup, it's excluded already."
elif [ $STATUS -eq 2 ]; then
  echo ""
  echo "🟡 SCAN INCOMPLETE — SSH to Air failed; rerun when reachable."
fi

exit $STATUS
