---
type: dashboard
id: revenue-blockers
title: "Revenue blockers — what's blocking $25M Satory contract right now"
date: 2026-04-30
status: active
last_updated: 2026-04-30
tags: [dashboard, revenue, blockers, satory, customer-facing, musk-step-2]
related:
  - "[[skills/musk-algorithm/skill]]"
  - "[[skills/karpathy-loop/skill]]"
  - "[[skills/session-operating-contract/skill]]"
---

# Revenue blockers — Satory $25M contract

> **Read this BEFORE any substrate work.** Substrate hygiene compounds. Customer revenue compounds faster. Both matter; this dashboard makes the customer-facing gate visible to every session. Per session-operating-contract Rule 22 (revenue-precedence at session-start).

## Current state (live as of 2026-04-30T22:30 +05)

| Signal | Value | Verdict |
|---|---|---|
| `events.db total_events` | 154,516 | historical data exists |
| `events.db events_last_seen` | **2026-04-05T22:08:05** | 25+ days stale |
| `events.db today_events` | **0** | pipeline dead |
| `events.db today_violations` | **0** | no auto-fines |
| `wg-satory` peer endpoint | (none) | **Satory side never connects in** |
| `wg-satory` latest-handshake | (never) | tunnel never established from their end |
| `ip route` for 10.235.0.0/16 | OK via wg-satory | route exists, no peer |
| `ip route` for 10.170.0.0/16 | MISSING | second camera subnet completely unreachable |
| `satory.nousagaas.com` lock | `index-BSiWURaO.js` | LAW-016 holding; site honestly reports `events_stale: true` |

## The two unblock paths (both blocked on a named human)

### Path A — Asyl (NIT VPN PSK)

**One message, one human.** Forward this text to Asyl:

```
Асыл, нужен PSK + endpoint config для wg-satory. 25 дней без событий по контракту Satory.

Наша сторона (VPS) готова:
- endpoint: 65.108.215.200:51820
- public key: Qufs3RLRWF1zlf/VqnDhnTLaqtjAZGWaPN+/hGjX7jM=
- allowed-ips нашей стороны: 10.99.0.1/32

Нужно от тебя:
- PSK (preshared key)
- ваш public key
- подтверди что ваша сторона коннектится к нашему endpoint

Без этого 51 камера на 10.235.0.0/16 не пушит ни одного события. Контракт $25M ждёт.
```

**On delivery:** 51 cameras on 10.235.x.x push directly to VPS via tunnel. Live data within minutes.

### Path B — Denis (camera-dual-target, no VPN required)

**Doesn't depend on Asyl.** Two-step ladder: probe first, then dual-target.

#### B-step-1 — Egress probe (60 seconds, ZERO risk)

**Forward this to Denis BEFORE the dual-target script.** Tells us in one command whether the Satory network can even reach our endpoint. No camera changes, no config writes, no exposure — just a curl.

```
Денис, перед dual-target нужен один short test (60 сек, ничего не ломает).

Запусти ВНУТРИ Satory сети (с любой машины откуда видишь камеры на 10.235.x.x):

  curl -v --max-time 5 http://65.108.215.200:9080/health

Пришли мне ВЕСЬ вывод — `* Connected to`, `* Trying`, HTTP-код, любая ошибка.

Это даст ответ за 5 секунд: можно ли восстановить data flow или нужен другой подход.

Наша сторона уже готова и проверена:
- :9080 listen — да (isapi_listener.py PID 834871, uptime > 12 часов)
- /health — отвечает HTTP 200 OK за 200ms из внешнего интернета
- firewall — ALLOW 9080/tcp v4+v6
- ожидаемый ответ: HTTP/1.1 200 OK, body "OK"
```

**Decision tree on Denis's curl output:**

