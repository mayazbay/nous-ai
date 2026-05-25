---
type: spec
id: SPEC-PHASE-3-BDL-REPLACEMENT
title: "Phase 3 BDL replacement — REQ-090 through REQ-105 so the factory doesn't idle on restart"
date: 2026-04-08
tags: [spec, phase-3, bdl-replacement, erap, req, factory, task-queue, reqs]
source_count: 1
status: reviewed
last_updated: 2026-04-08
priority: p0
related: [bdl-replacement-state-2026-04-07, AUDIT-029-three-vpns-reconciled-camera-nit-firewall, shep-client-registration-2026-04-08, camera-path-c-staging-2026-04-08, LAW-006-task-equals-requirement, erap_requirements]
---

# Phase 3 BDL replacement spec — REQ-090 through REQ-105

## Why this spec exists

Factory task DB (`/root/nous-agaas/logs/task_queue.db`) has **0 pending tasks, 63 total** as of 2026-04-08 ~17:25 Almaty. All 63 are `[failed]`, `[done]`, or `[blocked]`. **When Madi restarts the factory after topping up Anthropic credit, it will idle immediately** — exactly the looping/wasting-tokens behavior Madi wants to avoid.

This spec defines the Phase 3 BDL-replacement REQs so CEO can read the wiki on first cycle, convert them into `pending` tasks, and feed Coder a real pipeline.

**Critical scope constraint**: the current `graph.py` Coder prompt (lines 555-560) writes ONLY to `satory-frontend/src/...` paths. It does NOT handle backend work. Phase 3 REQs in this spec are **frontend-first** so they're executable by the existing factory without a second worker. Backend REQs (mediamtx install, StrongSwan, SOAP client) are listed separately as **human+Claude Code manual tasks**, NOT factory tasks.

## Business tag convention (from LAW-011)

- `[demo]` — visible in the demo site at `satory.nousagaas.com`. Investor/partnership value.
- `[risk]` — reduces a known failure mode (hallucination, crash, data loss).
- `[ops]` — operational hygiene (config, cleanup, monitoring).
- `[cost]` — reduces Anthropic/infra spend.

## Phase 3 REQ list (factory-executable — frontend only)

### REQ-090 [demo] Error boundary wrapping LivePlayer for LESSON-067 resilience

**What:** Add a React Error Boundary around the `<LivePlayer />` instance in `Cameras.tsx`. If the HLS player ever fails to mount (hls.js load error, autoplay rejection, anything), the boundary catches it and renders a graceful fallback instead of crashing the whole SPA.

**Why:** LESSON-067 just bit us today — a crash in LivePlayer brought down the entire `satory.nousagaas.com` site. An error boundary would have limited the blast radius to the camera drawer video area, keeping the rest of the page working.

**Where:** `satory-frontend/src/components/Cameras.tsx` detail drawer area, wrap the `<LivePlayer>` JSX in a new `<LivePlayerErrorBoundary>` class component (new file `satory-frontend/src/components/LivePlayerErrorBoundary.tsx`).

**Acceptance criteria:**
- [ ] New file `src/components/LivePlayerErrorBoundary.tsx` exports a class component that implements `componentDidCatch(error, info)` + `getDerivedStateFromError(error)`.
- [ ] Fallback UI: static placeholder image or a simple "Видео недоступно" message in the same aspect-video container.
- [ ] Cameras.tsx detail drawer uses `<LivePlayerErrorBoundary><LivePlayer src={...} /></LivePlayerErrorBoundary>`.
- [ ] TypeScript compiles clean.
- [ ] Manual test: intentionally break the LivePlayer import, rebuild, verify only the camera drawer shows the fallback while the rest of the page still renders.

**Estimate:** 30 minutes factory time.

### REQ-091 [demo] Lazy HLS previews on camera grid cards (top 6, not all 243)

**What:** Enhance the grid view in `Cameras.tsx` so the **first 6 visible camera cards** auto-play a small HLS preview (same Mux demo stream for now, swap to per-camera URLs when mediamtx lands). Keep cards 7-243 as static placeholders. Use IntersectionObserver to start/stop video based on viewport visibility.

**Why:** Madi's repeated ask: "I want to see live cameras." Currently only the detail drawer has live video. Adding a 6-card live preview gives investors immediate "real live system" feedback on landing.

**Constraint:** 243 simultaneous HLS players would crash any browser. 6 is empirically safe (60 fps × 6 = ~40 MB/s decode budget on modern Macs). Use IntersectionObserver to cap concurrency.

