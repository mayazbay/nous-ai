#!/bin/bash
# morning-brief.sh v2 — 4am Almaty daily. Bash 3.2 compatible (no associative arrays).
# Merged: full factory audit + update availability + staleness + state-change diff.
# State-change alerts: always post a brief, mark CHANGES since yesterday.

set -u
source /Users/madia/nous-agaas/.env 2>/dev/null
source /Users/madia/nous-agaas/litellm/.env 2>/dev/null

LOG=/Users/madia/nous-agaas/logs/morning-brief.log
STATE=/Users/madia/nous-agaas/logs/morning-brief-state.json
echo "=== $(date +%Y-%m-%dT%H:%M:%S) morning brief ===" >> "$LOG"

PREV_STATE="{}"
[ -f "$STATE" ] && PREV_STATE=$(cat "$STATE")

FAILS=0
RESULTS=""
CUR_JSON=""

_set() { CUR_JSON="${CUR_JSON},\"$1\":\"$2\""; }
_get_prev() { echo "$PREV_STATE" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('$1','?'))" 2>/dev/null; }

# 1. OpenClaw container
V=$(/usr/local/bin/docker inspect openclaw --format '{{.State.Health.Status}}' 2>/dev/null || echo missing)
_set openclaw "$V"
if [ "$V" = "healthy" ]; then
  RESULTS="${RESULTS}✅ openclaw: $V\n"
else
  RESULTS="${RESULTS}❌ openclaw: $V\n"; FAILS=$((FAILS+1))
fi

# 2. OpenClaw host-published healthz. TCP-open alone is insufficient: Docker
# can accept the port while a loopback-only container listener returns empty.
OC_HTTP=$(curl --max-time 5 -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18789/healthz 2>/dev/null)
if [ "$OC_HTTP" = "200" ]; then
  _set port18789 healthz_200
  RESULTS="${RESULTS}✅ openclaw healthz 200\n"
else
  _set port18789 "healthz_${OC_HTTP:-000}"
  RESULTS="${RESULTS}❌ openclaw healthz ${OC_HTTP:-000}\n"; FAILS=$((FAILS+1))
fi

