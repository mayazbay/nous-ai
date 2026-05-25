---
id: SPEC-AIR-TOOLS-MIGRATION-V1-2026-04-18
type: spec
title: "Air tools/ migration v1 — close AP-27 (8-session carryover), convert untracked Air automation into vault-sourced + test-harnessed scripts, with delete-with-evidence policy for proven-dead launchd jobs"
date: 2026-04-18
status: reviewed
last_updated: 2026-04-18
owner: claude-code-mac (Opus 4.7 1M) + Madi Ayazbay
tags: [spec, air-tools-migration, ap-27, ap-36, ap-37-candidate, infrastructure, rule-zero, karpathy-pattern, tan-pattern, session-46, compounding]
source_count: 6
related:
  - HANDOFF-AUTO-2026-04-17-session-45-atomic-audit
  - HANDOFF-AUTO-2026-04-17-session-44-atomic-audit
  - SPEC-SECRETS-MANIFEST-V1-2026-04-17
  - audit
  - infrastructure
  - secrets-management
  - evidence-verification
  - CLAUDE.md
---

# Air `tools/` Migration v1 — Close AP-27 + Phase-A Hygiene First

**Scope:** Session 46 design for the A→D workflow Madi approved 2026-04-18 morning. Phase A (hygiene, ~90 min): push queued gbrain timeline, write AP-36 test harness, rotate APK_BOT_TOKEN, wire aggregator cron. Phase D (compounding, ~2.5 hr): inventory → classify → migrate → test → sync → audit every launchd-registered Air automation script, absorbing learnings into `infrastructure` skill (no new LESSON files, RULE ZERO).

**Driver:** Madi's session-46 directive *"plan everything, execute 1-by-1 atomically, 100% or handoff, find root causes, save evolving skills, use gbrain + obsidian + Karpathy pattern."* After reviewing 4 options (A hygiene / B BDL forensics / C APK bot T26-T33 / D AP-27 migration), Madi picked the Karpathy+Tan+Finn answer: **pay down 8-session-old debt with mechanical enforcement**, not ship features or investigate symptoms.

**Author context:** AP-27 has been deferred since session 37 (first surfaced when Air `~/nous-agaas/tools/` was discovered untracked in git). Every session carrying it forward accumulates risk: more untracked scripts drift, more launchd jobs depend on unaudited paths, more bus-factor concentration. Session 45 E-phase shipped AP-35 (pre-push parity) + AP-36 (server hook sibling-test requirement) which are now the **levers** that make this migration safe: every script gets a sibling test harness, every drift gets mechanically blocked at push time.

## 0. Goal + non-goals

### Goal

By session 46 close: every launchd-registered Nous script on Air is in **exactly one** of these states, with evidence:

1. **VAULT-SOURCED + TESTED** — source-of-truth is vault `tools/<name>.sh` (committed), sibling `tools/test_<name>.sh` exists and passes, Air copy MD5-matches vault, wiki-to-runtime-rsync keeps them in sync, plist references either vault path directly or the rsync'd Air copy (documented).
2. **PROVEN DEAD + DELETED** — script passed all 5 proof-of-deadness tests (run history, reverse call-graph, doctrine search, Madi confirmation, restoration recipe), unloaded + rm'd, audit entry records the deletion.
3. **HONEST HANDOFF** — script was classified but not yet migrated this session (time-box protection); remaining work carried to session 47 with exact bucket + next concrete step.

### Non-goals (explicitly deferred)

- Not the APK bot T26-T33 features (sentinel / digest / self-heal / full-suite gate) — option C, deferred.
- Not BDL camera-reachability forensics — option B, deferred to session 47 or later.
- Not the 3rd compounding hook (CLAUDE.md/SKILL.md MD5 ↔ reality) — noted in session-45 close, deferred.
- Not the Mac-primary gbrain/QMD migration (Spec B from session 38) — separate future spec.
- Not secret rotation other than APK_BOT_TOKEN — uses `secrets-management` skill v1.2 pattern; other secrets follow when their services are next touched.

## 1. Locked decisions

