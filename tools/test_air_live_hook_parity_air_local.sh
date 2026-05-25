#!/bin/bash
# Regression: Air-local hook parity must not SSH back into `air`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/.claude/hooks"
for hook in post-session.sh sync-banned-patterns.sh task-completed-enforce.sh; do
  printf 'fixture-%s\n' "$hook" > "$TMP/.claude/hooks/$hook"
done

OUT="$TMP/out.txt"
HOME="$TMP" SESSION_FORCE_AIR_LOCAL=1 bash "$ROOT/tools/test_air_live_hook_parity.sh" >"$OUT" 2>&1
grep -q "test_air_live_hook_parity: red=0 yellow=0" "$OUT"
