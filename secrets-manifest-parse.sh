#!/bin/bash
# secrets-manifest-parse.sh — extract rows from pages/secrets-manifest.md matching (service, target).
# Usage: secrets-manifest-parse.sh <manifest-path> <service> <target>
# Output lines: "<key>|<type>|<icloud>|<value-if-constant>"
set -euo pipefail
[ "$#" -eq 3 ] || { echo "usage: $0 <manifest.md> <service> <target>" >&2; exit 1; }
MANIFEST="$1"
SERVICE="$2"
TARGET="$3"

awk -F'|' -v svc="$SERVICE" -v tgt="$TARGET" '
  /^## Active entries/ { in_table=1; next }
  /^## / && in_table { in_table=0 }
  in_table && /^\| [A-Z]/ {
    key=$2; desc=$3; service=$4; targets=$5; type=$6; icloud=$7; rotation=$8; value=$9
    gsub(/^ +| +$/, "", key)
    gsub(/^ +| +$/, "", service)
    gsub(/^ +| +$/, "", targets)
    gsub(/^ +| +$/, "", type)
    gsub(/^ +| +$/, "", icloud)
    gsub(/^ +| +$/, "", value)

    if (service != svc) next
    split(targets, tarr, /, */)
    for (i in tarr) if (tarr[i] == tgt) {
      if (type == "constant") {
        print key "|" type "|" icloud "|" value
      } else {
        print key "|" type "|" icloud "|"
      }
      break
    }
  }
' "$MANIFEST"
