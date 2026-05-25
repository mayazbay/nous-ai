---
type: spec
id: SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20
title: "Nous AGaaS public/private substrate split (GitHub mirror + VPS private)"
tags: [spec, substrate, github, mirror, private-public, compounding, foundation]
date: 2026-05-20
source_count: 0
status: draft
last_updated: 2026-05-20
related: ["[[ceo-hierarchy]]", "[[architecture-quickref]]", "[[karpathy-loop]]", "[[gbrain-ops]]"]

---

# Nous AGaaS public/private substrate split

> **Goal.** Mirror the compounding-value parts of Nous AGaaS (skills, laws, methodology, public specs) to a GitHub repo so every codex/opus/`/code`/future-agent session reads + writes the SAME substrate from anywhere on earth. Keep the secret-bearing parts (credentials, customer data, raw business state) on the existing VPS bare repo and Mac/Air working copies. Two repos, one logical brain.

## Compounding stack (what gets stronger with every commit)

| Layer | Role | Public side | Private side |
|---|---|---|---|
| **Obsidian vault** | Browse + edit by humans | `nous-public/` mirror | full vault on Mac + Air |
| **gbrain** | Semantic search + embeddings | indexes public from GitHub clone | indexes private from VPS bare |
| **OpenBrain** | Real-time thought capture | projects only the SHA of thought payloads to public; raw stays private | full payloads in private |
| **Karpathy doctrine (RULE ZERO)** | Skills compound, lessons don't | every skill bump is a public commit — the world reads Tan/Karpathy/Finn pattern in action | private skills (if any) stay on private remote |
| **GitHub mirror** | Worldwide read + (eventual) contribute | the entire `nous-public` repo | not present — GitHub never sees private substrate |
| **Pre-commit credential scanner** | Foundation safety | every public commit blocked unless scanner returns 0 matches | private commits get the same gate, fail-open is forbidden |
| **CI on public repo** | Doctrine drift, link gates, scanner | runs on every PR + push | n/a (private has the wiki pre-commit hooks already) |

## Path classification (canonical mapping)

### PUBLIC — compounds globally

```
agents/**                        # agent definitions, no secrets
laws/**                          # top-level laws
pages/skills/**                  # 113 files — Karpathy/Tan/Finn IP
pages/laws/**                    # 34 files
pages/concepts/**                # 102 files — vocabulary + methodology
pages/lessons/**                 # 28 files — historical receipts (frozen at ≤129 per RULE ZERO)
pages/specs/**                   # 69 files — design docs (spot-check exclusions, see below)
pages/systems/**                 # 39 files — architecture docs
pages/dashboards/**              # 73 files — metric definitions (values may need redaction)
pages/aliases/**                 # 77 files — name resolution
pages/schemas/**
pages/tools/**
pages/prompts/**
pages/roadmap/**
templates/**
tools/**                         # source code (credentials live in env, never in tools/)
CLAUDE.md
README.md
index.md
```

### PRIVATE — VPS only

```
pages/legal/**                   # 10 files — ERAP creds, certs, NDA artifacts
pages/personal/**
pages/team/**
pages/tenants/**                 # 269 files — customer-specific data
pages/projects/**                # 51 files — internal project state, business secrets
pages/inbox/**                   # 99 files — raw incoming (unfiltered, often quotes)
pages/proof-pack/**              # operator proof packets (may include creds)
pages/exports/**                 # exports of internal state
pages/goals/**                   # 8 files — internal goal state
pages/mercury/**                 # agent memory facts (may include user info)
pages/sources/**                 # 90 files — summaries of raw source documents
pages/task-results/**            # 881 files — raw model outputs with internal context
pages/progress/**                # 549 files — handoffs that quote internal state + API output
pages/audits/**                  # 441 files — audits often quote evidence (move to public per-file after manual review)
pages/decisions/**               # internal decisions
pages/plans/**                   # 25 files — business context
pages/communications/**          # 23 files — internal comms
raw/**                           # 67M — source documents (immutable, immutable IP)
briefs/**                        # 3.3M — internal briefs
tenants/**                       # customer data
projects/**                      # project state
test-results/**                  # test outputs that may include real data
logs/**                          # runtime logs
.env*                            # env files — NEVER commit anywhere
*.key
*.pem
secrets/**
```

### Default — PRIVATE (fail-safe)

Any path not matched above defaults to PRIVATE. New top-level directories require an explicit decision before they can sync public.

### Per-file overrides (frontmatter)

A file can override its default classification via frontmatter:

```yaml
---
visibility: public           # force public even if default is private
# or
visibility: private          # force private even if default is public
---
```

The override is checked AFTER the path-based default. The credential scanner still runs regardless — `visibility: public` does not bypass the scanner.

## Credential scanner contract

`tools/scan_credentials.sh <file...>` returns exit 0 if clean, exit 1 if any match. Patterns checked:

- Telegram bot token: `\d{8,11}:[A-Za-z0-9_-]{30,}`
- OpenRouter / Anthropic / xAI / OpenAI API key shapes: `sk-[A-Za-z0-9-]{40,}`, `xai-[A-Za-z0-9-]{40,}`, `sk-ant-[A-Za-z0-9-]{40,}`
- AWS keys: `AKIA[0-9A-Z]{16}`
- GCP service account: `"private_key": "-----BEGIN` <!-- scanner:allow -->
- SSH private keys: `-----BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY-----`
- Generic high-entropy strings (>32 chars of base64-like) with adjacent `(password|api_key|token|secret)[:=]` indicator
- The CREDENTIAL_HANDOFF_RE family from `command_center.py` (login/password/credential/доступы/etc.) IN A FILE DESTINED FOR PUBLIC

