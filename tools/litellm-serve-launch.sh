#!/bin/bash
# litellm-serve-launch.sh — Air LiteLLM serve runner (session 47 M4, D3-INLINE extraction)
#
# Extracted from com.nous.litellm.plist ProgramArguments inline-bash (session 47 M4).
# KeepAlive=true; launchd restarts automatically on exit.
#
# Air runtime path: /Users/madia/nous-agaas/tools/litellm-serve-launch.sh
# Plist label:      com.nous.litellm
# Schedule:         always-on (KeepAlive)
# Port:             4000
# Config:           /Users/madia/nous-agaas/litellm/config.yaml
# Env:              /Users/madia/nous-agaas/litellm/.env (auto-sourced with set -a)
#
# Rollback: if this script breaks, restore the pre-M4 plist backup at
#   ~/Library/LaunchAgents/com.nous.litellm.plist.pre-m4-2026-04-18
# and `launchctl bootout` + `bootstrap`.

set -u
cd /Users/madia/nous-agaas
set -a
source litellm/.env
set +a
exec /Library/Frameworks/Python.framework/Versions/3.11/bin/litellm --config litellm/config.yaml --port 4000
