---
type: concept
id: CONCEPT-ISAPI
title: "ISAPI — Camera Event Protocol"
tags: [concept, isapi, cameras, hikvision, events]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# ISAPI — Hikvision Camera Event Protocol

HTTP-based protocol used by Hikvision cameras to push ANPR (license plate) events to our server.

## How it works
Camera detects vehicle → camera sends HTTP POST to our server:9080 → ISAPI listener parses XML → stores event in SQLite → 154K events captured so far

## How we use it
- ISAPI listener runs on VPS port 9080
- Only 51 cameras actively pushing (APK/intersection type)
- 145 LU cameras online but NOT configured to push (need ISAPI subscription setup)

## Key facts
- ISAPI is PASSIVE — cameras push to us, we dont poll
- LU cameras need subscription configuration by Denis
- Memory leak at ~1.5GB — cron restart at 2AM

## See also
- [[cameras|Camera Network]]
- [[erap|ERAP Pipeline]]
- [[LESSON-021-145-0-root-cause|LESSON-021]]