Scanner is run by:
1. `.git/hooks/pre-commit` on every commit (both Mac vault and Air-wiki working copies)
2. `tools/git_push_split.sh` before any push to the public remote
3. CI on the public GitHub repo on every PR + push (defense-in-depth)

Three-layer gate. If any one of them fails, the public commit is blocked.

## Sync wrapper contract

`tools/git_push_split.sh [<rev-range>]`:

1. Resolve `<rev-range>` (default: `@{u}..HEAD`).
2. For each commit in range:
   a. List touched paths.
   b. Partition: PUBLIC bucket (matches public globs + scanner clean) vs PRIVATE bucket (everything else).
   c. If both buckets non-empty: cherry-pick into two new commits with `[public]` / `[private]` prefixes.
3. Push private bucket to `vps` remote (existing, unchanged).
4. Push public bucket to `github` remote.
5. Idempotent: re-running with the same range is a no-op (uses commit message tags to detect already-mirrored commits).

## Multi-substrate compounding integration

### gbrain
- gbrain's VPS instance already indexes the full wiki working copy at `/root/nous-agaas/wiki`. No change.
- Optionally: stand up a gbrain-public instance that indexes only the GitHub clone, for external readers who can't access the VPS.
- The `mcp__gbrain__*` tools continue to work identically; semantic search spans the union for trusted callers.

### OpenBrain
- OpenBrain projection (AP-44) writes `pages/inbox/openbrain/<date>/openbrain-<id>.md`. `pages/inbox/**` is PRIVATE by default — raw thought payloads stay private.
- A future skill can promote vetted OpenBrain payloads to public (e.g., a Karpathy-loop output worth sharing) via the `visibility: public` frontmatter + manual review.

### Obsidian
- `[[wikilink]]` resolution: a public file linking to `[[CRED-...]]` resolves only on machines that have BOTH repos cloned. In the public-only view, the link shows as unresolved (red). This is acceptable — it is an audit signal that a public doc is referencing private substrate, which usually means the reference should be replaced with a redacted summary.
- The vault is one logical tree on Mac + Air (private dominant). The public mirror is read-only-ish on the public side (you write to your local vault, the wrapper splits the push).

### Karpathy doctrine
- RULE ZERO (skills compound, no new LESSON files) applies in the public repo too.
- New skill = public commit by default (skills are doctrine IP, share with the world).
- Skills can opt out via `visibility: private` in frontmatter (e.g., a tenant-specific skill).
- The drift gate (`tools/test_skill_internal_consistency.sh`) runs in CI on the public repo.

## Migration plan

1. **Phase 0 — scanner first** (this session): build + test `tools/scan_credentials.sh`. Run it across the entire vault as a one-shot audit. Any hits get redacted or moved to private. Nothing ships public until the scanner returns 0 across the public subset.
2. **Phase 1 — local pre-commit hook** (this session): install the scanner as `.git/hooks/pre-commit` on Mac + Air + VPS working copies. Block any commit that adds a credential pattern to a public-classified path.
3. **Phase 2 — initial public push** (needs Madi's GitHub repo): once GitHub `nous-public` exists, run `tools/git_push_split.sh --initial` to push the entire public subset as one big squashed commit. Subsequent pushes are normal per-commit.
4. **Phase 3 — CI on public** (next session): GitHub Actions for scanner + skill drift + link gate on every PR + push.
5. **Phase 4 — read-back** (future): if external collaborators contribute, PRs land on public; an Air-side process detects new commits on `github/main`, pulls into the local public mirror, and surfaces them in the next handoff for Madi's review before merging into the canonical wiki.

## Test plan

- `test_credential_scanner_catches_telegram_token` — scanner returns 1 when a public file contains `12345:ABCDEFGH...`
- `test_credential_scanner_ignores_private_paths` — scanner exits 0 on a `pages/legal/*.md` with creds (private path, scanner just warns)
- `test_split_wrapper_idempotent` — running git_push_split twice on the same range pushes once
- `test_split_wrapper_partitions_mixed_commit` — a commit touching both `pages/skills/` and `pages/legal/` becomes two commits, one per remote
- `test_visibility_frontmatter_override` — `visibility: private` on a `pages/skills/` file keeps it off the public push
- `test_public_subset_clean_audit` — full-vault dry run: scanner returns 0 across every PUBLIC-classified file

## Why this is god-level

This combines six compounding loops into one feedback loop:

1. **Karpathy/Tan/Finn skills** — every learning becomes doctrine, doctrine compounds across sessions
2. **gbrain semantic search** — doctrine is retrievable by meaning, not just by name
3. **OpenBrain capture** — thoughts auto-projected into substrate, never lost
4. **Obsidian browsing** — humans navigate the same brain LLMs read
5. **GitHub mirror** — the public layer compounds across the world (other engineers, future hires, even other companies that adopt the pattern)
6. **Pre-commit + CI gates** — the system polices itself; safety is structural, not vibes

The result: a single source of truth that every agent on every host reads and writes, with a safety boundary that's mechanically enforced rather than trust-based, and a public surface that lets the methodology compound past Nous AGaaS itself.

## See also

- [[karpathy-loop]] — operating doctrine + 6-axis scorecard
- [[gbrain-ops]] — gbrain operation + indexing
- [[ceo-hierarchy]] AP-42 / AP-43 — credential safety (this spec is the infra layer that enforces what those APs declare)
- [[architecture-quickref]] — current Air/VPS/Mac topology (this spec extends it with GitHub)
- [[SPEC-BOT-DM-RELAY-2026-05-20]] — sibling spec, also follow-up from today's audit
