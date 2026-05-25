---
type: system
id: RUNBOOK-CLAUDE-EXPORT-INGEST
title: "Runbook — Claude.ai Data Export → Obsidian Vault (Pathway 2)"
tags: [runbook, system, claude-ai, export, ingest, pathway-2, karpathy]
date: 2026-04-09
source_count: 0
status: reviewed
last_updated: 2026-04-09
related: [SOURCE-CLAUDE-EXPORT-MEMORIES-2026-04-09, SOURCE-CLAUDE-HISTORY-INDEX-2026-04-09]
---

# Runbook — Claude.ai Data Export → Obsidian Vault (Pathway 2)

**Pathway 2 = recurring export ingest.** Madi triggers a Claude.ai Data Export every few weeks/months from `claude.ai → Settings → Privacy → Export Data`. This runbook turns that raw bundle into compounding vault pages without a single LLM call (factory is off until credits restored).

Companion runbooks:
- **Pathway 1** — live Claude Desktop sessions flow through the `nous-wiki-qmd` MCP server, so co-work conversations read the vault in real time (fix applied 2026-04-09, needs Desktop restart).
- **Pathway 3** — Claude Code sessions write to `pages/progress/claude-memory/` via the LAW-005 symlink, so local terminal work lands in the vault automatically.

Pathway 2 is the **cold-history ingest** that catches everything Pathways 1 and 3 don't.

## Trigger

Run this runbook whenever:
1. Madi pastes a fresh export path (typical: `~/Downloads/data-YYYY-MM-DD-HH-MM-SS-batch-0000/`)
2. More than ~30 days have passed since the last ingest and the free-tier Claude.ai memory has drifted
3. A major project milestone wants a historical snapshot (e.g., pre-launch, post-incident)

Do NOT run it just to "re-sync" — the export is a snapshot, not a live stream. Running it twice on the same bundle is harmless but wasteful.

## Export contents (4 files)

| File | Size (typical) | What it is | Ingest priority |
|---|---|---|---|
| `memories.json` | ~45 KB | `conversations_memory` (biographical free-text) + `project_memories` dict (per-project rich memory) | **P0** — highest signal, drives 10-15 page updates alone |
| `projects.json` | ~30-50 KB | Array of Claude.ai Projects with `description` + doc lists | **P0** — confirms project framing + doc inventories |
| `conversations.json` | 100-200 MB | Full array of all conversations, each with messages | **P1** — rule-based metadata extract only (too large for LLM pass without credits) |
| `users.json` | ~1 KB | Single user record with account UUID | P2 — save for provenance; no content |

## The ingest (exact steps)

### Step 0 — verify vault is healthy

```bash
# From inside the vault directory
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"

# Symlink intact
readlink "/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory"
# Must return: /Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/progress/claude-memory

# Mac ↔ VPS at same git hash
git log --oneline -1
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git log --oneline -1'
```

If anything fails, **HALT** and fix before ingesting — you don't want partial writes diverging from VPS.

### Step 1 — preserve the raw bundle

Copy the small files into `raw/documents/claude-export-YYYY-MM-DD/`. **Do NOT copy `conversations.json`** — it's too large for git (158 MB in the 2026-04-09 bundle).

```bash
EXPORT_DATE="2026-04-09"    # ← update per run
EXPORT_DIR="$HOME/Downloads/data-2026-04-09-08-06-40-batch-0000"   # ← update per run
DEST="/Users/madia/Documents/Projects/Nous AGaaS/Nous/raw/documents/claude-export-${EXPORT_DATE}"

mkdir -p "$DEST"
cp "$EXPORT_DIR/memories.json" "$DEST/"
cp "$EXPORT_DIR/projects.json" "$DEST/"
cp "$EXPORT_DIR/users.json" "$DEST/"
# Intentionally NOT copying conversations.json — reference by original path
```

Write a one-line README in that folder noting the conversations.json path + why it's excluded.

### Step 2 — memories.json + projects.json (manual LLM-free ingest)

This is the **high-value step**. You're extracting ~50 KB of curated free text and turning it into 15-20 entity/project/family/source page updates.

