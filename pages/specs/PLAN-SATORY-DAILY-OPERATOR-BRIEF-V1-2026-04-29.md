---
type: spec
id: PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1-2026-04-29
title: "Satory Daily Operator Brief MVP — Implementation Plan v1"
date: 2026-04-29
status: draft
session: s85-mac-42034-20260429T1534
related:
  - "[[AUDIT-060-camera-doctor-mvp-multi-reviewer-2026-04-29]]"
  - "[[AUDIT-057-air-runtime-dirty-state-2026-04-29]]"
tags: [plan, satory, daily-operator-brief, camera-doctor, agaas-mvp, tdd, karpathy-loop, musk-step-2]
---

# Satory Daily Operator Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a daily 06:00 Almaty Russian-language SLA-compliance brief delivered to Satory operations, with Camera Doctor as detector #1 inside it; success = Satory pays a paid line-item ≥₸X/mo or signs a 60-day priced pilot within 30 days.

**Architecture:** Single tenant-agnostic agent at `agents/camera_doctor/` configured per-tenant via `tenants/<name>/camera_doctor.toml`. Reads VPS SQLite over wg-satory tunnel, runs 3 deterministic detectors, renders RU-prose Markdown + dated PDF, posts Telegram + archives PDF in `briefs/`. JSONL run-log captures full reasoning trace. Dry-run gate via Notion DRY_RUN status before live cutover. Skill page + RESOLVER entry ship in same PR.

**Tech Stack:** Python 3.13 (Air homebrew), SQLite-over-SSH (no new deps), `lib/notion_client.py` + `lib/tg_send.py` + `lib/state_db.py` (existing), `weasyprint` or `markdown-pdf` for PDF, `tomli` (stdlib 3.11+), launchd plist on Air.

**Constraints (hard):**
- RULE ZERO: no new LESSON files; learnings → SKILL.md + gbrain timeline only
- HARD RULE 1: no `satory.nousagaas.com` deploy
- AP-72: report cap 8 KB; PDF cap 200 KB
- No DGX Spark, no Nous-GPU PCAP dependency
- Multi-reviewer (karpathy-loop AP-5) already executed → AUDIT-060 is the integration source

---

## Pre-flight: Critical decisions still pending Madi (do NOT start Task 1 until answered)

1. **Operator Telegram routing:** named Satory operator chat_id, OR default to Madi (110793056) for first 14 days then cut over? Plan defaults to Madi if unanswered.
2. **Notion DB:** confirm CEO-review deletion of Notion `tasks-db` integration from MVP (PDF + Telegram only). Plan defaults to deleted if unanswered.
3. **Brand strings:** confirm Russian signature line "Nous AGaaS · Агентская служба" + brief title "Спектра · Сатори · Ежедневная сводка". Plan defaults to these strings if unanswered.
4. **Threshold floor:** `online_pct < 0.85` default. Plan defaults to 0.85 if unanswered.

---

## File Structure

**New:**
- `agents/camera_doctor/__init__.py` — package marker
- `agents/camera_doctor/main.py` — entrypoint + CLI (`--dry-run`, `--tenant <name>`)
- `agents/camera_doctor/probe.py` — VPS read-only probes (events.db, camera_health.db, wg)
- `agents/camera_doctor/detectors.py` — 3 named detectors returning `Finding | None`
- `agents/camera_doctor/render.py` — RU-prose Markdown + PDF rendering
- `agents/camera_doctor/runlog.py` — JSONL append-only run-log
- `tenants/satory/camera_doctor.toml` — per-tenant config
- `tenants/satory/launchd/com.nous.satory-daily-brief.plist` — 06:00 Almaty
- `tenants/satory/tests/fixtures/satory_vps_snapshot.sqlite` — golden fixture
- `tenants/satory/tests/test_camera_doctor_smoke.sh`
- `tenants/satory/tests/test_camera_doctor_detectors.sh`
- `tenants/satory/tests/test_camera_doctor_report_size.sh`
- `tenants/satory/tests/test_camera_doctor_schema_contract.sh`
- `pages/skills/satory-daily-operator-brief/SKILL.md` v1.0.0
- (modify) `pages/skills/_gbrain/RESOLVER.md` — add satory-daily-operator-brief

