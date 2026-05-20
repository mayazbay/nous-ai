"""Bidirectional Obsidian ↔ OpenBrain (Nate B Jones) sync — Ship 3 wave 4.

The canonical registry (`tools/library_canonical_registry.py`) is the JOIN key
across the Obsidian vault, gbrain, and OpenBrain. This module materializes the
OpenBrain side of that join:

* **Up** — for every Obsidian markdown file in ``SYNC_DIRS`` whose ``content_hash``
  has drifted from the registry's recorded hash, fire-and-forget a
  ``capture_thought`` MCP call tagged ``nous-vault`` + ``<dir>`` +
  ``canonical:<uuid>``. We do NOT wait for the thought_id — the MCP daemon
  records it asynchronously, and ``sync_state.jsonl`` is the local audit
  receipt.

* **Down** — synchronously list thoughts tagged ``nous-vault-inbox`` via MCP
  ``search_thoughts``, then materialize each NEW one (i.e. no existing inbox
  file for that ``thought_id``) into ``pages/inbox/openbrain/YYYY-MM-DD-<id>.md``
  with ``status: needs-promotion`` frontmatter. The human (or a downstream
  promoter agent) decides where it lives.

* **Conflicts** — registry entries that have BOTH ``obsidian_path`` and
  ``openbrain_thought_ids`` AND whose current ``content_hash`` differs from
  what the registry recorded. Vault wins for body, OpenBrain wins for tags
  (informational — this module identifies, does not auto-resolve).

All MCP shell-outs are **fail-soft**: any subprocess error is logged to
``logs/openbrain-sync.log`` and never raised. Stdlib only.

CLI::

    python3 tools/library_openbrain_sync.py --direction both
    python3 tools/library_openbrain_sync.py --direction up --dry-run --json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from tools import library_canonical_registry as registry  # type: ignore
except ImportError:  # pragma: no cover — exercised by direct invocation
    HERE = Path(__file__).resolve().parent
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import library_canonical_registry as registry  # type: ignore

ALMATY = dt.timezone(dt.timedelta(hours=5))
INBOX_REL = Path("pages/inbox/openbrain")
CONFLICT_DIR_REL = Path("pages/library")
LOG_REL = Path("logs/openbrain-sync.log")
SYNC_STATE_REL = Path("pages/systems/openbrain-sync-state.jsonl")
SYNC_DIRS = (
    "pages/systems",
    "pages/skills",
    "pages/audits",
    "pages/plans",
    "pages/laws",
    "pages/concepts",
)

# Body cap matches what we publish to OpenBrain — they truncate long thoughts
# anyway, and 2 KB keeps the MCP payload + log lines small.
_BODY_CAP = 2000
_MCP_TIMEOUT_SECONDS = 10
_INBOX_TAG = "nous-vault-inbox"


def default_wiki() -> Path:
    """Resolve the wiki root from ``NOUS_WIKI`` or by walking from this file.

    Mirrors ``library_canonical_registry.default_wiki`` exactly so Mac/Air/VPS
    all converge on the same path semantics.
    """
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


# ---------------------------------------------------------------------------
# Logging + sync-state JSONL
# ---------------------------------------------------------------------------

def _log_path(wiki: Path) -> Path:
    return wiki / LOG_REL


def _sync_state_path(wiki: Path) -> Path:
    return wiki / SYNC_STATE_REL


def _append_log(wiki: Path, msg: str) -> None:
    """Append a single log line to ``logs/openbrain-sync.log``.

    Best-effort: failure here is silent, since this IS the failure channel.
    """
    path = _log_path(wiki)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = now_kzt().isoformat()
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{ts}\t{msg}\n")
    except OSError:
        # Logging must never raise. If even the log can't be written, drop it.
        pass


def _append_sync_state(wiki: Path, event: dict[str, Any]) -> None:
    """Append-only sync events at ``pages/systems/openbrain-sync-state.jsonl``.

    Each row is self-describing; downstream tools dedup by ``(direction, path)``
    or ``(direction, thought_id)`` as appropriate.
    """
    path = _sync_state_path(wiki)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, default=str)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:
        _append_log(wiki, f"sync_state write failed: {exc}")


def _load_sync_state(wiki: Path) -> list[dict[str, Any]]:
    """Read all sync_state events. Malformed lines are skipped."""
    path = _sync_state_path(wiki)
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return rows
    except OSError as exc:
        _append_log(wiki, f"sync_state read failed: {exc}")
        return rows
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _last_thought_id_for_path(wiki: Path, path: str) -> str | None:
    """Find the latest ``thought_id`` we queued for ``obsidian_path``.

    Used by ``detect_conflicts`` to know whether OpenBrain has ever seen this
    file. ``None`` if never synced.
    """
    last_id: str | None = None
    for event in _load_sync_state(wiki):
        if event.get("direction") != "up":
            continue
        if event.get("path") != path:
            continue
        tid = event.get("thought_id")
        if isinstance(tid, str) and tid:
            last_id = tid
    return last_id


# ---------------------------------------------------------------------------
# MCP shell-outs (fail-soft)
# ---------------------------------------------------------------------------

def _mcp_capture_thought(payload: dict[str, Any], log_path: Path) -> str:
    """Fire-and-forget MCP ``capture_thought`` call.

    We launch the MCP CLI in a new session, redirect stdout/stderr to the log
    file, and do NOT wait for the result. Returns the sentinel ``"queued"``
    on success, ``"failed"`` if even the ``Popen`` call raised — but it never
    re-raises. The actual ``thought_id`` is recovered later via
    ``_mcp_search_thoughts`` (or accepted as eventually-consistent).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # We pipe the payload via stdin so we don't pollute argv. The MCP
        # daemon for Nate B Jones' OpenBrain accepts JSON-on-stdin under the
        # `mcp call` convention. If the binary is missing, OSError → log + return.
        with open(log_path, "ab") as log_fh:
            proc = subprocess.Popen(
                [
                    "mcp",
                    "call",
                    "claude_ai_Open_Brain",
                    "capture_thought",
                ],
                stdin=subprocess.PIPE,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
            )
            try:
                proc.stdin.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                proc.stdin.close()
            except (OSError, BrokenPipeError) as exc:
                # The child may have exited before we wrote; log + move on.
                ts = now_kzt().isoformat()
                with open(log_path, "a", encoding="utf-8") as txt:
                    txt.write(f"{ts}\tcapture_thought stdin write failed: {exc}\n")
        return "queued"
    except (OSError, FileNotFoundError, subprocess.SubprocessError) as exc:
        ts = now_kzt().isoformat()
        try:
            with open(log_path, "a", encoding="utf-8") as txt:
                txt.write(f"{ts}\tcapture_thought Popen failed: {exc}\n")
        except OSError:
            pass
        return "failed"


