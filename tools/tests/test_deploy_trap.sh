#!/bin/bash
set -euo pipefail
[[ "$(uname -s)" == "Darwin" ]] || { echo "SKIP: Mac-only"; exit 0; }

DEPLOY="$(cd "$(dirname "$0")/../.." && pwd)/tools/secrets-deploy.sh"
[ -x "$DEPLOY" ] || { echo "FAIL: deploy not exec"; exit 1; }

grep -q "trap cleanup EXIT" "$DEPLOY"        || { echo "FAIL: no trap cleanup EXIT in deploy"; exit 1; }
grep -q "rm -f '\$DEST.new'" "$DEPLOY"       || { echo "FAIL: cleanup function doesn't rm staging"; exit 1; }
grep -q "trap - EXIT" "$DEPLOY"              || { echo "FAIL: success path doesn't clear trap"; exit 1; }

echo "OK: trap cleanup structure present"
