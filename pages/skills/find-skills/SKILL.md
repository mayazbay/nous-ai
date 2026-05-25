---
tier: 2
type: skill
name: find-skills
id: SKILL-FIND-SKILLS
version: 1.0.0
last_updated: 2026-04-22
status: active
description: "Meta-skill: discover + install agent skills from the open skills ecosystem (skills.sh leaderboard, vercel-labs/skills CLI). Upstream: github.com/vercel-labs/skills. Query by natural-language intent → queries skills.sh leaderboard + runs `npx skills find <query>` → verifies install-count + source-reputation + GitHub-stars before recommending → installs via `npx skills add <owner/repo@skill> -g -y`. Use when user asks 'how do I do X', 'find a skill for X', 'is there a skill that can...', or expresses interest in extending capabilities. Quality gate: prefer skills with 1K+ installs; verify official sources (vercel-labs, anthropics, microsoft); treat <100 stars with skepticism."
triggers:
  - how do I do X
  - find a skill for X
  - is there a skill for X
  - is there a skill that can
  - can you do X
  - extend capabilities
  - wish I had help with
  - search for tools, templates, or workflows
tools: [Bash]
mutating: false
absorbs_sources:
  - "https://github.com/vercel-labs/skills"
  - "https://skills.sh/"
related: [karpathy-coding-principles, karpathy-loop, session-operating-contract, mistake-to-skill]
tags: [skill, meta, discovery, vercel-labs, skills-ecosystem, skills.sh, npx, cross-agent, claude-code, codex, opencode, cursor, 2026-04-22]
title: "find-skills v1.0.0"
---

# find-skills v1.0.0

## Purpose

Discovery-and-install tool for the open agent-skills ecosystem. Operates at the **meta-skill layer** — instead of executing a task, it helps the agent pick the right task-skill from the ecosystem.

Installed 2026-04-22 via official `npx skills add vercel-labs/skills --skill find-skills -g -a claude-code -y`. The command completed on both Mac and Air with Socket verdict "Safe" + 0 alerts + Snyk "Med Risk" (reviewed; acceptable for trusted Vercel Labs origin).

## When to invoke

Exactly the triggers upstream defines. Three shapes:

1. **User asks for help with a task that might have an existing skill** — "how do I make my React app faster?" → `npx skills find react performance`.
2. **User asks directly about skill discovery** — "is there a skill for X?" → leaderboard check + CLI search.
3. **User expresses interest in extending capabilities** — "I wish I had something that does X" → search ecosystem.

## Quality gate (upstream discipline — non-negotiable)

Before recommending any skill, verify:
- **Install count ≥ 1K** preferred. <100 installs = skeptical.
- **Source reputation** — `vercel-labs`, `anthropics`, `microsoft` > unknown.
- **GitHub stars ≥ 100** on the source repo.
- **Security signals** — run `npx skills add <pkg> --list` first; check Socket/Snyk verdict in output.

If none of the above, say so. Don't recommend on vibes.

## Deployment (honest state)

| Surface | Path | Status |
|---|---|---|
| Mac Claude Code | `~/.claude/skills/find-skills/SKILL.md` | ✅ via `npx skills add` |
| Air Claude Code | `~/.claude/skills/find-skills/SKILL.md` on Air | ✅ via `npx skills add` |
| Air factory runtime | `~/nous-agaas/skills/vercel-find-skills/SKILL.md` | ✅ via `tools/gstack_to_openclaw_adapter.py --prefix vercel-` |
| Vault wrapper | `pages/skills/find-skills/SKILL.md` (this file) | ✅ |
| Source archive | `pages/concepts/vercel-skills-ecosystem-2026-04-22/` | ✅ |
| RESOLVER row | `pages/skills/_gbrain/RESOLVER.md` | ✅ |
| CLAUDE.md pointers | Mac-root + vault | ✅ |

Factory count: 78/124 → 79/125 ready post-install.

## How it fits with our existing stack

- **Complementary to `karpathy-loop`** (meta-scorecard) and **`karpathy-coding-principles`** (code-behavior). find-skills is the **skill-discovery meta-layer**.
- **Paired with `gbrain-skillify`** (our adapted Tan skill — "turn any raw feature or script into a gbrain-compatible skill"). Workflow: `find-skills` → install upstream skill → `skillify` → enrich to our vault format.
- **Dovetails with RULE ZERO**: the skills ecosystem is gbrain-timeline-compatible. Every adopted upstream skill gets our adapter + vault wrapper + gbrain timeline entry, so the "compounding skill pack" thesis holds regardless of origin.

## Workflow (concrete)

```bash
# 1. User asks: "Is there a skill for writing changelogs?"
# 2. Check leaderboard first:
open https://skills.sh/?q=changelog
# 3. CLI search:
npx skills find changelog
# 4. Inspect candidates — prefer 1K+ installs from known sources:
npx skills add vercel-labs/agent-skills --list | grep -i changelog
# 5. Security pre-check via --list output (Socket / Snyk alerts displayed)
# 6. Install globally for Claude Code:
npx skills add vercel-labs/agent-skills --skill changelog-generator -g -a claude-code -y
# 7. Adapt for factory (our extra step — not in upstream):
python3 tools/gstack_to_openclaw_adapter.py \
  --source <cloned-repo>/skills \
  --target ~/nous-agaas/skills \
  --prefix vercel-
# 8. Restart factory, verify openclaw skills info <skill>
# 9. Write vault wrapper at pages/skills/<skill>/SKILL.md + RESOLVER row
# 10. Push gbrain timeline entry
```

Steps 1-6 are upstream flow. Steps 7-10 are **our compounding extensions** so factory + gbrain + vault all inherit every adopted skill.

## Anti-patterns (to codify after first real use — pending)

- AP-1 (pending): installing based on search rank without verifying install-count. Recommend → user runs → skill misbehaves → trust-tax on the discovery workflow itself.
- AP-2 (pending): skipping the factory-adapter step. Claude Code gets the skill; factory doesn't; `/ask` queries find-skills agent-locally fail in factory.

## Evidence trail

- **2026-04-22** | v1.0.0 created. Madi forwarded the vercel-labs/skills repo + the "Find Skills" framing (describe what you want → ecosystem suggests perfect skill). Deployed same-day via official CLI on Mac + Air; adapted for factory with `gstack_to_openclaw_adapter.py --prefix vercel-`. Factory skill count 78/124 → 79/125 ready; `openclaw skills info vercel-find-skills` returned "✓ Ready". Mac DNS unreliable for raw.githubusercontent.com (intermittent this session) but VPS route proven for source archival. No new LESSON (RULE ZERO). Pattern: *every future skill ecosystem becomes another adapter invocation + vault wrapper + gbrain timeline — the compounding pack grows without exponential maintenance.*

## See also

- Upstream: [github.com/vercel-labs/skills](https://github.com/vercel-labs/skills)
- [skills.sh](https://skills.sh/) — leaderboard + browse
- [[karpathy-coding-principles]] — code-behavior sibling
- [[karpathy-loop]] — meta-scorecard sibling
- `gbrain-skillify` — our adapter-applied Tan skill for turning raw features into skills (planned; not yet authored)
- `gbrain-skillpack-check` — validates the growing pack stays conformant (planned; not yet authored)
- [[concepts/forrestchang-karpathy-claudemd-source-2026-04-21/CLAUDE]] — adjacent absorption pattern (concept directory)
- [[gbrain-minions]] — also adapted-in from upstream gbrain
