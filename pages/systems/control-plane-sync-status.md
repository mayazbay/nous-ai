---
type: system
id: control-plane-sync-status
title: "Статус синхронизации контрольной плоскости"
last_updated: 2026-05-25T09:58:29.493825+05:00
status: blocked
tags: [control-plane, todoist, notion, github, langsmith, factory]
---

# Статус синхронизации контрольной плоскости

- Последний цикл: `2026-05-25-095819`
- Общий статус: `blocked`
- Старт: `2026-05-25T09:58:19.222533+05:00`
- Финиш: `2026-05-25T09:58:29.493825+05:00`
- Сухой прогон: `False`

## Матрица статусов

| Компонент | Состояние | Сводка |
|---|---:|---|
| git_preflight | `blocked` | dirty tree before sync (2 paths) |
| notion_sync | `skipped_preflight` | git preflight blocked; step intentionally not started |
| todoist_control_plane | `skipped_preflight` | git preflight blocked; step intentionally not started |
| todoist_register_export | `skipped_preflight` | git preflight blocked; step intentionally not started |
| satory_todoist_deep_audit | `skipped_preflight` | git preflight blocked; step intentionally not started |
| substrate_probe | `skipped_preflight` | git preflight blocked; step intentionally not started |
| factory_probe | `skipped_preflight` | git preflight blocked; step intentionally not started |
| langsmith | `skipped_preflight` | git preflight blocked; step intentionally not started |
| model_bakeoff | `skipped_preflight` | git preflight blocked; step intentionally not started |
| russian_docs_gate | `skipped_preflight` | git preflight blocked; step intentionally not started |
| russian_docs_gate | `done` | failures=0 |
| git_writeback | `done` | committed=True head=e49320f1 github=ok |

## Правила блокировок

- `blocked`: API/runtime/git путь сломан; нужна фабрика или оператор.
- `not_done`: детерминированный план есть, но не применён в этом цикле.
- `working` / `in_progress`: сейчас выполняется; не должен оставаться после финиша цикла.
- `done`: проверено живым выводом команды.
- `skipped`: намеренно пропущено, обычно из-за dry-run или недельного cadence gate.
