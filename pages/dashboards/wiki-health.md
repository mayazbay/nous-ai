---
type: dashboard
id: DASH-WIKI-HEALTH
title: "Wiki health — общий обзор"
tags: [dashboard, health, lint, dataview]
date: 2026-04-07
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Wiki Health Dashboard

Updated automatically. Lint runs weekly (Monday) + monthly (1st of month).

## Page counts by type

```dataview
TABLE length(rows) as "Count"
FROM "pages"
WHERE type
GROUP BY type
SORT length(rows) DESC
```

## Latest lint reports

```dataview
TABLE date, file.mtime as "Generated"
FROM "pages/audits"
WHERE type = "lint"
SORT date DESC
LIMIT 5
```

## Pages without "related" frontmatter (potential orphans)

```dataview
LIST
FROM "pages"
WHERE !related
LIMIT 30
```

## See also
- [[index]]
- `tools/wiki_lint.py`
- `tools/raw_hygiene.py`
