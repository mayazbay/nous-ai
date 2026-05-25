#!/bin/bash
# daily-skill-evals.sh — Tan/Karpathy/Musk skillify Step 5 (automate AFTER validate)
# Runs check_resolvable.py + trigger_eval.py against canonical resolver, telegrams
# on FAIL (any dark/orphan, or trigger_eval pass-rate regression > 5%).
# Closes audit-skill AP-22 ("audit-lies pattern") + musk-algorithm AP-3
# (physically-impossible-violated): without this cron, the audits exist but rot.
# Session 67, 2026-04-23.
#
# Schedule: Air launchd com.nous.daily-skill-evals at 04:15 (after morning-brief 04:00).
# Logs: ~/nous-agaas/logs/daily-skill-evals.log
# State: ~/nous-agaas/state/daily-skill-evals.last (last pass rate for regression check)

set -u

WIKI="${WIKI:-/Users/madia/nous-agaas/wiki}"
RESOLVER="$WIKI/pages/skills/_gbrain/RESOLVER.md"
CHECK_RESOLVABLE="$WIKI/tools/check_resolvable.py"
TRIGGER_EVAL="$WIKI/tools/trigger_eval.py"
LLM_JUDGE="$WIKI/tools/llm_judge_routing.py"

# Export both the Telegram env and the LiteLLM service env to child processes.
# Sourcing without set -a leaves LITELLM_MASTER_KEY invisible to Python.
for env_file in "$HOME/nous-agaas/.env" "$HOME/nous-agaas/litellm/.env"; do
  if [ -f "$env_file" ]; then
    set -a
    source "$env_file" 2>/dev/null || true
    set +a
  fi
done

# Keep scheduled audit loops on the primary low-cost model by default.
# AP-24: paid Anthropic judges require an explicit JUDGE_MODEL override.
JUDGE_MODEL="${JUDGE_MODEL:-glm-5.1}"
JUDGE_MODEL_ID=$(printf '%s' "$JUDGE_MODEL" | tr -c 'A-Za-z0-9_.-' '_')
JUDGE_WALL_TIMEOUT="${JUDGE_WALL_TIMEOUT:-900}"

LOG_DIR="$HOME/nous-agaas/logs"
STATE_DIR="$HOME/nous-agaas/state"
LOG="$LOG_DIR/daily-skill-evals.log"
STATE="$STATE_DIR/daily-skill-evals.last"
JUDGE_STATE="$STATE_DIR/daily-skill-evals.judge.${JUDGE_MODEL_ID}.last"
JUDGE_OUT_LOG="$LOG_DIR/daily-skill-evals.llm_judge.${JUDGE_MODEL_ID}.last.log"
mkdir -p "$LOG_DIR" "$STATE_DIR"

LOCK_DIR="$STATE_DIR/daily-skill-evals.lock"
NOW_EPOCH=$(date +%s)
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  LOCK_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "?")
  LOCK_STARTED=$(cat "$LOCK_DIR/started_at" 2>/dev/null || echo 0)
  LOCK_AGE=$((NOW_EPOCH - LOCK_STARTED))
  if [ "$LOCK_AGE" -gt "$JUDGE_WALL_TIMEOUT" ]; then
    echo "⚠️ stale daily-skill-evals lock pid=$LOCK_PID age=${LOCK_AGE}s; replacing" >> "$LOG"
    rm -rf "$LOCK_DIR"
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
      echo "⚠️ daily-skill-evals already running; lock recreated by another process" >> "$LOG"
      exit 0
    fi
  else
    echo "⚠️ daily-skill-evals already running pid=$LOCK_PID age=${LOCK_AGE}s; skipping overlapping run" >> "$LOG"
    exit 0
  fi
fi
echo "$$" > "$LOCK_DIR/pid"
echo "$NOW_EPOCH" > "$LOCK_DIR/started_at"
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

NOW=$(date "+%Y-%m-%dT%H:%M:%S%z")
echo "=== $NOW daily-skill-evals start ===" >> "$LOG"

FAILS=0
ALERTS=""
SUMMARY=""

# Pre-flight: required files exist
for f in "$RESOLVER" "$CHECK_RESOLVABLE" "$TRIGGER_EVAL" "$LLM_JUDGE"; do
  if [ ! -f "$f" ]; then
    echo "PROBE BROKEN: missing $f" >> "$LOG"
    ALERTS="${ALERTS}❌ probe broken: missing $f%0A"
    FAILS=$((FAILS+1))
  fi
done

if [ "$FAILS" -gt 0 ]; then
  echo "fails=$FAILS (pre-flight)" >> "$LOG"
