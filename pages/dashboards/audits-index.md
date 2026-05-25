---
type: dashboard
id: DASH-AUDITS-INDEX
title: "Audits — все аудиты"
tags: [dashboard, audits, dataview]
date: 2026-04-07
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# All audits

```dataview
TABLE title, date, status
FROM "pages/audits"
WHERE type = "audit"
SORT date DESC
```

## Audits by status

```dataview
TABLE length(rows) as "Count"
FROM "pages/audits"
WHERE type = "audit"
GROUP BY status
```

## Recent doctrine + operations (April 2026, hub)

Prose-form back-links to keep these pages reachable until each finds its
topical home — they sit in the Tier-A1 doctrine universe but lack inbound
references from skills/laws/audits.

### Audits
- [[AUDIT-TELEGRAM-CONTROL-PLANE-2026-04-26]] — Telegram control plane audit
- [[AUDIT-057-sovereign-agaas-infra-dgx-spark-2026-04-28]] — Sovereign AGaaS infra DGX Spark eval
- [[AUDIT-054-morning-review-followup-2026-04-28]] — Morning review follow-up
- [[gbrain-weekly-2026-04-20]] — gbrain weekly health audit

### Specs
- [[two-track-erap-strategy-2026-04-16]] — Two-track ERAP strategy
- [[satory-assistant-search-tz-2026-04-29]] — Satory assistant search ТЗ
- [[SPEC-WEEKLY-DESKTOP-CLEANUP-2026-04-09]] — Weekly desktop cleanup spec

### Systems
- [[gstack-upgrade-state-2026-04-28]] — gstack upgrade state
- [[github-automation-state-2026-04-28]] — GitHub automation state

### Plans
- [[2026-04-14-grok-context-injection]] — Grok context injection plan

### Sibling dashboards
- [[satory-revenue-room-2026-04-27]] — Satory revenue room
- [[sources-recent]] — Recent ingested sources
- [[recent-lessons]] — Recent lessons

## See also
- [[index]]
