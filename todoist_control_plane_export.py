#!/usr/bin/env python3
"""Export Todoist as a durable control-plane task register.

The audit script keeps Todoist structurally clean. This exporter makes that
state visible to humans and agents by writing a source-backed register into the
vault. It is intentionally deterministic: no model decides routing, status, or
retry policy.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

from todoist_control_plane_audit import SATORY_TODOIST_PROJECT_ID, Todoist, build_audit, labels_for, token_from_env


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_MARKDOWN = Path("pages/systems/todoist-control-plane-register.md")
DEFAULT_JSON = Path("pages/systems/todoist-control-plane-register.json")
DEFAULT_CSV = Path("pages/exports/todoist-control-plane-register.csv")
DEFAULT_CONTEXT_QUEUE = Path("pages/systems/todoist-context-enrichment-queue.md")
OWNER_PREFIXES = ("исполнитель:", "owner:", "assignee:")
DEPT_PREFIXES = ("отдел:", "dept:", "department:")
STATUS_PREFIXES = ("статус:", "status:")
STATUS_VALUES = {"in_progress", "working", "done", "not_done", "blocked"}
STATUS_ALIASES = {
    "в_работе": "working",
    "в-работе": "working",
    "работает": "working",
    "готово": "done",
    "сделано": "done",
    "не_сделано": "not_done",
    "не-сделано": "not_done",
    "не сделано": "not_done",
    "заблокировано": "blocked",
    "блокер": "blocked",
}
STATUS_RU = {
    "blocked": "заблокировано",
    "done": "готово",
    "in_progress": "в работе",
    "working": "в работе",
    "not_done": "не сделано",
}
CONTEXT_RU = {
    "completed": "завершено",
    "needs_source": "нужен источник",
    "source_backed": "есть источник",
}
RISK_RU = {
    "default_priority": "приоритет по умолчанию",
    "invalid_section": "неверный раздел",
    "missing_department": "нет отдела",
    "missing_labels": "нет меток",
    "missing_owner": "нет владельца",
    "missing_project": "нет проекта",
    "no_description_or_note": "нет описания/комментария",
    "root_no_section": "корневая задача без раздела",
    "subtask_no_section_inherited": "подзадача без раздела",
}


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def md_escape(value: Any) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("|", "\\|")


def first_prefixed(labels: list[str], prefixes: tuple[str, ...], fallback: str) -> str:
    for label in labels:
        for prefix in prefixes:
            if label.startswith(prefix):
                return label.split(":", 1)[1] if ":" in label else label
    return fallback


def status_from_labels(labels: list[str]) -> str | None:
    for label in labels:
        for prefix in STATUS_PREFIXES:
            if label.startswith(prefix):
                raw = label.split(":", 1)[1].strip().lower().replace("-", "_")
                if raw in STATUS_VALUES:
                    return raw
                return STATUS_ALIASES.get(raw.replace("_", "-")) or STATUS_ALIASES.get(raw)
    return None


def derive_active_status(item: dict[str, Any], labels: list[str]) -> str:
    explicit = status_from_labels(labels)
    if explicit and explicit != "done":
        return explicit
    blob = " ".join([str(item.get("content") or ""), str(item.get("description") or ""), " ".join(labels)]).casefold()
    if any(token in blob for token in ["blocked", "blocker", "блокер", "заблок"]):
        return "blocked"
    if any(token in blob for token in ["in progress", "in_progress", "working", "делаю", "работаю"]):
        return "working"
    return "not_done"


def status_display(value: Any) -> str:
    text = str(value or "")
    return STATUS_RU.get(text, text)


def context_display(value: Any) -> str:
    text = str(value or "")
    return CONTEXT_RU.get(text, text)


def risk_display(value: Any) -> str:
    text = str(value or "")
    return RISK_RU.get(text, text)


def task_url(task_id: str, item: dict[str, Any]) -> str:
    return str(item.get("url") or f"https://todoist.com/showTask?id={task_id}")


def date_value(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("date") or value.get("datetime") or value.get("start") or "")
    return str(value or "")


def completed_at_value(item: dict[str, Any]) -> str:
    for key in ("completed_at", "completed_date", "completed_time"):
        if item.get(key):
            return str(item[key])
    return ""


def normalize_active_task(
    item: dict[str, Any],
    project: dict[str, Any] | None,
    section: dict[str, Any] | None,
    note_count: int,
) -> dict[str, Any]:
    task_id = str(item.get("id") or "")
    labels = labels_for(item)
    description_present = bool(str(item.get("description") or "").strip())
    effective_note_count = int(item.get("note_count") or note_count or 0)
    context_state = "source_backed" if description_present or effective_note_count > 0 else "needs_source"
    owner = first_prefixed(labels, OWNER_PREFIXES, "responsible_uid:" + str(item.get("responsible_uid"))) if item.get("responsible_uid") else first_prefixed(labels, OWNER_PREFIXES, "missing")
    department = first_prefixed(labels, DEPT_PREFIXES, "missing")
    return {
        "task_id": task_id,
        "status": derive_active_status(item, labels),
        "content": str(item.get("content") or ""),
        "project": str(project.get("name") if project else "missing"),
        "project_id": str(item.get("project_id") or ""),
        "section": str(section.get("name") if section else "NO_SECTION"),
        "section_id": str(item.get("section_id") or ""),
        "owner": owner,
        "department": department,
        "priority": int(item.get("priority") or 1),
        "labels": labels,
        "due": date_value(item.get("due")),
        "deadline": date_value(item.get("deadline")),
        "todoist_url": task_url(task_id, item),
        "description_present": description_present,
        "note_count": effective_note_count,
        "context_state": context_state,
        "parent_id": str(item.get("parent_id") or ""),
        "source": "todoist-active",
    }


def normalize_completed_task(item: dict[str, Any], projects: dict[str, dict[str, Any]], sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    task_id = str(item.get("task_id") or item.get("id") or "")
    project_id = str(item.get("project_id") or "")
    section_id = str(item.get("section_id") or "")
    project = projects.get(project_id)
    section = sections.get(section_id)
    return {
        "task_id": task_id,
        "status": "done",
        "content": str(item.get("content") or ""),
        "project": str(project.get("name") if project else project_id or "unknown"),
        "project_id": project_id,
        "section": str(section.get("name") if section else section_id or "unknown"),
        "section_id": section_id,
        "owner": "done",
        "department": "done",
        "priority": int(item.get("priority") or 0),
        "labels": item.get("labels") if isinstance(item.get("labels"), list) else [],
        "due": date_value(item.get("due")),
        "deadline": date_value(item.get("deadline")),
        "todoist_url": task_url(task_id, item) if task_id else "",
        "description_present": bool(str(item.get("description") or "").strip()),
        "note_count": int(item.get("note_count") or 0),
        "context_state": "completed",
        "completed_at": completed_at_value(item),
        "parent_id": str(item.get("parent_id") or ""),
        "source": "todoist-completed",
    }


def notes_by_item(sync: dict[str, Any]) -> collections.Counter[str]:
    result: collections.Counter[str] = collections.Counter()
    for note in sync.get("notes", []):
        if isinstance(note, dict) and not note.get("is_deleted"):
            item_id = str(note.get("item_id") or note.get("task_id") or "")
            if item_id:
                result[item_id] += 1
    return result


def fetch_completed_tasks(
    client: Todoist,
    *,
    since: dt.datetime,
    until: dt.datetime,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    error: dict[str, Any] | None = None
    while len(rows) < limit:
        params: dict[str, Any] = {
            "since": iso_z(since),
            "until": iso_z(until),
            "limit": min(50, limit - len(rows)),
        }
        if cursor:
            params["cursor"] = cursor
        try:
            payload = client.request("GET", "/tasks/completed/by_completion_date", params=params)
        except Exception as exc:
            error = {"error": exc.__class__.__name__, "detail": str(exc)[:500]}
            break
        if not isinstance(payload, dict):
            error = {"error": "unexpected_payload", "detail": str(type(payload))}
            break
        batch = [row for row in payload.get("items", []) if isinstance(row, dict)]
        rows.extend(batch)
        cursor = payload.get("next_cursor")
        if not cursor or not batch:
            break
    return rows, error


def build_register(sync: dict[str, Any], completed: list[dict[str, Any]], completed_error: dict[str, Any] | None, completed_days: int) -> dict[str, Any]:
    audit = build_audit(sync)
    projects = {str(p.get("id")): p for p in audit["_objects"]["projects"]}
    sections = {str(s.get("id")): s for s in audit["_objects"]["sections"]}
    note_counts = notes_by_item(sync)

    active_rows = [
        normalize_active_task(
            item,
            projects.get(str(item.get("project_id") or "")),
            sections.get(str(item.get("section_id") or "")),
            note_counts.get(str(item.get("id") or ""), 0),
        )
        for item in audit["_objects"]["items"]
    ]
    active_rows.sort(key=lambda row: (row["status"], row["project"].casefold(), row["section"].casefold(), -row["priority"], row["content"].casefold()))

    completed_rows = [
        normalize_completed_task(item, projects, sections)
        for item in completed
        if str(item.get("project_id") or "") == SATORY_TODOIST_PROJECT_ID
    ]
    completed_rows.sort(key=lambda row: row.get("completed_at") or "", reverse=True)

    all_rows = active_rows + completed_rows
    status_counts = collections.Counter(row["status"] for row in all_rows)
    context_counts = collections.Counter(row["context_state"] for row in active_rows)
    department_counts = collections.Counter(row["department"] for row in active_rows)
    owner_counts = collections.Counter(row["owner"] for row in active_rows)

    captured = now_kzt()
    return {
        "captured_at": captured.isoformat(),
        "captured_at_utc": iso_z(captured),
        "source": {
            "todoist_sync_api": "/api/v1/sync",
            "completed_api": "/api/v1/tasks/completed/by_completion_date",
            "completed_days": completed_days,
            "completed_error": completed_error,
        },
        "counts": {
            "active_tasks": len(active_rows),
            "recent_completed_tasks": len(completed_rows),
            "total_register_rows": len(all_rows),
            "contextless_active_tasks": context_counts.get("needs_source", 0),
            "hard_gate_risk_total": sum(
                int(audit["risk_counts"].get(key) or 0)
                for key in [
                    "missing_project",
                    "invalid_section",
                    "root_no_section",
                    "subtask_no_section_inherited",
                    "missing_owner",
                    "missing_department",
                    "missing_labels",
                    "default_priority",
                ]
            ),
        },
        "risk_counts": audit["risk_counts"],
        "status_counts": dict(sorted(status_counts.items())),
        "context_counts": dict(sorted(context_counts.items())),
        "department_counts": dict(department_counts.most_common()),
        "owner_counts": dict(owner_counts.most_common()),
        "active_tasks": active_rows,
        "recent_done_tasks": completed_rows,
        "artifacts": {},
    }


def render_task_table(rows: list[dict[str, Any]], *, limit: int | None = None) -> list[str]:
    selected = rows[:limit] if limit else rows
    lines = [
        "| Статус | P | Проект | Раздел | Владелец | Отдел | Задача | Срок | Контекст | Ссылка |",
        "|---|---:|---|---|---|---|---|---|---|---|",
    ]
    for row in selected:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{md_escape(status_display(row['status']))}`",
                    str(row.get("priority") or ""),
                    md_escape(row.get("project")),
                    md_escape(row.get("section")),
                    md_escape(row.get("owner")),
                    md_escape(row.get("department")),
                    md_escape(row.get("content")),
                    md_escape(row.get("due") or row.get("deadline")),
                    f"`{md_escape(context_display(row.get('context_state')))}`",
                    f"[Todoist]({row.get('todoist_url')})" if row.get("todoist_url") else "",
                ]
            )
            + " |"
        )
    if limit and len(rows) > limit:
        lines.append(f"| `_обрезано_` |  |  |  |  |  | ещё {len(rows) - limit} строк в CSV/JSON |  |  |  |")
    return lines


def render_markdown(register: dict[str, Any], markdown_path: Path, json_path: Path, csv_path: Path) -> str:
    counts = register["counts"]
    completed_error = register["source"].get("completed_error")
    lines = [
        "---",
        "type: system",
        "id: todoist-control-plane-register",
        'title: "Реестр контрольной плоскости Todoist"',
        f"last_updated: {register['captured_at']}",
        "status: active",
        "tags: [todoist, control-plane, tasks, factory, notion, google-drive, gbrain]",
        "---",
        "",
        "# Реестр контрольной плоскости Todoist",
        "",
        f"- Снято: `{register['captured_at']}`",
        f"- Активных задач: `{counts['active_tasks']}`",
        f"- Недавно завершённых задач: `{counts['recent_completed_tasks']}`",
        f"- Жёстких рисков: `{counts['hard_gate_risk_total']}`",
        f"- Активных задач без реального контекста: `{counts['contextless_active_tasks']}`",
        f"- JSON-артефакт: `{json_path}`",
        f"- CSV-артефакт: `{csv_path}`",
        "",
        "## Правило",
        "",
        "Todoist — очередь исполнения. Эта страница — детерминированная модель чтения для людей и агентов. Жёсткие структурные ошибки можно чинить автоматически; контекст задач добавляется только из реального источника.",
        "",
        "## Счётчики статусов",
        "",
    ]
    for key, value in register["status_counts"].items():
        lines.append(f"- `{status_display(key)}`: `{value}`")
    lines.extend(["", "## Счётчики контекста", ""])
    for key, value in register["context_counts"].items():
        lines.append(f"- `{context_display(key)}`: `{value}`")
    lines.extend(["", "## Счётчики отделов", ""])
    for key, value in register["department_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Счётчики рисков", ""])
    for key, value in register["risk_counts"].items():
        lines.append(f"- `{risk_display(key)}` (`{key}`): `{value}`")
    if completed_error:
        lines.extend(["", "## API завершённых задач", "", f"- Статус: `заблокировано`", f"- Ошибка: `{md_escape(completed_error)}`"])
    else:
        lines.extend(["", "## API завершённых задач", "", "- Статус: `готово`"])
    lines.extend(["", "## Реестр активных задач", ""])
    lines.extend(render_task_table(register["active_tasks"]))
    lines.extend(["", "## Недавно завершённые задачи", ""])
    if register["recent_done_tasks"]:
        lines.extend(render_task_table(register["recent_done_tasks"], limit=120))
    else:
        lines.append("- За выбранное окно завершённые задачи не вернулись.")
    contextless = [row for row in register["active_tasks"] if row["context_state"] == "needs_source"]
    lines.extend(["", "## Активные задачи без реального контекста", ""])
    if contextless:
        lines.append("Это yellow, не red. Нельзя добавлять фейковые заметки; обогащать только из реальных артефактов Obsidian/Gmail/Notion/Drive/proof.")
        lines.extend([""])
        lines.extend(render_task_table(contextless, limit=120))
    else:
        lines.append("- нет")
    lines.append("")
    return "\n".join(lines)


def render_context_enrichment_queue(register: dict[str, Any], queue_path: Path, markdown_path: Path) -> str:
    contextless = [row for row in register["active_tasks"] if row["context_state"] == "needs_source"]
    lines = [
        "---",
        "type: system",
        "id: todoist-context-enrichment-queue",
        'title: "Очередь обогащения контекста Todoist"',
        f"last_updated: {register['captured_at']}",
        "status: active",
        "tags: [todoist, factory, context-enrichment, russian, gbrain, notion, openbrain]",
        "---",
        "",
        "# Очередь обогащения контекста Todoist",
        "",
        f"- Снято: `{register['captured_at']}`",
        f"- Исходный реестр: `{markdown_path}`",
        f"- Артефакт очереди: `{queue_path}`",
        f"- Задач без контекста: `{len(contextless)}`",
        "",
        "## Правило",
        "",
        "Эта очередь для фабрики. Нельзя добавлять выдуманные описания, ссылки или комментарии. Каждая задача получает контекст только из реального источника: Obsidian, gbrain, Notion, Gmail, Google Drive, GitHub, proof/task-result или живой Telegram/операционный лог.",
        "",
        "## Как выполнять каждую задачу",
        "",
        "1. Открой Todoist-задачу по ссылке.",
        "2. Найди источник по точному названию задачи, проекту, контрагенту, дедлайну и ключевым словам в Obsidian/gbrain/Notion/Gmail/Drive/GitHub.",
        "3. Если источник найден, добавь в Todoist краткое описание на русском: цель, следующий шаг, владелец, отдел, ссылка на источник, критерий готовности.",
        "4. Если нужен AI-исполнитель, добавь/оставь метки `исполнитель:AI-фабрика`, `отдел:AI-фабрика`, `статус:в-работе` или `статус:заблокировано` по факту.",
        "5. Если источник не найден, не выдумывай. Оставь задачу yellow, создай task-result с фразой `источник не найден`, укажи где искал, и поставь блокер на владельца.",
        "6. После обновления синхронизируй контрольную плоскость: Todoist → Notion → Obsidian register → gbrain/OpenBrain projection → GitHub.",
        "",
        "## Критерий готовности",
        "",
        "- В Todoist есть реальный source-backed комментарий или описание.",
        "- В Obsidian есть след: register/queue/task-result/audit с Todoist id.",
        "- gbrain находит задачу или связанный артефакт по названию.",
        "- Notion mirror показывает тот же статус, владельца, отдел и ссылку на Todoist.",
        "- Ничего не выдумано и не заполнено шаблонной водой.",
        "",
        "## Очередь задач",
        "",
    ]
    if not contextless:
        lines.append("- Все активные задачи уже имеют реальный контекст.")
        return "\n".join(lines) + "\n"

    for idx, row in enumerate(contextless, start=1):
        labels = ", ".join(row.get("labels") or []) or "нет"
        lines.extend(
            [
                f"### {idx}. {row['content']} (`{row['task_id']}`)",
                "",
                f"- Todoist: {row['todoist_url']}",
                f"- Проект: `{row['project']}`",
                f"- Раздел: `{row['section']}`",
                f"- Владелец: `{row['owner']}`",
                f"- Отдел: `{row['department']}`",
                f"- Приоритет: `{row['priority']}`",
                f"- Метки: `{labels}`",
                f"- Срок: `{row.get('due') or row.get('deadline') or 'нет'}`",
                "- Почему в очереди: у задачи нет описания и нет реального комментария-источника.",
                "",
                "Инструкция фабрике:",
                "",
                "1. Ищи источник по названию задачи целиком, затем по 2-3 главным словам из названия.",
                f"2. Проверь проект `{row['project']}` и раздел `{row['section']}`: там обычно лежит контекст владельца и бизнес-цель.",
                "3. Проверь Obsidian/gbrain, затем Notion, затем Gmail/Drive/GitHub, если задача связана с письмом, файлом или кодом.",
                "4. Если найден источник, запиши в Todoist короткое русское описание: `что сделать`, `зачем`, `кто отвечает`, `какой отдел`, `ссылка на источник`, `что считается готово`.",
                "5. Если задача уже фактически выполнена, не закрывай молча: найди доказательство, добавь ссылку, обнови статус и создай receipt в `pages/task-results/`.",
                "6. Если источник не найден, создай блокер с точным списком проверенных мест. Не добавляй фейковый контекст.",
                "",
                "Критерий готовности:",
                "",
                "- Todoist-задача больше не попадает в `no_description_or_note`.",
                "- Есть ссылка на реальный источник или честный блокер.",
        "- Обновленный реестр показывает `context_state=source_backed` или задача явно `blocked` с доказательством.",
        "",
    ]
        )
    return "\n".join(lines)


def render_csv(register: dict[str, Any]) -> str:
    fields = [
        "source",
        "task_id",
        "status",
        "content",
        "project",
        "section",
        "owner",
        "department",
        "priority",
        "labels",
        "due",
        "deadline",
        "completed_at",
        "context_state",
        "description_present",
        "note_count",
        "todoist_url",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in register["active_tasks"] + register["recent_done_tasks"]:
        clean = dict(row)
        clean["labels"] = ",".join(row.get("labels") or [])
        writer.writerow(clean)
    return buffer.getvalue()


def write_outputs(register: dict[str, Any], *, markdown_path: Path, json_path: Path, csv_path: Path, queue_path: Path) -> None:
    register["artifacts"] = {
        "markdown": str(markdown_path),
        "json": str(json_path),
        "csv": str(csv_path),
        "context_enrichment_queue": str(queue_path),
    }
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(register, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    csv_path.write_text(render_csv(register), encoding="utf-8")
    markdown_path.write_text(render_markdown(register, markdown_path, json_path, csv_path), encoding="utf-8")
    queue_path.write_text(render_context_enrichment_queue(register, queue_path, markdown_path), encoding="utf-8")


def summary_payload(register: dict[str, Any], *, wrote: bool, markdown_path: Path, json_path: Path, csv_path: Path, queue_path: Path) -> dict[str, Any]:
    return {
        "captured_at": register["captured_at"],
        "status": "done" if register["counts"]["hard_gate_risk_total"] == 0 else "not_done",
        "wrote": wrote,
        "counts": register["counts"],
        "risk_counts": register["risk_counts"],
        "status_counts": register["status_counts"],
        "context_counts": register["context_counts"],
        "artifacts": {
            "markdown": str(markdown_path),
            "json": str(json_path),
            "csv": str(csv_path),
            "context_enrichment_queue": str(queue_path),
        },
        "completed_error": register["source"].get("completed_error"),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--context-queue", type=Path, default=DEFAULT_CONTEXT_QUEUE)
    parser.add_argument("--completed-days", type=int, default=30)
    parser.add_argument("--completed-limit", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    client = Todoist(token_from_env(args.env_file))
    sync = client.sync()
    until = dt.datetime.now(dt.timezone.utc)
    since = until - dt.timedelta(days=max(1, min(args.completed_days, 92)))
    completed, completed_error = fetch_completed_tasks(
        client,
        since=since,
        until=until,
        limit=max(0, args.completed_limit),
    )
    register = build_register(sync, completed, completed_error, args.completed_days)
    if not args.dry_run:
        write_outputs(register, markdown_path=args.markdown, json_path=args.json_out, csv_path=args.csv, queue_path=args.context_queue)
    payload = summary_payload(register, wrote=not args.dry_run, markdown_path=args.markdown, json_path=args.json_out, csv_path=args.csv, queue_path=args.context_queue)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(register, args.markdown, args.json_out, args.csv))
    return 0 if payload["status"] == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
