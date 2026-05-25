---
tier: 2
type: skill
name: satory-daily-operator-brief
id: SKILL-SATORY-DAILY-OPERATOR-BRIEF
version: 1.2.2
last_updated: 2026-05-14
status: active
description: "v1.2.2 — Camera Doctor V2 tenant-agnostic daily operator brief agent. Tenant fitness is mechanically probed via tools/probe_tenant.py <tenant>: config parse, ERAP SSH dial-tone, DB path presence, WireGuard interface check, and integer alert_chat_id with structured exit codes (0 fit, 1 config invalid, 2 network unreachable, 3 warning). v1.2.2 separates APK status bot evidence from main factory bot health."
triggers:
  - any work on camera_doctor agent or Satory ERAP integration
  - camera brief not delivered
  - Satory operator brief debugging
  - fleet status queries
tools: [Read, Write, Bash, ssh]
mutating: false
related: [session-operating-contract, autonomous-build-manager, agent-quality]
tags: [skill, satory, camera-doctor, daily-brief, revenue, telegram, launchd]
title: "satory-daily-operator-brief v1.2.2"
---

# satory-daily-operator-brief v1.2.2

## Purpose

Daily Russian-language camera fleet SLA brief delivered at 06:00 Almaty to Satory operators. Revenue vehicle: bill Satory per active operator receiving the brief.

## Architecture

```
Air launchd (06:00) → agents/camera_doctor/main.py --tenant satory
  → probe.query_events_remote (SSH → VPS events.db)
  → probe.query_camera_health_remote (SSH → VPS camera_health.db)
  → tenant-configured detectors → render.render_markdown + render_pdf
  → tools/tg_send.sh (when mode=live) → briefs/ archive + JSONL runlog
```

**Key files:**
- `agents/camera_doctor/` — probe, detectors, render, runlog, main
- `tenants/satory/camera_doctor.toml` — per-tenant config (flip `mode=live` to go live)
- `tenants/gov-pilot/camera_doctor.toml` — dry-run-only stub proving multi-tenant load path
- `tenants/satory/launchd/com.nous.satory-daily-brief.plist` — tracked 06:00 Almaty schedule for `com.nous.satory-daily-brief`
- Air also has `~/Library/LaunchAgents/com.nous.satory-camera-doctor.plist` with `--dry-run`; inspect both labels before live cutover
- `~/nous-agaas/logs/satory-camera-doctor/YYYY-MM-DD.jsonl` — Air runlog
- `~/nous-agaas/wiki/briefs/` — PDF archive

## Running

```bash
# Dry-run (no Telegram, logs to runlog):
cd ~/nous-agaas/wiki && python3 -m agents.camera_doctor.main --tenant satory --dry-run

# Config check only:
python3 -m agents.camera_doctor.main --tenant satory --config-only

# Go live (AFTER 7 dry-run cycles + 0 schema failures + Madi approval):
bash tools/camera_doctor_live_cutover.sh satory
```

## Tenant config contract

Every Camera Doctor tenant config must define:

- `[tenant]`: `slug`, `display_name`, `brief_language` (`ru` or `en`), `timezone`, `expected_camera_count`
- `[erap]`: `ssh_host`, `events_db`, `camera_health_db`, optional registry/APK DB paths
- `[network]`: `wg_interface`
- `[notify]`: `alert_chat_id`, `pdf_archive_path`, `pdf_naming`
- `[thresholds]`: fleet, mirror freshness, offline age, wrong-direction, and WireGuard thresholds
- `[brand]`: `brief_title`, `agent_signature`, `language`
- `[mode]`: `dry_run` or `live`

Satory still carries legacy `[vps]` / `tg_chat_id` keys during migration for backward compatibility, but shared runtime reads normalized `[erap]`, `[network]`, and `alert_chat_id`.

## Tenant Fitness Probe

Run before onboarding or promoting any tenant beyond config-only:

```bash
python3 tools/probe_tenant.py <tenant>
```

Exit codes are structured:

- `0`: fit
- `1`: config invalid
- `2`: network unreachable
- `3`: warning-only state

The probe validates TOML shape, `[erap]` DB path fields, `[notify].alert_chat_id` integer format, SSH dial-tone to `[erap].ssh_host` (`ssh <host> echo ok` only; no DB query), and `agents.camera_doctor.probe.wg_handshake_age()` for `[network].wg_interface`. Local Mac lacks `wg`, so a healthy SSH dial-tone records `skipped_local_wg_unavailable` instead of failing Satory; hosts with `wg` installed fail stale handshakes as network-unreachable.

Current contract:

```bash
python3 tools/probe_tenant.py satory      # exit 0
python3 tools/probe_tenant.py gov-pilot   # exit 2 (placeholder host)
```

## 5 Runtime Detector Slots

