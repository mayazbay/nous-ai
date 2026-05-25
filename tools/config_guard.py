"""Config Guard — ensures config.py and graph.py survive restarts."""
import shutil
import os
from datetime import datetime

CONFIG = "/root/nous-agaas/config.py"
GRAPH = "/root/nous-agaas/graph.py"
BACKUP_DIR = "/root/nous-agaas/backups"

def backup_configs():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
    for f in [CONFIG, GRAPH]:
        name = os.path.basename(f)
        backup = os.path.join(BACKUP_DIR, f"{name}.{ts}")
        shutil.copy2(f, backup)
    # Keep only last 10 backups per file
    for prefix in ["config.py", "graph.py"]:
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith(prefix)])
        for old in backups[:-10]:
            os.remove(os.path.join(BACKUP_DIR, old))

def validate_config():
    import py_compile
    errors = []
    for f in [CONFIG, GRAPH]:
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(str(e))
    return errors

if __name__ == "__main__":
    backup_configs()
    errors = validate_config()
    if errors:
        print("ERRORS:", errors)
    else:
        print("Config guard: backed up + validated OK")
