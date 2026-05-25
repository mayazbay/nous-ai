---
type: spec
id: RUNBOOK-WEBSITE-RESTORE
title: "Runbook — restore the satory.nousagaas.com amazing design from any broken state"
tags: [runbook, spec, website, vercel, rollback, alias, satory, emergency, p0, law-013]
date: 2026-04-09
source_count: 0
status: reviewed
last_updated: 2026-04-09
priority: p0
related: [HANDOFF-2026-04-08-NIGHT, LESSON-068-rollback-first-when-source-tree-unknown, LESSON-067-next-build-passes-doesnt-mean-runtime-works, LESSON-065-wrong-project-detour, LAW-013-truth]
---

# Runbook — restore `satory.nousagaas.com` from any broken state

> **Read this when**: the website at `https://satory.nousagaas.com` shows the wrong design, "Filler block" placeholder text, "Нет данных" cards, "Satory Portal Redesign" in the title bar, or any state that does NOT match Madi's "amazing design" (sidebar with Обзор/Камеры/Нарушения/ЕРАП Конвейер/Карта/Состояние, 242 buildings, 156/243 cameras, floor plans, real API data from `api.nousagaas.com`).

## 🔄 2026-04-09 EVENING UPDATE — URL routing added, new primary target

The amazing design was **rebuilt with React Router** on 2026-04-09 evening so that **every page now has its own URL** (responding to Madi's complaint: "every single page that I click is just a visual change, but the website doesn't change"). The rebuild lives in a different Vercel project (`satory-stitch`, same team as the old `satory-nextjs`), and the custom domain alias was moved to it.

**Current production target (as of 2026-04-09 ~23:30 Almaty):**

| Field | Value |
|---|---|
| Deploy ID | `dpl_GMPGr9z7z27Naqo7oZCFxMDLSVt3` |
| Short URL | `satory-stitch-8yjoui0yj-mayazbay-4383s-projects.vercel.app` |
| Vercel project | `satory-stitch` (`prj_4qRRxkhEGUp16WnJ7GcEzWAxjmPA`) |
| Source | `/Users/madia/Desktop/nous ai/satory-stitch/` (buildable; `.vercel/project.json` linked) |
| Bundle (Vercel-built) | `/assets/index-GGnwid2t.js` + `/assets/index-Dn78pLzl.css` |
| Framework | Vite 6 + React 19 + React Router v6.30 (BrowserRouter / Routes / Route) |
| Routes | `/`, `/cameras`, `/tracking`, `/violations`, `/erap`, `/map`, `/archive`, `/status`, `/settings`, `/help` |
| SPA fallback | `vercel.json` rewrites `/(.*)` → `/index.html` (unchanged) |
| API proxy | `vercel.json` rewrites `/api/proxy/(.*)` → `https://api.nousagaas.com/api/$1` (unchanged) |

**NEW one-line fix** (use this first if the website shows wrong content now):

```bash
npx vercel alias set satory-stitch-8yjoui0yj-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
```

If you get an npm cache EACCES error on `~/.npm/_cacache`, prepend `NPM_CONFIG_CACHE=/tmp/npm-cache-satory` to the command — the root-owned cache directories from an old npm bug break `npx vercel@latest` fresh installs until `sudo chown -R 501:20 ~/.npm` is run.

**Fallback** — if the new routing deploy breaks for any reason, the old known-good pre-routing amazing design is still reachable:

```bash
npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
```

The old `g2grt4mi8` deploy is preserved in the `satory-nextjs` Vercel project — this just moves the alias back. The ORIGINAL one-line fix section below still works as this second-level fallback.

**Verification after either command** (same as the original section): read the HTML body, check the bundle hash (new fingerprint is `index-GGnwid2t.js` for the routing build, `index-BSiWURaO.js` for the pre-routing fallback), curl `/api/proxy/health` and expect `{"status":"ok","total_events":154516,...}`.

See [[HANDOFF-2026-04-09-EVENING-website-routing]] for the full evening session bridge, [[LESSON-071-rebuild-half-done-source-via-fingerprint-and-archive-harvest]] for the rebuild recipe, and [[AUDIT-031-1c-hallucination-root-cause-2026-04-09]] for the adjacent hallucination root cause (unrelated to the website, but same session).

---

## The one-line fix (copy-paste safe) — ORIGINAL Apr 7 fallback

```bash
npx vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
```

That's it. Takes ~4 seconds. Requires an authenticated Vercel CLI session on the `mayazbay-4383s-projects` team scope (run `vercel whoami` to check — should return `mayazbay-4383`).

## What this command does

- Reassigns the custom domain alias `satory.nousagaas.com` to deploy `dpl_6FZjfKY3sVwRXcdRGFrKdcCBYrpH` (URL alias `g2grt4mi8`)
- That deploy is the Vite/React build created **Tue Apr 07 2026 14:29:05 Kazakhstan Time** — the canonical "amazing design"
- Fingerprint of this deploy (for identification if the deploy ID ever needs to be re-verified):
  - Bundle: **Vite/React**, single `/assets/index-*.js` script (~1.16 MB)
  - Title: `SATORY VKO — Система видеонаблюдения`
  - HTML shell: `<div id="root">` (NOT `<div id="__next">` — this is NOT Next.js)
  - JS bundle contains: `floor`×81, `242`×8, `156`×5, `243`×1, `Камер`×23, `Обзор`×5, `Нарушения`×5, `Алтай`×1, `Риддер`×1, `proxy/cameras`×7, `proxy/violations`×6, `proxy/erap`×3, `proxy/stats`×1, `api.nousagaas`×1, `building`×1
  - Backend rewrite: `/api/proxy/*` → `https://api.nousagaas.com/api/*` (spectra-dashboard)

## Verification — always read the body, never trust HTTP 200

After running the alias command, verify by reading the HTML body:

```bash
curl -s -L https://satory.nousagaas.com/ -o /tmp/satory_check.html
echo "=== title ==="
grep -oE '<title[^>]*>[^<]+</title>' /tmp/satory_check.html
echo "=== Vite asset reference (should be 2+) ==="
grep -c 'index-BSiWURaO\|index-vah-lEGi\|/assets/' /tmp/satory_check.html
echo "=== should be ZERO ==="
grep -c 'Filler block\|Satory Portal Redesign' /tmp/satory_check.html
echo "=== backend proxy live? ==="
curl -s -L -o /tmp/stats.json -w 'HTTP %{http_code}\n' https://satory.nousagaas.com/api/proxy/stats
head -c 150 /tmp/stats.json
```

Expected output when correctly restored:

```
=== title ===
<title>SATORY VKO — Система видеонаблюдения</title>
=== Vite asset reference (should be 2+) ===
2
=== should be ZERO ===
0
=== backend proxy live? ===
HTTP 200
{"hourly": [{"hour": "00", "count": 1881}, {"hour": "01", "count": 3186}, ...
```

If any of those don't match, the fix didn't take effect (or the alias got swapped again) — go to the troubleshooting section below.

## Why `vercel rollback` is NOT the command to use

`vercel rollback <deploy-url>` is documented as "quickly revert back to a previous deployment" but **it only updates the Vercel project's default production subdomain** (`satory-nextjs.vercel.app`). It does NOT automatically move custom domain aliases (`satory.nousagaas.com`).

In the 2026-04-08 night → 04-09 incident, a prior Claude session ran:

```bash
npx vercel rollback https://satory-nextjs-o61g1mbsx-mayazbay-4383s-projects.vercel.app --yes
```

and got a `Success! satory-nextjs was rolled back to o61g1mbsx` message. That was TRUE — the project's internal production pointer moved. But the actual URL Madi uses (`satory.nousagaas.com`) stayed on the broken `2hbi0hr7k` deploy because the custom domain alias is a SEPARATE binding that `rollback` does not touch.

**Always use `vercel alias set` when fixing a custom domain. Never trust `vercel rollback` for a production custom domain.** See [[LESSON-068-rollback-first-when-source-tree-unknown]] and [[LESSON-069-vercel-rollback-doesnt-move-custom-domains]].

## Known deploy IDs (2026-04-09 snapshot)

| Deploy ID | Alias URL | Created | Build Type | Status |
|---|---|---|---|---|
| `dpl_6FZjfKY3sVwRXcdRGFrKdcCBYrpH` | `g2grt4mi8` | 2026-04-07 14:29 | **Vite/React** | ✅ **THE AMAZING DESIGN** — current production target |
| `dpl_3WRMCgN7727p4hb5tjdNkayFc2ou` | `pilreczl1` | 2026-04-07 12:25 | Vite/React (probably) | Candidate fallback — earlier same-day build |
| `dpl_HASDnyCjygnJMAvSb3sXMowYVcY7` | `gp6p9656x` | 2026-04-07 12:34 | Vite/React (probably) | Candidate fallback |
| `dpl_BbG4AuiJuL1joVpnLcreLz9YfjTH` | `owiibuh2e` | 2026-04-07 05:06 | Vite/React (probably) | Earliest same-day candidate |
| `dpl_5d2BkSPRX1AGbax3C1eZW7xKHmNQ` | `o61g1mbsx` | 2026-04-08 12:42 | Next.js | ❌ Not the amazing design — loading-screen SPA. Do NOT alias here. |
| `dpl_HtYCEtUL3zNt199G3Nx8SJtcmfbS` | `a00k9gunl` | 2026-04-08 17:12 | Next.js (preview) | Camera-fix preview — never verified visually. |
| `dpl_8MhtMru9fbLctJX8q2n9wLVWXQAJ` | `2hbi0hr7k` | 2026-04-08 18:42 | Next.js | ❌❌❌ **THE BROKEN ONE** — "Filler block", "Satory Portal Redesign" title, `/dashboard` 404. **DO NOT ALIAS HERE EVER.** |

## Fallback sequence (if `g2grt4mi8` ever fails)

If `g2grt4mi8` stops serving correctly (Vercel deletes it, the deploy errors out, whatever), fall back in this order:

```bash
# Try #2
npx vercel alias set satory-nextjs-pilreczl1-mayazbay-4383s-projects.vercel.app satory.nousagaas.com

# Try #3
npx vercel alias set satory-nextjs-gp6p9656x-mayazbay-4383s-projects.vercel.app satory.nousagaas.com

# Try #4
npx vercel alias set satory-nextjs-owiibuh2e-mayazbay-4383s-projects.vercel.app satory.nousagaas.com
```

After each, re-run the verification commands above. Stop at the first one whose HTML body shows Vite assets + the `SATORY VKO` title + the JS bundle markers.

## Permanent deletion commands (one-shot cleanup)

When Madi is ready to permanently wipe the archived mess, these are the commands. **These are destructive and irreversible** — Madi must run them personally; Claude sessions are prohibited from permanent deletions even with explicit permission.

### Step 1 — nuke the archived local directories

```bash
# Verify the archive exists and contains only what you expect
ls -la ~/Desktop/ARCHIVED-satory-next-js-messes-2026-04-09/

# Expected contents:
#   satory-nextjs/        (Next.js port, Apr 9 00:15)
#   satory-portal/        (duplicated-file Next.js mess, Apr 8 14:24)
#   satory-live/          (Next.js port with cameras-p.json data, Apr 6 12:22)
#   satory-v0-original/   (v0.app Next.js template, Mar 30)
#   satory-nextjs-export.zip  (85KB Apr 3 backup)
#   NEW-satory-nousagaas-com-dashboard-2026-04-08.png  (screenshot of broken state)

# If the contents match, nuke it
rm -rf ~/Desktop/ARCHIVED-satory-next-js-messes-2026-04-09/
```

### Step 2 — remove the broken Vercel deploys

```bash
# These ARE the broken Next.js deploys from Apr 8. Removing them frees the Vercel
# project slot of confusion. The amazing design g2grt4mi8 (Apr 7) stays untouched.

cd ~/Documents/Projects/Nous\ AGaaS  # or any directory with vercel CLI auth

npx vercel remove dpl_8MhtMru9fbLctJX8q2n9wLVWXQAJ --yes   # the broken one
npx vercel remove dpl_HtYCEtUL3zNt199G3Nx8SJtcmfbS --yes   # camera-fix preview
npx vercel remove dpl_5d2BkSPRX1AGbax3C1eZW7xKHmNQ --yes   # the Next.js morning deploy
```

### Step 3 — verify the amazing design is still serving

```bash
curl -s -L https://satory.nousagaas.com/ | grep -oE '<title[^>]*>[^<]+</title>'
# Expected: <title>SATORY VKO — Система видеонаблюдения</title>

curl -s -L -o /tmp/stats.json -w 'HTTP %{http_code}\n' https://satory.nousagaas.com/api/proxy/stats
head -c 150 /tmp/stats.json
# Expected: HTTP 200 + {"hourly":[{"hour":"00","count":1881},...]}
```

**IMPORTANT: if step 3 fails after step 2 (i.e., the amazing design is gone), run the fallback sequence from earlier in this runbook to re-alias to `pilreczl1`/`gp6p9656x`/`owiibuh2e`.**

## Troubleshooting

### "vercel alias set" returns "not authorized"

Run `vercel login` first. The CLI should be authenticated as `mayazbay-4383`.

### The alias set succeeds but the site still shows the broken design

This can happen for 30-60 seconds due to Vercel edge cache. Hard-refresh your browser (⌘+Shift+R on Mac) and try again. If still broken after 2 minutes:

```bash
# Check what the alias ACTUALLY points to right now
npx vercel alias ls 2>&1 | grep 'satory.nousagaas.com'
```

If it shows the broken deploy, your `alias set` command failed silently. Re-run.

### The site is completely down (HTTP 5xx)

```bash
# Check all the deploy URLs' raw status
for u in g2grt4mi8 pilreczl1 gp6p9656x owiibuh2e; do
  echo "=== $u ==="
  curl -s -I "https://satory-nextjs-${u}-mayazbay-4383s-projects.vercel.app/" | head -3
done
```

If any of them return 401, that's Vercel Authentication — the deploys are private behind login. Only the `satory.nousagaas.com` alias is public. The fix is to `alias set` the alias to a deploy that the team has access to (all 4 above).

### The `g2grt4mi8` deploy has been deleted from Vercel history

Look for the next-oldest Vite/React build via `npx vercel ls satory-nextjs` and `npx vercel inspect <url>`. The fingerprint to match:

- Bundle outputs include `/assets/index-*.js` (Vite pattern)
- No `api/proxy/cameras` or other lambdas (Vite is SPA-only, no serverless routes)
- Build duration ~9-11 seconds (Vite is fast)

If no Vite/React builds remain in Vercel history, the only recovery is to rebuild from source. See the section below.

## Rebuilding from source (last resort)

**The Vite/React source tree for the amazing design is NOT on Madi's Mac as of 2026-04-09.** It's not in `~/Desktop/`, not in `~/Documents/`, not in any git repo I've found. It might be:

- In Google Drive (if Madi built it with Google/Gemini in a web session)
- In a deleted v0.app project
- Extractable from the Vercel build artifacts (complex, may not be complete)
- Extractable from the deployed JS bundle via a code-to-JSX tool (partial recovery, styling lost)

If all deploys are gone AND the source is unrecoverable, the amazing design is lost and we'd need to reconstruct it from:
1. The screenshot at `~/Desktop/ARCHIVED-satory-next-js-messes-2026-04-09/NEW-satory-nousagaas-com-dashboard-2026-04-08.png` (shows the **BROKEN** state — still useful as a sidebar-layout reference for a rebuild)
2. Madi's memory of what the amazing design looked like
3. The JS bundle contents (fetch from `g2grt4mi8.vercel.app/assets/index-BSiWURaO.js` while it's still live and reverse-engineer)

**Action item for a future session**: download the JS bundle + CSS + any assets from the live `g2grt4mi8` deploy into `~/Desktop/satory-amazing-design-vite-bundle-2026-04-09/` as a backup. One command:

```bash
mkdir -p ~/Desktop/satory-amazing-design-vite-bundle-2026-04-09
cd ~/Desktop/satory-amazing-design-vite-bundle-2026-04-09
curl -s -O https://satory.nousagaas.com/assets/index-BSiWURaO.js
curl -s -O https://satory.nousagaas.com/assets/index-vah-lEGi.css
curl -s https://satory.nousagaas.com/ > index.html
echo "Backup captured $(date)" > README.txt
```

This doesn't recover the source but it preserves the deployed artifacts if Vercel ever deletes the deploy.

## Open forensic question (not blocking)

**Who/what kept deploying Next.js builds over the Vite amazing design?** The Vercel project `satory-nextjs` has NO git integration (`vercel git ls` → no connection). All deploys came from CLI invocations against the project. Multiple Next.js deploys happened over Apr 8 (12:42, 17:12, 18:42) from an unknown source tree. Possibilities:

1. Another Claude Code session in parallel (autonomous afternoon run, per [[HANDOFF-2026-04-08-EOD]])
2. Madi himself from a different terminal / machine
3. A v0.app auto-deploy trigger
4. A scheduled task or cron
5. The fired session `f71aaefd` attempting to "fix" camera-path-c per LESSON-067

Resolving this prevents recurrence. Ask Madi next time he's calm.

## See also
- [[LESSON-068-rollback-first-when-source-tree-unknown]] — the rollback discipline lesson that prompted the first fix attempt
- [[LESSON-069-vercel-rollback-doesnt-move-custom-domains]] — the technical gotcha that made the first fix attempt silently fail
- [[LESSON-067-next-build-passes-doesnt-mean-runtime-works]] — the Camera Path C deploy that the fired session was trying to fix
- [[LESSON-065-wrong-project-detour]] — the earlier "wrong local directory" lesson
- [[HANDOFF-2026-04-08-NIGHT]] — the session handoff documenting the crisis + resolution
- [[camera-path-c-staging-2026-04-08]] — the staging spec (now OUTDATED since `~/Desktop/satory-nextjs` is archived)
- [[AUDIT-028-bulletproof-post-fda-and-physical-enforcement-gaps]] — `additionalDirectories` whitelist (needs Desktop/satory-nextjs REMOVED since archived)
- [[LAW-013-truth]] — honest failure disclosure
