---
type: spec
id: SPEC-SESSION-47-V1-2026-04-18
title: "Session 47 carryover burn-down — 13 atomic operations under Karpathy-primary"
tags: [spec, session-47, carryover-burn-down, karpathy, atomic, tan-pattern, 2026-04-18]
date: 2026-04-18
source_count: 0
status: draft
last_updated: 2026-04-18
related:
  - HANDOFF-AUTO-2026-04-18-session-46-POST-DEEP-AUDIT-compounding-gates
  - HANDOFF-AUTO-2026-04-18-session-46-air-tools
  - SPEC-AIR-TOOLS-MIGRATION-V1-2026-04-18
  - PLAN-AIR-TOOLS-MIGRATION-V1-2026-04-18
  - AMD-006-auto-memory-session-continuity-substrate
  - feedback_default_right_way
  - audit
  - infrastructure
  - mistake-to-skill
  - evidence-verification
  - gbrain-ops
---

# Session 47 Spec — Carryover Burn-down + Compounding Gates

## Context

Session 46 (GOD_PROMPT v1.0 + deep-audit + 3 compounding gates I/J/K) and session 46-B (Air tools migration AP-27 Phase A + D2-DRIFT) both closed with honest-handoff carryovers. Session 47 executes those carryovers atomically 1-by-1 under Karpathy-primary discipline: every operation compounds for future sessions, no shortcuts, stop-at-blocker if quality <100% with honest handoff to session 48.

## Opening State (verified 2026-04-18 pre-execution)

- **Vault 4-way HEAD:** `5497df10cff4ac8c4fb6976baa1ec2f22d8d1b18` (Mac = VPS wiki = VPS bare = Air wiki)
- **Hooks:** pre-commit `9a99bdda2f6977544e7d5f2d83e24c82` (Mac + Air + VPS + `tools/pre-commit-hook-tan-pattern.sh`) · pre-push `2e34402d3c57b2d879aa24fb0c5ba189` · pre-receive `b8cfb21ca1cc827b03b5f9de1b227742`
- **Skill parity:** `OK: all skill frontmatter <-> H1 versions match` (0 drifts across 20 skills)
- **Air launchd:** 17 `com.nous` services active
- **OpenClaw:** Up 2 days (healthy); **LiteLLM:** `"I'm alive!"`
- **APK-bot-polling:** active; token rotation completed 2026-04-18 11:45:44 UTC; Madi-verified via `/start` at 11:47:05
- **gbrain:** 1009 pages · 99.71% embed coverage (7 legacy missing) · brain_score 77 · 0 dead links
- **QMD:** 987 docs · needsEmbedding=0

## Already-Done (since session 46 POST-DEEP-AUDIT handoff)

- ✅ **APK_BOT_TOKEN rotation** — commit `dde42b40`; `secrets-management` v1.2 → v1.3 absorbed AP-10 (bot-owned WARNING/ERROR handlers that stringify httpx exceptions leak URL-with-token; amends AP-9)
- ✅ **AMD-006 auto-memory amendment** — commit `4ace6b6f`; `pages/laws/AMD-006-auto-memory-session-continuity-substrate.md`
- ✅ **Pre-commit RULE 4 SKILL.md version parity gate** — session 46 Phase I, infrastructure AP-43, hook MD5 `9a99bdda…`
- ✅ **Nightly context-injector regression launchd** — session 46 Phase K, `com.nous.context-injector-regression` 03:30 KZT daily

## Scope — 13 Atomic Operations

Sequenced by Karpathy-primary priority (compounding × unblocked first). Each row is a single atomic op with its own commit, its own quality gate, its own stop-or-continue decision point.

