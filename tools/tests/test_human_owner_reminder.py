from __future__ import annotations

import datetime as dt
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import human_owner_reminder as reminder


KZT = dt.timezone(dt.timedelta(hours=5))
SATORY_ID = "6gJ5j8PRVVCWpgCq"


def _item(task_id: str, owner: str, **overrides):
    base = {
        "id": task_id,
        "content": f"Задача {task_id}",
        "project_id": SATORY_ID,
        "checked": False,
        "completed_at": None,
        "is_deleted": False,
        "labels": [f"исполнитель:{owner}", "отдел:Продажи", "проект:Фабрика-Satory-ВКО"],
        "priority": 2,
        "updated_at": "2026-05-10T00:00:00Z",
        "due": None,
        "note_count": 1,
    }
    base.update(overrides)
    return base


def test_build_plan_selects_human_overdue_and_excludes_ai_factory() -> None:
    sync = {
        "items": [
            _item("a", "Daniyar", due={"date": "2026-05-12"}, priority=4),
            _item("b", "AI-фабрика", due={"date": "2026-05-12"}, priority=4),
            _item("c", "Асылбек", updated_at="2026-05-13T09:00:00Z"),
        ]
    }

    plan = reminder.build_plan(
        sync,
        owners={"Данияр", "Асылбек"},
        stale_days=3,
        max_per_owner=5,
        now=dt.datetime(2026, 5, 13, 10, 0, tzinfo=KZT),
    )

    assert plan["considered_human_tasks"] == 2
    assert plan["reminder_count"] == 1
    assert plan["reminders"]["Данияр"][0]["task_id"] == "a"
    assert "срок просрочен" in plan["reminders"]["Данияр"][0]["reasons"][0]
    assert "AI-фабрика" not in plan["reminders"]


def test_build_plan_excludes_non_satory_projects() -> None:
    sync = {
        "items": [
            _item("a", "Daniyar", due={"date": "2026-05-12"}, priority=4, project_id="personal"),
            _item("b", "Daniyar", due={"date": "2026-05-12"}, priority=4),
        ]
    }

    plan = reminder.build_plan(
        sync,
        owners={"Данияр"},
        stale_days=3,
        max_per_owner=5,
        now=dt.datetime(2026, 5, 13, 10, 0, tzinfo=KZT),
    )

    assert plan["considered_human_tasks"] == 1
    assert plan["reminders"]["Данияр"][0]["task_id"] == "b"


def test_build_plan_detects_actionable_task_comments() -> None:
    sync = {
        "items": [_item("a", "Daniyar", content="Проверить ЕРАП", updated_at="2026-05-13T09:00:00Z")],
        "notes": [
            {"id": "n1", "item_id": "a", "content": "Готово, можно закрывать", "posted_at": "2026-05-13T04:30:00Z"},
            {"id": "n2", "item_id": "a", "content": "Ежедневное напоминание AI-фабрики (2026-05-13).", "posted_at": "2026-05-13T04:00:00Z"},
        ],
    }

    plan = reminder.build_plan(
        sync,
        owners={"Данияр"},
        stale_days=3,
        max_per_owner=5,
        now=dt.datetime(2026, 5, 13, 10, 0, tzinfo=KZT),
    )

    assert plan["comment_reply_count"] == 1
    assert plan["comment_replies"][0]["note_id"] == "n1"
    assert plan["comment_replies"][0]["intent"] == "done"


def test_build_plan_adds_evidence_from_task_comments() -> None:
    sync = {
        "items": [
            _item(
                "a",
                "Daniyar",
                due={"date": "2026-05-12"},
                priority=4,
                description="Notion: https://www.notion.so/example",
            )
        ],
        "notes": [
            {
                "id": "n1",
                "item_id": "a",
                "content": "Drive: https://drive.google.com/file/d/example/view\nИсточник: source-finder",
                "posted_at": "2026-05-13T04:30:00Z",
            },
        ],
    }

    plan = reminder.build_plan(
        sync,
        owners={"Данияр"},
        stale_days=3,
        max_per_owner=5,
        now=dt.datetime(2026, 5, 13, 10, 0, tzinfo=KZT),
    )

    evidence = plan["reminders"]["Данияр"][0]["evidence"]
    assert evidence["source_backed"] is True
    assert evidence["human_checkable"] is True
    assert evidence["close_ready"] is True
    assert evidence["proof_channels"] == ["google_drive", "notion"]


