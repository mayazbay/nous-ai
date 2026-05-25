---
type: lesson
id: LESSON-014
title: "Command palette was initialized to open"
enforcement: awareness
tags: [lesson, factory]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: archived-no-absorption-needed
---

# LESSON-014: Command palette was initialized to open

## LESSON-014 (2026-04-06): Command palette was initialized to open
- App.tsx had: useState(() => localStorage.getItem("satory_auth") === "true")
- This made command palette auto-open on every page load when authenticated
- Blocked all page views — user could not see any content
- FIX: useState(false) — palette starts closed, opens only on Cmd+K
- ROOT CAUSE: Google AI Studio design used this for demo. Not appropriate for production.

## See also
- [[COMPILED-KNOWLEDGE|Compiled Knowledge]]
- [[PERMANENT-RULES|RULES]]
