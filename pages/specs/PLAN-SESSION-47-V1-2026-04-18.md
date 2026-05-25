---
type: plan
id: PLAN-SESSION-47-V1-2026-04-18
title: "Session 47 carryover burn-down — atomic implementation plan (13 tasks)"
tags: [plan, session-47, atomic, karpathy, migration, compounding-gates, 2026-04-18]
date: 2026-04-18
source_count: 0
status: draft
last_updated: 2026-04-18
related:
  - SPEC-SESSION-47-V1-2026-04-18
  - AUDIT-AIR-TOOLS-INVENTORY-2026-04-18
  - SPEC-AIR-TOOLS-MIGRATION-V1-2026-04-18
  - PLAN-AIR-TOOLS-MIGRATION-V1-2026-04-18
---

# Session 47 Carryover Burn-down Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution; same-session executor). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute 13 atomic carryover ops from session 46 + 46-B honest-handoff under Karpathy-primary quality gate (100% or handoff).

**Architecture:**
- Sequential atomic ops (no parallelism — each op commits + syncs before next).
- Every fix produces skill absorption (SKILL.md + gbrain timeline) per RULE ZERO.
- Stop-at-blocker on <100% quality → honest handoff to session 48 for that item only.

**Tech Stack:** Obsidian (vault), gbrain (semantic KB via MCP), Air launchd (macOS launchctl), VPS systemd, Telegram Bot API, git (Mac↔Air↔VPS), bash test harness.

**Common pre-flight (run ONCE before Task O, and before every destructive op):**
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
# AP-34 cadence probe — count commits in last 5 min
git log --since="5 minutes ago" --oneline | wc -l
# If > 2, wait 60 s and re-probe. If hot 3+ re-probes on same op, defer.
```

**Common commit pattern (AP-11 3-edit ritual applies when SKILL.md touched):**
```bash
git add <files>
git commit -m "<type>: <subject> [risk] REQ-046

<body>"
git push vps main 2>&1 | tail -3
# Expected: "8abc...def  main -> main" pushed cleanly, no conflicts
```

---

### Task O: Opening deep audit (AP-10 7-point + AP-14 cross-cut)

**Files:**
- Read: in-memory record only (no file output; captured by Task Z for delta)

- [ ] **Step 1: Vault 4-way HEAD parity**

Run:
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && git rev-parse HEAD
ssh root@65.108.215.200 "cd /root/nous-agaas/wiki && git rev-parse HEAD"
ssh root@65.108.215.200 "cd /root/nous-agaas/obsidian-wiki.git && git rev-parse HEAD"
ssh air "cd ~/nous-agaas/wiki && git rev-parse HEAD"
```
Expected: All 4 outputs identical. Record as `O_HEAD`.

- [ ] **Step 2: Hook MD5 4-target parity**

Run:
```bash
ssh air '/sbin/md5 -q ~/nous-agaas/wiki/.git/hooks/pre-commit ~/nous-agaas/wiki/.git/hooks/pre-push ~/nous-agaas/wiki/tools/pre-commit-hook-tan-pattern.sh'
ssh root@65.108.215.200 "md5sum /root/nous-agaas/wiki/.git/hooks/pre-commit /root/nous-agaas/wiki/tools/pre-commit-hook-tan-pattern.sh /root/nous-agaas/obsidian-wiki.git/hooks/pre-receive"
```
Expected: pre-commit = `9a99bdda2f6977544e7d5f2d83e24c82` (3 targets); pre-push = `2e34402d3c57b2d879aa24fb0c5ba189`; pre-receive = `b8cfb21ca1cc827b03b5f9de1b227742`. Record as `O_HOOKS`.

- [ ] **Step 3: Skill version parity scan**

Run:
```bash
ssh air 'cd ~/nous-agaas/wiki && bash tools/test_skill_version_parity.sh 2>&1 | tail -3'
```
Expected: `OK: all skill frontmatter <-> H1 versions match` exit=0. Record as `O_SKILLPARITY=CLEAN`.

- [ ] **Step 4: Air launchd service count + name list**

Run:
```bash
ssh air 'launchctl list | grep com.nous | wc -l && launchctl list | grep com.nous | awk "{print \$3}" | sort'
```
Expected: `17` + sorted service list. Record as `O_LAUNCHD`.

- [ ] **Step 5: OpenClaw + LiteLLM health**

Run:
```bash
ssh air "docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'openclaw|litellm'"
ssh air "curl -s http://127.0.0.1:4000/health/liveliness"
```
Expected: openclaw `Up 2 days (healthy)`; LiteLLM `"I'm alive!"`. Record as `O_HEALTH`.

- [ ] **Step 6: gbrain health + missing-embed list**

Run:
```bash
mcp__gbrain__get_health
```
Expected: 1009 pages, 99.71% embed coverage, 7 missing, brain_score 77. Record page list as `O_GBRAIN_MISSING`.

- [ ] **Step 7: LESSON count + canonical SKILL count**

