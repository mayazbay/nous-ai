---
type: system
id: SYS-API
title: "API Routes — api.nousagaas.com"
tags: [system, api, routes, endpoints]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# API Routes — api.nousagaas.com

All routes served by police_dashboard.py on localhost:8090.
Caddy proxies api.nousagaas.com → :8090.
Frontend calls /api/proxy/* → Vercel rewrites to api.nousagaas.com/api/*.

## Key Endpoints
- GET /api/cameras — 243 cameras with status, GPS, type (JSON)
- GET /api/events — Recent vehicle events with plates, speeds (JSON)
- GET /api/stats — Dashboard summary: counts, active cameras
- GET /api/violations — Filtered violations list
- POST /api/violations/create — Create violation from event
- GET /api/health — System health check

## IMPORTANT
- URL is /api/cameras NOT /api/v1/cameras (no v1 prefix!)
- Camera GPS: VKO region (lat 49-51, lon 82-85), NOT Almaty
- Auth: Bearer token in Authorization header

## See also
- [[cameras|Camera Network]]
