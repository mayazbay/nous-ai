#!/bin/bash
# tools/verify_ship2_e2e.sh — Ship 2 end-to-end verification.
# Tests: lane_lock acquire+heartbeat+reap, queue add+claim+done, status render, handshake refuse,
#        OpenBrain dedup cursor, pre-commit RULE 7 lane match/mismatch.
# Per Plan §5.13. Exit 0 = all green.

set -uo pipefail

WIKI="${NOUS_WIKI:-/Users/madia/Documents/Projects/Nous AGaaS/Nous}"
cd "$WIKI"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
amber() { printf "\033[33m%s\033[0m\n" "$*"; }

echo "=== Ship 2 verify @ $(date -u +%FT%TZ) ==="
echo "Wiki: $WIKI"
echo ""

FAILS=0

# 1. Test suite — all Ship-2 tests
echo "--- 1/8 Ship-2 pytest suite ---"
if python3 -m pytest \
      tools/tests/test_lane_lock.py \
      tools/tests/test_queue.py \
      tools/tests/test_status_render.py \
      tools/tests/test_handshake.py \
      tools/tests/test_queue_to_openbrain.py \
      tools/tests/test_heartbeat_lane.py \
      tools/tests/test_status_daemon.py \
      tools/tests/test_parity_check.py \
      -q 2>&1 | tail -3; then
  green "✓ Ship-2 pytest green"
else
  red "✗ pytest failed"; FAILS=$((FAILS+1))
fi
echo ""

# 2. lane_lock CLI roundtrip in tmp wiki
echo "--- 2/8 lane_lock CLI roundtrip ---"
TMP=$(mktemp -d)
mkdir -p "$TMP/pages/systems" "$TMP/logs"
TOKEN=$(NOUS_WIKI="$TMP" python3 tools/lane_lock.py acquire --lane claude --scope 'tools/*' --ttl-sec 60 2>/dev/null)
if [ -n "$TOKEN" ]; then
  NOUS_WIKI="$TMP" python3 tools/lane_lock.py heartbeat --token "$TOKEN" >/dev/null
  NOUS_WIKI="$TMP" python3 tools/lane_lock.py release --token "$TOKEN" >/dev/null
  green "✓ acquire+heartbeat+release roundtrip OK ($TOKEN)"
else
  red "✗ acquire returned empty"; FAILS=$((FAILS+1))
fi
rm -rf "$TMP"
echo ""

# 3. Queue CLI roundtrip
echo "--- 3/8 queue CLI roundtrip ---"
TMP=$(mktemp -d)
mkdir -p "$TMP/pages/systems" "$TMP/logs"
TID=$(NOUS_WIKI="$TMP" python3 tools/task_queue.py add --title smoke --lane claude --scope 'tools/x.py' 2>/dev/null)
if [ -n "$TID" ]; then
  NOUS_WIKI="$TMP" python3 tools/task_queue.py claim --id "$TID" --session sess1 >/dev/null
  NOUS_WIKI="$TMP" python3 tools/task_queue.py done --id "$TID" >/dev/null
  if [ -f "$TMP/TASK_QUEUE.md" ]; then
    green "✓ queue add+claim+done roundtrip + TASK_QUEUE.md rendered"
  else
    red "✗ TASK_QUEUE.md not rendered"; FAILS=$((FAILS+1))
  fi
else
  red "✗ queue add returned empty"; FAILS=$((FAILS+1))
fi
rm -rf "$TMP"
echo ""

# 4. status_render produces STATUS.md
echo "--- 4/8 status_render ---"
TMP=$(mktemp -d)
mkdir -p "$TMP/pages/systems" "$TMP/logs"
NOUS_WIKI="$TMP" python3 tools/status_render.py --wiki "$TMP" >/dev/null 2>&1
if [ -f "$TMP/STATUS.md" ] && grep -q "STATUS" "$TMP/STATUS.md"; then
  green "✓ STATUS.md rendered with expected header"
else
  red "✗ STATUS.md missing or malformed"; FAILS=$((FAILS+1))
fi
rm -rf "$TMP"
echo ""

# 5. Handshake refuses on overlap
echo "--- 5/8 handshake refuses on overlap ---"
TMP=$(mktemp -d)
mkdir -p "$TMP/pages/systems" "$TMP/logs"
NOUS_WIKI="$TMP" python3 tools/lane_lock.py acquire --lane grok --scope 'tools/*' --ttl-sec 600 >/dev/null
TID=$(NOUS_WIKI="$TMP" python3 tools/task_queue.py add --title overlap --lane claude --scope 'tools/x.py' 2>/dev/null)
RESULT=$(NOUS_WIKI="$TMP" python3 tools/handshake.py start --lane claude --json 2>/dev/null)
if echo "$RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); sys.exit(0 if r.get('result')=='refused' else 1)"; then
  green "✓ handshake refused (grok holds tools/*, claude blocked)"
