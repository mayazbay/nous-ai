from __future__ import annotations

import json
from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import cheap_pool_benchmark as benchmark


def test_sample_prompts_stratifies_by_prompt_length(tmp_path: Path) -> None:
    log_path = tmp_path / "ask-hierarchy.jsonl"
    prompts = [
        "short status",
        "medium " * 40,
        "long " * 220,
        "another short",
    ]
    rows = [
        {"ts": "2026-05-01T00:00:00Z", "source": "telegram:tg_1:grok-ceo", "prompt": prompt, "decision": "ok"}
        for prompt in prompts
    ]
    log_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    sampled = benchmark.sample_prompts(log_path, limit=3)

    assert len(sampled) == 3
    assert any(len(item["prompt"]) < 40 for item in sampled)
    assert any(len(item["prompt"]) > 500 for item in sampled)


def test_load_fixture_prompts_preserves_case_id_and_task_class(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        json.dumps({"case_id": "russian-1", "task_class": "russian_operator_notes", "prompt": "Ответь по-русски"}) + "\n",
        encoding="utf-8",
    )

    prompts = benchmark.load_fixture_prompts(fixture)

    assert prompts == [{"case_id": "russian-1", "task_class": "russian_operator_notes", "prompt": "Ответь по-русски"}]


def test_fixture_response_passed_checks_task_specific_output() -> None:
    coding = {"case_id": "coding-1", "task_class": "coding", "prompt": "Write function"}
    rag = {"case_id": "rag-1", "task_class": "retrieval_qa", "prompt": "Answer"}

    assert benchmark.fixture_response_passed(coding, "def dedupe_preserve_order(items):\n    seen=set()\n    return []", "")
    assert not benchmark.fixture_response_passed(coding, "Here is an explanation without code", "")
    assert benchmark.fixture_response_passed(rag, "The orphan rate is 0%; Air auto-tick is com.nous.gbrain-cycle.", "")
    assert not benchmark.fixture_response_passed(rag, "It is healthy.", "")


def test_run_benchmark_scores_candidates_with_pass_rate_latency_and_cost(monkeypatch, tmp_path: Path) -> None:
    prompts = [{"case_id": "p1", "task_class": "unknown", "prompt": "Reply OK"}, {"case_id": "p2", "task_class": "unknown", "prompt": "Reply JSON"}]

    def fake_call(model: str, prompt: str, *, base_url: str, master_key: str, timeout: int, max_tokens: int):
        if model == "qwen3-coder-plus":
            return "OK", 900, "", 0.0004
        if "JSON" in prompt:
            return "", 5000, "timeout", 0.002
        return "OK", 4000, "", 0.002

    monkeypatch.setattr(benchmark, "call_model", fake_call)

    result = benchmark.run_benchmark(
        models=["deepseek-v4-flash", "qwen3-coder-plus"],
        prompts=prompts,
        base_url="http://litellm",
        master_key="test",
        timeout=1,
        max_tokens=32,
    )

    assert result["winner"]["model"] == "qwen3-coder-plus"
    assert result["summary"]["qwen3-coder-plus"]["pass_rate"] == 1.0
    assert result["summary"]["deepseek-v4-flash"]["errors"] == 1
    assert result["results"][0]["task_class"] == "unknown"


def test_write_benchmark_report_flags_override_candidate(tmp_path: Path) -> None:
    result = {
        "current_model": "deepseek-v4-flash",
        "winner": {"model": "qwen3-coder-plus", "score": 0.88},
        "summary": {"deepseek-v4-flash": {"score": 0.4}, "qwen3-coder-plus": {"score": 0.88}},
        "results": [],
    }

    path = benchmark.write_report(result, tmp_path, today="2026-05-17")

    text = path.read_text(encoding="utf-8")
    assert path.name == "CHEAP-POOL-BENCHMARK-2026-05-17.md"
    assert "override-candidate" in text
    assert "qwen3-coder-plus" in text