| # | Decision | Value | Rationale |
|---|---|---|---|
| 1 | A precedes D, no shortcut | A1 → A2 → A3 → A4 → D0 → D7, atomic | AP-36 test harness (A2) is the lever for D2; token rotation (A3) is acute security; gbrain entry (A1) closes session-45 MCP-disconnect honesty debt. |
| 2 | "Migrated" definition | 4-condition strong bar: (a) vault is SoT, (b) sibling test exists + passes, (c) Air MD5 = vault MD5, (d) plist references documented | Rejects weak interpretations like "rsync'd but untested" or "in vault but launchd still points at Air-local copy." |
| 3 | Dead-code default policy | **DELETE WITH EVIDENCE** this session (not defer) | Karpathy: lean substrate. Tan: debt payoff, not roll-over. Finn: close the loop. Defer = rot compounds. |
| 4 | Dead-code proof gate | 5 evidence tests; ALL must pass | Protects against overconfident deletion. See §3. |
| 5 | 100% gate vs completion pressure | Better 60% migrated + 100% audited + honest handoff than 90% migrated with unclear state | Madi's explicit "100% or handoff" rule; inherited from session 45's self-discipline. |
| 6 | Time ceiling | ≈4 hours total (A ≈90min + D ≈2.5hr + absorb+handoff ≈30min) | If D2 bucket > time budget, migrate safest N scripts, honest handoff for the rest. |
| 7 | Test harness pattern | Sibling `tools/test_<name>.sh`, AP-36 style: reject-path + accept-path scenarios with explicit PASS/FAIL echo + exit code | Already proven for `pre-push-sanity.sh` + `test_pre_push_sanity.sh`. Reuse this pattern. |
| 8 | RULE ZERO | Every learning → SKILL.md (likely `infrastructure` AP-39 / AP-40) + gbrain timeline entry. **Zero new LESSON files.** Pre-commit hook enforces. | Session 35 onward; RULE ZERO. |
| 9 | Runtime sync scope | `wiki-to-runtime-rsync` (Air launchd) currently watches `pages/skills/`; extend to `tools/` so vault drift auto-propagates | Prevents the next AP-29-style scope gap. |
| 10 | Audit page location | `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` | Wiki schema; audit-NNN pattern or descriptive slug both acceptable per existing `pages/audits/` conventions. |
| 11 | Close-audit probe added to `audit` skill | New AP-14 candidate: "For every MIGRATE-CLEAN-SOURCED script, assert Air copy MD5 = vault copy MD5 at session open + close" | Compounds: future sessions catch drift mechanically, no vibes. |
| 12 | Parallel-session guard | Run AP-34 cadence probe on any shared repo before destructive ops in D | Already done at session open (0 commits); re-run before D2 deletions. |

## 2. Components + phase breakdown

### Phase A — hygiene (4 atomic steps, ~90 min)

#### A0 — Re-probe parallel-session cadence on vault (AP-34, ≤2 min)

