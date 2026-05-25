from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import satory_ai_factory_queue as queue


def _task(task_id: str, title: str, **overrides):
    row = {
        "task_id": task_id,
        "content": title,
        "description": "",
        "status": "not_done",
        "owner": "AI-фабрика",
        "factory_route": "ready_for_ai_factory",
        "execution_state": "queued",
        "queue_reason": "AI-owned ready task",
        "delete_candidate_reason": "",
        "latest_human_signal": {},
        "next_action_compact": "AI-фабрика берет один маленький slice.",
        "close_gate": "do_not_close_missing_notion_or_drive_proof",
        "todoist_url": f"https://todoist.com/showTask?id={task_id}",
        "comments": [],
    }
    row.update(overrides)
    return row


def test_build_queue_prioritizes_bdl_apk_erap_and_skips_ledger() -> None:
    report = {
        "tasks": [
            _task("normal", "Обновить страницу статуса"),
            _task("apk", "[ERAP] Проверить APK события ЛУ100"),
        ]
    }
    first_event = queue.event_fingerprint(report["tasks"][1])
    ledger = {"runs": {first_event: {"ok": True}}}

    selected = queue.build_queue(report, ledger, limit=3, priority="bdl-apk-erap")

    assert [event["task"]["task_id"] for event in selected] == ["normal"]


def test_build_queue_skips_delete_review_rows() -> None:
    report = {
        "tasks": [
            _task("delete", "Приветствие — настройка", delete_candidate_reason="meta", execution_state="delete_review"),
            _task("real", "[ERAP] Проверить APK"),
        ]
    }

    selected = queue.build_queue(report, {"runs": {}}, limit=3, priority="bdl-apk-erap")

    assert [event["task"]["task_id"] for event in selected] == ["real"]


def test_build_queue_skips_prior_ai_owned_task_without_new_human_signal() -> None:
    row = _task("already", "[ERAP] Проверить APK")
    report = {"tasks": [row]}
    ledger = {"runs": {"older-event": {"task_id": "already", "ok": True}}}

    selected = queue.build_queue(report, ledger, limit=3, priority="bdl-apk-erap")

    assert selected == []


def test_queue_diagnostics_explains_ledger_idle() -> None:
    row = _task("already", "[ERAP] Проверить APK")
    report = {"tasks": [row]}
    ledger = {"runs": {"older-event": {"task_id": "already", "ok": True}}}

    diagnostics = queue.queue_diagnostics(report, ledger, priority="bdl-apk-erap")

    assert diagnostics["queued_candidates"] == 1
    assert diagnostics["ledger_blocked_candidates"] == 1
    assert diagnostics["unblocked_candidates"] == 0
    assert diagnostics["ledger_blocked_samples"][0]["task_id"] == "already"


def test_build_queue_retries_failed_event_once() -> None:
    row = _task("retry", "[ERAP] Проверить APK")
    report = {"tasks": [row]}
    event_id = queue.event_fingerprint(row)
    ledger = {"runs": {event_id: {"task_id": "retry", "ok": False, "status": "openclaw_failed", "attempts": 1}}}

    selected = queue.build_queue(report, ledger, limit=3, priority="bdl-apk-erap")

    assert [event["task"]["task_id"] for event in selected] == ["retry"]


def test_build_queue_skips_failed_event_after_attempt_cap() -> None:
    row = _task("retry", "[ERAP] Проверить APK")
    report = {"tasks": [row]}
    event_id = queue.event_fingerprint(row)
    ledger = {"runs": {event_id: {"task_id": "retry", "ok": False, "status": "openclaw_failed", "attempts": 2}}}

    selected = queue.build_queue(report, ledger, limit=3, priority="bdl-apk-erap")

    assert selected == []


