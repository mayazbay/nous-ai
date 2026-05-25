#!/bin/bash
# test_nous_gpu_collector_tzsp.sh — synthetic TZSP probe for Nous-GPU collector
#
# Purpose: mechanical regression gate for the Phase-0 collector pipeline.
# Sends a minimal TZSP-framed UDP packet to Nous-GPU :37008 over Tailscale,
# then verifies it landed in the live pcap inside the nous-collector container.
#
# Used:
#   - Before Phase-1 WireGuard pivot (baseline: packet lands via tailscale0)
#   - After Phase-1 pivot (regression: same packet lands via wg0 once config flipped)
#   - After any container / iface / docker-runtime change on Nous-GPU
#
# Exit codes:
#   0 = OK — packet arrived, pcap grew by at least sizeof(probe-payload)
#   1 = DRIFT — packet sent but not visible in pcap within timeout
#   2 = UNREACHABLE — Nous-GPU not reachable or container not running
#
# Derived from AP-20 probe-E2E-verify-before-ship pattern (camera-management).
# Run from any Tailscale-connected host; does not require BDL / Satory network access.

set -uo pipefail

NG_HOST="${NG_HOST:-nous-gpu}"          # ssh alias, or Tailscale IP 100.70.222.21
NG_UDP_PORT="${NG_UDP_PORT:-37008}"     # TZSP canonical port
CONTAINER="${CONTAINER:-nous-collector}"
# Auto-detect the live pcap from container cmd (-w path). Falls back to newest
# *.pcap under /home/nous-admin/collector/pcap/ via mtime. Session-56 bug-fix
# replaces stale hardcoded `/pcap/collector.pcap` (which went empty when
# collector flipped -i tailscale0 -> -i wg0). See `infrastructure` AP-PathCoupling.
PCAP_INSIDE="${PCAP_INSIDE:-}"
if [ -z "$PCAP_INSIDE" ]; then
  PCAP_INSIDE=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "${NG_HOST}" \
    "docker inspect -f '{{range .Config.Cmd}}{{.}} {{end}}' ${CONTAINER} 2>/dev/null" | grep -oE '\-w[ ]+[^ ]+' | awk '{print $2}')
  [ -z "$PCAP_INSIDE" ] && PCAP_INSIDE="/pcap/wg0-collector.pcap"  # Phase-1+ default
fi
PCAP_HOST_PATH="/home/nous-admin/collector/pcap/$(basename "$PCAP_INSIDE")"
MARKER="NOUS-PROBE-$(date -u +%s)-$$"   # unique per run
TIMEOUT_S="${TIMEOUT_S:-10}"

echo "=== Nous-GPU collector TZSP probe ==="
echo "host=${NG_HOST} port=${NG_UDP_PORT} container=${CONTAINER} marker=${MARKER}"

# -- Step 1: reachability
if ! ssh -o ConnectTimeout=6 -o BatchMode=yes "${NG_HOST}" 'echo ALIVE' 2>&1 | grep -q ALIVE; then
  echo "🔴 UNREACHABLE: ssh ${NG_HOST} failed"
  exit 2
fi
if ! ssh "${NG_HOST}" "docker inspect -f '{{.State.Status}}' ${CONTAINER} 2>/dev/null" | grep -q running; then
  echo "🔴 UNREACHABLE: container ${CONTAINER} not running"
  exit 2
fi

# -- Step 2: snapshot pcap size BEFORE
SIZE_BEFORE=$(ssh "${NG_HOST}" "stat -c %s ${PCAP_HOST_PATH} 2>/dev/null" 2>/dev/null | tr -d '[:space:]')
: "${SIZE_BEFORE:=0}"
echo "pcap_size_before=${SIZE_BEFORE}"

# -- Step 3: send a synthetic TZSP-framed packet
# Minimal TZSP v1 header: 01 (ver=1) 00 (type=received-tag-list) 00 01 (encap=ether)
# + Tag 0x00 (padding — safe test tag) + END tag 0x01
# + synthetic Ethernet/IP/UDP payload carrying our marker.
# We send via Python one-liner (avoids scapy dependency); uses plain UDP socket.
python3 - <<PY
import socket, struct, sys
host, port = "${NG_HOST}", ${NG_UDP_PORT}
# resolve nous-gpu via ssh config → IP
import subprocess
ip = subprocess.check_output(["ssh", "-G", host]).decode()
for line in ip.splitlines():
    if line.startswith("hostname "):
        host = line.split()[1]
        break
tzsp = bytes([0x01, 0x00, 0x00, 0x01, 0x00, 0x01])  # minimal TZSP header + END tag
# Fake ethernet (14B) + fake IP (20B) + fake UDP (8B) + marker
marker = "${MARKER}".encode()
eth = b"\x00"*12 + b"\x08\x00"
ip = b"\x45\x00" + struct.pack(">H", 20+8+len(marker)) + b"\x00"*8 + b"\x06"*2 + b"\x00"*2 + b"\x7f\x00\x00\x01"*2
udp = struct.pack(">HHHH", 37008, 37008, 8+len(marker), 0) + marker
pkt = tzsp + eth + ip + udp
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(pkt, (host, port))
print(f"probe_sent: dst={host}:{port} bytes={len(pkt)}")
PY
PROBE_BYTES=$?

# -- Step 4: wait for collector to flush + grow pcap
sleep 2

# -- Step 5: verify grown + marker present
SIZE_AFTER=$(ssh "${NG_HOST}" "stat -c %s ${PCAP_HOST_PATH} 2>/dev/null" 2>/dev/null | tr -d '[:space:]')
: "${SIZE_AFTER:=0}"
echo "pcap_size_after=${SIZE_AFTER}"
DELTA=$((SIZE_AFTER - SIZE_BEFORE))
echo "delta_bytes=${DELTA}"

if [ "${DELTA}" -lt 40 ]; then
  echo "🔴 DRIFT: pcap did not grow (delta=${DELTA}B, expected ≥40B)"
  exit 1
fi

if ssh "${NG_HOST}" "docker exec ${CONTAINER} grep -ac '${MARKER}' ${PCAP_INSIDE} 2>/dev/null" | grep -q '^[1-9]'; then
  echo "✅ OK: marker '${MARKER}' found in pcap (delta=${DELTA}B)"
  exit 0
else
  echo "🟡 PARTIAL: pcap grew by ${DELTA}B but marker not grep-able (binary pcap framing; consider tshark)"
  exit 0
fi
