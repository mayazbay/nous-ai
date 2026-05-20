#!/bin/bash
# Portable burst-test lane for Blacksmith/GitHub Actions.
#
# This suite intentionally excludes Air-only, launchd-only, SSH-only, tokened,
# and live OpenClaw mutation tests. Use it as the first disposable 32-vCPU lane;
# grow it only after each new test proves portable in CI.
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cd "$ROOT"

echo "== Blacksmith burst suite =="
echo "root=$ROOT"
echo "jobs=$JOBS"

echo
echo "== Python syntax compile =="
PY_LIST="$TMP_DIR/python-files.null"
find tools tenants -name '*.py' -not -path '*/__pycache__/*' -print0 > "$PY_LIST"
if [ -s "$PY_LIST" ]; then
  xargs -0 -n 1 -P "$JOBS" python3 -m py_compile < "$PY_LIST"
fi

echo
echo "== Structural shell gates =="
SHELL_TESTS=(
  "tools/test_skill_version_parity.sh"
  "tools/test_no_duplicate_skill_headers.sh"
  "tools/test_agent_identity_runtime_parity.sh"
  "tools/test_wiki_to_runtime_rsync.sh"
  "tools/test_musk_step_2.sh"
  "tools/test_pre_receive_lesson_count_guard.sh"
  "tools/test_codex_review_loop_workflows.sh"
)

for test_file in "${SHELL_TESTS[@]}"; do
  if [ -f "$test_file" ]; then
    echo "-- $test_file"
    bash "$test_file"
  fi
done

echo
echo "== Python unit tests =="
python3 -m pytest -q \
  tools/test_lesson_absorption_watcher.py \
  tools/test_ghost_debt_dashboard.py \
  tools/test_skill_from_debug.py \
  tools/test_dream_cycle.py \
  tools/test_readme_dashboard.py \
  tools/test_operator_boundaries.py

echo
echo "== Standalone Python probes =="
python3 tools/test_context_injector_v2.py

cat > "$TMP_DIR/run_task_fixture.jsonl" <<'JSONL'
{"ts":"2026-04-27T00:00:00+05:00","model_selected":"deepseek-v4-flash","model":"deepseek-v4-flash","execution_path":"fixture"}
{"ts":"2026-04-27T00:00:01+05:00","model_selected":"deepseek-v4-pro","model":"deepseek-v4-pro","execution_path":"fixture"}
JSONL
python3 tools/test_run_task_model_truth.py --log "$TMP_DIR/run_task_fixture.jsonl"

echo
echo "BLACKSMITH_BURST_TESTS_OK"
