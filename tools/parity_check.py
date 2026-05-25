"""Failover parity check — hash a deterministic manifest of substrate files.

Step 7 of Ship 1: produces `pages/systems/parity-latest.json` capturing a
sha256 of each manifest file plus a roll-up `manifest_sha256`. Air / VPS can
re-compute after `git pull` and compare against the on-disk value to confirm
content parity with the Mac that pushed.

Step 7b will wire `tools/model_failover_state.py::_recompute_parity` to call
`compute_and_write`. This module is stdlib-only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform  # noqa: F401  (kept for future host metadata expansion)
import socket
import sys  # noqa: F401  (kept available for CLI extensions)
from pathlib import Path
from typing import Any


MANIFEST_REL = Path("pages/systems/parity-manifest.txt")
PARITY_LATEST_REL = Path("pages/systems/parity-latest.json")

_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_CHUNK = 65536


def load_manifest(wiki: Path) -> list[str]:
    """Read parity-manifest.txt, return list of relative file paths.

    Ignores blank lines and lines beginning with `#`. Order is preserved
    exactly as listed in the file — do not sort.
    """
    manifest_path = wiki / MANIFEST_REL
    paths: list[str] = []
    with manifest_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            paths.append(line)
    return paths


def file_sha256(path: Path) -> str:
    """sha256 hex of file bytes.

    Returns sha256 of empty bytes if:
      - the file does not exist, OR
      - the path is a broken symlink (target missing).

    This intentional fallback keeps parity reproducible across hosts where a
    transient artifact (e.g. HANDOFF-AUTO-LATEST.symlink target) may not yet
    resolve. Hashing is chunked so large files don't blow memory.
    """
    try:
        if path.is_symlink() and not path.exists():
            return _EMPTY_SHA256
        if not path.exists():
            return _EMPTY_SHA256
    except OSError:
        return _EMPTY_SHA256

    hasher = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(_CHUNK)
                if not chunk:
                    break
                hasher.update(chunk)
    except OSError:
        return _EMPTY_SHA256
    return hasher.hexdigest()


def _now_iso_plus5() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=5))).isoformat()


def compute_parity(wiki: Path) -> dict[str, Any]:
    """Compute and return the parity dict WITHOUT writing to disk.

    Shape:
        {
            "algo": "sha256",
            "host": "<hostname>",
            "ts": "<ISO with +05:00 tz>",
            "manifest_sha256": "<hex>",
            "files": {"<relpath>": "<hex>", ...}
        }

    manifest_sha256 = sha256("\\n".join(f"{path}:{file_sha256(wiki/path)}" ...))
    where the ordering is the manifest's listed order.
    """
    manifest_paths = load_manifest(wiki)
    files: dict[str, str] = {}
    parts: list[str] = []
    for rel in manifest_paths:
        digest = file_sha256(wiki / rel)
        files[rel] = digest
        parts.append(f"{rel}:{digest}")

    manifest_sha256 = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return {
        "algo": "sha256",
        "host": socket.gethostname(),
        "ts": _now_iso_plus5(),
        "manifest_sha256": manifest_sha256,
        "files": files,
    }


def compute_and_write(wiki: Path) -> Path:
    """Compute parity and write atomically to pages/systems/parity-latest.json.

    Atomic write: serialize to `<dest>.tmp`, fsync, then `os.rename` into place.
    Returns the path written.
    """
    parity = compute_parity(wiki)
    dest = wiki / PARITY_LATEST_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")

    payload = json.dumps(parity, indent=2, sort_keys=False) + "\n"
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            # fsync can fail on some filesystems (e.g. tmpfs in containers);
            # we still rename — atomicity is preserved by rename itself.
            pass
    os.rename(tmp, dest)
    return dest


def verify(wiki: Path) -> tuple[bool, str]:
    """Recompute parity for this host and compare against on-disk parity-latest.json.

    Returns (ok, message). ok=True iff computed manifest_sha256 equals the
    on-disk value. Used by Air/VPS after `git pull` as a content-parity gate.
    If the parity file is absent, returns (False, "no parity-latest.json").
    """
    dest = wiki / PARITY_LATEST_REL
    if not dest.exists():
        return False, "no parity-latest.json"
    try:
        on_disk = json.loads(dest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"parity-latest.json unreadable: {exc}"

    computed = compute_parity(wiki)
    on_disk_root = on_disk.get("manifest_sha256")
    computed_root = computed["manifest_sha256"]
    if on_disk_root == computed_root:
        return True, f"parity OK manifest_sha256={computed_root}"

    # Diagnose which file(s) drifted.
    on_disk_files = on_disk.get("files", {}) or {}
    drifted: list[str] = []
    for rel, digest in computed["files"].items():
        if on_disk_files.get(rel) != digest:
            drifted.append(rel)
    drift_summary = ", ".join(drifted) if drifted else "(no per-file diff found)"
    return (
        False,
        f"parity DRIFT on-disk={on_disk_root} computed={computed_root} drifted={drift_summary}",
    )


def _default_wiki() -> Path:
    here = Path(__file__).resolve().parents[1]
    if (here / "pages").exists():
        return here
    if (here / "wiki" / "pages").exists():
        return here / "wiki"
    return here


def main() -> int:
    parser = argparse.ArgumentParser(description="Failover parity check")
    parser.add_argument(
        "--wiki",
        type=Path,
        default=Path(os.environ.get("NOUS_WIKI") or _default_wiki()),
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Check on-disk parity vs computed; exit 1 on drift",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print parity dict as JSON",
    )
    args = parser.parse_args()

    if args.verify:
        ok, msg = verify(args.wiki)
        print(msg)
        return 0 if ok else 1

    path = compute_and_write(args.wiki)
    if args.json:
        print(path.read_text())
    else:
        print(f"wrote {path.relative_to(args.wiki)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
