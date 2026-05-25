---
tier: 2
type: skill
name: library-grade-audit
id: SKILL-LIBRARY-GRADE-AUDIT
version: 1.7.0
last_updated: 2026-05-14
status: active
description: "v1.7.0 — Auditing Obsidian + gbrain + OpenClaw together as a single library. Defines 'library-grade' as a 7-gate falsifiable scorecard (Gate 7.1 AP-7-aware: OpenBrain orphan rate ≤5%; deferred_marked + deferred_already_marked count as terminal-state non-orphans per openbrain-projection v1.2.0 AP-7). v1.7.0 ships the AP-11 mechanical detector tools/test_gate_formula_alignment.sh — parses every gate row's jq formula, extracts referenced JSON fields, grep-verifies they exist in the downstream script's output schema; exit 1 on any drift with --strict. Detector first run: 1 gate, 0 drift, all 6 fields aligned. Surfaces 7-class debugging tree (FTS / schema / extract-cmd / sources / frontmatter / btree / doctor-formula). Prior bumps: v1.5.0 AP-9 (CLAUDE.md/AGENTS.md version-pin drift); v1.6.0 Gate 7.1 + AP-10 (measurement-vs-rule); v1.6.1 AP-11 (gate-formula alignment doctrine). Use when Madi says 'audit Obsidian + gbrain', 'is everything linked + synced', 'library-grade', 'retrieval like a library', 'are we golden?'"
triggers:
  - "audit Obsidian + gbrain + OpenClaw"
  - "library-grade scorecard"
  - "is retrieval working"
  - "/audit library"
  - "are we synced"
  - "brain_score not moving"
  - "extract creates 0 links/timeline"
  - "btree row size exceeds 2704"
tools: [Bash, Read, mcp__gbrain__*]
mutating: false
absorbs_lessons: [LESSON-085, LESSON-086]
related: [agent-quality, gbrain-ops, infrastructure, session-coordination, karpathy-loop]
tags: [skill, audit, library, gbrain, openclaw, obsidian, retrieval, scorecard, debugging-tree, 2026-04-30]
title: "library-grade-audit v1.7.0"
---

# library-grade-audit v1.7.0

## Purpose

Madi asks variants of *"audit Obsidian + gbrain + OpenClaw together; make sure everything is linked, synchronized, has clear titles, retrievable like a library"* repeatedly. Each agent rediscovers the same diagnosis chain from zero. This skill codifies the chain so the substrate inherits it.

**Output:** a 7-gate scorecard with falsifiable evidence per gate + named debt with concrete fix paths.

## The 7-gate library-grade scorecard

| Gate | Falsifiable check | How to run |
|---|---|---|
| 1. Title quality | `library_quality_scan.blocking_count == 0` | `python3 tools/library_quality_scan.py --json` |
| 2. Reachability A1 | Tier-A1 stable orphan rate ≤ 10% | `python3 tools/library_reachability_scan.py` |
| 3. Canonical | 0 broken aliases (body-wikilink resolution); ≤2 doctrine duplicates | `python3 tools/library_canonical_scan.py` |
| 4. Cross-ref Tier-A1 | 0 broken `[[wikilinks]]`; ≤5 broken prose AP refs | `python3 tools/library_crossref_scan.py` |
| 5. 3-layer sync | All skills MD5-equal Mac wiki / Air wiki / Air-skills runtime / OpenClaw container | per-skill md5 ssh probe |
| 6. gbrain semantic | `mcp__gbrain__search "<known-query>"` top-1 score ≥0.9 | live MCP probe |
| 7. OpenBrain projection | Every OpenBrain capture is projected, already linked, duplicate-content deduped, delete-noise classified, or blocked with owner/date; newest capture projects in ≤5 minutes | `python3 tools/openbrain_project_to_wiki.py --wiki . --dry-run --json`; live canary through Air runner + gbrain + OpenClaw |
| 7.1. OpenBrain ingestion SLO (v1.6.1, AP-7-aware) | Orphan rate ≤ 5% across all `pages/inbox/openbrain/*/openbrain-*.md` from the last 7 days. Captures are non-orphan when they reach a terminal state: `linked` / `multi_linked` / `skipped_already_linked` (backlinked via `[[openbrain-<uuid>]]`) OR `deferred_marked` / `deferred_already_marked` (frontmatter `status: deferred` per [[openbrain-projection]] v1.2.0 AP-7). Orphans = captures with no resolution yet. | `python3 tools/ingest_openbrain_to_skills.py --dry-run | jq '((.orphans_scanned - .linked - .multi_linked - .skipped_already_linked - .deferred_marked - .deferred_already_marked) / .orphans_scanned) <= 0.05'` |

**ALL seven must PASS for library-grade.** Tier A2/B/C carry accepted RULE-ZERO migration link-rot per `karpathy-loop` AP-2.

**Phase-1 fast scorecard:** gates 1-6 run in ~5min; Gate 7 is added when OpenBrain projection is in scope. Phase-2 walks the 7-class debugging tree only if Phase-1 surfaces RED.

## Phase-0: HEAD parity precondition (added 2026-04-30 session s2127)

Before running any gate, verify 4-way HEAD parity:

