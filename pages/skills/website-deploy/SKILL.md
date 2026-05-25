---
tier: 3
type: skill
name: website-deploy
version: 1.6.0
description: Rules for any work touching satory.nousagaas.com — the Satory VKO surveillance portal. The website is LOCKED to deploy g2grt4mi8. All future work must read and lint root DESIGN.md, prove the local source tree matches the live bundle, then edit or deploy only through the gated workflow. Covers design-contract lint, pre-flight check, source-of-truth proof, deploy workflow, rollback, and verification.
triggers:
  - any work on satory.nousagaas.com
  - any mention of Vercel, deploy, frontend, satory-nextjs
  - deploying or rolling back the website
  - building or editing any frontend component for Satory
  - generating Satory or Nous UI
  - DESIGN.md
  - design system
  - verifying website is working
tools: [Bash, Read, Grep]
mutating: true
absorbs_lessons: [LESSON-008, LESSON-009, LESSON-010, LESSON-013, LESSON-041, LESSON-053, LESSON-065, LESSON-067, LESSON-068, LESSON-069, LESSON-071, LESSON-072, LESSON-073, LESSON-075, LESSON-076]
absorbs_laws: [LAW-012, LAW-016, AMENDMENT-002]
title: "website-deploy v1.6.0"
---

# website-deploy v1.6.0

## Purpose

The Satory VKO website broke 7+ times across sessions because the wiki had knowledge but no enforcement. This skill is the enforcement mechanism — mandatory pre-flight, safe deploy sequence, verified rollback.

**THE ONE RULE:** `satory.nousagaas.com` = `g2grt4mi8` FOREVER. This is non-negotiable.

## Contract

**Inputs:** A request to change, deploy, test, or rollback the Satory website.

**Outputs:** Production website unchanged (or improved) with all pages working. Never regressed.

**Invariants:**
- Root `DESIGN.md` is read and linted BEFORE any Satory/Nous UI generation or frontend edit
- Pre-flight check runs BEFORE any website work
- Local source tree is fingerprint-matched to the live bundle BEFORE any edit or deploy
- Every deploy is verified by BROWSER test, not curl
- Rollback is always ready before promoting to production
- `satory.nousagaas.com` always points to `satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app`
- Factory is stopped before any manual deploy

## Phases

### Phase 0 — Pre-flight check (MANDATORY — run before ANY website work)

```bash
# Design contract gate: run from the wiki/repo root.
python3 tools/check_design_contract.py

# Official DESIGN.md spec lint. Use temp npm cache because ~/.npm may contain
# root-owned cache files from older npm runs.
NPM_CONFIG_CACHE=/tmp/nous-npm-cache npx -y @google/design.md lint DESIGN.md
```

Both commands must return zero errors before any UI generation, source edit, preview deploy, production deploy, or design-system extraction. Warnings from the official linter are not cosmetic; fix them unless a documented upstream false-positive exists.

```bash
# Is the locked version still live?
CURRENT_JS=$(curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1)
if [ "$CURRENT_JS" = "index-BSiWURaO.js" ]; then
    echo "LOCKED VERSION LIVE — safe to proceed"
else
    echo "WRONG VERSION LIVE: $CURRENT_JS — RESTORE NOW with:"
    echo "npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com"
fi
```

If the check fails, RESTORE FIRST, then investigate why it changed. Never proceed on a wrong version.

If the request includes editing website source, also prove the local tree matches the live bundle before changing files. Do not trust directory names.

```bash
# Live bundle markers
BUNDLE=$(curl -s "https://satory.nousagaas.com/" | grep -o '/assets/index-[^"]*\.js' | head -1)
curl -s "https://satory.nousagaas.com$BUNDLE" | grep -E "api/proxy/login|Вход в систему|admin@satory.kz" -n

# Local tree markers (run from the candidate source tree)
rg -n "api/proxy/login|Вход в систему|admin@satory.kz|index-BSiWURaO|index-Bj622IkA" .
```

Expected: the local tree contains the same real-auth markers as the live bundle and does not contain stale fake-login markers. If the markers disagree, stop before editing and reconstruct or identify the real source tree first. Source drift is a production risk even when the live website is healthy.

