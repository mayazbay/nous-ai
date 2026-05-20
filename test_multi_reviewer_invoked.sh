#!/usr/bin/env bash
# tools/test_multi_reviewer_invoked.sh
#
# karpathy-loop AP-5 mechanical detector. For each recent HANDOFF-*.md that
# claims a multi-reviewer pass or describes a triggering plan (>2h work /
# >3 subsystems / >200 lines / new doctrine skill / new infra gate /
# user-facing behavior change), grep the session's tool-call log for evidence
# of Skill(plan-*-review|autoplan) invocation. Missing evidence = AP-5
# violation (mental-simulation hard-banned for triggering plans).
#
# Usage:
#   bash tools/test_multi_reviewer_invoked.sh           # scan last 24h handoffs, print findings
#   bash tools/test_multi_reviewer_invoked.sh --json    # machine-readable
#   bash tools/test_multi_reviewer_invoked.sh --since 7  # last N days
#
# Exit codes:
#   0 = all triggering handoffs have evidence (or none triggered)
#   1 = at least one AP-5 violation found (missing evidence)
#   2 = environment / fatal error
#
# Wired into com.nous.light-probe (15-min cron on Air) — see karpathy-loop v1.11.0.

set -uo pipefail

# Defaults
SINCE_DAYS=1
JSON=0
VAULT_ROOT="${VAULT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SESSIONS_GLOB="${SESSIONS_GLOB:-$HOME/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/*.jsonl}"

while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1 ;;
    --since) shift; SINCE_DAYS="${1:-1}" ;;
    -h|--help) sed -n '1,30p' "$0"; exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

if ! command -v find >/dev/null; then echo "find required" >&2; exit 2; fi
if ! command -v grep >/dev/null; then echo "grep required" >&2; exit 2; fi

# Triggering keywords (mirrored from karpathy-loop AP-5)
# Any handoff matching one of these is considered "triggering"
TRIGGER_PATTERNS=(
  "axis #3"
  "axis 3"
  "Multi-reviewer pass"
  "multi-reviewer"
  ">2h"
  "more than 2 hours"
  ">3 subsystems"
  ">200 lines"
  "new doctrine"
  "new infra gate"
  "user-facing behavior"
  "user-facing change"
)

# Evidence tokens (any of these in session jsonl satisfies the gate)
EVIDENCE_TOKENS=(
  'Skill(plan-ceo-review)'
  'Skill(plan-devex-review)'
  'Skill(plan-design-review)'
  'Skill(plan-eng-review)'
  'Skill(autoplan)'
  '"plan-ceo-review"'
  '"plan-devex-review"'
  '"plan-design-review"'
  '"plan-eng-review"'
  '"autoplan"'
)

# Find recent HANDOFFs (bash-3 compatible: read into array via loop)
HANDOFFS=()
while IFS= read -r f; do
  HANDOFFS+=("$f")
done < <(find "$VAULT_ROOT/pages/progress" -maxdepth 1 -type f -name "HANDOFF-*.md" -mtime -"$SINCE_DAYS" 2>/dev/null | sort -r)

if [ "${#HANDOFFS[@]}" -eq 0 ]; then
  if [ "$JSON" = "1" ]; then
    printf '{"scanned": 0, "triggering": 0, "violations": 0, "details": []}\n'
  else
    echo "No HANDOFFs in the last $SINCE_DAYS day(s)."
  fi
  exit 0
fi

# Helper: does file contain any pattern from a list?
file_matches_any() {
  local file="$1"; shift
  for pat in "$@"; do
    if grep -qi -- "$pat" "$file" 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

# Helper: do any session jsonl files contain any evidence token?
sessions_have_evidence() {
  for token in "${EVIDENCE_TOKENS[@]}"; do
    # use bash glob with set -- (no quoting on SESSIONS_GLOB)
    # shellcheck disable=SC2086
    if grep -l -- "$token" $SESSIONS_GLOB 2>/dev/null | head -1 | grep -q .; then
      return 0
    fi
  done
  return 1
}

scanned=0
triggering=0
violations=0
details_json="[]"
details=()

for handoff in "${HANDOFFS[@]}"; do
  scanned=$((scanned + 1))
  rel="${handoff#$VAULT_ROOT/}"
  if file_matches_any "$handoff" "${TRIGGER_PATTERNS[@]}"; then
    triggering=$((triggering + 1))
    if sessions_have_evidence; then
      verdict="evidence_found"
    else
      verdict="VIOLATION_no_evidence"
      violations=$((violations + 1))
    fi
    details+=("$rel:$verdict")
    details_json=$(python3 -c "
import json, sys
existing = json.loads('''$details_json''')
existing.append({'handoff': '''$rel''', 'verdict': '''$verdict'''})
print(json.dumps(existing))
")
  fi
done

if [ "$JSON" = "1" ]; then
  printf '{"scanned": %d, "triggering": %d, "violations": %d, "details": %s}\n' \
    "$scanned" "$triggering" "$violations" "$details_json"
else
  echo "Scanned $scanned handoff(s) in last $SINCE_DAYS day(s)."
  echo "Triggering plans (per AP-5 thresholds): $triggering"
  echo "AP-5 violations (no Skill(plan-*-review|autoplan) evidence): $violations"
  if [ "$triggering" -gt 0 ]; then
    echo
    echo "Per-handoff verdicts:"
    for d in "${details[@]}"; do echo "  $d"; done
  fi
fi

if [ "$violations" -gt 0 ]; then
  exit 1
fi
exit 0
