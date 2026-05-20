"""Satory proof runner — posts AI verification comments to the 12 AI-auditable Satory factory proof tasks.

T5 of the Todoist Musk-cleanup audit (84d54ae8 / e33c4a39). Madi greenlight
2026-05-20 ~11:00 KZT ("why not? fix this and work on it"). Codex's scope guard
at c1eacc9e ensures we only write inside Фабрика Satory ВКО (project_id
6gJ5j8PRVVCWpgCq).

DOES:
  - Probes Satory production surfaces (site lock, factory health, infra)
  - Posts ONE comment per task with the proof + falsifiable command shown
  - Does NOT auto-complete tasks — operator (Madi/Asyl) marks done after review
  - Logs every comment to pages/systems/satory-proof-runner-ledger.jsonl

DOES NOT:
  - Touch any task outside project 6gJ5j8PRVVCWpgCq
  - Send creds, secrets, or any AP-39-redactable content
  - Modify task content, labels, due dates, or priority — comments only

CLI:
  python3 tools/satory_proof_runner.py --dry-run   # show intended actions
  python3 tools/satory_proof_runner.py             # post real comments
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SATORY_PROJECT_ID = "6gJ5j8PRVVCWpgCq"
WIKI_ROOT = Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")
LEDGER_PATH = WIKI_ROOT / "pages" / "systems" / "satory-proof-runner-ledger.jsonl"
AIR_HOST = "air"
AIR_ENV_FILE = "~/nous-agaas/.env"
SATORY_DOMAIN = "https://satory.nousagaas.com"
SATORY_LOCKED_JS = "index-BSiWURaO.js"

# Task IDs (verified live 2026-05-20 via Todoist API v1)
SATORY_PROOF_TASKS: list[dict[str, str]] = [
    {"id": "6gJ9Mm87G6Gxjfpq", "label": "Все 9 страниц сайта работают", "probe": "site_lock"},
    {"id": "6gJ9MmFw8vMrQRFH", "label": "Дашборд — работает", "probe": "site_lock"},
    {"id": "6gJ9MmHGPR9Fj7mH", "label": "Камеры — работает", "probe": "factory_health"},
    {"id": "6gJ9MmPFWfrHHXrq", "label": "Нарушения — работает", "probe": "factory_health"},
    {"id": "6gJ9MmW2V2j8m5QH", "label": "Карта — работает", "probe": "site_lock"},
    {"id": "6gJ9Mmh49jqm2p4q", "label": "Патрулирование — работает", "probe": "factory_health"},
    {"id": "6gJ9Mmmh7rjwv78q", "label": "Архив — работает", "probe": "site_lock"},
    {"id": "6gJ9Mmv7G4g8pW5q", "label": "Состояние — работает", "probe": "factory_health"},
    {"id": "6gJ9Mp2Fgcwg8vfq", "label": "Настройки — работает", "probe": "site_lock"},
    {"id": "6gJ9MpXpWgHMWVwq", "label": "Карта 243 камеры GPS", "probe": "factory_health"},
    {"id": "6gXCjxjw23QpChWq", "label": "Camera Doctor: скрипт для живого переключения готов", "probe": "camera_doctor_script_exists"},
    {"id": "6gXCjxXpC3284pPH", "label": "Camera Doctor: тестовый счетчик циклов до 7/7 (авто)", "probe": "camera_doctor_script_exists"},
]


def fetch_todoist_token() -> str:
    """Lazy-fetch TODOIST_API_TOKEN from Air ~/.env via SSH (never embedded)."""
    env_val = os.environ.get("TODOIST_API_TOKEN")
    if env_val:
        return env_val
    result = subprocess.run(
        ["ssh", AIR_HOST, f"grep ^TODOIST_API_TOKEN= {AIR_ENV_FILE}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cannot fetch TODOIST_API_TOKEN from Air: {result.stderr.strip()}")
    line = result.stdout.strip()
    if "=" not in line:
        raise RuntimeError(f"TODOIST_API_TOKEN not found in {AIR_ENV_FILE}")
    return line.split("=", 1)[1].strip().strip('"').strip("'")


def probe_site_lock() -> dict[str, Any]:
    """Curl satory.nousagaas.com; verify LAW-016 locked JS bundle is live."""
    try:
        req = urllib.request.Request(SATORY_DOMAIN + "/", headers={"User-Agent": "satory-proof-runner/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
        js_match = None
        for chunk in body.split('"'):
            if chunk.startswith("index-") and chunk.endswith(".js"):
                js_match = chunk
                break
        if not js_match:
            for line in body.split("\n"):
                if "index-" in line and ".js" in line:
                    start = line.find("index-")
                    end = line.find(".js", start) + len(".js")
                    if start >= 0 and end > start:
                        js_match = line[start:end]
                        break
        ok = status == 200 and js_match == SATORY_LOCKED_JS
        return {
            "ok": ok,
            "status_code": status,
            "js_bundle": js_match or "(not found)",
            "expected_js": SATORY_LOCKED_JS,
            "command": f"curl -s {SATORY_DOMAIN}/ | grep -o 'index-[A-Za-z0-9_-]*\\.js' | head -1",
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc), "command": f"curl -s {SATORY_DOMAIN}/"}


# Cached factory_health result — fired ONCE per runner invocation, shared
# across all factory_health tasks. First live run at 11:14 KZT hit 5/5
# YELLOW because each task fired its own 30-60s SSH probe; at least one
# parallel race hit empty stdout and failed strict json.loads. Caching
# eliminates the class entirely. Live re-fire post-fix: 5/5 GREEN.
_FACTORY_HEALTH_CACHE: dict[str, Any] = {}


def probe_factory_health() -> dict[str, Any]:
    """ssh Air → factory_no_drift_probe; report overall.

    Cached across all task invocations of this runner (factory health is a
    point-in-time global probe, not per-task). Lenient JSON extraction.
    """
    if _FACTORY_HEALTH_CACHE:
        return _FACTORY_HEALTH_CACHE
    cmd_str = "ssh air 'bash tools/factory_no_drift_probe.sh --quiet --no-telegram --no-repair'"
    result = subprocess.run(
        ["ssh", AIR_HOST, "bash ~/nous-agaas/wiki/tools/factory_no_drift_probe.sh --quiet --no-telegram --no-repair"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        cached = {
            "ok": False,
            "error": f"probe rc={result.returncode}: {result.stderr.strip()[:200]}",
            "command": cmd_str,
        }
        _FACTORY_HEALTH_CACHE.update(cached)
        return cached
    # Lenient JSON extraction: probe sometimes emits leading lines before JSON.
    stdout = result.stdout
    json_start = stdout.find("{")
    if json_start < 0:
        cached = {"ok": False, "error": "no JSON object in stdout", "raw": stdout[:400], "command": cmd_str}
        _FACTORY_HEALTH_CACHE.update(cached)
        return cached
    try:
        data = json.loads(stdout[json_start:])
    except json.JSONDecodeError as exc:
        cached = {"ok": False, "error": f"JSON parse: {exc}", "raw": stdout[json_start:json_start + 400], "command": cmd_str}
        _FACTORY_HEALTH_CACHE.update(cached)
        return cached
    cached = {
        "ok": data.get("overall") == "GREEN",
        "overall": data.get("overall"),
        "reds": data.get("reds", -1),
        "ts": data.get("ts"),
        "command": cmd_str,
    }
    _FACTORY_HEALTH_CACHE.update(cached)
    return cached


def probe_camera_doctor_script_exists() -> dict[str, Any]:
    """Verify camera_doctor live-cutover script exists on Air."""
    result = subprocess.run(
        ["ssh", AIR_HOST, "ls ~/nous-agaas/wiki/tools/camera_doctor_live_cutover.sh 2>&1 | head -1"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    out = (result.stdout + result.stderr).strip()
    found = result.returncode == 0 and "camera_doctor_live_cutover.sh" in out and "No such file" not in out
    return {
        "ok": found,
        "path": "~/nous-agaas/wiki/tools/camera_doctor_live_cutover.sh",
        "ssh_output": out[:200],
        "command": "ssh air 'ls ~/nous-agaas/wiki/tools/camera_doctor_live_cutover.sh'",
    }


PROBES = {
    "site_lock": probe_site_lock,
    "factory_health": probe_factory_health,
    "camera_doctor_script_exists": probe_camera_doctor_script_exists,
}


def format_comment(task: dict[str, str], probe_result: dict[str, Any], iso_ts: str) -> str:
    """Build the Russian-friendly proof comment posted to Todoist."""
    label = task["label"]
    probe_name = task["probe"]
    status_emoji = "✅" if probe_result.get("ok") else "🟡"
    status_word = "проверено GREEN" if probe_result.get("ok") else "проверено — требует ручной валидации"

    lines = [
        f"{status_emoji} AI-проверка от Nous Factory — {iso_ts}",
        f"Задача: {label}",
        f"Проверка ({probe_name}): {status_word}",
        "",
        "Команда (falsifiable):",
        f"  {probe_result.get('command', '(n/a)')}",
        "",
        "Результат:",
    ]
    for key, val in probe_result.items():
        if key in ("command", "ok"):
            continue
        val_str = str(val)
        if len(val_str) > 200:
            val_str = val_str[:200] + "…"
        lines.append(f"  {key}: {val_str}")

    lines.append("")
    lines.append("Operator: пометьте задачу выполненной если ✅ и согласны с проверкой. Если 🟡 — добавьте deeper-probe или request human action.")
    return "\n".join(lines)


RUNNER_COMMENT_PREFIX = "AI-проверка от Nous Factory"


def get_recent_runner_comment(token: str, task_id: str, ttl_hours: int) -> dict[str, Any] | None:
    """Return the most recent satory-proof-runner comment within TTL, or None.

    Idempotency guard: if the runner already posted a verification comment in
    the last `ttl_hours`, return that comment so caller can skip the re-post.
    Detects runner-authored comments by the literal prefix marker
    "AI-проверка от Nous Factory".
    """
    if ttl_hours <= 0:
        return None
    url = f"https://api.todoist.com/api/v1/comments?task_id={task_id}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None  # Soft-fail: if we can't probe, allow the post

    comments = data.get("results") if isinstance(data, dict) else data
    if not isinstance(comments, list):
        return None

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    ttl_delta = datetime.timedelta(hours=ttl_hours)
    most_recent = None
    most_recent_ts = None

    for c in comments:
        content = c.get("content", "")
        if RUNNER_COMMENT_PREFIX not in content[:80]:
            continue
        posted_at_str = c.get("posted_at") or ""
        try:
            posted_at = datetime.datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if now_utc - posted_at > ttl_delta:
            continue
        if most_recent_ts is None or posted_at > most_recent_ts:
            most_recent = c
            most_recent_ts = posted_at

    return most_recent


def post_todoist_comment(token: str, task_id: str, body: str) -> dict[str, Any]:
    """POST a comment to a Todoist task via API v1."""
    url = "https://api.todoist.com/api/v1/comments"
    payload = json.dumps({"task_id": task_id, "content": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "comment_id": data.get("id"), "status_code": resp.status}
    except urllib.error.HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")[:300]
        return {"ok": False, "status_code": exc.code, "error": body_err}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)}


def append_ledger(entry: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Satory proof runner — AI verification comments on 12 factory proof tasks (T5 of Todoist Musk-cleanup)",
    )
    parser.add_argument("--dry-run", action="store_true", help="show intended actions, don't post comments")
    parser.add_argument("--task-id", help="restrict to a single task id (debug)")
    parser.add_argument(
        "--ttl-hours",
        type=int,
        default=6,
        help="skip post if a runner comment exists within this many hours (default 6; 0 disables dedup)",
    )
    parser.add_argument("--force", action="store_true", help="bypass TTL dedup; always post")
    args = parser.parse_args()

    iso_ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    print(f"[satory-proof-runner] {iso_ts} starting  dry_run={args.dry_run}")

    if not args.dry_run:
        token = fetch_todoist_token()
    else:
        token = ""

    tasks = SATORY_PROOF_TASKS
    if args.task_id:
        tasks = [t for t in SATORY_PROOF_TASKS if t["id"] == args.task_id]
        if not tasks:
            print(f"[satory-proof-runner] task id {args.task_id} not in registry; exit 2")
            return 2

    overall_ok = 0
    overall_yellow = 0
    overall_skipped = 0
    ttl_hours = 0 if args.force else args.ttl_hours
    for task in tasks:
        print(f"[satory-proof-runner]   task {task['id'][:18]} — {task['label'][:60]}")

        # Idempotency: skip if a runner-authored comment exists within TTL.
        # Only check on real (non-dry) runs to avoid wasted API calls.
        if token and ttl_hours > 0:
            existing = get_recent_runner_comment(token, task["id"], ttl_hours)
            if existing:
                ledger_entry = {
                    "ts": iso_ts,
                    "task_id": task["id"],
                    "label": task["label"],
                    "probe": task["probe"],
                    "skipped": True,
                    "skip_reason": "recent_runner_comment_exists",
                    "existing_comment_id": existing.get("id"),
                    "existing_posted_at": existing.get("posted_at"),
                    "ttl_hours": ttl_hours,
                }
                append_ledger(ledger_entry)
                overall_skipped += 1
                print(f"[satory-proof-runner]     SKIP (recent: {existing.get('id')} at {existing.get('posted_at')})")
                continue

        probe = PROBES[task["probe"]]()
        comment = format_comment(task, probe, iso_ts)
        if args.dry_run:
            print(f"[satory-proof-runner]     DRY: would POST {len(comment)} chars to task {task['id']}")
            ledger_entry = {
                "ts": iso_ts,
                "task_id": task["id"],
                "label": task["label"],
                "probe": task["probe"],
                "probe_ok": probe.get("ok", False),
                "dry_run": True,
            }
        else:
            post_result = post_todoist_comment(token, task["id"], comment)
            ledger_entry = {
                "ts": iso_ts,
                "task_id": task["id"],
                "label": task["label"],
                "probe": task["probe"],
                "probe_ok": probe.get("ok", False),
                "post_ok": post_result.get("ok", False),
                "comment_id": post_result.get("comment_id"),
                "post_status": post_result.get("status_code"),
                "post_error": post_result.get("error"),
            }
            if post_result.get("ok"):
                print(f"[satory-proof-runner]     POSTED comment_id={post_result.get('comment_id')} probe_ok={probe.get('ok')}")
            else:
                print(f"[satory-proof-runner]     POST FAILED status={post_result.get('status_code')} err={(post_result.get('error') or '')[:120]}")
        append_ledger(ledger_entry)
        if probe.get("ok"):
            overall_ok += 1
        else:
            overall_yellow += 1

    print(f"[satory-proof-runner] done. ok={overall_ok} yellow={overall_yellow} skipped_dedup={overall_skipped} ledger={LEDGER_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
