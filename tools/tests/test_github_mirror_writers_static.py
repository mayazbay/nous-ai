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


def test_obsidian_sync_wrapper_selects_host_local_vault() -> None:
    text = _text("tools/nous-obsidian-sync.sh")

    assert "resolve_nous_vault()" in text
    assert "canonical_remote()" in text
    assert "acquire_lock()" in text
    assert "nous-obsidian-sync.lock" in text
    assert "NOUS_VAULT_OVERRIDE" in text
    assert "run started (vault=$NOUS_VAULT)" in text
    assert 'fetch "$CANONICAL_REMOTE" main' in text
    assert 'push "$CANONICAL_REMOTE" main' in text
    assert "/Users/madia/nous-agaas/wiki" in text
    assert "/Users/madia/Documents/Projects/Nous AGaaS/Nous" in text
    assert text.index("/Users/madia/nous-agaas/wiki") < text.index(
        "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
    )


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
