---
type: system
id: todoist-control-plane-register
title: "Реестр контрольной плоскости Todoist"
last_updated: 2026-05-25T06:57:20.805316+05:00
status: active
tags: [todoist, control-plane, tasks, factory, notion, google-drive, gbrain]
---

# Реестр контрольной плоскости Todoist

- Снято: `2026-05-25T06:57:20.805316+05:00`
- Активных задач: `107`
- Недавно завершённых задач: `17`
- Жёстких рисков: `0`
- Активных задач без реального контекста: `0`
- JSON-артефакт: `pages/systems/todoist-control-plane-register.json`
- CSV-артефакт: `pages/exports/todoist-control-plane-register.csv`

## Правило

Todoist — очередь исполнения. Эта страница — детерминированная модель чтения для людей и агентов. Жёсткие структурные ошибки можно чинить автоматически; контекст задач добавляется только из реального источника.

## Счётчики статусов

- `заблокировано`: `20`
- `готово`: `17`
- `не сделано`: `83`
- `в работе`: `4`

## Счётчики контекста

- `есть источник`: `107`

## Счётчики отделов

- `Продажи`: `46`
- `AI-фабрика`: `23`
- `Доставка`: `17`
- `Юристы`: `4`
- `Финансы`: `4`
- `Юр`: `4`
- `Партнёрство`: `3`
- `Technical`: `2`
- `Coordination`: `2`
- `GR`: `1`
- `Техника`: `1`

## Счётчики рисков

- `нет проекта` (`missing_project`): `0`
- `неверный раздел` (`invalid_section`): `0`
- `корневая задача без раздела` (`root_no_section`): `0`
- `подзадача без раздела` (`subtask_no_section_inherited`): `0`
- `нет владельца` (`missing_owner`): `0`
- `нет отдела` (`missing_department`): `0`
- `нет меток` (`missing_labels`): `0`
- `приоритет по умолчанию` (`default_priority`): `0`
- `нет описания/комментария` (`no_description_or_note`): `0`

## API завершённых задач

- Статус: `готово`

## Реестр активных задач

