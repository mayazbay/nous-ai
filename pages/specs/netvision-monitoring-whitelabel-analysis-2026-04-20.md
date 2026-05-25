---
type: spec
id: netvision-monitoring-whitelabel-analysis-2026-04-20
title: "Analysis — Netvision Monitoring White-Label proposal (2026-04-20, v2 JV reframe)"
tags: [analysis, spec, proposal, netline, white-label, russian, joint-venture, general-partner, technology-partner, satory, kz-exclusivity, royalty, minimum-annual-payment, risk, open-questions, v2-jv-reframe]
date: 2026-04-20
source_count: 1
status: v2-jv-reframe
last_updated: 2026-04-20
related: [source-netvision-monitoring-whitelabel-proposal-2026-04-20, letter-to-saken-aga-netvision-v3-2026-04-20, netvision-remediation-plan-2026-04-20, netline, satory-expansion-3-regions, saken-aga-netline-briefing-ru, satory, spectra-its]
language: en
audience: [madi, smatay]
---

# Analysis — Netvision Monitoring White-Label Proposal (v2 — JV Reframe)

**Source:** [[source-netvision-monitoring-whitelabel-proposal-2026-04-20]]
**Decision owner:** Madi + Smatay
**Recommendation:** ⚠️ **The current proposal is a licensor-vs-buyer structure, not a JV. Counter-propose joint-venture structure first; if counterparty agrees in principle, proceed to NDA. If they refuse JV, walk.** Full formal counter-proposal draft: [[letter-to-saken-aga-netvision-v3-2026-04-20]].

> **v2 note (2026-04-20, session 53):** v1 of this analysis framed the deal as licensor-vs-buyer and asked "how do we soften the vendor terms?" Madi re-educated mid-session: the correct frame is **Joint Venture** where Nous/Satory is **General Partner** (carries capital, market, execution risk) and counterparty is **Technology Partner / LP** (contributes product, engineering, support). Whole analysis below is reframed under JV lens. Remediation captured in `session-operating-contract` AP-6. See also [[netvision-remediation-plan-2026-04-20]].

---

## 0. Commercial frame — the structure we are pursuing

**Joint Venture (JV) / General Partner + Technology Partner.** Not licensor + distributor. Not vendor + reseller. Not franchise + MAP.

| Role | Party | Contributes | Bears risk on |
|---|---|---|---|
| **General Partner (GP)** | Nous / Satory | Capital · in-country execution · brand · market access (3 KZ regions at start) · regulatory navigation · deployment + support L1 · working capital for pilots + initial scaling | Market risk · execution risk · capital risk · regulatory risk |
| **Technology Partner (LP)** | Counterparty (presumed NetLine pending Q1) | Product · ongoing R&D · source engineering · updates · support L2+L3 · training · new data-source connectors | Product risk · IP risk · engineering-capacity risk |
| **Shared (JV)** | JV entity | Governance · pricing policy · territory · roadmap · profit pool | Shared commercial risk |

**Profit split:** 50 / 50 of JV net revenue (consistent with the 50% royalty split already in the proposal).

**Critical asymmetry — this is our leverage.** The counterparty faces **zero new-capital exposure** in this deal. They contribute existing product + engineering time; they do not underwrite Kazakhstan market entry. We underwrite the entire market-entry cost (capital, pilots, execution, government relations, support infrastructure). Therefore: **every term in the proposal that demands guaranteed income independent of JV outcomes (MAP floor, upfront localization fee with no profit link, pilots 100% on us) is not a partnership term — it is a rent-extraction term that destroys the JV structure.**

### What the proposal already gets right (JV-consistent)

- **50% royalty on analytic core + 50% royalty on data-source connectors.** This is the JV profit split in license-transaction form. Keep.
- **White-label brand rights in RK.** Consistent with GP owning the local go-to-market.
- **Support division (L1 on us, L2+L3 on them).** Consistent with GP handles local, LP handles product.
- **NDA-first sequence.** Healthy.

### What the proposal breaks (anti-JV terms)

