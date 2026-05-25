#!/usr/bin/env python3
"""Clean-boundary wrapper for scheduled Mercury refresh.

The old launchd command regenerated tracked Mercury files directly in the Mac
vault. If another lane had dirty files, Mercury added more dirt and the next
agent inherited a confusing peer-owned residual. This wrapper only writes
Mercury outputs when the worktree has no non-Mercury dirt, then commits the
generated outputs path-limited.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
MERCURY_OUTPUTS = (
    "pages/mercury/facts.jsonl",
    "pages/progress/claude-memory/MEMORY-mercury.md",
)


def run(cmd: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def parse_status(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            paths.append(path)
    return paths


def dirty_paths(repo: Path) -> list[str]:
    result = run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, timeout=30)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "git status failed").strip())
    return parse_status(result.stdout)


def split_mercury_dirty(paths: list[str]) -> tuple[list[str], list[str]]:
    mercury = [path for path in paths if path in MERCURY_OUTPUTS]
    other = [path for path in paths if path not in MERCURY_OUTPUTS]
    return mercury, other


def print_block(title: str, paths: list[str]) -> None:
    print(title)
    for path in paths:
        print(f"  - {path}")


def commit_outputs(repo: Path, *, dry_run: bool, no_push: bool) -> int:
    mercury, other = split_mercury_dirty(dirty_paths(repo))
    if other:
        print_block("mercury_refresh: skip commit; non-Mercury dirty paths appeared:", other)
        return 0
    if not mercury:
        print("mercury_refresh: clean; no Mercury output changes")
        return 0
    if dry_run:
        print_block("mercury_refresh: dry-run would commit:", mercury)
        return 0

    add = run(["git", "add", *MERCURY_OUTPUTS], cwd=repo, timeout=60)
    if add.returncode != 0:
        sys.stderr.write(add.stderr or add.stdout)
        return add.returncode or 1

    staged = run(["git", "diff", "--cached", "--quiet", "--", *MERCURY_OUTPUTS], cwd=repo, timeout=30)
    if staged.returncode == 0:
        print("mercury_refresh: clean; no staged Mercury changes")
        return 0

    commit = run(
        ["git", "commit", "-m", "auto-sync: mercury refresh", "--", *MERCURY_OUTPUTS],
        cwd=repo,
        timeout=120,
    )
    if commit.returncode != 0:
        sys.stderr.write(commit.stderr or commit.stdout)
        return commit.returncode or 1
    print(commit.stdout.strip())

    if no_push:
        return 0

    failed = False
    for remote in ("vps", "github", "air"):
        push = run(["git", "push", remote, "HEAD:main"], cwd=repo, timeout=180)
        if push.returncode != 0:
            failed = True
            sys.stderr.write(f"mercury_refresh: push {remote} failed:\n{push.stderr or push.stdout}\n")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    before = dirty_paths(repo)
    _mercury_before, other_before = split_mercury_dirty(before)
    if other_before:
        print_block("mercury_refresh: skipped; shared worktree has non-Mercury dirty paths:", other_before)
        return 0

    if args.dry_run:
        print("mercury_refresh: dry-run generation skipped")
        return commit_outputs(repo, dry_run=True, no_push=args.no_push)

    python = repo / ".venv" / "bin" / "python"
    py = str(python if python.exists() else Path(sys.executable))
    for cmd in (
        [py, "tools/mercury_seed.py", "--apply"],
        ["bash", "tools/mercury_phase3_regen.sh", "--regen"],
    ):
        result = run(cmd, cwd=repo, timeout=180)
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode != 0:
            sys.stderr.write(result.stderr or result.stdout)
            return result.returncode or 1

    return commit_outputs(repo, dry_run=False, no_push=args.no_push)


if __name__ == "__main__":
    raise SystemExit(main())
