#!/bin/bash
# morning-update-apply.sh — 05:07 Almaty daily
# Auto-applies SAFE updates. Notifies for risky ones. Always reports via Telegram.
#
# SAFE auto-apply: gbrain patches (same minor), Claude CLI npm updates, skillpack rsync
# RISKY notify-only: gbrain minor/major, OpenClaw image bumps, GStack/Codex/LiteLLM freshness anomalies
# Location: /Users/madia/nous-agaas/tools/morning-update-apply.sh

set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"
source /Users/madia/nous-agaas/.env 2>/dev/null

LOG=/Users/madia/nous-agaas/logs/morning-update-apply.log
STATE_DIR=/Users/madia/nous-agaas/state
OC_IMAGE_STATE="$STATE_DIR/morning-update-openclaw-image.last"
mkdir -p "$STATE_DIR"
echo "=== $(date +%Y-%m-%dT%H:%M:%S) morning update apply ===" >> "$LOG"

REPORT=""
APPLIED=""
NOTIFIED=""

_docker_manifest_digest() {
  IMAGE_REF="$1"
  /usr/local/bin/docker manifest inspect --verbose "$IMAGE_REF" 2>/dev/null | python3 -c '
import json
import sys

raw = sys.stdin.read().strip()
if not raw:
    sys.exit(0)

data = json.loads(raw)
items = data if isinstance(data, list) else [data]

def item_digest(item):
    desc = item.get("Descriptor", {}) if isinstance(item, dict) else {}
    digest = desc.get("digest")
    if digest:
        return digest
    ref = item.get("Ref", "") if isinstance(item, dict) else ""
    if "@" in ref:
        return ref.rsplit("@", 1)[1]
    return ""

for item in items:
    desc = item.get("Descriptor", {}) if isinstance(item, dict) else {}
    platform = desc.get("platform", {}) or item.get("Platform", {})
    if platform.get("os") == "linux" and platform.get("architecture") == "amd64":
        digest = item_digest(item)
        if digest:
            print(digest)
            sys.exit(0)

for item in items:
    digest = item_digest(item)
    if digest:
        print(digest)
        sys.exit(0)
'
}

