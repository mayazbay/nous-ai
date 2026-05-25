---
type: law
id: LAW-018
title: "Pre-send fact-check for outbound partner messages"
status: draft
enforcement: prompt
tags: [law, fact-check, outbound, partner-comms, hallucination-prevention, law-013, law-015]
related: [LAW-013, LAW-008, LAW-015, AUDIT-031]
date: 2026-04-09
last_updated: 2026-04-24
source_count: 0
---

<!-- session 71, 2026-04-24: renumbered from LAW-016 → LAW-018 to resolve ID collision with LAW-016-website-deployment-lock (newer, reviewed, cited everywhere in CLAUDE.md). This file keeps the same title + content; only the ID changes. Backlinks in command-center/SKILL.md, satory-dashboard/SKILL.md, website-deploy/SKILL.md, _gbrain/RESOLVER.md updated in the same commit. -->

# LAW-018: PRE-SEND FACT-CHECK FOR OUTBOUND PARTNER MESSAGES

Status: **DRAFT — pending Madi approval**
Enforcement: Prompt-level. Candidate for TaskCompleted hook Gate 9 (AUDIT-026 Phase 2 expansion).
Drafted: 2026-04-09 evening by the session that rebuilt satory.nousagaas.com with routing, responding to AUDIT-031.

## The Law

Every outbound partner message — email, Telegram, letter, proposal, brief, call cheat sheet — that contains factual claims MUST be verified claim-by-claim **before** it is handed to the user for copy-paste or sending.

A "factual claim" is any specific, falsifiable assertion. Numbers, dates, statuses ("we asked on X", "we have Y", "they have not delivered Z"), deliverable states, names, addresses, prices, headcounts, URLs, endpoints, counts, percentages, uptime figures — all count. Opinions and recommendations do not count.

## Rules

1. **Produce a verified-claims table alongside the draft.** One row per factual claim. Columns: `claim`, `source`, `confidence`. The table lives in the draft's vault source page (not the body the user copy-pastes) so the next Claude can audit it.

2. **Each claim's source must be concrete.** A vault file path, a live API response captured in the same session, a specific cell in an xlsx, a specific message from the user in this conversation, or a previous entry in `pages/communications/`. "Seems reasonable" is NOT a source. "Based on my understanding" is NOT a source. A past session's vague memory is NOT a source.

3. **Any claim with confidence below "verified" must be flagged inline** in the draft with `[UNVERIFIED: reason]`, and the user must be asked to confirm or delete it before the draft is finalized for sending.

4. **Numbers, dates, and deliverable-status claims are high-risk.** They require a direct source — no inference, no guessing, no padding. If the source doesn't exist, the claim is REMOVED, not softened. "We asked on April 3" without a logged April 3 message gets DELETED.

5. **If no source can be produced for a claim, the claim is deleted.** Not padded with "probably", not hedged to "we believe", not softened to "we think". Deleted.

6. **Structure padding is not a justification.** A bullet list of 5 asks is not better than 4 if the 5th is invented to balance the list. Produce exactly as many items as you can verify. If the user wants a longer list, say so explicitly: "I can verify 4 items; do you want to ask Madi to confirm a 5th?" — do NOT invent.

7. **The verification table is shown to the user alongside the draft** when the draft is presented, or stored at a discoverable path (e.g. the `verified_against:` field in the draft's frontmatter). The user must be able to scan it and catch anything Claude missed.

8. **When the user pushes back on a specific claim** ("that's вранье"), the response is to CHECK IT — against the vault, the file system, the user's prior messages, or the live system — not to argue or soften. The user being wrong is rarer than the model being wrong; default to investigation, not defense.

## Why

[[AUDIT-031-1c-hallucination-root-cause-2026-04-09|AUDIT-031]] documents the incident:

On 2026-04-09 a previous Claude Code session drafted a Telegram letter to Даниар (Satory CEO) answering his 3 questions. Inside a "what we need from your side" bullet list, the draft invented claim 1c — that Даниар had failed to deliver the VKO monitor config since April 3. Madi had actually SENT that config to Даниар himself, in an xlsx (`Направления_АПК_г_Усть_Каменогорск,_Алтай_и_Риддер.xlsx`) that literally contained columns for installation address, direction of camera, coordinates, and speed limit — the exact three items the bullet said were missing, plus coordinates as a bonus. The xlsx was even rendered on the live dashboard map.

The hallucinated claim would have made Madi look forgetful and accusatory to a partner CEO, and could have damaged the Satory↔Daniyar relationship at a critical integration moment.

Root cause: no enforced verification step for factual claims in outbound partner messages. The model produced a plausible-looking bullet to fill a structural slot in a list, with zero check against the vault, the file system, or Madi's prior messages. Madi caught it only because he re-read the draft himself and recognized the lie the moment the evening session started.

The catch rate of "user re-reads every draft carefully" is high (Madi is sharp) but not 100%, and the cost of a missed partner-hallucination is high (relationship damage with people we need to work with for years). This law trades a small up-front cost (one verification pass per outbound message) for a large risk reduction.

## Applied to ALL agents AND Claude Code

Drafting is everyone's job. Verification is also everyone's job. A draft without a verification record is not finished. Agents that produce partner comms without a verification step are flagged by the TaskCompleted hook (when Gate 9 lands).

## See also

- [[LAW-013-truth]] — honest reporting is the foundation; LAW-016 is its operational enforcement for outbound comms
- [[LAW-008-anti-hallucination|LAW-008]] — related hallucination block
- [[LAW-015-root-cause-evolution|LAW-015]] — every mistake becomes a lesson, and this law IS a lesson becoming a law
- [[AUDIT-031-1c-hallucination-root-cause-2026-04-09|AUDIT-031]] — the incident that motivated this law
- [[telegram-daniyar-letter-2026-04-09-corrected]] — the corrected draft that triggered this work; note its frontmatter `verified_against:` field, which is the first real-world instance of the Rule 2 / Rule 7 pattern
