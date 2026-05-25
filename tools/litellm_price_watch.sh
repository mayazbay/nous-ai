#!/bin/bash
# litellm_price_watch.sh — daily Telegram alert as DeepSeek V4 promo expiry approaches
#
# Promo end: 2026-05-31 15:59 UTC (per Dataconomy / DeepSeek docs, captured 2026-04-30)
#   Promo prices: $0.435 in / $0.87 out per 1M tokens
#   Post-promo:   $1.74  in / $3.48  out per 1M tokens (4x)
#
# Alerts: T-7, T-3, T-1 days, and on/after expiry day. Idempotent per-day via state file.
# Cron: launchd com.nous.litellm-price-watch every morning at 09:00 KZT.
#
# v1.0.0 — session s108-air-49979 (2026-04-30)

set -u

EXPIRY="2026-05-31"
EXPIRY_EPOCH=$(date -j -f "%Y-%m-%d" "$EXPIRY" "+%s" 2>/dev/null || date -d "$EXPIRY" "+%s")
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
TODAY=$(date +%Y-%m-%d)

STATE_DIR="$HOME/nous-agaas/state"
mkdir -p "$STATE_DIR"
STATE="$STATE_DIR/litellm-price-watch.last"

# Read last-alert date so we don't spam
LAST=$(cat "$STATE" 2>/dev/null || echo "")
[ "$LAST" = "$TODAY" ] && exit 0   # already alerted today

ALERT=""
if [ "$DAYS_LEFT" -le 0 ]; then
  ALERT="🔴 DeepSeek V4 promo EXPIRED ($EXPIRY). Pricing 4x'd: \$1.74/M in, \$3.48/M out. Re-evaluate direct API vs OpenRouter contract NOW. Worker model default: deepseek-v4-pro."
elif [ "$DAYS_LEFT" -eq 1 ]; then
  ALERT="🟡 DeepSeek V4 promo expires TOMORROW ($EXPIRY). Pricing rises 4x at 15:59 UTC. Last day at \$0.435/\$0.87 per M."
elif [ "$DAYS_LEFT" -eq 3 ]; then
  ALERT="🟡 DeepSeek V4 promo expires in 3 days ($EXPIRY). After: \$1.74/M in, \$3.48/M out. Decide: stay on OpenRouter or move to direct API contract."
elif [ "$DAYS_LEFT" -eq 7 ]; then
  ALERT="🟢 DeepSeek V4 promo expires in 7 days ($EXPIRY). Heads-up; pricing 4x's at expiry. No action yet."
fi

if [ -n "$ALERT" ]; then
  TG_SCRIPT="$HOME/nous-agaas/wiki/tools/tg_send.sh"
  if [ -x "$TG_SCRIPT" ]; then
    bash "$TG_SCRIPT" "$ALERT" >/dev/null 2>&1 && echo "$TODAY" > "$STATE"
  fi
  echo "[$TODAY] alert sent: days_left=$DAYS_LEFT" >> "$STATE_DIR/litellm-price-watch.log"
fi

exit 0