# ── 1. gbrain check ──────────────────────────────────────────────────────────
GB_JSON=$(ssh -o StrictHostKeyChecking=no root@65.108.215.200 'export PATH=/root/.bun/bin:$PATH && /opt/nous-agaas/gbrain/bin/gbrain check-update --json 2>/dev/null' 2>/dev/null)
GB_HAS=$(echo "$GB_JSON" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("yes" if d.get("hasUpdate") else "no")' 2>/dev/null)
if [ "$GB_HAS" = "yes" ]; then
  GB_CUR=$(echo "$GB_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("currentVersion","?"))' 2>/dev/null)
  GB_NEW=$(echo "$GB_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("latestVersion","?"))' 2>/dev/null)
  echo "  gbrain: $GB_CUR → $GB_NEW available" >> "$LOG"
  # Auto-apply if patch (matching first 2 segments)
  CUR_MM=$(echo "$GB_CUR" | cut -d. -f1-2)
  NEW_MM=$(echo "$GB_NEW" | cut -d. -f1-2)
  if [ "$CUR_MM" = "$NEW_MM" ]; then
    echo "  PATCH detected, auto-applying" >> "$LOG"
    UPDATE_OUT=$(ssh -o StrictHostKeyChecking=no root@65.108.215.200 'export PATH=/root/.bun/bin:$PATH && cd /opt/nous-agaas/gbrain && PGPASSWORD=gbrain2026 pg_dump -h localhost -U gbrain -d gbrain > /root/gbrain-backup-$(date +%Y%m%d-%H%M).sql && git pull origin master 2>&1 | tail -3 && bun install 2>&1 | tail -3 && bun run build 2>&1 | tail -3' 2>&1)
    echo "$UPDATE_OUT" >> "$LOG"
    APPLIED="${APPLIED}- gbrain: $GB_CUR → $GB_NEW (patch auto-applied)\n"
    # Re-rsync skillpack to Air in case skills changed
    rsync -avz --delete root@65.108.215.200:/opt/nous-agaas/gbrain/skills/ /Users/madia/nous-agaas/skills/_gbrain/ >> "$LOG" 2>&1
  else
    NOTIFIED="${NOTIFIED}- gbrain: $GB_CUR → $GB_NEW (minor/major — RUN MANUALLY: ssh vps 'cd /opt/nous-agaas/gbrain && git pull && bun install && bun run build && ./bin/gbrain init --url postgresql://gbrain:gbrain2026@localhost:5432/gbrain')\n"
  fi
fi

# ── 2. Claude Code CLI ──────────────────────────────────────────────────────
CLAUDE_CUR=$($HOME/.npm-global/bin/claude --version 2>/dev/null | head -1 | awk '{print $1}')
NPM_LATEST=$(npm view @anthropic-ai/claude-code version 2>/dev/null)
echo "  claude: $CLAUDE_CUR → $NPM_LATEST" >> "$LOG"
if [ -n "$CLAUDE_CUR" ] && [ -n "$NPM_LATEST" ] && [ "$CLAUDE_CUR" != "$NPM_LATEST" ]; then
  # Auto-apply (npm update is generally safe)
  UPDATE_OUT=$(npm install -g @anthropic-ai/claude-code@latest 2>&1 | tail -3)
  echo "$UPDATE_OUT" >> "$LOG"
  NEW_VER=$($HOME/.npm-global/bin/claude --version 2>/dev/null | head -1 | awk '{print $1}')
  if [ "$NEW_VER" = "$NPM_LATEST" ]; then
    APPLIED="${APPLIED}- Claude Code CLI: $CLAUDE_CUR → $NPM_LATEST (auto-applied)\n"
  else
    NOTIFIED="${NOTIFIED}- Claude Code CLI: install attempted, version still $NEW_VER\n"
  fi
fi
CLAUDE_PATH_BIN=$(command -v claude 2>/dev/null || true)
if [ -n "$CLAUDE_PATH_BIN" ] && [ "$CLAUDE_PATH_BIN" != "$HOME/.npm-global/bin/claude" ]; then
  CLAUDE_PATH_VER=$("$CLAUDE_PATH_BIN" --version 2>/dev/null | head -1 | awk '{print $1}')
  CLAUDE_USER_VER=$($HOME/.npm-global/bin/claude --version 2>/dev/null | head -1 | awk '{print $1}')
  if [ -n "$CLAUDE_PATH_VER" ] && [ -n "$CLAUDE_USER_VER" ] && [ "$CLAUDE_PATH_VER" != "$CLAUDE_USER_VER" ]; then
    NOTIFIED="${NOTIFIED}- Claude Code CLI: PATH resolves stale ${CLAUDE_PATH_BIN} (${CLAUDE_PATH_VER}); production /code uses $HOME/.npm-global/bin/claude (${CLAUDE_USER_VER}). Fix shell PATH or symlink before trusting plain 'claude'.\n"
  fi
fi

# ── 3. OpenClaw image ───────────────────────────────────────────────────────
OC_CUR_TAG=$(/usr/local/bin/docker ps --filter name=openclaw --format '{{.Image}}' 2>/dev/null | head -1)
# Don't auto-pull — major changes can break config. Inspect registry manifests only.
if [ -n "$OC_CUR_TAG" ]; then
  CUR_DIGEST=$(_docker_manifest_digest "$OC_CUR_TAG")
  LATEST_DIGEST=$(_docker_manifest_digest ghcr.io/openclaw/openclaw:latest)
  if [ -n "$CUR_DIGEST" ] && [ -n "$LATEST_DIGEST" ] && [ "$CUR_DIGEST" != "$LATEST_DIGEST" ]; then
    OC_SIG="${OC_CUR_TAG}|${CUR_DIGEST}|${LATEST_DIGEST}"
    OC_LAST=$(cat "$OC_IMAGE_STATE" 2>/dev/null || true)
    if [ "$OC_SIG" != "$OC_LAST" ]; then
      NOTIFIED="${NOTIFIED}- OpenClaw image: :latest differs from current (RISKY auto-apply, manual: see skills/infrastructure/SKILL.md AP-61; review AP-4 before any container config change)\n"
      printf "%s\n" "$OC_SIG" > "$OC_IMAGE_STATE"
    else
      echo "  openclaw: latest differs from current, already notified for this digest pair" >> "$LOG"
    fi
  elif [ -n "$CUR_DIGEST" ] && [ -n "$LATEST_DIGEST" ]; then
    rm -f "$OC_IMAGE_STATE" 2>/dev/null || true
  else
    echo "  openclaw: unable to compare registry manifest digests (current=$CUR_DIGEST latest=$LATEST_DIGEST)" >> "$LOG"
  fi
fi

# ── 4. GStack skillpack freshness ───────────────────────────────────────────
GSTACK_CHECK=""
for GSTACK_BIN_DIR in \
  "$HOME/.agents/skills/gstack/bin" \
  "$HOME/.Codex/skills/gstack/bin" \
  "$HOME/.codex/skills/gstack/bin" \
  "$HOME/.claude/skills/gstack/bin"
do
  if [ -x "$GSTACK_BIN_DIR/gstack-update-check" ]; then
    GSTACK_CHECK=$("$GSTACK_BIN_DIR/gstack-update-check" 2>/dev/null || true)
    [ -n "$GSTACK_CHECK" ] && echo "  gstack: checker=$GSTACK_BIN_DIR/gstack-update-check" >> "$LOG"
    break
  fi
done
if [ -n "$GSTACK_CHECK" ]; then
  echo "  gstack: update signal: $GSTACK_CHECK" >> "$LOG"
  NOTIFIED="${NOTIFIED}- GStack skills: update signal present — run the gstack upgrade workflow manually, then rerun skill/version gates. Signal: ${GSTACK_CHECK}\n"
else
  echo "  gstack: no update signal (or checker unavailable)" >> "$LOG"
fi

# ── 5. Codex CLI/App freshness ──────────────────────────────────────────────
CODEX_BIN="${CODEX_CMD:-}"
if [ -z "$CODEX_BIN" ]; then
  for candidate in \
    "/Applications/Codex.app/Contents/Resources/codex" \
    "/opt/homebrew/bin/codex" \
    "/usr/local/bin/codex" \
    "$HOME/.npm-global/bin/codex"
  do
    if [ -x "$candidate" ]; then
      CODEX_BIN="$candidate"
      break
    fi
  done
fi
if [ -n "$CODEX_BIN" ] && [ -x "$CODEX_BIN" ]; then
  CODEX_VER=$("$CODEX_BIN" --version 2>&1 | head -1)
  echo "  codex: ${CODEX_VER:-version command returned empty} ($CODEX_BIN)" >> "$LOG"
else
  NOTIFIED="${NOTIFIED}- Codex CLI: no executable found in the known Air paths; /codex Telegram route may be degraded.\n"
fi

# ── 6. LiteLLM readiness/version ────────────────────────────────────────────
LITELLM_HEALTH=$(curl -fsS --max-time 5 http://127.0.0.1:4000/health/readiness 2>/dev/null || true)
if echo "$LITELLM_HEALTH" | grep -qi '"status"[[:space:]]*:[[:space:]]*"healthy"'; then
  LITELLM_VER=$(echo "$LITELLM_HEALTH" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("litellm_version","?"))' 2>/dev/null)
  echo "  litellm: healthy version=${LITELLM_VER:-?}" >> "$LOG"
else
  NOTIFIED="${NOTIFIED}- LiteLLM: readiness check failed or unhealthy; inspect com.nous.litellm before changing model routes.\n"
fi

# ── Telegram report ─────────────────────────────────────────────────────────
if [ -n "$APPLIED" ] || [ -n "$NOTIFIED" ]; then
  MSG="🌅 Morning update check (05:07 Almaty)"
  if [ -n "$APPLIED" ]; then
    MSG="${MSG}

✅ Auto-applied:
${APPLIED}"
  fi
  if [ -n "$NOTIFIED" ]; then
    MSG="${MSG}

⚠️ Manual review needed:
${NOTIFIED}"
  fi
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      -d "text=${MSG}" >> "$LOG" 2>&1
  fi
else
  echo "  No updates available — silent (no Telegram)" >> "$LOG"
fi

echo "=== done ===" >> "$LOG"
