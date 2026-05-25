#!/usr/bin/env bash
# test_github_mirror_secret_scan.sh — fail closed before any GitHub mirror/export.
#
# This scans the current tree for high-confidence secret literals. It is intentionally
# narrower than generic "sk-" grep so normal words such as "risk-to..." do not trip it.

set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"

TMP="$(mktemp -t github-mirror-secret-scan.XXXXXX)"
trap 'rm -f "$TMP"' EXIT

rg -n --hidden \
  --glob '!/.git/**' \
  --glob '!raw/**' \
  --glob '!**/raw/**' \
  --glob '!**/__pycache__/**' \
  --glob '!**/node_modules/**' \
  --glob '!**/.obsidian/workspace.json' \
  --glob '!**/.obsidian/plugins/**' \
  --glob '!**/*.pyc' \
  --glob '!**/*.pcap' \
  --glob '!**/*.pcap.zst' \
  --glob '!**/*.sqlite' \
  --glob '!**/*.db' \
  --glob '!**/.env' \
  --glob '!**/.env.*' \
  --glob '!**/auth.json' \
  -e '[0-9]{8,10}:[A-Za-z0-9_-]{35,}' \
  -e 'sk-litellm-[A-Za-z0-9_-]{20,}' \
  -e 'sk-lf-[A-Za-z0-9_-]{20,}' \
  -e 'gh[pousr]_[A-Za-z0-9_]{20,}' \
  -e 'github_pat_[A-Za-z0-9_]{20,}' \
  -e 'AKIA[0-9A-Z]{16}' \
  -e 'AIza[0-9A-Za-z_-]{35}' \
  -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' \
  -e 'Bearer[[:space:]]+[A-Za-z0-9._-]{24,}' \
  "$ROOT" >"$TMP" || true

if [ -s "$TMP" ]; then
  echo "FAIL: high-confidence secret literals found; refusing GitHub mirror/export" >&2
  cut -d: -f1 "$TMP" | sort -u | sed -n '1,120p' >&2
  exit 2
fi

echo "OK: GitHub mirror secret scan clean for $ROOT"
