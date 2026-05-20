#!/bin/bash
# test_gbrain_autopilot_secret_loading.sh — AP-34 credential hygiene gate.

set -u

HOST="${GBRAIN_HOST:-root@65.108.215.200}"
REMOTE_SCRIPT="${GBRAIN_AUTOPILOT_SCRIPT:-/root/.gbrain/autopilot-run.sh}"
LOCAL_SCRIPT="${LOCAL_GBRAIN_AUTOPILOT_SCRIPT:-$(cd "$(dirname "$0")/.." && pwd)/tools/gbrain-autopilot-run.sh}"

fail=0

check_runner_content() {
  local label="$1"
  local script="$2"

  grep -Fq "/root/.config/codex/auth.json" "$script" || {
    echo "$label autopilot script does not load /root/.config/codex/auth.json"
    fail=1
  }
  grep -Fq "GBRAIN_OPENAI_COMPAT_ENV" "$script" || {
    echo "$label autopilot script does not support the OpenAI-compatible proxy env"
    fail=1
  }
  grep -Fq "flock -n /var/lock/gbrain-autopilot.lock" "$script" || {
    echo "$label autopilot script lost the autopilot flock"
    fail=1
  }
  grep -Fq 'gbrain_link_builder.py' "$script" || {
    echo "$label autopilot script does not rebuild custom gbrain links"
    fail=1
  }
  grep -Fq 'sync --repo "$WIKI" --no-embed' "$script" || {
    echo "$label autopilot script does not run a bounded wiki sync cycle"
    fail=1
  }
  grep -Fq 'extract all --dir "$WIKI"' "$script" || {
    echo "$label autopilot script does not extract links/timeline in the cycle"
    fail=1
  }
  grep -Fq 'embed --stale' "$script" || {
    echo "$label autopilot script does not embed stale chunks in the cycle"
    fail=1
  }
  grep -Fq 'GBRAIN_AUTOPILOT_ONCE' "$script" || {
    echo "$label autopilot script lacks a one-cycle verification mode"
    fail=1
  }
  grep -Fq 'GBRAIN_AUTOPILOT_CMD_TIMEOUT' "$script" || {
    echo "$label autopilot script does not expose per-command timeout control"
    fail=1
  }
  grep -Fq 'timeout -k 10s "$CMD_TIMEOUT"' "$script" || {
    echo "$label autopilot script does not bound gbrain subcommands with timeout"
    fail=1
  }
  if grep -Fq '"$GBRAIN" autopilot' "$script"; then
    echo "$label autopilot script delegates to the non-returning gbrain autopilot daemon"
    fail=1
  fi
  # AP-99 / AP-100 (codex council 2026-05-20): assert the lying-log gate is wired
  # so canonical-vs-runtime drift cannot recur. Any future redeploy that strips
  # the gate must fail this test, not silently downgrade observability.
  grep -Fq 'test_no_lying_logs.py' "$script" || {
    echo "$label autopilot script does not invoke the AP-99 lying-log gate (test_no_lying_logs.py)"
    fail=1
  }
  grep -Fq 'tg_send.sh' "$script" || {
    echo "$label autopilot script does not fire tg_send.sh alert on AP-99 gate failure"
    fail=1
  }
  grep -Fq 'cycle_tmp' "$script" || {
    echo "$label autopilot script does not capture cycle output to a tmp file for gating"
    fail=1
  }
  grep -Fq 'AP-99' "$script" || {
    echo "$label autopilot script does not reference AP-99 wiring (gate is unmarked)"
    fail=1
  }
  grep -Fq 'PIPESTATUS[1]' "$script" || {
    echo "$label autopilot script does not check tee integrity via PIPESTATUS[1] (AP-100 P2 fix)"
    fail=1
  }
  # AP-101 (codex council 2026-05-20): assert per-phase gating + tg_send fallback.
  grep -Fq 'run_lying_log_gate' "$script" || {
    echo "$label autopilot script does not use run_lying_log_gate helper (AP-101 P3-1)"
    fail=1
  }
  grep -Fq 'embed_tmp' "$script" || {
    echo "$label autopilot script does not gate after embed --stale specifically (AP-101 P3-1: link-builder runs against degraded state on lying-log)"
    fail=1
  }
  grep -Fq 'alerts-fallback.jsonl' "$script" || {
    echo "$label autopilot script does not log tg_send delivery failures to fallback JSONL (AP-101 P3-2)"
    fail=1
  }
  grep -Fq 'post-embed' "$script" || {
    echo "$label autopilot script does not label the post-embed gate context (AP-101 audit-trail)"
    fail=1
  }
}

check_local() {
  if [ ! -f "$LOCAL_SCRIPT" ]; then
    echo "missing local canonical script: $LOCAL_SCRIPT"
    fail=1
    return
  fi
  bash -n "$LOCAL_SCRIPT" || fail=1
  if grep -Eq 'OPENAI_API_KEY=.*sk-|sk-proj-' "$LOCAL_SCRIPT"; then
    echo "local canonical script contains an inline OpenAI key"
    fail=1
  fi
  check_runner_content "local canonical" "$LOCAL_SCRIPT"
}