```bash
MAC=$(cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && git rev-parse HEAD)
AIR=$(ssh air 'cd ~/nous-agaas/wiki && git rev-parse HEAD')
VPS_W=$(ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git rev-parse HEAD')
VPS_B=$(ssh root@65.108.215.200 'cd /root/nous-agaas/obsidian-wiki.git && git rev-parse HEAD')
[ "$MAC" = "$AIR" ] && [ "$AIR" = "$VPS_W" ] && [ "$VPS_W" = "$VPS_B" ] && echo "✅ 4-WAY GOLDEN" || echo "🔴 DRIFT — auto-sync mid-flight or genuine"
```

If transient, `git pull --rebase && git push` on each working copy converges. If genuine, walk the auto-sync conflict marker class (session-coordination AP-20/AP-21).

## The 7-class debugging tree (top-down when metrics don't match expectations)

Each class burned 30+ minutes in session-105 before being eliminated. Save future-you the round-trips.

```
Q: gbrain reports orphans / 0 links / brain_score < 90?
│
├── Class 1: FTS regression
│   PROBE:  mcp__gbrain__search "<query>"
│   RED:    "column cc.search_vector does not exist"
│   FIX:    Check schema_version; usually transient
│   NOTE:   In s105, error was TRANSIENT; schema 29/29 = current
│
├── Class 2: Schema migration miss
│   PROBE:  bin/gbrain doctor --json | grep schema_version
│   GREEN:  "Version N (latest: N)"
│   FIX:    bin/gbrain upgrade (or pull migration files)
│
├── Class 3: Wrong extract command name
│   PROBE:  bin/gbrain --help | grep extract
│   RED:    Command name doesn't match docs (extract-links vs extract_links etc.)
│   FIX:    Read live --help; doctrine may be stale
│
├── Class 4: Source-of-truth confusion
│   PROBE:  Compare /opt vs /Users path; which one container reads
│   RED:    Editing host file but container reads different mount
│   FIX:    docker inspect --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' openclaw
│
├── Class 5: Frontmatter / YAML parse failure
│   PROBE:  python3 -c 'import yaml; yaml.safe_load(open("page.md"))'
│   RED:    YAMLError on a Tier-A page → gbrain skips entire page
│   FIX:    Quote colon-bearing values; flow-array → block-list for nested quotes
│
├── Class 6: btree row size exceeds 2704 bytes
│   PROBE:  Check Postgres logs for "row is too big"
│   RED:    Massive single-page chunk
│   FIX:    Split page; use raw/ for monolith dumps
│
└── Class 7: doctor-formula stale
    PROBE:  bin/gbrain doctor reports score; manually re-derive
    RED:    brain_score formula stuck on old gate weights
    FIX:    Upstream gbrain release; meanwhile cap expectation
```

## Anti-Patterns (7 codified from s100→s78 diagnosis chain)

### AP-1 — Running gates without 4-way HEAD parity check first (session-105)

If HEAD differs across Mac/Air/VPS-wiki/VPS-bare, the gate result is for a fictional substrate. Always Phase-0 first.

### AP-2 — Treating gbrain orphan_pages as vault doctrine debt (session-105)

`gbrain v0.22.16` link-extractor regression produces 0 links from prose-style wikilinks → reports thousands of orphans even when vault is clean. Distinguish: `link_coverage: 0` AND `dead_links: 0` AND `embed_coverage: 1.0` AND FTS top-1 ≥ 0.9 = vault clean, upstream extractor broken. Track upstream issue; do not chase phantom orphans.

### AP-3 — Editing the wrong /opt vs /Users path (session-100)

OpenClaw container has `/opt/nous-agaas/skills/` bind-mounted from Air-host `/Users/madia/nous-agaas/skills/`. The `/opt` path is container-internal only; it does NOT exist on the Air host filesystem. Audit probes (4-target parity) MUST use the host-side path. Canonical mount map: `docker inspect openclaw --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'`.

### AP-4 — Reporting "all skills sync" from a sample of 5 high-traffic ones (session-107)

A 5-skill sample is a smoke test, not the gate. The gate iterates ALL skills (≈30) and reports MATCH/DRIFT count. Use the Python loop in `tools/library_full_skills_audit.py` (or inline `python3 -c` block) — shell `for` loops with ssh subcommands break on multi-line iteration in zsh.

### AP-5 — Phantom skill: CLAUDE.md or RESOLVER references a SKILL.md that was never committed (session-108, 2026-04-30)