### Phase 1 — Development

1. Work in `~/Desktop/satory-nextjs/` or a temporary directory OUTSIDE the Obsidian vault.
2. Never create a `code/satory/` or similar directory in the vault — it becomes a trap for future sessions.
3. Any new API endpoint integration: create `transforms.ts` with explicit field mapping. API field names differ from frontend types. (AP-8)
4. Any new components: wire into router/App.tsx and add nav entry. A component nobody can navigate to is NOT done. (AP-9)
5. Any 3rd-party library: use dynamic import inside `useEffect` for heavy libs (hls.js, charting, etc.) to avoid SSR/hydration failures. (AP-3)

### Phase 2 — Local testing

```bash
# Build check (TypeScript + static analysis)
npm run build

# Local smoke test
npm run dev
# Open http://localhost:3000 in REAL BROWSER with DevTools → Console
# Navigate: Dashboard → Cameras → Violations → Map
# Check: no red console errors, real data loading, no "Filler block"
```

`npm run build` passing does NOT mean the app works in the browser. (AP-3)

### Phase 3 — Deploy to preview (NOT production first)

```bash
# Note current production deploy ID for instant rollback
CURRENT_PROD_URL="satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app"

# Deploy to preview (omit --prod)
cd ~/Desktop/satory-nextjs
npx vercel

# Visit the preview URL in a REAL BROWSER
# Test: login → dashboard → cameras → every feature you changed
# Only if ALL work: promote to production
```

### Phase 4 — Promote to production

```bash
# STOP the factory first if it's running (AP-6)
# ssh air 'launchctl stop com.nous.telegram-poll'  # only if factory does auto-deploys

# Promote using alias set (NOT vercel rollback)
npx vercel alias set <your-preview-url> satory.nousagaas.com

# Verify immediately
CURRENT_JS=$(curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1)
echo "Live JS: $CURRENT_JS"
```

### Phase 5 — Verify production

```bash
# Check 1: asset fingerprint
curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1
# Expected: your new fingerprint

# Check 2: API proxy works (not just 200 — check real data)
curl -s "https://satory.nousagaas.com/api/proxy/stats" | python3 -m json.tool | head -20
# Expected: real JSON with camera counts, NOT HTML/404

# Check 3: Open in REAL BROWSER (not curl)
# Navigate to satory.nousagaas.com → login → check dashboard shows real numbers
```

### Phase 6 — Rollback (if anything broken)

```bash
# RESTORE LOCKED VERSION immediately:
npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com

# Verify:
curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1
# Expected: index-BSiWURaO.js
```

## Anti-Patterns

### AP-1 — satory.nousagaas.com is LOCKED to g2grt4mi8 FOREVER
**LESSON-073. CEO direct order.** This version has real backend auth, Cerebro/BDL features, full sidebar. Seven sessions broke the site rebuilding from scratch. Do NOT rebuild from scratch. Do NOT alias to any other deploy. Only build INTO the `satory-nextjs` codebase.

```bash
# ❌ NEVER
npx vercel alias set any-other-deploy.vercel.app satory.nousagaas.com

# ✅ ALWAYS keep or build on top of g2grt4mi8
# Locked deploy: satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app
# Asset fingerprint: index-BSiWURaO.js
```

Restore command:
```bash
npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
```

### AP-2 — Don't use `vercel rollback` for custom domain fixes
**LESSON-069.** `vercel rollback` only moves the `<project>.vercel.app` subdomain. The custom domain `satory.nousagaas.com` stays on whatever it was aliased to. This caused a 6-hour damage window because the rollback appeared to succeed (Vercel said "success") but the custom domain was untouched.

```bash
# ❌ WRONG — doesn't move custom domain
npx vercel rollback <deploy-url> --yes

# ✅ RIGHT — explicitly moves custom domain alias
npx vercel alias set <deploy-url> satory.nousagaas.com
```

After any alias set: verify with `curl -s https://satory.nousagaas.com/ | grep 'index-'`. Do NOT trust Vercel CLI's success message alone.

