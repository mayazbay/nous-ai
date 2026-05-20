"""Health Monitor — Chief of Staff agent that prevents death loops and token waste.

Runs INSIDE each cycle at key checkpoints. Also has a standalone mode for the watchdog.
Monitors:
1. API health (pre-flight check before each cycle)
2. Error rate (same error 3+ times = circuit breaker)
3. Cycle duration (stuck cycle detection)
4. Token/cost tracking
"""
import time
import json
import os
from datetime import datetime

HEALTH_DB = '/root/nous-agaas/data/health.json'
ERROR_LOG = '/root/nous-agaas/data/error_log.json'

def _load_health():
    try:
        with open(HEALTH_DB, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'errors': [], 'api_status': {}, 'cycle_starts': [], 'alerts_sent': []}

def _save_health(data):
    os.makedirs(os.path.dirname(HEALTH_DB), exist_ok=True)
    with open(HEALTH_DB, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def preflight_check() -> dict:
    """Run BEFORE each cycle. Test all model APIs with minimal tokens.
    Returns {ok: bool, failed_models: [...], message: str}
    """
    from config import MODELS, get_llm
    failed = []
    results = {}
    
    for role, cfg in MODELS.items():
        try:
            llm = get_llm(role)
            # Minimal ping — 1 token response
            resp = llm.invoke('Reply with OK')
            results[role] = 'ok'
        except Exception as e:
            err_str = str(e)
            failed.append({'role': role, 'model': cfg['model'], 'error': err_str[:200]})
            results[role] = f'FAIL: {err_str[:100]}'
            print(f'[HEALTH] {role} ({cfg[model]}): FAIL — {err_str[:100]}', flush=True)
    
    health = _load_health()
    health['api_status'] = results
    health['last_preflight'] = datetime.utcnow().isoformat()
    _save_health(health)
    
    if failed:
        # Send Telegram alert for failed models
        try:
            from tools.telegram_bot import send_message
            models_down = ', '.join(f'{f[role]}({f[model]})' for f in failed)
            send_message(f'⚠️ HEALTH: Models DOWN before cycle: {models_down}. Factory will skip these roles.')
        except Exception:
            pass
    
    return {
        'ok': len(failed) == 0,
        'failed_models': failed,
        'results': results,
        'message': 'All models healthy' if not failed else f'{len(failed)} model(s) down'
    }

def record_error(node: str, error: str):
    """Record an error. If same node errors 3+ times in a row, trigger circuit breaker."""
    health = _load_health()
    entry = {
        'node': node,
        'error': error[:300],
        'timestamp': datetime.utcnow().isoformat()
    }
    health['errors'].append(entry)
    # Keep last 100 errors only
    health['errors'] = health['errors'][-100:]
    _save_health(health)
    
    # Check for death loop: same node erroring 3+ times in last 10 minutes
    recent = [e for e in health['errors'] 
              if e['node'] == node 
              and (datetime.utcnow() - datetime.fromisoformat(e['timestamp'])).total_seconds() < 600]
    
    if len(recent) >= 3:
        # CIRCUIT BREAKER
        alert_key = f'{node}_' + datetime.utcnow().strftime('%Y%m%d%H')
        if alert_key not in health.get('alerts_sent', []):
            health.setdefault('alerts_sent', []).append(alert_key)
            health['alerts_sent'] = health['alerts_sent'][-50:]
            _save_health(health)
            try:
                from tools.telegram_bot import send_message
                send_message(
                    f'🔴 DEATH LOOP DETECTED: {node} has failed {len(recent)} times in 10min.\n'
                    f'Last error: {error[:200]}\n'
                    f'Circuit breaker activated — skipping this node.'
                )
            except Exception:
                pass
        return True  # Signal: skip this node
    
    return False  # No circuit breaker needed

def record_cycle_start():
    """Track cycle start times for stuck detection."""
    health = _load_health()
    health['cycle_starts'].append(datetime.utcnow().isoformat())
    health['cycle_starts'] = health['cycle_starts'][-50:]
    health['current_cycle_start'] = datetime.utcnow().isoformat()
    _save_health(health)

def record_cycle_end(task_title: str, success: bool):
    """Track cycle completion."""
    health = _load_health()
    health['last_cycle_end'] = datetime.utcnow().isoformat()
    health['last_task'] = task_title
    health['last_success'] = success
    if 'current_cycle_start' in health:
        start = datetime.fromisoformat(health['current_cycle_start'])
        duration = (datetime.utcnow() - start).total_seconds()
        health['last_cycle_duration_sec'] = round(duration)
    _save_health(health)

def check_stuck_cycle(max_minutes=45) -> bool:
    """Called by watchdog. Returns True if current cycle is stuck."""
    health = _load_health()
    start_str = health.get('current_cycle_start')
    end_str = health.get('last_cycle_end')
    
    if not start_str:
        return False
    
    start = datetime.fromisoformat(start_str)
    elapsed = (datetime.utcnow() - start).total_seconds() / 60
    
    # If cycle started but hasn't ended and it's been > max_minutes
    if end_str:
        end = datetime.fromisoformat(end_str)
        if end > start:
            return False  # Cycle completed normally
    
    if elapsed > max_minutes:
        try:
            from tools.telegram_bot import send_message
            send_message(
                f'🔴 STUCK CYCLE: Running for {int(elapsed)} minutes (max {max_minutes}).\n'
                f'Last task: {health.get(last_task, unknown)}\n'
                f'Restarting factory service...'
            )
        except Exception:
            pass
        return True
    
    return False

def get_health_summary() -> str:
    """Human-readable health summary for CEO/Reporter."""
    health = _load_health()
    lines = ['=== Factory Health ===']
    
    # API status
    api = health.get('api_status', {})
    for role, status in api.items():
        icon = '✅' if status == 'ok' else '🔴'
        lines.append(f'{icon} {role}: {status}')
    
    # Recent errors
    errors = health.get('errors', [])
    if errors:
        recent = errors[-5:]
        lines.append(f'\nRecent errors ({len(errors)} total):')
        for e in recent:
            lines.append(f'  - {e[node]}: {e[error][:80]}')
    
    # Cycle stats
    if health.get('last_cycle_duration_sec'):
        lines.append(f'\nLast cycle: {health[last_cycle_duration_sec]}s')
    if health.get('last_task'):
        lines.append(f'Last task: {health[last_task]}')
    
    return '\n'.join(lines)
