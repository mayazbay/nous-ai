from __future__ import annotations

import sys
import types
import importlib.util
from datetime import date, datetime
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
cost_tracker = types.ModuleType("cost_tracker")
cost_tracker.daily_report = lambda *args, **kwargs: {}
cost_tracker.format_report = lambda *args, **kwargs: ""
sys.modules.setdefault("cost_tracker", cost_tracker)

factory_health = types.ModuleType("factory_health")
factory_health.run_checks = lambda *args, **kwargs: []
factory_health._load_extra_envs = lambda *args, **kwargs: {}
sys.modules.setdefault("factory_health", factory_health)

sys.path.insert(0, str(TOOLS_DIR))
spec = importlib.util.spec_from_file_location("command_center_receipt_under_test", TOOLS_DIR / "command_center.py")
assert spec and spec.loader
command_center = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command_center)


def test_direct_telegram_task_result_receipt_redacts_and_writes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NOUS_WIKI", str(tmp_path))
    monkeypatch.setenv("NOUS_TELEGRAM_RESULT_COMMIT", "0")
    monkeypatch.setattr(
        command_center,
        "_now_almaty",
        lambda: datetime(2026, 5, 19, 17, 26, 37, tzinfo=command_center.ALMATY_TZ),
    )

    rel = command_center._write_telegram_task_result_receipt(
        "/ask-langgraph-codex-execution",
        1772,
        "test: inO_RCN$$vL7Knl7\nprod: Hwm6Z$rOc@X~pqvb\nPublic IP: 65.108.215.200",
        "Accepted. password: should-not-persist",
        model="gpt-5.5",
        via="/ask LangGraph route: ChatGPT/Codex execution",
    )

    assert rel is not None
    receipt = tmp_path / rel
    assert receipt.exists()
    text = receipt.read_text(encoding="utf-8")
    assert "source: \"telegram:tg_1772:ask-langgraph-codex-execution\"" in text
    assert "test: [REDACTED]" in text
    assert "prod: [REDACTED]" in text
    assert "password=[REDACTED]" in text
    assert "inO_RCN$$vL7Knl7" not in text
    assert "Hwm6Z$rOc@X~pqvb" not in text
    assert "should-not-persist" not in text


def test_post_ask_classifier_pins_runtime_ingest_paths_to_wiki(monkeypatch, tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    today = date.today().isoformat()
    inbox = wiki / "pages" / "inbox" / today
    inbox.mkdir(parents=True)
    (inbox / "1888-unknown.md").write_text("---\nmsg_id: 1888\n---\n\n# Original message\n\nmake task\n\n# End\n")
    monkeypatch.setenv("NOUS_WIKI", str(wiki))

    intent_classifier = types.ModuleType("intent_classifier")
    intent_classifier.classify = lambda body: {
        "intent": "task",
        "confidence": 0.95,
        "rationale": "test",
        "classifier_model": "stub",
    }

    telegram_ingest_persist = types.ModuleType("telegram_ingest_persist")
    telegram_ingest_persist.VAULT = Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")
    telegram_ingest_persist.INBOX_ROOT = telegram_ingest_persist.VAULT / "pages" / "inbox"
    telegram_ingest_persist.TASKS_FILE = telegram_ingest_persist.VAULT / "TASKS.md"
    telegram_ingest_persist.MERCURY_FACTS = telegram_ingest_persist.VAULT / "pages" / "mercury" / "facts.jsonl"

    def classify(slug: str, intent: str, confidence: float, rationale: str, classifier_model: str) -> dict:
        assert telegram_ingest_persist.VAULT == wiki
        assert telegram_ingest_persist.INBOX_ROOT == wiki / "pages" / "inbox"
        assert telegram_ingest_persist.TASKS_FILE == wiki / "TASKS.md"
        assert telegram_ingest_persist.MERCURY_FACTS == wiki / "pages" / "mercury" / "facts.jsonl"
        return {"slug": slug.replace("unknown", intent), "side_effects": {"tasks": True}}

    telegram_ingest_persist.classify = classify
    monkeypatch.setitem(sys.modules, "intent_classifier", intent_classifier)
    monkeypatch.setitem(sys.modules, "telegram_ingest_persist", telegram_ingest_persist)

    footer = command_center._classify_inbox_post_ask(1888, "make task")

    assert "Saved as task" in footer
    assert "TASKS.md" in footer