| # | ID | Bucket | Subject | Est | Compound |
|---|---|---|---|---|---|
| 1 | **O** | Audit | Opening deep audit (AP-10 7-point + AP-14 cross-cut) | 5m | baseline record |
| 2 | **M1** | Migration | `git mv satory_events_watcher.py` pages/systems/ → tools/ | 5m | dir-hygiene |
| 3 | **H1** | Housekeeping | 7 legacy gbrain missing embeddings → 100% | 10m | search quality + possible gbrain AP |
| 4 | **C1** | Compounding | 3rd Tan gate: SKILL.md MD5 citation ↔ reality hook | 45m | **NEW AP (infrastructure)** |
| 5 | **M2** | Migration | D4 FIRST lesson-absorption orphan + AP-39 5-test | 45m | **NEW AP (mistake-to-skill)** |
| 6 | **M3** | Migration | D2-CLEAN 6-script atomic loop (smallest-first) | 60-90m | vault/runtime parity |
| 7 | **S1** | Service | Aggregator cron wiring (apk-status-bot T13c) | 15m | /status live data |
| 8 | **C2** | Doctrine | MEMORY-ARCHITECTURE.md draft (AMD-006 Rule 4) | 30m | doctrine artifact |
| 9 | **M4** | Migration | D3-INLINE wiki-sync + litellm inline `bash -c` extraction | 30m | audit-visibility |
| 10 | **M5** | Migration | D5 wiki-to-runtime-rsync scope extension to `tools/` | 20m | rsync gap closure |
| 11 | **M6** | Migration | D4 OLD-BACKUPS 14-file batch (AP-39 applied) | 30m | cleanup + AP validation |
| 12 | **F1** | Coordination | BDL forensics internal-side rule-out + ext coord ask | 45m | investigation artifact |
| 13 | **Z** | Audit | Close deep audit + HANDOFF + 4-way sync | 20m | session receipt |

**Total estimate:** 5-6 hours active execution, 11-13 commits minimum, ≥2 new APs absorbed, ≥12 gbrain timeline entries pushed, zero new LESSON files.

## Per-Item Approach

### O — Opening deep audit

**AP-10 7-point:** skill parity scanner · 4-target hook MD5 · Air launchd count + names · OpenClaw `docker ps` health · LiteLLM `/health/liveliness` · gbrain `get_health` (pages, embed %, brain_score, dead_links, missing_embeddings) · LESSON filesystem count = 129 frozen · canonical SKILL.md count = 20 · stray SKILL.md outside `pages/skills/` = 0.

**AP-14 cross-cut (deep):** any frontmatter/H1 drift? any `tools/test_*.py` assertion staler than current spec threshold? gbrain chunk_index=0 for each bumped skill matches wiki H1? any 3+ session-old carryover rot?

**Output:** in-memory baseline record for close comparison (Z).

### M1 — satory_events_watcher.py relocation

**Current:** session 46-B D1 classified `pages/systems/air-runtime-scripts/satory_events_watcher.py` as WRONG-DIR.
**Target:** `tools/satory_events_watcher.py`.
**Method:** `git mv` → update `pages/systems/air-runtime-scripts/README.md` registry (remove moved entry) → verify Air `com.nous.satory-events-watcher.plist` script path + edit if needed → bootout+bootstrap → `launchctl list | grep satory-events-watcher` shows last exit 0 → 4-way sync → commit `[risk] REQ-046` named `fix: git mv satory_events_watcher.py air-runtime-scripts/ → tools/ (D2-WRONG-DIR)`.

### H1 — 7 legacy gbrain missing embeddings

**Method:**
1. `mcp__gbrain__get_health` with detail — get 7-page list
2. Per-page: `get_page` → inspect frontmatter + body → diagnose root cause (empty body? malformed frontmatter? binary content? sync-brain exclusion rule?)
3. Fix per root cause: either source-fix + `put_page` OR targeted `sync_brain full: true`
4. Verify `get_health` shows 100% embed coverage
5. If root-cause is systemic (e.g., sync-brain exclusion pattern), absorb as `gbrain-ops` AP

### C1 — SKILL.md MD5 citation ↔ reality hook (3rd Tan gate)

**Problem statement:** SKILL.md prose cites hook/tool MD5s (e.g., `pre-commit MD5 9a99bdda…`). If the cited file drifts without the SKILL.md citation updating, doctrine silently lies. Session-45 proposed this as the 3rd compounding gate after AP-35 (pre-push hook-parity) and AP-43 (pre-commit SKILL version parity).

**Design:**
- Pre-push scans staged SKILL.md changes for `[a-f0-9]{32}` hex tokens adjacent to `MD5` or `md5` keyword
- For each citation, extract nearest file path in surrounding context (within same paragraph)
- Compute current file MD5; compare to citation
- On mismatch → REJECT with remediation message (list each drifted citation + path + expected vs actual)

