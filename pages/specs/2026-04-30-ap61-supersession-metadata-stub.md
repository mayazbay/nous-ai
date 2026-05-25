---
type: spec
id: SPEC-AP61-SUPERSESSION-METADATA-V0-2026-04-30
title: "AP-61 supersession metadata at gbrain index layer — stub capturing lane-D's surfaced gap"
tags: [spec, ap-61, supersession-metadata, gbrain, ranking, drift, third-spec, lane-A, session-100]
date: 2026-04-30
status: accepted-defaults-applied
last_updated: 2026-04-30
related: [2026-04-30-mercury-hybrid-retrieval-gap-analysis, 2026-04-30-doctrine-drift-detector-spec, 2026-04-30-llm-query-rewriter-shim-design, AUDIT-062-retrieval-quality-synthesis-2026-04-30, gbrain-ops, audit, mistake-to-skill]
source_count: 2
sources:
  - "Peer lane-D AUDIT-062 retrieval-quality synthesis, 2026-04-30 — surfaced this gap as 'the missing piece both grader spec and rewriter spec leave on the table'"
  - "Mercury thesis source page (karpathy-mercury-agent-memory-architecture-2026-04-30) — 'Conflict resolution: when two facts disagree, the system needs rules: newer wins, higher-confidence wins, or ask the user. Silent contradiction is failure.'"
---

# SPEC — AP-61 supersession metadata (stub)

> **This is a STUB.** Full spec needs `Skill(superpowers:brainstorming)` → `Skill(autoplan)` → implementation lane in a future session. This file exists so peer lane-D's AUDIT-062 finding does NOT decay. Per RULE ZERO, decay is the failure mode. Capture now, expand later.

## Provenance

Surfaced 2026-04-30 by peer lane-D's [[AUDIT-062-retrieval-quality-synthesis-2026-04-30]], a meta-synthesis across 4 retrieval-quality artifacts (Mercury harness spec, query-rewriter spec, AUDIT-061 substrate audit, Mercury thesis source page). Lane-D's verbatim framing:

> When a legacy synthesis page outranks the current authoritative doctrine in gbrain query results, the root cause is at the index/metadata layer. Reformulating the query (rewriter) or scoring the answer (grader) treats the symptom, not the cause.

> Per Mercury thesis ("Memory drift is real" + "Ranking matters more than storage"), the cleanest fix to gap 1 is structured supersession metadata that the ranker can parse. Today, drift correction is a prose `> ⚠️ DRIFT CORRECTION` header in LESSON-087 — invisible to both the BM25 ranker and the vector ranker.

The 6-probe evidence appended to the Mercury thesis source page confirmed the failure mode empirically: 2 of 6 retrieval probes ranked legacy synthesis pages above current canonical doctrine for `Telegram-MCP-ban` and `Musk-5-step` queries. The substrate is mechanically healthy (AUDIT-061: 100% embedding coverage, 0 dark, 0 orphan) AND semantically drifted (the ranker has no signal to demote superseded pages).

## The gap

Today, when canonical doctrine is updated:
- The new authoritative page is added to the wiki, gets indexed normally.
- The old page is marked superseded by adding a `> ⚠️ DRIFT CORRECTION` prose header.
- That header is **prose** — neither BM25 nor pgvector nor gbrain v0.10.1's ranker reads it as a structured signal.
- BM25 keeps ranking the old page on lex matches; pgvector keeps ranking it on cosine similarity to the original embedding.
- Result: agents searching gbrain for current doctrine sometimes get superseded pages first.

Neither [[2026-04-30-mercury-hybrid-retrieval-gap-analysis]] (output-side scoring) nor [[2026-04-30-llm-query-rewriter-shim-design]] (input-side rewriting) addresses this. They both treat downstream symptoms.

## Rough proposal (will be brainstormed properly in a future session)

A frontmatter contract the gbrain ranker can parse:

```yaml
---
type: source
id: legacy-synthesis-pre-2026-03
title: "Old synthesis from before the Q1 doctrine consolidation"
status: superseded                    # NEW
superseded_by: [karpathy-loop, session-operating-contract]   # NEW (wikilink list)
superseded_at: 2026-03-15             # NEW (ISO date)
superseded_reason: "Q1 doctrine consolidation merged 6 prior synthesis docs into 2 canonical skills"   # NEW (1-line)
---
```

The gbrain ranker reads `status: superseded` at query time and applies a configurable demotion factor (default: `score *= 0.3`) to the superseded page's relevance score. The newer canonical pages it points to get a small boost (`score *= 1.1`). Result: a query for "Telegram MCP ban" returns the current `[[telegram-routing]]` skill at the top instead of LESSON-087-pre-correction.

## Brainstorm-resolved decisions (s100-mac-23069 lane-A, 2026-04-30, recommended-defaults via "keep going" delegation)

The 6 open questions are resolved as follows. Madi can override any single answer with a one-line reply; otherwise these are the working assumptions.

### D1 — Frontmatter schema: signal by presence, NO status: field
**v1 fields (3, all required when superseded):**
- `superseded_by: [wikilink, ...]` (1+ wikilinks to current authoritative page(s)) — **PRESENCE of this field is the supersession signal**
- `superseded_at: YYYY-MM-DD` (ISO date)
- `superseded_reason: "<1-line>"` (rationale, ≤140 chars)

**Critical: NO `status:` field is added.** Autoplan v1 (full 6-voice, 2026-04-30) caught a BLOCKER: 782 existing wiki pages already use `status:` with 129 distinct values (`reviewed`, `draft`, `active`, `final`, `complete`, `alias-redirect`, ...). AP-61's previous proposed enum (`current|superseded|archived`) collided with all of them. Solution: drop the field entirely. The PRESENCE of `superseded_by:` is unambiguous (no other field uses that name in the existing vault — verified via `grep -rh '^superseded_by:' pages/ | wc -l = 6` known cases, all already-supersession markers).

