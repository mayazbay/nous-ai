#!/usr/bin/env python3
"""Runs BEFORE factory starts. If this fails, systemd refuses to start."""
import sys, os
sys.path.insert(0, "/root/nous-agaas")
os.chdir("/root/nous-agaas")

errors = []

# 1. graph.py imports clean
try:
    import graph
    print("[OK] graph.py imports")
except Exception as e:
    errors.append(f"graph.py: {e}")
    print(f"[FAIL] graph.py: {e}")

# 2. task_db functions exist
try:
    from tools.task_db import get_pending_tasks, update_task, create_task
    print("[OK] task_db functions")
except ImportError as e:
    errors.append(f"task_db: {e}")
    print(f"[FAIL] task_db: {e}")

# 3. wiki exists and not empty
wiki = "/root/nous-agaas/wiki/pages/lessons/auto_lessons.md"
if os.path.isfile(wiki) and os.path.getsize(wiki) > 1000:
    print(f"[OK] wiki ({os.path.getsize(wiki)} bytes)")
else:
    errors.append("wiki missing or corrupted")
    print("[FAIL] wiki")

# 4. Read graph.py source for all code checks
with open("/root/nous-agaas/graph.py") as f:
    src = f.read()

# 5. Command palette bug check
app_tsx = "/root/nous-agaas/codebase/satory-frontend/src/App.tsx"
if os.path.isfile(app_tsx):
    with open(app_tsx) as f:
        app = f.read()
    if "isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)" in app:
        print("[OK] command palette = false")
    elif "isCommandPaletteOpen" in app and "satory_auth" in app:
        errors.append("COMMAND PALETTE BUG: auto-opens on auth")
        print("[FAIL] command palette bug ACTIVE")
    else:
        print("[OK] command palette (not found, ok)")

# 6. LAW-006 hard block exists (not just prompt)
if "law006_no_requirement_mapping" in src:
    print("[OK] LAW-006 hard block")
else:
    errors.append("LAW-006 hard block missing in graph.py")
    print("[FAIL] LAW-006 hard block")

# 7. LAW-011 hard block exists (not just warning)
if "law011_no_business_outcome" in src:
    print("[OK] LAW-011 hard block")
else:
    errors.append("LAW-011 hard block missing in graph.py")
    print("[FAIL] LAW-011 hard block")

# 8. failed_checks initialized BEFORE content checks (not after)
site_def_idx = src.find("site = os.getenv")
content_check_idx = src.find("for endpoint, expected, name in content_checks")
if site_def_idx > 0 and content_check_idx > 0 and site_def_idx < content_check_idx:
    print("[OK] site + failed_checks init order")
else:
    errors.append("site/failed_checks initialization order bug in deploy_node")
    print("[FAIL] site/failed_checks init order")

# 9. LAWS constant present
if "LAW-001 EVOLUTION" in src and "LAW-013 TRUTH" in src:
    print("[OK] LAWS constant present")
else:
    errors.append("LAWS constant missing or incomplete")
    print("[FAIL] LAWS constant")

# 10. create_task() schema-safe (no more column crashes)
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("task_db", "/root/nous-agaas/tools/task_db.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = open("/root/nous-agaas/tools/task_db.py").read()
    if "PRAGMA table_info" in src:
        print("[OK] create_task schema-safe")
    else:
        errors.append("create_task() is NOT schema-safe - will crash on missing columns")
        print("[FAIL] create_task not schema-safe")
except Exception as e:
    errors.append(f"task_db check failed: {e}")
    print(f"[FAIL] task_db: {e}")

# 11. Obsidian wiki exists (Karpathy LLM Wiki)
obs_wiki = "/root/nous-agaas/wiki/laws"
if os.path.isdir(obs_wiki):
    law_count = len([f for f in os.listdir(obs_wiki) if f.startswith("LAW-")])
    if law_count >= 12:
        print(f"[OK] Wiki laws ({law_count} law files)")
    else:
        errors.append(f"Wiki laws incomplete: only {law_count} law files (need 12)")
        print(f"[FAIL] Wiki laws ({law_count}/12 law files)")
else:
    errors.append("Wiki laws directory not found at /root/nous-agaas/wiki/laws/")
    print("[FAIL] Obsidian wiki missing")


# 12. PHANTOM INNER directory must NOT exist (LESSON-048)
phantom = "/root/nous-agaas/codebase/satory-frontend/satory-frontend"
if os.path.exists(phantom):
    errors.append(f"PHANTOM INNER directory exists at {phantom} — factory must NEVER write to satory-frontend/satory-frontend/. See LESSON-048.")
    print("[FAIL] PHANTOM INNER directory present")
else:
    print("[OK] no phantom INNER directory")

if errors:
    print(f"\n*** {len(errors)} ERRORS — REFUSING TO START ***")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("\n*** ALL CHECKS PASSED ***")
    sys.exit(0)