- **Why new:** discovered during self-review that parallel Claude Code session 46 (GOD_PROMPT v1.0 completion thread) committed `9607a00e` at 2026-04-18 10:27:02 — a different subsystem (context_injector_v2 feature-flag A/B), but same vault. Session-45 AP-34 rule requires re-probe before any destructive op.
- **Probe:** `cd <vault> && git fetch vps main --quiet && git log --since='5 minutes ago' vps/main --oneline | wc -l`
- **Proceed if:** commit count is 0 AND last commit age ≥ 5 min (cache the parallel session's close state).
- **Defer if:** any commits in last 5 min — wait 5 more min, re-probe. Maximum 3 defer cycles (15 min); if still hot, extend plan + check with Madi.

#### A1 — push queued gbrain timeline entries (≤10 min)

- **Target 1:** `pages/skills/infrastructure/skill`
  - **Entry (v2.31):** `v2.30 → v2.31 adds AP-35 (pre-push hook parity gate — Mac + 3-wiki live-hook MD5 must match vault tools/ source; codifies session-45 GAP 1) + AP-36 (every new server hook requires sibling tools/test_<name>.sh; codifies session-45 GAP 2). Session 45 E-phase; gbrain entry deferred due to MCP disconnect; pushed session 46 A1.`
  - **Entry (v2.32):** `v2.31 → v2.32 adds AP-37 (design caps ≤ spec-named thresholds, with wrapper-bytes included; first hit context_injector_v2 MAX_CONTEXT_CHARS_V2=12_000 vs G4 8_192 → tuned to 7_500) + AP-38 (feature-flagged cutover MUST ship with deploy-time A/B probe; 1495 v2 runs flowed before Round-1 probe measured the gap). GOD_PROMPT v1.0 P7 T27+T28 completion. Parallel session-46 work; gbrain timeline not pushed with skill bump; pushed by Air-tools-migration thread at A1.` — **CREDIT TO PARALLEL SESSION; push on their behalf for gbrain honesty.**
- **Target 2:** `pages/skills/evidence-verification/skill`
  - **Entry (v1.6):** `v1.5 → v1.6 adds AP-11 (per the parallel session's commit message). Need to read SKILL.md to verify exact AP-11 summary before pushing.`
- **Verify:** `mcp__gbrain__get_timeline` on both slugs shows all 3 new entries within 60s.

#### A2 — write `tools/test_pre_receive_lesson_count_guard.sh` (≈30 min)

- **Purpose:** close session-45 AP-36 self-violation (AP-36 was written demanding sibling tests for new server hooks; pre-receive was installed without one).
- **Pattern:** mirror `tools/test_pre_push_sanity.sh` 5-scenario structure but specialized to server pre-receive semantics:
  1. **ACCEPT scenario 1:** push that doesn't add LESSON file → pre-receive exits 0.
  2. **REJECT scenario 1:** push that adds LESSON-130 via `git add` → pre-receive exits non-zero, stderr contains "LESSON count > 129".
  3. **REJECT scenario 2:** push that adds LESSON-130 via rename from outside `pages/lessons/individual/` → pre-receive exits non-zero.
  4. **ACCEPT scenario 2:** push adds LESSON-130 BUT commit message has `LESSON-EXEMPT` → pre-receive exits 0.
  5. **ACCEPT scenario 3:** push edits existing LESSON-042 (no count change) → pre-receive exits 0.
- **Infra:** use temp git repo (`mktemp -d`) as fake bare, install pre-receive there, drive pushes from a clone. Clean up on exit.
- **Verify:** all 5 scenarios PASS; script is idempotent and self-cleaning.
- **Commit:** `tools/test_pre_receive_lesson_count_guard.sh` to vault; `infrastructure` skill gets a Timeline line noting AP-36 self-violation closed.

#### A3 — rotate APK_BOT_TOKEN (≈10 min)

- **Why:** token leaked into VPS journald 2× on 2026-04-17 18:19:47 + 18:20:17 before session-42 `1a1f071` httpx silence fix. Session 45 queued rotation; session 46 executes.
- **Steps:**
  1. BotFather DM: `/revoke` → generate new token for `@NousAPKstatusbot`.
  2. Mac Keychain: `tools/secrets-keychain-add.swift nous-agaas/APK_BOT_TOKEN <new-token> --icloud no` (local-only per `secrets-management` v1.2 AP-8).
  3. Deploy: `tools/secrets-deploy.sh apk-status-bot vps` (pipe-never-variable).
  4. Restart: `ssh root@65.108.215.200 "systemctl restart apk-bot-polling"`.
  5. Smoke: Madi taps `/start` in DM → bot replies with welcome + keyboard.
  6. Journald cleanup: `ssh root@65.108.215.200 "journalctl --vacuum-time=1h --unit=apk-bot-polling.service"` — only the pre-fix historical lines get purged; everything post-`1a1f071` is clean.
- **Verify:** old token returns HTTP 401 on direct API call; new token returns 200 with same bot username; `/start` replies; no token-looking string in post-rotation `journalctl -u apk-bot-polling --since '5 min ago'`.

#### A4 — wire aggregator cron (≈15 min)

- **Why:** `apk_health_current` table stays empty until the aggregator runs on a schedule. Bot shows "Нет данных" (honest per session-42 AP-7), but we can make it honest AND populated.
- **Location:** VPS crontab, user `deploy`.
- **Line:** `*/10 * * * * cd /opt/nous-agaas/apk-status-bot && .venv/bin/python -m apk_status_bot.aggregator >> /var/log/apk-bot/aggregator.log 2>&1`
- **Prereq check:** `/var/log/apk-bot/` exists + writable by `deploy`; create if not.
- **Verify:** wait 1 cycle (≤10 min); `sqlite3 /opt/nous-agaas/erap/data/apk_health.db "SELECT COUNT(*) FROM apk_health_current"` > 0; Madi taps 📊 Статус button → live count replaces "Нет данных".

### Phase D — Air `tools/` migration (~2.5 hr)

#### D0 — inventory (≤30 min, read-only)

- **Tools used:** `ssh air "launchctl list | grep com.nous"`; for each label: `launchctl print gui/$(id -u)/<label>`; `cat <plist>`; `ls -la <ProgramArguments[0]>`; `md5 <script>`; `stat -f '%m' <script>` (mtime); `git ls-files <script>` (tracked-in-vault test).
- **Output:** `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` — a table with columns:
  - `label` (com.nous.xxx)
  - `plist_path` (~/Library/LaunchAgents/...)
  - `program_args` (script + args)
  - `script_path` (absolute, host-side)
  - `script_md5`
  - `script_mtime`
  - `tracked_in_vault_tools` (yes/no)
  - `tracked_in_vault_other` (yes/no + path if yes)
  - `calls_other_scripts` (list)
  - `reads_secrets` (yes/no)
  - `last_run_from_launchd` (from journal or log)
  - `provisional_bucket` (VAULT-ALREADY / MIGRATE-CLEAN / MIGRATE-WITH-SECRETS / DEAD-CODE-CANDIDATE / UNKNOWN)
- **Invariant:** **zero mutations on Air during D0.** Read-only inspection only. Evidence-verification AP-6 compliance.

#### D1 — classify (≤15 min, assigns canonical bucket)

- For each row in D0 inventory: apply deterministic rules and assign the canonical bucket.
  - **VAULT-ALREADY** if `tracked_in_vault_tools == yes` and Air copy MD5 matches vault MD5.
  - **MIGRATE-CLEAN** if (a) not in vault, (b) no secrets read, (c) reverse call-graph has no external callers (other than its own plist).
  - **MIGRATE-WITH-SECRETS** if (a) not in vault or in vault but Air-specific env needed, (b) reads tokens/paths that must stay local.
  - **DEAD-CODE-CANDIDATE** if all 5 §3 tests pass; if any fails, demote to MIGRATE-CLEAN or MIGRATE-WITH-SECRETS by content.
  - **UNKNOWN** only if evidence is contradictory or insufficient — treated as HOLD, never migrated or deleted; flagged in audit for next session.
- **Update audit table** with final bucket + rationale.

#### D2 — migrate MIGRATE-CLEAN bucket, atomic one-by-one (~60 min, time-boxed)

- **For each script, 100% sub-gate:**
  1. Read Air script; copy to vault `tools/<name>.sh`.
  2. Write sibling `tools/test_<name>.sh` (AP-36 pattern): minimum PASS-path test (script runs with `--dry-run` or equivalent and exits 0); regression tests added where script has branching logic.
  3. Run `bash tools/test_<name>.sh` locally — must print `✅ ALL N SCENARIOS PASS` and exit 0.
  4. Commit vault changes: `tools/<name>.sh` + `tools/test_<name>.sh` in one commit with REQ-xxx tag.
  5. rsync to Air: `rsync -av "/Users/madia/.../tools/<name>.sh" air:~/nous-agaas/tools/`
  6. Verify: `ssh air "md5 ~/nous-agaas/tools/<name>.sh"` == vault md5.
  7. plist unchanged (points at `~/nous-agaas/tools/<name>.sh` already on Air).
  8. Watch next scheduled run in `launchctl print` → exit code 0.
- **Stop gate:** if any sub-step fails for script N → stop the bucket, do not touch N+1; honest handoff in audit.

#### D3 — migrate MIGRATE-WITH-SECRETS bucket (time permitting)

- Same 8-step sub-gate as D2 PLUS:
  - Secret extracted into `~/nous-agaas/config/<name>.env` (Air-local, Keychain-sourced via `tools/secrets-deploy.sh`).
  - Script reads secret via `source config/<name>.env`, never inline.
  - Sibling test mocks the secret (e.g., `APK_BOT_TOKEN=dummy-for-test bash tools/<name>.sh --dry-run`).
  - New row added to `pages/secrets-manifest.md`.
- If time-limit hits mid-bucket: stop, honest handoff, do not half-migrate.

#### D4 — DEAD-CODE resolution (delete-with-evidence, see §3 gate)

- For each DEAD-CODE-CANDIDATE that passes all 5 proof tests:
  1. Record restoration recipe in audit: `git show <sha>:<plist-or-script-path> > /tmp/restore && launchctl load <plist>`.
  2. `ssh air "launchctl bootout gui/\$(id -u)/<label>"` (unload).
  3. `ssh air "rm <plist> <script>"`.
  4. Audit entry: script name, 5 evidence blocks, restoration recipe, deletion ISO timestamp.
  5. gbrain timeline entry on the audit page: `Deleted <label> (proof: <summary>); restoration recipe preserved.`
- If any of the 5 tests fails → demote to MIGRATE-CLEAN/WITH-SECRETS; do NOT delete.

#### D5 — runtime sync hardening (≈15 min)

- Locate `wiki-to-runtime-rsync` launchd job (likely `com.nous.wiki-to-runtime-rsync`).
- Read its ProgramArguments + script; identify rsync source filter.
- Extend filter to include vault `tools/` (currently only `pages/skills/` per AP-29 scope-gap fix).
- Test: touch a file in vault `tools/`; wait for next rsync cycle; verify Air `~/nous-agaas/tools/` picked it up.
- **NOTE:** this itself becomes a MIGRATE step for the rsync script — if it's not already vault-sourced, fix it using D2/D3 procedure. If it IS already vault-sourced (likely, since AP-29 fixed it), edit in vault + rsync + observe next cycle.

#### D6 — absorb learnings (~15 min)

- Whatever surprises came up in D0-D5 (plist path gotchas, launchd env var bugs, rsync races, proof-of-deadness false positives), absorb into `infrastructure` SKILL.md as new AP-N:
  - **AP-39 candidate** *(shifted from AP-37 — parallel session took 37/38 for GOD_PROMPT design-caps + A/B-probe rules, committed `9607a00e` at 10:27:02)*: "Proof-of-deadness 5-test gate — delete-with-evidence, never defer; document restoration recipe per deletion; session 46 Air tools migration pattern."
  - **AP-40 candidate (if applicable):** whatever the biggest concrete surprise from D0–D5 was.
- **H1 drift fix (piggyback):** `pages/skills/infrastructure/SKILL.md` line ~17 currently says `# infrastructure v2.29.0`; frontmatter is `version: 2.32.0`. Bump H1 to match. Same drift likely in other skills — quick sweep during D6.
- Add close-audit probe to `audit` skill: "Air `~/nous-agaas/tools/<name>.sh` MD5 must equal vault `tools/<name>.sh` MD5 for every MIGRATE-CLEAN-sourced script" (candidate AP-14).
- Push gbrain timeline entries for each skill bump.

#### D7 — close audit + handoff (~15 min)

- Run AP-10 7-point close audit v1.12 (host-side paths per AP-13).
- Update `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` with final state table: every script labeled with final bucket + migration status (MIGRATED / DELETED / HANDOFF).
- Write `pages/progress/HANDOFF-AUTO-2026-04-18-session-46-air-tools.md` — standard handoff format with:
  - TL;DR
  - Phase-by-phase result table
  - Remaining buckets with exact "next session first step" per script
  - Sync state (4-way vault HEAD, 4-target MD5, gbrain stats, QMD docs)
  - Skill versions changed
  - gbrain timeline entries pushed
  - Rule compliance checklist (RULE ZERO, AP-10, AP-12, AP-13, AP-34, AP-36, AP-39)
- Prepend session-46 block to MEMORY.md (this symlinked page).
- Final 4-way sync commit + push.

## 3. Proof-of-deadness 5-test gate (for DEAD-CODE bucket)

A launchd-registered script is DEAD-CODE only if **all 5 evidence tests pass** (no exceptions, no "looks dead"):

### Test 1 — run history proof

- `ssh air "launchctl print gui/\$(id -u)/<label>" | grep -E 'last exit code|runs'`
- **Pass condition:** either (a) no successful run in last 30 days, OR (b) every run in last 30 days produces stderr-only output / empty stdout (via journalctl or launchd StandardErrorPath file).
- **Fail condition:** any stdout-producing successful run within 30 days.

### Test 2 — reverse call-graph proof

- `grep -rn "<script_name>" ~/Documents/Projects/Nous\ AGaaS/Nous/ --include="*.sh" --include="*.md" --include="*.plist" --include="*.py"`
- `ssh air "grep -rn '<script_name>' ~/nous-agaas/ --include='*.sh' --include='*.plist' --include='*.py'"`
- `ssh root@65.108.215.200 "grep -rn '<script_name>' /root/nous-agaas/ --include='*.sh' --include='*.plist' --include='*.py'"`
- **Pass condition:** zero callers outside the script's own plist (grep finds only the plist + the script itself + maybe historical handoffs).
- **Fail condition:** any external caller (another script / cron entry / plist / active doctrine page).

### Test 3 — doctrine proof

- `mcp__gbrain__search query="<script_name>"` + `mcp__nous-wiki-qmd__query searches=[{type:'lex', query:'<script_name>'}]`
- **Pass condition:** zero mentions in last 10 sessions of progress/handoffs/skills, OR mentions exist but explicitly mark the script as "obsolete," "scheduled for removal," or "replaced by X."
- **Fail condition:** any active-doctrine mention of the script in current skill/law/spec pages without removal context.

### Test 4 — Madi confirmation (per-script, never batch)

- I state: (a) script name + plist label, (b) my reconstruction of its purpose from code, (c) why I believe it's dead, (d) evidence from Tests 1-3.
- Madi acks **per script** — no batch consent. If she's unsure, the script is NOT dead-code; demote.
- **Pass condition:** Madi explicit "yes, delete this one" for that specific script.

### Test 5 — restoration recipe preserved

- Before deletion, I record in audit:
  ```
  git show <current-vault-HEAD>:<plist-path> > /tmp/<label>.plist
  git show <current-vault-HEAD>:<script-path> > /tmp/<script-name>
  ssh air "cp /tmp/... ~/Library/LaunchAgents/"
  ssh air "launchctl load ~/Library/LaunchAgents/<plist-name>"
  ```
  …or the equivalent if the script was Air-only (no vault copy) — in which case restoration requires the git blob hash from `git ls-tree` on the branch where it was last seen. If no git history exists at all (Air-only, never committed), Test 5 FAILS and the script is not DEAD-CODE.
- **Pass condition:** a concrete 2-5 line shell recipe that restores the script to a running state.

**If any of Tests 1-5 fails → script is NOT dead-code.** Demote to the appropriate MIGRATE bucket and keep it running.

## 4. Data flow

```
              (session-46 open)
                      │
                      ▼
   ┌──────────────────────────────────┐
   │   3 gates + AP-10 + AP-34 probe  │   ← already done
   └──────────────────┬───────────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
           ▼                     ▼
    ┌───────────┐          ┌─────────────┐
    │ Phase A   │          │ Phase D     │
    │ hygiene   │          │ migration   │
    └─┬─┬─┬─┬───┘          └┬────┬──────┘
      │ │ │ │                │    │
      │ │ │ └─ aggregator    │    └─ D0 inventory ─► AUDIT page
      │ │ │    cron          │       │
      │ │ │                  │       ▼
      │ │ └─── rotate token  │     D1 classify (4 buckets)
      │ │                    │       │
      │ └───── AP-36 harness │       ▼
      │                      │     D2 MIGRATE-CLEAN (8-step/script)
      └─────── gbrain entry  │       │
              (v2.31)        │       ▼
                             │     D3 MIGRATE-WITH-SECRETS (time-permitting)
                             │       │
                             │       ▼
                             │     D4 DEAD-CODE (5-test gate → delete/demote)
                             │       │
                             │       ▼
                             │     D5 rsync scope extend
                             │       │
                             │       ▼
                             │     D6 absorb AP-39 + AP-40
                             │       │
                             │       ▼
                             └───► D7 close audit + handoff + MEMORY
```

## 5. Testing strategy

- **AP-36 sibling-test for every new script** — `tools/test_<name>.sh` mirroring the `pre-push-sanity.sh` → `test_pre_push_sanity.sh` pattern. Each test script:
  - Uses `mktemp -d` for any disk fixtures; trap EXIT to clean up.
  - Runs multiple named scenarios (at least 1 ACCEPT-path + all known REJECT-paths).
  - Prints `✅ scenario N pass` on each success; `🔴 scenario N fail` + reason on failure.
  - Final line: `✅ ALL N SCENARIOS PASS` or `🔴 N/M SCENARIOS FAILED`.
  - Exit 0 iff all pass.
- **A2 specifically:** test `tools/pre-receive-lesson-count-guard.sh` via ephemeral bare repo + clone + craft commits for each of the 5 scenarios.
- **D2 per-script tests:** minimum is `script --dry-run || script --help || bash -n script.sh` (syntax check); add branch coverage where script has real branching.
- **D4 deletion recipe validation:** before executing the deletion, dry-run the restoration recipe in a `/tmp/` sandbox to confirm the commands produce a file identical (by MD5) to the current live one. Only then delete live.

## 6. Rollback plan

- **A1 (gbrain entry):** reversible via `mcp__gbrain__add_timeline_entry` with corrective summary. No destructive action.
- **A2 (test harness):** commit-addition; `git revert <sha>` removes it. No service impact.
- **A3 (token rotation):** old token is revoked; if new token fails, BotFather can issue another instantly; 2-3 min outage max. Bot tolerates.
- **A4 (aggregator cron):** crontab edit, reversible with `crontab -e` or pre-captured `crontab -l > /tmp/crontab.bak`.
- **D2/D3 (script migration):** Air copies are kept as-is until rsync overwrite; take `scp` backup to `/tmp/air-tools-backup-2026-04-18/` before any Air-side mutation. 5-line restore.
- **D4 (deletion):** restoration recipe is the rollback. Tested before execution (§5).
- **D5 (rsync scope extend):** edit rsync script; if breaks sync, revert in vault + rsync back to Air.
- **D6 (skill bump):** git revert on the SKILL.md commit. gbrain entry removable via `mcp__gbrain__add_timeline_entry` corrective.

## 7. Close audit criteria (what "done" means)

At session 46 close, all must be true:

- [ ] All 3 mandatory session gates PASS at close.
- [ ] AP-10 7-point audit v1.12 PASS at close (LESSON still 129, skill MD5 4-target parity, 4-way vault HEAD, hooks MD5 intact).
- [ ] A1–A4 all completed (gbrain entry present, AP-36 harness committed + passing, token rotated + verified, aggregator cron live with ≥1 successful run).
- [ ] Every Air-registered `com.nous` launchd job is labeled in audit with canonical bucket (VAULT-ALREADY / MIGRATE-CLEAN / MIGRATE-WITH-SECRETS / DEAD-CODE-DELETED / DEAD-CODE-DEMOTED / HANDOFF).
- [ ] MIGRATE-CLEAN bucket: for every script, (a) vault `tools/<name>.sh` exists, (b) `tools/test_<name>.sh` exists + passes, (c) Air MD5 = vault MD5, (d) launchd next-run observed green.
- [ ] DEAD-CODE-DELETED bucket: for every deleted script, audit entry records 5 proof blocks + restoration recipe + deletion timestamp.
- [ ] HANDOFF bucket (if any): each entry has exact next-session first step named.
- [ ] `infrastructure` SKILL.md bumped to v2.33+ with AP-39 (proof-of-deadness) + AP-40 (any new surprise) + Timeline entries. H1 drift (`v2.29.0`) fixed to match frontmatter.
- [ ] `audit` SKILL.md bumped to v1.13 with AP-14 (Air tools MD5 parity check at session open + close).
- [ ] gbrain timeline entries pushed for every skill bump this session.
- [ ] 4-way vault HEAD sync at close.
- [ ] Handoff + MEMORY block written.
- [ ] RULE ZERO upheld: 0 new LESSON files created.

## 8. Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| D0 inventory reveals >15 scripts, time budget busts | Medium | High | Time-box at 4 hr, honest handoff at 3 hr mark |
| A3 token rotation breaks `/start` reply (deploy script bug) | Low | Medium | A3 rollback: BotFather `/token` reissue; 2 min outage |
| Proof-of-deadness Test 4 (Madi confirmation) reveals I've mis-identified dead code | Medium | Low (defensive demote) | Demote to MIGRATE bucket; continue |
| Parallel Claude Code session appears mid-D | Low (0 commits last 5min now) | High (commit race) | Re-run AP-34 cadence probe before D2 + before any destructive op |
| MCP gbrain disconnects mid-absorption (session 45 pattern) | Medium | Medium | Write SKILL.md change first (persists to fs); queue gbrain entry as comment in HANDOFF for next session to replay |
| rsync scope extension (D5) breaks existing Air sync | Low | High | Test with non-critical dummy file first; revert if breaks |

## 9. Open questions to resolve during execution

- (D0) Are there `com.nous.*` LaunchAgents owned by `root` on Air in addition to user-level ones? `sudo launchctl print system | grep com.nous` — probably not, but check.
- (D2) For scripts that are Air-specific (e.g., reference `/Users/madia/Library/...` paths), do we migrate as-is to vault `tools/` with a comment marking Air-specificity, or do we abstract the paths into an env var? Default: migrate as-is + comment; abstract only if two+ Air-specific scripts share the same path.
- (D4) If Test 5 (restoration recipe) has no git history (Air-only, never tracked), is the script automatically demoted to MIGRATE-CLEAN? Yes — §3 Test 5 already says fail → demote.

## 10. Anti-patterns to avoid (Karpathy/Tan/Finn-aligned)

- ❌ **"Let's just inventory this session, migrate next session"** — the classic defer-rot pattern. Migrate the ready-to-migrate bucket now. Hand off only what can't be finished.
- ❌ **"This script is probably obsolete, let me just delete it"** — no 5-test gate. Not acceptable.
- ❌ **"These 3 dead scripts look similar, batch delete them"** — no. Per-script Madi consent. No batch.
- ❌ **"I'll write a LESSON-130 about this migration"** — RULE ZERO. Pre-commit + pre-receive both reject. Skill + gbrain only.
- ❌ **"Sibling test is overkill for this 20-line wrapper"** — AP-36 applies to every server hook; we're extending to every migrated automation script because the pattern compounds. 5-line tests for 20-line wrappers are fine.
- ❌ **"Aggregator cron is the same as A4 from any other project, I'll skip verify"** — no. Wait the cycle. Observe `apk_health_current` populate. Report live data back to Madi.
- ❌ **"4-way sync is optional at close if everything else passes"** — LAW-005 + AP-10. 4-way HEAD parity is non-negotiable at close.

## 11. Compounding payoff (why this is worth 4 hours)

After session 46 close:
- Future sessions no longer have to re-decide "what are these Air scripts?" — the audit is canonical, any drift triggers AP-14 alert.
- New Air automation is mechanically blocked from being Air-only: rsync watches `tools/`, pre-push parity gate watches vault `tools/` vs deployed copies.
- Dead-code deletion is no longer scary because 5-test gate + restoration recipe = provably reversible.
- AP-27 closes permanently; no session 47+ carryover tax.
- `infrastructure` skill now has AP-39 proof-of-deadness procedure — replayable across every future cleanup (BDL camera config cleanup, old Mac Pro scripts, VPS legacy crons, etc.).
- `audit` skill AP-14 adds Air tools MD5 parity to every future session-open audit, mechanical enforcement forever.

This is Karpathy's "make the substrate smarter." This is Tan's "pay down the oldest debt with compound interest." This is Finn's "close the loop, don't produce reports."

---

## Timeline

- **2026-04-18** | Spec written; Madi approved A→D scope + delete-with-evidence policy for DEAD-CODE bucket [[HANDOFF-AUTO-2026-04-17-session-45-atomic-audit]]
