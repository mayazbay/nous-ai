#!/usr/bin/env python3
"""Project OpenBrain MCP captures into the canonical Obsidian wiki.

The runner is intentionally boring:
- fetch recent captures from the OpenBrain MCP endpoint;
- render deterministic markdown files under pages/inbox/openbrain/YYYY-MM-DD;
- fail visibly on conflicts or MCP errors;
- optionally commit and push only projection files.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # macOS system Python can be older than 3.11.
    tomllib = None  # type: ignore[assignment]


ISO_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
LIST_BLOCK_RE = re.compile(
    r"(?ms)^\s*(?P<num>\d+)\.\s+\[(?P<created_at>[^\]]+)\]\s+id=(?P<id>[0-9a-f-]{36})\s+"
    r"\((?P<meta>[^)]*)\)\n\s+(?P<content>.*?)(?=\n\n\s*\d+\. |\Z)"
)


@dataclasses.dataclass(frozen=True)
class Thought:
    openbrain_id: str
    created_at: str
    content: str
    thought_type: str
    topics: tuple[str, ...]

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]

    @property
    def date(self) -> str:
        return self.created_at[:10]

    @property
    def filename(self) -> str:
        return f"openbrain-{self.openbrain_id}.md"


class ProjectionError(RuntimeError):
    pass


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def title_from_content(content: str, limit: int = 72) -> str:
    one_line = re.sub(r"\s+", " ", content).strip()
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1].rstrip() + "..."


def redact_sensitive_text(text: str) -> str:
    """Redact credential-shaped captures before they are projected to the wiki."""
    redacted = text
    redacted = re.sub(
        r"(?i)\b(password|pass|pwd|пароль|token|secret|api[_-]?key)\s*[:=]\s*([^\s,;]+)",
        lambda m: f"{m.group(1)}=[REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b((?:password|pass|pwd|пароль|token|secret|api[_-]?key)\s+)([A-Za-z0-9._@!#$%+=/-]{6,})",
        lambda m: f"{m.group(1)}[REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b((?:\d{1,3}\.){3}\d{1,3}\s+(?:admin|админ|root|user|username|login|логин)\s+)([^\s,;]+)",
        lambda m: f"{m.group(1)}[REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b((?:admin|админ|root|user|username|login|логин)/)([^\s,;]+)",
        lambda m: f"{m.group(1)}[REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b((?:admin|админ|root)\s+)(?=[^\s,;]*\d)([^\s,;]{6,})",
        lambda m: f"{m.group(1)}[REDACTED]",
        redacted,
    )
    return redacted


def load_mcp_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if os.environ.get("OPENBRAIN_MCP_URL"):
        return os.environ["OPENBRAIN_MCP_URL"]

    env_files = [
        pathlib.Path.home() / "nous-agaas/secrets/openbrain-projection.env",
        pathlib.Path.home() / "nous-agaas/.env",
    ]
    for env_file in env_files:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENBRAIN_MCP_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    config = pathlib.Path.home() / ".codex/config.toml"
    if config.exists() and tomllib is not None:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
        server = data.get("mcp_servers", {}).get("open-brain")
        if server and server.get("url"):
            return str(server["url"])

    raise ProjectionError("projection_failed: OPENBRAIN_MCP_URL not found in env, ~/nous-agaas/secrets, or ~/.codex/config.toml")


def parse_sse_json(payload: str) -> dict[str, Any]:
    data_lines = [line[5:].strip() for line in payload.splitlines() if line.startswith("data:")]
    if not data_lines:
        raise ProjectionError(f"projection_failed: MCP response did not contain SSE data: {payload[:200]}")
    return json.loads("\n".join(data_lines))


def call_mcp_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> str:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
    )
    completed = subprocess.run(
        [
            "curl",
            "-sS",
            "--fail-with-body",
            "-H",
            "Content-Type: application/json",
            "-H",
            "Accept: application/json, text/event-stream",
            "--data-binary",
            "@-",
            url,
        ],
        input=body,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if completed.returncode != 0:
        raise ProjectionError(f"projection_failed: curl rc={completed.returncode}: {completed.stderr.strip()} {completed.stdout[:300]}")
    decoded = parse_sse_json(completed.stdout)
    if decoded.get("error"):
        raise ProjectionError(f"projection_failed: MCP error: {decoded['error']}")
    result = decoded.get("result", {})
    if result.get("isError"):
        raise ProjectionError(f"projection_failed: tool {tool_name} returned isError: {result}")
    content = result.get("content") or []
    texts = [part.get("text", "") for part in content if part.get("type") == "text"]
    if not texts:
        raise ProjectionError(f"projection_failed: tool {tool_name} returned no text content")
    return "\n".join(texts)


def parse_list_thoughts(text: str) -> list[Thought]:
    thoughts: list[Thought] = []
    for match in LIST_BLOCK_RE.finditer(text):
        openbrain_id = match.group("id")
        if not UUID_RE.match(openbrain_id):
            raise ProjectionError(f"projection_failed: invalid OpenBrain id: {openbrain_id}")
        meta = match.group("meta")
        parts = [part.strip() for part in meta.split(" - ", 1)]
        thought_type = parts[0] if parts and parts[0] else "unknown"
        topics = tuple(t.strip() for t in parts[1].split(",") if t.strip()) if len(parts) > 1 else ()
        thoughts.append(
            Thought(
                openbrain_id=openbrain_id,
                created_at=match.group("created_at"),
                content=match.group("content").strip(),
                thought_type=thought_type,
                topics=topics,
            )
        )
    if not thoughts and "No thoughts found" not in text:
        raise ProjectionError("projection_failed: could not parse OpenBrain list output; MCP may not expose ids yet")
    return thoughts


def fetch_thoughts(url: str, limit: int, days: int | None) -> list[Thought]:
    args: dict[str, Any] = {"limit": limit}
    if days:
        args["days"] = days
    return parse_list_thoughts(call_mcp_tool(url, "list_thoughts", args))


def render_markdown(thought: Thought, projected_at: str) -> str:
    safe_content = redact_sensitive_text(thought.content)
    title = title_from_content(safe_content)
    lines = [
        "---",
        "type: openbrain-capture",
        f"id: openbrain-{thought.openbrain_id}",
        f"title: {yaml_quote(title)}",
        f"date: {thought.date}",
        f"created_at: {yaml_quote(thought.created_at)}",
        f"projected_at: {yaml_quote(projected_at)}",
        f"openbrain_id: {yaml_quote(thought.openbrain_id)}",
        f"content_hash: {yaml_quote(thought.content_hash)}",
        f"correlation_id: {yaml_quote('openbrain-projection:' + thought.openbrain_id)}",
        "source: openbrain",
        "status: projected",
        f"openbrain_type: {yaml_quote(thought.thought_type)}",
    ]
    if thought.topics:
        lines.append("topics:")
        lines.extend(f"  - {yaml_quote(topic)}" for topic in thought.topics)
    else:
        lines.append("topics: []")
    lines.extend(
        [
            f"backlink: {yaml_quote('supabase://thoughts/' + thought.openbrain_id)}",
            "---",
            "",
            f"# OpenBrain Capture - {thought.date}",
            "",
            safe_content,
            "",
            "## Projection",
            "",
            f"- OpenBrain ID: `{thought.openbrain_id}`",
            f"- Content hash: `{thought.content_hash}`",
            f"- Projected at: `{projected_at}`",
            "- Source: OpenBrain MCP",
            "",
        ]
    )
    return "\n".join(lines)


def projection_path(wiki: pathlib.Path, thought: Thought) -> pathlib.Path:
    return wiki / "pages/inbox/openbrain" / thought.date / thought.filename


def existing_projected_at(markdown: str) -> str | None:
    match = re.search(r'(?m)^projected_at:\s+"?([^"\n]+)"?\s*$', markdown)
    return match.group(1) if match else None


def scan_content_hashes(wiki: pathlib.Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    base = wiki / "pages/inbox/openbrain"
    if not base.exists():
        return hashes
    for path in sorted(base.glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r'(?m)^content_hash:\s+"?([0-9a-f]{16})"?\s*$', text)
        if match:
            hashes.setdefault(match.group(1), str(path.relative_to(wiki)))
    return hashes


def project_thought(
    wiki: pathlib.Path,
    thought: Thought,
    dry_run: bool,
    projected_at: str,
    content_hashes: dict[str, str] | None = None,
) -> dict[str, str]:
    path = projection_path(wiki, thought)
    rel = str(path.relative_to(wiki))
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        expected = f"content_hash: {yaml_quote(thought.content_hash)}"
        if expected not in existing:
            raise ProjectionError(f"projection_failed: existing file hash mismatch: {rel}")
        # Preserve non-projected lifecycle state (deferred / ingested / archived)
        # written by downstream tools like tools/ingest_openbrain_to_skills.py.
        # Hash already matches → content is canonical; clobbering the file would
        # wipe deferred_reason / deferred_at / status: deferred and put Gate 7.1
        # back into a 5-min chase loop. See openbrain-projection AP-8 (v1.3.0).
        if re.search(r"^status:\s*(deferred|ingested|archived)\s*$", existing, re.MULTILINE):
            return {"status": "exists", "path": rel, "openbrain_id": thought.openbrain_id}
        stable_projected_at = existing_projected_at(existing) or projected_at
        markdown = render_markdown(thought, stable_projected_at)
        if existing != markdown:
            if not dry_run:
                path.write_text(markdown, encoding="utf-8")
            return {"status": "would_update" if dry_run else "updated", "path": rel, "openbrain_id": thought.openbrain_id}
        return {"status": "exists", "path": rel, "openbrain_id": thought.openbrain_id}
    if content_hashes and thought.content_hash in content_hashes:
        return {
            "status": "duplicate_content",
            "path": content_hashes[thought.content_hash],
            "openbrain_id": thought.openbrain_id,
        }
    markdown = render_markdown(thought, projected_at)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        if content_hashes is not None:
            content_hashes.setdefault(thought.content_hash, rel)
    return {"status": "would_create" if dry_run else "created", "path": rel, "openbrain_id": thought.openbrain_id}


def git_remote(wiki: pathlib.Path) -> str:
    remotes = subprocess.check_output(["git", "-C", str(wiki), "remote"], text=True).split()
    if "vps" in remotes:
        return "vps"
    if "origin" in remotes:
        return "origin"
    raise ProjectionError("projection_failed: no vps/origin git remote available")


def commit_and_push(wiki: pathlib.Path) -> dict[str, str]:
    remote = git_remote(wiki)
    subprocess.run(["git", "-C", str(wiki), "fetch", remote, "main"], check=True)

    # AP-44 (2026-05-20): stage local openbrain projections BEFORE the merge
    # so the merge sees a clean working tree even when a sibling projection on
    # another host has landed the same filename on origin first. Without this,
    # `git merge --ff-only` aborts on "untracked working tree files would be
    # overwritten by merge" and the job exits 1 in a hot loop, bloating the
    # err.log. We add only the openbrain inbox; everything else outside that
    # path is untouched. `add` with `check=False` because "nothing to add" is
    # a valid no-op state.
    subprocess.run(
        ["git", "-C", str(wiki), "add", "--", "pages/inbox/openbrain"],
        check=False,
    )

    merge = subprocess.run(["git", "-C", str(wiki), "merge", "--ff-only", f"{remote}/main"], text=True, capture_output=True)
    if merge.returncode != 0:
        # Fall back to a regular merge with "ours" strategy for the openbrain
        # inbox only — the local projection is the source of truth for the
        # openbrain payload, and sibling commits to the same id are byte-equal
        # by design (deterministic id->path mapping with stable content hash).
        merge_fallback = subprocess.run(
            ["git", "-C", str(wiki), "merge", f"{remote}/main",
             "-X", "ours", "-m", "openbrain: auto-merge concurrent sibling projection"],
            text=True, capture_output=True,
        )
        if merge_fallback.returncode != 0:
            raise ProjectionError(
                f"projection_failed: git merge (ff-only and ours-fallback) failed: "
                f"{merge_fallback.stderr.strip() or merge_fallback.stdout.strip()}"
            )
    status = subprocess.check_output(["git", "-C", str(wiki), "status", "--porcelain", "--", "pages/inbox/openbrain"], text=True)
    if not status.strip():
        return {"git": "no_changes", "remote": remote}
    subprocess.run(["git", "-C", str(wiki), "add", "--", "pages/inbox/openbrain"], check=True)
    commit = subprocess.run(
        ["git", "-C", str(wiki), "commit", "-m", "openbrain: project captured thoughts", "--", "pages/inbox/openbrain"],
        text=True,
        capture_output=True,
    )
    if commit.returncode != 0:
        raise ProjectionError(f"projection_failed: git commit failed: {commit.stderr.strip() or commit.stdout.strip()}")
    subprocess.run(["git", "-C", str(wiki), "push", remote, "HEAD:main"], check=True)
    head = subprocess.check_output(["git", "-C", str(wiki), "rev-parse", "--short", "HEAD"], text=True).strip()
    return {"git": "committed_pushed", "remote": remote, "head": head}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project OpenBrain MCP thoughts into the Obsidian wiki")
    parser.add_argument("--wiki", default=os.getcwd(), help="Path to the wiki working copy")
    parser.add_argument("--mcp-url", help="OpenBrain MCP endpoint URL; otherwise read env/config")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--days", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--commit", action="store_true", help="Commit and push pages/inbox/openbrain changes")
    parser.add_argument("--once", action="store_true", help="One launchd cycle: write, commit, and push")
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    args = parser.parse_args(argv)

    if args.once:
        args.write = True
        args.commit = True
    if not args.dry_run and not args.write:
        args.dry_run = True

    result: dict[str, Any] = {
        "ok": False,
        "projection_failed": False,
        "projected_at": ISO_NOW(),
        "wiki": str(pathlib.Path(args.wiki).expanduser().resolve()),
    }
    try:
        wiki = pathlib.Path(args.wiki).expanduser().resolve()
        url = load_mcp_url(args.mcp_url)
        thoughts = fetch_thoughts(url, args.limit, args.days)
        content_hashes = scan_content_hashes(wiki)
        projections = [
            project_thought(wiki, thought, args.dry_run, result["projected_at"], content_hashes)
            for thought in thoughts
        ]
        result.update(
            {
                "ok": True,
                "dry_run": args.dry_run,
                "thoughts_seen": len(thoughts),
                "created": sum(1 for p in projections if p["status"] == "created"),
                "updated": sum(1 for p in projections if p["status"] == "updated"),
                "would_create": sum(1 for p in projections if p["status"] == "would_create"),
                "would_update": sum(1 for p in projections if p["status"] == "would_update"),
                "duplicate_content": sum(1 for p in projections if p["status"] == "duplicate_content"),
                "exists": sum(1 for p in projections if p["status"] == "exists"),
                "projections": projections,
            }
        )
        if args.commit and not args.dry_run:
            result["git"] = commit_and_push(wiki)
    except Exception as exc:
        result.update({"ok": False, "projection_failed": True, "error": str(exc)})
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"projection_failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"ok={result['ok']} dry_run={result['dry_run']} thoughts_seen={result['thoughts_seen']} "
            f"created={result['created']} updated={result['updated']} "
            f"would_create={result['would_create']} would_update={result['would_update']} "
            f"duplicate_content={result['duplicate_content']} exists={result['exists']}"
        )
        for item in result["projections"]:
            print(f"{item['status']}: {item['path']}")
        if result.get("git"):
            print("git:", json.dumps(result["git"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
