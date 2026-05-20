#!/bin/bash
# gbrain-autopilot-run.sh — cron entrypoint for gbrain autopilot.
#
# Runtime path on VPS: /root/.gbrain/autopilot-run.sh
# Cron: */5 * * * * '/root/.gbrain/autopilot-run.sh' >> '/root/.gbrain/autopilot.log' 2>&1

set -euo pipefail

export PATH="/root/.bun/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export DATABASE_URL="${DATABASE_URL:-postgresql://gbrain:gbrain2026@localhost:5432/gbrain}"

load_openai_compatible_proxy() {
  local proxy_env="${GBRAIN_OPENAI_COMPAT_ENV:-/root/.gbrain/openai-compatible.env}"
  if [ -f "$proxy_env" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$proxy_env"
    set +a
  fi
}

load_openai_key() {
  if [ -n "${OPENAI_API_KEY:-}" ]; then
    return 0
  fi

  local key=""
  if [ -f /root/.config/codex/auth.json ]; then
    key="$(python3 - <<'PY' 2>/dev/null || true
import json
from pathlib import Path

path = Path("/root/.config/codex/auth.json")
data = json.loads(path.read_text())
print(data.get("OPENAI_API_KEY", ""))
PY
)"
  fi

  if [ -z "$key" ] && [ -f /root/nous-agaas/.env ]; then
    key="$(grep -E '^OPENAI_API_KEY=' /root/nous-agaas/.env 2>/dev/null | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true)"
  fi

  if [ -n "$key" ]; then
    export OPENAI_API_KEY="$key"
  fi
}

load_openai_compatible_proxy
load_openai_key
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] gbrain autopilot: OPENAI_API_KEY missing; refusing to create embed ghosts" >&2
  exit 2
fi

if [ "${GBRAIN_AUTOPILOT_DRY_RUN:-0}" = "1" ]; then
  echo "gbrain autopilot dry-run: key_loaded len=${#OPENAI_API_KEY}"
  exit 0
fi

GBRAIN="${GBRAIN_BIN:-/opt/nous-agaas/gbrain/bin/gbrain}"
WIKI="${GBRAIN_WIKI_DIR:-/root/nous-agaas/wiki}"
TOOLS="${GBRAIN_TOOLS_DIR:-$WIKI/tools}"
INTERVAL="${GBRAIN_AUTOPILOT_INTERVAL:-300}"
CMD_TIMEOUT="${GBRAIN_AUTOPILOT_CMD_TIMEOUT:-240}"
export GBRAIN WIKI TOOLS INTERVAL CMD_TIMEOUT

# AP-15 ghost reset: fix chunks where embedded_at is set but embedding is NULL.
# This happens when OpenAI API calls fail mid-embed. Without this reset,
# ghosts are invisible to --stale and never get re-embedded.
PGPASSWORD=gbrain2026 psql -U gbrain -d gbrain -h localhost -q -c \
  "UPDATE content_chunks SET embedded_at = NULL WHERE embedding IS NULL AND embedded_at IS NOT NULL;" \
  2>/dev/null

if [ "${1:-}" != "__locked" ]; then
  # Non-blocking flock. If another instance holds the lock, exit immediately.
  exec flock -n /var/lock/gbrain-autopilot.lock "$0" __locked
fi

child_pid=""
stop_requested=0

stop_wrapper() {
  stop_requested=1
  if [ -n "${child_pid:-}" ]; then
    kill "$child_pid" 2>/dev/null || true
    wait "$child_pid" 2>/dev/null || true
    child_pid=""
  fi
  echo "gbrain autopilot wrapper stopping."
  exit 0
}

trap stop_wrapper TERM INT

run_cmd() {
  if command -v timeout >/dev/null 2>&1; then
    timeout -k 10s "$CMD_TIMEOUT" "$@" &
  else
    "$@" &
  fi
  child_pid=$!
  wait "$child_pid"
  local rc=$?
  child_pid=""
  return "$rc"
}

# AP-101 P3-2 (codex council): tg_send delivery-failure fallback. Telegram can
# be down/token-rotated/rate-limited; without an explicit fallback signal the
# operator only sees the cycle return 1 and may miss the lying-log root cause.
# Helper appends a JSONL row + stderr line on tg_send.sh non-zero exit so the
# delivery failure is observable in autopilot.log + alerts-fallback.jsonl.
run_lying_log_gate() {
  local log_file="$1"
  local context="$2"
  if python3 "$TOOLS/test_no_lying_logs.py" --input "$log_file" >&2; then
    return 0
  fi
  local fail_count tail_snip
  fail_count="$(grep -c 'embedding failed' "$log_file" || true)"
  tail_snip="$(tail -5 "$log_file" | tr '\n' ' ' | head -c 240)"
  if ! bash "$TOOLS/tg_send.sh" "🔴 gbrain autopilot lying-log violation ($context) on $(hostname) at $(date '+%FT%TZ'). ${fail_count} 'embedding failed' lines + positive 'pages embedded' summary. tail: ${tail_snip}" >&2; then
    echo "[cycle] custom-autopilot AP-101 ALERT tg_send_failed context=$context fail_count=$fail_count" >&2
    echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"event\":\"tg_send_failed\",\"context\":\"$context\",\"fail_count\":$fail_count,\"host\":\"$(hostname)\"}" >> "${GBRAIN_ALERT_FALLBACK_LOG:-/root/.gbrain/alerts-fallback.jsonl}" 2>/dev/null || true
  fi
  return 1
}

