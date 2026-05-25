#!/usr/bin/env python3
"""
satory_camera_query.py — read-side query for last recognized plate / photo.

The Mac repo has no direct access to camera storage (intake-only on VPS at
65.108.215.200:9080/events/camera/hxml). This module tries a fail-soft chain
of HTTP endpoints to surface the LAST recognized event for `/last-plate` and
`/last-photo` Telegram commands.

Doctrine: pages/skills/camera-event-query/SKILL.md v1.0.0
  AP-1: never claim a plate/photo if the read API returned no data
        — surface "не удалось получить" gracefully.
  AP-2: cache the last successful response for 30s to avoid hammering intake.
  AP-3: always include freshness timestamp so the operator can tell if stale.

Triggered by: command_center.py /last-plate, /last-photo
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger(__name__)

# Endpoint chain — tried in order; first 200 wins. The first endpoint guesses
# that the intake host may eventually expose a /last read companion to the
# /events/camera/hxml POST. The next two extend the existing api.nousagaas.com
# read surface. All three are fail-soft.
DEFAULT_ENDPOINTS = (
    "http://65.108.215.200:9080/events/camera/last",
    "https://api.nousagaas.com/api/cameras/last",
    "https://api.nousagaas.com/api/cameras/events?limit=1",
)

CACHE_TTL_SECONDS = int(os.environ.get("SATORY_CAMERA_QUERY_CACHE_TTL", "30"))
HTTP_TIMEOUT_SECONDS = int(os.environ.get("SATORY_CAMERA_QUERY_TIMEOUT", "8"))
USER_AGENT = "nous-satory-camera-query/1.0"

# Simple module-level cache (intentionally not threadsafe — Telegram poller is
# single-threaded; brief over-fetch on race is acceptable).
_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None, "source_url": ""}


def _get_endpoints() -> tuple[str, ...]:
    override = os.environ.get("SATORY_CAMERA_QUERY_ENDPOINTS", "").strip()
    if override:
        return tuple(p.strip() for p in override.split(",") if p.strip())
    return DEFAULT_ENDPOINTS


def _http_get_json(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> dict | None:
    """Best-effort GET. Returns parsed JSON dict on 200, else None."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                log.info("satory_camera_query non-200 from %s: %s", url, resp.status)
                return None
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if not isinstance(data, (dict, list)):
                return None
            # If list, wrap first item under "events" key for uniform shape.
            if isinstance(data, list):
                return {"events": data}
            return data
    except urllib.error.HTTPError as exc:
        log.info("satory_camera_query HTTPError %s: %s", url, exc)
        return None
    except urllib.error.URLError as exc:
        log.info("satory_camera_query URLError %s: %s", url, exc)
        return None
    except (TimeoutError, OSError) as exc:
        log.info("satory_camera_query timeout/OS %s: %s", url, exc)
        return None
    except (ValueError, json.JSONDecodeError) as exc:
        log.info("satory_camera_query JSON parse %s: %s", url, exc)
        return None
    except Exception as exc:  # noqa: BLE001 - never raise to caller
        log.warning("satory_camera_query unexpected %s: %s", url, exc)
        return None


def fetch_last_event(*, force_refresh: bool = False) -> dict | None:
    """Return the last camera event payload, or None on full failure.

    AP-2: cached for CACHE_TTL_SECONDS. Pass force_refresh=True to bypass.
    AP-1: returns None (not a stub) when no endpoint responds.
    """
    now = time.time()
    if not force_refresh:
        if _CACHE["payload"] is not None and (now - float(_CACHE["ts"])) < CACHE_TTL_SECONDS:
            return _CACHE["payload"]

    for url in _get_endpoints():
        payload = _http_get_json(url)
        if payload is None:
            continue
        normalized = _normalize_event_payload(payload)
        if normalized is None:
            continue
        _CACHE["ts"] = now
        _CACHE["payload"] = normalized
        _CACHE["source_url"] = url
        return normalized

    return None


def _normalize_event_payload(payload: dict) -> dict | None:
    """Extract a single event dict from a variety of API shapes.

    Accepted shapes:
      {"plate": "...", "ts": "...", ...}                         # /last
      {"event": {...}}                                            # nested
      {"events": [{...}, ...]}                                    # list
      {"data": [{...}, ...]} or {"data": {"events": [...]}}       # wrapper
      {"items": [{...}, ...]}                                     # paginated
    """
    if not isinstance(payload, dict):
        return None

    # Single-event shape — has a plate-ish field
    direct_keys = ("plate", "license_plate", "number", "номер", "plate_text")
    if any(k in payload for k in direct_keys):
        return payload

    # Nested "event" key
    nested = payload.get("event")
    if isinstance(nested, dict):
        return nested

    # Multiple events — take the first (callers ask for "last", APIs typically
    # return newest-first; if API is ascending, the endpoint itself is wrong)
    for list_key in ("events", "items", "results"):
        items = payload.get(list_key)
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                return first

    # "data" wrapper
    data = payload.get("data")
    if isinstance(data, dict):
        if any(k in data for k in direct_keys):
            return data
        for list_key in ("events", "items", "results"):
            items = data.get(list_key)
            if isinstance(items, list) and items:
                first = items[0]
                if isinstance(first, dict):
                    return first
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return first

    return None


