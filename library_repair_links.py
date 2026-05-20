"""Detect + optionally repair broken Obsidian wikilinks — Ship 3 wave 5b.

Scans every ``pages/**/*.md`` for ``[[wikilinks]]`` and classifies each
target as ``resolved`` / ``single_match`` / ``multi_match`` / ``unknown``
against the canonical registry's alias index.

Default mode is read-only — it writes a dated audit at
``pages/library/broken-links-YYYY-MM-DD.md`` listing every link that
needs a human eye (``multi_match`` and ``unknown``).

``--apply`` mode additionally rewrites every ``single_match`` link in
place (atomic per-file write) so the vault converges toward the canonical
slugs that gbrain + OpenBrain index against.

Resolution order for each target:

1. ``pages/**/<target>.md`` exists → ``resolved``.
2. ``registry.get(alias=target)`` returns exactly one entry → ``single_match``.
3. Otherwise scan all registry entries for case-insensitive alias matches.
   - 1 match → ``single_match``.
   - 0 matches → ``unknown``.
   - >1 matches → ``multi_match``.

Audit lives in ``pages/library/`` (NOT ``pages/audits/`` — that's a peer
scope owned by Ship 3 wave 5a). Output is deterministic so siblings can
diff cleanly.

CLI::

    python3 tools/library_repair_links.py            # audit only
    python3 tools/library_repair_links.py --apply    # also rewrite single_match
    python3 tools/library_repair_links.py --json     # machine-readable summary
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from tools import library_canonical_registry as registry  # type: ignore
except ImportError:  # pragma: no cover - exercised via CLI subprocess
    import library_canonical_registry as registry  # type: ignore


ALMATY = dt.timezone(dt.timedelta(hours=5))
AUDIT_DIR_REL = Path("pages/library")
# Match [[target]] and [[target|display]]. The target is the first capture group;
# the optional display label is the second. Targets containing newlines, pipes,
# or closing brackets are rejected so we don't grab block-refs/embeds by accident.
WIKILINK_RE = re.compile(r"\[\[([^\]\|\n]+)(?:\|([^\]\n]+))?\]\]")
PAGES_REL = Path("pages")


# ---------------------------------------------------------------------------
# Path helpers (mirror tools/library_canonical_registry.py for parity)
# ---------------------------------------------------------------------------


def default_wiki() -> Path:
    """Resolve the vault root from ``NOUS_WIKI`` or by walking from this file.

    Mirrors ``library_canonical_registry.default_wiki`` so Mac/Air/VPS agree
    on the same root.
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
# Scanning
# ---------------------------------------------------------------------------


def _iter_markdown(wiki: Path):
    pages_root = wiki / PAGES_REL
    if not pages_root.exists():
        return
    for path in sorted(pages_root.rglob("*.md")):
        if path.is_file():
            yield path


def _build_file_index(wiki: Path) -> dict[str, list[Path]]:
    """Index every ``pages/**/*.md`` by lowercased stem.

    A list per stem because two different sub-folders may share a stem
    (e.g. ``pages/skills/factory-ops.md`` and ``pages/systems/factory-ops.md``).
    """
    index: dict[str, list[Path]] = {}
    for path in _iter_markdown(wiki):
        stem = path.stem.lower()
        index.setdefault(stem, []).append(path)
    return index


def _build_alias_index(wiki: Path) -> dict[str, list[dict[str, Any]]]:
    """Index every registry entry's aliases (case-insensitive) → entries."""
    index: dict[str, list[dict[str, Any]]] = {}
    try:
        entries = registry.list_all(wiki=wiki)
    except Exception as exc:  # pragma: no cover - defensive
        print(
            f"library_repair_links: registry.list_all failed: {exc}",
            file=sys.stderr,
        )
        return index
    for entry in entries:
        aliases = entry.get("aliases") or []
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            if not isinstance(alias, str) or not alias:
                continue
            key = alias.lower()
            bucket = index.setdefault(key, [])
            # Dedup by canonical_uuid so the same entry isn't counted twice
            # when two of its own aliases share a normalized form.
            uid = entry.get("canonical_uuid")
            if not any(e.get("canonical_uuid") == uid for e in bucket):
                bucket.append(entry)
    return index


def _normalize_target(raw: str) -> str:
    """Strip whitespace + optional anchor/section/extension from a wikilink target."""
    target = raw.strip()
    # Drop ``#section`` and ``^block`` refs — we resolve to the page itself.
    for sep in ("#", "^"):
        if sep in target:
            target = target.split(sep, 1)[0].strip()
    if target.lower().endswith(".md"):
        target = target[:-3]
    return target


def _resolution_target(target: str) -> str:
    """Return the bare stem used for file + alias lookup (final path segment, lowercase)."""
    bare = target.replace("\\", "/").split("/")[-1]
    return bare.lower()


