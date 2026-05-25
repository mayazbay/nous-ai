#!/bin/bash
# sync_public_mirror.sh — one-way sync of the PUBLIC-classified vault subset
# to a separate git mirror that pushes to GitHub.
#
# Architecture (per SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20):
#   Canonical vault (this repo) ─┐
#                                ├──► public mirror (separate git repo) ──► github.com/.../nous-public
#   Credential scanner gate ─────┘
#
# The mirror is a SIBLING directory (not a clone of this repo). It has its
# own independent git history derived from periodic syncs. This avoids the
# git history filtering complexity of trying to use one repo with two
# remotes, and gives a hard mechanical guarantee that private content
# never reaches GitHub: only files matching the PUBLIC_GLOBS in
# tools/scan_credentials.py are ever copied to the mirror.
#
# Usage:
#   ./tools/sync_public_mirror.sh --mirror-dir <path>
#   ./tools/sync_public_mirror.sh --mirror-dir <path> --message "subj"
#   ./tools/sync_public_mirror.sh --mirror-dir <path> --dry-run
#
# Pre-flight requirements for <path>:
#   1. exists and is a git working tree
#   2. has a remote named 'github' pointing at the target public repo
#   3. is on branch 'main' (or whatever the public default is)
#
# The script is idempotent: running it twice in a row is a no-op when
# the canonical hasn't changed.

set -euo pipefail

MIRROR_DIR=""
COMMIT_MSG=""
DRY_RUN=0
SKIP_PUSH=0
INITIAL=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mirror-dir) MIRROR_DIR="$2"; shift 2 ;;
        --message)    COMMIT_MSG="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=1; shift ;;
        --skip-push)  SKIP_PUSH=1; shift ;;
        --initial)    INITIAL=1; shift ;;
        --help|-h)    sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$MIRROR_DIR" ]]; then
    echo "🔴 --mirror-dir is required" >&2
    echo "usage: $0 --mirror-dir <path> [--message <subj>] [--dry-run]" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CANONICAL="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -d "$CANONICAL/.git" ]]; then
    echo "🔴 canonical $CANONICAL is not a git repo" >&2; exit 2
fi

MIRROR_DIR="$(cd "$MIRROR_DIR" 2>/dev/null && pwd || echo "")"
if [[ -z "$MIRROR_DIR" || ! -d "$MIRROR_DIR/.git" ]]; then
    echo "🔴 mirror dir does not exist or is not a git repo: $MIRROR_DIR" >&2
    echo "   bootstrap with: git clone <github-url> $MIRROR_DIR" >&2
    exit 2
fi

if [[ "$INITIAL" -eq 0 ]]; then
    if ! git -C "$MIRROR_DIR" remote get-url github >/dev/null 2>&1; then
        echo "🔴 mirror $MIRROR_DIR has no 'github' remote" >&2
        echo "   add with: git -C $MIRROR_DIR remote add github <github-url>" >&2
        exit 2
    fi
fi

# Public path manifest (must stay in sync with PUBLIC_GLOBS in tools/scan_credentials.py).
PUBLIC_GLOBS=(
    "agents/"
    "laws/"
    "pages/skills/"
    "pages/laws/"
    "pages/concepts/"
    "pages/lessons/"
    "pages/specs/"
    "pages/systems/"
    "pages/dashboards/"
    "pages/aliases/"
    "pages/schemas/"
    "pages/tools/"
    "pages/prompts/"
    "pages/roadmap/"
    "templates/"
    "tools/"
)
PUBLIC_FILES=(
    "CLAUDE.md"
    "README.md"
    "index.md"
)

echo "📤 sync canonical → mirror"
echo "   canonical: $CANONICAL"
echo "   mirror:    $MIRROR_DIR"
echo

RSYNC_FLAGS=(-a --delete --exclude='.git/' --exclude='__pycache__/' --exclude='*.pyc' --exclude='.DS_Store')
if [[ "$DRY_RUN" -eq 1 ]]; then
    RSYNC_FLAGS+=(--dry-run --itemize-changes)
fi

for d in "${PUBLIC_GLOBS[@]}"; do
    src="$CANONICAL/$d"
    dst="$MIRROR_DIR/$d"
    if [[ ! -d "$src" ]]; then
        if [[ -d "$dst" && "$DRY_RUN" -eq 0 ]]; then
            rm -rf "$dst"
            echo "  removed (no src): $d"
        fi
        continue
    fi
    mkdir -p "$dst"
    # Both src and dst end with `/` (from PUBLIC_GLOBS). With both trailing
    # slashes, rsync copies CONTENT of src INTO dst, preserving the dir
    # name. Without this discipline (e.g., dirname-of-dst as target), the
    # subtree gets flattened one level into the mirror root. Bug found
    # 2026-05-25 when CI on nous-ai failed because tools/scan_credentials.py
    # had been flattened to mirror/scan_credentials.py.
    rsync "${RSYNC_FLAGS[@]}" "$src" "$dst" 2>&1 | head -20
done

for f in "${PUBLIC_FILES[@]}"; do
    src="$CANONICAL/$f"
    dst="$MIRROR_DIR/$f"
    if [[ -f "$src" ]]; then
        rsync "${RSYNC_FLAGS[@]}" "$src" "$dst" 2>&1 | head -5
    elif [[ -f "$dst" && "$DRY_RUN" -eq 0 ]]; then
        rm -f "$dst"
    fi
done

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo
    echo "✅ dry-run: rsync diff above; scanner gate + commit skipped"
    exit 0
fi

echo
echo "🔍 running credential scanner on the mirror"
if ! python3 "$CANONICAL/tools/scan_credentials.py" --repo-root "$MIRROR_DIR" --all-public; then
    echo
    echo "🔴 BLOCKED: scanner found credential patterns in the mirror"
    echo "   fix in the canonical vault first, then re-run this sync."
    echo "   reset the mirror's working tree before another attempt:"
    echo "       git -C $MIRROR_DIR reset --hard HEAD && git -C $MIRROR_DIR clean -fd"
    exit 1
fi
echo "✅ scanner clean (0 findings on mirror)"

cd "$MIRROR_DIR"
if [[ -z "$(git status --porcelain)" ]]; then
    echo
    echo "✅ mirror already up-to-date (no changes to commit)"
    exit 0
fi

git add -A

if [[ -z "$COMMIT_MSG" ]]; then
    CANONICAL_HEAD="$(git -C "$CANONICAL" rev-parse --short HEAD)"
    COMMIT_MSG="sync: mirror public substrate from canonical ${CANONICAL_HEAD}"
fi

git commit -m "$COMMIT_MSG" -m "Synced from canonical at:
  $CANONICAL
  HEAD: $(git -C "$CANONICAL" rev-parse HEAD)
  Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Per SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20.
Scanner: 0 findings." 2>&1 | tail -3

if [[ "$SKIP_PUSH" -eq 1 ]]; then
    echo
    echo "✅ committed; --skip-push set, not pushing"
    exit 0
fi

echo
echo "📤 pushing to github"
git push github HEAD:main 2>&1 | tail -5

echo
echo "✅ sync complete"