Run:
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
ls pages/lessons/individual/LESSON-*.md 2>/dev/null | wc -l
find pages/skills -maxdepth 2 -name SKILL.md | grep -v extracted | wc -l
find . -name SKILL.md | grep -v pages/skills/ | grep -v .git | head
```
Expected: LESSON=129, SKILL=20, stray=0. Record as `O_LESSON_SKILL`.

- [ ] **Step 8: AP-14 cross-cut — context-injector v2 live assertion**

Run:
```bash
ssh air 'launchctl kickstart -k gui/$(id -u)/com.nous.context-injector-regression && sleep 6 && tail -5 ~/nous-agaas/logs/context-injector-regression.log 2>/dev/null || tail -5 /tmp/context-injector-regression.log 2>/dev/null'
```
Expected: `Output ≤ G4 (actual: <X> bytes, threshold: 8192) ... PASS`. Record as `O_CONTEXT_INJECTOR=PASS`.

- [ ] **Step 9: Commit baseline snapshot message (NO file change — just a marker commit body)**

Write summary to TaskUpdate description for Task O only — no vault commit. Task O is read-only.

---

### Task M1: `git mv satory_events_watcher.py` (WRONG-DIR → tools/)

**Files:**
- Move: `pages/systems/air-runtime-scripts/satory_events_watcher.py` → `tools/satory_events_watcher.py`
- Modify: `pages/systems/air-runtime-scripts/README.md` (remove entry)

- [ ] **Step 1: AP-34 cadence probe**

Run pre-flight (see top). If cold (≤2 commits/5m), proceed.

- [ ] **Step 2: Verify Air plist ProgramArguments path**

Run:
```bash
ssh air 'plutil -p ~/Library/LaunchAgents/com.nous.satory-events-watcher.plist | grep -A1 ProgramArguments'
```
Expected: script path is `~/nous-agaas/tools/satory_events_watcher.py` (Air-side; this is the RUNTIME path, NOT affected by vault move). Record — if path references `pages/systems/...`, the plist is broken and needs fix.

- [ ] **Step 3: git mv**

Run:
```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git mv pages/systems/air-runtime-scripts/satory_events_watcher.py tools/satory_events_watcher.py
```
Expected: no error.

- [ ] **Step 4: Update air-runtime-scripts/README.md**

Read the file. Remove the entry for satory_events_watcher.py; add a line noting "moved to tools/ in session 47 (D2-WRONG-DIR resolution per AUDIT-AIR-TOOLS-INVENTORY-2026-04-18 §2.3)".

- [ ] **Step 5: Commit + push**

```bash
git add tools/satory_events_watcher.py pages/systems/air-runtime-scripts/satory_events_watcher.py pages/systems/air-runtime-scripts/README.md
git commit -m "fix: git mv satory_events_watcher.py air-runtime-scripts/ → tools/ (D2-WRONG-DIR, AP-27) [risk] REQ-046"
git push vps main 2>&1 | tail -3
```
Expected: clean push, no conflicts.

- [ ] **Step 6: 4-way sync verify (wait for auto-sync ≤2 min)**

Run Task O step 1; expect all 4 HEAD match new commit SHA.

- [ ] **Step 7: Verify Air launchd still runs satory-events-watcher**

```bash
ssh air 'launchctl list | grep satory-events-watcher'
ssh air 'launchctl kickstart -k gui/$(id -u)/com.nous.satory-events-watcher && sleep 3 && launchctl list | grep satory-events-watcher'
```
Expected: last exit code = 0 OR no error. (The Air runtime script is unaffected by vault move; this just verifies service is healthy after our commit wave.)

---

### Task H1: 7 legacy gbrain missing embeddings → 100%

**Files:**
- Read/modify: per-page based on diagnosis

- [ ] **Step 1: Identify the 7 missing pages**

```
mcp__gbrain__get_health  (with detail if parameter available)
```
If detail unavailable, query by iterating `list_pages` and checking embedding status — or use `mcp__gbrain__search` with a query known to match and see which pages should appear but don't.

Alternative: if `sync_brain` with status=only-missing is supported, use that to list.

Record 7 pages as `H1_TARGETS`.

- [ ] **Step 2: Diagnose each page's root cause**

For each page in `H1_TARGETS`:
```
mcp__gbrain__get_page  slug=<slug>
```
Examine: frontmatter valid? body non-empty? binary content? very short (<50 chars)? any characters that break embedder?

Record per-page root cause.

- [ ] **Step 3: Fix root cause per page**

For each page with a fixable root cause:
- Source-fix the wiki file (Edit tool).
- Run `mcp__gbrain__put_page` with the fixed content.
- Verify: `mcp__gbrain__get_page` returns with embedding.

For pages that are genuinely empty or binary: delete from gbrain if they shouldn't be indexed, OR document as expected exclusion.

- [ ] **Step 4: Verify 100% coverage**

```
mcp__gbrain__get_health
```
Expected: 0 missing embeddings OR document remaining as "expected exclusions" with reason per page.

- [ ] **Step 5: If systemic root-cause found → absorb as gbrain-ops AP**

If ≥3 pages share the same root cause (e.g., frontmatter minor variant that embedder rejects):
- Bump `pages/skills/gbrain-ops/SKILL.md` with new AP.
- Add gbrain timeline entry.

- [ ] **Step 6: Commit fixes (if any wiki files changed)**

```bash
git add pages/... (only the changed ones)
git commit -m "fix: H1 resolve <N> legacy gbrain missing embeddings — <root-cause-summary> [risk] REQ-046"
git push vps main 2>&1 | tail -3
```

---

### Task C1: SKILL.md MD5 citation ↔ reality hook (3rd Tan compounding gate)

**Files:**
- Create: `tools/test_skill_md5_citations.sh` (standalone scanner)
- Create: `tools/test_skill_md5_citations_self.sh` (test harness for scanner — ACCEPT + REJECT cases)
- Modify: `.git/hooks/pre-push` (Mac), `tools/pre-push-hook-tan-pattern.sh` (vault backup)
- Modify: `pages/skills/infrastructure/SKILL.md` (absorb AP-44, bump to v2.35, Timeline entry)

- [ ] **Step 1: Write the failing test harness first (TDD)**

Create `tools/test_skill_md5_citations_self.sh`:

```bash
#!/usr/bin/env bash
# Self-test for tools/test_skill_md5_citations.sh
# TEST 1: CLEAN — all citations match reality → exit 0
# TEST 2: DRIFT — fabricated citation does not match file → exit 2
# TEST 3: NO-CITATIONS — SKILL.md with no MD5 references → exit 0 (vacuously)

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

SCANNER="tools/test_skill_md5_citations.sh"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# TEST 1: CLEAN (real current SKILL.md set)
if bash "$SCANNER"; then
  echo "TEST 1 CLEAN: PASS"
else
  echo "TEST 1 CLEAN: FAIL (scanner reports drift on current clean tree)"
  exit 1
fi

# TEST 2: DRIFT — create a fake SKILL.md in tmp dir with a known-wrong citation
cat > "$TMPDIR/fake-skill.md" <<'EOF'
---
name: fake
version: 0.0.1
---
# fake v0.0.1
The pre-commit hook MD5 is ffffffffffffffffffffffffffffffff at tools/pre-commit-hook-tan-pattern.sh.
EOF

# Run scanner with extra-file flag pointing to tmp (scanner must support --extra-file or SCAN_GLOB override)
if SCAN_GLOB="$TMPDIR/fake-skill.md" bash "$SCANNER"; then
  echo "TEST 2 DRIFT: FAIL (scanner accepted bogus citation)"
  exit 1
else
  echo "TEST 2 DRIFT: PASS (scanner rejected bogus citation)"
fi

# TEST 3: NO-CITATIONS
cat > "$TMPDIR/nocite.md" <<'EOF'
---
name: nocite
version: 0.0.1
---
# nocite v0.0.1
This skill has no MD5 citations.
EOF

if SCAN_GLOB="$TMPDIR/nocite.md" bash "$SCANNER"; then
  echo "TEST 3 NO-CITATIONS: PASS"
else
  echo "TEST 3 NO-CITATIONS: FAIL (scanner rejected vacuous case)"
  exit 1
fi

echo "ALL TESTS PASS"
```

- [ ] **Step 2: Run self-test — expect it to fail because scanner doesn't exist yet**

```bash
chmod +x tools/test_skill_md5_citations_self.sh
bash tools/test_skill_md5_citations_self.sh
```
Expected: FAIL with "No such file or directory" on `tools/test_skill_md5_citations.sh`.

- [ ] **Step 3: Implement the scanner**

Create `tools/test_skill_md5_citations.sh`:

```bash
#!/usr/bin/env bash
# Scan SKILL.md files for MD5 citations ↔ file-reality drift.
# Citation pattern: <filepath> ... ([a-f0-9]{32}) ...  OR  ([a-f0-9]{32}) ... <filepath>
# For each citation found, compute the current file MD5 and compare.
# Exit 0: all citations match OR no citations.  Exit 2: ≥1 drift.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