run_cycle() {
  local start elapsed cycle_tmp embed_tmp sub_rc tee_rc
  start="$(date +%s)"
  # AP-100 P3-fix: sweep stale tmps left from prior signals/crashes.
  find /tmp -maxdepth 1 -name 'gbrain-autopilot-cycle.*.log' -mmin +30 -delete 2>/dev/null || true
  find /tmp -maxdepth 1 -name 'gbrain-autopilot-embed.*.log' -mmin +30 -delete 2>/dev/null || true
  cycle_tmp="$(mktemp /tmp/gbrain-autopilot-cycle.XXXXXX.log)"
  embed_tmp="$(mktemp /tmp/gbrain-autopilot-embed.XXXXXX.log)"
  echo "gbrain autopilot cycle starting. Repo: $WIKI"

  # AP-101 P3-1 (codex council): gate AFTER embed --stale specifically so
  # link-builder never runs against degraded embedding state. Previous design
  # gated only at end-of-chain; if embed emitted lying-log but exited 0,
  # link-builder ran on a degraded brain before the cycle was marked failed.

  # Phase 1: sync + extract (no embedding; no lying-log risk here).
  set +e
  {
    run_cmd "$GBRAIN" sync --repo "$WIKI" --no-embed && \
    run_cmd "$GBRAIN" extract all --dir "$WIKI"
  } 2>&1 | tee -a "$cycle_tmp"
  sub_rc="${PIPESTATUS[0]}"
  tee_rc="${PIPESTATUS[1]}"
  set -e
  if [ "$sub_rc" -ne 0 ]; then
    rm -f "$cycle_tmp" "$embed_tmp"
    return "$sub_rc"
  fi
  if [ "$tee_rc" -ne 0 ]; then
    echo "[cycle] custom-autopilot AP-100 ALERT tee_failed phase=1 rc=$tee_rc" >&2
    rm -f "$cycle_tmp" "$embed_tmp"
    return 1
  fi

  # Phase 2: embed --stale (where lying-log appears). Gate IMMEDIATELY.
  set +e
  run_cmd "$GBRAIN" embed --stale 2>&1 | tee -a "$embed_tmp" | tee -a "$cycle_tmp" >/dev/null
  local embed_rc embed_tee1_rc embed_tee2_rc
  embed_rc="${PIPESTATUS[0]}"
  embed_tee1_rc="${PIPESTATUS[1]}"
  embed_tee2_rc="${PIPESTATUS[2]}"
  set -e
  if [ "$embed_rc" -ne 0 ]; then
    rm -f "$cycle_tmp" "$embed_tmp"
    return "$embed_rc"
  fi
  if [ "$embed_tee1_rc" -ne 0 ] || [ "$embed_tee2_rc" -ne 0 ]; then
    echo "[cycle] custom-autopilot AP-100 ALERT tee_failed phase=2 rc1=$embed_tee1_rc rc2=$embed_tee2_rc" >&2
    rm -f "$cycle_tmp" "$embed_tmp"
    return 1
  fi

  # AP-99 / AP-101 gate POST-EMBED (link-builder skipped on violation).
  if ! run_lying_log_gate "$embed_tmp" "post-embed"; then
    rm -f "$cycle_tmp" "$embed_tmp"
    elapsed="$(($(date +%s) - start))"
    echo "[cycle] custom-autopilot AP-99 ALERT lying-logs (post-embed) exit=1 elapsed=${elapsed}s next=${INTERVAL}s"
    return 1
  fi
  rm -f "$embed_tmp"

  # Phase 3: link-builder (only reached if embed was clean).
  set +e
  run_cmd bash -c 'cd "$1" && python3 "$2/gbrain_link_builder.py"' _ "$WIKI" "$TOOLS" 2>&1 | tee -a "$cycle_tmp"
  local link_rc link_tee_rc
  link_rc="${PIPESTATUS[0]}"
  link_tee_rc="${PIPESTATUS[1]}"
  set -e
  if [ "$link_rc" -ne 0 ]; then
    rm -f "$cycle_tmp"
    return "$link_rc"
  fi
  if [ "$link_tee_rc" -ne 0 ]; then
    echo "[cycle] custom-autopilot AP-100 ALERT tee_failed phase=3 rc=$link_tee_rc" >&2
    rm -f "$cycle_tmp"
    return 1
  fi

  # Backstop: re-run gate on full cycle_tmp in case phase 1 or 3 emitted the
  # pattern. Cheap belt-and-braces. AP-99 / AP-101.
  if ! run_lying_log_gate "$cycle_tmp" "full-cycle-backstop"; then
    rm -f "$cycle_tmp"
    elapsed="$(($(date +%s) - start))"
    echo "[cycle] custom-autopilot AP-99 ALERT lying-logs (backstop) exit=1 elapsed=${elapsed}s next=${INTERVAL}s"
    return 1
  fi
  rm -f "$cycle_tmp"

  elapsed="$(($(date +%s) - start))"
  echo "[cycle] custom-autopilot elapsed=${elapsed}s next=${INTERVAL}s"
}

consecutive_errors=0
while [ "$stop_requested" -eq 0 ]; do
  if run_cycle; then
    consecutive_errors=0
  else
    consecutive_errors=$((consecutive_errors + 1))
    echo "gbrain autopilot cycle failed (${consecutive_errors}/5)" >&2
    if [ "$consecutive_errors" -ge 5 ]; then
      exit 1
    fi
  fi

  if [ "${GBRAIN_AUTOPILOT_ONCE:-0}" = "1" ]; then
    exit 0
  fi

  sleep "$INTERVAL" &
  child_pid=$!
  wait "$child_pid" || true
  child_pid=""
done