def _mcp_search_thoughts(query: str, log_path: Path) -> list[dict[str, Any]]:
    """Synchronous MCP ``search_thoughts`` call. Returns ``[]`` on any failure.

    Times out at ``_MCP_TIMEOUT_SECONDS``. Never raises.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "mcp",
                "call",
                "claude_ai_Open_Brain",
                "search_thoughts",
                "--query",
                query,
            ],
            capture_output=True,
            timeout=_MCP_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        ts = now_kzt().isoformat()
        try:
            with open(log_path, "a", encoding="utf-8") as txt:
                txt.write(f"{ts}\tsearch_thoughts timed out: {exc}\n")
        except OSError:
            pass
        return []
    except (OSError, FileNotFoundError, subprocess.SubprocessError) as exc:
        ts = now_kzt().isoformat()
        try:
            with open(log_path, "a", encoding="utf-8") as txt:
                txt.write(f"{ts}\tsearch_thoughts failed: {exc}\n")
        except OSError:
            pass
        return []

    if result.stderr:
        try:
            with open(log_path, "ab") as fh:
                fh.write(result.stderr)
        except OSError:
            pass

    stdout = result.stdout or b""
    if not stdout.strip():
        return []
    try:
        parsed = json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        ts = now_kzt().isoformat()
        try:
            with open(log_path, "a", encoding="utf-8") as txt:
                txt.write(f"{ts}\tsearch_thoughts JSON decode failed: {exc}\n")
        except OSError:
            pass
        return []

    # Accept either a bare list or ``{"thoughts": [...]}``.
    if isinstance(parsed, list):
        return [t for t in parsed if isinstance(t, dict)]
    if isinstance(parsed, dict):
        thoughts = parsed.get("thoughts")
        if isinstance(thoughts, list):
            return [t for t in thoughts if isinstance(t, dict)]
    return []


# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------

def _iter_sync_files(wiki: Path) -> list[Path]:
    """All markdown files inside SYNC_DIRS, sorted for determinism."""
    out: list[Path] = []
    for rel in SYNC_DIRS:
        d = wiki / rel
        if not d.is_dir():
            continue
        for p in d.rglob("*.md"):
            if p.is_file():
                out.append(p)
    out.sort()
    return out


def _dir_label(rel_path: str) -> str:
    """Top-level directory name (e.g. ``pages/systems/foo.md`` → ``systems``)."""
    parts = Path(rel_path).parts
    if len(parts) >= 2 and parts[0] == "pages":
        return parts[1]
    return parts[0] if parts else "unknown"


def _read_body_capped(path: Path) -> str:
    """First ``_BODY_CAP`` characters of the file, or ``""`` on read failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return ""
    return text[:_BODY_CAP]