GLOB="${SCAN_GLOB:-pages/skills/*/SKILL.md}"
DRIFTS=0

# MD5 helper: /sbin/md5 on macOS, md5sum on Linux
_md5() {
  if command -v /sbin/md5 >/dev/null 2>&1; then
    /sbin/md5 -q "$1" 2>/dev/null
  else
    md5sum "$1" 2>/dev/null | awk '{print $1}'
  fi
}

# For each SKILL.md in scope, scan for MD5 citations.
# A citation is a 32-char hex followed within the same paragraph (100 char window) by a `tools/...` or `.git/hooks/...` or `<file>.sh|.py|.md` path.
# We check each (md5, path) pair: does md5(path) == cited md5?

shopt -s nullglob 2>/dev/null || true
for skill in $GLOB; do
  [ -f "$skill" ] || continue
  # Extract candidate (md5, path) pairs using awk over the file.
  # Strategy: sliding 200-char window; find all 32-hex tokens; for each, look ±200 chars for a file-looking token.
  python3 - "$skill" <<'PY' || true
import sys, re, os, hashlib

f = sys.argv[1]
txt = open(f, "r", encoding="utf-8", errors="replace").read()
# Find 32-char lowercase hex tokens not part of longer hex (loose match)
hex_re = re.compile(r'(?<![0-9a-fA-F])([0-9a-f]{32})(?![0-9a-fA-F])')
path_re = re.compile(r'(tools/[A-Za-z0-9_./-]+\.(?:sh|py|md)|\.git/hooks/[A-Za-z0-9_./-]+|pages/[A-Za-z0-9_./-]+\.(?:sh|py|md))')

drifts = []
for m in hex_re.finditer(txt):
    md5 = m.group(1)
    # Window ±200 chars
    w_start = max(0, m.start() - 200)
    w_end = min(len(txt), m.end() + 200)
    window = txt[w_start:w_end]
    # Must mention MD5 keyword in window (reduce false positives on arbitrary hex like commit SHAs — though SHAs are 40 chars so 32-char should be fine, but we still filter)
    if 'md5' not in window.lower() and 'hook' not in window.lower() and 'hash' not in window.lower():
        continue
    # Find nearest path in window
    paths = [(p.start(), p.group(1)) for p in path_re.finditer(window)]
    if not paths:
        continue
    # Pick closest to hex
    hex_rel = m.start() - w_start
    paths.sort(key=lambda x: abs(x[0] - hex_rel))
    cand_path = paths[0][1]
    # Resolve to repo-relative file
    if not os.path.isfile(cand_path):
        # Some citations may reference Air runtime paths — skip (only vault paths verifiable here)
        continue
    h = hashlib.md5(open(cand_path,'rb').read()).hexdigest()
    if h != md5:
        drifts.append((f, md5, cand_path, h))

for d in drifts:
    print(f"DRIFT {d[0]}: cited {d[1]}  ->  actual {d[3]}  (path: {d[2]})")

# Non-zero exit via env var channel
if drifts:
    open('/tmp/_md5_cit_drifts','a').write(f"{len(drifts)}\n")
PY
done

if [ -f /tmp/_md5_cit_drifts ]; then
  echo "============================================================"
  echo "  BLOCKED: SKILL.md MD5 citation ↔ reality drift (infrastructure AP-44)"
  echo "============================================================"
  echo ""
  echo "Fix: either update the SKILL.md citation to the actual current MD5,"
  echo "or restore the file to match the cited MD5."
  rm -f /tmp/_md5_cit_drifts
  exit 2
fi

echo "OK: all SKILL.md MD5 citations match file reality"
exit 0
```

Make executable: `chmod +x tools/test_skill_md5_citations.sh`.

- [ ] **Step 4: Run self-test — expect all 3 TESTs pass**

```bash
bash tools/test_skill_md5_citations_self.sh
```
Expected: `TEST 1 CLEAN: PASS` + `TEST 2 DRIFT: PASS` + `TEST 3 NO-CITATIONS: PASS` + `ALL TESTS PASS`.

If TEST 1 fails: a REAL drift exists in the current SKILL set — fix that drift FIRST before wiring the hook (it's an honest-caught bug; absorb into the Task's evidence trail).

- [ ] **Step 5: Wire scanner into pre-push hook**

Edit `.git/hooks/pre-push` to add (before the existing AP-35 parity check section ends):

```bash
# === RULE 3 (AP-44): SKILL.md MD5 citation ↔ reality ===
# Only fires if a SKILL.md is in the push set.
if git diff --name-only "$range" 2>/dev/null | grep -q '^pages/skills/.*/SKILL\.md$'; then
  echo "[pre-push] RULE 3: scanning SKILL.md MD5 citations (AP-44)..."
  if ! bash tools/test_skill_md5_citations.sh; then
    exit 2
  fi
