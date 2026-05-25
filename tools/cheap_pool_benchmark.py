#!/usr/bin/env python3
"""Monthly cheap-pool benchmark against recent `/ask` prompts or fixed fixtures."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import statistics
import urllib.error
import urllib.request
from typing import Any


DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_ASK_LOG = Path("/Users/madia/nous-agaas/logs/ask-hierarchy.jsonl")
DEFAULT_BASE_URL = "http://127.0.0.1:4000/v1/chat/completions"
DEFAULT_MODELS = ["deepseek-v4-flash", "deepseek-v4-pro", "qwen3-coder-plus", "kimi-k2.6", "glm-5.1"]


def _prompt_from_row(row: dict[str, Any]) -> str:
    for key in ("prompt", "query", "task", "message"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def sample_prompts(log_path: Path, *, limit: int = 10) -> list[dict[str, str]]:
    rows = []
    if not log_path.exists():
        return []
    for raw in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        prompt = _prompt_from_row(row)
        if prompt:
            rows.append({"case_id": f"ask_{len(rows) + 1}", "prompt": prompt})
    buckets = {
        "short": [r for r in rows if len(r["prompt"]) < 120],
        "medium": [r for r in rows if 120 <= len(r["prompt"]) < 600],
        "long": [r for r in rows if len(r["prompt"]) >= 600],
    }
    sampled: list[dict[str, str]] = []
    while len(sampled) < min(limit, len(rows)):
        progressed = False
        for bucket in ("short", "medium", "long"):
            if buckets[bucket]:
                sampled.append(buckets[bucket].pop(0))
                progressed = True
                if len(sampled) >= limit:
                    break
        if not progressed:
            break
    return sampled


def load_fixture_prompts(fixture_path: Path, *, limit: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for lineno, raw in enumerate(fixture_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{fixture_path}:{lineno}: invalid JSONL row: {exc}") from exc
        prompt = _prompt_from_row(row)
        if not prompt:
            raise ValueError(f"{fixture_path}:{lineno}: fixture row missing prompt/query/task/message")
        rows.append(
            {
                "case_id": str(row.get("case_id") or f"fixture_{len(rows) + 1}"),
                "task_class": str(row.get("task_class") or "unknown"),
                "prompt": prompt,
            }
        )
        if limit is not None and len(rows) >= limit:
            break
    return rows


def _line_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _cyrillic_count(text: str) -> int:
    return sum(1 for char in text if "\u0400" <= char <= "\u04ff")


def fixture_response_passed(prompt: dict[str, str], text: str, error: str) -> bool:
    if error or not text.strip():
        return False
    task_class = prompt.get("task_class", "")
    lowered = text.lower()
    if task_class == "coding":
        return "def dedupe_preserve_order" in lowered and "seen" in lowered and "return" in lowered
    if task_class == "audit_summarization":
        bullet_lines = [
            line
            for line in text.splitlines()
            if line.strip().startswith(("-", "*", "•")) or line.strip()[:2] in {"1.", "2.", "3."}
        ]
        return len(bullet_lines) == 3 and all(len(line.split()) <= 18 for line in bullet_lines)
    if task_class == "retrieval_qa":
        return "0%" in text and "com.nous.gbrain-cycle" in text
    if task_class == "russian_operator_notes":
        return _cyrillic_count(text) >= 40 and _line_count(text) >= 3 and ("2" in text or "час" in lowered)
    if task_class == "long_handoff_compression":
        sentences = [part for part in text.replace("\n", " ").split(".") if part.strip()]
        has_owner = "owner" in lowered or "madi" in lowered or "мади" in lowered
        return 2 <= len(sentences) <= 6 and "shipped" in lowered and ("open" in lowered or "outstanding" in lowered) and has_owner
    return True


def call_model(
    model: str,
    prompt: str,
    *,
    base_url: str,
    master_key: str,
    timeout: int,
    max_tokens: int,
) -> tuple[str, int, str, float]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Answer briefly and follow the user's requested format."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {master_key}", "Content-Type": "application/json"},
        method="POST",
    )
    start = dt.datetime.now(dt.timezone.utc)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        latency_ms = int((dt.datetime.now(dt.timezone.utc) - start).total_seconds() * 1000)
        content = body.get("choices", [{}])[0].get("message", {}).get("content") or ""
        usage = body.get("usage") or {}
        cost = float(usage.get("cost") or usage.get("cost_est") or 0.0)
        return content, latency_ms, "", cost
    except urllib.error.HTTPError as exc:
        latency_ms = int((dt.datetime.now(dt.timezone.utc) - start).total_seconds() * 1000)
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return "", latency_ms, f"HTTP {exc.code}: {detail}", 0.0
    except Exception as exc:
        latency_ms = int((dt.datetime.now(dt.timezone.utc) - start).total_seconds() * 1000)
        return "", latency_ms, f"{type(exc).__name__}: {exc}", 0.0


def run_benchmark(
    *,
    models: list[str],
    prompts: list[dict[str, str]],
    base_url: str,
    master_key: str,
    timeout: int,
    max_tokens: int,
) -> dict[str, Any]:
    results = []
    for model in models:
        for prompt in prompts:
            text, latency_ms, error, cost = call_model(
                model,
                prompt["prompt"],
                base_url=base_url,
                master_key=master_key,
                timeout=timeout,
                max_tokens=max_tokens,
            )
            results.append(
                {
                    "model": model,
                    "case_id": prompt["case_id"],
                    "task_class": prompt.get("task_class", "ask_log"),
                    "passed": fixture_response_passed(prompt, text, error),
                    "latency_ms": latency_ms,
                    "error": error,
                    "cost_est": cost,
                    "got": text.strip()[:200],
                }
            )
    summary: dict[str, dict[str, Any]] = {}
    for model in models:
        rows = [r for r in results if r["model"] == model]
        passed = sum(1 for r in rows if r["passed"])
        errors = sum(1 for r in rows if r["error"])
        latencies = [float(r["latency_ms"]) for r in rows]
        costs = [float(r["cost_est"]) for r in rows]
        pass_rate = passed / len(rows) if rows else 0.0
        error_rate = errors / len(rows) if rows else 1.0
        p50 = statistics.median(latencies) if latencies else 999999.0
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        summary[model] = {
            "passed": passed,
            "total": len(rows),
            "pass_rate": pass_rate,
            "errors": errors,
            "error_rate": error_rate,
            "p50_latency_ms": p50,
            "avg_cost": avg_cost,
        }
    max_inv_latency = max((1 / max(v["p50_latency_ms"], 1.0) for v in summary.values()), default=1.0)
    max_inv_cost = max((1 / max(v["avg_cost"], 1e-12) for v in summary.values()), default=1.0)
    for model, item in summary.items():
        latency_score = (1 / max(item["p50_latency_ms"], 1.0)) / max_inv_latency
        cost_score = (1 / max(item["avg_cost"], 1e-12)) / max_inv_cost
        reliability = 1.0 - item["error_rate"]
        item["score"] = round(0.5 * item["pass_rate"] + 0.2 * latency_score + 0.2 * cost_score + 0.1 * reliability, 6)
    winner_model, winner = max(summary.items(), key=lambda kv: kv[1]["score"]) if summary else ("", {"score": 0.0})
    return {"winner": {"model": winner_model, "score": winner["score"]}, "summary": summary, "results": results}


def write_report(result: dict[str, Any], output_dir: Path, *, today: str | None = None) -> Path:
    day = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=5))).date().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"CHEAP-POOL-BENCHMARK-{day}.md"
    current = result.get("current_model", "")
    winner = result.get("winner", {})
    status = "override-candidate" if current and winner.get("model") and winner.get("model") != current else "no-change"
    lines = [
        "---",
        "type: progress",
        f"id: CHEAP-POOL-BENCHMARK-{day}",
        f'title: "Cheap-pool benchmark {day}"',
        f"date: {day}",
        f"status: {status}",
        "tags: [model-rotation, benchmark, cheap-pool]",
        "---",
        "",
        f"# Cheap-pool benchmark {day}",
        "",
        f"Status: `{status}`",
        f"Current pin: `{current}`",
        f"Benchmark winner: `{winner.get('model', '')}` score `{float(winner.get('score', 0.0)):.4f}`",
        "",
        "| Model | Score | Pass rate | Errors | P50 latency ms |",
        "|---|---:|---:|---:|---:|",
    ]
    for model, item in sorted(result.get("summary", {}).items()):
        lines.append(
            f"| `{model}` | {float(item.get('score', 0.0)):.4f} | {float(item.get('pass_rate', 0.0)):.2f} | "
            f"{int(item.get('errors', 0))} | {float(item.get('p50_latency_ms', 0)):.0f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--ask-log", type=Path, default=DEFAULT_ASK_LOG)
    parser.add_argument("--fixture", type=Path, help="Fixed JSONL fixture corpus. Required for promotion gates.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--base-url", default=os.environ.get("LITELLM_CHAT_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--current-model", default="deepseek-v4-flash")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--today")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    prompts = load_fixture_prompts(args.fixture, limit=args.limit) if args.fixture else sample_prompts(args.ask_log, limit=args.limit)
    master_key = os.environ.get("LITELLM_MASTER_KEY", "")
    if not master_key:
        env_path = Path.home() / "nous-agaas/litellm/.env"
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8").splitlines():
                if raw.startswith("LITELLM_MASTER_KEY="):
                    master_key = raw.split("=", 1)[1].strip().strip('"')
                    break
    if not master_key:
        raise SystemExit("LITELLM_MASTER_KEY missing")
    result = run_benchmark(
        models=[m.strip() for m in args.models.split(",") if m.strip()],
        prompts=prompts,
        base_url=args.base_url,
        master_key=master_key,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
    )
    result["current_model"] = args.current_model
    result["prompt_count"] = len(prompts)
    if args.fixture:
        result["fixture_path"] = str(args.fixture)
        result["task_classes"] = sorted({item.get("task_class", "unknown") for item in prompts})
    report = write_report(result, args.output_dir or args.wiki / "pages/progress", today=args.today)
    result["report_path"] = str(report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"winner={result['winner']['model']} report={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
