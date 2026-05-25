---
type: spec
id: netvision-remediation-plan-2026-04-20
title: "Plan — Netvision proposal remediation + JV reframe + 3-AP skill codification (session 53)"
tags: [plan, spec, remediation, netline, netvision-monitoring, white-label, joint-venture, general-partner, technology-partner, session-operating-contract, karpathy-ratchet, musk-5-step]
date: 2026-04-20
source_count: 0
status: draft-awaiting-approval
last_updated: 2026-04-20
related: [netvision-monitoring-whitelabel-analysis-2026-04-20, source-netvision-monitoring-whitelabel-proposal-2026-04-20, netline, satory-expansion-3-regions, saken-aga-netline-briefing-ru, madi-profile]
language: en
audience: [madi]
---

# Netvision Proposal Remediation — Implementation Plan (session 53)

> **For execution:** 7 tasks, sequenced, Musk-5-step-leaned (3 candidate tasks deleted during planning — see §Musk pass). Plan-first-then-execute per Madi's directive. STOP at Task 2 for approval before touching substrate.

**Goal:** Correct three concrete failures from session 52-mid — (a) wrong commercial frame (licensor-vs-buyer → JV / GP-LP), (b) confidentiality leak in outbound draft, (c) drafting-without-gbrain-verification — then codify all three into runtime doctrine so they cannot recur.

**Architecture:** Surgical patches to existing spec + fresh Russian v3 letter + 3 APs into `session-operating-contract` skill + one logical commit + 4-way sync + gbrain timeline. No rewrites, no new files beyond what's strictly additive.

**Standard:** Musk 5-step (question-delete-simplify-accelerate-automate) + Karpathy ratchet (every failure → skill, every skill → compounding substrate) + Tan lean (zero decorative tasks). RULE ZERO in force (no new LESSON files).

---

## Context — the three failures in one paragraph each

**Failure 1 — Wrong commercial frame.** My session-52-mid analysis treated the NetLine proposal as licensor-vs-buyer and asked "how do we shift this toward partnership?" Madi re-educated: the correct frame is a **Joint Venture** where Nous/Satory is the **General Partner** (brand, capital, in-country execution, market access, regulatory) and NetLine is the **Technology Partner / LP** (product, engineering, updates). The 50/50 profit share the proposal contains is *consistent* with that JV — what *breaks* the JV is (i) the 50 M ₽/yr MAP floor collecting guaranteed rent regardless of outcomes, (ii) their license server / kill-switch with no co-governance, (iii) no co-capital contribution framework, (iv) no source-escrow for JV-dissolution scenarios. "NetLine has no risk in this deal" is the critical asymmetry: *they invest zero new capital*, so we own the negotiating position to demand a true JV structure.

**Failure 2 — Confidentiality leak in outbound draft.** The session-52-mid Russian draft letter named "GR через Сакен ага" and "подписанный NDA с КПСиСУ" *as selling-points to the counterparty*. Those are internal context (HOW we operate) not external pitch material (WHAT we deliver). Saken aga is Madi's mentor and the intro channel, not a GR-for-sale asset. Specific private NDAs are not sales collateral. Leak never reached the counterparty — Madi caught it in draft. Never committed to the vault as outbound-framed content (internal references to Saken aga as intro channel are factual substrate and stay). Fix is forward-only.

**Failure 3 — Drafted outbound correspondence in Madi's name without gbrain identity verification.** Signed the session-52-mid draft «Ади» (wrong) instead of «Мади Аязбай» (correct per `pages/entities/madi-profile`). The substrate contains the correct name, signature convention, titles; a single `gbrain.get_page` call would have surfaced it. Failure class: writing outbound in someone's name from memory/phonetic guess instead of from substrate.

---

## Musk-5-step pass on this plan (visible, for audit)

Applied before freezing task list. Deletions were faster than additions.

1. **Make requirements less dumb.** Original mental draft had 9 tasks including "full rewrite of analysis spec" and "new handoff page." Question: are both needed? **No.** Spec rewrite → surgical patch (same info density, less drift risk, less diff to review). Handoff page is a session-close artifact; this is mid-session remediation, not session close — fold into end-of-session standard handoff when the session actually closes.
2. **Delete parts/processes.** Deleted: full-spec-rewrite, separate-handoff-page, pre-commit skill lint for this change (session 51 AP-20 already exercises it). 3 tasks cut.
3. **Simplify.** Three AP codifications → single commit, single version bump, single gbrain timeline entry. Not three round-trips.
4. **Accelerate cycle time.** Tasks 3 (spec patch), 4 (Russian v3), 5 (skill AP codification) have no cross-dependencies — executable in parallel tool calls in a single turn.
5. **Automate.** Auto-sync cron already handles 4-way push; `soao.sh` SessionStart hook already runs scanners. Nothing to automate here.