else

  # 1. check_resolvable — any dark/orphan = FAIL
  RES_JSON=$(python3 "$CHECK_RESOLVABLE" --wiki "$WIKI" --json 2>&1)
  DARK=$(echo "$RES_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['counts']['dark'])" 2>/dev/null || echo "ERR")
  ORPH=$(echo "$RES_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['counts']['orphan'])" 2>/dev/null || echo "ERR")
  OK_N=$(echo "$RES_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['counts']['ok'])" 2>/dev/null || echo "ERR")

  if [ "$DARK" = "0" ] && [ "$ORPH" = "0" ]; then
    echo "✅ check_resolvable: $OK_N OK / 0 dark / 0 orphan" >> "$LOG"
    SUMMARY="${SUMMARY}✅ resolvable: $OK_N/$OK_N%0A"
  elif [ "$DARK" = "ERR" ] || [ "$ORPH" = "ERR" ]; then
    echo "❌ check_resolvable: probe broken (cannot parse JSON)" >> "$LOG"
    ALERTS="${ALERTS}❌ check_resolvable probe broken%0A"
    FAILS=$((FAILS+1))
  else
    echo "❌ check_resolvable: $OK_N OK / $DARK dark / $ORPH orphan" >> "$LOG"
    ALERTS="${ALERTS}❌ resolvable: $DARK dark / $ORPH orphan%0A"
    SUMMARY="${SUMMARY}❌ resolvable: $DARK dark / $ORPH orphan%0A"
    FAILS=$((FAILS+1))
  fi

  # 2. trigger_eval — record pass rate, alert on regression > 5%
  EVAL_OUT=$(python3 "$TRIGGER_EVAL" --resolver "$RESOLVER" 2>&1)
  PASS_LINE=$(echo "$EVAL_OUT" | grep -oE '[0-9]+/[0-9]+ passed' | head -1)
  PASSED=$(echo "$PASS_LINE" | awk -F'[/ ]' '{print $1}')
  TOTAL=$(echo "$PASS_LINE" | awk -F'[/ ]' '{print $2}')

  if [ -z "${PASSED:-}" ] || [ -z "${TOTAL:-}" ] || [ "$TOTAL" = "0" ]; then
    echo "❌ trigger_eval: probe broken (cannot parse pass line)" >> "$LOG"
    ALERTS="${ALERTS}❌ trigger_eval probe broken%0A"
    FAILS=$((FAILS+1))
  else
    RATE=$(python3 -c "print(round($PASSED/$TOTAL*100, 1))" 2>/dev/null || echo "0")
    LAST=$(cat "$STATE" 2>/dev/null || echo "0")
    DROP=$(python3 -c "print(1 if ($LAST - $RATE) > 5 else 0)" 2>/dev/null || echo "0")

    echo "📊 trigger_eval: $PASSED/$TOTAL = ${RATE}% (last: ${LAST}%)" >> "$LOG"
    SUMMARY="${SUMMARY}📊 trigger_eval: ${RATE}% (was ${LAST}%)%0A"

    if [ "$DROP" = "1" ]; then
      echo "❌ trigger_eval REGRESSION: $LAST% → $RATE%" >> "$LOG"
      ALERTS="${ALERTS}❌ trigger_eval REGRESSION: ${LAST}% → ${RATE}%%0A"
      FAILS=$((FAILS+1))
    fi

    echo "$RATE" > "$STATE"
  fi

  # 3. LLM judge — actual routing quality via $JUDGE_MODEL through LiteLLM.
  # Closes audit AP-23 (audit-tool METHOD must equal runtime METHOD); the naive
  # Jaccard matcher above is a proxy, this is ground truth.
  JUDGE_OUT=$(python3 - "$LLM_JUDGE" "$RESOLVER" "$JUDGE_MODEL" "$JUDGE_WALL_TIMEOUT" <<'PYEOF' 2>&1
import subprocess
import sys

script, resolver, model, timeout_raw = sys.argv[1:]
timeout = int(timeout_raw)
cmd = ["python3", script, "--resolver", resolver, "--model", model]

try:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    print(proc.stdout, end="")
    raise SystemExit(proc.returncode)
except subprocess.TimeoutExpired as exc:
    if exc.stdout:
        print(exc.stdout, end="")
    if exc.stderr:
        print(exc.stderr, end="")
    print(f"ERROR: llm_judge wall-timeout after {timeout}s")
    raise SystemExit(124)
PYEOF
  )
  JUDGE_RC=$?
  printf "%s\n" "$JUDGE_OUT" > "$JUDGE_OUT_LOG"
  JUDGE_PASS_LINE=$(echo "$JUDGE_OUT" | grep -oE 'LLM judge \([^)]+\): [0-9]+/[0-9]+' | head -1)
  JUDGE_PASSED=$(echo "$JUDGE_PASS_LINE" | grep -oE '[0-9]+/[0-9]+' | awk -F/ '{print $1}')
  JUDGE_TOTAL=$(echo "$JUDGE_PASS_LINE" | grep -oE '[0-9]+/[0-9]+' | awk -F/ '{print $2}')
  JUDGE_ERRORS=$(echo "$JUDGE_OUT" | grep -oE 'Errors: [0-9]+' | awk '{print $2}' | tail -1)
  JLAST=$(cat "$JUDGE_STATE" 2>/dev/null || echo "0")

  if [ "$JUDGE_RC" -ne 0 ]; then
    echo "❌ llm_judge ($JUDGE_MODEL): probe broken (exit=$JUDGE_RC; state preserved at ${JLAST}%; see $JUDGE_OUT_LOG)" >> "$LOG"
    ALERTS="${ALERTS}❌ llm_judge probe broken: exit=$JUDGE_RC (state preserved; see $JUDGE_OUT_LOG)%0A"
    SUMMARY="${SUMMARY}🤖 llm_judge: probe broken (state preserved; was ${JLAST}%)%0A"
    FAILS=$((FAILS+1))
  elif [ -z "${JUDGE_PASSED:-}" ] || [ -z "${JUDGE_TOTAL:-}" ] || [ "$JUDGE_TOTAL" = "0" ]; then
    echo "❌ llm_judge ($JUDGE_MODEL): probe broken (cannot parse pass line)" >> "$LOG"
    ALERTS="${ALERTS}❌ llm_judge probe broken (cannot parse pass line; see $JUDGE_OUT_LOG)%0A"
    SUMMARY="${SUMMARY}🤖 llm_judge: probe broken (state preserved; was ${JLAST}%)%0A"
    FAILS=$((FAILS+1))
  elif [ "$JUDGE_PASSED" = "0" ] && [ "${JUDGE_ERRORS:-0}" = "$JUDGE_TOTAL" ]; then
    echo "❌ llm_judge ($JUDGE_MODEL): probe broken ($JUDGE_ERRORS/$JUDGE_TOTAL model/API errors; state preserved at ${JLAST}%; see $JUDGE_OUT_LOG)" >> "$LOG"
    ALERTS="${ALERTS}❌ llm_judge probe broken: ${JUDGE_ERRORS}/${JUDGE_TOTAL} model/API errors (state preserved; see $JUDGE_OUT_LOG)%0A"
    SUMMARY="${SUMMARY}🤖 llm_judge: probe broken (state preserved; was ${JLAST}%)%0A"
    FAILS=$((FAILS+1))
  else
    JRATE=$(python3 -c "print(round($JUDGE_PASSED/$JUDGE_TOTAL*100, 1))" 2>/dev/null || echo "0")
    JDROP=$(python3 -c "print(1 if ($JLAST - $JRATE) > 5 else 0)" 2>/dev/null || echo "0")

    echo "🤖 llm_judge ($JUDGE_MODEL): $JUDGE_PASSED/$JUDGE_TOTAL = ${JRATE}% (last: ${JLAST}%)" >> "$LOG"
    SUMMARY="${SUMMARY}🤖 llm_judge: ${JRATE}% (was ${JLAST}%)%0A"

    if [ "$JDROP" = "1" ]; then
      echo "❌ llm_judge REGRESSION: $JLAST% → $JRATE%" >> "$LOG"
      ALERTS="${ALERTS}❌ llm_judge REGRESSION: ${JLAST}% → ${JRATE}%%0A"
      FAILS=$((FAILS+1))
    fi

    echo "$JRATE" > "$JUDGE_STATE"
  fi

  echo "fails=$FAILS" >> "$LOG"
fi

# Telegram on FAIL only (Karpathy bad-news-loud, good-news-quiet)
if [ "$FAILS" -gt 0 ] && [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  MSG="🔴 daily-skill-evals — $FAILS failure(s) ($NOW)%0A%0A${ALERTS}%0ACurrent state:%0A${SUMMARY}%0ALog: $LOG"
  curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=${MSG}" >> "$LOG" 2>&1
elif [ "$FAILS" -eq 0 ]; then
  echo "🟢 all green; no telegram (Karpathy good-news-quiet)" >> "$LOG"
fi

echo "=== $NOW daily-skill-evals end (fails=$FAILS) ===" >> "$LOG"
exit "$FAILS"
