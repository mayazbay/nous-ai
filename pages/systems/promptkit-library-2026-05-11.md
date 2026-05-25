---
type: system
id: promptkit-library-2026-05-11
title: "Promptkit/Guide Library Import — 2026-05-11"
date: 2026-05-11
status: active
tags: [system, source-library, executive-circle, promptkit, openbrain, openclaw, codex, gbrain]
related:
  - "PLAN-download-promptkit-ingest-2026-05-11"
  - "AUDIT-download-promptkits-2026-05-11"
  - "openbrain-projection"
  - "karpathy-coding-principles"
---

# Promptkit/Guide Library Import — 2026-05-11

## Why this exists

These files were downloaded source material with opaque filenames. They were not reliably retrievable by Obsidian, gbrain, or OpenClaw until copied into the vault with clear canonical paths.

This page is the retrieval index. The source files are preserved as exact copies under `pages/sources/executive-circle/`.

## Source inventory

| Canonical source | Original file | SHA-256 | Use |
|---|---|---|---|
| [[2026-05-08-the-judge-layer-is-the-product-prompt-kit]] | `/Users/madia/Downloads/20260508-246-promptkit-1.md` | `b649acf3bc1826a1ab8d861a41d3f123c3ac67c2d9bfed5b61c3e9f138cde615` | Prompt set for judge criteria, judge prompts, eval suites, and architecture review. |
| [[2026-05-08-openbrain-judge-extender]] | `/Users/madia/Downloads/20260508-246-guide-main.md` | `9d81001e9cf4ad42d05076361e26db44db046aac5d8516035a6c1ca4c00c82a2` | OpenBrain judge/action architecture reference; not an approved implementation plan by itself. |
| [[2026-05-08-ai-roadmap-build-room-prompt-kit]] | `/Users/madia/Downloads/20260508-eub-promptkit-1.md` | `dc119c432b5811e9d23aecd2975fc9305e50f95a662a0d301cf62b26c943b83b` | Roadmap-to-build-room audit prompts: access map, platform repair playbook. |
| [[2026-05-04-codex-plugins-prompt-kit]] | `/Users/madia/Downloads/20260504-knu-promptkit-1.md` | `f671604855742250c1638a6e7e5d96bd4464bce73d9c893b3e85c0c51590d935` | Codex plugin workflow audit, decision tree, starter plugin, testing checklist. |
| [[2026-05-04-ultimate-codex-plugin-guide]] | `/Users/madia/Downloads/20260504-knu-guide-main.md` | `4cee9de12e6f1df05bc7ce60f3f1bfa24f648ea50fb3538b2a93a8dbb4a3aaf2` | Guide for building skill-first Codex plugins; useful when promoting repeated workflows into plugin form. |
| [[2026-05-04-end-of-trusted-human-code-prompt-kit]] | `/Users/madia/Downloads/20260504-qbn-promptkit-1.md` | `9b263aa668874410372e7c23d988b7e44f40a6e39873fc384522ab5f1a07ba19` | Verification-readiness and eval-quality diagnostics. |
| [[2026-05-03-ob1-agent-memory-for-openclaw-reference-links]] | `/Users/madia/Downloads/20260503-vkv-guide-main.md` | `dfd5caa0f417d13c555dcf8e38b08ae67313eeb330ae0674aabb3deff62ea7f7` | OB1/OpenClaw memory contract reference. Evaluate against existing gbrain/OpenClaw memory path before adoption. |
| [[2026-05-04-work-primitive-semantic-moat-prompt-kit]] | `/Users/madia/Downloads/20260504-eqj-promptkit-1.md` | `148fe4eb131faed2c7be797684bcda3e750189fb3faf13994ff20cc3b5fc2741` | Agent-readiness, trust architecture, and semantic moat prompts. |
| [[2026-04-28-anticipation-gap-prompt-kit]] | `/Users/madia/Downloads/20260428-3x9-promptkit-1.md` | `9a2a73d5f3519601fc35493d383c5aa8f38159fad8fd034e27959ce69e7718f3` | Consumer AI product and delegation audit prompts. |
| [[2026-04-28-ai-calendar-hygiene-guide]] | `/Users/madia/Downloads/20260428-3x9-guide-main.md` | `f8b4a4a436099a1ad0237f280586bba09661e532265a415138f9a5753c49eb00` | Calendar hygiene audit and prevention workflow. Reference only until tied to Google Calendar/Notion/Todoist runbook. |
| [[2026-04-28-thin-ice-job-audit-prompt-kit]] | `/Users/madia/Downloads/20260428-tt3-promptkit-1.md` | `a5a64716666f399f4a4bbe2e2d7754c527a2c50ed5ef30f93387c06828adddf1` | Career/work-risk self-audit prompts. Archive/reference, not factory-critical. |

## Immediate operating decisions

- Promote now: none. These are source materials, not runtime doctrine.
- Use as references now:
  - OpenBrain/OpenClaw: `openbrain-judge-extender`, `the-judge-layer-is-the-product-prompt-kit`, `ob1-agent-memory-for-openclaw-reference-links`.
  - Codex/GStack: `ultimate-codex-plugin-guide`, `codex-plugins-prompt-kit`.
  - Verification doctrine: `end-of-trusted-human-code-prompt-kit`.
  - Product strategy: `work-primitive-semantic-moat-prompt-kit`, `ai-roadmap-build-room-prompt-kit`.
- Archive only until a concrete workflow needs them: `anticipation-gap-prompt-kit`, `ai-calendar-hygiene-guide`, `thin-ice-job-audit-prompt-kit`.

## Guardrails

- Do not implement OpenBrain Judge Extender from the guide without a separate design review against the current OpenBrain projection skill and OpenClaw runtime.
- Do not create new LESSON files from these imports. If a repeated workflow emerges, update the relevant `pages/skills/<skill>/SKILL.md` and gbrain timeline per RULE ZERO.
- Do not treat these source files as proof that the system is working. Working status still comes from live checks: git parity, gbrain retrieval, OpenClaw mount health, and task-result evidence.
- Do not use API-backed model routes for deterministic transforms that can be handled by code.

## Retrieval queries

Use these query strings when checking gbrain/OpenClaw retrieval:

- `OpenBrain Judge Extender action proposal schema provenance labels`
- `Codex plugin guide skill first marketplace entry testing checklist`
- `OB1 Agent Memory for OpenClaw runtime neutral API contracts`
- `End of Trusted Human Code eval quality diagnostic`
- `AI Calendar Hygiene audit prevention workflow`
