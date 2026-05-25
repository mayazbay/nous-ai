#!/usr/bin/env python3
"""Tenant fitness probe for Camera Doctor V2."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))

from agents.camera_doctor import probe


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tenants").is_dir() and (parent / "agents").is_dir():
            return parent
    return here.parents[1]


def load_config(root: Path, tenant: str) -> dict:
    path = root / "tenants" / tenant / "camera_doctor.toml"
    if not path.is_file():
        raise FileNotFoundError(f"tenant config not found: {path}")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def erap_db_paths(config: dict) -> dict[str, str]:
    erap = config.get("erap")
    if not isinstance(erap, dict):
        raise ValueError("missing [erap] section")
    paths = {
        key: value for key, value in erap.items()
        if key.endswith("_db") and isinstance(value, str) and value
    }
    required = {"events_db", "camera_health_db"}
    missing = sorted(required - set(paths))
    if missing:
        raise ValueError(f"missing [erap] DB path(s): {', '.join(missing)}")
    return paths


def validate_chat_id(config: dict) -> int:
    chat_id = config.get("notify", {}).get("alert_chat_id")
    if not isinstance(chat_id, int) or isinstance(chat_id, bool):
        raise ValueError("[notify].alert_chat_id must be an integer")
    return chat_id


def ssh_echo(ssh_bin: str, host: str, timeout_s: int) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [
                ssh_bin,
                "-o", f"ConnectTimeout={timeout_s}",
                "-o", "BatchMode=yes",
                host,
                "echo", "ok",
            ],
            text=True,
            capture_output=True,
            timeout=timeout_s + 2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0 and "ok" in result.stdout, output


def run_probe(root: Path, tenant: str, ssh_bin: str, timeout_s: int) -> tuple[int, dict]:
    payload: dict = {"tenant": tenant, "checks": {}, "warnings": []}
    try:
        config = load_config(root, tenant)
        tenant_cfg = config.get("tenant", {})
        erap = config.get("erap", {})
        host = str(erap.get("ssh_host") or "")
        if not host:
            raise ValueError("missing [erap].ssh_host")
        db_paths = erap_db_paths(config)
        chat_id = validate_chat_id(config)
    except (FileNotFoundError, tomllib.TOMLDecodeError, ValueError) as exc:
        payload["status"] = "config_invalid"
        payload["error"] = str(exc)
        return 1, payload

    payload["display_name"] = tenant_cfg.get("display_name", tenant)
    payload["checks"]["erap_db_paths"] = db_paths
    payload["checks"]["notify"] = {"alert_chat_id": chat_id, "format": "int"}

    ok, ssh_output = ssh_echo(ssh_bin, host, timeout_s)
    payload["checks"]["ssh"] = {"host": host, "ok": ok, "output": ssh_output}
    if not ok:
        payload["status"] = "network_unreachable"
        return 2, payload

    iface = str(config.get("network", {}).get("wg_interface") or "")
    if not iface:
        payload["status"] = "config_invalid"
        payload["error"] = "missing [network].wg_interface"
        return 1, payload
    wg = probe.wg_handshake_age(iface)
    wg_binary = shutil.which("wg")
    max_age = int(config.get("thresholds", {}).get("wg_handshake_max_age_s", 600))
    age = int(wg.get("age_seconds", 10**9))
    wg_status = "ok"
    if age > max_age:
        if wg_binary is None:
            wg_status = "skipped_local_wg_unavailable"
        else:
            payload["status"] = "network_unreachable"
            payload["checks"]["wireguard"] = {
                "interface": iface,
                "age_seconds": age,
                "max_age_seconds": max_age,
                "status": "stale",
            }
            return 2, payload
    payload["checks"]["wireguard"] = {
        "interface": iface,
        "age_seconds": age,
        "max_age_seconds": max_age,
        "status": wg_status,
    }
    payload["status"] = "fit"
    return 0, payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Probe Camera Doctor tenant fitness.")
    ap.add_argument("tenant")
    ap.add_argument("--timeout", type=int, default=5)
    args = ap.parse_args(argv)

    root = Path(os.environ.get("PROBE_TENANT_REPO_ROOT", repo_root()))
    ssh_bin = os.environ.get("PROBE_TENANT_SSH", "ssh")
    code, payload = run_probe(root, args.tenant, ssh_bin, args.timeout)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code

if __name__ == "__main__":
    sys.exit(main())
