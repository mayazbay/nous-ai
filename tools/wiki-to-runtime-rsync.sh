#!/bin/bash
# wiki-to-runtime-rsync.sh — auto-sync wiki skills + tools to Air runtime on change
# Triggered by launchd WatchPath on ~/nous-agaas/wiki/pages/skills/ AND ~/nous-agaas/wiki/tools/
# NEVER uses --delete (LESSON from session 24 Wave 3 — wiped _gbrain/)
# Main skill pass excludes _gbrain/ + extracted/; _gbrain/ syncs additively after.
# Uses flock for concurrency.
# Part of GOD_PROMPT v1.0 (spec: pages/specs/god-prompt-v1-design-2026-04-15.md)
# Session 47 M5: extended to cover tools/ (closes session-46 Phase K rsync-scope gap).
set -euo pipefail

WIKI_SKILLS_DIR="${WIKI_SKILLS_DIR:-$HOME/nous-agaas/wiki/pages/skills}"
RUNTIME_SKILLS_DIR="${RUNTIME_SKILLS_DIR:-$HOME/nous-agaas/skills}"
WIKI_SYSTEMS_DIR="${WIKI_SYSTEMS_DIR:-$HOME/nous-agaas/wiki/pages/systems}"
WIKI_TOOLS_DIR="${WIKI_TOOLS_DIR:-$HOME/nous-agaas/wiki/tools}"
RUNTIME_TOOLS_DIR="${RUNTIME_TOOLS_DIR:-$HOME/nous-agaas/tools}"
WIKI_TENANTS_DIR="${WIKI_TENANTS_DIR:-$HOME/nous-agaas/wiki/pages/tenants}"
WIKI_TENANT_RUNTIME_DIR="${WIKI_TENANT_RUNTIME_DIR:-$HOME/nous-agaas/wiki/tenants}"
RUNTIME_TENANTS_DIR="${RUNTIME_TENANTS_DIR:-$HOME/nous-agaas/tenants}"
LOCAL_BIN_DIR="${LOCAL_BIN_DIR:-$HOME/.local/bin}"
DOCKER_BIN="${DOCKER_BIN:-}"
if [ -z "$DOCKER_BIN" ]; then
  DOCKER_BIN=$(command -v docker 2>/dev/null || true)
fi
OPENCLAW_CONTAINER="${OPENCLAW_CONTAINER:-openclaw}"
LOCK_FILE="${LOCK_FILE:-/tmp/wiki-rsync.lock}"
LOG_DIR="${LOG_DIR:-$HOME/nous-agaas/wiki/pages/progress}"
TS=$(date +%Y-%m-%d-%H-%M-%S)

# Acquire lock (non-blocking — skip if another rsync is running)
# Uses shlock (macOS/BSD portable) or flock (Linux) if available
if command -v flock >/dev/null 2>&1; then
  exec 200>"$LOCK_FILE"
  flock -n 200 || { echo "[$TS] SKIP: another rsync holds the lock"; exit 0; }
elif command -v shlock >/dev/null 2>&1; then
  shlock -p $$ -f "$LOCK_FILE" || { echo "[$TS] SKIP: another rsync holds the lock"; exit 0; }
  trap "rm -f '$LOCK_FILE'" EXIT
else
  # Minimal mkdir-based lock (atomic on POSIX)
  if ! mkdir "${LOCK_FILE}.d" 2>/dev/null; then
    echo "[$TS] SKIP: another rsync holds the lock"; exit 0
  fi
  trap "rmdir '${LOCK_FILE}.d'" EXIT
fi

# Rsync — NEVER pass --delete (LESSON from session 24 Wave 3 — wiped _gbrain/).
# Default rsync behaviour is no-delete. Do NOT add --delete.
# Exclude _gbrain from this first pass; sync it additively below.
rsync -av \
  --exclude='_gbrain/' \
  --exclude='extracted/' \
  "$WIKI_SKILLS_DIR/" "$RUNTIME_SKILLS_DIR/" \
  > "/tmp/wiki-rsync-$TS.log" 2>&1

# Check for changed files (rsync itemize format — grep -c exits 1 on no matches, hence || true)
CHANGED=$(grep -c '^>f' "/tmp/wiki-rsync-$TS.log" 2>/dev/null || true)
CHANGED=${CHANGED:-0}

if [ "$CHANGED" -gt 0 ]; then
  mkdir -p "$LOG_DIR"
  {
    echo "## $(date '+%Y-%m-%d %H:%M:%S') wiki→runtime rsync"
    echo ""
    echo "Changed files: $CHANGED"
    echo '```'
    grep '^>f' "/tmp/wiki-rsync-$TS.log" | head -50
    echo '```'
    echo ""
  } >> "$LOG_DIR/rsync-log-$(date +%Y-%m-%d).md"
fi

echo "[$TS] OK: rsync complete ($CHANGED files changed)"