**Artefacts:**
- `tools/test_skill_md5_citations.sh` — standalone scanner (exit 0 clean / 2 drift); usable outside hook
- `.git/hooks/pre-push` — new rule invokes scanner (sibling of AP-35 parity check)
- `tools/pre-push-hook-tan-pattern.sh` — vault-synced backup
- 3-wiki deploy (Mac + Air + VPS)

**Live test:**
- REJECT path: edit hook MD5 citation in `pages/skills/infrastructure/SKILL.md` to drift; `git push` → REJECT with readable message
- ACCEPT path: restore → `git push` → ACCEPT
- ESCAPE hatch: `git push --no-verify` works in emergency

**Absorb:** `infrastructure` v2.34 → **v2.35** · AP-44 (MD5-citation mechanical gate, 3rd Tan compounding gate). gbrain timeline entry pushed.

### M2 — D4 FIRST lesson-absorption orphan + AP-39 5-test

**Context:** session 46-B designed AP-39 proof-of-deadness 5-test gate in SPEC §3 but did NOT absorb because no real D4 evidence. Session 47 executes first D4.

**Target:** DEAD-CANDIDATE script named in `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` (1 item). Name resolved at execution time.

**5-test proof-of-deadness (candidate AP-39):**
1. `grep -r "<script-name>" ~/Documents/Projects/Nous\ AGaaS/Nous` — no wiki-code references
2. `ssh air "launchctl list | grep -i <script-name>"` — no launchd usage
3. `ssh root@vps "crontab -l"` + `ssh air "crontab -l"` — no cron usage
4. `grep -r "<script-name>" pages/` — no doc reference
5. `git log --all --follow -- <path>` — last-touch > 60 days

All 5 PASS → delete → observe 5-min live — verify no launchd-log errors, no user-visible breakage → commit with evidence.

**Absorb:** `mistake-to-skill` v1.8 → **v1.9** · AP-39 (proof-of-deadness 5-test gate, real evidence from first execution). gbrain timeline entry pushed.

### M3 — D2-CLEAN 6-script atomic loop

**6 scripts classified MIGRATE-CLEAN** in session 46-B D1 (re-resolve exact list from `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md`). Ordered smallest-first; session_rotate.sh (~1 KB) known smallest.

**Per-script atomic loop:**
1. Read Air copy (authoritative per AP-40)
2. `scp air:~/nous-agaas/tools/<script> vault/tools/<script>`
3. Verify MD5 matches Air source
4. Register in `tools/wiki-to-runtime-rsync.sh` scope (after M5 extends it)
5. Update `pages/systems/air-runtime-scripts/README.md` (authoritative registry) with script entry + path
6. Commit `[risk] REQ-046` per script
7. 4-way sync probe post-commit
8. Next script

**`backup.sh` on Desktop (LAW-005 violation):** extra verification — confirm Desktop is not backup destination elsewhere + move to vault.

### S1 — Aggregator cron wiring (apk-status-bot T13c)

**VPS deploy (coordinate user=deploy):**
```
*/10 * * * * deploy cd /opt/nous-agaas/apk-status-bot && .venv/bin/python -m apk_status_bot.aggregator
```

**Verify chain:**
1. `crontab -l -u deploy` shows entry
2. Within 10 min: `journalctl | grep aggregator` shows first run
3. DB probe: `sqlite3 /opt/nous-agaas/erap/data/apk_health.db "SELECT COUNT(*) FROM apk_health_current"` — non-zero
4. Telegram bot `/status` returns live data (Madi-visible probe)

If records=0 due to NIT VPN blocker per session 46-B honest-note, document and handoff the probe-wiring as done without data.

### C2 — MEMORY-ARCHITECTURE.md draft

**Purpose:** per AMD-006 Rule 4 — separate compiled view of architecture ground truth. Stable reference, ~80 lines, not a truncation of MEMORY.md.

