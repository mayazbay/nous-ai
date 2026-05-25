#!/bin/bash
# Runs every test_*.sh in the same directory. Exit 0 iff all pass.
set -u
cd "$(dirname "$0")"
FAIL=0
for t in test_*.sh; do
  [ "$t" = "test_all.sh" ] && continue
  [ -x "$t" ] || chmod +x "$t"
  echo "=== $t ==="
  if ./"$t"; then
    echo "PASS: $t"
  else
    echo "FAIL: $t"
    FAIL=$((FAIL+1))
  fi
done
echo ""
[ "$FAIL" -eq 0 ] && { echo "ALL GREEN"; exit 0; } || { echo "$FAIL failing"; exit 1; }
