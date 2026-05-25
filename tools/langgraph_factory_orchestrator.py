#!/usr/bin/env python3
"""LangGraph spine for the Nous Telegram/OpenClaw factory router.

The graph is intentionally small: classify, plan, finish. The production
decision logic stays in factory_orchestration_policy.py so tests and Todoist
dispatch can use the same source of truth. If LangGraph is not installed, this
CLI returns the same policy result with langgraph_available=false instead of
pretending the graph ran.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Literal
from typing_extensions import TypedDict

from factory_orchestration_policy import (
    ROUTE_CHATGPT_EXECUTION,
    ROUTE_CODEX_VERIFICATION,
    ROUTE_GROK_DECISION,
    ROUTE_LONG_WORK_GOAL,
    classify_text,
    model_pipeline_for_text,
)


class RouterState(TypedDict, total=False):
    text: str
    decision: dict[str, Any]
    execution_plan: dict[str, Any]
    langgraph_available: bool
    error: str


def run_orchestration(text: str) -> dict[str, Any]:
    """Run the route through LangGraph when available, otherwise fallback."""
    try:
        return _run_langgraph(text)
    except ModuleNotFoundError as exc:
        result = _fallback(text)
        result["error"] = f"LangGraph unavailable: {exc.name}"
        return result


def _run_langgraph(text: str) -> dict[str, Any]:
    from langgraph.graph import END, START, StateGraph

    def classify_node(state: RouterState) -> RouterState:
        decision = classify_text(state["text"]).to_dict()
        return {"decision": decision, "langgraph_available": True}

    def route_node(state: RouterState) -> Literal["goal_node", "codex_node", "grok_node", "routine_node"]:
        route = state["decision"]["route"]
        if route == ROUTE_LONG_WORK_GOAL:
            return "goal_node"
        if route in (ROUTE_CHATGPT_EXECUTION, ROUTE_CODEX_VERIFICATION):
            return "codex_node"
        if route == ROUTE_GROK_DECISION:
            return "grok_node"
        return "routine_node"

    def goal_node(state: RouterState) -> RouterState:
        return {"execution_plan": _plan_for(state["text"], state["decision"])}

    def codex_node(state: RouterState) -> RouterState:
        return {"execution_plan": _plan_for(state["text"], state["decision"])}

    def grok_node(state: RouterState) -> RouterState:
        return {"execution_plan": _plan_for(state["text"], state["decision"])}

    def routine_node(state: RouterState) -> RouterState:
        return {"execution_plan": _plan_for(state["text"], state["decision"])}

    graph = StateGraph(RouterState)
    graph.add_node("classify", classify_node)
    graph.add_node("goal_node", goal_node)
    graph.add_node("codex_node", codex_node)
    graph.add_node("grok_node", grok_node)
    graph.add_node("routine_node", routine_node)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route_node)
    graph.add_edge("goal_node", END)
    graph.add_edge("codex_node", END)
    graph.add_edge("grok_node", END)
    graph.add_edge("routine_node", END)
    compiled = graph.compile()
    state = compiled.invoke({"text": text})
    return _public_result(state)


def _fallback(text: str) -> dict[str, Any]:
    decision = classify_text(text).to_dict()
    return _public_result(
        {
            "text": text,
            "decision": decision,
            "execution_plan": _plan_for(text, decision),
            "langgraph_available": False,
        }
    )


def _plan_for(text: str, decision: dict[str, Any]) -> dict[str, Any]:
    route = decision["route"]
    if route == ROUTE_LONG_WORK_GOAL:
        action = "create_goal_todoist_and_delegate_worker_slices"
    elif route == ROUTE_CHATGPT_EXECUTION:
        action = "run_codex_gpt55_subscription"
    elif route == ROUTE_CODEX_VERIFICATION:
        action = "run_codex_shell_verification"
    elif route == ROUTE_GROK_DECISION:
        action = "route_openclaw_grok_ceo_first_pass"
    else:
        action = "route_openclaw_grok_ceo_routine"
    return {
        "action": action,
        "model_pipeline": model_pipeline_for_text(text),
        "todoist_action": decision["todoist_action"],
        "production_runtime": "OpenClaw",
        "learning_core": "Hermes canary only",
        "memory_substrate": ["Obsidian", "gbrain", "OpenBrain"],
    }


def _public_result(state: RouterState) -> dict[str, Any]:
    return {
        "langgraph_available": bool(state.get("langgraph_available")),
        "decision": state.get("decision", {}),
        "execution_plan": state.get("execution_plan", {}),
        "error": state.get("error", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True, help="Text to classify through the factory router")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()
    result = run_orchestration(args.text)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        decision = result["decision"]
        plan = result["execution_plan"]
        print(f"route={decision.get('route')}")
        print(f"reason={decision.get('reason')}")
        print(f"action={plan.get('action')}")
        print(f"langgraph_available={result.get('langgraph_available')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

