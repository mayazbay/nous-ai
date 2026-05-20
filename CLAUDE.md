---
type: schema
id: SCHEMA
title: "Wiki Schema — How This Knowledge Base Works"
tags: [schema, instructions, meta, karpathy, trefethen, god-level]
date: 2026-04-06
source_count: 0
status: reviewed
last_updated: 2026-04-20
related: [AUDIT-023, AUDIT-027, LAW-005, LAW-016, SYS-WIKI-SCHEMA-DETAIL, SYS-ARCHITECTURE-QUICKREF]
---

> **Architecture topology + hard rules:** [[architecture-quickref]] (session-start-shim mirror). **Runtime behavior contract:** [[session-operating-contract]] v1.17.0 (session-108 Rule 22 revenue-precedence; session-69 paste-target pointer; session-64-late Rule 19 authorial-commit; session-56-ext Rule 17 execute-pre-approved; session-55 Rule 15 execute-tactical; session-53 Rule 13 outbound-discipline). **Engineering method (The Book of Elon codified, session 64 + factory-runtime gate session 68):** [[musk-algorithm]] v1.4.0 — The Algorithm 5-steps exact order + Idiot Index + Magic-Wand-Number + Thinking-in-Limits + Factory-is-Product + Attack-the-Constraint + 10%-add-back rule + Bad-News-Loud + Ban-Acronyms + Close-the-RL-Loop + 69 Core Musk Methods + Spec-Kit cognitive-debt guard requiring deletion/replacement before implementation + APs including optimize-before-delete, unsigned-requirement, physically-impossible-violated, agent-autonomy-loop, and spec-without-deletion/replacement. Mechanical detector: `tools/test_musk_step_2.sh`. **Operating doctrine + 6-axis scorecard + multi-virtual-reviewer (Skill-tool-invoked, NOT mental simulation):** [[karpathy-loop]] v1.12.0 — AP-11 makes "skills are the prompts" a runtime gate; AP-5 hard-bans mental simulation for triggering plans; AP-12 adds narrow Council escalation for AP-5 plans with IR/retrieval, novel cost/latency, security/billing isolation, single-ablation evidence, or lock-in risk; `Skill(plan-ceo-review)` / `Skill(plan-devex-review)` / `Skill(plan-design-review)` / `Skill(plan-eng-review)` or `Skill(autoplan)` required on plans >2h / >3 subsystems / >200 lines / new doctrine skill. **Code-behavior 12-rule layer (Karpathy/forrestchang + May-2026 extension):** [[karpathy-coding-principles]] v1.1.0. **Skill-discovery meta-layer (Vercel Labs ecosystem):** [[find-skills]] v1.0.0 — `npx skills find <query>` + skills.sh leaderboard. **Multi-model CEO hierarchy:** [[ceo-hierarchy]] v1.7.0 — `/codex` is the explicit OpenAI Codex CEO path; OpenClaw worker labor defaults to DeepSeek V4 Flash and escalates to guarded routes; `grok-ceo` and `nous` are OpenClaw-hosted agent identities, not OpenClaw itself. **Parallel-session startup (paste-target for non-Mac-CLI sessions):** [[opus-4-7-parallel-startup]] v1.0.0 — pointer-wrapper for claude.ai web / phone /code / API consumers. **Parallel-session coordination:** [[session-coordination]] v1.33.0 — AP-5 cross-session stage-bleed (use `git commit -o <path>` anti-collision pattern when peer sessions active); v1.31 row-tolerant readers; v1.32 strips Mac-hardcoded vault paths from registry scripts so Air-side tests do not hang on unreachable paths; v1.33 generalizes pre-action handshake to every durable substrate write. **Library-grade audit (Obsidian + gbrain + OpenClaw):** [[library-grade-audit]] v1.7.0 — 7-gate falsifiable scorecard (Gate 7.1 AP-7-aware) + 7-class debugging tree + 11 APs. v1.7.0 ships the AP-11 mechanical detector `tools/test_gate_formula_alignment.sh` (parses gate-row jq formulas vs downstream script output schemas; exit 1 on drift with `--strict`; 0/1 drift on first run against openbrain-projection v1.2.0 schema). Triggers: "audit Obsidian + gbrain", "library-grade", "is retrieval working", "brain_score not moving", "extract creates 0 links". Phase-1 fast scorecard runs scanners + doctor JSON in 5 min; Phase-2 walks the debugging tree only if Phase-1 surfaces RED.