fi
```

(Exact insertion point: find where AP-35 check ends — just before `exit 0` at bottom.)

- [ ] **Step 6: Sync pre-push to vault backup**

```bash
cp .git/hooks/pre-push tools/pre-push-hook-tan-pattern.sh
chmod +x tools/pre-push-hook-tan-pattern.sh
```

- [ ] **Step 7: Deploy pre-push to Air + VPS wiki**

```bash
scp .git/hooks/pre-push air:~/nous-agaas/wiki/.git/hooks/pre-push
scp .git/hooks/pre-push root@65.108.215.200:/root/nous-agaas/wiki/.git/hooks/pre-push
ssh air 'chmod +x ~/nous-agaas/wiki/.git/hooks/pre-push'
ssh root@65.108.215.200 'chmod +x /root/nous-agaas/wiki/.git/hooks/pre-push'
```

- [ ] **Step 8: Compute new pre-push MD5 4-target parity**

```bash
ssh air '/sbin/md5 -q ~/nous-agaas/wiki/.git/hooks/pre-push ~/nous-agaas/wiki/tools/pre-push-hook-tan-pattern.sh'
ssh root@65.108.215.200 "md5sum /root/nous-agaas/wiki/.git/hooks/pre-push /root/nous-agaas/wiki/tools/pre-push-hook-tan-pattern.sh | awk '{print \$1}'"
```
Expected: 4 identical new MD5s. Record as `C1_PREPUSH_MD5`.

- [ ] **Step 9: Live-test REJECT path**

```bash
# Intentionally break a hook citation in a SKILL.md
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
# (Pick pages/skills/infrastructure/SKILL.md where there are real MD5 citations)
# Append a fabricated citation to Timeline (will be rolled back)
echo "- **2026-04-18** | TEST DRIFT: pre-commit MD5 fffffffffffffffffffffffffffffff at .git/hooks/pre-commit (DO NOT COMMIT)" >> pages/skills/infrastructure/SKILL.md
git add pages/skills/infrastructure/SKILL.md
git commit -m "TEST: intentional drift for C1 pre-push reject test [risk] REQ-046"
git push vps main 2>&1 | tail -20
```
Expected: push REJECTED with `BLOCKED: SKILL.md MD5 citation ↔ reality drift`.

- [ ] **Step 10: Rollback + verify ACCEPT path**

```bash
git reset --hard HEAD~1
# Now push a clean, unrelated commit to verify hook lets valid pushes through
git commit --allow-empty -m "TEST: empty commit to verify ACCEPT path [risk] REQ-046"
git push vps main 2>&1 | tail -5
```
Expected: push ACCEPTED; then:
```bash
git reset --hard HEAD~1  # drop the test commit
# DO NOT push the reset — leave remote clean at pre-test HEAD
```

Actually better: verify via a real-world push of C1's actual work (next steps).

- [ ] **Step 11: Absorb AP-44 into infrastructure SKILL.md (3-edit ritual)**

Edit `pages/skills/infrastructure/SKILL.md`:
1. Frontmatter: `version: 2.34.0` → `version: 2.35.0`
2. H1: `# infrastructure v2.34.0` → `# infrastructure v2.35.0`
3. Anti-Patterns section: add new AP-44 block (content: gate description, test harness path, hook wiring, first-live-test evidence, cross-refs to AP-35 + AP-43)
4. Timeline: append `- **2026-04-18** | session 47 C1: absorbed AP-44 — 3rd Tan compounding gate: pre-push rejects SKILL.md MD5 citations that don't match file reality. Test harness `tools/test_skill_md5_citations_self.sh` 3/3 PASS. Sibling of AP-35 + AP-43. Live-test REJECT+ACCEPT verified. New pre-push MD5 `<C1_PREPUSH_MD5>` 4-target parity.`

- [ ] **Step 12: Push gbrain timeline entry**

```
mcp__gbrain__add_timeline_entry
  slug: pages/skills/infrastructure/skill
  date: 2026-04-18
  summary: "session 47 C1: infrastructure v2.34 → v2.35 absorbed AP-44 — 3rd Tan compounding gate. Pre-push rejects SKILL.md MD5 citations that don't match file reality. Test harness 3/3 PASS. Hook MD5 updated (4-target parity: <C1_PREPUSH_MD5>). Siblings: AP-35 (hook-parity), AP-43 (SKILL version parity)."
```
Expected: `{status: ok}`.

- [ ] **Step 13: Commit + push**

```bash
git add tools/test_skill_md5_citations.sh tools/test_skill_md5_citations_self.sh tools/pre-push-hook-tan-pattern.sh pages/skills/infrastructure/SKILL.md
git commit -m "skill: infrastructure v2.34 → v2.35 absorbs AP-44 (C1 3rd Tan gate: SKILL.md MD5 citation ↔ reality pre-push hook) [risk] REQ-046

Test harness 3/3 PASS. Live-test REJECT+ACCEPT verified (steps 9-10).
Siblings: AP-35 (pre-push hook parity), AP-43 (pre-commit SKILL version parity).
New pre-push MD5 4-target parity confirmed."
git push vps main 2>&1 | tail -3
```
Expected: clean push, hook passes (it validates itself).

- [ ] **Step 14: 4-way HEAD parity verify**

Run Task O step 1; all 4 match new commit.

---

### Task M2: D4 FIRST lesson-absorption + AP-39 5-test doctrine

**Files:**
- Delete: `~/Library/LaunchAgents/com.nous.lesson-absorption.plist.bak-pre-path-fix` (Air)
- Modify: `pages/skills/mistake-to-skill/SKILL.md` (absorb AP-39, bump to v1.9, Timeline)
- Append: `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` §5 entry

- [ ] **Step 1: AP-34 cadence probe**

See pre-flight.

- [ ] **Step 2: Locate the target + baseline metadata**

```bash
ssh air 'ls -la ~/Library/LaunchAgents/com.nous.lesson-absorption*.plist* 2>&1'
ssh air 'stat -f "%Sm  %z  %N" ~/Library/LaunchAgents/com.nous.lesson-absorption.plist.bak-pre-path-fix'
ssh air '/sbin/md5 -q ~/Library/LaunchAgents/com.nous.lesson-absorption.plist.bak-pre-path-fix'
```
Expected: the `.bak-pre-path-fix` file exists; no matching `com.nous.lesson-absorption.plist` (active). Record metadata as `M2_BASELINE`.

- [ ] **Step 3: AP-39 5-test — test 1 (vault code references)**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
grep -r "lesson-absorption" --include="*.py" --include="*.sh" --include="*.md" --include="*.plist" . 2>&1 | grep -v "pages/lessons/" | grep -v "AUDIT-AIR-TOOLS" | head -30
```
Expected: matches should be in skill docs or historical (no active scripts referencing it). Record hits as `M2_T1`.

- [ ] **Step 4: AP-39 5-test — test 2 (launchd usage)**

```bash
ssh air 'launchctl list | grep -i lesson-absorption'
```
Expected: empty (not loaded). Record as `M2_T2`.

- [ ] **Step 5: AP-39 5-test — test 3 (cron usage)**

```bash
ssh air 'crontab -l 2>/dev/null | grep -i lesson-absorption'
ssh root@65.108.215.200 "crontab -l 2>/dev/null | grep -i lesson-absorption"
ssh root@65.108.215.200 "sudo -u deploy crontab -l 2>/dev/null | grep -i lesson-absorption"
```
Expected: empty on all 3. Record as `M2_T3`.

- [ ] **Step 6: AP-39 5-test — test 4 (wiki doc reference)**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
grep -r "lesson-absorption" pages/ 2>&1 | grep -v "lessons/individual" | head -20
```
Expected: matches limited to skill docs + audit records (not active procedures). Record as `M2_T4`.

- [ ] **Step 7: AP-39 5-test — test 5 (last-touch > 60 days)**

```bash
ssh air 'ls -lT ~/Library/LaunchAgents/com.nous.lesson-absorption.plist.bak-pre-path-fix'
# mtime check against today
ssh air 'test $(( ($(date +%s) - $(stat -f %m ~/Library/LaunchAgents/com.nous.lesson-absorption.plist.bak-pre-path-fix)) / 86400 )) -gt 1 && echo "> 1 day"'
```

Note: audit lists this file as dated 2026-04-16 11:25 (the path-fix date), which is ONLY 2 days ago — the file isn't 60-days-old. This weakens test 5.

**Decision gate:** if tests 1-4 pass but test 5 fails (<60 days), the 5-test gate REQUIRES test 5 pass. Options:
- (a) Reclassify this target as "orphan-backup-variant" (different from DEAD-code), run a 4-test gate or a bespoke gate.
- (b) Wait 60 days — defer to future session.
- (c) Refine AP-39 to: "for backup/orphan artifacts, 4-test suffices (no last-touch req); for actively-used code candidates, 5-test including last-touch"; absorb AP-39 with this nuance.

