---
type: skill
id: gbrain-deals
title: "gbrain-native deals + tender pipeline (CRM-on-substrate)"
version: 1.0.0
tier: 3
tags: [skill, deals, crm, pipeline, tender, satory, p5-1, moonlit-pnueli]
date: 2026-05-23
status: active
source_count: 3
last_updated: 2026-05-23
related:
  - "[[COUNCIL-2026-05-23-business-tooling]]"
  - "[[ceo-hierarchy]]"
  - "[[control-plane-sync]]"
  - "[[todoist-control-plane]]"
---

# gbrain-deals v1.0.0

> **Purpose:** track Nous AGaaS / Spectra / Satory deals and tenders inside the existing AI substrate (Obsidian + gbrain + Telegram + launchd) instead of bolting on an external CRM. One Markdown file per deal at `pages/deals/DEAL-<YYYY-MM-DD>-<slug>.md`, auto-aggregated by `tools/deals_pipeline_view.py`, weekly Russian Telegram digest via `com.nous.pipeline-weekly-digest` Sat 09:00 KZT.
> **Verdict that birthed this skill:** [COUNCIL-2026-05-23-business-tooling](../../audits/COUNCIL-2026-05-23-business-tooling) — Grok-4 winning, $0.14 council cost. Beats Bitrix24 ($300-600/mo, weak substrate integration), Salesforce ($1500+/mo, very high risk), Todoist Pipeline section (partial integration).

## When this skill fires

- New tender drops (goszakup.gov.kz / Russian tender feeds / direct customer ask)
- Existing deal advances or stalls (stage transition)
- Madi asks "what's in the pipeline this week?"
- Sat 09:00 KZT scheduled weekly digest
- Post-mortem on a lost deal (proigран stage transition)

## Anti-Patterns

### AP-1 — Don't fabricate deals
If a deal isn't real (no source email, no Telegram message, no recorded conversation, no published tender), do NOT create a `DEAL-*.md` file. Per `agent-quality` AP-3 (don't show hardcoded or fake data) + Madi's "no fake proof" rule. Source field MUST cite a real artifact.

### AP-2 — Don't invent monetary values
If `value_kzt` is unknown, leave it `0` or blank. Never estimate. The aggregator sorts on real numbers; fake numbers corrupt the pipeline view and waste Madi's attention. Use the body field for "value TBD pending RFP" if needed.

### AP-3 — Russian operator surface is mandatory
All `status` values MUST be the Russian stage labels (`ведущий` / `квалифицированный` / `предложение` / `переговоры` / `выигран` / `проигран`). English aliases are accepted in tooling (`canon_stage()` normalizes) but the on-disk frontmatter uses Russian. Per `todoist-control-plane` v1.8.9 doctrine for Satory team handoff.

### AP-4 — Don't bypass the substrate
Do NOT add Bitrix24 / Salesforce / Slack / Linear as a "supplementary" pipeline tool. The council verdict ([COUNCIL-2026-05-23-business-tooling](../../audits/COUNCIL-2026-05-23-business-tooling)) was explicit: gbrain-native COMPOUNDS the AI factory; external CRM FRACTURES it. Revisit threshold: 5+ active deals >$100k AND a clear gap that the gbrain-native layer cannot close.

### AP-5 — Stale deals must be visible, not hidden
Any deal in an active stage (ведущий/квалифицированный/предложение/переговоры) whose `last_touched` field hasn't moved in >14 days is reported as "stuck" in the accountability table. Stuck deals get a `goal_runner.py` follow-up cycle Mon 09:00 KZT asking Madi 1 question per stuck deal. Don't bury stale deals; surface them loudly per `factory-ops` bad-news-loud pattern.

### AP-6 — Weekly digest is bilingual by audience
Sat 09:00 KZT digest is RUSSIAN (Satory team is Russian-speaking). If Madi wants an English-only digest to his DM separately, add `--lang en` to the plist. Default = Russian to the team chat.

### AP-7 — Lost-deal post-mortem triggers a council
When a deal moves to `проигран`, the next manual or automated cycle should kick off a `multi_model_consult` 3-model post-mortem: "Why did we lose this deal? What would have changed the outcome? What pattern should we encode for next time?" Verdict → audit doc + new AP here or in `factory-ops`. Compounds.

## Current rules (binding)

1. One file per deal at `pages/deals/DEAL-<YYYY-MM-DD>-<slug>.md` using the schema in `pages/deals/_TEMPLATE.md`.
2. Russian stage labels in frontmatter (canonical); English aliases accepted in tooling.
3. `value_kzt` is honest integer or 0. Never invented.
4. `last_touched` MUST be updated on every status/notes/next-action change. The aggregator uses it for stuck-deal detection.
5. `source` MUST cite a real artifact (URL, email msg-id, Telegram msg-id, dated conversation reference).
6. `tools/deals_pipeline_view.py` runs hourly (optional launchd) to regenerate `pages/deals/_index.md` + daily digest. Manual run: `python3 tools/deals_pipeline_view.py`.
7. `com.nous.pipeline-weekly-digest` runs Sat 09:00 KZT, pushes Russian summary via `tg_send.sh`. Must NOT bootstrap until ≥1 real deal exists (otherwise wastes a notification).
8. Lost deals trigger a `multi_model_consult` post-mortem (AP-7).
9. Stuck deals trigger a Mon 09:00 KZT follow-up cycle (AP-5).
10. The gbrain-deals skill, the deals folder, the tool, the plist, and the council audit are all backlinked — `related:` frontmatter on each surfaces the others.

## Implementation surface

- Folder: `pages/deals/` (README + _TEMPLATE + _index + DEAL-*.md)
- Aggregator: `tools/deals_pipeline_view.py`
- Plist (vault-tracked): `tools/launchd/com.nous.pipeline-weekly-digest.plist`
- Council source: `pages/audits/COUNCIL-2026-05-23-business-tooling.md`
- RESOLVER row: `pages/skills/_gbrain/RESOLVER.md` (AGaaS Factory section)
- gbrain indexing: deals are first-class searchable entities via standard vault ingest

## Acceptance criteria (per council verdict)

- [ ] First weekly digest lands Sat 2026-05-30 09:00 KZT covering ≥1 real tracked deal
- [ ] At least one stage transition observed through the substrate before next council
- [ ] Madi's daily pipeline-tracking oversight ≤ 5 min (the whole point)

## Timeline

- **2026-05-23** | v1.0.0 created by Opus per [P5.1 council verdict](../../audits/COUNCIL-2026-05-23-business-tooling). 7 APs codified (no fabrication, no fake values, Russian operator surface, no substrate bypass, stuck-deal visibility, bilingual-by-audience, lost-deal council post-mortem). Implementation: `tools/deals_pipeline_view.py` + `tools/launchd/com.nous.pipeline-weekly-digest.plist` + `pages/deals/` scaffold (README + TEMPLATE + bootstrap _index). Awaits Madi to seed the first real deal before plist bootstrap. No new LESSON (RULE ZERO).
