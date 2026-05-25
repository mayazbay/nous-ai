---
type: spec
id: SPEC-2026-04-30-llm-query-rewriter-shim
title: "Thin LLM-query-rewriter shim above gbrain — design spec"
tags: [spec, retrieval, gbrain, query-rewriting, hybrid-search, karpathy-loop, musk-algorithm, ceo-hierarchy]
date: 2026-04-30
status: hold-per-audit-062-sequencing
last_updated: 2026-04-30
related:
  - "[[gbrain-ops]]"
  - "[[ceo-hierarchy]]"
  - "[[karpathy-loop]]"
  - "[[musk-algorithm]]"
  - "[[karpathy-coding-principles]]"
  - "[[session-coordination]]"
  - "[[mercury/PHASE-3-LIVE]]"
session: s100-mac-23069-20260430T1016
---

# Thin LLM-query-rewriter shim above gbrain — design spec

## TL;DR

Add a single thin Python module that calls DeepSeek V4 Flash (via existing Air LiteLLM proxy) to rewrite every gbrain query into a fan-out of `(lex, vec, hyde, graph_seed)` sub-queries before dispatch. **Compounding leverage:** every future agent retrieval — across 1524 wiki pages today, scaling to GBrain-author-class 75k territory — gets stronger recall on ambiguous natural-language queries at ~$0.001 cost per call. **Does not fork upstream gbrain.** Does not require v0.11+ schema upgrade (currently blocked at AP-46/47/56/47). Does not collide with active peer lanes `s100-mac-39119` (autopilot link-builder), `s100-mac-42043` (sync audit), or `s100-mac-51815` (library audit).

## Problem statement

The X/Twitter discourse around Mercury Agent (50-item cap) vs the GBrain author's claim ("75k markdown files, hybrid retrieval handles it: vector + keyword + graph + LLM rewriting") names the four pillars of agent-class retrieval. Empirical audit of our gbrain v0.10.1 MCP surface this session shows we already ship 3 of 4:

| Pillar | Status in our v0.10.1 | Evidence |
|---|---|---|
| Vector search | ✅ live | `mcp__gbrain__query` description: "Hybrid search with vector + keyword + multi-query expansion" |
| BM25 / keyword | ✅ live | `mcp__gbrain__search` (FTS), also folded into `query` |
| Graph traversal | ✅ live | `mcp__gbrain__traverse_graph`, `get_backlinks`, `get_links` |
| **LLM query rewriting** | ⚠️ ambiguous | `expand: bool default true` exists, but `expand=true` and `expand=false` returned **identical top-5** for the probe `"auth bug last quarter"` |

The v0.10.1 `expand` flag is wired but its behavior is opaque. Two possibilities:
- **Hypothesis A:** upstream `expand` is synonym/lex-class only; LLM rewriting is missing.
- **Hypothesis B:** upstream `expand` does call an LLM, but our query was already discriminating enough that top-5 didn't shift; or the LLM tuning is weak; or the prompt is generic.

Either way, the **rewriter behavior is not under our control**. Our retrieval fidelity is hostage to whatever upstream did.

## Why now (Musk step-2 / Karpathy compounding lens)

**Musk step-2 ("delete the requirement"):** the bigger lanes I considered are all worse trades:
- Forking upstream gbrain: permanent maintenance debt, blocked by AP-46/47/56 schema wedge.
- Mass prose→wikilink conversion: closed via doctrine amendment AP-52, hygiene churn.
- Installing kepano's obsidian-skills today: orthogonal, schedule as follow-up.
- Installing LLM Council: duplicates `karpathy-loop` AP-5's tool-invoked multi-reviewer.

**Karpathy/Tan compounding ("skills compound, lessons rot"):** the rewriter is a single ~80-LOC module + one new AP in `gbrain-ops`. Every future agent — factory worker, `/code` Telegram session, Codex CEO — gets stronger retrieval automatically. Skills compound through this, not through forks.

**Billion-dollar-solopreneur framing:** one engineer + one shim that improves every agent's recall = exactly the leverage profile cited in your prompt. No new infra, no new platform.

## Phase 0 — Empirical check (must run BEFORE any code)

Before writing the rewriter, prove which hypothesis (A or B) is actually true upstream. **30 minutes work, decides the rest of the spec:**

