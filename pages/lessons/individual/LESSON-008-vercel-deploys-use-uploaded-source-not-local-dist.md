---
type: lesson
id: LESSON-008
title: "Vercel deploys use UPLOADED source, not local dist"
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

# LESSON-008: Vercel deploys use uploaded source, not local dist

## LESSON-008 (2026-04-06): Vercel deploys use UPLOADED source, not local dist
- vercel --prod uploads source files and rebuilds on Vercel servers
- Local dist/ is in .gitignore, so Vercel never sees it
- If you need prebuilt deploy: use --prebuilt with .vercel/output/
- BUT prebuilt loses rewrite/proxy support — use normal deploy instead
- VERIFY: after deploy, curl the actual CDN URL and check the JS bundle hash matches
- If transforms are missing from bundle, the file wasnt uploaded or import path is wrong

## See also
- [[AMENDMENT-002-post-deploy-check|AMD-002]]
- [[LAW-012-golden-deploy|LAW-012]]
