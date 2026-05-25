---
type: convention
title: Skill Tier Classification Convention
date: 2026-05-04
status: active
related:
  - "[[plans/PLAN-SUBSTRATE-V2-2026-05-03]]"
  - "[[plans/PLAN-SUBSTRATE-V2-REQUIREMENTS-2026-05-03]]"
---

# Skill Tier Classification Convention

Per Nate B Jones "Skills Are Infrastructure" (`20260324-kyk` Prompt 4) — every canonical skill in `pages/skills/<name>/SKILL.md` carries a `tier:` frontmatter field with values 1, 2, or 3.

Enforced by `Nous/.git/hooks/pre-commit` RULE 11 (substrate-v2 Phase 0.7, 2026-05-04). Source canonical: `Nous/tools/pre-commit-canonical`.

## Tier 1 — Standards (auto-load every session)

Non-negotiable doctrine. Every Claude Code, Codex, factory worker, OpenClaw session loads these mandatorily at session-start. If output violates a Tier-1 skill, that's a defect.

**The 5 Tier-1 skills (as of 2026-05-04):**
- `agent-quality` — every action is checked
- `evidence-verification` — every claim must be verified
- `error-classification` — every error must be tagged
- `karpathy-coding-principles` — every code change
- `session-operating-contract` — runtime contract for every session

(All `pages/laws/LAW-*.md` files are implicit Tier-1 — they are constitution-level and load via separate mechanism.)

**Tier 1 graduates (planned):**
- `substrate-event-log` — to be added in substrate-v2 Phase A. Every session must know how to emit events.

## Tier 2 — Methodology (load by domain)

Compounding doctrine for high-leverage workflows. Loaded by relevance to the current task. Not always loaded but always reachable.

**The 19 Tier-2 skills (as of 2026-05-04):**

| Skill | Loaded when |
|---|---|
| `karpathy-loop` | Plans, multi-step work, session-close scoring |
| `musk-algorithm` | Engineering decisions, scope reviews |
| `audit` | Audit work |
| `library-grade-audit` | Obsidian + gbrain retrieval audits |
| `mistake-to-skill` | Codifying lessons (RULE ZERO doctrine) |
| `planning-discipline` | Planning multi-step work |
| `ceo-hierarchy` | LLM routing decisions |
| `factory-ops` | Factory worker operations |
| `command-center` | OpenClaw / Telegram routing |
| `gbrain-ops` | gbrain operations |
| `air-ssh-access` | Working with Air machine |
| `find-skills` | Skill discovery |
| `session-coordination` | Multi-session work, anti-collision |
| `session-architecture` | Session design |
| `storage-retrieval` | Knowledge work |
| `secrets-management` | Handling secrets / env |
| `tailscale-stability` | Network / Tailscale issues |
| `infrastructure` | Infra changes |
| `operator-boundaries` | Scope decisions |

## Tier 3 — Personal workflow / per-task (by request)

Specific patterns for individual workflows. Loaded only when invoked by name or explicit topic match.

**The 7 Tier-3 skills (as of 2026-05-04):**
- `camera-management`
- `collaborative-reading`
- `kazakhstan-regulatory`
- `metrology-cert-tracker`
- `satory-dashboard`
- `smartbridge-soap-client`
- `website-deploy`

## Frontmatter format

```yaml
---
tier: 1   # or 2 or 3
...other fields...
---
```

The `tier:` field is required. Pre-commit hook (RULE 11) rejects any new or modified canonical SKILL.md without a valid `tier:` value in {1, 2, 3}.

## Sub-skills under `pages/skills/_gbrain/*/SKILL.md`

Sub-skills under the `_gbrain/` directory (e.g. `_gbrain/brain-ops/SKILL.md`) are exempt from RULE 11 because they are not canonical Nous skills — they are gbrain ingest sub-modules registered in `_gbrain/RESOLVER.md`. The hook regex `^pages/skills/[^/_][^/]*/SKILL\.md$` excludes paths starting with `_`.

## Counts

| Tier | Count | % |
|---|---|---|
| 1 | 5 | 16% |
| 2 | 19 | 61% |
| 3 | 7 | 23% |
| **Total** | **31** | 100% |

## Adding new skills

When creating a new canonical skill via `Skill(superpowers:writing-skills)`:
1. Decide the tier based on this convention's definitions
2. Include `tier: <N>` in the frontmatter from the start
3. If unsure, default to Tier 3 — it's easier to promote than demote
4. Register in `_gbrain/RESOLVER.md` if it should appear in agent skill discovery

## See also

- [[plans/PLAN-SUBSTRATE-V2-2026-05-03]] §Phase 0.5
- [[skills/find-skills]] — skill discovery mechanism
- Source: Nate B Jones "Skills Are Infrastructure" (2026-03-24 prompt kit)
