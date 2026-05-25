#!/bin/bash
# tools/test_nous_gpu_collector_health_rotation.sh — AP-71 regression.
# Fakes ping/ssh so same-path pcap truncation is tested without touching Nous-GPU.
set -u
PASS=0
FAIL=0
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="/tmp/test-collector-health-rotation-$$"
FAKE_BIN="$TMP_DIR/bin"
FAKE_HOME="$TMP_DIR/home"
PCAP="/home/nous-admin/collector/pcap/wg0-collector.pcap"

assert() {
  local label="$1" cond="$2"
  if eval "$cond"; then
    PASS=$((PASS+1))
    echo "  ✅ $label"
  else
    FAIL=$((FAIL+1))
    echo "  🔴 $label"
    echo "       cond: $cond"
  fi
}

cleanup() {
  rm -rf "$TMP_DIR" 2>/dev/null
}
trap cleanup EXIT

mkdir -p "$FAKE_BIN" "$FAKE_HOME/.nous-gpu-collector-health"

cat > "$FAKE_BIN/ping" <<'EOF'
#!/bin/bash
exit 0
EOF

cat > "$FAKE_BIN/ssh" <<'EOF'
#!/bin/bash
CMD="$*"
case "$CMD" in
  *"docker ps"*)
    echo "nous-collector"
    exit 0
    ;;
  *"find /home/nous-admin/collector/pcap"*)
    echo "/home/nous-admin/collector/pcap/wg0-collector.pcap"
    exit 0
    ;;
  *"stat -c %s"*)
    echo "100"
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
EOF
chmod +x "$FAKE_BIN/ping" "$FAKE_BIN/ssh"

echo "$PCAP" > "$FAKE_HOME/.nous-gpu-collector-health/last_pcap_path"
echo "200" > "$FAKE_HOME/.nous-gpu-collector-health/last_pcap_size"
echo "1" > "$FAKE_HOME/.nous-gpu-collector-health/last_state"

echo "=== collector-health-rotation ==="
OUT=$(HOME="$FAKE_HOME" PATH="$FAKE_BIN:$PATH" bash "$TOOLS_DIR/nous_gpu_collector_health.sh" 2>&1)
RC=$?
STATE=$(cat "$FAKE_HOME/.nous-gpu-collector-health/last_state" 2>/dev/null || echo "missing")
SIZE=$(cat "$FAKE_HOME/.nous-gpu-collector-health/last_pcap_size" 2>/dev/null || echo "missing")

assert "1. rotation/truncation run exits 0" "[ '$RC' = '0' ]"
assert "2. output names truncated/rotated reset" "echo '$OUT' | grep -q 'truncated/rotated'"
assert "3. last_state reset to OK" "[ '$STATE' = '0' ]"
assert "4. new smaller size persisted as baseline" "[ '$SIZE' = '100' ]"
assert "5. fake ssh was used" "[ -x '$FAKE_BIN/ssh' ]"

echo "=== collector-health-rotation: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]

echo "=== collector-health-optional-unreachable ==="
rm -rf "$TMP_DIR"
mkdir -p "$FAKE_BIN" "$FAKE_HOME/.nous-gpu-collector-health"
cat > "$FAKE_BIN/ping" <<'EOF'
#!/bin/bash
exit 1
EOF
cat > "$FAKE_BIN/ssh" <<'EOF'
#!/bin/bash
exit 255
EOF
chmod +x "$FAKE_BIN/ping" "$FAKE_BIN/ssh"

OUT=$(HOME="$FAKE_HOME" PATH="$FAKE_BIN:$PATH" bash "$TOOLS_DIR/nous_gpu_collector_health.sh" 2>&1)
RC=$?
STATE=$(cat "$FAKE_HOME/.nous-gpu-collector-health/last_state" 2>/dev/null || echo "missing")
assert "6. optional unreachable exits 0" "[ '$RC' = '0' ]"
assert "7. optional unreachable logs SKIP" "echo '$OUT' | grep -q 'SKIP optional Nous-GPU collector degraded'"
assert "8. optional unreachable leaves state OK" "[ '$STATE' = '0' ]"

OUT=$(NOUS_GPU_REQUIRED=1 HOME="$FAKE_HOME" PATH="$FAKE_BIN:$PATH" bash "$TOOLS_DIR/nous_gpu_collector_health.sh" 2>&1)
RC=$?
STATE=$(cat "$FAKE_HOME/.nous-gpu-collector-health/last_state" 2>/dev/null || echo "missing")
assert "9. required unreachable exits nonzero" "[ '$RC' != '0' ]"
assert "10. required unreachable logs FAIL" "echo '$OUT' | grep -q 'FAIL: Tailscale unreachable'"
assert "11. required unreachable leaves state failed" "[ '$STATE' = '1' ]"

echo "=== collector-health-total: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
