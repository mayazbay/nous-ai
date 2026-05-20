from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_auto_sync_scripts_rebase_github_before_pushing_mirror() -> None:
    for rel in ("tools/nous-obsidian-sync.sh", "tools/wiki-sync-launch.sh"):
        text = _text(rel)
        assert "fetch github main" in text
        assert "rebase github/main" in text
        assert "push github main" in text
        assert text.index("fetch github main") < text.index("push github main")
        assert text.index("rebase github/main") < text.index("push github main")


def test_live_mac_obsidian_sync_wrapper_matches_tracked_script_when_present() -> None:
    live = Path("/Users/madia/.local/bin/nous-obsidian-sync.sh")
    if not live.exists():
        return

    assert live.read_text(encoding="utf-8") == _text("tools/nous-obsidian-sync.sh")


def test_control_plane_rebases_github_before_pushing_mirror() -> None:
    text = _text("tools/control_plane_sync_loop.py")

    fetch_index = text.index('fetch_remote_main_oid(wiki, "github"')
    rebase_index = text.index('"rebase", github_target')
    push_index = text.index('"push", "github", "main"')

    assert fetch_index < push_index
    assert rebase_index < push_index