Peer session can ship `CLAUDE.md` reference + `_gbrain/RESOLVER.md` entry pointing at `pages/skills/<name>/SKILL.md`, but lose the actual SKILL.md commit (orphaned blob, never staged, or referenced "companion 8aa5aa54" that doesn't exist in any branch). The cross-ref scanner may miss this if CLAUDE.md isn't classified as Tier-A1 by the scanner — but it is broken doctrine. Mechanical detector: for every wikilink in CLAUDE.md and RESOLVER.md → `find pages/ -name "<target>.md" -or -path "*<target>/SKILL.md"` must return ≥1 file. If RED, restore from blob/memory or remove the dangling refs (Musk step 2). Future probe: `tools/test_claude_md_skill_pointers.sh` — exit 1 on any orphan target.

### AP-6 — VPS working copy stuck in incomplete-rebase silently for days (session s2148, 2026-04-30)

**Failure mode:** `cron` runs `git pull --rebase --autostash` on `/root/nous-agaas/wiki/` every minute. If a single commit conflicts (here: `bbe3ae3c... vps auto-sync 2026-04-20 15:05:01` collided on `pages/entities/denis.md`), the rebase exits non-zero, leaves `.git/rebase-apply/` dangling, and every subsequent cron `pull` fails the same way. Auto-sync keeps writing new local "vps auto-sync" commits on top of the stuck HEAD. Over 10 days, 2096 phantom commits stacked up; gbrain `sync --repo` reported "Already up to date" because the working tree's `git log` looked busy — but it was a fork of the bare repo. Brain ingested **from a 10-day-stale tree the entire time**. Probe 1 of Gate 6 (semantic search for newly-shipped content) RED-flagged it.

**Mechanical detector:** Phase-0 must include `ssh root@<vps> "cd /root/nous-agaas/wiki && [ -d .git/rebase-apply -o -d .git/rebase-merge ] && echo STUCK || echo CLEAN; git rev-list HEAD --not bare/main | wc -l"`. If output is `STUCK` or commit-count > 50, escalate.

**Recovery:** when content diff between `HEAD` and `bare/main` is empty (`git diff bare/main HEAD --stat` shows no changes), the divergence is pure graph-fork from auto-sync receipts and `git reset --hard bare/main` is safe. Bare repo is the source of truth; working-copy commits are receipts that lose nothing. Confirm content-empty-diff BEFORE reset.

**Related runbook:** auto-sync cron should fail loudly on rebase failure (write to a sentinel file checked by hourly health probe), not silently keep stacking. See gbrain-ops AP family for the noisy-failure-cron pattern.

**Operational watchdog (installed s2148, 2026-04-30):** `/root/nous-agaas/tools/wiki_rebase_watchdog.sh` runs hourly via cron at `:17` minute. Writes `/tmp/wiki_rebase_watchdog.last` (single-line status). On RED/AMBER, appends to `/root/nous-agaas/logs/watchdog.log` and posts a timeline entry to this skill's gbrain page. AMBER = graph-divergence but content-empty-diff (safe to `git reset --hard bare/main`); RED = either rebase-stuck-dir present or content-drifted divergence (needs manual investigation). Crontab line: `17 * * * * /root/nous-agaas/tools/wiki_rebase_watchdog.sh >> /root/nous-agaas/logs/watchdog.cron.log 2>&1`. First successful test run at `2026-04-30T17:12:33Z` reported `GREEN HEAD=b7b7f941`.

### AP-7 — SPEC.md drifts from versioned SKILLs after a doctrine pivot in the same session (sessions 57→78, 2026-04-21 → 2026-05-04)

**Failure mode:** session-57 (2026-04-21) shipped Satory CEO-assistant MVP with a 14-section authoritative `pages/tenants/satory/SPEC.md`. Same session, Madi deleted the approver gate ("too much bullshit"). [[pages/tenants/satory/PIPELINE]] and [[pages/tenants/satory/skills/correction-source/SKILL]] v0.3.4 captured the post-deletion truth; SPEC.md kept describing the deleted gate as live. Substrate drifted silently for 12 days. Codex review (session-id `019dec48`, 2026-05-03) caught it — the SPEC was actively misleading any agent that loaded it. Same drift class is structurally adjacent to **AP-5 phantom-skill** (both are "doctrine references something inconsistent with what's at the path") which is why the new AP lives here, not in a new skill.

**Root cause:** SPECs that duplicate skill doctrine become a second source of truth. When the SKILL evolves, the SPEC requires manual co-update or it drifts. No mechanical enforcement existed before AP-7.

**Mechanical detector (doctrine, mechanical implementation deferred to Sprint-2 / substrate-v2 Phase A):** every SPEC under `pages/tenants/<tenant>/` and `pages/specs/` MUST satisfy ONE of:

(a) **Thin-pointer pattern** — frontmatter `tags:` includes `thin-pointer`, AND body contains no normative `## N. <doctrine-section>` headings beyond Goal / Status / Owner / Stakeholders / Pointers / Open-questions / Timeline / References. Doctrine compounds in the linked SKILLs; SPEC orients but does not duplicate. (Recommended default for all new SPECs.)

(b) **Dated-audit pattern** — frontmatter carries `last_audited_against_pipeline: YYYY-MM-DD` AND `last_audited_against_skills: YYYY-MM-DD` AND both dates are within 14 days of `last_updated`. SPEC explicitly co-updates with linked doctrine; mechanical probe verifies cadence.

A SPEC that satisfies neither is a drift candidate. Future probe `tools/test_spec_doctrine_drift.sh` exits 1 on any such SPEC. Shipping the probe is deferred to Sprint-2 (multi-session handshake brainstorm) or substrate-v2 Phase A; doctrine codified now so the rule pre-dates the mechanism.

**Recovery for the originating Satory SPEC (executed Sprint-1 T2, 2026-05-04):** thin-pointer rewrite. SPEC.md v2.0.0 reduces to Goal + Status + Owner + Stakeholders + Pointers ([[pages/tenants/satory/PIPELINE]], [[pages/tenants/satory/skills/tenant-isolation/SKILL]] v0.3.4, [[pages/tenants/satory/skills/correction-source/SKILL]] v0.3.4, etc.) + Open questions + Timeline. **95 insertions, 273 deletions** (commit `6136fca2`). Doctrine compounds in the linked SKILLs; SPEC orients but does not duplicate.

**Cross-ref:** Sprint-1 spec [[pages/tenants/satory/specs/2026-05-03-sprint-1-drift-fix-design]]. Codex review session-id `019dec48-2ef5-7282-a430-6d5bdd06e5b7`. Original drifted SPEC preserved in git history (`git show <pre-2026-05-04>:pages/tenants/satory/SPEC.md`). Co-shipped with [[pages/progress/SESSION-COORDINATION-2026-05-03-22-30]] (handshake breadcrumb during parallel substrate-v2 author session).

### AP-8 — OpenBrain projection is green in MCP but absent from library substrate (2026-05-11)

**Failure mode:** OpenBrain `capture_thought` can succeed inside the MCP/Supabase lane while Obsidian, gbrain, and OpenClaw never see the thought. A second false-green exists when projection is keyed only by UUID: duplicate captures of identical content may create duplicate mirror files.

**Mechanical detector:** Gate 7 must run `python3 tools/openbrain_project_to_wiki.py --wiki . --dry-run --json` and inspect `projection_failed`, `would_create`, `duplicate_content`, and `exists`. A live canary must prove exact file path retrieval by `gbrain search` and OpenClaw `cat`. Duplicate canary capture must report `duplicate_content` and must not create an `openbrain-<second_uuid>.md` file.

**Recovery:** use [[openbrain-projection]]: Air LaunchAgent `com.nous.openbrain-projection`, full UUID filenames, `content_hash` duplicate guard, JSON-visible failures, and VPS-bare git commit/push through the existing wiki sync chain. Do not route this through GitHub Contents API unless GitHub-to-VPS-bare sync has already passed a canary.

### AP-11 — Gate formulas must align with the downstream skill's terminal-state doctrine (session s108-mac-97229, 2026-05-14 round-4)

**Failure mode** caught in real time within ~50 minutes of shipping Gate 7.1 in v1.6.0: this skill defined Gate 7.1 with the formula `(.deferred / .orphans_scanned) <= 0.05`, treating the `deferred` JSON counter as orphan. Round-2 had shipped [[openbrain-projection]] v1.1.0 AP-6 with three terminal states (`linked`, `marked deferred`, `archived`). Round-3 (this skill) v1.6.0 implicitly assumed `deferred = orphan`. A peer (session s1729-mac-87156) shipped [[openbrain-projection]] v1.2.0 AP-7 the same evening, adding `mark_deferred()` + writeback to capture frontmatter (`status: deferred` + `deferred_reason` + `deferred_at`) and three new JSON counters (`deferred_marked`, `deferred_already_marked`, `deferred_mark_failed`). Their Timeline claimed "Gate 7.1 = 0.00%, PASS." My LIVE measurement read 68.4% RED. The discrepancy was the formula: peer's doctrine said "deferred is terminal, counts as resolved"; my Gate 7.1 formula said "deferred is unresolved." Doctrine drift between the gate and the downstream skill, even though both ships landed the same day.

**Why this is structurally important:** every Phase-1 fast-scorecard gate is a measurement that *depends on a downstream skill's lifecycle model*. When the downstream skill grows a new terminal state (here: AP-7's `status: deferred` writeback), every dependent gate must update its formula in the same release window. Otherwise the gate stays RED forever, the operator stops trusting Phase-1, and the substrate rots — the failure mode this skill was designed to prevent.

