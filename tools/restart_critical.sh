#!/usr/bin/env bash
# Restart guard for critical Nous AGaaS Air/VPS jobs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PYTHON="${PYTHON:-/opt/homebrew/bin/python3}"
WINDOW_SECONDS="${RESTART_CRITICAL_WINDOW_SECONDS:-600}"
DRY_RUN="${RESTART_CRITICAL_DRY_RUN:-0}"
CORRELATION_ID="${RESTART_CRITICAL_CORRELATION_ID:-restart-critical-$(date -u +%Y%m%dT%H%M%SZ)}"
ACTOR="${RESTART_CRITICAL_ACTOR:-codex-pane2}"
VPS_SSH="${RESTART_CRITICAL_VPS_SSH:-root@65.108.215.200}"
STATE_DIR="${RESTART_CRITICAL_STATE_DIR:-/Users/madia/nous-agaas/state/restart_critical}"

uid="$(id -u)"

json_log() {
  local target="$1" action="$2" status="$3" detail="$4"
  RESTART_TARGET="$target" \
  RESTART_ACTION="$action" \
  RESTART_STATUS="$status" \
  RESTART_DETAIL="$detail" \
  RESTART_ACTOR="$ACTOR" \
  RESTART_CORRELATION_ID="$CORRELATION_ID" \
  "$PYTHON" - "$SCRIPT_DIR" <<'PY'
import os
import sys
import time

sys.path.insert(0, sys.argv[1])
from log_event import append_event

target = os.environ["RESTART_TARGET"]
action = os.environ["RESTART_ACTION"]
status = os.environ["RESTART_STATUS"]
detail = os.environ["RESTART_DETAIL"]
payload = {
    "target": target,
    "action": action,
    "status": status,
    "detail": detail,
    "intent_id": f"restart-critical:{target}:{int(time.time_ns())}",
    "idempotency_key": f"restart-critical:{target}:{action}:{int(time.time_ns())}",
}
append_event(
    source="restart_critical",
    external_id=target,
    actor=os.environ["RESTART_ACTOR"],
    payload=payload,
    correlation_id=os.environ["RESTART_CORRELATION_ID"],
)
PY
}

print_result() {
  local target="$1" action="$2" status="$3" detail="$4"
  printf '%s target=%s action=%s status=%s detail=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$target" "$action" "$status" "$detail"
  json_log "$target" "$action" "$status" "$detail"
}

launchd_line_state() {
  local line="${1:-}"
  if [ -z "$line" ]; then
    echo "restart label_missing"
    return 0
  fi
  # shellcheck disable=SC2086
  set -- $line
  local pid="${1:-}" exit_code="${2:-}"
  if [ -z "$pid" ] || [ -z "$exit_code" ]; then
    echo "restart bad_launchctl_line"
  elif [ "$pid" != "-" ]; then
    echo "ok running_pid_$pid"
  elif [ "$exit_code" = "0" ]; then
    echo "ok clean_exit"
  else
    echo "failed exit_$exit_code"
  fi
}

safe_state_name() {
  printf '%s' "$1" | tr -c 'A-Za-z0-9_.-' '_'
}

failure_age_for_label() {
  local label="$1" detail="$2"
  local now path mtime
  now="$(date +%s)"
  mkdir -p "$STATE_DIR"
  path="$STATE_DIR/$(safe_state_name "$label.$detail").first_seen"
  if [ ! -e "$path" ]; then
    printf '%s\n' "$now" > "$path"
    echo 0
  else
    mtime="$(stat -f %m "$path" 2>/dev/null || echo "$now")"
    echo $((now - mtime))
  fi
}

clear_failure_for_label() {
  local label="$1"
  local prefix
  mkdir -p "$STATE_DIR"
  prefix="$STATE_DIR/$(safe_state_name "$label")."
  rm -f "$prefix"*.first_seen 2>/dev/null || true
}

restart_launchd() {
  local label="$1" plist="$2"
  if [ "$DRY_RUN" = "1" ]; then
    return 0
  fi
  launchctl bootout "gui/$uid/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$uid" "$plist"
  launchctl kickstart -k "gui/$uid/$label" 2>/dev/null || true
}

check_launchd_target() {
  local target="$1" label="$2" plist="$3"
  local line state verdict detail age
  line="$(launchctl list | awk -v lbl="$label" '$3 == lbl {print $1 " " $2 " " $3}')"
  state="$(launchd_line_state "$line")"
  verdict="${state%% *}"
  detail="${state#* }"
  if [ "$verdict" = "ok" ]; then
    clear_failure_for_label "$label"
    print_result "$target" "check" "ok" "$detail"
    return 0
  fi
  if [ "$verdict" = "failed" ]; then
    age="$(failure_age_for_label "$label" "$detail")"
    if [ "$age" -gt "$WINDOW_SECONDS" ]; then
      print_result "$target" "check" "stale_failure_no_restart" "$detail observed_age=${age}s"
      return 0
    fi
    restart_launchd "$label" "$plist"
    clear_failure_for_label "$label"
    print_result "$target" "restart" "restarted" "$detail observed_age=${age}s"
    return 0
  fi
  restart_launchd "$label" "$plist"
  clear_failure_for_label "$label"
  print_result "$target" "restart" "restarted" "$detail"
}

