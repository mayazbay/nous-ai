---
id: SPEC-APK-STATUS-BOT-A-2026-04-17
type: spec
title: "Spec A — APK Status Bot (@NousAPKstatusbot) — ships this session"
tags: [spec, apk, satory, telegram-bot, jira-webhook, self-heal, cerebro-replacement, req-003, rule-zero]
date: 2026-04-17
source_count: 3
status: draft
last_updated: 2026-04-17
owner: claude-code-mac
related:
  - REQ-003
  - camera-management
  - satory-dashboard
  - infrastructure
  - factory-ops
  - LAW-002
  - LAW-016
  - LAW-018
  - LESSON-102
  - LESSON-107
  - LESSON-109
  - LESSON-123
  - cerebro-bdl-vms-requirements
  - SPEC-MAC-PRIMARY-HA-NEXT-SESSION
---

# Spec A — APK Status Bot (`@NousAPKstatusbot`) — VPS-primary, ships this session

> **Companion spec B (next session):** `SPEC-MAC-PRIMARY-HA-NEXT-SESSION` — Mac Pro primary knowledge layer + gbrain/QMD migration + warm replicas on Air + backup stack. Spec A is designed to run on the current VPS-primary architecture and continue working unchanged after Spec B migrates the knowledge tier.

## 0. Context & goal

**Source material:**
1. Madi + Satory team meeting transcript, 2026-04-17 morning — full Russian discussion with Daniyar, Oset/Denis, Papa (Smatay), Victor Yuschik. Pipeline problem: 153k events in events.db but only 30 of 243 APKs produce plate numbers reliably. Bot asked for to monitor daily.
2. Papa Smatay WhatsApp message, 2026-04-17 11:57:51 / 11:59:28 — formal spec:
   - Daily 7am report (workday starts 8am) for all accessible APKs.
   - Per-APK: (1) no speed when radar present, (2) no plate — always OR sometimes, (3) other problems.
   - Summary at end: "these APKs don't show speed / these APKs don't show plates."
3. Daniyar mid-meeting: webhook to Jira on zero-speed from radar, format + URL TBD.

**Goal:** Replace the manual Excel process Satory uses to detect broken APKs with an autonomous, bulletproof monitoring service. Ship MVP this session. Evolve via Karpathy / Tan skill-compounding (SKILL.md + gbrain timeline, no new LESSON files per RULE ZERO).

**Mapping:** REQ-003 (centralized monitoring of all components) from `cerebro-bdl-vms-requirements`. Business tag `[revenue]` — Cerebra replacement is the Satory revenue path.

## 1. Decisions locked with Madi (this session)

| # | Decision | Value | Rationale |
|---|---|---|---|
| 1 | Scope | B — ЛУ + ПРК (243 APKs with radar). ОВН excluded (no radar → plate-only, defer to later). | Matches transcript "АПК с радаром"; Daniyar Jira-webhook covers radar data. |
| 2 | Failure rule | B (ratio threshold) for MVP, C (baseline-relative) in P2 once we have 14+ days. | Thresholds: <10% = broken, 10–70% = partial, ≥70% = ok. 20-event floor (baseline-adjusted). |
| 3 | Delivery | B — 8am digest + live transition alerts (30-min debounce, 4-h suppress on re-fire, recoveries always sent). | Matches transcript's "24/7 as soon as it falls, we must act." |
| 4 | Recipients | C — single group chat "Nous APK Status" (Madi creates, adds bot + Daniyar + Denis + Papa + whoever). | One channel, everyone sees same state. |
| 5 | Jira webhook | C — generic config-driven webhook interface. Jira plugs in when Daniyar sends URL. | Ships today without blocking on external party. |
| 6 | Backfill | C — April 1 → today + explicit `data_gap` rows for 2026-04-02 → 2026-04-05 (LESSON-102). | Matches Madi's "с 1 апреля" ask + doesn't hallucinate over known outage. |
| 7 | Interactivity | B — push + `/status` `/apk <id>` `/today` `/help`. `/silence` and `/history` in P2. | Day-to-day ops covered without second product. |
| 8 | Host | VPS (same machine as events.db + camera_monitor cron). Self-heal agent on Air. | Aggregator is I/O-bound on events.db; cross-host watcher must be on different machine. |
| 9 | Schedule | 07:00 KZT digest; 10-min aggregator cron; 15-min sentinel. | Digest in hand by 8am. |
| 10 | Tier architecture | Approach 2 (tier split). Tier A Mac-primary (Spec B), Tier B Air 24/7 utilities, Tier C VPS public services. | Mac can't host camera-pushed services (no public IP, sleeps, travels). |
| 11 | Spec split | Two specs (Spec A bot, Spec B HA). | Bot ships today correct; HA gets session it deserves next. |
| 12 | Language | Russian for all user-facing messages. | Satory team language. |

