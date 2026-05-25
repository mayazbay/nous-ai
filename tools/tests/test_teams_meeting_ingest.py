from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import teams_meeting_ingest as ingest


SUMMARY = """
Summary

### Действия и следующие шаги

- [ ]  Виктор Юрьевич подготовить отчет по ЦОДу с указанием недостатков, необходимого оборудования и финансовых затрат
- [ ]  Мади проверить и запустить процесс договора с Перспективой на этой неделе
- [ ]  Андрей Стрия завершить инвентаризацию с фактическими данными и фотографиями всех объектов в течение двух недель
- [ ]  Провести совещание завтра по организации сбора фотоотчетов от монтажников для инвентаризации
- [ ]  Даниэль отправить конкурсные документы по ДП через АСОЛ 21 мая
- [ ]  Назель проверить наличие второго участника в конкурсе ДП

### Переход управления транспортом в ЦИТ

- Документы подготовлены
"""


def test_extract_actions_from_notion_summary_block_with_owners_and_dates() -> None:
    actions = ingest.extract_action_items(SUMMARY, base_date="2026-05-18")

    assert [action.owner for action in actions[:3]] == ["Виктор Юрьевич", "Мади", "Андрей Стрия"]
    assert actions[0].team == "Инфраструктура"
    assert actions[1].team == "Юридический отдел"
    assert actions[2].due_date == "2026-06-01"
    assert actions[3].owner == ""
    assert actions[3].team == "Производство"
    assert actions[3].due_date == "2026-05-19"
    assert actions[4].owner == "Даниэль"
    assert actions[4].due_date == "2026-05-21"
    assert actions[5].owner == "Назель"


def test_clean_vtt_transcript_removes_cues_and_preserves_speaker_text() -> None:
    raw = """WEBVTT

1
00:00:01.000 --> 00:00:03.000
<v Madi>Доброе утро всем, начнем еженедельный отчет.

2
00:00:03.000 --> 00:00:05.000
<v Виктор Юрьевич>По ЦОДу ситуация такова.
"""

    cleaned = ingest.clean_transcript(raw)

    assert "WEBVTT" not in cleaned
    assert "-->" not in cleaned
    assert "Madi: Доброе утро всем" in cleaned
    assert "Виктор Юрьевич: По ЦОДу ситуация такова" in cleaned


def test_build_task_candidates_are_satory_scoped_and_source_backed() -> None:
    actions = ingest.extract_action_items(SUMMARY, base_date="2026-05-18")
    candidates = ingest.build_task_candidates(
        actions,
        source_path="pages/sources/meetings/source-teams-weekly-ops-2026-05-18.md",
        source_url="vault:pages/sources/meetings/source-teams-weekly-ops-2026-05-18.md",
    )

    first = candidates[0]
    assert first["todoist_payload"]["project_id"] == ingest.SATORY_TODOIST_PROJECT_ID
    assert "источник:teams-meeting" in first["todoist_payload"]["labels"]
    assert "исполнитель:Виктор Юрьевич" in first["todoist_payload"]["labels"]
    assert "отдел:Инфраструктура" in first["todoist_payload"]["labels"]
    assert "pages/sources/meetings/source-teams-weekly-ops-2026-05-18.md" in first["todoist_payload"]["description"]
    assert first["todoist_payload"]["due_date"] == ""

    dp = candidates[4]
    assert dp["todoist_payload"]["due_date"] == "2026-05-21"
    assert "отдел:Коммерческий отдел" in dp["todoist_payload"]["labels"]


def test_write_ingestion_creates_source_page_and_candidate_receipt(tmp_path: Path) -> None:
    result = ingest.write_ingestion(
        wiki_root=tmp_path,
        title="Weekly Ops",
        meeting_date="2026-05-18",
        summary_text=SUMMARY,
        transcript_text="Madi: Доброе утро всем.\nВиктор Юрьевич: По ЦОДу ситуация такова.",
        meeting_url="https://teams.microsoft.com/l/meetup-join/example",
        notion_url="https://www.notion.so/example",
        ingested_at="2026-05-18T11:45:00+05:00",
    )

    source = tmp_path / result["source_path"]
    receipt = tmp_path / result["candidates_path"]
    assert source.exists()
    assert receipt.exists()

    source_text = source.read_text(encoding="utf-8")
    assert "type: source" in source_text
    assert "source_channel: \"Microsoft Teams transcript + Notion AI summary\"" in source_text
    assert "## Действия" in source_text
    assert "- [ ] Виктор Юрьевич подготовить отчет по ЦОДу" in source_text
    assert "## Transcript" in source_text

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["action_count"] == 6
    assert payload["source_path"] == result["source_path"]
    assert payload["tasks"][0]["owner"] == "Виктор Юрьевич"
