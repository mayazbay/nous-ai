#!/bin/bash
# pre-push sanity — Tan/Karpathy-style compounding gate for hook drift.
#
# Codifies session-45 GAP 1: "live hook patched but vault tools/ backup not synced."
# Runs on every `git push` from a vault working copy. Rejects if any live hook in
# ~/.claude/hooks/*.sh has a diverged MD5 from its vault tools/<name>.sh twin.
#
# Install: copy to <wiki>/.git/hooks/pre-push + chmod +x.
# Source of truth lives at <vault>/tools/pre-push-sanity.sh. Re-deploy to all 3
# wiki clones (Mac, VPS, Air) when this file changes — use `sha1sum` parity with
# the canonical to detect drift.
#
# Escape hatch: set `VAULT_PREPUSH_SKIP=1 git push` for a known-legitimate desync
# case (e.g. the vault backup is intentionally ahead of the live hook pending
# deploy). The skip is logged to stderr so the audit trail is preserved.
#
# Exit 0 = allow push, exit 1 = block push (stderr message shown).

set -u

# ── Escape hatch ────────────────────────────────────────────────
if [ "${VAULT_PREPUSH_SKIP:-0}" = "1" ]; then
  echo "pre-push-sanity: VAULT_PREPUSH_SKIP=1 set — bypassing check. Reason must be documented in commit message." >&2
  exit 0
fi

# ── Locate vault tools/ dir from this hook's install location ────
# .git/hooks/pre-push  →  repo root is $(git rev-parse --show-toplevel)
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ] || [ ! -d "$REPO_ROOT/tools" ]; then
  # Not a vault repo (no tools/ dir). Nothing to check — allow.
  exit 0
fi
VAULT_TOOLS="$REPO_ROOT/tools"

# ── Live hooks dir (Claude Code) ────────────────────────────────
LIVE_HOOKS="$HOME/.claude/hooks"
if [ ! -d "$LIVE_HOOKS" ]; then
  # No live hooks dir on this host (e.g. a CI box). Nothing to check.
  exit 0
fi

# ── Cross-platform MD5 ──────────────────────────────────────────
md5_of() {
  local f="$1"
  if command -v md5 >/dev/null 2>&1; then
    # Mac
    md5 -q "$f"
  elif command -v md5sum >/dev/null 2>&1; then
    # Linux
    md5sum "$f" | awk '{print $1}'
  else
    echo "NO_MD5_TOOL"
  fi
}

# ── CHECK A: live hook ↔ vault tools/ MD5 parity ────────────────
DRIFT=()
for live in "$LIVE_HOOKS"/*.sh; do
  [ -f "$live" ] || continue
  name=$(basename "$live")
  vault="$VAULT_TOOLS/$name"
  # Only care when vault copy EXISTS — means it's meant to be tracked
  [ -f "$vault" ] || continue

  live_md5=$(md5_of "$live")
  vault_md5=$(md5_of "$vault")

  if [ "$live_md5" != "$vault_md5" ]; then
    DRIFT+=("  ${name} [A: ~/.claude/hooks ↔ tools/]")
    DRIFT+=("    live:  $live  ($live_md5)")
    DRIFT+=("    vault: $vault  ($vault_md5)")
  fi
done

# ── CHECK B: .git/hooks/* ↔ tools/*-hook-canonical parity (s73 AP-56) ──
# Codifies the s68p silent-drift class: `.git/hooks/pre-commit` was patched
# live across 3 hosts but the canonical `tools/pre-commit-hook-tan-pattern.sh`
# wasn't written back → 5-day silent divergence until s72 SOAO surfaced.
# Check A catches ~/.claude/hooks drift; git versions don't cover .git/hooks/*
# so this check is the analogous compounding gate for that hook class.
#
# Explicit mapping (not globbed) — adding a new git hook requires adding a row
# here, which hits AP-43 (SKILL.md version parity) when documented, so drift is
# physically caught at the git boundary.
GIT_HOOKS_DIR="$REPO_ROOT/.git/hooks"
GIT_HOOK_MAP=(
  "pre-commit:pre-commit-hook-tan-pattern.sh"
  "commit-msg:commit-msg-hook.sh"
  "pre-push:pre-push-sanity.sh"
)
for row in "${GIT_HOOK_MAP[@]}"; do
  hook_name="${row%%:*}"
  canon_name="${row##*:}"
  deployed="$GIT_HOOKS_DIR/$hook_name"
  canon="$VAULT_TOOLS/$canon_name"
  [ -f "$deployed" ] || continue  # hook not installed locally — skip
  [ -f "$canon" ] || continue      # canonical missing — not this hook's drift
  deployed_md5=$(md5_of "$deployed")
  canon_md5=$(md5_of "$canon")
  if [ "$deployed_md5" != "$canon_md5" ]; then
    DRIFT+=("  ${hook_name} [B: .git/hooks ↔ tools/ canon]")
    DRIFT+=("    deployed: $deployed  ($deployed_md5)")
    DRIFT+=("    canon:    $canon  ($canon_md5)")
  fi
done

if [ ${#DRIFT[@]} -gt 0 ]; then
  echo "" >&2
  echo "═══════════════════════════════════════════════════════════════" >&2
  echo "pre-push-sanity: HOOK DRIFT DETECTED — push REJECTED" >&2
  echo "═══════════════════════════════════════════════════════════════" >&2
  echo "One or more hooks have diverged from their vault-tracked canon." >&2
  echo "  A = ~/.claude/hooks/<name>.sh ↔ tools/<name>.sh (session-45 AP-35)" >&2
  echo "  B = .git/hooks/<name>          ↔ tools/<canon>.sh (session-73 AP-56)" >&2
  echo "" >&2
  for line in "${DRIFT[@]}"; do
    echo "$line" >&2
  done
  echo "" >&2
  echo "Fix:" >&2
  echo "  A-vault-stale:    cp \$HOME/.claude/hooks/<name>.sh tools/<name>.sh && git add tools/<name>.sh" >&2
  echo "  A-live-stale:     cp tools/<name>.sh \$HOME/.claude/hooks/<name>.sh" >&2
  echo "  B-canon-stale:    cp .git/hooks/<name> tools/<canon>.sh && git add tools/<canon>.sh" >&2
  echo "  B-deployed-stale: cp tools/<canon>.sh .git/hooks/<name> && chmod +x .git/hooks/<name>" >&2
  echo "  escape:           VAULT_PREPUSH_SKIP=1 git push   (document reason in commit msg)" >&2
  echo "═══════════════════════════════════════════════════════════════" >&2
  exit 1
fi

exit 0
