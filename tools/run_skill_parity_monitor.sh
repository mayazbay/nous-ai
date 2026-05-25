#!/usr/bin/env bash
# Launchd-driven monitor wrapping tools/test_skills_cross_host_parity.sh.
# Writes:
#   ~/nous-agaas/logs/skill-parity.log           append-only run log
#   ~/nous-agaas/logs/skill-parity-state.json    last-run state for fast peek
# Retry policy: up to 4 attempts with 150s backoff before declaring red. Sized
# to cover one full Air `com.nous.wiki-sync` cycle (StartInterval=300s) plus
# the rsync execution window, because sub-second 3-way git divergence is
# normal during high peer-session velocity but Air's wiki-sync daemon is what
# actually converges substrate (per HANDOFF-AUTO-2026-04-30-session-100-mac-
# 23069-library-audit-closeout). On first failure, also actively trigger an
# Air git pull to convert passive waiting into active convergence — cheaper
# than waiting for Air's next scheduled pull.
#
# Usage:
#   bash tools/run_skill_parity_monitor.sh        # prints final state, exit 0/1
#
# Env overrides forwarded to the underlying test:
#   AIR_HOST, OPENCLAW_NAME, SKIP_CONTAINER

set -uo pipefail

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${SKILL_PARITY_LOG_DIR:-$HOME/nous-agaas/logs}"
LOG_FILE="$LOG_DIR/skill-parity.log"
STATE_FILE="$LOG_DIR/skill-parity-state.json"

mkdir -p "$LOG_DIR"
cd "$VAULT"

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

attempt=0
max_attempts=4
backoff=150
final_status=""
final_output=""
total=0
drift=-1

while [ "$attempt" -lt "$max_attempts" ]; do
  attempt=$((attempt + 1))
  raw=$(bash tools/test_skills_cross_host_parity.sh 2>&1)
  rc=$?

  # On first failure, actively trigger Air pull instead of passively waiting
  # for Air's next scheduled wiki-sync (every 300s). Skip if SKIP_CONTAINER=1
  # which signals SSH-to-air is unavailable from this host context.
  if [ "$rc" != "0" ] && [ "$attempt" = "1" ] && [ "${SKIP_CONTAINER:-0}" != "1" ]; then
    ssh -o BatchMode=yes -o ConnectTimeout=5 "${AIR_HOST:-air}" \
      "cd ~/nous-agaas/wiki && git pull --rebase 2>&1 | tail -1" >/dev/null 2>&1 || true
  fi

  total=$(echo "$raw" | sed -n 's/^test_skills_cross_host_parity: total=\([0-9]*\) drift=\([0-9]*\).*/\1/p' | head -1)
  drift=$(echo "$raw" | sed -n 's/^test_skills_cross_host_parity: total=\([0-9]*\) drift=\([0-9]*\).*/\2/p' | head -1)
  total=${total:-0}
  drift=${drift:-99}

  final_output="$raw"

  if [ "$rc" = "0" ] && [ "$drift" = "0" ]; then
    final_status="green"
    break
  fi

  final_status="red"
  if [ "$attempt" -lt "$max_attempts" ]; then
    sleep "$backoff"
  fi
done

now=$(ts)

{
  echo "[$now] attempt=$attempt status=$final_status total=$total drift=$drift"
  if [ "$final_status" = "red" ]; then
    echo "$final_output" | sed 's/^/    /'
  fi
} >> "$LOG_FILE"

# State JSON for fast peek; written atomically via temp+mv
tmp="$STATE_FILE.tmp.$$"
cat > "$tmp" <<JSON
{
  "last_run": "$now",
  "status": "$final_status",
  "total_skills": $total,
  "drift_count": $drift,
  "attempts": $attempt
}
JSON
mv "$tmp" "$STATE_FILE"

if [ "$final_status" = "green" ]; then
  echo "GREEN: $total/$total skills byte-identical across 4 hosts (state=$STATE_FILE)"
  exit 0
fi
echo "RED: drift=$drift skills after $attempt attempts (log=$LOG_FILE)"
exit 1