| Denis's output contains | Verdict | Next action |
|---|---|---|
| `HTTP/1.1 200 OK` + `OK` body | ✅ Egress works | Run camera-dual-target.sh (next ladder step) |
| `Connection timed out` after 5s | 🟡 Egress blocked at firewall/NAT | Ask Denis if Satory egress allows TCP/9080 outbound; if not, request firewall rule OR fall back to Path A (VPN) |
| `Connection refused` | 🔴 Reaches host but port closed | NOT POSSIBLE if our pre-flight is GREEN — re-verify our `:9080` listener; this means session-state drifted between probe and run |
| `Could not resolve host` | 🔴 DNS broken inside Satory | Ask Denis to use raw IP `65.108.215.200` (already is — so this means /etc/resolv.conf or HTTP proxy interference) |
| `SSL` / `TLS` errors | 🟡 HTTPS-only proxy in path | Confirm Satory egress is HTTP-clean; if proxy mandates HTTPS, expose `:9443` with cert (already TODO) |

#### B-step-2 — Dual-target script (only if B-step-1 returns 200)

**Two-pass protocol — dry-run first, then commit.** The script lives at:
- Vault canonical: [`tools/camera-dual-target.sh`](tools/camera-dual-target.sh) (md5 `36aa93bf`)
- VPS mirror: `/opt/nous-agaas/erap/tools/camera-dual-target.sh` (same md5; original backed up to `.bak.s2148`)
- New flags: `--dry-run` (no PUT, just print plan) + `--limit N` (first N cameras only)

```
Денис, тест прошёл — egress работает. Теперь dual-target в 2 прохода.

Скрипт перенастраивает push-target камер на ДВА endpoint'а:
их BDL/Cerebro + наш VPS. Не ломает их пайплайн, добавляет наш.

ПРОХОД 1 — dry-run на 1 камеру (60 сек, ничего не меняет):

  bash /opt/nous-agaas/erap/tools/camera-dual-target.sh --dry-run --limit 1

Покажет PLAN-строку: какой ID добавит, на какую камеру. Если выглядит ок — следующий шаг.

ПРОХОД 2 — dry-run на ВСЕ камеры (всё ещё ничего не меняет):

  bash /opt/nous-agaas/erap/tools/camera-dual-target.sh --dry-run

Сводка: сколько камер достижимы, сколько уже имеют наш endpoint, сколько изменит.

ПРОХОД 3 — LIVE (PUT changes):

  bash /opt/nous-agaas/erap/tools/camera-dual-target.sh

Целевой endpoint наш VPS: 65.108.215.200:9080/events/camera/hxml
Сетка камер: 51 на 10.235, ~190 на 10.170 (текущий скрипт покрывает 10.235).

Когда пушнут хотя бы 1 событие → events.db → satory.nousagaas.com → unblock.
Откат: для каждой камеры в логах будет ID добавленной записи; удалить через DELETE httpHosts/<id>.
```

**On delivery:** cameras dual-push, our VPS receives independently of VPN state.

#### B-step-3 — ДП forwarding (Madi directive 2026-05-12 14:30 KZT)

Per Madi: *"Денис знает же где платформа стоит? Ему надо маршрут построить до Дп — we must have that!"*

The dual-target in B-step-2 routes camera events to OUR VPS only. But the full pipeline must end at **ДП (Дорожная Полиция / Department of Police)** — the actual recipient of the fines. Without the ДП hop, events arrive at our platform but the fines never reach the customer that pays.

Two possible architectures, both require Denis input to confirm which is canonical:

**Architecture A** — cameras push directly to ДП as a third dual-target entry:
```
Cameras (10.235.*) ──► id=1 БДЛ (10.141.0.104:8581)        [existing]
                  ├──► id=2 our VPS (65.108.215.200:9080)  [B-step-2]
                  └──► id=3 ДП endpoint (IP:port TBD)       [B-step-3 NEW]
```
Denis owns this — adds a third HttpHostNotification entry via the same `camera-dual-target.sh` pattern.

