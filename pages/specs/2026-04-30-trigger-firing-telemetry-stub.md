---
type: spec
id: SPEC-TRIGGER-FIRING-TELEMETRY-V0-2026-04-30
title: "Trigger-firing telemetry — invocation-time silent-skip detector (4th sibling stub)"
tags: [spec, trigger-firing, silent-skip, invocation-time, telemetry, fourth-spec, lane-A, session-100]
date: 2026-04-30
status: rethink-accepted-defaults-applied
last_updated: 2026-04-30
related: [2026-04-30-mercury-hybrid-retrieval-gap-analysis, 2026-04-30-doctrine-drift-detector-spec, 2026-04-30-llm-query-rewriter-shim-design, 2026-04-30-ap61-supersession-metadata-stub, gbrain-ops, session-operating-contract, karpathy-loop, ceo-hierarchy]
source_count: 1
sources:
  - "Skill(autoplan) Phase-1 CEO subagent review of doctrine-drift-detector-spec, 2026-04-30 — surfaced as 10x reframe of the doctrine-drift detection problem"
---

# SPEC — Trigger-firing telemetry (stub)

> **This is a STUB.** Full spec needs `Skill(superpowers:brainstorming)` → `Skill(autoplan)` → implementation lane in a future session. This file exists so the autoplan-2 CEO subagent's 10x reframe does NOT decay between sessions. Per RULE ZERO, decay is the failure mode.

## Provenance

The Phase-1 CEO subagent review of [[2026-04-30-doctrine-drift-detector-spec]] (autoplan v2, 2026-04-30) flagged this finding as the strongest reframe argument:

> **Wrong leverage point.** The bottleneck is NOT "skill not followed." It's "skill never read because session didn't trigger it." Detection should live at *invocation time* (the trigger fired but the skill wasn't loaded → log it), not at audit time (a week later, an LLM re-reads the handoff and guesses).
>
> **10x reframe:** Build a *trigger-firing telemetry layer*. Every time a regex in any skill's `triggers:` matches the live session input, log `(session_id, skill, triggered_at, was_loaded)`. Now you have a deterministic, $0/wk, real-time signal: "skill X had triggers fire 47 times this week, was loaded 3 times — silent-skip rate 94%." THAT is the failure mode. No LLM judge, no rubric calibration, no quarterly sweep.
>
> The current spec is essentially: *let's pay an LLM weekly to re-read what already happened and guess*. The cheaper, more accurate move is *instrument the moment of decision*.

The sibling doctrine-drift spec (audit-time, output-side) was accepted-with-defaults including T6 = "capture this reframe as 4th sibling stub, out-of-scope for THIS spec; don't conflate audit-time with invocation-time observability — different mechanism, different data path, different question."

## What this proposes (sketch only — not designed yet)

A telemetry layer instrumented at the moment an agent decides whether to invoke a skill.

**Mechanism (rough):**
- Each skill's `triggers:` frontmatter gets parsed into a regex set (or, more robustly, embedded into an invocation-time matcher).
- Every inbound message to OpenClaw factory / Claude Code / Codex / Telegram poller passes through a matcher that emits one row per trigger that fires:

  ```jsonl
  {"ts": "2026-05-04T09:23:14Z", "session_id": "s103-mac-77714-...", "skill": "session-operating-contract", "trigger_pattern": "every new session", "matched_text_excerpt": "starting session", "was_loaded": true, "loaded_via": "auto-CLAUDE.md"}
  {"ts": "2026-05-04T09:24:01Z", "session_id": "s103-mac-77714-...", "skill": "audit", "trigger_pattern": "audit substrate", "matched_text_excerpt": "audit the wiki", "was_loaded": false, "loaded_via": null}
  ```

- A weekly aggregator computes per-skill silent-skip rate = `count(was_loaded=false) / count(*)`.
- Any skill with silent-skip > 30% over 7 days surfaces in a `pages/audits/INDEX.md` row + tg_send digest line.