### AP-3 — next build passing ≠ runtime works
**LESSON-067.** `next build` catches TypeScript + static analysis errors. It does NOT catch:
- Client-side hydration failures
- Runtime type errors (`undefined.foo`)
- UMD/ESM default-export mismatches (e.g. `hls.js`)
- Errors inside `useEffect`

Always run `npm run dev` and open in a REAL BROWSER with DevTools → Console open. If there are red errors, fix before deploying.

Heavy 3rd-party libs (hls.js, chart libs, etc.) must use dynamic import in `useEffect`:
```tsx
useEffect(() => {
  (async () => {
    const mod = await import('hls.js');
    const Hls = mod.default;
    // use Hls...
  })();
}, []);
```

### AP-4 — HTTP 200 is not enough — verify CONTENT
**LESSON-010.** A broken SPA returns HTTP 200 with a skeleton HTML and zero real data — `curl -I` looks fine. Verify content:

```bash
# Check JS bundle fingerprint
curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1

# Check API proxy returns real JSON (not 404 or HTML redirect)
curl -s "https://satory.nousagaas.com/api/proxy/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d.get('total_cameras', 'MISSING'))"

# Check for placeholder/fake content
curl -s "https://satory.nousagaas.com/" | grep -c "Filler block"  # expect 0
```

### AP-5 — Vercel deploys use uploaded source, not local dist
**LESSON-008.** `vercel --prod` uploads source files and rebuilds on Vercel's servers. Local `dist/` is in `.gitignore` — Vercel never sees it. If transforms or API calls are missing from the deployed bundle, the file wasn't uploaded or the import path is wrong.

Verify the deployed bundle contains your changes:
```bash
BUNDLE=$(curl -s "https://satory.nousagaas.com/" | grep -o '/assets/index-[^"]*\.js' | head -1)
curl -s "https://satory.nousagaas.com$BUNDLE" | grep -c "your_function_name"
# Expected: > 0
```

### AP-6 — Stop the factory before manual deploys
**LESSON-013.** If any automated process is still running (factory, watchdog, cron), it may deploy its own version and overwrite your manual deploy within 60 seconds. Before any manual deploy:

```bash
ssh air 'launchctl list | grep factory'  # check if any factory jobs are running
# If auto-deploy jobs exist, disable them before manual work:
# ssh air 'launchctl stop <job-name>'
```

After manual deploy, verify the bundle hash matches YOUR build:
```bash
curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1
# Compare to your local build's output: ls ~/Desktop/satory-nextjs/.vercel/output/static/assets/
```

### AP-7 — Never deploy without browser test first
**LESSON-075, LESSON-076.** The only valid test for a website is: open a REAL BROWSER, log in, navigate every page, check DevTools Console for red errors. curl tests pass because curl doesn't render React or follow the same cookie/redirect chain.

Deploy checklist — ALL required before `vercel alias set satory.nousagaas.com`:
- [ ] `npm run build` passes
- [ ] `npm run dev` → open in browser → no console errors
- [ ] Navigate: Dashboard, Cameras, Violations, Map
- [ ] Real data visible (not "Данные недоступны" everywhere)
- [ ] `vercel` (preview URL, not --prod)
- [ ] Open preview URL in browser and repeat above
- [ ] Only now: `vercel alias set <preview-url> satory.nousagaas.com`

### AP-8 — API field names ≠ frontend types — always transform
**LESSON-009.** The backend API may return `camera_ip`, `camera_type`, `location`, `server_city`. The frontend may expect `id`, `type`, `address`, `zone`. Never assume they match. Create an explicit `transforms.ts`:

```typescript
// transforms.ts
export function transformCamera(raw: ApiCamera): Camera {
  return {
    id: raw.camera_id,
    type: raw.camera_type,
    address: raw.location,
    zone: raw.server_city,
    // ... explicit mapping of every field
  };
}
```

Test the transform output against component expectations BEFORE deploying.

### AP-9 — Components must be wired into router
**LESSON-041.** A component file committed and deployed is NOT done. It is dead code until it is:
1. Imported in `App.tsx` (or the app router)
2. Given a route entry
3. Reachable from a nav element

Before marking any UI task done, verify:
```bash
grep -n "ComponentName" src/App.tsx  # expect import + route entry
```

