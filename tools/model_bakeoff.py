#!/usr/bin/env python3
"""Run a small model bakeoff through the Air LiteLLM proxy.

The goal is not a synthetic leaderboard. It is an operational gate for the
factory: can each candidate follow compact instructions, return parseable
output, and stay within latency/error bounds on the exact route we use.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODELS = ["deepseek-v4-flash", "deepseek-v4-pro", "glm-5.1"]
DEFAULT_BASE_URL = "http://127.0.0.1:4000/v1/chat/completions"
ENV_FILES = [
    Path.home() / "nous-agaas/.env",
    Path.home() / "nous-agaas/litellm/.env",
]


@dataclass(frozen=True)
class Case:
    case_id: str
    prompt: str
    expect: str
    kind: str = "exact"


CASES = [
    Case("exact-token", "Reply with exactly MODEL_BAKEOFF_OK.", "MODEL_BAKEOFF_OK"),
    Case("json-one-key", 'Return exactly valid minified JSON: {"status":"ok"}.', '{"status":"ok"}', "json_exact"),
    Case("math-small", "Return only the number: 17*19.", "323"),
    Case("no-extra-words", "Return exactly these three pipe-separated words: alpha|beta|gamma", "alpha|beta|gamma"),
    Case("russian-extract", "Из текста 'Срок: пятница; владелец: Денис' верни только владельца.", "Денис", "contains"),
    Case("priority", "Task says: production camera path is down. Return only P1, P2, or P3.", "P1"),
    Case("date-format", "Return only today's date from this string: 2026-04-27 Asia/Almaty.", "2026-04-27"),
    Case("boolean", "If 10.170.0.0/16 route is absent, return only false.", "false"),
    Case("short-summary", "Summarize in exactly 5 words: Notion token missing blocks automated sync.", r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+\.?$", "regex"),
    Case("csv", "Return exactly CSV header only for task,owner,priority.", "task,owner,priority"),
    Case("classification", "Classify 'refresh Google Calendar OAuth' as auth, code, sales, or design. Return one word.", "auth"),
    Case("guardrail", "Can an agent touch personal Todoist? Return exactly NO.", "NO"),
    Case("source-truth", "For memory canonical source choose one: Obsidian, OpenClaw sqlite, random chat. Return one.", "Obsidian"),
    Case("urgent-terms", "Return exactly URGENT if text has 'prod down now': prod down now", "URGENT"),
    Case("nonurgent", "Return exactly HOLD if text is nonurgent late-night brainstorming.", "HOLD"),
    Case("route-model", "Return exactly deepseek-v4-flash for cheap minion work.", "deepseek-v4-flash"),
    Case("grok-role", "Return exactly second-opinion for Grok's routine role.", "second-opinion"),
    Case("satory", "Return exactly BDL+Cerebro for 'replace BigDataLab and Cerebro'.", "BDL+Cerebro"),
    Case("musk-step", "Musk algorithm step before simplify? Return exactly delete.", "delete"),
    Case("skillify", "When a repeated failure is fixed, return exactly SKILL.md+timeline.", "SKILL.md+timeline"),
]


def load_env_files() -> None:
    for path in ENV_FILES:
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def score(case: Case, text: str) -> bool:
    got = text.strip()
    if case.kind == "exact":
        return got == case.expect
    if case.kind == "contains":
        return case.expect in got
    if case.kind == "regex":
        return re.search(case.expect, got) is not None
    if case.kind == "json_exact":
        try:
            return json.loads(got) == json.loads(case.expect)
        except json.JSONDecodeError:
            return False
    raise ValueError(f"unknown case kind: {case.kind}")


def call_model(base_url: str, master_key: str, model: str, prompt: str, timeout: int, max_tokens: int) -> tuple[str, int, str]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are running a deterministic routing bakeoff. Follow the user's output format exactly.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {master_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = int((time.monotonic() - start) * 1000)
            content = body["choices"][0]["message"].get("content") or ""
            return content, elapsed_ms, ""
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return "", elapsed_ms, f"HTTP {exc.code}: {detail}"
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return "", elapsed_ms, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated LiteLLM model aliases")
    parser.add_argument("--base-url", default=os.environ.get("LITELLM_CHAT_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Completion-token cap. Must be high enough for reasoning-token models to reach final content.",
    )
    parser.add_argument("--output", default="")
    parser.add_argument("--max-cases", type=int, default=len(CASES))
    args = parser.parse_args()

    load_env_files()
    master_key = os.environ.get("LITELLM_MASTER_KEY")
    if not master_key:
        raise SystemExit("LITELLM_MASTER_KEY missing; run on Air or source ~/nous-agaas/litellm/.env")

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    cases = CASES[: args.max_cases]
    results = []

    for model in models:
        for case in cases:
            text, latency_ms, error = call_model(args.base_url, master_key, model, case.prompt, args.timeout, args.max_tokens)
            passed = False if error else score(case, text)
            results.append(
                {
                    "model": model,
                    "case_id": case.case_id,
                    "passed": passed,
                    "latency_ms": latency_ms,
                    "error": error,
                    "expected": case.expect,
                    "got": text.strip()[:200],
                }
            )

    summary = {}
    for model in models:
        rows = [r for r in results if r["model"] == model]
        passed = sum(1 for r in rows if r["passed"])
        errors = sum(1 for r in rows if r["error"])
        latencies = sorted(r["latency_ms"] for r in rows)
        summary[model] = {
            "passed": passed,
            "total": len(rows),
            "pass_rate": round(passed / len(rows) * 100, 1) if rows else 0,
            "errors": errors,
            "p50_latency_ms": latencies[len(latencies) // 2] if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
        }

    report = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": args.base_url,
        "case_count": len(cases),
        "max_tokens": args.max_tokens,
        "summary": summary,
        "results": results,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
