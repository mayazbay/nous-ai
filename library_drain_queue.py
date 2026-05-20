"""Drain .gbrain/queue.jsonl: chunk + embed + insert each queued file.

Idempotent: skips files whose content_hash in canonical-registry matches the
current file. Fail-soft: any embed/insert failure logs to
``logs/library-drain.log``; queue entry retried next pass.

Runs as one-shot (default; launchd hits it every 60s) OR ``--loop`` (manual
debugging). Stdlib only for control-flow; sqlite-vec / sentence-transformers
are only touched via library_embed_db / library_embed_voyage which gracefully
degrade if those libs are absent.

Ship 3 wave 7. Pairs with:
    * .git/hooks/post-commit (writes .gbrain/queue.jsonl)
    * ~/Library/LaunchAgents/com.nous.library-graph.plist (60s timer)
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterator

try:
    from tools import library_canonical_registry as registry
    from tools import library_embed
    from tools import library_embed_voyage
    from tools import library_embed_db
except ImportError:  # running with tools/ already on sys.path
    import library_canonical_registry as registry  # type: ignore
    import library_embed  # type: ignore
    import library_embed_voyage  # type: ignore
    import library_embed_db  # type: ignore


ALMATY = dt.timezone(dt.timedelta(hours=5))
QUEUE_REL = Path(".gbrain/queue.jsonl")
QUEUE_LOCK_REL = Path("logs/library-drain.lock")
LOG_REL = Path("logs/library-drain.log")


# ---------------------------------------------------------------------------
# Path resolution helpers (mirrors library_canonical_registry)
# ---------------------------------------------------------------------------


def default_wiki() -> Path:
    """Resolve the wiki root from NOUS_WIKI, or by walking from this file."""
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parents[1]
    if (here / "pages").exists():
        return here
    if (here / "wiki" / "pages").exists():
        return here / "wiki"
    return here


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def _queue_path(wiki: Path) -> Path:
    return wiki / QUEUE_REL


def _lock_path(wiki: Path) -> Path:
    return wiki / QUEUE_LOCK_REL


def _log_path(wiki: Path) -> Path:
    return wiki / LOG_REL


def _ensure_dirs(wiki: Path) -> None:
    _queue_path(wiki).parent.mkdir(parents=True, exist_ok=True)
    _lock_path(wiki).parent.mkdir(parents=True, exist_ok=True)
    _log_path(wiki).parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _with_lock(wiki: Path) -> Iterator[None]:
    """fcntl.LOCK_EX on logs/library-drain.lock so concurrent drains serialize."""
    _ensure_dirs(wiki)
    lock_path = _lock_path(wiki)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Queue IO
# ---------------------------------------------------------------------------


def _read_queue(wiki: Path) -> list[dict[str, Any]]:
    """Read all queue entries. Dedupe by path (keep latest by ts; ties: last seen).

    Malformed lines are silently skipped (they will be dropped on truncate).
    """
    path = _queue_path(wiki)
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError:
        return []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if not isinstance(obj.get("path"), str) or not obj["path"]:
            continue
        rows.append(obj)

    # Dedupe by path; keep the row with the latest ts. Ties: last-seen wins.
    by_path: dict[str, dict[str, Any]] = {}
    for r in rows:
        p = r["path"]
        prev = by_path.get(p)
        if prev is None:
            by_path[p] = r
            continue
        prev_ts = prev.get("ts", "") or ""
        curr_ts = r.get("ts", "") or ""
        # Lexicographic compare on ISO-8601 timestamps is correct sort order.
        if curr_ts >= prev_ts:
            by_path[p] = r
    return list(by_path.values())


def _truncate_queue(wiki: Path) -> None:
    """Empty the queue file atomically. Caller MUST hold the drain lock."""
    target = _queue_path(wiki)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text("", encoding="utf-8")
    os.replace(tmp, target)


def _append_log(wiki: Path, msg: str) -> None:
    """Append a single line to logs/library-drain.log. Best-effort."""
    target = _log_path(wiki)
    target.parent.mkdir(parents=True, exist_ok=True)
    stamp = now_kzt().isoformat()
    try:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp}  {msg}\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Main drain
# ---------------------------------------------------------------------------


def drain_once(
    wiki: Path,
    *,
    prefer_embedder: str = "voyage",
) -> dict[str, Any]:
    """One drain pass.

    Returns:
        {"processed": N, "skipped_unchanged": N, "errors": N,
         "auth_missing": N, "files": [...]}

    Behavior per queued path:
      1. registry.add(path) — idempotent; returns existing UUID if already known.
      2. Read file; compute content_hash.
      3. If content_hash matches the registry's stored content_hash → skip
         (skipped_unchanged += 1).
      4. Else: chunk via library_embed.chunk_file.
      5. Make embedder via library_embed_voyage.make_embedder(prefer=...).
      6. embedder.embed(chunks).
      7. If any result has error == 'auth_missing' → set auth_missing for this
         file and STOP processing further files (queue NOT truncated; retried
         next pass).
      8. Else: library_embed_db.init_db(wiki, dim=embedder.dim) +
         insert_chunks(...) via ChunkInsert.
      9. registry.update_field for content_hash + embed_model + embed_dim +
         gbrain_chunk_ids ([f'{uuid}:{i}' for i in 0..len(chunks)]).
     10. Any per-file exception: log + errors += 1, continue with remaining files.

    Queue truncation:
      * On overall success (processed >= 1 AND auth_missing == 0) → truncate.
      * If auth_missing > 0 → leave queue intact (retry next pass).
      * If only skipped_unchanged → truncate (all entries handled).
      * If only errors → leave queue intact (retry next pass).
    """
    summary: dict[str, Any] = {
        "processed": 0,
        "skipped_unchanged": 0,
        "errors": 0,
        "auth_missing": 0,
        "files": [],
    }

    with _with_lock(wiki):
        entries = _read_queue(wiki)
        if not entries:
            return summary

        embedder = None  # lazy — only build when first needed
        auth_missing_hit = False

        for entry in entries:
            rel_path = entry["path"]
            abs_path = wiki / rel_path
            file_record: dict[str, Any] = {"path": rel_path}

            if auth_missing_hit:
                # Don't process further files once we've established auth is
                # broken — keeps queue intact + avoids needless calls.
                file_record["status"] = "deferred_auth_missing"
                summary["files"].append(file_record)
                continue

            try:
                # 1. Register (or look up) canonical UUID.
                #    Note: registry.add() initialises content_hash from the
                #    on-disk file when creating a new entry, so for brand-new
                #    paths the hash will match below. We use the presence of
                #    embed_dim > 0 (or a non-empty gbrain_chunk_ids list) to
                #    distinguish "first-ever embed needed" from "already
                #    embedded + content unchanged".
                uid = registry.add(rel_path, wiki=wiki)
                file_record["uuid"] = uid

                # 2. Hash the on-disk file.
                new_hash = registry.file_content_hash(abs_path)

                # 3. Skip if content_hash matches AND the entry has already
                #    been embedded at least once. A fresh-add entry has
                #    content_hash set but embed_dim == 0 → must still embed.
                current = registry.get(uuid=uid, wiki=wiki)
                embed_dim = current.get("embed_dim") if current else 0
                chunk_ids_field = current.get("gbrain_chunk_ids") if current else None
                already_embedded = bool(
                    (isinstance(embed_dim, int) and embed_dim > 0)
                    or (isinstance(chunk_ids_field, list) and chunk_ids_field)
                )
                if (
                    current is not None
                    and current.get("content_hash") == new_hash
                    and already_embedded
                ):
                    summary["skipped_unchanged"] += 1
                    file_record["status"] = "skipped_unchanged"
                    summary["files"].append(file_record)
                    continue

                # 4. Chunk the file.
                chunks = library_embed.chunk_file(abs_path)
                if not chunks:
                    # Empty file or missing file — record as skipped but
                    # update the hash so we don't loop on it next pass.
                    registry.update_field(uid, "content_hash", new_hash, wiki=wiki)
                    summary["skipped_unchanged"] += 1
                    file_record["status"] = "skipped_empty"
                    summary["files"].append(file_record)
                    continue

                # 5. Build embedder if not yet built.
                if embedder is None:
                    embedder = library_embed_voyage.make_embedder(
                        prefer=prefer_embedder
                    )

                # 6. Embed.
                results = embedder.embed(chunks)

                # 7. Bail out on auth_missing — queue NOT truncated so we
                #    retry once the key shows up.
                if any(getattr(r, "error", "") == "auth_missing" for r in results):
                    summary["auth_missing"] += 1
                    file_record["status"] = "auth_missing"
                    summary["files"].append(file_record)
                    auth_missing_hit = True
                    _append_log(
                        wiki,
                        f"auth_missing for {rel_path}; deferring drain "
                        f"(embedder={getattr(embedder, 'name', '?')})",
                    )
                    continue

                # Any other per-result error → log + count as error; do NOT
                # write into the DB or update registry hash, so we retry.
                errored = [r for r in results if getattr(r, "error", "")]
                if errored:
                    summary["errors"] += 1
                    file_record["status"] = "embed_error"
                    file_record["error"] = getattr(errored[0], "error", "")
                    summary["files"].append(file_record)
                    _append_log(
                        wiki,
                        f"embed error for {rel_path}: "
                        f"{file_record['error']} (embedder={getattr(embedder, 'name', '?')})",
                    )
                    continue

                # 8. Init DB + insert chunks.
                dim = int(getattr(embedder, "dim", 0))
                model_name = str(getattr(embedder, "name", "unknown"))
                library_embed_db.init_db(wiki, dim=dim)
                batch = [
                    library_embed_db.ChunkInsert(
                        canonical_uuid=uid,
                        chunk_idx=chunks[i].chunk_idx,
                        heading_path=chunks[i].heading_path,
                        text=chunks[i].text,
                        content_hash=chunks[i].content_hash,
                        vector=list(results[i].vector),
                        embed_model=model_name,
                        embed_dim=dim,
                    )
                    for i in range(len(chunks))
                ]
                inserted = library_embed_db.insert_chunks(wiki, batch)

                # 9. Update registry: content_hash, embed_model, embed_dim,
                #    gbrain_chunk_ids.
                chunk_ids = [f"{uid}:{i}" for i in range(len(chunks))]
                registry.update_field(uid, "content_hash", new_hash, wiki=wiki)
                registry.update_field(uid, "embed_model", model_name, wiki=wiki)
                registry.update_field(uid, "embed_dim", dim, wiki=wiki)
                registry.update_field(uid, "gbrain_chunk_ids", chunk_ids, wiki=wiki)

                summary["processed"] += 1
                file_record["status"] = "processed"
                file_record["chunks"] = len(chunks)
                file_record["inserted"] = inserted
                summary["files"].append(file_record)

            except Exception as exc:  # per-file isolation
                summary["errors"] += 1
                file_record["status"] = "exception"
                file_record["error"] = repr(exc)
                summary["files"].append(file_record)
                _append_log(wiki, f"exception draining {rel_path}: {exc!r}")
                continue

        # Truncate decision:
        # - auth_missing → leave queue intact for next pass
        # - errors only → leave queue intact for retry
        # - processed > 0 with no auth_missing → truncate (success path)
        # - all skipped_unchanged with no errors/auth_missing → truncate
        if summary["auth_missing"] == 0 and summary["errors"] == 0:
            if summary["processed"] >= 1 or summary["skipped_unchanged"] >= 1:
                _truncate_queue(wiki)

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(
        description="Drain .gbrain/queue.jsonl: embed-on-commit chain"
    )
    p.add_argument("--wiki", type=Path, default=None)
    p.add_argument("--loop", action="store_true")
    p.add_argument("--interval-sec", type=int, default=60)
    p.add_argument(
        "--prefer",
        choices=("voyage", "local", "stub"),
        default="voyage",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    wiki = args.wiki if args.wiki is not None else default_wiki()

    if args.loop:
        while True:
            try:
                result = drain_once(wiki, prefer_embedder=args.prefer)
                print(json.dumps(result, default=str))
            except Exception as exc:
                print(f"drain_queue: {exc}", file=sys.stderr)
            time.sleep(args.interval_sec)
        # unreachable
        return 0

    result = drain_once(wiki, prefer_embedder=args.prefer)
    if args.json:
        print(json.dumps(result, default=str))
    else:
        print(
            f"processed={result.get('processed', 0)} "
            f"skipped_unchanged={result.get('skipped_unchanged', 0)} "
            f"errors={result.get('errors', 0)} "
            f"auth_missing={result.get('auth_missing', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
