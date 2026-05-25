---
type: spec
id: SPEC-REMOVE-WORKER-TASK-FILTER
title: "Remove stale WORKER_TASK_FILTER=frontend from nous-agaas systemd drop-in (dead config)"
date: 2026-04-08
tags: [spec, factory, systemd, cleanup, worker-task-filter, req, ops]
source_count: 0
status: reviewed
last_updated: 2026-04-08
priority: p2
related: [phase-3-bdl-replacement-reqs-2026-04-08, AUDIT-019-session-close-apr7, factory-coder-prompt-fix-src-paths-2026-04-08]
historical: true
---

# SPEC — Remove stale `WORKER_TASK_FILTER=frontend` from nous-agaas systemd drop-in

## Problem

The systemd service `nous-agaas.service` has a drop-in override at `/etc/systemd/system/nous-agaas.service.d/worker1.conf` containing:

```
[Service]
Environment=WORKER_ID=worker1
Environment=WORKER_TASK_FILTER=frontend
```

The `WORKER_TASK_FILTER` env var is **dead config**. The current `/root/nous-agaas/graph.py` does NOT read it — `grep WORKER_TASK_FILTER /root/nous-agaas/graph.py` returns empty. Only the old backup files (`graph.py.backup.20260405_*`) reference it in the deprecated `_filter_tasks_by_worker()` function.

AUDIT-019 flagged this as a cleanup: *"Factory task filter (`WORKER_TASK_FILTER=frontend`) is in systemd unit but not honored by current graph.py. Either remove from unit or reinstate filter logic."*

There's ALSO a second worker unit file at `/etc/systemd/system/nous-worker2.service` with `Environment=WORKER_TASK_FILTER=backend` — currently disabled (`systemctl list-unit-files` shows `nous-worker2.service disabled enabled`).

## Why it matters

Three risks of keeping dead config:

1. **Confusion**: future contributors (or me in a later session) see `WORKER_TASK_FILTER=frontend` and think the factory only processes frontend tasks. It doesn't. This is exactly the "lies to future readers" problem we want to eliminate per LAW-013.
2. **Accidental reinstatement**: if someone tries to "fix" the filter by re-adding `_filter_tasks_by_worker()` to graph.py, they'll be adding complexity based on a flag that was already deprecated for a reason (single-worker setup is simpler and current scale doesn't need parallelism).
3. **Environment pollution**: every factory process inherits the env var, which could accidentally be read by a tool that isn't graph.py (e.g., a future helper script).

## Proposed fix

### Option A (recommended) — Delete the drop-in file entirely

```bash
# Backup first
sudo cp /etc/systemd/system/nous-agaas.service.d/worker1.conf \
        /tmp/worker1.conf.backup.$(date +%Y%m%d_%H%M%S)

# Remove the drop-in
sudo rm /etc/systemd/system/nous-agaas.service.d/worker1.conf

# Also remove the parent directory if empty (it was only for this drop-in)
sudo rmdir /etc/systemd/system/nous-agaas.service.d/ 2>/dev/null || true

# Reload systemd
sudo systemctl daemon-reload

# Verify
systemctl show nous-agaas --no-pager | grep -iE "environment|filter"
# Expected: no WORKER_TASK_FILTER, no WORKER_ID (unless they're in the base unit file too)
```

**Side effect to verify:** the base unit file at `/etc/systemd/system/nous-agaas.service` does NOT rely on `WORKER_ID` or `WORKER_TASK_FILTER`. Verify with `grep WORKER /etc/systemd/system/nous-agaas.service` — should be empty. If WORKER_ID is needed for logging or anything, preserve it in the base unit instead of the drop-in.

### Option B — Edit the drop-in to keep WORKER_ID only

```bash
sudo tee /etc/systemd/system/nous-agaas.service.d/worker1.conf <<EOF
[Service]
Environment=WORKER_ID=worker1
EOF

sudo systemctl daemon-reload
```

Use this if `WORKER_ID` is read anywhere for logging or task claiming. Per grep, it doesn't look like graph.py uses WORKER_ID either, but I haven't audited every tool — better safe.

### Option C — Keep it and add a comment explaining the historical context

```bash
sudo tee /etc/systemd/system/nous-agaas.service.d/worker1.conf <<EOF
[Service]
# NOTE 2026-04-08: WORKER_TASK_FILTER and WORKER_ID are LEGACY config.
# Current graph.py ignores both (single-worker setup). Do not re-enable
# task filtering without also re-adding _filter_tasks_by_worker() in graph.py.
# See pages/specs/remove-worker-task-filter-systemd-2026-04-08.md in the vault.
Environment=WORKER_ID=worker1
Environment=WORKER_TASK_FILTER=frontend
EOF
```

Use this if Madi wants to preserve the config file for historical reasons but make the deadness explicit. Less clean than Option A.

**My recommendation:** Option A. Delete it. Minimum surface area. If anything goes wrong, the backup is at `/tmp/worker1.conf.backup.*` and can be restored in 10 seconds.

### Separately — decide fate of `nous-worker2.service`

The disabled `nous-worker2.service` unit file also has `Environment=WORKER_TASK_FILTER=backend`. It's currently disabled so it's not actively harmful, but it's the same dead config.

**Proposal:** delete the unit file entirely. It's disabled and references dead config. If a second worker is ever needed (unlikely given single-worker + bigger-tasks strategy from AUDIT-022), re-create it fresh.

```bash
sudo rm /etc/systemd/system/nous-worker2.service
sudo systemctl daemon-reload
```

## Test plan

1. Apply Option A (or B or C) on `/etc/systemd/system/nous-agaas.service.d/worker1.conf`.
2. `systemctl daemon-reload`
3. `systemctl show nous-agaas --no-pager | grep Environment` — verify WORKER_TASK_FILTER is gone.
4. If factory is running: `systemctl status nous-agaas` — verify still active, no errors.
5. If factory is stopped: wait for Madi to restart after credit top-up. Verify first cycle runs normally (no "no pending tasks because filter blocked everything" errors).

## Risk assessment

- **Config change risk**: LOW. Environment variable removal doesn't change any code. Factory is stopped right now anyway.
- **Behavior change**: NONE. graph.py already ignores the env var. Removing it produces zero runtime difference.
- **Rollback**: INSTANT via `cp` from `/tmp/worker1.conf.backup.*` + `systemctl daemon-reload`.
- **Dependencies**: NONE. Independent of all other factory fixes.

## Why NOT apply this change today

Same reasoning as the graph.py Coder prompt fix: factory is stopped, can't verify the cleanup end-to-end without running it, and running costs credits Madi has paused. Also, this is a P2 (cleanup) not a P0 (blocker) — no urgency.

**When to apply:** either (a) alongside the graph.py Coder prompt fix in the first post-credit-top-up session, OR (b) opportunistically any time the factory is being restarted for another reason.

## See also
- [[factory-coder-prompt-fix-src-paths-2026-04-08]] — companion fix spec
- [[phase-3-bdl-replacement-reqs-2026-04-08]] — Phase 3 REQs that need the factory to not idle
- [[AUDIT-019-session-close-apr7]] — original flag of this issue
- [[AUDIT-022-nit-vpn-reversal-ceo-sonnet-leverage-strategy]] — the single-worker + bigger-tasks decision (why no second worker needed)