**v2 (deferred, NOT in v1):**
- Partial supersession (some sections live, others dead)
- Graded confidence (0–1 demotion factor instead of binary)
- Page-level archival vs supersession distinction (e.g. `archived_at:` for dead-stop pages that don't redirect)

**Why minimal v1:** Pang/Karpathy ship-and-measure pattern. Presence-based signaling catches the obvious cases. Graded confidence is over-engineering until a concrete failure case exists.

### D2 — Ranker integration: query-time filter (cheapest, reversible)
At query time, the ranker reads each candidate page's frontmatter and applies:
- `superseded_by:` field present → `score *= <demotion>` (default `0.3`, configurable per gbrain config)
- `superseded_by:` field absent → no change (this is the default for the 99%+ majority of pages)
- `superseded_by:` target pages → `score *= 1.1` only if Phase-2-eval shows canonical-target demotion is happening; defer the boost in v1 (Codex Eng F8: canonical boost may create false gravity, ship demotion-only first)

**Demotion factor calibration: NOT 0.3 by default.** Autoplan v1 caught magic-number-ism. Phase-2 acceptance includes a sweep `{0.0, 0.1, 0.3, 0.5, 0.7, 1.0}` against lane-D's 6 retrieval probes; pick the smallest demotion that flips 2/6 fails to 0/6 without false demotion of useful history. Replace 0.3 with measured value before any production use.

**No new tables, no index rebuild, no embedding regeneration.** Pure read-time field-presence check + score multiply. Reversible by `gbrain config set supersession.demotion 1.0` (no demotion). Implementation lift: ~15 LOC in the ranker; gbrain v0.23+ work — OR a local post-retrieval reranker shim under Nous control (Codex CEO's reframe; preferred).

### D3 — Migration strategy: opt-in, manual at first; no retroactive bulk
**Day-1 policy:** every NEW supersession event (a new authoritative page replaces an older one) gets `status: superseded` + `superseded_by:` added to the old page MANUALLY by whoever creates the new page. Tooling: `tools/mark_superseded.sh <old-slug> <new-slug>` one-liner that opens both pages in $EDITOR with the right edits pre-staged.

**No bulk LLM-judged retroactive pass.** Two reasons: (a) LLM-judge for "is this superseded?" has the same calibration-set problem as the doctrine-drift LLM judge — silent doctrine reshaping. (b) Most "old" pages are `progress`/`task-result` (auto-gen chronologicals, ~791 of 1865 pages); they're not superseded, they're historical. Marking them superseded would be wrong.

**Lazy-migration trigger:** when an agent or Madi edits an old page that's clearly superseded (e.g. a LESSON file with a `> ⚠️ DRIFT CORRECTION` prose header), they convert the prose marker to structured frontmatter as a side-task during that edit. Compounds organically.

### D4 — Composability with gbrain-ops: NEW AP (AP-61), not a separate doctrine skill
**This becomes [[gbrain-ops]] AP-61** ("Supersession metadata frontmatter contract"), once the implementation lands. Per RULE ZERO, AP gets added to gbrain-ops SKILL.md when the failure→skill loop fires (i.e., once the first superseded-page-outranks-canonical incident is caught and codified). Until then, this spec is the proposal; the AP is the codification.

**Why no separate skill:** the failure mode (ranker doesn't demote superseded pages) is already gbrain-territory. Adding a separate `supersession-metadata` skill creates a 90th skill nobody invokes. AP-on-existing-skill is the smallest atomic shape per `mistake-to-skill` AP-11.

### D5 — Wiki-tooling integration: pre-commit validator + resolver counter
**Pre-commit hook addition** (gated on Phase 1 of implementation): for any page with `status: superseded`, validate that every `superseded_by:` wikilink resolves to an existing page. Failure rejects the commit with `superseded_by target [[X]] does not resolve`.

**Resolver enhancement:** `tools/check_resolvable.py` adds a `superseded` count to its JSON output: `{ok: 56, dark: 0, orphan: 0, superseded: N}`. Counter visible in `gbrain doctor` and soao output.

**`get_health` enhancement:** add `superseded_pages: N` field alongside `orphan_pages`. Solo-founder readability: when `superseded_pages` rises, doctrine consolidation happened; when `orphan_pages` rises, drift is accumulating. Different signals, different actions.

### D6 — Existing prose `> ⚠️ DRIFT CORRECTION` headers: opt-in script, no auto-migration
Ship `tools/find_drift_corrections.py` that scans wiki for prose drift-correction headers and reports candidates. **Output is a list, not a mutation.** Madi or an agent reviews each candidate, decides if it's truly superseded (might be partial/historical/contextual), and applies frontmatter manually via `tools/mark_superseded.sh`.

**Why no auto-migration:** drift-correction headers were written by humans for human reading. Automated conversion to structured frontmatter risks false-positives on contextual headers ("⚠️ This was the old approach, kept for historical reference") that AREN'T superseded — just annotated.

## Phases (Musk-ordered, falsifiable per phase)

### Phase 0 — Frontmatter schema landed; no ranker integration yet
**Acceptance:**
- `pages/schemas/supersession.v1.json` exists with the 4 required fields (D1).
- Pre-commit hook validates `superseded_by:` wikilinks resolve (D5).
- 1 example page in vault has `status: superseded` (proof-of-shape).
- Resolver counts `superseded` pages.

**Falsifiable:** `python3 tools/check_resolvable.py --wiki . --json | jq .resolver.superseded` returns ≥ 1.

**No ranker change yet.** This phase tests only the metadata + tooling. ~50 LOC. ~1 hour.

### Phase 1 — `tools/mark_superseded.sh` ships
**Acceptance:**
- `tools/mark_superseded.sh <old-slug> <new-slug>` writes `status: superseded`, `superseded_by:`, `superseded_at:`, `superseded_reason:` to old page; opens $EDITOR for `superseded_reason` rationale.
- `tools/test_mark_superseded.sh` passes on synthetic fixtures.
- Operator workflow: 1 command marks supersession.

**Falsifiable:** `tools/mark_superseded.sh test-old test-new && grep -q "status: superseded" pages/test-old.md`.

### Phase 2 — gbrain ranker reads `status` field (gbrain v0.23+ work)
**Out of wiki-repo scope.** This requires upstream gbrain CLI/MCP changes:
- Query-time field filter (D2).
- Configurable `supersession.demotion` (default 0.3).
- `gbrain doctor` reports superseded count.

**Acceptance gated on gbrain v0.23 release.** Until then, the metadata exists in the wiki but the ranker ignores it (graceful degradation).

### Phase 3 — `tools/find_drift_corrections.py` opt-in audit
**Acceptance:**
- Scans wiki for prose `> ⚠️ DRIFT CORRECTION` and similar legacy markers.
- Outputs a candidate list (slugs + line numbers + 1-line context).
- Operator reviews + applies via Phase 1 tool.
- **No auto-mutation.**

**Falsifiable:** runs on current wiki, reports a finite list of candidates Madi can spot-check.

## Rejection criteria for the whole spec

Any of these triggers a kill — surface to Madi, do not auto-tighten:
1. Phase 0 frontmatter schema causes a pre-commit-hook FP storm (>5 false rejects per week): schema is too strict; rethink.
2. After 60 days, < 3 pages have been marked `superseded`: nobody's using the tool; doctrine consolidation isn't actually happening; the metadata is solving a non-problem.
3. gbrain v0.23 doesn't ship Phase-2 ranker integration within 6 months: schema sits unused; kill spec OR contribute the ranker change upstream.

## Stays out-of-scope (this spec)

- Implementation: no `tools/mark_superseded.sh` written from this lane. Implementation lane opens after `Skill(autoplan)` runs on this draft.
- Bulk retroactive migration of 791 progress/task-result pages — NEVER. Those are chronological logs, not superseded doctrine.
- LLM-judge for supersession candidates — explicitly rejected per D6 rationale.
- gbrain ranker code changes — upstream gbrain repo work (v0.23+ milestone).

## Composition with sibling specs

| Spec | Layer | Solves what |
|---|---|---|
| [[2026-04-30-mercury-hybrid-retrieval-gap-analysis]] | Output | "Is the agent's reply *good* given what was retrieved?" |
| [[2026-04-30-doctrine-drift-detector-spec]] | Doctrine | "Are the rules in skill files actually being followed?" |
| [[2026-04-30-llm-query-rewriter-shim-design]] | Input | "Is the query well-formed before retrieval runs?" |
| **This spec** | **Index** | **"Is the ranker demoting superseded pages?"** |

Pang's self-healing harness composed with Mercury's hybrid retrieval composed with this index-layer fix = the full retrieval-quality stack. Each layer is independently shippable; together they close the loop the Mercury thesis describes.

## Falsifiability of this stub itself

```bash
# Acceptance to move stub → draft:
# Run Skill(superpowers:brainstorming) on this stub. Resolve ≥6 open questions.
# Output: status: stub-pending-brainstorm → draft-pending-autoplan.

# Acceptance to remain stub indefinitely (kill criterion):
# If 60 days pass and no new incidence of "legacy synthesis page outranks canonical doctrine"
# is observed in real /ask traffic (per Mercury Phase 1 grader output once it's live),
# this gap is hypothetical at solo scale. Kill spec.
```

## See also

- [[AUDIT-062-retrieval-quality-synthesis-2026-04-30]] — peer lane-D's synthesis that surfaced this gap
- [[2026-04-30-mercury-hybrid-retrieval-gap-analysis]] — sibling output-side spec
- [[2026-04-30-doctrine-drift-detector-spec]] — sibling doctrine-side spec
- [[2026-04-30-llm-query-rewriter-shim-design]] — sibling input-side spec (lane-D)
- [[gbrain-ops]] — operating procedures the implementation must compose with (especially AP-50 prose-blindness, which this spec proposes to fix structurally)
- [[mistake-to-skill]] — AP-11 3-edit ritual the eventual implementation must honor
- [[audit]] — AP-14/AP-15 evidence chain + codification ≠ self-application

## /autoplan review report v1 (full 6-voice, 2026-04-30)

> First autoplan run with full 6-voice dual-review (Codex CLI authed at 09:57 UTC; AP-61 first to benefit from real cross-model triangulation). 3 phases × 2 voices = 6 reviewers. **All 6 said TIGHTEN-FIRST.** 2 BLOCKERS, 8 high, 12 medium across phases.

### Cross-phase consensus (caught by 4-of-6 or more voices)

| Finding | Severity | Voices flagging it |
|---|---|---|
| **`status:` field name collision** with 782 existing pages using 129 distinct values (`reviewed`, `draft`, `active`, `final`, `complete`, ...) | **BLOCKER** | Codex Eng + Codex DX + DX Claude (3) |
| **Phase-0 spec-vs-disk gap** — `pages/schemas/supersession.v1.json` doesn't exist, pre-commit validator absent, resolver counter not wired | **BLOCKER** | All 6 voices |
| **`mark_superseded.sh` duplicate-YAML-keys bug** — appends new `status:` without removing existing | **BLOCKER** | Codex DX (only one to catch this exact failure mode) |
| **awk frontmatter injection fragility** — CRLF/multi-line YAML/literal `---` markers corrupt files | high | Eng Claude + Codex Eng |
| **`score *= 0.3` magic number** — uncalibrated against MRR/nDCG | high | CEO Claude + Codex CEO + Codex Eng (3) |
| **gbrain v0.22 ingest behavior on `superseded_by:` UNVERIFIED** — silent JSONB pass-through OR schema rejection (catastrophic) | high | Eng Claude + Codex Eng |
| **Phase-2 dependency on garrytan/gbrain v0.23+** — Madi has no commit access; off-repo gating | high | CEO Claude + Codex CEO + Codex Eng |
| **`find_drift_corrections.py` FP rate ~50%** — flags AP-61 spec itself + `## Historical` section headers | high | All 6 voices |
| **Mercury Phase-1 grader 70% obsoletes AP-61** — index-layer fix may be redundant once output-layer grader runs 30 days | high | CEO Claude + Codex CEO |
| **lint.py interaction hidden side-effect** — already skips duplicate-content checks for any file with `superseded_by` text → AP-61 hides existing detections | high | Codex DX (only one to grep lint.py) |
| **Wikilink resolution mismatch** — script writes `[[karpathy-loop]]` but real path is `pages/skills/karpathy-loop/SKILL.md` | medium | Eng Claude + DX Claude + Codex DX |
| **Idempotency partial-state blind spot** — only checks `status: superseded`, missing 3 of 4 fields silently passes | medium | Eng Claude + Codex Eng |
| **No rollback / `--dry-run` / `--help` flags** | medium | DX Claude + Codex DX |
| **Race conditions w/ 8 active peer lanes** — no per-file lock | medium | Eng Claude + Codex Eng |

### Phase 1 — CEO dual-voice (TIGHTEN-FIRST consensus)

- **CEO Claude:** RETHINK-leaning; argued AP-61 is 70% redundant with Mercury Phase-1 once it runs. Strong reframe: ship Phase-0 schema only, defer Phase-1+3 until Mercury telemetry confirms index-layer is on critical path.
- **CEO Codex:** TIGHTEN-FIRST; right-problem reframe = "prevent stale doctrine from entering answer context using cheapest owned mechanism that can be measured on live traffic." Crucial new alternative: **local post-retrieval reranker under Nous control (don't depend on garrytan/gbrain)**.

### Phase 3 — Eng dual-voice (TIGHTEN-FIRST consensus)

- **Eng Claude:** LEAKY architecture; 12 findings, 14-test minimum pre-Phase-1-real-data; strongest single finding = Phase-0 deliverables don't exist on disk despite spec claiming they're shipped.
- **Eng Codex:** TIGHTEN-FIRST; 12 findings with concrete file:line references; **caught the `status:` field collision (P0 #2)** that no other voice up to that point had identified by ground-truthing against actual file frontmatter; also caught `mv` cross-filesystem non-atomicity.

### Phase 3.5 — DX dual-voice (TIGHTEN-FIRST consensus)

- **DX Claude:** scorecard 3.75/10; 11 findings; ground-truthed 633+ pages with `status:` non-`current/superseded/archived` values.
- **DX Codex:** scorecard 18/80 = 2.25/10; 10 findings; **caught the duplicate-YAML-keys bug (P0 #3)** in `mark_superseded.sh` that no other voice had fully traced; ground-truthed 782 non-SKILL pages with 129 distinct status values; caught `lint.py` already-existing `superseded_by:` text suppression behavior.

### Aggregate verdict: REVISE-REQUIRED

Not just TIGHTEN — the schema collision + duplicate-keys bug + Phase-0 spec-vs-disk gap together constitute a **structural defect**, not a polish gap. Status flipped to `revise-required-pending-bs8`. The shipped tools (`mark_superseded.sh` + `find_drift_corrections.py`) are NOT safe to run on real data until at least the 3 BLOCKERS are fixed.

### Recommended revision plan (to land before any Phase-1 real-data run)

1. **Rename `status:` → `supersession_status:` (or drop it entirely; signal supersession by presence of `superseded_by:`).** Single-edit Karpathy "delete the part" fix. Eliminates the 782-page collision at v1, closes BLOCKER #1.
2. **Fix `mark_superseded.sh` duplicate-keys bug.** Don't append; either parse YAML properly (use `python3 + PyYAML`) or detect+rewrite-existing `status:` instead of inserting a new one. Closes BLOCKER #3.
3. **Ship Phase-0 deliverables actually:** `pages/schemas/supersession.v1.json` + pre-commit validator (transitive wikilink resolution + cycle detection, ~50 LOC python before Tier-A1 library scanners) + `tools/check_resolvable.py` superseded counter. Closes BLOCKER #2.
4. **gbrain v0.22 round-trip canary:** synthetic page with all fields → `mcp__gbrain__put_page` → assert ingest + search + get round-trip works, OR reject this whole approach until v0.23 lands. 3-minute test before any real mutation.
5. **Calibrate demotion factor:** sweep `{0.0, 0.1, 0.3, 0.5, 0.7, 1.0}` on lane-D's 6-probe set; pick smallest demotion that flips 2/6 fails to 0/6. Replace magic 0.3 with measured value.
6. **Consider Codex CEO's reframe — local post-retrieval reranker under Nous control.** Don't bet entire Phase-2 on upstream garrytan/gbrain v0.23 timeline. Implement post-retrieval shim in `command_center.py` or `tools/gbrain_smart_query.py` (when it lands).
7. **Tighten `find_drift_corrections.py`** per multiple-voice convergence: drop `header_supersede` + `bold_correction` patterns; require `⚠️` AND explicit `superseded|deprecated|replaced` word; restrict to first 30 lines of each page; exclude pages with `tags: spec`.
8. **Mercury sequencing:** per CEO dual-voice consensus, **do not run mark_superseded.sh on real data until Mercury Phase-1 telemetry confirms `stale_doctrine` `issues:` correlate with retrieval-rank-of-superseded-page > 1.** Otherwise this whole spec is solving a 2/6-probe artifact.

### Decision Audit Trail (gstack 6-principles)

| # | Phase | Decision | Class | Principle | Rationale |
|---|---|---|---|---|---|
| 1 | P0 | Skip Phase 2 (Design) | Mechanical | P5 explicit | UI scope = 0 hits |
| 2 | P0 | Codex available, run full 6-voice | Mechanical | P6 bias-action | First successful Codex autoplan after usage_limit cleared |
| 3 | P1+P3+P3.5 | All 6 voices ran successfully | Mechanical | (no degradation) | Real cross-model triangulation |
| 4 | P3 | Mark `status:` field collision BLOCKER | Auto | P5 explicit | 4-of-6 voices ground-truthed against 782+ existing pages |
| 5 | P3 | Mark Phase-0 spec-vs-disk gap BLOCKER | Auto | P1 completeness | 6-of-6 voices independently flagged |
| 6 | P3.5 | Mark duplicate-YAML-keys BLOCKER | Auto | P5 explicit | Codex DX traced exact failure mode in code |
| 7 | P3 | Set status `revise-required-pending-bs8` not just `tighten` | Auto | P5 explicit | 3 BLOCKERS = structural not polish |
| 8 | P1 | Surface CEO Codex reframe (local reranker) as TASTE | Taste | P3 pragmatic | Reasonable people could disagree on upstream-vs-owned |

### Surfaced taste decisions for Madi (T1-T3)

**T1 — Field rename: `status` → `supersession_status` OR drop entirely?**
- A (recommended): drop the `status:` field; presence of `superseded_by:` signals supersession. Cleanest, no schema collision, zero migration debt for 782 existing pages.
- B: rename to `supersession_status: superseded`. Keeps explicit enum for ranker config but adds one new field name to a vault with 633+ pages already using `status:`.
- C: keep `status: current|superseded|archived` and write a 782-page migration. Highest churn, breaks every existing query.

**T2 → A APPLIED: local Nous-controlled post-retrieval reranker.** Phase-2 ranker integration does NOT depend on garrytan/gbrain v0.23 timeline. Implementation lives in `command_center.py` or `tools/gbrain_smart_query.py` (future). Owned, measurable, reversible via env var `SUPERSESSION_DEMOTION=1.0`. Upstream gbrain v0.23 contribution becomes opportunistic, not blocking.

**T3 → A APPLIED: Mercury-sequenced.** No real-data `tools/mark_superseded.py` runs until Mercury Phase-1 grader produces ≥30 days of telemetry showing `stale_doctrine` issue (or equivalent) correlates with index-rank-of-superseded-page > 1. Until then, the BLOCKER-fix tooling shipped this session sits cold. Don't optimize a layer that may not be on the critical path.

## Timeline

- **2026-04-30** | Stub created in s100-mac-23069 lane-A from peer lane-D's AUDIT-062 finding. Captures the missing third piece neither Mercury nor query-rewriter specs cover (index-layer supersession metadata vs output-side scoring vs input-side rewriting). Status: `stub-pending-brainstorm`.
- **2026-04-30** | `Skill(superpowers:brainstorming)` ran. 6 D1-D6 questions resolved with recommended defaults. Status: `stub-pending-brainstorm` → `draft-pending-autoplan`. 103 → 199 lines.
- **2026-04-30** | `Skill(autoplan)` v1 ran in FULL 6-VOICE (Codex usage_limit cleared at 09:57 UTC). 3 phases (CEO + Eng + DX, Design skipped no UI scope). All 6 voices verdict: TIGHTEN-FIRST. 2 BLOCKERS surfaced (status field collision + Phase-0 spec-vs-disk gap), 1 critical implementation bug (duplicate YAML keys in mark_superseded.sh), 8 high, 12 medium. Status: `draft-pending-autoplan` → `revise-required-pending-bs8`. The shipped Phase-1 tooling (mark_superseded.sh + find_drift_corrections.py) is NOT safe to run on real data until BLOCKERS fixed. 8-row Decision Audit Trail. 3 taste decisions (T1-T3) surfaced for Madi.