**Content:**
- Architecture quick-reference table (VPS/Air/Mac topology — extracted from current MEMORY.md + CLAUDE.md §Architecture)
- HARD RULES summary
- Skill-layer runtime paths (container-internal `/opt/nous-agaas/` vs host-side `/Users/madia/nous-agaas/` per session 45 AP-10 pt2 clarification)
- Symlink semantics (LAW-005)
- Master index: skill/law/AMD IDs → paths

**Location:** `pages/progress/claude-memory/MEMORY-ARCHITECTURE.md` (same dir as MEMORY.md for symlink co-location).

**Register:** append pointer line to MEMORY.md "Memory Files Index" section.

### M4 — D3-INLINE extraction (wiki-sync + litellm plists)

**2 launchd plists** with inline `bash -c` scripts. Per plist:
1. Extract inline bash to vault `tools/<service>-launch.sh`
2. Rewrite plist `ProgramArguments` to absolute path
3. `scp` both to Air runtime
4. `launchctl bootout` + `launchctl bootstrap`
5. `launchctl kickstart -k` to verify
6. Tail log — expect same behavior as before
7. Commit

### M5 — D5 rsync scope extension

**Current:** `tools/wiki-to-runtime-rsync.sh` covers `pages/skills/` only. Session 46 Phase K surfaced this gap.

**Method:**
1. Extend script: add `tools/` to rsync source paths (with exclude list for `.bak-*`, `.v1-archived-*`)
2. Bump infrastructure AP-29 (or add new AP)
3. Live test: edit a `tools/` script in vault → wait rsync cycle (or kickstart) → verify Air copy updated
4. Verify MD5 parity post-rsync
5. Commit + skill absorption

### M6 — D4 OLD-BACKUPS 14-file batch

**14 `.bak-pre-path-fix` files** on Air. Apply AP-39 5-test (validated in M2).

**Batch eligibility check:** if all 14 share (a) same suffix `.bak-pre-path-fix`, (b) last-touch in same 7-day window, (c) no references in vault or launchd → single batch delete. Else per-file 5-test.

**Evidence log:** append to `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` with per-file pass/fail.

### F1 — BDL forensics internal-side rule-out

**Per session 42 FINAL Addendum C** (5-session-old carryover).

**VPS-side probes:**
1. `iptables -L -n -v` filter for BDL IPs — any drops?
2. `ip route` + `ip rule` — BDL subnet routing
3. `mtr -c 20 -r <BDL-camera-IP>` — where drops happen
4. `tcpdump -i any -nn host <BDL-IP> -c 100` — 30-60 sec egress sample
5. Tailscale/NIT-VPN tunnel status (`tailscale status`, relevant `ip link`)

**Deliverable:** `pages/audits/AUDIT-BDL-FORENSICS-2026-04-18.md`
- Per-probe evidence
- Candidate cause code: `VPN_TUNNEL_DOWN` / `BDL_FIREWALL_BLOCK` / `CAMERAS_POWERED_OFF` / `NOUS_ROUTE_MISSING` / `NOUS_FIREWALL_BLOCK`
- External coordination ask for Madi to forward:
  - Daniyar: NIT VPN uptime since 2026-04-05
  - BDL ops: firewall-log request for our egress IP since 2026-04-05
  - Papa Smatay: physical verification of 2-3 APKs (power + network LED)

If first probe determines cause locally → no external ask needed → cause code + fix plan only.

### Z — Close deep audit + handoff

**Re-run opening probes + delta:**
- 4-way HEAD parity
- Hook MD5 4-target (expect change on pre-push if C1 shipped; all others unchanged)
- Skill parity scanner clean
- Air launchd count (≥17)
- LESSON count (expect 129; RULE ZERO proof)
- gbrain health delta (expect +12 timeline entries at minimum)

**Handoff file:** `pages/progress/HANDOFF-AUTO-2026-04-18-session-47.md`
- 13-op ledger: status per op (DONE / HANDOFF with reason / BLOCKED)
- APs absorbed list with skill version + cross-refs
- gbrain timeline entries pushed list
- Commits named
- Remaining carryovers (if any) with concrete first-step each
- Karpathy scorecard numbers

## Quality Gates (per-item, mandatory)

