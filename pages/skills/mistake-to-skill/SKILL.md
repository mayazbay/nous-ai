---
tier: 2
name: mistake-to-skill
description: "The evolution engine: lesson→skill→runtime pipeline. Use AFTER any debug session, bug fix, repeated prompt, repeated instruction, or validated non-obvious success. Manual /skill-capture command. 7-day SLA for lesson absorption. Absorbs Karpathy SPL + Tan SKILLPACK + JPL embed-into-procedures. Triggers on 'lesson', 'absorb', 'skill-capture', 'debug session', 'bug fix', 'skill update', 'evolution', 'skills are the prompts'."
type: skill
id: SKILL-MISTAKE-TO-SKILL
version: 1.13.0
status: active
absorbs_laws: [LAW-001, LAW-009, LAW-015, LAW-017, AMD-005]
absorbs_lessons: [LESSON-085]
tags: [skill, evolution, lesson-absorption, skill-capture, god-prompt, 2026-04-15]
date: 2026-04-15
source_count: 0
last_updated: 2026-05-11
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, planning-discipline, error-classification, gbrain-ops, LAW-001-evolution, LAW-009-self-evolution, LAW-015-root-cause-evolution, LAW-017-success-is-skill, LESSON-085-never-declare-done-without-e2e-test]
title: "mistake-to-skill v1.13.0"
---

# mistake-to-skill v1.13.0

## Current rules (compiled truth — session 35 update)

**The skill layer is the compounding artifact. The gbrain timeline is the evidence trail. LESSON-NNN files are deprecated** (session 35 retirement; pre-commit hook physically blocks new ones). The Tan/Karpathy/Finn pattern: doctrine in SKILL.md, evidence in gbrain timelines. NASA's static lessons-DB was useful <25% of the time because LESSON files decay; skills + searchable timelines compound.

1. **Every bug fix or learned rule lands in a SKILL.md update.** New AP, new phase, or new bullet under "Current rules". Bump skill version. Append a one-line `## Timeline` entry. Same task: do NOT defer.
2. **Every SKILL.md update is paired with a `mcp__gbrain__add_timeline_entry`** on the same skill page (slug `pages/skills/<skill>/skill`, date today, summary describing the rule). This is the new audit trail; LESSON files no longer fill that role.
3. **NEVER create `pages/lessons/individual/LESSON-NNN-*.md`.** The pre-commit hook in every wiki working copy rejects new LESSON files. See AP-8.
4. **Every validated non-obvious success also produces a skill delta.** Not always a new skill — often a new rule in an existing skill. Err on capturing.
5. **Every repeated prompt is a candidate missing skill.** If Madi has to paste the same operating instruction twice in one workstream, stop treating it as a better prompt. Find the owner skill and codify the rule, or prove the owner skill already covers it.
6. **Manual promotion command: `/skill-capture`.** Invokes `skill-from-debug.py` on Air — creates a draft skill under `pages/skills/extracted/<slug>/SKILL.md` with `draft: true`. Madi reviews + promotes.
7. **Autonomous mutation is FORBIDDEN unless Madi explicitly asks the agent to update the skill layer in the current task.** Dream cycle proposes, `/skill-capture` drafts, Madi approves. Anti-slop rule (GOD_PROMPT §6). Never self-modify skill body without human review.
8. **Historical LESSON files up to ceiling LESSON-129** are receipts. Current filesystem count is allowed to be **≤129** after deletion/migration into gbrain timelines. They may be edited (drift correction — see AP-7) or deleted, but agents MUST NOT create any new `LESSON-NNN` file, including gap-filling old numbers.

## P1 — After a debug session (manual protocol, session-35 update)

1. Identify the owner skill via `mcp__gbrain__search` for the closest topic, then `pages/skills/_gbrain/RESOLVER.md`. If no fit → create a new skill (and register in RESOLVER).
2. Update `pages/skills/<owner>/SKILL.md`:
   - Add the rule (new `### AP-N`, new `### Phase`, or new bullet under "Current rules").
   - Append `LESSON-NNN` to `absorbs_lessons` ONLY if you are absorbing an existing historical LESSON. **Do not invent a new LESSON-NNN.**
   - Bump skill `version:` in frontmatter AND in `# heading v1.X.Y`.
   - Append a one-line `## Timeline` entry: `- YYYY-MM-DD | vX.Y.Z — <what changed and why>. <session-N>.`
3. Append to gbrain timeline:
   ```
   mcp__gbrain__add_timeline_entry  slug="pages/skills/<owner>/skill"  date=YYYY-MM-DD  summary="<one-line description>"
   ```
4. `git add pages/skills/<owner>/SKILL.md && git commit -m "skill: <owner> vX.Y.Z — <change summary>"`. The pre-commit hook will pass (skill-only commit, no LESSON file).
5. Wait for `wiki-to-runtime-rsync` to deploy to Air's `~/nous-agaas/skills/` (every change-event, ≤5s typical). Verify with: `ls -t ~/nous-agaas/skills/<owner>/SKILL.md` shows your edit time.

## P1-legacy — Editing an existing LESSON file (drift correction or migration)

