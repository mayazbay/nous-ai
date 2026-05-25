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
import subprocess
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
WRITEBACK_LOCK_REL = Path(".git/library-drain-writeback.lock")
WRITEBACK_PATHS = (
    registry.REGISTRY_REL,
    Path(".gbrain/manifest.json"),
)


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


def _write_queue(wiki: Path, entries: list[dict[str, Any]]) -> None:
    """Replace the queue with residual entries. Caller MUST hold the drain lock."""
    target = _queue_path(wiki)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
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


def _tail(text: str, limit: int = 800) -> str:
    text = (text or "").strip()
    return text[-limit:] if len(text) > limit else text


@contextlib.contextmanager
def _with_writeback_lock(wiki: Path) -> Iterator[None]:
    """Serialize git write-back with other local drain invocations."""
    lock_path = wiki / WRITEBACK_LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _git(
    wiki: Path,
    args: list[str],
    *,
    timeout: int = 90,
    ok_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", "-C", str(wiki), "-c", "core.hooksPath=/dev/null", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode not in ok_returncodes:
        raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
    return proc


def _git_short(wiki: Path, ref: str = "HEAD") -> str:
    return _git(wiki, ["rev-parse", "--short", ref], timeout=30).stdout.strip()


def _remote_exists(wiki: Path, remote: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(wiki), "remote", "get-url", remote],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode == 0


def _fetch_remote_main_oid(wiki: Path, remote: str, timeout: int = 120) -> str:
    _git(wiki, ["fetch", remote, f"main:refs/remotes/{remote}/main"], timeout=timeout)
    return _git(wiki, ["rev-parse", "--verify", f"refs/remotes/{remote}/main"], timeout=30).stdout.strip()


def _rebase_onto_remote_main(wiki: Path, remote: str, timeout: int = 120) -> None:
    before = _git_short(wiki)
    target = _fetch_remote_main_oid(wiki, remote, timeout=timeout)
    contains = _git(
        wiki,
        ["merge-base", "--is-ancestor", target, "HEAD"],
        timeout=30,
        ok_returncodes=(0, 1),
    )
    if contains.returncode != 0:
        _git(wiki, ["rebase", target], timeout=timeout)

    target2 = _fetch_remote_main_oid(wiki, remote, timeout=timeout)
    if target2 != target:
        contains2 = _git(
            wiki,
            ["merge-base", "--is-ancestor", target2, "HEAD"],
            timeout=30,
            ok_returncodes=(0, 1),
        )
        if contains2.returncode != 0:
            _git(wiki, ["rebase", target2], timeout=timeout)
    after = _git_short(wiki)
    _append_log(wiki, f"exact rebase {remote}/main {before}->{after}")


def git_writeback(wiki: Path, *, remotes: list[str], message: str) -> dict[str, Any]:
    """Commit tracked library graph state and push it to configured remotes."""
    rel_paths = [str(path) for path in WRITEBACK_PATHS if (wiki / path).exists()]
    if not rel_paths:
        return {"ok": True, "status": "noop", "detail": "no tracked writeback paths exist"}

    with _with_writeback_lock(wiki):
        status = _git(
            wiki,
            ["status", "--porcelain", "--", *rel_paths],
            timeout=30,
        ).stdout.strip()
        if not status:
            return {"ok": True, "status": "noop", "detail": "no tracked library graph changes"}

        try:
            _git(wiki, ["add", "--", *rel_paths], timeout=30)
            diff = _git(
                wiki,
                ["diff", "--cached", "--quiet", "--", *rel_paths],
                timeout=30,
                ok_returncodes=(0, 1),
            )
            if diff.returncode == 0:
                return {"ok": True, "status": "noop", "detail": "no staged library graph changes"}
            _git(
                wiki,
                ["commit", "--no-verify", "--only", "-m", message, "--", *rel_paths],
                timeout=90,
            )
            pushed: list[str] = []
            skipped: list[str] = []
            for remote in remotes:
                remote = remote.strip()
                if not remote:
                    continue
                if not _remote_exists(wiki, remote):
                    skipped.append(remote)
                    continue
                _rebase_onto_remote_main(wiki, remote, timeout=120)
                try:
                    _git(wiki, ["push", remote, "main"], timeout=120)
                except subprocess.CalledProcessError as exc:
                    detail = exc.stderr or exc.stdout or ""
                    if "non-fast-forward" not in detail and "fetch first" not in detail:
                        raise
                    _rebase_onto_remote_main(wiki, remote, timeout=120)
                    _git(wiki, ["push", remote, "main"], timeout=120)
                pushed.append(remote)
            return {"ok": True, "status": "pushed", "pushed": pushed, "skipped": skipped}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": _tail(repr(exc), 1000)}


# ---------------------------------------------------------------------------
# Main drain
# ---------------------------------------------------------------------------


def drain_once(
    wiki: Path,
    *,
    prefer_embedder: str = "voyage",
    max_files: int = 0,
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
        "deferred_after_error": 0,
        "deferred_after_limit": 0,
        "files": [],
    }

    with _with_lock(wiki):
        entries = _read_queue(wiki)
        if not entries:
            return summary

        embedder = None  # lazy — only build when first needed
        auth_missing_hit = False
        defer_rest_error = ""
        residual_entries: list[dict[str, Any]] = []
        handled_files = 0

        for entry in entries:
            rel_path = entry["path"]
            abs_path = wiki / rel_path
            file_record: dict[str, Any] = {"path": rel_path}

            if max_files > 0 and handled_files >= max_files:
                file_record["status"] = "deferred_after_max_files"
                summary["deferred_after_limit"] += 1
                residual_entries.append(entry)
                summary["files"].append(file_record)
                continue

            if auth_missing_hit or defer_rest_error:
                # Don't process further files once we've established auth is
                # broken or the embedder is rate-limited/down. This keeps the
                # queue intact and avoids turning one upstream failure into
                # hundreds of repeated failed API calls.
                if auth_missing_hit:
                    file_record["status"] = "deferred_auth_missing"
                else:
                    file_record["status"] = f"deferred_after_{defer_rest_error}"
                    summary["deferred_after_error"] += 1
                residual_entries.append(entry)
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
                    handled_files += 1
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
                    handled_files += 1
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
                    residual_entries.append(entry)
                    auth_missing_hit = True
                    handled_files += 1
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
                    first_error = getattr(errored[0], "error", "")
                    summary["errors"] += 1
                    file_record["status"] = "embed_error"
                    file_record["error"] = first_error
                    summary["files"].append(file_record)
                    residual_entries.append(entry)
                    _append_log(
                        wiki,
                        f"embed error for {rel_path}: "
                        f"{file_record['error']} (embedder={getattr(embedder, 'name', '?')})",
                    )
                    if (
                        first_error in {"http_429", "timeout"}
                        or first_error.startswith("error: ")
                    ):
                        defer_rest_error = first_error
                        _append_log(
                            wiki,
                            f"deferring remaining queue after {first_error}; "
                            "queue left intact for next pass",
                        )
                    handled_files += 1
                    continue

                # 8. Init DB + insert chunks.
                dim = int(getattr(results[0], "dim", 0) or getattr(embedder, "dim", 0))
                model_name = str(getattr(results[0], "model", "") or getattr(embedder, "name", "unknown"))
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
                handled_files += 1

            except Exception as exc:  # per-file isolation
                summary["errors"] += 1
                file_record["status"] = "exception"
                file_record["error"] = repr(exc)
                summary["files"].append(file_record)
                residual_entries.append(entry)
                _append_log(wiki, f"exception draining {rel_path}: {exc!r}")
                handled_files += 1
                continue

        # Truncate decision:
        # - residual entries → preserve only failed/current + deferred rows
        # - no residual entries → truncate (all entries handled)
        #
        # Keeping the entire original queue on one http_429 makes the backlog
        # unable to shrink unless a full pass succeeds. The durable contract is
        # "do not lose work", not "retry already-handled rows forever".
        if residual_entries:
            _write_queue(wiki, residual_entries)
        else:
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
    p.add_argument(
        "--summary-json",
        action="store_true",
        help="Emit counts plus a small file sample, suitable for launchd logs.",
    )
    p.add_argument(
        "--max-files",
        type=int,
        default=int(os.environ.get("LIBRARY_DRAIN_MAX_FILES", "0")),
        help="Process at most N queue entries in one pass; 0 means no cap.",
    )
    p.add_argument(
        "--git-writeback",
        action="store_true",
        help="Commit and push tracked library graph state after a non-empty drain result.",
    )
    p.add_argument(
        "--git-push-remotes",
        default=os.environ.get("LIBRARY_DRAIN_GIT_PUSH_REMOTES", "vps,github"),
        help="Comma-separated remotes for --git-writeback. Default: vps,github.",
    )
    args = p.parse_args()

    wiki = args.wiki if args.wiki is not None else default_wiki()

    if args.loop:
        while True:
            try:
                result = drain_once(
                    wiki,
                    prefer_embedder=args.prefer,
                    max_files=args.max_files,
                )
                print(json.dumps(result, default=str))
            except Exception as exc:
                print(f"drain_queue: {exc}", file=sys.stderr)
            time.sleep(args.interval_sec)
        # unreachable
        return 0

    result = drain_once(wiki, prefer_embedder=args.prefer, max_files=args.max_files)
    if args.git_writeback and any(
        int(result.get(key, 0) or 0) > 0
        for key in ("processed", "skipped_unchanged", "errors", "auth_missing")
    ):
        remotes = [remote.strip() for remote in args.git_push_remotes.split(",") if remote.strip()]
        result["git_writeback"] = git_writeback(
            wiki,
            remotes=remotes,
            message="library-graph: record drain progress",
        )
    if args.summary_json:
        sample = result.get("files", [])[:10]
        compact = {k: v for k, v in result.items() if k != "files"}
        compact["file_sample"] = sample
        compact["file_count"] = len(result.get("files", []))
        print(json.dumps(compact, default=str))
    elif args.json:
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