## 2. Data model (apk_health.db — sibling to events.db on VPS)

**Connection pragmas (every process):**
```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
```

**Schema (version 1):**

```sql
CREATE TABLE apk_health_daily (
  date                TEXT NOT NULL,           -- YYYY-MM-DD KZT
  apk_id              TEXT NOT NULL,           -- camera_ip, authoritative per events.db
  apk_type            TEXT NOT NULL CHECK (apk_type IN ('lu','prk','ovn')),
  address             TEXT,
  calibration_valid   INTEGER NOT NULL,
  n_events            INTEGER NOT NULL,
  n_with_speed        INTEGER NOT NULL,
  n_with_plate        INTEGER NOT NULL,       -- plate_confidence > 0 AND plate_number != ''
  n_with_hc_plate     INTEGER NOT NULL,       -- plate_confidence >= 80
  speed_rate          REAL,
  plate_rate          REAL,
  hc_plate_rate       REAL,
  speed_status        TEXT NOT NULL CHECK (speed_status IN ('ok','partial','broken','undetermined','data_gap')),
  plate_status        TEXT NOT NULL CHECK (plate_status IN ('ok','partial','broken','undetermined','data_gap')),
  silence_status      TEXT NOT NULL CHECK (silence_status IN ('ok','broken','undetermined')),
  other_issues        TEXT,                   -- JSON array of issue labels
  computed_at         TEXT NOT NULL,
  PRIMARY KEY (date, apk_id)
);

CREATE TABLE apk_health_current (
  apk_id                TEXT PRIMARY KEY,
  apk_type              TEXT NOT NULL,
  address               TEXT,
  calibration_valid     INTEGER NOT NULL,
  last_event_at         TEXT,
  n_events_24h          INTEGER NOT NULL,
  n_with_speed_24h      INTEGER NOT NULL,
  n_with_plate_24h      INTEGER NOT NULL,
  n_with_hc_plate_24h   INTEGER NOT NULL,
  speed_rate_24h        REAL,
  plate_rate_24h        REAL,
  speed_status          TEXT NOT NULL,
  plate_status          TEXT NOT NULL,
  silence_status        TEXT NOT NULL,
  speed_broken_since    TEXT,
  plate_broken_since    TEXT,
  silence_broken_since  TEXT,
  speed_healthy_since   TEXT,
  plate_healthy_since   TEXT,
  silence_healthy_since TEXT,
  baseline_7d_traffic   INTEGER,              -- median daily events over last 7d
  other_issues          TEXT,
  updated_at            TEXT NOT NULL
);

CREATE TABLE apk_transition_state (
  apk_id              TEXT NOT NULL,
  dimension           TEXT NOT NULL CHECK (dimension IN ('speed','plate','silence')),
  confirmed_status    TEXT NOT NULL CHECK (confirmed_status IN ('ok','partial','broken')),
  candidate_status    TEXT,
  candidate_since     TEXT,
  last_alert_sent_at  TEXT,
  PRIMARY KEY (apk_id, dimension)
);

CREATE TABLE alert_queue (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  kind                TEXT NOT NULL,
  apk_id              TEXT,
  dimension           TEXT,
  target              TEXT NOT NULL,         -- 'telegram:<chat_id>' | 'webhook:<name>'
  payload             TEXT NOT NULL,
  dedup_key           TEXT NOT NULL,
  priority            INTEGER NOT NULL DEFAULT 5,
  status              TEXT NOT NULL CHECK (status IN ('pending','sent','failed')),
  attempts            INTEGER NOT NULL DEFAULT 0,
  max_attempts        INTEGER NOT NULL DEFAULT 6,
  next_attempt_at     TEXT NOT NULL,
  last_error          TEXT,
  enqueued_at         TEXT NOT NULL,
  sent_at             TEXT
);
CREATE UNIQUE INDEX idx_alert_dedup_pending ON alert_queue(dedup_key, target) WHERE status='pending';
CREATE INDEX idx_alert_due ON alert_queue(next_attempt_at) WHERE status='pending';

CREATE TABLE apk_health_transitions (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  apk_id              TEXT NOT NULL,
  dimension           TEXT NOT NULL,
  from_status         TEXT NOT NULL,
  to_status           TEXT NOT NULL,
  confirmed_at        TEXT NOT NULL,
  candidate_seen_at   TEXT NOT NULL,
  alert_queued_id     INTEGER,
  reason_snapshot     TEXT                    -- JSON: n_events, rates at decision time
);

CREATE TABLE sentinel_heartbeat (
  component           TEXT PRIMARY KEY,       -- 'aggregator'|'sender'|'digest'|'ingest'|'self_heal_agent'|'unknown_apk'
  host                TEXT NOT NULL,
  last_ok_at          TEXT NOT NULL,
  last_status         TEXT NOT NULL CHECK (last_status IN ('ok','degraded','down')),
  run_stats           TEXT,
  details             TEXT
);

CREATE TABLE webhook_deliveries (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  alert_id      INTEGER NOT NULL REFERENCES alert_queue(id),
  webhook_name  TEXT NOT NULL,
  url           TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('pending','sent','failed','skipped')),
  http_code     INTEGER,
  response_body TEXT,                         -- truncated to 4 KB
  attempt       INTEGER NOT NULL,
  attempted_at  TEXT NOT NULL,
  duration_ms   INTEGER,
  error         TEXT                          -- auth headers stripped
);

CREATE TABLE self_heal_incidents (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_type     TEXT NOT NULL,
  detected_at       TEXT NOT NULL,
  resolved_at       TEXT,
  outcome           TEXT CHECK (outcome IN ('auto_resolved','escalated_human','still_broken','cancelled')),
  attempts_json     TEXT NOT NULL,
  opus_spend_usd    REAL DEFAULT 0,
  escalated_to      TEXT,
  notes             TEXT
);

CREATE TABLE known_outages (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  start_ts    TEXT NOT NULL,
  end_ts      TEXT NOT NULL,
  reason      TEXT NOT NULL,
  source      TEXT NOT NULL                  -- 'manual' | 'auto_detect'
);

CREATE TABLE config_thresholds (
  key          TEXT PRIMARY KEY,
  value        TEXT NOT NULL,
  description  TEXT,
  updated_at   TEXT NOT NULL
);
-- seeded values:
INSERT INTO config_thresholds VALUES
 ('broken_rate_max',         '0.10', 'rate below this = broken',                datetime('now','+5 hours')),
 ('partial_rate_max',        '0.70', 'rate below this (and above broken) = partial', datetime('now','+5 hours')),
 ('min_events_for_eval',     '20',   'min events in 24h to classify',            datetime('now','+5 hours')),
 ('debounce_minutes',        '30',   'min time candidate must persist',          datetime('now','+5 hours')),
 ('resuppress_hours',        '4',    'suppress re-fire of same transition',      datetime('now','+5 hours')),
 ('ingest_floor_day_30min',  '300',  'min events/30min during 07-22 KZT',        datetime('now','+5 hours')),
 ('ingest_floor_night_30min','30',   'min events/30min during 22-07 KZT',        datetime('now','+5 hours')),
 ('anomalous_speed_kmh',     '300',  'events with speed above this = radar glitch', datetime('now','+5 hours')),
 ('anomalous_event_count',   '15000','events/24h above this = stuck detector',   datetime('now','+5 hours'));

CREATE TABLE _schema_meta (
  version     INTEGER PRIMARY KEY,
  applied_at  TEXT NOT NULL,
  description TEXT
);
INSERT INTO _schema_meta VALUES (1, datetime('now','+5 hours'), 'initial spec-A schema');

-- known outage
INSERT INTO known_outages VALUES
 (1, '2026-04-02T00:00:00+05:00', '2026-04-05T22:08:00+05:00',
  'ISAPI listener silent; cameras re-pointed to BDL only (LESSON-102)', 'manual');
```

