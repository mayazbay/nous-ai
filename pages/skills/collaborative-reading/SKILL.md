---
tier: 3
type: skill
name: collaborative-reading
version: 1.2.0
last_updated: 2026-04-28
status: active
description: "Use when Madi wants to read a book, chapter, PDF, long article, transcript, or source text with OpenClaw/GBrain as a memory-aware thinking partner. Turns nonfiction reading into sourced notes, Madi-specific commentary, project implications, tasks, and new skills without losing provenance or dumping raw copyrighted text. v1.2.0 distinguishes operating import state from optional live dialogue cursor so an already-imported book is not misreported as unfinished."
triggers:
  - read this book with me
  - read chapter by chapter
  - book with gbrain
  - collaborative reading
  - parse this chapter
  - talk to the book
  - extract ideas from this book
  - The Book of Elon
tools: [Bash, Read, Grep]
mutating: true
related: [gbrain-ops, operator-boundaries, media-ingest, ingest, daily-task-manager, satory-revenue-room]
tags: [skill, gbrain, openclaw, reading, books, memory, second-brain]
title: "collaborative-reading v1.2.0"
---

# collaborative-reading v1.2.0

## Purpose

Make nonfiction reading compound inside the second brain. The agent reads with Madi, not at Madi: it uses the full source text, remembers Madi's goals and preferences, comments on why the idea matters to Nous/Satory/family/health, and saves the durable outputs into Obsidian and gbrain.

## Contract

**Inputs:** owned/local PDF, transcript, article, ebook text, or pasted excerpt; optional current question from Madi.

**Outputs:** source-manifested book page, chapter map, reading cursor, commentary tied to Madi's life/company context, extracted decisions/tasks/skills, and gbrain-searchable notes.

**Invariants:**
- Full text is required for book/chapter claims. If text is missing or extraction fails, say exactly what is missing and stop before analysis.
- Obsidian/gbrain stay the durable memory. OpenClaw may retrieve; it does not become the raw archive.
- Quotes are anchors, not the product. For copyrighted/non-public books, do not paste long passages into chat or notes; quote at most short snippets and summarize the rest.
- Reading work must sharpen judgment or revenue. If a reading session produces no project implication, personal preference, decision, task, or skill candidate, say so plainly.

## Phases

### 1. Prove the source

1. Locate the source file or URL.
2. Extract text with a structured tool where possible. OCR only if the PDF is scanned.
3. Save provenance under `pages/sources/<source>/<YYYY>/<slug>.md` or a project-specific equivalent.
4. Register every working artifact with hash and role: original PDF/ebook, OCR output, markdown conversion, extracted text cache. Do not leave a PDF-only record when the active session uses a markdown/text derivative.
5. Write or update a manifest in `pages/sources/manifests/`.
6. If the book is copyrighted, store path/provenance and notes, not a full reproduced copy in a chat-facing note.

### 2. Create the reading state

Create a page with:

- `source`, `source_id`, `captured_at`, `privacy`, `subject`, `project`, `entities`, `retrieval_policy`, `freshness`
- chapter/section map
- reading cursor: current chapter, page/paragraph range, last session date
- open questions Madi wants the book to answer
- links to relevant entities/projects, especially Satory, Nous AGaaS, Musk algorithm, Karpathy loop, sales, family/health boundaries

### 3. Read in small loops

Default loop:

1. Read 1-3 paragraphs or one coherent subsection.
2. Output:
   - short source anchor: chapter/page/paragraph, with a short quote only if needed
   - plain explanation of the idea
   - Madi-specific commentary: why this matters for Satory/Nous/revenue/family/health
   - disagreement or caveat if the book is wrong, dated, or not useful
   - one question to discuss, only when it would actually improve thinking
3. Update the reading cursor.

### 4. Extract durable value

After each chapter or high-signal section, classify outputs:

