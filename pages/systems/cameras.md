---
type: system
id: SYS-CAMERAS
title: "Camera Network — 243 Cameras"
tags: [system, cameras, network, hikvision]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# Camera Network

**Total:** 243 APK cameras across 3 cities (connected to our system)
**Video access:** 109 cameras (Ust-Kamenogorsk linear, video stream confirmed)
**VKO contract scope:** 5,800 cameras total (Spectra ITS contract, future)
**Source:** Denis Excel (955+ entries with GPS, speed limits, certs)

## By City
| City | Type | Subnet | Credentials | Status |
|------|------|--------|-------------|--------|
| Ust-Kamenogorsk (UKG) | LU (highway) | 10.170.x.x | oper/<REDACTED-see-.env> | 156 online |
| Ust-Kamenogorsk (UKG) | Perekrestok | 10.235.x.x | admin/<REDACTED-see-.env> | 51 active |
| Ridder | LU + Perekrestok | 10.164.x.x | unknown | Ping OK, ISAPI no |
| Altay | LU | 10.165.x.x | unknown | Ping OK, ISAPI no |

## Hardware
- Model: Hikvision iDS-2CD9396-BIS (iDS-TCV907-BIR for APK)
- ISAPI subscription port: 9080
- VPN server: 89.40.56.150

## Key Issue: 26,000 False Violations
Speed thresholds set to 60 km/h default. Real limits vary: 40/60/70/80.
Fixed by importing correct speed limits from Denis Excel per camera location.

## Certificates
WARNING: Many metrology certificates expired late 2024. Cameras with expired certs CANNOT legally issue violations.

See also: [ERAP Pipeline](erap.md), [Overview](../overview.md)

## See also
- [[erap|ERAP Pipeline]]
