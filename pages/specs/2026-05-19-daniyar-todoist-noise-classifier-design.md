---
type: spec
id: SPEC-2026-05-19-daniyar-todoist-noise-classifier-design
title: "Daniyar Todoist noise classifier (LLM-augmented) — Spec-Kit /specify"
date: 2026-05-19
status: draft
owner: claude-opus-4-7
priority: p1
tags: [spec-kit, todoist, daniyar, classifier, llm, noise-reduction, satory, operator-digest, mission-2026-05-19]
related:
  - [[MISSION-2026-05-19-always-on-satory-ai-factory]]
  - [[skills/todoist-control-plane]]
  - [[HANDSHAKE-2026-05-19-three-lane-opus-codex-codex2]]
---

# SPEC — Daniyar Todoist noise classifier (LLM-augmented)

Spec-Kit shape. **Do not implement until Madi approves this spec.**

Slot E from `[[HANDSHAKE-2026-05-19-three-lane-opus-codex-codex2]]`. Tightens the operator digest signal by classifying Daniyar's repetitive low-signal entries before they reach the daily Russian digest the Satory team sees.

## Constitution (rules this spec inherits)

- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` — operator digest is plain Russian status/blocker/next/owner/proof; no AI bookkeeping spam.
- `[[skills/todoist-control-plane]]` v1.8.3 — `execution_state` + `delete_candidate_reason` fields already exist on each task row; the classifier extends, not replaces.
- `[[skills/musk-algorithm]]` v1.3.0 step 2 — delete before adding. Do not add a new classifier if existing rule-based heuristics suffice; only fill the edge-case 20%.
- `[[skills/karpathy-coding-principles]]` — surgical changes, no speculative features, simplicity first.
- AP-21 — canary-only for new runtime; classifier outputs first land in audit-only mode before influencing the digest.

## Specify (what we're building)

A **thin LLM-augmentation layer** on top of the existing rule-based deep audit classifier (`tools/satory_todoist_deep_audit.py`). For tasks the rule-based heuristics leave UNCLASSIFIED (`delete_candidate_reason` is null AND `execution_state` is not one of `queued/blocked/review_delete`), invoke an LLM (default: `local-mlx-coder` via LiteLLM — $0 marginal cost) to assign one of:

- `SIGNAL` — real work, ready for the digest
- `NOISE` — repetitive low-value entry (e.g., "Приветствие — настройка брифинга", "напомни Мади еще раз про X")
- `DUPLICATE` — same content as another task within last 7 days
- `META` — about Todoist itself (onboarding, setup, restructure)
- `DELETE_CANDIDATE` — confidently archivable; surface for Madi confirmation
- `UNSURE` — confidence below threshold; escalate to multi-model-consult (when that skill ships)

The classifier writes into a NEW field `llm_noise_class` + `llm_noise_confidence` on each task row. The operator digest reader uses this field to filter: only `SIGNAL` reaches the digest; `NOISE` is silent-logged to `pages/systems/todoist-noise-ledger.jsonl`; `DUPLICATE` is silently merged into parent task; `META` stays in Todoist but does not surface to digest; `DELETE_CANDIDATE` gets a Madi-action-required entry once per day.

### Fields added to deep audit row

```json
{
  "llm_noise_class": "SIGNAL|NOISE|DUPLICATE|META|DELETE_CANDIDATE|UNSURE",
  "llm_noise_confidence": 0.0,  // 0.0–1.0
  "llm_noise_rationale": "string (max 200 chars, in Russian for operator review)",
  "llm_noise_classifier_model": "local-mlx-coder",
  "llm_noise_classified_at": "ISO8601 timestamp",
  "llm_noise_replaces_rule_decision": true  // false if rule had already decided
}
```

### Default routing matrix (after classifier ships)

| llm_noise_class | confidence | Operator digest | Todoist action | Action |
|---|---|---|---|---|
| `SIGNAL` | ≥0.7 | ✅ included | none | digest emits |
| `SIGNAL` | <0.7 | ✅ included with `(?)` marker | none | digest emits with confidence flag |
| `NOISE` | ≥0.8 | ❌ filtered | none | silent ledger entry only |
| `DUPLICATE` | ≥0.8 | ❌ filtered (parent included) | optional: merge comment | silent ledger + merge log |
| `META` | ≥0.6 | ❌ filtered | none | silent ledger only |
| `DELETE_CANDIDATE` | ≥0.85 | ❌ filtered | mark for archive | Madi-action-required: daily summary at 09:00 KZT lists candidates |
| `UNSURE` | any | ✅ included with `(?)` | none | escalate to multi-model-consult if available |

## Clarify (open questions for Madi)

1. **Threshold tuning** — defaults above (`0.7`/`0.8`/`0.85`) are conservative. Confirm or override after first 24h of canary run.
2. **Owner scope** — start with Daniyar entries only (Slot E framing) OR all owners (broader noise reduction)? **Recommend: Daniyar only for v1; widen after 7-day proof.**
3. **Fallback when MLX down** — degrade to rule-based decision (current behavior) OR escalate to deepseek-v4-flash? **Recommend: degrade gracefully** (no escalation cost on a noise classifier).
4. **Russian rationale only** — generated rationale field in Russian (operator-facing) OR also English (Madi internal review)? **Recommend: Russian only**; Madi can ask multi-model-consult if he needs English explanation.
5. **Daily DELETE_CANDIDATE digest cadence** — once per day at 09:00 KZT (Satory morning) OR end-of-day? **Recommend: 09:00 KZT** with the regular morning operator digest.
6. **Telegram delivery of DELETE_CANDIDATE list** — direct Madi DM via `tg_send.sh` OR include in Satory group digest? **Recommend: Madi DM only** (private operator-management decision).

## Plan (architecture)

```
┌──────────────────────────────────────────────────────────────┐
│  tools/satory_todoist_deep_audit.py (existing)               │
│  - rule-based classifier already populates                   │
│    delete_candidate_reason + execution_state                 │
│                                                              │
│  AFTER rule-based pass:                                      │
│    for row in tasks:                                         │
│      if row.delete_candidate_reason or                       │
│         row.execution_state in {'queued','blocked',          │
│                                  'review_delete'}:           │
│         skip (rule already decided)                          │
│      else:                                                   │
│         row.llm_noise_class = call_classifier(row)           │
└────────────────────────┬─────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│  tools/todoist_noise_classifier.py (NEW, ~120 lines)         │
│  - prompt: "Classify this Todoist task per                   │
│    {SIGNAL|NOISE|DUPLICATE|META|DELETE_CANDIDATE|UNSURE}     │
│    based on content, comments, owner, last-update-age."      │
│  - LiteLLM model: local-mlx-coder                            │
│  - response schema: JSON {class, confidence, rationale_ru}   │
│  - cache by content sha8 (idempotent re-classifications)     │
│  - timeout: 10s; on timeout → return UNSURE                  │
│  - daily cost cap: $0 (MLX local); fallback rule-based       │
└──────────────────────────────────────────────────────────────┘
```

### Files

- **New**: `tools/todoist_noise_classifier.py` (~120 lines)
- **New**: `tools/tests/test_todoist_noise_classifier.py` (fixture-based, ~80 lines)
- **New**: `pages/specs/benchmark-fixtures/daniyar-noise-fixture-2026-05-19.jsonl` (30 labeled examples)
- **Modify**: `tools/satory_todoist_deep_audit.py` (add LLM-augmentation pass after rule-based; ~25 lines)
- **Modify**: `tools/human_owner_reminder.py` (digest filter respects `llm_noise_class`; ~15 lines)
- **Modify**: `pages/skills/todoist-control-plane/SKILL.md` (new AP for the LLM layer; RULE ZERO 3-edit ritual)
- **New**: `pages/systems/todoist-noise-ledger.jsonl` (silent ledger of NOISE/DUPLICATE/META decisions, append-only)

### Deletion (Musk step 2 first)

Before shipping a new classifier, audit existing rule-based heuristics in `tools/satory_todoist_deep_audit.py`. If the rule-based hit rate is already >85% on a labeled fixture, the LLM-augmentation may be **scope-cuttable** — Musk step 2 says delete this slice entirely. Acceptance gate: classify the 30-entry fixture with rules-only first; if rules-only ≥85% accurate, this spec gets shelved. If <85%, ship the LLM layer.

## Tasks (Spec-Kit ordered)

- [ ] **T1** — Madi answers Clarify Q1–Q6.
- [ ] **T2** — Author the 30-entry labeled fixture (real Daniyar entries from last 30 days, manually labeled).
- [ ] **T3** — Measure rule-based accuracy on the fixture. If ≥85%, SHELVE this spec; document outcome in audit; close.
- [ ] **T4** — If rules-only <85%, author `tools/todoist_noise_classifier.py` + regression tests.
- [ ] **T5** — Wire LLM-augmentation pass into `satory_todoist_deep_audit.py` after rule-based pass (canary mode: writes `llm_noise_*` fields but does NOT yet filter digest).
- [ ] **T6** — Canary 24h: measure agreement rate between LLM-augmentation and operator (Madi) ground truth. Acceptance: ≥90% agreement on `SIGNAL`/`NOISE` calls, ≥95% on `DELETE_CANDIDATE` (false positives = bad).
- [ ] **T7** — Wire digest filter to respect `llm_noise_class` AFTER 24h canary clears.
- [ ] **T8** — `pages/skills/todoist-control-plane` SKILL.md AP for LLM-augmentation layer. RULE ZERO 3-edit ritual.
- [ ] **T9** — Promote daily DELETE_CANDIDATE digest to 09:00 KZT Madi DM after 7-day false-positive rate ≤2%.

## Implement (execution log — append as work happens)

(empty until Madi approves spec)

## Acceptance criteria (binding, falsifiable)

1. **Rule-based-only fixture accuracy measured first.** If ≥85% on the 30-entry labeled fixture, spec is shelved per Musk step 2. Falsifiable: rerun T3 anytime; result is deterministic.
2. **LLM-augmentation only fires on previously-unclassified rows.** Rule-based decisions remain authoritative for rows they covered. Test: no row has both `delete_candidate_reason != null` AND `llm_noise_class != null`.
3. **Cost cap holds**: $0/day on MLX path. If MLX down, classifier falls back to rules-only (no API spend on noise classification).
4. **24h canary agreement ≥90% on SIGNAL/NOISE**, ≥95% on DELETE_CANDIDATE. Operator (Madi) confirms ground truth on a sample of 20 entries per day.
5. **No silent over-filter**: any row classified as NOISE/META/DELETE_CANDIDATE writes to `todoist-noise-ledger.jsonl` for audit. Falsifiable: spot-check ledger entries against Todoist task IDs.
6. **Daniyar's repetitive setup/onboarding entries get filtered out of operator digest** (the bug Madi originally flagged). Falsifiable: post-deploy digest sample should contain zero "Приветствие — настройка брифинга"-style entries.

## Rollback path

- Set env `TODOIST_LLM_NOISE_DISABLED=1` → classifier short-circuits, returns rule-based-only behavior.
- Or revert the digest filter modification; classifier still writes fields but doesn't affect digest.
- Or remove `pages/systems/todoist-noise-ledger.jsonl` (silent ledger; no data loss).
- No production data lost; all decisions are advisory/canary until T7.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM false-positives on DELETE_CANDIDATE (archives real work) | Med | High | Threshold 0.85; Madi-action-required daily review; rule-based decisions authoritative |
| MLX timeout under load slows audit cycle | Med | Low | 10s per-row timeout; return UNSURE on timeout (no blocking) |
| Bias in fixture labels (Madi labels skew toward Daniyar voice patterns) | Med | Med | Co-label with Codex spawn for diversity; track agreement |
| Scope creep: classifier expanded to all owners before Daniyar v1 proves | Low | Med | Spec explicitly scopes to Daniyar; widening requires new spec slice |
| LLM hallucinates a "rationale" without grounding | Med | Low | Rationale field is advisory only; gate decisions on confidence threshold |
| Adds tool LOC without removing existing rules | Med | Med | Musk step 2 acceptance: tool LOC flat or down (delete redundant rule heuristics where LLM subsumes) |

## See also

- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` — Satory operator digest doctrine
- `[[skills/todoist-control-plane]]` v1.8.3 — current classifier doctrine
- `[[HANDSHAKE-2026-05-19-three-lane-opus-codex-codex2]]` — Slot E origin
- `[[2026-05-19-multi-model-consult-skill-design]]` — escalation target for UNSURE rows when multi-model-consult ships
- `[[CHEAP-POOL-BENCHMARK-2026-05-19]]` — local-mlx-coder benchmark win (this classifier uses it)

## Timeline

- **2026-05-19 15:55 KZT** — Tier-0 MLX bakeoff GREEN, enables this spec (MLX is the $0-cost classifier engine).
- **2026-05-19 16:00 KZT** — Spec authored by Claude Opus 4.7 lane. Awaiting Madi review.
