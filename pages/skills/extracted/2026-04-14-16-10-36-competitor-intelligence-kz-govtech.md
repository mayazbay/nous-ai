---
type: skill
title: Competitive Intelligence Analysis — KZ GovTech Market
version: 1.0.0
extracted_from: pages/task-results/2026-04-14-16-10-36-analyze-the-global-vision-technologies-c.md
extracted_by: claude-session-15 (manual — Air screen-locked, 2026-04-14)
date: 2026-04-14
tags: [competitor, strategy, kz-gov, satory, erap, isap]
---

## When to Use

Run this skill whenever a new competitor is identified in the KZ government tech / smart city / law enforcement market — ЕРАП integrators, APK/camera system vendors, violation processing platforms, smart-city contractors.

## Framework: Always Deliver 3 Outputs

### 1. Three Technical Differentiators Satory Must Develop

Focus differentiators on layers competitors can't quickly replicate:

- **Legal logic layer** — automated КоАП code mapping + violation classification + metrology validation. Competitors offering "dumb pipe" (camera → ЕРАП) don't have this.
- **Cryptographic compliance** — GOST-signed SOAP via NCANode, full ЭЦП (ECP) signing chain. Hard to build fast.
- **Data quality moat** — metrology cert auto-verification before ЕРАП submission. Under KZ law, violations from uncertified cameras are legally inadmissible — this is a legal moat, not just technical.

Format: ① ② ③ numbered. Each: concrete technical name + why competitor can't easily replicate.

### 2. Single Fastest Move This Week

Always ask: what single action unblocks the biggest technical proof?
- Usually: VPN access (NIT preshared key from Asyl) OR live camera connection.
- Never: architecture planning, slide preparation, more research, waiting for meetings.
- Goal: produce one verifiable demo (real event → classification → signed submission) before competitor closes their first reference client.

### 3. One Risk If We Do Nothing for 30 Days

Focus on **reference installation dynamics** in KZ government procurement:
- First vendor to close a reference client sets the RFP template for future contracts.
- In KZ government, the second option is always "same as [first vendor]" — becoming the alternative, not the default, is catastrophic.
- Name the specific client type they're likely to close (municipality, КАЗГУ, highway agency) and the deadline window.

## Satory's Standing Moats (as of 2026-04-14)

Use as differentiator checklist — verify currency before citing:

| Asset | Status | Evidence |
|-------|--------|---------|
| ERAP backend | ✅ Live | 57 files, 19,106 lines, KOAP mapping + violation classification |
| smartbridge-soap-client | ✅ Live | GOST crypto, SOAP envelope, NCANode ЭЦП signing, 26 tests pass |
| metrology-cert-tracker | ✅ Live | Expired cert detection, CSV export, 17 tests pass |
| violation-event-pipeline | ⚠️ Blocked | Blocked on NIT VPN (skill #3) — cite as "in development" |
| Live camera integration | ⚠️ Blocked | Same NIT VPN blocker |

## KZ GovTech Competitor Registry

| Competitor | Offer | Price | Timeline | Protocol | Source |
|------------|-------|-------|----------|----------|--------|
| ТОО «Global Vision Technologies» | APK→ЕРАП integration | 98M KZT / 243 APK | 7–20 days | ISAP, Hikvision, Klubtika VPN | [[source-gvt-meeting-2026-04-14]] |
| Presight AI | Astana Smart City | $173M contract | — | — | [[SYNTHESIS-2026-04-12-three-ai-research]] |

Add new competitors as rows when encountered.

## Example Output (from GVT analysis 2026-04-14)

**Fastest move:** Get NIT VPN credentials from Asyl — unblocks violation-event-pipeline + live camera testing.
**30-day risk:** GVT closes a КАЗГУ or municipal client → becomes reference installation → Satory is relegated to "alternative" in all future RFPs. Window: GVT is priced for speed (7-20 day delivery means they want contract signed NOW).
