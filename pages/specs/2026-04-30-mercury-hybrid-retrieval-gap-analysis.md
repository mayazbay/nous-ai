---
type: spec
id: SPEC-MERCURY-HYBRID-RETRIEVAL-V1-2026-04-30
title: "Mercury hybrid retrieval gap-analysis + self-healing grader harness for /ask"
tags: [spec, mercury, hybrid-retrieval, self-healing-harness, grader, ceo-hierarchy, gbrain-ops, lane-A, session-100]
date: 2026-04-30
status: accepted-with-defaults
last_updated: 2026-04-30
related: [gbrain-ops, ceo-hierarchy, session-operating-contract, karpathy-loop, karpathy-coding-principles, audit, mistake-to-skill]
source_count: 3
sources:
  - "Peter Pang (CREAO), 'The Self-Healing Agent Harness', 2026-04-28 (X thread + Substack-style essay)"
  - "Mercury hybrid-retrieval thesis — gbrain v0.10.1 lex+vec+hyde sub-query design"
  - "ceo-hierarchy v1.2.3 telemetry — ~/nous-agaas/logs/ask-hierarchy.jsonl"
---

# SPEC — Mercury hybrid retrieval gap-analysis + self-healing grader harness for /ask

> **Lane:** session-100 lane-A (s100-mac-23069). Read-only audit + spec-only deliverable. **No code shipped from this lane.** `Skill(autoplan)` ran 2026-04-30 (subagent-only, codex unavailable). Aggregate verdict: TIGHTEN-FIRST + sibling-spec. 24 fixes auto-applied to the body; 6 taste decisions (T1-T6) defaulted per Madi's "keep going" greenlight (3× repeated session-100 prompt = approve recommended defaults). Status: `accepted-with-defaults`. Implementation lane opens in a future session. Sibling reframe captured at [[2026-04-30-doctrine-drift-detector-spec]] (T6).

## 0. Executive (Musk step-2 first)

**The gap (what is currently missing):** Nous AGaaS has rich retrieval substrate (gbrain v0.10.1 lex/vec/hyde, 1523 pages, 100% embedding coverage) and rich routing telemetry (`~/nous-agaas/logs/ask-hierarchy.jsonl` per [[ceo-hierarchy]] v1.2.3 Rule 4–6) but **no closed loop that scores retrieval or response quality on live `/ask` traffic and feeds the score back into either the retrieval policy or the engineering pipeline.** Without that loop, the Mercury hybrid-retrieval design and the Tan/Karpathy/Finn skills-compound architecture can drift silently — exactly the failure mode RULE ZERO and [[session-operating-contract]] §6 (failure→skill) try to prevent, but only post-hoc and only when a human notices.

**The Musk step-2 question:** what deletes? **The proposal is to delete nothing existing yet** — the retrieval stack is healthy ([[AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30]] verified GREEN). What deletes is the *manual* grader role: today the only judge of `/ask` quality is Madi reading the answer on his phone. We replace that with a panel of 3 model-family-diverse async judges scoring the JSONL stream we already write, with zero added user-facing latency.

**The 10% add-back (Musk rule):** keep one human-calibration sample (~5% of judged turns weekly) so the panel can never drift away from Madi's taste without a tripwire firing.

## 1. Why this is a Mercury problem and a Pang problem

[[gbrain-ops]] currently exposes three sub-query primitives: `lex` (BM25 keyword), `vec` (semantic), `hyde` (hypothetical-document). The "Mercury" framing is hybrid: best results come from running multiple sub-queries in parallel and merging by score. That's the **input** side of retrieval.

Peter Pang's "Self-Healing Agent Harness" essay (2026-04-28) describes the **output** side of the same loop:

| Pang component | Role | Nous AGaaS analogue today | Nous AGaaS gap |
|---|---|---|---|
| **Component 1 — Tri-judge panel grader** on live traffic, async, per-category rubric, schema-locked tool call, mathematical consensus across 3 model families | Replaces human QA review and offline benchmark evals — a low score on `messageId X` is both a metric and a bug report | `~/nous-agaas/logs/ask-hierarchy.jsonl` records every `/ask` turn with `correlation_id=tg_<msg_id>`, tier-1/tier-2 spans, cost, latency, model. **No quality score is written.** | No grader. No category router. No persisted `quality` / `issues` / `confidence` per turn. |
| **Component 2 — 6-job engineering pipeline** (detect→investigate→fix→verify→re-grade→report) | Turns scores into Linear tickets, draft PRs, verified fixes, re-grade-on-close, regression revert | Closest thing: VPS `vps_skill_extractor.py` (10-min cron) extracts skills from task results, plus RULE ZERO: failure→skill loop captured manually | No clustering of poor turns. No automated triage. No automated PR. The "engineering pipeline" today is one human (Madi) + 1–4 Claude/Codex sessions reading handoffs. |
| **Component 3 — AI-gated grey rollout bridge** (10% canary cohort scored against baseline; statistical promotion ladder; zero staging env) | Lets model swaps / system-prompt changes / tool-contract changes ship safely without staging | Air launchd `nightly-update-check` exists; OpenClaw hot-reload exists; **but no scored cohort comparison.** Every model swap today is "all 100% or nothing." | No traffic split, no head-to-head scoring, no automatic revert. |

