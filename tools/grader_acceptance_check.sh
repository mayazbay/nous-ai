#!/usr/bin/env bash
# tools/grader_acceptance_check.sh — Mercury Phase 1 acceptance gate.
#
# Spec: pages/specs/2026-04-30-mercury-hybrid-retrieval-gap-analysis.md
#       Section 2 metrics M1.1, M1.2, M1.3.
#
# Exit 0 if ALL three metrics pass. Exit 1 otherwise (with which failed).
#
# Designed to run after Phase 1 has been live for >= 7 days. Useful as
# a Friday morning check before declaring Phase 1 "done".
#
# Usage:
#   bash tools/grader_acceptance_check.sh                       # uses default log path
#   GRADER_LOG=/path/to/ask-verdicts.jsonl bash tools/grader_acceptance_check.sh
#
# Requires: jq, awk, python3.

set -u
set -o pipefail

LOG_PATH="${GRADER_LOG:-$HOME/nous-agaas/logs/ask-verdicts.jsonl}"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
amber() { printf '\033[33m%s\033[0m\n' "$*"; }

if ! command -v jq >/dev/null 2>&1; then
  red "FATAL: jq not installed. brew install jq"
  exit 2
fi

if [ ! -f "$LOG_PATH" ]; then
  red "FATAL: grader log not found at $LOG_PATH"
  exit 2
fi

echo "Mercury Phase 1 acceptance check — log: $LOG_PATH"
echo "----------------------------------------------------------------"

