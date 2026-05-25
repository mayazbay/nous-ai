#!/bin/bash
# Verify vault SOUL/USER/AGENTS identity files match OpenClaw runtime copies.
# Default is host-portable: skip when Docker/OpenClaw is unavailable.
# Set REQUIRE_OPENCLAW=1 on Air to fail closed.
set -euo pipefail

ROOT_DIR="${WIKI_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SYSTEMS_DIR="${WIKI_SYSTEMS_DIR:-$ROOT_DIR/pages/systems}"
DOCKER_BIN="${DOCKER_BIN:-}"
if [ -z "$DOCKER_BIN" ]; then
  DOCKER_BIN=$(command -v docker 2>/dev/null || true)
fi
OPENCLAW_CONTAINER="${OPENCLAW_CONTAINER:-openclaw}"
REQUIRE_OPENCLAW="${REQUIRE_OPENCLAW:-0}"

SOUL_SRC="$SYSTEMS_DIR/nous-agent-soul.md"
USER_SRC="$SYSTEMS_DIR/nous-agent-user.md"
AGENTS_SRC="$SYSTEMS_DIR/nous-agent-procedures.md"

red=0

fail_or_skip() {
  msg="$1"
  if [ "$REQUIRE_OPENCLAW" = "1" ]; then
    echo "FAIL: $msg"
    exit 1
  fi
  echo "SKIP: $msg"
  exit 0
}

require_src() {
  src="$1"
  if [ ! -f "$src" ]; then
    echo "FAIL: missing source $src"
    red=1
  fi
}

check_one() {
  src="$1"
  dst="$2"
  label="$3"
  tmp=$(mktemp)
  if ! "$DOCKER_BIN" exec "$OPENCLAW_CONTAINER" cat "$dst" > "$tmp" 2>/dev/null; then
    echo "FAIL: missing runtime $label at $dst"
    red=1
  elif cmp -s "$src" "$tmp"; then
    echo "OK: $label"
  else
    echo "FAIL: drift $label"
    echo "  source:  $src"
    echo "  runtime: $dst"
    red=1
  fi
  rm -f "$tmp"
}

require_src "$SOUL_SRC"
require_src "$USER_SRC"
require_src "$AGENTS_SRC"

if [ "$red" -ne 0 ]; then
  exit "$red"
fi

if [ -z "$DOCKER_BIN" ] || [ ! -x "$DOCKER_BIN" ]; then
  fail_or_skip "docker unavailable"
fi

if ! "$DOCKER_BIN" inspect "$OPENCLAW_CONTAINER" >/dev/null 2>&1; then
  fail_or_skip "$OPENCLAW_CONTAINER container not found"
fi

if [ "$("$DOCKER_BIN" inspect -f '{{.State.Running}}' "$OPENCLAW_CONTAINER" 2>/dev/null || echo false)" != "true" ]; then
  fail_or_skip "$OPENCLAW_CONTAINER container not running"
fi

check_one "$SOUL_SRC" "/home/node/.openclaw/workspace/SOUL.md" "workspace/SOUL.md"
check_one "$USER_SRC" "/home/node/.openclaw/workspace/USER.md" "workspace/USER.md"
check_one "$AGENTS_SRC" "/home/node/.openclaw/workspace/AGENTS.md" "workspace/AGENTS.md"
check_one "$SOUL_SRC" "/opt/nous-agaas/agents/SOUL.md" "agents/SOUL.md"
check_one "$USER_SRC" "/opt/nous-agaas/agents/USER.md" "agents/USER.md"
check_one "$AGENTS_SRC" "/opt/nous-agaas/agents/AGENTS.md" "agents/AGENTS.md"
check_one "$USER_SRC" "/home/node/.openclaw/workspaces/grok-ceo/USER.md" "grok-ceo/USER.md"

if [ "$red" -eq 0 ]; then
  echo "OK: agent identity runtime parity"
fi
exit "$red"