| Статус | P | Проект | Раздел | Владелец | Отдел | Задача | Срок | Контекст | Ссылка |
|---|---:|---|---|---|---|---|---|---|---|
| `заблокировано` | 2 | Фабрика Satory ВКО | 🏗️ Замена BDL | AI-фабрика | AI-фабрика | ГОСТ KalkanCrypt |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9MpPPmPC73w5q) |
| `заблокировано` | 2 | Фабрика Satory ВКО | 🏗️ Замена BDL | AI-фабрика | Доставка | ЕРАП тест с SmartBridge |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9MpHchQcGRqHH) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Асыл | GR | [ERAP] Получить доступ в тестовую среду ЕРАП | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf3RFGwjXF4r4wq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Юристы | Юристы | Goal: Build and prove the Satory AI Factory control plane as a real 24/7 operating system. GOAL: Make Фабрика Satory ВКО operate without Madi babysitting: Telegram group full-chat memory, Todoist task/comment intake, Notion/Google Drive human proof, Obsidian/gbrain/OpenBrain sync, OpenClaw worker execution, Hermes watchdog supervision, and Grok -> GPT/Opus -> cheap-worker model hierarchy all working on live Air. CONTEXT: Repo: /Users/madia/Documents/Projects/Nous AGaaS/Nous. Live host: Air is the 24/7 runtime; Mac is dev/review only. Current HEAD known from Mac/VPS/GitHub: 67ac4b5e. Latest handoff showed Goal Mode green through 2026-05-14 12:00 KZT, including Grok route canary. Command-center v2.11.3 supports Satory-only full-chat observe mode via TELEGRAM_FULL_CHAT_CHAT_IDS, but Air live deploy/env/restart must be verified. Goal Mode v1.0.12 uses grok-reasoning by default for goal-cycle workers; GPT-5.5/Codex is explicit high-judgment escalation. Control-plane sync owns Todoist/Notion/LangSmith/GitHub/register status; Google Drive upload is still blocked by 403 until OAuth/folder permission is fixed. Scope is ONLY Фабрика Satory ВКО. Do not mutate personal Todoist/Notion/projects. CONSTRAINTS: No personal project mutations. No fake Todoist descriptions, fake proof, fake Drive links, or fake “done.” Do not close/delete Todoist tasks unless Notion + Google Drive/human-checkable proof exists. Do not run uncapped AI takeover. Start with capped intake: one AI-owned Satory Todoist task per cycle. Do not make Hermes the router. OpenClaw executes; Hermes supervises/kicks/escalates. Before high-risk implementation decisions, run adversarial review with Grok 4.3/grok-reasoning and Opus 4.7/opus if routes are live. If not live, record blocker and do not pretend. PRIORITY: 1. Prove live Air/Telegram/Todoist/Notion/Drive/GitHub/gbrain/OpenBrain status from commands, not old summaries. 2. Enable full-chat Satory Telegram memory safely: privacy off, group id allowlisted, all group text persisted, only commands/AI: execute. 3. | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfFp3f264xhVmCq) |
| `заблокировано` | 2 | Фабрика Satory ВКО | 📥 Входящие / Разбор | AI-фабрика | AI-фабрика | Goal: SUB-TASKS (one slice per goal-cycle; pick the smallest unblocked one): 1. Tier-0 step 4 — Air reach proof for Mac 127.0.0.1:8080 over Tailscale 100.100.197.19:8080 OR scoped SSH tunnel. Audit to pages/audits/TIER-0-AIR-REACH-PROOF-<YYYY-MM-DD>.md. NO /approve needed (read-only proof). DO FIRST. 2. Tier-0 step 5 — Add LiteLLM local-mlx-coder route alias on Air:4000 mapping to the Mac MLX endpoint. Probe `litellm --test --model local-mlx-coder`. TELEGRAM /APPROVE BEFORE RELOAD. 3. Tier-0 step 6 — ceo-hierarchy SKILL.md v1.8.6 → v1.9.0 via RULE ZERO 3-edit ritual: add AP-25 "Tier-0 local-mac MLX promoted to worker chain" + insert local-mlx-coder BEFORE deepseek-v4-flash in worker fallback chain. TELEGRAM /APPROVE BEFORE COMMIT. 4. Hermes promotion — work the 4 RED proofs from hermes_promotion_runner.py: todoist_canary_proof, notion_canary_proof, gbrain_timeline_proof, cost_receipt. Each gets a small artifact at pages/audits/HERMES-<PROOF-NAME>-<date>.md. On 10/10 GREEN, the runner self-adds AP-26 (or whichever next AP) to ceo-hierarchy via its own RULE ZERO ritual. 5. Run tools/cheap_pool_benchmark.py --log-path pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl --limit 5 comparing deepseek-v4-flash + qwen3-coder-plus + kimi-k2.6 + glm-5.1 + local-mlx-coder on coding / audit_summarization / retrieval_qa / russian_operator_notes / long_handoff_compression. Telegram diff report. CONSTRAINTS: - AP-32 git commit -o <path> per substrate write (session-coordination v1.33.0). - AP-21 NO silent deploy — each /approve gate is mandatory. Telegram Madi with proposal + diff before any deploy. - AP-18 goal-cycle workers use grok-reasoning by default; /codex GPT-5.5 for high-judgment slices only. - RULE ZERO no new LESSON files (pre-commit hook rejects); all learnings → SKILL.md + gbrain timeline. - 4-way HEAD parity (Mac / VPS-bare / VPS-working / Gi |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gg9CWc8HJ6W44jq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Айсхан | Финансы | [Maru/KEONA] Айсхан проверить остаток средств: 260 млн или 200 млн |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6MGjwx9h2Vjq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Жанара | Финансы | [Maru/KEONA] Жанара/юрист: проверить налог по внесению прав ПО в УФ Maru Analytics |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfGJWQF5cGPc2Gq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Партнёрство | [Maru/KEONA] Мади договориться с Умалатом о покупке его доли | 2026-05-25 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6JwvhvhPxVWH) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Партнёрство | [Maru/KEONA] Мади созвониться с Назиром и назначить нотариальную сделку |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6M4QxRV94Ppq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Бухгалтер | Финансы | [Maru/KEONA] Оплатить 130 млн KZT за поставку товара по договору поставки |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6MWQ8vHvvJCH) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Жанара | Финансы | [Maru/KEONA] Оценить вклад прав ПО/ERAP и прав Keon-A для УФ/JV |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfGJWcmWhGgM3RH) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Роза | Юр | [Maru/KEONA] Подготовить документ требований к правам от корейских партнёров |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6HxCH98WjmMq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Роза | Юр | [Maru/KEONA] Подготовить и подписать меморандум/соглашение о совместной реализации проекта |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6JCphGxjXfjH) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Бухгалтер | Продажи | [Maru/KEONA] Подготовить оплату 50% через Maru Analytics | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg4pmJmV7Mxqq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Роза | Юр | [Maru/KEONA] Подписать договор поставки |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6Jgvc9qHh5vq) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Роза | Юр | [Maru/KEONA] Подписать лицензионное соглашение |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6JQp8Hw8g3HH) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Партнёрство | KEONA: отправить Lim revised contract + HS code answer | 2026-05-22 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gh7CqCxgf2rrJjH) |
| `заблокировано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Данияр | Продажи | KEONA: подписать СП перед/параллельно оплате 50% |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf7XmV6CHWPm7PH) |
| `заблокировано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Данияр | Техника | [Maru/KEONA] Уточнить, кто отвечает за шкаф по аппаратной части |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6P8rHHrM3jXH) |
| `заблокировано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | responsible_uid:58809990 | Продажи | Оплатить 3 млн KZT за сервис Cerebro за май после 30 мая и АВР |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfG6MvVQ5q2rxjH) |
| `не сделано` | 4 | Фабрика Satory ВКО | ⚙️ Фабрика | Nous | Доставка | Цель: Подготовить пакет bootstrap одной командой для factory-reset оборудования АПК Мергеновского к 2026-05-19: клонировать wiki, установить OpenClaw + LiteLLM + Telegram poller + gbrain, зарегистрировать хост в pages/entities + skills/_gbrain/RESOLVER, запустить E2E smoke из Telegram, сохранить smoke-proof для передачи; доставить bootstrap.sh, README, страницу хост-сущности, артефакт smoke-proof; без пропущенных шагов, без скрытых учётных данных, каждый шаг с проверкой | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcpv6rhmQV5F88H) |
| `не сделано` | 3 | Фабрика Satory ВКО | ⚙️ Фабрика | AI-фабрика | AI-фабрика | [Nous-GPU] Определить роль мини-сервера NVIDIA для ERAP/Satory | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf3RHWgvQcVRvrq) |
| `не сделано` | 3 | Фабрика Satory ВКО | ⚙️ Фабрика | AI-фабрика | AI-фабрика | Satory client Playwright test infrastructure (E2E + per-page render verification) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gfHgxcXgmRPxxhq) |
| `не сделано` | 3 | Фабрика Satory ВКО | ⚙️ Фабрика | Nous | Юристы | Цель: Держать фабрику Nous AGaaS в зелёном статусе 7 дней: проверять паритет Air/VPS/Mac, OpenClaw, LiteLLM, Telegram poller, Goal Mode, OpenBrain projection, gbrain retrieval, Todoist sync и OpenRouter caps каждый цикл; исправлять только доказанные дрейфы и кодировать повторяемые ошибки в скиллы | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcpr5FhVw6Gvg2q) |
| `не сделано` | 3 | Фабрика Satory ВКО | ⚙️ Фабрика | Nous | AI-фабрика | Цель: Превратить Nous AGaaS в продаваемый пакет доказательств операционной системы: на каждом цикле извлекать одно живое доказательство из аудитов, передач, результатов задач или runtime-проверок и превращать его в артефакт, понятный клиенту/инвестору, демонстрационный скрипт, кейс-стади или пилотный одностраничник с точными доказательствами | 2026-06-15 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcpvMpvMFfRq7vH) |
| `не сделано` | 2 | Фабрика Satory ВКО | ⚙️ Фабрика | AI-фабрика | AI-фабрика | AI Factory: очередь задач кокпита на Q3 (4 улучшения) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCm2ff48pcC6hq) |
| `не сделано` | 2 | Фабрика Satory ВКО | ⚙️ Фабрика | AI-фабрика | AI-фабрика | Страница статуса Live |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9Mq5vmF8gXcXH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🎬 Замена Cerebro | Асыл | Доставка | BDL Трек C: План B Cerebro (Асыл, к D14) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCjx9cGR9pqMVq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🎬 Замена Cerebro | AI-фабрика | AI-фабрика | Прямое видео + PTZ |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9MpfQM3H8rWGH) |
| `не сделано` | 2 | Фабрика Satory ВКО | 🎬 Замена Cerebro | responsible_uid:40697968 | AI-фабрика | Карта 243 камеры GPS | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9MpXpWgHMWVwq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🏗️ Замена BDL | Роза Садырова | Юристы | BDL Трек A: судебный процесс (Роза, в процессе) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCjx4jgwcP3qWq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🏗️ Замена BDL | Мади | AI-фабрика | BDL Трек B: давление на BDL для исправления (Мади, в процессе) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCjx7hqqXR3G8H) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🏗️ Замена BDL | AI-фабрика | AI-фабрика | ISAPI push-listener |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9Mp46qW455CVq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🏗️ Замена BDL | Асыл | Продажи | BDL Трек E: Возрождение Spectra (Asyl+Madi, от D14) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCjxVwQMqPgFGH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🏗️ Замена BDL | AI-фабрика | AI-фабрика | Номерные знаки КЗ |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9Mp8v34X82gQH) |
| `не сделано` | 2 | Фабрика Satory ВКО | 🏗️ Замена BDL | AI-фабрика | AI-фабрика | Метрология автопроверка |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gJ9MpQJ24Jx22gH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | AI-фабрика | Technical | [ERAP] Выбрать модель тестирования с 3 серверами в КЗ | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf3RFjmcrR66MCH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Мади | Coordination | [ERAP] Мади: утвердить ответ Руслану по отдельному тестовому стенду | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf53JFhxCFV8VGH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Влад | Доставка | [Mergen/ERAP] Сбросить 1 APK к заводским настройкам и включить HTTP push с медиа | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gc5j8QPJxG6JXPq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | responsible_uid:44598829 | Доставка | свяжись пожалуйста с Ерасылом, и узнай сколько дней занимает получение доступа к тестовой среде. | 2026-05-14 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf5GWC8fw6p3rxH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Данияр | Coordination | [ERAP] Сравнить предложения по тестированию Negizone и KSL | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf3RGWQFPW37gpq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Асыл | Доставка | [Mergen/ERAP] Подтвердить статус тестовой конечной точки SmartBridge | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gc5j9JgQQprXFGq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Роза Садырова | Доставка | [Mergen/ERAP] Подтвердить ЭЦП/OID/путь легального подписанта | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gc5j97C7RQgvj3q) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Роза Садырова | Доставка | Полицейские документы: обновление статуса от Розы |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCm28XVrCMR6mH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Виктор Юрьевич | Доставка | Виктор Юрьевич — подпись протокола СОПА |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6q5mgp36qwqhq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Асылбек | Доставка | Восстановить upstream зеркало для коллектора Nous-GPU | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gVV4pC7H8h9C2Cq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Асылбек | Доставка | Запросить у вендора пароли для АПК камеры |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6q65WJ8WCRCfH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Влад | AI-фабрика | Изучить документацию HikVision для factory reset APK |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR67fvvgw9p5F4q) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Денис | AI-фабрика | Организовать канал для подключения Дуикса |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6pFG5prvG9QrH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Роза Садырова | Юристы | Организовать трехстороннюю комиссию по передаче лицензии |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR67g7vq966GH4q) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Виктор Юрьевич | Доставка | Подготовить размеченные документы для подписи Нурбека |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR67g3V23wXjMvH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Виктор Юрьевич | Доставка | Подписать протокол СОПА изменений |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6pF4xJcmjj3RH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Роза Садырова | Доставка | Решить вопрос доступа к камерам через официальное письмо в управление пассажирского транспорта |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6pFJjrjXvFwwq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Влад | Доставка | Сделать сброс настроек к заводским на АПК камере |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6q68VhR5462xq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Руслан | AI-фабрика | Обновить и верифицировать адресный список для передачи ЛУ вместе с Коваленко |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR67grQfhfhQQXH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Асылбек | Доставка | Получить ещё два коммерческих предложения по информационной безопасности |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6pFf2CXgcW68H) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📥 Входящие / Разбор | responsible_uid:58809990 | AI-фабрика | Провести анализ отсутствующих радаров на 14 из 51 перекрёстков |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6pFrmC7FpQ9rH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Асоль | Продажи | Синхронизировать бэклог JIRA с визуализацией карты |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR67gVh29r8j7Vq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Айда | AI-фабрика | Создать дашборд статуса MADI по APK |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR67gjr25j3fGvq) |
| `не сделано` | 2 | Фабрика Satory ВКО | 📥 Входящие / Разбор | AI-фабрика | AI-фабрика | Goal: Promote Tier-0 MLX from canary to production routing + walk Hermes 10-proof canary→production via tools/hermes_promotion_runner.py + run new 5-task benchmark on pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl, all gated by Madi /approve per AP-21 doctrine,. SUBSTRATE REFS (read before any slice): - Spec: pages/specs/2026-05-17-hermes-factory-design.md (Reality Check + Section 9 + Revised scope) - Tier-0 audit: pages/audits/TIER-0-MLX-DEPLOY-PROOF-2026-05-17.md (steps 1-3 GREEN; 4-6 pending) - Hermes audit: pages/audits/HERMES-PROMOTION-RUNNER-DEPLOY-PROOF-2026-05-17.md (6/10 GREEN; 4 RED: todoist canary, notion canary, gbrain timeline, cost receipt) - Handshake: pages/progress/HANDSHAKE-2026-05-17-claude-codex-hermes-promot ion-rotation.md - Benchmark fixture: pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl - Session handoff: pages/progress/HANDOFF-2026-05-17-claude-opus-4-7-session-close.md | 2026-05-25 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gg9CRWcRhmQgHxq) |
| `не сделано` | 2 | Фабрика Satory ВКО | 📥 Входящие / Разбор | AI-фабрика | AI-фабрика | Имеется камера VAR, на которой можно выполнить сброс к заводским настройкам | 2026-05-22 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf5HQ62hGMH2p8H) |
| `не сделано` | 2 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Мади | AI-фабрика | Решить: отвечать ли Connex Digital на их follow-up (предложение ZoomFlow — замена Jira/Notion для Satory) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR7rm72W68C8rhq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📷 Camera Doctor — пилот Satory | Мади | Продажи | Camera Doctor: выставлен первый счет |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCjxm37CWpWjcq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 📷 Camera Doctor — пилот Satory | AI-фабрика | AI-фабрика | Camera Doctor: скрипт для живого переключения готов |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCjxjw23QpChWq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | [Maru/KEONA] Зафиксировать Maru Analytics как основную компанию для Keon-A | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg5Qcg68F6vGH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | [Maru/KEONA] Подтвердить, может ли Maru Analytics быть buyer/importer для Proforma | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWm2qjhPQc9p5q) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | [Maru/KEONA] Получить документы Maru Analytics: регистрация, БИН, Astana Hub, реквизиты | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWQgcq8r8QRHQq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Асыл | Продажи | KEONA 12:00: Асыл — рассчитать питание и трафик АПК min/max: полный поток против только событий | 2026-05-24 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg5W78R2x236H) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | KEONA 12:00: Мади/GR — получить одобрение DTS/Ярослава или путь без возражений | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg5phC3XHr2wH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | KEONA 12:00: Мади/Назель/Роза — организовать живой звонок с Алматом по Maru Analytics/JV/Astana Hub | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg5GCv2VW47fq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Назель | Продажи | KEONA 12:00: Назель/Роза — подготовить юридические вопросы по JV на русском, затем перевести на корейский | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg566Fwpv3Gpq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Назель | Продажи | KEONA 12:00: Назель/Роза — провести внутреннее юридическое обсуждение до созвона с Алматом | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg59V9jrCMCxq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | DK | Продажи | KEONA: DK — подтвердить 3 площадки VKO, готовность питания/мачт/интернета, стажёров и план приёма инженеров Keon-A | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWQhcpFhm7Jh2H) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Асыл | Продажи | KEONA: запросить спецификацию нагревателя, пакет подготовки площадки, инструкции по установке и недостающие документы RF/импорта | 2026-05-24 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWQh9QW78FHhVH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Асыл | Продажи | KEONA: начать изготовление кронштейна по чертежам Pan-Tilt/Cabinet и проверить нагрузку/допуски/детали болтов | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWQhMpChMgWP8H) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Назель | Продажи | KEONA: обновить Framework/Supply/Software Licence под один объединённый этап + документы KAZ-патента/IP | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWQh285GWXcCCH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | AI-фабрика | Продажи | KEONA: поддерживать единый источник правды Notion/Todoist/Obsidian/gbrain/OpenBrain | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWwjHfFF8j9G7q) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | AI-фабрика | Продажи | KEONA: после каждого звонка обновлять Notion Docs Library и Obsidian project hub на русском | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWwjfRqMX8gVqq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Роза | Продажи | KEONA: Роза контролирует таблицу legal/certification и MOU с дорожной полицией после готовности 3 APK | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWQh2cfgrH8vMH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Выпустить импортную лицензию Казахстана на весь каталог Keon-A |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vgr83jc66hRq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Керон (Keon-A) | Продажи | Запросить у Keon-A сокращение срока контроллера с 4–5 недель до 2–3 недель |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vh79hwWvVvVq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Исправить наименование грузоотправителя: Maru System → Keon-A Information Technology |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vghQJ5vrr4GH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Обновить Статью 4 контракта: FCA Seoul → FCA Gimpo (Incoterms 2020) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vgcPc9H2JR8q) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Отправить 3 корейским форвардерам запросы на предложение (RFQ) по авиафрахту из Gimpo | 2026-04-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vgxm3vrjqFqH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Отправить отзыв по Kiona Данияру |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCjxrq7p9647GH) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Отправить подписанный контракт с реквизитами Keon-A (пересмотренный FCA Gimpo) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vgXCWcjX3Pcq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Подготовить авансовый перевод 50% = USD 19,260 в течение 1 раб. дня после подписания |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vh59VqJG2vQq) |
| `не сделано` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Nous | Продажи | Цель: Вести коммерческий pipeline KEONA/SPECTRA/Maru до тех пор, пока у каждого активного контрагента не будет текущего следующего действия, владельца, черновика/доказательства, списка рисков и согласования Obsidian/Todoist; создавать один конкретный коммерческий артефакт за цикл и никогда не отправлять внешние сообщения без одобрения Мади | 2026-05-31 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcpvJ5xrcpxQJmH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | AI-фабрика | Продажи | KEONA 12:00: AI Factory/Мади — подготовить презентацию таймлайна для Keon-A с факторами задержки | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg52fM4rvpMPH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | DK | Продажи | KEONA 12:00: DK/VKO — подтвердить готовность Усть-Каменогорска и логистику на неделю 15.06.2026 | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg5x4jVgh4gCH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Асыл | Продажи | KEONA 12:00: Асыл — рассчитать размеры solar/wind/battery для удалённых площадок ВКО | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg5fFpCf684XH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | AI-фабрика | Продажи | KEONA/Infrastructure: обновить GStack 1.26.0.0 → 1.31.1.0 после защиты dirty local skill tree | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gccG86Fxc3Pq8PH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Бухгалтер | Продажи | KEONA: бухгалтерия — подготовить банковский путь/passport-of-deal для аванса USD 23,500 после финального Proforma/buyer | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcWQhr453VPQv6H) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Данияр | Продажи | Закрыть складской инвентарь ISC + запросить КП у Лим |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCm2696Jfg32Vq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Асылбек | Продажи | Отправить Keon-A 10-значный HS-код освещения (9405.49.2xxx) после финализации брокером |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vgqv2gWcXQpq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Асылбек | Продажи | Подготовить крепёжные кронштейны для Pan-Tilt и Cabinet заранее |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vgmVG9vJ32VH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | AI-фабрика | Продажи | Подтвердить дату пилота Keon-A |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gXCm23h39PMjwfq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Керон (Keon-A) | Продажи | Подтвердить с Keon-A, что коммерческий инвойс остаётся USD 22,520 после замены Pan-Tilt на автоматический |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vhGv3QCFwmhH) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Получить и проверить файл Dimension & Weight за 2026-04-21 (вкл. Auto Pan-Tilt + Controller) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vhJxRPQGgfPq) |
| `не сделано` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Асылбек | Продажи | Рассчитать казахстанские таможенные пошлины и НДС по подтверждённым HS-кодам |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vhCjrFQJ8pvq) |
| `не сделано` | 2 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Керон (Keon-A) | Продажи | Запросить у Keon-A опыт локализации в других странах (Вьетнам/Индонезия/Узбекистан/БВ) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vhWvfrrXg4Fq) |
| `не сделано` | 2 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | Мади | Продажи | Подтвердить конкретные модели автомобилей РК для системы KOBES (мобильная фаза) |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vhhmQjH6mJ8H) |
| `не сделано` | 2 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | daniyar-decides | Продажи | Проработать долгосрочную структуру JV Satory–KEONA для статуса локального производителя РК |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gR6vhVmJq3C4CWq) |
| `в работе` | 4 | Фабрика Satory ВКО | 📋 Полиция / Бумажки | Асыл | Technical | [ERAP] Проверить монтаж VAR камеры и радара рядом с ЛУ | 2026-05-18 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gf3RHCCw67fMXRH) |
| `в работе` | 4 | Фабрика Satory ВКО | 📥 Входящие / Разбор | Асыл | Доставка | Восстановить upstream TZSP зеркало Nous-GPU на 10.99.99.1:37008 |  | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gVW6GX5CM3rRgmq) |
| `в работе` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | AI-фабрика | AI-фабрика | KEONA/SPECTRA: параллельно настроить АПК Keon-A, NOUS и SPECTRA для пилота | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcXg5mQqhvjFFPH) |
| `в работе` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | AI-фабрика | Продажи | KEONA/Infrastructure: починить нативный Codex QMD stdio коннектор или перенастроить на HTTP MCP | 2026-05-21 | `есть источник` | [Todoist](https://todoist.com/showTask?id=6gcX7CVhHQpv3gwH) |

## Недавно завершённые задачи

| Статус | P | Проект | Раздел | Владелец | Отдел | Задача | Срок | Контекст | Ссылка |
|---|---:|---|---|---|---|---|---|---|---|
| `готово` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | [KEONA] Получить подтверждение Lim/Aigerim по структуре Spectra ITS / Maru Analytics / Satory | 2026-05-22 | `завершено` | [Todoist](https://todoist.com/showTask?id=6ggrqX9c5cVp8rcq) |
| `готово` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | Приветствие — настройка брифинга Todoist (Данияр) |  | `завершено` | [Todoist](https://todoist.com/showTask?id=6gXCjwvxQX48JP8q) |
| `готово` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | [Maru/KEONA] Подготовить формулировку для корейцев по передаче прав |  | `завершено` | [Todoist](https://todoist.com/showTask?id=6gfG6J72FgmXRMfH) |
| `готово` | 2 | Фабрика Satory ВКО | 🎬 Замена Cerebro | done | done | завершите установку Var камеры до 14-мая-26 | 2026-05-14 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gf5H3PQQ9GHvhQH) |
| `готово` | 4 | Фабрика Satory ВКО | 🔴 Блокеры (нужны люди) | done | done | Переподключить OAuth Google Drive для зеркала регистрации control-plane Todoist |  | `завершено` | [Todoist](https://todoist.com/showTask?id=6gf3mQ3gFj4HFQhH) |
| `готово` | 1 | Фабрика Satory ВКО | unknown | done | done | Goal: Turn Nous AGaaS into a sellable operator-system proof pack: every cycle extract one live proof from audits, handoffs, task-results, or runtime checks and convert it into a customer/investor-readable artifact, demo script, case study, or pilot one-pager with exact evidence | 2026-06-15 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcq3g7429Wg47Gq) |
| `готово` | 1 | Фабрика Satory ВКО | unknown | done | done | Goal: Keep the Nous AGaaS factory green for 7 days: every cycle verify Air/VPS/Mac parity, OpenClaw, LiteLLM, Telegram poller, Goal Mode, OpenBrain projection, gbrain retrieval, Todoist sync, and OpenRouter caps; repair only evidence-proven drift, preserve dirty user changes, and codify reusable failures into skills | 2026-05-19 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcq3c5m5X6V95VH) |
| `готово` | 1 | Фабрика Satory ВКО | unknown | done | done | Goal: Drive the KEONA/SPECTRA/Maru commercial pipeline until every active counterparty has a current next action, owner, draft/proof artifact, risk list, and Obsidian/Todoist alignment; produce one concrete commercial artifact per cycle and never send external messages without Madi approval | 2026-05-31 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcq3JpfM46RMfHq) |
| `готово` | 3 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | KEONA: проверить GStack/Karpathy toolchain в checklist единого источника правды | 2026-05-12 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcWwm9Mh7cJC5Qq) |
| `готово` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | KEONA: добавить OpenBrain capture/projection после release openbrain lane | 2026-05-12 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcWwm5FVP2V6c6q) |
| `готово` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | KEONA 12:00: Мади — отправить Lim/Aigerim письмо на корейском + русском до 10:00 Алматы / 14:00 Сеул | 2026-05-12 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcXg4xVCq3J4HVq) |
| `готово` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | KEONA: Мади — отправить Lim/Aigerim письмо на корейском + русском, без английского | 2026-05-11 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcWm2P2f4M3g8vq) |
| `готово` | 4 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | KEONA: отправить Lim ответ на письмо 07.05 по heater/site-prep/IP/tax cert/Proforma/timeline | 2026-05-11 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcWQgpcMqwG75Gq) |
| `готово` | 1 | Фабрика Satory ВКО | 🤝 Партнерство KEONA | done | done | KEONA/Infrastructure: fix gbrain embedding backend for OpenRouter or restore OpenAI quota | 2026-05-12 | `завершено` | [Todoist](https://todoist.com/showTask?id=6gcXGwQFCHJWRFQq) |
| `готово` | 1 | Фабрика Satory ВКО | ⚙️ Фабрика | done | done | AI Factory D0: Pane 3 (Opus) credentials substrate fix |  | `завершено` | [Todoist](https://todoist.com/showTask?id=6gXCm2WprmhWgHfH) |
| `готово` | 1 | Фабрика Satory ВКО | ⚙️ Фабрика | done | done | AI Factory D0: Pane 2 (Codex GPT-5.5) 6 slices done |  | `завершено` | [Todoist](https://todoist.com/showTask?id=6gXCm2VRWM76v6Pq) |
| `готово` | 1 | Фабрика Satory ВКО | ⚙️ Фабрика | done | done | AI Factory D0: Pane 1 (Sonnet) 4 slices done |  | `завершено` | [Todoist](https://todoist.com/showTask?id=6gXCm2M384RPW4rH) |

## Активные задачи без реального контекста

- нет
