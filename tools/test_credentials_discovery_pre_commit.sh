#!/bin/bash
# test_credentials_discovery_pre_commit.sh — verifies the credentials drift gate
# rejects staged real .env keys that are missing from pages/secrets-manifest.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/pre-commit-hook-tan-pattern.sh"
CLI="$SCRIPT_DIR/credentials_discovery.py"
SANDBOX=$(mktemp -d /tmp/test-credentials-precommit-XXXXXX)

cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

[ -x "$HOOK" ] || { echo "FAIL: $HOOK missing or not executable" >&2; exit 3; }
[ -x "$CLI" ] || { echo "FAIL: $CLI missing or not executable" >&2; exit 3; }

cd "$SANDBOX"
git init -q
git config user.name "test" >/dev/null
git config user.email "test@test.local" >/dev/null

mkdir -p tools pages
cp "$HOOK" tools/pre-commit-hook-tan-pattern.sh
cp "$CLI" tools/credentials_discovery.py
chmod +x tools/pre-commit-hook-tan-pattern.sh tools/credentials_discovery.py

cat > runtime.env <<EOF
DOC_KEY=already-documented
EOF

cat > pages/secrets-manifest.md <<EOF
---
title: Secrets Manifest v2
---

# Secrets Manifest v2

## .env files inventory (audited 2026-05-05)

| host | path | service | notes |
|---|---|---|---|
| Mac | \`$SANDBOX/runtime.env\` | fixture | test |

## Active credentials (v2 — full registry)

### Fixture

| key | description | service | host(s) | rotation |
|---|---|---|---|---|
| DOC_KEY | documented fixture | fixture | Mac | as-needed |
EOF

git add tools pages README.md 2>/dev/null || true
echo "init" > README.md
git add tools pages README.md
git commit -q -m "init"

cp tools/pre-commit-hook-tan-pattern.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "=== TEST: staged .env with undocumented NEW_FAKE_KEY rejects commit ==="
cat > .env <<EOF
NEW_FAKE_KEY=test
EOF
git add -f .env

set +e
git commit -m "should reject undocumented env key" >/tmp/credentials-precommit.out 2>/tmp/credentials-precommit.err
RC=$?
set -e

if [ "$RC" -eq 0 ]; then
  echo "FAIL: commit unexpectedly succeeded" >&2
  cat /tmp/credentials-precommit.out
  cat /tmp/credentials-precommit.err >&2
  exit 1
fi

grep -q "BLOCKED: credentials manifest drift" /tmp/credentials-precommit.err || {
  echo "FAIL: missing credentials drift header" >&2
  cat /tmp/credentials-precommit.err >&2
  exit 1
}

grep -q "  - NEW_FAKE_KEY" /tmp/credentials-precommit.err || {
  echo "FAIL: missing exact NEW_FAKE_KEY line" >&2
  cat /tmp/credentials-precommit.err >&2
  exit 1
}

if grep -q "test" /tmp/credentials-precommit.err; then
  echo "FAIL: secret value leaked into hook stderr" >&2
  cat /tmp/credentials-precommit.err >&2
  exit 1
fi

echo "OK: pre-commit rejected undocumented NEW_FAKE_KEY without leaking value"