docker_finished_recent() {
  local finished_at="$1"
  "$PYTHON" - "$finished_at" "$WINDOW_SECONDS" <<'PY'
import datetime as dt
import sys

finished = sys.argv[1]
window = int(sys.argv[2])
if not finished or finished.startswith("0001-"):
    print("recent")
    raise SystemExit(0)
value = finished.replace("Z", "+00:00")
try:
    t = dt.datetime.fromisoformat(value)
except ValueError:
    print("recent")
    raise SystemExit(0)
age = (dt.datetime.now(dt.UTC) - t.astimezone(dt.UTC)).total_seconds()
print("recent" if age <= window else f"stale:{int(age)}")
PY
}

check_openclaw() {
  local inspect running health exit_code finished recency
  if ! inspect="$(docker inspect -f '{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{.State.ExitCode}} {{.State.FinishedAt}}' openclaw 2>/dev/null)"; then
    print_result "openclaw-docker" "restart" "failed" "container_missing"
    return 1
  fi
  # shellcheck disable=SC2086
  set -- $inspect
  running="${1:-false}"
  health="${2:-none}"
  exit_code="${3:-0}"
  finished="${4:-}"
  if [ "$running" = "true" ] && { [ "$health" = "healthy" ] || [ "$health" = "none" ]; }; then
    print_result "openclaw-docker" "check" "ok" "running=$running health=$health"
    return 0
  fi
  recency="$(docker_finished_recent "$finished")"
  if [ "$running" != "true" ] && [[ "$recency" == stale:* ]]; then
    print_result "openclaw-docker" "check" "stale_failure_no_restart" "running=$running health=$health exit=$exit_code finished=$finished $recency"
    return 0
  fi
  if [ "$DRY_RUN" != "1" ]; then
    docker restart openclaw >/dev/null
  fi
  print_result "openclaw-docker" "restart" "restarted" "running=$running health=$health exit=$exit_code finished=$finished"
}

check_autopilot() {
  local status cron_line start_out
  status="$(ssh -n -o BatchMode=yes -o ConnectTimeout=8 "$VPS_SSH" "pgrep -af '/root/.gbrain/autopilot-run.sh __locked' | head -1" 2>/dev/null || true)"
  if [ -n "$status" ]; then
    print_result "autopilot" "check" "ok" "$status"
    return 0
  fi
  cron_line="$(ssh -n -o BatchMode=yes -o ConnectTimeout=8 "$VPS_SSH" "crontab -l 2>/dev/null | grep -F \"GBRAIN_AUTOPILOT_ONCE=1 '/root/.gbrain/autopilot-run.sh'\" | head -1" 2>/dev/null || true)"
  if [ -n "$cron_line" ]; then
    print_result "autopilot" "check" "ok" "scheduled_one_shot: $cron_line"
    return 0
  fi
  if [ "$DRY_RUN" = "1" ]; then
    print_result "autopilot" "restart" "restarted" "dry_run_missing_process_and_scheduler"
    return 0
  fi
  start_out="$(ssh -n -o BatchMode=yes -o ConnectTimeout=8 "$VPS_SSH" "nohup env GBRAIN_AUTOPILOT_ONCE=1 /root/.gbrain/autopilot-run.sh >> /root/.gbrain/autopilot.log 2>&1 & echo started_pid=\$!" 2>&1)"
  print_result "autopilot" "restart" "restarted" "$start_out"
}

self_test() {
  local got tmp
  got="$(launchd_line_state '123 -15 com.nous.telegram-poll')"
  [ "$got" = "ok running_pid_123" ] || { echo "bad live-pid parse: $got"; return 1; }
  got="$(launchd_line_state '- 0 com.nous.telegram-poll')"
  [ "$got" = "ok clean_exit" ] || { echo "bad clean-exit parse: $got"; return 1; }
  got="$(launchd_line_state '- 1 com.nous.telegram-poll')"
  [ "$got" = "failed exit_1" ] || { echo "bad failed-exit parse: $got"; return 1; }
  got="$(launchd_line_state '')"
  [ "$got" = "restart label_missing" ] || { echo "bad missing-label parse: $got"; return 1; }
  tmp="$(mktemp)"
  echo "x" > "$tmp"
  [ "$(docker_finished_recent '0001-01-01T00:00:00Z')" = "recent" ] || { echo "bad docker zero-time parse"; return 1; }
  rm -f "$tmp"
  echo "restart_critical_self_test=ok"
}

main() {
  if [ "${1:-}" = "--self-test" ]; then
    self_test
    return $?
  fi
  check_launchd_target "telegram-poll" "com.nous.telegram-poll" "/Users/madia/Library/LaunchAgents/com.nous.telegram-poll.plist"
  check_launchd_target "litellm" "com.nous.litellm" "/Users/madia/Library/LaunchAgents/com.nous.litellm.plist"
  check_openclaw
  check_launchd_target "satory-camera-doctor" "com.nous.satory-camera-doctor" "/Users/madia/Library/LaunchAgents/com.nous.satory-camera-doctor.plist"
  check_autopilot
}

main "$@"
