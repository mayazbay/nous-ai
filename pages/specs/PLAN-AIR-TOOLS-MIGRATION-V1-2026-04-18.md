---
id: PLAN-AIR-TOOLS-MIGRATION-V1-2026-04-18
type: spec
title: "Plan — Session 46 Air tools migration v1 — atomic task list for A→D execution (hygiene + AP-27 closure + proof-of-deadness absorption), Karpathy-pattern compounding work"
date: 2026-04-18
status: reviewed
last_updated: 2026-04-18
owner: claude-code-mac (Opus 4.7 1M) + Madi Ayazbay
tags: [plan, air-tools-migration, session-46, ap-27, ap-36, ap-39-candidate, ap-40-candidate, infrastructure, audit, rule-zero, karpathy-pattern, tan-pattern, compounding]
source_count: 3
related:
  - SPEC-AIR-TOOLS-MIGRATION-V1-2026-04-18
  - HANDOFF-AUTO-2026-04-17-session-45-atomic-audit
  - audit
  - infrastructure
  - evidence-verification
  - secrets-management
---

# Air tools/ Migration v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (inline, with checkpoints). Steps use checkbox (`- [ ]`) syntax for tracking. The parent session is the driver; no subagents because parallel-session guarantees are fragile on shared vault (AP-34).

**Goal:** In one session, close session-45 compliance debt (A1+A2), rotate the leaked APK_BOT_TOKEN (A3), wire the apk-bot aggregator cron (A4), then close 8-session-old AP-27 by migrating every Air `com.nous.*` launchd script into vault `tools/` with sibling AP-36 test harnesses or proving-dead-and-deleting with 5-test evidence gate. Absorb learnings as AP-39/AP-40 in `infrastructure` + AP-14 in `audit`. Push all gbrain timeline entries. Zero new LESSON files. Honest handoff for anything not reaching 100%.

**Architecture:** Two-phase work. Phase A = 4 hygiene items, each atomic, gated by AP-34 cadence probe on vault. Phase D = inventory → classify → migrate → test → sync → delete-with-evidence → absorb → audit, one script at a time, with per-script 100% gate. No batch work. Every learning compounds (SKILL.md + gbrain). Vault auto-sync + 4-way parity + 4-target MD5 + pre-push hook together enforce no-drift.

**Tech Stack:** bash, git, launchctl, systemctl, rsync, sqlite3 (read-only probes), `mcp__gbrain__*` MCP tools (add_timeline_entry, get_timeline, search), Telegram Bot API (smoke), Mac Keychain via `tools/secrets-keychain-add.swift`, `tools/secrets-deploy.sh` (pipe-never-variable).

---

## Execution context (read first, informs every task)

- **Parallel session 46 (GOD_PROMPT thread):** closed at `9607a00e` ~10:27 KZT. Their `MEMORY.md` close block is present. Auto-sync on Mac continues pushing my spec/plan edits every 1-2 min. Re-probe cadence (AP-34) before every destructive step.
- **Vault auto-commit:** any file edit in `/Users/madia/Documents/Projects/Nous AGaaS/Nous/` triggers auto-commit + auto-push within 1-2 min via a background launchd job. This means: **do not rely on explicit `git commit` for every file**. Instead: verify commit landed via `git log --oneline -1 -- <path>` before proceeding to next task. Use explicit `git commit -m ...` when I want a named commit (e.g., skill bumps, handoffs) — these compose with auto-sync cleanly as long as there are no racing uncommitted hunks.
- **Remote naming:** vault remote is `vps` (not `origin`). Always `git fetch vps main`, `git log vps/main`, etc.
- **Host-side paths (AP-13):** Air runtime skills live at `/Users/madia/nous-agaas/skills/`, NOT `/opt/nous-agaas/skills/` (the latter is container-internal). Air `tools/` are at `~/nous-agaas/tools/` (= `/Users/madia/nous-agaas/tools/`).
- **Pre-commit + pre-receive hooks:** reject new `LESSON-NNN` files (RULE ZERO). Pre-push hook checks `~/.claude/hooks/*.sh` MD5 = vault `tools/*.sh` MD5 (AP-35). Don't bypass with `--no-verify` except in isolated test sandboxes.
- **AP-34 rule:** if vault `git log --since='5 minutes ago' vps/main | wc -l` ≥ 1, defer destructive ops. Re-probe at each phase boundary.

---

## File structure (what gets touched this session)

### Created

| Path | Purpose |
|---|---|
| `pages/specs/PLAN-AIR-TOOLS-MIGRATION-V1-2026-04-18.md` | This plan (already exists as of Task 0) |
| `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` | D0 inventory + D1 classification + D4 deletion evidence + D7 final state |
| `tools/test_pre_receive_lesson_count_guard.sh` | A2 — AP-36 self-violation closure; 5-scenario test harness for `tools/pre-receive-lesson-count-guard.sh` |
| `tools/<name>.sh` × N (N = MIGRATE-CLEAN bucket size, TBD from D0) | D2 — vault source-of-truth for each migrated Air script |
| `tools/test_<name>.sh` × N | D2 — AP-36 sibling test per migrated script |
| `tools/<name>-secrets.env.example` × M (M = MIGRATE-WITH-SECRETS bucket size, TBD) | D3 — template env files for secret-backed scripts |
| `pages/progress/HANDOFF-AUTO-2026-04-18-session-46-air-tools.md` | D7 close handoff |

### Modified

| Path | Change |
|---|---|
| `pages/skills/infrastructure/SKILL.md` | D6 — add AP-39 (proof-of-deadness), possibly AP-40 (surprise); bump version to v2.33+; fix H1 drift (currently `v2.29.0`, should match `version: 2.32.0+`) |
| `pages/skills/audit/SKILL.md` | D6 — add AP-14 (Air tools MD5 parity at session open + close); bump version to v1.13 |
| `pages/skills/_gbrain/RESOLVER.md` | D6 (only if any new skill created — likely not this session) |
| `pages/secrets-manifest.md` | D3 — new row per MIGRATE-WITH-SECRETS script |
| `pages/progress/claude-memory/MEMORY.md` | D7 — prepend "Session 46-B (Air tools migration thread)" block above parallel session's GOD_PROMPT block |
| `~/nous-agaas/tools/<name>.sh` × N on Air | D2 — rsync from vault (via explicit rsync or via wiki-to-runtime-rsync after D5) |
| VPS crontab (user `deploy`) | A4 — append aggregator cron line |
| Air `wiki-to-runtime-rsync` script (location TBD in D5) | D5 — extend rsync filter to include `tools/` |

### Deleted (only via D4 5-test gate + Madi per-script ack)

| Path | Condition |
|---|---|
| Air `~/Library/LaunchAgents/com.nous.<label>.plist` | script is DEAD-CODE-CONFIRMED, all 5 tests pass, Madi confirmed |
| Air `<ProgramArguments[0]>` script | same condition |

### Non-vault artifacts (synced via `tools/secrets-deploy.sh`)

| Path | Change |
|---|---|
| Mac Keychain entry `nous-agaas/APK_BOT_TOKEN` | A3 — new rotated token; local-only per secrets-management v1.2 AP-8 |
| VPS `/opt/nous-agaas/.env` (line `APK_BOT_TOKEN=...`) | A3 — atomic rewrite via pipe-never-variable |

---

## Phase A — Hygiene (atomic, ~90 min)

### Task A0: Re-probe vault cadence (AP-34)

**Files:** none (read-only probes)

- [ ] **Step A0.1: Fetch + probe vault cadence.**

Run:
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && \
  git fetch vps main --quiet && \
  COMMITS=$(git log --since='5 minutes ago' vps/main --oneline | wc -l | tr -d ' ') && \
  echo "commits last 5 min: $COMMITS" && \
  LAST=$(git log -1 vps/main --format='%ci') && \
  echo "last commit: $LAST" && \
  echo "now: $(date '+%Y-%m-%d %H:%M:%S %z')"
