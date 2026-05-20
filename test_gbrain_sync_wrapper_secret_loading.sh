#!/bin/bash
# test_gbrain_sync_wrapper_secret_loading.sh — AP-35 credential hygiene gate.

set -u

HOST="${GBRAIN_HOST:-root@65.108.215.200}"
REMOTE_SCRIPT="${GBRAIN_SYNC_WRAPPER_SCRIPT:-/root/nous-agaas/wiki/tools/gbrain_sync_wrapper.sh}"
LOCAL_SCRIPT="${LOCAL_GBRAIN_SYNC_WRAPPER_SCRIPT:-$(cd "$(dirname "$0")/.." && pwd)/tools/gbrain_sync_wrapper.sh}"

fail=0

check_script_text() {
  local label="$1"
  local path="$2"

  bash -n "$path" || fail=1
  if grep -Eq 'OPENAI_API_KEY=.*sk-|sk-proj-' "$path"; then
    echo "$label contains an inline OpenAI key"
    fail=1
  fi
  grep -Fq "/root/.config/codex/auth.json" "$path" || {
    echo "$label does not load /root/.config/codex/auth.json"
    fail=1
  }
  grep -Fq "/root/nous-agaas/.env" "$path" || {
    echo "$label does not fall back to /root/nous-agaas/.env"
    fail=1
  }
  grep -Fq "OPENAI_API_KEY missing; refusing to create embed ghosts" "$path" || {
    echo "$label does not fail closed when OPENAI_API_KEY is missing"
    fail=1
  }
  grep -Fq 'TOOLS="${GBRAIN_TOOLS_DIR:-$WIKI/tools}"' "$path" || {
    echo "$label does not run wiki-local gbrain tools"
    fail=1
  }
}

check_local() {
  if [ ! -f "$LOCAL_SCRIPT" ]; then
    echo "missing local canonical script: $LOCAL_SCRIPT"
    fail=1
    return
  fi
  check_script_text "local sync wrapper" "$LOCAL_SCRIPT"
}

check_remote() {
  if [ "$HOST" = "local" ]; then
    test -f "$REMOTE_SCRIPT" || {
      echo "local runtime sync wrapper missing: $REMOTE_SCRIPT"
      fail=1
      return
    }
    check_script_text "local runtime sync wrapper" "$REMOTE_SCRIPT"
    OPENAI_API_KEY= GBRAIN_SYNC_WRAPPER_DRY_RUN=1 "$REMOTE_SCRIPT" | grep -Eq '^gbrain sync wrapper dry-run: key_loaded len=[1-9][0-9]*$' || {
      echo "local runtime sync wrapper could not load OPENAI_API_KEY in dry-run mode"
      fail=1
    }
    return
  fi

  ssh -o ConnectTimeout=10 "$HOST" "test -f '$REMOTE_SCRIPT' && bash -n '$REMOTE_SCRIPT'" >/dev/null || {
    echo "remote sync wrapper missing or syntax-broken: $HOST:$REMOTE_SCRIPT"
    fail=1
    return
  }
  if ssh -o ConnectTimeout=10 "$HOST" "grep -Eq 'OPENAI_API_KEY=.*sk-|sk-proj-' '$REMOTE_SCRIPT'"; then
    echo "remote sync wrapper contains an inline OpenAI key"
    fail=1
  fi
  ssh -o ConnectTimeout=10 "$HOST" "grep -Fq '/root/.config/codex/auth.json' '$REMOTE_SCRIPT'" || {
    echo "remote sync wrapper does not load /root/.config/codex/auth.json"
    fail=1
  }
  ssh -o ConnectTimeout=10 "$HOST" "grep -Fq '/root/nous-agaas/.env' '$REMOTE_SCRIPT'" || {
    echo "remote sync wrapper does not fall back to /root/nous-agaas/.env"
    fail=1
  }
  ssh -o ConnectTimeout=10 "$HOST" "grep -Fq 'OPENAI_API_KEY missing; refusing to create embed ghosts' '$REMOTE_SCRIPT'" || {
    echo "remote sync wrapper does not fail closed when OPENAI_API_KEY is missing"
    fail=1
  }
  ssh -o ConnectTimeout=10 "$HOST" "grep -Fq 'TOOLS=\"\${GBRAIN_TOOLS_DIR:-\$WIKI/tools}\"' '$REMOTE_SCRIPT'" || {
    echo "remote sync wrapper does not run wiki-local gbrain tools"
    fail=1
  }
  ssh -o ConnectTimeout=10 "$HOST" "OPENAI_API_KEY= GBRAIN_SYNC_WRAPPER_DRY_RUN=1 '$REMOTE_SCRIPT' | grep -Eq '^gbrain sync wrapper dry-run: key_loaded len=[1-9][0-9]*$'" || {
    echo "remote sync wrapper could not load OPENAI_API_KEY in dry-run mode"
    fail=1
  }
}

check_local
check_remote

if [ "$fail" -ne 0 ]; then
  echo "FAIL: gbrain sync wrapper credential hygiene drift"
  exit 1
fi

echo "OK: gbrain sync wrapper loads OpenAI key from auth/env and has no inline key"