### AP-10 — Rollback first when source tree is unknown
**LESSON-068.** When you find a broken production deploy and don't know what codebase built it, do NOT spend time hunting source files. Rollback first, investigate second.

```bash
# List recent deploys
npx vercel ls satory-nextjs

# Find the last known-good deploy (before the breakage)
# Roll back via alias set (NOT vercel rollback):
npx vercel alias set <last-known-good-url> satory.nousagaas.com
```

The source tree question can wait. Restoring production cannot.

### AP-11 — API adapter bypass causes black screen
**LESSON-072.** If the frontend bypasses the API adapter (calls raw API directly instead of via the proxy/adapter layer), cookie/auth headers may be wrong, CORS may fail, and React gets back error objects instead of arrays. `undefined.filter()` crashes = black screen.

The adapter layer (`/api/proxy/*`) exists to handle auth, CORS, and data transformation. Never bypass it.

## Output Format

After any website deploy:
1. Asset fingerprint of live site (from curl)
2. API proxy response (first 50 chars of real JSON)
3. Screenshot or browser confirmation (if available)
4. Pre-flight check output

## Files

| File | Role |
|------|------|
| `~/Desktop/satory-nextjs/` | Canonical working copy (NOT in vault) |
| `satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app` | Locked production deploy |
| `index-BSiWURaO.js` | Locked asset fingerprint |


### AP-12 — Run all golden-deploy gates before any production push (LAW-012)

**LAW-012.** No code reaches production unless ALL gates pass IN ORDER:

1. **Pre-merge pytest baseline** — capture current test count before any changes
2. **Code merged to main** — never deploy from a feature branch
3. **Post-merge pytest** — zero new failures vs baseline (regression = rollback)
4. **`npm run build` succeeds** — exit code 0, no TypeScript errors
5. **Vercel deploy completes** — `vercel --prod` exits 0, deployment URL returned
6. **Smoke test passes:**
   - HTTP 200 from `https://satory.nousagaas.com/`
   - Response body > 500 bytes (not an error page)
   - At least one real camera IP visible in `/api/cameras` response
7. **30-minute canary** — monitor error rates before declaring done

**Rollback on ANY failure:**
```bash
npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
```

### AP-13 — TSC baseline creep is the deploy gate working correctly (LESSON-053)

**LESSON-053.** REQ-005 (map marker clustering) deploy was blocked by `tsc --noEmit`: baseline 61 type errors, post-change count 63 → +2 new errors → CYCLE failed. Task marked `failed`, ~$2 of LLM spend without a deploy. This is a SUCCESS of the deploy gate, not a failure — untyped `react-leaflet-markercluster` would have shipped to production and introduced a silent regression.

**Rule:** TSC baseline creep is non-negotiable. A failed CYCLE for +N type errors is the expected outcome, not a bug to work around. NEVER:
- Lower the baseline to unblock a deploy ("just set baseline=63")
- Add `@ts-ignore` or `@ts-expect-error` to silence the new errors
- Use `any` to cast around the untyped library API
- Disable the TSC gate for "this one urgent fix"

**Correct responses when TSC gate blocks:**
1. Fix the types at the source (write proper declarations, fork `@types/*`, contribute upstream).
2. Wrap the untyped library in a narrow, typed adapter (`lib/map-clusters.ts`) so only the adapter imports the untyped module.
3. If neither is possible in scope, REJECT the requirement and document the decision (not every feature is worth shipping untyped).

**Baseline update rule:** the baseline is auto-updated ONLY when the error count goes DOWN. A human-approved baseline bump (up) requires a PR comment justifying the exception — never silent.

**Detection:** `npx tsc --noEmit 2>&1 | grep "error TS" | wc -l` before and after any branch that touches a 3rd-party library, especially `leaflet`, `d3`, and anything with `@types/*` listed as "DefinitelyTyped maintainer absent" in GitHub issues.

