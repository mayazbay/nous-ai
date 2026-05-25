---
type: audit
id: AUDIT-<% await tp.user.next_audit_id() %>
title: "<% tp.file.title %>"
tags: [audit]
date: <% tp.date.now("YYYY-MM-DD") %>
source_count: 0
status: in-progress
last_updated: <% tp.date.now("YYYY-MM-DD") %>
related: []
---

# <% tp.file.title %>

_(Compiled truth — rewrite findings when evidence changes.)_

**Scope:** _(What you are auditing and why)_

**Findings:**
1.
2.
3.

**Recommendations:**
- [ ]
- [ ]

---

## Timeline

- **<% tp.date.now("YYYY-MM-DD") %>** | Audit started

## See also
- [[index]]
