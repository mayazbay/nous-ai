---
type: concept
id: CONCEPT-VAULT-MODEL
title: "Vault model decision — two vaults, hub-and-spoke"
tags: [concept, architecture, obsidian, karpathy, decision]
date: 2026-04-07
related: [AUDIT-016, AUDIT-017, AUDIT-018, CLAUDE.md]
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Vault Model Decision — Two Vaults, Hub-and-Spoke

## Question (from Madi)
> Is it everything in one vault, or is every single thing in a different vault? If it's my second brain, that has to be like the main thing, the core of everything — like me — but it connects to different projects. Is that the correct way of thinking?

## Answer
**Yes and no.** The intuition of "me at the center, everything connects" is correct. The mistake is conflating "connected" with "in the same vault."

### Karpathy's actual recommendation
One knowledge base per **domain** — not one per life, not one per project.

### Three options considered
1. **ONE big vault for everything** — fails at scale (>400 pages index breaks), leaks private data into business context, confuses LLM on entity identity.
2. **Multi-vault per topic** (family / health / business / ai-agents / …) — entities drift across vaults, cross-vault wikilinks don't work in Obsidian, you have to remember which vault to open.
3. **TWO vaults with hub-and-spoke INSIDE each** ← chosen.

### The chosen model (2026-04-07)
Two vaults, strict privacy separation:

| Vault | Domain | Path (Mac) | Backup (VPS) |
|-------|--------|------------|--------------|
| Nous wiki | Business / product / Satory VKO / factory | `~/Documents/Projects/Nous AGaaS/Nous/` | `/root/nous-agaas/wiki/` (live) |
| Brain | Personal life (everything that isn't Nous) | `~/Documents/Brain/` | `/root/brain.git` (bare backup) |

Inside each vault: topic subfolders under `pages/`, all cross-linked via ```wikilinks```. Madi is the implicit hub in the Brain vault (every personal subfolder ultimately connects to him). Nous wiki has its own hub (the Satory VKO product).

### Why two, not one
- **Privacy / legal.** Nous wiki may be audited, subpoenaed, shown to investors, or partially shared with Spectra ITS. Personal life data must never be `grep`-able from that context.
- **Retention.** Business records have legal retention requirements. Personal notes don't.
- **Audience.** Factory agents (CEO / Coder / Validator) write to the Nous wiki. Only Madi + Claude Code write to Brain.
- **Entity identity.** "Madi" in Nous wiki = CEO of Nous Ltd. "Madi" in Brain = person. Different contexts, correctly separated.

### Why two, not seven (one per topic)
- Entities drift across vaults (Smatay appears in Family + Business, updates go stale).
- Cross-vault wikilinks don't work in Obsidian natively.
- Cognitive overhead of remembering which vault to open.
- Karpathy's own warning at ~100-400 pages per base is an upper bound; most personal life-brains stay well under that even with all topics merged.

### Hub-and-spoke concretely
```
~/Documents/Brain/
├── CLAUDE.md           (schema, vault identity check)
├── index.md            (master catalog, categorized)
├── log.md              (append-only chronological)
├── raw/                (immutable sources: X archive, AI conversations, notes, books)
└── pages/
    ├── family/         (Smatay, siblings, kids — private)
    ├── health/         (sleep, gym, diet, medical)
    ├── learning/       (books, courses, frameworks)
    ├── projects/       (personal side-projects, NOT Nous)
    ├── people/         (friends, mentors — NOT business contacts)
    └── concepts/       (mental models, frameworks)
```

Everything in `pages/family/smatay.md` can link to `pages/health/sleep-routine.md` via ``sleep-routine``. They're all in ONE vault. The implicit hub is Madi himself — not a literal `madi.md` file, but the fact that every subfolder ultimately relates to him.

### What NOT to do
- ❌ Do not create `pages/business/` inside Brain with Spectra ITS notes — that belongs in Nous wiki.
- ❌ Do not create `pages/family/` inside Nous wiki — that belongs in Brain.
- ❌ Do not symlink between vaults.
- ❌ Do not put Nous credentials or sensitive business data in Brain.
- ❌ Do not create a third vault for "AI agents" or "YouTube" or any other topic — it goes as a subfolder inside the vault it naturally belongs to.

### How Claude knows which vault it's in
Both `CLAUDE.md` files now carry a **Vault identity check** block at the top. When Claude Code starts a session, the first file it reads is CLAUDE.md, and the first thing CLAUDE.md says is "you are in Vault X, the OTHER vault is Y, never mix them."

### Related
- [[AUDIT-016-brain-cli-evaluation]] — why we rejected the Node brain CLI + multi-vault approach
- [[AUDIT-017-brain-cli-adoption-complete]] — scaffolded the Brain vault on Mac
- [[AUDIT-018-sync-and-lint-bulletproof]] — bidirectional git sync + vault identity markers
- Karpathy LLM Wiki pattern (original gist)