# RULE ZERO — Tan / Karpathy / Alex Finn Pattern (DO NOT WRITE NEW LESSON FILES)

**Updated session 35, 2026-04-16. Supersedes the prior "skill + lesson co-commit" rule, which trapped agents into writing LESSON files.**

When you find a bug, fix something, or learn anything worth persisting:

1. **Add the rule to `pages/skills/<skill>/SKILL.md`** (new AP, new phase, or new bullet under "Current rules"). Bump the skill version. Append a one-line entry to that skill's `## Timeline`.
2. **Append a timeline entry to gbrain** for the same skill page:
   ```
   mcp__gbrain__add_timeline_entry  slug="pages/skills/<skill>/skill"  date=YYYY-MM-DD  summary="..."
   ```
3. **Commit only the SKILL.md change.** No LESSON file. The pre-commit hook (`.git/hooks/pre-commit`, replicated on Mac+VPS+Air wikis) PHYSICALLY REJECTS any commit that adds `pages/lessons/individual/LESSON-NNN-*.md`.

**Why no new LESSON files?** Tan/Karpathy/Finn architecture: SKILL.md = doctrine (read at runtime), gbrain timeline = evidence (searchable). A separate LESSON-NNN file decays. Skills compound. Lessons rot.

**Historical LESSON files up to ceiling LESSON-129 are receipts.** Some historical LESSON files have already been deleted/migrated into the skill + gbrain-timeline substrate. Current filesystem count is allowed to be **≤129**; it must never grow by adding new `LESSON-NNN` files.

**Drift gate (also enforced by hook):** any LESSON file you DO edit must have matching `id:` (or `name:`), `title:`, and `# H1`. Hook runs the drift scan from `mistake-to-skill` AP-7 on every staged LESSON modification.

**If you catch yourself about to create any new `LESSON-NNN` file — including LESSON-130 or gap-filling old numbers — STOP.** Update the skill instead. If no existing skill fits, create one and register in `pages/skills/_gbrain/RESOLVER.md`.

---

# MANDATORY SESSION GATE — RUN BEFORE ANY WORK

```bash
# Gate 1: Website lock (LAW-016)
CURRENT_JS=$(curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1)
if [ "$CURRENT_JS" = "index-BSiWURaO.js" ]; then echo "✅ GATE-1: Website locked correctly"; else echo "🔴 GATE-1 FAIL: Website wrong! Run: npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com"; fi

# Gate 2: No code/satory/ trap in vault (LESSON-076)
if [ -d "code/satory" ]; then echo "🔴 GATE-2 FAIL: code/satory/ exists — DELETE IT"; else echo "✅ GATE-2: No code/satory/ trap"; fi

# Gate 3: Vault symlink intact (LAW-005)
SYMLINK=$(readlink "$HOME/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory" 2>/dev/null)
if echo "$SYMLINK" | grep -q "claude-memory"; then echo "✅ GATE-3: Memory symlink intact"; else echo "🔴 GATE-3 FAIL: Memory symlink broken"; fi
```

**If ANY gate 🔴 → STOP and fix BEFORE any work.**

## BRAIN-FIRST RULE

- **Before ANY action** — query GBrain for related context, lessons, past mistakes.
- **After ANY new knowledge** — write it back to the vault. Brain compounds only if you write back.
- **Iron law back-linking** — entity A on page B → page A MUST be discoverable from B. Bidirectional. Always. **Both forms count:** `[[wikilink]]` (machine-readable in Obsidian + gbrain v0.11+) OR prose cross-ref (e.g. `karpathy-loop AP-8`, `gbrain-ops AP-50`) which is human-readable and grep/Obsidian-discoverable. Choose form by audience: prose for skill-body fluency, wikilink for entity/concept/source pages. **Tool-specific blindness is a tooling gap, not a doctrine violation:** gbrain v0.10.1 prose-blindness produces ~696 false-orphan reports — use `ripgrep` + Obsidian backlink panel + gbrain combined for complete view (see [[gbrain-ops]] AP-50). gbrain v0.11+ extractor upgrade tracked under that AP.
- **Every mistake** → SKILL.md update (new AP / phase / rule) + gbrain timeline entry on the skill page. **NEVER a new LESSON-NNN file** (session 35 RULE ZERO; the hook enforces this physically).

