"""Deploy tool — actually runs deployment commands. Ships code to production."""

import subprocess
import os

def deploy_frontend():
    """Deploy satory-frontend to Vercel. Returns success status and output."""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "codebase", "satory-frontend")
    
    if not os.path.isdir(frontend_dir):
        return {"success": False, "output": "satory-frontend directory not found"}
    
    # HARD GUARD: Force vite build before every deploy
    import json as _json
    pkg_path = os.path.join(frontend_dir, "package.json")
    if os.path.isfile(pkg_path):
        with open(pkg_path) as _f:
            _pkg = _json.load(_f)
        changed = False
        if _pkg.get("scripts", {}).get("build") != "vite build":
            _pkg["scripts"]["build"] = "vite build"
            _pkg["scripts"]["dev"] = "vite"
            _pkg["scripts"]["preview"] = "vite preview"
            changed = True
        for dep_key in ["dependencies", "devDependencies"]:
            if "react-scripts" in _pkg.get(dep_key, {}):
                del _pkg[dep_key]["react-scripts"]
                changed = True
        if changed:
            with open(pkg_path, "w") as _f:
                _json.dump(_pkg, _f, indent=2)
            print("[Deploy] GUARD: Forced vite build in package.json")

    steps = [
        (["npm", "install", "--legacy-peer-deps"], "Installing dependencies"),
        (["npm", "run", "build"], "Building frontend"),
        (["vercel", "deploy", "--prod", "--yes", "--token", os.getenv("VERCEL_TOKEN", "")], "Deploying to Vercel"),
    ]
    
    outputs = []
    for cmd, desc in steps:
        try:
            result = subprocess.run(cmd, cwd=frontend_dir, capture_output=True, text=True, timeout=300)
            outputs.append(desc + ": " + ("OK" if result.returncode == 0 else "FAILED"))
            if result.returncode != 0:
                outputs.append(result.stderr[:500])
                return {"success": False, "output": "\n".join(outputs)}
        except Exception as e:
            outputs.append(desc + ": ERROR " + str(e))
            return {"success": False, "output": "\n".join(outputs)}
    
    # Verify live site
    import requests
    try:
        resp = requests.get("https://satory.nousagaas.com", timeout=10)
        outputs.append("Live site: HTTP " + str(resp.status_code))
    except Exception:
        outputs.append("Live site: could not verify")
    
    return {"success": True, "output": "\n".join(outputs)}


def verify_live_site():
    """Check if satory.nousagaas.com is working."""
    import requests
    try:
        resp = requests.get("https://satory.nousagaas.com", timeout=10)
        return {"status_code": resp.status_code, "working": resp.status_code == 200}
    except Exception as e:
        return {"status_code": 0, "working": False, "error": str(e)}
