#!/usr/bin/env python3
"""Block model-default promotion unless a candidate wins real Nous fixtures."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
from typing import Any


DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_FIXTURE = DEFAULT_WIKI / "pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl"
REQUIRED_TASK_CLASSES = {
    "coding",
    "audit_summarization",
    "retrieval_qa",
    "russian_operator_notes",
    "long_handoff_compression",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_approved_pair(proposal_path: Path) -> tuple[str, str]:
    text = proposal_path.read_text(encoding="utf-8", errors="replace")
    current = re.search(r"^Current:\s*`([^`]+)`", text, flags=re.MULTILINE)
    winner = re.search(r"^Winner:\s*`([^`]+)`", text, flags=re.MULTILINE)
    if not current or not winner:
        raise ValueError(f"could not parse current/winner from {proposal_path}")
    return current.group(1), winner.group(1)


def fixture_profile(fixture_path: Path) -> dict[str, Any]:
    classes: set[str] = set()
    case_ids: set[str] = set()
    for lineno, raw in enumerate(fixture_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{fixture_path}:{lineno}: invalid JSONL row: {exc}") from exc
        case_id = str(row.get("case_id") or "").strip()
        task_class = str(row.get("task_class") or "").strip()
        prompt = str(row.get("prompt") or row.get("query") or row.get("task") or row.get("message") or "").strip()
        if not case_id or not task_class or not prompt:
            raise ValueError(f"{fixture_path}:{lineno}: fixture row requires case_id, task_class, and prompt")
        case_ids.add(case_id)
        classes.add(task_class)
    return {"case_count": len(case_ids), "task_classes": sorted(classes), "case_ids": sorted(case_ids)}


def _check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def _summary_row(benchmark: dict[str, Any], model: str) -> dict[str, Any]:
    row = (benchmark.get("summary") or {}).get(model)
    return row if isinstance(row, dict) else {}


def _result_classes(benchmark: dict[str, Any], model: str) -> set[str]:
    classes = set()
    for row in benchmark.get("results") or []:
        if row.get("model") == model and row.get("case_id"):
            classes.add(str(row.get("task_class") or "unknown"))
    return classes


def evaluate_promotion(
    *,
    proposal_path: Path,
    benchmark_json_path: Path,
    fixture_path: Path = DEFAULT_FIXTURE,
    min_cases: int = 5,
    required_task_classes: set[str] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    required = required_task_classes or REQUIRED_TASK_CLASSES
    current, candidate = parse_approved_pair(proposal_path)
    benchmark = load_json(benchmark_json_path)
    fixture = fixture_profile(fixture_path)
    benchmark_winner = str((benchmark.get("winner") or {}).get("model") or "")
    benchmark_current = str(benchmark.get("current_model") or "")
    prompt_count = int(benchmark.get("prompt_count") or 0)
    recorded_fixture = str(benchmark.get("fixture_path") or "")
    recorded_classes = set(benchmark.get("task_classes") or [])
    current_row = _summary_row(benchmark, current)
    candidate_row = _summary_row(benchmark, candidate)
    current_score = float(current_row.get("score") or 0.0)
    candidate_score = float(candidate_row.get("score") or 0.0)
    current_passed = int(current_row.get("passed") or 0)
    candidate_passed = int(candidate_row.get("passed") or 0)
    current_errors = int(current_row.get("errors") or 0)
    candidate_errors = int(candidate_row.get("errors") or 0)
    candidate_classes = _result_classes(benchmark, candidate)
    current_classes = _result_classes(benchmark, current)

    _check(checks, "candidate_is_new_default", candidate != current, f"current={current} candidate={candidate}")
    _check(checks, "benchmark_current_matches_proposal", benchmark_current == current, f"benchmark_current={benchmark_current} proposal_current={current}")
    _check(checks, "benchmark_winner_matches_candidate", benchmark_winner == candidate, f"benchmark_winner={benchmark_winner} candidate={candidate}")
    _check(checks, "fixture_case_count", fixture["case_count"] >= min_cases, f"fixture_cases={fixture['case_count']} min_cases={min_cases}")
    _check(checks, "benchmark_prompt_count", prompt_count >= min_cases, f"prompt_count={prompt_count} min_cases={min_cases}")
    _check(checks, "fixture_path_recorded", bool(recorded_fixture) and Path(recorded_fixture).name == fixture_path.name, f"recorded_fixture={recorded_fixture or '<missing>'}")
    _check(checks, "fixture_classes_cover_required", set(fixture["task_classes"]) >= required, f"fixture_classes={fixture['task_classes']}")
    _check(checks, "benchmark_classes_cover_required", recorded_classes >= required, f"benchmark_classes={sorted(recorded_classes)}")
    _check(checks, "candidate_summary_present", bool(candidate_row), f"candidate={candidate} summary_present={bool(candidate_row)}")
    _check(checks, "current_summary_present", bool(current_row), f"current={current} summary_present={bool(current_row)}")
    _check(checks, "candidate_result_classes", candidate_classes >= required, f"candidate_classes={sorted(candidate_classes)}")
    _check(checks, "current_result_classes", current_classes >= required, f"current_classes={sorted(current_classes)}")
    _check(checks, "candidate_cases_covered", int(candidate_row.get("total") or 0) >= min_cases, f"candidate_total={candidate_row.get('total', 0)}")
    _check(checks, "current_cases_covered", int(current_row.get("total") or 0) >= min_cases, f"current_total={current_row.get('total', 0)}")
    _check(checks, "candidate_score_beats_current", candidate_score > current_score, f"candidate_score={candidate_score} current_score={current_score}")
    _check(checks, "no_pass_regression", candidate_passed >= current_passed, f"candidate_passed={candidate_passed} current_passed={current_passed}")
    _check(checks, "no_error_regression", candidate_errors <= current_errors, f"candidate_errors={candidate_errors} current_errors={current_errors}")

    ok = all(item["ok"] for item in checks)
    return {
        "ok": ok,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "proposal_path": str(proposal_path),
        "benchmark_json_path": str(benchmark_json_path),
        "fixture_path": str(fixture_path),
        "current": current,
        "candidate": candidate,
        "benchmark_winner": benchmark_winner,
        "checks": checks,
    }


def write_audit(result: dict[str, Any], output_dir: Path, *, today: str | None = None) -> Path:
    day = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=5))).date().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"MODEL-PROMOTION-GATE-{day}.md"
    status = "green" if result["ok"] else "red"
    lines = [
        "---",
        "type: audit",
        f"id: MODEL-PROMOTION-GATE-{day}",
        f'title: "Model promotion gate {day}"',
        f"date: {day}",
        f"status: {status}",
        "tags: [model-promotion, benchmark, cheap-pool, satory-nous-fixtures]",
        "---",
        "",
        f"# Model promotion gate {day}",
        "",
        f"Status: `{status}`",
        f"Current: `{result['current']}`",
        f"Candidate: `{result['candidate']}`",
        f"Benchmark winner: `{result['benchmark_winner']}`",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for check in result["checks"]:
        marker = "GREEN" if check["ok"] else "RED"
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| `{check['name']}` | {marker} | {detail} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--benchmark-json", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--min-cases", type=int, default=5)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--today")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = evaluate_promotion(
        proposal_path=args.proposal,
        benchmark_json_path=args.benchmark_json,
        fixture_path=args.fixture,
        min_cases=args.min_cases,
    )
    if args.output_dir:
        result["audit_path"] = str(write_audit(result, args.output_dir, today=args.today))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"promotion_gate={'GREEN' if result['ok'] else 'RED'} candidate={result['candidate']} current={result['current']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