**Verified events.db schema (2026-04-17, via `ssh root@VPS sqlite3 .schema`):**
columns used by aggregator: `camera_ip`, `event_time`, `vehicle_speed`, `plate_number`, `plate_confidence`.
existing indexes: `idx_events_plate(plate_number)`, `idx_events_violation(is_violation)`, `idx_events_time(event_time)`.
**missing index (must add pre-deploy):** `(camera_ip, event_time)` composite for aggregator GROUP BY performance. Migration script `tools/apply_events_db_index.sh`.

## 3. Failure detection logic + state machine

### 3.1 Aggregator query (single GROUP BY, not N+1)

```sql
SELECT camera_ip,
       COUNT(*)                                                                        AS n_events,
       SUM(CASE WHEN vehicle_speed > 0 THEN 1 ELSE 0 END)                              AS n_with_speed,
       SUM(CASE WHEN plate_confidence > 0 AND plate_number != '' THEN 1 ELSE 0 END)    AS n_with_plate,
       SUM(CASE WHEN plate_confidence >= 80 THEN 1 ELSE 0 END)                         AS n_with_hc_plate,
       MAX(event_time)                                                                 AS last_event_at,
       SUM(CASE WHEN vehicle_speed > 300 THEN 1 ELSE 0 END)                            AS n_anomalous_speed
  FROM vehicle_events
 WHERE event_time >= datetime('now','+5 hours','-24 hours')
   AND camera_ip != ''
 GROUP BY camera_ip;
```