| # | Name | Fires when | Severity |
|---|---|---|---|
| 1 | Mirror Data Stale | vehicle_events.MAX(event_time) > 24h ago | yellow/red at >48h |
| 2 | VPN/Network Down | tenant WireGuard handshake > 600s OR fleet_online == 0 | red |
| 3 | Fleet Degraded | online_pct < tenant threshold | yellow/red by 14d p10 |
| 4 | Cameras Offline >7d | camera_status offline age exceeds threshold | yellow/red by count |
| 5 | Camera Pointing Wrong Direction | optional field/vision probe reports sky/ground/wrong-direction rate above threshold | yellow/red; silent without probe |

Wrong-direction is intentionally optional in V2: yesterday's Almaty-Kapchagai field finding (~40% of inspected cameras pointed at sky/ground) is business-case fuel for government audit work, not fabricated production telemetry. It fires only when an `orientation_probe` payload is supplied.

## Live Cutover (Mechanical Gate)

Do not manual-edit TOML and plist state for live cutover. Run:

```bash
bash tools/camera_doctor_live_cutover.sh satory
```

The script enforces AP-4 mechanically:

- Validates `tenants/<tenant>/camera_doctor.toml` is loadable, `[mode].mode == "dry_run"`, and `[notify].alert_chat_id` is an integer.
- Atomically flips TOML to `mode = "live"` and removes `--dry-run` from every tracked Camera Doctor plist for that tenant, including `tenants/<tenant>/launchd/*.plist` and legacy `tools/launchd/com.nous.<tenant>-camera-doctor.plist`.
- Copies edited plists to Air `~/Library/LaunchAgents/`, then runs `launchctl bootout` + `launchctl bootstrap` over SSH.
- Fails if any Air plist still contains `--dry-run` while TOML is live.
- Runs an immediate Air pipeline probe (`python3 -m agents.camera_doctor.main --tenant <tenant>`) and requires `alert_sent=True`.
- Rolls local TOML/plist edits back from backups on any partial failure before success.

Satory remains dry-run until the 7-clean-cycle gate is met and Madi approves the live flip.

## Dry-run gate (Phase 6)

Run 7 dry-run cycles. Zero schema-contract failures. Then use the mechanical gate above. The live evidence remains the next runlog line with `alert_sent=true`, but the cutover state change is now script-owned rather than memory-owned.

## AP-1 — events.db is 61MB; never SCP it

Query remotely via SSH using `probe.query_events_remote`. SCP will timeout after 30s. The probe functions execute sqlite3 over SSH and return plain dicts.

## AP-2 — Nested single quotes in SSH sqlite3 commands

Use double-quote shell wrapping: `f'sqlite3 {remote_path} "SELECT ... WHERE status=\\'online\\';"'`. Single quotes inside the SQL must be escaped or the shell will break the command.

## AP-4 — Air has two launchd labels; inspect both before live

Verified 2026-05-05: the tracked repo plist is `tenants/satory/launchd/com.nous.satory-daily-brief.plist`, label `com.nous.satory-daily-brief`, ProgramArguments `python3 -m agents.camera_doctor.main --tenant satory` (no CLI `--dry-run`). Air also has `~/Library/LaunchAgents/com.nous.satory-camera-doctor.plist`, label `com.nous.satory-camera-doctor`, ProgramArguments include `--dry-run`.

Before live cutover, inspect both:

```bash
ssh air 'plutil -p ~/Library/LaunchAgents/com.nous.satory-daily-brief.plist'
ssh air 'plutil -p ~/Library/LaunchAgents/com.nous.satory-camera-doctor.plist'
```

If the legacy `com.nous.satory-camera-doctor` job is loaded, either unload it or remove `--dry-run` intentionally. TOML-only live flip is insufficient while any loaded launchd label still passes CLI `--dry-run`.

### AP-5 — APK status bot is camera monitoring, not main factory health

The APK status bot (`Nous AI`, `apk-bot-polling.service` on VPS) is separate from main `@nousAGaaSbot` (`Nous AGaaS`, `com.nous.telegram-poll` on Air). Do not mix their Telegram evidence.

If `apk_health_current` is empty, the bot must not stop at "no data" and must not imply all APKs are broken. It must read the surrounding proof before replying:

```bash
ssh root@65.108.215.200 'systemctl is-active nous-isapi; ss -tlnp | grep 9080'
ssh root@65.108.215.200 'sqlite3 /opt/nous-agaas/erap/data/events.db "select count(*), max(event_time), max(created_at) from vehicle_events;"'
ssh root@65.108.215.200 'sqlite3 /opt/nous-agaas/erap/data/camera_health.db "select status, count(*) from camera_status where last_check > datetime('\''now'\'','\''-1 hour'\'') group by status;"'
ssh root@65.108.215.200 'wg show wg-satory latest-handshakes; wg show wg-satory endpoints; wg show wg-satory transfer'
ssh root@65.108.215.200 'sqlite3 /opt/nous-agaas/erap/data/apk_health.db "select subnet_label, method, sum(ok), count(*) from camera_reachability where probed_at=(select max(probed_at) from camera_reachability) group by subnet_label, method;"'
```

