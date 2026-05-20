#!/usr/bin/env python3
"""Daily human-owner reminders for the Nous control plane.

OpenClaw owns worker execution. This script owns the human escalation loop:
find human-owned Todoist tasks that are overdue, blocked, high-priority, or
stale, then ping once per day through Todoist comments and Telegram digests.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from todoist_control_plane_audit import SATORY_TODOIST_PROJECT_ID, Todoist, active_item, labels_for, token_from_env
from todoist_control_plane_export import derive_active_status, status_display
try:
    from factory_orchestration_policy import (
        ROUTE_GROK_DECISION,
        ROUTE_LONG_WORK_GOAL,
        classify_text as classify_factory_route,
    )
except Exception:
    ROUTE_GROK_DECISION = "grok_decision_review"
    ROUTE_LONG_WORK_GOAL = "long_work_goal"
    classify_factory_route = None


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_STATUS_PAGE = Path("pages/systems/human-owner-reminder-status.md")
DEFAULT_LEDGER = Path("pages/systems/human-owner-reminder-ledger.json")
DEFAULT_AUDIT_DIR = Path("pages/audits")
DEFAULT_OWNERS = ("Мади", "Данияр", "Асылбек", "Асыл")
RUN_TASK = Path(os.environ.get("NOUS_RUN_TASK", "/Users/madia/nous-agaas/run_task.py"))
RUN_TASK_PYTHON = Path(os.environ.get("NOUS_RUN_TASK_PYTHON", sys.executable))
OWNER_PREFIXES = ("исполнитель:", "owner:", "assignee:")
AI_COMMENT_PREFIXES = (
    "Ежедневное напоминание AI-фабрики",
    "AI-фабрика увидела",
    "AI-фабрика приняла",
    "Русская версия предыдущего комментария:",
)
CONTEXT_COMMENT_PREFIX_RE = re.compile(
    r"(?im)^\s*(notion|todoist|github|git|obsidian|gbrain|openbrain|source|evidence|proof|audit|context|"
    r"источник|контекст|доказательство|доказательства|ссылка|ссылки|план vault|черновик ответа|статус/решение)\s*:"
)
CONTEXT_ARTIFACT_RE = re.compile(
    r"(?i)(https://www\.notion\.so|pages/(projects|systems|audits|proof-pack|task-results|progress)/|"
    r"HANDOFF-AUTO-|AUDIT-|PROOF-|GOAL-\d|task-result)"
)
CONTEXT_TEMPLATE_PHRASES = (
    "если блокировано, написать блокер",
    "если заблокировано, напишите",
    "если заблокировано, написать",
    "что нужно: обновить статус",
    "действие фабрики: комментарии в todoist добавлены",
    "if blocked, write blocker",
)
DONE_RE = re.compile(r"(?i)\b(done|complete|completed)\b|готово|сделано|выполнено|закрыто|завершено")
BLOCKED_RE = re.compile(r"(?i)\b(blocked|blocker)\b|заблок|блокер|не получается|не могу|нет доступа|нужен доступ|мешает|ошибка")
WORKING_RE = re.compile(r"(?i)\b(in progress|working|started)\b|в работе|работаю|делаю|начал|начала|беру")
AI_REQUEST_RE = re.compile(r"(?i)^\s*(ai|ии|фабрика|factory)\s*[:：-]")
QUESTION_RE = re.compile(
    r"(?i)\?|(?:есть|у меня|мой)\s+вопрос|вопрос\s*:|\bquestion\b|подскажи|помоги|что делать|как правильно|нужно ли|можно ли"
)
OWNER_ALIASES = {
    "madi": "Мади",
    "мади": "Мади",
    "daniyar": "Данияр",
    "даниар": "Данияр",
    "данияр": "Данияр",
    "assylbek": "Асылбек",
    "asylbek": "Асылбек",
    "асылбек": "Асылбек",
    "assyl": "Асыл",
    "asyl": "Асыл",
    "асыл": "Асыл",
}
OWNER_CHAT_ENV = {
    "Мади": ("MADI_TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID"),
    "Данияр": ("DANIYAR_TELEGRAM_CHAT_ID", "DANIYAR_CHAT_ID"),
    "Асылбек": ("ASSYLBEK_TELEGRAM_CHAT_ID", "ASYLBEK_TELEGRAM_CHAT_ID", "ASSYLBEK_CHAT_ID"),
    "Асыл": ("ASSYL_TELEGRAM_CHAT_ID", "ASYL_TELEGRAM_CHAT_ID", "ASSYL_CHAT_ID"),
}
OWNER_FALLBACK_CHAT_ENV = (
    "OWNER_REMINDER_FALLBACK_CHAT_ID",
    "TELEGRAM_GROUP_CHAT_ID",
    "TELEGRAM_FULL_CHAT_CHAT_IDS",
    "TELEGRAM_GROUP_OBSERVE_CHAT_IDS",
)


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def iso_now() -> str:
    return now_kzt().isoformat()


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [str(part) for part in cmd],
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "ok": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "timeout",
            "ok": False,
        }


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values


def tail(text: str, limit: int = 1200) -> str:
    clean = str(text or "").strip()
    return clean if len(clean) <= limit else clean[-limit:]


def parse_ts(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(ALMATY)


def due_date(item: dict[str, Any]) -> dt.date | None:
    due = item.get("deadline") or item.get("due")
    value: Any = due
    if isinstance(due, dict):
        value = due.get("datetime") or due.get("date")
    if not value:
        return None
    text = str(value)
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(ALMATY).date()
    except ValueError:
        pass
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def owner_from_labels(labels: list[str]) -> str | None:
    for label in labels:
        for prefix in OWNER_PREFIXES:
            if label.startswith(prefix):
                raw = label.split(":", 1)[1].strip()
                return OWNER_ALIASES.get(raw.casefold(), raw)
    return None


def task_url(item: dict[str, Any]) -> str:
    task_id = str(item.get("id") or "")
    return str(item.get("url") or f"https://todoist.com/showTask?id={task_id}")


def reminder_reasons(item: dict[str, Any], *, today: dt.date, stale_before: dt.datetime) -> list[str]:
    labels = labels_for(item)
    status = derive_active_status(item, labels)
    reasons: list[str] = []
    due = due_date(item)
    if due and due < today:
        reasons.append(f"срок просрочен: {due.isoformat()}")
    elif due and due == today:
        reasons.append("срок сегодня")
    if status == "blocked":
        reasons.append("статус заблокировано")
    if int(item.get("priority") or 1) >= 4:
        reasons.append("приоритет P4")
    updated = parse_ts(item.get("updated_at") or item.get("added_at"))
    if updated and updated < stale_before:
        reasons.append(f"нет обновления с {updated.date().isoformat()}")
    return reasons


def build_plan(
    sync: dict[str, Any],
    *,
    owners: set[str],
    stale_days: int,
    max_per_owner: int,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    current = now or now_kzt()
    today = current.date()
    stale_before = current - dt.timedelta(days=stale_days)
    selected: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    comment_replies: list[dict[str, Any]] = []
    grouped_notes = notes_by_item(sync)
    considered = 0
    for item in sync.get("items", []):
        if not isinstance(item, dict) or not active_item(item):
            continue
        if str(item.get("project_id") or "") != SATORY_TODOIST_PROJECT_ID:
            continue
        labels = labels_for(item)
        owner = owner_from_labels(labels)
        if not owner or owner not in owners:
            continue
        considered += 1
        task_id = str(item.get("id") or "")
        for note in grouped_notes.get(task_id, []):
            posted_at = parse_ts(note.get("posted_at") or note.get("created_at"))
            if posted_at and posted_at < current - dt.timedelta(days=14):
                continue
            content = str(note.get("content") or "")
            intent = comment_intent(content)
            if not intent:
                continue
            comment_replies.append(
                {
                    "note_id": str(note.get("id") or ""),
                    "task_id": task_id,
                    "owner": owner,
                    "intent": intent,
                    "content": str(item.get("content") or ""),
                    "comment": content,
                    "posted_at": posted_at.isoformat() if posted_at else "",
                    "url": task_url(item),
                }
            )
        reasons = reminder_reasons(item, today=today, stale_before=stale_before)
        if not reasons:
            continue
        updated = parse_ts(item.get("updated_at") or item.get("added_at"))
        due = due_date(item)
        selected[owner].append(
            {
                "task_id": str(item.get("id") or ""),
                "owner": owner,
                "content": str(item.get("content") or ""),
                "status": derive_active_status(item, labels),
                "priority": int(item.get("priority") or 1),
                "due": due.isoformat() if due else "",
                "updated_at": updated.isoformat() if updated else "",
                "reasons": reasons,
                "url": task_url(item),
                "labels": labels,
            }
        )
    for owner, rows in selected.items():
        rows.sort(
            key=lambda row: (
                0 if any("просрочен" in reason for reason in row["reasons"]) else 1,
                0 if row["status"] == "blocked" else 1,
                -int(row["priority"]),
                row["due"] or "9999-99-99",
                row["updated_at"] or "",
            )
        )
        selected[owner] = rows[:max_per_owner]
    return {
        "captured_at": current.isoformat(),
        "owners": sorted(owners),
        "stale_days": stale_days,
        "max_per_owner": max_per_owner,
        "considered_human_tasks": considered,
        "reminders": dict(selected),
        "reminder_count": sum(len(rows) for rows in selected.values()),
        "comment_replies": comment_replies,
        "comment_reply_count": len(comment_replies),
    }


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sent": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sent": {}}
    return payload if isinstance(payload, dict) else {"sent": {}}


def already_pinged(ledger: dict[str, Any], day: str, owner: str, task_id: str) -> bool:
    return bool(ledger.get("sent", {}).get(day, {}).get(owner, {}).get(task_id))


def mark_pinged(ledger: dict[str, Any], day: str, owner: str, task_id: str, channel: str) -> None:
    ledger.setdefault("sent", {}).setdefault(day, {}).setdefault(owner, {})[task_id] = {
        "at": iso_now(),
        "channel": channel,
    }


def already_replied_to_comment(ledger: dict[str, Any], note_id: str) -> bool:
    return bool(ledger.get("comment_replies", {}).get(str(note_id)))


def mark_replied_to_comment(
    ledger: dict[str, Any],
    note_id: str,
    task_id: str,
    intent: str,
    extra: dict[str, Any] | None = None,
) -> None:
    row = {
        "at": iso_now(),
        "task_id": str(task_id),
        "intent": intent,
    }
    if extra:
        row.update(extra)
    ledger.setdefault("comment_replies", {})[str(note_id)] = row


def notes_by_item(sync: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for note in sync.get("notes", []):
        if not isinstance(note, dict) or note.get("is_deleted"):
            continue
        item_id = str(note.get("item_id") or note.get("task_id") or note.get("parent_id") or "")
        if item_id:
            grouped[item_id].append(note)
    for rows in grouped.values():
        rows.sort(key=lambda row: str(row.get("posted_at") or row.get("created_at") or ""))
    return dict(grouped)


def is_ai_comment(text: str) -> bool:
    clean = str(text or "").strip()
    return any(clean.startswith(prefix) for prefix in AI_COMMENT_PREFIXES)


def is_context_comment(text: str) -> bool:
    clean = str(text or "").strip()
    folded = clean.casefold()
    if CONTEXT_COMMENT_PREFIX_RE.search(clean):
        return True
    if CONTEXT_ARTIFACT_RE.search(clean):
        return True
    return any(phrase in folded for phrase in CONTEXT_TEMPLATE_PHRASES)


def comment_intent(text: str) -> str | None:
    clean = str(text or "").strip()
    if not clean or is_ai_comment(clean):
        return None
    if AI_REQUEST_RE.search(clean):
        return "ai_request"
    if is_context_comment(clean):
        return None
    if BLOCKED_RE.search(clean):
        return "blocked"
    if DONE_RE.search(clean):
        return "done"
    if WORKING_RE.search(clean):
        return "working"
    if QUESTION_RE.search(clean):
        return "question"
    return None


def comment_reply_text(row: dict[str, Any]) -> str:
    task_title = re.sub(r"\s+", " ", row.get("content", "")).strip()[:120]
    if row["intent"] == "ai_request":
        return (
            "AI-фабрика увидела запрос в комментарии, но автоматический запуск был отключен для этого прохода. "
            "Чтобы взять задачу без потери контекста, оставьте один комментарий в формате: "
            "`AI: результат нужен такой-то; источник такой-то; срок такой-то`. "
            f"Задача: {task_title}"
        )
    if row["intent"] == "blocked":
        return (
            "AI-фабрика увидела блокер. Напишите одним комментарием: 1) что именно мешает, "
            "2) кто следующий владелец, 3) какой срок, 4) может ли AI-фабрика сама это сделать. "
            "Если может, начните комментарий с `AI:`."
        )
    if row["intent"] == "done":
        return (
            "AI-фабрика увидела комментарий «готово». Если работа реально завершена, отметьте задачу выполненной в Todoist. "
            "Если не завершена — напишите оставшийся блокер или следующий шаг."
        )
    if row["intent"] == "working":
        return (
            "AI-фабрика приняла статус «в работе». Обновите, пожалуйста, следующий конкретный шаг и срок в Todoist. "
            "Если нужна помощь AI-фабрики, начните комментарий с `AI:`."
        )
    return (
        "AI-фабрика увидела вопрос в комментарии. Если нужен ответ или действие AI, напишите отдельный комментарий "
        "с `AI:` и ожидаемым результатом. Иначе укажите ответственного человека и срок."
    )


def ai_factory_prompt(row: dict[str, Any]) -> str:
    task_title = re.sub(r"\s+", " ", row.get("content", "")).strip()
    comment = str(row.get("comment") or "").strip()
    return f"""Ты AI-фабрика Satory. Это явный запрос из Todoist-комментария, начинающегося с `AI:`.

