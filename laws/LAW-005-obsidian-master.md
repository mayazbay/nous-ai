---
type: law
id: LAW-005
title: "Obsidian is Single Source of Truth (physically enforced)"
status: permanent
enforcement: symlink
tags: [obsidian, wiki, memory, hierarchy, source-of-truth, physical-enforcement]
related: [LAW-001, AMD-003, LAW-013]
date: 2026-04-08
last_updated: 2026-04-08
source_count: 0
---
# LAW-005: OBSIDIAN IS THE SINGLE SOURCE OF TRUTH
Status: **PERMANENT + PHYSICALLY ENFORCED**. Updated 2026-04-08.
Enforcement: Symlinks + architecture. Claude Code and all agents physically CANNOT write state outside the Obsidian vault.

> Madi verbatim 2026-04-08: "You don't breathe, you don't work without it. That's it. And agents as well."

## Hierarchy (STRICT)

1. **Obsidian Wiki** = MASTER. THE ONLY SOURCE OF TRUTH.
   - Mac path: `/Users/madia/Documents/Projects/Nous AGaaS/Nous/`
   - VPS path: `/root/nous-agaas/wiki/` (bidirectional git sync every 60s via bare repo)
   - ALL agents read this BEFORE any work
   - ALL lessons, laws, specs, progress, conversation state, Claude Code auto-memory, session handoffs, prompts, scratchpads — written HERE. Nowhere else.
   - If ANYTHING on any disk contradicts the wiki → WIKI WINS, the other copy is stale and must be deleted or re-derived from the wiki.

2. **Claude Code auto-memory** = PHYSICALLY INSIDE THE WIKI via symlink.
   - External path: `/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/`
   - This path is a **symlink** → `pages/progress/claude-memory/` in the vault.
   - When Claude Code writes MEMORY.md, feedback_*.md, lessons_*.md, user_profile.md, project_live_state.md, the write lands INSIDE the vault. Git sync picks it up within 60s and pushes to VPS.
   - **You physically cannot bypass Obsidian** — there is no separate `memory/` directory.
   - Set up 2026-04-08 by moving all existing auto-memory files into `pages/progress/claude-memory/`, `rmdir`-ing the old path, then `ln -s` back.

3. **Mem0 / any other "memory" system** = FORBIDDEN unless it's a view over the vault.
   - No parallel memory stores. Not in ~/.claude elsewhere. Not in Mac Notes. Not in scattered text files. Not in the Claude Code session that only exists in RAM.
   - If an agent learns something, it goes into `pages/lessons/` or `pages/progress/` FIRST, then is accessible to everyone.

## Verification commands (agent self-check at session start)

```bash
# Must print: "memory -> /Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/progress/claude-memory"
ls -la ~/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/ | grep memory

# Must show MEMORY.md inside the vault
ls "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/progress/claude-memory/MEMORY.md"

# Must show the vault at the same git hash as VPS
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && git log --oneline -1
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git log --oneline -1'
```

If ANY of these fail → HALT. Restore the symlink + sync BEFORE touching anything else.

## The Flow (no exceptions)

1. New law / lesson / fix / feedback / project state / user preference / session insight discovered
2. Write it to the vault FIRST. Path depends on type:
   - Law → `laws/LAW-XXX-slug.md`
   - Lesson → `pages/lessons/individual/LESSON-XXX-slug.md`
   - Audit → `pages/audits/AUDIT-XXX-slug.md`
   - Session state / auto-memory → `pages/progress/claude-memory/`
   - Session handoff → `pages/progress/HANDOFF-YYYY-MM-DD.md`
   - User feedback → `pages/progress/claude-memory/feedback_*.md`
3. Update `index.md` if it's a new canonical page
4. Append a one-liner to `log.md` so the chronological record is complete
5. Commit happens automatically via the 60s launchagent + wiki_to_bare cron

## Why Obsidian is master
- **Single artifact, all agents.** Claude Code, CEO factory, Coder, Validator, Researcher, Obsidian-native AI, future Madi-phone capture — all read from the same 209 markdown files. No drift, no divergence.
- **Karpathy LLM Wiki thesis.** The model learns through the artifact, not through weights. Every action mutates the shared state. The vault IS the evolving brain.
- **Physically fail-closed.** If the symlink breaks, the next command that tries to write outside fails loudly instead of silently creating a parallel reality.
- **Madi can read, edit, search it.** Obsidian on Mac + phone via sync. Every commit is reviewable. Nothing is opaque.
- **Zero cost to read.** On-disk markdown. No API calls. No rate limits.
- **Survives Claude Code session death.** Everything persisted, nothing in volatile chat memory.

## See also
- [[AMENDMENT-003-memory-sync|AMD-003]]
- [[LAW-001-evolution|LAW-001]]
- [[LAW-013-truth|LAW-013]]
- [[LESSON-060-plugin-hallucination-root-cause|LESSON-060]] — the hallucination that motivated stronger enforcement
- [[AUDIT-024-physical-enforcement-of-law5|AUDIT-024]] — the 2026-04-08 implementation audit with verification commands
- [[session-20260408-0020-law5-physical-enforcement|SESSION-20260408-0020]] — overnight autonomous session digest
- [[MEMORY]] — the symlinked auto-memory file that this law protects
