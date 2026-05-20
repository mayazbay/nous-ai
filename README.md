# Nous Factory Dashboard

Last update: 2026-04-27T15:58:28+05:00

This README is the human/agent front door. Detailed memory stays in Obsidian/gbrain; this page is the fast status surface.

## Current State

| Metric | Value |
|---|---:|
| Skills | 30 |
| Task-results today | 15 |
| Dashboards | 24 |

## Latest Signals

| Signal | File | Summary |
|---|---|---|
| Handoff | `pages/progress/HANDOFF-AUTO-2026-04-27-15-00.md` | Factory auto-checkpoint — 2026-04-27-15-00 KZT |
| Task result | `pages/task-results/2026-04-27-15-25-48-reply-exactly-ask-route-ok.md` | 2026-04-27-15-25-48-reply-exactly-ask-route-ok.md |

## Burst Compute

| Lane | Status | Command |
|---|---|---|
| Blacksmith 32 vCPU portable tests | configured, manual GitHub trigger pending org/app wiring | `bash tools/blacksmith_burst_tests.sh` |
| Local/Air proof | script-first, secret-free | `bash tools/blacksmith_burst_tests.sh` |

## Sweeper Model

ClawSweeper pattern adapted for Nous:

- review lane proposes only
- apply lane is the only writer
- README is the dashboard
- external GitHub issue/PR mutation waits for scoped `gh` auth or a GitHub App token
- Obsidian/gbrain remains the memory substrate

## Operator Commands

```bash
python3 tools/readme_dashboard.py
bash tools/blacksmith_burst_tests.sh
```
