#!/bin/bash
# nous_gpu_collector_health.sh — 5-min health probe for the Nous-GPU Phase-0/1
# sniff-target collector.
#
# Source skill: [[infrastructure]], [[PHASE-0-COLLECTOR-DEPLOYMENT-2026-04-21]].
# Runs from Air via `com.nous.nous-gpu-collector-health` launchd every 5 min.
# State-change alerting only — Telegram alert on transition OK→fail or fail→OK,
# silent on steady-state. Logs every run to ~/nous-agaas/logs/collector-health.out.
#
# Checks:
#   1. Tailscale ping to 100.70.222.21 (2s timeout)
#   2. Docker container `nous-collector` running on Nous-GPU (SSH, 5s timeout)
#   3. Latest active pcap: newest *.pcap in /home/nous-admin/collector/pcap/
#      with mtime within last 15 minutes. Fail if none.
#   4. Growth alarm: delta between this probe and last probe of the SAME pcap
#      file must be >= MIN_DELTA_BYTES (default 10 KB). State-tracked by
#      (pcap_path, size) tuple so rotation / rename resets delta cleanly.
#
# History: session-56 v1 hardcoded `PCAP=/home/nous-admin/collector/pcap/collector.pcap`
# which went stale once collector flipped to `-i wg0 -w /pcap/wg0-collector.pcap`
# — probe false-green'd on a 24-byte stub. Session-56 bug-fix replaces with
# latest-mtime lookup (future-proof: Phase-2 per-camera pcap splits OK) + delta
# alarm (catches silent-stream-stop). See `infrastructure` skill AP covering
# "shipped-artifact path coupling — audit consumers on any output-path rename."

set -u
QUIET=0
for arg in "$@"; do case "$arg" in --quiet) QUIET=1 ;; esac; done
log() { [ "$QUIET" -eq 1 ] || echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }

NAME="nous-collector"
TS_IP="100.70.222.21"
PCAP_DIR="/home/nous-admin/collector/pcap"
MTIME_WINDOW_MIN=15      # must see a pcap write within this window
MIN_DELTA_BYTES=10240    # 10 KB; at ~0.9 Mbit/s sustained we expect 10s of MB per 5-min probe
MIN_WG_PAYLOAD_BYTES=1024 # Ignore WireGuard keepalive-scale RX movement
STATE_DIR="$HOME/.nous-gpu-collector-health"
STATE_LAST="$STATE_DIR/last_state"
STATE_SIZE="$STATE_DIR/last_pcap_size"
STATE_PCAP="$STATE_DIR/last_pcap_path"
STATE_WG_RX="$STATE_DIR/last_wg_rx"
STATE_WG_TX="$STATE_DIR/last_wg_tx"
TG_SEND="$HOME/nous-agaas/tools/tg_send.sh"
mkdir -p "$STATE_DIR"

last_state=0
[ -f "$STATE_LAST" ] && last_state=$(cat "$STATE_LAST")

notify() {
  # $1 = "down" or "recovered"; $2 = free-form message
  [ -x "$TG_SEND" ] || return 0
  bash "$TG_SEND" "$2" >/dev/null 2>&1 || true
}

fail() {
  # $1 = reason
  log "FAIL: $1"
  if [ "$last_state" -eq 0 ]; then
    notify "down" "🔴 Nous-GPU collector DOWN — $1"
  fi
  echo 1 > "$STATE_LAST"
  exit 1
}

