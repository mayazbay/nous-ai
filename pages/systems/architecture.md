---
type: system
id: SYS-ARCH
title: "VPS Architecture"
tags: [system, architecture, vps, services]
date: 2026-04-06
last_updated: 2026-04-20
source_count: 1
status: reviewed
---
# VPS Architecture — 65.108.215.200

> **Peer compute hosts** (not VPS): **Air M2 MacBook** (`100.122.219.22`, primary 24/7 compute — see [[air-ssh-access]]); **[[nous-gpu|Nous-GPU]]** (RTX 5070 / CUDA 13.0 / `100.70.222.21`, Assyl+Alex provisioned 2026-04-20, Tailscale ACL pending).

## Directories
- /root/nous-agaas/ — Factory (AI pipeline, graph.py, agents, tools)
- /opt/nous-agaas/ — Production (police dashboard, ISAPI listener, event DB)
- /root/nous-agaas/codebase/satory-frontend/ — Frontend source (Vite+React)

## Services (systemd)
- caddy — Reverse proxy, SSL (ports 80, 443)
- spectra-dashboard — Police dashboard (port 8090)
- nous-isapi — ISAPI event listener (port 9080)
- nous-agaas — Factory (when running)

## Routing (Caddy)
- satory.nousagaas.com → Vercel (frontend SPA)
- api.nousagaas.com → localhost:8090 (police dashboard API)
- nousagaas.com → localhost:3000 (Next.js portal)

## API Routes (police_dashboard.py on :8090)
/api/cameras, /api/events, /api/stats, /api/violations,
/api/health, /api/login, /api/export, /api/erap,
/api/system-events, /api/traffic-density, /api/watchlists,
/api/archives, /api/tracking, /api/map, /api/search, /api/audit

## See also
- [[cameras|Camera Network]]
- [[erap|ERAP Pipeline]]
- [[api_routes|API Routes]]
