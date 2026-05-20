from __future__ import annotations

from pathlib import Path
import sys

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import todoist_russianize as russianize

SATORY_ID = "6gJ5j8PRVVCWpgCq"


def test_needs_translation_ignores_protected_product_names() -> None:
    assert russianize.needs_translation("Reconnect Google Drive OAuth for Todoist control-plane register mirror")
    assert not russianize.needs_translation("KEONA / SPECTRA / Todoist / OpenClaw")
    assert not russianize.needs_translation("Keon-A АПК + NOUS/SPECTRA smoke proof")
    assert not russianize.needs_translation("Поделись файлом: pages/communications/outbound/DANIYAR-KIONA-FEEDBACK-2026-05-05.md.")
    assert not russianize.needs_translation("Notion: https://www.notion.so/abc123\nИсточник: SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13.md")
    assert russianize.visible_latin_words("Не отправлено: нужен Madi approval.") == ["approval"]


def test_label_target_translates_system_labels_without_touching_unknowns() -> None:
    assert russianize.label_target("отдел:AI Factory") == "отдел:AI-фабрика"
    assert russianize.label_target("исполнитель:Madi") == "исполнитель:Мади"
    assert russianize.label_target("status:blocked") == "статус:заблокировано"
    assert russianize.label_target("Daniyar") == "Данияр"
    assert russianize.label_target("high_impact") == "высокий_эффект"
    assert russianize.label_target("keona") is None


def test_build_plan_preserves_ids_and_creates_russian_updates() -> None:
    payload = {
        "projects": [{"id": SATORY_ID, "name": "Satory VKO Factory", "is_deleted": False, "is_archived": False}],
        "sections": [{"id": "s1", "project_id": SATORY_ID, "name": "📥 Intake / Triage", "is_deleted": False}],
        "labels": [{"id": "l1", "name": "отдел:AI Factory", "is_deleted": False}],
        "items": [
            {
                "id": "t1",
                "content": "Payment for Trash Collection",
                "description": "",
                "project_id": SATORY_ID,
                "section_id": "s1",
                "labels": ["отдел:AI Factory", "исполнитель:Madi", "status:blocked"],
                "priority": 4,
            }
        ],
    }
    translations = {"task:t1:content": "Оплата за вывоз мусора"}

    plan, residual = russianize.build_plan(payload, translations)

    assert residual["translation_errors"] == []
    assert any(row["action"] == "update_project" and row["id"] == SATORY_ID and row["after"] == "Фабрика Satory ВКО" for row in plan)
    assert any(row["action"] == "update_section" and row["id"] == "s1" and row["after"] == "📥 Входящие / Разбор" for row in plan)
    assert not any(row["action"] == "update_label" for row in plan)
    task_update = next(row for row in plan if row["action"] == "update_task" and row["id"] == "t1")
    assert task_update["after"]["content"] == "Оплата за вывоз мусора"
    assert task_update["after"]["labels"] == ["отдел:AI-фабрика", "исполнитель:Мади", "статус:заблокировано"]
    assert task_update["before"]["content"] == "Payment for Trash Collection"


def test_build_plan_translates_active_task_comments() -> None:
    payload = {
        "projects": [{"id": SATORY_ID, "name": "Фабрика Satory ВКО", "is_deleted": False, "is_archived": False}],
        "sections": [],
        "labels": [],
        "items": [{"id": "t1", "content": "Русская задача", "description": "", "project_id": SATORY_ID, "labels": [], "priority": 2}],
        "notes": [{"id": "n1", "item_id": "t1", "content": "If blocked, write blocker and next owner.", "is_deleted": False}],
    }
    translations = {"note:n1:content": "Если заблокировано, напишите блокер и следующего ответственного."}

    plan, _residual = russianize.build_plan(payload, translations)

    note_update = next(row for row in plan if row["action"] == "update_note")
    assert note_update["id"] == "n1"
    assert note_update["item_id"] == "t1"
    assert note_update["after"] == "Если заблокировано, напишите блокер и следующего ответственного."


def test_candidate_entries_ignores_mixed_russian_human_comment() -> None:
    payload = {
        "projects": [{"id": SATORY_ID, "name": "Фабрика Satory ВКО", "is_deleted": False, "is_archived": False}],
        "sections": [],
        "labels": [],
        "items": [{"id": "t1", "content": "Русская задача", "description": "", "project_id": SATORY_ID, "labels": [], "priority": 2}],
        "notes": [
            {
                "id": "n1",
                "item_id": "t1",
                "content": "1 - необходимо получить доступ в тестовую среду ЕРАПа\n2 - подписать СП\n3 - параллельно Keon-A АПК настроить NOUS и SPECTRA\n4 - произвести оплату 50% через Maru systems",
                "is_deleted": False,
            }
        ],
    }

    assert russianize.candidate_entries(payload) == []
    plan, residual = russianize.build_plan(
        payload,
        {"note:n1:content": "Русская версия предыдущего комментария:\nне надо"},
    )
    assert plan == []
    assert residual["skipped"][0]["reason"] == "mixed Russian human comment; do not echo translation"


