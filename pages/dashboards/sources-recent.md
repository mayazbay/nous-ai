---
type: dashboard
id: DASH-SOURCES-RECENT
title: "Recent sources — последние ingested"
tags: [dashboard, sources, dataview]
date: 2026-04-07
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Recent ingested sources

```dataview
TABLE title, date, file.mtime as "Modified"
FROM "pages/sources"
SORT date DESC
LIMIT 30
```

## Sources by language

```dataview
TABLE length(rows) as "Count"
FROM "pages/sources"
GROUP BY language
```

## See also
- [[index]]
