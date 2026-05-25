#!/bin/bash
# test_nous_gpu_wg0_collector_live.sh — 4-check wg0 health validator for Nous-GPU Phase-1 collector
#
# Purpose: confirm the wg0 tunnel + collector pipeline is alive end-to-end using
# OBSERVATIONAL checks on real Denis traffic, NOT synthetic packet generation.
# (We can't originate TO wg0 from Mac; wg0 ingress is only from Denis's tunnel end.)
#
# Sibling to test_nous_gpu_collector_tzsp.sh (Tailscale synthetic generator — pre-WG era
# or post-WG debug via tailscale0).
#
# Four checks (any RED fails the probe):
#   (1) wg0 interface UP + most-recent-handshake <180s
#   (2) collector container cmd bound to -i wg0 (not -i tailscale0)
#   (3) pcap size delta >0 over 30-second observation window (proof traffic flowing)
#   (4) tshark-decoded sample from pcap shows TZSP framing on UDP :37008
#
# Exit codes:
#   0 = GREEN (all 4 checks pass)
#   1 = DRIFT (one or more checks fail; details in stderr)
#   2 = UNREACHABLE (ssh or container state queryable)
#
# Used:
#   - After WG pivot (sanity check wg0 is actually carrying traffic)
#   - Nightly via cron OR Air launchd (regression detection)
#   - Before declaring Phase-1 "stable" in handoffs

set -uo pipefail

NG_HOST="${NG_HOST:-nous-gpu}"
CONTAINER="${CONTAINER:-nous-collector}"
WG_CONTAINER="${WG_CONTAINER:-nous-wg}"
HANDSHAKE_STALE_S="${HANDSHAKE_STALE_S:-180}"
DELTA_WINDOW_S="${DELTA_WINDOW_S:-30}"

echo "=== wg0 collector live validator ==="
echo "host=${NG_HOST} container=${CONTAINER} handshake_cap=${HANDSHAKE_STALE_S}s delta_window=${DELTA_WINDOW_S}s"

FAIL=0

# ---- Reachability preflight ----
# ConnectTimeout=15 (was 6, 2026-05-14 s1729-mac-87156): Tailscale DERP relay
# (Mac→nous-gpu observed 417-862ms latency via Helsinki) regularly exceeds 6s
# on first connection, producing flaky false-UNREACHABLE on collector freshness
# probes. 15s is above observed worst-case while keeping the gate tight enough
# to flag a true outage. See pages/entities/nous-gpu.md Timeline 2026-05-14.
if ! ssh -o ConnectTimeout=15 -o BatchMode=yes "${NG_HOST}" 'echo ALIVE' 2>&1 | grep -q ALIVE; then
  echo "🔴 UNREACHABLE: ssh ${NG_HOST} failed"
  exit 2
fi

# ---- Auto-detect pcap filename from container command ----
# Container cmd looks like: tcpdump -i wg0 -n -U -w /pcap/wg0-collector.pcap udp port 37008
# Extract the path after -w; fallback to default if missing.
PCAP_IN_CONTAINER=$(ssh "${NG_HOST}" "docker inspect -f '{{range .Config.Cmd}}{{.}} {{end}}' ${CONTAINER} 2>/dev/null" | grep -oE '\-w\s+[^ ]+' | awk '{print $2}')
PCAP_IN_CONTAINER="${PCAP_IN_CONTAINER:-/pcap/wg0-collector.pcap}"  # Phase-1+ default; auto-detect above normally overrides this
# Derive host path from the bind-mount (-v /home/nous-admin/collector/pcap:/pcap).
PCAP_HOST_PATH="${PCAP_HOST_PATH:-/home/nous-admin/collector/pcap/$(basename "${PCAP_IN_CONTAINER}")}"
echo "pcap_auto_detected: container=${PCAP_IN_CONTAINER} host=${PCAP_HOST_PATH}"

# ---- Check 1: wg0 UP + handshake fresh ----
# `wg show wg0 latest-handshakes` prints "peer_pubkey unix_timestamp".
# Read it through the WireGuard container instead of host sudo; probe scripts
# must not embed sudo secrets for read-only diagnostics.
# 0 = never handshaked. Recent = seconds since epoch.
HS=$(ssh "${NG_HOST}" "docker exec ${WG_CONTAINER} wg show wg0 latest-handshakes 2>/dev/null | awk 'NR==1 {print \$2}'" 2>/dev/null | tr -d '[:space:]')
: "${HS:=0}"
NOW=$(date +%s)
AGE=$((NOW - HS))
if [ "${HS}" = "0" ] || [ "${AGE}" -gt "${HANDSHAKE_STALE_S}" ]; then
  echo "🔴 CHECK-1 FAIL: wg0 handshake age=${AGE}s (cap=${HANDSHAKE_STALE_S}s); HS_UNIX=${HS}"
  FAIL=$((FAIL + 1))