**Why this is different from doctrine-drift (audit-time):**
- Doctrine-drift asks "did the agent follow the rules in the skills it loaded?"
- Trigger-firing asks "did the agent load the right skills in the first place?"
- These are orthogonal failure modes. An agent can load the right skill and still violate it (caught by doctrine-drift). An agent can also fail to load a skill that should have triggered, then "act fine" because no rule applied (caught by trigger-firing).

**Why this is different from Mercury Phase 1 (output-side):**
- Mercury asks "is the agent's reply good?"
- Trigger-firing asks "did the right skills inform the reply?"
- Mercury catches semantic failures in the response; trigger-firing catches structural failures in the routing.

**Why this is different from the query rewriter (input-side):**
- Query rewriter asks "is the user's query well-formed for retrieval?"
- Trigger-firing asks "did the right skill rules fire on the user's query?"
- Different layers of the same input pipeline.

## Brainstorm-resolved decisions (s100-mac-23069 lane-A, 2026-04-30, "do 1 by 1" delegation)

### D1 — Matcher location: Claude Code session-start hook + OpenClaw factory pre-processor (2 sites, defer Codex+Telegram)
**Sites in v1:**
- **Claude Code session-start hook** (`~/.claude/hooks/session-start-soao.sh` already exists; extend it). Fires on EVERY session start; sees the user's first message + the auto-loaded CLAUDE.md context. Cheapest instrumentation.
- **OpenClaw factory pre-processor** (in `command_center.py` before `_run_openclaw`). Sees every Telegram-routed `/ask` turn. Adds `trigger_fired:[skill_slug,...]` field to existing `ask-hierarchy.jsonl` row.

**Defer to v2:**
- Codex CLI wrapper (`tools/codex-nous.sh` could log; defer until Codex paths stabilize)
- Telegram poller (already routes via OpenClaw; double-instrumentation = double-counting)

**Why 2 sites not 4:** Claude Code + OpenClaw cover ~95% of agent invocations. Codex usage is sparse; Telegram poller already feeds OpenClaw. Two instrumentation points = simpler debugging, less PII surface.

### D2 — `triggers:` regex contract: backfill audit FIRST, then v1 schema lands
**Pre-requisite (Phase 0):** audit existing `triggers:` field coverage across all 56 skills. Per doctrine-drift Eng F11, current coverage is ~30/56. Output: `pages/audits/triggers-coverage-2026-04-30.md`. Skills missing the field get a backfill PR (NEW lane, not this one).

**v1 schema for `triggers:`:**
```yaml
triggers:
  - pattern: "every new session"          # Plain phrase (lowercase, regex-escaped)
    case: insensitive                     # case-sensitive | insensitive (default)
    scope: user_message                   # user_message | system_prompt | both (default user_message)
  - pattern: "(?:start|kick off).+session"  # Explicit regex (must escape special chars)
    regex: true                           # marks this as raw regex
```

**Backwards compat:** existing skills with `triggers: [- "phrase"]` (string-only) treated as `pattern: phrase, case: insensitive, scope: user_message, regex: false`.

### D3 — "Loaded" definition: skills-resolver output post-invocation (cheaper)
**v1 mechanism:** instrument the resolver step. After CLAUDE.md is processed and skills are matched, log which `[[skill-name]]` references appeared. A skill is "loaded" if its slug appears in the resolver's resolved-set OR appears in the active conversation context (regex on session log).

**Why not LLM-call-site instrumentation:** that requires modifying every LLM client (Claude Code, OpenClaw, Codex CLI). Resolver-side is one site, one log.