---

## File map

| # | File | Action | Responsibility |
|---|---|---|---|
| 1 | `pages/specs/netvision-remediation-plan-2026-04-20.md` | **CREATE** (this file) | The plan itself |
| 2 | `pages/specs/netvision-monitoring-whitelabel-analysis-2026-04-20.md` | **PATCH** §1 / §3 / §4 / §6 / §8 / §9 | JV-frame reframe of existing analysis |
| 3 | `pages/communications/letter-to-saken-aga-netvision-v3-2026-04-20.md` | **CREATE** | Clean copy-paste Russian v3 letter, tracked as an artifact (not just chat output) |
| 4 | `pages/skills/session-operating-contract/SKILL.md` | **PATCH** — 3 new APs + version bump + Timeline | Codify 3 failures |
| 5 | `pages/entities/netline.md` | **MINOR PATCH** — add JV-frame note in the 2026-04-20 update section | Keep entity page consistent with new analysis frame |
| 6 | `pages/projects/satory-expansion-3-regions.md` | **MINOR PATCH** — update banner to reflect JV-frame reframe | Keep project-level status consistent |

**Deleted from candidate file list** (Musk step 2):
- ~~Separate session handoff page~~ — fold into standard session-close handoff when session actually closes
- ~~New `outbound-correspondence-discipline` skill~~ — doctrine belongs in `session-operating-contract`, not in a skill-sprawl fork

---

## Task sequence

### Task 1 — Write and save this plan file (DONE)

**Files:** Create `pages/specs/netvision-remediation-plan-2026-04-20.md`

- [x] **Step 1:** Write the plan file with all 7 tasks, spec coverage, Musk pass, file map.
- [x] **Step 2:** Commit immediately (independent of approval) so the plan itself is in the substrate and surviveable across sessions.
- [x] **Step 3:** Present plan to Madi.

### Task 2 — Await Madi approval on plan (HARD GATE)

- [ ] Madi reviews plan. Approves, modifies, or rejects.
- [ ] If approved → proceed to Task 3. If modified → apply + re-confirm. If rejected → stop and draft handoff.

---

### Task 3 — Patch analysis spec with JV / GP-LP reframe

**Files:** Modify `pages/specs/netvision-monitoring-whitelabel-analysis-2026-04-20.md`

- [ ] **Step 1:** Insert new `§0 — Commercial frame (corrected 2026-04-20)` at the top explaining: Nous/Satory = General Partner; NetLine = Technology Partner / LP; 50/50 profit split is baseline; NetLine's zero-new-capital exposure = our negotiating leverage.
- [ ] **Step 2:** Patch §1 "TL;DR": three-points update — (a) scope-gap finding stays, (b) structural frame is JV/GP-LP not licensor, (c) my prior licensor-framed questions were wrong-framed.
- [ ] **Step 3:** Patch §3 "Red flags": mark R1 (kill-switch), R2 (license-server), R4 (RUB), R5 (pilot funding), R8 (scope mismatch) — severity revised under JV frame. MAP floor = primary structural break from JV (new R0, highest severity).
- [ ] **Step 4:** Patch §4 "Green flags": G1-G7 retained but reframed under JV lens (the 50% royalty is NOT a compromise — it IS the JV split and is consistent).
- [ ] **Step 5:** Replace §5 "Five critical clarifications" with v3 questions reframed around JV structure (not licensor concessions).
- [ ] **Step 6:** Rewrite §6 "Recommended next action" — current licensor-framed recommendation is wrong; new recommendation assumes JV counter-proposal.
- [ ] **Step 7:** Rewrite §7 "Decision criteria" — shift from "proceed to NDA if they soften" to "proceed to NDA if they accept JV structural change (MAP removal, tenge, source escrow, co-governance)."
- [ ] **Step 8:** Patch §8 "Broader strategy" — retain Plan A/B/C but recast under JV frame.
- [ ] **Step 9:** Add entry to §9 Open questions: `[model-drift] session-52-mid analysis misframed the deal as licensor-vs-buyer — corrected via writing-plans + gbrain madi-profile re-read. Captured in session-operating-contract AP.`

