from __future__ import annotations

from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import langgraph_factory_orchestrator as orchestrator


def test_orchestrator_returns_public_decision_shape() -> None:
    result = orchestrator.run_orchestration("Fix the Telegram OpenClaw route and verify it.")

    assert "langgraph_available" in result
    assert result["decision"]["route"] == "chatgpt_execution"
    assert result["execution_plan"]["action"] == "run_codex_gpt55_subscription"
    assert result["execution_plan"]["production_runtime"] == "OpenClaw"

