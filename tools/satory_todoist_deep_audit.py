#!/usr/bin/env python3
"""Deep Satory-only Todoist task/comment audit.

This is a read model for the factory. It does not mutate Todoist, Notion,
Google Drive, or the vault unless explicitly asked to write local audit files.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from human_owner_reminder import comment_intent, due_date, reminder_reasons
from todoist_control_plane_audit import (
    SATORY_TODOIST_PROJECT_ID,
    Todoist,
    active_item,
    build_audit,
    filter_satory_sync,
    labels_for,
    token_from_env,
)
from todoist_control_plane_export import (
    first_prefixed,
    normalize_active_task,
    status_display,
)


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_JSON = Path("pages/systems/satory-todoist-deep-audit.json")
DEFAULT_INDEX = Path("pages/systems/satory-todoist-deep-audit-index.md")
DEFAULT_AUDIT_DIR = Path("pages/audits")
DRIVE_PROOF_AUDIT = Path("pages/audits/AUDIT-google-drive-proof-path-2026-05-14-1812.md")
DRIVE_PROOF_URL = "https://drive.google.com/open?id=1Lc5TDe8HPfDPvKOIfNWZNL6LB-ZHYkRy"
OWNER_PREFIXES = ("исполнитель:", "owner:", "assignee:")
DEPT_PREFIXES = ("отдел:", "dept:", "department:")
AI_OWNER_VALUES = {"AI-фабрика", "AI Factory", "Nous"}
GROUP_DIGEST_OWNERS = {"Асыл", "Асылбек", "Данияр"}
ACTIONABLE_COMMENT_INTENTS = {"ai_request", "blocked", "done", "working", "question"}
FACTORY_PROOF_COMMENT_MARKERS = (
    "AI-фабрика взяла задачу в one-beam очередь",
    "Event: `todoist-task:",
    "Proof: `pages/audits/SATORY-AI-FACTORY-QUEUE-",
)
DELETE_CANDIDATE_TITLE_RE = re.compile(
    r"(?i)\b("
    r"приветствие|daily\s+reminder|ежедневн(?:ый|ая)\s+контроль|"
    r"настройка\s+брифинга|служебн(?:ая|ый)|test\s+task|ping\s+task"
    r")\b"
)
OPERATOR_PRIORITY_RE = re.compile(r"(?i)\b(apk|апк|bdl|бдл|erap|ерап|cerebro|церебро|satory|лу\s*\d+)\b")
PROOF_URLS = {
    "notion": re.compile(r"https://(?:www\.)?notion\.so/\S+", re.I),
    "google_drive": re.compile(r"https://(?:drive|docs)\.google\.com/\S+", re.I),
    "github": re.compile(r"https://github\.com/\S+", re.I),
    "vault": re.compile(r"\bpages/(?:projects|systems|audits|proof-pack|task-results|progress|tenants)/\S+", re.I),
    "todoist": re.compile(r"https://todoist\.com/\S+", re.I),
}
SECRET_RE = re.compile(
    r"(?i)\b(token|api[_-]?key|authorization|bearer|password|passwd|secret)\b\s*[:=]\s*[^\s`]+"
)


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def md_escape(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text.replace("|", "\\|")


def redact(value: Any) -> str:
    return SECRET_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", str(value or ""))


def note_item_id(note: dict[str, Any]) -> str:
    return str(note.get("item_id") or note.get("task_id") or note.get("parent_id") or "")


def notes_by_item(sync: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for note in sync.get("notes", []):
        if not isinstance(note, dict) or note.get("is_deleted"):
            continue
        item_id = note_item_id(note)
        if item_id:
            grouped[item_id].append(note)
    for rows in grouped.values():
        rows.sort(key=lambda row: str(row.get("posted_at") or row.get("created_at") or ""))
    return dict(grouped)


def proof_flags(*texts: str, notes: list[dict[str, Any]] | None = None) -> dict[str, bool]:
    combined = "\n".join(texts)
    flags = {name: bool(pattern.search(combined)) for name, pattern in PROOF_URLS.items()}
    flags["attachment"] = any(bool(note.get("file_attachment")) for note in notes or [])
    flags["human_checkable"] = any(flags[key] for key in ("notion", "google_drive", "github", "vault", "attachment"))
    flags["close_ready"] = bool(flags["notion"] and flags["google_drive"])
    return flags


def drive_proof_path_health(proof_counts: dict[str, int]) -> dict[str, Any]:
    """Separate active close-gate counts from durable Drive storage health."""

    audit_text = DRIVE_PROOF_AUDIT.read_text(encoding="utf-8") if DRIVE_PROOF_AUDIT.exists() else ""
    approved = all(
        token in audit_text
        for token in [
            "Google Drive proof artifact storage is approved",
            DRIVE_PROOF_URL,
            "HTTP/2 200",
            "gdrive:Satori A.I./Todoist Control Plane/",
        ]
    )
    if approved and proof_counts["google_drive"] == 0 and proof_counts["close_ready"] == 0:
        interpretation = "drive_path_approved_no_active_task_ready_to_close"
    elif proof_counts["google_drive"] > 0 and proof_counts["close_ready"] > 0:
        interpretation = "active_tasks_have_drive_and_close_ready_proof"
    elif approved:
        interpretation = "drive_path_approved_active_tasks_still_missing_close_proof"
    else:
        interpretation = "drive_path_unverified_or_blocked"
    return {
        "google_drive_storage": "approved" if approved else "unverified",
        "approval_audit": str(DRIVE_PROOF_AUDIT),
        "approval_url": DRIVE_PROOF_URL if approved else "",
        "active_task_google_drive_count": proof_counts["google_drive"],
        "active_task_close_ready_count": proof_counts["close_ready"],
        "interpretation": interpretation,
    }


def normalized_owner(labels: list[str], item: dict[str, Any]) -> str:
    if item.get("responsible_uid"):
        return "responsible_uid:" + str(item.get("responsible_uid"))
    return first_prefixed(labels, OWNER_PREFIXES, "missing")


def normalized_department(labels: list[str]) -> str:
    return first_prefixed(labels, DEPT_PREFIXES, "missing")


def is_ai_owner(owner: str) -> bool:
    return owner in AI_OWNER_VALUES or "AI" in owner or "ИИ" in owner


def comment_row(note: dict[str, Any]) -> dict[str, Any]:
    content = redact(note.get("content") or "")
    intent = comment_intent(content) or "context"
    if any(marker in content for marker in FACTORY_PROOF_COMMENT_MARKERS):
        intent = "context"
    return {
        "note_id": str(note.get("id") or ""),
        "posted_at": str(note.get("posted_at") or note.get("created_at") or ""),
        "author_id": str(note.get("posted_uid") or note.get("user_id") or ""),
        "intent": intent,
        "has_file_attachment": bool(note.get("file_attachment")),
        "proof_flags": proof_flags(content, notes=[note]),
        "content": content,
    }


def task_route(row: dict[str, Any], reminders: list[str]) -> tuple[str, str]:
    if row["status"] == "blocked":
        return (
            "blocked",
            "Не закрывать. Владелец должен написать точный блокер, следующий шаг и кто может снять блокировку.",
        )
    if row["context_state"] == "needs_source":
        return (
            "needs_source_enrichment",
            "Фабрика ищет реальный источник в Obsidian/gbrain/Notion/Gmail/Drive/GitHub. Без источника не выдумывать описание.",
        )
    if is_ai_owner(row["owner"]):
        return (
            "ready_for_ai_factory",
            "AI-фабрика может взять один маленький slice, но результат должен оставить proof в Todoist + Obsidian/gbrain; закрывать только после Notion+Drive proof.",
        )
    if reminders:
        return (
            "human_owner_reminder",
            "Оставить ежедневное напоминание человеку; AI помогает только после комментария `AI:` или явного поручения.",
        )
    return (
        "human_owned_monitor",
        "Следить за статусом и сроком. Не менять/закрывать без человеческого обновления или доказательства.",
    )


def latest_human_signal(comments: list[dict[str, Any]]) -> dict[str, str] | None:
    for comment in reversed(comments):
        intent = str(comment.get("intent") or "")
        if intent in ACTIONABLE_COMMENT_INTENTS:
            return {
                "note_id": str(comment.get("note_id") or ""),
                "posted_at": str(comment.get("posted_at") or ""),
                "intent": intent,
                "content": str(comment.get("content") or "")[:500],
            }
    return None


def delete_candidate_reason(row: dict[str, Any], comments: list[dict[str, Any]]) -> str:
    title = str(row.get("content") or row.get("title") or "")
    description = str(row.get("description") or "")
    if DELETE_CANDIDATE_TITLE_RE.search(title):
        return "meta_or_onboarding_noise_title"
    if row.get("context_state") == "needs_source" and not comments and DELETE_CANDIDATE_TITLE_RE.search(description):
        return "contextless_meta_task"
    return ""


def task_execution_metadata(
    row: dict[str, Any],
    *,
    route: str,
    next_action: str,
    reminders: list[str],
    flags: dict[str, bool],
    comments: list[dict[str, Any]],
) -> dict[str, Any]:
    signal = latest_human_signal(comments)
    delete_reason = delete_candidate_reason(row, comments)
    owner = str(row.get("owner") or "")
    title = str(row.get("content") or "")
    operator_task = owner in GROUP_DIGEST_OWNERS or bool(OPERATOR_PRIORITY_RE.search(title))

    if delete_reason:
        execution_state = "review_delete"
        queue_reason = delete_reason
        compact = "Проверить: удалить или объединить с реальной задачей. В чат не выводить."
    elif signal and signal["intent"] == "done":
        execution_state = "awaiting_proof"
        queue_reason = "human_done_signal_requires_proof"
        compact = "Проверить proof. Закрывать только если есть Notion + Drive."
    elif signal and signal["intent"] == "blocked":
        execution_state = "blocked"
        queue_reason = "human_blocked_signal"
        compact = "Зафиксировать точный блокер, кто снимает и следующий шаг."
    elif signal and signal["intent"] == "working":
        execution_state = "human_working"
        queue_reason = "human_working_signal"
        compact = "Ожидать обновление владельца; не дублировать напоминание."
    elif signal and signal["intent"] in {"ai_request", "question"}:
        execution_state = "queued"
        queue_reason = f"human_{signal['intent']}"
        compact = next_action
    elif route == "ready_for_ai_factory":
        execution_state = "queued"
        queue_reason = "ai_owner_ready"
        compact = next_action
    elif route == "needs_source_enrichment":
        execution_state = "queued"
        queue_reason = "missing_source_context"
        compact = "Найти реальный источник в Obsidian/gbrain/Notion/Drive/GitHub; не выдумывать."
    elif route == "blocked":
        execution_state = "blocked"
        queue_reason = "task_status_blocked"
        compact = "Снять блокер или запросить один конкретный внешний proof."
    elif reminders:
        execution_state = "digest_only"
        queue_reason = "human_reminder_digest"
        compact = "Показать человеку только в компактном дайджесте: статус, блокер, следующий шаг, proof."
    else:
        execution_state = "monitor"
        queue_reason = "no_actionable_signal"
        compact = next_action

    return {
        "execution_state": execution_state,
        "queue_reason": queue_reason,
        "delete_candidate_reason": delete_reason,
        "human_digest_eligible": bool(operator_task and not delete_reason),
        "latest_human_signal": signal,
        "next_action_compact": compact,
        "proof_ready": bool(flags.get("close_ready")),
    }


def build_deep_audit(sync: dict[str, Any], *, captured_at: dt.datetime | None = None) -> dict[str, Any]:
    captured = captured_at or now_kzt()
    filtered = filter_satory_sync(sync)
    audit = build_audit(filtered)
    projects = {str(project.get("id")): project for project in audit["_objects"]["projects"]}
    sections = {str(section.get("id")): section for section in audit["_objects"]["sections"]}
    grouped_notes = notes_by_item(filtered)
    today = captured.date()
    stale_before = captured - dt.timedelta(days=3)

    task_rows: list[dict[str, Any]] = []
    comment_rows: list[dict[str, Any]] = []
    for item in audit["_objects"]["items"]:
        if not isinstance(item, dict) or not active_item(item):
            continue
        task_id = str(item.get("id") or "")
        notes = grouped_notes.get(task_id, [])
        labels = labels_for(item)
        base = normalize_active_task(
            item,
            projects.get(str(item.get("project_id") or "")),
            sections.get(str(item.get("section_id") or "")),
            len(notes),
        )
        base["owner"] = normalized_owner(labels, item)
        base["department"] = normalized_department(labels)
        comments = [comment_row(note) for note in notes]
        comments_intents = collections.Counter(row["intent"] for row in comments)
        comments_text = [row["content"] for row in comments]
        flags = proof_flags(str(item.get("content") or ""), str(item.get("description") or ""), *comments_text, notes=notes)
        reminders = reminder_reasons(item, today=today, stale_before=stale_before)
        route, next_action = task_route(base, reminders)
        close_gate = "ready_to_close" if flags["close_ready"] else "do_not_close_missing_notion_or_drive_proof"
        execution = task_execution_metadata(
            base,
            route=route,
            next_action=next_action,
            reminders=reminders,
            flags=flags,
            comments=comments,
        )
        task_row = {
            **base,
            "description": redact(item.get("description") or ""),
            "comment_count": len(comments),
            "comments_intents": dict(sorted(comments_intents.items())),
            "comments": comments,
            "proof_flags": flags,
            "close_gate": close_gate,
            "factory_route": route,
            "next_factory_action": next_action,
            "reminder_reasons": reminders,
            **execution,
        }
        task_rows.append(task_row)
        for comment in comments:
            comment_rows.append(
                {
                    "task_id": task_id,
                    "task_title": base["content"],
                    "task_url": base["todoist_url"],
                    **comment,
                }
            )

    route_counts = collections.Counter(row["factory_route"] for row in task_rows)
    proof_counts = {
        key: sum(1 for row in task_rows if row["proof_flags"].get(key))
        for key in ["notion", "google_drive", "github", "vault", "attachment", "human_checkable", "close_ready"]
    }
    completion_guard = {
        "rule": "Не закрывать и не удалять задачу без Notion + Google Drive proof.",
        "close_ready_tasks": proof_counts["close_ready"],
        "missing_close_proof_tasks": len(task_rows) - proof_counts["close_ready"],
    }
    proof_path_health = drive_proof_path_health(proof_counts)
    factory_queue = [
        {
            "task_id": row["task_id"],
            "title": row["content"],
            "url": row["todoist_url"],
            "route": row["factory_route"],
            "status": row["status"],
            "context_state": row["context_state"],
            "owner": row["owner"],
            "next_action": row["next_factory_action"],
            "execution_state": row["execution_state"],
            "queue_reason": row["queue_reason"],
            "delete_candidate_reason": row["delete_candidate_reason"],
            "human_digest_eligible": row["human_digest_eligible"],
            "latest_human_signal": row["latest_human_signal"],
            "next_action_compact": row["next_action_compact"],
        }
        for row in task_rows
        if row["factory_route"] in {"ready_for_ai_factory", "needs_source_enrichment", "blocked"}
        or row["execution_state"] in {"queued", "review_delete"}
    ]
    return {
        "captured_at": captured.isoformat(),
        "scope": {
            "project_id": SATORY_TODOIST_PROJECT_ID,
            "project_names": ["Фабрика Satory ВКО", "Satory VKO Factory"],
            "personal_projects_touched": 0,
        },
        "counts": {
            "active_tasks": len(task_rows),
            "comments": len(comment_rows),
            "human_tasks": sum(1 for row in task_rows if not is_ai_owner(row["owner"])),
            "ai_owned_tasks": sum(1 for row in task_rows if is_ai_owner(row["owner"])),
            "contextless_tasks": sum(1 for row in task_rows if row["context_state"] == "needs_source"),
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
        "route_counts": dict(sorted(route_counts.items())),
        "proof_counts": proof_counts,
        "proof_path_health": proof_path_health,
        "completion_guard": completion_guard,
        "factory_queue": factory_queue,
        "tasks": task_rows,
        "comments": comment_rows,
    }


def render_markdown(report: dict[str, Any], json_path: Path) -> str:
    counts = report["counts"]
    lines = [
        "---",
        "type: audit",
        "id: AUDIT-satory-todoist-deep",
        'title: "Глубокий аудит Todoist Фабрика Satory ВКО"',
        f"date: {now_kzt().date().isoformat()}",
        "status: active",
        "tags: [audit, todoist, satory, factory, comments, google-drive, notion]",
        "---",
        "",
        "# Глубокий аудит Todoist Фабрика Satory ВКО",
        "",
        f"- Снято: `{report['captured_at']}`",
        f"- JSON с полным списком задач и комментариев: `{json_path}`",
        f"- Scope: только `Фабрика Satory ВКО` / `{report['scope']['project_id']}`",
        f"- Личных проектов затронуто: `{report['scope']['personal_projects_touched']}`",
        "",
        "## CTO-правило",
        "",
        "Todoist — очередь исполнения. Фабрика — исполнитель. Notion + Google Drive — человечески проверяемое доказательство перед закрытием. Obsidian/gbrain/OpenBrain/GitHub — долговременная память и воспроизводимость.",
        "",
        "Не закрывать и не удалять задачу только потому, что агент написал «готово». Закрытие допустимо только когда есть proof: Notion-страница + Google Drive/Docs/Sheets ссылка, либо честный блокер почему Drive/Notion пока невозможны.",
        "",
        "## Сводка",
        "",
        f"- Активных задач: `{counts['active_tasks']}`",
        f"- Комментариев/заметок: `{counts['comments']}`",
        f"- AI-owned задач: `{counts['ai_owned_tasks']}`",
        f"- Human-owned задач: `{counts['human_tasks']}`",
        f"- Без source-backed контекста: `{counts['contextless_tasks']}`",
        f"- Жёстких structural рисков: `{counts['hard_gate_risk_total']}`",
        "",
        "## Маршруты фабрики",
        "",
    ]
    for key, value in report["route_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Proof-счётчики", ""])
    for key, value in report["proof_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    health = report["proof_path_health"]
    lines.extend(
        [
            "",
            "## Proof-path health",
            "",
            f"- Google Drive storage: `{health['google_drive_storage']}`",
            f"- Active-task Google Drive proofs: `{health['active_task_google_drive_count']}`",
            f"- Active-task close-ready proofs: `{health['active_task_close_ready_count']}`",
            f"- Interpretation: `{health['interpretation']}`",
        ]
    )
    if health["approval_url"]:
        lines.append(f"- Approved Drive proof URL: {health['approval_url']}")
    lines.extend(["", "## Очередь фабрики", ""])
    if report["factory_queue"]:
        lines.extend(
            [
                "| Маршрут | Exec | Статус | Владелец | Задача | Следующее действие |",
                "|---|---|---|---|---|---|",
            ]
        )
        for row in report["factory_queue"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{md_escape(row['route'])}`",
                        f"`{md_escape(row['execution_state'])}`",
                        f"`{md_escape(status_display(row['status']))}`",
                        md_escape(row["owner"]),
                        f"[{md_escape(row['title'])}]({row['url']})",
                        md_escape(row["next_action_compact"] or row["next_action"]),
                    ]
                )
                + " |"
            )
    else:
        lines.append("- Нет задач, требующих маршрута фабрики.")
    lines.extend(["", "## Все активные задачи и комментарии", ""])
    for idx, row in enumerate(report["tasks"], start=1):
        lines.extend(
            [
                f"### {idx}. {row['content']} (`{row['task_id']}`)",
                "",
                f"- Todoist: {row['todoist_url']}",
                f"- Статус: `{status_display(row['status'])}`",
                f"- Раздел: `{row['section']}`",
                f"- Владелец: `{row['owner']}`",
                f"- Отдел: `{row['department']}`",
                f"- Приоритет: `{row['priority']}`",
                f"- Контекст: `{row['context_state']}`",
                f"- Маршрут фабрики: `{row['factory_route']}`",
                f"- Execution state: `{row['execution_state']}`",
                f"- Queue reason: `{row['queue_reason']}`",
                f"- Delete candidate: `{row['delete_candidate_reason']}`",
                f"- Human digest eligible: `{row['human_digest_eligible']}`",
                f"- Compact next action: `{row['next_action_compact']}`",
                f"- Close/delete gate: `{row['close_gate']}`",
                f"- Proof flags: `{json.dumps(row['proof_flags'], ensure_ascii=False, sort_keys=True)}`",
                f"- Комментариев: `{row['comment_count']}`",
            ]
        )
        if row["description"]:
            lines.extend(["", "Описание:", "", "```", row["description"][:1200], "```"])
        if row["comments"]:
            lines.extend(["", "Комментарии:"])
            for comment in row["comments"]:
                content = comment["content"][:1200]
                lines.extend(
                    [
                        f"- `{comment['note_id']}` `{comment['posted_at']}` intent=`{comment['intent']}` attachment=`{comment['has_file_attachment']}`",
                        "  ```",
                        "  " + content.replace("\n", "\n  "),
                        "  ```",
                    ]
                )
        lines.append("")
    return "\n".join(lines)


def render_index(report: dict[str, Any], json_path: Path, markdown_path: Path) -> str:
    counts = report["counts"]
    guard = report["completion_guard"]
    lines = [
        "---",
        "type: system",
        "id: satory-todoist-deep-audit-index",
        'title: "Индекс глубокого аудита Todoist Фабрика Satory ВКО"',
        f"last_updated: {report['captured_at']}",
        f"status: {report['status'] if 'status' in report else 'active'}",
        "tags: [todoist, satory, factory, comments, proof, gbrain, notion, google-drive]",
        "---",
        "",
        "# Индекс глубокого аудита Todoist Фабрика Satory ВКО",
        "",
        "Этот файл короткий специально: его должен быстро находить gbrain/OpenBrain. Полный построчный аудит лежит отдельным большим файлом.",
        "",
        "## Артефакты",
        "",
        f"- Полный Markdown-аудит: `{markdown_path}`",
        f"- Полный JSON-аудит: `{json_path}`",
        "- Scope: только `Фабрика Satory ВКО` / `6gJ5j8PRVVCWpgCq`.",
        "- Личных проектов затронуто: `0`.",
        "",
        "## Сводка",
        "",
        f"- Активных задач: `{counts['active_tasks']}`",
        f"- Комментариев Todoist прочитано: `{counts['comments']}`",
        f"- AI-owned задач: `{counts['ai_owned_tasks']}`",
        f"- Human-owned задач: `{counts['human_tasks']}`",
        f"- Без source-backed контекста: `{counts['contextless_tasks']}`",
        f"- Жёстких structural рисков: `{counts['hard_gate_risk_total']}`",
        "",
        "## Маршруты фабрики",
        "",
    ]
    for key, value in report["route_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Proof gate", ""])
    lines.append(f"- Правило: {guard['rule']}")
    lines.append(f"- Готовы к закрытию: `{guard['close_ready_tasks']}`")
    lines.append(f"- Нельзя закрывать без Notion+Drive proof: `{guard['missing_close_proof_tasks']}`")
    lines.append("")
    lines.append("Если `close_ready_tasks=0`, это не сбой фабрики. Это честный сигнал: работа остается открытой, пока нет human-checkable proof.")
    health = report["proof_path_health"]
    lines.extend(
        [
            "",
            "## Proof-path health",
            "",
            f"- Google Drive storage: `{health['google_drive_storage']}`",
            f"- Active-task Google Drive proofs: `{health['active_task_google_drive_count']}`",
            f"- Active-task close-ready proofs: `{health['active_task_close_ready_count']}`",
            f"- Interpretation: `{health['interpretation']}`",
        ]
    )
    if health["approval_url"]:
        lines.append(f"- Approved Drive proof URL: {health['approval_url']}")
    return "\n".join(lines)


def default_markdown_path() -> Path:
    stamp = now_kzt().strftime("%Y-%m-%d-%H%M")
    return DEFAULT_AUDIT_DIR / f"AUDIT-satory-todoist-deep-{stamp}.md"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    client = Todoist(token_from_env(args.env_file))
    report = build_deep_audit(client.sync())
    markdown_path = args.markdown or default_markdown_path()
    report["status"] = "done" if report["counts"]["hard_gate_risk_total"] == 0 else "not_done"
    if not args.dry_run:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        args.index.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        markdown_path.write_text(render_markdown(report, args.json_out), encoding="utf-8")
        args.index.write_text(render_index(report, args.json_out, markdown_path), encoding="utf-8")
    payload = {
        "status": report["status"],
        "captured_at": report["captured_at"],
        "wrote": not args.dry_run,
        "json": str(args.json_out),
        "markdown": str(markdown_path),
        "index": str(args.index),
        "counts": report["counts"],
        "risk_counts": report["risk_counts"],
        "route_counts": report["route_counts"],
        "proof_counts": report["proof_counts"],
        "proof_path_health": report["proof_path_health"],
        "completion_guard": report["completion_guard"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(report, args.json_out))
    return 0 if payload["status"] == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
