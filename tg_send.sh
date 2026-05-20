#!/bin/bash
# tg_send.sh — send-only Telegram helper using @nousAGaaSbot's token.
#
# Karpathy/Tan/Musk-clean: one bot, one token, any host / any agent can push
# notifications to Madi's phone. No polling (that's telegram_poll.py on Air's
# job exclusively), no HTTP 409 risk, no new bot.
#
# Session 51, 2026-04-20. Codified under CLAUDE.md HARD RULE 1 narrowed scope
# (class-wide ban dropped; token-specific rule applies — this script sends,
# doesn't poll, so no conflict).
#
# Token resolution order:
#   1. $TELEGRAM_BOT_TOKEN env var (if caller pre-set it)
#   2. ~/nous-agaas/.env (if running ON Air, file is local)
#   3. ssh air 'grep TELEGRAM_BOT_TOKEN ~/nous-agaas/.env' (remote hosts)
#
# Usage:
#   bash tools/tg_send.sh "text message"              # send plain text to Madi (default chat_id)
#   bash tools/tg_send.sh --markdown "*bold*"         # enable Markdown parse_mode
#   bash tools/tg_send.sh --chat 123456789 "text"     # send to custom chat_id
#   bash tools/tg_send.sh --chat 123 -m "text"        # both flags (short forms)
#   bash tools/tg_send.sh --chat -100... --reply-to 42 "text"
#
# Exit codes:
#   0 = sent
#   1 = token unavailable
#   2 = missing message argument
#   3 = Telegram API rejected (includes reason on stderr)
#   5 = group personal salutation blocked without addressee proof
#
# Examples:
#   bash tools/tg_send.sh "session 51 closed, 10 artifacts shipped, GOLDEN"
#   echo "build failed at step 5" | xargs -I {} bash tools/tg_send.sh "🔴 {}"

set -u

CHAT_ID="110793056"  # Madi Ayazbay, Telegram user_id (from ~/.claude/channels/telegram/access.json)
PARSE_MODE=""
MESSAGE=""
REPLY_TO=""
ALLOW_NAMED_ADDRESSEE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --chat|-c) CHAT_ID="$2"; shift 2 ;;
    --reply-to) REPLY_TO="$2"; shift 2 ;;
    --allow-named-addressee) ALLOW_NAMED_ADDRESSEE="1"; shift ;;
    --markdown|-m) PARSE_MODE="Markdown"; shift ;;
    --markdownv2) PARSE_MODE="MarkdownV2"; shift ;;
    --html) PARSE_MODE="HTML"; shift ;;
    -h|--help)
      echo "usage: $0 [--chat <id>] [--reply-to <msg_id>] [--allow-named-addressee] [--markdown|--markdownv2|--html] <text>"
      exit 0
      ;;
    *) MESSAGE="$1"; shift ;;
  esac
done

if [ -z "$MESSAGE" ]; then
  echo "❌ missing message argument. Use $0 -h for help." >&2
  exit 2
fi

# --- Group named-addressee guard (command-center AP-41, 2026-05-18) ---
# Manual sends to groups do not carry Telegram sender provenance. Default to
# neutral group wording unless the operator deliberately bypasses this guard.
if [[ "$CHAT_ID" == -* && -z "${TELEGRAM_GROUP_ADDRESSEE_OK:-}" && -z "$ALLOW_NAMED_ADDRESSEE" ]]; then
  if ! python3 - "$MESSAGE" <<'PY'
import re
import sys

message = sys.argv[1].lstrip()
named = re.compile(
    r"^(?:"
    r"Денис|Denis|Асылбек|Асильбек|Assylbek|Asylbek|Мади|Madi|Руслан|Ruslan|"
    r"Назель|Nazel|Роза|Roza|Даниэль|Daniel|Виктор|Viktor|Андрей|Andrey|"
    r"Mady|Ермек|Yermek|Кирилл|Kirill"
    r"),\s+"
)
sys.exit(1 if named.match(message) else 0)
PY
  then
    echo "🔴 tg_send BLOCKED: group message starts with a personal salutation but has no sender proof." >&2
    echo "   Use neutral wording (Коллеги, ...) or deliberately pass --allow-named-addressee / TELEGRAM_GROUP_ADDRESSEE_OK=1 after verifying the addressee." >&2
    exit 5
  fi
