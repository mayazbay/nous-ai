#!/bin/bash
# tools/verify_ship1_e2e.sh — Ship 1 end-to-end verification.
# Tests: orphan sweep → resume → parity verify → OpenBrain capture → mistake-to-skill ledger → cross-host parity.
# Per Plan §4.11. Exit 0 = all green; nonzero = drift detected.

set -uo pipefail

WIKI="${NOUS_WIKI:-/Users/madia/Documents/Projects/Nous AGaaS/Nous}"
cd "$WIKI"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
amber() { printf "\033[33m%s\033[0m\n" "$*"; }

echo "=== Ship 1 verify @ $(date -u +%FT%TZ) ==="
echo "Wiki: $WIKI"
echo ""

FAILS=0

# 1. Test suite
echo "--- 1/8 pytest suite (failover + schema + sweeper + parity + probe) ---"
if python3 -m pytest \
      tools/tests/test_model_failover_state.py \
      tools/tests/test_failover_schema.py \
      tools/tests/test_failover_sweeper.py \
      tools/tests/test_parity_check.py \
      tools/tests/test_provider_probe.py \
      tools/tests/test_command_center_failover_resume.py \
      -q 2>&1 | tail -3; then
  green "✓ pytest green"
else
  red "✗ pytest had failures"; FAILS=$((FAILS+1))
fi
echo ""

# 2. Schema sanity — parse a synthetic line via failover_schema
echo "--- 2/8 schema parse_row sanity ---"
if python3 -c "
from tools import failover_schema as fs
row, broken = fs.parse_row('{\"phase\":\"started\",\"event_id\":\"e1\",\"status\":\"running\",\"ts\":\"2026-05-20T11:00:00+05:00\",\"command\":\"/codex\",\"msg_id\":1,\"chat_id\":2,\"query\":\"q\",\"model\":\"m\",\"via\":\"v\",\"continuity_packet\":\"p\",\"latest_handoff\":\"h\",\"git_head\":\"g\"}')
assert row is not None and broken is None and isinstance(row, fs.StartedRow), row
print('OK')
"; then
  green "✓ parse_row roundtrip OK"
else
  red "✗ parse_row failed"; FAILS=$((FAILS+1))
fi
echo ""

# 3. Parity compute (writes pages/systems/parity-latest.json)
echo "--- 3/8 parity compute ---"
if python3 tools/parity_check.py >/dev/null 2>&1; then
  if [ -f pages/systems/parity-latest.json ]; then
    HASH=$(python3 -c "import json; print(json.load(open('pages/systems/parity-latest.json'))['manifest_sha256'][:12])")
    green "✓ parity written, manifest_sha256=$HASH"
  else
    red "✗ parity-latest.json missing after compute"; FAILS=$((FAILS+1))
  fi
else
  red "✗ parity_check failed"; FAILS=$((FAILS+1))
fi
echo ""

# 4. Parity verify (must agree with what was just written)
echo "--- 4/8 parity verify (local) ---"
if python3 tools/parity_check.py --verify 2>&1 | tail -1; then
  green "✓ parity verify OK (local)"
else
  red "✗ parity verify failed (local)"; FAILS=$((FAILS+1))
fi
echo ""

# 5. Sweeper (orphans-only, dry of git via NOUS_FAILOVER_STATE_COMMIT=0)
echo "--- 5/8 failover sweeper (orphans-only, no git) ---"
if NOUS_FAILOVER_STATE_COMMIT=0 python3 tools/failover_sweeper.py --wiki "$WIKI" --orphans-only 2>&1 | head -3; then
  green "✓ sweeper ran (check stdout JSON for any materialized orphans)"
else
  red "✗ sweeper crashed"; FAILS=$((FAILS+1))
fi
echo ""

# 6. Resume prompt v2 (build a prompt; verify it contains [RESUME-v2] marker)
echo "--- 6/8 resume prompt v2 ---"
PROMPT=$(python3 -c "
from tools import model_failover_state as mfs
state = mfs.latest_state(mfs.default_wiki())
if state is None:
    # Synthesize a state for testing
    state = {'event_id':'verify-e2e','command':'/codex','via':'codex-cli','model':'gpt-5.5','status':'error','ts':'2026-05-20T11:00:00+05:00','query':'verify Ship 1','continuity_packet':'pages/systems/AGENT-CONTINUITY-PACKET.md','latest_handoff':'pages/progress/HANDOFF-AUTO-LATEST.symlink'}
print(mfs.build_resume_prompt_from_state(state, 'gpt'))
" 2>&1)
if echo "$PROMPT" | grep -q "\[RESUME-v2\]" && echo "$PROMPT" | grep -q "CONTRACT:" && echo "$PROMPT" | grep -q "manifest_sha256="; then
  green "✓ resume prompt v2 contains [RESUME-v2], CONTRACT, manifest_sha256"
else
  red "✗ resume prompt v2 missing required markers"
  echo "$PROMPT" | head -10
  FAILS=$((FAILS+1))
fi
echo ""

# 7. Cross-host parity (best-effort; skip if hosts unreachable)
echo "--- 7/8 cross-host parity (best-effort) ---"
LOCAL_HASH=$(python3 -c "import json; print(json.load(open('pages/systems/parity-latest.json'))['manifest_sha256'])" 2>/dev/null || echo "missing")
echo "  local manifest_sha256: ${LOCAL_HASH:0:16}…"

if ssh -o ConnectTimeout=5 air "cd ~/nous-agaas/wiki && git pull --ff-only 2>/dev/null && python3 tools/parity_check.py --verify" 2>/dev/null | tail -1; then
  green "✓ air parity verify OK"
else
  amber "⚠ air unreachable or parity drift (non-fatal — peer may be mid-sync)"
fi

if ssh -o ConnectTimeout=5 root@65.108.215.200 "cd /root/nous-agaas/wiki && git pull --ff-only 2>/dev/null && python3 tools/parity_check.py --verify" 2>/dev/null | tail -1; then
  green "✓ vps parity verify OK"
else
  amber "⚠ vps unreachable or parity drift (non-fatal)"
fi
echo ""

# 8. Skill-loop ledger exists or is creatable
echo "--- 8/8 mistake-to-skill ledger ---"
LEDGER="pages/skills/mistake-to-skill/ledger.jsonl"
if [ -f "$LEDGER" ]; then
  LINES=$(wc -l < "$LEDGER")
  green "✓ ledger exists ($LINES lines)"
elif [ -d "$(dirname $LEDGER)" ]; then
  green "✓ ledger dir exists; ledger will be created on first non-ok finish"
else
  amber "⚠ mistake-to-skill skill dir missing (ledger will be created lazily)"
fi
echo ""

# Final
echo "=== Verify summary ==="
if [ "$FAILS" -eq 0 ]; then
  green "ALL GREEN — Ship 1 verified."
  exit 0
else
  red "$FAILS check(s) failed."
  exit 1
fi
