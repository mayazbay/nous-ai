---
type: spec
id: SPEC-SATORY-AGAAS-FULL-DISPLACEMENT-2026-04-26
title: "Satory AGaaS full displacement matrix — BDL + Cerebro + autonomous agents"
project: satory
date: 2026-04-26
priority: p0
status: active
tags:
  - satory
  - agaas
  - bdl
  - cerebro
  - replacement
  - autonomy
  - agents
  - vms
  - erap
related:
  - satory-client-operating-system-bdl-cerebro-replacement-2026-04-26
  - bdl
  - cerebro
  - cerebro_bdl_vms_requirements
  - bdl-mergen-violation-card-schema-2026-04-08
  - satory-dashboard/SKILL
---

# Satory AGaaS Full Displacement Matrix — BDL + Cerebro + Autonomous Agents

## Mandate

The target is not "a better website." The target is a Satory AGaaS operating system that replaces everything BDL and Cerebro can do today, then evolves beyond them with AI agents.

Success means:

```text
BDL/Cerebro capability parity
+ live client operations
+ autonomous monitoring/repair/reporting
+ compounding memory in Obsidian/gbrain/skills
+ human sign-off only for legal, budget, political, or irreversible actions
```

This spec is the working scoreboard. Any future task must map to one capability below or be deleted/deprioritized.

## Source Basis

- [[cerebro_bdl_vms_requirements]] — 89 VMS + transport + event-detection requirements.
- [[cerebro_requirements]] — Cerebro core modules.
- [[bdl_features]] — original BDL replacement checklist.
- [[bdl-mergen-violation-card-schema-2026-04-08]] — golden violation-card schema.
- [[audit-briefing-jacub-fura-final-2026-02-17-5ec44fa0]] — Notion-derived Cerebro/BDL briefing.
- [[synthesis-vms-cameras-erap-2026-04-09]] — 65-conversation VMS/camera/ERAP synthesis.
- [[satory-client-operating-system-bdl-cerebro-replacement-2026-04-26]] — client product mandate.

## Capability Layers

### Layer 1 — BDL / Mergen Data Plane

| Capability | What BDL/Mergen covers today | Satory AGaaS replacement target | Current proof needed |
|---|---|---|---|
| APK hardware integration | Hikvision/Dahua APK camera/radar integration | Vendor-agnostic adapters: Hikvision ISAPI, Dahua/OVN, ONVIF, future Keona/NetLine/etc. | One direct event path from camera/APK to Nous DB |
| Camera configuration | Server-side settings, event targets, credentials | Authorized config agent with per-camera state, no BDL dependency, audit log | Config one authorized camera and record before/after |
| Fleet health | Knows which APK/cameras are online/offline | Fresh `/api/proxy/cameras`, last-check age, source-of-truth per camera | Root-cause `0 / 281` online |
| Event ingestion | Receives plate/speed/metadata from APK | `isapi_listener`/event pipeline with raw event capture and normalized schema | Fresh event in DB from live path |
| Violation rules | Speed/red-light/stop-line/lane/etc. | LAW-002 + rule engine mapped to KoAP, configurable per road/camera | Synthetic + live test cases |
| Evidence package | Scene photo, plate crop, metadata, video clip | Evidence storage + retrieval + legal display | One complete violation card with images |
| ERAP handoff | Packages and submits to ERAP | SmartBridge/ERAP queue with signed payload, retries, statuses | Test submission proof or exact blocker |
| Metrology/certification chain | Mergen certificate and calibration metadata | Store certificate references, calibration dates, legal defensibility fields | Certificate inventory linked to cameras |
| Audit trail | Internal BDL lifecycle logs | Append-only event/card/operator/system logs | Show lifecycle history on one card |
| Credentials/control | Holds access and slows transfer | Satory-owned credential registry with guardrails and owner approvals | Credential map without secrets in vault |

### Layer 2 — Cerebro VMS / Operator Plane