**Acceptance criteria:**
- [ ] Only the first 6 cards in the filtered camera list have a `<LivePlayer>` replacing the picsum.photos placeholder.
- [ ] Cards 7+ keep the static image as before.
- [ ] IntersectionObserver pauses video when the card scrolls out of view.
- [ ] Each card's video has its own "LIVE" badge and "Демо-поток" disclaimer.
- [ ] Bundle size increase < 50 KB gzipped beyond what REQ-090 already added.

**Estimate:** 1-2 hours factory time. Risk: medium (needs careful lifecycle).

### REQ-092 [risk] Replace picsum.photos entirely with local SVG placeholder

**What:** The camera grid currently uses `https://picsum.photos/seed/${cam.id}/400/225` for thumbnails. This is an external dependency — if picsum.photos goes down, the grid shows broken image icons. Replace with a locally-served SVG placeholder (e.g., a camera icon with the camera ID overlaid).

**Why:** LAW-013 (truth): we don't control picsum.photos. A broken external image looks like a broken app to investors. Local SVG is zero-dependency + reliable.

**Acceptance criteria:**
- [ ] New file `satory-frontend/src/assets/camera-placeholder.svg` — a simple monochrome camera icon (feather-icons style).
- [ ] All references to `picsum.photos` in Cameras.tsx replaced with the local SVG.
- [ ] SVG is inlined via the `?react` suffix or `import svgUrl from './foo.svg'` pattern.
- [ ] `grep -r picsum satory-frontend/src` returns empty.

**Estimate:** 30 minutes factory time.

### REQ-093 [demo] Camera status heart-health indicator in Header

**What:** Add a small "156 / 243 cameras online" indicator to the Header component that pulses green when >70% cameras are online, yellow 30-70%, red <30%. Data from `/api/proxy/cameras` (already fetched via SWR).

**Why:** Provides at-a-glance system health to anyone on the page. Investor demo value.

**Acceptance criteria:**
- [ ] New sub-component in `satory-frontend/src/components/layout/Header.tsx`: `<CameraHealthIndicator />`.
- [ ] Uses existing SWR cache for `/api/proxy/cameras` (don't create a new fetcher).
- [ ] Pulsing dot + count + percentage.
- [ ] Color threshold: green >70%, yellow 30-70%, red <30%.

**Estimate:** 45 minutes factory time.

### REQ-094 [ops] Camera filter: "with live feed" vs "without"

**What:** Add a new filter button in Cameras.tsx filter bar: "С видео" (With video) / "Без видео" (Without video). The "with video" filter shows only cameras we've successfully fetched an HLS manifest for (per REQ-091's lazy preview results).

**Why:** Once mediamtx + real RTSP sources are wired (REQ-101 infra), Madi + Asyl will want to quickly find which cameras are streaming vs which are metadata-only.

**Acceptance criteria:**
- [ ] New filter button in the existing filter bar.
- [ ] Tracks per-camera HLS availability in component state (map of cam.id → 'pending' | 'available' | 'failed').
- [ ] Updates on every successful or failed HLS manifest load event.
- [ ] Filter click applies the boolean filter and shows the count.

**Estimate:** 1 hour factory time. Dependency: REQ-091 must ship first.

### REQ-095 [risk] Violations page SWR key collision fix (LESSON-016 regression check)

**What:** Audit `satory-frontend/src/components/Violations.tsx` for SWR cache key collisions per [[LESSON-016-swr-cache-collision-critical]]. Verify every `useSWR` call uses a unique key prefix matching the fetcher's path.

**Why:** LESSON-016 was a critical bug (cache collision caused wrong data to appear). Regression-proof it by adding a test or audit comment in every Violations-adjacent component.

**Acceptance criteria:**
- [ ] Every useSWR call in Violations.tsx has a comment naming the intended cache scope.
- [ ] No two useSWR calls share the same bare key like `/api/proxy/violations` — must be `/api/proxy/violations?filter=all` or similar scoped.
- [ ] Reference LESSON-016 in a file-level header comment.

**Estimate:** 30 minutes factory time.

### REQ-096 [demo] ERAP pipeline status badge in Dashboard stats card

**What:** Add a small ERAP pipeline status indicator to Dashboard.tsx's stats cards — shows the number of violations currently pending submission, average time in queue, and last successful submission timestamp. Data: extend `/api/proxy/erap` with these fields.

**Why:** Satory leadership wants to see "the pipeline is alive" at a glance on the dashboard. Currently Dashboard shows static counts only.

**Acceptance criteria:**
- [ ] New `<ERAPPipelineStatus />` sub-component in Dashboard.
- [ ] Fetches from `/api/proxy/erap/stats` (new endpoint — BACKEND dep, blocked on SOAP client REQ-101).
- [ ] Falls back to "API not available" honestly if the endpoint 404s.
- [ ] Uses same glow styling as existing stat cards.