def test_build_plan_ignores_personal_projects() -> None:
    payload = {
        "projects": [{"id": "personal", "name": "Family", "is_deleted": False, "is_archived": False}],
        "sections": [{"id": "s1", "project_id": "personal", "name": "📥 Intake / Triage", "is_deleted": False}],
        "labels": [{"id": "l1", "name": "отдел:AI Factory", "is_deleted": False}],
        "items": [
            {
                "id": "t1",
                "content": "Payment for Trash Collection",
                "description": "",
                "project_id": "personal",
                "section_id": "s1",
                "labels": ["отдел:AI Factory", "исполнитель:Madi", "status:blocked"],
                "priority": 4,
            }
        ],
        "notes": [{"id": "n1", "item_id": "t1", "content": "If blocked, write blocker.", "is_deleted": False}],
    }
    translations = {"task:t1:content": "Оплата за вывоз мусора", "note:n1:content": "Если заблокировано, напишите блокер."}

    plan, _residual = russianize.build_plan(payload, translations)
    entries = russianize.candidate_entries(payload)

    assert plan == []
    assert entries == []


def test_apply_plan_skips_immutable_comment_instead_of_echoing_translation() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls = []

        def request(self, method: str, path: str, **kwargs):
            self.calls.append((method, path, kwargs))
            if path == "/comments/n1":
                response = requests.Response()
                response.status_code = 400
                raise requests.HTTPError("400 Client Error", response=response)
            return {"id": "new-note"}

    client = FakeClient()
    counts = russianize.apply_plan(
        client,
        [
            {
                "action": "update_note",
                "id": "n1",
                "item_id": "t1",
                "before": "If blocked, write blocker.",
                "after": "Если заблокировано, напишите блокер.",
            }
        ],
        sleep=0,
    )

    assert counts == {"update_note_immutable_skipped": 1}
    assert client.calls == [("POST", "/comments/n1", {"json": {"content": "Если заблокировано, напишите блокер."}})]


def test_parse_translation_payload_accepts_fenced_json() -> None:
    raw = '```json\n[{"id":"x","ru":"Привет"}]\n```'

    assert russianize.parse_translation_payload(raw) == {"x": "Привет"}


def test_parse_translation_payload_extracts_json_array_from_preamble() -> None:
    raw = 'Вот перевод:\n[{"id":"x","ru":"Привет"}]\n'

    assert russianize.parse_translation_payload(raw) == {"x": "Привет"}


def test_parse_translation_payload_accepts_translations_object() -> None:
    raw = '{"translations":[{"id":"x","ru":"Привет"}]}'

    assert russianize.parse_translation_payload(raw) == {"x": "Привет"}


def test_single_translation_fallback_accepts_plain_russian_only() -> None:
    assert russianize.single_translation_fallback("Вот перевод: Купить книгу", "Buy the book") == "Купить книгу"
    assert russianize.single_translation_fallback("Buy the book", "Buy the book") is None


def test_acceptable_translation_rejects_russian_to_english_regression() -> None:
    assert russianize.acceptable_translation("Разослать RFQ на авиафрахт", "Разослать RFQ на авиафрахт")
    assert not russianize.acceptable_translation("Разослать 3 корейским форвардерам RFQ", "Send RFQs to 3 Korean forwarders")


def test_acceptable_translation_rejects_damaged_evidence_path() -> None:
    original = "Якорь: pages/projects/GOAL-20260512-135930-have-a-one-command-bootstrap-pack-ready-for-mergenovskii-s-f.md"
    damaged = "Якорь: pages/projects/GOAL-20260512-135930-have-a-one-command-bootstrap-pack-ready-for-mergenovskii-s.md"

    assert russianize.evidence_refs(original) == [
        "pages/projects/GOAL-20260512-135930-have-a-one-command-bootstrap-pack-ready-for-mergenovskii-s-f.md"
    ]
    assert not russianize.acceptable_translation(original, damaged)


def test_provider_key_order_prefers_matching_provider_key() -> None:
    assert russianize.provider_key_order("https://openrouter.ai/api/v1/chat/completions")[0] == "OPENROUTER_API_KEY"
    assert russianize.provider_key_order("https://api.openai.com/v1/chat/completions")[0] == "OPENAI_API_KEY"
    assert russianize.provider_key_order("http://127.0.0.1:4000/v1/chat/completions")[0] == "LITELLM_MASTER_KEY"