### AP-14 — Source tree names are not proof; fingerprint-match before editing
**Session 2026-04-26 website audit.** The locked production site was healthy on `index-BSiWURaO.js`, but the obvious local tree `codebase/satory-frontend` did not match the live bundle: local `src/components/Login.tsx` still had fake-login `admin@satory.kz` markers and local `dist/` had `index-Bj622IkA.js`, while the live bundle used real `/api/proxy/login` auth and matched historical `work/Login.tsx` markers. A stale source tree can pass as "the website code" and cause the next agent to rebuild or deploy the wrong product.

**Rule:** before editing, deploying, or asking a worker to touch the Satory website, prove the candidate source tree is the one that built the locked live bundle.

```bash
# 1. Protected production must still be live.
curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1
# Expected: index-BSiWURaO.js

# 2. Compare live bundle markers to candidate source markers.
BUNDLE=$(curl -s "https://satory.nousagaas.com/" | grep -o '/assets/index-[^"]*\.js' | head -1)
curl -s "https://satory.nousagaas.com$BUNDLE" | grep -E "api/proxy/login|admin@satory.kz|Вход в систему" -n
rg -n "api/proxy/login|admin@satory.kz|Вход в систему" ~/Desktop/satory-nextjs /Users/madia/Documents/Projects/Nous\ AGaaS/codebase 2>/dev/null
```

**Pass condition:** live bundle, local source, and local build artifacts tell the same story. If they disagree, do not edit or deploy. First mark the candidate tree `stale`, reconstruct the canonical source, or create a clean branch whose markers match the locked deploy. This is Musk step 2: delete the false assumption that a directory name proves source ownership.

### AP-15 — UI generation without DESIGN.md is prompt drift

**Session 2026-05-14 design contract gate.** Stitch/AI design-system workflows make `DESIGN.md` the portable contract between humans and agents. Without a repo-level design contract, each UI agent invents palette, density, Russian-copy rules, and proof-link behavior from memory. That recreates the same class of drift that previously broke Satory frontend work: plausible-looking surfaces that are not operator-usable.

**Rule:** before generating, editing, reviewing, or delegating any Satory/Nous UI, read root `DESIGN.md` and run both gates:

```bash
python3 tools/check_design_contract.py
NPM_CONFIG_CACHE=/tmp/nous-npm-cache npx -y @google/design.md lint DESIGN.md
```

If the official linter cannot run because npm/network is down, the local checker is the hard minimum and the npm failure must be surfaced in the handoff. If either gate reports an error, fix the design contract first. Do not proceed from remembered style preferences.

**Local contract additions beyond the open DESIGN.md spec:** Satory operator-facing UI is Russian by default; completed work must expose proof links; nested cards, negative letter spacing, one-note palettes, decorative orbs, and marketing-first operational screens are forbidden; LAW-016 production lock still dominates every design decision.

## Brain-aware invocation (gstack v0.18.0.0, 2026-04-17)

Before any website touch (vercel command, domain alias, component edit, TS baseline change), `mcp__gbrain__search` with the component/env name — the LAW-016 `g2grt4mi8` lock + JS hash `index-BSiWURaO.js` + TSC baseline history are well-documented. Any drift already has a prior AP. Fast keyword search only. After deploy, `mcp__gbrain__add_timeline_entry slug="pages/skills/website-deploy/skill"` with "<component> → <env>: hash <new-hash>". See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

## Rules absorbed from lessons

- **LESSON-008:** Vercel deploys use uploaded source; local dist is invisible. See AP-5.
- **LESSON-009:** API field names ≠ frontend types — always transform explicitly. See AP-8.
- **LESSON-010:** HTTP 200 is not enough — verify content (bundle fingerprint + API JSON). See AP-4.
- **LESSON-013:** Factory revert loop can overwrite manual deploys; stop factory before manual work. See AP-6.
- **LESSON-041:** Components must be imported + routed + reachable; file existence ≠ feature done. See AP-9.
- **LESSON-067:** `next build` passing ≠ runtime works; always browser-test; use dynamic imports for 3rd-party libs. See AP-3.
- **LESSON-068:** Rollback first when source tree unknown; investigate second. See AP-10.
- **LESSON-069:** `vercel rollback` does NOT move custom domain aliases; always use `vercel alias set`. See AP-2.
- **LESSON-071:** Rebuild half-done source via fingerprint + archive harvest if source lost.
- **LESSON-072:** Never bypass API adapter layer — causes auth failures + black screen. See AP-11.
- **LESSON-073:** Website locked to g2grt4mi8 FOREVER. CEO direct order. See AP-1.
- **LESSON-075:** Never deploy without browser test — curl is insufficient for SPA. See AP-7.
- **LESSON-076:** Pre-flight check mandatory before any website work; code/satory/ in vault is a trap. See Phase 0, AP-7.

