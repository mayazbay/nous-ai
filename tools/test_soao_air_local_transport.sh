#!/bin/bash
# Regression: SOAO must not mark Air unreachable when executed on Air.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOAO="$ROOT/tools/soao.sh"

grep -q 'SESSION_FORCE_AIR_LOCAL' "$SOAO"
grep -q 'AIR_LOCAL' "$SOAO"
grep -q 'AIR_HEAD="$MAC_HEAD"' "$SOAO"
grep -q 'AIR_PC="$MAC_PC"' "$SOAO"
grep -q 'docker exec openclaw' "$SOAO"
