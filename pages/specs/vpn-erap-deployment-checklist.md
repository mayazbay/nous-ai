---
type: spec
id: SPEC-VPN-ERAP-DEPLOY
title: "SUPERSEDED — no VPN needed, see AUDIT-021"
tags: [spec, superseded, deprecated]
date: 2026-04-07
related: [AUDIT-021, SPEC-ERAP]
status: superseded
last_updated: 2026-04-07
source_count: 1
---
# SUPERSEDED

This checklist was written based on the assumption that SmartBridge required a VPN tunnel. After re-reading the SmartBridge PDF, that assumption was wrong.

**The real transport is public HTTPS on sb.egov.kz with WS-Security and ECP signatures.**

**The real blockers are bureaucratic:** OID registration with КПСиСУ, ECP cert from НУЦ РК, serviceId/clientId UUIDs issued after OID.

**See:**
- [[AUDIT-021-strategic-reset-vpn-myth-factory-redesign]] — full correction
- [[erap_requirements]] — the REAL technical spec for ERAP integration
- [[outreach-messages-2026-04-07]] — what to ask humans (Asyl, Denis, Aidana, Roza, Tolgat)
