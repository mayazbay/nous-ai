---
tier: 3
name: defuddle
version: 1.0.0
description: Extract clean markdown content from web pages using Defuddle CLI, removing clutter and navigation to save tokens. Use instead of WebFetch when the user provides a URL to read or analyze, for online documentation, articles, blog posts, or any standard web page. Do NOT use for URLs ending in .md — those are already markdown, use WebFetch directly.
type: skill
id: defuddle
title: "defuddle v1.0.0"
tags: [skill, web-extract, ingest]
date: 2026-05-07
last_updated: 2026-05-07
status: ingested
related: ["[[RESOLVER]]", "[[AUDIT-kepano-obsidian-skills-eval-2026-05-07]]"]
source: kepano/obsidian-skills @ github.com/kepano/obsidian-skills
---

# defuddle v1.0.0

Use Defuddle CLI to extract clean readable content from web pages. Prefer over WebFetch for standard web pages — it removes navigation, ads, and clutter, reducing token usage.

If not installed: `npm install -g defuddle`

## Usage

Always use `--md` for markdown output:

```bash
defuddle parse <url> --md
```

Save to file:

```bash
defuddle parse <url> --md -o content.md
```

Extract specific metadata:

```bash
defuddle parse <url> -p title
defuddle parse <url> -p description
defuddle parse <url> -p domain
```

## Output formats

| Flag | Format |
|------|--------|
| `--md` | Markdown (default choice) |
| `--json` | JSON with both HTML and markdown |
| (none) | HTML |
| `-p <name>` | Specific metadata property |

## When NOT to use

- URLs ending in `.md` → already markdown, use `WebFetch` directly.
- Authenticated/private URLs → defuddle won't authenticate; use a dedicated MCP tool (gh, etc.) instead.
- GitHub repos → use `gh api`/`gh repo view` instead of fetching the rendered HTML.

## Provenance

Mirrored from `kepano/obsidian-skills` (Stephan Ango / Obsidian product lead) on 2026-05-07. See [[AUDIT-kepano-obsidian-skills-eval-2026-05-07]] for evaluation rationale and the 4 skills that were deferred or skipped.

## Timeline

- **2026-05-07** | v1.0.0 — installed from kepano/obsidian-skills bundle. defuddle CLI not yet installed in this environment; run `npm install -g defuddle` before first invocation. (Per [[AUDIT-kepano-obsidian-skills-eval-2026-05-07]].)
