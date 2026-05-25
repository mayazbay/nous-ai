---
type: system
id: air-runtime-scripts-README
title: "Air runtime scripts — backup copies under version control"
tags: [air, runtime, scripts, backup]
date: 2026-04-15
source_count: 0
status: reviewed
last_updated: 2026-04-15
related: [infrastructure, LESSON-108, LESSON-109]
---

# Air Runtime Scripts — Backup Copies

Backup copies of the one-off operational Python scripts that live on the M2 Air but are not otherwise in any git repo. Kept here so they survive if Air dies.

**Authoritative copy:** the Air filesystem paths below are the ones launchd actually executes. Do NOT call these vault copies directly. When editing, edit on Air (or here with an `rsync` back to Air in the same change).

| Script | Air path | launchd job | Purpose |
|--------|----------|-------------|---------|
| `auto_checkpoint.py` | `~/nous-agaas/auto_checkpoint.py` | `com.nous.auto-checkpoint` (8×/day) | Writes `HANDOFF-AUTO-*.md` via run_task.py + GLM-5.1 when there are new task-results since last checkpoint |

**Moved out of this dir (session 47 M1):**
- `satory_events_watcher.py` → `tools/satory_events_watcher.py` (D2-WRONG-DIR resolution, AUDIT §2.3). Air runtime path unchanged.

## Canonical `tools/` registry — Air launchd scripts tracked in vault

Updated session 47 M3 (2026-04-18) — MIGRATE-CLEAN bucket pulled into vault for version control + rsync scope coverage (session-47 M5 extends `wiki-to-runtime-rsync` to `tools/`).

| Vault path | Air runtime path | launchd label | Schedule | Purpose |
|---|---|---|---|---|
| `tools/satory_events_watcher.py` | `~/nous-agaas/tools/satory_events_watcher.py` | `com.nous.satory-events-watcher` | every 300 s | Fires Telegram alert when `events_last_seen` advances past the 2026-04-05 frozen baseline (Denis's dual-target script landed indicator) |
| `tools/log-rotate.sh` | `~/nous-agaas/tools/log-rotate.sh` | `com.nous.log-rotate` | Sun 03:00 Almaty | Truncates logs > 5MB in `~/nous-agaas/logs/`, keeps last 1000 lines |
| `tools/capture_to_nous_pending.sh` | `~/.local/bin/capture_to_nous_pending.sh` | `com.nous.capture-courier` | every 30 s | Moves capture attachments into the vault `raw/pending/` tree |
| `tools/session_rotate.sh` | `~/nous-agaas/tools/session_rotate.sh` | `com.nous.session-rotate` | daily 22:45 | Archives today's Claude Code session transcripts |
| `tools/staleness-check.sh` | `~/nous-agaas/tools/staleness-check.sh` | `com.nous.staleness` | every 3600 s | Flags stale state in dashboards; emits Telegram alert on drift |
| `tools/nous-obsidian-sync.sh` | `~/.local/bin/nous-obsidian-sync.sh` | `com.nous.obsidian-sync` | every 60 s | Obsidian vault → VPS bare git sync runner |
| `tools/backup.sh` | 🚨 `~/Desktop/nous ai/backup.sh` | `com.nous.backup` | daily 03:00 Almaty | Daily iMac mission-control + alpha-trading DB backups. **LAW-005 violation remaining** — Air runtime path is still on Desktop; plist update deferred to session 48 (needs kickstart-verify). Vault copy tracks content only. |
| `tools/auto_checkpoint.py` | `~/nous-agaas/auto_checkpoint.py` | `com.nous.auto-checkpoint` | 8×/day | (Currently also tracked in `pages/systems/air-runtime-scripts/` — consolidation candidate for future session.) |

**LAW-005 carryover (session 48):** `backup.sh` Air runtime path is still `~/Desktop/nous ai/backup.sh` (LAW-005 violation — operational script on Desktop). Full migration requires:
1. `scp vault/tools/backup.sh air:~/nous-agaas/tools/backup.sh` (M5 rsync may handle once scope extends)
2. Edit `~/Library/LaunchAgents/com.nous.backup.plist` `ProgramArguments` from `/Users/madia/Desktop/nous ai/backup.sh` → `/Users/madia/nous-agaas/tools/backup.sh`
3. `launchctl bootout gui/$(id -u)/com.nous.backup` + `bootstrap`
4. `launchctl kickstart -k` to verify (script ssh's to iMac 192.168.1.30; failures graceful per design)
5. Once kickstart confirms exit 0 + verified next 03:00 run succeeds, delete Desktop copy.

## Update procedure

When you change either script:

1. Edit on Air directly, or edit here and `rsync` back.
2. Run manually once to verify the change: `cd ~/nous-agaas && /opt/homebrew/bin/python3 <script>`
3. Sync the vault copy: `rsync -av air:<path> <vault-path>`
4. Commit + push — both changes in the same commit.

## See also

- [[SKILL]] — AP-14 (subprocess wrapper discipline), AP-15 (timestamp compare discipline)
- [[LESSON-108-subprocess-error-reporting-stderr-head-vs-tail]]
- [[LESSON-109-iso-timestamp-string-compare-false-positive]]
