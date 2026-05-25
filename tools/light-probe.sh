#!/bin/bash
# light-probe.sh — every 15 min
# Fast mechanical checks. NO LLM. Only alert on state CHANGE (green→red or red→green).
# Location on Air: /Users/madia/nous-agaas/tools/light-probe.sh
#
# FLAP-SUPPRESSION (session 35, 2026-04-16):
#   - Models listed in KNOWN_FLAPPING_MODELS never generate state-change alerts
#     for their own up/down transitions, only for overall unhealthy_count diffs
#     that include MORE than the known-flapping set.
#   - Per-alert-type debounce: a given state-change key will not re-alert inside
#     DEBOUNCE_SECS of its previous alert. Default 4h for model-health, 15min for
#     infrastructure (OpenClaw/LiteLLM/telegram-poll/wiki-sync).
#   - Ground rule: "monitor, don't page" for externally-caused noise. A flap that
#     MEMORY.md explicitly annotates as "monitor, don't act" must not wake Madi.
# See infrastructure SKILL.md AP-23 for the rule codification.

set -u
source /Users/madia/nous-agaas/.env 2>/dev/null
source /Users/madia/nous-agaas/litellm/.env 2>/dev/null

STATE=/Users/madia/nous-agaas/logs/light-probe-state.json
LOG=/Users/madia/nous-agaas/logs/light-probe.log
ALERT_HISTORY=/Users/madia/nous-agaas/logs/light-probe-alert-history.json
MODEL_HEALTH_CACHE=/Users/madia/nous-agaas/logs/light-probe-model-health.json
MODEL_HEALTH_INTERVAL=${MODEL_HEALTH_INTERVAL:-14400}  # 4h; deep /health calls provider canaries
MODEL_HEALTH_SUMMARY=/Users/madia/nous-agaas/tools/litellm_health_summary.py

# Known-flapping models (ZAI GLM-4.5-flash endpoint is degraded/intermittent —
# MEMORY.md session 34: "ZAI endpoint intermittently degraded … Fallback chain
# handles it correctly … monitor, don't act"). Any model in this list has its
# own up/down transitions silenced. The overall count diff still alerts IF
# another model enters/leaves the unhealthy list.
#
# 2026-04-27: OpenRouter DeepSeek V4 shared providers returned transient 429s
# ("temporarily rate-limited upstream"). Treat those shared-pool rate-limit
# flips as monitor-only until BYOK/direct provider routing exists; task-path
# failures are still caught by run_task/model_escalator.
KNOWN_FLAPPING_MODELS="zai/glm-4.5-flash,openrouter/deepseek/deepseek-v4-flash,openrouter/deepseek/deepseek-v4-pro"
MODEL_HEALTH_IGNORED_MODELS="${MODEL_HEALTH_IGNORED_MODELS:-gpt-5.5,gemini/gemini-embedding-001}"

# Debounce (seconds): a same-key alert inside this window is dropped.
DEBOUNCE_MODEL_HEALTH=14400   # 4 hours for model health flaps
DEBOUNCE_INFRA=900            # 15 minutes for infra state (OpenClaw/LiteLLM/etc.)

PREV_STATE="{}"
if [ -f "$STATE" ]; then
  PREV_STATE=$(cat "$STATE")
fi

TS=$(date +%Y-%m-%dT%H:%M:%S)
NOW_EPOCH=$(date +%s)

json_get_from() {
  local doc="$1"
  local key="$2"
  local default="${3:-}"
  printf "%s" "$doc" | python3 -c '
import json
import sys

key = sys.argv[1]
default = sys.argv[2]
try:
    data = json.load(sys.stdin)
    value = data.get(key, default)
    print(default if value is None else value)
except Exception:
    print(default)
' "$key" "$default" 2>/dev/null || printf "%s" "$default"
}

# Checks (cheap, <1s each)
OC=$(/usr/local/bin/docker inspect openclaw --format '{{.State.Health.Status}}' 2>/dev/null || echo missing)
OC_HTTP=$(curl --max-time 5 -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18789/healthz 2>/dev/null)
PORT=$([ "$OC_HTTP" = "200" ] && echo up || echo down)
LLM=$(curl --max-time 5 -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-}" http://localhost:4000/health/readiness 2>/dev/null)
LLM=$([ "$LLM" = "200" ] && echo ok || echo fail)
TG=$(launchctl list | awk '$3 == "com.nous.telegram-poll" {print $2}')
WS=$(launchctl list | awk '$3 == "com.nous.wiki-sync" {print $2}')

CUR=$(python3 -c "import json; print(json.dumps({'openclaw':'$OC','port18789':'$PORT','litellm':'$LLM','telegram_poll':'$TG','wiki_sync':'$WS'}))")
echo "$CUR" > "$STATE"


