---
type: skill
name: substrate-split-mirroring
id: SKILL-SUBSTRATE-SPLIT-MIRRORING
version: 1.0.0
tier: 2
last_updated: 2026-05-20
date: 2026-05-20
status: active
description: "Split substrate doctrine: keep canonical vault private on VPS, mirror only the public-classified subset (skills, laws, concepts, specs, systems, methodology, tools) to a GitHub public repo via a one-way rsync wrapper gated by a credential scanner. Lets Karpathy/Tan/Finn doctrine compound across the world while keeping legal/tenants/inbox/handoffs/raw secrets on the existing VPS bare repo. Foundation for multi-agent collaboration (codex, opus, /code, future) reading + writing the same brain from any host."
triggers:
  - new agent or session asks 'where is the public version of Nous'
  - user asks how to share skill/law/spec content externally
  - any commit adds credential-shaped content to a PUBLIC-classified path
  - new top-level directory introduced in the vault (needs classification)
  - GitHub public repo gets a PR that needs to flow back to canonical
  - audit reveals private content accidentally synced to mirror
tools: [Bash, Read, Edit, Write]
mutating: true
absorbs_sources:
  - "SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20"
  - "SPEC-BOT-DM-RELAY-2026-05-20"
related: [ceo-hierarchy, karpathy-loop, karpathy-coding-principles, gbrain-ops, session-operating-contract, session-coordination, infrastructure, architecture-quickref, find-skills]
tags: [skill, substrate, github, mirror, compounding, credentials-safety, public-private-split, two-repo, billion-dollar-solopreneur, 2026-05-20]
title: "substrate-split-mirroring v1.0.0"
---

# substrate-split-mirroring v1.0.0

## Purpose

Make the high-leverage IP in Nous AGaaS — skills (Karpathy/Tan/Finn doctrine), laws, concepts, methodology specs, system architecture, public dashboards, source code in `tools/` — compound globally on GitHub, while the secret-bearing parts (legal credentials, tenant data, raw inbox, handoffs that quote internal state, project state) stay on the existing VPS-private substrate. One brain, two boundaries, mechanical enforcement.

**Why this matters:** the substrate is the handshake. The more agents (codex, opus, `/code`, future) and humans read + write the same source, the faster doctrine compounds. Pinning the canonical brain to a private VPS limits compounding to whoever has SSH access. Mirroring the safe-to-share subset to GitHub turns the doctrine layer into a public artifact other engineers can fork, learn from, and contribute back to — without ever risking a credential leak through that channel.

## Current rules (binding)

### 1. Two repos, one logical brain

```
Canonical (full content, including private):
  Mac vault:  /Users/madia/Documents/Projects/Nous AGaaS/Nous/
  Air-wiki:   /Users/madia/nous-agaas/wiki/
  VPS bare:   root@65.108.215.200:/root/nous-agaas/obsidian-wiki.git

Public mirror (derived, public subset only):
  Local clone: ~/Documents/Projects/nous-public-mirror/ (Madi's machine)
  GitHub:      github.com/<owner>/nous-public (private or public repo)
```

The canonical is unchanged. The mirror is a SIBLING git repository (not a clone of the canonical) populated by `tools/sync_public_mirror.sh`. The mirror's git history is independent and per-sync.

### 2. Path classification is path-based with a per-file override

`tools/scan_credentials.py` and `tools/sync_public_mirror.sh` share the SAME `PUBLIC_GLOBS` and `PRIVATE_GLOBS` table (mirrored, see SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20 for canonical mapping). Default for unclassified paths is **PRIVATE** (fail-safe).

A file can override its path-based default via frontmatter:

```yaml
---
visibility: public      # force public on a normally-private path
visibility: private     # force private on a normally-public path
---
```

`visibility: public` does NOT bypass the credential scanner — the scanner still runs.

### 3. Credential scanner is the only mechanical safety net

`tools/scan_credentials.py` is the only mechanical gate that prevents secrets from reaching the mirror. It runs at three layers:

1. Pre-commit hook on canonical (Mac + Air + VPS working copies) — blocks the commit if a public-classified file gains credential-shaped content
2. Inside `tools/sync_public_mirror.sh` — runs `--all-public` on the mirror after rsync, blocks the commit+push if any finding
3. CI on the GitHub public repo (when set up) — defense-in-depth on incoming PRs

If any one layer fails, the public commit is blocked. The other two layers must also be green by design (no single layer should be load-bearing alone).

### 4. Sync is operator-triggered (V0), launchd-triggered (V1+)

V0: Madi runs `bash tools/sync_public_mirror.sh --mirror-dir ~/Documents/Projects/nous-public-mirror` after committing canonical changes he wants public.

