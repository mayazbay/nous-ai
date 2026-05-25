---
type: lesson
id: LESSON-092
title: "LESSON-092: OpenClaw Docker config — ~/.openclaw/openclaw.json, not /app/openclaw.json"
tags: [lessons, openclaw, docker, config, air, migration, infrastructure]
date: 2026-04-15
source_count: 0
status: absorbed
absorbed_at: 2026-04-16
last_updated: 2026-04-15
related: [air-migration-plan-2026-04-14, LESSON-090-litellm-native-vs-docker-macos, LESSON-091-docker-image-transfer-scp-not-pipe]
session: 21
severity: P1
integrated_into: infrastructure
absorbed_into: infrastructure
---

# LESSON-092: OpenClaw Docker config — `~/.openclaw/openclaw.json`, not `/app/openclaw.json`

## The Problem

```bash
# WRONG — mounts config to /app/openclaw.json:
docker run -d --name openclaw \
  -v ~/nous-agaas/openclaw/openclaw.json:/app/openclaw.json \
  ghcr.io/openclaw/openclaw:2026.3.28
```

OpenClaw logs showed:
```
[gateway] auth token was missing. Generated a new token and saved it to config
[gateway] agent model: anthropic/claude-opus-4-6   # wrong! should be litellm/glm-5.1
```

`openclaw agents list` showed default `main` agent instead of our `nous` agent.
`run_task.py` failed with: `Error: Unknown agent id "nous"`.

## Root Cause

OpenClaw **reads its runtime config from `~/.openclaw/openclaw.json`** (i.e., `/home/node/.openclaw/openclaw.json` inside the container), NOT from `/app/openclaw.json`.

The file at `/app/openclaw.json` exists in the image but is **not the active config file** — it is documentation or a template. OpenClaw generates its user config at `~/.openclaw/openclaw.json` on first run.

On VPS, the `~/.openclaw/openclaw.json` had already been initialized with our full config (agents, models, LiteLLM). On a **fresh container** (Air), it only contains defaults — including the wrong `main` agent and `anthropic/claude-opus-4-6` model.

## Trap: File bind mount locks parent directory

```bash
# ALSO WRONG — file bind mount causes EACCES:
docker run -d --name openclaw \
  -v ~/nous-agaas/openclaw/openclaw.json:/home/node/.openclaw/openclaw.json \
  ghcr.io/openclaw/openclaw:2026.3.28
```

When Docker bind-mounts a single FILE into a directory, it sets the parent directory ownership in a way that the container's `node` user can't create sibling files/dirs. Result:
```
EACCES: permission denied, mkdir '/home/node/.openclaw/workspace'
EACCES: permission denied, mkdir '/home/node/.openclaw/canvas'
GatewayClientRequestError: missing scope: operator.write
```

The workspace can't be created → agent can't run tasks.

## The Fix

**Use `docker cp` to inject the config after first startup, then restart:**

```bash
# Step 1: Start container WITHOUT config mount (let it initialize defaults)
docker run -d \
  --name openclaw \
  --restart unless-stopped \
  -p 18789:18789 \
  --platform linux/amd64 \
  -v ~/nous-agaas/wiki:/root/nous-agaas/wiki \
  -v ~/nous-agaas/skills:/opt/nous-agaas/skills \
  ghcr.io/openclaw/openclaw:2026.3.28

# Step 2: Wait for OpenClaw to start (logs show "listening on ws://127.0.0.1:18789")
docker logs openclaw --tail 5

# Step 3: Copy our config into the running container
docker cp ~/nous-agaas/openclaw/openclaw.json openclaw:/home/node/.openclaw/openclaw.json

# Step 4: Restart so OpenClaw reads our config
docker restart openclaw

# Step 5: Verify correct agent and model loaded
docker logs openclaw --tail 5
# Expected:
# [gateway] agent model: litellm/glm-5.1
# [gateway] listening on ws://127.0.0.1:18789
```

## Verification

```bash
# Agents should show 'nous' (default) with litellm/glm-5.1:
docker exec openclaw openclaw agents list

# End-to-end test:
cd ~/nous-agaas && python3 run_task.py "Reply with exactly: AIR_OPENCLAW_OK"
# Expected: AIR_OPENCLAW_OK
```

## Warning: lossless-claw plugin

The config references the `lossless-claw` plugin which is not installed in fresh containers. OpenClaw logs a config warning and ignores it — this is harmless:

```
plugins.entries.lossless-claw: plugin not found: lossless-claw (stale config entry ignored)
```

To eliminate this, remove the `plugins:` section from `openclaw.json` for Air deployment.

## Rule

**Never mount OpenClaw config as a bind mount.** Use `docker cp` to inject config into the container on first run.

For persistent config across `docker rm + docker run` cycles, use a Docker named volume:
```bash
docker volume create openclaw-config
docker run -d --name openclaw \
  -v openclaw-config:/home/node/.openclaw \
  ...
# Initialize: docker run --rm -v openclaw-config:/data alpine cp /your/config.json /data/openclaw.json
```

---

## Timeline

- **2026-04-15** | Session 21: Discovered `/app/openclaw.json` is not the active config. Root cause: OpenClaw uses `~/.openclaw/openclaw.json`. File bind mount caused EACCES. Fixed with `docker cp` + restart. Verified: `AIR_GLM_OK` via glm-5.1 directly.

## See also

- [[air-migration-plan-2026-04-14]] — migration context
- [[LESSON-090-litellm-native-vs-docker-macos]] — LiteLLM native deployment
- [[LESSON-091-docker-image-transfer-scp-not-pipe]] — Docker image transfer