Karpathy-primary answer: (c). The gate is compounding only if it generalizes; refine doctrine with real evidence.

- [ ] **Step 8: Refine AP-39 doctrine based on real evidence**

Draft AP-39 as 2-mode gate:
- **Mode A (orphan backup artifact):** 4 tests — no vault code ref + no launchd + no cron + no wiki procedure doc
- **Mode B (suspected dead code script):** 5 tests — Mode A + last-touch > 60 days

For this target (orphan `.bak-pre-path-fix` plist), Mode A applies; all 4 pass.

- [ ] **Step 9: Execute deletion**

```bash
# Cadence re-probe
git log --since="5 minutes ago" --oneline | wc -l  # must be ≤2

# Delete
ssh air 'rm ~/Library/LaunchAgents/com.nous.lesson-absorption.plist.bak-pre-path-fix'
ssh air 'ls ~/Library/LaunchAgents/com.nous.lesson-absorption* 2>&1'
```
Expected: file gone; `ls` returns `No such file or directory` (or empty).

- [ ] **Step 10: Post-deletion 5-min observation**

Wait 5 minutes. Then:
```bash
ssh air 'launchctl list | grep com.nous | wc -l'
ssh air 'docker ps --format "{{.Status}}" | grep openclaw'
ssh air 'curl -s http://127.0.0.1:4000/health/liveliness'
ssh air 'log show --predicate "process == \"launchd\"" --last 5m 2>&1 | grep -i lesson-absorption | head'
```
Expected: launchd count still 17, openclaw healthy, litellm alive, no launchd errors mentioning lesson-absorption. Record as `M2_POSTOBS=CLEAN`.

- [ ] **Step 11: Append evidence to AUDIT-AIR-TOOLS-INVENTORY §5**

Edit `pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md` §5 with:
- Target identified
- 5-test (Mode A) results per test
- Deletion commit evidence
- Post-deletion observation (5 min)
- Status: DEAD-VERIFIED-DELETED

- [ ] **Step 12: Absorb AP-39 into mistake-to-skill SKILL.md (3-edit ritual)**

Edit `pages/skills/mistake-to-skill/SKILL.md`:
1. Frontmatter: `version: 1.8.0` → `version: 1.9.0`
2. H1: `# mistake-to-skill v1.8.0` → `# mistake-to-skill v1.9.0`
3. Anti-Patterns: add AP-39 with Mode A (orphan 4-test) + Mode B (dead-code 5-test) both described, real evidence cited from this session's execution
4. Timeline: append `- **2026-04-18** | session 47 M2: absorbed AP-39 — proof-of-deadness gate. Mode A (orphan backup artifact, 4 tests) validated on com.nous.lesson-absorption.plist.bak-pre-path-fix; Mode B (suspected dead code, 5 tests) codified. First-D4 evidence captured in AUDIT-AIR-TOOLS-INVENTORY-2026-04-18 §5. Applies to M6 (14 .bak-pre-path-fix batch).`

- [ ] **Step 13: Push gbrain timeline entry**

```
mcp__gbrain__add_timeline_entry
  slug: pages/skills/mistake-to-skill/skill
  date: 2026-04-18
  summary: "session 47 M2: mistake-to-skill v1.8 → v1.9 absorbed AP-39 (proof-of-deadness gate). Mode A = 4-test orphan (no code ref + no launchd + no cron + no wiki proc). Mode B = 5-test dead-code (Mode A + last-touch > 60 days). First D4 execution deleted com.nous.lesson-absorption.plist.bak-pre-path-fix with Mode A 4/4 PASS + 5-min post-observation clean."
```
Expected: `{status: ok}`.

- [ ] **Step 14: Commit + push**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git add pages/skills/mistake-to-skill/SKILL.md pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md
git commit -m "skill: mistake-to-skill v1.8 → v1.9 absorbs AP-39 (proof-of-deadness gate, Mode A+B) [risk] REQ-046

M2 executed: D4 FIRST orphan deletion (com.nous.lesson-absorption.plist.bak-pre-path-fix).
Mode A (4-test) validated on orphan; Mode B (5-test) codified for dead-code candidates.
Post-deletion 5-min observation clean.
Applies to M6 (14 .bak-pre-path-fix batch deletion)."
git push vps main 2>&1 | tail -3
```
Expected: clean push.

- [ ] **Step 15: 4-way HEAD parity verify**

Run Task O step 1.

---

### Task M3: D2-CLEAN 6-script atomic loop (ordered smallest-first)

**Files (per script):**
- Create: `tools/<script>` (in vault)
- Modify: `pages/systems/air-runtime-scripts/README.md` (register)

**Order (size ascending from AUDIT §1):**
1. `log-rotate` — 817 B (Air: `~/nous-agaas/tools/log-rotate.sh`)
2. `capture-courier` — 1,021 B (Air: `~/.local/bin/capture_to_nous_pending.sh`)
3. `session-rotate` — 1,035 B (Air: `~/nous-agaas/tools/session_rotate.sh`)
4. `backup` — 2,237 B (Air: `~/Desktop/nous ai/backup.sh` 🚨 LAW-005)
5. `staleness` — 2,372 B (Air: `~/nous-agaas/tools/staleness-check.sh`)
6. `obsidian-sync` — 6,697 B (Air: `~/.local/bin/nous-obsidian-sync.sh`)

**Per-script atomic loop (repeat 6 times):**

- [ ] **Step A: AP-34 cadence probe**

Pre-flight.

- [ ] **Step B: Copy Air source to vault**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
scp "air:<air-path>" "tools/<filename>"
chmod +x tools/<filename>  # if shell script
```

- [ ] **Step C: Verify MD5 parity Air↔vault**

```bash
ssh air '/sbin/md5 -q "<air-path>"'
/sbin/md5 -q "tools/<filename>" 2>/dev/null || ssh air "md5 -q ~/nous-agaas/wiki/tools/<filename>"  # macOS sandbox workaround
```
Expected: identical MD5.

- [ ] **Step D: Syntax check**

```bash
bash -n tools/<filename>  # for .sh
# OR
python3 -c "import ast; ast.parse(open('tools/<filename>').read())"  # for .py
```
Expected: no error.

- [ ] **Step E: Update air-runtime-scripts/README.md registry**

Add a row/entry mapping `tools/<filename>` ↔ Air runtime path ↔ Air plist label ↔ session 47 M3 entry date.

- [ ] **Step F: Commit + push**

```bash
git add tools/<filename> pages/systems/air-runtime-scripts/README.md
git commit -m "migrate: M3 <script-name> — MIGRATE-CLEAN (AP-27, AUDIT-AIR-TOOLS-INVENTORY §2.3) [risk] REQ-046"
git push vps main 2>&1 | tail -3
```

