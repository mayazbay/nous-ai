from __future__ import annotations

from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from factory_orchestration_policy import (
    ROUTE_CHATGPT_EXECUTION,
    ROUTE_GROK_DECISION,
    ROUTE_LONG_WORK_GOAL,
    ROUTE_OPENCLAW_ROUTINE,
    classify_text,
    model_pipeline_for_text,
)


def test_decision_prompt_routes_to_grok_first_pass() -> None:
    decision = classify_text("Which approach should we use for Hermes or OpenClaw routing?")

    assert decision.route == ROUTE_GROK_DECISION
    assert decision.first_pass_model == "grok-reasoning"


def test_runtime_word_does_not_trigger_run_execution_marker() -> None:
    decision = classify_text("Should we use Hermes or OpenClaw as the production runtime?")

    assert decision.route == ROUTE_GROK_DECISION


def test_bounded_execution_routes_to_chatgpt_codex() -> None:
    decision = classify_text("Fix the Todoist source comments and verify the audit.")

    assert decision.route == ROUTE_CHATGPT_EXECUTION
    assert decision.execution_route == "codex:gpt-5.5-subscription"


def test_satory_apk_external_operator_query_routes_to_chatgpt_codex() -> None:
    decision = classify_text("from asyl: Мади кстати как у тебя ПО работает с Апк? фиксирует что-то?")

    assert decision.route == ROUTE_CHATGPT_EXECUTION
    assert "Satory APK/ERAP" in decision.reason


def test_satory_var_camera_access_query_routes_to_chatgpt_codex() -> None:
    decision = classify_text(
        "Telegram group sender @aliakbar_asylbek: Message: "
        "стоп, на ЛУ 100 рядом повесили Вар с радаром. "
        "ты видишь эту камеру? есть ли доступ у тебя к этой камере"
    )

    assert decision.route == ROUTE_CHATGPT_EXECUTION
    assert "Satory camera/APK live proof" in decision.reason


def test_external_operator_endpoint_proof_routes_to_chatgpt_codex() -> None:
    decision = classify_text(
        "Telegram group sender @denis: Message: события пошли, какой endpoint и consumer, "
        "видите ли логи по событиям?"
    )

    assert decision.route == ROUTE_CHATGPT_EXECUTION
    assert decision.todoist_action == "codex_external_proof"
    assert "external operator proof" in decision.reason


def test_top_tier_second_brain_routes_to_chatgpt_codex_supervisor() -> None:
    decision = classify_text("I need the top tier GPT second brain to make this bulletproof.")

    assert decision.route == ROUTE_CHATGPT_EXECUTION
    assert decision.todoist_action == "codex_supervise_then_delegate"


def test_top_tier_cto_ceo_question_routes_to_chatgpt_codex_supervisor() -> None:
    decision = classify_text("What would a top-tier CTO/CEO do with this agent factory?")

    assert decision.route == ROUTE_CHATGPT_EXECUTION
    assert decision.todoist_action == "codex_supervise_then_delegate"


def test_long_work_routes_to_goal_and_chinese_worker_pipeline() -> None:
    text = "Implement everything step by step, audit the whole factory, create tasks, and do not come back until it is 100% done. " * 8
    decision = classify_text(text)
    pipeline = model_pipeline_for_text(text)

    assert decision.route == ROUTE_LONG_WORK_GOAL
    assert pipeline[:3] == ["grok-reasoning", "deepseek-v4-flash", "deepseek-v4-pro"]
    assert "kimi-k2.6" in pipeline
    assert "codex:gpt-5.5-subscription" in pipeline


def test_routine_chat_stays_openclaw() -> None:
    decision = classify_text("show status")

    assert decision.route == ROUTE_OPENCLAW_ROUTINE