1. Root-cause documented (if fix)
2. Live-probe test (not just code-diff; exit=0 or equivalent positive signal)
3. Skill absorption: SKILL.md (frontmatter + H1 + Timeline — AP-11 3-edit ritual) + gbrain `add_timeline_entry`
4. 4-target MD5 parity verify (for files that are replicated)
5. Atomic commit `[risk] REQ-046`
6. Post-commit `git status` clean + 4-way HEAD parity probe

## Cross-cut Rules (apply to every atomic op)

- **RULE ZERO:** zero new LESSON files; every learning → SKILL.md + gbrain timeline
- **AP-34 cadence probe:** before any destructive op (delete, rm, git mv, launchctl bootout), probe parallel-session commit cadence (5-min window); wait + re-probe if hot
- **AP-26 MVP=Running Service:** "deployed plist" ≠ "done"; live kickstart with exit=0 required
- **AP-14 deep audit doctrine:** Z close cross-cuts beyond 7-point AP-10 (stale-assertion scan + gbrain-reality parity)
- **Karpathy-primary:** compounding path always, shortcut never; never present shortcut as equal option; honest handoff if blocked
- **LAW-005 vault-master:** Obsidian is truth (except AP-40 `tools/` Air-authoritative host-specific paths)
- **AP-11 SKILL version 3-edit ritual:** every SKILL.md bump edits frontmatter + H1 + Timeline together (pre-commit RULE 4 enforces)
- **AP-41 gbrain zero-duplicate rule:** before pushing timeline entry on another session's behalf, `get_timeline` to check if already pushed

## Stop Conditions (trigger honest handoff mid-session)

- Any gate fails and root-cause not resolvable in <30 min → handoff that item with evidence
- AP-34 cadence hot 3+ re-probes (parallel session hammering same subsystem) → defer that item
- External dependency (network, Madi action, third-party) unresolvable → partial done + coordination-ask documented in handoff

## Close Deliverables

- `HANDOFF-AUTO-2026-04-18-session-47.md` (13-op ledger + evidence + remaining carryovers)
- 4-way vault HEAD parity proof (Mac = VPS wiki = VPS bare = Air)
- Skill-parity scanner exit=0
- Hook MD5 4-target parity (updated after C1 pre-push bump)
- gbrain health delta from O baseline
- LESSON count still 129
- APs absorbed list + gbrain timeline entries list
- Karpathy scorecard: ≥2 APs · ≥10 gbrain · ≥1 mechanical gate · zero rot

## Success Metric (Karpathy scorecard)

- ✅ ≥2 new APs absorbed (C1 + M2 + possibly M5 + possibly H1)
- ✅ ≥10 gbrain timeline entries pushed
- ✅ ≥1 new mechanical gate live (C1 pre-push MD5 citation gate)
- ✅ Zero rot smuggled (no comments-without-code, no files-without-sync, no claims-without-probe)
- ✅ Every atomic op ends in commit + sync + absorption, OR in honest handoff

## See Also

- [[HANDOFF-AUTO-2026-04-18-session-46-POST-DEEP-AUDIT-compounding-gates]]
- [[HANDOFF-AUTO-2026-04-18-session-46-air-tools]]
- [[SPEC-AIR-TOOLS-MIGRATION-V1-2026-04-18]]
- [[PLAN-AIR-TOOLS-MIGRATION-V1-2026-04-18]]
- [[AUDIT-AIR-TOOLS-INVENTORY-2026-04-18]]
- [[AMD-006-auto-memory-session-continuity-substrate]]
- [[feedback_default_right_way]]
- [[audit]] — AP-10 + AP-14
- [[infrastructure]] — AP-29/34/35/37/38/40/41/43
- [[mistake-to-skill]] — AP-11; AP-39 (this session)
- [[evidence-verification]] — AP-11
- [[gbrain-ops]]
- [[secrets-management]] — AP-10

## Timeline

- **2026-04-18** | Session 47 spec drafted after Madi's Karpathy-primary + atomic-100%-or-handoff directive. Scope: 13 atomic operations covering M1-M6 migration carryovers + C1-C2 compounding gates + S1 service + F1 coordination + H1 housekeeping + O/Z opening+closing audits. Target ≥2 new APs, ≥10 gbrain entries, RULE ZERO upheld. Opening state verified 4-way `5497df10`; all pre-session gates green.
