#!/bin/bash
# Verify the Air OpenClaw runtime matches the Nous full-stack contract:
# runtime/orchestrator != agent identity, and the shared skills/SOUL substrate is mounted.
set -u

AIR_HOST="${AIR_HOST:-air}"

ssh -o BatchMode=yes -o ConnectTimeout=10 "$AIR_HOST" 'bash -s' <<'REMOTE'
set -u
FAIL=0

pass() { printf 'OK: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; FAIL=1; }

need_file() {
  local path="$1"
  local label="$2"
  if [ -f "$path" ]; then pass "$label"; else fail "$label missing: $path"; fi
}

need_grep() {
  local pattern="$1"
  local path="$2"
  local label="$3"
  if [ ! -f "$path" ]; then
    fail "$label missing file: $path"
  elif grep -Eq "$pattern" "$path"; then
    pass "$label"
  else
    fail "$label missing pattern: $pattern in $path"
  fi
}

STATUS="$(docker ps --filter 'name=^/openclaw$' --format '{{.Status}}' 2>/dev/null || true)"
case "$STATUS" in
  *healthy*) pass "openclaw container is healthy ($STATUS)" ;;
  *) fail "openclaw container not healthy: ${STATUS:-not running}" ;;
esac

MOUNTS="$(docker inspect openclaw --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' 2>/dev/null || true)"
OPENCLAW_HOME="$(printf '%s\n' "$MOUNTS" | awk '$3 == "/home/node/.openclaw" {print $1; exit}')"
WIKI_SRC="$(printf '%s\n' "$MOUNTS" | awk '$3 == "/opt/nous-agaas/wiki" {print $1; exit}')"
SKILLS_SRC="$(printf '%s\n' "$MOUNTS" | awk '$3 == "/opt/nous-agaas/skills" {print $1; exit}')"

[ -n "$OPENCLAW_HOME" ] && [ -d "$OPENCLAW_HOME" ] && pass "OpenClaw home mount exists: $OPENCLAW_HOME" || fail "OpenClaw home mount missing"
[ -n "$WIKI_SRC" ] && [ -d "$WIKI_SRC" ] && pass "wiki mount exists: $WIKI_SRC -> /opt/nous-agaas/wiki" || fail "wiki mount missing"
[ -n "$SKILLS_SRC" ] && [ -d "$SKILLS_SRC" ] && pass "skills mount exists: $SKILLS_SRC -> /opt/nous-agaas/skills" || fail "skills mount missing"

if [ -n "$OPENCLAW_HOME" ] && [ -f "$OPENCLAW_HOME/openclaw.json" ]; then
  python3 - "$OPENCLAW_HOME/openclaw.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
fail = 0

def check(cond, msg):
    global fail
    if cond:
        print(f"OK: {msg}")
    else:
        print(f"FAIL: {msg}")
        fail = 1

agents = {a.get("id"): a for a in data.get("agents", {}).get("list", [])}
skills_dirs = data.get("skills", {}).get("load", {}).get("extraDirs", [])
check(data.get("agents", {}).get("defaults", {}).get("workspace") == "/home/node/.openclaw/workspace", "default workspace is OpenClaw workspace")
check("/opt/nous-agaas/skills" in skills_dirs, "shared Nous skill root is loaded by OpenClaw")
check("nous" in agents, "agent 'nous' is registered")
check("grok-ceo" in agents, "agent 'grok-ceo' is registered")
check(agents.get("nous", {}).get("workspace") == "/home/node/.openclaw/workspace", "nous uses default Nous workspace")
check(agents.get("grok-ceo", {}).get("workspace") == "/home/node/.openclaw/workspaces/grok-ceo", "grok-ceo uses isolated workspace")
check(agents.get("nous", {}).get("model") == "litellm/deepseek-v4-flash", "nous default worker model is deepseek-v4-flash")
check(agents.get("grok-ceo", {}).get("model") == "litellm/grok-reasoning", "grok-ceo Tier-1 model is grok-reasoning")
sys.exit(fail)
PY
  [ "$?" -eq 0 ] || FAIL=1
else
  fail "openclaw.json missing under OpenClaw home"
fi

if [ -n "$OPENCLAW_HOME" ]; then
  need_file "$OPENCLAW_HOME/workspace/AGENTS.md" "Nous workspace AGENTS.md"
  need_file "$OPENCLAW_HOME/workspace/SOUL.md" "Nous workspace SOUL.md"
  need_file "$OPENCLAW_HOME/workspace/USER.md" "Nous workspace USER.md"
  need_file "$OPENCLAW_HOME/workspace/TOOLS.md" "Nous workspace TOOLS.md"
  need_file "$OPENCLAW_HOME/workspaces/grok-ceo/AGENTS.md" "grok-ceo AGENTS.md"
  need_file "$OPENCLAW_HOME/workspaces/grok-ceo/SOUL.md" "grok-ceo SOUL.md"
  need_file "$OPENCLAW_HOME/workspaces/grok-ceo/USER.md" "grok-ceo USER.md"
  need_file "$OPENCLAW_HOME/workspaces/grok-ceo/TOOLS.md" "grok-ceo TOOLS.md"
  need_grep 'I am \*\*Nous\*\*' "$OPENCLAW_HOME/workspace/SOUL.md" "Nous SOUL identity is mounted"
  need_grep '/ask.*grok-ceo|grok-ceo.*Tier-1' "$OPENCLAW_HOME/workspace/AGENTS.md" "Nous AGENTS route table names grok-ceo"
  need_grep 'Tier-1 President proxy|Tier-1 Telegram CEO router' "$OPENCLAW_HOME/workspaces/grok-ceo/SOUL.md" "grok-ceo SOUL identity is mounted"
  need_grep 'role: Tier-1 President / CEO proxy' "$OPENCLAW_HOME/workspaces/grok-ceo/IDENTITY.md" "grok-ceo IDENTITY is mounted"
fi

if [ -n "$SKILLS_SRC" ]; then
  need_file "$SKILLS_SRC/gstack/SKILL.md" "gstack skill is visible to OpenClaw"
  need_file "$SKILLS_SRC/gstack/openclaw/skills/gstack-openclaw-ceo-review/SKILL.md" "gstack OpenClaw CEO-review skill is visible"
  need_file "$SKILLS_SRC/gstack/openclaw/skills/gstack-openclaw-investigate/SKILL.md" "gstack OpenClaw investigate skill is visible"
  need_file "$SKILLS_SRC/ceo-hierarchy/SKILL.md" "ceo-hierarchy skill is visible"
  need_file "$SKILLS_SRC/command-center/SKILL.md" "command-center skill is visible"
  need_file "$SKILLS_SRC/factory-ops/SKILL.md" "factory-ops skill is visible"
  need_file "$SKILLS_SRC/openbrain-projection/SKILL.md" "openbrain-projection skill is visible"
fi

if [ "$FAIL" -eq 0 ]; then
  echo "OK: OpenClaw full-stack contract holds (runtime, agents, SOUL files, skills, gstack, OpenBrain skill)"
fi
exit "$FAIL"
REMOTE
