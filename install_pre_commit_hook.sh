#!/usr/bin/env bash
# install_pre_commit_hook.sh — substrate-v2 Phase 0.3
#
# Symmetric deploy of canonical pre-commit hook to all 3 wiki replicas
# (Mac local, Air via Tailscale, VPS via SSH). Reads from
# Nous/tools/pre-commit-hook-tan-pattern.sh (git-tracked, Mac is authoritative).
#
# Usage:
#   bash tools/install_pre_commit_hook.sh [--dry-run]
#
# Eng-review fix (autoplan 2026-05-04, Eng-Med-8): script exits non-zero
# on ANY per-host failure with explicit smoke-test verification per host.

set -euo pipefail

REPO_ROOT="/Users/madia/Documents/Projects/Nous AGaaS/Nous"
CANONICAL="$REPO_ROOT/tools/pre-commit-hook-tan-pattern.sh"
MAC_HOOK="$REPO_ROOT/.git/hooks/pre-commit"
AIR_HOOK_REMOTE="~/nous-agaas/wiki/.git/hooks/pre-commit"
VPS_HOST="root@65.108.215.200"
VPS_HOOK_REMOTE="/root/nous-agaas/wiki/.git/hooks/pre-commit"

DRY=""
[[ "${1:-}" == "--dry-run" ]] && DRY="--dry-run"

failures=0

verify_size() {
    local host="$1"
    local local_size remote_size
    local_size=$(wc -c < "$CANONICAL" | tr -d ' ')
    remote_size="$2"
    if [ "$local_size" = "$remote_size" ]; then
        echo "    ✅ $host: size matches canonical ($local_size bytes)"
    else
        echo "    ❌ $host: size mismatch — canonical=$local_size remote=$remote_size"
        failures=$((failures + 1))
    fi
}

echo "[0/4] Verifying canonical exists and is sane…"
test -f "$CANONICAL" || { echo "FAIL: $CANONICAL missing"; exit 2; }
canonical_size=$(wc -c < "$CANONICAL" | tr -d ' ')
echo "  canonical: $canonical_size bytes"
echo "  shebang: $(head -1 "$CANONICAL")"

echo
echo "[1/4] Mac (local copy from canonical → .git/hooks/)…"
if [ -z "$DRY" ]; then
    cp "$CANONICAL" "$MAC_HOOK"
    chmod +x "$MAC_HOOK"
fi
verify_size "Mac" "$(wc -c < "$MAC_HOOK" | tr -d ' ')"

echo
echo "[2/4] Air (rsync via Tailscale)…"
if [ -z "$DRY" ]; then
    rsync -av "$CANONICAL" "air:$AIR_HOOK_REMOTE"
    ssh -o ConnectTimeout=10 air "chmod +x $AIR_HOOK_REMOTE" || { echo "    ❌ Air chmod failed"; failures=$((failures + 1)); }
    air_size=$(ssh -o ConnectTimeout=10 air "wc -c < $AIR_HOOK_REMOTE" 2>/dev/null | tr -d ' ')
    verify_size "Air" "$air_size"
else
    rsync -av --dry-run "$CANONICAL" "air:$AIR_HOOK_REMOTE"
fi

echo
echo "[3/4] VPS (rsync via SSH)…"
if [ -z "$DRY" ]; then
    rsync -av "$CANONICAL" "$VPS_HOST:$VPS_HOOK_REMOTE"
    ssh -o ConnectTimeout=10 "$VPS_HOST" "chmod +x $VPS_HOOK_REMOTE" || { echo "    ❌ VPS chmod failed"; failures=$((failures + 1)); }
    vps_size=$(ssh -o ConnectTimeout=10 "$VPS_HOST" "wc -c < $VPS_HOOK_REMOTE" 2>/dev/null | tr -d ' ')
    verify_size "VPS" "$vps_size"
else
    rsync -av --dry-run "$CANONICAL" "$VPS_HOST:$VPS_HOOK_REMOTE"
fi

echo
echo "[4/4] Result"
if [ "$failures" -eq 0 ]; then
    echo "  ✅ All 3 hosts in sync with canonical ($canonical_size bytes)"
    [ -z "$DRY" ] && echo "  Smoke-test (manual): cd ~/nous-agaas/wiki && create + stage a LESSON-130-test.md → commit must FAIL"
    exit 0
else
    echo "  ❌ $failures host(s) failed verification — investigate before declaring symmetric"
    exit 1
fi