```bash
ssh root@65.108.215.200 'grep -rn "expand" /opt/nous-agaas/gbrain/src/ | grep -iE "(rewrite|llm|prompt|chat\\.completion)" | head -20'
ssh root@65.108.215.200 'grep -rn "multi-query" /opt/nous-agaas/gbrain/src/ | head -10'
```

**If hypothesis B (upstream expand is already LLM-class):**
→ Don't write a wrapper. Tune the upstream prompt (vault-overlay file at `/opt/nous-agaas/gbrain/skills/query/SKILL.md` style if upstream supports it, else fork-with-overlay). Spec ends. ~$0 cost.

**If hypothesis A (upstream expand is synonym/lex-only):**
→ Proceed to Phase 1+. ~$0.001/query cost, ~80 LOC.

Phase 0 is a hard gate. No code in Phase 1+ until Phase 0 result is logged in this spec's Timeline.

## Approaches (assuming Phase 0 confirms hypothesis A)

### Approach 1: Wrapper script `tools/gbrain_smart_query.py` (RECOMMENDED)

```
caller → gbrain_smart_query.py
            ↓
            rewrite(query, intent) via LiteLLM(DeepSeek V4 Flash)
            ↓
            returns SubQuery list: [
              {type: "lex", query: "auth"},
              {type: "lex", query: "authentication"},
              {type: "vec", query: "session token validation bug"},
              {type: "hyde", query: "<one-paragraph hypothetical answer>"},
              {graph_seed: "auth-system"},
              {graph_seed: "LESSON-074"},
            ]
            ↓
            dispatch each via mcp__gbrain__query / search / traverse_graph
            ↓
            rerank by reciprocal-rank-fusion + dedup by slug
            ↓
            returns ranked top-N to caller
```

- **Pros:** zero upstream coupling; survives any gbrain upgrade; testable in isolation; cacheable per (query, intent) hash.
- **Cons:** adds one network hop (Air LiteLLM); requires LITELLM_MASTER_KEY available wherever called.
- **Cost:** ~$0.0008/call (DeepSeek V4 Flash, ~500 input + 300 output tokens).
- **Latency:** ~1.2s vs ~200ms for raw query. Acceptable for human-driven `/ask` flows; verify for in-loop factory polling.

### Approach 2: MCP-server-shim that intercepts `mcp__gbrain__query`

Expose a new tool name `mcp__gbrain__smart_query` from a custom MCP server that proxies to gbrain after rewriting. Agents could be migrated tool-by-tool.

- **Pros:** invocation site stays clean (just rename the tool).
- **Cons:** new MCP server to operate (process, deps, restart on update). Higher operational debt than Approach 1.

### Approach 3: Fork upstream `expand` implementation, replace with LLM call

- **Pros:** all gbrain consumers benefit transparently (no caller changes).
- **Cons:** **strictly forbidden** by AP-46/47/56 risk profile. v0.11+ upgrade is already blocked on schema; adding a fork point makes the next upgrade harder. Hard NO.

**Recommendation: Approach 1.** Smallest blast radius, zero coupling, adoptable per-skill.

## Detailed design (Approach 1)

### File layout

```
tools/
  gbrain_smart_query.py           # ~80 LOC — public API
  test_gbrain_smart_query.py      # unit tests (rewriter prompt golden + fusion math)
  test_gbrain_smart_query_e2e.sh  # E2E against live gbrain MCP

pages/skills/gbrain-ops/SKILL.md  # NEW AP-57 documenting when to use smart_query
pages/skills/gbrain-ops/SKILL.md  # bump to v1.49.0
```

### Public API

```python
def smart_query(
    query: str,
    intent: str | None = None,
    limit: int = 10,
    cache: bool = True,
) -> list[Result]:
    """Rewrite -> fan-out -> rerank. One-call replacement for raw mcp__gbrain__query."""
```

### Rewriter prompt (golden — must be tested)

System prompt (≤200 tokens):
```
You expand a user query into sub-queries for a hybrid markdown knowledge base.
Output JSON: {"lex": [...3 keyword variants...], "vec": "...one semantic restatement...",
              "hyde": "...one paragraph as if you were the answer document...",
              "graph_seeds": [...up to 3 likely entity/skill/concept slugs...]}
No commentary. JSON only. Fail closed: if input is empty, return {"lex":[],"vec":"","hyde":"","graph_seeds":[]}.
```

