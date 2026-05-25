#!/bin/bash
# bump_openclaw_skills_version.sh — trigger OpenClaw to refresh skillsSnapshot
#
# Session 48 W11/W12 (2026-04-18) workaround for OpenClaw 2026.4.14 bug where
# `chokidar` watcher doesn't bump `skillsSnapshot.version`, leaving sessions.json
# frozen with the skill set present at session creation time. Result: newly-added
# skills under /opt/nous-agaas/skills/ are invisible to the running factory until
# this bump fires.
#
# Use after adding/renaming/removing a SKILL.md that you want factory to see.
# Bumps version by 1. The next direct OpenClaw CLI agent call triggers
# `shouldRefreshSnapshotForVersion`, which rebuilds the snapshot from the live
# filesystem.
#
# Runs on Mac; ssh-exec's the actual bump on Air inside the openclaw container.
#
# Absorbed as infrastructure v2.39 AP-46. Paired AP-36 sibling-test at
# tools/test_bump_openclaw_skills_version.sh.

set -eu

SSH_HOST="${OPENCLAW_SSH_HOST:-air}"
SESSIONS_JSON_PATH="/home/node/.openclaw/agents/nous/sessions/sessions.json"
AGENT_KEY="${OPENCLAW_AGENT_KEY:-agent:nous:main}"
AGENT_ID="${OPENCLAW_AGENT_ID:-nous}"
REQUIRED_SKILLS_CSV="${OPENCLAW_REQUIRED_SKILLS:-ceo-hierarchy,collaborative-reading,find-skills,musk-algorithm,operator-boundaries,session-architecture,gbrain-ops,karpathy-loop,session-coordination,session-operating-contract}"

if ! ssh -o ConnectTimeout=10 "$SSH_HOST" "true" 2>/dev/null; then
  echo "ERROR: cannot ssh to $SSH_HOST" >&2
  exit 1
fi

cleanup_probe_processes() {
  local token="$1"
  ssh "$SSH_HOST" "docker exec openclaw sh -lc \"sleep 1; PIDS=\\\$(ps -eo pid,args | grep 'openclaw agent' | grep '$token' | grep -v grep | awk '{print \\\$1}'); if [ -n \\\"\\\$PIDS\\\" ]; then kill -9 \\\$PIDS 2>/dev/null || true; fi\"" >/dev/null 2>&1 || true
}

echo "=== 1/3 backup sessions.json ==="
ssh "$SSH_HOST" "docker exec openclaw cp $SESSIONS_JSON_PATH ${SESSIONS_JSON_PATH}.bak-\$(date +%s)" || {
  echo "ERROR: backup failed" >&2
  exit 1
}

echo "=== 2/3 bump version (+1) ==="
ssh "$SSH_HOST" "docker exec -i openclaw python3 << PYEOF
import json, sys
p = \"$SESSIONS_JSON_PATH\"
d = json.load(open(p))
key = \"$AGENT_KEY\"
if key not in d or \"skillsSnapshot\" not in d[key]:
    print(f\"ERROR: {key} or skillsSnapshot missing\", file=sys.stderr)
    sys.exit(2)
old = d[key][\"skillsSnapshot\"].get(\"version\", 0)
d[key][\"skillsSnapshot\"][\"version\"] = old + 1
with open(p, \"w\") as f:
    json.dump(d, f, indent=2)
print(f\"bumped {old} -> {old + 1}\")
PYEOF
" || {
  echo "ERROR: version bump failed" >&2
  exit 1
}

echo "=== 3/3 trigger rebuild via trivial task ==="
TOKEN="BUMP_VERIFY_$(date +%s)"
if ! AGENT_OUTPUT=$(ssh "$SSH_HOST" "docker exec openclaw openclaw agent --agent '$AGENT_ID' --message 'Reply with: $TOKEN' --json --timeout 120" 2>&1); then
  cleanup_probe_processes "$TOKEN"
  printf '%s\n' "$AGENT_OUTPUT" >&2
  echo "WARN: OpenClaw did not finish cleanly — skillsSnapshot refresh may be incomplete" >&2
  exit 1
fi
cleanup_probe_processes "$TOKEN"
if ! printf '%s\n' "$AGENT_OUTPUT" | grep -q "$TOKEN"; then
  printf '%s\n' "$AGENT_OUTPUT" >&2
  echo "WARN: OpenClaw did not echo $TOKEN — skillsSnapshot refresh may be incomplete" >&2
  exit 1
fi

echo ""
echo "=== skillsSnapshot after bump ==="
ssh "$SSH_HOST" "docker exec -i openclaw python3 << PYEOF
import json, sys
d = json.load(open(\"$SESSIONS_JSON_PATH\"))
snap = d[\"$AGENT_KEY\"][\"skillsSnapshot\"]
loaded = {s.get(\"name\") for s in snap.get(\"skills\", []) if isinstance(s, dict)}
required = {s for s in \"$REQUIRED_SKILLS_CSV\".split(\",\") if s}
missing = sorted(required - loaded)
print(f\"  version: {snap.get('version')}\")
print(f\"  skills loaded: {len(snap.get('skills', []))}\")
if missing:
    print(\"  missing required: \" + \", \".join(missing), file=sys.stderr)
    sys.exit(3)
print(\"  required skills: OK\")
PYEOF
" || {
  echo "ERROR: required skills still missing after refresh" >&2
  exit 1
}
cleanup_probe_processes "$TOKEN"

echo ""
echo "✅ version bump complete"