## HARD RULES (violations = session termination)

- **NEVER deploy to satory.nousagaas.com** without Madi's explicit approval (LAW-016)
- **NEVER create code/satory/ in the vault** — trap that caused 7 incidents (LESSON-076)
- **NEVER modify police_dashboard.py on VPS** without browser test first (LESSON-075)

---

# Wiki Schema

> **Vault:** `/Users/madia/Documents/Projects/Nous AGaaS/Nous/` (Mac) ↔ `/root/nous-agaas/wiki/` (VPS)
> **Memory symlink:** `~/.claude/...memory/` → `pages/progress/claude-memory/` (LAW-005)
> **Single vault.** No other vault exists.

## Directory Structure

```
wiki/
  CLAUDE.md            # This file — core rules
  index.md             # Content catalog (human + agent navigable)
  log.md               # Append-only chronological record
  MEMORY.md            # Claude Code auto-memory (symlinked)
  laws/                # 15 laws + amendments
  raw/                 # Source documents (immutable, NEVER delete)
  pages/
    entities/          # People and organizations
    concepts/          # Topics, technologies, glossary
    sources/           # Summaries of source documents
    specs/             # Requirements and specifications
    systems/           # Technical system docs + wiki-schema-detail.md
    legal/             # Credentials, compliance
    lessons/individual/# LESSON-NNN-slug.md (LAW-015)
    audits/            # AUDIT-NNN-slug.md
    progress/          # Handoffs + claude-memory/
    projects/          # Active project state
    skills/            # SKILL.md per skill (18 domain skills)
  tools/               # Automation scripts
```

## YAML Frontmatter (required on every page)

```yaml
---
type: [law|lesson|audit|spec|entity|concept|source|progress|compiled|schema|legal|system|project]
id: [unique identifier]
title: "[descriptive title]"
tags: [kebab-case, list]
date: [YYYY-MM-DD, creation date]
source_count: [integer]
status: [draft|reviewed|needs_update|deprecated]
last_updated: [YYYY-MM-DD]
related: [[id-1], [id-2]]
---
```

## Compiled Truth + Timeline Format

Every page: **above `---` = compiled truth** (mutable, current state). **Below `---` = timeline** (append-only, `- **YYYY-MM-DD** | Event [[source]]`).

## Citations

Every factual claim must cite its source: `[[wikilink]]` for vault pages, `[Source: raw/path]` for raw files.

## Cross-References & Contradictions

- Use `[[wikilinks]]` for every mention. Every page ends with `## See also`.
- Mark contradictions: `> **CONTRADICTION:** [old] vs [new]. Resolution: [...]`

## Key Workflows (detail in [[SYS-WIKI-SCHEMA-DETAIL]])

- **Ingest:** raw/pending → pages/sources + update ≥8 related pages + log.md
- **Task done:** log.md + update status + LESSON if error + TaskCompleted 8-gate hook
- **Query:** index.md → qmd search → read pages → synthesize with citations → write back insights
- **Error:** LESSON file → backlinks → log.md → 3× repeat = escalate to law

## Page Formats (detail in [[SYS-WIKI-SCHEMA-DETAIL]])

- **Entity:** role, decisions, See also
- **Skill:** Anti-Patterns (`### AP-N`), Phases, "Rules absorbed" section, Timeline. Bump version on every change. **This is where new rules go** (session 35 RULE ZERO).
- **Lesson (legacy, historical only):** title, root cause, prevention, what next time. **Do NOT create new LESSON files** — pre-commit hook rejects. Existing LESSONs may be edited or deleted only.
- **Audit:** scope, findings, recommendations
- **Source/Spec/Legal:** see [[SYS-WIKI-SCHEMA-DETAIL]]

## See also

- [[SYS-WIKI-SCHEMA-DETAIL]] — full workflows, page templates, lint rules
- [[LAW-005-obsidian-master]] — Obsidian as single source of truth
- [[LAW-015-root-cause-evolution]] — lesson format and root-cause discipline
