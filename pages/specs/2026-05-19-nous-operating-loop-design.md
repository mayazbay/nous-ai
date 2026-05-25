---
type: spec
id: SPEC-2026-05-19-nous-operating-loop-design
title: "Nous operating loop — stricter-than-Spec-Kit workflow ladder (Madi directive 2026-05-19 ~18:05 KZT)"
date: 2026-05-19
status: draft
owner: claude-opus-4-7
priority: p0-constitution
tags: [spec-kit, operating-loop, constitution, doctrine, workflow, codex, opus, openclaw, obsidian, gbrain, openbrain, hermes, musk, karpathy, tan, mission-2026-05-19]
related:
  - [[MISSION-2026-05-19-always-on-satory-ai-factory]]
  - [[session-operating-contract]]
  - [[musk-algorithm]]
  - [[karpathy-loop]]
  - [[session-coordination]]
  - [[HANDSHAKE-2026-05-19-3-codex-opus-hermes-grok-hybrid-1748]]
---

# Nous operating loop — stricter-than-Spec-Kit workflow ladder

## Constitution (this is the constitution step itself)

Madi verbatim directive 2026-05-19 ~18:05 KZT:

> "The workflow I would choose now: Spec Kit style, but stricter than Spec Kit alone:
> `/constitution → /specify → /clarify → Musk delete/reduce → /plan → /tasks → canary → proof → skill/gbrain/OpenBrain sync → promotion`.
> That is the operating loop for Codex, Claude Code, OpenClaw, Obsidian, gbrain, and OpenBrain."

This is the binding 10-step ladder. Every non-trivial change goes through it, in order, with no step skipped. Stricter than vanilla Spec-Kit because:

1. **Musk delete/reduce inserted between Clarify and Plan** — every spec must show what gets deleted/replaced BEFORE planning impl (musk-algorithm v1.4.0 cognitive-debt guard).
2. **Canary and Proof are mandatory pre-promotion** — no production replacement without canary container + falsifiable proof gate (AP-21 24h soak doctrine, AP-29 model fixture wins).
3. **Skill/gbrain/OpenBrain sync is its own step** — RULE ZERO compliance is part of the loop, not an afterthought.

## The 10-step ladder

| # | Step | Artifact | Owner-default | Exit gate |
|---|---|---|---|---|
| 1 | `/constitution` | This doc or doc-of-its-kind | Lane proposer | Madi acknowledgement |
| 2 | `/specify` | `pages/specs/YYYY-MM-DD-<topic>-design.md` | Lane proposer | Spec doc committed |
| 3 | `/clarify` | Open-questions block in spec | Lane proposer | 1-4 Q&A pairs documented |
| 4 | **Musk delete/reduce** | `delete-considered:` annotation in spec + commit msg | Lane proposer | Net LOC flat-or-down OR explicit defer-window |
| 5 | `/plan` | Architecture section of spec | Lane proposer | Phases + file list + rollback path |
| 6 | `/tasks` | Spec-Kit task list with checkboxes | Lane proposer | Each task ≤ 1-2 hours of work |
| 7 | **canary** | Canary tag + isolated deploy | Owner lane (per MISSION scope) | `factory_no_drift_probe.sh --quiet` GREEN |
| 8 | **proof** | Falsifiable test fixtures + 6-axis Karpathy scorecard | Owner lane | All fixtures GREEN, scorecard recorded |
| 9 | **skill/gbrain/OpenBrain sync** | `pages/skills/<skill>/SKILL.md` AP fold + gbrain timeline push + OpenBrain capture | Owner lane | All 3 substrates updated, RULE ZERO clean (no LESSON files) |
| 10 | **promotion** | Production deploy + acceptance criterion verified | Owner lane | Acceptance criteria from spec checked, Madi greenlight if model-class/destructive |

## Clarify (open questions for Madi)

