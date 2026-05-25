---
type: runbook-index
title: Substrate v2 Reliability Runbooks
date: 2026-05-04
status: draft
related:
  - "[[plans/PLAN-SUBSTRATE-V2-2026-05-03]]"
---

# Substrate v2 Reliability Runbooks

Six documented failure modes plus replication-slot recovery (added per autoplan Eng-High-7). Each runbook: detection signals, immediate response (≤0 min target), root-cause diagnosis, post-mortem template.

| # | Mode | Recovery target |
|---|---|---|
| 01 | Supabase down → Air mirror promote | 30 min |
| 02 | Air offline → telegram_poll fails over to VPS | 5 min |
| 03 | OpenRouter down → cached embeddings only | 1 min (degraded) |
| 04 | Mac↔Supabase split → local SQLite queue | seconds (auto-buffer) |
| 05 | Concurrent skill edits → conflict_detected → merge | 1–10 min |
| 06 | Projection bug → rollback to last-good git tag | 5 min |
| 07 | Replication slot invalidated → full resync | 30–60 min |

**Compounded uptime target post-runbook:** ~98.5% (vs 91.8% raw). ~11 hrs/month vs 60 hrs/month.

Tracked monthly in pages/audits/AUDIT-RELIABILITY-MONTHLY.md (created Phase A).