### 3.2 Classification (per APK, per dimension)

```
if day ∈ known_outages:                     → all statuses = 'data_gap'
elif n_events == 0:                         → silence_status='broken', speed/plate='undetermined'
elif n_events < effective_floor:            → speed/plate='undetermined', silence_status='ok'
else:
    speed_status = 'broken' if speed_rate < 0.10 else
                   'partial' if speed_rate < 0.70 else
                   'ok'
    plate_status = same ladder on plate_rate
    silence_status = 'ok'
```

`effective_floor = max(5, min(20, int(baseline_7d_traffic * 0.5)))`

### 3.3 Other-issue detection (Papa's #3)

Run after primary classification; writes JSON array to `other_issues` column:

| Signal | Label |
|---|---|
| `n_anomalous_speed >= 5` | `"аномальная скорость — радар глючит"` |
| `n_events > anomalous_event_count` (15000) | `"слишком много событий — залипание"` |
| `calibration_valid = 0` | `"метр. сертификат истёк"` |
| `plate_length < 4 OR > 10` in ≥30% of non-empty plates | `"формат номера нестандартный"` |
| `MAX(event_time) - MIN(event_time) < 1h` with `n_events > 100` | `"события в узком окне — возможно дубль"` |

### 3.4 Debounce state machine (per (apk_id, dimension))

```
State:    confirmed_status ∈ {ok,partial,broken}
          candidate_status ∈ {null,ok,partial,broken}
          candidate_since
          last_alert_sent_at

On observation new_status:
  if new_status == 'undetermined' or 'data_gap':
      no-op (no state change)
  elif new_status == confirmed_status:
      clear candidate
  elif new_status != candidate_status:
      candidate_status = new_status
      candidate_since = now
  elif (now - candidate_since) >= 30 min:
      # confirm transition
      prior = confirmed_status
      confirmed_status = new_status
      candidate = null
      decide_and_enqueue_alert(prior, new_status)
      append_forensic_log(prior, new_status, ...)

decide_and_enqueue_alert:
  flapping_count = count_transitions(apk, dim, last_4h)
  if new_status == 'ok' (recovery):
      ENQUEUE recovery alert, no suppress
  elif flapping_count >= 2:
      ENQUEUE flapping alert, priority=3
  elif (now - last_alert_sent_at) < 4h:
      SKIP (genuine re-fire during suppress window)
  else:
      ENQUEUE broken alert, priority=5
  last_alert_sent_at = now
```

### 3.5 Ingest-gap guard (prevents 243-alert storm)

Before any transition detection runs:
```
recent = COUNT events in last 30 min
floor = config.ingest_floor_{day|night}_30min based on now_kz().hour
if recent < floor:
    if not global.ingest_paused:
        enqueue 'ingest_paused' alert
        global.ingest_paused = True
    # still update apk_health_current snapshots, but SKIP transitions + alerts
else:
    if global.ingest_paused:
        enqueue 'ingest_resumed' alert
        global.ingest_paused = False
```

### 3.6 Unknown-APK sweep (end of run)

```sql
SELECT DISTINCT camera_ip FROM events.vehicle_events
 WHERE event_time >= datetime('now','+5 hours','-24 hours')
   AND camera_ip != ''
   AND camera_ip NOT IN (SELECT ip_address FROM registry.cameras)
```
If non-empty → `sentinel_heartbeat` component `unknown_apk`, status `degraded`, details = IP list. Visible in ops next morning.

### 3.7 Atomicity

Every aggregator run wraps all writes in `BEGIN IMMEDIATE ... COMMIT;`. One transaction per run. Partial crash → SQLite rolls back, next cycle retries.

## 4. Telegram surface

### 4.1 Morning digest (07:00 KZT, group chat)

Format matches Papa's 2026-04-17 11:57 WhatsApp requirement exactly:

```
🌅 *Сводка АПК — {date} 07:00*

⚠️ *Всего с проблемами:* {broken_count} из {total_count}

🔴 *Не показывают скорость* ({speed_broken_count})
 1. ЛУ-015 — ул. Абая, 145 (10.170.15.3) — 5 д. (с 12.04)
 ...

🟡 *Не показывают номер — никогда* ({plate_broken_count})
 ...

🟠 *Не показывают номер — иногда* ({plate_partial_count})
 ...

⚫ *Молчат — нет событий* ({silence_broken_count})
 ...

❓ *Другие проблемы* ({other_count})
 • ЛУ-128 — аномальная скорость (иногда >300 км/ч, радар глючит)
 • ⚠ ПРК-007 — метрологический сертификат истёк 12.2024
 ...

✅ *Восстановились за сутки:* {recovered_count}
 ...

📊 *Поток:* OK ({recent_events} соб./30 мин)

───────────────────────────────

📋 *Резюме (для обхода):*

*Не показывают скорость:*
{csv_list_ids} ({count})

*Не показывают номер — всегда:*
{csv_list_ids} ({count})

*Не показывают номер — иногда:*
{csv_list_ids} ({count})

*Другие проблемы:*
{csv_list_ids} ({count})

_/apk <id> — подробности | /today — обновить_
```

If `ingest_paused` is active at send time, prepend:
```
⚠️ *ВНИМАНИЕ:* поток событий приостановлен с {since}.
Данные ниже могут быть неактуальными.
───────────────────────────────
```

Rules:
- Sort broken APKs by `broken_since` ASC (longest-broken first).
- ⚠ prefix for expired-calibration APKs.
- Categories shown only if non-empty.
- If >30 APKs in one category → top-30 + "остальные: /apk broken speed".
- Chunk messages at 4000 chars by category boundary. Max 4 messages per digest at peak.
- MarkdownV2 escape `_*[]()~>#+-=|{}.!` in dynamic content.

### 4.2 Live alerts

**Broken (first time or after >4h ok):**
```
🔴 *АПК сломался*

*ЛУ-015* — ул. Абая, 145
IP: 10.170.15.3
Что: *нет скорости* (радар молчит)
Событий 24ч: 180 / со скоростью: 12 (6.7%)
Подтверждено: {now}
Сломан с: {broken_since} (~{duration})

/apk 10.170.15.3
```

**Recovered (always sent, never suppressed):**
```
✅ *АПК восстановился*

*ЛУ-015* — ул. Абая, 145 (10.170.15.3)
Что: *скорость снова работает*
Был сломан с {broken_since}, восстановился {now}
Простой: {duration}
```

**Flapping (≥3rd transition in 4h):**
```
⚠️ *ФЛАПИНГ — АПК нестабилен*

*ЛУ-015* — ул. Абая, 145 (10.170.15.3)
Что: *нет скорости* (3-я смена состояния за 4ч)
Скорее всего: физическая проблема (радар, питание, контакт).
Необходима проверка на месте.

/apk 10.170.15.3
```

### 4.3 Ingest-pipeline alerts

**Paused:**
```
⚠️ *Пауза в мониторинге АПК*

Поток событий: {recent}/30 мин (норма: ≥{floor})
Возможные причины:
• isapi\_listener упал
• BDL переставил камеры — см. LESSON-102
• Сетевой разрыв VPS↔Satory

Агент самовосстановления запущен.
*Алерты по отдельным АПК приостановлены* до восстановления потока.
Время паузы: {now}
```

**Resumed:**
```
✅ *Поток событий восстановлен*

Длительность паузы: {paused_duration}
Поток сейчас: {recent}/30мин (норма)
Возобновляю алерты по АПК.
```

### 4.4 Sentinel escalation (via @nousAGaaSbot DM — different host, different token)

```
🚨 *Сбой бота мониторинга АПК*

Компонент: `{component}`
Последний успешный запуск: {last_ok} ({ago} назад, норма ≤20 мин)
Агент самовосстановления: попытался {attempts} — не помогло.
Потрачено: ${spend} / ${budget}
Требуется ручное вмешательство.

ssh root@VPS "journalctl -u apk-aggregator -n 50"
```

### 4.5 Commands

| Command | Response |
|---|---|
| `/status` | One line: "✅ 201/243 работают, ⚠️ 42 не работают (28 нет скорости, 31 нет номера, 5 молчат). Обновлено: HH:MM." |
| `/apk <ip>` | Per-APK panel: address, 24h counts, rates, current status, broken-since, last 5 transitions, calibration flag. |
| `/today` | Re-send 4.1 digest on demand. |
| `/help` | Russian help text. |

### 4.6 Rate-limit + retry

- Telegram rate-limit: 1-second gap between messages to same chat; honors 429 `retry_after`.
- Retry on 5xx/timeout: 1/5/15/60/240/1440 min backoff, max 6 attempts.
- 4xx non-429 → mark `failed`, no retry.
- Idempotency: `dedup_key` UNIQUE per `(key, target, pending)` — re-enqueue = no-op.

