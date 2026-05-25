#!/usr/bin/env bash
set -euo pipefail

# Hermes WebUI canary runner.
# Keeps the phone-facing WebUI private, password-protected, and separate from
# the production OpenClaw/Telegram route.

COMMAND="${1:-status}"
HOME_DIR="${HOME:-/Users/madia}"
ENV_FILE="${HERMES_WEBUI_ENV_FILE:-$HOME_DIR/nous-agaas/secrets/hermes-webui.env}"
APP_DIR="${HERMES_WEBUI_APP_DIR:-$HOME_DIR/.local/share/nous/hermes-webui}"
DEFAULT_PYTHON="$HOME_DIR/.hermes/hermes-agent/venv/bin/python"
PYTHON_BIN="${HERMES_WEBUI_PYTHON:-$DEFAULT_PYTHON}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
  fi

  export HERMES_BASE_HOME="${HERMES_BASE_HOME:-$HOME_DIR/.hermes}"
  export HERMES_WEBUI_AGENT_DIR="${HERMES_WEBUI_AGENT_DIR:-$HOME_DIR/.hermes/hermes-agent}"
  export HERMES_WEBUI_HOST="${HERMES_WEBUI_HOST:-0.0.0.0}"
  export HERMES_WEBUI_PORT="${HERMES_WEBUI_PORT:-8787}"
  export HERMES_WEBUI_STATE_DIR="${HERMES_WEBUI_STATE_DIR:-$HOME_DIR/.hermes/webui}"
  export HERMES_WEBUI_DEFAULT_WORKSPACE="${HERMES_WEBUI_DEFAULT_WORKSPACE:-$HOME_DIR/nous-agaas/wiki}"
  export HERMES_WEBUI_BOT_NAME="${HERMES_WEBUI_BOT_NAME:-Hermes Canary}"
  export HERMES_WEBUI_PROFILE="${HERMES_WEBUI_PROFILE:-nouscanary}"
  export HERMES_WEBUI_FACTORY_SKILLS_DIR="${HERMES_WEBUI_FACTORY_SKILLS_DIR:-$HOME_DIR/nous-agaas/skills}"
  export HERMES_MODEL="${HERMES_MODEL:-gpt-5.5}"
  if [[ "${HERMES_WEBUI_PROFILE:-default}" == "default" ]]; then
    export HERMES_HOME="${HERMES_HOME:-$HERMES_BASE_HOME}"
  else
    export HERMES_HOME="${HERMES_BASE_HOME}/profiles/${HERMES_WEBUI_PROFILE}"
  fi
}

require_app() {
  if [[ ! -d "$APP_DIR" ]]; then
    echo "missing Hermes WebUI app dir: $APP_DIR" >&2
    exit 2
  fi
}

require_password() {
  if [[ -z "${HERMES_WEBUI_PASSWORD:-}" ]]; then
    echo "HERMES_WEBUI_PASSWORD is required before binding beyond localhost" >&2
    exit 3
  fi
}

active_profile_name() {
  if [[ -f "$HERMES_BASE_HOME/active_profile" ]]; then
    local profile
    profile="$(tr -d '[:space:]' < "$HERMES_BASE_HOME/active_profile")"
    if [[ -n "$profile" ]]; then
      printf '%s\n' "$profile"
      return 0
    fi
  fi
  printf 'default\n'
}

profile_config_path() {
  if [[ "${HERMES_WEBUI_PROFILE:-default}" == "default" ]]; then
    printf '%s/config.yaml\n' "$HERMES_BASE_HOME"
  else
    printf '%s/profiles/%s/config.yaml\n' "$HERMES_BASE_HOME" "$HERMES_WEBUI_PROFILE"
  fi
}

ensure_active_profile() {
  mkdir -p "$HERMES_BASE_HOME"
  if [[ "${HERMES_WEBUI_PROFILE:-default}" == "default" ]]; then
    : > "$HERMES_BASE_HOME/active_profile"
  else
    printf '%s\n' "$HERMES_WEBUI_PROFILE" > "$HERMES_BASE_HOME/active_profile"
  fi
}

