#!/usr/bin/env bash
# test_qmd_real_freshness.sh — sibling test for qmd_real_freshness.sh
# Session 49 artifact; per `infrastructure` AP-36 sibling-test pattern.
#
# Test matrix (4 scenarios):
#   T1 fresh local  — mock log file just touched; STALE_HOURS=30; expect exit 0, status=fresh
#   T2 stale local  — mock log file aged 36h; STALE_HOURS=30;    expect exit 1, status=stale
#   T3 unknown      — non-existent log file; STALE_HOURS=30;     expect exit 2, status=unknown
#   T4 json shape   — --json flag on fresh case; validate keys:  expect exit 0, JSON parseable

set -u
FAIL=0
PASS=0
TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL="${TOOL_DIR}/qmd_real_freshness.sh"

if [[ ! -x "$TOOL" ]] && [[ ! -r "$TOOL" ]]; then
  echo "FATAL: cannot find $TOOL"
  exit 2
fi

TMPDIR_T="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_T"' EXIT

assert() {
  local name="$1"; local expected_exit="$2"; local actual_exit="$3"; local extra="${4:-}"
  if [[ "$actual_exit" == "$expected_exit" ]]; then
    printf '  [PASS] %s (exit=%d)%s\n' "$name" "$actual_exit" "${extra:+ — $extra}"
    PASS=$((PASS + 1))
  else
    printf '  [FAIL] %s (expected exit=%d, got %d)%s\n' "$name" "$expected_exit" "$actual_exit" "${extra:+ — $extra}"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== T1: fresh local log ==="
fresh_log="$TMPDIR_T/qmd-embed-fresh.log"
: > "$fresh_log"  # touch (mtime = now)
out=$(VPS_HOST="" QMD_EMBED_LOG="$fresh_log" STALE_HOURS=30 bash "$TOOL" 2>&1)
rc=$?
assert "fresh local returns 0" 0 "$rc" "output: $out"
echo "$out" | grep -qE 'FRESH|fresh' && echo "  output contains 'fresh'" || { echo "  WARN: output missing 'fresh' token"; FAIL=$((FAIL + 1)); }

echo ""
echo "=== T2: stale local log (36h old) ==="
stale_log="$TMPDIR_T/qmd-embed-stale.log"
: > "$stale_log"
# Back-date by 36 hours. macOS touch uses -t YYYYMMDDHHMM; Linux touch uses -d.
if date -v-36H +%Y%m%d%H%M >/dev/null 2>&1; then
  stale_ts=$(date -v-36H +%Y%m%d%H%M)
  touch -t "$stale_ts" "$stale_log"
else
  touch -d "36 hours ago" "$stale_log"
fi
out=$(VPS_HOST="" QMD_EMBED_LOG="$stale_log" STALE_HOURS=30 bash "$TOOL" 2>&1)
rc=$?
assert "stale local returns 1" 1 "$rc" "output: $out"
echo "$out" | grep -qE 'STALE|stale' && echo "  output contains 'stale'" || { echo "  WARN: output missing 'stale' token"; FAIL=$((FAIL + 1)); }

echo ""
echo "=== T3: missing log file ==="
missing_log="$TMPDIR_T/nonexistent.log"
out=$(VPS_HOST="" QMD_EMBED_LOG="$missing_log" STALE_HOURS=30 bash "$TOOL" 2>&1)
rc=$?
assert "missing log returns 2" 2 "$rc" "output: $out"
echo "$out" | grep -qE 'UNKNOWN|unknown' && echo "  output contains 'unknown'" || { echo "  WARN: output missing 'unknown' token"; FAIL=$((FAIL + 1)); }

echo ""
echo "=== T4: --json output shape on fresh case ==="
json_log="$TMPDIR_T/qmd-embed-json.log"
: > "$json_log"
out=$(VPS_HOST="" QMD_EMBED_LOG="$json_log" STALE_HOURS=30 bash "$TOOL" --json 2>&1)
rc=$?
assert "json fresh returns 0" 0 "$rc"
# Validate JSON-ish shape: must contain all required keys
required_keys=(tool version status age_hours threshold_hours cron_log_epoch reason)
all_found=1
for k in "${required_keys[@]}"; do
  if ! echo "$out" | grep -q "\"$k\""; then
    echo "  [FAIL] JSON missing key: $k"
    all_found=0
  fi
done
if [[ $all_found -eq 1 ]]; then
  echo "  [PASS] JSON shape contains all 7 required keys"
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
fi
# Make sure JSON parses as JSON via python3 (available on Mac + VPS + Air)
if command -v python3 >/dev/null 2>&1; then
  if echo "$out" | python3 -c 'import json,sys; json.loads(sys.stdin.read()); print("  [PASS] JSON parseable via python3")' 2>/dev/null; then
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] JSON not parseable via python3"
    FAIL=$((FAIL + 1))
  fi
fi

echo ""
echo "=============================="
echo "Summary: PASS=$PASS FAIL=$FAIL"
echo "=============================="
exit $FAIL
