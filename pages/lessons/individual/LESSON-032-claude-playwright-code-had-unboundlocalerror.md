---
type: lesson
id: LESSON-032
title: "Claude Playwright code had UnboundLocalError"
tags: [lesson, factory]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: absorbed
absorbed_into: agent-quality
absorbed_at: 2026-04-17
---

# LESSON-032: Claude Playwright code had UnboundLocalError

## LESSON-032 (2026-04-06): Claude Playwright code had UnboundLocalError
Claude added Playwright check to deploy_node but failed_checks variable used before defined.
Deploy_node crashed on EVERY deploy — ALL golden deploy checks skipped.
Broken code went live because the safety gate itself was broken.
ROOT CAUSE: Claude added code without running it once. LAW-004 violation. THIRD TIME.
FIX: Initialize failed_checks=[] before Playwright block.
IRONY: The amendment designed to prevent broken deploys was itself broken.

## See also
- [[LAW-004-5-commandments|LAW-004]]
