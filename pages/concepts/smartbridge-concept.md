---
type: concept
id: CONCEPT-SMARTBRIDGE
title: "SmartBridge / ШЭП — Government Security Gateway"
tags: [concept, smartbridge, shep, government, gateway, erap]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# SmartBridge / ШЭП — Government Security Gateway

Government security gateway that sits between our server and ERAP. Required for all violation submissions.

## How it works
Our server → SmartBridge (ШЭП) → ERAP
- SmartBridge = catalog/registration system (sb.egov.kz)
- ШЭП = actual runtime gateway for data transmission
- Requires mTLS + JWT since September 2025
- AsyncChannel v10 protocol

## Current status
- Gateway CONFIRMED WORKING (April 3, 2026 — 18 requests)
- ECP certificate was the blocker — now resolved
- Registration via Spectra ITS company (BIN 070640013540)
- 3-week timeline via Spectra ITS platform
- Test environment: apply Monday via sb.egov.kz

## Key facts
- WSDL analyzed, SOAP/XML format
- ERAP XML namespace: esb.sergek.kz/cxf/violation (Sergek format)
- 21 violation codes supported
- service_id + client_id (UUID) required
- Response: boolean true/false

## See also
- [[erap|ERAP Pipeline]]
- [[LAW-002-autofine|LAW-002]]