```

Expected: `commits last 5 min: 0` AND last-commit age ≥ 5 min → PROCEED.

- [ ] **Step A0.2: If ≥ 1 commit, defer.**

If commits > 0: wait 5 min (use `ScheduleWakeup` with 300s for delays ≥300s, OR stay active with other local prep). Re-run A0.1. Maximum 3 defer cycles (15 min). If still hot after 3 cycles, announce "parallel session 46 still active; extending plan — will not proceed to A3/A4/D until quiet," and check in with Madi.

- [ ] **Step A0.3: Confirm AP-34 clearance in internal note.**

No file change. Just: update running log (in Task #1 metadata or just proceed). Proceed to A1.

---

### Task A1: Push queued gbrain timeline entries (for v2.31, v2.32, evidence-verification v1.6)

**Files:**
- Read: `pages/skills/infrastructure/SKILL.md` (lines around Timeline, v2.31 + v2.32 entries)
- Read: `pages/skills/evidence-verification/SKILL.md` (v1.6 AP-11 entry)
- Modify (via MCP): gbrain timeline for `pages/skills/infrastructure/skill` + `pages/skills/evidence-verification/skill`

- [ ] **Step A1.1: Extract exact v2.31 Timeline line from infrastructure SKILL.md.**

Run:
```bash
grep -n "v2\.31\.0" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/infrastructure/SKILL.md"
```
Read the matching Timeline line (starts with `- **2026-04-17** | v2.31.0 — Session 45 addendum...`). Copy it verbatim; this is the summary source for the gbrain entry.

- [ ] **Step A1.2: Extract exact v2.32 Timeline line from infrastructure SKILL.md.**

Run:
```bash
grep -n "v2\.32\.0" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/infrastructure/SKILL.md"
```
Copy verbatim. Note this is parallel session's work — crediting in gbrain entry.

- [ ] **Step A1.3: Read evidence-verification SKILL.md v1.6 AP-11 entry.**

Run:
```bash
grep -n "v1\.6\.0\|AP-11" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/evidence-verification/SKILL.md"
```
Copy Timeline v1.6 line verbatim.

- [ ] **Step A1.4: Push gbrain entry for infrastructure v2.31.**

Use MCP tool:
```
mcp__gbrain__add_timeline_entry
  slug = "pages/skills/infrastructure/skill"
  date = "2026-04-17"
  summary = "<verbatim v2.31.0 line copied in A1.1; truncate to ~500 chars if longer; suffix with '(pushed session 46-B A1 — session-45 MCP-disconnect carryover)'>"
  source = "session-46-air-tools-migration"
```

- [ ] **Step A1.5: Push gbrain entry for infrastructure v2.32.**

```
mcp__gbrain__add_timeline_entry
  slug = "pages/skills/infrastructure/skill"
  date = "2026-04-18"
  summary = "<verbatim v2.32.0 line; suffix with '(CREDIT: parallel session-46 GOD_PROMPT thread; pushed by session-46-B air-tools-migration thread on their behalf for gbrain honesty)'>"
  source = "session-46-god-prompt-thread"
```

- [ ] **Step A1.6: Push gbrain entry for evidence-verification v1.6.**

```
mcp__gbrain__add_timeline_entry
  slug = "pages/skills/evidence-verification/skill"
  date = "2026-04-18"
  summary = "<verbatim v1.6.0 line; suffix '(CREDIT: parallel session-46 GOD_PROMPT thread; pushed by session-46-B)'>"
  source = "session-46-god-prompt-thread"
```

- [ ] **Step A1.6b: Push gbrain entry for mistake-to-skill v1.8 (discovered mid-plan).**

Parallel session (commit `dfc0f06f`) bumped `mistake-to-skill` v1.7 → v1.8 adding AP-11 (SKILL.md frontmatter/H1/Timeline parity) + fix 7 drifts (including infrastructure H1 v2.29→v2.32 and evidence-verification H1 v1.5→v1.6) + shipped `tools/test_skill_version_parity.sh`. Push gbrain entry on their behalf:

```
mcp__gbrain__add_timeline_entry
  slug = "pages/skills/mistake-to-skill/skill"
  date = "2026-04-18"
  summary = "v1.7 → v1.8 — AP-11 (SKILL.md frontmatter/H1/Timeline version parity; extends AP-7 from LESSON drift to skill drift). Found 7 drifts across 20 skills (2 session-46 + 5 pre-existing); all fixed. Shipped tools/test_skill_version_parity.sh drift scanner. Next-session candidate: wire into pre-commit hook (Tan/Karpathy compounding-hook pattern). CREDIT: parallel session-46 GOD_PROMPT thread deep-audit; pushed by session-46-B."
  source = "session-46-god-prompt-thread"
```

- [ ] **Step A1.7: Verify all 4 entries landed in gbrain.**

```
mcp__gbrain__get_timeline slug = "pages/skills/infrastructure/skill"
```
Expect: the 2 new entries present at top (or wherever gbrain sorts them).

```
mcp__gbrain__get_timeline slug = "pages/skills/evidence-verification/skill"
```
Expect: v1.6 entry present.

- [ ] **Step A1.8: Mark A1 complete.**

No file change. Proceed to A2.

---

### Task A2: Write `tools/test_pre_receive_lesson_count_guard.sh` (AP-36 self-violation closure)

**Files:**
- Create: `tools/test_pre_receive_lesson_count_guard.sh`
- Read: `tools/pre-receive-lesson-count-guard.sh` (SUT)
- Read: `tools/test_pre_push_sanity.sh` (pattern reference)
- Modify: `pages/skills/infrastructure/SKILL.md` (Timeline line noting AP-36 self-violation closed)

- [ ] **Step A2.1: Read full pre-receive hook source.**

Run:
```bash
cat "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/pre-receive-lesson-count-guard.sh"
```
Identify: the stdin contract (old_sha new_sha ref_name), the FROZEN_COUNT=129, the LESSON-EXEMPT escape-hatch logic, the ls-tree grep pattern.

- [ ] **Step A2.2: Read pattern template.**

Run:
```bash
cat "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/test_pre_push_sanity.sh"
```
Note: scenario-per-function, `mktemp -d` + `trap` cleanup, PASS/FAIL echo per scenario, final summary + exit code.

- [ ] **Step A2.3: Write the test harness (full file, ~180 lines).**

Create `/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/test_pre_receive_lesson_count_guard.sh` with this content:

```bash
#!/bin/bash
# Functional test harness for tools/pre-receive-lesson-count-guard.sh.
# Exercises 5 canonical scenarios:
#   1. ACCEPT-nochange     push modifies unrelated file             → exit 0
#   2. REJECT-add          push adds LESSON-130 via git add         → exit 1
#   3. REJECT-rename       push adds LESSON-130 via rename          → exit 1
#   4. ACCEPT-exempt       scenario 2 BUT commit has LESSON-EXEMPT  → exit 0
#   5. ACCEPT-edit         push modifies existing LESSON-042        → exit 0
#
# Run: cd <vault> && bash tools/test_pre_receive_lesson_count_guard.sh
# Prints one PASS/FAIL per scenario + final summary. Exits 0 iff all pass.

set -u

HOOK="$(git rev-parse --show-toplevel)/tools/pre-receive-lesson-count-guard.sh"
if [ ! -x "$HOOK" ]; then
  echo "🔴 FAIL: pre-receive-lesson-count-guard.sh not found or not executable at $HOOK"
  exit 1
fi

TMPROOT=$(mktemp -d)
trap "rm -rf '$TMPROOT'" EXIT

FAIL=0

setup_bare_with_hook() {
  # Create fresh bare repo with the hook installed as pre-receive.
  local BARE="$1"
  rm -rf "$BARE"
  git init --bare --quiet "$BARE"
  cp "$HOOK" "$BARE/hooks/pre-receive"
  chmod +x "$BARE/hooks/pre-receive"
}

seed_clone_with_129_lessons() {
  # Create a work-tree clone seeded with 129 LESSON files (the frozen count) + minimal structure.
  local BARE="$1"
  local WT="$2"
  git clone --quiet "$BARE" "$WT"
  cd "$WT"
  git config user.email "test@example.com"
  git config user.name "test"
  mkdir -p pages/lessons/individual
  for i in $(seq 1 129); do
    N=$(printf '%03d' "$i")
    echo "---
type: lesson
id: LESSON-$N
---
# LESSON-$N" > "pages/lessons/individual/LESSON-$N-placeholder.md"
  done
  echo "readme" > README.md
  git add -A
  git commit --quiet -m "seed: 129 lessons at frozen count" --no-verify
  git push --quiet origin main:main
  cd - >/dev/null
}

run_scenario() {
  local NAME="$1"
  local EXPECT="$2"   # "accept" | "reject"
  local ACTUAL="$3"   # "accept" | "reject"
  if [ "$EXPECT" = "$ACTUAL" ]; then
    echo "✅ scenario $NAME pass (expected=$EXPECT, got=$ACTUAL)"
  else
    echo "🔴 scenario $NAME FAIL (expected=$EXPECT, got=$ACTUAL)"
    FAIL=$((FAIL + 1))
  fi
}

# ---------- Scenario 1: ACCEPT-nochange ----------
BARE1="$TMPROOT/s1.git"
WT1="$TMPROOT/s1_wt"
setup_bare_with_hook "$BARE1"
seed_clone_with_129_lessons "$BARE1" "$WT1"
(
  cd "$WT1"
  echo "edit" >> README.md
  git add README.md
  git commit --quiet -m "docs: tweak readme" --no-verify
  if git push --quiet origin main:main 2>/dev/null; then
    echo accept
  else
    echo reject
  fi
) > "$TMPROOT/s1.out"
run_scenario "1 ACCEPT-nochange" "accept" "$(cat "$TMPROOT/s1.out")"

# ---------- Scenario 2: REJECT-add ----------
BARE2="$TMPROOT/s2.git"
WT2="$TMPROOT/s2_wt"
setup_bare_with_hook "$BARE2"
seed_clone_with_129_lessons "$BARE2" "$WT2"
(
  cd "$WT2"
  echo "---
type: lesson
id: LESSON-130
---
# LESSON-130" > pages/lessons/individual/LESSON-130-newlesson.md
  git add pages/lessons/individual/LESSON-130-newlesson.md
  git commit --quiet -m "lesson: add 130 (should be rejected)" --no-verify
  if git push --quiet origin main:main 2>/dev/null; then
    echo accept
  else
    echo reject
  fi
) > "$TMPROOT/s2.out"
run_scenario "2 REJECT-add" "reject" "$(cat "$TMPROOT/s2.out")"

