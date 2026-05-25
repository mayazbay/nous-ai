"""Ship 3 wave 8 migration: archive gbrain shell, build canonical registry,
embed every doc via Voyage, write health snapshot.

Idempotent: rerunning is safe (archive skips if already archived; registry add is
idempotent by path; drain_queue skips unchanged content via content_hash).

CLI::

    python3 tools/migrate_ship3.py --wiki .                       # full migration
    python3 tools/migrate_ship3.py --wiki . --skip-embed          # skip Step C (Voyage)
    python3 tools/migrate_ship3.py --wiki . --dry-run             # plan only, no writes
    python3 tools/migrate_ship3.py --wiki . --json                # JSON result dump
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from tools import library_canonical_registry as registry
    from tools import library_drain_queue
    from tools import library_health
    from tools import library_embed_db  # noqa: F401 (re-exported for tests)
except ImportError:
    # Make tools/ importable when run as `python3 tools/migrate_ship3.py`.
    _HERE = Path(__file__).resolve().parent
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    import library_canonical_registry as registry  # type: ignore  # noqa: E402
    import library_drain_queue  # type: ignore  # noqa: E402
    import library_health  # type: ignore  # noqa: E402
    import library_embed_db  # type: ignore  # noqa: E402,F401


ALMATY = dt.timezone(dt.timedelta(hours=5))
SYNC_DIRS: tuple[str, ...] = (
    "pages/systems",
    "pages/skills",
    "pages/audits",
    "pages/plans",
    "pages/laws",
    "pages/concepts",
)
GBRAIN_LEGACY = Path.home() / ".claude" / "skills" / "gstack" / ".gbrain" / "skills"
QUEUE_REL = Path(".gbrain") / "queue.jsonl"


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


# ---------------------------------------------------------------------------
# Step A: archive the lying gbrain shell
# ---------------------------------------------------------------------------


def _archive_dest(src: Path, *, now: dt.datetime | None = None) -> Path:
    """Compose the destination archive path next to ``src``."""
    moment = now if now is not None else now_kzt()
    return src.parent / f"skills.archived-ship3-{moment.strftime('%Y%m%d')}"


_STUB_README = """# This directory was archived 2026-05-20.

Ship 3 of the god-tier plan retired the legacy gbrain skill-directory cache.
The REAL embedding index now lives at:
  /Users/madia/Documents/Projects/Nous AGaaS/Nous/.gbrain/index.db

Archived to: skills.archived-ship3-{stamp}/

See pages/skills/library-graph/SKILL.md for the new doctrine.
See pages/plans/from-gpt-implemented-the-delightful-riddle.md §6.8 for migration history.
"""


def archive_gbrain_shell(
    *,
    src: Path | None = None,
    dry_run: bool = False,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Archive the legacy gbrain skills shell to ``skills.archived-ship3-<date>/``.

    Idempotent:
      * If ``src`` does not exist → ``archived=False, reason='missing'``.
      * If ``src`` already looks like the README-only stub (no subdirectories,
        only a README.md) → ``archived=False, reason='already_stub'``.
      * Otherwise: ``mv src dest``, recreate empty ``src``, drop in README stub.
    """
    if src is None:
        src = GBRAIN_LEGACY

    result: dict[str, Any] = {
        "archived": False,
        "src": str(src),
        "dest": None,
        "reason": "",
    }

    if not src.exists():
        result["reason"] = "missing"
        return result

    # Stub detection: only README.md inside and no subdirectories.
    try:
        contents = list(src.iterdir())
    except OSError as exc:
        result["reason"] = f"oserror:{exc!r}"
        return result

    only_readme = (
        len(contents) <= 1
        and all(p.is_file() and p.name == "README.md" for p in contents)
    )
    if only_readme:
        result["reason"] = "already_stub"
        return result

    dest = _archive_dest(src, now=now)
    result["dest"] = str(dest)

    if dry_run:
        result["reason"] = "dry_run"
        return result

    # Don't clobber an existing archive — name it with a numeric suffix.
    final_dest = dest
    suffix = 1
    while final_dest.exists():
        final_dest = dest.parent / f"{dest.name}-{suffix}"
        suffix += 1
    result["dest"] = str(final_dest)

    os.rename(str(src), str(final_dest))
    src.mkdir(parents=True, exist_ok=True)
    stamp = (now if now is not None else now_kzt()).strftime("%Y-%m-%d")
    (src / "README.md").write_text(
        _STUB_README.format(stamp=stamp), encoding="utf-8"
    )

    result["archived"] = True
    result["reason"] = "ok"
    return result


# ---------------------------------------------------------------------------
# Step B: walk SYNC_DIRS and populate the canonical registry
# ---------------------------------------------------------------------------


def _walk_target_md(wiki: Path) -> list[str]:
    """Return sorted relative posix paths under SYNC_DIRS for every *.md file."""
    out: list[str] = []
    seen: set[str] = set()
    for sub in SYNC_DIRS:
        root = wiki / sub
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                rel = path.relative_to(wiki).as_posix()
            except ValueError:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            out.append(rel)
    return out