The user-facing output must name the concrete current layer: listener up, latest event time, fresh camera poll counts, reachability probe counts, and whether the root cause is NIT VPN / route to `10.170.*` and `10.235.*`.

## AP-3 — PDF cap is 256KB, not 200KB

weasyprint embeds Cyrillic fonts (baseline ~150KB overhead). Setting 200KB is unreachable. Risk being guarded (runaway multi-MB file) is addressed at 256KB.

## Phase completion status (2026-05-05)

- Phase 1 (skeleton + fixture): ✅ complete
- Phase 2 (original 3 detectors, TDD): ✅ complete
- Phase 3 (render + PDF + runlog): ✅ complete
- Phase 4 (SSH delivery wiring): ✅ complete — remote SQL queries, launchd deployed
- Phase 5 (skill page + RESOLVER): ✅ this file
- Phase 6 (7 dry-run cycles): 🔄 in progress — Day 1 of 2
- Phase 7 (revenue acceptance): ⏳ pending
- Camera Doctor V2 multi-tenant refactor: ✅ complete through Phase D; 46 Python tests pass locally (`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 -m pytest tenants/satory/tests -q`)

## Timeline

- **2026-05-14 openbrain** | OpenBrain Capture - 2026-05-05 Session start 2026-05-05 claude-pane1-sonnet-v1o… [[openbrain-33e6e6a1-4c4e-4066-842f-82bbd6419baa]]
- **2026-05-14** v1.2.2 — Added AP-5 after Satory Telegram proof mixed main `@nousAGaaSbot` factory health with separate APK camera-status bot output. VPS evidence showed `nous-isapi` active on `:9080`, `events.db` latest event `2026-04-05T22:08:05.856+05:00`, fresh camera poll `0/243`, reachability `ping 0/10`, and WireGuard endpoint/handshake missing. APK status output now must name those layers instead of stopping at "no data". No new LESSON (RULE ZERO).
- **2026-05-05** v1.2.1 — Added `tools/probe_tenant.py <tenant>` fitness contract. Satory real config returns exit 0 with SSH dial-tone; gov-pilot placeholder returns exit 2 network-unreachable. Tests cover Satory config with mocked SSH success and gov-pilot config with mocked SSH failure.
- **2026-05-05** v1.2.0 — Replaced AP-4 manual live-cutover doctrine with `tools/camera_doctor_live_cutover.sh <tenant>`. The script flips TOML + all tracked Camera Doctor plists atomically, reloads Air launchd, fails on live/dry-run inconsistency, verifies immediate `alert_sent=True`, and rolls local edits back on partial failure. Added pytest coverage with mocked SSH/SCP success + rollback.
- **2026-05-05** v1.1.1 — Corrected launchd doctrine after final verification: tracked repo job is `com.nous.satory-daily-brief` with no CLI `--dry-run`; Air also has legacy `com.nous.satory-camera-doctor` with `--dry-run`. Live cutover must inspect both labels.
- **2026-05-05** v1.1.0 — Camera Doctor V2 multi-tenant refactor shipped: normalized tenant config, tenant-agnostic `main.py`/`probe.py`/`render.py`, 3 new detector classes (wrong direction, offline >7d, mirror stale >24h), dry-run-only `gov-pilot` config, 46/46 tests passing. Satory launchd entrypoint preserved.
- **2026-05-05** v1.0.1 — AP-4 added: plist --dry-run hardcoding bug. Live-mode cutover requires both TOML + plist change. Plist name corrected (camera-doctor, not daily-brief). Go-live instructions updated.
- **2026-05-06** v1.0.0 — Phase 1-5 shipped. Phases 1-3 were already implemented from prior session. Phase 4 (SSH remote query instead of SCP, launchd deployed to Air) + Phase 5 (this skill + RESOLVER) shipped 2026-05-06. First live dry-run produced 3 findings: Mirrors Stopped (29 days), WireGuard down, 243/281 cameras offline. Dry-run cycles starting.

gbrain-timeline-ok: 2026-05-05 CLI fallback returned `{status: ok}` after MCP timeline transport closed.

## See also

- [[specs/PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1-2026-04-29]] — full implementation plan
- [[audits/AUDIT-060-camera-doctor-mvp-multi-reviewer-2026-04-29]] — multi-reviewer findings
- [[progress/CONSTRAINT-CHECK-2026-05-06]] — why this was prioritized over substrate-v2
