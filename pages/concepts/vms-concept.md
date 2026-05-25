---
type: concept
id: CONCEPT-VMS
title: "VMS — Video Management System"
tags: [concept, vms, cerebro, replacement, core]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# VMS — Video Management System

The core system we are building to replace Cerebro. Manages cameras, video streams, events, violations, and analytics.

## What it must do (89 requirements)
- Camera management: add/edit/delete, health monitoring, 100K+ cameras
- Video: live streams, 30-day recording, playback, H.264/H.265
- Events: detection, search, notifications, audit trail
- Analytics: vehicle recognition, plate reading, speed detection
- Map: camera locations, traffic density, clustering
- Users: roles, permissions, audit trail, Russian/Kazakh interface

## Current state
- 6 features fully done (8%)
- 28 partially done (19%)
- 117 missing (77%)
- 48 P0 blockers

## See also
- [[cameras|Camera Network]]
- [[cerebro_bdl_vms_requirements|VMS Requirements]]