ensure_factory_external_skills() {
  local config_path
  config_path="$(profile_config_path)"
  if [[ ! -f "$config_path" || ! -d "$HERMES_WEBUI_FACTORY_SKILLS_DIR" ]]; then
    return 0
  fi

  "$PYTHON_BIN" - "$config_path" "$HERMES_WEBUI_FACTORY_SKILLS_DIR" <<'PY'
from pathlib import Path
import sys

config = Path(sys.argv[1])
skills_dir = sys.argv[2]
text = config.read_text(encoding="utf-8")
if skills_dir in text:
    raise SystemExit(0)

lines = text.splitlines()
skills_idx = next((i for i, line in enumerate(lines) if line.strip() == "skills:"), None)
if skills_idx is None:
    lines.extend(["skills:", "  external_dirs:", f"    - {skills_dir}"])
else:
    section_end = len(lines)
    for i in range(skills_idx + 1, len(lines)):
        if lines[i] and not lines[i].startswith((" ", "\t")):
            section_end = i
            break

    ext_idx = next(
        (i for i in range(skills_idx + 1, section_end) if lines[i].lstrip().startswith("external_dirs:")),
        None,
    )
    if ext_idx is None:
        lines[section_end:section_end] = ["  external_dirs:", f"    - {skills_dir}"]
    elif lines[ext_idx].strip() == "external_dirs: []":
        lines[ext_idx:ext_idx + 1] = ["  external_dirs:", f"    - {skills_dir}"]
    else:
        insert_at = ext_idx + 1
        while insert_at < section_end and lines[insert_at].startswith("    - "):
            insert_at += 1
        lines.insert(insert_at, f"    - {skills_dir}")

new_text = "\n".join(lines) + "\n"
if new_text != text:
    config.write_text(new_text, encoding="utf-8")
PY
}

ensure_agent_skill_sort_shim() {
  local skills_tool="$HERMES_WEBUI_AGENT_DIR/tools/skills_tool.py"
  if [[ ! -f "$skills_tool" ]]; then
    return 0
  fi

  "$PYTHON_BIN" - "$skills_tool" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "def _sort_skills(" in text:
    raise SystemExit(0)

shim = '''

# Hermes WebUI compatibility shim.
# WebUI v0.51.92 imports _sort_skills, while some agent builds only expose
# skills_list sorting internally. Keep /api/skills usable until the agent and
# WebUI release trains converge.
def _sort_skills(skills):
    return sorted(
        skills,
        key=lambda item: (
            str(item.get("category") or ""),
            str(item.get("name") or "").lower(),
        ),
    )
'''

path.write_text(text.rstrip() + shim + "\n", encoding="utf-8")
PY
}

ensure_external_session_profile_shim() {
  local models_py="$APP_DIR/api/models.py"
  if [[ ! -f "$models_py" ]]; then
    return 0
  fi

  "$PYTHON_BIN" - "$models_py" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = "            'profile': None,\n            'source_tag': CLAUDE_CODE_SOURCE,"
new = "            'profile': os.getenv('HERMES_WEBUI_PROFILE') or None,\n            'source_tag': CLAUDE_CODE_SOURCE,"
if new in text:
    raise SystemExit(0)
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
}