_FRONTMATTER_SAFE = re.compile(r"[\r\n]+")


def _frontmatter_value(value: str) -> str:
    """Sanitize a value for a single-line YAML scalar (no newlines)."""
    return _FRONTMATTER_SAFE.sub(" ", value).strip()


# ---------------------------------------------------------------------------
# sync_up — vault → OpenBrain
# ---------------------------------------------------------------------------

def sync_up(
    wiki: Path,
    *,
    dry_run: bool = False,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Walk SYNC_DIRS, queue ``capture_thought`` for files with drifted hashes.

    For each file:
      - If not in the registry, ``registry.add`` it (gets a fresh canonical uuid).
      - Compare current ``content_hash`` against the registry's recorded hash.
        Unchanged → skip.
      - Drifted → build payload, ``_mcp_capture_thought``, append sync_state.

    Returns counters + per-file list (``files``) for downstream reporting.
    """
    moment = now if now is not None else now_kzt()
    log_path = _log_path(wiki)
    queued = 0
    skipped = 0
    errors = 0
    file_events: list[dict[str, Any]] = []

    for abs_path in _iter_sync_files(wiki):
        try:
            rel = str(abs_path.relative_to(wiki))
        except ValueError:
            errors += 1
            continue

        try:
            current_hash = registry.file_content_hash(abs_path)
        except Exception as exc:  # pragma: no cover — file_content_hash is defensive already
            _append_log(wiki, f"hash failed for {rel}: {exc}")
            errors += 1
            continue

        try:
            entry = registry.get(path=rel, wiki=wiki)
        except Exception as exc:  # pragma: no cover
            _append_log(wiki, f"registry.get failed for {rel}: {exc}")
            errors += 1
            continue

        newly_added = False
        if entry is None:
            try:
                uid = registry.add(rel, wiki=wiki, now=moment)
                entry = registry.get(uuid=uid, wiki=wiki) or {"canonical_uuid": uid}
                newly_added = True
            except Exception as exc:
                _append_log(wiki, f"registry.add failed for {rel}: {exc}")
                errors += 1
                continue

        uid = entry.get("canonical_uuid", "")
        recorded_hash = entry.get("content_hash", "")

        # Skip only when the entry already existed AND the hash is stable.
        # A freshly-added entry has its content_hash populated by registry.add
        # at file-read time, which would otherwise look "stable" on the first
        # pass and never sync. We always queue the first sync for new entries.
        if (
            not newly_added
            and recorded_hash
            and recorded_hash == current_hash
        ):
            skipped += 1
            continue

        dir_label = _dir_label(rel)
        title = entry.get("title") or registry.title_from_path(abs_path)
        body = _read_body_capped(abs_path)
        payload: dict[str, Any] = {
            "type": "nous-vault",
            "title": title,
            "body": body,
            "tags": ["nous-vault", dir_label, f"canonical:{uid}"],
            "source_path": rel,
            "content_hash": current_hash,
        }

        status = "dry-run"
        if not dry_run:
            status = _mcp_capture_thought(payload, log_path)
            if status == "failed":
                errors += 1
            else:
                queued += 1
                # Bump the registry's recorded content_hash so unchanged-skip
                # works on the next call. The ``thought_id`` is filled in
                # later (when sync_down or a reconciliation pass observes it).
                try:
                    registry.update_field(
                        uid, "content_hash", current_hash, wiki=wiki, now=moment
                    )
                except Exception as exc:
                    _append_log(wiki, f"registry.update_field hash failed for {rel}: {exc}")
        else:
            queued += 1  # dry-run still counts as "would-queue"

        event = {
            "ts": moment.isoformat(),
            "direction": "up",
            "path": rel,
            "uuid": uid,
            "status": status,
            "content_hash": current_hash,
        }
        _append_sync_state(wiki, event)
        file_events.append({"path": rel, "uuid": uid, "status": status})

    return {
        "queued": queued,
        "skipped_unchanged": skipped,
        "errors": errors,
        "files": file_events,
    }


# ---------------------------------------------------------------------------
# sync_down — OpenBrain → vault inbox
# ---------------------------------------------------------------------------

_SAFE_FNAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_thought_id(thought_id: str) -> str:
    """Filesystem-safe slice of a thought_id (collapse anything non-alnum)."""
    cleaned = _SAFE_FNAME.sub("-", thought_id).strip("-")
    return cleaned or "unknown"


def _inbox_glob(wiki: Path, thought_id: str) -> bool:
    """True if any file matching ``*-<thought_id>.md`` already exists in inbox."""
    inbox = wiki / INBOX_REL
    if not inbox.exists():
        return False
    safe = _safe_thought_id(thought_id)
    for p in inbox.glob(f"*-{safe}.md"):
        if p.is_file():
            return True
    return False


def sync_down(
    wiki: Path,
    *,
    dry_run: bool = False,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Pull OpenBrain thoughts tagged ``nous-vault-inbox``, materialize NEW ones.

    Returns counters. For each thought:
      - Skip if an inbox file for that ``thought_id`` already exists.
      - Else write ``pages/inbox/openbrain/YYYY-MM-DD-<id>.md`` with
        frontmatter ``{type, status: needs-promotion, thought_id, received}``
        followed by the thought body.
    """
    moment = now if now is not None else now_kzt()
    log_path = _log_path(wiki)
    inbox = wiki / INBOX_REL
    inbox.mkdir(parents=True, exist_ok=True)

    thoughts = _mcp_search_thoughts(f"tag:{_INBOX_TAG}", log_path)

    materialized = 0
    skipped = 0
    errors = 0

    for thought in thoughts:
        if not isinstance(thought, dict):
            errors += 1
            continue
        thought_id_raw = thought.get("thought_id") or thought.get("id") or ""
        if not isinstance(thought_id_raw, str) or not thought_id_raw:
            errors += 1
            continue
        thought_id = _safe_thought_id(thought_id_raw)

        if _inbox_glob(wiki, thought_id_raw):
            skipped += 1
            continue

        title = thought.get("title") or thought.get("type") or "openbrain inbox"
        body = thought.get("body") or thought.get("content") or ""
        if not isinstance(body, str):
            try:
                body = json.dumps(body, ensure_ascii=False)
            except (TypeError, ValueError):
                body = str(body)

        date_str = moment.strftime("%Y-%m-%d")
        fname = f"{date_str}-{thought_id}.md"
        out_path = inbox / fname

        frontmatter_lines = [
            "---",
            "type: openbrain-inbox",
            "status: needs-promotion",
            f"thought_id: {_frontmatter_value(thought_id_raw)}",
            f"received: {moment.isoformat()}",
            f"title: {_frontmatter_value(str(title))}",
            "---",
            "",
        ]
        content = "\n".join(frontmatter_lines) + body
        if not content.endswith("\n"):
            content += "\n"

        if dry_run:
            materialized += 1
            event = {
                "ts": moment.isoformat(),
                "direction": "down",
                "thought_id": thought_id_raw,
                "status": "dry-run",
            }
            _append_sync_state(wiki, event)
            continue

        try:
            out_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            _append_log(wiki, f"inbox write failed for {thought_id_raw}: {exc}")
            errors += 1
            continue

        materialized += 1
        event = {
            "ts": moment.isoformat(),
            "direction": "down",
            "thought_id": thought_id_raw,
            "path": str(out_path.relative_to(wiki)),
            "status": "materialized",
        }
        _append_sync_state(wiki, event)

    return {
        "materialized": materialized,
        "skipped_existing": skipped,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# detect_conflicts — registry entries with drift across both substrates
# ---------------------------------------------------------------------------

def detect_conflicts(
    wiki: Path,
    *,
    now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """Find registry entries with both ``obsidian_path`` AND
    ``openbrain_thought_ids`` whose current ``content_hash`` differs from the
    registry's recorded hash. Writes a conflicts-of-the-day report under
    ``pages/library/openbrain-conflicts-YYYY-MM-DD.md`` (only if there are
    candidates). Returns the list of conflict dicts (possibly empty).

    Conservative: identifies candidates, does not auto-resolve. Vault wins for
    body, OpenBrain wins for tags — but that's a downstream operator decision.
    """
    moment = now if now is not None else now_kzt()
    try:
        entries = registry.list_all(wiki=wiki)
    except Exception as exc:  # pragma: no cover
        _append_log(wiki, f"registry.list_all failed: {exc}")
        return []

    conflicts: list[dict[str, Any]] = []
    for entry in entries:
        path = entry.get("obsidian_path")
        thought_ids = entry.get("openbrain_thought_ids") or []
        if not isinstance(path, str) or not path:
            continue
        if not isinstance(thought_ids, list) or not thought_ids:
            continue

        abs_path = wiki / path
        try:
            current_hash = registry.file_content_hash(abs_path)
        except Exception as exc:  # pragma: no cover
            _append_log(wiki, f"hash failed for {path}: {exc}")
            continue

        recorded = entry.get("content_hash") or ""
        if recorded and current_hash and recorded != current_hash:
            conflicts.append(
                {
                    "uuid": entry.get("canonical_uuid", ""),
                    "obsidian_path": path,
                    "openbrain_thought_ids": list(thought_ids),
                    "recorded_hash": recorded,
                    "current_hash": current_hash,
                    "title": entry.get("title", ""),
                }
            )

    if conflicts:
        report_path = (
            wiki / CONFLICT_DIR_REL / f"openbrain-conflicts-{moment.strftime('%Y-%m-%d')}.md"
        )
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                "---",
                "type: openbrain-conflicts",
                f"date: {moment.strftime('%Y-%m-%d')}",
                f"count: {len(conflicts)}",
                "---",
                "",
                f"# OpenBrain ↔ Vault conflicts — {moment.strftime('%Y-%m-%d')}",
                "",
                "Vault wins for body, OpenBrain wins for tags. Resolve manually.",
                "",
            ]
            for c in conflicts:
                lines.append(
                    f"- `{c['obsidian_path']}` "
                    f"(uuid `{c['uuid']}`, "
                    f"thoughts {c['openbrain_thought_ids']}) — "
                    f"recorded `{c['recorded_hash'][:18]}…` vs "
                    f"current `{c['current_hash'][:18]}…`"
                )
            lines.append("")
            report_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError as exc:
            _append_log(wiki, f"conflict report write failed: {exc}")

    return conflicts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Bidirectional Obsidian ↔ OpenBrain sync"
    )
    p.add_argument("--wiki", type=Path, default=None)
    p.add_argument(
        "--direction",
        choices=("up", "down", "both"),
        default="both",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    wiki = args.wiki or default_wiki()
    result: dict[str, Any] = {"up": None, "down": None, "conflicts": None}

    if args.direction in ("up", "both"):
        result["up"] = sync_up(wiki, dry_run=args.dry_run)
    if args.direction in ("down", "both"):
        result["down"] = sync_down(wiki, dry_run=args.dry_run)
    if args.direction == "both":
        result["conflicts"] = detect_conflicts(wiki)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, default=str))
    else:
        up = result.get("up")
        if up:
            print(
                f"up: queued={up.get('queued', 0)} "
                f"skipped={up.get('skipped_unchanged', 0)} "
                f"errors={up.get('errors', 0)}"
            )
        down = result.get("down")
        if down:
            print(
                f"down: materialized={down.get('materialized', 0)} "
                f"skipped={down.get('skipped_existing', 0)} "
                f"errors={down.get('errors', 0)}"
            )
        conflicts = result.get("conflicts")
        if conflicts is not None:
            print(f"conflicts: {len(conflicts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
