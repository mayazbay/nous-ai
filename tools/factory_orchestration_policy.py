#!/usr/bin/env python3
"""Deterministic routing policy for the Nous Telegram AI factory.

Pure module: no network, no model calls, no Todoist writes. LangGraph and
command_center both call this so Telegram and Todoist do not drift.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


GROK_DECISION_MODEL = "grok-reasoning"
CHATGPT_EXECUTION_ROUTE = "codex:gpt-5.5-subscription"
LONG_WORK_PRIMARY_MODEL = "deepseek-v4-flash"
LONG_WORK_ESCALATION_MODEL = "deepseek-v4-pro"
LONG_WORK_FALLBACK_MODELS = ("kimi-k2.6", "glm-5.1", "glm-4.5-flash")

ROUTE_OPENCLAW_ROUTINE = "openclaw_routine"
ROUTE_GROK_DECISION = "grok_decision_review"
ROUTE_CHATGPT_EXECUTION = "chatgpt_execution"
ROUTE_LONG_WORK_GOAL = "long_work_goal"
ROUTE_CODEX_VERIFICATION = "codex_verification"


LONG_WORK_MARKERS = (
    "24h",
    "24 h",
    "for hours",
    "for days",
    "long work",
    "whole thing",
    "everything",
    "all tasks",
    "all of them",
    "deep-dive",
    "deep dive",
    "audit the whole",
    "factory",
    "orchestrate",
    "todoist backlog",
    "keep working",
    "don't come back",
    "do not come back",
    "100% done",
    "end-to-end",
    "step by step",
    "один за одним",
    "все задачи",
)

DECISION_MARKERS = (
    "decide",
    "decision",
    "which approach",
    "what would",
    "what is the best",
    "best option",
    "should we",
    "should i",
    "tradeoff",
    "trade-off",
    "architecture",
    "strategy",
    "best cto",
    "elon",
    "musk",
    "garry tan",
    "karpathy",
    "grok",
    "gemini",
    "claude",
    "research",
    "что лучше",
    "стоит ли",
)

EXECUTION_MARKERS = (
    "do it",
    "fix",
    "implement",
    "ship",
    "create",
    "build",
    "audit",
    "run",
    "verify",
    "set up",
    "wire",
    "deploy",
    "start working",
    "сделай",
    "почини",
    "проверь",
    "запусти",
)

SHELL_VERIFICATION_MARKERS = (
    "verify:",
    "run exact commands",
    "save outputs",
    "ssh air",
    "launchctl",
    "python3 -m pytest",
    "factory_no_drift_probe",
    "git rev-parse",
)

SENSITIVE_SATORY_OPERATOR_MARKERS = (
    "telegram group sender",
    "external operator",
    "from asyl",
    "from assyl",
    "from assylbek",
    "from denis",
    "from ruslan",
    "asyl",
    "asylbek",
    "assyl",
    "assylbek",
    "denis",
    "денис",
    "ruslan",
    "руслан",
    "асыл",
    "асиль",
    "асылбек",
)

SENSITIVE_SATORY_APK_MARKERS = (
    "апк",
    "apk",
)

SENSITIVE_SATORY_CAMERA_MARKERS = (
    "камера",
    "камеру",
    "камеры",
    "camera",
    "вар",
    "var",
    "радар",
    "лу ",
    "lu ",
)

SENSITIVE_SATORY_PROOF_MARKERS = (
    "есть ли",
    "фиксирует",
    "фиксац",
    "видишь",
    "видно",
    "доступ",
    "событ",
    "лог",
    "erap",
    "ерап",
    "заявк",
    "оскемен",
    "өскемен",
    "proof",
    "evidence",
)

EXTERNAL_OPERATOR_PROOF_SUBJECT_MARKERS = (
    "апк",
    "apk",
    "camera",
    "камера",
    "вар",
    "var",
    "радар",
    "endpoint",
    "consumer",
    "косаммер",
    "ip",
    "айпи",
    "events",
    "event",
    "событ",
    "log",
    "лог",
    "erap",
    "ерап",
    "bdl",
    "бдл",
    "лу ",
    "lu ",
    "заявк",
)

TOP_TIER_SUPERVISOR_MARKERS = (
    "top tier",
    "top-tier",
    "top module",
    "gpt at the top",
    "gpt on top",
    "second brain",
    "2nd brain",
    "frontier",
    "best cto",
    "best ceo",
    "karpathy",
    "garry tan",
    "elon",
    "bulletproof",
    "god level",
    "top gpt",
    "топ gpt",
)

CUSTOMER_TRANSFORMATION_MARKERS = (
    "what's in it for me",
    "what do i get",
    "customer",
    "customers",
    "buying behavior",
    "anticipated future",
    "transformation",
    "destination",
    "canary islands",
    "benefit",
    "result",
    "change in their life",
    "клиент",
    "покуп",
    "продаж",
    "выгода",
    "результат",
)


@dataclass(frozen=True)
class OrchestrationDecision:
    route: str
    reason: str
    first_pass_model: str
    execution_route: str
    worker_model: str
    escalation_model: str
    fallback_models: tuple[str, ...]
    todoist_action: str
    langgraph_spine: str = "required"
    hermes_boundary: str = "canary_only"
    openclaw_boundary: str = "production_runtime"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fallback_models"] = list(self.fallback_models)
        return data


def classify_text(text: str) -> OrchestrationDecision:
    """Classify one operator/task text into the factory route.

    Requirement order:
    1. Exact verification runs through Codex because it needs shell/tool access.
    2. Long work becomes a durable Goal/Todoist item and cheap worker slices.
    3. Strategy/architecture/choice gets Grok first-pass review.
    4. Bounded execution can use ChatGPT/Codex subscription.
    5. Everything else stays routine OpenClaw/grok-ceo.
    """
    raw = (text or "").strip()
    q = _normalize(raw)
    length = len(raw)

    if not q:
        return _decision(ROUTE_OPENCLAW_ROUTINE, "empty message", "none")

    if _has_any(q, SHELL_VERIFICATION_MARKERS):
        return _decision(ROUTE_CODEX_VERIFICATION, "shell verification requires tool access", "none")

    if _is_external_operator_proof_query(q):
        return _decision(
            ROUTE_CHATGPT_EXECUTION,
            "external operator proof question (Satory camera/APK live proof / Satory APK/ERAP) requires mandatory GPT/Codex execution with evidence context",
            "codex_external_proof",
        )

    if _is_top_tier_supervisor_query(q):
        return _decision(
            ROUTE_CHATGPT_EXECUTION,
            "top-tier/second-brain or customer-transformation request requires Codex/GPT-5.5 supervisor first",
            "codex_supervise_then_delegate",
        )

    if _is_long_work(q, length):
        return _decision(
            ROUTE_LONG_WORK_GOAL,
            "long or multi-step work must become durable Goal/Todoist state",
            "create_goal_and_delegate",
        )

    if _has_any(q, DECISION_MARKERS) and not _looks_like_bounded_execution(q):
        return _decision(
            ROUTE_GROK_DECISION,
            "decision/strategy prompt gets Grok first-pass review",
            "grok_first_pass",
        )

    if _looks_like_bounded_execution(q):
        return _decision(
            ROUTE_CHATGPT_EXECUTION,
            "bounded executable task can use ChatGPT/Codex subscription",
            "codex_execute",
        )

    return _decision(ROUTE_OPENCLAW_ROUTINE, "routine chat/status stays on OpenClaw", "openclaw_grok")


def model_pipeline_for_text(text: str) -> list[str]:
    """Return the model pipeline suitable for Todoist descriptions."""
    decision = classify_text(text)
    if decision.route == ROUTE_LONG_WORK_GOAL:
        return [
            decision.first_pass_model,
            decision.worker_model,
            decision.escalation_model,
            *decision.fallback_models,
            decision.execution_route,
        ]
    if decision.route in (ROUTE_CHATGPT_EXECUTION, ROUTE_CODEX_VERIFICATION):
        return [decision.execution_route, decision.first_pass_model, decision.worker_model]
    if decision.route == ROUTE_GROK_DECISION:
        return [decision.first_pass_model, decision.execution_route, decision.worker_model]
    return [decision.first_pass_model, decision.worker_model, decision.escalation_model]


def _decision(route: str, reason: str, todoist_action: str) -> OrchestrationDecision:
    return OrchestrationDecision(
        route=route,
        reason=reason,
        first_pass_model=GROK_DECISION_MODEL,
        execution_route=CHATGPT_EXECUTION_ROUTE,
        worker_model=LONG_WORK_PRIMARY_MODEL,
        escalation_model=LONG_WORK_ESCALATION_MODEL,
        fallback_models=LONG_WORK_FALLBACK_MODELS,
        todoist_action=todoist_action,
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(_contains_marker(text, marker) for marker in markers)


def _contains_marker(text: str, marker: str) -> bool:
    marker = marker.strip().lower()
    if re.fullmatch(r"[a-z0-9]+", marker):
        return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text) is not None
    return marker in text


def _is_long_work(text: str, length: int) -> bool:
    if length > 1800 and (_has_any(text, EXECUTION_MARKERS) or _has_any(text, DECISION_MARKERS)):
        return True
    marker_count = sum(1 for marker in LONG_WORK_MARKERS if marker in text)
    return marker_count >= 1 and (length > 500 or _has_any(text, EXECUTION_MARKERS))


def _looks_like_bounded_execution(text: str) -> bool:
    if _has_any(text, DECISION_MARKERS) and not _has_any(text, EXECUTION_MARKERS):
        return False
    if len(text) > 1800:
        return False
    if text.startswith(EXECUTION_MARKERS):
        return True
    return _has_any(text, EXECUTION_MARKERS) and not _has_any(text, LONG_WORK_MARKERS)


def _is_external_operator_proof_query(text: str) -> bool:
    """True for external operator proof/access/log questions.

    The bot must not guess on group-facing questions such as "do you see this
    camera?", "does APK fix events?", or "which endpoint should receive logs?".
    These are mandatory Codex routes: evidence first, answer second.
    """
    if not _has_any(text, SENSITIVE_SATORY_OPERATOR_MARKERS):
        return False
    if not _has_any(text, SENSITIVE_SATORY_PROOF_MARKERS):
        return False
    return (
        _has_any(text, SENSITIVE_SATORY_APK_MARKERS)
        or _has_any(text, SENSITIVE_SATORY_CAMERA_MARKERS)
        or _has_any(text, EXTERNAL_OPERATOR_PROOF_SUBJECT_MARKERS)
    )


def _is_sensitive_satory_apk_operator_query(text: str) -> bool:
    """True for short external Satory APK/camera/ERAP proof questions.

    These are exactly the operator-facing messages where a cheap routine answer
    is dangerous: the model must not guess whether АПК means Android APK, a
    camera is reachable, or traffic-enforcement events exist. Escalate before
    OpenClaw writes a reply.
    """
    if not (
        _has_any(text, SENSITIVE_SATORY_APK_MARKERS)
        or _has_any(text, SENSITIVE_SATORY_CAMERA_MARKERS)
    ):
        return False
    if not _has_any(text, SENSITIVE_SATORY_PROOF_MARKERS):
        return False
    return _has_any(text, SENSITIVE_SATORY_OPERATOR_MARKERS)


def _is_top_tier_supervisor_query(text: str) -> bool:
    if _has_any(text, TOP_TIER_SUPERVISOR_MARKERS):
        return True
    return _has_any(text, CUSTOMER_TRANSFORMATION_MARKERS) and _has_any(text, EXECUTION_MARKERS)
