---
type: system
id: SYS-GSTACK-UPGRADE-STATE-2026-04-28
title: "GStack upgrade state — Mac + Air"
tags: [system, gstack, gbrain, openclaw, skillpack, audit, 2026-04-28]
date: 2026-04-28
status: verified
last_updated: 2026-04-28
related:
  - gbrain-ops
  - karpathy-loop
  - musk-algorithm
---

# GStack Upgrade State — 2026-04-28

## Decision

GStack is updated on both operating hosts:

- Mac: `/Users/madia/.claude/skills/gstack`
- Air: `/Users/madia/nous-agaas/skills/gstack`
- Upstream: `https://github.com/garrytan/gstack.git`
- Commit: `675717e`
- Version: `1.17.0.0`

## Root Cause Found

The first post-upgrade smoke failed for two reasons:

1. GStack templates changed, so generated host skill files needed regeneration.
2. `scripts/skill-check.ts` treated every `SKILL.md.tmpl` as requiring a same-path `SKILL.md`, but the generator intentionally skips `claude/SKILL.md` because `hosts/claude.ts` has `skipSkills: ['claude']`.

Air had one extra environment issue: noninteractive SSH did not include `~/.bun/bin` on `PATH`, so package scripts that invoke `bun` internally failed unless called with `PATH=$HOME/.bun/bin:$PATH`.

## Local Patch

Until upstream absorbs the fix, both Mac and Air have the same local patch in:

`scripts/skill-check.ts`

The checker now reads the Claude host config and treats an intentionally skipped template as a green "skipped for Claude Code" result instead of a missing generated file.

## Verification

Mac:

```bash
cd /Users/madia/.claude/skills/gstack
bun install --frozen-lockfile
bun run gen:skill-docs --host all
bun run skill:check
bun test test/gbrain-detect-install.test.ts test/gstack-gbrain-source-wireup.test.ts test/gbrain-lib-verify.test.ts
```

Air:

```bash
ssh air 'cd ~/nous-agaas/skills/gstack && PATH=$HOME/.bun/bin:$PATH ~/.bun/bin/bun install --frozen-lockfile'
ssh air 'cd ~/nous-agaas/skills/gstack && PATH=$HOME/.bun/bin:$PATH ~/.bun/bin/bun run gen:skill-docs --host all'
ssh air 'cd ~/nous-agaas/skills/gstack && PATH=$HOME/.bun/bin:$PATH ~/.bun/bin/bun run skill:check'
ssh air 'cd ~/nous-agaas/skills/gstack && PATH=$HOME/.bun/bin:$PATH ~/.bun/bin/bun test test/gbrain-detect-install.test.ts test/gstack-gbrain-source-wireup.test.ts test/gbrain-lib-verify.test.ts'
```

Results:

- `skill:check`: pass on Mac and Air.
- Targeted gbrain/GStack tests: 56 pass, 0 fail on Mac and Air.

## Next Action

Create a GitHub issue/PR target for the upstream checker bug before the next GStack update, so the local patch can eventually be deleted and future `git pull --ff-only` stays clean.