**Estimate:** 1 hour factory time. **BLOCKED** on `/api/proxy/erap/stats` endpoint (see manual REQ-101).

### REQ-097 [ops] Sidebar: auto-collapse on < 1024px width

**What:** `satory-frontend/src/components/layout/Sidebar.tsx` currently has a manual `collapsed` toggle. Add `window.matchMedia('(max-width: 1024px)').matches` detection to auto-collapse on narrow viewports.

**Why:** Investors show the site on laptops + tablets. Auto-collapse prevents the sidebar from dominating the viewport on small screens.

**Acceptance criteria:**
- [ ] On window resize event, if width < 1024px, `setCollapsed(true)`.
- [ ] On width > 1024px, restore previous user choice.
- [ ] localStorage persists user's explicit choice across sessions.

**Estimate:** 30 minutes factory time.

### REQ-098 [ops] CommandPalette indexing for all views

**What:** Audit `satory-frontend/src/components/CommandPalette.tsx` to ensure every view in `ViewType` has a corresponding entry in the command palette. Current: missing `help` view per earlier grep.

**Why:** CommandPalette is Madi's primary keyboard navigation. Missing entries create friction.

**Acceptance criteria:**
- [ ] Every `ViewType` enum value has a palette entry.
- [ ] Each entry has a label, icon, and keyboard shortcut (where available).
- [ ] `Cmd+K` opens palette, typing filters, Enter navigates.

**Estimate:** 30 minutes factory time.

### REQ-099 [demo] Tracking page: show "live location" marker on map

**What:** `Tracking.tsx` currently shows a mock route on a map. Add a pulsing "current location" marker at the most recent camera hit. Use the existing leaflet integration.

**Why:** Demo impact — "see a plate move across the city in real time" is a powerful demo moment.

**Acceptance criteria:**
- [ ] Most recent point in the tracking route has a larger, pulsing marker.
- [ ] Hover shows timestamp + camera ID.
- [ ] Existing route polyline stays intact.

**Estimate:** 1 hour factory time.

### REQ-100 [risk] TypeScript strict mode baseline enforcement test

**What:** Add a git pre-commit hook test (or Coder pre-build check) that runs `tsc --noEmit --strict` and fails if the error count exceeds the baseline recorded in `tests/baseline-tsc.json`. Per [[LESSON-043-tsc-strict-not-checked-183-type-errors-leaked]].

**Why:** LESSON-043 showed 183 TypeScript strict errors leaked because nothing enforced the baseline. This REQ adds the enforcement.

**Acceptance criteria:**
- [ ] New file `satory-frontend/tests/baseline-tsc.json` with current error count.
- [ ] New script `satory-frontend/scripts/check-tsc-baseline.sh` that runs tsc and compares.
- [ ] CI integration (if Madi adds CI later).

**Estimate:** 1 hour factory time.

## Manual tasks (NOT factory, for Claude Code / Madi / Denis directly)

These touch backend infra or human processes — current factory pipeline can't execute them. They're tracked as REQs here so next-session Claude Code can pick them up.

### REQ-101 [demo] Install `mediamtx` on VPS 65.108.215.200 for RTSP → HLS proxy

**Blocked by:** Camera VPN #1 is ESTABLISHED ✅ + MikroTik ACL accept #3 pending (Denis). Once ACL is applied, factory can reach the cameras at `10.235.x.x` / `10.170.x.x` and pull RTSP.

**Plan:**
1. `apt install mediamtx` or download from GitHub releases
2. Configure `/etc/mediamtx.yml` with per-camera RTSP source entries (pulling from the registered 50 configured APK cameras)
3. Expose HLS playlist endpoints at `http://localhost:8888/<cam-id>/index.m3u8`
4. Add nginx reverse proxy at `/hls/<cam-id>/` on `api.nousagaas.com` with CORS headers for browser HLS consumption
5. Test: `curl https://api.nousagaas.com/hls/cam-001/index.m3u8` returns a valid m3u8 playlist
6. Swap the `DEMO_HLS_URL` constant in `LivePlayer.tsx` for per-camera `https://api.nousagaas.com/hls/${cam.id}/index.m3u8`

**Estimate:** 1-2 hours Claude Code time.

### REQ-102 [ops] Install StrongSwan on VPS + configure NIT SmartBridge VPN #2

**Blocked by:** PSK delivery from NIT (via Madi nарочно) after Asyl's form submission.

**Plan:** Per [[source-nit-vpn-tech-conditions-2026-04-08]] and [[shep-client-registration-2026-04-08]] Phase 5. Full StrongSwan `/etc/ipsec.conf` template already in those pages.

**Estimate:** 1-2 hours Claude Code time after PSK arrives.

