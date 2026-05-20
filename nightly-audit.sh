#!/bin/bash
# nightly-audit.sh — 4am Almaty daily
# Full factory-stack health check. Reports PASS/FAIL for each subsystem.
# Location on Air: /Users/madia/nous-agaas/tools/nightly-audit.sh

set -u
cd /Users/madia/nous-agaas
source /Users/madia/nous-agaas/.env 2>/dev/null
source /Users/madia/nous-agaas/litellm/.env 2>/dev/null

LOG=/Users/madia/nous-agaas/logs/nightly-audit.log
echo "=== $(date +%Y-%m-%dT%H:%M:%S) 4am audit ===" >> "$LOG"

FAILS=0
RESULTS=""

# 1. OpenClaw container healthy
OC_STATUS=$(/usr/local/bin/docker inspect openclaw --format '{{.State.Health.Status}}' 2>/dev/null || echo "missing")
if [ "$OC_STATUS" = "healthy" ]; then
  RESULTS="${RESULTS}✅ openclaw container: $OC_STATUS\n"
else
  RESULTS="${RESULTS}❌ openclaw container: $OC_STATUS\n"; FAILS=$((FAILS+1))
fi

# 2. OpenClaw port open (WebSocket, not HTTP — use nc -z to just check TCP)
if nc -z localhost 18789 2>/dev/null; then
  RESULTS="${RESULTS}✅ openclaw port 18789 listening\n"
else
  RESULTS="${RESULTS}❌ openclaw port 18789 not listening\n"; FAILS=$((FAILS+1))
fi

# 3. LiteLLM liveness. Use readiness here; /health is a deep provider canary
# and should not drive the narrow scheduled heartbeat.
LLM_CODE=$(curl --max-time 5 -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-}" http://localhost:4000/health/readiness 2>/dev/null)
if [ "$LLM_CODE" = "200" ]; then
  RESULTS="${RESULTS}✅ litellm readiness\n"
else
  RESULTS="${RESULTS}❌ litellm not responding\n"; FAILS=$((FAILS+1))
fi

# 4. Telegram poll launchd
TG_PID=$(launchctl list | awk '$3 == "com.nous.telegram-poll" {print $1}')
TG_EXIT=$(launchctl list | awk '$3 == "com.nous.telegram-poll" {print $2}')
if [ "$TG_EXIT" = "0" ]; then
  RESULTS="${RESULTS}✅ telegram-poll launchd (exit=$TG_EXIT, pid=$TG_PID)\n"
else
  RESULTS="${RESULTS}❌ telegram-poll launchd exit=$TG_EXIT\n"; FAILS=$((FAILS+1))
fi

# 5. Wiki sync launchd
WS_EXIT=$(launchctl list | awk '$3 == "com.nous.wiki-sync" {print $2}')
if [ "$WS_EXIT" = "0" ]; then
  RESULTS="${RESULTS}✅ wiki-sync launchd\n"
else
  RESULTS="${RESULTS}❌ wiki-sync exit=$WS_EXIT\n"; FAILS=$((FAILS+1))
fi

# 6. gbrain health (via SSH to VPS — also sets DATABASE_URL so DB check works)
GB_SCORE=$(ssh -o StrictHostKeyChecking=no root@65.108.215.200 'export DATABASE_URL="postgresql://gbrain:gbrain2026@localhost:5432/gbrain" && cd /opt/nous-agaas/gbrain && bin/gbrain doctor --fast --json 2>/dev/null' 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("health_score", d.get("healthScore","?")))' 2>/dev/null)
if [ -n "$GB_SCORE" ] && [ "$GB_SCORE" != "?" ]; then
  RESULTS="${RESULTS}✅ gbrain health: ${GB_SCORE}/100\n"
else
  RESULTS="${RESULTS}⚠️ gbrain doctor unreachable\n"
fi

# 7. End-to-end factory probe (trivial task). macOS has no `timeout` cmd;
#    use perl -e alarm for a 60s cap.
FACTORY_OUT=$(cd /Users/madia/nous-agaas && perl -e 'alarm shift; exec @ARGV' 300 python3 run_task.py "Reply with exactly: NIGHTLY_AUDIT_OK" 2>&1)
if echo "$FACTORY_OUT" | grep -q "NIGHTLY_AUDIT_OK"; then
  RESULTS="${RESULTS}✅ factory end-to-end probe\n"
else
  RESULTS="${RESULTS}❌ factory probe failed: ${FACTORY_OUT:0:100}\n"; FAILS=$((FAILS+1))
fi

# Report
echo -e "$RESULTS" >> "$LOG"
echo "fails=$FAILS" >> "$LOG"

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  if [ "$FAILS" = "0" ]; then
    ICON="🟢"; HEADER="Heartbeat green"
  else
    ICON="🔴"; HEADER="${FAILS} FAILURE(S) — check Air"
  fi
  MSG="${ICON} 4am audit — ${HEADER}

${RESULTS}
Log: /Users/madia/nous-agaas/logs/nightly-audit.log"
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=${MSG}" >> "$LOG" 2>&1
fi

echo "=== done ===" >> "$LOG"