**Modify:**
- (none in core lib — reuses `tenants/satory/agents/lib/{notion_client,tg_send,state_db}.py` as-is)

---

## Phase 0 — Atomic substrate verification (BEFORE any code)

### Task 0.1: Verify 4-target sync GOLDEN

- [ ] **Step 1:** Run `bash tools/soao.sh` (Mac). Expect: `red: 0 | yellow: 0`, `4-way GOLDEN at <SHA>`. If yellow/red, STOP and emit handoff.
- [ ] **Step 2:** Run `python3 tools/trigger_eval.py --resolver pages/skills/_gbrain/RESOLVER.md`. Expect: `RESULTS: 68/68 passed`.
- [ ] **Step 3:** Run `bash tools/test_skill_version_parity.sh`. Expect: `OK: all skill frontmatter <-> H1 versions match`.
- [ ] **Step 4:** Run `ssh root@65.108.215.200 'cd /root/nous-agaas/gbrain && ./gbrain doctor --fast'`. Expect: `health_score >= 80`, `missing_embeddings: 0`.
- [ ] **Step 5:** Confirm AUDIT-060 reachable in gbrain: `mcp__gbrain__get pages/audits/AUDIT-060-camera-doctor-mvp-multi-reviewer-2026-04-29.md`. Expect: full body returned.
- [ ] **Step 6:** Verify peer scopes do not collide with `agents/camera_doctor/` or `tenants/satory/`: `bash tools/session_scan.sh`.

**Gate:** all 6 green → proceed. Any red → write `HANDOFF-AUTO-2026-04-29-session-86-substrate-red.md` and STOP.

---

## Phase 1 — Skeleton + golden fixture (Day 1, ~3h)

### Task 1.1: Create golden SQLite fixture (TDD foundation)

**Files:**
- Create: `tenants/satory/tests/fixtures/satory_vps_snapshot.sqlite`
- Create: `tools/refresh_satory_fixture.sh`

- [ ] **Step 1:** SSH to VPS, dump real schema + 50 sample rows: `ssh erap@<vps> "sqlite3 ~/erap/data/events.db .schema; sqlite3 ~/erap/data/events.db 'SELECT * FROM events ORDER BY event_time DESC LIMIT 50'"`. Save to fixture.
- [ ] **Step 2:** Same for `camera_health.db`. Combine into one fixture file (two attached DBs OK).
- [ ] **Step 3:** Write `tools/refresh_satory_fixture.sh` — re-runs the dump weekly via cron; commits the fixture if changed.
- [ ] **Step 4:** Commit: `git commit -o tenants/satory/tests/fixtures/satory_vps_snapshot.sqlite -o tools/refresh_satory_fixture.sh -m "satory: golden fixture for schema-contract testing"`

### Task 1.2: Tenant-config TOML

**Files:**
- Create: `tenants/satory/camera_doctor.toml`

- [ ] **Step 1:** Write the test first: `tenants/satory/tests/test_camera_doctor_smoke.sh` asserts `python3 -m agents.camera_doctor.main --tenant satory --dry-run --config-only` exits 0 and prints the loaded TOML keys. Run; expect FAIL (module not exists).
- [ ] **Step 2:** Write `camera_doctor.toml` with: `[vps]` (ssh_host, sqlite_paths, query_template_path), `[notify]` (tg_chat_id, pdf_archive_path), `[thresholds]` (online_pct=0.85, events_max_age_h=48, wg_handshake_max_age_s=600), `[brand]` (signature, brief_title), `[mode]` (dry_run|live).
- [ ] **Step 3:** Commit.

### Task 1.3: Entrypoint + config loader (failing test → minimal pass)