def test_context_comments_do_not_trigger_replies() -> None:
    sync = {
        "items": [_item("a", "Асыл", content="[Mergen/ERAP] Подтвердить выход APK -> VPS :9080")],
        "notes": [
            {
                "id": "n1",
                "item_id": "a",
                "content": "Notion: https://www.notion.so/example\nСтатус/решение: production send заблокирована до тестов.",
                "posted_at": "2026-05-13T04:30:00Z",
            },
            {
                "id": "n2",
                "item_id": "a",
                "content": "Если блокировано, написать блокер и следующего ответственного.",
                "posted_at": "2026-05-13T04:31:00Z",
            },
            {
                "id": "n3",
                "item_id": "a",
                "content": "pages/projects/GOAL-20260512-example.md says blocked until legal path.",
                "posted_at": "2026-05-13T04:32:00Z",
            },
        ],
    }

    plan = reminder.build_plan(
        sync,
        owners={"Асыл"},
        stale_days=3,
        max_per_owner=5,
        now=dt.datetime(2026, 5, 13, 10, 0, tzinfo=KZT),
    )

    assert plan["comment_reply_count"] == 0


def test_human_blocker_and_ai_request_comments_still_trigger_replies() -> None:
    assert reminder.comment_intent("Я заблокирован: нет доступа к тестовой среде ЕРАП") == "blocked"
    assert reminder.comment_intent("AI: проверь почему камера недоступна, источник https://example.com") == "ai_request"


def test_instruction_checklists_with_voprosy_do_not_trigger_question_reply() -> None:
    text = (
        "•Подготовить детальные юридические вопросы по СП на русском и английском языках\n\n"
        "•Четко определить, какая компания будет основной для корейских партнеров\n\n"
        "•Необходимо указать превалирующий язык в договоре"
    )

    assert reminder.comment_intent(text) is None
    assert reminder.comment_intent("У меня вопрос: какой срок по ЕРАП?") == "question"


def test_comment_reply_text_is_idiot_proof_and_russian() -> None:
    text = reminder.comment_reply_text({"intent": "blocked", "content": "Подключить тестовую среду"})

    assert "AI-фабрика увидела блокер" in text
    assert "кто следующий владелец" in text
    assert "`AI:`" in text


def test_ai_factory_prompt_is_satory_only_and_russian() -> None:
    prompt = reminder.ai_factory_prompt(
        {
            "task_id": "t1",
            "owner": "Данияр",
            "url": "https://todoist.com/showTask?id=t1",
            "content": "Проверить ЕРАП",
            "comment": "AI: проверь доступ к тестовой среде",
        }
    )

    assert "Фабрика Satory ВКО" in prompt
    assert "Не трогай личные проекты" in prompt
    assert "Статус: готово | в работе | заблокировано" in prompt


class FakeTodoist:
    def __init__(self) -> None:
        self.comments: list[tuple[str, str]] = []

    def request(self, method: str, path: str, json=None):  # noqa: ANN001 - test double mirrors loose client API.
        assert method == "POST"
        assert path == "/comments"
        self.comments.append((json["task_id"], json["content"]))
        return {"id": f"c{len(self.comments)}"}