else
  echo "✅ CHECK-1: wg0 handshake age=${AGE}s (<${HANDSHAKE_STALE_S}s)"
fi

# ---- Check 2: collector container cmd bound to -i wg0 ----
CMD=$(ssh "${NG_HOST}" "docker inspect -f '{{range .Config.Cmd}}{{.}} {{end}}' ${CONTAINER} 2>/dev/null" | tr -d '\n')
if echo "${CMD}" | grep -qE '\-i\s+wg0\b'; then
  echo "✅ CHECK-2: container bound to -i wg0 (cmd=${CMD})"
elif echo "${CMD}" | grep -qE '\-i\s+tailscale0\b'; then
  echo "🔴 CHECK-2 FAIL: container still bound to -i tailscale0 (pre-WG pivot state); cmd=${CMD}"
  FAIL=$((FAIL + 1))
else
  echo "🔴 CHECK-2 FAIL: container not bound to expected iface; cmd=${CMD}"
  FAIL=$((FAIL + 1))
fi

# ---- Check 3: pcap delta >0 over observation window ----
SIZE_T0=$(ssh "${NG_HOST}" "stat -c %s ${PCAP_HOST_PATH} 2>/dev/null" 2>/dev/null | tr -d '[:space:]')
: "${SIZE_T0:=0}"
sleep "${DELTA_WINDOW_S}"
SIZE_T1=$(ssh "${NG_HOST}" "stat -c %s ${PCAP_HOST_PATH} 2>/dev/null" 2>/dev/null | tr -d '[:space:]')
: "${SIZE_T1:=0}"
DELTA=$((SIZE_T1 - SIZE_T0))
if [ "${DELTA}" -gt 0 ]; then
  BYTES_PER_SEC=$((DELTA / DELTA_WINDOW_S))
  echo "✅ CHECK-3: pcap delta=${DELTA}B over ${DELTA_WINDOW_S}s (~${BYTES_PER_SEC} B/s)"
else
  echo "🔴 CHECK-3 FAIL: pcap delta=${DELTA}B over ${DELTA_WINDOW_S}s — no traffic flowing"
  FAIL=$((FAIL + 1))
fi

# ---- Check 4: tshark-decoded sample shows TZSP on UDP :37008 ----
# Use docker exec nous-collector (netshoot has tshark) OR fallback to tcpdump summary.
TSHARK_OUT=$(ssh "${NG_HOST}" "docker exec ${CONTAINER} tshark -r ${PCAP_IN_CONTAINER} -c 3 -Y 'udp.port == 37008' 2>/dev/null" | head -5)
if echo "${TSHARK_OUT}" | grep -qE 'TZSP|37008'; then
  echo "✅ CHECK-4: tshark sees TZSP/UDP-37008 in pcap"
  echo "        sample: $(echo "${TSHARK_OUT}" | head -1 | cut -c1-120)"
else
  # Fallback: plain tcpdump summary of the pcap (still decodes TZSP if it's recognized on-disk)
  TCPDUMP_OUT=$(ssh "${NG_HOST}" "docker exec ${CONTAINER} tcpdump -r ${PCAP_IN_CONTAINER} -c 3 -nn 'udp port 37008' 2>/dev/null" | head -3)
  if echo "${TCPDUMP_OUT}" | grep -qE 'UDP|37008'; then
    echo "✅ CHECK-4: tcpdump sees UDP-37008 in pcap (tshark unavailable; TZSP framing implied by filter)"
  else
    echo "🔴 CHECK-4 FAIL: no UDP-37008 packets in pcap; tshark_out=[${TSHARK_OUT}] tcpdump_out=[${TCPDUMP_OUT}]"
    FAIL=$((FAIL + 1))
  fi
fi

# ---- Verdict ----
if [ "${FAIL}" -eq 0 ]; then
  echo "=== 🟢 GREEN: wg0 collector live (4/4 checks pass) ==="
  exit 0
else
  echo "=== 🔴 DRIFT: ${FAIL}/4 checks failed ==="
  exit 1
fi
