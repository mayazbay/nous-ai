---
type: system
id: SYS-WIKI-SCHEMA-DETAIL
title: "Wiki Schema Detail — Workflows, Page Formats, Lint Rules"
tags: [system, schema, wiki, workflows, templates, karpathy, 2026-04-16]
date: 2026-04-16
source_count: 0
status: reviewed
last_updated: 2026-04-16
related: [SCHEMA, AUDIT-023, AUDIT-027, LAW-005, LAW-015]
---

# Wiki Schema Detail

This page contains detailed workflows, page format templates, and lint rules that were previously in CLAUDE.md. Moved here during GOD_PROMPT v1.0 Task 29 to keep CLAUDE.md under 130 lines.

For the core schema rules, see `CLAUDE.md` in the vault root.

## Focus Areas

Every new page must relate to at least one:
1. **Satory VKO / ERAP integration** — cameras, VMS, BDL, violations, ISAPI, SmartBridge/ВШЭП, ЭЦП
2. **Nous AGaaS factory** — agent architecture, budget gates, watchdog, task queues
3. **Spectra ITS government compliance** — OID, ECP certs, NUC RK, tenders
4. **Partner network** — NetLine, Saken aga, Russian white-label, Coram AI
5. **Meta: wiki hygiene + laws** — 15 laws + amendments, Karpathy compliance, audits

## Three Layers

1. **raw/** — immutable source documents. NEVER modified or deleted (LESSON-061). Only `README.md` at top level; all else in subfolders (LESSON-059).
2. **pages/** — LLM-maintained wiki. YAML frontmatter required. Types: law, lesson, audit, spec, entity, concept, source, progress, compiled, schema, legal, system, project.
3. **CLAUDE.md** — schema + critical rules. Read by all agents at session start.

### raw/ Allowed Subfolders
`recordings/`, `meetings/`, `telegram/`, `state-snapshots/`, `documents/`, `images/`, `legal/`, `specs/`, `team/`, `transcripts/`, `pending/`, `processed/`, `unsorted/`, plus dated dump folders.

## Ingest Workflow

1. Source → `raw/pending/` (via Obsidian Sync, capture-courier, telegram_poll, cp/mv)
2. `tools/ingest_pending.py` picks it up
3. Create summary in `pages/sources/` with frontmatter + citations
4. Update `index.md`
5. Update ALL relevant entity/concept/spec/project pages (target: ≥8 pages — "10-15 pages per source" rule from Karpathy)
6. Add `> CONTRADICTION:` callouts where new info disagrees
7. Append to `log.md`
8. Source stays in raw/ permanently
9. Bump `source_count` on updated pages

## Task Completion Workflow

1. Append to `log.md`
2. Update spec `status` frontmatter
3. Update `last_updated` on touched pages
4. Store LESSON if anything went wrong (LAW-015)
5. TaskCompleted hook (8 gates): LAW-006 REQ-xxx, LAW-011 business tag, App.tsx wiring, TSC baseline, LAW-005 vault committed (hard block), Mac↔VPS HEAD compat (hard block), log.md entry (warn), LAW-015 LESSON for bug-fix (hard block)

## Query Workflow

1. Read `index.md` to orient
2. Use `qmd` MCP (BM25 + vector + rerank)
3. Read relevant pages
4. Synthesize with citations
5. Write back insights as wiki pages (Karpathy compounding loop)
6. Cross-check via lex + vec + hyde for high-stakes

## Error Workflow

1. Store LESSON in `pages/lessons/individual/LESSON-NNN-slug.md` (LAW-015 format)
2. Update related pages with backlinks
3. Append to `log.md`
4. 3× repeat → escalate to law/amendment

## Lint Rules

`wiki_lint.py` runs weekly (Mon 04:00) + monthly (1st 04:00) + on-demand.

Severity: 🔴 Error (hard), 🟡 Warning (soft), 🔵 Info (suggestions).

Checks: law files present, YAML frontmatter, orphan pages, broken wikilinks, contradictions, stale claims (>30d), undefined acronyms, missing cross-refs, unattributed claims, raw/ hygiene.

Output: `pages/audits/lint-YYYY-MM-DD.md`

## Page Format Templates

### Entity
```yaml
type: entity, id: entity-name, tags, date, source_count, status, last_updated, related
```
Body: Role, what they do, key decisions, See also.

### Lesson
See [[LAW-015-root-cause-evolution]]: title, root cause, prevention, what to do next time. Path: `pages/lessons/individual/LESSON-NNN-slug.md`.

### Audit
See recent audits for format. Path: `pages/audits/AUDIT-NNN-slug.md`.

### Source
Summary with provenance. Must reference raw/ path. See [[source-ecp-requirements-pdf-2026-04-08]].

### Spec
Uses status track: draft → reviewed → needs_update → deprecated. See [[erap_requirements]].

### Legal / Credentials
Must include `sensitive: true`, rotation policy, access control, leak response.

---

## Timeline

- **2026-04-16** | Created from CLAUDE.md trim (GOD_PROMPT Task 29). Content relocated, not deleted.

## See also

- [[AUDIT-023-karpathy-llm-wiki-compliance-deep-audit]]
- [[AUDIT-027-god-level-alignment-vs-trefethen-mempalace-brain]]
- [[LAW-005-obsidian-master]]
- [[LAW-015-root-cause-evolution]]