def test_ai_request_comment_dispatches_one_factory_slice(monkeypatch, tmp_path: Path) -> None:
    plan = {
        "captured_at": "2026-05-13T10:00:00+05:00",
        "owners": ["Данияр"],
        "considered_human_tasks": 1,
        "reminder_count": 0,
        "reminders": {"Данияр": []},
        "comment_replies": [
            {
                "note_id": "n1",
                "task_id": "t1",
                "owner": "Данияр",
                "intent": "ai_request",
                "content": "Проверить ЕРАП",
                "comment": "AI: проверь доступ к тестовой среде",
                "url": "https://todoist.com/showTask?id=t1",
            }
        ],
        "comment_reply_count": 1,
    }
    dispatched: list[str] = []

    def fake_dispatch(wiki, row, *, dry_run, timeout):  # noqa: ANN001 - test double.
        dispatched.append(row["note_id"])
        return {"ok": True, "source": "todoist-comment:t1:n1", "detail": "Статус: в работе\nЧто сделал: проверил"}

    monkeypatch.setattr(reminder, "dispatch_ai_factory_request", fake_dispatch)
    client = FakeTodoist()

    result = reminder.apply_reminders(
        client,
        plan,
        wiki=tmp_path,
        ledger_path=Path("ledger.json"),
        dry_run=False,
        no_todoist_comments=False,
        todoist_reminder_comments=False,
        no_telegram=True,
        no_comment_replies=False,
        no_ai_dispatch=False,
        comment_sweep_only=True,
        max_ai_requests_per_run=3,
        ai_request_timeout=5,
        sleep=0,
    )

    assert dispatched == ["n1"]
    assert result["factory_requests_started"] == 1
    assert result["factory_requests_failed"] == 0
    assert result["comment_replies_added"] == 1
    assert "OpenClaw/run_task" in client.comments[0][1]
    assert "Статус: в работе" in client.comments[0][1]


def test_ai_factory_dispatch_passes_policy_worker_model(monkeypatch, tmp_path: Path) -> None:
    run_task = tmp_path / "run_task.py"
    run_task.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(cmd, *, cwd=None, timeout=60, env=None):  # noqa: ANN001 - mirrors helper signature.
        captured["cmd"] = cmd
        return {"ok": True, "stdout": "Статус: в работе", "stderr": "", "returncode": 0}

    monkeypatch.setattr(reminder, "RUN_TASK", run_task)
    monkeypatch.setattr(reminder, "run", fake_run)

    result = reminder.dispatch_ai_factory_request(
        tmp_path,
        {
            "task_id": "t1",
            "note_id": "n1",
            "content": "Проверить ЕРАП",
            "comment": "AI: implement the Satory audit fix and verify it.",
            "owner": "Данияр",
            "url": "https://todoist.com/showTask?id=t1",
        },
        dry_run=False,
        timeout=5,
    )

    assert result["ok"] is True
    assert result["route"] == "chatgpt_execution"
    assert result["model"] == "deepseek-v4-flash"
    cmd = captured["cmd"]
    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == "deepseek-v4-flash"


def test_comment_sweep_only_does_not_send_daily_reminder(monkeypatch, tmp_path: Path) -> None:
    plan = {
        "captured_at": "2026-05-13T10:00:00+05:00",
        "owners": ["Данияр"],
        "considered_human_tasks": 1,
        "reminder_count": 1,
        "reminders": {
            "Данияр": [
                {
                    "task_id": "t1",
                    "owner": "Данияр",
                    "priority": 4,
                    "status": "blocked",
                    "content": "Просроченная задача",
                    "reasons": ["срок просрочен"],
                    "url": "https://todoist.com/showTask?id=t1",
                }
            ]
        },
        "comment_replies": [],
        "comment_reply_count": 0,
    }
    monkeypatch.setattr(reminder, "send_telegram", lambda *args, **kwargs: {"ok": False})
    client = FakeTodoist()

    result = reminder.apply_reminders(
        client,
        plan,
        wiki=tmp_path,
        ledger_path=Path("ledger.json"),
        dry_run=False,
        no_todoist_comments=False,
        todoist_reminder_comments=False,
        no_telegram=False,
        no_comment_replies=False,
        no_ai_dispatch=False,
        comment_sweep_only=True,
        max_ai_requests_per_run=3,
        ai_request_timeout=5,
        sleep=0,
    )

    assert client.comments == []
    assert result["todoist_comments_added"] == 0
    assert result["telegram_sent"] == 0
    assert result["telegram_skipped"] == 0


