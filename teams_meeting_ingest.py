#!/usr/bin/env python3
"""Ingest Teams meeting transcript artifacts into the Nous control plane.

Phase 1 is deliberately artifact-first: consume a Teams transcript/Notion AI
summary after the meeting, write a source page, and produce Todoist candidate
payloads. It does not join calls, poll Teams audio, or mutate Todoist directly.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


try:
    from ops_task_spine import SATORY_TODOIST_PROJECT_ID
except ImportError:  # pragma: no cover - allows direct execution from odd cwd
    SATORY_TODOIST_PROJECT_ID = "6gJ5j8PRVVCWpgCq"


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_SOURCE_DIR = Path("pages/sources/meetings")
DEFAULT_TASK_RESULTS_DIR = Path("pages/task-results")
CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*(.+?)\s*$")
TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2}(?:[.,]\d{3})?\s+-->\s+\d{2}:\d{2}:\d{2}(?:[.,]\d{3})?")
VOICE_TAG_RE = re.compile(r"<v\s+([^>]+)>(.*?)</v>|<v\s+([^>]+)>(.*)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
RU_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}
KNOWN_OWNERS = [
    "Виктор Юрьевич",
    "Андрей Стрия",
    "Даниэль",
    "Назель",
    "Мади",
    "Роза",
    "Айсхан",
    "Ассол",
]


@dataclasses.dataclass(frozen=True)
class ActionItem:
    text: str
    owner: str
    team: str
    due_date: str
    priority: str
    source_quote: str


def clean_transcript(raw: str) -> str:
    """Return readable transcript text from Teams/WebVTT/plain text."""
    lines: list[str] = []
    for original in raw.splitlines():
        line = original.strip()
        if not line:
            continue
        if line == "WEBVTT" or line.startswith(("NOTE", "STYLE", "REGION")):
            continue
        if line.isdigit() or TIMESTAMP_RE.match(line):
            continue
        line = _clean_vtt_voice_tag(line)
        line = HTML_TAG_RE.sub("", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract_action_items(summary_text: str, *, base_date: str | dt.date) -> list[ActionItem]:
    """Extract unchecked action items from a Notion AI meeting summary."""
    base = _parse_date(base_date)
    lines = _action_block_lines(summary_text)
    actions: list[ActionItem] = []
    for line in lines:
        match = CHECKBOX_RE.match(line)
        if not match:
            continue
        text = re.sub(r"\s+", " ", match.group(1)).strip()
        owner, team = _owner_and_team(text)
        actions.append(
            ActionItem(
                text=text,
                owner=owner,
                team=team,
                due_date=_due_date(text, base),
                priority=_priority(text),
                source_quote=text,
            )
        )
    return actions


def build_task_candidates(
    actions: list[ActionItem],
    *,
    source_path: str,
    source_url: str,
) -> list[dict[str, Any]]:
    """Build Todoist-ready candidate payloads without calling Todoist."""
    candidates: list[dict[str, Any]] = []
    for index, action in enumerate(actions, start=1):
        labels = [
            "источник:teams-meeting",
            f"отдел:{action.team}",
            f"приоритет:{action.priority}",
        ]
        if action.owner:
            labels.append(f"исполнитель:{action.owner}")
        else:
            labels.append("исполнитель:операционный-владелец-нужен")
        payload: dict[str, Any] = {
            "content": action.text,
            "project_id": SATORY_TODOIST_PROJECT_ID,
            "description": "\n".join(
                [
                    f"Источник: {source_url}",
                    f"Vault path: {source_path}",
                    f"Доказательство: {action.source_quote}",
                    "Готовность: задача закрывается только после фактического результата или ссылки на доказательство.",
                ]
            ),
            "priority": _todoist_priority(action.priority),
            "labels": labels,
        }
        if action.due_date:
            payload["due_date"] = action.due_date
        else:
            payload["due_date"] = ""
        candidates.append(
            {
                "index": index,
                "owner": action.owner,
                "team": action.team,
                "due_date": action.due_date,
                "priority": action.priority,
                "source_quote": action.source_quote,
                "todoist_payload": payload,
            }
        )
    return candidates


def write_ingestion(
    *,
    wiki_root: Path,
    title: str,
    meeting_date: str,
    summary_text: str,
    transcript_text: str,
    meeting_url: str = "",
    notion_url: str = "",
    ingested_at: str | None = None,
) -> dict[str, Any]:
    """Write source page and Todoist candidate receipt under a wiki root."""
    date = _parse_date(meeting_date)
    timestamp = ingested_at or dt.datetime.now(ALMATY).replace(microsecond=0).isoformat()
    slug = _slug(title, meeting_date)
    source_id = f"source-teams-{slug}"
    source_rel = DEFAULT_SOURCE_DIR / f"{source_id}.md"
    source_url = notion_url.strip() or f"vault:{source_rel.as_posix()}"
    actions = extract_action_items(summary_text, base_date=date)
    cleaned_transcript = clean_transcript(transcript_text)
    source_markdown = render_source_page(
        source_id=source_id,
        title=title,
        meeting_date=meeting_date,
        ingested_at=timestamp,
        summary_text=summary_text,
        transcript_text=cleaned_transcript,
        actions=actions,
        meeting_url=meeting_url,
        notion_url=notion_url,
    )
    candidates = build_task_candidates(
        actions,
        source_path=source_rel.as_posix(),
        source_url=source_url,
    )
    receipt_rel = DEFAULT_TASK_RESULTS_DIR / f"{meeting_date}-teams-meeting-ingest-{slug}.json"
    receipt = {
        "type": "teams_meeting_ingest",
        "title": title,
        "meeting_date": meeting_date,
        "ingested_at": timestamp,
        "source_path": source_rel.as_posix(),
        "source_url": source_url,
        "action_count": len(actions),
        "tasks": candidates,
    }

    (wiki_root / source_rel).parent.mkdir(parents=True, exist_ok=True)
    (wiki_root / receipt_rel).parent.mkdir(parents=True, exist_ok=True)
    (wiki_root / source_rel).write_text(source_markdown, encoding="utf-8")
    (wiki_root / receipt_rel).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "source_path": source_rel.as_posix(),
        "candidates_path": receipt_rel.as_posix(),
        "action_count": len(actions),
    }


def render_source_page(
    *,
    source_id: str,
    title: str,
    meeting_date: str,
    ingested_at: str,
    summary_text: str,
    transcript_text: str,
    actions: list[ActionItem],
    meeting_url: str,
    notion_url: str,
) -> str:
    """Render the canonical source page for one meeting."""
    action_lines = [f"- [ ] {action.text}" for action in actions]
    frontmatter = [
        "---",
        "type: source",
        f"id: {source_id}",
        f"title: {_json_string(title)}",
        f"date: {meeting_date}",
        "status: ingested",
        'source_channel: "Microsoft Teams transcript + Notion AI summary"',
        "language: ru",
        "tags: [source, meeting, teams, notion-ai, satory, todoist]",
        f"ingested_at: {_json_string(ingested_at)}",
    ]
    if meeting_url:
        frontmatter.append(f"meeting_url: {_json_string(meeting_url)}")
    if notion_url:
        frontmatter.append(f"notion_url: {_json_string(notion_url)}")
    frontmatter.append("---")

    sections = [
        "\n".join(frontmatter),
        f"# {title} — {meeting_date}",
        "## Действия",
        "\n".join(action_lines) if action_lines else "_Нет чекбокс-действий в summary._",
        "## Summary",
        summary_text.strip(),
        "## Transcript",
        transcript_text.strip() or "_Transcript artifact was empty or unavailable._",
    ]
    return "\n\n".join(sections).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki-root", type=Path, default=Path("."))
    parser.add_argument("--title", required=True)
    parser.add_argument("--date", required=True, dest="meeting_date")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--meeting-url", default="")
    parser.add_argument("--notion-url", default="")
    parser.add_argument("--ingested-at")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    summary_text = args.summary.read_text(encoding="utf-8")
    transcript_text = args.transcript.read_text(encoding="utf-8") if args.transcript else ""
    result = write_ingestion(
        wiki_root=args.wiki_root,
        title=args.title,
        meeting_date=args.meeting_date,
        summary_text=summary_text,
        transcript_text=transcript_text,
        meeting_url=args.meeting_url,
        notion_url=args.notion_url,
        ingested_at=args.ingested_at,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"source={result['source_path']}")
        print(f"candidates={result['candidates_path']}")
        print(f"action_count={result['action_count']}")
    return 0


def _action_block_lines(summary_text: str) -> list[str]:
    lines = summary_text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        folded = line.casefold()
        if line.lstrip().startswith("#") and ("действ" in folded or "следующ" in folded or "action" in folded):
            start = index + 1
            break
    if start is None:
        return lines
    result: list[str] = []
    for line in lines[start:]:
        if line.lstrip().startswith("#") and result:
            break
        result.append(line)
    return result


def _owner_and_team(text: str) -> tuple[str, str]:
    for owner in KNOWN_OWNERS:
        if text.startswith(owner + " "):
            return owner, _team(text)
    return "", _team(text)


def _team(text: str) -> str:
    folded = text.casefold()
    rules = [
        (("цод", "сервер", "кондиционер", "вентиляц", "опс", "пожар"), "Инфраструктура"),
        (("сопа", "договор", "юрид", "перспектив", "регистрац"), "Юридический отдел"),
        (("инвентар", "фотоотчет", "монтаж", "объект"), "Производство"),
        (("kiona", "keona", "maru", "корей", "сп ", "сотруднич"), "Партнерства"),
        (("дп", "конкурс", "асол", "ценов"), "Коммерческий отдел"),
        (("дрон", "акимат", "эколог"), "GR"),
        (("telegram", "телеграм", "todoist", "тудуист", "бот", "ai-ассист"), "AI Factory"),
    ]
    for needles, team in rules:
        if any(needle in folded for needle in needles):
            return team
    return "Операции"


def _priority(text: str) -> str:
    folded = text.casefold()
    if any(token in folded for token in ("критически", "завтра", "11:00", "21 мая", "22 мая", "на этой неделе")):
        return "p1"
    if any(token in folded for token in ("в течение двух недель", "на следующей неделе", "до конца")):
        return "p2"
    return "p2"


def _due_date(text: str, base: dt.date) -> str:
    folded = text.casefold()
    explicit = re.search(r"\b(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b", folded)
    if explicit:
        day = int(explicit.group(1))
        month = RU_MONTHS[explicit.group(2)]
        year = base.year
        candidate = dt.date(year, month, day)
        if candidate < base:
            candidate = dt.date(year + 1, month, day)
        return candidate.isoformat()
    if "завтра" in folded:
        return (base + dt.timedelta(days=1)).isoformat()
    if "в течение двух недель" in folded:
        return (base + dt.timedelta(days=14)).isoformat()
    if "на этой неделе" in folded:
        return _friday_of_week(base).isoformat()
    if "на следующей неделе" in folded:
        return (base + dt.timedelta(days=7)).isoformat()
    if "до конца мая" in folded:
        return dt.date(base.year if base.month <= 5 else base.year + 1, 5, 31).isoformat()
    return ""


def _friday_of_week(value: dt.date) -> dt.date:
    days_until_friday = 4 - value.weekday()
    if days_until_friday < 0:
        days_until_friday += 7
    return value + dt.timedelta(days=days_until_friday)


def _todoist_priority(priority: str) -> int:
    return {"p1": 4, "p2": 3, "p3": 2, "p4": 1}.get(priority, 3)


def _parse_date(value: str | dt.date) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def _slug(title: str, meeting_date: str) -> str:
    ascii_title = title.encode("ascii", "ignore").decode("ascii").lower()
    stem = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")
    if not stem:
        stem = hashlib.sha256(title.encode("utf-8")).hexdigest()[:10]
    return f"{stem}-{meeting_date}"


def _clean_vtt_voice_tag(line: str) -> str:
    match = VOICE_TAG_RE.search(line)
    if not match:
        return line
    speaker = (match.group(1) or match.group(3) or "").strip()
    body = (match.group(2) or match.group(4) or "").strip()
    return f"{speaker}: {body}" if speaker else body


def _json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


if __name__ == "__main__":
    raise SystemExit(main())