fi

# --- Agent-autonomy gate (musk-algorithm AP-4, session 68p 2026-04-23) ---
# Block outbound Telegram messages that contain deference-dressed-as-autonomy
# red-flag phrases (e.g. "optional: X", "whenever ready", "your call", etc).
# These phrases waste Madi's attention-budget (babysitting). Physical gate.
#
# Bypass (operator risk): AUTONOMY_BYPASS=1 bash tools/tg_send.sh "..."
if [ -z "${AUTONOMY_BYPASS:-}" ]; then
  # Locate the detector: prefer same-repo tools/, else vault, else /Users/madia/Documents/.../tools/
  DETECTOR=""
  for candidate in \
    "$(dirname "$0")/test_agent_autonomy.sh" \
    "$HOME/Documents/Projects/Nous AGaaS/Nous/tools/test_agent_autonomy.sh" \
    "$HOME/nous-agaas/wiki/tools/test_agent_autonomy.sh" \
    "/root/nous-agaas/wiki/tools/test_agent_autonomy.sh"; do
    if [ -x "$candidate" ]; then DETECTOR="$candidate"; break; fi
  done
  if [ -n "$DETECTOR" ]; then
    if ! echo "$MESSAGE" | bash "$DETECTOR" --stdin >/dev/null 2>&1; then
      echo "" >&2
      echo "🔴 tg_send BLOCKED: message contains agent-autonomy (AP-4) red-flag phrases." >&2
      echo "   These phrases waste Madi's attention-budget (babysitting mode)." >&2
      echo "   Red flags being caught:" >&2
      echo "$MESSAGE" | bash "$DETECTOR" --stdin 2>&1 | grep -E "^[0-9]+:" | head -5 >&2
      echo "" >&2
      echo "   Decide autonomously and rephrase. Or if TRULY requires Madi input," >&2
      echo "   add one of these hall-pass phrases to the message:" >&2
      echo "     physically-impossible-without-madi / named-author-required /" >&2
      echo "     3 cycles passed with no progress / social-side-effect /" >&2
      echo "     production-write-requires-ack" >&2
      echo "" >&2
      echo "   Emergency bypass: AUTONOMY_BYPASS=1 bash tools/tg_send.sh \"...\"" >&2
      exit 4
    fi
  fi
fi

# --- resolve token ---
TOKEN="${TELEGRAM_BOT_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  if [ -r "$HOME/nous-agaas/.env" ]; then
    TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$HOME/nous-agaas/.env" 2>/dev/null | cut -d= -f2-)
  fi
fi
if [ -z "$TOKEN" ]; then
  TOKEN=$(ssh -o ConnectTimeout=5 -o BatchMode=yes air 'grep ^TELEGRAM_BOT_TOKEN= ~/nous-agaas/.env 2>/dev/null | cut -d= -f2-' 2>/dev/null)
fi
if [ -z "$TOKEN" ]; then
  echo "❌ TELEGRAM_BOT_TOKEN not found in env, ~/nous-agaas/.env, or via ssh air" >&2
  exit 1
fi

# --- send ---
POST_ARGS=(-d "chat_id=${CHAT_ID}" --data-urlencode "text=${MESSAGE}")
[ -n "$PARSE_MODE" ] && POST_ARGS+=(-d "parse_mode=${PARSE_MODE}")
[ -n "$REPLY_TO" ] && POST_ARGS+=(-d "reply_to_message_id=${REPLY_TO}")

RESPONSE=$(curl -s --max-time 10 -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" "${POST_ARGS[@]}" 2>&1)

OK=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print('yes' if d.get('ok') else 'no')
except Exception:
    print('no')
" 2>/dev/null)

if [ "$OK" = "yes" ]; then
  MSG_ID=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d['result']['message_id'])
except Exception:
    print('?')
" 2>/dev/null)
  echo "✅ sent to chat_id=${CHAT_ID} (msg_id=${MSG_ID})"
  exit 0
else
  ERR=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('description', 'unknown'))
except Exception:
    print('bad response')
" 2>/dev/null)
  echo "❌ Telegram API rejected: $ERR" >&2
  exit 3
fi