User prompt: `query` + (if intent) `\nIntent: {intent}`.

### Fusion (reciprocal rank fusion, RRF)

For each sub-query result list, score `s = 1 / (60 + rank)`. Sum scores per slug across all sub-queries. Sort descending. Dedup by `slug`. Return top `limit`.

### Caching

`functools.lru_cache(maxsize=512)` on `(query, intent)` tuple. TTL not needed — vault content changes invalidate by triggering a different rewrite output rarely; cache is a request-scoped optimization, not a long-lived store.

### Failure modes

- LiteLLM 5xx / network error → fall back to raw `mcp__gbrain__query(query, expand=True)`. Log warning. Never fail-closed on retrieval.
- LLM returns invalid JSON → log + fallback to raw query. Pre-commit test asserts JSON parser handles 5 known-bad outputs.
- Rewriter returns empty sub-queries → fallback to raw query.

## Phases

| Phase | Work | Verification gate | Owner |
|---|---|---|---|
| **0** | Empirical upstream check (grep gbrain src for LLM call in expand path) | Result logged in Timeline | this session |
| 1 | Implement `tools/gbrain_smart_query.py` + unit tests | `python3 -m pytest tools/test_gbrain_smart_query.py -v` all green | next session (post-approval) |
| 2 | Eval harness: 20 hand-curated (query, expected-slug) pairs | `smart_query` MRR@10 ≥ raw query MRR@10 + 20% on the eval set | next session |
| 3 | E2E against live gbrain MCP | `bash tools/test_gbrain_smart_query_e2e.sh` returns 0; latency p95 < 2s | next session |
| 4 | Add AP-57 to `gbrain-ops` SKILL.md, bump v1.48.0 → v1.49.0, gbrain timeline entry | RULE ZERO: no LESSON file; pre-commit hook passes | next session |
| 5 | Migrate one consumer (`tools/run_task.py` or similar) to `smart_query` as canary | 24h soak, no regression in factory metrics | session +1 |
| 6 | Document in [[gbrain-ops]] AP-57 + cross-ref [[ceo-hierarchy]] (DeepSeek as rewriter model) | rsync to Air runtime via `tools/wiki-to-runtime-rsync.sh` | session +1 |

## Success criteria