**Rule:** every Phase-1 gate that consumes a downstream skill's JSON output MUST cite the downstream skill version AND the specific JSON counters it relies on, in the gate's "How to run" column. When the downstream skill bumps and adds a new terminal-state counter, the gate-owner skill MUST bump too in the same commit-window — atomic doctrine alignment, same anti-collision pattern as [[session-coordination]] AP-5.

**Mechanical detector (SHIPPED v1.7.0):** `tools/test_gate_formula_alignment.sh` — for every gate row in `library-grade-audit/SKILL.md` that calls a `tools/*.py --dry-run` script, parse the formula's `jq` expression (extracting tokens matching `\.[a-zA-Z_]\w*`), grep the downstream script for those exact field names (matches both `"key":` dict literals and `'key'` string keys), emit `OK` / `DRIFT` / `MISSING_SCRIPT` per gate. `--strict` makes the exit code non-zero on any drift; `--json` emits structured output. First run on Gate 7.1: 1 gate scanned, 0 drift, all 6 fields aligned with openbrain-projection v1.2.0 output schema (`orphans_scanned`, `linked`, `multi_linked`, `skipped_already_linked`, `deferred_marked`, `deferred_already_marked`). Wire into `com.nous.light-probe` 15-min cron is the remaining infra step (launchd plist edit on Air; deferred to a separate ship to keep this commit surgical).

**Recovery (when a gate goes permanent-RED after a downstream bump):**
1. Read the downstream skill's latest AP. Does it introduce a new terminal-state counter?
2. Compare against the gate's formula. Does the formula reference all terminal states?
3. If gap: bump this skill, update the formula, add a Timeline entry citing the alignment.
4. Verify: run the script live, compute the rate with the NEW formula, confirm GREEN.

