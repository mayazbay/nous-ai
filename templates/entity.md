---
type: entity
id: ENTITY-<% tp.file.title.toUpperCase().replace(/ /g, '-') %>
title: "<% tp.file.title %>"
tags: [entity]
date: <% tp.date.now("YYYY-MM-DD") %>
source_count: 0
status: draft
last_updated: <% tp.date.now("YYYY-MM-DD") %>
related: []
---

# <% tp.file.title %>

_(Compiled truth — rewrite this section when evidence changes. Current state only.)_

**Role:** _(person/company, position, relevance to Satory/Nous/Spectra)_

**Contact:**
- Email:
- Phone:
- Address:

**Key facts:**
- _(fact with [[source]])_

---

## Timeline

_(Append-only — never rewrite entries. Newest at bottom.)_

- **<% tp.date.now("YYYY-MM-DD") %>** | Page created

## See also
- [[index]]
