#!/usr/bin/env python3
"""One-shot resolver for Subgroup E tasks (#11 and #14) after Madi clarification.

#11 (Карта 243 камеры GPS): post resolution comment (target=243, current=12).
#14 (Автоматические тесты Playwright): create new task for Satory client
    Playwright test infra; post resolution comment on #14 referencing the new
    task. Madi answer 2026-05-14: "New initiative — build Playwright test
    infra for Satory client site".

Idempotent: skips comments that already match the resolution marker.

Usage:
  python3 tools/todoist_resolve_subgroup_e.py --env-file /Users/madia/nous-agaas/.env --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

TODOIST_BASE = "https://api.todoist.com/api/v1"
PROJECT_ID = "6gJ5j8PRVVCWpgCq"
SECTION_14 = "6gJ9Mh5QmGQC9xCq"  # ⚙️ Фабрика

TASK_11 = "6gJ9MpXpWgHMWVwq"  # Карта 243 камеры GPS
TASK_14 = "6gJ9Mq4XQp536PvH"  # Автоматические тесты Playwright

MARKER = "Источник: source-finder UPDATE 2026-05-14"

COMMENT_11 = (
    "Источник: source-finder UPDATE 2026-05-14 (Мади clarification).\n\n"
    "ЦЕЛЬ (target): 243 камеры GPS — это будущее покрытие deployment.\n"
    "ТЕКУЩЕЕ (current): ~12 active camera deployments в VKO region per Notion "
    "«🏢 SATORY GROUP» (https://www.notion.so/2b1cb8f8c69f8150a79df8c404f0a445).\n\n"
    "Маршрут: source_backed_future. Задача остаётся актуальной — это roadmap to 243.\n"
    "Доктрина (todoist-control-plane v1.7.1): источник зафиксирован, target/current разнесены явно."
)

NEW_TASK_CONTENT = "Satory client Playwright test infrastructure (E2E + per-page render verification)"
NEW_TASK_DESCRIPTION = (
    "Build Playwright test infrastructure for satory.nousagaas.com — per-page render "
    "verification (9 routes), interactive flow tests (login, dashboard load, camera "
    "list, map render), responsive layouts. Distinct from tools/weekly_library_canary.sh "
    "(vault-side smoke). Scope: client portal only. Resolves and supersedes parent task "
    "#14 (Автоматические тесты Playwright). Owner: AI-фабрика."
)
NEW_TASK_LABELS = [
    "исполнитель:AI-фабрика",
    "отдел:AI-фабрика",
    "project:satory",
    "priority:p3",
    "route:source_backed_new_initiative",
    "parent-of:6gJ9Mq4XQp536PvH",
]


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_token(env_file: Path) -> str:
    env = {**load_env(env_file), **os.environ}
    return env.get("SATORY_TODOIST_TOKEN") or env.get("TODOIST_API_TOKEN") or ""


def list_comments(token: str, task_id: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    out = []
    cursor = None
    while True:
        params = {"task_id": task_id}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{TODOIST_BASE}/comments", headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("results", []))
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return out


def post_comment(token: str, task_id: str, body: str) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(
        f"{TODOIST_BASE}/comments",
        headers=headers,
        json={"task_id": task_id, "content": body},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def create_task(token: str, payload: dict) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(f"{TODOIST_BASE}/tasks", headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def already_resolved(comments: list[dict]) -> bool:
    return any((c.get("content") or "").startswith(MARKER) for c in comments)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("/Users/madia/nous-agaas/.env"),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.apply and not args.dry_run:
        print("ERROR: pass --apply OR --dry-run", file=sys.stderr)
        return 2

    token = get_token(args.env_file)
    if not token:
        print(f"ERROR: no token in {args.env_file}", file=sys.stderr)
        return 2

    result: dict = {"mode": "apply" if args.apply else "dry-run", "actions": []}

    # Phase 11 — comment on #11
    c11 = list_comments(token, TASK_11)
    if already_resolved(c11):
        result["actions"].append({"task": TASK_11, "result": "skipped_idempotent"})
    elif args.apply:
        resp = post_comment(token, TASK_11, COMMENT_11)
        result["actions"].append({"task": TASK_11, "result": "comment_posted", "id": resp.get("id")})
    else:
        result["actions"].append({"task": TASK_11, "result": "would_comment", "preview": COMMENT_11[:120]})

    # Phase 12a — create new Playwright task
    new_task_payload = {
        "content": NEW_TASK_CONTENT,
        "description": NEW_TASK_DESCRIPTION,
        "project_id": PROJECT_ID,
        "section_id": SECTION_14,
        "labels": NEW_TASK_LABELS,
        "priority": 3,
    }
    new_task_id = None
    if args.apply:
        # Check if a similar task already exists to avoid dupes
        headers = {"Authorization": f"Bearer {token}"}
        existing = requests.get(
            f"{TODOIST_BASE}/tasks",
            headers=headers,
            params={"project_id": PROJECT_ID, "section_id": SECTION_14},
            timeout=30,
        )
        existing.raise_for_status()
        existing_tasks = existing.json().get("results", [])
        dup = next((t for t in existing_tasks if t.get("content") == NEW_TASK_CONTENT), None)
        if dup:
            new_task_id = dup.get("id")
            result["actions"].append({"task": "NEW_PLAYWRIGHT", "result": "skipped_dup_exists", "id": new_task_id})
        else:
            created = create_task(token, new_task_payload)
            new_task_id = created.get("id")
            result["actions"].append({"task": "NEW_PLAYWRIGHT", "result": "created", "id": new_task_id})
    else:
        result["actions"].append({
            "task": "NEW_PLAYWRIGHT",
            "result": "would_create",
            "preview": NEW_TASK_CONTENT,
        })

    # Phase 12b — comment on #14
    c14 = list_comments(token, TASK_14)
    comment_14 = (
        f"Источник: source-finder UPDATE 2026-05-14 (Мади clarification).\n\n"
        f"Scope: новая инициатива — Playwright test infrastructure для Satory client "
        f"сайта (satory.nousagaas.com). НЕ дубликат tools/weekly_library_canary.sh "
        f"(которая покрывает vault-side smoke).\n\n"
        f"Создан follow-up task: {new_task_id or '(dry-run, not created)'} — "
        f"«{NEW_TASK_CONTENT}».\n\n"
        f"Маршрут: source_backed_new_initiative. Доктрина (todoist-control-plane v1.7.1): "
        f"scope-clarification получен от Мади, source = новый child task с детальным описанием."
    )
    if already_resolved(c14):
        result["actions"].append({"task": TASK_14, "result": "skipped_idempotent"})
    elif args.apply:
        resp = post_comment(token, TASK_14, comment_14)
        result["actions"].append({"task": TASK_14, "result": "comment_posted", "id": resp.get("id")})
    else:
        result["actions"].append({"task": TASK_14, "result": "would_comment", "preview": comment_14[:120]})

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