| Output | Destination |
|---|---|
| Preference about Madi | `pages/personal/` or existing user profile page |
| Business thesis | `pages/concepts/` or relevant project page |
| Satory execution task | Todoist Satory project, if write policy allows; otherwise a vault task proposal |
| Repeated failure mode or rule | relevant `pages/skills/<skill>/SKILL.md` + gbrain timeline |
| Source-only fact | source page with citation |
| Meeting/client implication | relevant tenant/project page |

### 5. Apply operator boundaries

Before starting a deep reading loop, check `operator-boundaries`:

- If local time is after the active quiet-hours gate and the request is not urgent/revenue-critical, save the source and queue the reading session for morning.
- If Madi explicitly overrides with urgency, proceed and record the override in the reading state.

## Output Format

```markdown
Reading: {book/title} -- {chapter/section}
Anchor: {page/chapter/paragraph}

Idea:
{short explanation}

Why it matters for Madi:
{specific connection to Nous/Satory/personal goals}

Action extracted:
{none | task | decision | skill candidate | project note}

Saved:
{paths updated}
```

## Anti-Patterns

### AP-1 -- Talking about a book without the text

Book-title familiarity is not enough. Do not infer chapter content from memory, reviews, or vibes. Source text first, analysis second.

### AP-2 -- Transcript dump instead of reading partner

Raw extraction is not the value. The value is the commentary, connection to Madi's live projects, and durable extraction into tasks/preferences/skills.

### AP-3 -- Raw-life mount bypass

Do not mount a whole library, chat archive, browser profile, or book folder directly into OpenClaw context. Route through source manifests and gbrain indexing per `gbrain-ops` AP-37.

### AP-4 -- Reading that does not compound

If a reading session produces useful insight, save it. If it produces no useful insight, record that honestly and move on. Do not let reading become another untracked token sink.

### AP-5 -- Alternate source artifact drift

If the agent reads a converted `.md`, OCR text, or extracted cache while the manifest records only the original PDF/URL, the librarian now has a false source map. Future agents may cite the wrong artifact, miss the better working text, or believe the reading state is "not started" even after a doctrine import. Fix: every alternate artifact gets a hash, path, role, and preferred-use note in the source page and manifest before analysis continues.

### AP-6 -- Doctrine import confused with interactive reading cursor

If a book has already been converted into runtime doctrine or an operating import, do not call the whole book "not done" just because Madi has not done a conversational chapter-by-chapter read with the agent. Track two states separately:

- **Operating import state:** source proof, chapter map, project implications, tasks/rules/skills extracted.
- **Dialogue cursor:** where Madi and the agent are in an optional live reading session.

Fix: before answering "is the book done?", inspect the source reading state and any operating import artifact. If operating import is complete but dialogue is open, say exactly that.

## Timeline

- **2026-04-28** | v1.1.0 -> v1.2.0 -- Absorbed AP-6 after the Book of Elon state showed "chapter-by-chapter collaborative reading not started" even though `musk-algorithm`, SOUL, and AGENTS already contained the book-level doctrine. Created a separate operating import closure artifact so agents distinguish "runtime doctrine imported" from "optional live dialogue not started." No new LESSON (RULE ZERO).
- **2026-04-27** | v1.0.0 -> v1.1.0 -- Absorbed AP-5 after Book of Elon audit found source provenance drift: the source page tracked only the PDF hash/path and "not started" cursor, while the current Codex task used `/Users/madia/Downloads/The+Book+of+Elon+Free+PDF.md` (9,320-line markdown working text) and prior sessions had already imported book-level doctrine into `musk-algorithm`. Rule: register all alternate artifacts and update reading state before analysis. No new LESSON (RULE ZERO).
- **2026-04-27** | v1.0.0 -- Created from Madi's Gary Tan/OpenClaw/GBrain note about reading nonfiction chapter-by-chapter with an AI that knows the user. Codifies the full-text, source-manifest, memory-aware commentary, and task/skill extraction loop. No new LESSON (RULE ZERO).