# ---------- Scenario 3: REJECT-rename ----------
BARE3="$TMPROOT/s3.git"
WT3="$TMPROOT/s3_wt"
setup_bare_with_hook "$BARE3"
seed_clone_with_129_lessons "$BARE3" "$WT3"
(
  cd "$WT3"
  mkdir -p pages/drafts
  echo "---
type: lesson
id: LESSON-130
---
# LESSON-130" > pages/drafts/candidate.md
  git add pages/drafts/candidate.md
  git commit --quiet -m "draft: stage candidate" --no-verify
  git mv pages/drafts/candidate.md pages/lessons/individual/LESSON-130-via-rename.md
  git commit --quiet -m "promote: rename draft into canonical LESSON path" --no-verify
  if git push --quiet origin main:main 2>/dev/null; then
    echo accept
  else
    echo reject
  fi
) > "$TMPROOT/s3.out"
run_scenario "3 REJECT-rename" "reject" "$(cat "$TMPROOT/s3.out")"

# ---------- Scenario 4: ACCEPT-exempt ----------
BARE4="$TMPROOT/s4.git"
WT4="$TMPROOT/s4_wt"
setup_bare_with_hook "$BARE4"
seed_clone_with_129_lessons "$BARE4" "$WT4"
(
  cd "$WT4"
  echo "---
type: lesson
id: LESSON-130
---
# LESSON-130" > pages/lessons/individual/LESSON-130-emergency.md
  git add pages/lessons/individual/LESSON-130-emergency.md
  git commit --quiet -m "emergency lesson LESSON-EXEMPT for compliance audit retention" --no-verify
  if git push --quiet origin main:main 2>/dev/null; then
    echo accept
  else
    echo reject
  fi
) > "$TMPROOT/s4.out"
run_scenario "4 ACCEPT-exempt" "accept" "$(cat "$TMPROOT/s4.out")"

# ---------- Scenario 5: ACCEPT-edit ----------
BARE5="$TMPROOT/s5.git"
WT5="$TMPROOT/s5_wt"
setup_bare_with_hook "$BARE5"
seed_clone_with_129_lessons "$BARE5" "$WT5"
(
  cd "$WT5"
  echo "additional line" >> pages/lessons/individual/LESSON-042-placeholder.md
  git add pages/lessons/individual/LESSON-042-placeholder.md
  git commit --quiet -m "lesson: amend 042 with drift correction" --no-verify
  if git push --quiet origin main:main 2>/dev/null; then
    echo accept
  else
    echo reject
  fi
) > "$TMPROOT/s5.out"
run_scenario "5 ACCEPT-edit" "accept" "$(cat "$TMPROOT/s5.out")"

# ---------- Summary ----------
echo
if [ "$FAIL" -eq 0 ]; then
  echo "✅ ALL 5 SCENARIOS PASS"
  exit 0
else
  echo "🔴 $FAIL/5 SCENARIOS FAILED"
  exit 1
fi
```

(Write this whole content via the Write tool.)

- [ ] **Step A2.4: Mark the test harness executable.**

Run:
```bash
chmod +x "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/test_pre_receive_lesson_count_guard.sh"
```
Expected: no output (exit 0).

- [ ] **Step A2.5: Run the test harness locally.**

Run:
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && bash tools/test_pre_receive_lesson_count_guard.sh
```
Expected final line: `✅ ALL 5 SCENARIOS PASS` and exit code 0.