ensure_mcp_inventory_cache_shim() {
  local routes_py="$APP_DIR/api/routes.py"
  if [[ ! -f "$routes_py" ]]; then
    return 0
  fi

  "$PYTHON_BIN" - "$routes_py" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "# Hermes WebUI canary MCP inventory cache fallback."
if marker in text:
    raise SystemExit(0)

old = '''    return {
        str(entry.get("name")): entry
        for entry in statuses
        if isinstance(entry, dict) and entry.get("name")
    }
'''
new = '''    runtime = {
        str(entry.get("name")): entry
        for entry in statuses
        if isinstance(entry, dict) and entry.get("name")
    }
    if any(entry.get("connected") for entry in runtime.values() if isinstance(entry, dict)):
        return runtime

    # Hermes WebUI canary MCP inventory cache fallback.
    # The stock endpoint is intentionally read-only and only reports MCP tools
    # already registered in the current chat runtime. For the Nous canary page,
    # keep the panel useful by reading a cache populated by a startup probe.
    try:
        cache_path = STATE_DIR / "mcp_inventory.json"
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        servers = cached.get("servers") if isinstance(cached, dict) else {}
        if isinstance(servers, dict) and servers:
            return {
                str(name): value
                for name, value in servers.items()
                if isinstance(value, dict)
            }
    except Exception:
        pass
    return runtime
'''
if old not in text:
    raise SystemExit("MCP runtime return block not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
}

ensure_factory_events_api_shim() {
  local routes_py="$APP_DIR/api/routes.py"
  if [[ ! -f "$routes_py" ]]; then
    return 0
  fi

  "$PYTHON_BIN" - "$routes_py" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "# Hermes WebUI canary factory-events API shim."

helper = r'''

# Hermes WebUI canary factory-events API shim.
# This is read-only. It lets the canary surface observe the live Nous factory
# ledgers without becoming the production Telegram/OpenClaw router.
def _handle_nous_factory_events(handler, parsed):
    import collections as _collections
    import datetime as _dt
    import json as _json
    import os as _os
    from pathlib import Path as _Path

    qs = parse_qs(parsed.query)
    try:
        limit = int(qs.get("limit", ["40"])[0])
    except (TypeError, ValueError):
        limit = 40
    limit = max(1, min(limit, 200))

    root = _Path(_os.getenv("NOUS_FACTORY_ROOT", "/Users/madia/nous-agaas"))
    sources = [
        ("ops_events", root / "state" / "ops_events.jsonl"),
        ("factory_self_heal", root / "logs" / "factory-self-heal.jsonl"),
        ("hermes_factory_watchdog", root / "logs" / "hermes-factory-watchdog.jsonl"),
    ]

    def _tail_jsonl(source_name, path, max_lines):
        out = []
        meta = {
            "name": source_name,
            "path": str(path),
            "exists": path.exists(),
            "count": 0,
            "error": None,
        }
        if not path.exists():
            return meta, out
        try:
            lines = _collections.deque(maxlen=max_lines)
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        lines.append(line)
            for line in lines:
                try:
                    item = _json.loads(line)
                except Exception as exc:
                    out.append(
                        {
                            "kind": "malformed_jsonl",
                            "source": source_name,
                            "source_path": str(path),
                            "error": str(exc),
                            "line_preview": line[:300],
                        }
                    )
                    continue
                if not isinstance(item, dict):
                    continue
                event = {
                    "kind": source_name,
                    "source_path": str(path),
                    "ts": item.get("ts") or item.get("started_at") or item.get("finished_at"),
                    "status": item.get("overall") or item.get("status"),
                    "source": item.get("source"),
                    "actor": item.get("actor"),
                    "correlation_id": item.get("correlation_id"),
                    "fingerprint": item.get("fingerprint"),
                    "external_id": item.get("external_id"),
                    "idempotency_key": item.get("idempotency_key"),
                }
                if source_name == "factory_self_heal":
                    event["repairs"] = item.get("repairs", [])
                    event["notification"] = item.get("notification")
                out.append(event)
            meta["count"] = len(out)
        except Exception as exc:
            meta["error"] = str(exc)
        return meta, out

    source_meta = []
    events = []
    for source_name, source_path in sources:
        meta, source_events = _tail_jsonl(source_name, source_path, limit)
        source_meta.append(meta)
        events.extend(source_events)

    def _event_sort_key(event):
        ts = event.get("ts") or ""
        return str(ts)

    events = sorted(events, key=_event_sort_key, reverse=True)[:limit]

    queue_status_path = root / "wiki" / "pages" / "systems" / "satory-ai-factory-queue-status.md"
    queue_status = {
        "path": str(queue_status_path),
        "exists": queue_status_path.exists(),
        "fields": {},
    }
    if queue_status_path.exists():
        try:
            for raw in queue_status_path.read_text(encoding="utf-8", errors="replace").splitlines()[:80]:
                line = raw.strip()
                if line.startswith("- ") and ":" in line:
                    key, value = line[2:].split(":", 1)
                    queue_status["fields"][key.strip()] = value.strip()
        except Exception as exc:
            queue_status["error"] = str(exc)

    payload = {
        "ok": True,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "profile": _os.getenv("HERMES_WEBUI_PROFILE", ""),
        "workspace": _os.getenv("HERMES_WEBUI_DEFAULT_WORKSPACE", ""),
        "limit": limit,
        "sources": source_meta,
        "queue_status": queue_status,
        "events": events,
    }
    return j(handler, payload)
'''

if marker not in text:
    anchor = "\ndef handle_get(handler, parsed) -> bool:\n"
    if anchor not in text:
        raise SystemExit("handle_get anchor not found for factory-events shim")
    text = text.replace(anchor, helper + anchor, 1)

route = '''    if parsed.path == "/api/factory-events":
        return _handle_nous_factory_events(handler, parsed)

'''
if route not in text:
    anchor = '    if parsed.path in ("/manifest.json", "/manifest.webmanifest"):\n'
    if anchor not in text:
        raise SystemExit("manifest anchor not found for factory-events route")
    text = text.replace(anchor, route + anchor, 1)

path.write_text(text, encoding="utf-8")
PY
}

ensure_webui_state_seed() {
  "$PYTHON_BIN" "$SCRIPT_DIR/hermes_webui_factory_seed.py"
}

ensure_webui_runtime() {
  ensure_active_profile
  ensure_factory_external_skills
  ensure_agent_skill_sort_shim
  ensure_external_session_profile_shim
  ensure_mcp_inventory_cache_shim
  ensure_factory_events_api_shim
  ensure_webui_state_seed
}

status_report() {
  local launchd_line=""
  local health_url="http://127.0.0.1:${HERMES_WEBUI_PORT:-8787}/health"
  local health_status="RED"
  local phone_status=""
  local lan_status=""

  launchd_line="$(launchctl list 2>/dev/null | awk '/com[.]nous[.]hermes-webui-canary/ {print; exit}' || true)"
  if curl -fsS --max-time 5 "$health_url" >/dev/null 2>&1; then
    health_status="GREEN"
  fi

  phone_status="$(phone_url 2>&1)" || phone_status="RED: $phone_status"
  lan_status="$(lan_url 2>&1)" || lan_status="RED: $lan_status"

  echo "Hermes WebUI canary"
  if [[ -n "$launchd_line" ]]; then
    echo "launchd: $launchd_line"
  else
    echo "launchd: RED: com.nous.hermes-webui-canary not loaded"
  fi
  echo "health: $health_status $health_url"
  echo "active-profile: $(active_profile_name)"
  echo "profile-home: $HERMES_HOME"
  echo "workspace: $HERMES_WEBUI_DEFAULT_WORKSPACE"
  echo "phone-url: $phone_status"
  echo "lan-url: $lan_status"
  echo "note: launchd runs run-foreground, so ctl.sh PID-file status is advisory only"

  [[ "$health_status" == "GREEN" && -n "$launchd_line" ]]
}

phone_url() {
  if ! command -v tailscale >/dev/null 2>&1; then
    echo "tailscale-cli-unavailable" >&2
    exit 4
  fi

  local ip=""
  ip="$(tailscale ip -4 2>/dev/null | head -1 || true)"
  if [[ -z "$ip" ]]; then
    echo "tailscale-ip-unavailable; run: tailscale up" >&2
    exit 4
  fi
  printf 'http://%s:%s\n' "$ip" "${HERMES_WEBUI_PORT:-8787}"
}

lan_url() {
  if [[ -n "${HERMES_WEBUI_LAN_URL:-}" ]]; then
    printf '%s\n' "$HERMES_WEBUI_LAN_URL"
    return 0
  fi

  local ip=""
  ip="$(ifconfig 2>/dev/null | awk '/inet 192[.]168[.]/ {print $2; exit}' || true)"
  if [[ -z "$ip" ]]; then
    ip="$(ifconfig 2>/dev/null | awk '/inet 10[.]/ {print $2; exit}' || true)"
  fi
  if [[ -z "$ip" ]]; then
    echo "lan-ip-unavailable" >&2
    exit 4
  fi
  printf 'http://%s:%s\n' "$ip" "${HERMES_WEBUI_PORT:-8787}"
}

load_env

case "$COMMAND" in
  run-foreground)
    require_app
    require_password
    ensure_webui_runtime
    cd "$APP_DIR"
    exec "$PYTHON_BIN" "$APP_DIR/bootstrap.py" \
      --foreground \
      --no-browser \
      --skip-agent-install \
      --host "$HERMES_WEBUI_HOST" \
      "$HERMES_WEBUI_PORT"
    ;;
  status)
    require_app
    status_report
    ;;
  start|stop|restart|logs)
    require_app
    if [[ "$COMMAND" == "start" || "$COMMAND" == "restart" ]]; then
      require_password
    fi
    cd "$APP_DIR"
    exec ./ctl.sh "$COMMAND" "${@:2}"
    ;;
  health)
    exec curl -fsS --max-time 5 "http://127.0.0.1:${HERMES_WEBUI_PORT}/health"
    ;;
  phone-url)
    phone_url
    ;;
  lan-url)
    lan_url
    ;;
  *)
    echo "usage: $0 {run-foreground|start|stop|restart|status|logs|health|phone-url|lan-url}" >&2
    exit 2
    ;;
esac
