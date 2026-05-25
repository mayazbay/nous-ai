---
type: system
title: "GitHub Automation State"
date: 2026-04-28
status: active
tags: [github, blacksmith, clawsweeper, gstack, automation, ci]
related:
  - github-operating-policy-2026-04-28
  - factory-ops
  - infrastructure
  - gbrain-ops
---

# GitHub Automation State

## Repository

- Repo: `mayazbay/nous-agaas-private`
- URL: https://github.com/mayazbay/nous-agaas-private
- Visibility: private
- Default branch: `main`
- Collaborators: owner only at creation time
- Mirror type: sanitized snapshot, not raw vault history

## Labels

Created:

- `automation`
- `blacksmith`
- `clawsweeper`
- `proposal-only`
- `gstack`

## Issues

- #1 — Connect Blacksmith burst CI to private mirror: https://github.com/mayazbay/nous-agaas-private/issues/1
- #2 — Evaluate ClawSweeper-style sweeper in proposal-only mode: https://github.com/mayazbay/nous-agaas-private/issues/2
- #3 — Upstream GStack skip-aware skill-check patch: https://github.com/mayazbay/nous-agaas-private/issues/3

## Blacksmith

Current state:

- Workflow exists: `.github/workflows/blacksmith-burst-tests.yml`
- Workflow is active in GitHub.
- No workflow runs exist yet.
- Local portable suite passed on Mac:
  - command: `bash tools/blacksmith_burst_tests.sh`
  - result marker: `BLACKSMITH_BURST_TESTS_OK`

Guardrail:

- Keep `workflow_dispatch` manual-only until the Blacksmith app/runner is connected and one green run proves the private repo path.
- The workflow must stay secret-free.

## ClawSweeper

Observed source pattern from `openclaw/clawsweeper` on 2026-04-28:

- README is the dashboard.
- One markdown report per issue/PR.
- Conservative close policy.
- Maintainer-authored items are protected.
- Open PR-linked issues stay open until the PR resolves.

Nous rollout state:

- Phase 1 is proposal-only.
- No automatic issue closing.
- No Todoist or Notion writes.
- No personal-surface access.

## Current Blockers

- Blacksmith app/runner must be connected to `mayazbay/nous-agaas-private` before the workflow can prove 32-vCPU execution.
- ClawSweeper-style automation needs a proposal-only config and audit artifact before any scheduled run.
- Local GStack checker patch should be upstreamed or deliberately carried; both Mac and Air currently keep the same local `scripts/skill-check.ts` modification at upstream `675717e`.