**Reading pattern:**
```bash
python3 -c "import json; d=json.load(open('$DEST/memories.json'))[0]; print(d['conversations_memory'])"
python3 -c "import json; d=json.load(open('$DEST/memories.json'))[0]; [print(k, ':', v[:500]) for k,v in d['project_memories'].items()]"
python3 -c "import json; [print(p['name'], '—', p.get('description','')[:200]) for p in json.load(open('$DEST/projects.json'))]"
```

**Write pattern** — produce, at minimum:
1. One **source page** at `pages/sources/source-claude-export-memories-YYYY-MM-DD.md` that lists provenance, what's in each file, and which pages were updated/created.
2. **Update existing entities** mentioned in the memory (personal contacts, organizations, partners, competitors, mentors). Bump `source_count` and `last_updated`.
3. **Create new entities** for anyone/anything the memory introduces that the vault doesn't have yet. Target 8-15 new pages if the gap is large.
4. **Flag contradictions** using `> CONTRADICTION:` callouts whenever the memory disagrees with an existing page. Never silently retract — always log the conflict.
5. **Family/personal stuff** goes in `pages/personal/` (single-vault rule). Default to one consolidated `family.md` unless a person has enough unique context to warrant their own page.

**Minimum-bar check:** If you touched fewer than **8 pages** on a `memories.json` ingest, you missed something. Re-read the Karpathy rule in CLAUDE.md and look again. The 2026-04-09 baseline was 19 pages touched — aim higher each time.

### Step 3 — conversations.json (rule-based pipeline)

```bash
python3 "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/claude_export_ingest.py" \
  --source "$EXPORT_DIR" \
  --export-date "$EXPORT_DATE" \
  --dry-run

# If counts look reasonable, run for real
python3 "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/claude_export_ingest.py" \
  --source "$EXPORT_DIR" \
  --export-date "$EXPORT_DATE"
```

This writes `pages/sources/claude-history/index-YYYY-MM-DD.md` + `topic-*.md` files. It uses `json.load()` (stdlib) — the 158 MB file expands to ~1-2 GB in memory, which is fine on a Mac as a one-shot.

**Tunable:** `TOPIC_KEYWORDS` in the script. The 2026-04-09 baseline put **167/294** conversations into `other` — that's too high. Each successful re-run should lower that number. Add keywords observed in the top 20 names under `topic-other.md` to the appropriate category list, and re-run. No LLM needed.

### Step 4 — update `index.md`

Append new entries to the **Sources** section under a `### claude-history` sub-header. List:
- The master index page
- Each topic page with its conversation count

This keeps `index.md` navigable by humans and agents. It's how the next session finds the ingest.

### Step 5 — append `log.md` (2 entries minimum)

```markdown
## [YYYY-MM-DD] ingest | claude-ai-export memories.json + projects.json from <path>. Updated: <list>. Created: <list>. Source page: <name>. Total: N updates + M creates + K source pages = X pages touched.

## [YYYY-MM-DD] ingest | claude-history: ran tools/claude_export_ingest.py against conversations.json (N MB, C conversations, <oldest> → <newest>). Wrote P pages to pages/sources/claude-history/. Topic counts: <breakdown>. <Notes on tuning>.
```

Format is strict: `## [YYYY-MM-DD] action | description`. `wiki_lint.py` will reject anything else.

### Step 6 — update `MEMORY.md`

Add a one-line index entry pointing at the new source page:

```markdown
- [Claude.ai export YYYY-MM-DD](../sources/source-claude-export-memories-YYYY-MM-DD.md) — N pages touched, C contradictions logged, K new entities
```

Keep `MEMORY.md` itself lean — per LAW-005 it's the index, not the content.