# === PER-MODEL HEALTH CHECK (LESSON-122, session 32) ===
# /health returns 200 even with dead models, but it is a deep provider canary.
# Do NOT call it every 15 minutes: OpenRouter/ZAI shared providers can rate-limit
# canaries and create their own false flap storm. Cache it; fast liveness uses
# /health/readiness above.
LITELLM_KEY="${LITELLM_MASTER_KEY:-}"
UNHEALTHY_COUNT=$(json_get_from "$PREV_STATE" models_unhealthy "")
HEALTHY_COUNT=$(json_get_from "$PREV_STATE" models_healthy "")
DEAD_MODELS=$(json_get_from "$PREV_STATE" dead_models "")

CACHE_AGE=$(python3 - "$MODEL_HEALTH_CACHE" "$NOW_EPOCH" <<'PYEOF' 2>/dev/null || echo 999999
import json, os, sys
path, now = sys.argv[1], int(sys.argv[2])
try:
    with open(path) as f:
        data = json.load(f)
    print(now - int(data.get("checked_at", 0)))
except Exception:
    print(999999)
PYEOF
)

if [ -f "$MODEL_HEALTH_CACHE" ] && [ "${CACHE_AGE:-999999}" -lt "$MODEL_HEALTH_INTERVAL" ]; then
  CACHED=$(cat "$MODEL_HEALTH_CACHE" 2>/dev/null || echo "{}")
  UNHEALTHY_COUNT=$(json_get_from "$CACHED" models_unhealthy "$UNHEALTHY_COUNT")
  HEALTHY_COUNT=$(json_get_from "$CACHED" models_healthy "$HEALTHY_COUNT")
  DEAD_MODELS=$(json_get_from "$CACHED" dead_models "$DEAD_MODELS")
else
  HEALTH_JSON=$(curl --max-time 45 -s -H "Authorization: Bearer $LITELLM_KEY" http://localhost:4000/health 2>/dev/null)
  if [ -f "$MODEL_HEALTH_SUMMARY" ]; then
    PARSED=$(echo "$HEALTH_JSON" | MODEL_HEALTH_IGNORED_MODELS="$MODEL_HEALTH_IGNORED_MODELS" python3 "$MODEL_HEALTH_SUMMARY" 2>/dev/null || echo "")
  else
    PARSED=$(echo "$HEALTH_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print('%s\t%s\t%s' % (d.get('healthy_count',''), d.get('unhealthy_count',''), ','.join([(e.get('model') or 'unknown-model') for e in d.get('unhealthy_endpoints',[])]) or 'none'))" 2>/dev/null || echo "")
  fi
  if [ -n "$PARSED" ]; then
    HEALTHY_COUNT=$(printf "%s" "$PARSED" | awk -F '\t' '{print $1}')
    UNHEALTHY_COUNT=$(printf "%s" "$PARSED" | awk -F '\t' '{print $2}')
    DEAD_MODELS=$(printf "%s" "$PARSED" | awk -F '\t' '{print $3}')
    python3 - "$MODEL_HEALTH_CACHE" "$NOW_EPOCH" "$HEALTHY_COUNT" "$UNHEALTHY_COUNT" "$DEAD_MODELS" <<'PYEOF' 2>/dev/null || true
import json, sys
path, checked_at, healthy, unhealthy, dead = sys.argv[1:]
with open(path, "w") as f:
    json.dump({
        "checked_at": int(checked_at),
        "models_healthy": healthy,
        "models_unhealthy": unhealthy,
        "dead_models": dead,
    }, f)
PYEOF
  else
    echo "[$TS] model-health probe broken; using previous state" >> "$LOG"
  fi
fi

if [ -n "$HEALTHY_COUNT" ] && [ -n "$UNHEALTHY_COUNT" ] && [ -n "$DEAD_MODELS" ]; then
  CUR=$(echo "$CUR" | python3 -c "import json,sys; d=json.load(sys.stdin); d['models_healthy']='$HEALTHY_COUNT'; d['models_unhealthy']='$UNHEALTHY_COUNT'; d['dead_models']='$DEAD_MODELS'; print(json.dumps(d))")
else
  echo "[$TS] model-health probe broken; no previous/cache baseline, leaving model fields absent" >> "$LOG"
fi
echo "$CUR" > "$STATE"

# Compare to previous. Only alert on transition.
CHANGES=""
SUPPRESSED_CHANGES=""

# Load alert history (key -> last_alert_epoch)
HIST="{}"
if [ -f "$ALERT_HISTORY" ]; then
  HIST=$(cat "$ALERT_HISTORY")
fi

# Helper: check if a dead_models transition is ONLY about known-flapping models.
is_only_known_flapping() {
  local prev_list="$1" cur_list="$2"
  # Symmetric diff = models entering or leaving unhealthy
  python3 - <<PYEOF
prev = set([m.strip() for m in "$prev_list".split(",") if m.strip() and m.strip() != "none"])
cur  = set([m.strip() for m in "$cur_list".split(",")  if m.strip() and m.strip() != "none"])
known = set([m.strip() for m in "$KNOWN_FLAPPING_MODELS".split(",") if m.strip()])
diff = prev.symmetric_difference(cur)
# True iff every model that changed state is in the known-flapping list
print("yes" if diff and diff.issubset(known) else "no")
PYEOF
}

# Helper: check debounce — returns "alert" or "drop"
check_debounce() {
  local key="$1" window="$2"
  local last
  last=$(echo "$HIST" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$key',0))" 2>/dev/null || echo 0)
  [ -z "$last" ] && last=0
  local age=$(( NOW_EPOCH - last ))
  if [ "$age" -lt "$window" ]; then
    echo drop
  else
    echo alert
  fi
}

for k in openclaw port18789 litellm telegram_poll wiki_sync models_healthy models_unhealthy dead_models; do
  PREV_V=$(json_get_from "$PREV_STATE" "$k" "__missing__")
  CUR_V=$(json_get_from "$CUR" "$k" "__missing__")
  if [ "$PREV_V" != "__missing__" ] && [ "$CUR_V" != "__missing__" ] && [ "$PREV_V" != "$CUR_V" ]; then
    line="• $k: $PREV_V → $CUR_V"

    # Suppress known-flapping model transitions.
    # If ONLY glm-4.5-flash (or other listed models) moves in/out of dead_models,
    # and the counts only shift by its contribution, suppress all three related keys.
    suppress=no
    case "$k" in
      dead_models)
        only_flap=$(is_only_known_flapping "$PREV_V" "$CUR_V")
        [ "$only_flap" = "yes" ] && suppress=yes
        ;;
      models_healthy|models_unhealthy)
        # If corresponding dead_models delta is only-flapping, drop the count delta too.
        PREV_DM=$(json_get_from "$PREV_STATE" dead_models "__missing__")
        CUR_DM=$(json_get_from "$CUR" dead_models "__missing__")
        if [ "$PREV_DM" != "__missing__" ] && [ "$CUR_DM" != "__missing__" ] && [ "$PREV_DM" != "$CUR_DM" ]; then
          only_flap=$(is_only_known_flapping "$PREV_DM" "$CUR_DM")
          [ "$only_flap" = "yes" ] && suppress=yes
        fi
        ;;
    esac

    # Per-key debounce
    case "$k" in
      dead_models|models_healthy|models_unhealthy)
        dec=$(check_debounce "$k|$CUR_V" "$DEBOUNCE_MODEL_HEALTH")
        ;;
      *)
        dec=$(check_debounce "$k|$CUR_V" "$DEBOUNCE_INFRA")
        ;;
    esac
    [ "$dec" = "drop" ] && suppress=yes

    if [ "$suppress" = "yes" ]; then
      SUPPRESSED_CHANGES="${SUPPRESSED_CHANGES}${line} [suppressed]