def test_build_queue_allows_same_task_when_new_human_signal_exists() -> None:
    row = _task(
        "already",
        "[ERAP] Проверить APK",
        latest_human_signal={"note_id": "new-note", "intent": "ai_request"},
        queue_reason="human_ai_request",
    )
    report = {"tasks": [row]}
    ledger = {"runs": {"older-event": {"task_id": "already", "ok": True}}}

    selected = queue.build_queue(report, ledger, limit=3, priority="bdl-apk-erap")

    assert [event["task"]["task_id"] for event in selected] == ["already"]


def test_external_operator_proof_fails_closed_without_codex(tmp_path: Path) -> None:
    row = _task(
        "apk",
        "from Asyl: APK камера фиксирует события ЕРАП?",
        description="Нужно проверить доступ/лог/событие по камере.",
    )
    event = {"event_id": queue.event_fingerprint(row), "task": row}

    result = queue.dispatch_event(tmp_path, event, dry_run=False, allow_codex=False, timeout=5)

    assert result["ok"] is False
    assert result["status"] == "blocked_codex_required"
    assert result["model"].startswith("codex:")


def test_proof_heavy_satory_task_forces_codex_route_without_allow_codex(tmp_path: Path) -> None:
    row = _task(
        "dashboard",
        "Дашборд — работает",
        comments=[
            {
                "content": "Источник: source-finder. Runtime smoke HTTP 200; полная Playwright проверка queued.",
            }
        ],
    )
    event = {"event_id": queue.event_fingerprint(row), "task": row}

    result = queue.dispatch_event(tmp_path, event, dry_run=False, allow_codex=False, timeout=5)

    assert result["ok"] is False
    assert result["status"] == "blocked_codex_required"
    assert result["route"] == "chatgpt_execution"


def test_routine_satory_task_stays_on_openclaw_routine() -> None:
    row = _task("draft", "Подготовить короткий текст письма", description="Собрать черновик ответа из уже известных вводных.")

    decision = queue.decision_for_row(row)

    assert decision["route"] == "openclaw_routine"