### Step 7 — commit

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git add pages/ raw/documents/claude-export-YYYY-MM-DD/ index.md log.md pages/progress/claude-memory/MEMORY.md tools/claude_export_ingest.py
git status    # sanity check
git commit -m "ingest | Claude.ai export YYYY-MM-DD — X pages touched"
# Do NOT push unless Madi asked; the LaunchAgent syncs every 60s
```

## Verification checklist

After ingest, confirm:

- [ ] `pages/sources/source-claude-export-memories-YYYY-MM-DD.md` exists and lists all updated + created pages
- [ ] `pages/sources/claude-history/index-YYYY-MM-DD.md` exists with proper frontmatter
- [ ] Each `topic-*.md` has a valid YAML header and a conversation list
- [ ] `index.md` has entries under Sources for both the memories source and the claude-history sub-block
- [ ] `log.md` has two new entries matching the required format
- [ ] `raw/documents/claude-export-YYYY-MM-DD/` contains `memories.json`, `projects.json`, `users.json` (not `conversations.json`)
- [ ] `git status` is clean after commit
- [ ] Mac HEAD matches VPS HEAD after the LaunchAgent sync cycle (check within 2 minutes)

If any check fails, fix before moving on. Half-ingested sources are worse than no ingest — they create contradictions nobody asked for.

## Known gotchas

1. **`ijson` is not installed** on this Mac. The script uses `json.load()` instead. Don't "upgrade" to ijson without running the full ingest to confirm the streaming parser works — the current approach is simpler and proven.
2. **Multi-line frontmatter values.** `yaml_escape` in the script handles quotes in titles, but emoji-laden conversation names can still surprise it. If a topic page fails to parse, read the offending file and quote-escape by hand.
3. **Duplicate conversation names.** Madi has ~3 conversations named "Daily token spending in USD". The script keeps all of them — don't dedupe by name.
4. **Date drift.** The script uses `created_at` from the export, which is UTC ISO-8601 with a `Z` suffix. `parse_iso` strips the `Z`. Do not compare these to Almaty local dates without a timezone conversion.
5. **"Other" bucket is load-bearing.** 167/294 in the 2026-04-09 run were `other`. Don't try to force them into wrong categories — just tune `TOPIC_KEYWORDS` based on observed names and re-run.
6. **`conversations.json` size can break tools.** 158 MB in 2026-04-09. On a machine with <4 GB free RAM the `json.load()` will thrash or crash. Close Chrome before running on anything smaller than a 16 GB machine.
7. **Never put `conversations.json` in git.** It exceeds GitHub's 100 MB hard limit and will abort the push. Reference by original `~/Downloads/...` path in the source page.

## What Pathway 2 does NOT do

- ❌ It does not summarize individual conversations. That requires LLM calls, which require Anthropic credits, which are off.
- ❌ It does not deduplicate memory claims against existing vault content. You (the human/LLM running the runbook) must do the contradiction check by hand.
- ❌ It does not replace Pathway 1 (live MCP). If Claude Desktop still says "I don't have context on X" after an ingest, the MCP is broken — fix that, not this.
- ❌ It does not run automatically. There's no cron. It's a manual, per-export operation.

## When to deep-ingest a specific conversation

The `topic-*.md` pages are metadata only. If one conversation is especially valuable (e.g., a 225-message Paperclip architecture discussion), deep-ingest it by:

1. Extract the full conversation body:
   ```bash
   python3 -c "
   import json
   convs = json.load(open('$EXPORT_DIR/conversations.json'))
   target = [c for c in convs if c['uuid'] == 'UUID-HERE'][0]
   for m in target.get('chat_messages', []):
       sender = m.get('sender') or m.get('role')
       text = m.get('text') or ''.join(c.get('text','') for c in m.get('content',[]))
       print(f'--- {sender} ---\n{text}\n')
   " > /tmp/conv-deep-ingest.txt
   ```
2. Read it by hand (or hand it to a future Claude session when credits are back).
3. Write a `source-claude-conv-<slug>-YYYY-MM-DD.md` summary in `pages/sources/` with all the usual frontmatter + citations.
4. Cross-reference from the relevant topic page's entry for that UUID.

## See also
- [[source-claude-export-memories-2026-04-09]] — the first full Pathway 2 run
- [[source-claude-history-index-2026-04-09]] — first claude-history output
- [[CLAUDE|CLAUDE.md schema]] — the "10-15 pages per source" rule
- [[LAW-005-obsidian-master]] — why everything must land in the vault
