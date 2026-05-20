from __future__ import annotations

import json
from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import cheap_pool_winner_picker as picker


TASK_CLASSES = [
    "coding",
    "audit_summarization",
    "retrieval_qa",
    "russian_operator_notes",
    "long_handoff_compression",
]


def _models_payload() -> dict:
    return {
        "data": [
            {
                "id": "deepseek/deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "context_length": 64000,
                "pricing": {"prompt": "0.10", "completion": "0.20"},
                "quality": 0.70,
            },
            {
                "id": "qwen/qwen3-coder-plus",
                "name": "Qwen3 Coder Plus",
                "context_length": 128000,
                "pricing": {"prompt": "0.08", "completion": "0.16"},
                "quality": 0.95,
            },
            {
                "id": "anthropic/claude-opus-4-7",
                "name": "Claude Opus 4.7",
                "context_length": 200000,
                "pricing": {"prompt": "15", "completion": "75"},
                "quality": 1.0,
            },
        ]
    }


def _write_log(path: Path) -> None:
    rows = [
        {"ts": "2026-05-14T00:00:00Z", "model": "deepseek-v4-flash", "latency_ms": 5000, "decision": "ok", "cost_est": 0.001},
        {"ts": "2026-05-15T00:00:00Z", "model": "deepseek-v4-flash", "latency_ms": 7000, "decision": "error", "cost_est": 0.001},
        {"ts": "2026-05-16T00:00:00Z", "model": "qwen3-coder-plus", "latency_ms": 2500, "decision": "ok", "cost_est": 0.0007},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_fixture(path: Path) -> None:
    rows = [
        {"case_id": f"{task_class}-1", "task_class": task_class, "prompt": f"Prompt for {task_class}"}
        for task_class in TASK_CLASSES
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_green_benchmark(path: Path, fixture: Path) -> None:
    results = []
    for model in ("deepseek-v4-flash", "qwen3-coder-plus"):
        for task_class in TASK_CLASSES:
            results.append({"model": model, "case_id": f"{task_class}-1", "task_class": task_class, "passed": True, "error": ""})
    payload = {
        "current_model": "deepseek-v4-flash",
        "winner": {"model": "qwen3-coder-plus", "score": 0.72},
        "fixture_path": str(fixture),
        "task_classes": TASK_CLASSES,
        "prompt_count": 5,
        "summary": {
            "deepseek-v4-flash": {"passed": 4, "total": 5, "errors": 1, "score": 0.50},
            "qwen3-coder-plus": {"passed": 5, "total": 5, "errors": 0, "score": 0.72},
        },
        "results": results,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_pick_winner_filters_chinese_open_source_and_requires_margin(tmp_path: Path) -> None:
    log_path = tmp_path / "ask-hierarchy.jsonl"
    _write_log(log_path)

    result = picker.pick_winner(
        _models_payload(),
        current_model="deepseek-v4-flash",
        ask_log=log_path,
        now_iso="2026-05-17T03:00:00+05:00",
    )

    assert result["current"]["model"] == "deepseek-v4-flash"
    assert result["winner"]["model"] == "qwen3-coder-plus"
    assert result["should_propose"] is True
    assert all("claude" not in item["model"] for item in result["candidates"])


def test_write_proposal_markdown_when_winner_beats_current(tmp_path: Path) -> None:
    result = {
        "current": {"model": "deepseek-v4-flash", "score": 0.50},
        "winner": {"model": "qwen3-coder-plus", "score": 0.72},
        "should_propose": True,
        "margin_required": 1.05,
        "candidates": [],
    }

    path = picker.write_proposal(result, tmp_path, today="2026-05-17")

    text = path.read_text(encoding="utf-8")
    assert path.name == "CHEAP-POOL-PROPOSAL-2026-05-17.md"
    assert "deepseek-v4-flash" in text
    assert "qwen3-coder-plus" in text
    assert "/approve cheap-pool 2026-05-17" in text


def test_no_proposal_when_winner_does_not_clear_margin(tmp_path: Path) -> None:
    payload = {
        "data": [
            {
                "id": "deepseek/deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "context_length": 64000,
                "pricing": {"prompt": "0.10", "completion": "0.20"},
                "quality": 0.90,
            },
            {
                "id": "qwen/qwen3-coder-plus",
                "name": "Qwen3 Coder Plus",
                "context_length": 64000,
                "pricing": {"prompt": "0.10", "completion": "0.20"},
                "quality": 0.91,
            },
        ]
    }

    result = picker.pick_winner(payload, current_model="deepseek-v4-flash", ask_log=tmp_path / "missing.jsonl")

    assert result["should_propose"] is False


def test_approve_proposal_updates_ceo_hierarchy_pin_with_rule_zero_marker(tmp_path: Path) -> None:
    proposal = picker.write_proposal(
        {
            "current": {"model": "deepseek-v4-flash", "score": 0.50},
            "winner": {"model": "qwen3-coder-plus", "score": 0.72},
            "should_propose": True,
            "margin_required": 1.05,
            "candidates": [],
        },
        tmp_path,
        today="2026-05-17",
    )
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\n"
        "type: skill\n"
        "title: \"ceo-hierarchy v1.8.6\"\n"
        "version: 1.8.6\n"
        "---\n\n"
        "# ceo-hierarchy v1.8.6\n\n"
        "## Current rules (binding)\n\n"
        "- Existing pin: `deepseek-v4-flash`.\n\n"
        "## Timeline\n\n"
        "- **2026-05-15** | v1.8.5 -> v1.8.6 -- AP-24.\n",
        encoding="utf-8",
    )

    changed = picker.apply_approved_pin(skill, proposal, today="2026-05-17")

    text = skill.read_text(encoding="utf-8")
    assert changed is True
    assert "version: 1.8.7" in text
    assert "# ceo-hierarchy v1.8.7" in text
    assert "Current cheap-pool pin: `qwen3-coder-plus`" in text
    assert "gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill" in text


def test_approve_proposal_skips_runtime_rsync_by_default(tmp_path: Path, capsys) -> None:
    proposal = picker.write_proposal(
        {
            "current": {"model": "deepseek-v4-flash", "score": 0.50},
            "winner": {"model": "qwen3-coder-plus", "score": 0.72},
            "should_propose": True,
            "margin_required": 1.05,
            "candidates": [],
        },
        tmp_path,
        today="2026-05-17",
    )
    skill = tmp_path / "SKILL.md"
    fixture = tmp_path / "fixture.jsonl"
    benchmark = tmp_path / "benchmark.json"
    _write_fixture(fixture)
    _write_green_benchmark(benchmark, fixture)
    skill.write_text(
        "---\n"
        "type: skill\n"
        "title: \"ceo-hierarchy v1.8.6\"\n"
        "version: 1.8.6\n"
        "---\n\n"
        "# ceo-hierarchy v1.8.6\n\n"
        "## Current rules (binding)\n\n"
        "## Timeline\n\n",
        encoding="utf-8",
    )

    rc = picker.main(
        [
            "--approve-proposal",
            str(proposal),
            "--skill-path",
            str(skill),
            "--wiki",
            str(tmp_path),
            "--today",
            "2026-05-17",
            "--promotion-benchmark-json",
            str(benchmark),
            "--promotion-fixture",
            str(fixture),
            "--dry-run",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["approved"] is True
    assert payload["promotion_gate"]["ok"] is True
    assert payload["runtime_rsync"]["detail"].startswith("runtime rsync skipped")


def test_approve_proposal_requires_promotion_benchmark_json(tmp_path: Path, capsys) -> None:
    proposal = picker.write_proposal(
        {
            "current": {"model": "deepseek-v4-flash", "score": 0.50},
            "winner": {"model": "qwen3-coder-plus", "score": 0.72},
            "should_propose": True,
            "margin_required": 1.05,
            "candidates": [],
        },
        tmp_path,
        today="2026-05-17",
    )

    rc = picker.main(["--approve-proposal", str(proposal), "--wiki", str(tmp_path), "--dry-run", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["approved"] is False
    assert payload["promotion_gate"]["ok"] is False