| Capability | What Cerebro covers today | Satory AGaaS replacement target | Current proof needed |
|---|---|---|---|
| Live camera feeds | Live VMS for thousands of cameras | Browser VMS with live stream/HLS/RTSP proxy, role-based access | One real camera stream in portal |
| Camera map | Clickable camera map | Map with status, city, camera type, health, events | Map route with fresh data |
| Archive/search | Search by face, plate, time, location | Plate/time/camera/event/person search with export | Search returns real archived event |
| User roles | Police/admin/operator access | Admin/operator/inspector roles and audit log | Auth flow + role test |
| Camera tree/grouping | City/building/group hierarchy | City, road, school, intersection, agency grouping | Tree/filter UI with real inventory |
| Event dashboard | Events and incident logs | Unified event feed across Safe Roads/Safe City | Real event feed, no placeholders |
| Face recognition | Wanted/person list matching | Optional module, legally gated, on-prem/data-sovereign | Scope/legal gate; not default |
| Vehicle analytics | ANPR, type/color/model, route tracking | ANPR + route graph + watchlists | Plate route across cameras |
| Video analytics | crowd, smoke, weapon, motion, object, quality, sound, traffic lights | Modular AI detectors, each with confidence/calibration/evidence | Detector registry and first production detector |
| Reporting | Daily/weekly/monthly, operator/camera reports | Auto reports to Telegram/Obsidian/portal, with anomalies | One daily report with real metrics |
| Exports | Video/screenshots/lists | CSV/PDF/video/image export with Russian chars and evidence hashes | Export proof |
| High availability | Failover, replication, backups | Watchers, backups, restore drills, health dashboards | Restore drill or backup proof |

### Layer 3 — AGaaS Agent Layer

This is where Satory should become better than BDL and Cerebro, not just equal.

| Agent | Mission | Inputs | Outputs | Human sign-off needed |
|---|---|---|---|---|
| CEO Router Agent | Translate Telegram/Notion intent into work queue | Telegram, Notion meetings, Obsidian state | Prioritized tasks, owner, proof request | Only for strategy/political calls |
| Fleet Doctor Agent | Monitor camera health and root-cause outages | camera DB, events DB, logs, network probes | Red/yellow/green diagnosis, repair plan | Before touching cameras/network |
| Event Ingestion Agent | Keep raw events flowing and normalized | ISAPI/ONVIF/webhooks/logs | Fresh event tables, drift alerts | No, unless config change required |
| Violation QA Agent | Validate legal classification and evidence completeness | events, KoAP rules, evidence | pass/fail cards, missing fields | For edge cases / low confidence |
| ERAP Submission Agent | Package, sign, submit, retry | violation cards, ECP signer, queue | submitted/failed/retried statuses | Before production legal submission policy changes |
| VMS Operator Agent | Help operators search, summarize, investigate | portal DB, archive, map, camera state | answers, reports, navigation shortcuts | No for read-only actions |
| Detector Trainer Agent | Improve CV/ANPR models and calibrations | false positives, labeled evidence, GPU | model proposals, metrics, rollback plan | Before model promotion |
| Report Agent | Produce daily/weekly management reports | events, health, task state | Telegram/Obsidian/Notion report | No for routine reports |
| Librarian Agent | Store every decision and skill correctly | all sessions, task results, docs | Obsidian pages, SKILL updates, gbrain timeline | No, but must obey RULE ZERO |
| Task Sync Agent | Keep Satory tasks in Todoist/Notion safely | approved tasks, project guardrails | Satory-only task updates | Yes until write guardrails proven |
| Security/Ops Agent | Watch secrets, access attempts, BDL/Cerebro exposure | logs, credentials inventory, access events | alerts, incident notes | Yes for credential rotations |
| Cost Agent | Keep model/API/infra spend controlled | LiteLLM, OpenClaw, usage logs | daily cost alarm, routing suggestions | No unless disabling paid model |