def test_daily_reminders_are_digest_only_by_default(tmp_path: Path) -> None:
    plan = {
        "captured_at": "2026-05-13T10:00:00+05:00",
        "owners": ["Данияр"],
        "considered_human_tasks": 1,
        "reminder_count": 1,
        "reminders": {
            "Данияр": [
                {
                    "task_id": "t1",
                    "owner": "Данияр",
                    "priority": 4,
                    "status": "blocked",
                    "content": "Просроченная задача",
                    "reasons": ["срок просрочен"],
                    "url": "https://todoist.com/showTask?id=t1",
                }
            ]
        },
        "comment_replies": [],
        "comment_reply_count": 0,
    }
    client = FakeTodoist()

    result = reminder.apply_reminders(
        client,
        plan,
        wiki=tmp_path,
        ledger_path=Path("ledger.json"),
        dry_run=False,
        no_todoist_comments=False,
        todoist_reminder_comments=False,
        no_telegram=True,
        no_comment_replies=False,
        no_ai_dispatch=False,
        comment_sweep_only=False,
        max_ai_requests_per_run=3,
        ai_request_timeout=5,
        sleep=0,
    )

    assert client.comments == []
    assert result["todoist_comments_added"] == 0
    assert result["todoist_comments_skipped"] == 1
    assert result["todoist_reminder_comments_enabled"] is False
    assert result["mode"] == "daily_digest_plus_comment_sweep"


def test_same_day_ledger_blocks_duplicate_telegram_digest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(reminder, "now_kzt", lambda: dt.datetime(2026, 5, 13, 10, 0, tzinfo=KZT))
    plan = {
        "captured_at": "2026-05-13T10:00:00+05:00",
        "owners": ["Мади"],
        "considered_human_tasks": 1,
        "reminder_count": 1,
        "reminders": {
            "Мади": [
                {
                    "task_id": "t1",
                    "owner": "Мади",
                    "priority": 4,
                    "status": "blocked",
                    "content": "Просроченная задача",
                    "reasons": ["срок просрочен"],
                    "url": "https://todoist.com/showTask?id=t1",
                }
            ]
        },
        "comment_replies": [],
        "comment_reply_count": 0,
    }
    ledger_path = Path("ledger.json")
    (tmp_path / ledger_path).write_text(
        '{"sent":{"2026-05-13":{"Мади":{"t1":{"at":"x","channel":"digest-only"}}}}}\n',
        encoding="utf-8",
    )
    sent: list[tuple[str | None, str]] = []
    monkeypatch.setattr(reminder, "send_telegram", lambda _wiki, message, chat_id, _dry_run: sent.append((chat_id, message)) or {"ok": True})
    client = FakeTodoist()

    result = reminder.apply_reminders(
        client,
        plan,
        wiki=tmp_path,
        ledger_path=ledger_path,
        dry_run=True,
        no_todoist_comments=True,
        todoist_reminder_comments=False,
        no_telegram=False,
        no_comment_replies=False,
        no_ai_dispatch=False,
        comment_sweep_only=False,
        max_ai_requests_per_run=3,
        ai_request_timeout=5,
        sleep=0,
    )

    assert result["todoist_comments_skipped"] == 1
    assert result["telegram_sent"] == 0
    assert sent == []