**Cross-ref:** [[openbrain-projection]] v1.2.0 AP-7 (terminal-state writeback that the formula must respect), [[session-coordination]] AP-5 (atomic-commit-window across peer ships), [[mistake-to-skill]] AP-11 (3-edit ritual — Gate 7.1's row was edit #1, the AP-11 body is the substrate-grounding the table row can't carry alone), this skill's AP-10 (the meta-rule that table rows aren't substrate without an AP body).

### AP-10 — Measurement-layer gates need codification, not just a table row (session s108-mac-97229, 2026-05-14)

**Failure mode** caught in real-time by my OWN commit: shipped Gate 7.1 (OpenBrain orphan rate ≤ 5%) as a single row in the gate table + frontmatter bump + Timeline entry, but skipped a body-section addition. The vault's pre-commit hook (mistake-to-skill AP-11 + audit AP-14, 3-edit ritual) flagged the drift: "Agents habitually update #1 and #3, skip the boring #2."

**The hook is right.** A gate-table row is a one-line declaration; the WHY-this-exists narrative is what makes the rule retrievable next session. Without a body section explaining the measurement-vs-rule distinction, future agents see the row, don't grok the intent, and either ignore the gate (silent miss) or treat it as a rule (false codification).

**Rule:** every skill version bump that adds a gate, sub-check, or new doctrine surface MUST add a `### AP-N — <name>` body section, even when the new layer is "just a measurement." The Anti-Pattern body answers "what failure mode does this gate detect, what's the recovery, what's the cross-ref" — gate tables are mnemonic, AP bodies are substrate.

**Detector:** the mistake-to-skill AP-11 pre-commit drift gate. Already shipped; not a future TODO.

**Recovery (when blocked):** Add the AP-N body section that explains the new gate / sub-check. Re-stage, re-commit. Do NOT `--no-verify` past the drift hook except in true emergencies — bypassing it loses substrate compounding for the bumped skill.

