from __future__ import annotations

import json
from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import model_promotion_gate as gate


TASK_CLASSES = [
    "coding",
    "audit_summarization",
    "retrieval_qa",
    "russian_operator_notes",
    "long_handoff_compression",
]


def _write_fixture(path: Path) -> None:
    rows = [
        {"case_id": f"{task_class}-1", "task_class": task_class, "prompt": f"Prompt for {task_class}"}
        for task_class in TASK_CLASSES
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_proposal(path: Path, *, current: str = "deepseek-v4-flash", candidate: str = "qwen3-coder-plus") -> None:
    path.write_text(
        f"# Cheap-pool proposal\n\nCurrent: `{current}` score `0.5000`.\nWinner: `{candidate}` score `0.7000`.\n",
        encoding="utf-8",
    )


def _benchmark_payload(*, fixture: Path, current: str = "deepseek-v4-flash", candidate: str = "qwen3-coder-plus", winner: str = "qwen3-coder-plus") -> dict:
    results = []
    for model in (current, candidate):
        for task_class in TASK_CLASSES:
            results.append(
                {
                    "model": model,
                    "case_id": f"{task_class}-1",
                    "task_class": task_class,
                    "passed": True,
                    "error": "",
                }
            )
    return {
        "current_model": current,
        "winner": {"model": winner, "score": 0.75 if winner == candidate else 0.60},
        "fixture_path": str(fixture),
        "task_classes": TASK_CLASSES,
        "prompt_count": 5,
        "summary": {
            current: {"passed": 4, "total": 5, "errors": 1, "score": 0.55},
            candidate: {"passed": 5, "total": 5, "errors": 0, "score": 0.75},
        },
        "results": results,
    }


def test_promotion_gate_green_when_candidate_wins_real_fixture(tmp_path: Path) -> None:
    fixture = tmp_path / "nous-task-classes-2026-05-18.jsonl"
    proposal = tmp_path / "proposal.md"
    benchmark = tmp_path / "benchmark.json"
    _write_fixture(fixture)
    _write_proposal(proposal)
    benchmark.write_text(json.dumps(_benchmark_payload(fixture=fixture)), encoding="utf-8")

    result = gate.evaluate_promotion(proposal_path=proposal, benchmark_json_path=benchmark, fixture_path=fixture)

    assert result["ok"] is True
    assert all(check["ok"] for check in result["checks"])


def test_promotion_gate_red_when_benchmark_winner_is_not_candidate(tmp_path: Path) -> None:
    fixture = tmp_path / "nous-task-classes-2026-05-18.jsonl"
    proposal = tmp_path / "proposal.md"
    benchmark = tmp_path / "benchmark.json"
    _write_fixture(fixture)
    _write_proposal(proposal)
    benchmark.write_text(json.dumps(_benchmark_payload(fixture=fixture, winner="deepseek-v4-flash")), encoding="utf-8")

    result = gate.evaluate_promotion(proposal_path=proposal, benchmark_json_path=benchmark, fixture_path=fixture)

    assert result["ok"] is False
    assert any(check["name"] == "benchmark_winner_matches_candidate" and not check["ok"] for check in result["checks"])


def test_promotion_gate_red_when_fixture_class_is_missing(tmp_path: Path) -> None:
    fixture = tmp_path / "nous-task-classes-2026-05-18.jsonl"
    proposal = tmp_path / "proposal.md"
    benchmark = tmp_path / "benchmark.json"
    _write_fixture(fixture)
    _write_proposal(proposal)
    payload = _benchmark_payload(fixture=fixture)
    payload["task_classes"] = TASK_CLASSES[:-1]
    payload["results"] = [row for row in payload["results"] if row["task_class"] != "long_handoff_compression"]
    benchmark.write_text(json.dumps(payload), encoding="utf-8")

    result = gate.evaluate_promotion(proposal_path=proposal, benchmark_json_path=benchmark, fixture_path=fixture)

    assert result["ok"] is False
    assert any(check["name"] == "benchmark_classes_cover_required" and not check["ok"] for check in result["checks"])