def test_fresh_digest_only_row_still_sends_telegram(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(reminder, "now_kzt", lambda: dt.datetime(2026, 5, 13, 10, 0, tzinfo=KZT))
    plan = {
        "captured_at": "2026-05-13T10:00:00+05:00",
        "owners": ["Мади"],
        "considered_human_tasks": 1,
        "reminder_count": 1,
        "reminders": {
            "Мади": [
                {
                    "task_id": "t1",
                    "owner": "Мади",
                    "priority": 4,
                    "status": "blocked",
                    "content": "Просроченная задача",
                    "reasons": ["срок просрочен"],
                    "url": "https://todoist.com/showTask?id=t1",
                }
            ]
        },
        "comment_replies": [],
        "comment_reply_count": 0,
    }
    sent: list[tuple[str | None, str]] = []
    monkeypatch.setattr(reminder, "send_telegram", lambda _wiki, message, chat_id, _dry_run: sent.append((chat_id, message)) or {"ok": True})
    client = FakeTodoist()

    result = reminder.apply_reminders(
        client,
        plan,
        wiki=tmp_path,
        ledger_path=Path("ledger.json"),
        dry_run=True,
        no_todoist_comments=True,
        todoist_reminder_comments=False,
        no_telegram=False,
        no_comment_replies=False,
        no_ai_dispatch=False,
        comment_sweep_only=False,
        max_ai_requests_per_run=3,
        ai_request_timeout=5,
        sleep=0,
    )

    assert result["todoist_comments_skipped"] == 1
    assert result["telegram_sent"] == 1
    assert len(sent) == 1
    assert "Ежедневный контроль Satory: Мади" in sent[0][1]


def test_comment_reply_ledger_blocks_duplicate_note_reply() -> None:
    ledger = {"comment_replies": {"n1": {"task_id": "a", "intent": "done", "at": "x"}}}

    assert reminder.already_replied_to_comment(ledger, "n1") is True
    assert reminder.already_replied_to_comment(ledger, "n2") is False


def test_ledger_blocks_duplicate_same_day_ping() -> None:
    ledger = {"sent": {"2026-05-13": {"Данияр": {"a": {"at": "x", "channel": "todoist-comment"}}}}}

    assert reminder.already_pinged(ledger, "2026-05-13", "Данияр", "a") is True
    assert reminder.already_pinged(ledger, "2026-05-13", "Данияр", "b") is False


def test_comment_text_is_russian_and_actionable() -> None:
    row = {
        "owner": "Данияр",
        "status": "blocked",
        "reasons": ["статус заблокировано"],
    }

    text = reminder.comment_text(row, "2026-05-13")

    assert "Ежедневное напоминание AI-фабрики" in text
    assert "Ответственный: Данияр" in text
    assert "обновите задачу в Todoist" in text


def test_missing_direct_chat_digest_goes_to_madi() -> None:
    rows = [
        {
            "priority": 4,
            "status": "blocked",
            "content": "Тестовая задача",
            "reasons": ["срок сегодня"],
            "url": "https://todoist.com/showTask?id=x",
            "evidence": {
                "source_backed": True,
                "human_checkable": True,
                "close_ready": False,
                "proof_channels": ["notion"],
                "source_channels": ["notion"],
            },
        }
    ]

    text = reminder.digest_for_missing_direct_chats([("Данияр", rows)])

    assert "нет прямого Telegram" in text
    assert "Данияр" in text
    assert "Действие фабрики" in text
    assert "Проверка фабрики: доказательство есть (Notion)" in text
    assert "Todoist: https://todoist.com/showTask?id=x" in text
    assert "Proof: https://todoist.com/showTask?id=x" not in text
    assert "комментарии в Todoist добавлены" not in text


def test_missing_direct_chat_digest_can_use_group_fallback() -> None:
    rows = [{"priority": 4, "status": "blocked", "content": "Тестовая задача", "reasons": ["срок сегодня"], "url": "https://todoist.com/showTask?id=x"}]

    text = reminder.digest_for_missing_direct_chats([("Данияр", rows)], group_fallback=True)

    assert "общий дайджест" in text
    assert "Личные DM включатся" in text


def test_fallback_owner_chat_id_prefers_group_env() -> None:
    env = {"TELEGRAM_GROUP_CHAT_ID": "-1002064137259"}

    assert reminder.fallback_owner_chat_id(env) == "-1002064137259"


def test_fallback_owner_chat_id_accepts_comma_list() -> None:
    env = {"TELEGRAM_FULL_CHAT_CHAT_IDS": "-1002064137259, -100111"}

    assert reminder.fallback_owner_chat_id(env) == "-1002064137259"


def test_load_env_file_supports_launchd_stripped_environment(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_GROUP_CHAT_ID=-1002064137259\n# comment\nEMPTY=\n", encoding="utf-8")

    values = reminder.load_env_file(env_file)

    assert values["TELEGRAM_GROUP_CHAT_ID"] == "-1002064137259"
    assert values["EMPTY"] == ""


def test_missing_owner_direct_dm_uses_group_fallback(monkeypatch, tmp_path: Path) -> None:
    plan = {
        "captured_at": "2026-05-13T10:00:00+05:00",
        "owners": ["Данияр", "Мади"],
        "considered_human_tasks": 2,
        "reminder_count": 2,
        "reminders": {
            "Данияр": [
                {
                    "task_id": "t1",
                    "owner": "Данияр",
                    "priority": 4,
                    "status": "blocked",
                    "content": "Просроченная задача",
                    "reasons": ["срок просрочен"],
                    "url": "https://todoist.com/showTask?id=t1",
                }
            ],
            "Мади": [
                {
                    "task_id": "t2",
                    "owner": "Мади",
                    "priority": 4,
                    "status": "blocked",
                    "content": "Задача Мади",
                    "reasons": ["срок просрочен"],
                    "url": "https://todoist.com/showTask?id=t2",
                }
            ],
        },
        "comment_replies": [],
        "comment_reply_count": 0,
    }
    sent: list[tuple[str | None, str]] = []
    monkeypatch.setattr(reminder, "send_telegram", lambda _wiki, message, chat_id, _dry_run: sent.append((chat_id, message)) or {"ok": True})
    client = FakeTodoist()

    result = reminder.apply_reminders(
        client,
        plan,
        wiki=tmp_path,
        ledger_path=Path("ledger.json"),
        dry_run=True,
        no_todoist_comments=True,
        todoist_reminder_comments=False,
        no_telegram=False,
        no_comment_replies=False,
        no_ai_dispatch=False,
        comment_sweep_only=False,
        max_ai_requests_per_run=3,
        ai_request_timeout=5,
        sleep=0,
        runtime_env={"TELEGRAM_CHAT_ID": "110793056", "TELEGRAM_GROUP_CHAT_ID": "-1002064137259"},
    )

    assert result["missing_direct_owner_chats"] == 1
    assert result["telegram_group_fallback_sent"] == 1
    assert result["telegram_skipped"] == 0
    assert sent[-1][0] == "-1002064137259"
    assert "общий дайджест" in sent[-1][1]


def test_writeback_retries_push_race(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    push_attempt = {"origin": 0, "github": 0}

    def fake_run(cmd, **kwargs):  # noqa: ANN001 - mirrors loose subprocess wrapper.
        calls.append(cmd)
        if cmd[:3] == ["git", "-c", "core.hooksPath=/dev/null"] and cmd[3] == "add":
            return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}
        if cmd[:3] == ["git", "diff", "--cached"]:
            return {"ok": False, "returncode": 1, "stdout": "", "stderr": ""}
        if cmd[:3] == ["git", "-c", "core.hooksPath=/dev/null"] and cmd[3] == "commit":
            return {"ok": True, "returncode": 0, "stdout": "committed", "stderr": ""}
        if cmd[:3] == ["git", "pull", "--rebase"]:
            return {"ok": True, "returncode": 0, "stdout": "up to date", "stderr": ""}
        if cmd[:3] == ["git", "remote", "get-url"]:
            return {"ok": True, "returncode": 0, "stdout": "git@github.com:x/y.git", "stderr": ""}
        if cmd[:3] == ["git", "fetch", "github"]:
            return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}
        if cmd[:4] == ["git", "-c", "core.hooksPath=/dev/null", "rebase"]:
            return {"ok": True, "returncode": 0, "stdout": "current", "stderr": ""}
        if cmd[:3] == ["git", "push", "origin"]:
            push_attempt["origin"] += 1
            ok = push_attempt["origin"] > 1
            return {"ok": ok, "returncode": 0 if ok else 1, "stdout": "ok" if ok else "", "stderr": "" if ok else "non-fast-forward"}
        if cmd[:3] == ["git", "push", "github"]:
            push_attempt["github"] += 1
            return {"ok": True, "returncode": 0, "stdout": "ok", "stderr": ""}
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(reminder, "run", fake_run)
    monkeypatch.setattr(reminder.time, "sleep", lambda *_args: None)

    result = reminder.writeback(tmp_path, [Path("pages/systems/status.md")], dry_run=False)

    assert result["ok"] is True
    assert push_attempt["origin"] == 2
    assert push_attempt["github"] == 2
    assert any(call[:3] == ["git", "pull", "--rebase"] for call in calls)
