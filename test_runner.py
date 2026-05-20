"""Test runner for agent code validation."""

import subprocess
import sys
import os
from config import CODEBASE_PATH


def run_pytest(test_path="tests/", timeout=120):
    """Run pytest and return results."""
    cwd = os.path.abspath(CODEBASE_PATH)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "-q"],
            cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout + result.stderr
        # Detect collection errors (hallucinated imports)
        collection_errors = output.count("ERROR collecting") + output.count("ImportError") + output.count("ModuleNotFoundError")
        if collection_errors > 0:
            errors = collection_errors
            print(f"[Test] WARNING: {collection_errors} collection errors (hallucinated imports?)")
        return {
            "success": result.returncode == 0,
            "passed": output.count(" PASSED"),
            "failed": output.count(" FAILED"),
            "errors": output.count(" ERROR"),
            "output": output[-2000:] if len(output) > 2000 else output,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "passed": 0, "failed": 0, "errors": 1,
                "output": f"Pytest timed out after {timeout}s", "returncode": -1}
    except Exception as e:
        return {"success": False, "passed": 0, "failed": 0, "errors": 1,
                "output": f"Failed to run pytest: {e}", "returncode": -1}


def install_package(package_name):
    """Install a missing Python package."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", package_name],
            capture_output=True, text=True, timeout=120
        )
        return {"success": result.returncode == 0, "package": package_name,
                "output": result.stdout + result.stderr}
    except Exception as e:
        return {"success": False, "package": package_name, "output": str(e)}
