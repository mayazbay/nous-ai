#!/bin/bash
# Regression guard: morning OpenClaw update checks must not mutate Docker state.
set -u

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)
TARGET="$SCRIPT_DIR/morning-update-apply.sh"

FAIL=0

OPENCLAW_SECTION=$(awk '
  /^# .*3\. OpenClaw image/ {in_section=1}
  /^# .*Telegram report/ {in_section=0}
  in_section {print}
' "$TARGET")

if printf "%s\n" "$OPENCLAW_SECTION" | grep -q 'docker pull'; then
  echo "FAIL: OpenClaw notify-only check must not run docker pull"
  FAIL=1
fi

if ! grep -q 'docker manifest inspect --verbose' "$TARGET"; then
  echo "FAIL: OpenClaw check must inspect registry manifests without pulling"
  FAIL=1
fi

if ! grep -q '_docker_manifest_digest()' "$TARGET"; then
  echo "FAIL: manifest digest parsing should live in a named helper"
  FAIL=1
fi

if ! grep -q 'isinstance(data, list)' "$TARGET"; then
  echo "FAIL: manifest parser must handle multi-platform list output"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "morning-update-openclaw-manifest: pass"
fi
exit "$FAIL"
