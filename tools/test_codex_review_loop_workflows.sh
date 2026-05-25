#!/bin/bash
# Verify the Codex landed-commit and PR review/fix loop is wired safely.
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${ROOT:-$SCRIPT_ROOT}"
if [ ! -d "$ROOT/.github/workflows" ] && [ -d "$ROOT/wiki/.github/workflows" ]; then
  ROOT="$ROOT/wiki"
fi
LANDED="$ROOT/.github/workflows/codex-landed-commit-loop.yml"
PR="$ROOT/.github/workflows/codex-pr-review-loop.yml"
HELPER="$ROOT/tools/codex_review_loop.py"

need_file() {
  [ -f "$1" ] || { echo "FAIL: missing $1"; exit 1; }
}

need() {
  local file="$1"
  local pattern="$2"
  grep -Fq -- "$pattern" "$file" || {
    echo "FAIL: $file missing pattern: $pattern"
    exit 1
  }
}

need_count() {
  local file="$1"
  local pattern="$2"
  local expected="$3"
  local actual
  actual="$(grep -Fc -- "$pattern" "$file" || true)"
  if [ "$actual" != "$expected" ]; then
    echo "FAIL: $file expected $expected occurrences of $pattern, found $actual"
    exit 1
  fi
}

reject() {
  local file="$1"
  local pattern="$2"
  if grep -Fq -- "$pattern" "$file"; then
    echo "FAIL: $file must not contain pattern: $pattern"
    exit 1
  fi
}

need_file "$LANDED"
need_file "$PR"
need_file "$HELPER"

need "$LANDED" "on:"
need "$LANDED" "workflow_dispatch:"
need "$LANDED" "github.event_name == 'workflow_dispatch'"
need "$LANDED" "github.actor != 'github-actions[bot]'"
reject "$LANDED" "  push:"
need "$LANDED" "actions: write"
need "$LANDED" "OPENAI_API_KEY is not configured; Codex landed-commit loop skipped."
need "$LANDED" "REVIEW_OUT: /tmp/codex-landed-review.md"
need "$LANDED" "CODEX_EFFORT: medium"
need "$LANDED" "CODEX_ACTION_ARGS:"
need "$LANDED" 'model_verbosity=\"medium\"'
need "$LANDED" "uses: openai/codex-action@v1"
need_count "$LANDED" "uses: openai/codex-action@v1" 1
need "$LANDED" 'codex-args: ${{ env.CODEX_ACTION_ARGS }}'
need_count "$LANDED" 'codex-args: ${{ env.CODEX_ACTION_ARGS }}' 1
need "$LANDED" "sandbox: read-only"
need "$LANDED" "codex exec"
need "$LANDED" "--sandbox workspace-write"
need "$LANDED" "--sandbox workspace-write <<'PROMPT'"
reject "$LANDED" "--sandbox workspace-write <<PROMPT"
need "$LANDED" 'git status --porcelain'
need "$LANDED" "gh pr create"
need "$LANDED" "codex/review-fix-"
need "$LANDED" "Loop: 1/5"
need "$LANDED" "rm -rf .codex"
need "$LANDED" "workflow run codex-pr-review-loop.yml"
reject "$LANDED" 'cache: "pip"'

need "$PR" "pull_request:"
need "$PR" "actions: write"
need "$PR" "cancel-in-progress: false"
need "$PR" "Codex-owned/generated PR heads are reviewed only by explicit workflow_dispatch"
need "$PR" "!startsWith(github.head_ref, 'codex/')"
need "$PR" "MAX_CODEX_REVIEW_LOOPS: \"5\""
need "$PR" "OPENAI_API_KEY is not configured; Codex PR review loop skipped."
need "$PR" "REVIEW_OUT: /tmp/codex-pr-review.md"
need "$PR" "CODEX_EFFORT: medium"
need "$PR" "CODEX_ACTION_ARGS:"
need "$PR" 'model_verbosity=\"medium\"'
need "$PR" "isCrossRepository"
need "$PR" "uses: openai/codex-action@v1"
need_count "$PR" "uses: openai/codex-action@v1" 1
need "$PR" 'codex-args: ${{ env.CODEX_ACTION_ARGS }}'
need_count "$PR" 'codex-args: ${{ env.CODEX_ACTION_ARGS }}' 1
need "$PR" "allow-bots: true"
need "$PR" "allow-bot-users: github-actions[bot]"
need "$PR" "sandbox: read-only"
need "$PR" "codex exec"
need "$PR" "--sandbox workspace-write"
need "$PR" "--sandbox workspace-write <<'PROMPT'"
reject "$PR" "--sandbox workspace-write <<PROMPT"
need "$PR" "startsWith(steps.prmeta.outputs.head, 'codex/')"
need "$PR" "steps.prmeta.outputs.is_cross_repository == 'false'"
need "$PR" 'git status --porcelain'
need "$PR" "fix: address Codex PR review findings"
need "$PR" "RUNNER_TEMP/codex-pr-meta.json"
need "$PR" "rm -rf .codex pr.json"
need "$PR" "workflow run codex-pr-review-loop.yml"
need "$PR" 'reached ${MAX_CODEX_REVIEW_LOOPS}'
need "$PR" "human review required"
need "$PR" "GITHUB_TOKEN cannot push workflow updates"
need "$PR" "Stop for unrepaired non-Codex findings"
need "$PR" "exit 1"
reject "$PR" 'cache: "pip"'
reject "$PR" '> pr.json'

need "$LANDED" "Codex produced no patch; human review required."
need "$LANDED" "git ls-remote --heads origin"
need "$LANDED" 'remote_sha="$(git ls-remote --heads origin "$branch"'
need "$LANDED" 'git checkout -B "$branch"'
need "$LANDED" "Generated patch already exists on"
need "$LANDED" "GITHUB_TOKEN cannot push workflow updates"
need "$LANDED" 'git push --force-with-lease="refs/heads/$branch:$remote_sha" origin "$branch"'
need "$LANDED" "gh pr list --head"
need "$LANDED" "Reusing existing fix PR"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
printf 'NO_FINDINGS\n' > "$tmp/no.txt"
python3 "$HELPER" classify "$tmp/no.txt" | grep -Fq "has_findings=false"
printf 'FINDINGS\n1. [high] tools/x.py:1 - bad - fix it\n' > "$tmp/yes.txt"
python3 "$HELPER" classify "$tmp/yes.txt" | grep -Fq "has_findings=true"

echo "OK: Codex review-loop workflows wired with manual landed loop, secret gate, PR gate, and 5-pass ceiling"
