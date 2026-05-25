---
type: dashboard
id: DASH-RECENT-LESSONS
title: "Lessons learned — последние 30"
tags: [dashboard, lessons, dataview]
date: 2026-04-07
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Recent Lessons (last 30)

```dataview
TABLE title, date, enforcement, file.mtime as "Modified"
FROM "pages/lessons/individual"
SORT date DESC
LIMIT 30
```

## Lessons by enforcement type

```dataview
TABLE length(rows) as "Count"
FROM "pages/lessons/individual"
GROUP BY enforcement
SORT length(rows) DESC
```

## See also
- [[index]]
