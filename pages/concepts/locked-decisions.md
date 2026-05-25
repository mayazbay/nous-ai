---
type: concept
id: CONCEPT-LOCKED
title: "Locked Decisions — Cannot Change"
tags: [concept, locked, decisions, permanent, config]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# Locked Decisions — Cannot Change Without CEO Madi Approval

Source: Master State document, April 1 2026

## Technical
- BIN: 070640013540 (Spectra ITS, in config.SYSTEM_BIN)
- Timezone: Asia/Almaty (config.now_kz())
- Crypto: GOST 34.10-2015
- AI stack: PaddleOCR + RT-DETR (Apache 2.0)
- NO Ultralytics (license issue)

## Numbers
- Cameras: 5,800 total (VKO region)
- MRP 2026: 4,325 tenge
- Contract: $23M (10.5B tenge)

## Architecture
- SOFTWARE ONLY — APK hardware untouchable (gov procurement)
- Three components: ISAPI server + VMS portal + ERAP module
- Pipeline: deterministic first, LLM second

## What Does NOT Exist (as of April 6)
- AI plate recognition (regex only, no trained model)
- Real GOST signatures (KalkanSigner built, needs production test)
- Live SmartBridge connection (gateway works, not connected yet)
- Any accuracy numbers (87/95/99.7% are NOT real)

## See also
- [[cameras|Camera Network]]
- [[erap|ERAP Pipeline]]
- [[LAW-013-truth|LAW-013]]
