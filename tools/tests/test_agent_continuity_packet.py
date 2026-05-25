from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import agent_continuity_packet as packet


def _make_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path
    (wiki / "pages" / "progress").mkdir(parents=True)
    (wiki / "pages" / "systems").mkdir(parents=True)
    (wiki / "pages" / "audits").mkdir(parents=True)
    (wiki / "pages" / "plans").mkdir(parents=True)
    (wiki / "pages" / "skills" / "multi-model-consult").mkdir(parents=True)
    return wiki


def test_build_packet_includes_latest_handoff_and_switch_commands(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    older = wiki / "pages" / "progress" / "HANDOFF-AUTO-2026-05-20-06-00.md"
    newer = wiki / "pages" / "progress" / "HANDOFF-AUTO-2026-05-20-09-00.md"
    older.write_text("# old\n", encoding="utf-8")
    newer.write_text("# newest\nFactory green.\n", encoding="utf-8")

    (wiki / "pages" / "audits" / "GROK-DIRECT-STRUCTURE-CONSULT-2026-05-20.md").write_text(
        "# grok\n", encoding="utf-8"
    )

    rendered = packet.build_packet(
        wiki,
        generated_at=dt.datetime(2026, 5, 20, 10, 30, tzinfo=packet.ALMATY),
    )

    assert "Agent Continuity Packet" in rendered
    assert "HANDOFF-AUTO-2026-05-20-09-00.md" in rendered
    assert "Factory green." in rendered
    assert "/code <task>" in rendered
    assert "/codex <task>" in rendered
    assert "/ask <task>" in rendered
    assert "multi_model_consult.py" in rendered
    assert "GROK-DIRECT-STRUCTURE-CONSULT-2026-05-20.md`: present" in rendered
    assert "git rev-parse --short HEAD" in rendered


def test_write_packet_creates_system_artifact(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    (wiki / "pages" / "progress" / "HANDOFF-AUTO-2026-05-20-09-00.md").write_text(
        "# handoff\n", encoding="utf-8"
    )

    path = packet.write_packet(wiki)

    assert path == wiki / packet.DEFAULT_OUTPUT_REL
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "This is the shared continuity source" in text
    assert "No new Telegram polling process" in text


def test_write_packet_does_not_rewrite_for_timestamp_only_refresh(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    (wiki / "pages" / "progress" / "HANDOFF-AUTO-2026-05-20-09-00.md").write_text(
        "# handoff\n", encoding="utf-8"
    )

    path = packet.write_packet(wiki)
    first = path.read_text(encoding="utf-8")
    packet.write_packet(wiki)
    second = path.read_text(encoding="utf-8")

    assert second == first