## 5. Generic webhook interface (Jira plugs in later)

**Config:** `/opt/nous-agaas/apk-status-bot/webhooks.toml` (600, not git-tracked).

```toml
[[webhook]]
name            = "jira-zero-speed"
enabled         = false                       # flip to true when Daniyar sends URL
url             = "TBD"
method          = "POST"
timeout_seconds = 10
max_attempts    = 6
[webhook.filters]
kinds           = ["transition_broken", "transition_flapping"]
dimensions      = ["speed"]
only_on_broken  = true
[webhook.headers]
Authorization   = "Basic ${JIRA_BASIC_AUTH}"
Content-Type    = "application/json"
[webhook.payload]
template = """..."""                          # Jira REST v3 create-issue shape

[[webhook]]
name            = "slack-ops"                 # example second webhook
enabled         = false
...
```

Template rendering: Jinja2-style `{{var}}` (HTML/JSON-escaped per template type). Env-var interpolation `${VAR}` from `.env`. Config reload is atomic per-alert-drain. HTTPS required (override only for localhost tests).

Every fire → row in `webhook_deliveries` with attempt, HTTP code, duration, response body (truncated 4 KB, auth headers stripped).

## 6. Backfill (one-shot)

`backfill_from_april1.py`:

1. Sanity abort if `events.db < 50,000` rows or `--start < 2026-01-01`.
2. Range: `2026-04-01 → today_kz - 1`.
3. Per-APK 7-day baseline (median daily events).
4. Day-by-day GROUP BY → classify → INSERT OR IGNORE.
5. Manual data-gap rows for 2026-04-02 → 2026-04-05.
6. Auto-gap: any day where `total_events < 5% × median(14_day)`.
7. Write `_schema_meta` + `sentinel_heartbeat` component `backfill`.
8. Emit summary.

CLI: `backfill_from_april1.py --start 2026-04-01 [--end YYYY-MM-DD] [--dry-run] [--force-redo]`.

Idempotent — re-run is safe. Stops at `today_kz - 1`; live aggregator owns today.

## 7. Self-heal agent (Air-hosted, Spec A minimal)

**Scope (Spec A):** watches the APK bot's own components only. Broader infrastructure watch → Spec B.

**Trigger:** reads `sentinel_heartbeat` via SSH every 5 min. On `last_ok_at > 20 min` for a component, opens an incident.

**Playbook (deterministic first, Opus 4.7 second):**
1. `systemctl restart <service>` via SSH.
2. `crontab -l | grep <entry>` check.
3. Opus 4.7 via `/usr/local/bin/claude --print --model claude-opus-4-7 --append-system-prompt "SRE agent…" --max-turns 3` with incident context + safe-command whitelist.

**Safety whitelist:** only `systemctl restart|status|is-active`, `journalctl`, `ls`, `stat`, `df`, `ps`, `crontab -l`, `curl http://localhost:*`, SELECT-only `sqlite3` against specific DBs. Forbidden always: `rm`, `mv`, `>`, `dd`, `kill -9`, `docker stop`, `/etc/*` writes, DROP/DELETE SQL.

**Budget per incident:** 3 attempts + $0.50 Opus spend. Daily agent cap $5 (matches existing `claude-code-budget` pattern).

**Escalation:** after cap → @nousAGaaSbot DM to Madi (chat_id 110793056) with exact next-step command. Agent self-disables for that incident until `/heal-reset <component>`.

**Cross-host watching:**
- Air watches VPS components (aggregator/sender/digest/ingest).
- VPS sentinel watches Air `self_heal_agent` heartbeat. If Air silent >30 min, VPS escalates via @nousAGaaSbot.

## 8. Error handling + observability

**Logging:** stdlib JSON formatter. stdout→journald + file rotation (7 days, logrotate).

**Log levels:** DEBUG (env-gated) / INFO / WARNING / ERROR / CRITICAL.

**Metrics (emitted; Langfuse wiring in Spec B):**
`apk_aggregator_run_duration_ms`, `apk_aggregator_rows_written`, `apk_aggregator_ingest_paused`, `apk_alerts_enqueued_total{kind,dimension}`, `apk_alerts_sent_total{target,status}`, `apk_opus_spend_usd`, `apk_sentinel_lag_seconds{component}`.

**Degradation policy (ordered):**
1. events.db stops growing → `ingest_paused` fires, APK transition alerts suppressed.
2. Telegram network down → alerts queue durably, drain on reconnect.
3. Jira 404 → `webhook_deliveries.failed`, Telegram still delivers.
4. Self-heal on Air down → VPS sends alert via @nousAGaaSbot.
5. VPS dies → Spec B (HA) scenario.