1. **50 M ₽/year Minimum Annual Payment (MAP).** Licensor-rent from GP regardless of JV outcomes. Fundamental anti-JV term. Must be removed or restructured into equity/reinvestment in the JV.
2. **Licensor-owned license server + 30-day kill-switch.** No co-governance of the infrastructure the JV depends on.
3. **No source escrow.** GP has no protection against LP disappearing, pivoting, or becoming sanctioned.
4. **Ruble-denominated commitments.** FX risk lives entirely on the GP (Kazakhstan) side. JV contracts should be tenge (GP's operating currency) or shared coridor.
5. **Pilots 100% funded by GP.** Either pilots are JV-level investment (shared) or GP-funded with royalty holiday until recovered. Not both full cost AND full royalty from day 1.
6. **Territory restriction (RK only, no sublicense, no export).** JV exclusivity for RK is fine; hard-restricting JV expansion to neighboring CIS markets without separate consent removes upside without offset.
7. **No co-governance.** "We retain the right to audit, suspend, block." Unilateral supplier-posture, not JV.

---

## 1. TL;DR — the three things to know before the next step

1. **Structural frame:** Current proposal = licensor + distributor. Correct frame = JV / GP-LP. Counter-propose JV or walk.
2. **Scope mismatch:** The [[saken-aga-netline-briefing-ru]] asked for **three** products (Netvision base VMS, ПАК ТОР, ПАК Гарпун). This proposal covers **one** (Netvision Monitoring — fleet-operability / maintenance-SLA platform for photo-video fixation camera complexes, verified from [net-line.pro/solutions/netvision-monitoring](https://net-line.pro/solutions/netvision-monitoring/)). Netvision Monitoring does NOT replace Cerebro, does NOT handle ERAP. Other three products appear available on the site but are not in this offer — must be added to the JV scope before any commitment.
3. **Sender identity unverified.** The proposal document does not name the legal entity. Product name matches [[netline]]'s catalog. Must confirm sender = NetLine (or identify actual sender) before NDA.

---

## 2. Commercial numbers (for reference)

| Item | Amount (₽) | Amount (USD @90₽/$) | Amount (₸ @6₸/₽) | Status under JV |
|---|---|---|---|---|
| One-time localization | 1.2 M ₽ | ~13 K | ~7.2 M ₸ | Acceptable as JV setup cost |
| Annual minimum (MAP) | 50 M ₽ | ~556 K | ~300 M ₸ | **Must be removed — anti-JV** |
| Royalty (core SW) | 50% per license | — | — | JV-consistent, keep |
| Royalty (data source connector) | 50% per license | — | — | JV-consistent, keep |

### Why MAP is the deal-breaker (arithmetic)

To cover the MAP purely from royalties at 50/50 split, the JV must generate **200 M ₽/year (~$2.2 M)** of Netvision-Monitoring-only licenses in Kazakhstan. This is the revenue of the JV, not ours. For a niche fleet-ops product that serves perhaps 5-15 large gov/infra buyers in KZ, this is aggressive-to-unrealistic in year 1-2. Under the MAP structure, any underperformance → GP writes a make-whole cheque to LP. Under pure-royalty JV, underperformance → both sides earn less. The MAP transfers all market risk to GP while the LP keeps guaranteed rent. That is what makes it not a JV.

---

## 3. Red flags (severity under JV lens)

### R0 · **Fundamental** — MAP floor = anti-JV
See §2 arithmetic. Single largest structural mismatch. Must be removed or converted to JV-level reinvestment (e.g., LP earns 50% of JV net revenue, 0% floor, but retains option to wind down participation if JV underperforms for N consecutive years).

### R1 · **High** — Licensor-owned license server with 30-day kill-switch
Clause 4.5: *"В случае задержки оплаты система мониторинга автоматически переходит в режим работы с ограниченным функционалом."* KZ gov pays 60-120 days late as a matter of normative practice. Unacceptable in a JV — the JV's own customers (gov end-clients) get bricked for payment timing outside JV control. Fix: kill-switch triggers only on JV-partner breach, not end-customer payment lag.

### R2 · **High** — No co-governance of license infrastructure
§5 "Мы сохраняем право... приостанавливать выдачу новых лицензий при нарушении условий." Unilateral. JV needs co-governance or at minimum dispute-resolution + cure-period before infrastructure-level action.

### R3 · **High** — No source escrow for JV dissolution / sanctions scenarios
Clause 3 withholds: analytic core source, connector source, licensing system source, build tools, internal algorithms. Under JV, GP cannot be left with a stack of useless binaries if LP exits or is sanctioned. Fix: escrow with a neutral Kazakhstan / international agent, release trigger = LP insolvency or JV termination.

### R4 · **Medium** — Ruble denomination
50 M ₽ MAP (if retained in any form) + royalty rates are in rubles. FX risk lives on GP side. Fix: all JV denominations in tenge; or a shared-corridor clause (e.g., ±15% from baseline rate).

### R5 · **Medium** — Pilots 100% GP-funded
Clause 4.6. Under JV, pilots are either JV-level capital expenditure (both sides contribute) or GP-funded with royalty holiday on the revenue from the pilot site until pilot cost is recovered.

### R6 · **Medium** — Hard territorial restriction (RK only)
Clause 6 blocks sublicense / sale outside RK without consent. JV-style exclusivity in RK is fine; hard-blocking regional expansion (UZ / KG / AZ) removes upside. Fix: right-of-first-refusal for adjacent CIS markets at pre-agreed terms.

### R7 · **Medium** — 8-week localization SLA with no remedy
Gov-tender cycles don't pause. 4-week slip = missed procurement window. Fix: liquidated-damages or service-credit structure for SLA misses.

### R8 · **High** — Scope mismatch vs original briefing
Original ask: three products (Netvision base + ПАК ТОР + ПАК Гарпун). Response: one product (Netvision Monitoring). Must know whether the other three are available for JV white-label; if not, the entire expansion thesis needs rework (see §8).

---

## 4. Green flags (JV-consistent elements already present)

### G0 · 50/50 royalty split
Directly maps to a JV profit split. This is the single most important element of a JV that the proposal already contains.

### G1 · First concrete written offer
Signed proposal > 6 weeks of verbal. Counterparty is serious enough to put numbers on paper.

### G2 · White-label brand rights in RK
Consistent with JV where GP owns local brand + go-to-market.

### G3 · Localization-cost discipline
1.2 M ₽ localization is a reasonable JV setup cost — small relative to the JV's projected operating budget.

### G4 · Ongoing R&D contribution from LP side
Clauses 3 + 7: they keep investing in product; we get updates. This is the LP's JV contribution in kind.

### G5 · Fair support division
L1 on GP (local), L2+L3 on LP (product). Mirrors the GP/LP role split.

### G6 · NDA-first sequence
Standard healthy sequence: NDA → meeting → terms → framework → localization. No pressure.

### G7 · Product-family upside potential
Netvision Monitoring may be a phase-1 feeler — the full Netvision + ПАК ТОР + ПАК Гарпун stack (per net-line.pro catalog) could follow under a broader JV framework. Leverage this in Q2.

---

## 5. Five structural questions to the counterparty (JV-frame)

Full formal Russian-language letter: [[letter-to-saken-aga-netvision-v3-2026-04-20]]. Summaries:

### Q1 · Legal entity of the sender
Name, registration data, relationship to the Netvision product line. Must be answered in writing before NDA.

### Q2 · Full product-line availability for JV
Are Netvision (base VMS), ПАК ТОР, ПАК Гарпун available for the JV in RK? If yes — on what terms, what timeline, single-framework or separate agreements? If no — what is required for them to become available?

### Q3 · Continuity mechanisms for end-customers
(a) Source-escrow or local fallback for JV-dissolution / sanctions scenarios? (b) Exclude automatic limited-functionality transition when the payment lag is caused by the government end-customer, not the JV?

### Q4 · Currency + payment-timing
(a) Tenge denomination with fixed-rate or corridor? (b) Alignment of JV payment cadence with KZ gov payment cadence (60-120d post-acceptance)?

### Q5 · Market-size realism
Counterparty's internal estimate of annual KZ market for Netvision Monitoring (and broader Netvision line). Reference-region data points (comparable Russian regions — volumes, customer structure, license life-cycle).

---

## 6. Recommended next action (JV-counter-proposal path)

**Do NOT sign NDA yet. Counter-propose JV structure first.** Staged:

| Step | Who | What | Timeframe |
|---|---|---|---|
| 1 | Madi | Short internal message to Saken aga (the trusted intermediary) stating JV position + requesting alignment call before formal reply | ✅ sent 2026-04-20 (long version) |
| 2 | Madi ↔ Saken aga | Alignment call — confirm Saken aga supports JV frame; agree on who delivers formal reply (Madi direct or via Saken aga relay) | ≤ 1 week |
| 3 | Madi | Send formal Russian counter-proposal letter to counterparty (draft: [[letter-to-saken-aga-netvision-v3-2026-04-20]]) | post alignment call |
| 4 | Counterparty | Respond to 5 structural questions + indicate position on JV frame | 2-3 weeks typical |
| 5 | Madi + Smatay | Decide go/no-go based on decision criteria in §7 | post response |
| 6 | Madi | If go: engage Aleksey ([[aleksei-satory]]) on JV structure + Kazakh law-firm sanctions opinion + NDA text | parallel, starts in step 5 |

---

## 7. Decision criteria — JV-frame gate

**Proceed to NDA if ALL of:**
- Q1 confirms a legitimate, non-sanctioned Russian legal entity with verifiable registration data.
- Q2 confirms the broader product catalog (at least: Netvision base + one of ПАК ТОР / ПАК Гарпун) is available for the JV, even if phased.
- Q3 gives at least a mechanism for source-escrow and an end-customer-payment-lag carve-out from the kill-switch.
- Counterparty agrees **in principle** to restructure the deal as a JV: MAP floor removed, governance shared, currency flexibility.

**Pause / renegotiate if ANY of:**
- Counterparty refuses JV frame and insists on licensor-only terms.
- Q2 shows the full stack is permanently off the table and only Netvision Monitoring is on offer.
- Q3 is a hard "no" on escrow or payment-lag carve-out.
- No movement on currency / MAP.

**Hard-stop / walk away if:**
- Sender entity is on an active sanctions list (OFAC / EU / UK).
- Counterparty refuses to name the legal entity in writing.
- Counterparty insists on MAP floor with no JV-level equity or reinvestment equivalent.

---

## 8. How this fits the broader expansion strategy

[[satory-expansion-3-regions]] is the umbrella. Under the JV frame:

- **Plan A (preferred):** Push counterparty to agree to JV structure covering Netvision base + ПАК ТОР + ПАК Гарпун (and Netvision Monitoring as a smaller component of the stack). 50/50 profit pool, no MAP, tenge, escrow, shared governance. This replaces the "3 regions" build-from-scratch path with a JV-powered rollout.
- **Plan B (fallback):** If counterparty accepts JV frame but limits scope to Netvision Monitoring only, take it — as a door-opener with first revenue visibility — and continue the VKO-native Cerebro/BDL-replacement path ([[bdl-replacement-state-2026-04-07]]) in parallel. The JV does not block own-stack development; it delivers a narrower product with a smaller footprint.
- **Plan C (walk):** If counterparty refuses JV frame entirely and holds the MAP-licensor structure, walk. The MAP alone (~$556 K/yr floor) does not justify itself on a narrow product with uncertain KZ market size. Continue building our own stack + reopen candidate search (Axxon, TRASSIR, Macroscop were earlier-stage candidates per [[satory-expansion-3-regions]]).

---

## 9. Open questions (dogfooded per `session-operating-contract`)

- `[open-question]` Q1 — sender legal entity — unresolved until counterparty answers. Blocks NDA.
- `[open-question]` Q2 — full product availability — blocks Plan A selection.
- `[dependency-risk]` Counterparty channel is currently single-threaded through Saken aga (intro channel). At NDA stage, direct commercial contact should be established for redundancy.
- `[weak-edge]` We have not independently demoed Netvision Monitoring against our actual KZ use cases. Pilot-assessment must precede deeper commitment regardless of structural terms.
- `[contradiction]` The 2026-04-07 briefing assumed all 3 products would be offered; the response narrows to one. Q2 resolves.
- `[model-drift]` v1 of this analysis (session-52-mid, same date) framed the deal as licensor-vs-buyer rather than JV/GP-LP. Frame-error captured in `session-operating-contract` AP-6 (classify-deal-structure-before-commercial-analysis). Remediation: [[netvision-remediation-plan-2026-04-20]].
- `[model-drift]` v1 Russian draft leaked internal intro-channel + private-NDA references as external pitch material. Frame-error captured in AP-5 (scrub-internal-context-from-outbound). Draft never sent to counterparty — caught in review.
- `[model-drift]` v1 Russian draft signed «Ади» instead of «Мади Аязбай». Identity-not-verified-from-substrate. Captured in AP-4 (identity-from-substrate-before-outbound).

## Timeline

- **2026-04-20** | v2 — JV reframe after Madi's mid-session re-education. Frame changed from licensor-vs-buyer to JV / GP-LP; R0 added (MAP = fundamental anti-JV); G0 added (50/50 royalty is JV-consistent); questions reframed around JV structure not licensor concessions; §6 recommendation rewritten as JV-counter-proposal path; §7 decision criteria gated on JV acceptance. 3 frame-error `[model-drift]` entries added to §9 with cross-refs to AP-4/5/6 in `session-operating-contract`.
- **2026-04-20** | v1 — Initial analysis from raw proposal text. Scope gap surfaced (1 product vs 3 in brief). Sender identity pending. 5 questions drafted. **Frame was wrong** — licensor-vs-buyer instead of JV; corrected in v2 same-day.

## See also

- [[source-netvision-monitoring-whitelabel-proposal-2026-04-20]] — raw text
- [[letter-to-saken-aga-netvision-v3-2026-04-20]] — formal Russian counter-proposal letter
- [[netvision-remediation-plan-2026-04-20]] — this session's remediation plan
- [[netline]] — probable sender / product-line owner
- [[satory-expansion-3-regions]] — umbrella project
- [[saken-aga-netline-briefing-ru]] — original 2026-04-07 briefing
- [[madi-profile]] — identity source of truth (signature verified here)
- [[bdl-replacement-state-2026-04-07]] — parallel VKO workstream
