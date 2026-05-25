#!/usr/bin/env bash
# Atomically flip a Camera Doctor tenant live. Do not run for Satory until the
# 7-clean-cycle gate passes and Madi approves the live flip.
set -euo pipefail

[ "$#" -eq 1 ] || { echo "usage: $0 <tenant>" >&2; exit 2; }
TENANT="$1"
case "$TENANT" in *[!A-Za-z0-9_-]*|"") echo "ERROR: invalid tenant slug" >&2; exit 2 ;; esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
ROOT="${CAMERA_DOCTOR_REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
AIR="${CAMERA_DOCTOR_AIR_HOST:-air}"
SSH="${CAMERA_DOCTOR_SSH:-ssh}"
SCP="${CAMERA_DOCTOR_SCP:-scp}"
STATE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/camera_doctor_cutover.XXXXXX")"
STATE="$STATE_DIR/state.json"
SUCCESS=0

rollback() {
  if [ "$SUCCESS" != "1" ] && [ -f "$STATE" ]; then
    python3 - "$STATE" <<'PY' >&2 || true
import json, os, shutil, sys
for item in reversed(json.load(open(sys.argv[1])).get("backups", [])):
    if os.path.exists(item["backup"]):
        tmp = f'{item["path"]}.rollback.{os.getpid()}'
        shutil.copy2(item["backup"], tmp)
        os.replace(tmp, item["path"])
print("camera_doctor_live_cutover: rolled back local TOML/plist edits")
PY
  fi
  rm -rf "$STATE_DIR"
}
trap rollback EXIT

python3 - "$ROOT" "$TENANT" "$STATE_DIR" <<'PY'
import json, os, plistlib, re, shutil, sys, tomllib
from pathlib import Path

root, tenant, state_dir = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
cfg_path = root / "tenants" / tenant / "camera_doctor.toml"
backup_dir = state_dir / "backups"
backup_dir.mkdir()
if not cfg_path.is_file():
    raise SystemExit(f"ERROR: tenant config not found: {cfg_path}")

cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
mode = str(cfg.get("mode", {}).get("mode", "dry_run"))
if mode != "dry_run":
    raise SystemExit(f"ERROR: expected [mode].mode='dry_run' before cutover, got {mode!r}")
if not isinstance(cfg.get("notify", {}).get("alert_chat_id"), int):
    raise SystemExit("ERROR: [notify].alert_chat_id must be an integer before live cutover")

def load_cd_plist(path):
    with path.open("rb") as fh:
        data = plistlib.load(fh)
    args = [str(x) for x in data.get("ProgramArguments", [])]
    ok = "agents.camera_doctor.main" in args and "--tenant" in args and tenant in args
    return data if ok else None

plists = []
for base in (root / "tenants" / tenant / "launchd", root / "tools" / "launchd"):
    if base.is_dir():
        for path in sorted(base.glob("*.plist")):
            data = load_cd_plist(path)
            if data is not None:
                plists.append((path, data))
if not plists:
    raise SystemExit(f"ERROR: no Camera Doctor launchd plist found for tenant {tenant!r}")

backups = []
def backup(path):
    target = backup_dir / f"{len(backups)}-{path.name}"
    shutil.copy2(path, target)
    backups.append({"path": str(path), "backup": str(target)})

def replace(path, data, *, plist=False):
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if plist:
        with tmp.open("wb") as fh:
            plistlib.dump(data, fh, sort_keys=False)
    else:
        tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)

backup(cfg_path)
for path, _ in plists:
    backup(path)
(state_dir / "state.json").write_text(json.dumps({"backups": backups}), encoding="utf-8")

lines, in_mode, changed = cfg_path.read_text(encoding="utf-8").splitlines(True), False, False
for i, line in enumerate(lines):
    s = line.strip()
    if s == "[mode]":
        in_mode = True
        continue
    if s.startswith("[") and s.endswith("]"):
        in_mode = False
    if in_mode and re.match(r"\s*mode\s*=", line):
        lines[i] = re.sub(r"=\s*.*", '= "live"', line.rstrip("\n")) + ("\n" if line.endswith("\n") else "")
        changed = True
        break
if not changed:
    lines += ["\n", "[mode]\n", 'mode = "live"\n']
replace(cfg_path, "".join(lines))

for path, data in plists:
    data["ProgramArguments"] = [arg for arg in data["ProgramArguments"] if arg != "--dry-run"]
    replace(path, data, plist=True)

(state_dir / "plists.txt").write_text("".join(f"{p}\n" for p, _ in plists), encoding="utf-8")
(state_dir / "bases.txt").write_text("".join(f"{p.name}\n" for p, _ in plists), encoding="utf-8")
print(f"prepared live cutover for tenant={tenant}: {cfg_path}")
for path, _ in plists:
    print(f"prepared plist: {path}")
PY

while IFS= read -r plist; do
  [ -n "$plist" ] || continue
  "$SCP" "$plist" "$AIR:Library/LaunchAgents/$(basename "$plist")"
done < "$STATE_DIR/plists.txt"

BASES="$(tr '\n' ' ' < "$STATE_DIR/bases.txt")"
CHECK="set -e; for base in $BASES; do f=\"\$HOME/Library/LaunchAgents/\$base\"; if [ -f \"\$f\" ] && grep -q -- '--dry-run' \"\$f\"; then echo \"ERROR: \$f still contains --dry-run\" >&2; exit 43; fi; done"
RELOAD="set -e; for base in $BASES; do f=\"\$HOME/Library/LaunchAgents/\$base\"; launchctl bootout \"gui/\$(id -u)\" \"\$f\" 2>/dev/null || true; launchctl bootstrap \"gui/\$(id -u)\" \"\$f\"; done"

"$SSH" "$AIR" "$CHECK"
"$SSH" "$AIR" "$RELOAD"
"$SSH" "$AIR" "$CHECK"
OUT="$("$SSH" "$AIR" "cd ~/nous-agaas/wiki && python3 -m agents.camera_doctor.main --tenant $TENANT")"
printf '%s\n' "$OUT"
printf '%s\n' "$OUT" | grep -q 'alert_sent=True' || {
  echo "ERROR: immediate Camera Doctor live probe did not report alert_sent=True" >&2
  exit 6
}

SUCCESS=1
trap - EXIT
rm -rf "$STATE_DIR"
echo "camera_doctor_live_cutover: tenant=$TENANT live cutover verified"