**Together these three components ARE the self-healing loop.** Mercury (lex+vec+hyde merge) is the retrieval engine; Pang's harness is the evaluation engine. Without the harness, Mercury's quality is unknowable; without Mercury, the harness has nothing to evaluate against. They compose.

## 2. Phased proposal (Musk-ordered: question → delete → simplify → accelerate → automate)

Each phase ships independently, has a falsifiable acceptance metric, and gets re-reviewed via `Skill(autoplan)` before merge.

### Phase 1 — Passive grader on `/ask` JSONL (no behavior change)

**Question the requirement first:** do we even need a tri-judge panel, or is a single-judge baseline enough? **Answer:** start with single-judge to ship in days, not weeks. [[karpathy-coding-principles]] Principle 2 (Simplicity First) — three judges is a Component-1 future enhancement, not a Phase-1 requirement.

**Scope:**
- New cron on Air (or VPS): every 5 min, read tail of `~/nous-agaas/logs/ask-hierarchy.jsonl`, find turns from last 15 min that have `final_response_text` AND no `quality_v1` field yet.
- For each, sample at the [[ceo-hierarchy]]-aware rate: 10% of grok-ceo Tier-1, 100% of Tier-3 (Codex / Opus direct), 100% of urgent-keyword bypass cases.
- Send to ONE judge (DeepSeek V4 Pro initially — cheap, already wired via LiteLLM, not the same family as production Tier-3 Opus, so self-preference is bounded).
- Persist verdict back to a sibling file `~/nous-agaas/logs/ask-grader.jsonl` keyed by `correlation_id` (NEVER mutate ask-hierarchy.jsonl — append-only invariant per [[gbrain-ops]] AP-7 silent-success ban).
- Schema-locked tool call: `{category ∈ {coding, research, status, ops, regulatory, satory, kazakhstan, telegram-meta, other}, quality ∈ {excellent, good, acceptable, poor}, issues ⊆ {incomplete, hallucination, tool_misuse, missed_context, wrong_routing, infra_flake, drift_artifact, persona_cosplay, no_done_protocol}, confidence ∈ [0,1], reasoning: 2–3 sentences}`.
- **Anti-pattern guard ([[karpathy-loop]] AP-5):** the grader is a *passive* observer. It does NOT replan, retry, or rewrite the response. Phase 1 is read-only.

**Falsifiable acceptance:**

```bash
# Metric M1.1 — coverage
jq -s 'length' ~/nous-agaas/logs/ask-grader.jsonl  # ≥ 50 graded turns over 7 days
# Metric M1.2 — sampling fidelity
jq -r '.tier' ~/nous-agaas/logs/ask-grader.jsonl | sort | uniq -c
# Expect: tier-3 ≥ 95% of tier-3 traffic, tier-1 ≈ 10% ± 3pp
# Metric M1.3 — schema conformance
jq -r 'select(.quality == null or .category == null) | .correlation_id' ~/nous-agaas/logs/ask-grader.jsonl
# Expect: empty (zero malformed)
```

**Cost ceiling (Magic-Wand-Number):** ≤ $1.50/day grader spend. Hard-stop: if `ask-grader-spend.jsonl` shows 7-day total > $10.50, the cron must self-throttle. Mirror the [[ceo-hierarchy]] $30/day cap pattern; reuse `_compose_cost_footer` style accounting.

**What deletes if Phase 1 ships well:** the manual mental grader Madi runs every time he reads a phone reply. He still reads it; he just doesn't have to be the only judge.

### Phase 2 — Cluster + triage to skill candidate, NOT auto-PR

[[karpathy-coding-principles]] Principle 3 (Surgical Changes) and [[karpathy-loop]] AP-2 (hygiene-disguised-as-value) both say: do not chase the dashboard. Pang ships auto-PRs (3/day cap, hard exclusions); Nous AGaaS does NOT have a code monorepo with predictable PR-review bandwidth, so Phase 2 stops one step earlier.

