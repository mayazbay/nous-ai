---
type: dashboard
id: DASH-ACTIVE-BLOCKERS
title: "Active blockers — все нерешённые"
tags: [dashboard, blockers, dataview]
date: 2026-04-07
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Active Blockers (live)

Все нерешённые блокеры из всех проектов и progress-страниц. Обновляется автоматически когда ты редактируешь любую страницу.

## All open tasks across the wiki

```dataview
TASK
FROM "pages"
WHERE !completed
GROUP BY file.link
SORT file.mtime DESC
```

## Recent progress pages (last 30 days)

```dataview
TABLE date as "Date", file.mtime as "Modified"
FROM "pages/progress"
SORT file.mtime DESC
LIMIT 20
```

## Open project items

```dataview
TABLE status, owner, date
FROM "pages/projects"
WHERE status != "complete" AND status != "done"
SORT date DESC
```

## See also
- [[index]]
- [[CLAUDE]]
