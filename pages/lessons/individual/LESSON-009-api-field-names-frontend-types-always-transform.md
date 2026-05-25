---
type: lesson
id: LESSON-009
title: "API field names != frontend types — always transform"
enforcement: awareness
tags: [lesson, factory]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
integrated_into: [website-deploy]
status: implicit-already-in-skill
absorbed_into: [website-deploy]
absorbed_at: 2026-04-16
---

# LESSON-009: API field names / frontend types — always transform

## LESSON-009 (2026-04-06): API field names != frontend types — always transform
- API returns: camera_ip, camera_type, location, server_city
- Frontend expects: id, type, address, zone  
- NEVER assume API matches frontend types
- Create transforms.ts with explicit field mapping
- Test transform output against component expectations BEFORE deploy

## See also
- [[cameras|Camera Network]]
