---
type: law
id: LAW-016
title: "LAW-016: Website Deployment Lock — Physical Enforcement"
tags: [law, deployment, website, enforcement, satory]
date: 2026-04-10
source_count: 0
status: reviewed
last_updated: 2026-04-10
related: [LESSON-069, LESSON-075, LESSON-076, LAW-005]
---

# LAW-016: Website Deployment Lock — Physical Enforcement

## The Law

**satory.nousagaas.com MUST always point to deployment `satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app` (asset hash: `index-BSiWURaO.js`).**

No Claude session, no agent, no automated process may deploy, alias, or redirect satory.nousagaas.com to any other deployment without EXPLICIT written approval from Madi in the CURRENT conversation.

## Mandatory Pre-Flight Check (run BEFORE any website-related work)

```bash
# MANDATORY: Run this BEFORE touching anything website-related
CURRENT_JS=$(curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1)
echo "Current JS: $CURRENT_JS"
if [ "$CURRENT_JS" = "index-BSiWURaO.js" ]; then
  echo "✅ LOCKED VERSION IS LIVE — DO NOT DEPLOY"
else
  echo "🔴 WRONG VERSION LIVE — RESTORE IMMEDIATELY:"
  echo "npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com"
fi
```

If the check shows ✅, **STOP. Do not deploy.** The website is correct.

## Prohibited Actions

1. **NEVER run `npx vercel deploy` or `npx vercel --prod` for satory.nousagaas.com** without Madi's explicit approval in the current conversation
2. **NEVER run `npx vercel alias set` on satory.nousagaas.com** except to restore the locked version
3. **NEVER create, modify, or deploy from any `code/satory/` directory** — that directory was deleted 2026-04-10 because it caused 4+ incidents of broken deployments
4. **NEVER modify `police_dashboard.py` on the VPS** without testing the full browser flow first — login → verify data loads → navigate between pages

## Restore Command (if broken)

```bash
npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
```

## Root Cause This Law Prevents

Between 2026-04-08 and 2026-04-10, the website was broken and restored **at least 5 times** by different Claude sessions. Each session:
1. Found source code in the vault that didn't match the production build
2. Made "improvements" (auth, MFA, strict endpoints)
3. Deployed without testing the full browser flow
4. Broke the website
5. The next session repeated steps 1-4

The pattern: **sessions treat the vault source code as authoritative, but the production build was made from different source that no longer exists in the vault.** The locked `g2grt4mi8` build is a pre-compiled artifact, not reproducible from any current source directory.

## When Can This Lock Be Lifted?

Only when ALL of these are true:
1. Madi explicitly says "build and deploy a new version"
2. A NEW source directory is created (not in the vault — use a temporary working directory)
3. The new build is tested in a REAL BROWSER (not curl, not assumptions)
4. Full flow verified: login → all pages load → no console errors → data displays correctly
5. Preview URL tested first, then promoted to production
6. The old locked version is recorded as the rollback target

## See also
- [[LESSON-069-vercel-rollback-doesnt-move-custom-domains]]
- [[LESSON-075-never-deploy-without-browser-test]]
- [[LESSON-076-recurring-website-deployment-failures]]
- [[LAW-005-obsidian-master]]