- **LAW-012:** All 7 golden-deploy gates must pass before production. Rollback on any failure. See AP-12.
- **LAW-016 (website lock):** satory.nousagaas.com MUST point to g2grt4mi8 FOREVER. Preflight check always. See AP-1.
- **AMENDMENT-002 (Post-Deploy Check):** Every deploy must pass all 7 gates before going live. Already enforced by AP-12 (golden deploy gate). This amendment is the formal codification.

- **LESSON-065:** Before editing any frontend code, verify which Vercel project+directory is the actual deploy source using `vercel inspect`. Multiple forks may exist with similar names; only one is live. See Phase 0.
- **LESSON-068 (expanded):** When production is broken and source tree is unknown, rollback to last known-good deploy BEFORE investigating what went wrong. Restoring production cannot wait; source questions can. See AP-10.
- **LESSON-072 (expanded):** All components must use the shared API adapter (`lib/api.ts`); never define local `const fetcher` bypassing the adapter layer. Wrap the entire app in ErrorBoundary so crashes show a retry page, never a black screen. See AP-11.

## Timeline

- 2026-05-14 | v1.6.0 — Added the canonical root `DESIGN.md` gate for Satory/Nous UI generation. Future agents must read and lint `DESIGN.md` with `python3 tools/check_design_contract.py` plus the official `@google/design.md` linter before UI generation, source edits, or deploy work. No new LESSON (RULE ZERO).
- 2026-04-17 | v1.3.0 — Session 36: absorbed LESSON-053 (TSC baseline creep, AP-13). TSC baseline block is the gate working correctly; never lower baseline, @ts-ignore, or any-cast to unblock. No new LESSON files (RULE ZERO).
- 2026-04-15 | v1.0.0 — created in Wave 3 migration; absorbed LESSON-008, 009, 010, 013, 041, 067, 068, 069, 071, 072, 073, 075, 076. The website lock (LESSON-073) is also enforced in CLAUDE.md Rule #2.

- 2026-04-15 | v1.1.0 — Wave 4: added AP-12 (golden deploy gate LAW-012). absorbs_laws: [LAW-012, LAW-016, AMENDMENT-002].

- 2026-04-16 | v1.2.0 — Absorbed LESSON-065 (verify deploy source before editing), LESSON-068 (rollback before source-hunt), LESSON-072 (shared API adapter + ErrorBoundary). Evidence: bulk lesson absorption session.
- 2026-04-16 | v1.2.1 — Absorbed AMENDMENT-002 (post-deploy check, already covered by AP-12). Session 32 orphan absorption.
- 2026-04-17 | v1.4.0 — Session 37: added Brain-aware invocation (gstack v0.18.0.0 adoption). Every vercel/domain/component touch must search gbrain for LAW-016 history + TSC baseline history before acting, and save outcome as timeline entry. No new LESSON (RULE ZERO).
- 2026-04-26 | v1.5.0 — Website audit: added AP-14 source-tree fingerprint proof. Live `index-BSiWURaO.js` was healthy, but local `codebase/satory-frontend` had fake-login/dist-marker drift; future website edits must prove source ownership before touching code.
## See also

- [[LESSON-073-website-locked-never-replace-g2grt4mi8]] — the CEO lock order
- [[LESSON-069-vercel-rollback-doesnt-move-custom-domains]] — the vercel alias set rule
- [[LESSON-076-recurring-website-deployment-failures]] — root cause of 7 repeat failures
- [[LESSON-067-next-build-passes-doesnt-mean-runtime-works]] — browser testing required
- `skills/agent-quality/SKILL.md` — AP-2 (done = browser visible, not deployed)
- `skills/_gbrain/RESOLVER.md` — skill dispatcher