"
    else
      CHANGES="${CHANGES}${line}
"
    fi
  fi
done

# Log suppressed transitions quietly (for auditability)
if [ -n "$SUPPRESSED_CHANGES" ]; then
  echo "[$TS] SUPPRESSED (known-flap or debounce):" >> "$LOG"
  echo "$SUPPRESSED_CHANGES" >> "$LOG"
fi

if [ -n "$CHANGES" ]; then
  echo "[$TS] STATE CHANGE (alertable):" >> "$LOG"
  echo "$CHANGES" >> "$LOG"

  # Update alert history for every alertable key
  HIST=$(echo "$CHANGES" | python3 -c "
import json, sys, os
hist = json.loads(open('$ALERT_HISTORY').read()) if os.path.exists('$ALERT_HISTORY') else {}
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('• '):
        continue
    # format: • key: prev → cur
    try:
        mid = line[2:].split(':', 1)
        key = mid[0].strip()
        val_part = mid[1].strip()
        cur_v = val_part.split('→')[-1].strip()
        hist[f'{key}|{cur_v}'] = $NOW_EPOCH
    except Exception:
        pass
print(json.dumps(hist))
")
  echo "$HIST" > "$ALERT_HISTORY"

  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    SUPERVISOR=/Users/madia/nous-agaas/wiki/tools/factory_self_heal.py
    if [ -f "$SUPERVISOR" ]; then
      printf "%s" "$CHANGES" |
        python3 "$SUPERVISOR" --stdin-light-changes --source light-probe --notify \
          >> "$LOG" 2>&1 || echo "[$TS] factory_self_heal failed for state change" >> "$LOG"
    else
      if echo "$CHANGES" | grep -qE "→ (down|missing|fail|unhealthy|[1-9])"; then
        ICON="🔴"
      else
        ICON="🟢"
      fi
      MSG="${ICON} State change at ${TS}

${CHANGES}"
      if [ -x /Users/madia/nous-agaas/tools/tg_send.sh ]; then
        bash /Users/madia/nous-agaas/tools/tg_send.sh "$MSG" >> "$LOG" 2>&1 || echo "[$TS] tg_send failed for state change" >> "$LOG"
      else
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
          -d "chat_id=${TELEGRAM_CHAT_ID}" \
          -d "text=${MSG}" > /dev/null 2>&1
      fi
    fi
  fi
else
  # quiet — just log a heartbeat line
  echo "[$TS] ok | oc=$OC port=$PORT llm=$LLM tg=$TG ws=$WS" >> "$LOG"
fi