**Scope:**
- Daily Air cron at 09:00 (after morning-brief 04:00, after morning-update-apply 05:07 — see [[architecture-quickref]]) reads last 24h of `ask-grader.jsonl`, clusters poor+acceptable turns by `(category, primary_issue)` pair, scores each cluster on a 5-axis severity (volume, recency, criticality, repeat-offender, blast-radius — Pang's 9-axis simplified for our scale).
- For top-3 clusters, write a candidate-skill-update markdown file at `pages/audits/grader-cluster-YYYY-MM-DD-<short-id>.md` containing: representative `correlation_id`s, exact quoted user query, exact quoted response, judge reasoning, and a *suggested* skill+AP to extend. **Do NOT mutate any SKILL.md.** [[mistake-to-skill]] AP-11 (3-edit ritual) requires human authorial approval per RULE ZERO.
- Push gbrain timeline entry on `pages/audits/grader-cluster-…` page so the cluster is searchable.
- Alert via `tools/tg_send.sh` ONLY if a cluster has severity > threshold AND repeats 3 days in a row. Avoid Telegram noise — [[operator-boundaries]] applies.

**Falsifiable acceptance:**

```bash
# Metric M2.1 — cluster output exists
ls pages/audits/grader-cluster-*.md | wc -l   # ≥ 1 per week of operation
# Metric M2.2 — false positive rate (manual review weekly)
# Madi reviews top cluster, marks {agree, disagree, ambiguous}.
# Target: agree ≥ 60% by week 4. If < 60%, switch judge model OR refine rubric.
# Metric M2.3 — no SKILL.md mutation by automation
git log --since="$(date -d '24 hours ago' '+%Y-%m-%d')" --author='cron' --name-only -- 'pages/skills/*/SKILL.md' | wc -l   # MUST be 0
```

**What deletes:** the "did anything regress this week" anxiety question that today only `tools/auto_checkpoint.py` partially answers.

### Phase 3 — Mercury hybrid-retrieval grader (the original lane question)

This is where Mercury and Pang merge. The Phase-1 grader scores ANSWERS. Phase 3 scores RETRIEVALS — the lex+vec+hyde merge that fed each gbrain-grounded answer.

**Scope:**
- For every `/ask` turn that touched gbrain (detectable via Tier-1 `research_only` classification per [[ceo-hierarchy]] Rule 1, OR via `mcp__gbrain__query` invocation in tier-2 trace), persist the candidate-set: top-K results from each sub-query (lex, vec, hyde) before merge.
- Grader judges: of the K candidates returned, was the top-3 set actually relevant to the user query? Use binary relevance per result + nDCG@5 as the headline metric.
- Track per-sub-query precision separately. If `lex` is dragging the merge down for some category, the merge weights need re-tuning. If `hyde` is the only useful retriever for "regulatory" queries, weight it harder there.
- Output: weekly `pages/audits/mercury-retrieval-week-YYYY-WW.md` with per-sub-query nDCG@5 trend.

**Falsifiable acceptance:**

```bash
# Metric M3.1 — nDCG@5 baseline established (week 1) and tracked
ls pages/audits/mercury-retrieval-week-*.md | sort | tail -1
# Metric M3.2 — retrieval-quality regression alarm
# If week-N nDCG@5 drops > 0.10 vs week-(N-1), tg_send alert and open audit page automatically.
```

**What deletes:** the "is gbrain getting smarter or dumber over time" question that today is unanswerable. Today AUDIT-061 confirms the substrate is HEALTHY (1563 pages, 0 dark, 100% embeddings) but health ≠ usefulness. Phase 3 is the usefulness gauge.

### Phase 4 — AI-gated grey rollout bridge (deferred — needs autoplan)

This is genuinely new doctrine and touches infrastructure (factory routing, OpenClaw model selection, async traffic splitting). Per [[karpathy-loop]] AP-5, this **must** go through `Skill(autoplan)` before any implementation lane opens. Out of scope for this spec.

The placeholder design: when a model swap PR (e.g. DeepSeek V4 Flash → V4 Turbo) is being considered, route 10% of `/ask` traffic to the new variant for 200+ turns, score head-to-head with Phase 1 grader, statistical-test the delta, auto-revert if `Δ ≤ -0.15` p<0.05. Pang's promotion ladder verbatim. **Don't build this yet.**

## 3. Composition with existing doctrine

This spec proposes nothing that conflicts with current rules. It composes with:

- **RULE ZERO** ([[CLAUDE]] header): Phase 2 produces *candidate* skill updates as audits, but only humans (or `Skill(autoplan)`-gated automation in a future phase) commit SKILL.md changes. The pre-commit hook still rejects new LESSON files.
- **[[session-operating-contract]] §4 DONE protocol:** the grader judges whether the agent EMITTED four artifacts when claiming done. `no_done_protocol` is one of the structured `issues` enums.
- **[[session-operating-contract]] §7 hard-banned:** `persona_cosplay` is a structured `issues` enum. The grader is the mechanical detector for AP-1 violations.
- **[[ceo-hierarchy]] Rule 4 cost footer:** Phase 1 footer extension — append `… | grade $0.0X` once the grader runs on that turn (latent, async, written in next reply if not yet judged).
- **[[gbrain-ops]] AP-50 (gbrain v0.10.1 prose-blindness):** the Phase-3 retrieval grader uses ripgrep + Obsidian backlink + gbrain combined for ground-truth relevance, not gbrain alone.
- **[[karpathy-coding-principles]] Principle 1 (Think Before Coding):** every Phase ships a falsifiable acceptance metric BEFORE the code, never after.
- **[[audit]] AP-14/AP-15 evidence chain + codification ≠ self-application:** every grader cluster page that proposes a skill update gets manually cross-checked against the substrate before any human or autoplan loop applies it.

## 4. Open questions (route to /codex CEO via Telegram for resolution)

1. **Judge model for Phase 1 — DeepSeek V4 Pro vs Grok vs Gemini?** Decision criteria: cost / family-distance from production / latency. [[ceo-hierarchy]] already wires DeepSeek + Grok via LiteLLM; Gemini would need `mcp-registry` lookup and key provisioning.
2. **JSONL append vs SQLite for grader history?** Append is simpler and matches the existing ask-hierarchy.jsonl pattern; SQLite would let Phase-2 clustering be a SQL `GROUP BY` instead of `jq | python`. Default to JSONL until Phase 2 proves clustering hot-loop.
3. **Telegram alert frequency:** Phase 2 says "3 days repeat" — is that aggressive enough? Conservative enough? Want Madi's call.
4. **Mercury Phase-3 ground truth labels:** binary relevance is cheap; do we want LLM-judged graded relevance (0-3 scale)? Affects nDCG@5 fidelity.
5. **Should Phase 1 also score `/codex` turns?** Codex is the CEO path; arguably the answers there are worth grading more, not less. But sampling at 100% and a higher per-judgment cost ceiling may be needed.

## 5. What this spec is NOT

- **Not a doctrine skill** — per [[karpathy-loop]] AP-5, new doctrine skills require `Skill(autoplan)` review. This is a gap-analysis spec; the doctrine extraction (if Phase 1 ships and proves out) happens via `mistake-to-skill` AP-11 in a later session.
- **Not a code change** — no SKILL.md edits triggered by THIS spec. Cross-references in existing skills (gbrain-ops AP timeline, ceo-hierarchy "see also") may be added as small AP-11 conformant updates in this same lane only if the spec is approved BS8.
- **Not a Telegram-routed deliverable** — this is a substrate-only artifact. Madi reads it via Obsidian or `mcp__gbrain__get_page`. The summary push to Telegram is a separate `tools/tg_send.sh` call after this commit lands.

## 6. Falsifiability of the spec itself

**Acceptance gate to move this from `draft-for-bs8-review` → `accepted`:**

```bash
# This file resolves cleanly through the existing wiki tools.
python3 tools/check_resolvable.py --wiki . --json | jq '.orphan, .dark'  # both 0
ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain search 'Mercury hybrid retrieval gap analysis self-healing harness Pang grader' --limit 5"
# Expect this page in top-3 within 5 min of next gbrain ingest cycle.
```

**Rejection criteria** (any one triggers a rewrite, not a tweak):
- Phase-1 cost ceiling unachievable: confirmed by single-judge dry-run on 100 historical turns showing > $0.30/turn average.
- Phase-2 cluster signal-to-noise < 30% agree-rate after 4 weeks: scrap clustering, fall back to "raw poor-turn list, human reads."
- Phase-3 retrieval grader cannot get K candidates from gbrain pre-merge (architectural blocker in v0.10.1 / would need v0.11+ first).

## 7. See also

- [[AUDIT-062-retrieval-quality-synthesis-2026-04-30]] — peer lane-D's cross-spec synthesis confirming GRADER-FIRST sequencing and surfacing the missing AP-61 supersession-metadata gap.
- [[2026-04-30-llm-query-rewriter-shim-design]] — sibling input-side spec (lane-D); orthogonal to this output-side grader; per AUDIT-062, holds until this Phase 1 produces ≥50 graded turns then revisits with grader-derived eval data.
- [[gbrain-ops]] — operating procedures for gbrain v0.10.1+, including AP-50 prose-blindness and the autopilot bounded-cycle rules.
- [[ceo-hierarchy]] — Tier-1/2/3 routing, JSONL telemetry, urgent-keyword bypass, the substrate this spec builds on.
- [[session-operating-contract]] — DONE protocol, RULE ZERO, hard-banned patterns.
- [[karpathy-loop]] — multi-virtual-reviewer mandatory gate (AP-5), 6-axis session-close scorecard.
- [[karpathy-coding-principles]] — think-before-coding, simplicity-first, surgical changes, goal-driven execution.
- [[musk-algorithm]] — 5-step canonical order, idiot-index, magic-wand-number, factory-is-product.
- [[audit]] — evidence chain, codification ≠ self-application.
- [[mistake-to-skill]] — AP-11 3-edit ritual for any subsequent skill update.
- [[AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30]] — the substrate-health audit that confirmed the retrieval *infrastructure* is healthy; this spec is what determines whether it is *useful*.

## /autoplan review report (s100-mac-23069 lane-A, 2026-04-30)

> Codex unavailable on Mac → all 3 phases ran in **subagent-only** degradation mode per autoplan skill matrix. Phase 2 (Design) **SKIPPED** — UI scope detection returned 6 matches but all 6 were false positives (Pang's 3-component pattern, "dashboard" idiom). DX scope: 14 matches (real — agent-as-user product surface).

### Phase 1 — CEO review

**Verdict:** RETHINK. 10 findings (2 critical, 4 high, 4 medium). Core argument: spec solves wrong problem at wrong scale. Pang's harness fits a 30-engineer SaaS shipping 3-8x/day; Madi is a solo founder doing his own real-time QA on his phone. The 4-phase commitment is a 6-month attention tax. **10x reframe proposed:** "doctrine drift detector" not "/ask quality grader" — pick 5 random skills weekly, ask LLM "is this skill being followed?" Catches the failure mode RULE ZERO is meant to catch, not the one Madi already catches with his eyes.

**Strongest dismissed alternatives the CEO surfaced:**
- (a) NO grader. One weekly human review of 10 random turns. 50 min/week, $0 infra.
- (c) Grader judges ONLY DONE-protocol presence (mechanical detector for AP-1). Cheap, falsifiable, project-native.
- (d) Skip grader; A/B test Mercury retrieval directly (lex vs lex+vec vs lex+vec+hyde) for next 200 gbrain-touching turns. Madi tags wins/losses on Telegram.

### Phase 3 — Eng review

**Verdict:** TIGHTEN-FIRST. Architecture is "LEAKY — directionally correct but underspecified on concurrency, rotation, schema enforcement, and recovery." 15 findings, 14-test minimum pre-Phase-1 plan, 9-row failure-modes registry. Top 4 critical/high gaps:
1. **No state-recovery contract** (F1) — no `ask-grader.state.json`, no idempotency key on `correlation_id`, crash mid-batch = double-grade + double-bill.
2. **`log-rotate` Sun 03:00 silently breaks tail offset weekly** (F2) — append-only invariant is fictional; need inode-aware tail.
3. **Cost ceiling has no real circuit breaker** (F4) — file-based cap with no LiteLLM-side budget tag = silent overrun. Use LiteLLM `metadata.user_id="grader"` + native budget enforcement; reconciliation at 23:55.
4. **Phase 3 is blocked on a 200-line gbrain refactor**, not a 1-line patch (F10) — pre-merge candidate exposure requires API versioning + payload widening + consumer updates. Make Phase 3 a separate gbrain-v0.11 milestone.

Plus: 5/5/5 cron staggering (Phase-1 to `*/5+2`; Phase-2 daily 09:00→09:23), `flock` lockfile for single-instance, `caffeinate -i` if cron lives on Mac (or move to VPS — host decision is load-bearing, not "or").

### Phase 3.5 — DX review

**Verdict:** TIGHTEN-FIRST. DX scorecard 21/80 (Discoverability 2, Escape Hatches 1, Onboarding 3, Composability 3). Time-to-hello-world for an agent asking "did my last /ask get a poor verdict?": **12-18 min**, hard floor at "never" for ambiguous schema fields. 14 findings. Top 4 critical/high gaps:
1. **First-poor-verdict signal is invisible for 2-4 weeks** (F1) — Phase 1 writes JSONL only; Phase 2's tg_send needs 3-day repeat. Bridge with **same-day digest at 21:00 Astana** from Phase 1.
2. **No `/grade <msg_id>` Telegram command** (F2) — phone-as-dashboard pattern broken. Madi must SSH+jq.
3. **`/trace tg_<id>` does NOT surface verdict** (F3) — composability gap. Phase-1 acceptance must require `command_center.py` join `ask-grader.jsonl` on `correlation_id` and append a `Verdict:` line.
4. **No kill switch / scope filter** (F7) — Madi can't pause grader during Satory migration storm. Need `~/nous-agaas/grader.policy.json` + `/grader pause 24h` Telegram command.

Plus: enum drift uncontrolled (F6 — needs `pages/skills/grader-rubric/SKILL.md` v1 owning the enums); naming inconsistency (`ask-grader.jsonl` is actor-named, but data is verdicts → `ask-verdicts.jsonl`); cluster-page template undefined; schema versioning absent.

### Cross-phase themes (concerns flagged in 2+ phases independently)

| Theme | CEO | Eng | DX | Resolution |
|---|---|---|---|---|
| Signal invisibility / empty-state UX | F2 (manual-burden) | F12 (no review verb) | F1+F4 (no digest, no heartbeat) | Daily digest at 21:00 + heartbeat record (auto-decided). |
| Cost-cap enforcement hand-wavy | F4 | F4 | F12 (no per-turn floor) | LiteLLM-side budget tag + per-turn $0.05 floor (auto-decided). |
| Phase 3 architecturally blocked on gbrain v0.11 | F5 | F10 | (silent) | Decouple Phase 3 from Phase 1/2; make it explicit gbrain-v0.11 dependency (auto-decided). |
| Schema / enum versioning vacuum | (silent) | F5 | F6+F14 | Own enums in `pages/skills/grader-rubric/SKILL.md` v1; record `schema: "grader.v1"` per record (auto-decided). |
| Composability with existing /trace + tg_send | (silent) | F12 | F3+F2+F5+F7 | `/grade <msg_id>` + /trace JOIN + `/grader pause` Telegram surfaces (auto-decided). |
| Solo-scale operator surface vs cron-output-on-disk | reframe | F13 host-decision | F1+F7 | **Surfaced as user-facing taste decision (T1) — not auto-decided.** |

### Decisions

| # | Phase | Decision | Class | Principle | Rationale | Rejected |
|---|---|---|---|---|---|---|
| 1 | Phase 0 | Skip Phase 2 (Design) | Mechanical | P5 explicit | All 6 UI-keyword matches were false positives | — |
| 2 | Phase 0 | Run subagent-only on all 3 phases | Mechanical | (codex unavailable) | `command -v codex` returned missing | — |
| 3 | Phase 1 | Run dual reviews on remaining phases | Mechanical | P6 bias-action | autoplan AP-5 mandates multi-reviewer for new doctrine | skip-reviews |
| 4 | Phase 3 | Add `ask-grader.state.json` checkpoint + correlation_id idempotency | Auto | P1 completeness | Eng F1 critical gap | hope-cron-never-crashes |
| 5 | Phase 3 | Inode-aware tail; read `.1` suffix on rotation | Auto | P1 completeness | Eng F2 + log-rotate Sun 03:00 reality | trust-rotation-not-to-happen |
| 6 | Phase 3 | LiteLLM `metadata.user_id="grader"` + server-side budget; reconciliation at 23:55 | Auto | P5 explicit | Eng F4 + CEO F4 | file-based-cap-only |
| 7 | Phase 3 | `flock -n` lockfile, single-instance guarantee | Auto | P5 explicit | Eng F7 | trust-launchd-not-to-coalesce |
| 8 | Phase 3 | Stagger Phase-1 cron to `*/5+2`; Phase-2 daily 09:00→09:23 | Auto | P5 explicit | Eng F6 | collide-with-gbrain-autopilot |
| 9 | Phase 3 | Schema enforcement via LiteLLM `response_format` + Pydantic validation; quarantine + alarm on fail | Auto | P1 completeness | Eng F5 | hope-LLMs-return-clean-JSON |
| 10 | Phase 3 | Deterministic sampling: `hash(correlation_id) % 100 < 10` | Auto | P5 explicit | Eng F11 (replay/audit) | random-sampling |
| 11 | Phase 3.5 | Heartbeat record every cron tick (file is never empty) | Auto | P1 completeness | DX F4 + CEO regret-2 (drift uncaught) | empty-file-on-day-0 |
| 12 | Phase 3.5 | Daily digest at 21:00 Astana via tg_send.sh from Phase 1 | Auto | P2 boil-lake | DX F1 (the 2-4 week silent window) + CEO F2 | wait-for-Phase-2 |
| 13 | Phase 3.5 | `/grade <msg_id>` Telegram command (Phase 1 acceptance metric M1.4) | Auto | P5 explicit | DX F2 + composability theme | jq-only-from-shell |
| 14 | Phase 3.5 | Extend `command_center.py` so `/trace` surfaces `Verdict:` line | Auto | P3 pragmatic + composability theme | DX F3 — parallel-universe risk | two-separate-observability-surfaces |
| 15 | Phase 3.5 | `pages/skills/grader-rubric/SKILL.md` v1 owns `quality` + `issues` enums; cron imports | Auto | P5 explicit + RULE ZERO | DX F6 + Eng F5 + cross-phase enum theme | inline-enum-as-set-literal |
| 16 | Phase 3.5 | Per-record `schema: "grader.v1"`; minor=additive, major=breaking; cluster aggregator declares versions | Auto | P1 completeness | DX F14 | one-schema-forever |
| 17 | Phase 3.5 | Sentinel record on every failure (`type: "judge_failure"`, `reason`, `next_step_for_operator`); save raw response to `~/nous-agaas/logs/grader-debug/` | Auto | P5 explicit | DX F5 + Eng F14 | silent-stderr-launchd-log |
| 18 | Phase 3.5 | Cluster-page template enforced via `tools/lint_cluster_page.py` pre-commit; mandatory frontmatter (severity 5-axis numeric, tags), TL;DR H1, "Recommended action" line | Auto | P1 completeness | DX F8 + AP-2 hygiene-vs-value | freeform-prose |
| 19 | Phase 3.5 | Filename `grader-cluster-YYYY-MM-DD-<category>-<primary_issue>.md` (deterministic, grep-able) | Auto | P5 explicit | DX F10 | random-hash-short-id |
| 20 | Phase 3.5 | `~/nous-agaas/grader.policy.json` kill-switch + `/grader pause N {category}` Telegram command | Auto | P1 completeness | DX F7 | edit-cron-source-to-pause |
| 21 | Phase 3.5 | Tg-send hard cap 1 alert/week from grader | Auto | P5 explicit | CEO F10 | unbounded-alert-frequency |
| 22 | Phase 3.5 | Self-exclude grader-emitted turns (`correlation_id` prefix `grader_*`) | Auto | P5 explicit | Eng F15 mirror-judging | accidental-feedback-loop |
| 23 | Phase 3 | Phase 3 (Mercury retrieval grader) explicitly gated on gbrain v0.11 milestone with separate spec | Auto | P3 pragmatic | CEO F5 + Eng F10 + cross-phase theme | march-toward-blocked-phase |
| 24 | Phase 3 | Phase 4 (AI-gated rollout) remains deferred; needs separate `Skill(autoplan)` | Mechanical | P5 explicit | unchanged from v1 | implement-now |

### Surfaced taste decisions (for Madi — not auto-decided)

These are the calls reasonable people could disagree on. Decide before any implementation lane opens.

- **T1 — RETHINK or TIGHTEN-FIRST?**
  CEO says rethink: replace the 4-phase plan with a 30-day single-cron probe (alt (c) DONE-protocol detector OR alt (d) Mercury A/B head-to-head). Eng + DX say tighten the spec and ship Phase 1 with the 24 auto-decided fixes above. **Default recommendation: TIGHTEN-FIRST**, because the auto-decided fixes already address most of the CEO's regret scenarios (heartbeat + digest + kill-switch + drift detection + cost cap), AND alternatives (a)/(c)/(d) can run IN PARALLEL with Phase 1 as separate 30-day probes — they are not mutually exclusive. The CEO's correct reframing ("doctrine drift detector") is itself a candidate for a separate spec; raise it as a sibling artifact, not a replacement.

- **T2 — Cron host: Mac/Air vs VPS.**
  Mac sleep risk + co-located with logs vs VPS uptime + needs log-pull. Eng F8/F13 demand a definite answer. **Default recommendation: VPS** (pull via `ssh air "tail -F …"` or hourly rsync), because Air is the M2 and Madi travels with the Mac per CLAUDE.md; "always-on" beats "co-located."

- **T3 — Single-judge vs 2-judge minimum.**
  DeepSeek V4 Pro alone (cheap, drift risk) vs DeepSeek+Grok (cost ~2×, no drift). CEO F3. **Default recommendation: single-judge for first 30 days + mandatory automatic 5% sample tagged for Madi review every Friday morning brief with one-tap reaction-emoji workflow on Telegram** (i.e., the "5% calibration" stops being optional). Re-evaluate at day 30; promote to 2-judge if calibration agree-rate < 70%.

- **T4 — Naming: `ask-grader.jsonl` vs `ask-verdicts.jsonl`.**
  DX F9 says actor-vs-noun matters. **Default recommendation: rename to `ask-verdicts.jsonl`**, keep `grader.py` as the cron filename and `pages/skills/grader-rubric/SKILL.md` as the rubric. Output→noun, process→verb. /trace says "Verdict: poor" grammatically.

- **T5 — Cluster page severity threshold for tg_send.**
  CEO F10 says 1/week max; spec said "3-day repeat AND severity > X" but X unset. **Default recommendation: 1 alert/week hard cap, picked by max severity 5-axis composite from Eng failure-modes registry.** Below threshold, page exists in vault for searchability but no push.

- **T6 — Reframing as a sibling spec.**
  Per T1's parallelism: should the CEO's "doctrine drift detector" reframe become a separate `pages/specs/2026-04-30-doctrine-drift-detector-spec.md`, also draft-for-bs8-review, also `Skill(autoplan)`-gated? **Default recommendation: yes, but session 102+ deliverable, not this lane.** Out of scope here.

### Recommendation aggregate

- **CEO:** RETHINK
- **Eng:** TIGHTEN-FIRST
- **DX:** TIGHTEN-FIRST
- **Aggregate (gstack 6-principle resolution):** **TIGHTEN-FIRST + sibling-spec for the CEO reframe.** Rationale: 24 of CEO's 10 findings are addressable via auto-decided fixes (signal invisibility → daily digest, drift uncaught → mandatory calibration, attention-tax → heartbeat-only Phase-1 with 60-day kill gate). The remaining CEO finding — "wrong leverage point, build doctrine-drift detector instead" — is a SECOND spec, not a replacement; T6 captures it.

## Timeline

- **2026-04-30** | s100-mac-23069 lane-A drafted v1 from session-99 audit + Pang 2026-04-28 essay + Mercury hybrid-retrieval thesis. No code changes shipped this lane. Awaiting BS8 + `Skill(autoplan)` review before any implementation lane opens. [[HANDOFF-AUTO-2026-04-30-session-99-top-cto-audit-active-s96-yellow]]
- **2026-04-30** | `Skill(autoplan)` ran (subagent-only mode, codex unavailable on Mac). 3 phases executed (CEO + Eng + DX; Design skipped, no UI scope). Aggregate verdict: TIGHTEN-FIRST + sibling-spec for CEO reframe. 24 auto-decided fixes appended to spec; 6 taste decisions surfaced for Madi (T1-T6). Restore point: `~/.gstack/projects/Nous/main-autoplan-restore-20260430-104104.md`. Spec status remains `draft-for-bs8-review`.
- **2026-04-30** | Status flipped to `accepted-with-defaults` after Madi 3× repeated session-100 prompt with "keep going" (= approve all 6 default taste decisions per session-operating-contract Rule 15 — execute pre-approved tactical decisions, no re-asking). T6 sibling spec spawned at [[2026-04-30-doctrine-drift-detector-spec]]. Mac/Air/VPS-bare/VPS-wiki 4-way GOLDEN at HEAD `74862ccb`. Both specs ingested into gbrain (page_id 4079 + 4097, score 1.0 on direct queries). Telegram digest sent (msg_id 1089).
- **2026-04-30** | Independent verification surfaced peer **lane-D**'s [[AUDIT-062-retrieval-quality-synthesis-2026-04-30]]: a meta-synthesis across 4 retrieval-quality artifacts (this spec + [[2026-04-30-llm-query-rewriter-shim-design]] + [[AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30]] + Mercury thesis source page). **Sequencing convergence:** lane-D independently reached `GRADER FIRST → REWRITER → INDEX-LAYER` — identical to this spec's autoplan-aggregate position. **New gap surfaced:** AP-61 supersession metadata at the gbrain index layer — neither this spec nor the rewriter spec covers it; both treat symptoms (output-side scoring; input-side rewriting) of the underlying drift cause (canonical pages outranked by legacy synthesis pages because the index has no supersession contract to demote them). Tracked as a future workstream beyond this lane's scope.
