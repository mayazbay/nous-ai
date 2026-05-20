#!/bin/bash
# tools/codex-nous.sh — local Codex launcher with session-registry handshake.
#
# Codex desktop/CLI does not currently expose a SessionStart hook equivalent to
# Claude Code. Use this launcher for local interactive Codex sessions that may
# touch Nous AGaaS substrate so other lanes can see the session before edits.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"

INTENT="${CODEX_SESSION_INTENT:-local interactive Codex}"
SCOPE="${CODEX_SESSION_SCOPE:-*}"
CODEX_BIN="${CODEX_BIN:-codex}"

bash "$VAULT/tools/session_self_register.sh" --intent "$INTENT" --scope "$SCOPE"

if command -v "$CODEX_BIN" >/dev/null 2>&1; then
  exec "$CODEX_BIN" "$@"
fi

if [ -x "$CODEX_BIN" ]; then
  exec "$CODEX_BIN" "$@"
fi

FALLBACK="/Applications/Codex.app/Contents/Resources/codex"
if [ -x "$FALLBACK" ]; then
  exec "$FALLBACK" "$@"
fi

echo "codex-nous: cannot find Codex binary. Set CODEX_BIN=/path/to/codex." >&2
exit 127