def scan_wikilinks(wiki: Path) -> list[dict[str, Any]]:
    """Scan every ``pages/**/*.md`` for wikilinks; classify each occurrence.

    Returns a list of dicts shaped:

    ``{source_path, line_num, target, display, status, candidates}``

    where ``status`` is one of ``resolved`` / ``single_match`` /
    ``multi_match`` / ``unknown`` and ``candidates`` is the list of
    registry entries backing the classification (length 1 for
    ``single_match``, ``>=2`` for ``multi_match``, ``[]`` for ``resolved``
    and ``unknown``).
    """
    file_index = _build_file_index(wiki)
    alias_index = _build_alias_index(wiki)

    out: list[dict[str, Any]] = []
    for path in _iter_markdown(wiki):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(
                f"library_repair_links: skipping {path}: {exc}",
                file=sys.stderr,
            )
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in WIKILINK_RE.finditer(line):
                raw_target = match.group(1)
                display = match.group(2)
                target = _normalize_target(raw_target)
                if not target:
                    continue
                key = _resolution_target(target)
                status, candidates = _classify(
                    key, file_index, alias_index
                )
                out.append(
                    {
                        "source_path": str(path.relative_to(wiki)),
                        "line_num": lineno,
                        "target": target,
                        "display": display,
                        "status": status,
                        "candidates": candidates,
                    }
                )
    return out


def _classify(
    key: str,
    file_index: dict[str, list[Path]],
    alias_index: dict[str, list[dict[str, Any]]],
) -> tuple[str, list[dict[str, Any]]]:
    """Classify a normalized lookup key. Returns ``(status, candidates)``."""
    # 1. File-on-disk wins outright when exactly one match.
    file_matches = file_index.get(key, [])
    if len(file_matches) == 1:
        return "resolved", []

    # 2. Registry alias lookup. registry.get(alias=...) returns the first
    #    case-sensitive hit; we want a stable case-insensitive view so we
    #    always go through the alias_index.
    alias_matches = alias_index.get(key, [])
    if len(alias_matches) == 1:
        return "single_match", list(alias_matches)
    if len(alias_matches) >= 2:
        return "multi_match", list(alias_matches)

    # 3. Multiple file-on-disk matches with no registry entry to disambiguate.
    if len(file_matches) >= 2:
        synthetic = [
            {"obsidian_path": str(p), "title": p.stem, "aliases": [p.stem]}
            for p in file_matches
        ]
        return "multi_match", synthetic

    return "unknown", []


# ---------------------------------------------------------------------------
# Audit writer
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via temp+rename for atomicity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_broken_links_audit(
    wiki: Path,
    broken: list[dict],
    *,
    now: dt.datetime | None = None,
) -> Path:
    """Write the dated broken-links audit to ``pages/library/``.

    ``broken`` should be the subset of ``scan_wikilinks`` rows with status
    in ``{"multi_match", "unknown"}``. The audit groups them into two
    sections so a human reviewer can fix unknowns first and disambiguate
    multi-matches second.

    The file is written via temp+rename so concurrent readers never see
    a half-written audit.
    """
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)
    date_str = moment.strftime("%Y-%m-%d")
    audit_path = wiki / AUDIT_DIR_REL / f"broken-links-{date_str}.md"

    lines: list[str] = []
    lines.append("---")
    lines.append("type: audit")
    lines.append(f"id: broken-links-{date_str}")
    lines.append(f'title: "Broken wikilinks — {date_str}"')
    lines.append("tags: [audit, library, wikilinks, ship-3]")
    lines.append(f"date: {date_str}")
    lines.append(f"last_updated: {date_str}")
    lines.append("status: draft")
    lines.append("---")
    lines.append("")
    lines.append(f"# Broken wikilinks — {date_str}")
    lines.append("")

    if not broken:
        lines.append("No broken wikilinks detected.")
        lines.append("")
        _atomic_write(audit_path, "\n".join(lines))
        return audit_path

    unknown = [b for b in broken if b.get("status") == "unknown"]
    multi = [b for b in broken if b.get("status") == "multi_match"]

    lines.append(
        f"Total broken: **{len(broken)}** "
        f"(unknown: {len(unknown)}, multi_match: {len(multi)})."
    )
    lines.append("")

    if unknown:
        lines.append("## Unknown targets")
        lines.append("")
        lines.append("Wikilinks pointing at no file and no registry alias. "
                     "Either create the page or fix the link.")
        lines.append("")
        lines.append("| source | line | target | display |")
        lines.append("| --- | --- | --- | --- |")
        for row in unknown:
            display = row.get("display") or ""
            lines.append(
                f"| `{row['source_path']}` "
                f"| {row['line_num']} "
                f"| `{row['target']}` "
                f"| {display} |"
            )
        lines.append("")

    if multi:
        lines.append("## Multi-match targets")
        lines.append("")
        lines.append("Wikilinks whose target resolves to >1 canonical entry. "
                     "Pick the right one and rewrite the link by hand "
                     "(or extend the alias list to disambiguate).")
        lines.append("")
        lines.append("| source | line | target | candidates |")
        lines.append("| --- | --- | --- | --- |")
        for row in multi:
            cands = row.get("candidates") or []
            cand_str = "; ".join(
                str(c.get("obsidian_path") or c.get("slug") or c.get("title") or "")
                for c in cands
            )
            lines.append(
                f"| `{row['source_path']}` "
                f"| {row['line_num']} "
                f"| `{row['target']}` "
                f"| {cand_str} |"
            )
        lines.append("")

    _atomic_write(audit_path, "\n".join(lines))
    return audit_path


