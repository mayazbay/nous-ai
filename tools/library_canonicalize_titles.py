"""Detect title-vs-filename-vs-slug drift across the vault — Ship 3 wave 5a.

Walks every markdown file under ``pages/**/*.md`` and the canonical registry,
classifies drift between the page's title (frontmatter / H1 / filename), its
canonical slug (``registry.slugify``), and its on-disk basename. Surfaces the
drift in a dated audit markdown for human review.

Drift types:

* ``filename_vs_slug``  — basename (minus ``.md``, lowercased) does NOT match
  ``slugify(title)``. Most common; results from human renames or imports.
* ``alias_vs_slug``     — a canonical-registry entry has an alias whose
  normalized slug differs from the entry's ``slug`` field.
* ``title_missing``     — file has no frontmatter ``title:`` and no H1 (the
  ``title_from_path`` resolver fell through to the filename-derived title).
  Flagged informationally; not auto-fixed.

Outputs to ``pages/library/title-drift-YYYY-MM-DD.md`` (NEW directory under
``pages/``; deliberately NOT ``pages/audits/`` which is in the s1030 banned
scope for the peer wave).

``--apply`` mode is reserved for phase-2 (renames must land with a human
checkpoint). Currently it is a no-op that just notes the count to stderr.

CLI::

    python3 tools/library_canonicalize_titles.py
    python3 tools/library_canonicalize_titles.py --json
    python3 tools/library_canonicalize_titles.py --wiki /path/to/vault

Plan ref: Ship 3 §6.10.
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
    from tools import library_canonical_registry as registry  # type: ignore
except ImportError:
    # When invoked as a script from tools/, the parent package isn't on sys.path.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import library_canonical_registry as registry  # type: ignore


ALMATY = dt.timezone(dt.timedelta(hours=5))
AUDIT_DIR_REL = Path("pages/library")
PAGES_REL = Path("pages")
REGISTRY_REL = registry.REGISTRY_REL  # pages/systems/canonical-registry.jsonl


# ---------------------------------------------------------------------------
# Path / time helpers (mirror registry.default_wiki / now_kzt)
# ---------------------------------------------------------------------------

def default_wiki() -> Path:
    """Resolve wiki root from NOUS_WIKI, or by walking from this file.

    Mirrors ``library_canonical_registry.default_wiki`` exactly so Mac/Air/VPS
    converge on the same semantics.
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


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def _basename_slug(path: Path) -> str:
    """Lowercased filename without the ``.md`` extension.

    NOT run through ``slugify`` — we want to compare the raw on-disk form.
    """
    return path.stem.lower()


def _is_canonical_basename(basename: str) -> bool:
    """A basename is already canonical iff it equals its own slugify result.

    Used to decide whether a mismatch is real drift or a benign formatting
    difference (e.g. underscores). Since ``slugify`` normalizes underscores +
    spaces + case, this catches the common ``Snake_Case`` rename gap.
    """
    return basename == registry.slugify(basename)


# ---------------------------------------------------------------------------
# Vault scan
# ---------------------------------------------------------------------------

def _iter_markdown(pages_root: Path):
    """Yield every ``*.md`` under ``pages_root`` (sorted, deterministic)."""
    if not pages_root.exists():
        return
    for path in sorted(pages_root.rglob("*.md")):
        if path.is_file():
            yield path


def _scan_pages(wiki: Path) -> list[dict[str, Any]]:
    """Scan markdown files for filename/title drift."""
    drifts: list[dict[str, Any]] = []
    pages_root = wiki / PAGES_REL
    for md_path in _iter_markdown(pages_root):
        try:
            rel = md_path.relative_to(wiki).as_posix()
        except ValueError:
            rel = str(md_path)
        title = registry.title_from_path(md_path)
        canonical_slug = registry.slugify(title) if title else ""
        basename_slug = _basename_slug(md_path)

        # Detect title-missing: the resolver fell back to the filename-derived
        # title. We re-derive the same fallback to check equality. If the file
        # also has no frontmatter+no H1, the derived title equals the
        # filename-fallback title.
        derived_from_name = registry._title_from_filename(md_path)
        had_real_title = _had_real_title(md_path)

        if not had_real_title and title == derived_from_name:
            drifts.append(
                {
                    "path": rel,
                    "title": title,
                    "canonical_slug": canonical_slug,
                    "basename_slug": basename_slug,
                    "drift_type": "title_missing",
                }
            )
            continue

        if canonical_slug and canonical_slug != basename_slug:
            drifts.append(
                {
                    "path": rel,
                    "title": title,
                    "canonical_slug": canonical_slug,
                    "basename_slug": basename_slug,
                    "drift_type": "filename_vs_slug",
                }
            )
    return drifts