Allowed and unblocked, BUT the pre-commit hook will run the drift scan (mistake-to-skill AP-7) on the staged LESSON. The file's frontmatter `id:` (or `name:`), `title:`, and `# H1` must all reference the same LESSON-NNN. Fix any drift before committing.

## P2 — After a validated non-obvious success

Same flow, but the "symptom" is "something worked that I wouldn't have expected to work" and "fix" is "the approach that worked." Same LESSON file format, same absorption path.

## P3 — When to create a NEW skill vs extend existing

Create a new skill if ALL of:
- No existing skill owns this domain (checked via RESOLVER.md + gbrain query)
- Content is ≥3 related rules (one rule → extend existing skill)
- Will be invoked by a distinct intent (not subsumed by existing triggers)

Otherwise: extend existing.

## P4 — What a "skill rule" looks like

One sentence imperative. One sentence why. One file:line reference where possible.

**Good:** "After ANY rsync to Air skills dir, grep for `_gbrain/skill-creator` — if missing, the rsync wiped the skillpack (session 24 Wave 3). Recover via `git checkout HEAD -- _gbrain/`."

**Bad:** "Be careful with rsync."

## Anti-patterns

### AP-1: Writing a LESSON and never absorbing it
**Symptom:** Ghost debt accumulates. LESSON-045 sits unabsorbed for 9 months; same bug bites us again in session 22.
**Fix:** 7-day SLA. `lesson-absorption-watcher.py` alerts on ≥7d ghosts. 0 unabsorbed is the weekly target.

### AP-2: Absorbing a rule without citing the LESSON
**Symptom:** Skill contains a rule; nobody knows why it's there; 3 months later someone removes it "because it doesn't seem necessary"; the original bug returns.
**Fix:** Every rule must have a `## Evidence trail` entry citing LESSON or LAW.

### AP-3: Autonomous skill mutation
**Symptom:** Dream cycle edits skills at night; morning brings surprise regressions.
**Fix:** Dream cycle WRITES TO `pages/progress/dream-cycle-YYYY-MM-DD.md` only. Never to `pages/skills/*/SKILL.md`. Madi reviews, `/skill-capture` drafts, git commit is the explicit gate.

### AP-4: "Just quick paraphrase, don't need the LESSON file"
**Symptom:** Rule goes into skill without audit trail; 6 months later someone challenges it; no evidence to defend.
**Fix:** Every skill rule change requires a referenced LESSON or LAW.

### AP-5: Lesson unabsorbed for >7 days (AMD-005 SLA violation)
**Symptom:** Ghost debt accumulates silently. The lesson exists but never reaches agent runtime. Same bug recurs.
**Rule:** Every lesson MUST be absorbed into a SKILL.md within 7 days. dream_cycle.py (nightly) and lesson_absorption_watcher.py (every 6h) flag overdue items. Target: >=95% absorption rate. Skills are the evolution substrate; standalone lessons decay.
**Fix:** AMD-005 codifies the 7-day SLA. Dual-write required: SKILL.md update + LESSON file in same commit.

### AP-6: Lesson absorbed without `absorbed_into` backlink
**Symptom:** Skill claims the lesson in `absorbs_lessons`, but the lesson file has no `absorbed_into` pointing back. Audit can't trace which skill owns which lesson. Session 33 found 97 lessons (70 implicit + 27 absorbed) missing backlinks.
**Rule:** When absorbing a lesson, ALWAYS add `absorbed_into: [skill-name]` and `absorbed_at: YYYY-MM-DD` to the lesson's frontmatter. The pre-commit hook enforces co-presence of lesson+skill in same commit, but does NOT enforce backlinks — this is manual discipline.