V1: a launchd job runs the sync hourly (or on a `git push vps` trigger). Same scanner gate; same idempotency.

The sync command is safe to re-run — if there are no canonical changes since the last sync, it's a no-op.

### 5. Compounding stack (each layer feeds the next)

| Layer | Read from | Write to | Compounding role |
|---|---|---|---|
| Karpathy / Tan / Finn skills | both | both | doctrine that survives session death; lessons rot, skills compound |
| Obsidian vault | both | canonical | humans browse + edit the brain |
| gbrain (VPS) | canonical | n/a | semantic retrieval of canonical (private + public both indexed locally) |
| OpenBrain | canonical (via projection) | canonical | real-time thought capture into `pages/inbox/openbrain/` (PRIVATE by default; promotable via `visibility: public` after manual review) |
| GitHub public mirror | derived from canonical | external collaborators (V1 PRs back to canonical) | world-scale read; v1 contribution flow |
| Pre-commit + CI scanner | both repos | enforces classification | mechanical safety; never trust authors to remember |

### 6. Frontmatter on every public file is non-negotiable

Public files **must** have valid frontmatter: `type`, `id`, `title`, `tags`, `date`, `status`, `last_updated`. The pre-commit drift gate enforces matching `id` + `title` + `# H1` (RULE ZERO heritage). Reason: external readers + CI tooling rely on the structured metadata.

### 7. No new LESSON files anywhere (RULE ZERO heritage)

The pre-commit hook in the canonical (and in the public mirror, when set up) rejects any new `pages/lessons/individual/LESSON-NNN-*.md` file. Skills compound, lessons rot. This rule travels with the mirror.

### 8. PRs back from GitHub require explicit human review

When a third-party contributor opens a PR on the public mirror, it does NOT auto-flow into the canonical. The next session reading the public mirror's `unmerged-prs.md` (CI-generated) reviews each PR, applies the approved changes to the canonical, and runs the sync again to push them back to the mirror. This keeps the canonical in control of every byte that enters its history.

## Operator workflow (Madi's runbook)

### One-time bootstrap

1. Create `github.com/<owner>/nous-public` (private or public — your call based on whether you want world-readable yet).
2. Locally: `git clone <github-url> ~/Documents/Projects/nous-public-mirror`
3. Verify the mirror has a `github` remote: `git -C ~/Documents/Projects/nous-public-mirror remote -v`
4. First sync: `cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && bash tools/sync_public_mirror.sh --mirror-dir ~/Documents/Projects/nous-public-mirror --message "initial: public substrate seed"`

