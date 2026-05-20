"""Unified library CLI: cross-system search + canonical registry + embed.

Ship 3 wave 3 of the library failover plan. This module is the operator-facing
single front door over the three durable substrates that compose the unified
library graph:

  - Obsidian vault   (filesystem; ripgrep BM25-ish over titles + bodies)
  - gbrain index     (sqlite-vec cosine via library_embed_db.search_vec)
  - OpenBrain        (Nate B Jones thought log via MCP shell-out)

The search subcommand fuses per-system result lists via Reciprocal Rank Fusion
(RRF, k_constant=60). Dedup happens by canonical_uuid via the registry; the
SearchHit dataclass carries the list of contributing systems so callers can
reason about which substrate surfaced each hit.

The embed subcommand chunks a file (library_embed.chunk_file), runs the
preferred embedder (voyage > local MiniLM > stub fallback), and writes the
chunks + vectors into ``.gbrain/index.db`` (library_embed_db.init_db +
insert_chunks). The registry subcommand is a thin wrapper over
library_canonical_registry.{add, get, list_all}.

Stubs for the remaining Ship 3 waves emit a clear
``NOT_IMPLEMENTED — coming in Ship 3 wave <N>`` line on stderr and exit 2,
so operators get a falsifiable signal rather than a silent no-op.

All search functions are fail-soft: if ripgrep or the mcp CLI is missing, or
the gbrain DB has no vec extension, or the Voyage key is absent, the relevant
sub-search returns ``[]`` and the router keeps going. ``search`` itself never
raises.

Plan: §6.4 (CLI orchestrator). Prior Ship 3 commits:
  - 96545054 registry
  - 2dccc5bb embed chunker
  - 84d6ded5 parity manifest
  - 9a528f58 Voyage + sqlite-vec DB
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Common locations to probe for `rg` when PATH lookup misses (e.g. when
# called from an editor / agent subprocess with a stripped PATH).
_RG_FALLBACK_PATHS: tuple[str, ...] = (
    "/opt/homebrew/bin/rg",
    "/usr/local/bin/rg",
    "/usr/bin/rg",
    "/opt/homebrew/opt/ripgrep/bin/rg",
    "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-darwin/rg",
    "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/x64-darwin/rg",
    "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/x64-linux/rg",
    "/usr/local/lib/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-linux/rg",
)


def _resolve_rg_binary() -> str | None:
    """Find the ``rg`` executable. Honors RG_BIN env, then PATH, then fallbacks."""
    forced = os.environ.get("RG_BIN", "").strip()
    if forced and Path(forced).is_file() and os.access(forced, os.X_OK):
        return forced
    found = shutil.which("rg")
    if found:
        return found
    for candidate in _RG_FALLBACK_PATHS:
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None

# Dual-import sibling tools so this module loads both as ``tools.library``
# (when run via pytest at the repo root) and as ``library`` (when run as
# ``python3 tools/library.py`` with tools/ on sys.path).
try:
    from tools import library_canonical_registry as registry
    from tools import library_embed as embed_mod
    from tools import library_embed_voyage as embed_voyage
    from tools import library_embed_db as embed_db
except ImportError:
    import library_canonical_registry as registry  # type: ignore
    import library_embed as embed_mod  # type: ignore
    import library_embed_voyage as embed_voyage  # type: ignore
    import library_embed_db as embed_db  # type: ignore


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SearchHit:
    """One fused search result.

    Attributes:
        canonical_uuid: ULID from the registry; "" if no registry entry exists
                        (e.g. an Obsidian path that hasn't been registered yet).
        title:          Human-readable title.
        snippet:        Short body excerpt for display.
        score:          RRF score (higher is better).
        system_sources: List of system names that contributed
                        (subset of {"obsidian", "gbrain", "openbrain"}).
        obsidian_path:  Relative path under the wiki; "" if not known.
    """

    canonical_uuid: str
    title: str
    snippet: str
    score: float
    system_sources: list[str]
    obsidian_path: str

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Wiki resolution — mirrors registry/queue conventions
# ---------------------------------------------------------------------------


def default_wiki() -> Path:
    """Resolve the wiki root via NOUS_WIKI env or walking up from this file."""
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parents[1]
    if (here / "pages").exists():
        return here
    if (here / "wiki" / "pages").exists():
        return here / "wiki"
    return here


# ---------------------------------------------------------------------------
# Per-system search functions — each is fail-soft (returns [] on any error).
# ---------------------------------------------------------------------------


def obsidian_search(query: str, *, wiki: Path, top: int = 30) -> list[dict[str, Any]]:
    """Ripgrep-based search over ``pages/**/*.md``.

    Returns a list of ``{path, snippet, rank, match_count}`` dicts. ``path``
    is relative to ``wiki``. Rank is 1-based, ordered by match count
    (descending). If ``rg`` is missing or returns non-zero, returns ``[]``.
    """
    if not query or not query.strip():
        return []
    pages_dir = wiki / "pages"
    if not pages_dir.exists():
        return []
    rg_bin = _resolve_rg_binary()
    if rg_bin is None:
        return []
    try:
        proc = subprocess.run(
            [
                rg_bin,
                "--line-number",
                "--no-heading",
                "-i",
                "--max-count=3",
                "--",
                query,
                str(pages_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return []
    except subprocess.TimeoutExpired:
        return []
    except OSError:
        return []
    if proc.returncode not in (0, 1):
        # rg exit 1 == no matches (normal). Anything else is an error.
        return []
    # Group matches by file. Each rg line: ``<path>:<lineno>:<text>``.
    by_path: dict[str, list[tuple[int, str]]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path_str, lineno_str, text = parts[0], parts[1], parts[2]
        try:
            lineno = int(lineno_str)
        except ValueError:
            continue
        by_path.setdefault(path_str, []).append((lineno, text))
    # Build snippet: take the first matching line plus 1 line before + 1 after
    # from the file body when possible.
    out: list[dict[str, Any]] = []
    for path_str, matches in by_path.items():
        match_count = len(matches)
        first_lineno, first_text = matches[0]
        snippet = first_text.strip()
        try:
            file_lines = Path(path_str).read_text(encoding="utf-8").splitlines()
            lo = max(0, first_lineno - 2)
            hi = min(len(file_lines), first_lineno + 1)
            snippet = "\n".join(file_lines[lo:hi]).strip()
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            pass
        try:
            rel = str(Path(path_str).resolve().relative_to(wiki.resolve()))
        except ValueError:
            rel = path_str
        out.append(
            {
                "path": rel,
                "snippet": snippet[:400],
                "match_count": match_count,
            }
        )
    out.sort(key=lambda r: r["match_count"], reverse=True)
    # Assign 1-based rank, truncate to top.
    ranked: list[dict[str, Any]] = []
    for i, r in enumerate(out[:top], start=1):
        r2 = dict(r)
        r2["rank"] = i
        ranked.append(r2)
    return ranked


def gbrain_search(query: str, *, wiki: Path, top: int = 30) -> list[dict[str, Any]]:
    """Vector search via library_embed_db.search_vec.

    Embeds the query (voyage preferred, falls back per ``make_embedder``),
    then runs sqlite-vec nearest-neighbor and joins each hit against the
    canonical registry for ``title`` + ``obsidian_path``.

    Fail-soft: if the embedder reports auth_missing/error, or the gbrain DB
    has no vec extension loaded, returns ``[]``.
    """
    if not query or not query.strip():
        return []
    try:
        embedder = embed_voyage.make_embedder(prefer="voyage")
    except Exception:
        return []
    # Build a dummy single-chunk to feed embed(); reuse the Chunk dataclass.
    try:
        Chunk = embed_mod.Chunk  # type: ignore[attr-defined]
        q_chunk = Chunk(chunk_idx=0, heading_path="", text=query, content_hash="")
    except Exception:
        return []
    try:
        results = embedder.embed([q_chunk])
    except Exception:
        return []
    if not results:
        return []
    res0 = results[0]
    if getattr(res0, "error", "") or not getattr(res0, "vector", None):
        return []
    vec = list(res0.vector)
    dim = res0.dim or len(vec)
    if not vec or not dim:
        return []
    try:
        hits = embed_db.search_vec(wiki, query_vector=vec, dim=dim, k=top)
    except Exception:
        return []
    if not hits:
        return []
    # Enrich with registry title + obsidian_path.
    out: list[dict[str, Any]] = []
    for i, h in enumerate(hits, start=1):
        uid = h.get("canonical_uuid", "")
        title = ""
        obsidian_path = ""
        if uid:
            try:
                entry = registry.get(uuid=uid, wiki=wiki)
            except Exception:
                entry = None
            if entry:
                title = entry.get("title", "") or ""
                obsidian_path = entry.get("obsidian_path", "") or ""
        out.append(
            {
                "canonical_uuid": uid,
                "title": title,
                "obsidian_path": obsidian_path,
                "snippet": (h.get("text", "") or "")[:400],
                "distance": h.get("distance", 0.0),
                "rank": i,
            }
        )
    return out


def openbrain_search(query: str, *, top: int = 30) -> list[dict[str, Any]]:
    """Shell out to the OpenBrain MCP CLI to search Nate B Jones thoughts.

    Best-effort: tries ``mcp call claude.ai_Open_Brain search_thoughts ...``.
    If ``mcp`` is absent or the invocation fails, returns ``[]``. Parses
    stdout as JSON; tolerates either a top-level list or a ``{"thoughts": [...]}``
    envelope.
    """
    if not query or not query.strip():
        return []
    cmd = [
        "mcp",
        "call",
        "claude.ai_Open_Brain",
        "search_thoughts",
        f"query={query}",
        f"limit={top}",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        return []
    except subprocess.TimeoutExpired:
        return []
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return []
    if isinstance(payload, dict):
        thoughts = payload.get("thoughts") or payload.get("results") or []
    elif isinstance(payload, list):
        thoughts = payload
    else:
        return []
    out: list[dict[str, Any]] = []
    for i, t in enumerate(thoughts[:top], start=1):
        if not isinstance(t, dict):
            continue
        out.append(
            {
                "thought_id": str(t.get("id") or t.get("thought_id") or ""),
                "title": str(t.get("title") or t.get("name") or ""),
                "snippet": str(t.get("body") or t.get("summary") or "")[:400],
                "rank": i,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def _registry_lookup_path(wiki: Path, path: str) -> dict[str, Any] | None:
    try:
        return registry.get(path=path, wiki=wiki)
    except Exception:
        return None


def _registry_lookup_alias(wiki: Path, alias: str) -> dict[str, Any] | None:
    if not alias:
        return None
    try:
        return registry.get(alias=alias, wiki=wiki)
    except Exception:
        return None


def rrf_merge(
    results_by_system: dict[str, list[dict[str, Any]]],
    *,
    wiki: Path,
    k_constant: int = 60,
) -> list[SearchHit]:
    """Reciprocal Rank Fusion across per-system result lists.

    Per RRF: ``score(d) = Σ 1 / (k_constant + rank_s(d))`` over systems ``s``
    that returned ``d``. Dedup is on canonical_uuid; results without a known
    canonical_uuid fall back to a synthetic key (``obsidian:<path>`` or
    ``openbrain:<thought_id>`` or ``unknown:<i>``) so they still surface but
    don't accidentally collide with registered entries.

    Returns SearchHits sorted by score desc, with ``system_sources`` set to the
    list of contributing system names in insertion order.
    """
    # Aggregation: key -> {score, hit_partial, sources}
    aggregated: dict[str, dict[str, Any]] = {}

    def _bump(key: str, system: str, rank: int, hit: SearchHit) -> None:
        weight = 1.0 / (k_constant + rank)
        entry = aggregated.get(key)
        if entry is None:
            aggregated[key] = {
                "score": weight,
                "hit": hit,
                "sources": [system],
            }
            return
        entry["score"] = entry["score"] + weight
        if system not in entry["sources"]:
            entry["sources"].append(system)
        # Merge: keep the first non-empty title / snippet / obsidian_path /
        # canonical_uuid we saw.
        existing: SearchHit = entry["hit"]
        merged = SearchHit(
            canonical_uuid=existing.canonical_uuid or hit.canonical_uuid,
            title=existing.title or hit.title,
            snippet=existing.snippet or hit.snippet,
            score=0.0,  # final score set after aggregation
            system_sources=[],  # set below
            obsidian_path=existing.obsidian_path or hit.obsidian_path,
        )
        entry["hit"] = merged

    for system, results in results_by_system.items():
        for r in results:
            rank = int(r.get("rank", 0) or 0)
            if rank <= 0:
                continue
            canonical_uuid = ""
            title = ""
            obsidian_path = ""
            snippet = str(r.get("snippet", "") or "")

            if system == "obsidian":
                path = str(r.get("path", "") or "")
                obsidian_path = path
                entry = _registry_lookup_path(wiki, path) if path else None
                if entry:
                    canonical_uuid = entry.get("canonical_uuid", "") or ""
                    title = entry.get("title", "") or ""
                key = canonical_uuid or f"obsidian:{path}"
            elif system == "gbrain":
                canonical_uuid = str(r.get("canonical_uuid", "") or "")
                title = str(r.get("title", "") or "")
                obsidian_path = str(r.get("obsidian_path", "") or "")
                key = canonical_uuid or f"gbrain:{r.get('chunk_idx', '')}"
            elif system == "openbrain":
                thought_id = str(r.get("thought_id", "") or "")
                title = str(r.get("title", "") or "")
                entry = _registry_lookup_alias(wiki, thought_id)
                if entry is None and title:
                    entry = _registry_lookup_alias(wiki, title)
                if entry:
                    canonical_uuid = entry.get("canonical_uuid", "") or ""
                    obsidian_path = entry.get("obsidian_path", "") or ""
                    if not title:
                        title = entry.get("title", "") or ""
                key = canonical_uuid or f"openbrain:{thought_id}"
            else:
                key = f"unknown:{system}:{rank}"

            hit = SearchHit(
                canonical_uuid=canonical_uuid,
                title=title or obsidian_path or "(untitled)",
                snippet=snippet,
                score=0.0,
                system_sources=[],
                obsidian_path=obsidian_path,
            )
            _bump(key, system, rank, hit)

    fused: list[SearchHit] = []
    for entry in aggregated.values():
        h: SearchHit = entry["hit"]
        fused.append(
            SearchHit(
                canonical_uuid=h.canonical_uuid,
                title=h.title,
                snippet=h.snippet,
                score=float(entry["score"]),
                system_sources=list(entry["sources"]),
                obsidian_path=h.obsidian_path,
            )
        )
    fused.sort(key=lambda x: x.score, reverse=True)
    return fused


# ---------------------------------------------------------------------------
# Unified search router
# ---------------------------------------------------------------------------


def _safe_call(fn, *args, **kwargs) -> list[dict[str, Any]]:
    """Wrap an individual per-system search so the router never raises."""
    try:
        out = fn(*args, **kwargs)
    except Exception:
        return []
    return out if isinstance(out, list) else []


def search(
    query: str,
    *,
    wiki: Path,
    system: str = "all",
    top: int = 10,
) -> list[SearchHit]:
    """Unified search. ``system`` in ``{all, obsidian, gbrain, openbrain}``.

    If ``system != 'all'``, only that single sub-search runs; the others are
    skipped. Per-system result lists are merged via RRF (k_constant=60).
    Returns at most ``top`` SearchHits. Never raises.
    """
    results_by_system: dict[str, list[dict[str, Any]]] = {}
    fetch_top = max(top * 3, 30)

    if system in ("all", "obsidian"):
        results_by_system["obsidian"] = _safe_call(
            obsidian_search, query, wiki=wiki, top=fetch_top
        )
    if system in ("all", "gbrain"):
        results_by_system["gbrain"] = _safe_call(
            gbrain_search, query, wiki=wiki, top=fetch_top
        )
    if system in ("all", "openbrain"):
        results_by_system["openbrain"] = _safe_call(
            openbrain_search, query, top=fetch_top
        )

    fused = rrf_merge(results_by_system, wiki=wiki)
    return fused[:top]


# ---------------------------------------------------------------------------
# CLI subcommand handlers
# ---------------------------------------------------------------------------


def cmd_search(args) -> int:
    wiki = default_wiki()
    hits = search(args.query, wiki=wiki, system=args.system, top=args.top)
    if args.json:
        print(json.dumps([h.as_dict() for h in hits], ensure_ascii=False))
    else:
        for h in hits:
            systems = ",".join(h.system_sources)
            uid = h.canonical_uuid or "-"
            print(f"{h.score:.4f}  {uid}  {h.title}  [systems: {systems}]")
    return 0


def cmd_embed(args) -> int:
    path: Path = args.path
    if not path.exists():
        print(f"library: path not found: {path}", file=sys.stderr)
        return 1
    chunks = embed_mod.chunk_file(path)
    if not chunks:
        print(f"library: no chunks produced for {path}", file=sys.stderr)
        return 1

    embedder = embed_voyage.make_embedder(prefer=args.prefer)
    results = embedder.embed(chunks)

    # Surface auth_missing as a non-fatal "couldn't embed" signal.
    auth_missing = any(getattr(r, "error", "") == "auth_missing" for r in results)

    if args.json:
        payload = {
            "chunks": [c.as_dict() for c in chunks],
            "embeddings": [dataclasses.asdict(r) for r in results],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1 if auth_missing else 0

    if auth_missing:
        print(
            "library: embedder reported auth_missing — set VOYAGE_API_KEY "
            "or use --prefer stub",
            file=sys.stderr,
        )
        return 1

    # Insert into .gbrain/index.db via embed_db.
    wiki = default_wiki()
    dim = results[0].dim if results else 0
    if dim <= 0:
        print("library: embedder returned dim=0 — nothing to insert", file=sys.stderr)
        return 1

    # Register the path so each chunk has a canonical_uuid.
    try:
        rel_path = str(path.resolve().relative_to(wiki.resolve()))
    except ValueError:
        rel_path = str(path)
    canonical_uuid = registry.add(rel_path, wiki=wiki)

    embed_db.init_db(wiki, dim=dim)
    batch = [
        embed_db.ChunkInsert(
            canonical_uuid=canonical_uuid,
            chunk_idx=chunks[i].chunk_idx,
            heading_path=chunks[i].heading_path,
            text=chunks[i].text,
            content_hash=chunks[i].content_hash,
            vector=list(results[i].vector),
            embed_model=results[i].model,
            embed_dim=results[i].dim,
        )
        for i in range(len(chunks))
        if not getattr(results[i], "error", "")
    ]
    inserted = embed_db.insert_chunks(wiki, batch)
    print(f"wrote {inserted} chunks to .gbrain/index.db")
    return 0


def cmd_registry(args) -> int:
    wiki = default_wiki()
    if args.rcmd == "add":
        uid = registry.add(
            args.path,
            title=args.title,
            aliases=args.alias or None,
            wiki=wiki,
        )
        print(uid)
        return 0
    if args.rcmd == "get":
        entry = registry.get(
            uuid=args.uuid,
            path=args.path,
            alias=args.alias,
            wiki=wiki,
        )
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
    if args.rcmd == "list":
        entries = registry.list_all(wiki=wiki)
        if args.json:
            print(json.dumps(entries, ensure_ascii=False))
        else:
            for e in entries:
                print(
                    f"{e.get('canonical_uuid', '')}  "
                    f"{e.get('obsidian_path', '')}  "
                    f"'{e.get('title', '')}'"
                )
        return 0
    return 1


def cmd_stub(label: str, wave: int) -> int:
    print(
        f"NOT_IMPLEMENTED — coming in Ship 3 wave {wave} ({label})",
        file=sys.stderr,
    )
    return 2


# ---------------------------------------------------------------------------
# argparse setup
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nous library — unified CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="cross-system unified search")
    p_search.add_argument("query")
    p_search.add_argument(
        "--system",
        choices=("all", "obsidian", "gbrain", "openbrain"),
        default="all",
    )
    p_search.add_argument("--top", type=int, default=10)
    p_search.add_argument("--json", action="store_true")

    p_embed = sub.add_parser("embed", help="chunk + embed + insert to .gbrain/index.db")
    p_embed.add_argument("path", type=Path)
    p_embed.add_argument("--json", action="store_true")
    p_embed.add_argument(
        "--prefer",
        choices=("voyage", "local", "stub"),
        default="voyage",
    )

    p_registry = sub.add_parser("registry", help="canonical registry CRUD")
    rsub = p_registry.add_subparsers(dest="rcmd", required=True)

    r_get = rsub.add_parser("get")
    rg = r_get.add_mutually_exclusive_group(required=True)
    rg.add_argument("--uuid")
    rg.add_argument("--path")
    rg.add_argument("--alias")
    r_get.add_argument("--field")
    r_get.add_argument("--json", action="store_true")

    r_add = rsub.add_parser("add")
    r_add.add_argument("--path", required=True)
    r_add.add_argument("--title")
    r_add.add_argument("--alias", action="append", default=[])

    r_list = rsub.add_parser("list")
    r_list.add_argument("--json", action="store_true")

    for stub_name, wave in (
        ("rebuild", 8),
        ("drain-queue", 7),
        ("canonicalize", 5),
        ("repair-links", 5),
        ("sync-openbrain", 4),
        ("health", 6),
        ("verify-end-to-end", 9),
    ):
        sp = sub.add_parser(stub_name, help=f"(stub — Ship 3 wave {wave})")
        sp.set_defaults(_stub_label=stub_name, _stub_wave=wave)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "search":
        return cmd_search(args)
    if args.cmd == "embed":
        return cmd_embed(args)
    if args.cmd == "registry":
        return cmd_registry(args)
    if hasattr(args, "_stub_label"):
        return cmd_stub(args._stub_label, args._stub_wave)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