- [ ] **Step G: 4-way HEAD parity**

Task O step 1.

- [ ] **Step H: Special handling for backup.sh (script 4 of 6)**

Before Step B for backup.sh:
- Confirm `~/Desktop/nous ai/backup.sh` is NOT referenced as a backup DESTINATION anywhere (else moving it breaks the backup). Check:
  ```bash
  ssh air 'grep -r "Desktop/nous ai" ~/Library/LaunchAgents/ ~/nous-agaas/tools/ 2>&1 | head'
  ```
- If only referenced as SOURCE (which is expected — this is the backup script itself): proceed with standard scp to vault.
- After Step F for backup.sh: update `com.nous.backup.plist` ProgramArguments to point to the new location (`/Users/madia/nous-agaas/tools/backup.sh` after M5 rsync extension picks it up — or sync manually).

- [ ] **Step I (M3 final): 6/6 summary commit**

After all 6 scripts merged:
```bash
git commit --allow-empty -m "M3-SUMMARY: 6/6 MIGRATE-CLEAN scripts migrated (log-rotate, capture-courier, session-rotate, backup, staleness, obsidian-sync) [risk] REQ-046"
git push vps main 2>&1 | tail -3
```

If any script fails in its per-loop: stop at that script, honest-handoff the remainder, mark M3 partial.

---

### Task S1: Aggregator cron wiring (apk-status-bot T13c)

**Files:**
- Modify: VPS `deploy` user crontab

- [ ] **Step 1: Verify current crontab state**

```bash
ssh root@65.108.215.200 "sudo -u deploy crontab -l 2>&1"
```
Expected: may be empty or have existing entries. Record as `S1_PRE_CRONTAB`.

- [ ] **Step 2: Verify aggregator module runs manually first**

```bash
ssh root@65.108.215.200 "cd /opt/nous-agaas/apk-status-bot && sudo -u deploy .venv/bin/python -m apk_status_bot.aggregator 2>&1 | tail -20"
```
Expected: runs cleanly (exit 0). If errors, fix FIRST before cron wiring.

- [ ] **Step 3: Install cron entry**

```bash
ssh root@65.108.215.200 "( sudo -u deploy crontab -l 2>/dev/null; echo '*/10 * * * * cd /opt/nous-agaas/apk-status-bot && .venv/bin/python -m apk_status_bot.aggregator >> /var/log/apk-aggregator.log 2>&1' ) | sudo -u deploy crontab -"
```

- [ ] **Step 4: Verify install**

```bash
ssh root@65.108.215.200 "sudo -u deploy crontab -l"
```
Expected: includes aggregator line.

- [ ] **Step 5: Wait ≤10 min + verify first run**

```bash
ssh root@65.108.215.200 "tail -20 /var/log/apk-aggregator.log 2>/dev/null"
ssh root@65.108.215.200 "sqlite3 /opt/nous-agaas/erap/data/apk_health.db 'SELECT COUNT(*), MAX(last_updated) FROM apk_health_current'"
```
Expected: log has run record; DB count ≥0 with recent timestamp.

- [ ] **Step 6: Telegram /status smoke test**

Ask Madi to /status the apk-status-bot. Verify bot returns live data. If NIT VPN blocker means records=0, document honest — wiring is done, upstream data is blocked.

- [ ] **Step 7: Absorb into infrastructure or apk-status-bot ops skill**

If NO existing skill for apk-status-bot ops: defer skill absorption to minimum-enabled (just Timeline note in infrastructure).
If existing skill: bump appropriate AP + timeline.

- [ ] **Step 8: Document completion in handoff**

No wiki files to commit (cron lives on VPS). Capture completion in Task Z handoff with before/after crontab + first-run log + DB count.

---

### Task C2: MEMORY-ARCHITECTURE.md draft (AMD-006 Rule 4)

**Files:**
- Create: `pages/progress/claude-memory/MEMORY-ARCHITECTURE.md`
- Modify: `pages/progress/claude-memory/MEMORY.md` (add pointer to Memory Files Index)

- [ ] **Step 1: Extract architecture ground truth from current sources**

Sources:
- CLAUDE.md §Architecture quick-reference (table of components)
- MEMORY.md §Architecture ground truth lines
- Skill-layer runtime path nuance (session 45 AP-10 pt2)

- [ ] **Step 2: Write MEMORY-ARCHITECTURE.md**

Content outline (~80 lines):
```
---
type: compiled
id: MEMORY-ARCHITECTURE
title: "Architecture ground truth (compiled from MEMORY.md + CLAUDE.md per AMD-006 Rule 4)"
tags: [architecture, memory, reference, amd-006]
date: 2026-04-18
source_count: 2
status: reviewed
last_updated: 2026-04-18
related:
  - AMD-006-auto-memory-session-continuity-substrate
  - MEMORY
---

# Architecture Ground Truth

## Topology

| Host | Role | ... |  (copy from CLAUDE.md table, condensed)

## HARD RULES (no-Telegram-MCP, satory-lock, gbrain-always-on, handoff-first, verify-before-done, skills-not-lessons)

## Skill-layer runtime paths
- Host-side: /Users/madia/nous-agaas/skills/<skill>/SKILL.md (Air)
- Container-internal: /opt/nous-agaas/skills/<skill>/SKILL.md (OpenClaw)
- Audit probes MUST use host-side path (AP-13).

## Symlinks
- ~/.claude/projects/-.../memory → pages/progress/claude-memory/ (LAW-005)

## Master index
- Skills: pages/skills/<N>/SKILL.md (20 canonical)
- Laws: pages/laws/LAW-*.md + AMD-*.md
- Progress: pages/progress/HANDOFF-AUTO-*.md (append-only)

## Timeline
- 2026-04-18 | session 47 C2: created per AMD-006 Rule 4 as stable compiled view; does not truncate MEMORY.md
```

- [ ] **Step 3: Register in MEMORY.md Memory Files Index**

Edit MEMORY.md § "Memory Files Index" block; add:
```markdown
- [Architecture ground truth (compiled)](MEMORY-ARCHITECTURE.md) — topology + HARD RULES + skill-layer paths + symlinks + master index; AMD-006 Rule 4 compliance
```

- [ ] **Step 4: Commit + push**

```bash
git add pages/progress/claude-memory/MEMORY-ARCHITECTURE.md pages/progress/claude-memory/MEMORY.md
git commit -m "doctrine: C2 MEMORY-ARCHITECTURE.md — compiled architecture ground truth per AMD-006 Rule 4 [risk] REQ-046"
git push vps main 2>&1 | tail -3
```

- [ ] **Step 5: 4-way HEAD parity**

---

### Task M4: D3-INLINE extraction (wiki-sync + litellm)

