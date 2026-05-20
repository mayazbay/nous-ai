"""Canonical UUID registry CRUD — Ship 3 wave 1a of the library failover plan.

Maps ``canonical_uuid`` ↔ ``obsidian_path`` (+ aliases + content_hash + future
gbrain chunk IDs + future OpenBrain thought IDs). The registry is the JOIN key
across the Obsidian vault, the gbrain vector DB (Ship 3 wave 2), and the
Nate-B-Jones OpenBrain thought log.

State files:

* Append-only JSONL: ``pages/systems/canonical-registry.jsonl``
  (newest-last; same pattern as ``tools/queue.py`` event_seq).
* fcntl lock:        ``logs/canonical-registry.lock``

Each row is a self-contained snapshot of the entry's state at that moment;
the "current" view is derived by reducing rows to most-recent per
``canonical_uuid``. This matches the queue.py durable-substrate pattern and
keeps the file safe to rsync without coordination.

CLI::

    python3 tools/library_canonical_registry.py add --path foo.md
    python3 tools/library_canonical_registry.py get --path foo.md [--field title|--json]
    python3 tools/library_canonical_registry.py get --uuid <ulid>
    python3 tools/library_canonical_registry.py get --alias my-doc
    python3 tools/library_canonical_registry.py update --uuid <ulid> --field title --value "New"
    python3 tools/library_canonical_registry.py list [--json]
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import secrets
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterator

ALMATY = dt.timezone(dt.timedelta(hours=5))
REGISTRY_REL = Path("pages/systems/canonical-registry.jsonl")
LOCK_REL = Path("logs/canonical-registry.lock")

# Crockford base32 alphabet — no I, L, O, U.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Fields that may be mutated via update_field. Everything else (canonical_uuid,
# slug, obsidian_path, created) is read-only.
_ALLOWED_UPDATE_FIELDS = frozenset(
    {
        "title",
        "aliases",
        "gbrain_chunk_ids",
        "openbrain_thought_ids",
        "content_hash",
        "embed_model",
        "embed_dim",
    }
)

# sha256 of the empty byte string — sentinel for missing files.
_EMPTY_SHA256 = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# ---------------------------------------------------------------------------
# Path resolution helpers (mirrors tools/queue.py default_wiki / now_kzt)
# ---------------------------------------------------------------------------

def default_wiki() -> Path:
    """Resolve the wiki root from NOUS_WIKI, or by walking from this file.

    Mirrors ``tools/queue.py::default_wiki`` exactly so Mac/Air/VPS all
    converge on the same path semantics.
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


def _resolve_wiki(wiki: Path | None) -> Path:
    return wiki if wiki is not None else default_wiki()


def _registry_path(wiki: Path) -> Path:
    return wiki / REGISTRY_REL


def _lock_path(wiki: Path) -> Path:
    return wiki / LOCK_REL


def _ensure_dirs(wiki: Path) -> None:
    _registry_path(wiki).parent.mkdir(parents=True, exist_ok=True)
    _lock_path(wiki).parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# ULID — Crockford base32, monotonic-sortable. Stdlib only.
# ---------------------------------------------------------------------------

def _b32_encode(value: int, length: int) -> str:
    """Encode ``value`` as Crockford base32, zero-padded to ``length`` chars."""
    if value < 0:
        raise ValueError("value must be non-negative")
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    if value != 0:
        raise ValueError(f"value does not fit in {length} base32 chars")
    return "".join(reversed(out))