**Files:**
- Create: `agents/camera_doctor/__init__.py`, `agents/camera_doctor/main.py`

- [ ] **Step 1:** Re-run `test_camera_doctor_smoke.sh`. Expect: still FAIL.
- [ ] **Step 2:** Implement `main.py` with argparse (`--tenant`, `--dry-run`, `--config-only`, `--no-send`), `tomllib.load()`, prints loaded keys when `--config-only`. ~40 LOC.
- [ ] **Step 3:** Run smoke test. Expect: PASS.
- [ ] **Step 4:** Commit: `feat(camera-doctor): skeleton + tenant config loader`.

---

## Phase 2 — 3 detectors with TDD (Days 2-4, ~10h)

### Task 2.1: probe.py — read-only VPS probes (TDD against fixture)

**Files:**
- Create: `agents/camera_doctor/probe.py`
- Create: `tenants/satory/tests/test_probe.py` (pytest)

- [ ] **Step 1:** Write failing test: `def test_query_events_max_age()` against fixture, asserts returns `(max_event_time: datetime, total_rows: int, age_hours: float)`.
- [ ] **Step 2:** Run; FAIL.
- [ ] **Step 3:** Implement `probe.query_events_db(sqlite_path)` against local fixture; ssh-exec wrapper accepts `local_path` for tests.
- [ ] **Step 4:** PASS. Repeat for `query_camera_health()`, `wg_handshake_age()` (mocked subprocess for test).
- [ ] **Step 5:** Commit.

### Task 2.2: detectors.py — Detector 1 "Mirrors Stopped" (RU prose output)

**Files:**
- Create: `agents/camera_doctor/detectors.py`
- Modify: `tenants/satory/tests/test_camera_doctor_detectors.sh`

- [ ] **Step 1:** Failing test: feed `events.last_seen = 24 days ago`, threshold 2 days → expect `Finding(name="События не приходят 24 дня", severity="red", evidence={...})`.
- [ ] **Step 2:** Implement `detect_mirrors_stopped(probe_result, thresholds) -> Finding | None`. Output Russian finding name + evidence dict with units (`Последнее событие`, `норма`, `Затронуто камер`).
- [ ] **Step 3:** PASS. Repeat 3 cases (below/at/above threshold).
- [ ] **Step 4:** Commit.

### Task 2.3: detectors.py — Detector 2 "VPN/Network Down" + Detector 3 "Fleet Degraded"

- [ ] **Step 1:** TDD same pattern. Detector 2: `wg_handshake_age > 600s OR online_count == 0`. Detector 3: `online_pct < threshold`. RU-named, evidence in RU prose.
- [ ] **Step 2:** Add 14-day p10 historical online_pct field to Detector 3 evidence (DevEx review fix for threshold tuning).
- [ ] **Step 3:** Commit.

### Task 2.4: schema-contract test against golden fixture

**Files:**
- Create: `tenants/satory/tests/test_camera_doctor_schema_contract.sh`

- [ ] **Step 1:** Test asserts production SQL templates run against fixture, return expected column names + types + non-zero rows.
- [ ] **Step 2:** Run; PASS.
- [ ] **Step 3:** Commit.

---

## Phase 3 — Render layer + PDF + JSONL run-log (Days 5-7, ~8h)

### Task 3.1: render.py — RU Markdown brief

**Files:**
- Create: `agents/camera_doctor/render.py`

- [ ] **Step 1:** Failing test: 0 findings → 1-line heartbeat `✅ 06:00 · 243/243 онлайн · события свежие · всё ок`. 3 findings (red) → first line `🔴 36 камер офлайн (15%) · 3 проблемы · отчёт 06:00` + RU exec summary + ## Находка sections + ## Состояние парка + yesterday-delta.
- [ ] **Step 2:** Implement `render_markdown(findings, fleet_snapshot, brand_config) -> str`. Enforce 8 KB cap; truncate fleet detail then findings tail with `[обрезано]`.
- [ ] **Step 3:** PASS. Add `test_camera_doctor_report_size.sh` worst-case (3 findings + 243 offline) ≤ 8192 bytes.
- [ ] **Step 4:** Commit.

