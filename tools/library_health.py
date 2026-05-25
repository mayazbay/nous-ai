"""Library health dashboard — Ship 3 wave 6 of the library failover plan.

Computes a JSON snapshot + Markdown dashboard of unified library state across the
Obsidian vault, the canonical UUID registry (wave 1), the gbrain vector DB
(wave 2), the audit reports (waves 5a/5b), and the model-failover ledger.

Outputs (both written atomically via temp + ``os.replace``):

* ``pages/systems/library-health.json`` — machine-readable snapshot.
* ``pages/systems/LIBRARY-HEALTH.md``  — human-readable dashboard.

Every field is fail-soft: a missing or malformed input degrades to 0 / False /
None / "" rather than raising. This keeps the dashboard usable when only some
substrates have been bootstrapped (Mac dev, fresh Air checkout, VPS rebuild).

CLI::

    python3 tools/library_health.py                       # write both + print MD
    python3 tools/library_health.py --json                # write both + print JSON
    python3 tools/library_health.py --no-write            # print MD only
    python3 tools/library_health.py --no-write --json     # print JSON only
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any

ALMATY = dt.timezone(dt.timedelta(hours=5))
HEALTH_JSON_REL = Path("pages/systems/library-health.json")
HEALTH_MD_REL = Path("pages/systems/LIBRARY-HEALTH.md")

# Relative locations on the vault filesystem.
PAGES_REL = Path("pages")
LIBRARY_REL = Path("pages") / "library"
GBRAIN_DB_REL = Path(".gbrain") / "index.db"
GBRAIN_QUEUE_REL = Path(".gbrain") / "queue.jsonl"
GBRAIN_MANIFEST_REL = Path(".gbrain") / "manifest.json"
FAILOVER_LATEST_REL = Path("pages/systems/MODEL-FAILOVER-LATEST.md")
PARITY_LATEST_REL = Path("pages/systems/parity-latest.json")


# ---------------------------------------------------------------------------
# Path resolution helpers (mirrors tools/queue.py / library_canonical_registry)
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


# ---------------------------------------------------------------------------
# Fail-soft counters
# ---------------------------------------------------------------------------

def count_obsidian_files(wiki: Path) -> int:
    """Count ``*.md`` files under ``pages/``. Fail-soft: 0 if pages/ missing."""
    pages = wiki / PAGES_REL
    if not pages.is_dir():
        return 0
    try:
        return sum(1 for _ in pages.rglob("*.md"))
    except OSError as exc:
        print(f"library_health: count_obsidian_files OSError: {exc}", file=sys.stderr)
        return 0


def count_canonical_registry(wiki: Path) -> int:
    """Count current-state size via library_canonical_registry.list_all (latest per uuid)."""
    try:
        try:
            from tools import library_canonical_registry as reg  # package import
        except ImportError:
            import library_canonical_registry as reg  # type: ignore[no-redef]
        return len(reg.list_all(wiki=wiki))
    except Exception as exc:  # noqa: BLE001 — fail-soft
        print(f"library_health: count_canonical_registry: {exc}", file=sys.stderr)
        return 0


def count_gbrain_state(wiki: Path) -> dict[str, Any]:
    """Probe gbrain on-disk state.

    Returns a dict with keys:
        indexed_chunks: int           — count_chunks() of chunks table, 0 if missing
        pending_queue: int            — lines in .gbrain/queue.jsonl, 0 if missing
        db_exists: bool               — .gbrain/index.db exists on disk
        sqlite_vec_loaded: bool       — manifest.json says sqlite_vec_loaded
    """
    db_path = wiki / GBRAIN_DB_REL
    queue_path = wiki / GBRAIN_QUEUE_REL
    manifest_path = wiki / GBRAIN_MANIFEST_REL

    state: dict[str, Any] = {
        "indexed_chunks": 0,
        "pending_queue": 0,
        "db_exists": False,
        "sqlite_vec_loaded": False,
    }

    state["db_exists"] = db_path.exists()

    # indexed_chunks via library_embed_db.count_chunks (DB-existence-tolerant).
    try:
        try:
            from tools import library_embed_db as edb  # package import
        except ImportError:
            import library_embed_db as edb  # type: ignore[no-redef]
        state["indexed_chunks"] = int(edb.count_chunks(wiki))
    except Exception as exc:  # noqa: BLE001 — fail-soft
        print(f"library_health: count_gbrain_state chunks: {exc}", file=sys.stderr)
        state["indexed_chunks"] = 0

    # pending_queue = non-empty line count in .gbrain/queue.jsonl.
    if queue_path.exists():
        try:
            count = 0
            with queue_path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        count += 1
            state["pending_queue"] = count
        except OSError as exc:
            print(f"library_health: queue read OSError: {exc}", file=sys.stderr)
            state["pending_queue"] = 0

    # sqlite_vec_loaded from manifest.json.
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            state["sqlite_vec_loaded"] = bool(data.get("sqlite_vec_loaded"))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"library_health: manifest read: {exc}", file=sys.stderr)
            state["sqlite_vec_loaded"] = False

    return state


# ---------------------------------------------------------------------------
# Audit pointers
# ---------------------------------------------------------------------------

_AUDIT_DATE_RE = re.compile(r"^(?P<prefix>[a-z0-9-]+)-(?P<date>\d{4}-\d{2}-\d{2})\.md$")
_BROKEN_TARGET_RE = re.compile(r"\[\[([^\]|#]+?)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")


def find_latest_audit(wiki: Path, prefix: str) -> tuple[Path | None, int]:
    """Find the newest ``pages/library/{prefix}-YYYY-MM-DD.md``.

    Returns ``(relative_path, count)`` or ``(None, 0)`` if no audit file exists.

    For ``prefix == "broken-links"`` the count is the number of unique broken
    targets (deduped ``[[wikilink]]`` targets) in the audit file body.

    For ``prefix == "title-drift"`` the count is the number of drift rows
    (markdown table rows excluding header + separator).

    Fail-soft for any unknown prefix: still returns the latest matching file
    with count=0.
    """
    library_dir = wiki / LIBRARY_REL
    if not library_dir.is_dir():
        return (None, 0)

    candidates: list[tuple[str, Path]] = []
    try:
        for entry in library_dir.iterdir():
            if not entry.is_file():
                continue
            m = _AUDIT_DATE_RE.match(entry.name)
            if not m:
                continue
            if m.group("prefix") != prefix:
                continue
            candidates.append((m.group("date"), entry))
    except OSError as exc:
        print(f"library_health: find_latest_audit OSError: {exc}", file=sys.stderr)
        return (None, 0)

    if not candidates:
        return (None, 0)

    # Newest by YYYY-MM-DD date string (lex sort works for this format).
    candidates.sort(key=lambda t: t[0])
    _, newest = candidates[-1]

    try:
        rel = newest.relative_to(wiki)
    except ValueError:
        rel = newest  # absolute fallback — caller should not hit this on-tree

    try:
        body = newest.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"library_health: audit read OSError: {exc}", file=sys.stderr)
        return (rel, 0)

    if prefix == "broken-links":
        unique_targets: set[str] = set()
        for m in _BROKEN_TARGET_RE.finditer(body):
            target = m.group(1).strip()
            if target:
                unique_targets.add(target)
        return (rel, len(unique_targets))

    if prefix == "title-drift":
        count = 0
        for line in body.splitlines():
            if not _TABLE_ROW_RE.match(line):
                continue
            # Skip header rows (any line whose pipe-cells are all dashes/colons +
            # whitespace) and the heading row that immediately precedes them.
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{1,}:?", c) for c in cells if c):
                # separator row — drop the prior header row too by decrementing
                if count > 0:
                    count -= 1
                continue
            count += 1
        return (rel, max(count, 0))

    return (rel, 0)


# ---------------------------------------------------------------------------
# Failover + parity pointers
# ---------------------------------------------------------------------------

_STATUS_LINE_RE = re.compile(r"^status:\s*([^\n\r]+)$", re.MULTILINE | re.IGNORECASE)


def latest_failover_status(wiki: Path) -> str | None:
    """Read ``pages/systems/MODEL-FAILOVER-LATEST.md`` and return the ``status`` field.

    Looks for a frontmatter line ``status: <value>``. Returns ``None`` if the
    file is absent or no status line is found.
    """
    path = wiki / FAILOVER_LATEST_REL
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"library_health: failover read OSError: {exc}", file=sys.stderr)
        return None
    # Restrict status lookup to the frontmatter block when present.
    if text.startswith("---"):
        after = text.split("\n", 1)[1] if "\n" in text else ""
        close = after.find("\n---")
        block = after[:close] if close >= 0 else after
    else:
        block = text
    m = _STATUS_LINE_RE.search(block)
    if not m:
        return None
    return m.group(1).strip() or None


def parity_hash(wiki: Path) -> str:
    """Return first 12 hex chars of ``parity-latest.json::manifest_sha256``.

    Empty string if the file is missing, malformed, or the field is absent.
    """
    path = wiki / PARITY_LATEST_REL
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"library_health: parity read: {exc}", file=sys.stderr)
        return ""
    value = data.get("manifest_sha256")
    if not isinstance(value, str):
        return ""
    return value[:12]


# ---------------------------------------------------------------------------
# Snapshot composition
# ---------------------------------------------------------------------------

def compute(wiki: Path, *, now: dt.datetime | None = None) -> dict[str, Any]:
    """Build the JSON snapshot. Fail-soft for every field."""
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    gbrain = count_gbrain_state(wiki)
    bl_path, bl_count = find_latest_audit(wiki, "broken-links")
    td_path, td_count = find_latest_audit(wiki, "title-drift")

    snapshot: dict[str, Any] = {
        "ts": moment.isoformat(),
        "host": socket.gethostname(),
        "obsidian_files": count_obsidian_files(wiki),
        "canonical_registry_size": count_canonical_registry(wiki),
        "gbrain_indexed_chunks": gbrain["indexed_chunks"],
        "gbrain_pending_queue": gbrain["pending_queue"],
        "gbrain_db_exists": gbrain["db_exists"],
        "gbrain_sqlite_vec_loaded": gbrain["sqlite_vec_loaded"],
        "openbrain_thoughts_local_cache": None,
        "broken_links_last_audit": bl_path.as_posix() if bl_path else None,
        "broken_links_count_last_audit": bl_count,
        "title_drift_last_audit": td_path.as_posix() if td_path else None,
        "title_drift_count_last_audit": td_count,
        "latest_failover_event_status": latest_failover_status(wiki),
        "parity_manifest_sha256": parity_hash(wiki),
    }
    return snapshot


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

_DASHBOARD_KEY_ORDER: tuple[str, ...] = (
    "ts",
    "host",
    "obsidian_files",
    "canonical_registry_size",
    "gbrain_indexed_chunks",
    "gbrain_pending_queue",
    "gbrain_db_exists",
    "gbrain_sqlite_vec_loaded",
    "openbrain_thoughts_local_cache",
    "broken_links_last_audit",
    "broken_links_count_last_audit",
    "title_drift_last_audit",
    "title_drift_count_last_audit",
    "latest_failover_event_status",
    "parity_manifest_sha256",
)


def _md_cell(value: Any) -> str:
    """Render a Python value for a markdown table cell."""
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    if isinstance(value, (int, float)):
        return f"`{value}`"
    return f"`{value}`"


def render_markdown(snapshot: dict[str, Any]) -> str:
    """Render the JSON snapshot as a Markdown dashboard.

    Sections:
      YAML frontmatter
      # LIBRARY-HEALTH
      ## Snapshot  (table of key:value)
      ## Detail    (sub-bullets per subsystem)
      ## See also  (links to source pages)
    """
    rows = []
    ts = str(snapshot.get("ts", ""))
    date = ts[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", ts) else now_kzt().date().isoformat()
    rows.append("---")
    rows.append("type: system")
    rows.append("id: LIBRARY-HEALTH")
    rows.append('title: "LIBRARY-HEALTH"')
    rows.append(f"date: {date}")
    rows.append("status: active")
    rows.append("generated_by: tools/library_health.py")
    rows.append("---")
    rows.append("")
    rows.append("# LIBRARY-HEALTH")
    rows.append("")
    rows.append(
        f"_Snapshot at {snapshot.get('ts', '')} on `{snapshot.get('host', '')}`. "
        "Generated by `tools/library_health.py` — fail-soft for every field._"
    )
    rows.append("")
    rows.append("## Snapshot")
    rows.append("")
    rows.append("| key | value |")
    rows.append("| --- | --- |")
    for key in _DASHBOARD_KEY_ORDER:
        if key not in snapshot:
            continue
        rows.append(f"| `{key}` | {_md_cell(snapshot[key])} |")
    # Render any extra keys we don't know about, at the end.
    for key in sorted(snapshot.keys()):
        if key in _DASHBOARD_KEY_ORDER:
            continue
        rows.append(f"| `{key}` | {_md_cell(snapshot[key])} |")

    rows.append("")
    rows.append("## Detail")
    rows.append("")
    rows.append("### Obsidian vault")
    rows.append("")
    rows.append(f"- `{snapshot.get('obsidian_files', 0)}` markdown files under `pages/`.")
    rows.append("")
    rows.append("### Canonical registry (Ship 3 wave 1)")
    rows.append("")
    rows.append(
        f"- `{snapshot.get('canonical_registry_size', 0)}` entries (latest-per-uuid in "
        "`pages/systems/canonical-registry.jsonl`)."
    )
    rows.append("")
    rows.append("### gbrain vector store (Ship 3 wave 2)")
    rows.append("")
    rows.append(f"- db_exists: {_md_cell(snapshot.get('gbrain_db_exists', False))}")
    rows.append(
        f"- sqlite_vec_loaded: {_md_cell(snapshot.get('gbrain_sqlite_vec_loaded', False))}"
    )
    rows.append(
        f"- indexed_chunks: {_md_cell(snapshot.get('gbrain_indexed_chunks', 0))}"
    )
    rows.append(
        f"- pending_queue: {_md_cell(snapshot.get('gbrain_pending_queue', 0))}"
    )
    rows.append("")
    rows.append("### Audits (Ship 3 waves 5a / 5b)")
    rows.append("")
    rows.append(
        "- broken-links: "
        f"{_md_cell(snapshot.get('broken_links_last_audit'))} "
        f"({snapshot.get('broken_links_count_last_audit', 0)} unique targets)"
    )
    rows.append(
        "- title-drift: "
        f"{_md_cell(snapshot.get('title_drift_last_audit'))} "
        f"({snapshot.get('title_drift_count_last_audit', 0)} drift rows)"
    )
    rows.append("")
    rows.append("### Model failover (Ship 1)")
    rows.append("")
    rows.append(
        "- latest event status: "
        f"{_md_cell(snapshot.get('latest_failover_event_status'))}"
    )
    rows.append("")
    rows.append("### Parity manifest (Ship 1 Step 7)")
    rows.append("")
    rows.append(
        f"- manifest_sha256 (first 12): {_md_cell(snapshot.get('parity_manifest_sha256', ''))}"
    )
    rows.append("")
    rows.append("## See also")
    rows.append("")
    rows.append("- `pages/systems/canonical-registry.jsonl`")
    rows.append("- [[pages/systems/MODEL-FAILOVER-LATEST]]")
    rows.append("- `pages/systems/parity-latest.json`")
    rows.append("- `.gbrain/manifest.json`, `.gbrain/index.db`, `.gbrain/queue.jsonl`")
    rows.append("")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

def _atomic_write_text(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` via a sibling ``.tmp`` + ``os.replace``."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    # Best-effort cleanup of stale tmp (e.g. crashed previous run).
    if tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, target)


def write_atomic(wiki: Path, snapshot: dict[str, Any]) -> tuple[Path, Path]:
    """Write both JSON + Markdown atomically. Returns ``(json_path, md_path)``."""
    json_path = wiki / HEALTH_JSON_REL
    md_path = wiki / HEALTH_MD_REL
    json_text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    md_text = render_markdown(snapshot)
    _atomic_write_text(json_path, json_text)
    _atomic_write_text(md_path, md_text)
    return (json_path, md_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Library health dashboard")
    p.add_argument("--wiki", type=Path, default=None)
    p.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    p.add_argument(
        "--no-write",
        action="store_true",
        help="Compute and print only; do not write the dashboard files",
    )
    args = p.parse_args()

    wiki = args.wiki if args.wiki is not None else default_wiki()
    snapshot = compute(wiki)

    if not args.no_write:
        json_path, md_path = write_atomic(wiki, snapshot)
        try:
            rel_json = json_path.relative_to(wiki)
            rel_md = md_path.relative_to(wiki)
            print(f"wrote {rel_json} + {rel_md}", file=sys.stderr)
        except ValueError:
            print(f"wrote {json_path} + {md_path}", file=sys.stderr)

    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