def generate_ulid(*, now: dt.datetime | None = None) -> str:
    """Generate a Crockford-base32 ULID (26 chars, monotonic-sortable).

    Format: 10-char timestamp (48-bit ms since epoch, base32) + 16-char
    randomness (80 bits, ``secrets.randbits``). Reference: ulid/spec on
    GitHub — implemented inline (stdlib only).

    Note: monotonicity across rapid successive calls relies on millisecond
    granularity of the timestamp prefix and the lexicographic sort property
    of Crockford base32. For sub-ms collisions we degrade gracefully because
    the 80-bit random suffix makes within-ms collision astronomically rare.
    """
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)
    ms = int(moment.timestamp() * 1000)
    if ms < 0 or ms >= (1 << 48):
        raise ValueError("timestamp out of 48-bit range")
    ts_part = _b32_encode(ms, 10)
    rand_part = _b32_encode(secrets.randbits(80), 16)
    return ts_part + rand_part


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def file_content_hash(path: Path) -> str:
    """Return ``sha256:<hex>`` for the bytes of ``path``.

    Missing files return the sentinel empty-bytes hash (so the registry can
    still hold a row before the actual file lands on disk; useful for
    placeholders + tests). Reads in 64 KB chunks to stay memory-bounded.
    """
    path = Path(path)
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                h.update(chunk)
    except FileNotFoundError:
        return _EMPTY_SHA256
    except OSError as exc:
        print(
            f"library_canonical_registry: OSError hashing {path}: {exc}",
            file=sys.stderr,
        )
        return _EMPTY_SHA256
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# Slug + title derivation
# ---------------------------------------------------------------------------

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9-]+")
_SLUG_DASH_RUN = re.compile(r"-+")
_FRONTMATTER_TITLE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
_H1_LINE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def slugify(title: str) -> str:
    """Lowercase kebab-case slug from an arbitrary title.

    Steps:
      1. Unicode NFKD normalize + strip combining marks (so "Café" → "cafe").
      2. Lowercase.
      3. Replace whitespace + underscores with dashes.
      4. Drop everything not in ``[a-z0-9-]``.
      5. Collapse multiple dashes to one.
      6. Strip leading/trailing dashes.
    """
    if not title:
        return ""
    normalized = unicodedata.normalize("NFKD", title)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    lowered = stripped.lower()
    # Convert whitespace + underscores to dashes BEFORE dropping non-alnum
    # so the dashes survive into the cleanup step.
    dashed = re.sub(r"[\s_]+", "-", lowered)
    cleaned = _SLUG_NON_ALNUM.sub("", dashed)
    collapsed = _SLUG_DASH_RUN.sub("-", cleaned)
    return collapsed.strip("-")


def _title_from_filename(path: Path) -> str:
    """Derive a title from a filename: strip extension, dash→space, title-case."""
    stem = path.stem
    if not stem:
        return ""
    spaced = re.sub(r"[-_]+", " ", stem).strip()
    if not spaced:
        return ""
    # Title-case each whitespace-separated word.
    return " ".join(word[:1].upper() + word[1:] for word in spaced.split())