def test_proof_heavy_satory_task_uses_codex_when_allowed(tmp_path: Path, monkeypatch) -> None:
    row = _task(
        "map",
        "Карта — работает",
        comments=[{"content": "Нужна proof проверка API /api/proxy/cameras и browser smoke."}],
    )
    event = {"event_id": queue.event_fingerprint(row), "task": row}
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, timeout=0):
        calls.append(cmd)
        return {
            "ok": True,
            "stdout": "Статус: в работе\nProof: pages/audits/map-proof.md\nСледующий шаг: зафиксировать.",
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(queue, "run", fake_run)

    result = queue.dispatch_event(tmp_path, event, dry_run=False, allow_codex=True, timeout=5)

    assert result["ok"] is True
    assert result["status"] == "codex_ran"
    assert result["route"] == "chatgpt_execution"
    assert calls[0][:6] == ["codex", "exec", "-m", "gpt-5.5", "--sandbox", "danger-full-access"]


def test_routine_queue_dry_run_is_safe(tmp_path: Path) -> None:
    row = _task("normal", "Обновить Satory dashboard proof")
    event = {"event_id": queue.event_fingerprint(row), "task": row}

    result = queue.dispatch_event(tmp_path, event, dry_run=True, allow_codex=False, timeout=5)

    assert result["ok"] is True
    assert result["status"] == "dry_run"


def test_factory_prompt_injects_referenced_air_vault_file(tmp_path: Path) -> None:
    source = tmp_path / "pages" / "plans" / "PLAN-COCKPIT-Q3-ENHANCEMENTS-2026-05-07.md"
    source.parent.mkdir(parents=True)
    source.write_text("Q3 cockpit evidence: seven operator checkpoints.", encoding="utf-8")
    row = _task(
        "ctx",
        "Проверить Q3 cockpit",
        description="Use pages/plans/PLAN-COCKPIT-Q3-ENHANCEMENTS-2026-05-07.md before answering.",
    )

    prompt = queue.factory_prompt(row, "event-ctx", tmp_path)

    assert "## Injected Air vault context" in prompt
    assert "pages/plans/PLAN-COCKPIT-Q3-ENHANCEMENTS-2026-05-07.md" in prompt
    assert "seven operator checkpoints" in prompt


def test_factory_prompt_records_missing_referenced_vault_file(tmp_path: Path) -> None:
    row = _task(
        "missing",
        "Проверить Hermes",
        description="Read pages/specs/missing-hermes-spec.md first.",
    )

    prompt = queue.factory_prompt(row, "event-missing", tmp_path)

    assert "Missing referenced vault files:" in prompt
    assert "pages/specs/missing-hermes-spec.md" in prompt


def test_openclaw_success_returncode_with_blocked_worker_text_is_blocked(tmp_path: Path, monkeypatch) -> None:
    row = _task("normal", "Обновить внутреннюю сводку")
    event = {"event_id": queue.event_fingerprint(row), "task": row}
    runner = tmp_path / "run_task.py"
    runner.write_text("# stub\n", encoding="utf-8")

    class Decision:
        def to_dict(self):
            return {"route": "openclaw_routine", "worker_model": "deepseek-v4-flash"}

    monkeypatch.setattr(queue, "RUN_TASK", runner)
    monkeypatch.setattr(queue, "classify_text", lambda _text: Decision())
    monkeypatch.setattr(
        queue,
        "run",
        lambda *_args, **_kwargs: {
            "ok": True,
            "stdout": "Статус: заблокировано\nProof: нет\nБлокер: workspace без доступа к wiki.",
            "stderr": "",
            "returncode": 0,
        },
    )

    result = queue.dispatch_event(tmp_path, event, dry_run=False, allow_codex=False, timeout=5)

    assert result["ok"] is False
    assert result["status"] == "openclaw_blocked"
    assert result["worker_failure_reason"] == "blocked_status"


def test_openclaw_markdown_bold_blocked_status_is_blocked(tmp_path: Path, monkeypatch) -> None:
    row = _task("normal", "Обновить внутреннюю сводку")
    event = {"event_id": queue.event_fingerprint(row), "task": row}
    runner = tmp_path / "run_task.py"
    runner.write_text("# stub\n", encoding="utf-8")

    class Decision:
        def to_dict(self):
            return {"route": "openclaw_routine", "worker_model": "deepseek-v4-flash"}

    monkeypatch.setattr(queue, "RUN_TASK", runner)
    monkeypatch.setattr(queue, "classify_text", lambda _text: Decision())
    monkeypatch.setattr(
        queue,
        "run",
        lambda *_args, **_kwargs: {
            "ok": True,
            "stdout": "**Статус:** заблокировано\n**Proof:** нет",
            "stderr": "",
            "returncode": 0,
        },
    )

    result = queue.dispatch_event(tmp_path, event, dry_run=False, allow_codex=False, timeout=5)

    assert result["ok"] is False
    assert result["status"] == "openclaw_blocked"
    assert result["worker_failure_reason"] == "blocked_status"


def test_openclaw_no_response_text_is_blocked(tmp_path: Path, monkeypatch) -> None:
    row = _task("normal", "Обновить внутреннюю сводку")
    event = {"event_id": queue.event_fingerprint(row), "task": row}
    runner = tmp_path / "run_task.py"
    runner.write_text("# stub\n", encoding="utf-8")

    class Decision:
        def to_dict(self):
            return {"route": "openclaw_routine", "worker_model": "deepseek-v4-flash"}

    monkeypatch.setattr(queue, "RUN_TASK", runner)
    monkeypatch.setattr(queue, "classify_text", lambda _text: Decision())
    monkeypatch.setattr(
        queue,
        "run",
        lambda *_args, **_kwargs: {
            "ok": True,
            "stdout": "⚠️ Agent couldn't generate a response. Please try again.",
            "stderr": "",
            "returncode": 0,
        },
    )

    result = queue.dispatch_event(tmp_path, event, dry_run=False, allow_codex=False, timeout=5)

    assert result["ok"] is False
    assert result["status"] == "openclaw_blocked"
    assert result["worker_failure_reason"] == "no_response"


def test_worker_side_effect_text_is_blocked() -> None:
    assert (
        queue.worker_failure_reason("Статус: в работе\nTodoist proof comment posted: `abc123`")
        == "worker_side_effect"
    )


def test_worker_created_slice_proof_paths_are_queue_writeback_owned() -> None:
    status = "\n".join(
        [
            " M pages/systems/satory-ai-factory-queue-ledger.json",
            "?? pages/audits/SATORY-SETTINGS-ROUTE-SLICE-2026-05-19.md",
            "?? pages/audits/OTHER.md",
            "?? pages/inbox/raw-secret.txt",
        ]
    )

    assert queue.worker_created_proof_paths_from_status(status) == [
        Path("pages/audits/SATORY-SETTINGS-ROUTE-SLICE-2026-05-19.md")
    ]


def test_openclaw_worker_routes_prefer_local_mlx_before_deepseek() -> None:
    assert queue.model_for_decision(
        {
            "route": "openclaw_routine",
            "worker_model": "deepseek-v4-flash",
        }
    ) == "local-mlx-coder"
    assert queue.model_for_decision(
        {
            "route": "long_work_goal",
            "worker_model": "deepseek-v4-flash",
        }
    ) == "local-mlx-coder"
    assert queue.model_for_decision(
        {
            "route": "chatgpt_execution",
            "worker_model": "deepseek-v4-flash",
        }
    ) == "deepseek-v4-flash"


def test_parse_args_accepts_explicit_dry_run() -> None:
    args = queue.parse_args(["--dry-run", "--json"])

    assert args.dry_run is True
    assert args.apply is False


def test_parse_args_accepts_git_writeback() -> None:
    args = queue.parse_args(["--apply", "--git-writeback", "--git-push-remotes", "origin"])

    assert args.apply is True
    assert args.git_writeback is True
    assert args.git_push_remotes == "origin"


def test_git_writeback_commits_and_pushes_queue_outputs(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, timeout=0):
        calls.append(cmd)
        if cmd == ["git", "status", "--porcelain", "--", "pages/audits/proof.md", "pages/systems/status.md"]:
            return {"ok": True, "stdout": " M pages/systems/status.md\n?? pages/audits/proof.md\n", "stderr": ""}
        if cmd == ["git", "status", "--porcelain"]:
            return {"ok": True, "stdout": "", "stderr": ""}
        if cmd == ["git", "rev-parse", "FETCH_HEAD"]:
            return {"ok": True, "stdout": "abc1234567890\n", "stderr": ""}
        return {"ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(queue, "run", fake_run)

    result = queue.git_writeback_queue_outputs(
        tmp_path,
        [Path("pages/systems/status.md"), Path("pages/audits/proof.md")],
        push_remotes=["origin", "github"],
        message="satory-queue: test",
    )

    assert result["status"] == "ok"
    assert ["git", "-c", "core.hooksPath=/dev/null", "commit", "--no-verify", "-m", "satory-queue: test", "-o", "pages/audits/proof.md", "pages/systems/status.md"] in calls
    assert ["git", "push", "origin", "main"] in calls
    assert ["git", "push", "github", "main"] in calls


def test_todoist_result_comment_mentions_no_close_without_proof() -> None:
    row = _task("normal", "Обновить Satory dashboard proof")
    text = queue.todoist_result_comment(
        row,
        {
            "ok": True,
            "route": "openclaw_routine",
            "model": "deepseek-v4-flash",
            "event_id": "event-1",
            "detail": "Статус: в работе",
        },
        "pages/audits/proof.md",
    )

    assert "one-beam очередь" in text
    assert "Notion+Drive proof" in text
    assert "pages/audits/proof.md" in text
