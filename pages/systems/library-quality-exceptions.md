---
type: system
id: LIBRARY-QUALITY-EXCEPTIONS
title: "Library quality exceptions"
status: active
date: 2026-04-30
tags: [library-quality, obsidian, gbrain, openclaw, exceptions]
related: [AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30, gbrain-ops, audit]
---

# Library quality exceptions

These are intentionally lower-strictness library classes for `tools/library_quality_scan.py`.
They are still indexed by gbrain, but they are not treated like Tier A operating doctrine.

## Pattern Exceptions

- pattern: `pages/sources/*.md` — reason: external/source captures; title quality varies by source; owner: substrate; review: 2026-07-31.
- pattern: `pages/sources/*/*.md` — reason: external/source captures; title quality varies by source; owner: substrate; review: 2026-07-31.
- pattern: `pages/sources/*/*/*.md` — reason: external/source captures; title quality varies by source; owner: substrate; review: 2026-07-31.
- pattern: `pages/skills/_gbrain/*.md` — reason: upstream gbrain skillpack docs mirror runtime capability, not Nous-authored doctrine; owner: substrate; review: 2026-07-31.
- pattern: `pages/skills/_gbrain/*/*.md` — reason: upstream gbrain skillpack docs mirror runtime capability, not Nous-authored doctrine; owner: substrate; review: 2026-07-31.
- pattern: `pages/concepts/*source*/*.md` — reason: source/reference captures are preserved close to source; owner: substrate; review: 2026-07-31.
- pattern: `pages/concepts/*upstream*/*.md` — reason: upstream/reference captures are preserved close to source; owner: substrate; review: 2026-07-31.
- pattern: `pages/progress/claude-memory/*.md` — reason: runtime memory/archive substrate, not canonical library pages; owner: substrate; review: 2026-07-31.
- pattern: `pages/progress/claude-memory/*/*.md` — reason: runtime memory/archive substrate, not canonical library pages; owner: substrate; review: 2026-07-31.
- pattern: `pages/task-results/*.md` — reason: machine-generated task receipts; retrieval value is timestamp/source, not polished title; owner: substrate; review: 2026-07-31.
- pattern: `pages/progress/commit-review-*.md` — reason: generated commit-review stream; daily grouping makes duplicate/missing titles acceptable; owner: substrate; review: 2026-07-31.
- pattern:  — reason: machine-generated skill extracts from task-results; source quality varies by origin task; owner: substrate; review: 2026-07-31.
- pattern: `pages/skills/extracted/*.md` — reason: machine-generated skill extracts from task-results; source quality varies by origin task; owner: substrate; review: 2026-07-31.