### AP-8: Creating a NEW LESSON-NNN file (Tan/Karpathy/Finn pattern violation)
**Symptom:** Agent finds a bug, instinctively writes `pages/lessons/individual/LESSON-130-foo.md` to "document the lesson." This was the prior pattern (LAW-015 + RULE ZERO co-commit hook), and it kept happening across sessions because the system prompt itself instructed it.
**Why it's wrong:** Tan, Karpathy, and Alex Finn — the practitioners running production AI agents that actually evolve — all use the same architecture: **SKILL.md = doctrine, gbrain timeline = evidence**. There is no "LESSON" entity. A separate LESSON-NNN file decays (NASA lessons-DB used <25% of the time, per the original Tan post). Skills compound because they're read at runtime; LESSONs rot because no agent re-reads them.
**Rule:** Do NOT create new LESSON-NNN files. Add the rule to a SKILL.md (new AP, phase, or "Current rules" bullet) AND append a gbrain timeline entry on the skill page. That's the entire receipt.
**Physical enforcement (session 35):** the pre-commit hook in every wiki working copy (Mac, VPS, Air) rejects any commit that adds `pages/lessons/individual/LESSON-NNN-*.md`. Hook lives at `.git/hooks/pre-commit`. Bypass requires `--no-verify` (operator's explicit decision; not for agents) or editing the hook on disk. The hook also blocks lesson id/title/H1 drift on existing files (AP-7).
**Migration path:** the existing 129 LESSON files remain as historical receipts. They will be migrated into gbrain timelines on the source skills over future sessions; the LESSON directory will eventually be deleted. Until then, edits to historical LESSONs are allowed (subject to AP-7 drift gate). Deletions are also allowed.
**If you are about to write LESSON-130 or higher and you are NOT an operator with explicit `--no-verify` intent: STOP. Open the relevant SKILL.md instead.**
Source: session 35 Garry-Tan enforcement audit, 2026-04-16. Evidence in this skill's Timeline entry below + gbrain timeline.

### AP-7: Lesson id / title / H1 drift from copy-paste
**Symptom:** Frontmatter `id:` says LESSON-123, but `title:` and `# H1` say LESSON-104 — stale from the template author copy-pasted. Session 35 found 5 such bugs: LESSON-113 (`name:` instead of `id:`), LESSON-123 (title+H1 said 104), LESSON-124 (H1 said 116), LESSON-125 (H1 said 117), LESSON-126 (H1 said 120). Search hits for "LESSON-123" miss content titled "LESSON-104"; gbrain's compiled truth pattern gets broken; runtime skill-loader may pick the wrong owner.
**Rule:** Every absorption audit MUST run a drift scan. Every lesson MUST have: `id:` (not `name:`), frontmatter `title:` starting with its own LESSON-NNN, and an H1 matching its own LESSON-NNN. Cross-skill copy-paste is the trigger.
**Drift scan (runs at every absorption cycle):**
```bash
cd <wiki>/pages/lessons/individual
for f in LESSON-*.md; do
  ID=$(grep -E "^id: " "$f" | head -1 | awk '{print $2}')
  TITLE_ID=$(grep -E "^title: " "$f" | head -1 | grep -oE "LESSON-[0-9]+[a-z]?" | head -1)
  H1_ID=$(grep -E "^# LESSON-" "$f" | head -1 | grep -oE "LESSON-[0-9]+[a-z]?" | head -1)
  [ -n "$TITLE_ID" ] && [ "$TITLE_ID" != "$ID" ] && echo "TITLE DRIFT: $f"
  [ -n "$H1_ID" ]    && [ "$H1_ID"    != "$ID" ] && echo "H1 DRIFT:    $f"
  [ -z "$ID" ] && echo "MISSING id: $f"
done
```
Exit code: non-zero if any drift — wire into pre-commit hook via a later iteration. Source: session-35 Garry-Tan enforcement audit 2026-04-16 (see Evidence trail below).

### AP-9: Dream cycle false positives from tool/data deploy lag (session 36)

**Symptom:** The 2026-04-17 03:15 Almaty dream cycle wrote `pages/dashboards/dream-cycle-proposals-2026-04-17` listing 23 lessons as "unabsorbed ≥7 days," including 11 as "UNMATCHED — needs manual triage." Session 36 audit cross-checked every single one against the wiki: **all 23 are already triaged** (12 `absorbed`, 7 `implicit-already-in-skill`, 4 `archived-no-absorption-needed` based on the proposal subset; wiki-wide distribution is 37 absorbed / 67 implicit / 24 archived). Zero new absorption work was actually needed. The dream cycle was a false-positive factory that would have driven an agent into 11 unnecessary skill edits if taken at face value.

**Root cause (confirmed on Mac, not yet on Air due to Tailscale re-auth block):** the `skip_statuses = {"absorbed", "archived-no-absorption-needed", "implicit-already-in-skill"}` filter in `tools/dream_cycle.py` was added at commit 66666b1a on 2026-04-16 13:19 Almaty. The session-33 backfill that populated `status: absorbed` + `absorbed_into:` on 97 lessons landed at commit c01265e7 on 2026-04-16 15:49 Almaty. Both changes exist on Mac and VPS wiki HEAD. The Air cron that runs `dream_cycle.py` at 03:15 Almaty must therefore be invoking a stale copy: either (a) `~/nous-agaas/wiki/tools/dream_cycle.py` is not up-to-date on Air (wiki sync lag), (b) the cron invokes a different path (`/opt/nous-agaas/tools/` legacy location), or (c) the lessons on Air had not yet been synced with the session-33/34 backfill when cron fired.

**Rule:** A dream-cycle proposal is **evidence of a deploy/sync bug until proven otherwise**, not a ground-truth list of absorption work. Before acting on proposals:
1. Spot-check the first 3 items against current wiki status (`grep '^status: ' pages/lessons/individual/LESSON-NNN-*.md`). If they already report `absorbed | implicit-already-in-skill | archived-no-absorption-needed` → STOP. The dream cycle is running stale data or stale code.
2. Confirm the runtime `dream_cycle.py` matches the wiki version: `md5 <wiki>/tools/dream_cycle.py` on each host that runs it. Drift = deploy bug.
3. Fix the deploy path (rsync / git pull) before interpreting any new proposals.

**Fix applied (session 36):** AP-9 documented here. Air rsync of `tools/dream_cycle.py` deferred to session 37 (Tailscale re-auth blocker). Next dream cycle should be re-run from the updated Air copy once unblocked, and its proposal compared against this session's proposal to measure the false-positive rate.

**Source:** Session 36 Phase C — tried to absorb 11 "UNMATCHED" lessons, discovered all 11 already triaged on disk, traced to dream cycle deploy lag. 2026-04-17.

### AP-11: SKILL.md version parity — bump frontmatter + H1 + Timeline together, not just one (session 46, 2026-04-18)

**Symptom:** Session 46 deep audit found 7 skills with drift between `version:` frontmatter and the `# <name> vX.Y.Z` H1 header. 2 were session-46 bumps (infrastructure: frontmatter v2.32 but H1 still said v2.29 — out by THREE cumulative bumps; evidence-verification: v1.6 vs v1.5). 5 were multi-session pre-existing drifts (agent-quality 1.8/1.7, gbrain-ops 1.18/1.15, planning-discipline 1.6/1.5, storage-retrieval missing H1, tailscale-stability missing H1).

**Why it matters:** Agents + tools that read the "current version" of a skill pull one or the other — drift = inconsistent answers. Worse, gbrain's chunk_index=0 embedding covers the H1 area, so search results serve the stale H1 version even after a post-commit autopilot re-sync. In session-46 probes this made gbrain return "infrastructure v2.29.0" for my "AP-37 query" long after I'd claimed v2.32.

**Real root cause:** The bump ritual is THREE edits that look like ONE conceptual change:
1. Frontmatter `version: X.Y.Z`
2. H1 `# <skill-name> vX.Y.Z`
3. Latest `## Timeline` line `- YYYY-MM-DD | vX.Y.Z — …`

Agents habitually update #1 and #3 (they're at the "interesting" ends of the file) and skim past #2 (the boring header). Nothing enforces the trio.

**Rule:** SKILL.md version bumps MUST update ALL FOUR:
- `^version:` line in frontmatter
- `^# <name> v` line (H1)
- new `## Timeline` (or `## Evidence trail`) entry
- **4th check (v1.9 round-2 2026-04-18):** Timeline↔Anti-Patterns parity — if the new Timeline/Evidence entry says `added AP-N` or `extended AP-N`, the Anti-Patterns section MUST contain a matching `### AP-N:` (or `- **AP-N:**`) bullet for that same N. Cross-reference with `grep -E "AP-[0-9]+" <SKILL.md>` and verify every AP referenced in a Timeline entry appears as an AP bullet.

**How to apply:** (a) Before committing a SKILL.md bump, run `bash tools/test_skill_version_parity.sh` — exits 0 if clean, 2 if any drift, lists each drift on stderr. (b) As of session 46 Phase I (infrastructure AP-43) the scanner is wired into pre-commit RULE 4 — version-parity drift is mechanically BLOCKED on commit. (c) As of session 48 Mac-interactive deep-audit (infrastructure **AP-46**) the scanner also enforces YAML-validity of the frontmatter block via `yaml.safe_load` — catches `[[wikilink]]` in list fields, unquoted colons in scalars, bad indentation. (d) As of session 48 Mac-interactive deep-audit (infrastructure **AP-48**) the scanner also enforces the 4th check — Timeline↔AP-bullet parity — mechanically: every `"added/extended/absorbed AP-N"` claim in `## Timeline` or `## Evidence trail` MUST have a matching bullet (`^### AP-N`, `^- **AP-N:**`, `^- **AP-N —**`, `^**AP-N:**`) anywhere in the same file. All 4 checks (version, YAML, Timeline↔AP, plus the implicit frontmatter-required-fields check in YAML validity) are pre-commit mechanical — agent compliance is no longer the bottleneck.

**Evidence for 4th check (round-2 addition 2026-04-18):** Session 46 first-round bumped `audit` v1.12 → v1.13 absorbing AP-14. All three existing checks passed — frontmatter ✓, H1 ✓, Timeline entry ✓ — but the AP-14 bullet was NEVER added to the Anti-Patterns section. The Timeline described the rule; the file contained no matching bullet. Round-2 deep-audit caught the orphan. The 3-check ritual passed vacuously because Timeline entries are free-form prose — they can describe "added AP-N" without enforcing any structural link to an actual AP-N bullet elsewhere in the file.

**Cross-ref:** `mistake-to-skill` AP-7 covers LESSON-file id/title/H1 drift via pre-commit scan. AP-11 is the SKILL.md equivalent — same class of drift, different target. `audit` AP-15 is the meta-pattern — self-compliance check when codifying rules mid-session. `infrastructure` AP-43 = pre-commit RULE 4 that mechanically enforces AP-11 checks (1)-(3).

### AP-12: YAML-invalid frontmatter silently drops gbrain ingestion (session 46, 2026-04-18)

**Symptom:** Session 46 Mac-interactive created new skill `session-operating-contract` v1.0.0. Pre-commit RULE 4 (AP-43) passed. 4-way HEAD parity confirmed at `b4413768`. Auto-sync pushed to VPS bare, which fan-out to VPS wiki + Air wiki. Air runtime rsync landed the SKILL.md at `/Users/madia/nous-agaas/skills/session-operating-contract/SKILL.md`. But `mcp__gbrain__get_page pages/skills/session-operating-contract/skill` returned `page_not_found`, and `mcp__gbrain__search session-operating-contract` returned only the alias `.md` (the folder-level SKILL.md was silently absent from gbrain). Two subsequent `sync_brain` calls (one incremental, one `full: true`) showed 0 pages added/modified for the new skill — gbrain ingester never picked it up.

**Why it matters:** Silent 50% deployment. Wiki has it, runtime has it, RESOLVER.md references it — but gbrain (the semantic search layer that agents query at runtime via `mcp__gbrain__search` / `get_page`) cannot retrieve the skill body. Agents reading RESOLVER.md at runtime will find a dead pointer. No error anywhere in the pipeline — sync_brain's response is `{"status": "synced", "added": 0}` regardless.

**Real root cause:** Frontmatter `related:` field used Obsidian wikilink syntax inside a YAML list:

```yaml
related: [[agent-quality]], [[evidence-verification]], [[mistake-to-skill]], ...
```

YAML interprets `[[` as the start of a nested sequence, and this form is structurally invalid (unclosed nesting, no separator). YAML parsers throw on it. Gbrain's ingester catches the parse exception and drops the page silently with no log entry visible to the sync response.

Pre-commit RULE 4 (`tools/test_skill_version_parity.sh`) uses `grep` on the frontmatter block to compare `^version:` to `^# <name> v` — it does NOT parse the YAML. Every structural frontmatter bug class (malformed lists, bad indentation, missing required fields, Obsidian constructs in YAML values) slips through the gate.

**Rule:** Skill frontmatter list-valued fields (`related:`, `absorbs_laws:`, `absorbs_lessons:`, `triggers:`, `tags:`, `tools:`) MUST use bare identifiers only. No `[[wikilink]]` syntax — that is an Obsidian body construct, not YAML. Wikilinks go in the `## See also` section of the body. Frontmatter must pass a YAML parser.

**How to apply:** (a) When writing or editing any SKILL.md frontmatter, use only bare identifiers in list fields. (b) Verify locally before commit: `python3 -c 'import yaml,sys; [yaml.safe_load(open(p).read().split("---")[1]) for p in sys.argv[1:]]' pages/skills/*/SKILL.md` — silent exit = all valid, any traceback = structurally broken file. (c) After pushing a new or renamed skill, ALWAYS confirm gbrain ingestion with `mcp__gbrain__get_page pages/skills/<name>/skill` before declaring done — `page_not_found` post-sync = AP-12 suspect, parse the frontmatter manually.

**Next-session compound gate (candidate):** Extend `tools/test_skill_version_parity.sh` with a YAML-safe-load step over every SKILL.md's frontmatter block; wire into pre-commit hook RULE 4. Same compounding-gate pattern as AP-43 turned AP-11 mechanical. Fail-closed means this class of silent-drop ingestion bug becomes physically impossible.

**Cross-ref:** `mistake-to-skill` AP-11 (version parity — OTHER structural SKILL.md check; both needed for full coverage). `infrastructure` AP-43 (current pre-commit RULE 4 mechanical gate — misses this class because scanner is grep-based). `session-operating-contract` rule 6 (failure→skill loop — this AP was the first failure caught by the newly-created skill and captured in-session per its own doctrine).

### AP-13: LESSON ceiling is not an exact-count invariant (session 79, 2026-04-29)

**Symptom:** A session-open audit compared the current vault's `pages/lessons/individual/LESSON-*.md` count against old doctrine that said "129 frozen" and flagged a mismatch: filesystem count was 24, max visible LESSON number was 104. Several shims and skills still described "existing LESSON-001 … LESSON-129" as if every historical file must remain present.

**Root cause:** Session-35 RULE ZERO froze new lesson creation, but explicitly allowed historical LESSON files to be deleted during migration into gbrain timelines. On 2026-04-25, VPS auto-sync commits `70d9f60f` and `2bfa4ece` deleted 105 historical lesson files; `commit-review-2026-04-26.md` then corrected `soao.sh` from `== 129` to `<= 129`. The invariant changed from exact count to ceiling, but session shims and parts of the skill layer kept the old phrasing.

**Rule:** Treat 129 as a maximum ceiling and historical ID namespace, not as the expected filesystem count. The live checks are: (1) no new `LESSON-NNN` files were added, (2) highest historical lesson number is `<=129`, and (3) gbrain lesson-page count, if checked, is compared to current filesystem count or documented migration state, never to a hard-coded 129.

**Fix:** Update RULE ZERO wording in Mac shims and vault schema to say current count may be lower after migration. Update audit/session skills to check ceiling + no-new-files rather than exact count. Update server-side hooks to reject newly added/copied/renamed canonical `LESSON-NNN` paths even when total count remains below the ceiling. Do not resurrect deleted historical lesson files just to satisfy stale count checks.

### AP-14: Repeated prompt loop means missing skill, not louder prompting (session 108, 2026-05-11)

**Symptom:** Madi repeats the same high-standard operating prompt across Claude, Codex, OpenClaw, gbrain, Obsidian, Notion/Todoist, and factory audit sessions: plan first, execute one by one, root-cause gaps, retry, save to skills/gbrain, and keep the whole factory evolving.

**Root cause:** The repeated instruction was treated as conversation context instead of a failing runtime interface. A chat prompt can be forgotten at compaction, by another lane, or by the next tool. A skill rule is loaded by future agents and becomes part of the factory.

**Rule:** On the second repeat of a non-trivial operating instruction, search `pages/skills/` and gbrain for the owner. If no rule exists, update the owner skill in the same lane (or create a skill only if no owner exists). If the owner already exists, add a compact AP or Current Rule entry rather than pasting the full prompt/article into `AGENTS.md`.

**Test:** A future agent should be able to answer "where is this behavior encoded?" with a specific `pages/skills/<skill>/SKILL.md` path plus a gbrain timeline entry. If the answer is "in chat history," this AP failed.

### AP-10: Confusion Protocol — stop at ambiguous absorption forks (gstack v0.18.0.0, 2026-04-17)

**Karpathy's #1 AI coding failure mode** applied to mistake→skill absorption: the agent confidently picks the wrong skill target or the wrong rule framing at an ambiguous fork. 10+ min rework when the wrong skill gets a cuckoo-rule.

**Asymmetric-cost forks in this skill:**
- **Which skill to absorb into** when two plausibly apply (e.g., a camera-auth bug could live in `camera-management` or `agent-quality`)
- **Extend existing AP** vs write a new AP — sometimes the rule is a minor extension of an existing AP, sometimes genuinely new
- **Is this rule already implicit in the skill?** — before absorbing, spot-check whether an existing AP already covers it (`implicit-already-in-skill` is a valid skip-status)
- **Is the root cause we found THE cause or just A cause?** — a "found" root cause may be a symptom; absorbing the symptom rule wastes the evidence

**Rule:** When the fork is asymmetric — ASK. "Hit a fork: absorb this into (A) skill X as new AP, or (B) skill Y extending AP-N? Or (C) already implicit in skill Z?" Don't absorb-anyway to close the ticket.

**Does NOT apply** to routine absorption where the target skill is obvious (e.g., a Telegram poller bug → `infrastructure` or a new skill if not covered).

### Brain-aware absorption (gstack v0.18.0.0, 2026-04-17)

Before absorbing a lesson or rule, `mcp__gbrain__search` for the affected file paths or the rule keywords — the same pattern may already be in an AP of an adjacent skill. After absorption, `mcp__gbrain__add_timeline_entry slug="pages/skills/mistake-to-skill/skill"` noting which source lesson was absorbed into which target skill + AP number. See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

### CEO review reinforcement (gstack v0.18.0.0, 2026-04-17)

**REVIEW ONLY — NO CODE CHANGES.** At every STOP point of the absorption flow (proposed target skill, proposed AP wording, proposed version bump) — present for CEO review and WAIT. Do NOT absorb-and-commit in one motion. The CEO may reject the target skill choice (AP-10 Confusion Protocol) or the AP wording. Absorption is done WHEN the commit lands and the CEO acknowledges, not when the Edit tool returns success. This reinforcement repeats because agents treat "wrote the AP" as "done".

## Rules absorbed

- **LAW-001** (Evolution): every mistake → lesson → skill → compounding
- **LAW-009** (Self-Evolution): agents get better every cycle — requires this loop
- **LAW-015** (Root-Cause Evolution): bug-fix requires LESSON file
- **LAW-017** (Success Is Skill): validated success → skill update
- **LESSON-085** (never declare done without e2e test): applied to "success" case
- **AMD-005** (Skill-First Evolution — 7-day absorption SLA): every lesson must be absorbed into a SKILL.md within 7 days. Skills are the evolution substrate; standalone lessons decay. See AP-5.

---

## Evidence trail

- **2026-05-20** | v1.13.0 evidence — claude-mac s1030 retired the legacy `vps_skill_extractor.py` cron on VPS as artifact of RULE ZERO doctrine working: extractor produced ZERO output for 20 consecutive days (2026-04-30 → 2026-05-20) because endpoint was hardcoded to `localhost:4000` but LiteLLM moved to Air. Audit surfaced the silent failure; Musk-step-2 chose DELETE over FIX since RULE ZERO substrate (SKILL.md APs + gbrain timeline + skill-evals) already covered the legacy compounding-from-task-results surface. Cron commented with full RETIRED marker citing this Timeline entry. Logrotate also installed for gbrain `/root/.gbrain/autopilot.log` (was 243 MB unrotated; now weekly with 100M trigger; force-rotated to 0 + .1=243M). **Cross-session stage-bleed observed live** during the same session: peer s1054 ran `git add -A` between this session's `git add` and `git commit --only` calls and absorbed the claude-mac COORD handshake file into their unrelated satory-proof-runner commit `a3109752` — session-coordination v1.33.0 AP-5 (anti-collision via `git commit --only`) demonstrated as load-bearing; without --only the stage-bleed window is unavoidable when peers commit at high cadence. No new AP here (the AP belongs in `session-coordination` which is peer-owned this session — `s108-mac-26485-20260520T1053`). No new LESSON (RULE ZERO). See [[COORD-2026-05-20-s1030-mac-opus-handshake]].
- **2026-05-11** | v1.13.0 — Added AP-14 and Current Rule 5 after Madi forwarded the Garry Tan framing "skills are the prompts" plus the repeated May-2026 Karpathy 12-rule prompt. Root cause: repeated high-standard prompts were preserved in chat/audit text but not explicitly treated here as a missing-skill signal. Rule: repeated prompt loop => find/update owner skill, not louder prompting. Source captured at `pages/sources/user-forwarded/skills-are-the-prompts-2026-05-11.md`. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.12.0 — Session 79 Mac Codex substrate audit: added AP-13 after root-causing the `LESSON` count drift. Current filesystem has 24 historical lessons; Apr 25 VPS auto-sync commits `70d9f60f` + `2bfa4ece` deleted 105 lesson receipts, and `commit-review-2026-04-26.md` explicitly changed the check from `==129` to `<=129`. The stale doctrine was in the shims/skills, not the filesystem. Follow-on TDD found the VPS pre-receive guard was count-only, so a hookless push could add a new lesson while staying below 129; patched the guard + test to reject any newly added/copied/renamed canonical `LESSON-NNN` path. Rule: 129 is a ceiling and historical namespace, not an exact count; never recreate deleted lessons to satisfy stale checks. No new LESSON file.
- **2026-04-18** | v1.11.0 — Session 48 Mac-interactive deep-audit (Madi-triggered, parallel to W-thread): updated AP-11 v1.9 4th-check section — "manual-only, next-session candidate" → "mechanical via `infrastructure` AP-48". Paired with infrastructure v2.40 → v2.41 same session. Scanner `tools/test_skill_version_parity.sh` now enforces all 3 structural checks on pre-commit RULE 4: (1) version parity (AP-43), (2) YAML validity (AP-46), (3) Timeline↔AP-bullet parity (AP-48). Evidence: deep-audit surfaced 2 real orphans accumulated across 1-2 sessions (`infrastructure` AP-45 from session 48 W4, `secrets-management` AP-10 from session 46-B A3) — both patched in the same deep-audit round. Orphan scanner live-tested POSITIVE 21/21 + NEGATIVE fabricated `/tmp/orph-test` with synthetic high-number AP claim and no matching bullet → exit 2. Doctrine-side impact: AP-11 v1.9's "agent compliance is the bottleneck" phase ends; machine compliance takes over. Meta-pattern `audit` AP-15 sub-class ("mid-session codified rule not applied to same-session edits") is mechanically closed for the AP-bullet dimension. No new LESSON (RULE ZERO).
- **2026-04-18** | v1.10.0 — Session 46 Mac-interactive (parallel to GOD_PROMPT thread). Added **AP-12** — YAML-invalid frontmatter silently drops gbrain ingestion. Evidence: new skill `session-operating-contract` v1.0.0 committed successfully (`6d0a0da6`), pre-commit RULE 4 (AP-43) passed, 4-way HEAD parity confirmed (`b4413768`), Air runtime rsync landed the file — but `mcp__gbrain__get_page pages/skills/session-operating-contract/skill` returned `page_not_found` and two `sync_brain` cycles showed 0 adds/modifies for the new skill. Root cause: frontmatter `related: [[agent-quality]], [[evidence-verification]], ...` — YAML parser rejects `[[` as malformed nested-sequence start. Gbrain ingester catches the exception silently, drops the page, sync response reports `synced` with no error surface. Pre-commit RULE 4 uses grep (not YAML parse), so the class of bug is invisible to the current mechanical gate. Fix (`ff860f49`): replaced `[[name]], [[name2]]` with bare `[name, name2]`; sync_brain re-ingested; 4 chunks created; page now resolvable in gbrain. Next-session compound gate candidate: extend `tools/test_skill_version_parity.sh` with `yaml.safe_load` step over every SKILL.md frontmatter block, wire into pre-commit RULE 4 — same AP-43 pattern that made AP-11 mechanical. Also first in-session demonstration of `session-operating-contract` rule 6 (failure→skill loop) working — the newly-created skill detected a failure mid-deployment and drove the capture per its own doctrine. No new LESSON (RULE ZERO).
- **2026-04-18** | v1.9.0 — Session 46 round-2 deep-audit: extended AP-11 with a 4th check — Timeline↔Anti-Patterns parity. Evidence: session-46 first round bumped `audit` v1.12 → v1.13 with frontmatter + H1 + Timeline all updated correctly (passed the manual scanner), but the AP-14 bullet was NEVER actually added to the Anti-Patterns section — orphan rule. The 3-check ritual passed vacuously because Timeline entries are free-form prose with no structural link to the AP section. 4th check: every Timeline entry describing `added AP-N` or `extended AP-N` must correspond to an actual AP-N bullet in Anti-Patterns. Manual-only until a future session extends `tools/test_skill_version_parity.sh` with Timeline↔AP-bullet grep and lets pre-commit RULE 4 (infrastructure AP-43) automate it. Also updated the "How to apply" section to reflect that AP-43 made the original 3-check scanner mechanical (was "next-session candidate" in v1.8; now live). Cross-ref `audit` AP-15 (self-compliance check — the meta-pattern that caught this orphan). No new LESSON (RULE ZERO).
- **2026-04-18** | v1.8.0 — Session 46 deep audit: added AP-11 (SKILL.md version parity — frontmatter + H1 + Timeline all three). Found 7 drifts across 20 skills; 2 were session-46 bumps (infrastructure v2.32 with H1 stuck at v2.29 — out by 3!, evidence-verification v1.6 with H1 v1.5), 5 multi-session pre-existing. Fixed all 7. Shipped `tools/test_skill_version_parity.sh` (manual drift scanner, exit 0 clean / exit 2 drift). Next-session candidate: wire into pre-commit hook for mechanical enforcement (Tan/Karpathy compounding-hook pattern — AP-35 precedent). No new LESSON (RULE ZERO).
- **2026-04-17** | v1.6.0 — Session 37: added AP-10 Confusion Protocol (gstack v0.18.0.0 adoption). Which-skill / extend-vs-new / implicit-already-in-skill / root-cause-or-symptom forks must ASK, not guess. Prevents cuckoo-rule absorption into wrong skill. No new LESSON (RULE ZERO).
- **2026-04-17** | v1.7.0 — Session 37: added Brain-aware absorption (G2 gstack v0.18.0.0) + CEO review reinforcement (G4). Absorption STOPs (target skill, AP wording, version bump) are review-only; agent must NOT treat "Edit returned success" as "done." No new LESSON (RULE ZERO).
- **2026-04-17** | v1.5.0 — Session 36: added AP-9 (dream cycle false positives from tool/data deploy lag). All 23 lessons in dream-cycle-proposals-2026-04-17 were already triaged (wiki-wide: 37 absorbed / 67 implicit / 24 archived = 128 total, zero ungrouped). Air cron must be running stale `dream_cycle.py` or against stale lesson data. Fix (Air rsync) deferred to session 37 pending Tailscale re-auth. The rule "dream-cycle proposal = deploy-bug-until-proven-otherwise" protects future agents from wasting 11+ skill edits on already-done work. **No LESSON file written — evidence lives here (skill Timeline) + gbrain timeline entry, per RULE ZERO.**
- **2026-04-15** | v1.0.0 created per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P2. The evolution engine itself. Absorbs §4 Karpathy SPL + Tan `/review` + JPL embed-into-procedures + LAWs 001/009/015/017 + LESSON-085.
- **2026-04-16** | v1.1.0 — Absorbed AMD-005 (7-day absorption SLA). Added AP-5 (ghost debt from unabsorbed lessons). Session 32 orphan absorption.
- **2026-04-16** | v1.3.0 — Session 35 Garry-Tan enforcement audit. Finding: 5 lesson id/title/H1 drift bugs (LESSON-113 used `name:` instead of `id:`; LESSON-123 title+H1 said 104; LESSON-124 H1 said 116; LESSON-125 H1 said 117; LESSON-126 H1 said 120). Fixed inline. Rule promoted to AP-7 with drift-scan snippet. **No LESSON file written for this finding — evidence lives here in the skill's timeline, per Tan/Karpathy pattern (skills + gbrain timeline only, never a separate LESSON file).** Drift-scan to be wired into pre-commit hook as a later phase.
- **2026-04-16** | v1.4.0 — Session 35 PHYSICAL-IMPOSSIBILITY hardening: added AP-8 ("Creating a NEW LESSON-NNN file"), rewrote "Current rules" to retire LESSON files entirely, replaced P1 with the SKILL+gbrain-timeline protocol, kept P1-legacy for editing existing LESSONs (subject to AP-7 drift gate). Pre-commit hook on Mac wiki rewritten (`.git/hooks/pre-commit`) to BLOCK any commit that adds a LESSON file (`--diff-filter=A` match `pages/lessons/individual/LESSON-NNN-*.md`). Hook also runs the AP-7 drift scan on every LESSON modification. Tested with a dummy LESSON-131-test.md — hook rejected with exit 1. CLAUDE.md updates in two places: Mac project `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` (RULE ZERO + Rule #6 retired) and wiki `Nous/CLAUDE.md` (RULE ZERO + BRAIN-FIRST RULE + Page Formats updated). LAW-015 amendment pending in this same session. VPS + Air hook deployment + Air `tools/light-probe.sh` deployment pending Tailscale re-auth — documented in HANDOFF for session 36.

## See also

- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[planning-discipline]]
- [[error-classification]]
- [[gbrain-ops]] — automation side of absorption
- [[LAW-001-evolution]]
- [[LAW-009-self-evolution]]
- [[LAW-015-root-cause-evolution]]
- [[LAW-017-success-is-skill]]
- [[LESSON-085-false-declaration-feature-done-without-end-to-end-test]]