### Task 4 — Create Russian v3 letter file

**Files:** Create `pages/communications/letter-to-saken-aga-netvision-v3-2026-04-20.md`

- [ ] **Step 1:** Write the letter as a standalone file with YAML frontmatter + bilingual framing context (English note at top explaining the frame, Russian letter body in fenced code-block so it's copy-paste clean).
- [ ] **Step 2:** Letter content:
  - Opening: identifies sender (Мади Аязбай), states that after closer analysis + team review, Madi wants to reframe the conversation before NDA.
  - Section 1: **what model we are proposing** — совместное предприятие / JV where Nous/Satory is the general partner (carries capital + market + execution risk) and counterparty is technology partner (contributes product + engineering); 50/50 profit split; no MAP; tenge; co-governance; source escrow.
  - Section 2: **what we bring as General Partner** — strictly external-pitch-safe items (brand presence / deployed reference installation / language / understanding of KZ gov procurement + banking rassrochka / capital commitment to pilots + deploy / market access to 3 regions). **No mention of Saken aga.** **No mention of specific private NDAs.** **No mention of mentor networks.** These are the HOW, not the WHAT.
  - Section 3: **what we ask from the Technology Partner** — full product scope (Netvision base + PAK THOR + PAK Harpun, not just Netvision Monitoring), source escrow, co-governance of JV entity, tenge pricing, pilots co-funded.
  - Section 4: **5 structural questions** (Q1 sender identity, Q2 full-catalog availability for JV, Q3 continuity + escrow + kill-switch mechanics, Q4 tenge + gov-tender payment timing, Q5 market-size realism).
  - Closing: correct signature «С уважением, Мади Аязбай» (verified from `pages/entities/madi-profile`).
- [ ] **Step 3:** Cross-reference the letter file from `netvision-monitoring-whitelabel-analysis-2026-04-20.md` §6 and from `netline.md` timeline.

### Task 5 — Codify 3 APs into `session-operating-contract`

**Files:** Modify `pages/skills/session-operating-contract/SKILL.md`

- [ ] **Step 1:** Read current version + Timeline format to confirm AP numbering + 3-edit ritual (frontmatter `version:` + H1 title + Timeline entry).
- [ ] **Step 2:** Append 3 new APs:
  - **AP-N — Identity-from-substrate before outbound drafting.** *Rule:* before writing any outbound text signed by a named person (Madi, Smatay, Aleksey, team), query `gbrain.get_page pages/entities/<slug>` for their current name, preferred sign-off, role-title, relevant confidentiality boundaries. No drafting from memory or phonetic transliteration. *Why:* session-52-mid signed "Ади" instead of "Мади Аязбай" because substrate wasn't queried. *How to apply:* first tool call on any outbound-drafting task must be gbrain or Read of the relevant entity page.
  - **AP-N+1 — Scrub internal-context leaks from outbound drafts.** *Rule:* before any outbound-framed text is put in front of user for review or sent, run a leak-check pass for: (a) mentor/introducer names framed as GR assets, (b) specific private NDAs framed as sales collateral, (c) internal operational HOW (how we source clients, who our connections are, where our leverage comes from). These are internal substrate, not external pitch material. *Why:* session-52-mid draft named "GR через Сакен ага" and "NDA с КПСиСУ" as pitches — breach of confidentiality and relationship positioning. *How to apply:* after drafting outbound text, re-read once with the single question "would I send this to a stranger?" — any internal HOW answers yes means it stays.
  - **AP-N+2 — Classify deal structure before commercial analysis.** *Rule:* before producing red-flag / green-flag / question-list analysis of any commercial proposal, classify the intended structure into: (a) pure vendor / buy-sell, (b) licensor + distributor, (c) white-label + royalty, (d) franchise + MAP, (e) joint venture (GP + LP), (f) merger/acquisition. Ask the user explicitly if frame is ambiguous — do not default to the proposal's *stated* structure, ask what the user *wants* the structure to be. *Why:* session-52-mid analyzed a proposal the user intended as JV/GP-LP under a licensor-vs-buyer frame — produced structurally wrong question list and wrong recommendations. *How to apply:* the first paragraph of any proposal analysis must state "frame: X" explicitly. User disagrees → re-analyze before drafting further.
- [ ] **Step 3:** Bump version (SemVer patch or minor, per existing pattern).
- [ ] **Step 4:** Append Timeline entry (one line) referencing this plan + 3 APs.
- [ ] **Step 5:** Push gbrain timeline entry on `pages/skills/session-operating-contract/skill` summarizing the 3 APs + version bump.

### Task 6 — Minor patches for consistency

**Files:** Modify `pages/entities/netline.md` and `pages/projects/satory-expansion-3-regions.md`

- [ ] **Step 1:** `netline.md` 2026-04-20 update section: append one-line note — "*Frame correction 2026-04-20: this deal is being re-approached as a Joint Venture (GP-LP) per Madi's framing, not as licensor-vs-buyer. See [[netvision-remediation-plan-2026-04-20]] + [[netvision-monitoring-whitelabel-analysis-2026-04-20]] §0.*"
- [ ] **Step 2:** `satory-expansion-3-regions.md` banner: update status line to reflect JV frame.

### Task 7 — Commit + 4-way sync + DONE protocol

- [ ] **Step 1:** `git add` the 5-6 modified files, one logical commit with message referencing this plan.
- [ ] **Step 2:** Push to VPS bare; verify 4-way HEAD parity (Mac / VPS bare / VPS wiki / Air).
- [ ] **Step 3:** Verify gbrain ingested the new files + timeline entry on `session-operating-contract`.
- [ ] **Step 4:** Run `tools/soao.sh` or equivalent; confirm GOLDEN.
- [ ] **Step 5:** Report DONE protocol with 4 artifacts (command + output + HEAD + counter-check) + Karpathy 6-axis scorecard.

---

## Spec coverage check (per writing-plans skill self-review)

Requirements from Madi's message, mapped to tasks:

| Madi's requirement | Task(s) |
|---|---|
| "plan everything, put it in the plan and tasks, execute 1 by 1" | Tasks 1-7 (sequenced), Task 2 hard gate |
| "quality 100%, if not stop and start handoff" | Task 7 step 4 — if any scanner/parity fails, stop + write handoff instead of claiming DONE |
| "all saved and synced everywhere with all details" | Task 7 step 2 (4-way), step 3 (gbrain) |
| "find root cause, fix, retry; if worked → new skill" | Failures 1-3 root-caused in §Context; Task 5 codifies all three as APs |
| "use obsidian + gbrain + karpathy" | Task 5 step 5 (gbrain timeline) + RULE ZERO (skill-only, no new LESSON) + Karpathy ratchet applied (every failure → AP) |
| "deep dive audit so nothing missing, atomic, 100% bulletproof, no lying" | Task 7 step 4 (soao); §Context explicit about what failed and what didn't; Task 5 covers the compounding discipline |
| "think like best CTO + Musk + Karpathy + Tan + billion-dollar solopreneur" | §Musk-5-step pass visible (3 tasks deleted); §Standard line; Task 5 applies Karpathy ratchet (3 APs absorbed live) |
| "optimize workflow + questions, evolving" | Task 3 (questions reframed under JV), Task 5 (workflow-layer codification), JV frame becomes precedent for future proposals |
| "long-term thinking and getting better" | APs in Task 5 compound — every future outbound draft, every future proposal analysis, every future signature now guarded by doctrine |

**Placeholder scan:** none — all task steps have concrete file paths, concrete actions, concrete content.

**Type consistency:** skill name `session-operating-contract` used consistently across Task 5 steps. AP numbers left as `AP-N, AP-N+1, AP-N+2` until Task 5 Step 1 reads the current skill file to pick actual numbers.

---

## Timeline

- **2026-04-20** | Plan drafted after three-failure correction from Madi in session 53. Invokes writing-plans skill per Madi's "use your superskills first to plan all" directive. 7 tasks, Musk-pass-applied (3 tasks cut), awaiting approval at Task 2.

## See also

- [[netvision-monitoring-whitelabel-analysis-2026-04-20]] — the analysis being patched
- [[source-netvision-monitoring-whitelabel-proposal-2026-04-20]] — raw proposal
- [[netline]] — probable sender
- [[madi-profile]] — gbrain identity source (Мади Аязбай)
- [[saken-aga-netline-briefing-ru]] — precedent for Russian outbound format (and the 3-product ask that this proposal partially answered)