- **Hard:** Phase 2 eval shows MRR@10 improvement ≥ 20% on the 20-pair eval set. Below threshold → spec is wrong, do NOT ship.
- **Hard:** Phase 4 SKILL.md update committed without creating a `LESSON-NNN-*.md` (pre-commit hook enforces).
- **Soft:** p95 latency of `smart_query` < 2s under DeepSeek Flash via LiteLLM.
- **Soft:** factory cost delta < $5/day even if every worker call is rewritten (1524 pages × 100 queries/day × $0.001 = $0.15/day budget).

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| DeepSeek down → factory blind on retrieval | Fallback to raw `mcp__gbrain__query` (failure mode #1 above) |
| Rewriter prompt drifts vault vocabulary | Pre-commit prompt-golden test must match committed prompt; CI gate |
| Cache poisoning (same query → bad expansion sticks) | LRU per-process; restart clears. No cross-session persistence. |
| Cost runaway if a buggy loop calls `smart_query` 10k times | LiteLLM master key has spending cap per `ceo-hierarchy`; budget alarm fires |
| Collision with upcoming gbrain v0.11+ `expand` upgrade | Wrapper is read-only on gbrain; v0.11+ ships → re-run Phase 0 → may delete this shim |
| Wrong model choice (DeepSeek vs Sonnet) | Make model name a config var; Phase 2 eval can A/B test |

## Cross-references

- `karpathy-loop` AP-5 — multi-virtual-reviewer must run on this spec before approval (`Skill(plan-eng-review)` + `Skill(plan-ceo-review)` minimum).
- `musk-algorithm` step-2 — Phase 0 is the "delete the requirement" gate; if upstream already does LLM rewriting, this spec self-deletes.
- `karpathy-coding-principles` (1) Think Before Coding — Phase 0 is the assumption check; (2) Simplicity First — 80 LOC, no abstractions; (3) Surgical Changes — one file + one AP; (4) Goal-Driven — MRR@10 +20% is the verifiable success criterion.
- `gbrain-ops` AP-46 / AP-47 / AP-56 — explains why Approach 3 (fork upstream) is forbidden.
- `gbrain-ops` AP-50 / AP-52 — graph traversal is doctrine-passed even though prose-form refs exist; rewriter graph_seeds compensate at retrieval time without source edits.
- `ceo-hierarchy` v1.1.0 — DeepSeek V4 Flash is the worker tier; consistent with rewriter model choice.
- `session-coordination` — this session's scope (`pages/specs/2026-04-30-llm-query-rewriter-shim-design.md`) does not overlap with active `s100` peer lanes.
- [[mercury/PHASE-3-LIVE]] — note: external "Mercury Agent" tool is unrelated to our internal Mercury MEMORY-injection system. Naming for this spec deliberately avoids "mercury".

## Anti-patterns this spec must NOT introduce

- ❌ "While we're at it" rewriting unrelated gbrain code (`karpathy-coding-principles` #3 surgical).
- ❌ Adding a `LESSON-NNN-*.md` for the eventual win (RULE ZERO; pre-commit hook rejects).
- ❌ Skipping Phase 0 because "we're pretty sure" upstream is hypothesis A (`karpathy-coding-principles` #1 think before coding).
- ❌ Migrating ALL consumers to `smart_query` in one PR (Phase 5 is canary-only; spread the migration).
- ❌ Hiding the model choice deep in code (config-var per Risks table).

## Multi-virtual-reviewer plan (per `karpathy-loop` v1.9 AP-5)

This spec triggers AP-5 because it introduces new doctrine (gbrain-ops AP-57) and new infra dependency (LiteLLM in retrieval path). Tool-invoked reviewers, NOT mental simulation:

1. `Skill(plan-eng-review)` — architecture, failure modes, eval methodology.
2. `Skill(plan-ceo-review)` — scope expansion: should this also intercept `traverse_graph`? Should this be the moment to also cache graph results? Compounding-leverage check.
3. (Optional) `Skill(plan-devex-review)` — caller ergonomics: is `smart_query` discoverable? Are migration steps obvious?

Reviewer outputs append to this spec's `## Timeline` section before any code is written.

## Open questions for Madi

1. **Phase 5 canary target:** which consumer migrates first? Default: `tools/run_task.py` (factory worker) — biggest leverage but also biggest blast radius. Alternative: a low-traffic CLI tool first.
2. **Eval set:** I'll seed 20 (query, expected-slug) pairs from existing handoffs, but final list should pass your sniff test. Want to provide seed queries, or accept my picks?
3. **LiteLLM auth in calling environments:** Mac sessions need LITELLM_MASTER_KEY too. Add to Mac `.env` or use Air-only execution? (Air-only is cleaner but blocks Mac-CLI smoke tests.)

---

## Reviewer findings (2026-04-30, both Skill-tool-invoked per karpathy-loop AP-5)

### plan-eng-review

- **A1 (P2):** Phase 0 needs a 0.5 termination clause. If hypothesis B (upstream `expand` already LLM-class), spec self-deletes; we do NOT modify upstream. ✅ FOLDED into Phase 0 below.
- **A2 (P2):** Single point of failure on LiteLLM. Add circuit breaker (3 failures → 60s skip). ✅ FOLDED.
- **A3 (P3):** Cache scope — per-process LRU dies with worker. Document this as v1 limitation; flag SQLite cache as v2 follow-up. ✅ FOLDED.
- **A4 (P3):** graph_seeds slug-resolution gap. Use `mcp__gbrain__resolve_slugs` before `traverse_graph`. ✅ FOLDED.
- **Q1 (P3):** Prompt-golden test — golden = exact-string match of system prompt + 3 input/output pairs, hashed. ✅ FOLDED into T2.
- **Q2 (P3):** `intent` injection point — append `\nIntent: {intent}` to user prompt. ✅ FOLDED.
- **Q3 (P4):** ~80 LOC is optimistic; realistic 130-160. ✅ Honesty update.
- **T1-T5:** 14 unit-test gaps + chaos test for LiteLLM-outage. ✅ Added Phase 1 deliverable.
- **T5 CRITICAL:** `test_gbrain_smart_query_litellm_outage.sh` — must prove fallback returns raw gbrain on LiteLLM 5xx. ✅ FOLDED.
- **P1 (P2):** Smart_query MUST be opt-in per call site; factory worker must NOT rewrite every retrieval. ✅ FOLDED into Phase 5.
- **Verdict:** NOT CLEARED until folded. Now folded ✅.

### plan-ceo-review

- **Mode:** SELECTIVE EXPANSION (vs HOLD). Core scope right; cherry-pick observability + model A/B.
- **Bigger framing:** Approach A (current spec) is correct v1, but commit explicitly to Approach B (single retrieval gateway daemon) as v2 trajectory or accept graveyard risk. ✅ FOLDED as Phase 7.
- **CRITICAL GAP — rewriter timeout:** add `LITELLM_TIMEOUT_S = 5`. Spec was unbounded. ✅ FOLDED.
- **CRITICAL GAP — cascading failure:** smart_query falls back to raw query, raw query also fails — return `[]` with `retrieval_unavailable=true` sentinel. ✅ FOLDED.
- **CRITICAL GAP — daily budget kill-switch:** `LITELLM_DAILY_BUDGET_USD` env var; auto-fall-back if exceeded. ✅ FOLDED.
- **E3 ACCEPTED:** Phase 4.5 — Mercury-style status dashboard at `pages/retrieval/STATUS.md` regenerated by launchd every 30 min (fallback rate, p50/p95, top-5 rewritten queries). ✅ ADDED.
- **E4 ACCEPTED:** Phase 2 eval runs DeepSeek vs Sonnet A/B (~$0.04 incremental cost on 20 queries). Empirical model choice. ✅ ADDED.
- **E1, E2 DEFERRED:** kepano obsidian-skills + LLM Council — separate specs, schedule via `/schedule`.
- **D1-D4 implementation decisions:** intent=instructor-style; PROMPT_VERSION="v1" in cache key; factory canary = context-load call only; Codex `/codex` migration is Phase 6. ✅ FOLDED.
- **Kill-switch env var:** `SMART_QUERY_DISABLED=1` skips entire shim. ✅ FOLDED.
- **Verdict:** NOT CLEARED until folded. Now folded ✅.

## Folded changes (post-review)

The above reviewer items are now part of the spec body:

- Phase 0 gains a Phase 0.5 termination clause: "if hypothesis B, spec ends — no upstream modification."
- Phase 1 work items: circuit breaker (3-fail/60s), `LITELLM_TIMEOUT_S=5`, `LITELLM_DAILY_BUDGET_USD` kill-switch, `SMART_QUERY_DISABLED=1` env var, `mcp__gbrain__resolve_slugs` for graph_seeds, `PROMPT_VERSION="v1"` in cache key, retrieval_unavailable sentinel, per-subquery cap=50 before RRF.
- Phase 2 eval: A/B test DeepSeek V4 Flash vs Sonnet 4.6 alongside MRR@10 baseline.
- Phase 4.5 (NEW): launchd-driven `pages/retrieval/STATUS.md` regen every 30 min.
- Phase 5: opt-in flag per caller; factory canary = context-load call only.
- Phase 7 (NEW): "Within 30 days post-canary, ≥3 of {Mercury, factory worker, Codex CEO, Telegram /ask} consumers route via smart_query OR write honest pause-update. If A's adoption stalls, promote logic into single retrieval-gateway daemon (Approach B)."
- Test file additions: T6 (timeout), T7 (daily budget), T8 (chaos: LiteLLM 5xx + gbrain 5xx + malformed JSON).
- Realistic LOC: 130-160 (not 80).

## Timeline

- **2026-04-30** | Spec draft v1 written by session `s100-mac-23069-20260430T1016`. Empirical evidence: `expand=true` and `expand=false` returned identical top-5 for `"auth bug last quarter"` (probe in this session). brain_score 80, embed_coverage 99.97% (1 missing), 653 orphan pages — flagged for lane `s100-mac-51815`. `[Source: this spec audit]`
- **2026-04-30** | plan-eng-review run via `Skill(plan-eng-review)`: 4 architecture issues + 3 code-quality + 14 test gaps + 2 perf — all folded. ✅
- **2026-04-30** | plan-ceo-review run via `Skill(plan-ceo-review)`: SELECTIVE EXPANSION, 3 critical gaps (timeout/cascade/budget) + 2 cherry-picks accepted (E3 status dashboard, E4 DeepSeek-vs-Sonnet A/B) + Phase 7 v2 trajectory commitment — all folded. ✅
- **2026-04-30** | **Phase 0 EMPIRICAL RESULT — REDESIGN.** SSH probe of `/opt/nous-agaas/gbrain/src/core/search/expansion.ts` (87 LOC) reveals:
  - Multi-query expansion **ALREADY uses Claude Haiku 4.5 via `@anthropic-ai/sdk` tool-use** to generate 2 alternative phrasings + 1 original = 3 sub-queries. Capability is built.
  - **Silent fallback on any error:** line 41 `catch { return [query]; }`. No telemetry on expansion fire-rate.
  - **Root cause of identical `expand=true`/`expand=false` probe results:** `ANTHROPIC_API_KEY` is NOT in the gbrain runtime environment. Verified via `tr "\0" "\n" < /proc/<pid>/environ` on all 3 live `gbrain serve` PIDs — empty. No `/opt/nous-agaas/gbrain/.env` file exists. So `new Anthropic()` instantiates, API call fails, expansion silently returns `[query]`. The whole feature has been dead since deployment.
  - **Side-flag:** 3 concurrent `gbrain serve` PIDs on VPS — AP-22 territory (orphan stdio MCP spawns); flag to s100-mac-51815, not this spec's scope.
  - **Side-flag:** secrets-management AP-5 / AP-9 / AP-10 are all good practices for SERVICES that load env, but no service unit appears to be loading anything for gbrain — root cause is missing loader, not missing key (key may exist elsewhere on VPS for other services).
- **2026-04-30** | Spec status: **REDESIGN REQUIRED.** Hypothesis A (no LLM at all) and hypothesis B (LLM-class, just weak) were both wrong. Reality: hypothesis C — LLM-class implementation exists upstream, dead at runtime due to missing env var.

## Redesign — three options now (Madi to choose)

### α (Musk step-2 winner — STRONGLY RECOMMENDED): Turn on what's there. Don't write code.

1. Add `ANTHROPIC_API_KEY` to gbrain runtime (via the same loader pattern factory + LiteLLM use).
2. Restart `gbrain serve` on VPS.
3. Re-run probe — same query, observe whether `expand=true`/`expand=false` now diverge.
4. If divergence + recall-improvement empirically present → **ship a 1-line documentation update to gbrain-ops AP-57 saying "expansion is live, requires ANTHROPIC_API_KEY in env" and close this spec.** Total work: ~10 minutes including verification.
5. If still no divergence (key set but expansion still no-ops for other reasons) → escalate to upstream issue.

**This is the literal Musk 5-step. Step 1: question the requirement (was it real? — yes, but partially solved). Step 2: delete unnecessary parts (the entire 150-LOC wrapper). Step 3: simplify (just supply the env var). Step 4: speed up (10 min vs days). Step 5: automate (loader pattern already exists for LiteLLM).**

### β: Wrapper anyway, on top of α.

After α is verified working, add the wrapper for capabilities upstream lacks: graph_seed extraction (no graph traversal in `expansion.ts`), HyDE generation, RRF fusion, fallback chain, telemetry on expansion fire-rate. Justified ONLY if α verifies live and we measure remaining gap. Original ~150-LOC spec body still applies, scoped to the delta.

### γ: α now, β later (RECOMMENDED ordering).

Ship α today (10 min). Measure for 1 week. Decide β based on data, not assumption.

**My recommendation: γ. You decide. The 150-LOC wrapper proposal is dead in its original form — supplying an env var supersedes it.**

## Phase 0.5 — production-touch confirmation needed

Adding `ANTHROPIC_API_KEY` to gbrain runtime is a **shared/production-system mutation** per the auto-mode rules. I will not do it without explicit "yes, do α" from you. The mutation is:

1. Read existing key from a known location (likely `~/.anthropic/api_key` per `secrets-management` skill, or factory env, or LiteLLM master config — to be confirmed without exposing the value).
2. Write it to `/opt/nous-agaas/gbrain/.env` with `0600` perms (per `secrets-management` AP-6).
3. Configure gbrain runtime to load `.env` (need to check which mechanism — systemd `EnvironmentFile=`? launchd? manual export-then-restart?).
4. Restart `gbrain serve` (which is currently 3 PIDs — also needs lane `s100-mac-51815` heads-up about AP-22).
5. Verify via fresh `mcp__gbrain__query` probe.

**If you say "go α," I'll first do a read-only check of where the key already lives on VPS, write a 5-step plan, and ASK before each mutation step.**
