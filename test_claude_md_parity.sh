#!/bin/bash
# test_claude_md_parity.sh — closes AP-49 drift class (session 54 Probe-B incident)
#
# Session 54 discovered that operational content added to Mac-root CLAUDE.md
# (HARD RULES, Telegram routing, architecture quickref, runtime contract
# pointer) was invisible to Air-side OpenClaw factory + `/code`-spawned CLI
# sessions because Mac-root CLAUDE.md lives OUTSIDE the vault sync. Fix:
# extract operational content to vault at pages/systems/architecture-quickref.md,
# install reciprocal pointers in both CLAUDE.md files.
#
# Session 76 extended the same class to Codex: Mac-root AGENTS.md is the Codex
# session-shim and must also point at the vault mirror.
#
# This probe verifies the reciprocal-pointer invariant holds — if either
# pointer goes missing, the class of drift that caused Probe-B is back.
#
# Checks:
#   1. Mac-root CLAUDE.md exists and references `pages/systems/architecture-quickref`
#      when the Mac project root is locally mounted
#   2. Mac-root AGENTS.md exists and references `pages/systems/architecture-quickref`
#      when the Mac project root is locally mounted
#   3. Vault-root CLAUDE.md (Nous/CLAUDE.md) exists and references `architecture-quickref`
#   4. architecture-quickref.md exists in the vault
#   5. architecture-quickref references back to Mac-root session-shims
#
# Exit codes:
#   0 = all 5 invariants hold
#   2 = one or more invariants broken (drift)
#
# Usage: bash tools/test_claude_md_parity.sh [--quiet]
#
# Source: `infrastructure` SKILL.md AP-49 (session 54, 2026-04-20).
# Wires into SOAO section 4.

set -u
QUIET=0
for arg in "$@"; do
  case "$arg" in --quiet) QUIET=1 ;; esac
done
log() { [ "$QUIET" -eq 1 ] || echo "$@"; }

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="$(cd "$VAULT/.." && pwd)"

MAC_ROOT_CLAUDE="$PROJECT_ROOT/CLAUDE.md"
MAC_ROOT_AGENTS="$PROJECT_ROOT/AGENTS.md"
VAULT_ROOT_CLAUDE="$VAULT/CLAUDE.md"
QUICKREF="$VAULT/pages/systems/architecture-quickref.md"
REQUIRE_MAC_ROOT_SHIMS=0

case "$PROJECT_ROOT" in
  *"/Documents/Projects/Nous AGaaS")
    REQUIRE_MAC_ROOT_SHIMS=1
    ;;
esac

RED=0

# 1. Mac-root CLAUDE.md exists + points to architecture-quickref
if [ ! -f "$MAC_ROOT_CLAUDE" ]; then
  if [ "$REQUIRE_MAC_ROOT_SHIMS" -eq 1 ]; then
    log "🔴 Mac-root CLAUDE.md missing at $MAC_ROOT_CLAUDE"
    RED=$((RED+1))
  else
    log "ℹ️ Mac-root CLAUDE.md not mounted on this host; skipping local shim check"
  fi
elif ! grep -q "architecture-quickref" "$MAC_ROOT_CLAUDE"; then
  log "🔴 Mac-root CLAUDE.md missing pointer to architecture-quickref"
  log "   Add: > **Vault mirror:** [[pages/systems/architecture-quickref]]"
  RED=$((RED+1))
else
  log "✅ Mac-root CLAUDE.md points to architecture-quickref"
fi

# 2. Mac-root AGENTS.md exists + points to architecture-quickref
if [ ! -f "$MAC_ROOT_AGENTS" ]; then
  if [ "$REQUIRE_MAC_ROOT_SHIMS" -eq 1 ]; then
    log "🔴 Mac-root AGENTS.md missing at $MAC_ROOT_AGENTS"
    RED=$((RED+1))
  else
    log "ℹ️ Mac-root AGENTS.md not mounted on this host; skipping local shim check"
  fi
elif ! grep -q "architecture-quickref" "$MAC_ROOT_AGENTS"; then
  log "🔴 Mac-root AGENTS.md missing pointer to architecture-quickref"
  log "   Add: > **Vault mirror:** [[pages/systems/architecture-quickref]]"
  RED=$((RED+1))
else
  log "✅ Mac-root AGENTS.md points to architecture-quickref"
fi

# 3. Vault-root CLAUDE.md exists + points to architecture-quickref
if [ ! -f "$VAULT_ROOT_CLAUDE" ]; then
  log "🔴 Vault-root CLAUDE.md missing at $VAULT_ROOT_CLAUDE"
  RED=$((RED+1))
elif ! grep -q "architecture-quickref" "$VAULT_ROOT_CLAUDE"; then
  log "🔴 Vault-root CLAUDE.md missing pointer to architecture-quickref"
  log "   Add: > **Architecture topology + hard rules:** [[architecture-quickref]]"
  RED=$((RED+1))
else
  log "✅ Vault-root CLAUDE.md points to architecture-quickref"
fi

# 4. architecture-quickref.md exists
if [ ! -f "$QUICKREF" ]; then
  log "🔴 architecture-quickref.md missing at $QUICKREF"
  log "   This is the vault substrate mirror of Mac-root operational content."
  log "   Restore from git log or last session-54 commit."
  RED=$((RED+1))
else
  log "✅ architecture-quickref.md present"
fi

# 5. architecture-quickref references Mac-root session-shims
if [ -f "$QUICKREF" ]; then
  if grep -qiE "(session-shim|session-start-shim|Mac-root|Mac-side|CLAUDE\.md.*session)" "$QUICKREF" \
     && grep -qiE "(AGENTS\.md|Codex session-shim|Codex.*session)" "$QUICKREF"; then
    log "✅ architecture-quickref references Mac-root CLAUDE.md + AGENTS.md as session-shims"
  else
    log "🔴 architecture-quickref missing session-shim reference back to Mac-root CLAUDE.md and/or AGENTS.md"
    log "   Add a line describing Mac-root CLAUDE.md and AGENTS.md as session-start shims this file mirrors."
    RED=$((RED+1))
  fi
fi

log ""
log "test_claude_md_parity: red=$RED"
[ "$RED" -gt 0 ] && exit 2
exit 0