Ограничения:
1. Работай только по проекту `Фабрика Satory ВКО`.
2. Не трогай личные проекты, личные задачи и внешние сообщения клиентам.
3. Выполни ровно один конкретный шаг, который можно честно сделать из данного контекста.
4. Если нельзя выполнить без доступа, денег, юридического решения или человеческого подтверждения, верни `БЛОКЕР:` и список того, что нужно.
5. Пиши по-русски, коротко, с доказательством или следующим действием.

Todoist:
- task_id: {row.get("task_id")}
- owner: {row.get("owner")}
- url: {row.get("url")}
- title: {task_title}

Комментарий человека:
{comment}

Формат ответа:
Статус: готово | в работе | заблокировано
Что сделал:
Доказательство:
Следующий шаг:
"""


def dispatch_ai_factory_request(
    wiki: Path,
    row: dict[str, Any],
    *,
    dry_run: bool,
    timeout: int,
) -> dict[str, Any]:
    source = f"todoist-comment:{row.get('task_id')}:{row.get('note_id')}"
    prompt = ai_factory_prompt(row)
    route = _factory_route_for_comment(row)
    model = _worker_model_for_route(route)
    if dry_run:
        return {"ok": True, "source": source, "detail": "dry-run", "route": route.get("route"), "model": model}
    if not RUN_TASK.exists():
        return {"ok": False, "source": source, "detail": f"run_task.py missing at {RUN_TASK}"}
    cmd = [
        str(RUN_TASK_PYTHON),
        str(RUN_TASK),
        "--source",
        source,
        "--timeout",
        str(timeout),
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)
    result = run(cmd, cwd=wiki, timeout=timeout + 45)
    return {
        "ok": result["ok"],
        "source": source,
        "detail": tail(result["stdout"] or result["stderr"], 2500),
        "returncode": result.get("returncode"),
        "route": route.get("route"),
        "model": model,
    }


def ai_request_reply_text(row: dict[str, Any], factory_result: dict[str, Any]) -> str:
    if factory_result.get("ok"):
        detail = tail(str(factory_result.get("detail") or ""), 1800)
        return (
            "AI-фабрика взяла запрос из комментария и провела один factory-slice через OpenClaw/run_task.\n"
            f"Маршрут: `{factory_result.get('route') or 'openclaw'}`; модель: `{factory_result.get('model') or 'agent-default'}`.\n\n"
            f"Источник: `{factory_result.get('source')}`\n\n"
            f"{detail}"
        )
    return (
        "AI-фабрика увидела запрос, но автоматический запуск не завершился. "
        "Задача не закрыта и не считается готовой.\n\n"
        f"Источник: `{factory_result.get('source')}`\n"
        f"Маршрут: `{factory_result.get('route') or 'openclaw'}`; модель: `{factory_result.get('model') or 'agent-default'}`.\n"
        f"Блокер: `{factory_result.get('detail')}`\n\n"
        "Что нужно: Мади или ответственный должен проверить блокер, затем повторить комментарий с `AI:`."
    )


def _factory_route_for_comment(row: dict[str, Any]) -> dict[str, Any]:
    if classify_factory_route is None:
        return {"route": "openclaw_routine", "worker_model": "deepseek-v4-flash", "first_pass_model": "grok-reasoning"}
    text = "\n".join(str(row.get(key) or "") for key in ("content", "comment"))
    try:
        return classify_factory_route(text).to_dict()
    except Exception:
        return {"route": "openclaw_routine", "worker_model": "deepseek-v4-flash", "first_pass_model": "grok-reasoning"}


def _worker_model_for_route(route: dict[str, Any]) -> str:
    if route.get("route") == ROUTE_GROK_DECISION:
        return str(route.get("first_pass_model") or "grok-reasoning")
    if route.get("route") == ROUTE_LONG_WORK_GOAL:
        return str(route.get("worker_model") or "deepseek-v4-flash")
    return str(route.get("worker_model") or "deepseek-v4-flash")


def comment_text(row: dict[str, Any], day: str) -> str:
    reasons = "; ".join(row["reasons"])
    return (
        f"Ежедневное напоминание AI-фабрики ({day}). "
        f"Ответственный: {row['owner']}. Статус: {status_display(row['status'])}. "
        f"Причина: {reasons}. "
        "Действие: обновите задачу в Todoist — в работе / готово / заблокировано; "
        "если заблокировано, напишите что мешает и кому передать."
    )


def add_todoist_comment(client: Todoist, task_id: str, content: str) -> dict[str, Any]:
    payload = client.request("POST", "/comments", json={"task_id": task_id, "content": content})
    return payload if isinstance(payload, dict) else {"ok": True}


def env_chat_id(owner: str, env: dict[str, str]) -> str | None:
    for key in OWNER_CHAT_ENV.get(owner, ()):
        if env.get(key):
            return env[key]
    return None


def first_chat_id(value: str | None) -> str | None:
    if not value:
        return None
    for part in re.split(r"[,\\s]+", value.strip()):
        if part:
            return part
    return None


def fallback_owner_chat_id(env: dict[str, str]) -> str | None:
    for key in OWNER_FALLBACK_CHAT_ENV:
        chat_id = first_chat_id(env.get(key))
        if chat_id:
            return chat_id
    return None


def digest_for_owner(owner: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"Ежедневный контроль Satory: {owner}", ""]
    for row in rows:
        reasons = "; ".join(row["reasons"])
        content = re.sub(r"\s+", " ", row["content"]).strip()
        lines.append(f"- {content[:120]}")
        lines.append(f"  Статус: P{row['priority']} {status_display(row['status'])}")
        lines.append(f"  Блокер/причина: {reasons}")
        lines.append("  Следующий шаг: обновить статус или написать точный блокер.")
        lines.append(f"  Proof: {row['url']}")
    lines.append("")
    lines.append("Внутренние AI-комментарии в чат не выводятся. Чат видит только статус, блокер, следующий шаг и proof.")
    return "\n".join(lines)


def digest_for_missing_direct_chats(missing: list[tuple[str, list[dict[str, Any]]]], *, group_fallback: bool = False) -> str:
    if group_fallback:
        lines = ["Ежедневный контроль Satory — кратко", "Нет личного Telegram DM для владельцев, поэтому только компактный общий дайджест.", ""]
    else:
        lines = ["Ежедневный контроль Satory — нет прямого Telegram для владельцев", ""]
    for owner, rows in missing:
        lines.append(f"{owner}:")
        visible_rows = rows[:3]
        for row in visible_rows:
            reasons = "; ".join(row["reasons"])
            content = re.sub(r"\s+", " ", row["content"]).strip()
            lines.append(f"- {content[:100]}")
            lines.append(f"  Статус: P{row['priority']} {status_display(row['status'])}")
            lines.append(f"  Блокер: {reasons}")
            lines.append("  Следующий шаг: обновить статус/блокер в Todoist.")
            lines.append(f"  Proof: {row['url']}")
        hidden = len(rows) - len(visible_rows)
        if hidden > 0:
            lines.append(f"- Еще {hidden} задач скрыто из группового дайджеста, чтобы не спамить чат.")
    lines.append("")
    if group_fallback:
        lines.append("Действие фабрики: общий дайджест отправлен. Личные DM включатся после добавления owner chat_id в env.")
    else:
        lines.append("Действие фабрики: прямой Telegram включится после добавления chat_id в env.")
    return "\n".join(lines)


def send_telegram(wiki: Path, message: str, chat_id: str | None, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"ok": True, "detail": "dry-run", "chat_id": chat_id or "default"}
    cmd = ["bash", "tools/tg_send.sh"]
    if chat_id:
        cmd.extend(["--chat", chat_id])
    cmd.append(message)
    env = os.environ.copy()
    env.setdefault("AUTONOMY_BYPASS", "1")
    result = run(cmd, cwd=wiki, timeout=45, env=env)
    return {"ok": result["ok"], "detail": tail(result["stdout"] + result["stderr"]), "chat_id": chat_id or "default"}


def render_status(plan: dict[str, Any], apply_result: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: system",
        "id: human-owner-reminder-status",
        'title: "Статус контроля человеческих задач"',
        f"last_updated: {plan['captured_at']}",
        "status: done",
        "tags: [todoist, telegram, humans, factory, hermes]",
        "---",
        "",
        "# Статус контроля человеческих задач",
        "",
        f"- Последний запуск: `{plan['captured_at']}`",
        f"- Режим: `{apply_result.get('mode', 'unknown')}`",
        f"- Человеческих задач проверено: `{plan['considered_human_tasks']}`",
        f"- Кандидатов на напоминание: `{plan['reminder_count']}`",
        f"- Нужно ответить на комментарии: `{plan.get('comment_reply_count', 0)}`",
        f"- Generic Todoist reminder comments: `{'enabled' if apply_result.get('todoist_reminder_comments_enabled') else 'disabled_digest_only'}`",
        f"- Комментариев-напоминаний добавлено: `{apply_result.get('todoist_comments_added', 0)}`",
        f"- Ответов на комментарии добавлено: `{apply_result.get('comment_replies_added', 0)}`",
        f"- Запросов в AI-фабрику запущено: `{apply_result.get('factory_requests_started', 0)}`",
        f"- Запросов в AI-фабрику не выполнено: `{apply_result.get('factory_requests_failed', 0)}`",
        f"- Telegram-дайджестов отправлено: `{apply_result.get('telegram_sent', 0)}`",
        f"- Владельцев без личного Telegram DM: `{apply_result.get('missing_direct_owner_chats', 0)}`",
        f"- Telegram fallback в общий чат: `{apply_result.get('telegram_group_fallback_sent', 0)}`",
        "",
        "| Ответственный | Задач |",
        "|---|---:|",
    ]
    for owner in plan["owners"]:
        lines.append(f"| {owner} | `{len(plan['reminders'].get(owner, []))}` |")
    lines.append("")
    return "\n".join(lines)


def render_audit(plan: dict[str, Any], apply_result: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: audit",
        f"id: HUMAN-OWNER-REMINDER-{now_kzt().strftime('%Y-%m-%d')}",
        f'title: "Аудит контроля человеческих задач - {now_kzt().strftime("%Y-%m-%d")}"',
        f"date: {now_kzt().date().isoformat()}",
        "status: done",
        "tags: [todoist, human-owner-reminder, factory, telegram]",
        "---",
        "",
        f"# Аудит контроля человеческих задач - {now_kzt().strftime('%Y-%m-%d')}",
        "",
        "## Сводка",
        "",
        f"- Снято состояние: `{plan['captured_at']}`",
        f"- Режим: `{apply_result.get('mode', 'unknown')}`",
        f"- Человеческих задач проверено: `{plan['considered_human_tasks']}`",
        f"- Кандидатов на напоминание: `{plan['reminder_count']}`",
        f"- Нужно ответить на комментарии: `{plan.get('comment_reply_count', 0)}`",
        f"- Generic Todoist reminder comments: `{'enabled' if apply_result.get('todoist_reminder_comments_enabled') else 'disabled_digest_only'}`",
        f"- Комментариев-напоминаний добавлено: `{apply_result.get('todoist_comments_added', 0)}`",
        f"- Ответов на комментарии добавлено: `{apply_result.get('comment_replies_added', 0)}`",
        f"- Запросов в AI-фабрику запущено: `{apply_result.get('factory_requests_started', 0)}`",
        f"- Запросов в AI-фабрику не выполнено: `{apply_result.get('factory_requests_failed', 0)}`",
        f"- Telegram-дайджестов отправлено: `{apply_result.get('telegram_sent', 0)}`",
        f"- Владельцев без личного Telegram DM: `{apply_result.get('missing_direct_owner_chats', 0)}`",
        f"- Telegram fallback в общий чат: `{apply_result.get('telegram_group_fallback_sent', 0)}`",
        "",
        "## Напоминания",
        "",
    ]
    for owner, rows in plan["reminders"].items():
        lines.append(f"### {owner}")
        for row in rows:
            lines.append(f"- `{row['task_id']}` P{row['priority']} `{status_display(row['status'])}` — {row['content']}")
            lines.append(f"  - Причина: {'; '.join(row['reasons'])}")
            lines.append(f"  - Todoist: {row['url']}")
        lines.append("")
    if plan.get("comment_replies"):
        lines.extend(["## План ответов на комментарии", ""])
        for row in plan["comment_replies"]:
            lines.append(f"- `{row['note_id']}` -> `{row['task_id']}` `{row['intent']}` — {row['content']}")
            lines.append(f"  - Комментарий: {row['comment'][:240]}")
        lines.append("")
    lines.extend(["## Результат применения", "", "```json", json.dumps(apply_result, ensure_ascii=False, indent=2, default=str), "```", ""])
    return "\n".join(lines)


def writeback(wiki: Path, paths: list[Path], dry_run: bool) -> dict[str, Any]:
    if dry_run or not paths:
        return {"ok": True, "detail": "dry-run or no paths"}
    rels = [str(path) for path in paths]
    add = run(["git", "-c", "core.hooksPath=/dev/null", "add", *rels], cwd=wiki, timeout=90)
    if not add["ok"]:
        return {"ok": False, "detail": tail(add["stdout"] + add["stderr"])}
    diff = run(["git", "diff", "--cached", "--quiet", "--", *rels], cwd=wiki, timeout=45)
    committed = False
    if diff["returncode"] == 1:
        commit = run(
            ["git", "-c", "core.hooksPath=/dev/null", "commit", "--no-verify", "-m", f"human-owner-reminder: {now_kzt().strftime('%Y-%m-%d')}"],
            cwd=wiki,
            timeout=120,
        )
        if not commit["ok"]:
            return {"ok": False, "detail": tail(commit["stdout"] + commit["stderr"])}
        committed = True
    elif diff["returncode"] != 0:
        return {"ok": False, "detail": tail(diff["stdout"] + diff["stderr"])}
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 3):
        pull = run(["git", "pull", "--rebase", "origin", "main"], cwd=wiki, timeout=180)
        github_rebase: dict[str, Any] = {"ok": True, "detail": "github remote absent"}
        if pull["ok"]:
            remote = run(["git", "remote", "get-url", "github"], cwd=wiki, timeout=30)
            if remote["ok"]:
                fetch = run(["git", "fetch", "github", "main"], cwd=wiki, timeout=120)
                github_rebase = {"ok": fetch["ok"], "detail": tail(fetch["stdout"] + fetch["stderr"])}
                if fetch["ok"]:
                    rebase = run(["git", "-c", "core.hooksPath=/dev/null", "rebase", "github/main"], cwd=wiki, timeout=180)
                    github_rebase = {"ok": rebase["ok"], "detail": tail(rebase["stdout"] + rebase["stderr"])}
                    if not rebase["ok"]:
                        run(["git", "rebase", "--abort"], cwd=wiki, timeout=45)
        origin = run(["git", "push", "origin", "main"], cwd=wiki, timeout=180) if pull["ok"] and github_rebase["ok"] else {"ok": False, "stdout": "", "stderr": "pre-push rebase failed"}
        github = run(["git", "push", "github", "main"], cwd=wiki, timeout=180) if pull["ok"] and github_rebase["ok"] else {"ok": False, "stdout": "", "stderr": "pre-push rebase failed"}
        attempt_detail = {
            "attempt": attempt,
            "pull": tail(pull["stdout"] + pull["stderr"]),
            "github_rebase": github_rebase,
            "origin": tail(origin["stdout"] + origin["stderr"]),
            "github": tail(github["stdout"] + github["stderr"]),
            "ok": bool(origin["ok"] and github["ok"]),
        }
        attempts.append(attempt_detail)
        if attempt_detail["ok"]:
            return {"ok": True, "detail": {"committed": committed, "attempts": attempts}}
        time.sleep(1)
    return {"ok": False, "detail": {"committed": committed, "attempts": attempts}}


def apply_reminders(
    client: Todoist,
    plan: dict[str, Any],
    *,
    wiki: Path,
    ledger_path: Path,
    dry_run: bool,
    no_todoist_comments: bool,
    todoist_reminder_comments: bool,
    no_telegram: bool,
    no_comment_replies: bool,
    no_ai_dispatch: bool,
    comment_sweep_only: bool,
    max_ai_requests_per_run: int,
    ai_request_timeout: int,
    sleep: float,
    runtime_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    day = now_kzt().date().isoformat()
    ledger = load_ledger(wiki / ledger_path)
    result: dict[str, Any] = {
        "todoist_comments_added": 0,
        "todoist_comments_skipped": 0,
        "todoist_reminder_comments_enabled": bool(todoist_reminder_comments and not no_todoist_comments),
        "comment_replies_added": 0,
        "comment_replies_skipped": 0,
        "factory_requests_started": 0,
        "factory_requests_failed": 0,
        "mode": "comment_sweep_only"
        if comment_sweep_only
        else ("daily_reminder_plus_comments" if todoist_reminder_comments and not no_todoist_comments else "daily_digest_plus_comment_sweep"),
        "telegram_sent": 0,
        "telegram_skipped": 0,
        "telegram_group_fallback_sent": 0,
        "missing_direct_owner_chats": 0,
        "errors": [],
    }
    if not comment_sweep_only:
        for owner, rows in plan["reminders"].items():
            for row in rows:
                if already_pinged(ledger, day, owner, row["task_id"]):
                    result["todoist_comments_skipped"] += 1
                    continue
                if no_todoist_comments or not todoist_reminder_comments:
                    result["todoist_comments_skipped"] += 1
                    mark_pinged(ledger, day, owner, row["task_id"], "digest-only")
                    continue
                if dry_run:
                    result["todoist_comments_added"] += 1
                    mark_pinged(ledger, day, owner, row["task_id"], "dry-run")
                    continue
                try:
                    add_todoist_comment(client, row["task_id"], comment_text(row, day))
                    result["todoist_comments_added"] += 1
                    mark_pinged(ledger, day, owner, row["task_id"], "todoist-comment")
                    time.sleep(sleep)
                except Exception as exc:  # noqa: BLE001 - external API error must be captured, not crash-looped.
                    result["errors"].append({"task_id": row["task_id"], "owner": owner, "error": exc.__class__.__name__, "detail": str(exc)[:500]})
    for row in plan.get("comment_replies", []):
        note_id = str(row.get("note_id") or "")
        if not note_id or already_replied_to_comment(ledger, note_id):
            result["comment_replies_skipped"] += 1
            continue
        if no_comment_replies:
            result["comment_replies_skipped"] += 1
            continue
        extra: dict[str, Any] = {}
        if dry_run:
            if row.get("intent") == "ai_request" and not no_ai_dispatch:
                if result["factory_requests_started"] < max_ai_requests_per_run:
                    result["factory_requests_started"] += 1
                    extra["factory_source"] = f"todoist-comment:{row.get('task_id')}:{note_id}"
                    extra["factory_ok"] = True
                else:
                    result["factory_requests_failed"] += 1
                    extra["factory_error"] = "max_ai_requests_per_run reached"
            result["comment_replies_added"] += 1
            mark_replied_to_comment(ledger, note_id, row["task_id"], row["intent"], extra)
            continue
        try:
            reply = comment_reply_text(row)
            if row.get("intent") == "ai_request" and not no_ai_dispatch:
                if result["factory_requests_started"] >= max_ai_requests_per_run:
                    factory_result = {
                        "ok": False,
                        "source": f"todoist-comment:{row.get('task_id')}:{note_id}",
                        "detail": "max_ai_requests_per_run reached",
                    }
                    result["factory_requests_failed"] += 1
                else:
                    factory_result = dispatch_ai_factory_request(
                        wiki,
                        row,
                        dry_run=False,
                        timeout=ai_request_timeout,
                    )
                    result["factory_requests_started"] += 1
                    if not factory_result.get("ok"):
                        result["factory_requests_failed"] += 1
                extra = {
                    "factory_source": factory_result.get("source"),
                    "factory_ok": factory_result.get("ok"),
                }
                reply = ai_request_reply_text(row, factory_result)
            add_todoist_comment(client, row["task_id"], reply)
            result["comment_replies_added"] += 1
            mark_replied_to_comment(ledger, note_id, row["task_id"], row["intent"], extra)
            time.sleep(sleep)
        except Exception as exc:  # noqa: BLE001 - external API error must be captured, not crash-looped.
            result["errors"].append({"task_id": row.get("task_id"), "note_id": note_id, "owner": row.get("owner"), "error": exc.__class__.__name__, "detail": str(exc)[:500]})
    if not no_telegram and not comment_sweep_only:
        env = runtime_env or os.environ.copy()
        missing_direct_chats: list[tuple[str, list[dict[str, Any]]]] = []
        fallback_chat_id = fallback_owner_chat_id(env)
        for owner, rows in plan["reminders"].items():
            if not rows:
                continue
            chat_id = env_chat_id(owner, env)
            if owner != "Мади" and not chat_id:
                missing_direct_chats.append((owner, rows))
                result["missing_direct_owner_chats"] += 1
                continue
            sent = send_telegram(wiki, digest_for_owner(owner, rows), chat_id, dry_run)
            if sent["ok"]:
                result["telegram_sent"] += 1
            else:
                result["errors"].append({"owner": owner, "error": "telegram_failed", "detail": sent})
        if missing_direct_chats:
            group_fallback = bool(fallback_chat_id)
            sent = send_telegram(
                wiki,
                digest_for_missing_direct_chats(missing_direct_chats, group_fallback=group_fallback),
                fallback_chat_id,
                dry_run,
            )
            if sent["ok"]:
                result["telegram_sent"] += 1
                if group_fallback:
                    result["telegram_group_fallback_sent"] += 1
                else:
                    result["telegram_skipped"] += len(missing_direct_chats)
            else:
                result["errors"].append({"owner": "Мади", "error": "telegram_fallback_failed", "detail": sent})
    if not dry_run:
        (wiki / ledger_path).parent.mkdir(parents=True, exist_ok=True)
        (wiki / ledger_path).write_text(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--status-page", type=Path, default=DEFAULT_STATUS_PAGE)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--owners", default=",".join(DEFAULT_OWNERS))
    parser.add_argument("--stale-days", type=int, default=3)
    parser.add_argument("--max-per-owner", type=int, default=5)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-todoist-comments", action="store_true", help="Legacy guard; default already avoids generic daily Todoist reminder comments.")
    parser.add_argument("--todoist-reminder-comments", action="store_true", help="Opt in to old per-task generic reminder comments. Default is digest-only to prevent spam.")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--no-comment-replies", action="store_true")
    parser.add_argument("--no-ai-dispatch", action="store_true")
    parser.add_argument("--comment-sweep-only", action="store_true")
    parser.add_argument("--max-ai-requests-per-run", type=int, default=3)
    parser.add_argument("--ai-request-timeout", type=int, default=300)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    owners = {OWNER_ALIASES.get(owner.strip().casefold(), owner.strip()) for owner in args.owners.split(",") if owner.strip()}
    runtime_env = os.environ.copy()
    runtime_env.update(load_env_file(args.env_file))
    client = Todoist(token_from_env(args.env_file))
    plan = build_plan(client.sync(), owners=owners, stale_days=args.stale_days, max_per_owner=args.max_per_owner)
    apply_result = apply_reminders(
        client,
        plan,
        wiki=args.wiki,
        ledger_path=args.ledger,
        dry_run=not args.apply,
        no_todoist_comments=args.no_todoist_comments,
        todoist_reminder_comments=args.todoist_reminder_comments,
        no_telegram=args.no_telegram,
        no_comment_replies=args.no_comment_replies,
        no_ai_dispatch=args.no_ai_dispatch,
        comment_sweep_only=args.comment_sweep_only,
        max_ai_requests_per_run=args.max_ai_requests_per_run,
        ai_request_timeout=args.ai_request_timeout,
        sleep=args.sleep,
        runtime_env=runtime_env,
    )
    writeback_result = {"ok": True, "detail": "dry-run"}
    if args.apply:
        status_rel = args.status_page
        audit_rel = args.audit_dir / f"HUMAN-OWNER-REMINDER-{now_kzt().strftime('%Y-%m-%d')}.md"
        (args.wiki / status_rel).parent.mkdir(parents=True, exist_ok=True)
        (args.wiki / audit_rel).parent.mkdir(parents=True, exist_ok=True)
        (args.wiki / status_rel).write_text(render_status(plan, apply_result), encoding="utf-8")
        (args.wiki / audit_rel).write_text(render_audit(plan, apply_result), encoding="utf-8")
        writeback_result = writeback(args.wiki, [args.status_page, args.ledger, audit_rel], dry_run=False)
    payload = {"plan": plan, "apply": apply_result, "writeback": writeback_result}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    else:
        summary = (
            f"human_owner_reminders={plan['reminder_count']} "
            f"comments={apply_result['todoist_comments_added']} "
            f"telegram={apply_result['telegram_sent']} "
            f"writeback_ok={bool(writeback_result.get('ok'))}"
        )
        if not writeback_result.get("ok"):
            summary += f" writeback_error={tail(json.dumps(writeback_result.get('detail'), ensure_ascii=False, default=str), 1000)}"
        print(summary)
    return 0 if not apply_result["errors"] and writeback_result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
