#!/bin/bash
# secrets-deploy.sh — pipe Keychain secrets into .env on a target machine.
# Usage: secrets-deploy.sh [--dry-run|--audit] <service> <target>
# Targets: vps, air
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "FAIL: secrets-deploy is Mac-only" >&2
  exit 1
fi

DRY_RUN=0
AUDIT=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    --audit)   AUDIT=1 ;;
    *) ARGS+=("$a") ;;
  esac
done
[ "${#ARGS[@]}" -eq 2 ] || { echo "usage: $0 [--dry-run|--audit] <service> <target>" >&2; exit 1; }
SERVICE="${ARGS[0]}"
TARGET="${ARGS[1]}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/pages/secrets-manifest.md"
PARSER="$ROOT/tools/secrets-manifest-parse.sh"
READER="$ROOT/tools/secrets-keychain-read.sh"

[ -f "$MANIFEST" ] || { echo "FAIL: manifest missing at $MANIFEST" >&2; exit 1; }
[ -x "$PARSER" ]   || { echo "FAIL: parser not executable at $PARSER" >&2; exit 1; }
[ -x "$READER" ]   || { echo "FAIL: reader not executable at $READER" >&2; exit 1; }

case "$TARGET" in
  vps)
    TARGET_HOST="65.108.215.200"
    SSH_USER="root"
    DEST="/opt/nous-agaas/.env"
    OWNER="deploy:deploy"
    ;;
  air)
    TARGET_HOST="air"
    SSH_USER="madia"
    DEST="/Users/madia/nous-agaas/.env"
    OWNER="madia:staff"
    ;;
  *) echo "FAIL: unknown target '$TARGET'" >&2; exit 1 ;;
esac

ROWS=$("$PARSER" "$MANIFEST" "$SERVICE" "$TARGET")
[ -n "$ROWS" ] || { echo "FAIL: no rows for service=$SERVICE target=$TARGET" >&2; exit 1; }

if [ "$DRY_RUN" -eq 1 ]; then
  echo "=== DRY RUN ==="
  echo "service: $SERVICE"
  echo "target : $TARGET ($SSH_USER@$TARGET_HOST)"
  echo "dest   : $DEST (owner $OWNER, mode 0600)"
  echo ""
  echo "Plan (from manifest):"
  printf '%s\n' "$ROWS" | while IFS='|' read -r key type icloud value; do
    case "$type" in
      secret)   echo "  SECRET   $key (icloud=$icloud; value from Keychain)" ;;
      constant) echo "  CONSTANT $key=$value" ;;
      *)        echo "  UNKNOWN  $key (type=$type)" ;;
    esac
  done
  exit 0
fi

if [ "$AUDIT" -eq 1 ]; then
  echo "=== AUDIT $SERVICE @ $TARGET ==="
  STAT=$(ssh -n -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=10 \
         "$SSH_USER@$TARGET_HOST" "stat -c '%a %U:%G %s' '$DEST' 2>&1" || true)
  echo "$STAT"
  if echo "$STAT" | grep -qE "^600 $OWNER [0-9]+$"; then
    echo "OK: .env present, 0600, owner=$OWNER"
    exit 0
  else
    echo "FAIL: .env not matching expected stat on $TARGET"
    exit 1
  fi
fi

echo "=== PRE-FLIGHT ==="
FAIL_PREFLIGHT=0
while IFS='|' read -r key type icloud value; do
  [ "$type" = "secret" ] || continue
  if security find-generic-password -s "nous-agaas/$key" -a nous >/dev/null 2>&1; then
    echo "ok: Keychain has nous-agaas/$key"
  else
    echo "MISSING: nous-agaas/$key — add via: echo -n VALUE | tools/secrets-keychain-add.swift nous-agaas/$key${icloud:+ --icloud}"
    FAIL_PREFLIGHT=1
  fi
done <<< "$ROWS"
[ "$FAIL_PREFLIGHT" -eq 0 ] || { echo "FAIL: pre-flight — populate Keychain first" >&2; exit 1; }

cleanup() {
  ssh -n -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=10 \
      "$SSH_USER@$TARGET_HOST" "rm -f '$DEST.new'" 2>/dev/null || true
}
trap cleanup EXIT

{
  printf '# Generated %s by secrets-deploy.sh for service=%s target=%s\n' \
         "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SERVICE" "$TARGET"
  printf '# DO NOT EDIT BY HAND. Rotate via Keychain + re-deploy.\n\n'
  while IFS='|' read -r key type icloud value; do
    case "$type" in
      constant)
        printf '%s=%s\n' "$key" "$value"
        ;;
      secret)
        printf '%s=' "$key"
        "$READER" "$key"
        printf '\n'
        ;;
    esac
  done <<< "$ROWS"
} | ssh -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=10 \
       "$SSH_USER@$TARGET_HOST" \
       "umask 077 && cat > '$DEST.new' && \
        chown '$OWNER' '$DEST.new' 2>/dev/null || true; \
        chmod 600 '$DEST.new' && \
        mv '$DEST.new' '$DEST'"

trap - EXIT

STAT=$(ssh -n -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=10 \
       "$SSH_USER@$TARGET_HOST" "stat -c '%a %U:%G %s' '$DEST'")
echo "=== POST-DEPLOY $DEST ==="
echo "$STAT"
echo "OK: deploy complete"
