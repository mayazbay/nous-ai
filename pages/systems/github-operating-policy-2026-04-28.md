---
type: system
title: "GitHub / Nous Operating Policy"
date: 2026-04-28
status: active
tags: [github, todoist, notion, obsidian, gbrain, blacksmith, clawsweeper, policy]
related:
  - gbrain-ops
  - secrets-management
  - factory-ops
  - infrastructure
---

# GitHub / Nous Operating Policy

## Decision

Madi approved this operating split on 2026-04-28:

- GitHub private mirror: `mayazbay/nous-agaas-private`
- Visibility: private
- Collaborators: none at first
- Push rule: secret scan before every mirror update
- GitHub role: code issues, PRs, CI, Blacksmith, ClawSweeper-style code automation
- Todoist role: Satory business tasks, owners, priorities, next actions
- Notion role: meetings, transcripts, summaries, team context
- Obsidian/wiki + gbrain role: permanent memory, skills, decisions, root causes, source manifests, retrieval

## Ownership Rules

Do not duplicate ownership across tools.

| Surface | Authoritative for | Link-only for |
|---|---|---|
| GitHub | code work, PR review, CI status, sanitized mirror snapshots | business tasks, meeting context, personal memory |
| Todoist | action execution for Satory/team work | permanent doctrine, meeting transcripts, code review |
| Notion | meeting source material and team discussion context | task execution, code CI, permanent skills |
| Obsidian/wiki + gbrain | durable memory, doctrine, root-cause learning, retrieval | live task UI, raw credentials, unreviewed crawler dumps |

## Automation Rules

Blacksmith and ClawSweeper are allowed after a clean private mirror push, but only in proposal mode first.

Allowed before explicit approval:

- run secret-free CI
- open issues
- update README/dashboard status
- label or comment on code issues
- propose issue closure with evidence

Not allowed before explicit approval:

- close issues automatically
- merge PRs
- write to Todoist
- edit Notion
- touch personal projects or personal Notion/Todoist
- mount raw credentials or raw chat databases into agent context

## Mirror Rules

The GitHub mirror is a sanitized snapshot, not raw vault history.

Required before push:

```bash
bash tools/test_github_mirror_secret_scan.sh /path/to/sanitized/snapshot
git status --short
```

The mirror must exclude `.git/`, raw exports, Obsidian workspace/plugin state, caches, databases, `.env*`, auth files, and other secret-bearing or machine-local artifacts.

## Memory Rule

If any GitHub issue, CI failure, Blacksmith result, or ClawSweeper proposal teaches a reusable lesson, do not leave it only in GitHub. Apply RULE ZERO:

1. update the relevant `pages/skills/<skill>/SKILL.md`
2. add a gbrain timeline entry for that skill page
3. link the GitHub issue or PR back to the vault page

This keeps GitHub as execution infrastructure while Obsidian/gbrain remains the second brain.
