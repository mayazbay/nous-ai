---
type: spec
id: SPEC-WEEKLY-DESKTOP-CLEANUP
title: "Weekly Desktop sendables cleanup — archive to vault + iCloud"
tags: [spec, desktop, cleanup, archive, sendables, weekly, icloud]
date: 2026-04-09
source_count: 0
status: draft
last_updated: 2026-04-09
related: [SPEC-LAW-005, ENTITY-MADI]
---

# SPEC: Weekly Desktop Sendables Cleanup

## Why this exists

Madi's working pattern: Claude prepares send-ready artifacts (Word docs, plain-text Telegram bodies, briefing PDFs) and stages them on `~/Desktop/`. Madi then sends them via Telegram/email/WhatsApp on his own time.

After they're sent, two things must happen:
1. **Originals must move into the vault** under `pages/progress/sent-archive/YYYY-WNN/` so they're version-controlled, searchable via `qmd`, and discoverable later.
2. **A copy must also live in the local Mac filesystem** under `~/Documents/Nous-Sent-Archive/YYYY/WNN/` so iCloud syncs them off-device for safety (the vault is git, not iCloud — it needs a separate iCloud-blessed home).

The Desktop must stay clean of stale sendables — otherwise Claude can't tell what's still pending vs. already sent, and the README index becomes a lie.

**Trigger:** On-demand only. Madi says "weekly cleanup" or "архивируй сендаблы" or similar. **Never automatic.** Madi controls cadence.

## Inputs

- `~/Desktop/SENDABLES-README-2026-04-09.md` (or whatever the current dated README is) — the source of truth for what's staged. Each item has a status block (`READY`, `READY (нужно вписать время)`, `STAGED`, etc.).
- Files referenced by the README (Word docs, .txt, .pdf, .docx).
- Madi's verbal/written confirmation per item: "sent" / "cancelled" / "still pending" / "archive anyway".

## Outputs

For each item Madi marks as **sent** or **cancelled**:

1. **Vault archive:**
   ```
   pages/progress/sent-archive/2026-W15/
     ├── INDEX.md                                  # what was archived this week + why
     ├── Keona-Capabilities-for-Roza-2026-04-09.docx
     ├── Daniyar-Telegram-2026-04-09.txt
     └── ...
   ```
   - `INDEX.md` carries the YAML frontmatter (`type: progress`, `id: ARCHIVE-2026-W15`, …) and one block per archived item explaining: original path, source vault page, recipient, send method, send date, sent/cancelled status, any reply notes.
   - The actual files live next to `INDEX.md` (not loose in `pages/progress/`).

2. **iCloud backup:**
   ```
   ~/Documents/Nous-Sent-Archive/2026/W15/
     └── (same files, mirrored)
   ```
   - Same names as the vault copy. iCloud picks them up from `~/Documents/` automatically — no extra work.
   - This is the "if vault git ever dies, I still have the artifacts" insurance layer.

3. **Desktop cleanup:**
   - Remove the archived files from `~/Desktop/`.
   - Rewrite `SENDABLES-README-YYYY-MM-DD.md` (date in filename matches today's run) with only the **still pending** items.
   - Old README is moved into the same vault archive folder under `INDEX-PREVIOUS.md` for traceability.

4. **Wiki sync:**
   - One commit per cleanup run: `chore(sent-archive): weekly cleanup 2026-WNN — N items archived, M still pending`
   - Append `log.md`: `## [YYYY-MM-DD] sync | weekly desktop sendables cleanup, N archived, M pending`
   - Update `pages/progress/claude-memory/MEMORY.md` "Open items" section if any pending items roll over from the previous week.

## Procedure (Claude executes when triggered)

1. **Read** the current `~/Desktop/SENDABLES-README-*.md`. List every item it references.
2. **Ask Madi** for status of each item, in one batch (not one at a time):
   ```
   Sendables status check (4 items):
     1. Roza Keona .docx     — sent / cancelled / still pending?
     2. Daniyar TG .txt      — sent / cancelled / still pending?
     3. NetLine briefing     — sent / cancelled / still pending?
     4. (anything else)      — sent / cancelled / still pending?
   ```
3. **Compute the ISO week number** for today (`date +%G-W%V`) — that becomes the `WNN` in the archive paths.
4. **Create the two destination folders** (vault + iCloud) if they don't exist:
   ```bash
   mkdir -p "pages/progress/sent-archive/2026-W15/"
   mkdir -p "$HOME/Documents/Nous-Sent-Archive/2026/W15/"
   ```
5. **For each item Madi confirmed `sent` or `cancelled`:**
   - `mv` from `~/Desktop/` → vault archive folder
   - `cp` (NOT `mv`) from vault archive folder → iCloud archive folder (so both have a copy; vault is the master, iCloud is the backup)
   - Append to the new `INDEX.md` with status block
6. **Write the new `INDEX.md`** with full YAML frontmatter and a one-paragraph summary at the top.
7. **Rewrite `SENDABLES-README-YYYY-MM-DD.md` on Desktop** with only the still-pending items.
8. **Move the old README** into the vault archive folder as `INDEX-PREVIOUS-README.md`.
9. **Commit + sync** vault. Append `log.md`. Update `MEMORY.md` if rollovers exist.
10. **Report back** to Madi:
    ```
    Cleanup complete (2026-W15):
      ✅ Archived 3 items: Roza.docx, Daniyar.txt, NetLine.docx
      ⏳ Still on Desktop (pending): (list)
      📂 Vault: pages/progress/sent-archive/2026-W15/
      ☁️ iCloud: ~/Documents/Nous-Sent-Archive/2026/W15/
      📝 Commit: <hash>
    ```

## What Claude must NEVER do here

- ❌ Never auto-trigger this without explicit user request.
- ❌ Never `rm` an artifact instead of `mv` to archive — even cancelled items must end up archived for traceability (in `cancelled/` subfolder).
- ❌ Never delete the iCloud copy if the vault copy exists, or vice versa — they're paired insurance.
- ❌ Never archive an item Madi hasn't explicitly confirmed status for. If unsure, leave on Desktop and flag as "unconfirmed" in the new README.
- ❌ Never archive artifacts that don't have a source page in the vault — first create the source page, then archive.

## Edge cases

| Case | Handling |
|------|---------|
| Madi says "sent" but file already moved off Desktop manually | Skip the move step, still write the INDEX entry with status `sent (manually moved before cleanup)`. |
| Same item across multiple Desktop README revisions | Only the latest README wins; older READMEs are already in archive folders. |
| Item marked sent but has NO source page in vault | Halt for that item. Create source page first (call it `pages/progress/late-archived-NAME-DATE.md`), then archive. Report to Madi. |
| Two items with the same filename across weeks | Append `-W15` suffix during archive: `Daniyar-Telegram-2026-04-09-W15.txt`. |
| Cancelled item with no replacement | Move to `pages/progress/sent-archive/2026-W15/cancelled/` with reason in the INDEX. |
| ISO week boundary (run on Sunday vs Monday) | Use `date +%G-W%V` (ISO week, treats Monday as start). Document in INDEX which date the run was on. |

## See also

- [[LAW-005-obsidian-master]] — why everything must end up in the vault
- [[website-restore-runbook-2026-04-09]] — example of an artifact that lives on Desktop temporarily
- [[roza-keona-kp-capability-list-2026-04-09]] — first artifact this spec will archive
- [[daniyar-response-draft-2026-04-09]] — second artifact this spec will archive