# 3. LiteLLM liveness. Use readiness here; /health is a deep provider canary
# that can flap/rate-limit external model endpoints and belongs in explicit
# model audits, not the narrow morning heartbeat.
if [ "$(curl --max-time 5 -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-}" http://localhost:4000/health/readiness 2>/dev/null)" = "200" ]; then
  _set litellm healthy
  RESULTS="${RESULTS}✅ litellm readiness\n"
else
  _set litellm down
  RESULTS="${RESULTS}❌ litellm down\n"; FAILS=$((FAILS+1))
fi

# 4. Telegram-poll launchd
V=$(launchctl list | awk '$3 == "com.nous.telegram-poll" {print $2}')
_set telegram_poll "$V"
if [ "$V" = "0" ]; then
  RESULTS="${RESULTS}✅ telegram-poll (exit=0)\n"
else
  RESULTS="${RESULTS}❌ telegram-poll exit=$V\n"; FAILS=$((FAILS+1))
fi

# 5. Wiki-sync launchd
V=$(launchctl list | awk '$3 == "com.nous.wiki-sync" {print $2}')
_set wiki_sync "$V"
if [ "$V" = "0" ]; then
  RESULTS="${RESULTS}✅ wiki-sync\n"
else
  RESULTS="${RESULTS}❌ wiki-sync exit=$V\n"; FAILS=$((FAILS+1))
fi

# 6. gbrain health
GB_SCORE=$(ssh -o StrictHostKeyChecking=no root@65.108.215.200 'export DATABASE_URL="postgresql://gbrain:gbrain2026@localhost:5432/gbrain" && cd /opt/nous-agaas/gbrain && bin/gbrain doctor --fast --json 2>/dev/null' 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("health_score","?"))' 2>/dev/null)
_set gbrain "$GB_SCORE"
if [ -n "$GB_SCORE" ] && [ "$GB_SCORE" != "?" ]; then
  RESULTS="${RESULTS}✅ gbrain: ${GB_SCORE}/100\n"
else
  RESULTS="${RESULTS}⚠️ gbrain unreachable\n"
fi

# 7. End-to-end factory probe
FACTORY_OUT=$(cd /Users/madia/nous-agaas && perl -e 'alarm shift; exec @ARGV' 300 /opt/homebrew/bin/python3 run_task.py "Reply with exactly: MORNING_OK" 2>&1)
if echo "$FACTORY_OUT" | grep -q "MORNING_OK"; then
  _set factory ok
  RESULTS="${RESULTS}✅ factory probe\n"
else
  _set factory failed
  RESULTS="${RESULTS}❌ factory probe: ${FACTORY_OUT:0:80}\n"; FAILS=$((FAILS+1))
fi

# 8. Task-results today (info, not pass/fail)
TR_COUNT=$(ls /Users/madia/nous-agaas/wiki/pages/task-results/ 2>/dev/null | grep "^$(date +%Y-%m-%d)" | wc -l | tr -d ' ')
_set tasks_today "$TR_COUNT"
RESULTS="${RESULTS}📊 task-results today: $TR_COUNT\n"

# State-change detection (bash 3.2-compatible: use for loop)
CHANGES=""
for k in openclaw port18789 litellm telegram_poll wiki_sync factory; do
  PREV_V=$(_get_prev "$k")
  CUR_V=$(echo "{${CUR_JSON#,}}" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('$k','?'))" 2>/dev/null)
  if [ "$PREV_V" != "?" ] && [ "$PREV_V" != "$CUR_V" ]; then
    CHANGES="${CHANGES}↻ $k: $PREV_V → $CUR_V\n"
  fi
done

# Update availability checks
OC_CUR=$(/usr/local/bin/docker image inspect ghcr.io/openclaw/openclaw:2026.4.14 --format '{{.Id}}' 2>/dev/null | head -c 15)
OC_LATEST=$(/usr/local/bin/docker manifest inspect --verbose ghcr.io/openclaw/openclaw:latest 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("Descriptor",{}).get("digest","?")[:15])' 2>/dev/null)
if [ -n "$OC_LATEST" ] && [ -n "$OC_CUR" ] && [ "$OC_LATEST" != "$OC_CUR" ]; then
  RESULTS="${RESULTS}⬆️  openclaw :latest differs ($OC_LATEST vs $OC_CUR)\n"
fi

GB_UPDATE=$(ssh -o StrictHostKeyChecking=no root@65.108.215.200 'export PATH=/root/.bun/bin:$PATH && /opt/nous-agaas/gbrain/bin/gbrain check-update --json 2>/dev/null' 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("yes" if d.get("hasUpdate") else "no")' 2>/dev/null)
[ "$GB_UPDATE" = "yes" ] && RESULTS="${RESULTS}⬆️  gbrain update available\n"

# Save state
echo "{${CUR_JSON#,},\"last_run\":\"$(date +%Y-%m-%dT%H:%M:%S)\"}" > "$STATE"

echo -e "$RESULTS" >> "$LOG"
[ -n "$CHANGES" ] && echo -e "CHANGES:\n$CHANGES" >> "$LOG"
echo "fails=$FAILS" >> "$LOG"

# Telegram
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  if [ "$FAILS" -gt 0 ]; then
    ICON="🔴"; STATUS="${FAILS} FAILURE(S) — check Air"
  else
    ICON="🟢"; STATUS="Morning heartbeat green"
  fi
  MSG="${ICON} ${STATUS}

${RESULTS}"
  [ -n "$CHANGES" ] && MSG="${MSG}
🔀 Since yesterday:
${CHANGES}"
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=${MSG}" >> "$LOG" 2>&1
fi

echo "=== done ===" >> "$LOG"