# Session 32 fix: also sync _gbrain/ from wiki to runtime (additive, no --delete)
# _gbrain/ was excluded because session 24 --delete wiped it.
# Now that _gbrain/ is tracked in wiki git, we can sync it safely WITHOUT --delete.
rsync -av \
  "$WIKI_SKILLS_DIR/_gbrain/" "$RUNTIME_SKILLS_DIR/_gbrain/" \
  >> "/tmp/wiki-rsync-$TS.log" 2>&1

echo "[$TS] OK: _gbrain sync complete"

# ─────────────────────────────────────────────────────────────────
# Session 47 M5: extend rsync to tools/ (closes Phase K rsync-scope gap).
# Vault tools/ → Air ~/nous-agaas/tools/ (majority of launchd scripts)
# Exclusions: test harnesses, hook-canonical copies, archive/backup artifacts.
# NEVER --delete.
# ─────────────────────────────────────────────────────────────────
if [ -d "$WIKI_TOOLS_DIR" ]; then
  mkdir -p "$RUNTIME_TOOLS_DIR"
  # Session 68p+ exclusion narrowed: exclude only *_self.sh (self-test harnesses,
  # dev-only) and *_self.py; production detectors (test_agent_autonomy.sh,
  # test_musk_step_2.sh, test_skill_bump_requires_gbrain_timeline.sh, etc.) MUST
  # reach runtime because they are called by hooks and tg_send.sh.
  rsync -av \
    --exclude='test_*_self.sh' \
    --exclude='test_*_self.py' \
    --exclude='pre-commit-hook-tan-pattern.sh' \
    --exclude='pre-push-hook-tan-pattern.sh' \
    --exclude='*.bak-*' \
    --exclude='*.v1-archived-*' \
    --exclude='*.pre-m4-*' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    "$WIKI_TOOLS_DIR/" "$RUNTIME_TOOLS_DIR/" \
    >> "/tmp/wiki-rsync-$TS.log" 2>&1
  echo "[$TS] OK: tools/ sync complete"

  # Special per-file rsync for scripts whose Air runtime lives in ~/.local/bin/
  # (capture-courier + obsidian-sync — historical plist paths from pre-nous-agaas/ era).
  # Keep vault→~/.local/bin/ 1:1 so plist ProgramArguments don't need to change.
  for f in capture_to_nous_pending.sh nous-obsidian-sync.sh; do
    if [ -f "$WIKI_TOOLS_DIR/$f" ]; then
      rsync -av "$WIKI_TOOLS_DIR/$f" "$LOCAL_BIN_DIR/$f" \
        >> "/tmp/wiki-rsync-$TS.log" 2>&1
    fi
  done
  echo "[$TS] OK: ~/.local/bin/ sync complete"
fi

# ─────────────────────────────────────────────────────────────────
# Session 77: sync agent identity substrate into OpenClaw runtime.
# SOUL/USER/AGENTS are not passive docs: OpenClaw reads them from its workspace.
# Keep the vault pages/systems copy canonical, mirror it into both the active
# workspace and the /opt/nous-agaas/agents substrate path. Do not overwrite the
# grok-ceo Tier-1 SOUL/AGENTS persona here; only share USER.md with it.
# NEVER --delete.
# ─────────────────────────────────────────────────────────────────
if [ -d "$WIKI_SYSTEMS_DIR" ]; then
  if [ -n "$DOCKER_BIN" ] && [ -x "$DOCKER_BIN" ] && \
     "$DOCKER_BIN" inspect "$OPENCLAW_CONTAINER" >/dev/null 2>&1 && \
     [ "$("$DOCKER_BIN" inspect -f '{{.State.Running}}' "$OPENCLAW_CONTAINER" 2>/dev/null || echo false)" = "true" ]; then
    SOUL_SRC="$WIKI_SYSTEMS_DIR/nous-agent-soul.md"
    USER_SRC="$WIKI_SYSTEMS_DIR/nous-agent-user.md"
    AGENTS_SRC="$WIKI_SYSTEMS_DIR/nous-agent-procedures.md"
    GROK_CEO_SOUL_SRC="$WIKI_SYSTEMS_DIR/grok-ceo-soul.md"
    GROK_CEO_IDENTITY_SRC="$WIKI_SYSTEMS_DIR/grok-ceo-identity.md"

    if [ -f "$SOUL_SRC" ] && [ -f "$USER_SRC" ] && [ -f "$AGENTS_SRC" ]; then
      # /opt/nous-agaas/ is root:755 inside container with no bind mount for
      # agents/, so node user can't mkdir. Create it as root once, chown to node.
      # /home/node/* paths are node-owned, so node can mkdir those directly.
      "$DOCKER_BIN" exec -u root "$OPENCLAW_CONTAINER" sh -lc \
        'mkdir -p /opt/nous-agaas/agents && chown node:node /opt/nous-agaas/agents'
      "$DOCKER_BIN" exec "$OPENCLAW_CONTAINER" sh -lc \
        'mkdir -p /home/node/.openclaw/workspace /home/node/.openclaw/workspaces/grok-ceo'

      "$DOCKER_BIN" cp "$SOUL_SRC" "$OPENCLAW_CONTAINER:/home/node/.openclaw/workspace/SOUL.md"
      "$DOCKER_BIN" cp "$USER_SRC" "$OPENCLAW_CONTAINER:/home/node/.openclaw/workspace/USER.md"
      "$DOCKER_BIN" cp "$AGENTS_SRC" "$OPENCLAW_CONTAINER:/home/node/.openclaw/workspace/AGENTS.md"

      "$DOCKER_BIN" cp "$SOUL_SRC" "$OPENCLAW_CONTAINER:/opt/nous-agaas/agents/SOUL.md"
      "$DOCKER_BIN" cp "$USER_SRC" "$OPENCLAW_CONTAINER:/opt/nous-agaas/agents/USER.md"
      "$DOCKER_BIN" cp "$AGENTS_SRC" "$OPENCLAW_CONTAINER:/opt/nous-agaas/agents/AGENTS.md"

      "$DOCKER_BIN" cp "$USER_SRC" "$OPENCLAW_CONTAINER:/home/node/.openclaw/workspaces/grok-ceo/USER.md"
      if [ -f "$GROK_CEO_SOUL_SRC" ]; then
        "$DOCKER_BIN" cp "$GROK_CEO_SOUL_SRC" "$OPENCLAW_CONTAINER:/home/node/.openclaw/workspaces/grok-ceo/SOUL.md"
      fi
      if [ -f "$GROK_CEO_IDENTITY_SRC" ]; then
        "$DOCKER_BIN" cp "$GROK_CEO_IDENTITY_SRC" "$OPENCLAW_CONTAINER:/home/node/.openclaw/workspaces/grok-ceo/IDENTITY.md"
      fi
      echo "[$TS] OK: OpenClaw SOUL/USER/AGENTS runtime sync complete"
    else
      echo "[$TS] WARN: skipped OpenClaw identity sync; missing one of nous-agent-{soul,user,procedures}.md"
    fi
  else
    echo "[$TS] SKIP: OpenClaw identity sync; docker unavailable or $OPENCLAW_CONTAINER not running"
  fi