If any scenario FAILS: read the failure message, fix either the test harness (if my reading of the hook is wrong) or stage a hook patch (if the hook has an actual bug — escalate, don't silently fix). Do NOT move forward until all 5 PASS.

- [ ] **Step A2.6: Update `infrastructure` SKILL.md Timeline with AP-36 self-violation closed.**

Read current SKILL.md Timeline lines via Grep. Add a new Timeline line at the top of the Timeline section:
```
- **2026-04-18** | v2.32.0 → v2.32.1 — Session 46-B A2: closed AP-36 self-violation. `tools/pre-receive-lesson-count-guard.sh` installed session 45 without sibling test; now has `tools/test_pre_receive_lesson_count_guard.sh` (5 scenarios: ACCEPT-nochange, REJECT-add, REJECT-rename, ACCEPT-exempt, ACCEPT-edit; all PASS). AP-36 now has 2/2 compliance: pre-push-sanity + pre-receive-lesson-count-guard. RULE ZERO upheld.
```
Bump frontmatter `version: 2.32.0` → `version: 2.32.1`.

- [ ] **Step A2.7: Push gbrain timeline entry for AP-36 self-violation closure.**

```
mcp__gbrain__add_timeline_entry
  slug = "pages/skills/infrastructure/skill"
  date = "2026-04-18"
  summary = "v2.32.0 → v2.32.1 — AP-36 self-violation closure. Session 45 wrote AP-36 requiring sibling tests/test_<name>.sh for every new server hook but installed tools/pre-receive-lesson-count-guard.sh without one; session 46-B A2 closes the gap. 5 scenarios (accept-nochange + reject-add + reject-rename + accept-exempt + accept-edit) all PASS."
  source = "session-46-B air-tools-migration A2"
```

- [ ] **Step A2.8: Verify commit landed.**

Wait ≤2 min for auto-sync. Run:
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && git log --oneline -3 -- tools/test_pre_receive_lesson_count_guard.sh pages/skills/infrastructure/SKILL.md
```
Expected: recent commits include the new test harness + SKILL.md update.

If not, explicit commit:
```bash
git add tools/test_pre_receive_lesson_count_guard.sh pages/skills/infrastructure/SKILL.md && \
  git commit -m "skill+test: infrastructure v2.32.0 → v2.32.1 + tools/test_pre_receive_lesson_count_guard.sh (AP-36 self-violation closed) [risk] REQ-046" && \
  git push vps main
```

---

### Task A3: Rotate APK_BOT_TOKEN (security carryover)

**Files:**
- Modify (via Keychain): `nous-agaas/APK_BOT_TOKEN` (Mac Keychain)
- Modify (via ssh + pipe): `/opt/nous-agaas/.env` on VPS (APK_BOT_TOKEN line)
- Read-only: `pages/secrets-manifest.md` (verify rotation cadence is satisfied)

**Pre-requisite:** AP-34 re-probe at start of Task A3 (vault cadence quiet ≥ 5 min).

**Madi-dependent step:** revoking the token requires Madi to DM BotFather. I cannot do this; I coordinate with her.

- [ ] **Step A3.1: Re-probe vault cadence (AP-34).**

Repeat Step A0.1. If not clean, defer.

- [ ] **Step A3.2: Confirm current live token functional (baseline).**

Run on VPS:
```bash
ssh root@65.108.215.200 "TOKEN=\$(grep '^APK_BOT_TOKEN=' /opt/nous-agaas/.env | cut -d= -f2-) && curl -s \"https://api.telegram.org/bot\$TOKEN/getMe\" | python3 -c 'import sys,json; r=json.load(sys.stdin); print(\"OK:\",r[\"result\"][\"username\"]) if r.get(\"ok\") else print(\"FAIL:\",r)'"
```
Expected: `OK: NousAPKstatusbot`. If FAIL, token is already broken — different issue, escalate.

- [ ] **Step A3.3: Coordinate with Madi — she revokes old token via BotFather.**

Send a text message to Madi:
> "Ready to rotate APK_BOT_TOKEN. Please DM @BotFather → `/mybots` → select NousAPKstatusbot → API Token → **Revoke current token** → paste the new token back to me here (or if you prefer, run `security add-generic-password -a madia -s nous-agaas/APK_BOT_TOKEN -w 'NEWTOKEN' -U` yourself and I'll skip step A3.4)."

WAIT for Madi to paste the new token OR confirm she added it to Keychain herself.

- [ ] **Step A3.4: Store new token in Mac Keychain (local-only).**

If Madi pasted the token to me:
```bash
tools/secrets-keychain-add.swift nous-agaas/APK_BOT_TOKEN "<NEW_TOKEN>" --icloud no
```
(Uses local-only per `secrets-management` v1.2 AP-8.)

Verify:
```bash
security find-generic-password -a madia -s nous-agaas/APK_BOT_TOKEN -w | head -1
```
Expected: prints the new token (briefly — do NOT pipe this to anywhere).

If Madi stored it herself: skip A3.4; verify with same `security find-generic-password` command.

- [ ] **Step A3.5: Deploy new token to VPS.**

Run:
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && bash tools/secrets-deploy.sh apk-status-bot vps
```
Expected: script reads Keychain → ssh pipe to VPS → atomic rename `/opt/nous-agaas/.env.tmp` → `/opt/nous-agaas/.env` with mode 0600. Exits 0 with confirmation.

- [ ] **Step A3.6: Restart apk-bot-polling service on VPS.**

Run:
```bash
ssh root@65.108.215.200 "systemctl restart apk-bot-polling && systemctl is-active apk-bot-polling"
```
Expected: `active`.

- [ ] **Step A3.7: Verify new token works via Telegram API.**

Run:
```bash
ssh root@65.108.215.200 "TOKEN=\$(grep '^APK_BOT_TOKEN=' /opt/nous-agaas/.env | cut -d= -f2-) && curl -s \"https://api.telegram.org/bot\$TOKEN/getMe\" | python3 -c 'import sys,json; r=json.load(sys.stdin); print(\"OK:\",r[\"result\"][\"username\"]) if r.get(\"ok\") else print(\"FAIL:\",r)'"
```
Expected: `OK: NousAPKstatusbot` (same username, different token).

- [ ] **Step A3.8: Smoke-test /start from Madi's DM.**

Ask Madi:
> "Tap /start in the bot DM now. Tell me what it replies."

Expected: WELCOME message + inline keyboard (📊 Статус / 🌅 Сегодня / ❓ Помощь / 🔄 Обновить / 🩺 Диагностика).

If she gets an error: stop, investigate (most likely `.env` format bug or process not re-read env).

- [ ] **Step A3.9: Purge pre-rotation token mentions from journald.**

Run:
```bash
ssh root@65.108.215.200 "journalctl --vacuum-time=30min --unit=apk-bot-polling.service 2>&1 | tail -3"
```
This vacuums journal entries older than 30 min (current time - 30 min). The pre-rotation leaked lines were from 2026-04-17 18:19:47 + 18:20:17 — well over 30 min ago, so they're purged.

Verify no token-looking strings in current journal:
```bash
ssh root@65.108.215.200 "journalctl -u apk-bot-polling -n 50 --no-pager 2>&1 | grep -E '[0-9]+:[A-Za-z0-9_-]{30,}' | head -3"
```
Expected: no output (no token-pattern strings).

- [ ] **Step A3.10: Commit secrets-manifest.md update (if manifest tracks last-rotation date).**

Read `pages/secrets-manifest.md`; if it has a "last_rotated" column for APK_BOT_TOKEN, update to `2026-04-18`. Commit. Else skip.

- [ ] **Step A3.11: Mark A3 complete.**

No file change. Proceed to A4.

---

### Task A4: Wire aggregator cron on VPS

**Files:**
- Modify: VPS crontab (user `deploy`)
- Read-only verify: VPS `/var/log/apk-bot/aggregator.log`, `/opt/nous-agaas/erap/data/apk_health.db`

- [ ] **Step A4.1: Verify aggregator module + __main__ exist.**

Run:
```bash
ssh root@65.108.215.200 "sudo -u deploy test -f /opt/nous-agaas/apk-status-bot/apk_status_bot/aggregator.py && sudo -u deploy cd /opt/nous-agaas/apk-status-bot && .venv/bin/python -c 'import apk_status_bot.aggregator as a; print(hasattr(a,\"main\") or hasattr(a,\"run\"))'"
```
Expected: `True`. If False, aggregator __main__ missing — stop + escalate.

- [ ] **Step A4.2: Ensure `/var/log/apk-bot/` exists + is writable by `deploy`.**

Run:
```bash
ssh root@65.108.215.200 "test -d /var/log/apk-bot && stat -c '%U:%G %a' /var/log/apk-bot"
```
Expected: `deploy:deploy 0755` or similar with deploy:deploy ownership.

If missing:
```bash
ssh root@65.108.215.200 "mkdir -p /var/log/apk-bot && chown deploy:deploy /var/log/apk-bot && chmod 0755 /var/log/apk-bot"
```

- [ ] **Step A4.3: Capture current crontab snapshot (rollback insurance).**

Run:
```bash
ssh root@65.108.215.200 "crontab -u deploy -l 2>/dev/null > /tmp/crontab-deploy-before-A4-2026-04-18 && wc -l /tmp/crontab-deploy-before-A4-2026-04-18"
```
Expected: prints line count; snapshot saved.

- [ ] **Step A4.4: Append aggregator cron line.**

Run:
```bash
ssh root@65.108.215.200 "(crontab -u deploy -l 2>/dev/null; echo '*/10 * * * * cd /opt/nous-agaas/apk-status-bot && .venv/bin/python -m apk_status_bot.aggregator >> /var/log/apk-bot/aggregator.log 2>&1') | crontab -u deploy -"
```

- [ ] **Step A4.5: Verify crontab now contains aggregator line.**

Run:
```bash
ssh root@65.108.215.200 "crontab -u deploy -l | grep aggregator"
```
Expected: 1 line matching the pattern `*/10 * * * * ... aggregator`.

- [ ] **Step A4.6: Wait for first scheduled run (≤10 min).**

Use ScheduleWakeup with 270s (stays in cache) + poll, or batch with other work. Poll condition:
```bash
ssh root@65.108.215.200 "tail -5 /var/log/apk-bot/aggregator.log 2>/dev/null | tail -1"
```
Expected after first cycle: non-empty log line with recent timestamp.

- [ ] **Step A4.7: Verify `apk_health_current` populated.**

Run:
```bash
ssh root@65.108.215.200 "sudo -u deploy sqlite3 -readonly /opt/nous-agaas/erap/data/apk_health.db 'SELECT COUNT(*), MAX(checked_at) FROM apk_health_current'"
```
Expected: COUNT > 0, MAX timestamp within last 10 min.

Note: if `apk_health_current` count is 0 because cameras still unreachable (NIT VPN blocker), that's honest not a bug — the row might be 0 but the table schema populated is what matters. Check for either COUNT > 0 OR last-attempt timestamp present.

- [ ] **Step A4.8: Smoke-test bot /status button.**

Ask Madi:
> "Tap 📊 Статус in the bot. Tell me what you see."

Expected: either a real count (if cameras respond), or an honest "Нет данных"-style message if still 0 reachable (per session-42 AP-7 no-data-honesty fix). Both are acceptable outcomes; the failure mode is silent edit or bogus "0/0 работают."

- [ ] **Step A4.9: Mark A4 complete.**

Proceed to Phase D.

---

## Phase D — Air `tools/` Migration (~2.5 hr, time-boxed; 100% gate per script)

### Task D0: Air launchd inventory (read-only, ~30 min)

**Files:**
- Create: `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md`

- [ ] **Step D0.1: Re-probe vault cadence (AP-34). Required before any destructive planning.**

Same as Step A0.1. If not clean, defer.

- [ ] **Step D0.2: Create audit page skeleton.**

Create `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` with this content (use Write tool):

```markdown
---
id: AUDIT-AIR-TOOLS-INVENTORY-2026-04-18
type: audit
title: "Air launchd tools inventory + classification + migration + deletion evidence (session 46-B, closes AP-27 8-session carryover)"
date: 2026-04-18
status: draft
last_updated: 2026-04-18
owner: claude-code-mac (Opus 4.7 1M) + Madi Ayazbay
tags: [audit, air-tools-migration, ap-27, session-46-B, rule-zero, karpathy-pattern]
source_count: 3
related:
  - SPEC-AIR-TOOLS-MIGRATION-V1-2026-04-18
  - PLAN-AIR-TOOLS-MIGRATION-V1-2026-04-18
  - audit
  - infrastructure
---

# Audit — Air `tools/` Migration (Session 46-B)

**Scope:** Every `com.nous.*` launchd job on Air (`ssh air`). Closes AP-27 8-session carryover (first surfaced session 37).

## 1. Inventory (D0 read-only)

<!-- Table populated in D0 -->

| # | Label | Plist Path | Program Args | Script Path (host-side) | Script MD5 | Script mtime | Tracked in vault `tools/` | Tracked elsewhere in vault | Calls (other scripts) | Reads secrets | Last launchd run / exit code | Provisional bucket |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## 2. Classification (D1)

<!-- Populated in D1 with final bucket per row + rationale. -->

## 3. Migration record (D2/D3)

<!-- Per-script migration entry — vault commit SHA, rsync timestamp, test pass confirmation, first-run exit code. -->

## 4. Dead-code evidence + restoration recipes (D4)

<!-- Per-deleted-script 5-test evidence block + restoration recipe + Madi ack timestamp + deletion timestamp. -->

## 5. Final state (D7)

<!-- MIGRATED | DELETED | HANDOFF per script; overall close-audit summary. -->

---

## Timeline
- **2026-04-18** | Audit page created; D0 inventory begins.
```

- [ ] **Step D0.3: Enumerate Nous launchd jobs on Air.**

Run:
```bash
ssh air "launchctl list | grep com.nous" > /tmp/air_launchctl_nous_2026-04-18.txt && cat /tmp/air_launchctl_nous_2026-04-18.txt
```
Expected: list of labels (e.g., `com.nous.litellm`, `com.nous.telegram-poll`, `com.nous.auto-checkpoint`, etc.).

Also check root:
```bash
ssh air "sudo launchctl print system 2>/dev/null | grep -E 'com\.nous' | head -20"
```
Expected: typically empty (Nous runs user-level). Note results.

- [ ] **Step D0.4: For each label, extract plist path + ProgramArguments + script content metadata.**

For each label `L` from step D0.3:
```bash
ssh air "launchctl print gui/\$(id -u)/<L>" > /tmp/air_launchctl_<L>.txt
```
Scan each file for: `path = ...` (plist location), `ProgramArguments = ...` (script + args), `last exit code`, `runs`, `program = ...`.

Then for each script path `S`:
```bash
ssh air "ls -la <S>; md5 -q <S>; stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' <S>"
```

- [ ] **Step D0.5: Check vault-tracked status per script.**

For each script `S`:
- Extract basename (e.g., `light-probe.sh` from `/Users/madia/nous-agaas/tools/light-probe.sh`).
- Check Mac vault:
```bash
ls -la "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/<basename>" 2>/dev/null
```
- If present: record MD5 of vault copy + note in table (`tracked_in_vault_tools = yes`).
- If not in `tools/`: grep vault for the basename:
```bash
grep -rln "<basename>" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/" --include="*.sh" --include="*.py" --include="*.md" 2>/dev/null | head -5
```
- If found elsewhere (e.g., `pages/skills/<skill>/<basename>`), note path.

- [ ] **Step D0.6: Reverse-call-graph probe.**

For each script `S` / basename `B`:
```bash
# Vault scan
grep -rln "<B>" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/" 2>/dev/null | head -10

# Air scan
ssh air "grep -rln '<B>' ~/nous-agaas/ 2>/dev/null | head -10"

# VPS scan
ssh root@65.108.215.200 "grep -rln '<B>' /root/nous-agaas/ /opt/nous-agaas/ 2>/dev/null | head -10"
```
Record callers in the "Calls (other scripts)" column — exclude self-references (the script itself + its own plist).

- [ ] **Step D0.7: Populate inventory table in audit page.**

Edit `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` §1 table with one row per label. Fill every column based on D0.3–D0.6 data.

- [ ] **Step D0.8: Commit audit page inventory.**

Explicit commit (this is a named milestone):
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && \
  git add pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md && \
  git commit -m "audit: D0 inventory — Air launchd com.nous jobs (session 46-B) [risk] REQ-046" && \
  git push vps main
```

- [ ] **Step D0.9: Push gbrain entry noting inventory done.**

```
mcp__gbrain__add_timeline_entry
  slug = "pages/audits/audit-air-tools-inventory-2026-04-18"
  date = "2026-04-18"
  summary = "D0 inventory complete; N=<count> launchd com.nous jobs enumerated with plist/script/MD5/mtime/vault-tracking/call-graph metadata; proceeding to D1 classification."
  source = "session-46-B air-tools-migration D0"
```

---

### Task D1: Classify each script into bucket

**Files:**
- Modify: `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` (populate §2 with final bucket per row)

- [ ] **Step D1.1: Apply classification rules per row.**

For each row in §1 inventory:
- **VAULT-ALREADY** if `tracked_in_vault_tools == yes` AND Air MD5 == vault MD5.
- **VAULT-ALREADY-DRIFT** if `tracked_in_vault_tools == yes` AND Air MD5 != vault MD5 — this is a repair case: figure out which side is right, sync, record.
- **MIGRATE-CLEAN** if `tracked_in_vault_tools == no`, no secrets, no external callers beyond its own plist.
- **MIGRATE-WITH-SECRETS** if `tracked_in_vault_tools == no` AND `reads_secrets == yes`, OR has Air-specific paths that must stay local.
- **DEAD-CODE-CANDIDATE** if all 5 D4 tests already pass at classification time (most will not — this is a provisional label).
- **UNKNOWN** only if evidence contradictory (e.g., script calls a missing module). Treat as HOLD.

- [ ] **Step D1.2: Update §2 table with canonical bucket per script.**

Edit audit page; add table for §2 with columns: `Label | Final bucket | Classification rationale (1-2 lines)`.

- [ ] **Step D1.3: Commit classification.**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && \
  git add pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md && \
  git commit -m "audit: D1 classification — <N> scripts bucketed (CLEAN=?, SECRETS=?, DEAD-CANDIDATE=?, VAULT-ALREADY=?) [risk] REQ-046" && \
  git push vps main
```

- [ ] **Step D1.4: Announce bucket sizes to Madi.**

Message Madi:
> "D1 classification done. Bucket sizes: VAULT-ALREADY=<N>, VAULT-ALREADY-DRIFT=<N>, MIGRATE-CLEAN=<N>, MIGRATE-WITH-SECRETS=<N>, DEAD-CODE-CANDIDATE=<N>, UNKNOWN=<N>. Proceeding to D2 migration of CLEAN bucket, one script at a time."

(This is a status message, not a permission ask.)

---

### Task D2: Migrate MIGRATE-CLEAN bucket (per-script atomic loop)

**Files (per script N):**
- Create: `tools/<name>.sh` (vault copy)
- Create: `tools/test_<name>.sh` (AP-36 sibling test)
- Read-only: `ssh air "cat ~/nous-agaas/tools/<name>.sh"`
- Modify (via rsync): `~/nous-agaas/tools/<name>.sh` on Air
- Modify: `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` §3 (migration record per script)

For each script N in MIGRATE-CLEAN bucket, do these 8 atomic steps. If any step fails: stop the bucket, do NOT proceed to script N+1, capture honest handoff in audit §5.

- [ ] **Step D2.N.1: Re-probe AP-34 cadence.**

Same as A0.1. Must be quiet.

- [ ] **Step D2.N.2: Pull Air script to local tmp.**

```bash
scp air:~/nous-agaas/tools/<name>.sh /tmp/air_<name>_2026-04-18.sh && \
  md5 -q /tmp/air_<name>_2026-04-18.sh
```

- [ ] **Step D2.N.3: Copy to vault `tools/`.**

```bash
cp /tmp/air_<name>_2026-04-18.sh "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/<name>.sh" && \
  chmod +x "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/<name>.sh"
```

- [ ] **Step D2.N.4: Read the script; design minimal sibling test.**

Read `tools/<name>.sh`. For the sibling `tools/test_<name>.sh`, minimum is:
- Scenario 1 (syntax-check): `bash -n <name>.sh` exits 0.
- Scenario 2 (help or dry-run): script supports `--help` or `--dry-run` → invoke; expect exit 0 + non-empty stdout.
- If script has no `--help` flag: add scenario "invoke in a sandbox where its side-effects are no-ops" (e.g., `HOME=/tmp bash <name>.sh` if script reads `$HOME/.state`).

Write `/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/test_<name>.sh` mirroring the `test_pre_push_sanity.sh` pattern: `mktemp -d` + trap cleanup + scenarios with PASS/FAIL echo + final summary + exit code.

- [ ] **Step D2.N.5: Run sibling test locally.**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && bash tools/test_<name>.sh
```
Expected: `✅ ALL N SCENARIOS PASS` + exit 0.

If FAIL: this is the stop gate. Investigate; do not proceed.

- [ ] **Step D2.N.6: Commit both files to vault.**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && \
  git add tools/<name>.sh tools/test_<name>.sh && \
  git commit -m "tools: migrate Air <name>.sh to vault with AP-36 sibling test (session 46-B D2) [risk] REQ-046" && \
  git push vps main
```
Expected: commit lands; pre-push hook passes (test_<name>.sh passes); pre-receive hook passes (no LESSON change).

- [ ] **Step D2.N.7: rsync to Air.**

```bash
rsync -av "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/<name>.sh" air:~/nous-agaas/tools/<name>.sh
```

- [ ] **Step D2.N.8: Verify Air MD5 == vault MD5.**

```bash
AIR_MD5=$(ssh air "md5 -q ~/nous-agaas/tools/<name>.sh") && \
  VAULT_MD5=$(md5 -q "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/<name>.sh") && \
  echo "Air=$AIR_MD5 Vault=$VAULT_MD5" && \
  [ "$AIR_MD5" = "$VAULT_MD5" ] && echo "✅ parity" || echo "🔴 drift"
```
Expected: `✅ parity`. If drift: stop.

- [ ] **Step D2.N.9: Observe next launchd run.**

```bash
ssh air "launchctl print gui/\$(id -u)/<label> | grep -E 'last exit code|runs'"
```
If script is scheduled to run within test window (e.g., hourly `light-probe`), wait for next run + verify exit 0.
If script is daily-scheduled: trigger manually via `launchctl kickstart gui/$(id -u)/<label>` + verify exit 0.

- [ ] **Step D2.N.10: Update audit §3 with migration record for this script.**

Edit audit page; append to §3:
```
### <name>
- Vault commit: `<sha>`
- rsync timestamp: <ISO>
- Test: tools/test_<name>.sh PASS
- Air MD5 = Vault MD5 = `<md5>`
- Next launchd run exit code: 0
- Migration status: **MIGRATED**
```

- [ ] **Step D2.N.11: Commit audit update.**

Covered by auto-sync within 1-2 min, or explicit:
```bash
git add pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md && \
  git commit -m "audit: D2 migration record — <name> migrated (session 46-B) [risk] REQ-046" && \
  git push vps main
```

**Repeat D2.N.1–D2.N.11 for each script in MIGRATE-CLEAN bucket, one at a time. Stop at 3-hour mark or any FAIL.**

---

### Task D3: Migrate MIGRATE-WITH-SECRETS bucket (time permitting)

Same pattern as D2 plus secrets extraction. For each script N:

- [ ] **Step D3.N.1: Re-probe AP-34, pull Air script, identify secret references.**

Run D2.N.1–D2.N.2. Then identify secrets:
```bash
grep -E '\b(TOKEN|API_KEY|PASSWORD|SECRET|BEARER)\b' /tmp/air_<name>_2026-04-18.sh
```
List each secret variable.

- [ ] **Step D3.N.2: Extract secrets into `.env` template.**

Create `/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/<name>-secrets.env.example`:
```
# Required secrets for tools/<name>.sh (Air-local; source via `. <name>-secrets.env`)
# Populate at: ~/nous-agaas/config/<name>-secrets.env (Air-only, 0600, never commit)
<SECRET_VAR_1>=
<SECRET_VAR_2>=
```

- [ ] **Step D3.N.3: Refactor script to source env file.**

Edit the Air script (now in local tmp) so it starts with:
```bash
# Load Air-local secrets
if [ -f "$HOME/nous-agaas/config/<name>-secrets.env" ]; then
  . "$HOME/nous-agaas/config/<name>-secrets.env"
fi
```
And remove any inline secret values.

- [ ] **Step D3.N.4: Install secrets on Air.**

For each secret variable: add to Mac Keychain if not already present, then deploy:
```bash
bash tools/secrets-deploy.sh <name> air
```
(Or manual one-liner if secrets-deploy.sh doesn't yet support this destination.)

Verify:
```bash
ssh air "test -f ~/nous-agaas/config/<name>-secrets.env && stat -f '%Sp' ~/nous-agaas/config/<name>-secrets.env"
```
Expected: `-rw-------` (0600).

- [ ] **Step D3.N.5: Copy refactored script to vault + sibling test (mock-secret mode).**

Same as D2.N.3 + D2.N.4. The sibling test should invoke the script with a dummy env file:
```bash
# in test_<name>.sh
TMP_ENV=$(mktemp)
trap "rm -f $TMP_ENV" EXIT
echo "<SECRET_VAR_1>=dummy-for-test" > "$TMP_ENV"
echo "<SECRET_VAR_2>=dummy-for-test" >> "$TMP_ENV"
HOME=$(mktemp -d) mkdir -p "$HOME/nous-agaas/config" && cp "$TMP_ENV" "$HOME/nous-agaas/config/<name>-secrets.env"
bash tools/<name>.sh --dry-run
```

- [ ] **Step D3.N.6: Run test + commit + rsync + MD5 verify + observe run (D2.N.5-D2.N.9 equivalents).**

Same procedure.

- [ ] **Step D3.N.7: Update `pages/secrets-manifest.md`.**

Append row for each secret variable:
```
| <SECRET_NAME> | Air | tools/<name>.sh | <rotation cadence, e.g., quarterly> | <last-rotated date or "never"> |
```

- [ ] **Step D3.N.8: Update audit §3.**

Same as D2.N.10; mark migration as `MIGRATED-WITH-SECRETS`.

**Same stop-gate discipline as D2.**

---

### Task D4: Dead-code resolution (5-test gate + per-script Madi ack)

For each script initially flagged DEAD-CODE-CANDIDATE in D1:

- [ ] **Step D4.N.1: Test 1 — run history proof.**

Run:
```bash
ssh air "launchctl print gui/\$(id -u)/<label>" 2>/dev/null | grep -E 'last exit code|runs'
```
Also check journald (if available) or the script's designated log file for the last 30 days. Record:
- Last exit code
- Runs count in last 30 days
- Last stdout-producing run date (or "none")

**Pass condition:** no stdout-producing successful run in 30 days OR every run produces stderr-only / empty stdout.
**Fail condition:** any successful run with real stdout in last 30 days → demote this script from DEAD-CODE-CANDIDATE to MIGRATE-CLEAN (or WITH-SECRETS).

- [ ] **Step D4.N.2: Test 2 — reverse call-graph proof.**

Run the 3 greps from SPEC §3 Test 2 (vault + Air + VPS). Record: list of external callers (if any). Exclude the script's own plist + the script itself.

**Pass:** zero external callers.
**Fail:** any caller → demote.

- [ ] **Step D4.N.3: Test 3 — doctrine proof.**

Run:
```
mcp__gbrain__search  query="<script_basename>"
mcp__nous-wiki-qmd__query  searches=[{type:'lex', query:'<script_basename>'}]
```
Record: any active-doctrine mentions (skills, laws, specs) in last 10 sessions. Distinguish "obsolete" mentions (OK) from "active" mentions (NOT OK).

**Pass:** zero active-doctrine mentions OR all mentions are marked obsolete.
**Fail:** active mention → demote.

- [ ] **Step D4.N.4: Test 4 — Madi per-script confirmation.**

Compose a message to Madi:
> "DEAD-CODE candidate: **<label>** (`<script_path>`).
> Purpose per my reading: <1-2 sentence reconstruction>.
> Evidence:
> - Test 1 (run history): <result summary>
> - Test 2 (call graph): <zero external callers | N callers>
> - Test 3 (doctrine): <zero mentions | N obsolete mentions>
> - Restoration recipe captured: yes (step D4.N.5).
> Proceed to delete this specific script? (y/n)"

Wait for explicit per-script "yes". No batch consent.

**Pass:** "yes" from Madi for THIS script.
**Fail:** "no" or "not sure" → demote (if "not sure", treat as demote-to-MIGRATE-CLEAN).

- [ ] **Step D4.N.5: Test 5 — restoration recipe.**

Capture:
```bash
# Plist git history (if tracked)
git log --all --oneline -- <plist-path-if-in-vault> | head -5
# Script git history (if tracked)
git log --all --oneline -- <script-vault-path> | head -5
# Generate restoration recipe
echo "# Restore <label> if deletion was wrong:
git show <latest-sha>:<plist-path> > /tmp/<label>.plist
ssh air 'cp /tmp/<label>.plist ~/Library/LaunchAgents/'
git show <latest-sha>:<script-path> > /tmp/<name>.sh
ssh air 'cp /tmp/<name>.sh ~/nous-agaas/tools/'
ssh air 'launchctl load ~/Library/LaunchAgents/<label>.plist'" > /tmp/restore_<label>.md
```

If script was Air-only and never committed anywhere: Test 5 FAILS (cannot provide provable restoration recipe); demote to MIGRATE-CLEAN and commit to vault before considering deletion.

**Pass:** concrete 3-5 line recipe exists, verified against real git blobs.
**Fail:** no git history → demote + migrate first.

- [ ] **Step D4.N.6: If ALL 5 tests pass, execute deletion.**

```bash
ssh air "launchctl bootout gui/\$(id -u)/<label>" && \
  ssh air "rm -f ~/Library/LaunchAgents/<plist-filename>" && \
  ssh air "rm -f <script-path>"
```
Verify:
```bash
ssh air "launchctl list | grep <label>"
```
Expected: empty.

- [ ] **Step D4.N.7: Record deletion in audit §4.**

Append to audit page §4:
```
### Deleted: <label>

- **Script:** `<script-path>`
- **Plist:** `<plist-path>`
- **Test 1 (run history):** <evidence block>
- **Test 2 (call graph):** <evidence block>
- **Test 3 (doctrine):** <evidence block>
- **Test 4 (Madi ack):** confirmed at <ISO timestamp>
- **Test 5 (restoration recipe):**
  ```
  <recipe from D4.N.5>
  ```
- **Deletion timestamp:** <ISO>
```

- [ ] **Step D4.N.8: Push gbrain timeline entry for the deletion.**

```
mcp__gbrain__add_timeline_entry
  slug = "pages/audits/audit-air-tools-inventory-2026-04-18"
  date = "2026-04-18"
  summary = "Deleted Air launchd job <label> per D4 5-test proof-of-deadness (run history quiet 30+ days / zero external callers / zero active doctrine / Madi confirmed / restoration recipe preserved). Session 46-B."
  source = "session-46-B air-tools-migration D4"
```

- [ ] **Step D4.N.9: Commit audit update.**

```bash
git add pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md && \
  git commit -m "audit: D4 deletion — <label> proved dead + removed (session 46-B) [risk] REQ-046" && \
  git push vps main
```

---

### Task D5: Extend wiki-to-runtime-rsync scope to include `tools/`

**Files:**
- Read + modify: `wiki-to-runtime-rsync` script (location TBD; likely `tools/wiki-to-runtime-rsync.sh` in vault, or vault-tracked from D0)

- [ ] **Step D5.1: Locate the rsync script + its plist.**

Run:
```bash
ssh air "launchctl list | grep -i rsync"
ssh air "ls ~/Library/LaunchAgents/ | grep -i rsync"
```
Expected: identify `com.nous.wiki-to-runtime-rsync` or similar.

Read the referenced script:
```bash
ssh air "cat <rsync-script-path>"
```

- [ ] **Step D5.2: Identify current rsync source filter.**

Look for `--include` / `--exclude` or explicit source-dir list. Current state per AP-29 (session 37.6): only `pages/skills/` is rsync'd to Air runtime.

- [ ] **Step D5.3: Extend scope to include `tools/`.**

Edit script to include both `pages/skills/` AND `tools/`. Exact edit depends on current shape:
- If `--include='pages/skills/'` list style: add `--include='tools/' --include='tools/*.sh'`.
- If explicit source dirs: add `tools/` as a second rsync invocation or a second source arg.

- [ ] **Step D5.4: Write or extend sibling test for the rsync script (AP-36).**

Create `tools/test_<rsync-script-name>.sh` if missing. Scenarios:
- ACCEPT: vault `tools/foo.sh` change → after rsync, Air `~/nous-agaas/tools/foo.sh` has matching MD5.
- ACCEPT: vault `pages/skills/foo/SKILL.md` change → Air `/Users/madia/nous-agaas/skills/foo/SKILL.md` has matching MD5.
- REJECT-equivalent: vault has `.git/` dir → Air should NOT receive `.git/` (rsync --exclude).

Since the rsync script runs against live Air and real vault, the test is an integration test: touch a canary file in vault `tools/`, run rsync script locally (or observe next scheduled run), verify Air received it.

- [ ] **Step D5.5: Deploy edited rsync script.**

If the script is vault-sourced: edit in vault, then D2 migration pattern (test + commit + rsync + observe).
If the script is Air-only (UNLIKELY given AP-29 scope): do D2 migration first (Air → vault), then edit.

- [ ] **Step D5.6: Test end-to-end: vault edit → rsync → Air.**

```bash
echo "# canary $(date +%s)" >> "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/__canary__.sh"
# Wait for next rsync cycle (depends on launchd schedule)
sleep <cycle-period>
ssh air "cat ~/nous-agaas/tools/__canary__.sh"
# Expected: contains the canary line
rm "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/__canary__.sh"
```

- [ ] **Step D5.7: Update infrastructure SKILL.md Timeline with D5 completion.**

Add Timeline line noting D5 rsync scope extension; AP-29 scope-gap fully closed.

- [ ] **Step D5.8: Commit.**

Standard commit pattern.

---

### Task D6: Absorb learnings into SKILL.md (RULE ZERO)

**Files:**
- Modify: `pages/skills/infrastructure/SKILL.md` (AP-39 + AP-40 if applicable + H1 drift fix + version bump + Timeline)
- Modify: `pages/skills/audit/SKILL.md` (AP-14 + version bump + Timeline)

- [ ] **Step D6.1: Add AP-39 to `infrastructure` SKILL.md.**

Read SKILL.md; find the last AP entry; append AP-39 with this structure:

```markdown
### AP-39 — Proof-of-deadness 5-test gate for launchd (session 46-B, 2026-04-18)

**Symptom:** During Air `tools/` migration (session 46-B D4), multiple `com.nous.*` launchd jobs appeared obsolete. The "easy way" would have been to delete them based on name-level reasoning ("probably the old poller, superseded by X"). The "right way" (Karpathy/Tan/Finn pattern) requires evidence.

**Root cause (meta):** Agents are biased toward confident deletion when a script "looks dead." Batch consent + vibe-based reasoning is how real dependencies get accidentally severed. The cost of false-delete (mysterious outage weeks later) vastly exceeds the cost of proof.

**Rule:** A launchd-registered script is DEAD-CODE only if **all 5 evidence tests pass**. No exceptions.

1. **Run history proof:** 30-day launchd + journald review; no successful stdout-producing run, OR every run is stderr-only/empty.
2. **Reverse call-graph proof:** vault + Air + VPS grep for basename; zero external callers.
3. **Doctrine proof:** gbrain + QMD search; zero active mentions in last 10 sessions (obsolete mentions OK).
4. **Madi confirmation:** per-script; agent states label + purpose + evidence + restoration; Madi explicit "yes" for THIS script.
5. **Restoration recipe:** concrete 3-5 line shell recipe from git blobs, verified to restore a running state. If script was Air-only (no git history): Test 5 FAILS; demote to MIGRATE bucket, commit to vault first, then re-evaluate.

If ANY test fails: script is NOT dead-code. Demote to MIGRATE-CLEAN / MIGRATE-WITH-SECRETS. Keep running.

**Absorbed as:** AP-39. Amends no prior AP. Compounds: future cleanups (BDL camera configs, old VPS crons, legacy Mac scripts) inherit the same 5-test gate mechanically.
```

- [ ] **Step D6.2: If any concrete surprise hit during D0-D5, absorb as AP-40.**

Examples of what might become AP-40: plist path gotcha (e.g., `~/Library/LaunchAgents/` vs `/Library/LaunchAgents/`); launchd env var surprise (e.g., `$HOME` undefined); rsync race (vault edit during rsync in-flight); MD5 parity failing due to line-ending diff (LF vs CRLF).

If NO surprise hit: AP-40 not created; note in audit "no new AP-40 this session; AP-39 only."

- [ ] **Step D6.3: H1 drift — ALREADY FIXED by parallel session commit `dfc0f06f` (mistake-to-skill v1.8 AP-11).**

Parallel session caught + fixed all 7 H1 drifts (including infrastructure v2.29→v2.32 and evidence-verification v1.5→v1.6) before session 46-B reached D6. No action needed here.

**But:** after A2.6 (which will bump infrastructure to v2.32.1) and after D6.4 (v2.33.0), re-verify H1 matches frontmatter. Run `tools/test_skill_version_parity.sh` (shipped by parallel session) to mechanically check; exit 0 = clean.

- [ ] **Step D6.4: Bump infrastructure version + add Timeline entry.**

Update frontmatter `version:` and Timeline:
```
- **2026-04-18** | v2.32.1 → v2.33.0 — Session 46-B D6 absorbs AP-39 (proof-of-deadness 5-test gate for launchd deletion; compound pattern from AP-27 closure). Also fixes H1 drift (was v2.29.0 since session 40; now matches frontmatter). RULE ZERO upheld; zero new LESSON files.
```

- [ ] **Step D6.5: Add AP-14 to `audit` SKILL.md.**

Read `pages/skills/audit/SKILL.md`. Append:

```markdown
### AP-14 — Air `tools/` MD5 parity at session open + close (session 46-B, 2026-04-18)

**Symptom:** Before AP-27 closure, Air `~/nous-agaas/tools/*.sh` had no parity check with vault `tools/*.sh`. Drift was possible + undetectable.

**Rule:** At session open AND close, for every script currently classified MIGRATE-CLEAN or VAULT-ALREADY in the latest Air-tools-migration audit:
```bash
for SCRIPT in <migrated list>; do
  AIR_MD5=$(ssh air "md5 -q ~/nous-agaas/tools/$SCRIPT")
  VAULT_MD5=$(md5 -q "$(git rev-parse --show-toplevel)/tools/$SCRIPT")
  [ "$AIR_MD5" = "$VAULT_MD5" ] || echo "DRIFT: $SCRIPT (Air=$AIR_MD5 Vault=$VAULT_MD5)"
done
```
Zero drift lines expected. Any drift → session gate FAIL; fix before proceeding.

**Amends:** AP-10 pt 2 (4-target MD5 parity). Extends parity check from skills to tools.
```

- [ ] **Step D6.6: Bump audit SKILL.md version to v1.13 + Timeline.**

```
- **2026-04-18** | v1.12.0 → v1.13.0 — Session 46-B adds AP-14 (Air tools MD5 parity at session open + close). Compounds: every future session opens by asserting `tools/*.sh` parity across Mac vault + Air runtime; drift triggers gate FAIL mechanically.
```

- [ ] **Step D6.7: Push gbrain timeline entries for both skill bumps.**

```
mcp__gbrain__add_timeline_entry
  slug = "pages/skills/infrastructure/skill"
  date = "2026-04-18"
  summary = "v2.32.1 → v2.33.0 — AP-39 proof-of-deadness 5-test gate + H1 drift fix. Session 46-B D6. Compounds: AP-27 closure procedure inherits to all future cleanups. Also AP-40 <if present, describe>."
  source = "session-46-B air-tools-migration D6"

mcp__gbrain__add_timeline_entry
  slug = "pages/skills/audit/skill"
  date = "2026-04-18"
  summary = "v1.12.0 → v1.13.0 — AP-14 Air tools MD5 parity at session open + close. Extends AP-10 pt 2. Session 46-B D6."
  source = "session-46-B air-tools-migration D6"
```

- [ ] **Step D6.8: Commit skill changes.**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && \
  git add pages/skills/infrastructure/SKILL.md pages/skills/audit/SKILL.md && \
  git commit -m "skills: infrastructure v2.33 (AP-39 proof-of-deadness) + audit v1.13 (AP-14 Air tools parity) — session 46-B D6 [risk] REQ-046" && \
  git push vps main
```

- [ ] **Step D6.9: Verify 4-target MD5 parity after skill bumps.**

Run the 4-target MD5 probe from session open (reprised):
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills" && \
  MAC=$(find . -maxdepth 2 -name SKILL.md -not -path "*/_gbrain/*" -not -path "*/extracted/*" -exec md5 -q {} \; | sort | md5 -q) && \
  ssh root@65.108.215.200 "cd /root/nous-agaas/wiki/pages/skills && find . -maxdepth 2 -name SKILL.md -not -path '*/_gbrain/*' -not -path '*/extracted/*' -exec md5sum {} \; | awk '{print \$1}' | sort | md5sum | awk '{print \$1}'" > /tmp/vps.md5 && \
  ssh air "cd ~/nous-agaas/wiki/pages/skills && find . -maxdepth 2 -name SKILL.md -not -path '*/_gbrain/*' -not -path '*/extracted/*' -exec md5 -q {} \; | sort | md5 -q" > /tmp/airwiki.md5 && \
  ssh air "cd /Users/madia/nous-agaas/skills && find . -maxdepth 2 -name SKILL.md -exec md5 -q {} \; | sort | md5 -q" > /tmp/airrt.md5 && \
  echo "Mac:$MAC VPS:$(cat /tmp/vps.md5) AirWiki:$(cat /tmp/airwiki.md5) AirRT:$(cat /tmp/airrt.md5)"
```
Expected: all 4 match.

If parity fails: it may be that wiki-to-runtime-rsync hasn't propagated yet (D5 extended scope to `tools/` but skills should already sync). Wait 5 min, re-run. If still fails: investigate.

---

### Task D7: Close audit + handoff + MEMORY prepend

**Files:**
- Modify: `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` §5 (final state)
- Create: `pages/progress/HANDOFF-AUTO-2026-04-18-session-46-air-tools.md`
- Modify: `pages/progress/claude-memory/MEMORY.md` (prepend session-46-B block)

- [ ] **Step D7.1: Run AP-10 v1.12 7-point close audit.**

Repeat all session-open probes:
1. 3 mandatory session gates (website lock, no code/satory, memory symlink)
2. 4-way vault HEAD parity
3. 4-target skill MD5 parity (with AP-13 host-side path)
4. LESSON fs count = 129
5. pre-commit, pre-push, TaskCompleted, pre-receive hook MD5 all intact
6. gbrain health (brain_score, pages_by_type.skill=21, lesson=129)
7. QMD needsEmbedding=0

Also run **new AP-14:** Air tools MD5 parity for all MIGRATED scripts.

Record results in audit §5.

- [ ] **Step D7.2: Update audit §5 with final state table.**

```
## 5. Final state (D7 close)

| # | Label | Final bucket | Status | Vault commit | Deletion ts (if applicable) | Handoff next-step (if applicable) |
|---|---|---|---|---|---|---|
```

One row per script in inventory. Fill final bucket + status:
- **MIGRATED** (D2 or D3 completed)
- **DELETED** (D4 5-test pass + Madi ack)
- **HANDOFF** (not started + not completed this session; include concrete next-step)
- **VAULT-ALREADY-SYNCED** (was already in vault; MD5 parity verified)

- [ ] **Step D7.3: Close-audit summary paragraph.**

Append to audit §5:
```
**Session 46-B close summary (2026-04-18):**
- Total com.nous launchd jobs inventoried: N.
- Bucket distribution: VAULT-ALREADY=A, MIGRATE-CLEAN=B (MIGRATED=B_done, HANDOFF=B_pending), MIGRATE-WITH-SECRETS=C (MIGRATED=C_done, HANDOFF=C_pending), DEAD-CODE=D (DELETED=D_done, DEMOTED=D_demoted).
- AP-27 status: <CLOSED if 100% migrated/deleted/vault-already | PARTIAL if honest handoff remains>.
- AP-10 7-point close: <PASS | specific FAIL codes>.
- New APs absorbed: infrastructure AP-39 (+ AP-40 if applicable), audit AP-14.
- gbrain timeline entries pushed: <count>.
- RULE ZERO compliance: 0 new LESSON files (verified).
```

- [ ] **Step D7.4: Write handoff file.**

Create `pages/progress/HANDOFF-AUTO-2026-04-18-session-46-air-tools.md` following session-45 handoff structure (TL;DR, phase-by-phase table, drift absorbed, APK bot status, remaining work, sync state at close, skill versions, gbrain timeline entries pushed, rule compliance, session-47 opening moves).

- [ ] **Step D7.5: Prepend session-46-B block to MEMORY.md.**

Edit MEMORY.md. Insert new block between the H1 (line 12) and the parallel session's "Session 46 (2026-04-18 Mac-interactive) — GOD_PROMPT v1.0..." block:

```
## Session 46-B (2026-04-18 Mac-interactive, Air tools migration thread) — AP-27 closure + Phase A hygiene complete: token rotated + AP-36 self-violation closed + aggregator cron live + N scripts migrated (M deleted-with-evidence, K handoff). New APs: infrastructure v2.33 AP-39 (proof-of-deadness 5-test gate) + audit v1.13 AP-14 (Air tools MD5 parity at open+close). 4-way vault parity `<HEAD>` at close.

Triggered by Madi: *"... plan everything, execute atomic 1-by-1, quality matters, 100% or stop and handoff, all saved + synced everywhere, no lie no BS, using obsidian + gbrain + karpathy, find root cause + fix + retry, success → new skill ..."*

<full narrative block — phases, APs, drift caught, parallel session coordination, open items>
```

- [ ] **Step D7.6: Final 4-way vault sync verify.**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && git rev-parse HEAD && \
  ssh root@65.108.215.200 "cd /root/nous-agaas/wiki && git rev-parse HEAD; cd /root/nous-agaas/obsidian-wiki.git && git rev-parse HEAD" && \
  ssh air "cd ~/nous-agaas/wiki && git rev-parse HEAD"
```
Expected: all 4 match.

- [ ] **Step D7.7: Push final gbrain timeline entry for session close.**

```
mcp__gbrain__add_timeline_entry
  slug = "pages/progress/handoff-auto-2026-04-18-session-46-air-tools"
  date = "2026-04-18"
  summary = "Session 46-B (Air tools migration thread) close. AP-27 <status>. N migrated + M deleted + K handoff. New APs: infrastructure v2.33 AP-39 + audit v1.13 AP-14. 4-way vault parity. Zero LESSON files created."
  source = "session-46-B close"
```

- [ ] **Step D7.8: Announce close to Madi.**

Message Madi:
> "Session 46-B close. Full report in HANDOFF-AUTO-2026-04-18-session-46-air-tools.md.
> - AP-27 status: <CLOSED / PARTIAL>
> - <N> scripts migrated, <M> deleted-with-evidence, <K> handoff
> - AP-39 (proof-of-deadness) + AP-14 (tools parity) absorbed
> - 4-way sync at <HEAD>
> Carryovers for session 47: <bulleted list>
> Compounding payoff: <1-sentence summary of what future sessions now inherit mechanically>."

---

## Self-review (agent runs this after plan is written)

1. **Spec coverage:**
   - SPEC §2 Phase A → Tasks A0, A1, A2, A3, A4 ✓
   - SPEC §2 Phase D D0 → Task D0 ✓
   - SPEC §2 Phase D D1 → Task D1 ✓
   - SPEC §2 Phase D D2 → Task D2 (per-script loop) ✓
   - SPEC §2 Phase D D3 → Task D3 (per-script loop) ✓
   - SPEC §2 Phase D D4 → Task D4 (per-script loop, 5-test gate) ✓
   - SPEC §3 proof-of-deadness 5 tests → Task D4.N.1-D4.N.5 ✓
   - SPEC §2 Phase D D5 → Task D5 ✓
   - SPEC §2 Phase D D6 → Task D6 (AP-39 + AP-40 + AP-14 + H1 drift fix) ✓
   - SPEC §2 Phase D D7 → Task D7 ✓
   - SPEC §7 close-audit criteria → Task D7.1 ✓
   - SPEC §9 open questions → surfaced at start of D0 and D2 ✓
   - SPEC §10 anti-patterns → implicitly avoided; "easy way" shortcuts not present in plan steps ✓

2. **Placeholder scan:**
   - "TBD" only in file structure table (MIGRATE-CLEAN bucket size TBD from D0) — legitimate, not a plan failure.
   - No "TODO", "implement later", "add appropriate error handling", or "similar to Task N" references.
   - Per-script loops are written once with `D2.N.X` syntax; executor repeats per script — acceptable pattern for variable-count loops.

3. **Type/name consistency:**
   - Bucket names: VAULT-ALREADY, VAULT-ALREADY-DRIFT, MIGRATE-CLEAN, MIGRATE-WITH-SECRETS, DEAD-CODE-CANDIDATE, UNKNOWN — used consistently.
   - AP numbers: AP-39 (my proof-of-deadness), AP-40 (surprise-tbd), AP-14 (audit Air tools parity) — checked against current fs state (AP-37/AP-38 taken by parallel session) ✓.
   - Paths: `/Users/madia/nous-agaas/skills/` (host-side per AP-13) vs `/opt/nous-agaas/skills/` (container-side) — correct throughout.
   - Remote name: `vps` (not `origin`) — correct throughout.

4. **Gaps found + fixed:** none surfaced; plan is comprehensive against SPEC.

---

## Timeline

- **2026-04-18** | Plan written; Madi approved scope + delete-with-evidence policy; SPEC + PLAN committed to vault [[SPEC-AIR-TOOLS-MIGRATION-V1-2026-04-18]]