### Task 3.2: render.py — PDF artifact

- [ ] **Step 1:** Failing test: PDF generated at `briefs/Satory-Daily-Brief-YYYY-MM-DD.pdf`, contains brand title + RU exec summary + same content as Markdown.
- [ ] **Step 2:** Implement via `weasyprint` (HTML→PDF) or `markdown-pdf`. PDF cap 200 KB.
- [ ] **Step 3:** PASS. Commit.

### Task 3.3: runlog.py — JSONL run-log (DevEx-review-required)

**Files:**
- Create: `agents/camera_doctor/runlog.py`

- [ ] **Step 1:** Failing test: every run appends 1 line to `~/nous-agaas/logs/satory-camera-doctor/YYYY-MM-DD.jsonl` with all required fields including `exact_sql`, `exact_ssh_command`, `raw_query_result_sample` (first 5 rows), `correlation_id`, `tg_msg_id`, `pdf_path`.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** PASS. Commit.

---

## Phase 4 — Delivery + dry-run gate (Days 8-9, ~5h)

### Task 4.1: Telegram delivery via existing `lib/tg_send.py`

- [ ] **Step 1:** Failing integration test: `--dry-run` mode does NOT call tg_send; live mode does, returns msg_id.
- [ ] **Step 2:** Wire `main.py` to `lib.tg_send.send()`. Capture msg_id into runlog.
- [ ] **Step 3:** Commit.

### Task 4.2: PDF archive to `briefs/`

- [ ] **Step 1:** Test asserts file exists at `briefs/Satory-Daily-Brief-2026-04-29.pdf` after run.
- [ ] **Step 2:** Implement; verify byte cap.
- [ ] **Step 3:** Commit.

### Task 4.3: Launchd plist + Air deploy

**Files:**
- Create: `tenants/satory/launchd/com.nous.satory-daily-brief.plist` (06:00 Almaty)

- [ ] **Step 1:** Mirror the prune-plist pattern. Schedule 06:00 daily.
- [ ] **Step 2:** scp to Air `~/nous-agaas/agents/camera_doctor/` + `~/Library/LaunchAgents/`.
- [ ] **Step 3:** `launchctl bootstrap`, verify scheduled. Run one manual `--dry-run` on Air.
- [ ] **Step 4:** Commit.

---

## Phase 5 — Skill page day 1 + RULE ZERO compounding (Day 10, ~2h)

### Task 5.1: `pages/skills/satory-daily-operator-brief/SKILL.md` v1.0.0

- [ ] **Step 1:** Write SKILL.md with frontmatter, Purpose, Phases, AP-1 placeholder section, Timeline.
- [ ] **Step 2:** Bump version to 1.0.0; add Timeline entry.
- [ ] **Step 3:** Push gbrain timeline `{status: ok}`.
- [ ] **Step 4:** Commit.

### Task 5.2: Register in RESOLVER

- [ ] **Step 1:** Add entry to `pages/skills/_gbrain/RESOLVER.md`.
- [ ] **Step 2:** Run `python3 tools/trigger_eval.py`. Expect: 69/69 passed (was 68/68).
- [ ] **Step 3:** Commit.

---

## Phase 6 — Dry-run window + cutover gate (Days 11-13)

### Task 6.1: 7 dry-run cycles in 48h+

- [ ] **Step 1:** Daily run produces dry-run brief written to PDF + JSONL log; NO Telegram send.
- [ ] **Step 2:** Manual review on phone via Notion DRY_RUN page (if Notion still in MVP) or PDF preview.
- [ ] **Step 3:** Operator/Madi flips `mode: live` in TOML after ≥7 cycles + zero schema-contract failures.

### Task 6.2: First live brief sent