**Failure table:** documented in Section 8 of the brainstorming (per-component failure modes, who notices, response). Embedded here as comments in the code modules.

## 9. Testing strategy (pytest gate, ≥30 tests)

Same pattern as `camera-management` skill's 23-test gate. All tests must pass before install on VPS.

Structure: `tests/conftest.py` + `tests/unit/` + `tests/integration/`.
Fixtures: snapshot `events.db` (10k rows, PII-scrubbed), synthetic 10-APK registry, `freezegun` time control.

30 named tests (T01–T30) covering: classifier boundaries, partial bucket (Papa's "иногда"), data-gap handling, state-machine debounce, 4-h suppress, flapping, ingest-paused no-storm, single GROUP BY query, transaction atomicity, unknown-APK, MarkdownV2 escape, Telegram 4000-char chunk, webhook disabled/enabled, env-var interp, secret not logged, dedup unique, exp backoff, self-heal whitelist, $0.50 budget cap, backfill idempotent, `--force-redo`, baseline fallback, `/status` Russian format.

Coverage target: 80% line on classifier/state_machine/alert_sender/webhook.

## 10. Deployment

### 10.1 Layout

VPS `/opt/nous-agaas/apk-status-bot/` — own `.venv`, modules under `apk_status_bot/`, `webhooks.toml` (not git), `tests/`, `Makefile`.
Air `~/nous-agaas/apk-self-heal/` — own `.venv`, modules under `self_heal/`, `tests/`.

### 10.2 Units + crons

systemd `apk-alert-sender.service` (User=deploy, `Restart=always`, `RestartSec=30`, `WatchdogSec=120`, `MemoryMax=256M`, journald).
cron VPS:
- `*/10 * * * *` aggregator
- `0 7 * * *` TZ="Asia/Almaty" digest
- `*/15 * * * *` sentinel
- `0 2 * * *` apk_health.db backup

launchd on Air: `com.nous.apk-self-heal.plist` (KeepAlive, RunAtLoad, env APK_SELF_HEAL_BUDGET_USD=5.00).

### 10.3 .env (VPS `/opt/nous-agaas/.env`, 600 deploy:deploy, never committed)

```
APK_BOT_TOKEN=<from-BotFather-@NousAPKstatusbot>       # Madi holds; injected at deploy time
APK_BOT_GROUP_CHAT_ID=                                  # filled after Madi creates group
APK_BOT_ADMIN_DM_CHAT_ID=110793056
APK_CONFIG_DIR=/opt/nous-agaas/apk-status-bot
APK_HEALTH_DB=/opt/nous-agaas/erap/data/apk_health.db
APK_EVENTS_DB=/opt/nous-agaas/erap/data/events.db
APK_REGISTRY_DB=/opt/nous-agaas/erap/data/camera_health.db
APK_DIGEST_TIME=07:00
APK_DIGEST_TZ=Asia/Almaty
# JIRA_BASIC_AUTH=...        # add when Daniyar sends URL + creds
```

Mirror only `APK_BOT_ADMIN_DM_CHAT_ID` + `APK_SELF_HEAL_BUDGET_USD` to Air's `~/nous-agaas/.env`.

### 10.4 Install runbook

```bash
# VPS
cd /opt/nous-agaas && git clone <repo> apk-status-bot
cd apk-status-bot && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp webhooks.example.toml webhooks.toml && chmod 600 webhooks.toml
# edit /opt/nous-agaas/.env — add APK_BOT_TOKEN
bash tools/apply_events_db_index.sh         # adds (camera_ip, event_time) index
python -m apk_status_bot.db migrate         # creates apk_health.db
python -m apk_status_bot.backfill_from_april1 --start 2026-04-01
systemctl daemon-reload
systemctl enable --now apk-alert-sender
crontab -e   # paste aggregator/digest/sentinel/backup lines
python -m pytest tests/ -v                  # all 30 pass
python -m apk_status_bot.smoke_test         # live-API ping

# Air
cd ~/nous-agaas && git clone <repo> apk-self-heal
cd apk-self-heal && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
launchctl load ~/Library/LaunchAgents/com.nous.apk-self-heal.plist
```

### 10.5 Uninstall (symmetric)

Stop services, disable crons, unload launchd. `apk_health.db` kept read-only as forensic archive.

### 10.6 Rotation / security

- `APK_BOT_TOKEN` rotation: BotFather `/revoke` → update .env on VPS + Air → systemctl restart.
- Jira creds per Atlassian policy.
- SSH key Air→VPS: restricted-command `authorized_keys` entry; rotate yearly.

## 11. Open items (must resolve before or during implementation)

| # | Item | Owner | Blocking? |
|---|---|---|---|
| O1 | Jira URL + auth + payload shape | Daniyar | No (generic webhook ships; Jira flips on via config) |
| O2 | Group chat creation + chat_id | Madi | Yes for digest delivery; bot runs without until then (DM fallback to Madi) |
| O3 | Denis Excel → camera_registry address merge | Denis / Madi | No (address can be empty initially, bot shows IP) |
| O4 | 243 APK access list (85 currently accessible) | Daniyar | No (bot filters to registered-only; grows as access expands) |
| O5 | `(camera_ip, event_time)` composite index on events.db | This spec | Yes (pre-deploy in install runbook) |
| O6 | Empirical ingest floor (P5 of observed 30-min counts) | Backfill step | No (defaults are conservative; refine on day 7) |

## 12. Success criteria (shipping definition)

1. All 30 tests pass on VPS.
2. Backfill produces 16 days × 243 APKs = 3,888 rows, 4 data-gap days recorded correctly.
3. Aggregator run time < 5 s against current events.db (154k rows).
4. `/status` command responds in < 2 s to group-chat query.
5. Digest message composed ≤ 4 chunks; total ≤ 16,000 chars.
6. Live alert latency: from ingestion → Telegram send < 60 s (given 10-min aggregator cadence: p95 ≤ 15 min end-to-end, with 30-min debounce this is expected floor).
7. Self-heal agent demonstrates one auto-recovery in staging (kill `apk-alert-sender` process, observe systemd restart + heartbeat resumes).
8. No secrets committed to git (pre-commit hook check).
9. Wiki + gbrain index this spec on next autopilot cycle.
10. Madi + Papa + Daniyar all receive first digest at 07:00 KZT next day and confirm format matches Papa's WhatsApp spec.

## 13. Relationship to Spec B (next session)

Spec B will deliver:
- gbrain + QMD migration to Mac-primary with Air warm replicas + VPS cold backup.
- Wiki git origin migration (GitHub or Hetzner storage box) removing VPS SPOF.
- Tailscale Mac preauth key (fixes OAuth refresh loop per `tailscale-stability` v1.1.0).
- Broader self-heal agent scope (VPS disk/memory/cert expiry, Langfuse, OpenClaw health).
- Hetzner nightly snapshot + Backblaze B2 weekly offsite.
- VPS disaster-recovery runbook (10-min rebuild via Ansible).

Spec A's bot continues running unchanged after Spec B migrates — it depends only on events.db (VPS) and the public Telegram API, both unaffected by the knowledge-tier migration.

## 14. Rule compliance

- **RULE ZERO (session 35):** no new LESSON files. Any rule learned during implementation → `camera-management` / `satory-dashboard` / `infrastructure` SKILL.md bump + gbrain timeline entry.
- **LAW-005 (Obsidian SoT):** this spec lives in `pages/specs/` and is indexed by gbrain on autopilot + QMD on daily embed.
- **LAW-016 (satory.nousagaas.com lock):** no frontend changes. Bot is Telegram-only UX. Any frontend APK-health visualization = Spec B decision to lift LAW-016.
- **LAW-018 (data contract camera):** this bot is read-only on `vehicle_events`. No ingest filtering. Respected.
- **Karpathy / Tan pattern:** MVP ships, validates against Papa spec, learnings become skill updates — compounding.

## 15. See also

- SPEC-MAC-PRIMARY-HA-NEXT-SESSION — sibling spec B (next session, never authored; historical reference only)
- [[camera-management]] — events.db + isapi_listener + camera_registry upstream
- [[satory-dashboard]] — /api/cameras freshness envelope (LAW-016 context)
- [[infrastructure]] — systemd/cron/launchd patterns
- [[factory-ops]] — OpenClaw + LiteLLM + Opus 4.7 cost budget
- [[LAW-002-autofine]] — 10% violation threshold (plate confidence ≥80%)
- [[LAW-016-satory-website-lock]] — why no new UI today
- [[LAW-018-data-contract-camera]] — save all events, filter at query
- [[LESSON-102-isapi-events-stop-camera-reconfigure-dual-target]] — 2026-04-05 data-gap origin
- [[LESSON-107-raw-protocol-sample-archive]] — raw capture for replay
- [[LESSON-109-iso-timestamp-string-compare-trap]] — datetime, not string compare
- [[LESSON-123-locked-frontend-shape-lock]] — add fields, don't change shape
- [[cerebro_bdl_vms_requirements]] — REQ-003 source
- [[HANDOFF-AUTO-2026-04-17-session-37]] — session 37 atomic audit baseline
