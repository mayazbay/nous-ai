#!/usr/bin/env python3
"""grok_image_gen.py — xAI Imagine image generation adapter for the Nous factory.

Wraps POST https://api.x.ai/v1/images/generations with:
  - cost-gate against XAI_DAILY_CAP_USD (default $5/day) using pages/systems/xai-premium-ledger.jsonl
  - Subscription-First amendment: fail-closed unless NOUS_PAID_API_ALLOWED=1
  - deprecation alarm: refuses grok-imagine-image-pro (deprecated 2026-05-15 per xai-premium-tools AP-2)
  - lazy env resolution (env var first, then ~/nous-agaas/.env via local read or ssh air)
  - artifact landing under pages/inbox/grok-images/YYYY-MM-DD/<hash>.{png,b64.txt}
  - structured JSON output for downstream Telegram replies

CLI:
  python3 tools/grok_image_gen.py --prompt "A neon city skyline at dusk"
  python3 tools/grok_image_gen.py --prompt "..." --aspect 16:9 --n 2 --response-format url
  python3 tools/grok_image_gen.py --prompt "..." --dry-run

Doctrine refs: pages/skills/xai-premium-tools/SKILL.md v1.0.0 (AP-1..AP-6).
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ALMATY = dt.timezone(dt.timedelta(hours=5))

XAI_ENDPOINT = "https://api.x.ai/v1/images/generations"
DEFAULT_MODEL = "grok-imagine-image-quality"
DEPRECATED_MODELS = {"grok-imagine-image-pro"}  # deprecated 2026-05-15

XAI_DAILY_CAP_USD = float(os.environ.get("XAI_DAILY_CAP_USD", "5.00"))
PER_CALL_CAP_USD = float(os.environ.get("XAI_IMAGE_PER_CALL_CAP", "0.10"))
ESTIMATED_COST_PER_IMAGE_USD = 0.04  # placeholder until Madi confirms billing rate
REQUEST_TIMEOUT_S = 60

LEDGER_REL = Path("pages/systems/xai-premium-ledger.jsonl")
INBOX_DIR_REL = Path("pages/inbox/grok-images")

AIR_HOST = "air"
AIR_ENV_FILE = "~/nous-agaas/.env"


def _vault_root() -> Path:
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    tool_root = Path(__file__).resolve().parents[1]
    if (tool_root / "pages").exists():
        return tool_root
    return Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")


def _fetch_env_var(name: str) -> str:
    val = os.environ.get(name)
    if val:
        return val
    local_env = Path.home() / "nous-agaas" / ".env"
    if local_env.exists():
        for line in local_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    try:
        proc = subprocess.run(
            ["ssh", AIR_HOST, f"grep ^{name}= {AIR_ENV_FILE} | head -1"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and "=" in proc.stdout:
            return proc.stdout.strip().split("=", 1)[1].strip().strip("'\"")
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return ""


def _today_almaty() -> str:
    return dt.datetime.now(ALMATY).strftime("%Y-%m-%d")


def _ledger_today_spend(vault: Path) -> float:
    ledger = vault / LEDGER_REL
    if not ledger.exists():
        return 0.0
    today = _today_almaty()
    total = 0.0
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not row.get("ok"):
            continue
        ts = row.get("ts", "")
        if ts.startswith(today):
            total += float(row.get("cost_usd") or 0.0)
    return total


def _ledger_append(vault: Path, row: dict[str, Any]) -> None:
    ledger = vault / LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _gate_or_die(vault: Path, est_cost: float, dry_run: bool) -> None:
    if est_cost > PER_CALL_CAP_USD:
        raise SystemExit(
            f"AP-1 gate: estimated cost ${est_cost:.4f} > XAI_IMAGE_PER_CALL_CAP "
            f"${PER_CALL_CAP_USD:.2f}. Refusing."
        )
    today_spend = _ledger_today_spend(vault)
    if (today_spend + est_cost) > XAI_DAILY_CAP_USD:
        raise SystemExit(
            f"AP-1 gate: today's xAI spend ${today_spend:.4f} + this call ${est_cost:.4f} "
            f"would exceed XAI_DAILY_CAP_USD ${XAI_DAILY_CAP_USD:.2f}. Refusing."
        )
    if dry_run:
        return
    if os.environ.get("NOUS_PAID_API_ALLOWED") != "1":
        raise SystemExit(
            "AP-6 gate: NOUS_PAID_API_ALLOWED != '1'. Set NOUS_PAID_API_ALLOWED=1 + "
            "NOUS_PAID_API_CAP_USD + NOUS_PAID_API_REASON, or use --dry-run."
        )


def _post(prompt: str, model: str, n: int, aspect_ratio: str | None,
          resolution: str | None, response_format: str, api_key: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "response_format": response_format,
    }
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    if resolution:
        body["resolution"] = resolution
    req = Request(
        XAI_ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return {"_error": f"HTTP {exc.code}", "_body": exc.read().decode("utf-8", "replace")[:600]}
    except URLError as exc:
        return {"_error": f"URL error: {exc}"}


def _save_artifacts(vault: Path, prompt: str, payload: dict[str, Any]) -> list[str]:
    out_dir = vault / INBOX_DIR_REL / _today_almaty()
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    data = payload.get("data") or []
    for idx, item in enumerate(data):
        digest = hashlib.sha256(
            (prompt + str(idx) + dt.datetime.now(ALMATY).isoformat()).encode("utf-8")
        ).hexdigest()[:10]
        if "b64_json" in item and item["b64_json"]:
            path = out_dir / f"{digest}.png"
            try:
                path.write_bytes(base64.b64decode(item["b64_json"]))
                saved.append(str(path.relative_to(vault)))
            except (ValueError, OSError) as exc:
                saved.append(f"<b64-decode-failed:{exc}>")
        elif "url" in item and item["url"]:
            path = out_dir / f"{digest}.url.txt"
            path.write_text(item["url"], encoding="utf-8")
            saved.append(str(path.relative_to(vault)))
    return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--aspect", dest="aspect_ratio", default=None,
                        help="e.g. 16:9, 1:1, 9:16")
    parser.add_argument("--resolution", default=None, help="e.g. 1024x1024")
    parser.add_argument("--response-format", default="b64_json", choices=["b64_json", "url"])
    parser.add_argument("--dry-run", action="store_true",
                        help="cost-gate + key-check only, no HTTP call")
    parser.add_argument("--json", action="store_true", help="print full JSON output")
    args = parser.parse_args(argv)

    if args.model in DEPRECATED_MODELS:
        print(
            f"AP-2 alarm: model {args.model!r} deprecated 2026-05-15. Use "
            f"{DEFAULT_MODEL!r}. Refusing.",
            file=sys.stderr,
        )
        return 2

    vault = _vault_root()
    est_cost = ESTIMATED_COST_PER_IMAGE_USD * args.n
    _gate_or_die(vault, est_cost, args.dry_run)

    if args.dry_run:
        result = {
            "ok": True,
            "dry_run": True,
            "model": args.model,
            "estimated_cost_usd": est_cost,
            "today_spend_so_far_usd": _ledger_today_spend(vault),
            "daily_cap_usd": XAI_DAILY_CAP_USD,
        }
        print(json.dumps(result, indent=2 if args.json else None))
        return 0

    api_key = _fetch_env_var("XAI_API_KEY")
    if not api_key:
        print("XAI_API_KEY not resolvable (env, local ~/nous-agaas/.env, or ssh air)", file=sys.stderr)
        return 1

    started = dt.datetime.now(ALMATY)
    payload = _post(
        args.prompt, args.model, args.n,
        args.aspect_ratio, args.resolution, args.response_format, api_key,
    )
    finished = dt.datetime.now(ALMATY)
    latency_ms = int((finished - started).total_seconds() * 1000)

    ok = "_error" not in payload
    saved = _save_artifacts(vault, args.prompt, payload) if ok else []
    prompt_hash = hashlib.sha256(args.prompt.encode("utf-8")).hexdigest()[:12]
    row = {
        "ts": started.isoformat(),
        "tool": "grok_image_gen",
        "model": args.model,
        "n": args.n,
        "prompt_hash": prompt_hash,
        "cost_usd": est_cost if ok else 0.0,
        "latency_ms": latency_ms,
        "artifacts": saved,
        "ok": ok,
        "error": payload.get("_error") if not ok else None,
    }
    _ledger_append(vault, row)

    result = {
        "ok": ok,
        "model": args.model,
        "prompt_hash": prompt_hash,
        "artifacts": saved,
        "cost_usd_est": est_cost,
        "latency_ms": latency_ms,
        "error": payload.get("_error"),
    }
    print(json.dumps(result, indent=2 if args.json else None))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
