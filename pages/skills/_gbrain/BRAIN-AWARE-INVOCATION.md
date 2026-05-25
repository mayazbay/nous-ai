---
type: skill
name: brain-aware-invocation
id: BRAIN-AWARE-INVOCATION
version: 1.0.0
date: 2026-04-17
status: reviewed
description: Shared pattern for brain-aware skills (gstack v0.18.0.0 adoption). Search gbrain BEFORE the core work for prior context; append findings to the skill's timeline AFTER.
source: gstack v0.18.0.0 release (2026-04-17)
tags: [gstack, gbrain, skill-pattern, karpathy, garry-tan]
triggers:
  - invoked by any skill that declares "brain-aware: true" in its frontmatter or rules
  - starting work on a file, service, or topic that may have prior findings
title: "Brain-Aware Invocation v1.0.0 (gstack v0.18.0.0)"
---

# Brain-Aware Invocation v1.0.0 (gstack v0.18.0.0)

## Why

gstack v0.18.0.0 made 10 of its 38 skill templates "brain-aware": before doing the core work, search the brain for prior context; after, save what you learned. This closes the learn-loop — past work informs future invocations.

Karpathy/Tan principle: skills compound. If the last agent who touched this file already found the right answer, the next agent should know.

## The two steps

### Step BEFORE (search, fast keyword)

Before core work:

```
mcp__gbrain__search  query="<keywords from the task>"  limit=10
```

Use **`search`** (fast keyword / BM25) — NOT **`query`** (expensive hybrid with embeddings). For affected file paths, search the full path string AND the bare filename.

If 0 hits → note "no prior context, proceeding from clean slate" and continue.
If hits → read top 3, factor into plan BEFORE starting work. If hits contradict the plan, stop and reconcile (see mistake-to-skill AP-10 Confusion Protocol).

### Step AFTER (timeline-add, on the skill page)

After core work done + verified:

```
mcp__gbrain__add_timeline_entry
  slug="pages/skills/<this-skill>/skill"
  date="YYYY-MM-DD"
  summary="<one-line what was done + outcome>"
  detail="<optional: commit hash, file paths touched, key finding>"
```

Skills compound when their timeline grows. This is the evidence trail the next agent reads during Step BEFORE.

## Which skills are brain-aware (as of 2026-04-17)

| Skill | Search-before keywords | Save-after summary convention |
|---|---|---|
| agent-quality | file path + function name | "Fixed bug in <file>, root cause <X>" |
| audit | subsystem name + date | "Audit <subsystem> on <date>: N pass / M fail" |
| mistake-to-skill | lesson id + target skill | "Absorbed LESSON-N into <skill> AP-M" |
| camera-management | camera UUID or IP | "Camera <UUID> <action>: <outcome>" |
| satory-dashboard | component or route | "Deploy <component>: JS hash <hash>" |
| infrastructure | service name + host | "<service> on <host>: <change>" |
| gbrain-ops | op type + target | "gbrain <op>: <target>, <outcome>" |
| command-center | command or route | "Routing <cmd>: <change>" |
| planning-discipline | plan id or topic | "Plan <id>: <decision>" |
| website-deploy | component + env | "Deployed <component> to <env>, hash <H>" |

## Anti-patterns

**AP-1: using `query` instead of `search`.** Hybrid query with embeddings is ~20× slower and costs embedding tokens. For pre-work context scan, keyword `search` is enough.

**AP-2: skipping save-after because "nothing noteworthy happened".** The null result IS noteworthy — the next agent should know you looked at file X and found it already correct. Save `"reviewed <file> — already correct, no change"`.

**AP-3: searching the wrong slug convention.** Timeline entries belong on the **skill** page (`pages/skills/<skill>/skill`), not on a dated journal. Verify the slug resolves before calling `add_timeline_entry`.

## Timeline

- 2026-04-17 | v1.0.0 — created per gstack v0.18.0.0 adoption (session 37). Shared pattern referenced by 10 domain skills via one-line bullet; eliminates per-skill duplication of the pattern text.

## See also

- [[skills/_gbrain/RESOLVER.md]] — skill dispatcher
- [[skills/mistake-to-skill/SKILL.md]] — AP-10 Confusion Protocol covers ambiguous search-result interpretation
- [[skills/gbrain-ops/SKILL.md]] — skill-level rules about gbrain health and maintenance
