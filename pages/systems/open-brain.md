---
type: system
id: SYS-OPEN-BRAIN
title: "Open Brain"
tags: [system, openbrain, mcp, supabase, gbrain, substrate]
date: 2026-05-03
last_updated: 2026-05-11
source_count: 2
status: active
openbrain_id: unknown-list-thoughts-omits-uuid
content_hash: db5f3670b8c8efd4
source: openbrain-manual-mirror
related: [factory-ops, architecture-quickref, AUDIT-openbrain-projection-2026-05-11]
---
# Open Brain

Open Brain is the Nate B. Jones-style MCP capture and recall path for Nous AGaaS. It is currently implemented as a Supabase-backed MCP service with pgvector storage and OpenRouter embeddings.

## Verified Surfaces

- Claude/Claude.ai Open Brain MCP is connected and exposes the Open Brain thought tools.
- The OpenBrain audit on 2026-05-11 verified `thought_stats` returned 9 thoughts.
- The active store contains mostly connector tests and session snapshots; the one durable setup event is mirrored here.

## Mirrored OpenBrain Event

Captured thought from 2026-05-03:

> Successfully set up Open Brain on 2026-05-03. Connected via Claude Code MCP. Stack: Supabase pgvector + OpenRouter embeddings

Audit classification: `mirror`. This was the only real infrastructure event in the 2026-05-11 OpenBrain gap matrix that did not already have a canonical vault page.

## Current Rule

Do not build a projection bridge just because the connector exists. Continue with manual mirrors until OpenBrain produces at least 10 real-signal `mirror` thoughts over a rolling 14-day window. If that threshold is reached, use the VPS/Air projection runner path, not GitHub Contents API, unless a GitHub-to-VPS-bare sync path is separately proven.

## See Also

- [[factory-ops]]
- [[architecture-quickref]]
- [[AUDIT-openbrain-projection-2026-05-11]]