def extract_fields(event: dict) -> dict:
    """Pull common fields from a heterogeneous event dict. Missing → None."""
    if not isinstance(event, dict):
        return {}

    def _pick(*keys):
        for k in keys:
            if k in event and event[k] not in (None, ""):
                return event[k]
        return None

    plate = _pick("plate", "license_plate", "number", "plate_text", "номер")
    speed = _pick("speed", "speed_kmh", "v", "скорость")
    limit = _pick("limit", "speed_limit", "max_speed", "лимит")
    violation = _pick("violation", "is_violation", "нарушение")
    camera_id = _pick("camera_id", "camera", "cam_id", "device_id", "камера")
    ts = _pick("ts", "timestamp", "captured_at", "time", "event_ts")
    photo_url = _pick("photo_url", "photo", "image_url", "image", "snapshot_url", "url")

    excess = None
    try:
        if speed is not None and limit is not None:
            excess = int(round(float(speed) - float(limit)))
    except (TypeError, ValueError):
        excess = None

    return {
        "plate": plate,
        "speed": speed,
        "limit": limit,
        "excess": excess,
        "violation": violation,
        "camera_id": camera_id,
        "ts": ts,
        "photo_url": photo_url,
    }


def _format_violation_ru(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    s = str(value).strip().lower()
    if s in ("true", "yes", "1", "да"):
        return "Да"
    if s in ("false", "no", "0", "нет"):
        return "Нет"
    return str(value)


def format_last_plate_ru(event: dict | None, *, source_url: str = "") -> str:
    """Russian-language Telegram reply for /last-plate.

    AP-1: graceful failure if event is None.
    AP-3: includes freshness timestamp.
    """
    if not event:
        return (
            "📷 Не удалось получить последнее событие. "
            "Intake-эндпоинт жив, но read-API ещё не подключён или вернул пусто.\n\n"
            "Команда для диагностики: <code>/last-plate-debug</code>"
        )

    f = extract_fields(event)
    if not f.get("plate"):
        return (
            "📷 Read-API ответил, но не вернул распознанный номер. "
            "Возможно, последнее событие — это снимок без OCR-результата.\n\n"
            f"Источник: <code>{source_url or 'unknown'}</code>"
        )

    speed_line = "—"
    if f.get("speed") is not None:
        if f.get("limit") is not None and f.get("excess") is not None:
            sign = "+" if f["excess"] >= 0 else ""
            speed_line = f"{f['speed']} км/ч (лимит {f['limit']}) — превышение {sign}{f['excess']}"
        else:
            speed_line = f"{f['speed']} км/ч"

    camera_line = str(f.get("camera_id") or "—")
    violation_line = _format_violation_ru(f.get("violation"))
    ts_line = str(f.get("ts") or "—")
    photo = f.get("photo_url")
    photo_line = str(photo) if photo else "—"

    return (
        "📷 Последний распознанный номер:\n"
        f"• Номер: <code>{f['plate']}</code>\n"
        f"• Скорость: {speed_line}\n"
        f"• Камера: <code>{camera_line}</code> / нарушение: {violation_line}\n"
        f"• Время: <code>{ts_line}</code>\n"
        f"• Фото: {photo_line}"
    )


def format_last_photo_ru(event: dict | None, *, source_url: str = "") -> str:
    """Russian-language Telegram reply for /last-photo."""
    if not event:
        return (
            "📷 Не удалось получить последнее фото. "
            "Read-API ещё не подключён или вернул пусто.\n\n"
            "Команда для диагностики: <code>/last-photo-debug</code>"
        )

    f = extract_fields(event)
    photo = f.get("photo_url")
    if not photo:
        return (
            "📷 Read-API ответил, но фото в ответе нет.\n\n"
            f"Последний номер: <code>{f.get('plate') or '—'}</code>\n"
            f"Время: <code>{f.get('ts') or '—'}</code>\n"
            f"Источник: <code>{source_url or 'unknown'}</code>"
        )

    plate = f.get("plate") or "—"
    ts_line = str(f.get("ts") or "—")
    return (
        "📷 Последнее фото:\n"
        f"• Номер: <code>{plate}</code>\n"
        f"• Время: <code>{ts_line}</code>\n"
        f"• Фото: {photo}"
    )


def get_last_plate_reply() -> str:
    """Top-level for /last-plate Telegram command."""
    event = fetch_last_event()
    return format_last_plate_ru(event, source_url=_CACHE.get("source_url", ""))


def get_last_photo_reply() -> str:
    """Top-level for /last-photo Telegram command."""
    event = fetch_last_event()
    return format_last_photo_ru(event, source_url=_CACHE.get("source_url", ""))


def _reset_cache_for_tests() -> None:
    _CACHE["ts"] = 0.0
    _CACHE["payload"] = None
    _CACHE["source_url"] = ""


if __name__ == "__main__":
    # Manual smoke-test: python3 tools/satory_camera_query.py
    logging.basicConfig(level=logging.INFO)
    ev = fetch_last_event()
    print("event:", ev)
    print("---")
    print(format_last_plate_ru(ev, source_url=_CACHE.get("source_url", "")))
