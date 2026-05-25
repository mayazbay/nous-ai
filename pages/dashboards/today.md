---
type: dashboard
id: DASH-TODAY
title: "Today — что важно сейчас"
tags: [dashboard, today, dataview]
date: 2026-04-07
last_updated: 2026-04-07
source_count: 1
status: reviewed
---
# Сегодня

## Open tasks (anywhere in wiki)

```dataview
TASK
FROM "pages"
WHERE !completed
LIMIT 20
```

## Modified in last 24 hours

```dataview
TABLE file.mtime as "Modified"
FROM "pages"
WHERE file.mtime > date(today) - dur(1 day)
SORT file.mtime DESC
LIMIT 20
```

## Sources ingested today

```dataview
LIST
FROM "pages/sources"
WHERE date = date(today)
```

## See also
- [[index]]
