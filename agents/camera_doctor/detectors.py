"""agents.camera_doctor.detectors — 3 named-failure detectors.

Phase 2 Tasks 2.2 + 2.3 of PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1.

Each detector:
  - takes probe-result dicts (shape from probe.py) + thresholds dict
  - returns a Finding dataclass when its rule fires, else None
  - emits RU-prose evidence labels per AUDIT-060 design review:
    operator-friendly (not engineer key=value), routes actions to humans
    not raw shell commands

Detectors:
  detect_mirrors_stopped(events_probe, fleet_probe, thresholds)
  detect_vpn_network_down(wg_probe, fleet_probe, thresholds)
  detect_fleet_degraded(fleet_probe, thresholds, historical_p10_pct)
  detect_camera_pointing_wrong_direction(orientation_probe, thresholds)
  detect_cameras_offline_over_7d(fleet_probe, thresholds)
  detect_mirror_data_stale(events_probe, fleet_probe, thresholds)

Severity ladder: green < yellow < red.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Finding:
    name: str
    severity: str  # "red" | "yellow" | "green"
    evidence: dict[str, Any] = field(default_factory=dict)
    action: str = ""


def _ru_days(hours: float) -> str:
    """Return RU '<N> дн.' or '<N> ч.' phrasing depending on size."""
    if hours >= 24:
        days = int(hours // 24)
        return f"{days} дн."
    return f"{int(hours)} ч."


# ---- Detector 1: Mirrors Stopped ----

def detect_mirrors_stopped(events_probe: dict, fleet_probe: dict,
                           thresholds: dict) -> Finding | None:
    """Fire when vehicle_events freshness exceeds events_max_age_h."""
    age_hours = events_probe.get("age_hours", 0.0)
    threshold_h = thresholds.get("events_max_age_h", 48)
    if age_hours <= threshold_h:
        return None

    last_event = events_probe.get("max_event_time")
    last_event_str = last_event.strftime("%Y-%m-%d") if last_event else "—"
    fleet_total = fleet_probe.get("total", 0)

    name = f"События не приходят {_ru_days(age_hours)}"
    norm_days = max(int(threshold_h // 24), 1)
    evidence = {
        "Последнее событие": last_event_str,
        "норма": f"≤ {norm_days} дн.",
        "Затронуто камер": f"{fleet_total} из {fleet_total}",
        "всего записей в vehicle_events": events_probe.get("total_rows", 0),
    }
    action = (
        "Написать @madi_dev в Telegram: «erap-mirror висит, нужен рестарт». "
        "Или создать задачу в Notion tasks-db с тегом infra, приоритет P1. "
        "Технические шаги (для дежурного инженера): "
        "`systemctl restart erap-mirror` на VPS, проверить upstream NVR feed."
    )
    return Finding(name=name, severity="red", evidence=evidence, action=action)


# ---- Detector 2: VPN/Network Down ----

def detect_vpn_network_down(wg_probe: dict, fleet_probe: dict,
                            thresholds: dict) -> Finding | None:
    """Fire when wg handshake stale OR online count is zero."""
    handshake_age = wg_probe.get("age_seconds", 10**9)
    threshold_s = thresholds.get("wg_handshake_max_age_s", 600)
    online = fleet_probe.get("online", 0)
    total = fleet_probe.get("total", 0)

    handshake_stale = handshake_age > threshold_s
    no_online = total > 0 and online == 0

    if not handshake_stale and not no_online:
        return None

    if handshake_stale and no_online:
        name = "VPN и сеть недоступны"
    elif handshake_stale:
        name = "WireGuard рукопожатие протухло"
    else:
        name = "Все камеры офлайн"

    evidence = {
        "wg_handshake_age_s": handshake_age,
        "норма handshake": f"≤ {threshold_s} с",
        "Онлайн камер": f"{online} из {total}",
    }
    action = (
        "Написать @madi_dev в Telegram: «wg-satory или сеть Сатори лежит, "
        "нужна проверка». Или создать задачу в Notion с тегом network, "
        "приоритет P0. Технические шаги: `wg-quick up wg-satory`, "
        "проверить пинг до 10.x.x.x VPS."
    )
    return Finding(name=name, severity="red", evidence=evidence, action=action)


# ---- Detector 3: Fleet Degraded ----

def detect_fleet_degraded(fleet_probe: dict, thresholds: dict,
                          historical_p10_pct: float = 0.0) -> Finding | None:
    """Fire when online_pct drops below threshold and below 14-day p10 floor."""
    total = fleet_probe.get("total", 0)
    if total <= 0:
        return None  # don't fire on empty fleet (probe data missing)
    online = fleet_probe.get("online", 0)
    online_pct = fleet_probe.get("online_pct", online / total if total else 0.0)
    threshold_pct = thresholds.get("online_pct_min", 0.85)

    if online_pct >= threshold_pct:
        return None

    # Severity: red if also below historical p10 (genuine regression),
    # yellow if just below threshold but still above historical floor
    severity = "red" if online_pct < historical_p10_pct else "yellow"

    offline = total - online
    name = f"Парк деградировал: {offline} камер офлайн ({online_pct * 100:.1f}%)"
    evidence = {
        "Онлайн": f"{online} из {total} ({online_pct * 100:.1f}%)",
        "норма": f"≥ {threshold_pct * 100:.0f}%",
        "Исторический 14-дневный p10": f"{historical_p10_pct * 100:.1f}%",
        "Свежие проверки за час": fleet_probe.get("fresh_check_count", 0),
    }
    action = (
        "Написать дежурному инженеру в Telegram список offline-камер "
        "(приложить отчёт). Если деградация коррелирует с временем суток или "
        "погодой — это не инцидент. Если резкий обвал — создать задачу "
        "в Notion с тегом fleet, приоритет P1."
    )
    return Finding(name=name, severity=severity, evidence=evidence, action=action)


# ---- Detector 4: Camera Pointing Wrong Direction ----

def detect_camera_pointing_wrong_direction(orientation_probe: dict,
                                           thresholds: dict) -> Finding | None:
    """Fire when a field/vision sample shows too many cameras aimed at sky/ground.

    This detector is intentionally probe-shape based. It does not invent V3
    vision telemetry; it fires only when a caller supplies inspection counts.
    """
    inspected = int(orientation_probe.get("inspected", orientation_probe.get("total", 0)) or 0)
    wrong = int(orientation_probe.get("wrong_direction_count", 0) or 0)
    if inspected <= 0 or wrong <= 0:
        return None

    wrong_pct = float(orientation_probe.get("wrong_direction_pct", wrong / inspected))
    threshold_pct = float(thresholds.get("wrong_direction_pct_min", 0.20))
    if wrong_pct < threshold_pct:
        return None

    severity = "red" if wrong_pct >= 0.40 else "yellow"
    examples = orientation_probe.get("examples", [])
    examples_text = ", ".join(str(x) for x in examples[:5]) if examples else "—"
    name = f"Камеры смотрят не туда: {wrong}/{inspected} ({wrong_pct * 100:.1f}%)"
    evidence = {
        "Неверное направление": f"{wrong} из {inspected} ({wrong_pct * 100:.1f}%)",
        "Порог": f"≥ {threshold_pct * 100:.0f}%",
        "Примеры": examples_text,
        "Типы ошибок": orientation_probe.get("wrong_direction_types", "sky/ground"),
    }
    action = (
        "Передать список камер полевой бригаде: проверить кронштейн, угол наклона "
        "и кадр до выезда. Это ручной/vision-сигнал, не замена V3-аудиту."
    )
    return Finding(name=name, severity=severity, evidence=evidence, action=action)


# ---- Detector 5: Camera Offline >7 Days ----

def detect_cameras_offline_over_7d(fleet_probe: dict, thresholds: dict) -> Finding | None:
    """Fire when individual cameras have been offline longer than threshold days."""
    stale_count = int(fleet_probe.get("offline_over_7d_count", 0) or 0)
    if stale_count <= 0:
        return None

    threshold_days = int(thresholds.get("camera_offline_max_age_days", 7))
    total = int(fleet_probe.get("total", 0) or 0)
    sample = fleet_probe.get("offline_over_7d_sample", [])
    sample_text = ", ".join(str(x) for x in sample[:5]) if sample else "—"
    severity = "red" if stale_count >= max(int(total * 0.10), 10) else "yellow"
    name = f"Камеры офлайн больше {threshold_days} дн.: {stale_count}"
    evidence = {
        "Камер просрочено": f"{stale_count} из {total}",
        "Порог": f"> {threshold_days} дн.",
        "Примеры IP": sample_text,
    }
    action = (
        "Сформировать ремонтный список для подрядчика: питание, канал связи, "
        "камера/NVR, затем закрывать по фактическому восстановлению."
    )
    return Finding(name=name, severity=severity, evidence=evidence, action=action)


# ---- Detector 6: Mirror Data Stale >24h ----

def detect_mirror_data_stale(events_probe: dict, fleet_probe: dict,
                             thresholds: dict) -> Finding | None:
    """Fire when ERAP mirror data has no fresh events for >24h."""
    age_hours = float(events_probe.get("age_hours", 0.0) or 0.0)
    stale_h = float(thresholds.get("mirror_stale_max_age_h", 24))
    if age_hours <= stale_h:
        return None

    critical_h = float(thresholds.get("mirror_critical_age_h",
                                      thresholds.get("events_max_age_h", 48)))
    severity = "red" if age_hours > critical_h else "yellow"
    last_event = events_probe.get("max_event_time")
    last_event_str = last_event.strftime("%Y-%m-%d") if last_event else "—"
    total = int(fleet_probe.get("total", 0) or 0)
    name = f"Зеркало данных устарело: {_ru_days(age_hours)}"
    evidence = {
        "Последнее событие": last_event_str,
        "Возраст данных": _ru_days(age_hours),
        "Порог": f"> {int(stale_h)} ч.",
        "Затронуто камер": f"{total} из {total}",
    }
    action = (
        "Проверить ERAP mirror ingest: источник событий, sqlite writer, место на диске "
        "и расписание синхронизации. При возрасте >48 ч. эскалировать как P1."
    )
    return Finding(name=name, severity=severity, evidence=evidence, action=action)