# ---------------------------------------------------------------------------
# Auto-repair
# ---------------------------------------------------------------------------


def _canonical_slug_for(entry: dict[str, Any]) -> str | None:
    """Return the best label to use as the canonical wikilink target."""
    slug = entry.get("slug")
    if isinstance(slug, str) and slug:
        return slug
    obsidian_path = entry.get("obsidian_path")
    if isinstance(obsidian_path, str) and obsidian_path:
        return Path(obsidian_path).stem
    title = entry.get("title")
    if isinstance(title, str) and title:
        return registry.slugify(title)
    return None


def auto_repair(wiki: Path, links: list[dict]) -> int:
    """Rewrite every ``single_match`` link in place. Returns rewrite count.

    Each source file is read once, every per-line rewrite for that file
    is applied, then the file is written back atomically (temp+rename).
    Display labels in ``[[target|display]]`` are preserved — only the
    pre-pipe target is replaced.
    """
    # Group rewrites per source file so we touch each file once.
    by_file: dict[str, list[dict]] = {}
    for link in links:
        if link.get("status") != "single_match":
            continue
        candidates = link.get("candidates") or []
        if len(candidates) != 1:
            continue
        new_target = _canonical_slug_for(candidates[0])
        if not new_target:
            continue
        link = dict(link)
        link["_new_target"] = new_target
        by_file.setdefault(link["source_path"], []).append(link)

    rewrites = 0
    for rel_path, rewrites_in_file in by_file.items():
        abs_path = wiki / rel_path
        try:
            original = abs_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(
                f"library_repair_links: cannot read {abs_path}: {exc}",
                file=sys.stderr,
            )
            continue

        # Build a per-line index of rewrites so we only touch the lines
        # we know about. A given line may have multiple wikilinks; we
        # only rewrite occurrences whose target matches the recorded one.
        by_line: dict[int, list[dict]] = {}
        for row in rewrites_in_file:
            by_line.setdefault(row["line_num"], []).append(row)

        lines = original.splitlines(keepends=True)
        file_changed = False
        for line_num, row_list in by_line.items():
            idx = line_num - 1
            if idx < 0 or idx >= len(lines):
                continue
            line = lines[idx]
            for row in row_list:
                old_target = row["target"]
                new_target = row["_new_target"]
                if old_target == new_target:
                    continue
                new_line, n = _replace_wikilink_target(
                    line, old_target, new_target
                )
                if n > 0:
                    line = new_line
                    rewrites += n
                    file_changed = True
            lines[idx] = line

        if file_changed:
            _atomic_write(abs_path, "".join(lines))

    return rewrites


def _replace_wikilink_target(
    line: str, old_target: str, new_target: str
) -> tuple[str, int]:
    """Replace ``[[old_target]]`` / ``[[old_target|display]]`` with the new target.

    Only the target portion (before ``|``) is touched. The display label,
    if any, is preserved verbatim. Anchor/section refs (``#sec``, ``^blk``)
    on the target are also preserved.
    """
    count = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal count
        raw_target = match.group(1)
        display = match.group(2)
        # Split anchor/section so we only compare the bare stem.
        bare = raw_target
        suffix = ""
        for sep in ("#", "^"):
            if sep in bare:
                bare, _, rest = bare.partition(sep)
                suffix = sep + rest
                break
        normalized = _normalize_target(bare)
        if _resolution_target(normalized) != _resolution_target(old_target):
            return match.group(0)
        count += 1
        new = f"[[{new_target}{suffix}"
        if display is not None:
            new += f"|{display}"
        new += "]]"
        return new

    new_line = WIKILINK_RE.sub(_sub, line)
    return new_line, count


# ---------------------------------------------------------------------------
# Summary + CLI
# ---------------------------------------------------------------------------


def summarize(links: list[dict]) -> dict[str, Any]:
    by_status = {"resolved": 0, "single_match": 0, "multi_match": 0, "unknown": 0}
    for link in links:
        status = link.get("status")
        if status in by_status:
            by_status[status] += 1
    return {"total": len(links), "by_status": by_status}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Detect + optionally repair broken wikilinks"
    )
    p.add_argument("--wiki", type=Path, default=None)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Auto-rewrite single_match links",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    wiki = args.wiki or default_wiki()
    links = scan_wikilinks(wiki)
    broken = [l for l in links if l["status"] in ("multi_match", "unknown")]
    audit_path = write_broken_links_audit(wiki, broken)

    rewrites = 0
    if args.apply:
        rewrites = auto_repair(wiki, links)

    summary = summarize(links)
    summary["rewrites"] = rewrites

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summary,
                    "audit_path": str(audit_path.relative_to(wiki)),
                }
            )
        )
    else:
        print(f"links scanned: {summary['total']}")
        for k, v in summary.get("by_status", {}).items():
            print(f"  {k}: {v}")
        print(f"audit: {audit_path.relative_to(wiki)}")
        if args.apply:
            print(f"rewrites applied: {rewrites}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
