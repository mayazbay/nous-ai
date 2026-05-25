---
type: lesson
id: LESSON-013
title: "Factory revert loop overwrites manual deploys"
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

# LESSON-013: Factory revert loop overwrites manual deploys

## LESSON-013 (2026-04-06): Factory revert loop overwrites manual deploys
- Claude deployed frontend manually with transforms
- Factory was still running and deployed its own version, REVERTING Claude changes
- Bundle hash changed from Claude deploy to factory deploy
- ROOT CAUSE: Factory was not stopped before manual work
- RULE: ALWAYS stop factory (systemctl stop nous-agaas) before doing manual frontend work
- RULE: After manual deploy, verify bundle hash matches YOUR build, not factory build

## See also
- [[AMENDMENT-002-post-deploy-check|AMD-002]]
- [[LAW-012-golden-deploy|LAW-012]]
