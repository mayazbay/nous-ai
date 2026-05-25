---
type: alias
target: skills/camera-management/skill
id: lesson-046-mrgn-ip-mismatch
title: "LESSON-046 (alias) — camera_registry MRGN ids vs vehicle_events IPs, no mapping"
tags: [alias, lesson-migration, rule-zero, camera-management, data-integrity]
date: 2026-04-30
status: alias-redirect
related:
  - "[[camera-management]]"
---

# LESSON-046 (alias) — MRGN/IP mismatch in camera registry

> **Migrated per RULE ZERO** — this LESSON was absorbed into
> [[camera-management]] skill. Alias preserves historical link resolution for
> handoffs that referenced the legacy LESSON-046 file.

**Original takeaway:** `camera_registry` keys cameras by MRGN ids while
`vehicle_events` keys by IP — no mapping table, so cross-system joins
silently produced wrong counts and wrong attribution.

**Source skill:** [[camera-management]] (camera-data integrity doctrine)

## See also
- [[camera-management]]
