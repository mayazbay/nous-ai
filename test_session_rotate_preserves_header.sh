#!/bin/bash
# Regression test for tools/session_rotate.sh.
# Verifies rotation measures files inside the container and preserves the
# OpenClaw JSONL session header instead of replacing files with invalid `[]`.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CONTAINER_ROOT="$TMP/container"
SESSION_DIR="$CONTAINER_ROOT/home/node/.openclaw/agents/nous/sessions"
mkdir -p "$SESSION_DIR" "$TMP/bin"

VALID="$SESSION_DIR/valid.jsonl"
INVALID="$SESSION_DIR/invalid.jsonl"

cat > "$VALID" <<'JSONL'
{"type":"session","version":3,"id":"test","timestamp":"2026-04-29T00:00:00.000Z","cwd":"/app"}
{"type":"model_change","modelId":"deepseek-v4-flash"}
{"type":"message","role":"assistant","text":"old context"}
JSONL
printf '[]\n' > "$INVALID"

cat > "$TMP/bin/docker" <<'SH'
#!/bin/bash
set -euo pipefail
if [ "$1" != "exec" ] || [ "$2" != "openclaw" ]; then
  echo "unexpected docker invocation: $*" >&2
  exit 64
fi
shift 2
if [ "$1" = "find" ]; then
  shift
  exec find "$CONTAINER_ROOT$1" "${@:2}"
fi
if [ "$1" = "sh" ] && [ "$2" = "-c" ]; then
  script="$3"
  shift 3
  args=()
  for arg in "$@"; do
    if [[ "$arg" == /home/node/* ]]; then
      args+=("$CONTAINER_ROOT$arg")
    else
      args+=("$arg")
    fi
  done
  exec sh -c "$script" "${args[@]}"
fi
echo "unsupported docker invocation: $*" >&2
exit 65
SH
chmod +x "$TMP/bin/docker"

PATH="$TMP/bin:$PATH" CONTAINER_ROOT="$CONTAINER_ROOT" \
  SESSION_ROTATE_LOG="$TMP/session-rotate.log" \
  bash "$ROOT/tools/session_rotate.sh"

VALID_LINES=$(wc -l < "$VALID" | tr -d ' ')
VALID_HEAD=$(head -n 1 "$VALID")
INVALID_BODY=$(cat "$INVALID")

if [ "$VALID_LINES" != "1" ]; then
  echo "FAIL: valid session should be reduced to one header line, got $VALID_LINES lines"
  exit 1
fi

case "$VALID_HEAD" in
  *'"type":"session"'*) ;;
  *) echo "FAIL: valid session header was not preserved: $VALID_HEAD"; exit 1 ;;
esac

if [ "$INVALID_BODY" != "[]" ]; then
  echo "FAIL: invalid session should be skipped unchanged"
  exit 1
fi

if ! grep -q "skipped $INVALID" "$TMP/session-rotate.log"; then
  echo "FAIL: invalid session skip was not logged"
  exit 1
fi

echo "OK: session_rotate preserves OpenClaw session headers"
