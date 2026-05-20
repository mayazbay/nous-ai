"""Health check and redundancy monitoring for the factory."""

import os
import datetime
import subprocess
from config import CODEBASE_PATH, LOG_DIR


def check_system_health() -> dict:
    """Comprehensive system health check."""
    health = {
        "timestamp": datetime.datetime.now().isoformat(),
        "checks": {},
        "overall": True,
    }

    # 1. Disk space
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            usage_pct = int(parts[4].replace("%", "")) if len(parts) > 4 else 0
            health["checks"]["disk"] = {
                "ok": usage_pct < 85,
                "usage_pct": usage_pct,
                "alert": f"Disk at {usage_pct}%" if usage_pct >= 85 else None
            }
    except Exception as e:
        health["checks"]["disk"] = {"ok": False, "error": str(e)}

    # 2. Codebase integrity
    codebase_ok = os.path.isdir(CODEBASE_PATH) and os.path.isdir(os.path.join(CODEBASE_PATH, "erap"))
    health["checks"]["codebase"] = {
        "ok": codebase_ok,
        "path": CODEBASE_PATH,
    }

    # 3. ChromaDB
    chromadb_ok = os.path.isdir("./data/chromadb")
    health["checks"]["chromadb"] = {"ok": chromadb_ok}

    # 4. Logs directory writable
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        test_file = os.path.join(LOG_DIR, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        health["checks"]["logs"] = {"ok": True}
    except Exception as e:
        health["checks"]["logs"] = {"ok": False, "error": str(e)}

    # 5. Git repo status
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=os.path.abspath(CODEBASE_PATH),
            capture_output=True, text=True, timeout=10
        )
        health["checks"]["git"] = {
            "ok": result.returncode == 0,
            "uncommitted": len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        }
    except Exception:
        health["checks"]["git"] = {"ok": False}

    # 6. API connectivity (check our own backend)
    try:
        import requests
        resp = requests.get("https://api.nousagaas.com/api/erap", timeout=10)
        health["checks"]["backend_api"] = {
            "ok": resp.status_code == 200,
            "status_code": resp.status_code
        }
    except Exception as e:
        health["checks"]["backend_api"] = {"ok": False, "error": str(e)}

    # 7. Camera VPN connectivity
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "10.235.1.3"],
            capture_output=True, text=True, timeout=5
        )
        health["checks"]["camera_vpn"] = {"ok": result.returncode == 0}
    except Exception:
        health["checks"]["camera_vpn"] = {"ok": False, "note": "VPN may not be on this machine"}

    # Overall status
    health["overall"] = all(
        c.get("ok", False) for c in health["checks"].values()
        if "camera_vpn" not in str(c)  # VPN might not be on local machine
    )

    return health


def get_health_summary(health: dict) -> str:
    """Format health check as a compact string for Telegram."""
    lines = []
    for name, check in health.get("checks", {}).items():
        icon = "✅" if check.get("ok") else "❌"
        detail = ""
        if "usage_pct" in check:
            detail = f" ({check['usage_pct']}%)"
        elif "error" in check:
            detail = f" ({check['error'][:50]})"
        elif "uncommitted" in check:
            detail = f" ({check['uncommitted']} uncommitted)"
        lines.append(f"{icon} {name}{detail}")
    return "\n".join(lines)


def check_backup_freshness() -> dict:
    """Check when the last backup/archive was made."""
    backup_info = {"last_backup": None, "age_hours": None, "needs_backup": True}

    # Check for any tar.gz files
    for path in ["/root/", "/Users/madia/Desktop/"]:
        try:
            for f in os.listdir(path):
                if "archive" in f.lower() and f.endswith(".tar.gz"):
                    fpath = os.path.join(path, f)
                    mtime = os.path.getmtime(fpath)
                    age_hours = (datetime.datetime.now().timestamp() - mtime) / 3600
                    if backup_info["age_hours"] is None or age_hours < backup_info["age_hours"]:
                        backup_info["last_backup"] = fpath
                        backup_info["age_hours"] = round(age_hours, 1)
                        backup_info["needs_backup"] = age_hours > 24 * 7  # Alert if >7 days
        except Exception:
            pass

    return backup_info