def _had_real_title(path: Path) -> bool:
    """True iff the file has explicit frontmatter ``title:`` OR an H1.

    Mirrors the resolution order inside ``registry.title_from_path`` but only
    reports whether one of the first two branches matched.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return False

    if text.startswith("---\n") or text.startswith("---\r\n"):
        after_open = text.split("\n", 1)[1] if "\n" in text else ""
        close_idx = after_open.find("\n---")
        if close_idx >= 0:
            fm_block = after_open[:close_idx]
            m = registry._FRONTMATTER_TITLE.search(fm_block)
            if m and m.group(1).strip():
                return True

    m = registry._H1_LINE.search(text)
    if m and m.group(1).strip():
        return True

    return False


def _scan_registry(wiki: Path) -> list[dict[str, Any]]:
    """Walk canonical-registry.jsonl; flag aliases whose slug != entry slug."""
    drifts: list[dict[str, Any]] = []
    reg_path = wiki / REGISTRY_REL
    if not reg_path.exists():
        return drifts
    # Reduce to current state per uuid (last-write-wins).
    try:
        rows = registry._load_registry(wiki)
    except Exception as exc:  # noqa: BLE001 — defensive; registry has its own logging
        print(f"library_canonicalize_titles: registry load failed: {exc}", file=sys.stderr)
        return drifts
    current = registry._latest_per_uuid(rows)
    for entry in current.values():
        slug = entry.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        aliases = entry.get("aliases")
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            if not isinstance(alias, str) or not alias:
                continue
            alias_slug = registry.slugify(alias)
            # The entry's stem (filename without .md) frequently is an alias.
            # Slugify might differ from the entry's slug field, which is the
            # title-derived slug — that's the drift we care about.
            if alias_slug and alias_slug != slug:
                drifts.append(
                    {
                        "path": entry.get("obsidian_path", ""),
                        "title": entry.get("title", ""),
                        "canonical_slug": slug,
                        "basename_slug": alias_slug,
                        "drift_type": "alias_vs_slug",
                        "alias": alias,
                        "canonical_uuid": entry.get("canonical_uuid", ""),
                    }
                )
    return drifts


def scan_vault(wiki: Path) -> list[dict[str, Any]]:
    """Walk ``pages/**/*.md`` and the canonical registry; return drift records.

    Each record has keys:

    * ``path``           — relative obsidian path (str)
    * ``title``          — derived title (str)
    * ``canonical_slug`` — ``slugify(title)`` or, for ``alias_vs_slug``, the
      registry entry's ``slug`` field
    * ``basename_slug``  — on-disk basename (lowercased, no ext), or for
      ``alias_vs_slug``, ``slugify(alias)``
    * ``drift_type``     — one of ``filename_vs_slug``, ``alias_vs_slug``,
      ``title_missing``

    Order: pages first (deterministic by path), then registry aliases.
    """
    wiki = _resolve_wiki(wiki)
    drifts = _scan_pages(wiki)
    drifts.extend(_scan_registry(wiki))
    return drifts


# ---------------------------------------------------------------------------
# Audit writer
# ---------------------------------------------------------------------------

def _format_audit(drifts: list[dict[str, Any]], *, now: dt.datetime) -> str:
    """Render the drift list as a markdown audit body."""
    iso = now.strftime("%Y-%m-%d")
    lines: list[str] = [
        "---",
        "type: audit",
        f"id: title-drift-{iso}",
        f'title: "Title / filename / slug drift — {iso}"',
        "tags: [library, drift, canonicalize, ship-3]",
        f"date: {iso}",
        "source_count: 0",
        "status: draft",
        f"last_updated: {iso}",
        "---",
        "",
        f"# Title / filename / slug drift — {iso}",
        "",
        f"Generated by `tools/library_canonicalize_titles.py` at {now.isoformat()}.",
        "",
    ]
    if not drifts:
        lines.append("No drift detected.")
        lines.append("")
        return "\n".join(lines)

    by_type: dict[str, list[dict[str, Any]]] = {}
    for d in drifts:
        by_type.setdefault(d.get("drift_type", "unknown"), []).append(d)

    lines.append(f"Total drift entries: **{len(drifts)}**")
    lines.append("")
    lines.append("## Summary by type")
    lines.append("")
    for t in sorted(by_type):
        lines.append(f"- `{t}`: {len(by_type[t])}")
    lines.append("")

    for t in sorted(by_type):
        lines.append(f"## {t}")
        lines.append("")
        lines.append("| path | title | canonical_slug | basename_slug |")
        lines.append("|---|---|---|---|")
        for d in by_type[t]:
            path = str(d.get("path", "")).replace("|", "\\|")
            title = str(d.get("title", "")).replace("|", "\\|")
            cslug = str(d.get("canonical_slug", "")).replace("|", "\\|")
            bslug = str(d.get("basename_slug", "")).replace("|", "\\|")
            lines.append(f"| {path} | {title} | `{cslug}` | `{bslug}` |")
        lines.append("")

    return "\n".join(lines)


def write_audit(
    wiki: Path,
    drifts: list[dict[str, Any]],
    *,
    now: dt.datetime | None = None,
) -> Path:
    """Write today's drift audit to ``pages/library/title-drift-YYYY-MM-DD.md``.

    Atomic: writes ``<file>.tmp`` then ``os.replace`` onto the final path so
    readers never see a partial file. If ``drifts`` is empty, writes a stub
    body containing "No drift detected." so downstream tooling can confirm
    the run happened.
    """
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    out_dir = wiki / AUDIT_DIR_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"title-drift-{moment.strftime('%Y-%m-%d')}.md"
    out_path = out_dir / fname
    tmp_path = out_dir / (fname + ".tmp")

    body = _format_audit(drifts, now=moment)
    tmp_path.write_text(body, encoding="utf-8")
    os.replace(tmp_path, out_path)
    return out_path


def summarize(drifts: list[dict[str, Any]]) -> dict[str, Any]:
    """Return summary stats for the drift list.

    Keys:
      * ``total``     — overall count
      * ``by_type``   — {drift_type: count} (sorted; explicit zero for the
        three known types so downstream UIs can render stable columns).
      * ``examples``  — first 3 records (verbatim)
    """
    by_type: dict[str, int] = {
        "filename_vs_slug": 0,
        "alias_vs_slug": 0,
        "title_missing": 0,
    }
    for d in drifts:
        t = d.get("drift_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total": len(drifts),
        "by_type": by_type,
        "examples": list(drifts[:3]),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Detect title/slug/alias drift")
    p.add_argument("--wiki", type=Path, default=None, help="Vault root (default: NOUS_WIKI or auto-resolve)")
    p.add_argument("--apply", action="store_true", help="Phase-2 reserved; currently no-op")
    p.add_argument("--json", action="store_true", help="Emit JSON summary instead of human text")
    args = p.parse_args()

    wiki = _resolve_wiki(args.wiki)
    drifts = scan_vault(wiki)
    audit_path = write_audit(wiki, drifts)
    summary = summarize(drifts)

    if args.apply:
        print(
            f"--apply currently no-op (phase 2 deferred); would rewrite {summary['total']} entries",
            file=sys.stderr,
        )

    if args.json:
        try:
            audit_rel = audit_path.relative_to(wiki).as_posix()
        except ValueError:
            audit_rel = str(audit_path)
        print(json.dumps({"summary": summary, "audit_path": audit_rel}))
    else:
        print(f"drift total: {summary['total']}")
        for k, v in summary.get("by_type", {}).items():
            print(f"  {k}: {v}")
        try:
            audit_rel = audit_path.relative_to(wiki).as_posix()
        except ValueError:
            audit_rel = str(audit_path)
        print(f"audit: {audit_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
