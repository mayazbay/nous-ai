---
type: system
id: satory-todoist-deep-audit-index
title: "Индекс глубокого аудита Todoist Фабрика Satory ВКО"
last_updated: 2026-05-25T10:46:09.257168+05:00
status: done
tags: [todoist, satory, factory, comments, proof, gbrain, notion, google-drive]
---

# Индекс глубокого аудита Todoist Фабрика Satory ВКО

Этот файл короткий специально: его должен быстро находить gbrain/OpenBrain. Полный построчный аудит лежит отдельным большим файлом.

## Артефакты

- Полный Markdown-аудит: `pages/audits/AUDIT-satory-todoist-deep-2026-05-25-1046.md`
- Полный JSON-аудит: `pages/systems/satory-todoist-deep-audit.json`
- Scope: только `Фабрика Satory ВКО` / `6gJ5j8PRVVCWpgCq`.
- Личных проектов затронуто: `0`.

## Сводка

- Активных задач: `107`
- Комментариев Todoist прочитано: `182`
- AI-owned задач: `19`
- Human-owned задач: `88`
- Без source-backed контекста: `0`
- Жёстких structural рисков: `0`

## Маршруты фабрики

- `blocked`: `20`
- `human_owned_monitor`: `4`
- `human_owner_reminder`: `66`
- `ready_for_ai_factory`: `17`

## Proof gate

- Правило: Не закрывать и не удалять задачу без Notion + Google Drive proof.
- Готовы к закрытию: `0`
- Нельзя закрывать без Notion+Drive proof: `107`

Если `close_ready_tasks=0`, это не сбой фабрики. Это честный сигнал: работа остается открытой, пока нет human-checkable proof.

## Proof-path health

- Google Drive storage: `approved`
- Active-task Google Drive proofs: `0`
- Active-task close-ready proofs: `0`
- Interpretation: `drive_path_approved_no_active_task_ready_to_close`
- Approved Drive proof URL: https://drive.google.com/open?id=1Lc5TDe8HPfDPvKOIfNWZNL6LB-ZHYkRy