## Autonomy Ladder

| Level | Meaning | Satory target |
|---|---|---|
| L0 Manual | Human tells every step | Kill this wherever possible |
| L1 Assisted | Agent drafts, human executes | Temporary for legal/vendor work |
| L2 Tool-using | Agent runs read-only checks and reports | Minimum for all monitoring |
| L3 Controlled write | Agent writes docs/tasks/config with guardrails | Target for Obsidian/gbrain/Todoist/Notion |
| L4 Self-repair | Agent detects, fixes, verifies, codifies skill | Target for software/data pipeline |
| L5 Business-autonomous | Agent runs whole operating loop, asks only for approvals | Long-term target; legal/political gates remain human |

Target operating mode:

- Read-only monitoring: L4.
- Obsidian/gbrain memory: L4.
- Website/frontend source changes: L2 until source ownership is proven, then L3.
- Backend camera/ERAP pipeline: L3 with high-risk gates.
- Legal/government/vendor communications: L1/L2 with Madi approval.
- Daily reporting and task creation: L3 once Todoist/Notion write guardrails are proven.

## President Interface

Madi should not babysit. The interface is:

```text
Telegram intent -> CEO Router Agent -> substrate lookup -> task plan -> execution by agents -> proof bundle -> Madi approves only high-risk decisions.
```

Every agent response must include:

1. What changed.
2. What proof was run.
3. Which BDL/Cerebro capability moved closer to replacement.
4. What remains blocked and who owns it.

## Current Gap Snapshot — 2026-04-26

| Area | Status | Why |
|---|---|---|
| Portal live/auth | Green | Locked site renders and authenticates |
| Source ownership | Red/Yellow | Live bundle does not match obvious local source |
| Camera health | Red | API reports `0 / 281` online |
| BDL event/ERAP proof | Yellow/Red | APIs exist; end-to-end proof not re-run here |
| Cerebro VMS parity | Yellow/Red | UI exists but live/archive/analytics parity not fully mapped |
| AGaaS memory loop | Green for Obsidian/gbrain | Skill + project + gbrain timeline working |
| Todoist/Notion writes | Red/Yellow | Write tools not exposed in this session; must be guarded to Satory only |
| OpenClaw runtime doctrine | Green | Air/OpenClaw sees updated `satory-dashboard` skill |

## Execution Order

Musk Step 2: delete work that does not move a replacement capability. Then execute:

1. **Source ownership first** — no website edits until the live source is proven.
2. **Camera health root cause** — `0 / 281` blocks BDL replacement truth.
3. **One BDL-free path** — camera/APK event -> normalized DB -> violation card -> ERAP queue/test submission.
4. **Cerebro parity gap map** — compare route-by-route against the 89 VMS requirements.
5. **AGaaS agent loops** — assign agents for fleet doctor, report, QA, ERAP, librarian.
6. **Task plane** — only after Satory-scoped Todoist/Notion write guards are proven.

## Non-Negotiables

- No "done" without proof.
- No site-deploy until source ownership is proven.
- No personal Todoist/Notion writes.
- No BDL/Cerebro roadmap leaks to incumbent actors without explicit strategy approval.
- No legal submission automation without human-approved policy.
- Every failure becomes SKILL.md + gbrain timeline under RULE ZERO.

## Acceptance Criteria For Full Displacement

The system is "almost fully autonomous" when:

1. Daily 03:00 run shows BDL/Cerebro capability coverage, not just host health.
2. At least one live camera/APK path runs without BDL.
3. At least one complete violation card matches the golden BDL/Mergen schema.
4. ERAP queue can submit in test or has a precise signed blocker.
5. Operators can search, map, review, and report without Cerebro for a defined subset.
6. Agents detect failures, retry, codify root cause, and notify Madi with proof.
7. Madi approves only high-risk decisions; routine monitoring/reporting/tasking is autonomous.