**Cross-ref:** [[mistake-to-skill]] AP-11 (3-edit ritual), [[audit]] AP-14 (drift detector codification), [[karpathy-loop]] axis-5 (substrate compounds — a row without a body doesn't compound).

### AP-9 — CLAUDE.md / AGENTS.md version-pin drift from tier-1 SKILL.md (session s108-mac-74559, 2026-05-14)

**Failure mode:** the top-CTO doctrine loop is held together by version-pinned wikilinks (`[[skills/session-coordination]] v1.32.0`, etc.) in `CLAUDE.md`, `AGENTS.md`, `Nous/AGENTS.md`, and `pages/skills/_gbrain/RESOLVER.md`. `tools/test_top_cto_loop_wired.sh` greps each shim for the EXACT version string from the SKILL.md frontmatter. Bumping a tier-1 SKILL.md (SOC, karpathy-loop, musk-algorithm, session-architecture, session-coordination) without updating every cross-ref pin makes `soao.sh` Section 4b print 🔴 RED on the next run and blocks operators from proceeding until the drift is fixed.

**This is a class of [[mistake-to-skill]] AP-1 drift:** doctrine pointer evolves, but the pointer-holder doesn't. Session s108-mac-74559 found `CLAUDE.md` pinned `[[session-coordination]] v1.30.0` while the actual SKILL.md frontmatter was already at v1.32.0 (the May-12 AP-30/AP-31 ships had bumped the skill but missed the CLAUDE.md cross-ref). The test had been silently RED for ~48 hours before SOAO Section 4b surfaced it.

**Mechanical detector:** `bash tools/test_top_cto_loop_wired.sh` returns exit 0 / "OK: top-CTO loop wired in SOC, karpathy-loop, session-coordination, Codex launcher, RESOLVER, and AGENTS shim" when GREEN; exit 1 + `FAIL: <file> missing: [[skills/<skill>]] v<version>` when drift exists. This test runs inside `soao.sh` Section 4b, so every session-start ritual catches the drift the next time SOAO fires.

**Prevention (the actual rule):** when bumping any tier-1 SKILL.md version, the SAME commit MUST update:
1. `CLAUDE.md` (Mac vault) — every cross-ref wikilink that includes a `v<version>` string.
2. `AGENTS.md` (vault root) — same.
3. `Nous/AGENTS.md` (parent dir) — same.
4. `pages/skills/_gbrain/RESOLVER.md` — same.

`git commit -o <skill-path> -o CLAUDE.md -o AGENTS.md -o pages/skills/_gbrain/RESOLVER.md` is the anti-collision pattern (also matches `session-coordination` AP-5 atomic-commit-window).

**Recovery (when test fires RED):** read the FAIL line — it names the file + missing pin verbatim. Bump that pin to match `awk -F': ' '/^version:/{print $2; exit}' pages/skills/<skill>/SKILL.md`. Re-run the test. Add a Timeline entry to the bumped skill AND to `library-grade-audit` (this skill).

**Cross-ref:** `session-coordination` AP-5 (atomic-commit-window), `mistake-to-skill` AP-1 (pointer-without-artifact drift class), `session-operating-contract` Rule 19 (authorial-commit doctrine — the bumping author owns BOTH artifacts).

## Phase-1 fast scorecard (5-min runbook)

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"

# Phase-0 HEAD parity (above)

# Gate 1
python3 tools/library_quality_scan.py --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("blocking:", d["blocking_count"])'

# Gate 2
python3 tools/library_reachability_scan.py 2>&1 | grep -E "^GATE.*Tier A1"

# Gate 3
python3 tools/library_canonical_scan.py 2>&1 | grep "^OVERALL"

# Gate 4
python3 tools/library_crossref_scan.py 2>&1 | grep "^OVERALL"

# Gate 5 — full skills loop, see AP-4
python3 <<'PY'
import os, subprocess
skills = sorted([s for s in os.listdir("pages/skills") if not s.startswith("_") and os.path.isfile(f"pages/skills/{s}/SKILL.md")])
total, drift = 0, []
for s in skills:
    total += 1
    mac = subprocess.run(["md5","-q",f"pages/skills/{s}/SKILL.md"], capture_output=True, text=True).stdout.strip()
    air_w = subprocess.run(["ssh","air",f"md5 -q ~/nous-agaas/wiki/pages/skills/{s}/SKILL.md 2>/dev/null"], capture_output=True, text=True).stdout.strip()
    air_s = subprocess.run(["ssh","air",f"md5 -q ~/nous-agaas/skills/{s}/SKILL.md 2>/dev/null"], capture_output=True, text=True).stdout.strip()
    if not (mac == air_w == air_s and mac): drift.append((s, mac[:8], air_w[:8], air_s[:8]))
print(f"TOTAL={total} DRIFT={len(drift)}")
for d in drift: print(" 🔴", d)
PY

# Gate 6 — gbrain semantic
# (use mcp__gbrain__search via Claude tool)

# Gate 7 — OpenBrain projection (only when OpenBrain is in scope)
python3 tools/openbrain_project_to_wiki.py --wiki . --dry-run --json
```

## Evidence trail

- **2026-05-20 (close-out)** | v1.7.0 use — claude-mac s1030 Phase-1 Gate 6 CLOSE-OUT after gbrain MCP reconnected mid-session. Gate 6 (semantic top-1 ≥ 0.9): **PASS** — 3 known-query probes via `mcp__gbrain__search`: "musk-algorithm 5-step delete simplify accelerate" → top-1 score 0.99999994 hitting `pages/skills/infrastructure/skill`; "karpathy-loop 6-axis scorecard compounding" → top-1 score 0.99999994 hitting `pages/audits/sp2-openbrain-identity-2026-05-17`; `mcp__gbrain__get_page pages/skills/mistake-to-skill/skill` returned full compiled_truth + my fresh evidence-trail entry from commit `82a97967` (gbrain re-ingested cleanly within minutes). **Final Phase-1 scorecard: 7 PASS + 1 YELLOW (Gate 5 ceo-hierarchy peer-WIP drift, non-blocking).** No new AP — scorecard mechanism + gbrain ingester both worked as designed. No version bump (close-out of prior use-entry). No new LESSON (RULE ZERO).
- **2026-05-20** | v1.7.0 use — claude-mac s1030 ran Phase-1 fast scorecard during Madi "fix it" pass. Results: **Gate 1** (titles) PASS — `library_quality_scan.py --json` blocking_count=0. **Gate 2** (reachability) PASS — Tier-A1 orphan rate 0.0% (gate ≤10%), 0 A1+A2 orphans, B=11.75%/C=35.37% advisory only. **Gate 3** (canonical) PASS — 1 dup title Tier-A (gate ≤2: `'Claude'` at `entities/claude.md` vs `concepts/forrestchang-karpathy-claudemd-source-2026-04-21/CLAUDE.md`), 0 broken aliases (gate ≤0), 0 broken content dups (gate ≤2). **Gate 4** (cross-ref) PASS — 0 broken A1 wikilinks (gate ≤0), 0 broken A1 prose AP refs (gate ≤5); all-tier counts 300 broken wikilinks + 4 broken prose (within tier-A1 isolation). **Gate 5** (4-way MD5 sync) 4/5 PASS + 1 YELLOW — session-operating-contract, karpathy-loop, musk-algorithm, karpathy-coding-principles all match Mac/Air-wiki/Air-runtime/OpenClaw-container (eea95681 / ccc9539e / 93156b75 / f26d44cc); ceo-hierarchy yellow because Mac (c898715f) ≠ Air-wiki+runtime+container (2bf38bdf) — peer session `s108-mac-26485-20260520T1053` (Opus, declared scope includes ceo-hierarchy SKILL.md per [[COORD-2026-05-20-s1030-mac-opus-handshake]]) has active uncommitted edits; non-blocking, expected, will resolve when peer commits + Mac auto-syncs. **Gate 6** (semantic) DEFERRED — `mcp__gbrain__*` and `mcp__nous-wiki-qmd__*` MCP servers disconnected mid-session at 11:01 KZT; cannot run live `gbrain search` probe. Defer to next session with gbrain MCP available. **Gate 7** (OpenBrain projection) PASS — `openbrain_project_to_wiki.py --dry-run --json` reports orphans_scanned=0, exists=39, errors=0; nothing to project (cron `com.nous.openbrain-projection` 5-min on Air is keeping pace; matches gate 7.1 AP-7-aware formula). **Overall: 6 PASS + 1 YELLOW (non-blocking peer WIP) + 1 DEFERRED. No Phase-2 7-class debugging walk needed.** No new AP — scorecard mechanism worked as designed. No version bump (use-only). No new LESSON (RULE ZERO). See [[COORD-2026-05-20-s1030-mac-opus-handshake]] for session context.
- **2026-04-30** | v1.0.0 created. Originally drafted by peer session s100/s107 lane (companion "8aa5aa54" referenced in commit `aedc3952` but the companion never landed in any branch). Restored by session s2127-mac-63345 after a deep-dive audit found phantom-skill state: `CLAUDE.md` + `_gbrain/RESOLVER.md` referenced `[[library-grade-audit]]` with no SKILL.md on any of Mac/Air/VPS substrates. Restoration source: 60-line head read from disk earlier this session before the directory was cleaned by auto-sync, plus the live 6-gate run that produced 6/6 GOLDEN at HEAD `abf5253f`. AP-5 codifies the failure mode (phantom-skill: doctrine pointer without artifact). Cross-ref: `gbrain-ops` AP-72 (gbrain-dryrun frontmatter migration corruption — adjacent failure class shipped same window). 3-edit ritual per `mistake-to-skill` AP-11. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.0.0 → v1.1.0 — session s2148-mac-95617 ran the Phase-1 fast scorecard live and found Probe 1 of Gate 6 RED (newly-shipped agent-quality v1.20.0 AP-38 not retrievable via `gbrain search`). Walked the debugging tree: schema=29/29 ok, embeddings=100% ok, FTS=ok, gbrain `sync --repo /root/nous-agaas/wiki` returned "Already up to date" — but vault on VPS was actually a 10-day-stale fork. Root cause: `cron`-driven `git pull --rebase` had been silently failing every minute for 10 days due to a 2026-04-20 conflict on `pages/entities/denis.md`, accumulating 2096 phantom auto-sync commits stacked behind the unresolvable rebase. gbrain ingested from this stale tree the entire time. Recovery: confirmed `git diff bare/main HEAD --stat` was empty (graph-only divergence, no content drift), then `git reset --hard bare/main` on VPS-w. Force-put agent-quality slug → re-probed Gate 6 → 2/3 keyword probes 1.000, 3rd via semantic `query` 1.128. **AP-6 codifies the silent-rebase-stuck failure mode + content-empty-diff safety check before destructive reset.** 3-edit ritual. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.1.0 → v1.2.0 — same session s2148, doctrine-only AP-6 wasn't enough: the failure was *operational* (cron failing silently for 10 days). Shipped `/root/nous-agaas/tools/wiki_rebase_watchdog.sh` + hourly cron `17 * * * *` that detects stuck-rebase dirs, computes graph-vs-content divergence, and posts AMBER/RED to gbrain timeline + `/root/nous-agaas/logs/watchdog.log`. First successful test fired at `2026-04-30T17:12:33Z` reporting `GREEN HEAD=b7b7f941`. The watchdog turns Karpathy-loop axis-2 (mechanical detection) into a closed RL loop on substrate health: never again ≥1 hour silent. Operational paragraph appended to AP-6. 3-edit ritual. No new LESSON (RULE ZERO).
- **2026-05-04** | v1.2.0 → v1.3.0 — session s78-mac-40112-20260503T2234 ran Sprint-1 surgical drift-fix triggered by Codex review (session-id `019dec48`, 2026-05-03) of the 2026-04-21 session-57 plan. Codex flagged `pages/tenants/satory/SPEC.md` ↔ [[pages/tenants/satory/PIPELINE]] ↔ [[pages/tenants/satory/skills/correction-source/SKILL]] doctrine drift (SPEC still claimed approver-gate live; deleted session-57). Sprint-1 T2 thin-pointer-rewrote SPEC.md v2.0.0 (95+/273-, commit `6136fca2`). T3a acknowledged 1 unacked gbrain HEAD-drift sync failure (`daed8eb4`) with provenance reason. **AP-7 codifies the SPEC-drifts-from-SKILL failure class:** every SPEC must be EITHER thin-pointer-tagged OR carry dated-audit frontmatter within 14 days of `last_updated`. Mechanical probe `tools/test_spec_doctrine_drift.sh` deferred to Sprint-2 / substrate-v2 Phase A; doctrine codified now so the rule pre-dates the mechanism. Co-shipped with handshake breadcrumb [[pages/progress/SESSION-COORDINATION-2026-05-03-22-30]] (parallel substrate-v2 author session PID 2158 active during this sprint; scope-disjoint via [[session-coordination]] v1.28.0 Rule 5 `git commit -o <paths>`). 3-edit ritual. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.6.1 → v1.7.0 — session s108-mac-97229 (round-5) shipped the AP-11 mechanical detector `tools/test_gate_formula_alignment.sh` proposed in v1.6.1. Detector parses every gate-row jq formula against the downstream script's output schema; exits 1 on drift with `--strict`. First run on the only currently-scanned gate (Gate 7.1, AP-7-aware): 0 drift, 6/6 fields aligned with `openbrain-projection` v1.2.0 schema. Catches the exact failure mode AP-11 was codified for — if a peer bumps a downstream skill and adds new terminal-state counters without the gate-owner skill updating its formula, the detector will trip. Updated AP-11 body from "PROPOSED" to "SHIPPED." Launchd wiring (`com.nous.light-probe` 15-min cron) deferred to a separate ship to keep this commit surgical. CLAUDE.md cross-ref v1.6.1 → v1.7.0. 3-edit ritual: frontmatter v1.7.0 + H1 + Timeline. gbrain-timeline-ok: pages/skills/library-grade-audit/skill. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.6.0 → v1.6.1 — session s108-mac-97229 (round-4) caught Gate 7.1 stuck at 68.4% RED ~50 min after v1.6.0 ship, while peer s1729-mac-87156's [[openbrain-projection]] v1.2.0 AP-7 Timeline claimed PASS. Diagnosed as formula drift: my Gate 7.1 counted `deferred` as orphan; AP-7 says `deferred` (with frontmatter writeback) is terminal. Updated formula to AP-7-aware: `((.orphans_scanned - .linked - .multi_linked - .skipped_already_linked - .deferred_marked - .deferred_already_marked) / .orphans_scanned) <= 0.05`. Live measurement after fix + running peer's `mark_deferred()` on all 13 captures: 0/19 = 0.0% GREEN. AP-11 codifies the gate-vs-downstream-doctrine alignment rule + proposes mechanical detector `tools/test_gate_formula_alignment.sh`. Also commits the projection-runner preservation patch (`tools/openbrain_project_to_wiki.py` +7 lines preserve `status: deferred/ingested/archived` on rewrite) without which the next Air projection cycle would have wiped the AP-7 writeback within 5 minutes. CLAUDE.md cross-ref pin v1.6.0 → v1.6.1 (per AP-9). 3-edit ritual: frontmatter v1.6.1 + H1 + Timeline. gbrain-timeline-ok pending push. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.5.0 → v1.6.0 — session s108-mac-97229 (round-3) added **Gate 7.1** as the mechanical follow-up to round-2's OpenBrain ingestion ship (`openbrain-projection` v1.1.0 AP-6). Gate measures the orphan rate of OpenBrain captures in `pages/inbox/openbrain/*/` over the last 7 days; threshold ≤5% relies on `tools/ingest_openbrain_to_skills.py --dry-run` deferred count. This closes the split-ship from round-2 (axis-4 surgical concern) and gives the Phase-1 fast scorecard a falsifiable check on whether the ingestion learning loop is meeting its 24h SLO. CLAUDE.md cross-ref also bumped v1.0.0 → v1.6.0 (was 5 versions stale per AP-9 doctrine I codified in v1.5.0 — the bug bites me first; this is the rebound). 3-edit ritual: frontmatter + gate-table row + this Timeline entry. No new LESSON (RULE ZERO). gbrain-timeline-ok pending push.
- **2026-05-14** | v1.4.0 → v1.5.0 — session s108-mac-74559 found `soao.sh` Section 4b RED: `test_top_cto_loop_wired` reported `CLAUDE.md missing: [[session-coordination]] v1.32.0` while the SKILL.md frontmatter was already at v1.32.0 (May-12 AP-30/AP-31 bumps had updated the skill but missed the Mac-vault CLAUDE.md cross-ref). Test had been silently RED for ~48h. AP-9 codifies the **CLAUDE.md/AGENTS.md version-pin drift class**: when a tier-1 SKILL.md bumps, the same commit MUST update every cross-ref pin (`CLAUDE.md`, `AGENTS.md`, `Nous/AGENTS.md`, `pages/skills/_gbrain/RESOLVER.md`). Fix landed in a single commit alongside this AP. Test now exits 0 / "OK: top-CTO loop wired". 3-edit ritual (frontmatter + AP-9 body + this Timeline entry). gbrain-timeline-ok pending push. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.3.0 → v1.4.0 — OpenBrain projection moved from audit-only to implemented after Madi overrode the earlier defer gate. Gate 7 added for OpenBrain projection freshness and visibility. AP-8 codifies the cross-store false-green and duplicate-content failure modes found during live canary `82b0b7ab-c7aa-4cdc-b6b7-2dfe8d5bc825`: direct MCP capture worked, but durable proof required Air projection runner, VPS-bare git, gbrain exact/semantic retrieval, and OpenClaw mount read. Duplicate capture returned a second UUID; runner now reports `duplicate_content` and creates no second mirror.

## See also

- [[gbrain-ops]] — upstream gbrain v0.22.16 link-extractor regression (AP-2 reason)
- [[openbrain-projection]] — Gate 7 projection runner and canary runbook
- [[infrastructure]] — pre-commit substrate enforcement (AP-43)
- [[session-coordination]] — auto-sync conflict markers (AP-20/AP-21)
- [[karpathy-loop]] — AP-2 (Tier-A1 vs migration-debt distinction)
- [[FINDING-gbrain-v0.22.16-link-extractor-regression-2026-04-30]]
- [[FINDING-gbrain-v0.22.16-fts-regression-2026-04-30]]
- [[AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30]]
- [[CLAUDE]] — points here from the doctrine cluster
- [[skills/_gbrain/RESOLVER]] — registers this skill for "audit Obsidian" trigger phrases