def title_from_path(path: Path) -> str:
    """Derive a title for an Obsidian markdown file.

    Resolution order:
      1. If file starts with ``---`` frontmatter block, parse the first
         ``title:`` line inside that block and return its value.
      2. Else: scan for the first H1 (``# Heading``) and return its content.
      3. Else (or file missing): derive from ``path.stem``.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return _title_from_filename(path)
    except UnicodeDecodeError:
        return _title_from_filename(path)

    # Frontmatter scan
    if text.startswith("---\n") or text.startswith("---\r\n"):
        # Find the closing fence.
        # Skip the opening fence line.
        after_open = text.split("\n", 1)[1] if "\n" in text else ""
        close_idx = after_open.find("\n---")
        if close_idx >= 0:
            fm_block = after_open[:close_idx]
            m = _FRONTMATTER_TITLE.search(fm_block)
            if m:
                value = m.group(1).strip()
                # Trim wrapping quotes if present.
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                if value:
                    return value

    # H1 scan
    m = _H1_LINE.search(text)
    if m:
        value = m.group(1).strip()
        if value:
            return value

    return _title_from_filename(path)


# ---------------------------------------------------------------------------
# Lock + JSONL IO
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _with_lock(wiki: Path) -> Iterator[None]:
    """Context manager that takes fcntl.LOCK_EX on the registry lock file."""
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


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append a row to the registry JSONL. Caller MUST hold the registry lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as fh:
        # Inner advisory lock — belt + suspenders (matches queue.py pattern).
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _load_registry(wiki: Path) -> list[dict[str, Any]]:
    """Read ALL rows from the registry JSONL.

    Malformed lines are logged to stderr and skipped (matches queue.py's
    row-tolerant reader pattern from session-coordination v1.31+).
    """
    path = _registry_path(wiki)
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return rows
    except OSError as exc:
        print(
            f"library_canonical_registry: OSError reading {path}: {exc}",
            file=sys.stderr,
        )
        return rows
    for lineno, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            print(
                f"library_canonical_registry: skipping malformed line {lineno}: {exc}",
                file=sys.stderr,
            )
            continue
        if not isinstance(obj, dict):
            print(
                f"library_canonical_registry: skipping non-object line {lineno}",
                file=sys.stderr,
            )
            continue
        rows.append(obj)
    return rows


def _latest_per_uuid(rows: list[dict]) -> dict[str, dict]:
    """Reduce rows to most-recent state per ``canonical_uuid``.

    Last-write-wins by file position (rows are append-only newest-last).
    Rows lacking a string ``canonical_uuid`` are silently dropped.
    """
    by_uuid: dict[str, dict] = {}
    for r in rows:
        uid = r.get("canonical_uuid")
        if not isinstance(uid, str) or not uid:
            continue
        by_uuid[uid] = dict(r)
    return by_uuid


# ---------------------------------------------------------------------------
# Public CRUD API
# ---------------------------------------------------------------------------

def _default_aliases(obsidian_path: str, title: str) -> list[str]:
    """Build the default alias list for a new entry."""
    stem = Path(obsidian_path).stem
    slug = slugify(title)
    seen: set[str] = set()
    result: list[str] = []
    for candidate in (stem, slug):
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


def add(
    obsidian_path: str,
    *,
    title: str | None = None,
    aliases: list[str] | None = None,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> str:
    """Register an obsidian_path. Returns its canonical_uuid.

    Idempotent: calling ``add`` twice with the same ``obsidian_path`` returns
    the existing canonical_uuid and does NOT append a second row.

    Otherwise:
      - Generate a fresh ULID.
      - Derive title via ``title_from_path`` if not provided.
      - Compute content_hash from the file.
      - Aliases default to ``[path.stem, slugify(title)]`` (deduplicated).
      - Append a new row with ``created == updated == now``.
    """
    wiki_path = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_lock(wiki_path):
        rows = _load_registry(wiki_path)
        current = _latest_per_uuid(rows)
        # Idempotency: search by obsidian_path.
        for uid, entry in current.items():
            if entry.get("obsidian_path") == obsidian_path:
                return uid

        derived_title = title if title is not None else title_from_path(
            wiki_path / obsidian_path
        )
        if not derived_title:
            derived_title = _title_from_filename(Path(obsidian_path))
        slug = slugify(derived_title)
        content_hash = file_content_hash(wiki_path / obsidian_path)
        alias_list = (
            list(aliases) if aliases is not None else _default_aliases(obsidian_path, derived_title)
        )
        # Dedup aliases while preserving order.
        seen: set[str] = set()
        deduped_aliases: list[str] = []
        for a in alias_list:
            if isinstance(a, str) and a and a not in seen:
                seen.add(a)
                deduped_aliases.append(a)

        uid = generate_ulid(now=moment)
        ts = moment.isoformat()
        row: dict[str, Any] = {
            "canonical_uuid": uid,
            "title": derived_title,
            "slug": slug,
            "obsidian_path": obsidian_path,
            "content_hash": content_hash,
            "gbrain_chunk_ids": [],
            "openbrain_thought_ids": [],
            "aliases": deduped_aliases,
            "created": ts,
            "updated": ts,
            "embed_model": "",
            "embed_dim": 0,
        }
        _append_jsonl(_registry_path(wiki_path), row)
        return uid


def get(
    *,
    uuid: str | None = None,
    path: str | None = None,
    alias: str | None = None,
    wiki: Path | None = None,
) -> dict[str, Any] | None:
    """Look up a registry entry by uuid, obsidian_path, or alias.

    Exactly one of ``{uuid, path, alias}`` must be set. Returns ``None`` if
    the entry is not found.
    """
    provided = [x for x in (uuid, path, alias) if x is not None]
    if len(provided) != 1:
        raise ValueError("exactly one of {uuid, path, alias} must be set")

    wiki_path = _resolve_wiki(wiki)
    rows = _load_registry(wiki_path)
    current = _latest_per_uuid(rows)

    if uuid is not None:
        return current.get(uuid)

    if path is not None:
        for entry in current.values():
            if entry.get("obsidian_path") == path:
                return entry
        return None

    # alias lookup
    for entry in current.values():
        aliases_field = entry.get("aliases")
        if isinstance(aliases_field, list) and alias in aliases_field:
            return entry
    return None


def update_field(
    uuid: str,
    field: str,
    value: Any,
    *,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> bool:
    """Update one field on the entry. Appends a new row reflecting the change.

    Allowed fields: ``title``, ``aliases``, ``gbrain_chunk_ids``,
    ``openbrain_thought_ids``, ``content_hash``, ``embed_model``, ``embed_dim``.

    Read-only fields (``canonical_uuid``, ``slug``, ``obsidian_path``,
    ``created``) are rejected — returns ``False`` without appending a row.

    Returns ``False`` if ``uuid`` is unknown OR ``field`` is not allowed.
    """
    if field not in _ALLOWED_UPDATE_FIELDS:
        return False

    wiki_path = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    with _with_lock(wiki_path):
        rows = _load_registry(wiki_path)
        current = _latest_per_uuid(rows)
        entry = current.get(uuid)
        if entry is None:
            return False

        new_row = dict(entry)
        new_row[field] = value
        # If title is updated, recompute slug too. The slug field is
        # read-only via update_field, but it derives from title, so we keep
        # it consistent inside the row.
        if field == "title" and isinstance(value, str):
            new_row["slug"] = slugify(value)
        new_row["updated"] = moment.isoformat()
        _append_jsonl(_registry_path(wiki_path), new_row)
        return True


def list_all(*, wiki: Path | None = None) -> list[dict[str, Any]]:
    """Return current state of every registry entry, sorted by ``created``."""
    wiki_path = _resolve_wiki(wiki)
    rows = _load_registry(wiki_path)
    current = _latest_per_uuid(rows)
    out = list(current.values())
    out.sort(key=lambda r: r.get("created") or "")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical registry CRUD")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("--path", required=True)
    p_add.add_argument("--title")
    p_add.add_argument("--alias", action="append", default=[])

    p_get = sub.add_parser("get")
    g = p_get.add_mutually_exclusive_group(required=True)
    g.add_argument("--uuid")
    g.add_argument("--path")
    g.add_argument("--alias")
    p_get.add_argument("--field", help="If set, print only this field's value")
    p_get.add_argument("--json", action="store_true")

    p_update = sub.add_parser("update")
    p_update.add_argument("--uuid", required=True)
    p_update.add_argument("--field", required=True)
    p_update.add_argument("--value", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--json", action="store_true")

    args = parser.parse_args()
    wiki = default_wiki()

    if args.cmd == "add":
        uuid = add(args.path, title=args.title, aliases=args.alias or None, wiki=wiki)
        print(uuid)
        return 0
    elif args.cmd == "get":
        entry = get(uuid=args.uuid, path=args.path, alias=args.alias, wiki=wiki)
        if entry is None:
            return 1
        if args.field:
            value = entry.get(args.field, "")
            if isinstance(value, list):
                print(" ".join(str(v) for v in value))
            else:
                print(value)
        elif args.json:
            print(json.dumps(entry, ensure_ascii=False))
        else:
            for k, v in entry.items():
                print(f"{k}: {v}")
        return 0
    elif args.cmd == "update":
        # Parse value as JSON if possible (for lists/dicts), else literal string.
        try:
            parsed = json.loads(args.value)
        except json.JSONDecodeError:
            parsed = args.value
        ok = update_field(args.uuid, args.field, parsed, wiki=wiki)
        return 0 if ok else 1
    elif args.cmd == "list":
        entries = list_all(wiki=wiki)
        if args.json:
            print(json.dumps(entries, ensure_ascii=False))
        else:
            for e in entries:
                print(f"{e['canonical_uuid']}  {e['obsidian_path']}  '{e['title']}'")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
