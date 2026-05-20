#!/usr/bin/env python3
"""Weekly cheap-pool winner picker for the Nous factory.

OpenRouter `/api/v1/models` currently exposes stable operational fields:
`id`, `name`, `context_length`, `pricing.prompt`, `pricing.completion`, and
`top_provider`. It does not expose one canonical quality score, so this tool
uses an explicit `quality`/`score`/`rank_score` field when present and otherwise
falls back to a conservative context-length capability proxy. Runtime quality is
kept out of this picker; the monthly benchmark validates real prompt quality.

The scheduled script drafts a proposal only. Manual approval can update the
ceo-hierarchy skill, but runtime rsync is opt-in so RULE ZERO gbrain/commit
evidence can land before production doctrine changes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import urllib.request
from typing import Any

import model_promotion_gate


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_ASK_LOG = Path("/Users/madia/nous-agaas/logs/ask-hierarchy.jsonl")
DEFAULT_POLICY = DEFAULT_WIKI / "tools/factory_orchestration_policy.py"
DEFAULT_FIXTURE = DEFAULT_WIKI / "pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl"
CHINESE_OS_MARKERS = (
    "deepseek",
    "qwen",
    "alibaba",
    "kimi",
    "moonshot",
    "glm",
    "z-ai",
    "zhipu",
    "baidu",
    "inclusionai",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_openrouter_models(url: str = OPENROUTER_MODELS_URL, timeout: int = 20) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def read_current_pin(policy_path: Path = DEFAULT_POLICY) -> str:
    if not policy_path.exists():
        return "deepseek-v4-flash"
    text = policy_path.read_text(encoding="utf-8")
    match = re.search(r'LONG_WORK_PRIMARY_MODEL\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "deepseek-v4-flash"


def normalize_model_alias(item: dict[str, Any]) -> str:
    raw = f"{item.get('id', '')} {item.get('name', '')}".lower()
    if "deepseek" in raw and "pro" in raw:
        return "deepseek-v4-pro"
    if "deepseek" in raw and "flash" in raw:
        return "deepseek-v4-flash"
    if "qwen" in raw and ("coder" in raw or "code" in raw):
        return "qwen3-coder-plus"
    if "qwen" in raw:
        return "qwen3"
    if "kimi" in raw or "moonshot" in raw:
        return "kimi-k2.6"
    if "glm" in raw and "5" in raw:
        return "glm-5.1"
    if "glm" in raw or "zhipu" in raw or "z-ai" in raw:
        return "glm-4.5-flash"
    slug = str(item.get("id") or item.get("name") or "unknown").split("/")[-1]
    return re.sub(r"[^a-z0-9._-]+", "-", slug.lower()).strip("-")


def is_chinese_open_source(item: dict[str, Any]) -> bool:
    raw = f"{item.get('id', '')} {item.get('name', '')} {item.get('description', '')}".lower()
    return any(marker in raw for marker in CHINESE_OS_MARKERS)


def price_per_token(item: dict[str, Any], key: str) -> float:
    try:
        return float((item.get("pricing") or {}).get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def quality_signal(item: dict[str, Any]) -> float:
    for key in ("quality", "score", "rank_score", "intelligence"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return max(0.0, float(value))
    context = item.get("context_length") or (item.get("top_provider") or {}).get("context_length") or 0
    try:
        return math.log10(max(float(context), 1.0)) / 6.0
    except (TypeError, ValueError):
        return 0.5


def extract_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for item in payload.get("data", []):
        if not is_chinese_open_source(item):
            continue
        prompt_price = price_per_token(item, "prompt")
        completion_price = price_per_token(item, "completion")
        candidates.append(
            {
                "model": normalize_model_alias(item),
                "openrouter_id": item.get("id"),
                "name": item.get("name") or item.get("id"),
                "prompt_price": prompt_price,
                "completion_price": completion_price,
                "blended_price": prompt_price + completion_price,
                "context_length": item.get("context_length") or (item.get("top_provider") or {}).get("context_length") or 0,
                "quality_raw": quality_signal(item),
            }
        )
    by_model: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        current = by_model.get(candidate["model"])
        if current is None or candidate["quality_raw"] > current["quality_raw"]:
            by_model[candidate["model"]] = candidate
    return list(by_model.values())


def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        parsed = dt.datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def read_runtime_stats(log_path: Path, *, now_iso: str | None = None, days: int = 7) -> dict[str, dict[str, float]]:
    now = parse_time(now_iso) if now_iso else dt.datetime.now(dt.timezone.utc)
    assert now is not None
    cutoff = now - dt.timedelta(days=days)
    rows_by_model: dict[str, list[dict[str, Any]]] = {}
    if not log_path.exists():
        return {}
    for raw in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        ts = parse_time(row.get("ts"))
        if ts and ts < cutoff:
            continue
        model = str(row.get("model") or "").strip()
        if not model:
            continue
        rows_by_model.setdefault(model, []).append(row)
    stats = {}
    for model, rows in rows_by_model.items():
        latencies = [float(r.get("latency_ms") or 0) for r in rows if r.get("latency_ms") is not None]
        decisions = [str(r.get("decision") or r.get("status") or "").lower() for r in rows]
        errors = sum(1 for value in decisions if any(token in value for token in ("error", "fail", "timeout", "red")))
        costs = [float(r.get("cost_est") or 0.0) for r in rows if r.get("cost_est") is not None]
        stats[model] = {
            "count": float(len(rows)),
            "p50_latency_ms": float(statistics.median(latencies)) if latencies else 6000.0,
            "error_rate": errors / len(rows) if rows else 0.05,
            "avg_cost": sum(costs) / len(costs) if costs else 0.0,
        }
    return stats


def _norm(value: float, max_value: float, default: float = 0.0) -> float:
    if max_value <= 0:
        return default
    return max(0.0, min(1.0, value / max_value))


def score_candidates(candidates: list[dict[str, Any]], stats: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    enriched = []
    for candidate in candidates:
        stat = stats.get(candidate["model"], {})
        price = float(candidate.get("blended_price") or 0.0)
        latency = float(stat.get("p50_latency_ms") or 6000.0)
        reliability = 1.0 - float(stat.get("error_rate", 0.05))
        enriched.append(
            {
                **candidate,
                "latency_ms": latency,
                "reliability": max(0.0, min(1.0, reliability)),
                "cost_raw": 1.0 / max(price, 1e-12),
                "latency_raw": 1.0 / max(latency, 1.0),
            }
        )
    max_quality = max((float(c["quality_raw"]) for c in enriched), default=1.0)
    max_cost = max((float(c["cost_raw"]) for c in enriched), default=1.0)
    max_latency = max((float(c["latency_raw"]) for c in enriched), default=1.0)
    for item in enriched:
        quality = _norm(float(item["quality_raw"]), max_quality)
        cost = _norm(float(item["cost_raw"]), max_cost)
        latency = _norm(float(item["latency_raw"]), max_latency)
        reliability = float(item["reliability"])
        item["score"] = round(0.4 * quality + 0.3 * cost + 0.2 * latency + 0.1 * reliability, 6)
    return sorted(enriched, key=lambda c: (c["score"], c["quality_raw"]), reverse=True)


def pick_winner(
    payload: dict[str, Any],
    *,
    current_model: str,
    ask_log: Path,
    now_iso: str | None = None,
    margin: float = 1.05,
) -> dict[str, Any]:
    candidates = extract_candidates(payload)
    stats = read_runtime_stats(ask_log, now_iso=now_iso)
    scored = score_candidates(candidates, stats)
    current = next((c for c in scored if c["model"] == current_model), None)
    if current is None:
        current = {"model": current_model, "score": 0.0, "name": current_model}
    winner = scored[0] if scored else current
    should = bool(scored) and winner["model"] != current_model and float(winner["score"]) > float(current["score"]) * margin
    return {
        "current": current,
        "winner": winner,
        "should_propose": should,
        "margin_required": margin,
        "candidates": scored,
        "generated_at": now_iso or dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def write_proposal(result: dict[str, Any], output_dir: Path, *, today: str | None = None) -> Path:
    day = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=5))).date().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"CHEAP-POOL-PROPOSAL-{day}.md"
    current = result["current"]
    winner = result["winner"]
    lines = [
        "---",
        "type: progress",
        f"id: CHEAP-POOL-PROPOSAL-{day}",
        f'title: "Cheap-pool proposal {day}"',
        f"date: {day}",
        "status: proposal",
        "tags: [model-rotation, cheap-pool, openrouter]",
        "---",
        "",
        f"# Cheap-pool proposal {day}",
        "",
        f"Current: `{current['model']}` score `{float(current.get('score', 0.0)):.4f}`.",
        f"Winner: `{winner['model']}` score `{float(winner.get('score', 0.0)):.4f}`.",
        "",
        "Promotion gate: before approval, run `tools/cheap_pool_benchmark.py --fixture pages/specs/benchmark-fixtures/nous-task-classes-2026-05-18.jsonl --json` and pass that JSON to `tools/model_promotion_gate.py`.",
        "Rule: metadata can nominate; only a real Satory/Nous fixture win can promote.",
        "",
        f"Approval command: `/approve cheap-pool {day}`",
        "",
        "| Model | Score | Price/token | P50 latency ms | Reliability |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in result.get("candidates", []):
        lines.append(
            f"| `{item['model']}` | {float(item.get('score', 0.0)):.4f} | "
            f"{float(item.get('blended_price') or 0.0):.12f} | {float(item.get('latency_ms') or 0):.0f} | "
            f"{float(item.get('reliability') or 0.0):.2f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def send_telegram(message: str, wiki: Path) -> dict[str, Any]:
    proc = subprocess.run(["bash", str(wiki / "tools/tg_send.sh"), message], cwd=str(wiki), capture_output=True, text=True)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def parse_approved_pair(proposal_path: Path) -> tuple[str, str]:
    text = proposal_path.read_text(encoding="utf-8", errors="replace")
    current = re.search(r"^Current:\s*`([^`]+)`", text, flags=re.MULTILINE)
    winner = re.search(r"^Winner:\s*`([^`]+)`", text, flags=re.MULTILINE)
    if not current or not winner:
        raise ValueError(f"could not parse current/winner from {proposal_path}")
    return current.group(1), winner.group(1)


def _bump_patch_version(text: str) -> tuple[str, str, str]:
    match = re.search(r"version:\s*(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        raise ValueError("ceo-hierarchy version field missing")
    old = ".".join(match.groups())
    new = f"{match.group(1)}.{match.group(2)}.{int(match.group(3)) + 1}"
    text = re.sub(r"version:\s*" + re.escape(old), f"version: {new}", text, count=1)
    text = text.replace(f'title: "ceo-hierarchy v{old}"', f'title: "ceo-hierarchy v{new}"', 1)
    text = text.replace(f"# ceo-hierarchy v{old}", f"# ceo-hierarchy v{new}", 1)
    return text, old, new


def apply_approved_pin(skill_path: Path, proposal_path: Path, *, today: str | None = None) -> bool:
    current, winner = parse_approved_pair(proposal_path)
    text = skill_path.read_text(encoding="utf-8")
    if f"Current cheap-pool pin: `{winner}`" in text:
        return False
    day = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=5))).date().isoformat()
    text, old_version, new_version = _bump_patch_version(text)
    pin_rule = (
        f"- Current cheap-pool pin: `{winner}`. Approved by weekly proposal over `{current}` on {day}; "
        "do not deploy future cheap-pool pin changes without a fresh `/approve cheap-pool` gate.\n"
    )
    text = text.replace("## Current rules (binding)\n\n", "## Current rules (binding)\n\n" + pin_rule, 1)
    timeline = (
        f"- **{day}** | v{old_version} -> v{new_version} -- cheap-pool pin `{winner}` approved over `{current}`. "
        "gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill\n"
    )
    if "## Timeline\n\n" in text:
        text = text.replace("## Timeline\n\n", "## Timeline\n\n" + timeline, 1)
    else:
        text += "\n## Timeline\n\n" + timeline
    skill_path.write_text(text, encoding="utf-8")
    return True


def rsync_ceo_hierarchy_to_air_runtime(wiki: Path, *, dry_run: bool = False) -> dict[str, Any]:
    source = str(wiki / "pages/skills/ceo-hierarchy/SKILL.md")
    commands = [
        ["rsync", "-az", source, "air:/Users/madia/nous-agaas/skills/ceo-hierarchy/SKILL.md"],
    ]
    if dry_run:
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": "dry-run: " + " && ".join(" ".join(cmd) for cmd in commands)}
    outputs = []
    for cmd in commands:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        outputs.append({"cmd": " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        if proc.returncode != 0:
            return {"ok": False, "returncode": proc.returncode, "outputs": outputs}
    return {"ok": True, "returncode": 0, "outputs": outputs}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--models-json", type=Path)
    parser.add_argument("--ask-log", type=Path, default=DEFAULT_ASK_LOG)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--skill-path", type=Path)
    parser.add_argument("--current-model")
    parser.add_argument("--margin", type=float, default=1.05)
    parser.add_argument("--today")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--approve-proposal", type=Path)
    parser.add_argument("--promotion-benchmark-json", type=Path)
    parser.add_argument("--promotion-fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--min-promotion-cases", type=int, default=5)
    parser.add_argument(
        "--rsync-air-runtime",
        action="store_true",
        help="Opt-in runtime rsync after approval. Use only after gbrain timeline + git commit discipline is satisfied.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.approve_proposal:
        skill_path = args.skill_path or args.wiki / "pages/skills/ceo-hierarchy/SKILL.md"
        if not args.promotion_benchmark_json:
            result = {
                "approved": False,
                "promotion_gate": {
                    "ok": False,
                    "reason": "--promotion-benchmark-json is required; no default-model approval without real fixture proof",
                },
            }
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["promotion_gate"]["reason"])
            return 1
        gate = model_promotion_gate.evaluate_promotion(
            proposal_path=args.approve_proposal,
            benchmark_json_path=args.promotion_benchmark_json,
            fixture_path=args.promotion_fixture,
            min_cases=args.min_promotion_cases,
        )
        if not gate["ok"]:
            result = {"approved": False, "promotion_gate": gate}
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else "promotion_gate=RED")
            return 1
        changed = apply_approved_pin(skill_path, args.approve_proposal, today=args.today)
        deploy = {
            "ok": True,
            "detail": "runtime rsync skipped; push gbrain timeline + commit the SKILL.md change before runtime deployment",
        }
        if changed and args.rsync_air_runtime:
            deploy = rsync_ceo_hierarchy_to_air_runtime(args.wiki, dry_run=args.dry_run)
        result = {
            "approved": changed,
            "promotion_gate": gate,
            "skill_path": str(skill_path),
            "runtime_rsync": deploy,
            "next": "mcp__gbrain__add_timeline_entry slug=pages/skills/ceo-hierarchy/skill, then commit with gbrain-timeline-ok evidence",
        }
        if not args.no_telegram and not args.dry_run:
            send_telegram(
                f"Cheap-pool approval applied from {args.approve_proposal.name}; "
                f"runtime_rsync={args.rsync_air_runtime} ok={deploy.get('ok')}",
                args.wiki,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"approved={changed} runtime_rsync_ok={deploy.get('ok')}")
        return 0 if deploy.get("ok") else 1

    payload = load_json(args.models_json) if args.models_json else fetch_openrouter_models()
    current = args.current_model or read_current_pin(args.policy)
    result = pick_winner(payload, current_model=current, ask_log=args.ask_log, margin=args.margin)
    proposal_path = None
    if result["should_propose"]:
        proposal_path = write_proposal(result, args.output_dir or args.wiki / "pages/progress", today=args.today)
        result["proposal_path"] = str(proposal_path)
        if not args.no_telegram and not args.dry_run:
            msg = (
                f"🟡 Cheap-pool weekly proposal: bump `{result['current']['model']}` -> "
                f"`{result['winner']['model']}`. Approval command: /approve cheap-pool {args.today or dt.date.today().isoformat()}"
            )
            result["telegram"] = send_telegram(msg, args.wiki)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"winner={result['winner']['model']} current={current} propose={result['should_propose']}")
        if proposal_path:
            print(f"proposal={proposal_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
