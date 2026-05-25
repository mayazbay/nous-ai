---
type: spec
id: SPEC-ERAP-INTAKE-DECISION-2026-05-12
title: "ERAP Intake Service — Architecture Decision 2026-05-12"
tags: [spec, erap, decision, architecture]
date: 2026-05-12
status: active
last_updated: 2026-05-12
related: [erap_requirements, two-track-erap-strategy-2026-04-16, smartbridge-vshp-client-credentials-2026-04-08]
---

# ERAP Intake Service — Architecture Decision (2026-05-12)

## Decision

Build a **self-contained minimal Python (FastAPI) service** at `Nous/projects/erap-intake/`.

## Rationale (Musk Step 2 applied)

### What we DELETED from scope
- Camera pipeline (ISAPI, Hikvision, event parser) — not needed for intake
- PostgreSQL / SQLite persistence — receipts saved to file in MVP
- Police dashboard — separate concern
- KalkanCrypt native .so dependency — not deployable without Linux SDK install
- Complex audit logging — basic file logging in MVP

### What we KEPT (minimum viable intake)
- `POST /violation` → validate → sign → post to ERAP → receipt
- NCAnode REST client (calls VPS port 14579 `/wsse/sign`)
- SOAP XML builder (pure Python, stdlib xml.etree)
- ERAP/SmartBridge HTTP client (configurable endpoint)
- Mock ERAP endpoint (for E2E testing without VPN)

## Language: Python 3.11+

**Chosen over Go** because:
- Existing ERAP codebase is Python (35K lines of soap_client.py logic documented)
- FastAPI is the fastest path to a working HTTP service
- NCAnode client is simple HTTP POST — no language advantage for Go

## Signing architecture

Two modes, controlled by `NCANODE_CERT_PATH` env var:

1. **NCAnode mode** (when cert configured): POST to `http://${NCANODE_HOST}:${NCANODE_PORT}/wsse/sign`
   - Requires: `.p12` certificate + password (from Aidana/NUC RK, ETA unknown)
   - On production: real GOST 34.10-2015 signature
   
2. **Mock mode** (when no cert): generates a mock ГОСТ-shaped signature for testing
   - Used for E2E testing until real ECP cert arrives
   - NCAnode HTTP call is still ATTEMPTED (to prove integration); mock is fallback

## ERAP endpoint

Configurable via `ERAP_ENDPOINT`:
- `mock://localhost:8091` — local mock ERAP (for testing)
- `https://smartbridge.era.kz/...` — real endpoint (requires NIT VPN + SmartBridge registration)

## Deployment

One-command: `bash bootstrap.sh`

Install location: `/opt/erap-intake/`

## Known blockers for production

| Blocker | Owner | Workaround |
|---|---|---|
| ECP certificate (.p12) | Aidana → NUC RK | Mock signing mode |
| NIT VPN to SmartBridge | Government / NIT | Mock ERAP endpoint |
| SmartBridge registration (KPSISU-S-5827) | Asylbek | Mock ERAP endpoint |

## Evidence trail

- `evidence/e2e-proof-<timestamp>.json` — input payload + SOAP XML + sign response + ERAP receipt
- `evidence/ncanode-probe-<timestamp>.json` — NCAnode API call proof
