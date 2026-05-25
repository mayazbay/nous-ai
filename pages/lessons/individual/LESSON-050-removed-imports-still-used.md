---
type: lesson
id: LESSON-050
title: Removing icon imports while JSX still references them = blank page on deploy
date: 2026-04-07
severity: critical
phase: phase-2C.7
tags: [react, imports, deploy, regression, sidebar]
status: archived-no-absorption-needed
last_updated: 2026-04-17
source_count: 1
---
# LESSON-050 — Dropped imports break the whole app silently at type-check time

## Symptom
After deploying Phase 2C.7 (Sidebar wiring for 6 new pages), every authenticated route returned a **blank page**. Playwright reported `body length = 0`. Browser console:

`PAGE ERROR: Shield is not defined`

The login screen still rendered (it does not import from Sidebar), so the Vercel deploy looked healthy on initial load.

## Root cause
While refactoring Sidebar.tsx imports to **add** 6 new lucide icons (TrendingUp, Flame, Building2, Scan, Target, HeartPulse), I rewrote the whole import block from scratch and **dropped** symbols that were still referenced inside JSX:

- `Shield`  → `<Shield className="w-5 h-5 text-white" />` in the logo block
- `Settings` → settings nav button
- `ChevronLeft` / `ChevronRight` → collapse toggle
- `LogOut` → logout button

`tsc --noEmit` did not catch this because the project's baseline tolerated module-level errors (broken pre-existing baseline). Vite built successfully because Rollup tree-shakes unused imports — it does not error on **missing** imports that are referenced at runtime; the JSX compiles to `React.createElement(Shield, ...)` and Shield resolves at runtime to the global scope, where it is `undefined`.

## Why it slipped through
1. **Project tsc baseline is dirty** — Pre-existing errors mask new ones. Cannot be trusted as a gate.
2. **Vite treats undefined React components as runtime errors** — they crash the whole tree, not just the offending node.
3. **Login screen does not depend on Sidebar** — first impression of deploy looks fine.
4. **I rewrote the import block instead of editing it** — dropped symbols lost in the rewrite.

## Fix
Re-add the dropped imports:
```tsx
import {
  LayoutDashboard, Camera, AlertTriangle, Network, Map as MapIcon,
  Activity, HardDrive, Route,
  Shield, Settings, ChevronLeft, ChevronRight, LogOut,  // <- restored
  TrendingUp, Flame, Building2, Scan, Target, HeartPulse,
} from "lucide-react";
```

## Permanent prevention
1. **Never rewrite import blocks. Always edit them in place** — surgical Edit tool calls only.
2. **After every Sidebar/Layout change, run a Playwright smoke test against an authenticated route** — not just the login screen.
3. **Reset the tsc baseline to zero errors** so new errors fail the build (queued for Phase 2D).
4. **Add an ESLint rule `no-undef` for component identifiers** — would have caught this at lint time.

## Verification
After fix: Playwright clicked all 6 new sidebar items and all rendered with real data.
- Здоровье камер: 243 cameras shown, real status counts
- Транспортная аналитика: 19 records from /api/proxy/violations
- Стоп-лист: honest "В разработке" stub
- All others: render OK, zero runtime errors

## Related
- LESSON-048 — phantom directory
- LESSON-045 — factory git add -A