**False-negative:** if a skill is loaded but never invoked semantically (the agent saw the rules but didn't follow them), trigger-firing won't catch it — that's doctrine-drift's job. Different layers. (Ref: D-table in this spec, "Why this is different from doctrine-drift").

### D4 — Privacy: hard field-allowlist, NEVER log raw user text
**v1 fields in trigger-firing JSONL (allowlist; everything else REJECTED at log site):**
```json
{
  "ts": "ISO8601",
  "session_id": "s103-mac-...",
  "skill": "session-operating-contract",
  "trigger_pattern_idx": 0,                  // index into skill's triggers: array, NOT the matched text
  "trigger_match_hash": "sha256-hex-12char", // hash of normalized matched substring; deduplication only
  "was_loaded": true,
  "loaded_via": "auto-CLAUDE.md|wikilink|skill-resolver|null"
}
```

**NEVER logged:**
- Matched text excerpt (PII risk — license plate, ИИН, phone, email, name)
- Full user message
- System prompt content
- Any free-form string from session

Same regex-redaction allowlist as doctrine-drift Eng F7. `tools/test_trigger_firing_pii.py` regression test required pre-Phase-1.

### D5 — Composability with shared INDEX: append to `pages/audits/INDEX.md`
Per doctrine-drift Decision #21 (already shipped/auto-generated). Trigger-firing weekly silent-skip-rate report is the 3rd writer. INDEX schema (TBD, peer-lane-owned currently): `| date | system | skill_or_topic | severity | link |`. Trigger-firing rows look like `| 2026-W18 | trigger-firing | session-operating-contract | medium-silent-skip-32% | [link] |`.

### D6 — Cost: in-memory regex eval, JSONL append, daily archive
**Per-message overhead:**
- 56 skills × ~3 patterns each = ~170 regex evals per agent message
- Python `re.compile`-cached, ~10μs each = ~1.7ms/message total
- JSONL append: 1-3 rows/message, ~200 bytes each, batch-flushed every 5s
- Daily volume: ~50 messages/day × 2 rows = ~100 rows/day, ~20KB/day

**Storage rotation:** hot tail at `~/nous-agaas/logs/trigger-firing/YYYY-WW.jsonl`. Weekly rollover; older weeks compress to `.jsonl.gz` (90% reduction). After 12 weeks, archive to gbrain timeline + delete jsonl. Same pattern as doctrine-drift Decision #25.

**Cost ceiling:** $0/wk (no LLM calls in v1). I/O budget: ≤$0.05/month disk + transfer (negligible).

### D7 — False-positive control: relevance threshold + skill-author opt-in strict mode
**v1 mitigation:** `triggers:` v1 schema (D2) supports `match_min_word_count: 3` (default) — patterns shorter than 3 words are advisory, not hard-counted in silent-skip rate. Patterns ≥3 words count fully.

**Skill-author opt-in:** `triggers_strict: true` in skill frontmatter forces all patterns to count fully. Use for skills with high-precision triggers (e.g., session-operating-contract Rule 1's "before touching anything in a new session" is a literal phrase, not a generic word).

**Defer LLM-residual semantic check** to Phase 1.5 — only ship if Phase 1 silent-skip rate is too noisy to act on (>50% noise rate by week 4).

## Phases (Musk-ordered)

### Phase 0 — `triggers:` coverage audit + v1 schema
**Acceptance:** `pages/audits/triggers-coverage-2026-04-30.md` reports % coverage; v1 schema documented in this spec; backfill lane scoped (NOT shipped from this lane).

**Falsifiable:** `python3 tools/triggers_audit.py` returns `{coverage: ≥80%, schema_v1_compliant: true}`.

### Phase 1 — Claude Code session-start hook instrumentation
**Acceptance:** `~/.claude/hooks/session-start-soao.sh` emits trigger-firing JSONL per D4 schema. Tested via 1 week of Madi's actual sessions. Silent-skip rate computed weekly via `tools/trigger_firing_weekly.py`.

**Falsifiable:** `jq '.skill | unique' ~/nous-agaas/logs/trigger-firing/$(date +%Y-W%V).jsonl | wc -l` ≥ 10 (10+ distinct skills triggering per week).

### Phase 2 — OpenClaw factory pre-processor instrumentation
**Acceptance:** `command_center.py` adds `trigger_fired:` field to ask-hierarchy.jsonl per turn. Composes with Mercury Phase 1's grader (which reads same file).

**Falsifiable:** `jq '.trigger_fired' ~/nous-agaas/logs/ask-hierarchy.jsonl | tail -50` shows non-empty arrays for ≥80% of turns.

### Phase 3 — Weekly silent-skip-rate digest + INDEX integration
**Acceptance:** Saturday 09:35 cron emits `pages/audits/trigger-firing-YYYY-WW.md` + appends to INDEX.md + tg_send 1-line digest.

**Falsifiable:** 4 consecutive weekly reports landed; tg_send msg_id confirmed weekly.

### Phase 4 — LLM-residual semantic check (deferred until Phase 1 noise > 50%)
**Out of scope until measured Phase 1 noise rate justifies the cost.**

## Rejection criteria for the whole spec

1. **Phase 0 `triggers:` coverage audit < 30%:** schema is too premature; the field doesn't exist in enough skills to bootstrap. Kill spec; backfill skills first.
2. **Phase 1 silent-skip rate > 80% across all skills:** the regex-trigger model is too noisy to be useful; the matcher is over-firing. Rethink mechanism (maybe semantic embedding similarity instead of regex).
3. **PII leak detected** in trigger-firing JSONL within 30 days of Phase 1 ship: D4 allowlist failed; structural privacy violation. Halt + remediate before any further work.
4. **60 days of operation, zero SKILL.md updates** authored by Madi from trigger-firing findings: signal is uncorrelated with action. Kill spec.

## Stays out-of-scope (this spec)

- Implementation: no `tools/trigger_firing.py` written from this lane. Implementation lane opens after `Skill(autoplan)` runs on this draft.
- `triggers:` field backfill on 26 skills missing it: separate lane.
- Mercury composability beyond the JSONL field-add: covered by Mercury sibling spec.
- Codex CLI + Telegram poller instrumentation: deferred to v2.
- LLM-residual semantic check: Phase 4 only, gated on Phase 1 noise measurement.

## Composition with the 4-spec retrieval-quality program

| Spec | Layer | Question | Mechanism | Cost |
|---|---|---|---|---|
| [[2026-04-30-mercury-hybrid-retrieval-gap-analysis]] | Output | Is the agent's reply good? | Pang's tri-judge / 6-job pipeline / AI-gated rollout, on `/ask` JSONL | $1.50/day |
| [[2026-04-30-doctrine-drift-detector-spec]] | Doctrine | Are skill rules being followed once loaded? | Weekly cron, mechanical regex pass + LLM judge on residual (deferred per T1) | $0.30/wk (deferred) |
| [[2026-04-30-llm-query-rewriter-shim-design]] | Input | Is the query well-formed for retrieval? | LLM-rewrite into lex+vec+hyde+graph_seed fan-out + RRF merge | ~$0.001/call |
| [[2026-04-30-ap61-supersession-metadata-stub]] | Index | Does the ranker demote superseded pages? | Frontmatter contract (`status: superseded`) the ranker parses | $0 (structural) |
| **This spec** | **Routing** | **Did the right skills load when triggers fired?** | **Invocation-time matcher, per-message JSONL, weekly silent-skip rate** | **~$0 (regex-only) + I/O** |

5 specs now in the retrieval-quality program. None block each other. None are mutually exclusive. Each is independently shippable. Together they bracket the full pipeline: input → routing → retrieval (index) → reasoning (doctrine adherence) → output.

## Why this is a candidate for FIRST-shipped (potentially)

Per CEO's argument: trigger-firing telemetry is the *cheapest, most falsifiable, most real-time* observability primitive of the 5. It does NOT need an LLM judge, calibration set, or schema-versioned consumer. It produces deterministic data the moment a decision is made. Phase 0 acceptance is a 1-week trace of trigger fires + silent-skip rates on existing 56 skills.

If this ships first, it potentially obsoletes doctrine-drift's LLM-judge pass entirely — because silent-skip rate IS the headline doctrine-drift signal. That's why the autoplan T1 default chose Pass-A-only-first for doctrine-drift: don't pay for an LLM judge that this cheaper layer might catch deterministically.

**Possibility:** the right sequencing for the retrieval-quality program is:
1. Mercury Phase 1 (already in flight, peer lane s103-77714)
2. Trigger-firing telemetry (this stub, full-spec'd next session)
3. Doctrine-drift Pass-A-only (after trigger-firing proves out, IF gaps remain)
4. Query rewriter Phase 0 (after Mercury Phase 1 has 50+ graded turns)
5. AP-61 supersession metadata (after structural drift confirmed by Mercury or trigger-firing)
6. Doctrine-drift Pass-B LLM judge (deferred indefinitely; gated on T2 calibration set + insufficient signal from trigger-firing)

This is a possible re-sequencing, not a decision. Future autoplan on this stub will resolve.

## Falsifiability of this stub itself

```bash
# Acceptance to move stub → draft:
# Run Skill(superpowers:brainstorming) on this stub. Resolve ≥6 open questions above.
# Output: status: stub-pending-brainstorm → draft-pending-autoplan.

# Acceptance to remain stub indefinitely (kill criterion):
# If Mercury Phase 1 + doctrine-drift Pass-A together catch ≥90% of doctrine
# violations Madi flags as "should have caught," trigger-firing is redundant.
# Kill spec.
```

## See also

- [[2026-04-30-mercury-hybrid-retrieval-gap-analysis]] — sibling output-side spec
- [[2026-04-30-doctrine-drift-detector-spec]] — sibling doctrine-side spec; this stub is the autoplan-2-T6 sibling that captures the CEO reframe
- [[2026-04-30-llm-query-rewriter-shim-design]] — sibling input-side spec (lane-D)
- [[2026-04-30-ap61-supersession-metadata-stub]] — sibling index-layer spec
- [[AUDIT-062-retrieval-quality-synthesis-2026-04-30]] — peer lane-D's cross-spec synthesis
- [[ceo-hierarchy]] — Tier-1/2/3 routing telemetry (`~/nous-agaas/logs/ask-hierarchy.jsonl`); this stub adds a trigger-firing JSONL alongside it
- [[gbrain-ops]] — operating procedures the implementation must compose with
- [[karpathy-loop]] — multi-virtual-reviewer (AP-5); the eventual autoplan on this stub must run dual-voice (Codex + Claude × 3 phases)
- [[session-operating-contract]] — Rule 1 session-start ritual (one of the things triggers should fire on)

## /autoplan review report v1 (full 6-voice, 2026-04-30)

> **6/6 voices verdict: RETHINK** (strongest autoplan consensus to date). All four phases CEO + Eng + DX × {Claude, Codex} converged on rewrite-not-tighten. Codex grounded findings with concrete file:line citations against actual source — including `tools/ask_grader.py:75` showing Mercury's `missed_context|wrong_routing` enum already covers ~70% of this spec's intent.

### The headline finding

**This spec measures the wrong layer. The right move is to extend `tools/context_injector_v2.py` (already exists, ~145 LOC of live matcher) + add a `UserPromptSubmit` hook (NOT SessionStart, which fires before the user types) + extend Mercury's existing `issues:` enum with a `silent_skip` value — instead of building a ~400 LOC parallel matcher.**

### Cross-phase consensus (caught by 5+ of 6 voices)

| Finding | Severity | Voices |
|---|---|---|
| **D1 cites the WRONG Claude hook** — `session-start-soao.sh` (line 43) runs SOAO + session registration, doesn't read prompt stdin. The right hook is `UserPromptSubmit`. Spec is half-broken on land. | **CRITICAL** | 5/6 |
| **Phase-0 schema-on-disk gap** — `pages/schemas/trigger_firing.v1.json` doesn't exist. Self-similar bug to AP-61 autoplan v1's BLOCKER. Pattern repeating across the 5-spec program. | **CRITICAL** | 5/6 |
| **No baseline measurement** — autoplan reframe was REASONING, not data. At 5-15 turns/day with 56 skills, per-skill weekly N=1-6, statistical power null. | **CRITICAL** | 4/6 |
| **Mercury redundancy** — `tools/ask_grader.py:75, :334` already implements `missed_context|wrong_routing` issue enum. Trigger-firing is the third bite at the same apple. | **CRITICAL** | 5/6 |
| **Coverage cherry-picked** — D1 covers Claude+OpenClaw, defers Codex CLI + Telegram poller. `tools/telegram_poll.py:223` + `command_center.py:959, :1003` show `/code` and `/codex` BYPASS OpenClaw. v1 stats won't represent CEO path. | **HIGH** | 6/6 |
| **PII hash rainbow-table-able for IIN** — 12-char SHA-256 prefix has 2^48 collision space; 12-digit Kazakh IIN namespace is 10^12 ≈ 2^40 < 2^48 → IIN HASHES ARE REVERSIBLE. | **HIGH** | 5/6 |
| **No regex-safety contract** — D2 allows raw `regex: true` patterns; backfilling 26 hand-extracted regexes will introduce ≥1 ReDoS pattern (e.g., `(a+)+b`). One bad pattern stalls every agent message. | **HIGH** | 5/6 |
| **No kill-switch / Telegram operator UX** — AP-61 ships `grader.policy.json`; this spec ignores that pattern. Madi can't disable from his phone. | **HIGH** | 5/6 |
| **Existing `context_injector_v2.py` already does live matching** — spec proposes ~400 LOC parallel matcher when ~60 LOC extension would do. | **HIGH** | 4/6 |
| **JSONL host-relative path divergence** — `~/nous-agaas/logs/...` resolves differently on Mac vs Air vs OpenClaw container. Spec implicitly assumes shared file. | **HIGH** | 4/6 |
| **Hash-only field destroys debuggability** — when skill author asks "why didn't skill X fire?" they need MORE than a hash. Need opt-in redacted debug mode. | **MEDIUM** | 3/6 |
| **`triggers_strict` naming bifurcates schema** — D7 introduces sibling field; spec convention is nested or list-of-objects. | **MEDIUM** | 3/6 |
| **INDEX.md auto-generator conflict** — D5 says "append a row" but `tools/audits_index_generate.py:3` regenerates the file. Manual append disappears on next regen. | **MEDIUM** | 2/6 |

### Phase 1 — CEO dual-voice (RETHINK consensus)

- **CEO Claude:** RETHINK; "speculative observability layer dressed as a measurement layer." Strongest dismissed alternative: **(a) extend Mercury Phase-1 enum with `silent_skip`** — single pipeline, downstream-grounded.
- **CEO Codex:** RETHINK; grounded in `tools/ask_grader.py:75` showing Mercury enum already covers `missed_context|wrong_routing`. Reframe: "trigger telemetry as diagnostic drill-down behind real failures, not headline metric." First establish baseline from Mercury + 20-50 labeled cases.

### Phase 3 — Eng dual-voice (RETHINK consensus)

- **Eng Claude:** LEAKY architecture, 4 critical findings, 15 total. Discovered: `context_injector_v2.py` ALREADY has Site B matcher (~145 LOC), and `tools/trigger_eval.py` has 50 hand-coded test cases reusable as ground truth.
- **Eng Codex:** RETHINK with concrete file:line citations across 13 source files. Strongest reframe: "extend `context_injector_v2` for OpenClaw, add `UserPromptSubmit` for Claude interactive, add dispatch-level telemetry in `command_center`, leave `telegram_poll` uninstrumented except correlation IDs, keep Mercury as downstream consumer."

### Phase 3.5 — DX dual-voice (TIGHTEN-FIRST + RETHINK)

- **DX Claude:** TIGHTEN-FIRST, scorecard 4.4/10, 13 findings. Caught: AP-61 self-similar schema-on-disk bug repeating; no `triggers-firing.policy.json` kill-switch despite AP-61's grader.policy.json precedent.
- **DX Codex:** RETHINK, scorecard **2.4/10** (lowest in 5-spec program). 12 findings with file:line refs. TTHW: "blocked / never today" (cannot produce + validate a first event without 4 missing tools). 5 P0 findings.

### Aggregate verdict: RETHINK + Mercury-extension + UserPromptSubmit + schema-on-disk

Not just TIGHTEN — the 6-voice consensus is to **rewrite around existing infrastructure**. The 4 P0/critical findings (wrong hook, schema-on-disk gap, no baseline, Mercury redundancy) constitute a structural defect, not polish gaps. Status flipped to `rethink-required-pending-bs8`.

### Recommended rewrite plan (concrete, file-citation-grounded)

1. **Add `UserPromptSubmit` hook** to `~/.claude/settings.json` (Claude Code Site A); SessionStart stays for session-open registration only. (Eng Claude F1 + Eng Codex F1)
2. **Extend `tools/context_injector_v2.py:145`** to return `{matched_skills, loaded_skills, scores}` structured output instead of building parallel matcher. (Eng Claude F3 + Eng Codex F3)
3. **Ship `pages/schemas/trigger_firing.v1.json`** as Phase-0 deliverable, mirroring `pages/schemas/supersession.v1.json` (AP-61 already has this). Self-similar fix to AP-61's BLOCKER. (DX Claude F1 + DX Codex P0)
4. **Drop `trigger_match_hash` OR rotate to HMAC** with secret salt + week bucket. Pure 12-char SHA prefix is rainbow-table-able for 12-digit IIN. (Eng Claude F3 + Eng Codex F6)
5. **Compile-time regex validator** (`tools/triggers_audit.py`) with ReDoS rejection (no nested unbounded quantifiers, no backrefs, length cap, per-pattern timeout 10ms on pathological input). Use Python `re` with timeout subprocess; consider `re2` for untrusted patterns. (Eng Claude F4 + Eng Codex F7)
6. **Reframe to Mercury extension first** — extend `ask_grader.py:75` issue enum with `silent_skip`, run Mercury Phase 1 for 30 days, see if `silent_skip` correlates with answer-quality drops. **Build standalone trigger-firing pipeline ONLY if Mercury can't localize the cause.** (CEO Claude+Codex consensus, DX Codex P1)
7. **Ship `~/nous-agaas/triggers-firing.policy.json` kill-switch** mirroring AP-61's `grader.policy.json`. Both Claude Code hook and OpenClaw pre-processor read on every fire. Madi can flip from any agent on any host. (DX Claude F6)
8. **Add `/trigger` Telegram surface** to `command_center.py:842` (cmd dispatcher already has `is_command()` for routing). Madi gets phone-side observability + `/trigger pause Nh` kill. (DX Codex P0)
9. **Per-host JSONL with explicit `host:` field** + aggregator merger. Existing pattern: `tools/tier_log.py:24` and `tools/ask_grader.py:50` use host-local paths. (Eng Codex F4)
10. **Schema-additive contract for `ask-hierarchy.jsonl`** — adding `trigger_fired:[...]` field must NOT break Mercury's existing `schema: "grader.v1"` reader. Test: `jsonschema` validation pre-flight. (DX Claude F3 + Eng Codex F9)
11. **Backfill UX for 26 missing `triggers:` fields** — auto-extract candidates with LLM ($0.26 total) + human-review batch + 5-skill pilot for FP-rate baseline before full backfill. (DX Claude F4 + DX Codex P1)
12. **Baseline-and-canary Phase 0** — 14-day passive observation with no alerts; ship full pipeline only if measured silent-skip rate >30% on TOP-10 invocation skills. (CEO consensus)

### Decision Audit Trail (gstack 6-principles)

| # | Phase | Decision | Class | Principle | Rationale |
|---|---|---|---|---|---|
| 1 | P0 | UI scope = 1 (false positive: "Component" in spec table); skip Phase 2 (Design) | Mechanical | P5 explicit | Same as prior 4 specs |
| 2 | P0 | Codex available, run full 6-voice | Mechanical | P6 bias-action | Codex usage_limit cleared |
| 3 | P1+P3+P3.5 | All 6 voices ran | Mechanical | (no degradation) | Real cross-model triangulation |
| 4 | P1 | Mark Mercury-redundancy as CRITICAL | Auto | P1 completeness | Codex grounded via `ask_grader.py:75` |
| 5 | P3 | Mark D1-wrong-hook as CRITICAL | Auto | P5 explicit | Both Eng voices grounded via `settings.json:52` + `session-start-soao.sh:43` |
| 6 | P3 | Mark schema-on-disk as CRITICAL (AP-61 self-similar) | Auto | P1 completeness | DX both voices |
| 7 | P3.5 | Set status `rethink-required-pending-bs8` not `tighten` | Auto | P5 explicit | 4 P0 findings = structural defect |
| 8 | P1 | Surface "extend Mercury OR build standalone" as USER CHALLENGE | User Challenge | P3 pragmatic | Both CEO models recommend changing direction; surface to Madi |

### Surfaced taste decisions for Madi (T1-T3) — Madi authorized "your call" 2026-04-30

**T1 → A APPLIED: extend Mercury Phase-1 first.** Run Mercury 30 days, build standalone trigger-firing only if Mercury's `issues:` enum can't localize the silent-skip cause. Spec body's Phase-0 + Phase-1 are paused until Mercury produces ≥30 days of `missed_context|wrong_routing` telemetry. New gate: standalone build greenlit only on data showing Mercury misses ≥20% of attributable silent-skips.

**T2 → A APPLIED: schema-on-disk + UserPromptSubmit + context_injector_v2 extension FIRST.** When standalone work IS authorized (per T1 gate), implementation order is: (a) `pages/schemas/trigger_firing.v1.json`, (b) `~/.claude/settings.json` `UserPromptSubmit` hook, (c) extend `tools/context_injector_v2.py:145` for OpenClaw site, (d) `command_center.py:842` `/trigger` Telegram surface, (e) `~/nous-agaas/triggers-firing.policy.json` kill-switch — in this order, no parallel ~400-LOC matcher.

**T3 → A APPLIED: instrument all 4 sites before global claims.** When implementation lane opens (per T1 gate), v1 covers Claude Code (UserPromptSubmit) + OpenClaw (context_injector_v2 extension) + Codex CLI (`tools/codex-nous.sh` wrapper) + Telegram poller (`telegram_poll.py:223` correlation-only, no matcher to avoid double-counting). Aggregate stats include `coverage_denominator` field per row. v2-deferred sites label themselves `partial_coverage: true` to prevent cherry-picked headlines.

## Timeline

- **2026-04-30** | Stub created in s100-mac-23069 lane-A as the T6 sibling from `Skill(autoplan)` v2 on the doctrine-drift spec. Captures the CEO subagent's 10x reframe: invocation-time observability, not audit-time. Status: `stub-pending-brainstorm`.
- **2026-04-30** | `Skill(superpowers:brainstorming)` ran. 7 D1-D7 questions resolved with recommended defaults. Status: `stub-pending-brainstorm` → `draft-pending-autoplan`. 131 → 235 lines.
- **2026-04-30** | `Skill(autoplan)` v1 ran in FULL 6-VOICE (Codex usage_limit cleared at 09:57 UTC). 3 phases (CEO + Eng + DX, Design skipped no UI scope). **All 6 voices verdict: RETHINK** (strongest autoplan consensus to date — 4 P0/critical findings cross-confirmed via file:line citations on real source code). Status: `draft-pending-autoplan` → `rethink-required-pending-bs8`. 13-row consensus table. 12-step recommended rewrite plan with concrete file refs. 3 taste decisions (T1-T3) surfaced. The shipped spec is NOT safe to ship as-is; recommended path is Mercury-extension + UserPromptSubmit + schema-on-disk before any standalone pipeline.
