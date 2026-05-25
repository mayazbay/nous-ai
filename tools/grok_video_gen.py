#!/usr/bin/env python3
"""grok_video_gen.py — xAI Imagine video generation adapter (async polling).

Wraps POST https://api.x.ai/v1/videos/generations + GET https://api.x.ai/v1/videos/{id}
with:
  - cost-gate against XAI_DAILY_CAP_USD + XAI_VIDEO_PER_CALL_CAP
  - Subscription-First amendment (NOUS_PAID_API_ALLOWED=1 required for live runs)
  - async polling every 5s, 10min wallclock cap (AP-3: never poll indefinitely)
  - text-to-video AND image-to-video (image= URL or local path; local files inlined as data URL)
  - artifact landing under pages/inbox/grok-videos/YYYY-MM-DD/<hash>.url.txt (URL pointer)
  - structured JSON output for downstream Telegram replies

CLI:
  python3 tools/grok_video_gen.py --prompt "A rocket launching at sunrise" --duration 10
  python3 tools/grok_video_gen.py --prompt "make this still photo come alive" --image https://...png
  python3 tools/grok_video_gen.py --prompt "..." --aspect 16:9 --resolution 720p --dry-run

Doctrine refs: pages/skills/xai-premium-tools/SKILL.md v1.0.0 (AP-1, AP-3, AP-4, AP-6).
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ALMATY = dt.timezone(dt.timedelta(hours=5))

XAI_GEN_ENDPOINT = "https://api.x.ai/v1/videos/generations"
XAI_POLL_ENDPOINT = "https://api.x.ai/v1/videos/{request_id}"
DEFAULT_MODEL = "grok-imagine-video"

XAI_DAILY_CAP_USD = float(os.environ.get("XAI_DAILY_CAP_USD", "5.00"))
PER_CALL_CAP_USD = float(os.environ.get("XAI_VIDEO_PER_CALL_CAP", "0.50"))
ESTIMATED_COST_PER_SECOND_USD = 0.04  # placeholder until Madi confirms billing
DEFAULT_DURATION_S = 5
MIN_DURATION_S = 1
MAX_DURATION_S = 15
REQUEST_TIMEOUT_S = 60
POLL_INTERVAL_S = 5
POLL_WALLCLOCK_CAP_S = 600  # 10 minutes per AP-3
ALLOWED_RESOLUTIONS = {"720p", "480p"}
ALLOWED_ASPECTS = {"16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"}

LEDGER_REL = Path("pages/systems/xai-premium-ledger.jsonl")
INBOX_DIR_REL = Path("pages/inbox/grok-videos")

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
        if row.get("ts", "").startswith(today):
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
            f"AP-1 gate: estimated cost ${est_cost:.4f} > XAI_VIDEO_PER_CALL_CAP "
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


def _image_to_data_url(image: str) -> str:
    if image.startswith(("http://", "https://", "data:")):
        return image
    path = Path(image).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"--image path not found: {image}")
    mime, _ = mimetypes.guess_type(path.name)
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _submit(prompt: str, model: str, duration: int, aspect_ratio: str | None,
            resolution: str | None, image: str | None, api_key: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
    }
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    if resolution:
        body["resolution"] = resolution
    if image:
        body["image"] = _image_to_data_url(image)
    req = Request(
        XAI_GEN_ENDPOINT,
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


def _poll(request_id: str, api_key: str, wallclock_cap_s: int = POLL_WALLCLOCK_CAP_S) -> dict[str, Any]:
    deadline = time.monotonic() + wallclock_cap_s
    url = XAI_POLL_ENDPOINT.format(request_id=request_id)
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        req = Request(url, headers={"Authorization": f"Bearer {api_key}"})
        try:
            with urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
                last = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            return {"_error": f"HTTP {exc.code}", "_body": exc.read().decode("utf-8", "replace")[:600]}
        except URLError as exc:
            return {"_error": f"URL error: {exc}"}
        status = last.get("status")
        if status in {"done", "failed", "expired"}:
            return last
        time.sleep(POLL_INTERVAL_S)
    last["_error"] = f"poll wallclock cap {wallclock_cap_s}s exceeded (AP-3)"
    return last


def _save_artifact(vault: Path, prompt: str, video_url: str | None) -> str | None:
    if not video_url:
        return None
    out_dir = vault / INBOX_DIR_REL / _today_almaty()
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(
        (prompt + dt.datetime.now(ALMATY).isoformat()).encode("utf-8")
    ).hexdigest()[:10]
    path = out_dir / f"{digest}.url.txt"
    path.write_text(video_url, encoding="utf-8")
    return str(path.relative_to(vault))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_S)
    parser.add_argument("--aspect", dest="aspect_ratio", default=None,
                        help=f"one of {sorted(ALLOWED_ASPECTS)}")
    parser.add_argument("--resolution", default=None,
                        help=f"one of {sorted(ALLOWED_RESOLUTIONS)}")
    parser.add_argument("--image", default=None,
                        help="URL or local path for image-to-video")
    parser.add_argument("--poll-cap", type=int, default=POLL_WALLCLOCK_CAP_S)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.duration < MIN_DURATION_S or args.duration > MAX_DURATION_S:
        print(f"--duration must be in [{MIN_DURATION_S},{MAX_DURATION_S}]", file=sys.stderr)
        return 2
    if args.aspect_ratio and args.aspect_ratio not in ALLOWED_ASPECTS:
        print(f"--aspect must be one of {sorted(ALLOWED_ASPECTS)}", file=sys.stderr)
        return 2
    if args.resolution and args.resolution not in ALLOWED_RESOLUTIONS:
        print(f"--resolution must be one of {sorted(ALLOWED_RESOLUTIONS)}", file=sys.stderr)
        return 2

    vault = _vault_root()
    est_cost = ESTIMATED_COST_PER_SECOND_USD * args.duration
    _gate_or_die(vault, est_cost, args.dry_run)

    if args.dry_run:
        result = {
            "ok": True,
            "dry_run": True,
            "model": args.model,
            "duration": args.duration,
            "estimated_cost_usd": est_cost,
            "today_spend_so_far_usd": _ledger_today_spend(vault),
            "daily_cap_usd": XAI_DAILY_CAP_USD,
            "poll_cap_s": args.poll_cap,
        }
        print(json.dumps(result, indent=2 if args.json else None))
        return 0

    api_key = _fetch_env_var("XAI_API_KEY")
    if not api_key:
        print("XAI_API_KEY not resolvable", file=sys.stderr)
        return 1

    started = dt.datetime.now(ALMATY)
    submit = _submit(
        args.prompt, args.model, args.duration,
        args.aspect_ratio, args.resolution, args.image, api_key,
    )
    if "_error" in submit:
        finished = dt.datetime.now(ALMATY)
        latency_ms = int((finished - started).total_seconds() * 1000)
        prompt_hash = hashlib.sha256(args.prompt.encode("utf-8")).hexdigest()[:12]
        _ledger_append(vault, {
            "ts": started.isoformat(),
            "tool": "grok_video_gen",
            "model": args.model,
            "duration_s": args.duration,
            "prompt_hash": prompt_hash,
            "cost_usd": 0.0,
            "latency_ms": latency_ms,
            "artifact": None,
            "ok": False,
            "error": submit["_error"],
        })
        print(json.dumps({"ok": False, "stage": "submit", "error": submit["_error"]},
                         indent=2 if args.json else None))
        return 3

    request_id = submit.get("request_id")
    if not request_id:
        print(json.dumps({"ok": False, "stage": "submit", "error": "no request_id in response",
                          "raw": submit}, indent=2 if args.json else None))
        return 3

    poll_result = _poll(request_id, api_key, wallclock_cap_s=args.poll_cap)
    finished = dt.datetime.now(ALMATY)
    latency_ms = int((finished - started).total_seconds() * 1000)
    status = poll_result.get("status")
    video = poll_result.get("video") or {}
    video_url = video.get("url")

    ok = status == "done" and bool(video_url) and "_error" not in poll_result
    artifact = _save_artifact(vault, args.prompt, video_url) if ok else None
    prompt_hash = hashlib.sha256(args.prompt.encode("utf-8")).hexdigest()[:12]

    _ledger_append(vault, {
        "ts": started.isoformat(),
        "tool": "grok_video_gen",
        "model": args.model,
        "duration_s": args.duration,
        "prompt_hash": prompt_hash,
        "cost_usd": est_cost if ok else 0.0,
        "latency_ms": latency_ms,
        "request_id": request_id,
        "status": status,
        "artifact": artifact,
        "ok": ok,
        "error": poll_result.get("_error") or (poll_result.get("error") or {}).get("message"),
    })

    result = {
        "ok": ok,
        "request_id": request_id,
        "status": status,
        "video_url": video_url,
        "artifact": artifact,
        "model": args.model,
        "duration_s": args.duration,
        "cost_usd_est": est_cost if ok else 0.0,
        "latency_ms": latency_ms,
    }
    if not ok:
        result["error"] = poll_result.get("_error") or (poll_result.get("error") or {}).get("message")
    print(json.dumps(result, indent=2 if args.json else None))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
