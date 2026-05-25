---
type: spec
id: DECISION-RIGHTS-PROTOCOL-2026-05-05
title: "Decision Rights Protocol — Протокол принятия решений"
date: 2026-05-05
status: active
owner: Madi Ayazbay
tags: [protocol, governance, decision-rights, platform-direction, todoist-gate]
related:
  - "[[entities/asyl]]"
  - "[[entities/roza]]"
  - "[[skills/session-operating-contract]]"
  - "[[skills/musk-algorithm]]"
---

# Decision Rights Protocol / Протокол принятия решений

**Version:** 1.0 — 2026-05-05
**Owner:** Madi Ayazbay
**Scope:** All platform-direction changes, vendor decisions, architectural choices

---

## English

### Rule

No platform-direction change ships without a one-page Decision Record.

### Decision Record — Required Fields

1. **Options considered** (minimum 2, ideally 3)
2. **Recommendation** — one sentence
3. **Owner** — single person accountable
4. **Impact analysis** — what changes, who is affected, reversibility
5. **Rollback plan** — how to undo within 24h
6. **Signatures** — Madi + Roza (both required before execution)

### Enforcement Gate (Todoist)

Tasks tagged `platform-direction` **cannot close** without a linked Decision Record.

- Agent checks for linked Decision Record at task-close time
- Refusal to provide Decision Record = governance event (logged, escalated — not silenced)
- Repeated refusal = performance issue

### Who This Applies To

| Role | Trigger |
|---|---|
| Asyl (Tech Lead) | Any platform architecture change, vendor selection, infra topology |
| Daniyar (CEO) | Partnership agreements, commercial structure |
| Roza (Legal/Director) | Legal structure changes, compliance decisions |
| Oskar (Ops) | Warehouse/ISC vendor changes above ₸500K |
| Madi | All of the above — Madi signs every Decision Record |

### What Counts as "Platform Direction"

- New vendor or technology adoption
- Removing or replacing existing system components
- API/contract changes with external parties
- Changes to agent autonomy or escalation policy
- Pricing decisions (floor: ₸500K/month for any Camera Doctor tier)

### What Does NOT Require a Decision Record

- Bug fixes with no behavioral change
- Documentation updates
- Monitoring/observability additions
- Test additions

---

## Русский

### Правило

Никакое изменение платформы не выходит в продакшн без одностраничного Decision Record.

### Decision Record — обязательные поля

1. **Рассмотренные варианты** (минимум 2, желательно 3)
2. **Рекомендация** — одно предложение
3. **Владелец** — один человек, несущий ответственность
4. **Анализ влияния** — что меняется, кого затрагивает, обратимость
5. **План отката** — как отменить изменение в течение 24 часов
6. **Подписи** — Мади + Роза (обе обязательны до исполнения)

### Гейт исполнения (Todoist)

Задачи с тегом `platform-direction` **не могут быть закрыты** без прикреплённого Decision Record.

- Агент проверяет наличие Decision Record при закрытии задачи
- Отказ предоставить Decision Record = событие управления (логируется, эскалируется — не замалчивается)
- Повторный отказ = проблема эффективности работы

### Кого это касается

| Роль | Триггер |
|---|---|
| Асыл (Tech Lead) | Любое изменение архитектуры платформы, выбор вендора, топология инфраструктуры |
| Данияр (CEO) | Партнёрские соглашения, коммерческая структура |
| Роза (Юрист/Директор) | Изменения юридической структуры, комплаенс-решения |
| Оскар (Операции) | Смена вендора склада/ISC на сумму свыше ₸500K |
| Мади | Всё вышеперечисленное — Мади подписывает каждый Decision Record |

### Что считается «направлением платформы»

- Принятие нового вендора или технологии
- Удаление или замена существующих компонентов системы
- Изменения API/контракта с внешними сторонами
- Изменения автономии агента или политики эскалации
- Ценовые решения (нижняя граница: ₸500K/месяц для любого тарифа Camera Doctor)

### Что НЕ требует Decision Record

- Исправления ошибок без изменения поведения
- Обновления документации
- Добавление мониторинга/наблюдаемости
- Добавление тестов

---

## Decision Record Template / Шаблон

```markdown
# Decision Record: [Название решения]

Date: YYYY-MM-DD
Owner: [Имя]
Status: Draft | Approved | Rejected

## Options / Варианты

| # | Вариант | Плюсы | Минусы |
|---|---|---|---|
| A | ... | ... | ... |
| B | ... | ... | ... |
| C | ... | ... | ... |

## Recommendation / Рекомендация

Вариант [X] — [одно предложение].

## Impact / Влияние

[Что меняется, кто затронут, обратимость.]

## Rollback / Откат

[Как отменить в течение 24 часов.]

## Signatures / Подписи

- Madi Ayazbay: _____ Date: _____
- Roza Sadyrova: _____ Date: _____
```

---

## See also

- [[entities/asyl]] — Tech Lead (primary gated role)
- [[skills/session-operating-contract]] — DONE protocol and governance doctrine
- [[skills/musk-algorithm]] — Step 2 first: require justification before any platform change