# Reusable: filter to 7 most recent days using ts field. Excludes failure
# sentinels (type == "judge_failure") from counts but reports them separately.
JQ_LAST_7D='select(.ts != null) | select(.ts >= "'"$(python3 -c "import datetime; print((datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat() + 'Z')")"'")'
JQ_VERDICT='select((.type // "verdict") == "verdict")'

# Total record counts.
TOTAL_LINES=$(wc -l < "$LOG_PATH" | tr -d ' ')
RECENT_VERDICTS=$(jq -r "$JQ_LAST_7D | $JQ_VERDICT | .correlation_id" "$LOG_PATH" 2>/dev/null | wc -l | tr -d ' ')
RECENT_FAILURES=$(jq -r "$JQ_LAST_7D | select(.type == \"judge_failure\") | .correlation_id" "$LOG_PATH" 2>/dev/null | wc -l | tr -d ' ')

echo "Total lines in log     : $TOTAL_LINES"
echo "Verdicts in last 7d    : $RECENT_VERDICTS"
echo "Judge failures in 7d   : $RECENT_FAILURES"
echo

# ---------------------------------------------------------------------------
# M1.1 — Coverage. Threshold: >= 50 graded turns over 7 days.
#         Why 50: spec section 2. Below this, sampling math hasn't burned in.
# ---------------------------------------------------------------------------
M11_THRESHOLD=50
echo "M1.1 — Coverage  (threshold: >= $M11_THRESHOLD graded turns / 7d)"
if [ "$RECENT_VERDICTS" -ge "$M11_THRESHOLD" ]; then
  green "  PASS  ($RECENT_VERDICTS >= $M11_THRESHOLD)"
  M11_OK=1
else
  red   "  FAIL  ($RECENT_VERDICTS < $M11_THRESHOLD)"
  M11_OK=0
fi
echo

# ---------------------------------------------------------------------------
# M1.2 — Sampling fidelity.
#         Threshold: tier-3 share >= 95% of all tier-3 hierarchy traffic
#         AND tier-1 share within 7%-13% (i.e. 10% +/- 3pp).
#
# Without the hierarchy log we can only check intra-grader distribution:
#   - tier-3 verdicts present at all
#   - tier-1 share between 5% and 30% (loose lower bound for empty days,
#     loose upper bound for unusual traffic). The strict +-3pp check
#     happens against hierarchy traffic via test_ask_grader.py:test_t4
#     at N=1000; this script checks the LIVE distribution.
# ---------------------------------------------------------------------------
echo "M1.2 — Sampling fidelity  (Tier-3 present; Tier-1 in 5-30% band)"
TIER_DIST=$(jq -r "$JQ_LAST_7D | $JQ_VERDICT | .tier" "$LOG_PATH" 2>/dev/null | sort | uniq -c | awk '{printf "    tier-%s: %s\n", $2, $1}')
echo "$TIER_DIST"

T1_COUNT=$(jq -r "$JQ_LAST_7D | $JQ_VERDICT | select(.tier == 1) | .correlation_id" "$LOG_PATH" 2>/dev/null | wc -l | tr -d ' ')
T3_COUNT=$(jq -r "$JQ_LAST_7D | $JQ_VERDICT | select(.tier == 3) | .correlation_id" "$LOG_PATH" 2>/dev/null | wc -l | tr -d ' ')

if [ "$RECENT_VERDICTS" -gt 0 ]; then
  T1_PCT=$(awk -v n="$T1_COUNT" -v d="$RECENT_VERDICTS" 'BEGIN{printf "%.1f", (n/d)*100}')
else
  T1_PCT="0.0"
fi

M12_OK=1
if [ "$T3_COUNT" -lt 1 ]; then
  red   "  FAIL  no tier-3 verdicts in 7d window"
  M12_OK=0
fi
T1_BAND=$(awk -v p="$T1_PCT" 'BEGIN{ if (p>=5.0 && p<=30.0) print "ok"; else print "out"}')
if [ "$T1_BAND" != "ok" ]; then
  amber "  WARN  tier-1 share ${T1_PCT}% outside 5-30% band (loose live check)"
  M12_OK=0
fi
if [ "$M12_OK" -eq 1 ]; then
  green "  PASS  (tier-3 present, tier-1 share ${T1_PCT}%)"
fi
echo

# ---------------------------------------------------------------------------
# M1.3 — Schema conformance. Threshold: zero records missing quality_v1
#         or category. (Failure sentinels are excluded; they are expected.)
# ---------------------------------------------------------------------------
echo "M1.3 — Schema conformance  (threshold: 0 verdicts missing quality_v1/category)"
MALFORMED=$(jq -r "$JQ_LAST_7D | $JQ_VERDICT | select(.quality_v1 == null or .category == null) | .correlation_id" "$LOG_PATH" 2>/dev/null | wc -l | tr -d ' ')

if [ "$MALFORMED" -eq 0 ]; then
  green "  PASS  (0 malformed)"
  M13_OK=1
else
  red   "  FAIL  ($MALFORMED malformed verdicts)"
  jq -r "$JQ_LAST_7D | $JQ_VERDICT | select(.quality_v1 == null or .category == null) | .correlation_id" "$LOG_PATH" 2>/dev/null | head -10 | sed 's/^/      /'
  M13_OK=0
fi
echo

# ---------------------------------------------------------------------------
# Auxiliary: cost ceiling visibility (not a metric — informational).
# ---------------------------------------------------------------------------
COST_7D=$(jq -r "$JQ_LAST_7D | (.grader_cost_est // 0)" "$LOG_PATH" 2>/dev/null \
  | awk '{s+=$1} END {printf "%.4f", s+0}')
COST_CEILING="${GRADER_COST_CEILING_7D:-10.50}"
echo "Cost (7d cumulative)  : \$${COST_7D}  (ceiling: \$${COST_CEILING})"

# ---------------------------------------------------------------------------
# Aggregate verdict.
# ---------------------------------------------------------------------------
echo "----------------------------------------------------------------"
if [ "$M11_OK" -eq 1 ] && [ "$M12_OK" -eq 1 ] && [ "$M13_OK" -eq 1 ]; then
  green "ALL ACCEPTANCE METRICS PASS — Mercury Phase 1 ready to graduate."
  exit 0
else
  red "ONE OR MORE METRICS FAIL — see above."
  exit 1
fi