**Architecture B** — our VPS is the forwarder to ДП via SmartBridge → ERAP:
```
Cameras → our VPS → NCAnode sign → SmartBridge → ERAP → ДП
```
We own the ДП hop. Denis confirms Satory side does NOT need to build the route — it's our responsibility through the existing signing/submission chain (NCAnode v3.4.1 on VPS:14579, SmartBridge `esb.sergek.kz/cxf`, KPSISU-S-5827 registration).

**Decision (Madi 2026-05-12 14:33 KZT): BOTH A and B coexist** — cameras dual/triple-target with ДП as id=3 (Architecture A), AND our VPS forwards in parallel via NCAnode → SmartBridge → ERAP → ДП (Architecture B). Redundant delivery: if either path fails, fines still reach ДП through the other. Denis owns the id=3 add; we own the signing/submission chain.

**Finalized message for Denis (forward after B-step-1 egress probe returns HTTP 200):**

```
Денис, по архитектуре полного потока:

Решено: оба пути работают параллельно — (A) камеры пушат напрямую до ДП как id=3 в HttpHostNotification, И (B) наш VPS параллельно подписывает (NCAnode v3.4.1 на VPS:14579) и сабмитит через SmartBridge → ERAP → ДП. Если один путь упадёт — штрафы всё равно дойдут через другой.

От тебя нужно:

1. IP:порт ДП-эндпоинта (приёмник от камер напрямую). Добавлю как id=3 в обновлённый camera-dual-target.sh, ты запустишь — камеры начнут пушать в три места одновременно: id=1 БДЛ (10.141.0.104:8581) + id=2 наш VPS (65.108.215.200:9080) + id=3 ДП.

2. Подтверди что из сети камер (10.235.*) есть сетевой route до ДП IP. Если нет — нужен NAT/route на вашей стороне ИЛИ edge gateway, иначе id=3 будет timeout-ить.

Параллельный путь (B) на нашей стороне уже работает: NCAnode подписывает, SmartBridge через регистрацию KPSISU-S-5827 сабмитит в ERAP, ERAP пушит в ДП. Это резервный канал.

Жду IP:порт ДП-эндпоинта.
```

**Open action (parallel to Denis):** update `tools/camera-dual-target.sh` to accept `--add-target IP:PORT` so id=3 can be added without rewriting the script. Currently the script only adds our VPS as id=2. Sonnet/Mac controller lane may pick this up; otherwise a future cycle.

## Daily check — drop in here every morning

```bash
# Single source of truth — internal port, never via /api/proxy/* (302 redirect)
ssh root@65.108.215.200 'curl -s http://localhost:8090/api/health | python3 -m json.tool' | grep -E "events_last_seen|today_events|events_stale"
```

Expected when unblocked:
- `events_last_seen` advances daily
- `today_events > 0`
- `events_stale: false`

## What this dashboard prevents

- Sessions burning hours on substrate hygiene while revenue is unplugged.
- Each session forgetting Asyl + Denis are the named-people unblock path (Musk Step 1: name the requirement-holder).
- The "factory works, what now?" loop where the answer is "ship to customer" not "audit the audit."

## Why this is THE highest-priority page

The factory is built. gbrain is at 78. Skills compound. **The customer is paying for camera/event ingestion that has not shipped a fresh event in 25 days.** Every other engineering decision is downstream of this.

> *"What's the customer-revenue blocker, and is it being addressed THIS session?"* — first question of every session-start, per session-operating-contract Rule 22.

## See also

- AUDIT-045 (full-factory-blockers-satory-sync-2026-04-27) — earlier audit of same blocker
- `pages/skills/satory-dashboard/SKILL.md` — freshness contract and per-endpoint freshness fields
- `pages/skills/musk-algorithm/SKILL.md` — Step 1: question the requirement, name the person
- `pages/skills/session-operating-contract/SKILL.md` Rule 22 — revenue-precedence at session-start