1. **New skill or extension?** This doctrine could land as either (a) a new `pages/skills/nous-operating-loop/SKILL.md` OR (b) an extension of `session-operating-contract` v1.17.0 → v1.18.0 with a new "Rule 23: ten-step ladder" entry. Recommend **(b)** — SOC is already the runtime contract every session reads; this is the natural fold target.
2. **Enforcement layer?** Pre-commit hook can mechanically check for `musk-step-2:` or `delete-considered:` annotation on commits that bump SKILL.md / add tools/* (already partially in place per musk-algorithm v1.4.0). Should we extend to require explicit ladder-step annotation (`ladder-step: 7-canary`, etc.) on all spec-derived commits? Recommend **defer** until 14-day soak proves the ladder rate-limits ship velocity acceptably.
3. **Apply retroactively?** My daily-evolution-runner ship (`05dfa3a8` + `1c2cf12e`) skipped steps 1, 2 partial, 3, 5, 6 — went straight from approved-spec to impl. Audit it as a soft retro-violation? Recommend **yes** — record retro-grade in next session-close as evidence of pre-doctrine velocity vs post-doctrine discipline.
4. **`/constitution` step for trivial fixes?** A one-line typo fix shouldn't trigger 10 steps. Define trivial-bypass: changes ≤ 10 LOC and ≤ 1 file in `pages/*` (non-skill) bypass steps 1-6 entirely, still require steps 9-10. Recommend codify as ladder AP-1.

## Musk delete/reduce (this spec's own step 4)

What this spec **deletes** when adopted:
- Implicit/informal flow patterns scattered across `session-operating-contract` Rule 13/15/17/19/22 — the ladder makes them explicit single-source.
- Ad-hoc "we follow Spec-Kit-ish" claims in handshake docs — replaced with concrete step references.

What this spec **adds**:
- 10-step ladder table (above)
- Trivial-bypass criterion (Clarify Q4)
- Cross-link to all 5 doctrine pillars (musk + karpathy + Tan-RULE-ZERO + Spec-Kit + Session-Operating-Contract)

Net: replacing ~5 scattered rules with 1 explicit ladder = doctrine reduction. Pass.

## Plan (when this lands as a skill or SOC extension)

```
session-operating-contract v1.17.0 -> v1.18.0
  + new Rule 23: "Ten-step Nous operating loop"
  + new AP-23: ladder-step-skipped (detector: commit msg lacks ladder-step annotation OR pre-commit hook can't trace artifact back to a spec)
  + Timeline entry pointing to this spec
  + Cross-ref: skills/musk-algorithm v1.4.0 (step 4), skills/karpathy-loop v1.12.0 (step 8 6-axis), session-coordination v1.33.0 (AP-32 pre-action), library-grade-audit v1.7.0 (step 8 falsifiable gates)
  + gbrain-timeline-ok marker

OR

NEW skill pages/skills/nous-operating-loop/SKILL.md v1.0.0
  + same 10-step ladder body
  + 4 APs (skip-ladder-step, skip-canary, skip-proof, skip-sync)
  + Mechanical detectors per AP
  + Register in pages/skills/_gbrain/RESOLVER.md

Madi chooses (a) or (b).
```

## Tasks

- [ ] **T1** — Madi answers Clarify Q1-Q4.
- [ ] **T2** — Author the ladder doctrine in chosen location (SOC v1.18.0 OR new skill).
- [ ] **T3** — Codex-3 (pages/skills/ lease holder per session_scan) co-signs OR Opus implements after lease release.
- [ ] **T4** — Pre-commit hook extension to enforce ladder-step annotation on substrate writes (deferred per Clarify Q2).
- [ ] **T5** — Retroactive audit of today's 10+ commits — which followed the ladder, which skipped.
- [ ] **T6** — Apply ladder dogfood-style to NEXT spec (multi-model-consult impl candidate).
- [ ] **T7** — 14-day soak window — measure ship-velocity delta vs pre-ladder baseline.

## Canary

This spec itself IS the canary. It's a substrate doc (low blast radius). Madi acknowledgement = canary-promoted to T2 ladder-fold candidate.

## Proof

Falsifiable gates this spec must pass before T2:
- ✅ No LESSON file created (RULE ZERO check)
- ✅ `pages/specs/` is Opus scope (AP-32 v1.33 pre-action confirmed)
- ✅ Spec format matches Spec-Kit shape (Constitution/Specify/Clarify/Musk/Plan/Tasks/Implement/Acceptance)
- ✅ Musk delete/reduce shown explicitly (above)
- ✅ Cross-links to 5 doctrine pillars present
- ⏳ Karpathy 6-axis self-score: pending (will run at T2 fold time)

## Skill/gbrain/OpenBrain sync

At T2:
- SKILL.md update (SOC v1.18.0 OR new skill) — Codex-3 lane OR Opus after lease release
- `mcp__gbrain__add_timeline_entry slug="pages/skills/<chosen>/skill"` via VPS CLI fallback
- OpenBrain capture: `mcp__claude_ai_Open_Brain__capture_thought` with this doc URL

## Promotion

After T2 + T5 retro-audit + 14-day soak, the ladder becomes the binding default for every agent (Codex, Claude Code, OpenClaw, Obsidian batches, gbrain ingestion, OpenBrain projection). Acceptance criterion: ship velocity in the 14-day soak window must be ≥ 80% of pre-ladder velocity AND ship-quality scorecard (Karpathy 6-axis) must average ≥ 1.5/2.0 across all axes.

## Acceptance criteria (binding, falsifiable)

1. **Single canonical location** — exactly one place names the ladder (SOC v1.18.0 OR new skill); other docs link to it.
2. **Every spec from 2026-05-20 forward shows step-4 delete/reduce annotation** — measurable via `git log --grep="delete-considered:"` count.
3. **Every promotion (step 10) records gbrain-timeline-ok marker** — measurable via `git log --grep="gbrain-timeline-ok"` since 2026-05-20.
4. **No LESSON file created in 14 days post-promotion** — RULE ZERO mechanical hook already enforces.
5. **Ship-velocity within 80% of pre-ladder baseline** — count commits/day in 14-day window vs 7-day pre window.

## See also

- `[[HANDSHAKE-2026-05-19-3-codex-opus-hermes-grok-hybrid-1748]]` — the 5-lane handshake that surfaced this constitution need
- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` — parent mission
- `[[skills/session-operating-contract]]` v1.17.0 — fold target candidate (a)
- `[[skills/musk-algorithm]]` v1.4.0 — step 4 source-of-truth
- `[[skills/karpathy-loop]]` v1.12.0 — step 8 6-axis source-of-truth
- `[[skills/session-coordination]]` v1.33.0 — AP-32 pre-action handshake doctrine (applies to every step's substrate write)
- `[[skills/library-grade-audit]]` v1.7.0 — step 8 falsifiable-gate source

## Timeline

- **2026-05-19 18:05 KZT** — Madi delivered the 10-step ladder verbatim as the binding operating loop for all 6 agents (Codex / Claude Code / OpenClaw / Obsidian / gbrain / OpenBrain).
- **2026-05-19 18:07 KZT** — This spec authored by Opus lane. AP-32 v1.33 pre-action handshake passed (pages/specs/ Opus scope, no peer authoring overlap). Awaiting Madi greenlight on Clarify Q1/Q2/Q4 + Codex-3 lease release for T2 fold.
