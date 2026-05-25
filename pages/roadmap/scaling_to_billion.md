---
type: roadmap
id: ROAD-SCALE
title: "Scaling to Billion — AGaaS Roadmap"
tags: [roadmap, scaling, agaas, billion]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
status: reviewed
---
# AGaaS Scaling Roadmap — Consolidated from Grok + Gemini Reviews (April 5, 2026)

## SOURCE: Triple AI audit (Claude + Grok + Gemini) — All three agreed on assessment below.

## Verdict
- ON TRACK for M Satory VKO contract
- NOT YET architected for billion-dollar scale
- Competitive moat: real government integration (ANPR, ERAP, GOST crypto) is RARE

## Current Architecture (What Works)
- 7-agent multi-provider (Opus CEO + Sonnet Coder + Kimi Researcher + Qwen Validator/Reporter)
- LangGraph 12-node DAG with task decomposition
- Mem0 + SQLite persistence, watchdog self-healing
- 87 tasks done, 212 tests, real camera data
- ~-40/day operating cost

## Critical Scaling Limits
1. Single-tenancy, single-VPS — no isolation between projects
2. No observability/tracing (mandatory for government audit trails)
3. No LLM gateway for cost/failover routing
4. Data residency (Finland VPS vs KZ law)
5. No multi-tenancy for multiple clients

## Phase 0: Stabilize (Week of April 7 — Post-Demo)
- Add tenant_id to FactoryState + SQLite
- Integrate LangSmith for tracing
- Health monitor with preflight checks (DONE April 5)

## Phase 1: Multi-Project Support (4-8 Weeks)
- Structured thread_id: tenant:{id}:project:{id}:session:{uuid}
- Migrate SQLite → PostgreSQL with RLS
- AsyncPostgresSaver for LangGraph checkpoints
- Celery/RabbitMQ for distributed task execution
- LLM gateway for intelligent routing

## Phase 2: Production-Grade (2-4 Months)
- Full observability + cost governance
- Usage-based billing per tenant
- Template library (Safe City, VMS configs)

## Phase 3: Billion-Dollar Scale (6-12 Months)
- Global regions with data residency
- Agent marketplace / reusable crew templates
- Enterprise: RBAC, SSO, SOC-2
- 1,000+ concurrent agents

## Multi-Tenancy Architecture (Gemini Spec)
- Thread ID format: tenant:{tenant_id}:project:{project_id}:session:{uuid}
- checkpoint_ns = tenant:{tenant_id}
- Separate conversations table with RLS
- Dynamic DSN routing: kz-* → KZ host, else → EU host
- validate_tenant as FIRST node in DAG
- Zero-downtime migration from current SQLite

## Cost at Scale
- Phase 0-1: +-15k/month for observability/distributed systems
- Phase 2+: Unit economics <10% of value delivered, 70-80% margins

## Factory Prompts (for autonomous implementation)
CEO: Implement full multi-tenancy in 12-node LangGraph factory. Extend FactoryState with tenant_id, project_id, audit_log. Thread_id format: tenant:{id}:project:{id}:session:{uuid}. Migrate to AsyncPostgresSaver. Create conversations table + RLS. Add validate_tenant node. Preserve all 87 tasks + 212 tests.

## Key Decision: Sequence
1. FIRST: Win Monday demo (BDL replacement works, all pages render)
2. THEN: Phase 0 (tenant awareness, LangSmith)
3. THEN: Phase 1 (multi-project, Postgres, distributed)
4. Revenue from Satory funds Phase 2-3

## Gemini Revenue Model (Corrected April 5)
- % of fines is ILLEGAL in KZ
- Hybrid model: SaaS subscription + AI service billing
- Undercut competitors: 120-140M KZT connection (vs 150M) + 25-28K KZT/camera/mo (vs 30K)
- AI premium: 24/7 monitoring, VLM plate recognition, metrology tracking, cross-db violation stacking
- 60,000 cameras nationwide x 25K/mo = 18B KZT/year ARR

## Gemini New Insights (worth keeping)
1. Article 31 AO Code (March 12, 2026): cameras can now penalize qualitative violations (phone, seatbelt)
2. VLM secondary validation for 2026 VIP plates = competitive moat + data flywheel
3. Structured Outputs (Claude API json_schema mode) eliminates prompt-coercion for ERAP payloads
4. SmartBridge 7-day discount window: delays in ERAP submission violate citizen rights
5. Edge-hashing: purge raw images after extraction, only store hashed metadata

## 4 New Factory Tasks (from reviews)
1. Metrology Validation Agent: check cert expiry before generating any fine
2. VLM plate validator: route low-confidence OCR to vision model
3. Structured Outputs: switch ERAP payload generation to json_schema mode
4. Edge hash-and-purge: delete raw JPEG after extracting plate data

## See also
- [[cameras|Camera Network]]
- [[erap|ERAP Pipeline]]
- [[cerebro_bdl_vms_requirements|VMS Requirements]]
