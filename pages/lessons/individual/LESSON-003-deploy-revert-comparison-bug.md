---
type: lesson
id: LESSON-003
title: "Deploy revert comparison bug"
tags: [lesson, factory]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: archived-no-absorption-needed
---

# LESSON-003: Deploy revert comparison bug

## LESSON-003 (2026-04-06): Deploy revert comparison bug
- Old code: compare post-merge failures against branch test results (WRONG)
- New code: compare against baseline_failures captured at cycle start (CORRECT)
- Line 289 in graph.py: `if post.get("failed",0) > len(state.get("baseline_failures", set()))`
- This caused ALL overnight merges to revert

## See also
- [[AMENDMENT-002-post-deploy-check|AMD-002]]
- [[LAW-012-golden-deploy|LAW-012]]
