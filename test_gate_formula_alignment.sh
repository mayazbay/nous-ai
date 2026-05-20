#!/usr/bin/env bash
# tools/test_gate_formula_alignment.sh
#
# library-grade-audit AP-11 mechanical detector. For each gate row in
# pages/skills/library-grade-audit/SKILL.md that consumes a downstream
# tools/*.py --dry-run JSON output via jq, verify every JSON field the
# formula references actually exists in the downstream script's output
# schema. A formula referencing a field the script no longer emits causes
# the gate to compute against undefined values, silently producing
# permanent-RED or false-GREEN.
#
# This catches the failure mode codified as AP-11 in library-grade-audit
# v1.6.1: round-3 Gate 7.1 formula `(.deferred / .orphans_scanned) <= 0.05`
# was correct against openbrain-projection v1.1.0 but went stale the
# moment peer s1729-mac-87156 shipped v1.2.0 AP-7 with new terminal-state
# counters (deferred_marked, deferred_already_marked). Gate stuck at 68%
# RED for ~50 min until v1.6.1 realigned the formula.
#
# Usage:
#   bash tools/test_gate_formula_alignment.sh           # human output
#   bash tools/test_gate_formula_alignment.sh --json    # machine-readable
#   bash tools/test_gate_formula_alignment.sh --strict  # exit 1 on drift
#
# Exit codes:
#   0 = all gate formulas align with downstream script schemas
#   1 = at least one drift (formula refs missing field) AND --strict
#   2 = environment / fatal error
#
# Wired into com.nous.light-probe (15-min cron on Air) — see
# library-grade-audit v1.7.0.

set -uo pipefail

JSON=0
STRICT=0
VAULT_ROOT="${VAULT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SKILL_FILE="$VAULT_ROOT/pages/skills/library-grade-audit/SKILL.md"

while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1 ;;
    --strict) STRICT=1 ;;
    -h|--help) sed -n '1,30p' "$0"; exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

[ -f "$SKILL_FILE" ] || { echo "FATAL: $SKILL_FILE not found" >&2; exit 2; }

# Extract gate rows. We look for lines that contain a `tools/X.py ... | jq '...'`
# fragment inside backticks. Pipe to a temp file for line-by-line processing.
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

# Capture each line that has a jq formula referencing tools/*.py.
# Format we emit per line: <gate_label>\t<script>\t<formula>
grep -E "tools/[a-z_]+\.py.*\| jq" "$SKILL_FILE" | while IFS= read -r line; do
  # Gate label: first column of the markdown table row (strip leading "| ")
  gate=$(printf '%s' "$line" | sed -E 's/^\| *//; s/ *\|.*//')
  # Script path: first match of tools/<name>.py
  script=$(printf '%s' "$line" | grep -oE 'tools/[a-z_]+\.py' | head -1)
  # Formula: text between `| jq '` and the next `'`
  formula=$(printf '%s' "$line" | sed -nE "s/.*\\| jq +'([^']+)'.*/\\1/p")
  [ -z "$script" ] && continue
  [ -z "$formula" ] && continue
  printf '%s\t%s\t%s\n' "$gate" "$script" "$formula" >> "$tmp"
done

# Helpers
extract_fields_from_formula() {
  # Match .word patterns (alphanumeric+underscore after the dot)
  printf '%s' "$1" | grep -oE '\.[a-zA-Z_][a-zA-Z0-9_]*' | sort -u | sed 's/^\.//'
}

extract_fields_from_script() {
  local script_path="$1"
  [ -f "$VAULT_ROOT/$script_path" ] || return 1
  # Heuristic: grep all "key": and summary["key"] / d['key'] / d.get('key' patterns
  {
    grep -oE '"[a-zA-Z_][a-zA-Z0-9_]*"\s*:' "$VAULT_ROOT/$script_path" \
      | sed -E 's/^"//; s/"\s*:$//'
    grep -oE "'[a-zA-Z_][a-zA-Z0-9_]+'" "$VAULT_ROOT/$script_path" \
      | tr -d "'"
  } | sort -u
}

# Initialize counters / findings (handle empty case explicitly for set -u)
gate_count=0
drift_count=0
findings=()

if [ -s "$tmp" ]; then
  while IFS=$'\t' read -r gate script formula; do
    [ -z "$gate" ] && continue
    gate_count=$((gate_count + 1))
    formula_fields=$(extract_fields_from_formula "$formula")

    if ! script_fields=$(extract_fields_from_script "$script"); then
      findings+=("MISSING_SCRIPT|$gate|$script|script not found at $script")
      drift_count=$((drift_count + 1))
      continue
    fi

    missing=()
    for f in $formula_fields; do
      if ! printf '%s\n' "$script_fields" | grep -qx "$f"; then
        missing+=("$f")
      fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
      csv=$(IFS=,; echo "${missing[*]}")
      findings+=("DRIFT|$gate|$script|missing=$csv")
      drift_count=$((drift_count + 1))
    else
      n=$(echo "$formula_fields" | wc -w | tr -d ' ')
      findings+=("OK|$gate|$script|all $n fields present")
    fi
  done < "$tmp"
fi

# Output
if [ $JSON -eq 1 ]; then
  printf '{"gates_scanned":%d,"drift_count":%d,"findings":[' "$gate_count" "$drift_count"
  first=1
  if [ ${#findings[@]} -gt 0 ]; then
    for f in "${findings[@]}"; do
      [ $first -eq 0 ] && printf ','
      first=0
      IFS='|' read -r status gate script detail <<<"$f"
      # Escape quotes in detail
      detail_esc=$(printf '%s' "$detail" | sed 's/"/\\"/g')
      printf '{"status":"%s","gate":"%s","script":"%s","detail":"%s"}' \
        "$status" "$gate" "$script" "$detail_esc"
    done
  fi
  printf ']}\n'
else
  echo "library-grade-audit gate-formula alignment scan"
  echo "Skill:  $(printf '%s' "$SKILL_FILE" | sed "s|$VAULT_ROOT/||")"
  echo "Gates:  $gate_count   Drift:  $drift_count"
  echo ""
  if [ ${#findings[@]} -gt 0 ]; then
    for f in "${findings[@]}"; do
      IFS='|' read -r status gate script detail <<<"$f"
      case "$status" in
        OK)             echo "  ✅ [$gate]  -> $script  ($detail)" ;;
        DRIFT)          echo "  🔴 DRIFT [$gate]  -> $script  ($detail)" ;;
        MISSING_SCRIPT) echo "  ⚠️  MISSING [$gate]  -> $script  ($detail)" ;;
      esac
    done
  fi
fi

if [ $drift_count -gt 0 ] && [ $STRICT -eq 1 ]; then
  exit 1
fi
exit 0