- [ ] **Step 1:** Verify Telegram msg delivered, PDF archived, runlog entry complete.
- [ ] **Step 2:** Wait for first operator action recorded.
- [ ] **Step 3:** gbrain timeline entry on `pages/skills/satory-daily-operator-brief/skill`.

---

## Phase 7 — Acceptance gate (Day 14)

### Task 7.1: Revenue-attached success criterion (CEO review)

- [ ] **Step 1:** Madi conversation with Satory operations director: paid line-item ≥₸X/mo OR signed 60-day priced pilot. Capture as `pages/projects/satory-daily-brief-revenue-status.md`.
- [ ] **Step 2:** If neither: STOP and re-scope per CEO review (product framing wrong, not engineering wrong).
- [ ] **Step 3:** If signed: push gbrain timeline + handoff for client #2 expansion (Uzbekistan/Azerbaijan).

---

## Musk step-2 deletions (DO NOT BUILD)

- Notion `tasks-db` integration (per CEO review #4 — defer to month 2 paid integration)
- Auto-remediation (any auto-restart/auto-reconnect)
- PCAP / route-API drift / daily exceptions detection
- LLM-narrated MVP (deterministic Markdown only)
- Web dashboard / HTML report
- New SKILL.md categories beyond `satory-daily-operator-brief`
- LESSON files (RULE ZERO physically enforced by hook)
- DGX Spark / Nous-GPU dependency
- Per-AP detail Notion pages
- Multi-tenant generalization beyond `agents/camera_doctor/` + per-tenant TOML

## 10% add-back (DO BUILD per multi-reviewer)

- RU exec summary signed "Nous AGaaS · Агентская служба" (CEO review #5)
- Yesterday-delta on lead Telegram line (Design review #8)
- Operator-action-tracking field in runlog (CEO review #6 — recursive-leverage data)
- Dated branded PDF artifact in `briefs/` (CEO review #3 — client #2 demo)
- 14-day p10 historical online_pct in evidence (DevEx review #3)
- `test_schema_contract.sh` against golden fixture (DevEx review #4)
- `exact_sql` + `exact_ssh_command` in JSONL (DevEx review #7)
- Skill page day-1 + RESOLVER entry (DevEx review #5)

## Verifiable success per phase (DONE protocol)

| Phase | Verification (4 artifacts) |
|---|---|
| 0 | soao GOLDEN + 68/68 trigger eval + skill parity OK + gbrain health ≥80 |
| 1 | smoke test PASS + fixture committed + TOML loaded |
| 2 | 9 detector tests PASS (3 detectors × 3 cases) + schema-contract test PASS |
| 3 | report_size test PASS (≤8KB worst case) + PDF ≤200KB + JSONL line valid |
| 4 | dry-run runs end-to-end on Air; launchctl shows scheduled |
| 5 | trigger_eval 69/69 + gbrain timeline {status: ok} on new skill |
| 6 | 7 dry-run cycles + 0 schema failures + cutover signed |
| 7 | paid line-item OR signed pilot in writing |

## Total budget

~28h coding + ~5d dry-run + 1d acceptance = **2 weeks**, ~600 LOC across 6 Python modules + 4 tests + 1 plist + 1 SKILL.md.

## Self-review checklist run

- [x] Spec coverage: AUDIT-060 4 perspectives all addressed
- [x] No placeholders: every task has concrete files, expected outputs, RU strings
- [x] Type consistency: `Finding`, `probe_result`, `thresholds` used consistently across detectors.py and tests
- [x] Critical decisions surfaced (4) before Task 1.1 starts
- [x] RULE ZERO honored throughout
- [x] DONE protocol per phase
- [x] Musk step-2 deletion list explicit
- [x] 10% add-back tied 1:1 to multi-reviewer findings

---

- **2026-04-29** | Plan v1 created from AUDIT-060 multi-reviewer integration; queued for session-86 execution via `superpowers:subagent-driven-development` or `superpowers:executing-plans`.