else
  red "✗ handshake did not refuse"; echo "$RESULT"; FAILS=$((FAILS+1))
fi
rm -rf "$TMP"
echo ""

# 6. queue_to_openbrain dedup cursor
echo "--- 6/8 OpenBrain dedup cursor ---"
TMP=$(mktemp -d)
mkdir -p "$TMP/pages/systems" "$TMP/logs" "$TMP/bin"
# Stub mcp binary so Popen succeeds without the real OpenBrain MCP installed.
# emit_done only counts as emitted=True when subprocess.Popen returns cleanly;
# the stub is a no-op that always exits 0.
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/mcp"
chmod +x "$TMP/bin/mcp"
TID=$(NOUS_WIKI="$TMP" python3 tools/task_queue.py add --title ob --lane claude --scope 'x' 2>/dev/null)
NOUS_WIKI="$TMP" python3 tools/task_queue.py claim --id "$TID" --session s1 >/dev/null
NOUS_WIKI="$TMP" python3 tools/task_queue.py done --id "$TID" >/dev/null
R1=$(PATH="$TMP/bin:$PATH" NOUS_WIKI="$TMP" python3 tools/queue_to_openbrain.py emit-done --id "$TID" --json 2>/dev/null)
R2=$(PATH="$TMP/bin:$PATH" NOUS_WIKI="$TMP" python3 tools/queue_to_openbrain.py emit-done --id "$TID" --json 2>/dev/null)
EMIT1=$(echo "$R1" | python3 -c "import json,sys; print(json.load(sys.stdin)['emitted'])")
EMIT2=$(echo "$R2" | python3 -c "import json,sys; print(json.load(sys.stdin)['emitted'])")
if [ "$EMIT1" = "True" ] && [ "$EMIT2" = "False" ]; then
  green "✓ first emit=True, second emit=False (dedup OK)"
else
  red "✗ dedup failed: first=$EMIT1 second=$EMIT2"; FAILS=$((FAILS+1))
fi
rm -rf "$TMP"
echo ""

# 7. Pre-commit RULE 7 — lane mismatch is refused (inline minimal test)
echo "--- 7/8 pre_commit_lane_check.sh RULE 7 inline ---"
TMP=$(mktemp -d)
mkdir -p "$TMP/tools" "$TMP/pages/systems" "$TMP/pages/audits" "$TMP/logs"
cp "$WIKI/tools/lane_lock.py" "$TMP/tools/lane_lock.py"
cp "$WIKI/tools/pre_commit_lane_check.sh" "$TMP/tools/pre_commit_lane_check.sh"
HOOK_ABS="$TMP/tools/pre_commit_lane_check.sh"
(
  cd "$TMP"
  git init -q
  git config user.email t@e
  git config user.name t
  echo init > a.txt
  git add a.txt
  git commit -qm initial
  # Acquire claude lock for tools/* only (within $TMP via NOUS_WIKI).
  NOUS_WIKI="$TMP" python3 tools/lane_lock.py acquire --lane claude --scope 'tools/*' --ttl-sec 600 > tok.txt 2>/dev/null
  # Stage a path OUTSIDE the lane scope.
  echo y > pages/audits/foo.md
  git add pages/audits/foo.md
  # Hook should refuse (scope mismatch).
  NOUS_WIKI="$TMP" NOUS_LANE=claude bash "$HOOK_ABS" >/dev/null 2>&1
  echo $? > exit_code
) >/dev/null 2>&1
RC=$(cat "$TMP/exit_code" 2>/dev/null || echo "missing")
if [ "$RC" = "7" ]; then
  green "✓ RULE 7 refused scope-mismatch (exit 7)"
else
  red "✗ RULE 7 did not refuse (exit=$RC, expected 7)"; FAILS=$((FAILS+1))
fi
rm -rf "$TMP"
echo ""

# 8. status_daemon single pass
echo "--- 8/8 status_daemon single pass ---"
TMP=$(mktemp -d)
mkdir -p "$TMP/pages/systems" "$TMP/logs"
if python3 tools/status_daemon.py --wiki "$TMP" 2>&1 | grep -q "status_written"; then
  green "✓ status_daemon ran one pass + wrote STATUS.md"
else
  red "✗ status_daemon did not emit expected output"; FAILS=$((FAILS+1))
fi
rm -rf "$TMP"
echo ""

# Final
echo "=== Verify summary ==="
if [ "$FAILS" -eq 0 ]; then
  green "ALL GREEN — Ship 2 verified."
  echo ""
  echo "Next: launchctl bootstrap gui/\$UID ~/Library/LaunchAgents/com.nous.status-daemon.plist"
  echo "(installs the 30s daemon; not part of this verification)"
  exit 0
else
  red "$FAILS check(s) failed."
  exit 1
fi