fi

# ─────────────────────────────────────────────────────────────────
# Session 68p+ fix: sync pages/tenants/*/skills/ → ~/nous-agaas/tenants/*/skills/
# Previously (sessions 21-67) tenant skills were only rsync'd manually or when
# a session remembered. Factory agents (extractor.py, writer.py, learner.py)
# read from ~/nous-agaas/tenants/<tenant>/skills/ — silent drift was possible.
# Session 68p hit the gap when task-extraction v0.2.9 bumps on Mac didn't
# reach Air runtime until manual rsync. Now covered automatically.
# NEVER --delete. Per-tenant; discovers tenants dynamically via glob.
# ─────────────────────────────────────────────────────────────────
if [ -d "$WIKI_TENANTS_DIR" ]; then
  for tenant_wiki_skills in "$WIKI_TENANTS_DIR"/*/skills/; do
    [ -d "$tenant_wiki_skills" ] || continue
    tenant_name=$(basename "$(dirname "$tenant_wiki_skills")")
    tenant_runtime_skills="$RUNTIME_TENANTS_DIR/$tenant_name/skills"
    mkdir -p "$tenant_runtime_skills"
    rsync -av \
      --exclude='_gbrain/' \
      --exclude='extracted/' \
      "$tenant_wiki_skills" "$tenant_runtime_skills/" \
      >> "/tmp/wiki-rsync-$TS.log" 2>&1
    echo "[$TS] OK: tenant/$tenant_name/skills/ sync complete"
  done
fi

# Session 2026-04-26: tenant runtime source now has a canonical vault copy at
# wiki/tenants/<tenant>/. Tenant skills remain canonical at
# wiki/pages/tenants/<tenant>/skills/ above. Sync source code/tests without
# secrets, state, caches, meeting payloads, or duplicate skills.
if [ -d "$WIKI_TENANT_RUNTIME_DIR" ]; then
  for tenant_src in "$WIKI_TENANT_RUNTIME_DIR"/*/; do
    [ -d "$tenant_src" ] || continue
    tenant_name=$(basename "$tenant_src")
    tenant_runtime="$RUNTIME_TENANTS_DIR/$tenant_name"
    mkdir -p "$tenant_runtime"
    rsync -av \
      --exclude='.env' \
      --exclude='state.db*' \
      --exclude='__pycache__/' \
      --exclude='*.pyc' \
      --exclude='skills/' \
      --exclude='meetings/*' \
      --exclude='vault-seed/' \
      "$tenant_src" "$tenant_runtime/" \
      >> "/tmp/wiki-rsync-$TS.log" 2>&1
    echo "[$TS] OK: tenant/$tenant_name/runtime-source sync complete"
  done
fi
