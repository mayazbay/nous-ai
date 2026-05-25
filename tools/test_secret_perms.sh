#!/bin/bash
# test_secret_perms.sh — verifies all *.env files in TARGET_DIR are mode 0600
#
# Usage: test_secret_perms.sh [TARGET_DIR]
#   TARGET_DIR defaults to $HOME/nous-agaas
#
# Exit codes:
#   0  — all non-template .env files are exactly 0600
#   2  — at least one .env drift found (perms ≠ 0600)
#   3  — target dir missing or error
#
# Exclusions (not scanned):
#   *.env.example, *.env.template, *.env.sample — these are templates without real values
#
# Absorbed as paired sibling-test for `secrets-management` v1.4 AP-11.
# Session 48 W2 (2026-04-18) — pre-commit RULE 6 underlying check.
# Portable across macOS (Mac + Air) and Linux (VPS + container) via BSD/GNU find.

set -u

TARGET_DIR="${1:-$HOME/nous-agaas}"

if [ ! -d "$TARGET_DIR" ]; then
  echo "ERROR: target dir $TARGET_DIR does not exist" >&2
  exit 3
fi

# find all *.env files, exclude template names, filter NOT exactly 0600
# `-perm 0600` = exactly those mode bits (BSD + GNU compatible when leading digit = 0)
DRIFT=$(find "$TARGET_DIR" -type f -name "*.env" \
  ! -name ".env.example" \
  ! -name ".env.template" \
  ! -name ".env.sample" \
  ! -perm 0600 2>/dev/null)

if [ -z "$DRIFT" ]; then
  # count how many .env files scanned total (sanity)
  TOTAL=$(find "$TARGET_DIR" -type f -name "*.env" \
    ! -name ".env.example" ! -name ".env.template" ! -name ".env.sample" \
    2>/dev/null | wc -l | tr -d ' ')
  echo "OK: all $TOTAL .env files under $TARGET_DIR are 0600"
  exit 0
else
  echo "DRIFT: the following .env files are NOT 0600:" >&2
  while IFS= read -r f; do
    # Portable stat: try BSD first, fall back to GNU
    if stat -f '  %Lp %N' "$f" 2>/dev/null; then
      :  # macOS path succeeded
    else
      stat -c '  %a %n' "$f" 2>/dev/null
    fi
  done <<< "$DRIFT"
  echo "" >&2
  echo "Fix: chmod 0600 <file>" >&2
  echo "Template exclusions recognized: .env.example / .env.template / .env.sample" >&2
  exit 2
fi