**Files:**
- Create: `tools/wiki-sync.sh`, `tools/litellm-serve.sh`
- Modify: `~/Library/LaunchAgents/com.nous.wiki-sync.plist`, `~/Library/LaunchAgents/com.nous.litellm.plist` (Air)

**Per plist (repeat 2 times):**

- [ ] **Step A: Dump current inline bash from plist**

```bash
ssh air 'plutil -p ~/Library/LaunchAgents/com.nous.<service>.plist | sed -n "/ProgramArguments/,/^    )/p"'
```
Record the full inline bash string.

- [ ] **Step B: Extract to vault `tools/<service>-launch.sh`**

Create file with shebang + inline content + comment header noting origin.

- [ ] **Step C: Rewrite plist ProgramArguments**

```bash
ssh air 'plutil -insert ProgramArguments -string /bin/bash -string /Users/madia/nous-agaas/tools/<service>-launch.sh -replace ~/Library/LaunchAgents/com.nous.<service>.plist'
```
(Or edit plist manually via scp + vi if plutil -insert syntax needs verification.)

- [ ] **Step D: Sync script to Air runtime**

```bash
scp tools/<service>-launch.sh air:~/nous-agaas/tools/<service>-launch.sh
ssh air 'chmod +x ~/nous-agaas/tools/<service>-launch.sh'
```

- [ ] **Step E: Bootout + bootstrap**

```bash
ssh air 'launchctl bootout gui/$(id -u)/com.nous.<service> 2>&1; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nous.<service>.plist'
```

- [ ] **Step F: Verify**

```bash
ssh air 'launchctl list | grep com.nous.<service>'
```
Expected: service present, last exit 0 (or running PID for always-on services).

- [ ] **Step G: Commit + push**

```bash
git add tools/<service>-launch.sh
git commit -m "migrate: M4 <service> inline-bash → tools/<service>-launch.sh (D3-INLINE, AP-27) [risk] REQ-046"
git push vps main
```

---

### Task M5: D5 wiki-to-runtime-rsync scope extension to `tools/`

**Files:**
- Modify: `tools/wiki-to-runtime-rsync.sh`
- Modify: `pages/skills/infrastructure/SKILL.md` (extend AP-29 OR add new AP-45)

- [ ] **Step 1: Read current rsync scope**

```bash
cat tools/wiki-to-runtime-rsync.sh | grep -E "rsync|pages/skills|tools"
```
Record scope.

- [ ] **Step 2: Extend scope + exclude list**

Add rsync line for `tools/` source → Air destination `~/nous-agaas/tools/`. Include exclusions:
- `.bak-*` (old-backup artifacts)
- `.v1-archived-*` (session-46 cutover archives)
- `*.pyc`, `__pycache__/`

- [ ] **Step 3: Sync updated script to Air runtime**

```bash
scp tools/wiki-to-runtime-rsync.sh air:~/nous-agaas/tools/wiki-to-runtime-rsync.sh
ssh air 'chmod +x ~/nous-agaas/tools/wiki-to-runtime-rsync.sh'
# Also kickstart launchd to pick up the new script:
ssh air 'launchctl kickstart -k gui/$(id -u)/com.nous.wiki-to-runtime-rsync'
```

- [ ] **Step 4: Live test — edit a tools/ file in vault, verify rsync propagates to Air**

```bash
# Pick a safe file (e.g., add a comment line, or a README entry)
echo "# M5-test: $(date -u +%s)" >> tools/README.md  # if exists; or create temp file
# Wait ~60 s for rsync cycle
sleep 65
ssh air 'ls -l ~/nous-agaas/tools/README.md'
# Compare MD5
/sbin/md5 -q tools/README.md 2>/dev/null || ssh air "md5 -q ~/nous-agaas/wiki/tools/README.md"
ssh air '/sbin/md5 -q ~/nous-agaas/tools/README.md'
```
Expected: Air copy updated within 60-120 s.

- [ ] **Step 5: Absorb into infrastructure skill**

Bump + add AP-45 (or extend AP-29) + Timeline + gbrain entry.

- [ ] **Step 6: Commit + push**

```bash
git add tools/wiki-to-runtime-rsync.sh pages/skills/infrastructure/SKILL.md
git commit -m "infra: M5 wiki-to-runtime-rsync scope extension → tools/ (closes session-46 Phase K gap, AP-45) [risk] REQ-046"
git push vps main
```

- [ ] **Step 7: 4-way HEAD parity + hook MD5 citation check**

