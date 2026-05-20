#!/usr/bin/env python3
"""Source-finder write-mode for the 26 Satory needs_source_enrichment tasks.

Posts one source-link comment per task per
[[AUDIT-satory-26-source-finder-dryrun-2026-05-14]].

Idempotent: skips any task that already has a comment starting with
`Источник: source-finder` (marker prefix).

Usage:
  python3 tools/todoist_source_finder.py --env-file ~/nous-agaas/.env --apply
  python3 tools/todoist_source_finder.py --env-file ~/nous-agaas/.env --dry-run

Doctrine: never fabricate sources. This script only posts comments backed by
real Notion pages or vault wikilinks. Two tasks (11, 14) are explicitly
flagged as "needs Madi clarification" — no fabricated source. See
todoist-control-plane v1.7.0 Source-Finder Loop section.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

TODOIST_BASE = "https://api.todoist.com/api/v1"
ALLOWED_PROJECT_ID = "6gJ5j8PRVVCWpgCq"
MARKER_PREFIX = "Источник: source-finder"


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def get_token(env_file: Path) -> str:
    env = {**load_env_file(env_file), **os.environ}
    token = env.get("SATORY_TODOIST_TOKEN") or env.get("TODOIST_API_TOKEN")
    if not token:
        raise RuntimeError("SATORY_TODOIST_TOKEN / TODOIST_API_TOKEN not found")
    return token


# Triage mapping per AUDIT-satory-26-source-finder-dryrun-2026-05-14.md
# Format: task_id -> (subgroup, source_body)
COMMENT_FOOTER = (
    "\n\nИсточник записан в коде: tools/todoist_source_finder.py + "
    "AUDIT-satory-26-source-finder-dryrun-2026-05-14.md.\n"
    "Доктрина (todoist-control-plane v1.7.0): источник не выдумывается; "
    "Subgroup E задачи остаются yellow до уточнения Мади."
)

PARENT_INHERITED_BODY = (
    "Источник: source-finder — родительская задача "
    "«Все 9 страниц сайта работают» (id=6gJ9Mm87G6Gxjfpq) — source-backed под "
    "LAW-016 lock satory.nousagaas.com, asset index-BSiWURaO.js.\n\n"
    "Runtime smoke 2026-05-14: HTTP 200 + asset matches LAW-016 на роуте. "
    "Полная Playwright проверка page-render queued как отдельная автоматизация.\n\n"
    "Дочерние задачи наследуют source-backed статус родителя."
)

NOTION_BASE = "https://www.notion.so"

TRIAGE: dict[str, tuple[str, str]] = {
    # Subgroup A — 8 parent-inherited site smoke tasks
    "6gJ9MmFw8vMrQRFH": ("A", PARENT_INHERITED_BODY),  # Дашборд
    "6gJ9MmHGPR9Fj7mH": ("A", PARENT_INHERITED_BODY),  # Камеры
    "6gJ9MmPFWfrHHXrq": ("A", PARENT_INHERITED_BODY),  # Нарушения
    "6gJ9MmW2V2j8m5QH": ("A", PARENT_INHERITED_BODY),  # Карта
    "6gJ9Mmh49jqm2p4q": ("A", PARENT_INHERITED_BODY),  # Патрулирование
    "6gJ9Mmmh7rjwv78q": ("A", PARENT_INHERITED_BODY),  # Архив
    "6gJ9Mmv7G4g8pW5q": ("A", PARENT_INHERITED_BODY),  # Состояние
    "6gJ9Mp2Fgcwg8vfq": ("A", PARENT_INHERITED_BODY),  # Настройки
    # Subgroup B — Notion-sourced product features
    "6gJ9Mp8v34X82gQH": (  # Номерные знаки КЗ
        "B",
        "Источник: source-finder — Notion: «Hikvision Deep Dive — Response to "
        "Kuba's Questions (for Audit Briefing)» "
        f"({NOTION_BASE}/30acb8f8c69f815188c5d3a3b94b70b7). "
        "ANPR engine, plate recognition, edge computing chip — "
        "распознавание номерных знаков выполняется на edge внутри HikVision камеры.",
    ),
    "6gJ9MpQJ24Jx22gH": (  # Метрология автопроверка
        "B",
        "Источник: source-finder — Notion (3 связанные страницы):\n"
        f"1) «ДОРОЖНАЯ КАРТА v2 — Замена BigDataLab — Подключение АПК к ЕРАП» ({NOTION_BASE}/30bcb8f8c69f81f4bf37c958756f8eb9) — метрологический сертификат комплекса «Мерген».\n"
        f"2) «Spectra ITS — Стартовый пакет + Письма» ({NOTION_BASE}/30bcb8f8c69f814aa7b5f43b6d966696) — Этап 2: Hikvision + Метрология (недели 2–12).\n"
        f"3) «Команда и роли (новая компания)» ({NOTION_BASE}/30bcb8f8c69f8140b243cce18108a633) — Команда 2 (Юр + Метрология): Назель + Роза + Жанара + метролог.",
    ),
    "6gJ9MpfQM3H8rWGH": (  # Прямое видео + PTZ
        "B",
        "Источник: source-finder — Notion: «Hikvision Deep Dive — Response to "
        f"Kuba's Questions» ({NOTION_BASE}/30acb8f8c69f815188c5d3a3b94b70b7) — "
        "HikVision PTZ cameras + edge live stream архитектура.",
    ),
    "6gJ9MppcCPQXq99H": (  # Поиск ТС
        "B",
        "Источник: source-finder — Notion: «Hikvision Deep Dive — Response to "
        f"Kuba's Questions» ({NOTION_BASE}/30acb8f8c69f815188c5d3a3b94b70b7) — "
        "ANPR + edge computing chip обеспечивают поиск ТС по номерам.",
    ),
    "6gJ9Mq5vmF8gXcXH": (  # Страница статуса Live
        "B",
        "Источник: source-finder — Notion: «SPECTRA ITS — MASTER STATE» "
        f"({NOTION_BASE}/32ecb8f8c69f810689deea7ca0acb7f2) — "
        "satory.nousagaas.com LIVE: 6+ страниц deployed; локированный asset "
        "index-BSiWURaO.js под LAW-016. Live status уже работает на satory.nousagaas.com/.",
    ),
    "6gJ9MqC4x9rGgpmH": (  # Расположение данных в КЗ
        "B",
        "Источник: source-finder — Notion (2 связанные страницы):\n"
        f"1) «ДОРОЖНАЯ КАРТА v2 — Замена BigDataLab» ({NOTION_BASE}/30bcb8f8c69f81f4bf37c958756f8eb9) — data residency архитектура.\n"
        f"2) «SPECTRA ITS — MASTER STATE» ({NOTION_BASE}/32ecb8f8c69f810689deea7ca0acb7f2) — "
        "production data flow.",
    ),
    # Subgroup C — KEONA business tasks
    "6gcXg52fM4rvpMPH": (  # Презентация Keon-A
        "C",
        "Источник: source-finder — Notion: «CYCLE-KEONA-CALL-BRIEF-2026-05-14 06:00 UTC» "
        f"({NOTION_BASE}/360cb8f8c69f819aaf60e6a35c1dceaf) + CYCLE-KEONA-DRAFT-EMAIL series — "
        "контекст таймлайна Keon-A пилота, факторы готовности.",
    ),
    "6gcXg566Fwpv3Gpq": (  # Назель/Роза — юр вопросы JV RU/KO
        "C",
        "Источник: source-finder — Notion: «KEONA Docs - Astana Hub vs MFCA JV Structure - 2026-05-11» "
        f"({NOTION_BASE}/35dcb8f8c69f81879087d4a2acb3748b). Maru Analytics in Astana Hub "
        "as operating/JV vehicle — основа для юридических вопросов Назель/Розе.",
    ),
    "6gcXg59V9jrCMCxq": (  # Назель/Роза — внутр юр обсуждение
        "C",
        "Источник: source-finder — Notion (2 страницы):\n"
        f"1) «KEONA Docs - Astana Hub vs MFCA JV Structure» ({NOTION_BASE}/35dcb8f8c69f81879087d4a2acb3748b).\n"
        f"2) «Команда и роли (новая компания)» ({NOTION_BASE}/30bcb8f8c69f8140b243cce18108a633) — "
        "Команда 2 (Юр + Метрология).",
    ),
    "6gcXg5GCv2VW47fq": (  # Мади/Назель/Роза — звонок с Алматом
        "C",
        "Источник: source-finder — Notion (2 страницы):\n"
        f"1) «CYCLE-MARU-CALL-BRIEF-2026-05-13 04:00 UTC» ({NOTION_BASE}/35fcb8f8c69f81e889ccec598e5afc82) — "
        "PATH A (Maru via Saken) vs Almat independent parallel path.\n"
        f"2) «KEONA Docs - Astana Hub vs MFCA JV Structure» ({NOTION_BASE}/35dcb8f8c69f81879087d4a2acb3748b).",
    ),
    "6gcXg5fFpCf684XH": (  # Асыл — solar/wind/battery
        "C",
        "Источник: source-finder — Notion: «KEONA 12:00 Execution Update - 2026-05-11» "
        f"({NOTION_BASE}/35dcb8f8c69f8138bcbdeebf58fe4f4c). "
        "Notion страница явно ссылается на эту задачу: «Solar/wind/battery sizing: 6gcXg5fFpCf684XH.»",
    ),
    "6gcXg5phC3XHr2wH": (  # Мади/GR — DTS/Ярослав
        "C",
        "Источник: source-finder — Notion: «CYCLE-SPECTRA-CALL-BRIEF-2026-05-12 12:00 UTC» "
        f"({NOTION_BASE}/35ecb8f8c69f815e9720f3c71f4d0cfe). "
        "Confirm VMS/Europassel DTS/Yaroslav — основа для GR-одобрения.",
    ),
    "6gcXg5x4jVgh4gCH": (  # DK/VKO Усть-Каменогорск
        "C",
        "Источник: source-finder — Notion: CYCLE-KEONA-DRAFT-EMAIL series "
        f"({NOTION_BASE}/360cb8f8c69f814e9d70e38ecb2afcfc — 2026-05-14 04:00 UTC) + KEONA Docs. "
        "Логистика доставки на неделю 15.06.2026 покрывается KEONA pipeline.",
    ),
    # Subgroup D — Vault-sourced VAR camera tasks
    "6gf5GWC8fw6p3rxH": (  # свяжись с Ерасылом / test env
        "D",
        "Источник: source-finder — vault: "
        "[[SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13]] "
        "(pages/sources/user-forwarded/SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13.md) + "
        "[[satory-erap-testing-status-2026-05-13]]. gbrain semantic score 0.99. "
        "Деталь: задача в той же ветке тестирования что и Var-камера. "
        "(Доказательство классификатор-промаха: AP-15 control-plane-sync v1.1.0.)",
    ),
    "6gf5H3PQQ9GHvhQH": (  # завершите установку Var камеры до 14-мая-26
        "D",
        "Источник: source-finder — vault: "
        "[[SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13]] "
        "(pages/sources/user-forwarded/SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13.md). "
        "Руслан 2026-05-13: складская вариофокальная камера + радар для тестов; "
        "это та самая Var камера. Статус/решение в [[satory-erap-testing-status-2026-05-13]].",
    ),
    "6gf5HQ62hGMH2p8H": (  # Имеется камера VAR на которой можно сделать factory reset
        "D",
        "Источник: source-finder — vault: "
        "[[SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13]] "
        "(pages/sources/user-forwarded/SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13.md). "
        "Руслан явно описал эту Var-камеру как тестовый стенд "
        "(не factory-reset рабочего АПК — 24 часа на восстановление, слетают калибровки).",
    ),
    # Subgroup E — 2 truly contextless (no fabrication; structured needs-Madi comment)
    "6gJ9MpXpWgHMWVwq": (  # Карта 243 камеры GPS
        "E",
        "Источник: source-finder — NOT FOUND (попытка прозрачно зафиксирована).\n\n"
        "Что искал: gbrain hybrid query «Карта 243 камеры GPS Satory расположение» (0 hits); "
        "Notion search (3 страницы, все упоминают «12 active camera deployments in VKO region», "
        "не 243). Несовпадение цифры: задача говорит 243, Notion говорит 12.\n\n"
        "Мади — нужно уточнение: это план будущего deployment (243), отдельный scope, "
        "или устаревшая цифра? Без ответа задача остаётся yellow по доктрине "
        "todoist-control-plane v1.7.0 (источник не выдумывается)."
    ),
    "6gJ9Mq4XQp536PvH": (  # Автоматические тесты Playwright
        "E",
        "Источник: source-finder — NOT FOUND (попытка прозрачно зафиксирована).\n\n"
        "Что искал: gbrain hybrid query «Автоматические тесты Playwright Satory сайт» (0 hits); "
        "Notion search (только общие SPECTRA ITS MASTER STATE упоминают satory.nousagaas.com).\n\n"
        "Мади — нужно уточнение: это (a) новая инициатива для добавления Playwright тестов "
        "Satory client сайта, или (b) уже покрыто tools/weekly_library_canary.sh "
        "(существующий runtime smoke)? Без scope-уточнения задача остаётся yellow."
    ),
}


def get_existing_comments(token: str, task_id: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    params = {"task_id": task_id}
    out = []
    cursor = None
    while True:
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


def already_has_marker(comments: list[dict]) -> bool:
    return any((c.get("content") or "").startswith(MARKER_PREFIX) for c in comments)


def post_comment(token: str, task_id: str, body: str) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"task_id": task_id, "content": body}
    r = requests.post(f"{TODOIST_BASE}/comments", headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("/Users/madia/nous-agaas/.env"),
        help="Env file with SATORY_TODOIST_TOKEN / TODOIST_API_TOKEN",
    )
    parser.add_argument("--apply", action="store_true", help="Actually post comments")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without posting")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help="Write a JSON receipt to this path (default: stdout)",
    )
    args = parser.parse_args(argv)

    if not args.apply and not args.dry_run:
        print("ERROR: pass --apply OR --dry-run explicitly", file=sys.stderr)
        return 2

    try:
        token = get_token(args.env_file)
    except RuntimeError as exc:
        print(f"ERROR: {exc} (env-file={args.env_file})", file=sys.stderr)
        return 2

    receipt: dict = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": "apply" if args.apply else "dry-run",
        "project_id": ALLOWED_PROJECT_ID,
        "marker": MARKER_PREFIX,
        "total": len(TRIAGE),
        "posted": 0,
        "skipped_idempotent": 0,
        "errors": 0,
        "per_task": [],
    }

    for task_id, (subgroup, body) in TRIAGE.items():
        full_body = body + COMMENT_FOOTER
        try:
            existing = get_existing_comments(token, task_id)
        except requests.HTTPError as e:
            receipt["errors"] += 1
            receipt["per_task"].append({
                "task_id": task_id, "subgroup": subgroup,
                "result": "error", "detail": f"fetch_comments_failed: {e}",
            })
            continue
        skip = already_has_marker(existing)
        if skip:
            receipt["skipped_idempotent"] += 1
            receipt["per_task"].append({
                "task_id": task_id, "subgroup": subgroup, "result": "skipped_idempotent",
            })
            continue
        if not args.apply:
            receipt["per_task"].append({
                "task_id": task_id, "subgroup": subgroup, "result": "would_post",
                "preview": full_body[:120],
            })
            continue
        try:
            resp = post_comment(token, task_id, full_body)
            receipt["posted"] += 1
            receipt["per_task"].append({
                "task_id": task_id, "subgroup": subgroup, "result": "posted",
                "comment_id": resp.get("id"),
            })
        except requests.HTTPError as e:
            receipt["errors"] += 1
            receipt["per_task"].append({
                "task_id": task_id, "subgroup": subgroup,
                "result": "error", "detail": f"post_failed: {e}",
            })

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"receipt -> {args.receipt}")
    if args.json:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    else:
        print(
            f"mode={receipt['mode']} total={receipt['total']} "
            f"posted={receipt['posted']} skipped={receipt['skipped_idempotent']} "
            f"errors={receipt['errors']}"
        )
    return 0 if receipt["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
