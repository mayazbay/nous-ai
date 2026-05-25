#!/usr/bin/env python3
"""Credentials discovery CLI for Nous AGaaS.

Authoritative data source: pages/secrets-manifest.md.
Doctrine source: pages/skills/credentials-discovery/SKILL.md.

This tool deliberately separates discovery from retrieval:
- find/audit modes never print secret values.
- source mode is the only path that prints a value, as an export statement.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shlex
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "pages" / "secrets-manifest.md"
MANIFEST_ABORT = "manifest v2 not yet shipped by Opus — abort"
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HOST_RE = re.compile(r"\b(Mac|Air|VPS)\b(?:\s+only)?(?:\s+`([^`]+)`)?", re.IGNORECASE)
REMOTE_SSH_TARGETS = {
    "mac": os.environ.get("CREDENTIALS_DISCOVERY_SSH_MAC", "mac"),
    "air": os.environ.get("CREDENTIALS_DISCOVERY_SSH_AIR", "air"),
    "vps": os.environ.get("CREDENTIALS_DISCOVERY_SSH_VPS", "root@65.108.215.200"),
}


class ManifestNotReady(RuntimeError):
    pass


class EnvReadError(RuntimeError):
    pass


@dataclass(frozen=True)
class EnvFile:
    host: str
    path: str
    service: str
    notes: str = ""


@dataclass
class Credential:
    key: str
    description: str
    services: list[str]
    hosts: set[str]
    rotation: str
    explicit_paths: dict[str, set[str]] = field(default_factory=dict)


@dataclass
class Manifest:
    path: pathlib.Path
    env_files: list[EnvFile]
    credentials: dict[str, Credential]


def normalize_host(host: str) -> str:
    value = host.strip().lower()
    if value == "mac":
        return "mac"
    if value == "air":
        return "air"
    if value == "vps":
        return "vps"
    return value


def strip_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_services(cell: str) -> list[str]:
    values = [part.strip() for part in re.split(r",|/|\band\b", cell) if part.strip()]
    return values or [cell.strip()]


def parse_host_cell(cell: str, env_files: list[EnvFile]) -> tuple[set[str], dict[str, set[str]]]:
    hosts: set[str] = set()
    explicit: dict[str, set[str]] = {}
    for match in HOST_RE.finditer(cell):
        host = normalize_host(match.group(1))
        hosts.add(host)
        path_hint = strip_cell(match.group(2) or "")
        if path_hint:
            explicit.setdefault(host, set()).update(resolve_path_hint(host, path_hint, env_files))
    return hosts, explicit


def resolve_path_hint(host: str, path_hint: str, env_files: list[EnvFile]) -> list[str]:
    if path_hint.startswith("/"):
        return [path_hint]
    suffix = path_hint.lstrip("./")
    matches = [env.path for env in env_files if env.host == host and env.path.endswith(suffix)]
    return matches or [path_hint]


def load_manifest(path: pathlib.Path = DEFAULT_MANIFEST) -> Manifest:
    if not path.exists():
        raise ManifestNotReady(MANIFEST_ABORT)
    text = path.read_text(encoding="utf-8")
    if "Secrets Manifest v2" not in text or "## Active credentials" not in text:
        raise ManifestNotReady(MANIFEST_ABORT)

    env_files: list[EnvFile] = []
    credentials: dict[str, Credential] = {}
    section = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line
            continue
        if not line.startswith("|"):
            continue
        cells = split_table_row(line)
        if not cells or cells[0].lower() in {"host", "key"} or set(cells[0]) == {"-"}:
            continue

        if section.startswith("## .env files inventory") and len(cells) >= 4:
            host = normalize_host(cells[0])
            env_files.append(
                EnvFile(
                    host=host,
                    path=strip_cell(cells[1]),
                    service=strip_cell(cells[2]),
                    notes=strip_cell(cells[3]),
                )
            )
            continue

        if section.startswith("## Active credentials") or section.startswith("### "):
            if len(cells) < 5 or not re.match(r"^[A-Z0-9_]+$", cells[0]):
                continue
            key = cells[0].strip()
            hosts, explicit_paths = parse_host_cell(cells[3], env_files)
            credentials[key] = Credential(
                key=key,
                description=strip_cell(cells[1]),
                services=parse_services(strip_cell(cells[2])),
                hosts=hosts,
                rotation=strip_cell(cells[4]),
                explicit_paths=explicit_paths,
            )

    if not env_files or not credentials:
        raise ManifestNotReady(MANIFEST_ABORT)
    return Manifest(path=path, env_files=env_files, credentials=credentials)


def parse_env(content: str, include_values: bool = False) -> dict[str, str | None]:
    parsed: dict[str, str | None] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not KEY_RE.match(key):
            continue
        value = clean_env_value(value.strip()) if include_values else None
        parsed[key] = value
    return parsed


def clean_env_value(value: str) -> str:
    if not value:
        return ""
    if (value[0], value[-1:]) in {('"', '"'), ("'", "'")} and len(value) >= 2:
        return value[1:-1]
    match = re.search(r"\s+#", value)
    if match:
        value = value[: match.start()].rstrip()
    return value


def _read_local_file(path: str) -> str:
    return pathlib.Path(path).read_text(encoding="utf-8")


def _read_remote_file(host: str, path: str, timeout_s: int = 15) -> str:
    target = REMOTE_SSH_TARGETS[host]
    result = subprocess.run(
        ["ssh", target, "cat", path],
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    if result.returncode != 0:
        raise EnvReadError(f"{host}:{path}:ssh_exit_{result.returncode}")
    return result.stdout


def current_host_alias() -> str:
    override = os.environ.get("CREDENTIALS_DISCOVERY_LOCAL_HOST", "").strip().lower()
    if override in {"mac", "air", "vps"}:
        return override
    hostname = socket.gethostname().lower()
    if "air" in hostname:
        return "air"
    if pathlib.Path("/root/nous-agaas").exists():
        return "vps"
    return "mac"


def read_env_file(host: str, path: str, include_values: bool = False) -> dict[str, str | None]:
    host = normalize_host(host)
    try:
        content = _read_local_file(path) if host == current_host_alias() else _read_remote_file(host, path)
    except FileNotFoundError as exc:
        raise EnvReadError(f"{host}:{path}:missing") from exc
    except subprocess.TimeoutExpired as exc:
        raise EnvReadError(f"{host}:{path}:ssh_timeout") from exc
    except OSError as exc:
        raise EnvReadError(f"{host}:{path}:read_error") from exc
    return parse_env(content, include_values=include_values)


def candidate_env_files(manifest: Manifest, credential: Credential, host: str | None = None) -> list[EnvFile]:
    hosts = {normalize_host(host)} if host else set(credential.hosts)
    candidates: list[EnvFile] = []
    for env in manifest.env_files:
        if hosts and env.host not in hosts:
            continue
        explicit = credential.explicit_paths.get(env.host)
        if explicit and env.path not in explicit:
            continue
        candidates.append(env)
    if not candidates and host:
        return [env for env in manifest.env_files if env.host == normalize_host(host)]
    return candidates


def find_key(manifest: Manifest, key: str) -> tuple[int, dict[str, object]]:
    credential = manifest.credentials.get(key)
    if credential is None:
        return 1, {"key": key, "known": False, "paths": [], "services": [], "rotation": None}

    paths: list[dict[str, object]] = []
    for env in candidate_env_files(manifest, credential):
        item: dict[str, object] = {"host": env.host, "file": env.path, "exists": False}
        try:
            keys = read_env_file(env.host, env.path, include_values=False)
            item["exists"] = key in keys
        except EnvReadError as exc:
            item["error"] = str(exc)
        paths.append(item)

    return 0, {
        "key": key,
        "known": True,
        "paths": paths,
        "services": credential.services,
        "rotation": credential.rotation,
    }


def collect_actual_env_keys(
    manifest: Manifest,
    include_staged: bool = True,
    hosts: set[str] | None = None,
) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    actual: dict[str, list[dict[str, str]]] = {}
    errors: list[str] = []

    for env in manifest.env_files:
        if hosts is not None and env.host not in hosts:
            continue
        try:
            keys = read_env_file(env.host, env.path, include_values=False)
        except EnvReadError as exc:
            errors.append(str(exc))
            continue
        for key in keys:
            actual.setdefault(key, []).append({"host": env.host, "file": env.path})

    if include_staged:
        for path, content in staged_env_contents():
            for key in parse_env(content, include_values=False):
                actual.setdefault(key, []).append({"host": "staged", "file": path})

    return actual, errors


def staged_env_contents() -> list[tuple[str, str]]:
    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        return []
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    out: list[tuple[str, str]] = []
    for path in result.stdout.splitlines():
        if not is_real_env_path(path):
            continue
        show = subprocess.run(
            ["git", "show", f":{path}"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if show.returncode == 0:
            out.append((path, show.stdout))
    return out


def is_real_env_path(path: str) -> bool:
    name = pathlib.PurePosixPath(path).name
    return name.endswith(".env") and not name.endswith((".env.example", ".env.template", ".env.sample"))


def audit_manifest(
    manifest: Manifest,
    include_staged: bool = True,
    hosts: set[str] | None = None,
) -> tuple[int, dict[str, object]]:
    actual, errors = collect_actual_env_keys(manifest, include_staged=include_staged, hosts=hosts)
    manifest_keys = set(manifest.credentials)
    actual_keys = set(actual)
    undocumented = sorted(actual_keys - manifest_keys)
    missing_runtime = sorted(manifest_keys - actual_keys)
    report: dict[str, object] = {
        "manifest": str(manifest.path),
        "ok": not undocumented and not errors,
        "manifest_key_count": len(manifest_keys),
        "actual_key_count": len(actual_keys),
        "hosts": sorted(hosts) if hosts is not None else ["air", "mac", "vps"],
        "undocumented_keys": undocumented,
        "manifest_keys_missing_runtime": missing_runtime,
        "read_errors": errors,
    }
    return (0 if report["ok"] else 1), report


def source_key(manifest: Manifest, key: str, host: str) -> tuple[int, str, str]:
    host = normalize_host(host)
    credential = manifest.credentials.get(key)
    if credential is None:
        return 1, "", f"unknown key in manifest: {key}\n"
    if host not in {"mac", "air", "vps"}:
        return 1, "", "host must be one of: mac, air, vps\n"
    if credential.hosts and host not in credential.hosts:
        return 1, "", f"{key} is not declared on host {host}\n"

    errors: list[str] = []
    for env in candidate_env_files(manifest, credential, host=host):
        try:
            values = read_env_file(env.host, env.path, include_values=True)
        except EnvReadError as exc:
            errors.append(str(exc))
            continue
        if key in values:
            value = values[key] or ""
            return 0, f"export {key}={shlex.quote(value)}\n", ""
    suffix = f" ({'; '.join(errors)})" if errors else ""
    return 1, "", f"{key} not found on host {host}{suffix}\n"


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find, audit, and source Nous AGaaS credentials without leaking values.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to pages/secrets-manifest.md")
    sub = parser.add_subparsers(dest="command", required=True)

    find = sub.add_parser("find", help="Find credential metadata and declared runtime paths")
    find.add_argument("key")

    audit = sub.add_parser("audit", help="Compare runtime .env keys against the manifest")
    audit.add_argument("--strict", action="store_true", help="Exit non-zero and print missing manifest keys on drift")
    audit.add_argument("--no-staged", action="store_true", help="Ignore staged .env files")
    audit.add_argument(
        "--hosts",
        default="mac,air,vps",
        help="Comma-separated host filter for runtime env reads (default: mac,air,vps)",
    )

    source = sub.add_parser("source", help="Print export KEY=<value> for explicit shell sourcing")
    source.add_argument("key")
    source.add_argument("--host", required=True, choices=["mac", "air", "vps"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(pathlib.Path(args.manifest))
    except ManifestNotReady:
        print(MANIFEST_ABORT, file=sys.stderr)
        return 2

    if args.command == "find":
        code, payload = find_key(manifest, args.key)
        print_json(payload)
        return code

    if args.command == "audit":
        hosts = {normalize_host(part) for part in args.hosts.split(",") if part.strip()}
        invalid_hosts = sorted(hosts - {"mac", "air", "vps"})
        if invalid_hosts:
            print(f"invalid host(s): {', '.join(invalid_hosts)}", file=sys.stderr)
            return 2
        code, payload = audit_manifest(manifest, include_staged=not args.no_staged, hosts=hosts)
        print_json(payload)
        if args.strict and (payload["undocumented_keys"] or payload["read_errors"]):
            print("credentials drift: undocumented env keys missing from pages/secrets-manifest.md:", file=sys.stderr)
            for key in payload["undocumented_keys"]:
                print(f"  - {key}", file=sys.stderr)
            for error in payload["read_errors"]:
                print(f"read error: {error}", file=sys.stderr)
            return 1
        return code

    if args.command == "source":
        code, stdout, stderr = source_key(manifest, args.key, args.host)
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        return code

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