### REQ-103 [ops] SOAP client for erap_violation_receiver with WS-Security + GOST signature

**Blocked by:** REQ-102 (NIT VPN #2 must be up) + ЭЦП certificate from НУЦ РК (Aidana pipeline, back ~Apr 15) + NDA signing (Daniyar → КПСиСУ).

**Plan:**
1. Use KalkanSigner (already built per master-state apr1)
2. Wrap every SOAP request in WS-Security envelope with XML signature
3. Submit to `erap_violation_receiver` through the tunnel at 195.12.122.44
4. Parse `SCSS001` / `SCSE002` / `SCSE003` response codes (per ЭЦП PDF)
5. Retry on `SCSE003` with exponential backoff

**Estimate:** 4-6 hours Claude Code time (complex crypto + XML).

### REQ-104 [demo] Promote camera-path-c preview to production after Madi's visual verify

**Blocked by:** Madi's visual verification of preview URL https://satory-nextjs-a00k9gunl-mayazbay-4383s-projects.vercel.app (see [[camera-path-c-staging-2026-04-08]]).

**Plan:** `cd ~/Desktop/satory-nextjs && vercel promote dpl_HtYCEtUL3zNt199G3Nx8SJtcmfbS --yes`.

**Estimate:** 1 minute manual.

### REQ-105 [ops] Camera credentials backfill for 59 unconfigured APK cameras

**Blocked by:** Denis (camera DevOps) + possibly BDL access (for pre-existing camera passwords) per [[LESSON-046-mrgn-ip-mismatch]].

**Plan:**
1. Denis provides list of 59 camera IPs currently on factory-default credentials
2. Denis provides the new admin credentials per camera
3. Either Claude Code OR Denis logs in to each camera via the ISAPI API and sets:
   - Custom username/password
   - Timezone → Asia/Almaty
   - NTP sync to a trusted server
   - Event HTTP listener endpoint → our VPS `/api/proxy/isapi/events`
4. Save the credentials in `raw/legal/camera-credentials-YYYY-MM-DD.md` (SENSITIVE marker).

**Estimate:** 2-3 hours of Denis's time; Claude Code can batch-ISAPI-configure if scripted.

## Factory cleanup REQs (manual, but low-risk code edits)

These are the graph.py / systemd cleanups from Madi's next-session priorities. **I've NOT applied them in this autonomous run** because touching graph.py without running the factory to verify is risky — but I've written a detailed fix spec per change. See:

- [[factory-coder-prompt-fix-src-paths-2026-04-08]] — graph.py Coder prompt fix (lines 557, 558, 582)
- [[remove-worker-task-filter-systemd-2026-04-08]] — systemd drop-in cleanup

## Acceptance criteria for the full Phase 3

Phase 3 is "complete" when:
1. Factory (when credits restored) can read this spec via CEO, convert REQ-090 to REQ-100 into pending tasks, execute them autonomously, and not idle.
2. Manual REQs (REQ-101 to REQ-105) are tracked and unblocked as external blockers clear.
3. `satory.nousagaas.com` has visible live camera feeds (from REQ-091 lazy previews + REQ-101 mediamtx).
4. ERAP submission pipeline can sign + submit violations to the test endpoint through VPN #2 (REQ-102 + REQ-103 + ЭЦП cert).

## Process notes

- **How the factory picks this up**: on next cycle start, CEO reads `pages/specs/` looking for pending work. CEO creates atomic tasks via `tools.task_db.create_task(title, desc, priority)` from the REQ entries. CEO's assignment text to Coder references the REQ-xxx tag, which Coder includes in the commit message and the LAW-006 gate verifies.
- **How to add task DB entries manually** (backup in case CEO doesn't pick them up): ssh to VPS → `cd /root/nous-agaas && venv/bin/python3 -c "import sys; sys.path.insert(0,'.'); from tools.task_db import create_task; create_task('[REQ-090] [demo] Error boundary for LivePlayer', 'see pages/specs/phase-3-...md', 2)"`.

## See also
- [[bdl-replacement-state-2026-04-07]] — ongoing BDL replacement state tracker
- [[AUDIT-029-three-vpns-reconciled-camera-nit-firewall]] — what the 3 VPNs unblock
- [[shep-client-registration-2026-04-08]] — ШЭП form values (currently being submitted by Asyl)
- [[camera-path-c-staging-2026-04-08]] — current camera preview deploy state
- [[LAW-006-task-equals-requirement]] — REQ-xxx tag enforcement
- [[LAW-011]] — business tag enforcement
- [[factory-coder-prompt-fix-src-paths-2026-04-08]] — graph.py fix spec
- [[remove-worker-task-filter-systemd-2026-04-08]] — systemd cleanup spec