check_remote() {
  if [ "$HOST" = "local" ]; then
    test -f "$REMOTE_SCRIPT" && bash -n "$REMOTE_SCRIPT" || {
      echo "local runtime autopilot script missing or syntax-broken: $REMOTE_SCRIPT"
      fail=1
      return
    }
    if grep -Eq 'OPENAI_API_KEY=.*sk-|sk-proj-' "$REMOTE_SCRIPT"; then
      echo "local runtime autopilot script contains an inline OpenAI key"
      fail=1
    fi
    check_runner_content "local runtime" "$REMOTE_SCRIPT"
    OPENAI_API_KEY= GBRAIN_AUTOPILOT_DRY_RUN=1 "$REMOTE_SCRIPT" | grep -Eq '^gbrain autopilot dry-run: key_loaded len=[1-9][0-9]*$' || {
      echo "local runtime autopilot script could not load OPENAI_API_KEY in dry-run mode"
      fail=1
    }
    return
  fi

  ssh -o ConnectTimeout=10 "$HOST" "test -f '$REMOTE_SCRIPT' && bash -n '$REMOTE_SCRIPT'" >/dev/null || {
    echo "remote autopilot script missing or syntax-broken: $HOST:$REMOTE_SCRIPT"
    fail=1
    return
  }
  if ssh -o ConnectTimeout=10 "$HOST" "grep -Eq 'OPENAI_API_KEY=.*sk-|sk-proj-' '$REMOTE_SCRIPT'"; then
    echo "remote autopilot script contains an inline OpenAI key"
    fail=1
  fi
  ssh -o ConnectTimeout=10 "$HOST" "grep -Fq '/root/.config/codex/auth.json' '$REMOTE_SCRIPT' && grep -Fq 'GBRAIN_OPENAI_COMPAT_ENV' '$REMOTE_SCRIPT' && grep -Fq 'flock -n /var/lock/gbrain-autopilot.lock' '$REMOTE_SCRIPT' && grep -Fq 'gbrain_link_builder.py' '$REMOTE_SCRIPT' && grep -Fq 'sync --repo \"\$WIKI\" --no-embed' '$REMOTE_SCRIPT' && grep -Fq 'extract all --dir \"\$WIKI\"' '$REMOTE_SCRIPT' && grep -Fq 'embed --stale' '$REMOTE_SCRIPT' && grep -Fq 'GBRAIN_AUTOPILOT_ONCE' '$REMOTE_SCRIPT' && grep -Fq 'GBRAIN_AUTOPILOT_CMD_TIMEOUT' '$REMOTE_SCRIPT' && grep -Fq 'timeout -k 10s \"\$CMD_TIMEOUT\"' '$REMOTE_SCRIPT' && ! grep -Fq '\"\$GBRAIN\" autopilot' '$REMOTE_SCRIPT'" || {
    echo "remote autopilot script lost the bounded-cycle runner contract"
    fail=1
  }
  # AP-99 / AP-100 (codex council 2026-05-20): assert lying-log gate wired on remote too.
  ssh -o ConnectTimeout=10 "$HOST" "grep -Fq 'test_no_lying_logs.py' '$REMOTE_SCRIPT' && grep -Fq 'tg_send.sh' '$REMOTE_SCRIPT' && grep -Fq 'cycle_tmp' '$REMOTE_SCRIPT' && grep -Fq 'AP-99' '$REMOTE_SCRIPT' && grep -Fq 'PIPESTATUS[1]' '$REMOTE_SCRIPT'" || {
    echo "remote autopilot script does not have AP-99 lying-log gate wiring (test_no_lying_logs.py / tg_send.sh / cycle_tmp / PIPESTATUS[1])"
    fail=1
  }
  # AP-101 (codex council 2026-05-20): assert per-phase gating + fallback on remote.
  ssh -o ConnectTimeout=10 "$HOST" "grep -Fq 'run_lying_log_gate' '$REMOTE_SCRIPT' && grep -Fq 'embed_tmp' '$REMOTE_SCRIPT' && grep -Fq 'alerts-fallback.jsonl' '$REMOTE_SCRIPT' && grep -Fq 'post-embed' '$REMOTE_SCRIPT'" || {
    echo "remote autopilot script does not have AP-101 per-phase gating + tg_send fallback (run_lying_log_gate / embed_tmp / alerts-fallback.jsonl / post-embed)"
    fail=1
  }
  ssh -o ConnectTimeout=10 "$HOST" "OPENAI_API_KEY= GBRAIN_AUTOPILOT_DRY_RUN=1 '$REMOTE_SCRIPT' | grep -Eq '^gbrain autopilot dry-run: key_loaded len=[1-9][0-9]*$'" || {
    echo "remote autopilot script could not load OPENAI_API_KEY in dry-run mode"
    fail=1
  }
}

check_local
check_remote

if [ "$fail" -ne 0 ]; then
  echo "FAIL: gbrain autopilot credential hygiene drift"
  exit 1
fi

echo "OK: gbrain autopilot loads OpenAI key from auth/env and has no inline key"