### Routine update (after committing canonical changes you want public)

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git push vps main                                                  # canonical update (unchanged)
bash tools/sync_public_mirror.sh --mirror-dir ~/Documents/Projects/nous-public-mirror
```

### What to do if the scanner blocks a sync

The scanner found a credential-shaped string in a PUBLIC-classified file. Fix in the canonical FIRST, then re-sync.

1. Read the scanner output (file path + line number + masked snippet).
2. Either:
   - Redact the credential and replace with a placeholder (`EXAMPLE_*`, `REDACTED`, `<your-key>`)
   - Move the file to a PRIVATE-classified path (e.g., from `pages/specs/` to `pages/projects/`)
   - Add `visibility: private` to the file's frontmatter
3. Commit the fix to canonical
4. Reset the dirty mirror: `git -C ~/Documents/Projects/nous-public-mirror reset --hard HEAD && git -C ~/Documents/Projects/nous-public-mirror clean -fd`
5. Re-run the sync

## Anti-Patterns

### AP-1 — One-repo-two-remotes via git-filter-repo (rejected design)

**Pattern:** Use a single git repo and try to filter the history at push-time via `git-filter-repo` or a custom pre-push hook that rewrites the diff.

**Why rejected:** (a) any developer mistake — a stray `git reflog` push, a force-push, a misconfigured `pre-receive` hook on the remote — could leak private content via the reflog or via a non-canonical ref. (b) `git push --tags` would need separate filtering. (c) operating in the same repo means a public clone has access to git objects that "shouldn't" be visible; this is a defense-in-depth violation even if the visible refs are filtered. (d) the canonical Mac vault + Air-wiki + VPS bare topology is already battle-tested; replacing it with a single-repo design would be a major migration with little upside.

**Correct pattern:** two repositories, one canonical and one derived. The derived mirror has its own independent git history. Private content cannot reach the mirror because the rsync wrapper only ever WRITES files matching `PUBLIC_GLOBS`.

### AP-2 — Inline redaction at author time instead of mechanical gates (rejected design)

**Pattern:** Tell authors "remember to redact credentials before committing." Trust them.

**Why rejected:** at session-37 a credential pattern appeared in a public-classified spec page because the author copy-pasted a real error message that included a token. The pre-commit hook caught it. Authors will forget; mechanical gates won't. Always prefer scanner enforcement over author discipline.

**Correct pattern:** `tools/scan_credentials.py` runs at three layers (pre-commit, sync wrapper, CI). Adding a fourth (push-time on the GitHub remote via Actions) is allowed for paranoia.

### AP-3 — Promoting an inbox/handoff/project-results file to public without review

**Pattern:** Add `visibility: public` to a `pages/inbox/openbrain/*.md` or `pages/progress/HANDOFF-*.md` file because "the content looks interesting."

**Why rejected:** these path classes are PRIVATE by default precisely because their content frequently quotes raw model output, API responses, and internal state. The scanner will catch the obvious credential patterns, but not all sensitive content is credential-shaped (e.g., a customer name + amount of money is not a credential pattern but is still confidential).

**Correct pattern:** if a HANDOFF or OpenBrain payload contains a generalizable insight worth sharing, distill it into a new skill or concept page (which is PUBLIC by default) and let THAT be the public artifact. Keep the raw artifact private.

### AP-4 — Forgetting to add a new top-level directory to the classification table

**Pattern:** A new top-level dir (e.g., `pages/customer-fingerprints/`) gets added to the vault but not to `PUBLIC_GLOBS` or `PRIVATE_GLOBS`. The default is PRIVATE, so it stays out of GitHub — but the spec page becomes silently incomplete and the next time someone audits the split, they have to re-derive the classification.

**Correct pattern:** when adding a new top-level path, update three things in lock-step:
1. `tools/scan_credentials.py` PRIVATE_GLOBS or PUBLIC_GLOBS
2. `tools/sync_public_mirror.sh` PUBLIC_GLOBS (if the new path is public)
3. `pages/specs/2026-05-20-nous-public-private-split.md` mapping table
4. This skill's "Current rules" table (above)

A future test (`tools/test_split_mapping_consistency.sh`) should mechanically grep the four sources and assert they agree. Tracked as TODO in the spec.

## Detector

```bash
# scanner self-test (built-in 7 cases)
python3 tools/scan_credentials.py --self-test

# scanner full-vault audit on the canonical (must return 0 findings)
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
python3 tools/scan_credentials.py --all-public

# sync dry-run (shows what would be copied without actually committing)
bash tools/sync_public_mirror.sh --mirror-dir ~/Documents/Projects/nous-public-mirror --dry-run
```

Green state for all three is the heartbeat of the split. CI on the public repo (when set up) runs the scanner on every PR + push.

## Evidence trail

<!--
musk-step-2: considered splitting this skill into two pages (one for the
credential scanner, one for the sync wrapper); rejected because they
share a single operator runbook and a single doctrine — forcing future
agents to read two pages to understand one architecture would be net
worse than one larger page they read once.

delete-considered: trimming AP-1 (rejected design) out of the skill body
to reduce surface; kept because the rejected design is operationally
important context for future agents who might propose the same
one-repo-two-remotes architecture again. Without AP-1 documented, the
rejection rationale would have to be rediscovered.
-->

- **2026-05-20** | v0.0.0 → v1.0.0 — Skill created after Madi green-lit Option 3 ("two repos, sensitive-filter layer") from the post-AP-43 audit conversation. Triggered by his question "let shave all the session codex and opus in github so all can work together everywhere, will that be amazing?" Foundation Phase 0 shipped same session:
  - `tools/scan_credentials.py` with 13 pattern classes + 7-case self-test + `--all-public` sweep (commit `83f6f57b`)
  - `pages/specs/2026-05-20-nous-public-private-split.md` full architecture spec (commit `83f6f57b`)
  - `tools/sync_public_mirror.sh` one-way rsync wrapper with scanner gate (commit `605a187e`)
  - Full-vault `--all-public` audit returned 0 findings (the entire public-classified vault subset is already clean)
  - No new LESSON file (RULE ZERO).
  - gbrain-timeline-pending: skill creation, slug becomes available after first canonical commit/import.

## See also

- [[SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20]] — full architecture spec, classification table, sync wrapper contract
- [[SPEC-BOT-DM-RELAY-2026-05-20]] — sibling spec from same session (Asyl relay), demonstrates the compounding-substrate pattern
- [[ceo-hierarchy]] AP-42 / AP-43 — credential safety doctrine (this skill is the infra layer that enforces it)
- [[karpathy-loop]] — operating doctrine + 6-axis scorecard (public IP)
- [[karpathy-coding-principles]] — code-behavior principles (public IP)
- [[gbrain-ops]] — gbrain operation (indexes both canonical halves)
- [[architecture-quickref]] — current Air/VPS/Mac topology (this skill extends it with GitHub)