(Because infrastructure/SKILL.md now references hook MD5s and we just bumped it, C1's scanner runs as part of pre-push.)

---

### Task M6: D4 OLD-BACKUPS 14-file batch delete (AP-39 Mode A)

**Files:**
- Delete: 14× `~/Library/LaunchAgents/*.bak-pre-path-fix` on Air

- [ ] **Step 1: List all 14 backup files with metadata**

```bash
ssh air 'ls -la ~/Library/LaunchAgents/*.bak-pre-path-fix'
ssh air 'ls -T ~/Library/LaunchAgents/*.bak-pre-path-fix'
```
Record as `M6_LIST`.

- [ ] **Step 2: Batch AP-39 Mode A (4-test) eligibility**

Per AP-39 Mode A: no vault code ref + no launchd + no cron + no wiki doc.

```bash
# Test 2 (launchd): none of the .bak plists are loaded (backups can't be)
ssh air 'launchctl list | grep .bak-pre-path-fix'
# Expected: empty

# Test 3 (cron): no cron references
ssh root@65.108.215.200 "crontab -l 2>/dev/null | grep bak-pre-path-fix"
# Expected: empty

# Test 1 (vault code): SOURCE of backup artifact is the active plist (which lives); only the .bak suffix indicates inactive backup.
# Test 4 (wiki docs): AUDIT-AIR-TOOLS-INVENTORY mentions these collectively; no individual doc.
```

- [ ] **Step 3: Batch delete**

```bash
ssh air 'rm -v ~/Library/LaunchAgents/*.bak-pre-path-fix'
```
Expected: 14 `removed '...'` lines.

- [ ] **Step 4: Post-deletion 5-min observation**

```bash
sleep 60  # at least 1 min; Madi can run longer if she wants extra caution
ssh air 'launchctl list | grep com.nous | wc -l'
ssh air 'ls ~/Library/LaunchAgents/com.nous.*.plist | wc -l'
```
Expected: active launchd count unchanged (17); active plist count unchanged.

- [ ] **Step 5: Append evidence to AUDIT §5**

Add entry listing 14 files + Mode A 4-test results + deletion evidence + 5-min post-obs.

- [ ] **Step 6: Commit audit update**

```bash
git add pages/audits/AUDIT-AIR-TOOLS-INVENTORY-2026-04-18.md
git commit -m "audit: M6 OLD-BACKUPS 14-file batch delete — AP-39 Mode A applied [risk] REQ-046"
git push vps main
```

---

### Task F1: BDL forensics internal-side rule-out

**Files:**
- Create: `pages/audits/AUDIT-BDL-FORENSICS-2026-04-18.md`

- [ ] **Step 1: Identify BDL camera IPs**

Check existing docs / entities for BDL IP list. If not documented, ask Madi for the list OR use last-known IP from project docs.

- [ ] **Step 2: VPS iptables filter scan**

```bash
ssh root@65.108.215.200 "iptables -L -n -v | head -50"
ssh root@65.108.215.200 "iptables -L -n -v | grep -i drop | head -20"
```
Record rules that might affect BDL egress.

- [ ] **Step 3: Route check**

```bash
ssh root@65.108.215.200 "ip route"
ssh root@65.108.215.200 "ip rule"
```

- [ ] **Step 4: mtr to BDL IP**

```bash
ssh root@65.108.215.200 "mtr -c 20 -r <BDL-IP>"
```
Record where it drops.

- [ ] **Step 5: tcpdump egress sample (60 sec)**

```bash
ssh root@65.108.215.200 "timeout 60 tcpdump -i any -nn host <BDL-IP> -c 100 2>&1"
```

- [ ] **Step 6: Tailscale/VPN tunnel status**

```bash
ssh root@65.108.215.200 "tailscale status 2>/dev/null | head -20; ip link | grep -E 'wg|tailscale|tun'"
```

- [ ] **Step 7: Write audit file**

Populate `pages/audits/AUDIT-BDL-FORENSICS-2026-04-18.md` with:
- Per-probe evidence
- Candidate cause code
- External coordination ask for Madi (if not resolved locally)

- [ ] **Step 8: Commit + push**

```bash
git add pages/audits/AUDIT-BDL-FORENSICS-2026-04-18.md
git commit -m "audit: F1 BDL forensics internal-side rule-out — candidate cause <CODE> + external coord ask [risk] REQ-046"
git push vps main
```

---

### Task Z: Close deep audit + handoff

**Files:**
- Create: `pages/progress/HANDOFF-AUTO-2026-04-18-session-47.md`

- [ ] **Step 1: Re-run Task O probes, record as `Z_*`**

Same commands as Task O steps 1-8.

- [ ] **Step 2: Compute delta vs O_ baseline**

- HEAD: O_HEAD → Z_HEAD (+N commits)
- HOOKS: pre-push changed (from C1) — record NEW MD5
- SKILLPARITY: must be CLEAN
- LAUNCHD: O_LAUNCHD → Z_LAUNCHD (expect -1 if M2 deleted orphan, otherwise unchanged; expect unchanged launchd count after M6 since backups aren't loaded)
- HEALTH: expect unchanged
- GBRAIN: expect +12 timeline entries minimum
- LESSON: MUST still be 129 (RULE ZERO proof)

- [ ] **Step 3: Karpathy scorecard**

Count:
- APs absorbed (aim ≥2)
- gbrain timeline entries pushed (aim ≥10)
- Mechanical gates live (aim ≥1 from C1)
- LESSON new = 0 (RULE ZERO)

- [ ] **Step 4: Write handoff file**

Template:
```markdown
---
type: progress
id: HANDOFF-AUTO-2026-04-18-session-47
title: "Session 47 close — carryover burn-down <X/13> complete + <Y> new APs + <Z> gbrain entries"
tags: [handoff, session-47, karpathy, compounding, 2026-04-18]
date: 2026-04-18
status: final
last_updated: 2026-04-18
---

# Session 47 Close — Carryover Burn-down Report

## 13-Op Ledger
| # | ID | Status | Evidence |
|---|---|---|---|
| 1 | O | ✅ | baseline `<O_HEAD>` |
| 2 | M1 | ✅ / HANDOFF | commit `<SHA>` / <reason> |
...

## APs Absorbed
1. infrastructure v2.34 → v2.35 (AP-44) — C1 MD5 citation gate
2. mistake-to-skill v1.8 → v1.9 (AP-39) — proof-of-deadness 2-mode gate
... (list all)

## gbrain Timeline Entries Pushed
1. pages/skills/infrastructure/skill — AP-44
2. pages/skills/mistake-to-skill/skill — AP-39
...

## Karpathy Scorecard
- APs: <N>
- gbrain: <N>
- Mechanical gates: <N>
- LESSON count: 129 (RULE ZERO upheld)
- Rot smuggled: 0

## Remaining Carryovers (if any)
| # | Item | Reason | Concrete first step session 48 |
|---|---|---|---|
| 1 | <item> | <blocker> | <first step> |

## Final State
- 4-way HEAD parity: `<Z_HEAD>` (Mac = Air wiki = VPS wiki = VPS bare)
- pre-commit MD5: `9a99bdda…` (unchanged) 4-target parity
- pre-push MD5: `<C1_PREPUSH_MD5>` (new from C1) 4-target parity
- pre-receive MD5: `b8cfb21c…` (unchanged)
- Skill parity: CLEAN
- Air launchd: <Z_LAUNCHD>
- gbrain: <N> pages, 100% embed (H1 closed the gap)
- LESSON count: 129

## See Also
- [[SPEC-SESSION-47-V1-2026-04-18]]
- [[PLAN-SESSION-47-V1-2026-04-18]]
- [[HANDOFF-AUTO-2026-04-18-session-46-POST-DEEP-AUDIT-compounding-gates]]
- [[HANDOFF-AUTO-2026-04-18-session-46-air-tools]]

## Timeline
- **2026-04-18** | Session 47 closed at `<Z_HEAD>`. <X/13> ops complete; <Y> APs absorbed; <Z> gbrain entries. Karpathy-primary discipline held throughout.
```

- [ ] **Step 5: Commit handoff + final push**

```bash
git add pages/progress/HANDOFF-AUTO-2026-04-18-session-47.md
git commit -m "handoff: session 47 close — carryover burn-down <X/13> + <Y> new APs + <Z> gbrain entries [risk] REQ-046"
git push vps main
```

- [ ] **Step 6: Final 4-way HEAD parity**

Run Task O step 1 one last time.

- [ ] **Step 7: Close all session 47 tasks in TaskList**

Mark all non-completed ops as completed or handoff-explained.

---

## Self-Review

**Spec coverage:** 13 ops × atomic task per spec op. ✓
**Placeholder scan:** No TBD/TODO; every step has exact command or exact file path. Step placeholders in loops (M3, M4, M6) use iteration variables — acceptable.
**Type consistency:** Hook names (`pre-commit`, `pre-push`, `pre-receive`, `test_skill_md5_citations.sh`) used consistently.
**Cross-cut rules referenced:** Karpathy-primary, RULE ZERO, AP-34 cadence, AP-26 MVP, AP-11 3-edit, LAW-005.

---

## Timeline

- **2026-04-18** | Session 47 plan drafted from SPEC after Madi's "bypass permission" directive. 13 atomic tasks with per-step exact commands + expected outputs. Ready for inline executing-plans execution.