is_uint() {
  case "${1:-}" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

wg_context() {
  # Adds context that separates "GPU dead" from "upstream stopped sending".
  # Uses the WireGuard container because host sudo may not be available.
  local now hs age transfer rx tx last_rx last_tx rx_delta tx_delta verdict
  now=$(date +%s)
  hs=$(ssh -o BatchMode=yes -o ConnectTimeout=5 nous-gpu \
    "docker exec nous-wg wg show wg0 latest-handshakes 2>/dev/null | awk 'NR==1 {print \$2}'" 2>/dev/null | tr -d '[:space:]')
  transfer=$(ssh -o BatchMode=yes -o ConnectTimeout=5 nous-gpu \
    "docker exec nous-wg wg show wg0 transfer 2>/dev/null | awk 'NR==1 {print \$2, \$3}'" 2>/dev/null)

  rx=$(echo "$transfer" | awk '{print $1}')
  tx=$(echo "$transfer" | awk '{print $2}')
  last_rx=$(cat "$STATE_WG_RX" 2>/dev/null || echo "")
  last_tx=$(cat "$STATE_WG_TX" 2>/dev/null || echo "")

  if is_uint "$hs" && [ "$hs" -gt 0 ]; then
    age=$((now - hs))
  else
    age="unknown"
  fi

  if is_uint "$rx"; then
    echo "$rx" > "$STATE_WG_RX"
  fi
  if is_uint "$tx"; then
    echo "$tx" > "$STATE_WG_TX"
  fi

  if is_uint "$rx" && is_uint "$last_rx"; then
    rx_delta=$((rx - last_rx))
  else
    rx_delta="unknown"
  fi
  if is_uint "$tx" && is_uint "$last_tx"; then
    tx_delta=$((tx - last_tx))
  else
    tx_delta="unknown"
  fi

  verdict="wg context inconclusive"
  if is_uint "$age" && [ "$age" -lt 300 ]; then
    if is_uint "$rx_delta" && [ "$rx_delta" -ge "$MIN_WG_PAYLOAD_BYTES" ]; then
      verdict="wg receiving data; collector filter/path may be wrong"
    elif is_uint "$rx_delta"; then
      verdict="wg alive, only keepalive-scale RX since last probe; upstream mirror likely stopped"
    fi
  elif is_uint "$age"; then
    verdict="wg handshake stale"
  fi

  printf 'wg_handshake_age=%ss wg_rx_delta=%sB wg_tx_delta=%sB; %s' \
    "$age" "$rx_delta" "$tx_delta" "$verdict"
}

# (1) Tailscale reachability — 2s ICMP timeout is too tight for Tailscale NAT
# traversal (relay/DERP routes can take 3-5s on first packet). False-negative
# class burned 4191 cycles before 2026-05-12 audit. Use 5s primary + SSH fallback:
# if ICMP doesn't make it but SSH does, host is reachable via Tailscale and the
# collector check should pass.
if ! ping -c 1 -W 5 "$TS_IP" >/dev/null 2>&1; then
  if ! ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
       "nous-admin@$TS_IP" "true" >/dev/null 2>&1; then
    fail "Tailscale unreachable $TS_IP (ICMP >5s AND SSH unreachable)"
  fi
  log "INFO: ICMP timeout but SSH reachable — relay/NAT-traversal latency, proceeding"
fi

# (2) Container running (quick SSH)
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 nous-gpu \
     "docker ps --filter name=$NAME --format '{{.Names}}' | grep -q $NAME" 2>/dev/null; then
  fail "docker container '$NAME' not running on nous-gpu"
fi

# (3) Latest active pcap — newest *.pcap with mtime within window
LATEST_PCAP=$(ssh -o BatchMode=yes -o ConnectTimeout=5 nous-gpu \
  "find $PCAP_DIR -maxdepth 1 -name '*.pcap' -type f -mmin -$MTIME_WINDOW_MIN -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-")

if [ -z "$LATEST_PCAP" ]; then
  fail "no pcap written in last ${MTIME_WINDOW_MIN} min under $PCAP_DIR — $(wg_context)"
fi

curr_size=$(ssh -o BatchMode=yes -o ConnectTimeout=5 nous-gpu \
  "stat -c %s $LATEST_PCAP 2>/dev/null || echo 0")

last_pcap=$(cat "$STATE_PCAP" 2>/dev/null || echo "")
last_size=$(cat "$STATE_SIZE" 2>/dev/null || echo 0)
echo "$LATEST_PCAP" > "$STATE_PCAP"
echo "$curr_size" > "$STATE_SIZE"

# If the tracked pcap file changed (rotation/rename/Phase transition), reset delta
# state — no delta alarm this cycle; next cycle compares against fresh baseline.
if [ "$LATEST_PCAP" != "$last_pcap" ]; then
  log "OK pcap=${LATEST_PCAP##*/} size=$curr_size (new/rotated — delta baseline reset)"
  if [ "$last_state" -ne 0 ]; then
    notify "recovered" "✅ Nous-GPU collector recovered (tracking ${LATEST_PCAP##*/}, size=$curr_size B)"
  fi
  echo 0 > "$STATE_LAST"
  exit 0
fi

# Same path can be truncated/recreated by tcpdump/container rotation. Treat the
# size drop as a fresh baseline; the next probe will enforce growth again.
if is_uint "$curr_size" && is_uint "$last_size" && [ "$curr_size" -lt "$last_size" ]; then
  log "OK pcap=${LATEST_PCAP##*/} size=$curr_size previous_size=$last_size (truncated/rotated — delta baseline reset)"
  if [ "$last_state" -ne 0 ]; then
    notify "recovered" "✅ Nous-GPU collector recovered (pcap=${LATEST_PCAP##*/} truncated/rotated, size=$curr_size B)"
  fi
  echo 0 > "$STATE_LAST"
  exit 0
fi

# (4) Growth alarm — same pcap, delta must be >= MIN_DELTA_BYTES
delta=$((curr_size - last_size))
if [ "$delta" -lt "$MIN_DELTA_BYTES" ]; then
  fail "pcap ${LATEST_PCAP##*/} delta=+$delta B (< $MIN_DELTA_BYTES min) — $(wg_context)"
fi

log "OK pcap=${LATEST_PCAP##*/} size=$curr_size delta=+$delta last_state=$last_state"

# Recovery transition
if [ "$last_state" -ne 0 ]; then
  notify "recovered" "✅ Nous-GPU collector recovered (pcap=${LATEST_PCAP##*/}, size=$curr_size B, delta=+$delta B since last probe)"
fi
echo 0 > "$STATE_LAST"
exit 0