def populate_registry(
    wiki: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Walk SYNC_DIRS, call registry.add(path) for each .md file (idempotent)."""
    files = _walk_target_md(wiki)
    summary: dict[str, Any] = {
        "added": 0,
        "existing": 0,
        "files": files,
    }

    if dry_run:
        summary["dry_run"] = True
        return summary

    for rel in files:
        existing = registry.get(path=rel, wiki=wiki)
        if existing is not None:
            summary["existing"] += 1
            continue
        registry.add(rel, wiki=wiki)
        summary["added"] += 1

    return summary


# ---------------------------------------------------------------------------
# Step C: pre-populate queue + drain via library_drain_queue
# ---------------------------------------------------------------------------


def queue_all_for_embed(
    wiki: Path,
    paths: list[str],
    *,
    dry_run: bool = False,
    now: dt.datetime | None = None,
) -> int:
    """Append entries to ``.gbrain/queue.jsonl``. Returns number of lines queued.

    Each entry mirrors the post-commit hook format::

        {"path": "<rel>", "event": "migrate_ship3", "ts": "<iso>"}
    """
    if not paths:
        return 0

    if dry_run:
        return len(paths)

    moment = now if now is not None else now_kzt()
    ts = moment.isoformat()
    queue_path = wiki / QUEUE_REL
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(queue_path, "a", encoding="utf-8") as fh:
        for rel in paths:
            line = json.dumps(
                {"path": rel, "event": "migrate_ship3", "ts": ts},
                ensure_ascii=False,
            )
            fh.write(line + "\n")
            count += 1
    return count


def run_embed_drain(
    wiki: Path,
    *,
    prefer: str = "voyage",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Call ``library_drain_queue.drain_once``. Returns the drain result dict.

    Dry-run skips the call entirely and reports it.
    """
    if dry_run:
        return {"dry_run": True, "prefer": prefer}
    return library_drain_queue.drain_once(wiki, prefer_embedder=prefer)


# ---------------------------------------------------------------------------
# Step D: health snapshot
# ---------------------------------------------------------------------------


def write_health_snapshot(wiki: Path) -> dict[str, Any]:
    """Compute + atomically write the library-health snapshot."""
    snapshot = library_health.compute(wiki)
    library_health.write_atomic(wiki, snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def migrate(
    wiki: Path,
    *,
    dry_run: bool = False,
    skip_embed: bool = False,
    prefer: str = "voyage",
) -> dict[str, Any]:
    """Run Steps A-D in order. Returns ``{"step_a": ..., "step_b": ..., ...}``."""
    result: dict[str, Any] = {}

    print("[migrate] Step A: archive gbrain shell", file=sys.stderr)
    result["step_a"] = archive_gbrain_shell(dry_run=dry_run)

    print("[migrate] Step B: build canonical registry", file=sys.stderr)
    result["step_b"] = populate_registry(wiki, dry_run=dry_run)

    if not skip_embed:
        print(
            "[migrate] Step C: embed via Voyage "
            "(full vault takes ~12 min, ~$0.09)",
            file=sys.stderr,
        )
        paths = result["step_b"].get("files", [])
        queued = queue_all_for_embed(wiki, paths, dry_run=dry_run)
        print(f"[migrate]   queued {queued} files", file=sys.stderr)
        result["step_c"] = run_embed_drain(wiki, prefer=prefer, dry_run=dry_run)
        result["step_c"]["queued"] = queued
    else:
        result["step_c"] = {"skipped": True}

    print("[migrate] Step D: health snapshot", file=sys.stderr)
    if dry_run:
        # Don't write — compute only.
        result["step_d"] = library_health.compute(wiki)
        result["step_d"]["dry_run"] = True
    else:
        result["step_d"] = write_health_snapshot(wiki)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description="Ship 3 wave 8 migration")
    p.add_argument("--wiki", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--skip-embed",
        action="store_true",
        help="Skip the expensive Voyage embed step (Step C). Useful when "
        "VOYAGE_API_KEY is missing or when testing.",
    )
    p.add_argument(
        "--prefer",
        choices=("voyage", "local", "stub"),
        default="voyage",
        help="Embedder preference passed to library_drain_queue.drain_once.",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    wiki = args.wiki if args.wiki is not None else registry.default_wiki()
    result = migrate(
        wiki,
        dry_run=args.dry_run,
        skip_embed=args.skip_embed,
        prefer=args.prefer,
    )

    if args.json:
        print(json.dumps(result, default=str, indent=2))
    else:
        print("\n=== MIGRATION COMPLETE ===")
        print(f"Step A (archive): {result['step_a']}")
        sb = result["step_b"]
        print(
            f"Step B (registry): added={sb.get('added')} "
            f"existing={sb.get('existing')} total={len(sb.get('files', []))}"
        )
        print(f"Step C (embed): {result.get('step_c')}")
        sd = result["step_d"]
        print(
            f"Step D (health): obsidian_files={sd.get('obsidian_files')} "
            f"canonical_registry_size={sd.get('canonical_registry_size')} "
            f"gbrain_indexed_chunks={sd.get('gbrain_indexed_chunks')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
