#!/bin/bash
# Verify the Musk/Karpathy/Tan top-CTO loop is wired into the runtime substrate.
set -u

SCRIPT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -z "${VAULT:-}" ]; then
  if [ -d "$SCRIPT_ROOT/pages/skills" ]; then
    VAULT="$SCRIPT_ROOT"
  elif [ -d "$SCRIPT_ROOT/wiki/pages/skills" ]; then
    VAULT="$SCRIPT_ROOT/wiki"
  else
    VAULT="$SCRIPT_ROOT"
  fi
fi
SKILLS_ROOT="$VAULT/pages/skills"
if [ ! -d "$SKILLS_ROOT" ]; then
  SKILLS_ROOT="$VAULT/skills"
fi
SOC="$SKILLS_ROOT/session-operating-contract/SKILL.md"
KAR="$SKILLS_ROOT/karpathy-loop/SKILL.md"
COORD="$SKILLS_ROOT/session-coordination/SKILL.md"
RES="$SKILLS_ROOT/_gbrain/RESOLVER.md"
AGENTS="$VAULT/../AGENTS.md"
CODEX_LAUNCHER="$VAULT/tools/codex-nous.sh"
CODEX_LAUNCHER_TEST="$VAULT/tools/test_codex_nous_launcher.sh"
FAIL=0

version_of() {
  awk -F': ' '/^version:/{print $2; exit}' "$1"
}

need() {
  local file="$1"
  local pattern="$2"
  if [ ! -f "$file" ]; then
    echo "FAIL: missing file: $file"
    FAIL=1
    return
  fi
  if ! grep -Fq "$pattern" "$file"; then
    echo "FAIL: $file missing: $pattern"
    FAIL=1
  fi
}

need "$SOC" "Billion-dollar tiny-team agent loop"
need "$SOC" "External action packet format"
need "$SOC" "Validator we will run"
need "$SOC" "The one-line self-test"

need "$KAR" "Top-CTO decision loop"
need "$KAR" "Thin harness, fat skills, deterministic gates"
need "$KAR" "Every non-trivial action runs these 10 questions"
need "$KAR" "Software 3.0 / Spec-As-Source Loop"
need "$KAR" "intent -> spec -> validator -> agent lane -> artifact -> skill/gbrain update"
need "$KAR" "A prompt is not source until it lands in a durable artifact"
need "$KAR" "Every spec has at least one validator"
need "$KAR" "Agent output is accepted only when the validator passes or the failure is codified"

need "$COORD" "Four-session handshake is the default for broad audits"
need "$COORD" "Controller lane"
need "$COORD" "Three helper lanes"
need "$COORD" "Handshake check:"
need "$COORD" 'controller runs `session_scan.sh` after helper registration'
need "$COORD" "Integration rule:"
need "$COORD" "git commit -o <paths>"
need "$COORD" "Close rule:"
need "$COORD" 'Local interactive Codex uses `tools/codex-nous.sh`'
need "$COORD" "### AP-15"

need "$CODEX_LAUNCHER" "session_self_register.sh"
need "$CODEX_LAUNCHER" 'exec "$CODEX_BIN" "$@"'
need "$CODEX_LAUNCHER_TEST" "codex-nous-launcher"
need "$CODEX_LAUNCHER_TEST" "fake-codex"

for skill in session-operating-contract karpathy-loop musk-algorithm session-architecture session-coordination; do
  need "$RES" "skills/$skill/SKILL.md"
done

if [ -f "$AGENTS" ]; then
  need "$AGENTS" "session-operating-contract"
  need "$AGENTS" "musk-algorithm"
  need "$AGENTS" "karpathy-loop"
  need "$AGENTS" "session-operating-contract/SKILL.md"
  need "$AGENTS" "v$(version_of "$SOC")"
  need "$AGENTS" "[[skills/musk-algorithm]] v$(version_of "$SKILLS_ROOT/musk-algorithm/SKILL.md")"
  need "$AGENTS" "[[skills/karpathy-loop]] v$(version_of "$KAR")"
fi

CLAUDE_SHIM="$VAULT/CLAUDE.md"
if [ -f "$CLAUDE_SHIM" ]; then
  need "$CLAUDE_SHIM" "[[session-operating-contract]] v$(version_of "$SOC")"
  need "$CLAUDE_SHIM" "[[musk-algorithm]] v$(version_of "$SKILLS_ROOT/musk-algorithm/SKILL.md")"
  need "$CLAUDE_SHIM" "[[karpathy-loop]] v$(version_of "$KAR")"
  need "$CLAUDE_SHIM" "[[session-coordination]] v$(version_of "$COORD")"
fi

if [ "$FAIL" -eq 0 ]; then
  echo "OK: top-CTO loop wired in SOC, karpathy-loop, session-coordination, Codex launcher, RESOLVER, and AGENTS shim"
fi
exit "$FAIL"
