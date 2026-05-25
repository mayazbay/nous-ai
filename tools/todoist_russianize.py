#!/usr/bin/env python3
"""Translate Todoist's human-facing control-plane text to Russian.

The script is intentionally conservative:
- IDs, URLs, source slugs, dates, labels used as evidence, and proper product
  names are preserved.
- Existing descriptions are translated when they already exist; no fake context
  is invented for tasks with empty descriptions.
- Default mode is dry-run. Use --apply only after reviewing the emitted plan.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import requests

from todoist_control_plane_audit import (
    Todoist,
    active_item,
    active_project,
    active_section,
    filter_satory_sync,
    labels_for,
    token_from_env,
)


ALMATY = dt.timezone(dt.timedelta(hours=5))
RESOURCE_TYPES = ["projects", "sections", "labels", "items", "notes"]
AUDIT_DIR = Path("pages/audits")

PROJECT_NAME_MAP = {
    "Satory VKO Factory": "Фабрика Satory ВКО",
}

SECTION_NAME_MAP = {
    "📥 Intake / Triage": "📥 Входящие / Разбор",
    "Intake / Triage": "Входящие / Разбор",
    "🏗️ BDL Replacement": "🏗️ Замена BDL",
    "BDL Replacement": "Замена BDL",
    "🧠 Cerebro Replacement": "🧠 Замена Cerebro",
    "🎬 Cerebro Replacement": "🎬 Замена Cerebro",
    "Cerebro Replacement": "Замена Cerebro",
    "📷 Camera Doctor — Satory Pilot": "📷 Camera Doctor — пилот Satory",
    "Camera Doctor — Satory Pilot": "Camera Doctor — пилот Satory",
    "🤝Keona Partnership": "🤝 Партнерство KEONA",
    "Keona Partnership": "Партнерство KEONA",
    "Started": "Начато",
    "In progress": "В работе",
    "Done": "Готово",
    "Not Done": "Не сделано",
    "Blocked": "Заблокировано",
}

LABEL_NAME_MAP = {
    "email": "письмо",
    "factory": "фабрика",
    "high_impact": "высокий_эффект",
    "Zere": "Зере",
    "Yerden": "Ерден",
    "Assyl": "Асыл",
    "Yerbolat": "Ерболат",
    "Ainur": "Айнур",
    "Akmarzhan": "Акмаржан",
    "Danil_Chen": "Данил_Чен",
    "Saken aga": "Сакен-ага",
    "Tamerlan": "Тамерлан",
    "Shona": "Шона",
    "Emeric": "Эмерик",
    "Daniyar": "Данияр",
    "Roza": "Роза",
    "Madi": "Мади",
    "Papa": "Папа",
    "Akhmet": "Ахмет",
    "Muratik": "Муратик",
    "Chihoon": "Чихун",
    "status:blocked": "статус:заблокировано",
    "status:working": "статус:в-работе",
    "status:in_progress": "статус:в-работе",
    "status:not_done": "статус:не-сделано",
    "status:done": "статус:готово",
    "проект:Satory-VKO-Factory": "проект:Фабрика-Satory-ВКО",
    "проект:Satory-AI": "проект:Satory-AI",
    "проект:Personal": "проект:Личное",
    "проект:Me": "проект:Мои-задачи",
    "проект:Family": "проект:Семья",
}

DEPARTMENT_VALUE_MAP = {
    "AI Factory": "AI-фабрика",
    "Delivery": "Доставка",
    "Revenue": "Продажи",
    "Operations": "Операции",
    "Personal Ops": "Личные-операции",
    "Legal": "Юристы",
    "Finance": "Финансы",
}

OWNER_VALUE_MAP = {
    "AI Factory": "AI-фабрика",
    "Madi": "Мади",
    "Daniyar": "Данияр",
    "Assyl": "Асыл",
    "Asyl": "Асыл",
    "Yerden": "Ерден",
    "Roza": "Роза",
    "Papa": "Папа",
    "Legal": "Юристы",
    "DK / AI Factory": "ДК / AI-фабрика",
}

PROTECTED_LATIN_TERMS = {
    "AGaaS",
    "AI",
    "API",
    "APK",
    "Air",
    "Anthropic",
    "Assyl",
    "Assylbek",
    "BDL",
    "BIN",
    "Camera",
    "Doctor",
    "Cerebro",
    "Claude",
    "Codex",
    "Company",
    "Daniyar",
    "DeepSeek",
    "ERAP",
    "FastAPI",
    "GBrain",
    "GitHub",
    "Gmail",
    "Google",
    "Hermes",
    "HS",
    "Inbox",
    "JSON",
    "KalkanCrypt",
    "Kaspi",
    "Keon",
    "Keon-A",
    "KEONA",
    "Kimi",
    "KZ",
    "KazTelePort",
    "Kazakhtelecom",
    "Kazcloud",
    "LangSmith",
    "LiteLLM",
    "Ltd",
    "Mac",
    "Madi",
    "Maru",
    "MCP",
    "Mergen",
    "Mergenovskii",
    "NCANode",
    "Negizone",
    "Notion",
    "NOUS",
    "Nous",
    "NVIDIA",
    "Obsidian",
    "OpenAI",
    "OpenBrain",
    "OpenClaw",
    "OpenRouter",
    "Opus",
    "PDF",
    "PDFs",
    "proof",
    "Promixx",
    "PS",
    "QMD",
    "Satory",
    "SmartBridge",
    "smoke",
    "Sonnet",
    "SPECTRA",
    "Tesla",
    "Telegram",
    "Todoist",
    "VAR",
    "VKO",
    "VPS",
}

URL_RE = re.compile(r"https?://\S+")
MARKDOWN_URL_RE = re.compile(r"\]\((https?://[^)]+)\)")
DOMAIN_RE = re.compile(r"\b[\w.-]+\.(?:ai|com|io|kz|md|net|org|ru|so)\b", re.IGNORECASE)
PATH_RE = re.compile(r"(?<!\w)(?:~?/|/)?(?:[\w .()_-]+/)+[\w .()_-]+")
FILE_RE = re.compile(r"\b[\w .()_-]+\.(?:csv|docx|json|log|md|pdf|png|py|sh|toml|txt|xlsx|yaml|yml)\b", re.IGNORECASE)
SOURCE_SLUG_RE = re.compile(
    r"\b(?:AUDIT|GOAL|HANDOFF|LEASE|PLAN|PROOF|SKILL|SOURCE|TASK-RESULT|pages|source|task-result)-[A-Za-z0-9_-]+\b",
    re.IGNORECASE,
)
EVIDENCE_REF_RE = re.compile(
    r"(?:[\w .()_-]+/)+[\w .()_-]+\.(?:csv|docx|json|log|md|pdf|png|py|sh|toml|txt|xlsx|yaml|yml)|"
    r"\b(?:AUDIT|GOAL|HANDOFF|LEASE|PLAN|PROOF|SKILL|SOURCE|TASK-RESULT)-[A-Za-z0-9_.-]+\b",
    re.IGNORECASE,
)
LATIN_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'_-]{2,}\b")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
DEFAULT_LLM_URL = os.environ.get("TODOIST_RUSSIANIZE_LLM_URL", "https://openrouter.ai/api/v1/chat/completions")
DEFAULT_MODEL = os.environ.get("TODOIST_RUSSIANIZE_MODEL", "deepseek/deepseek-v4-flash")


class TranslationError(RuntimeError):
    pass


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def load_env(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path or not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def provider_key_order(api_url: str) -> tuple[str, ...]:
    lowered = str(api_url or "").lower()
    if "openrouter.ai" in lowered:
        return ("OPENROUTER_API_KEY", "LITELLM_MASTER_KEY", "OPENAI_API_KEY")
    if "api.openai.com" in lowered:
        return ("OPENAI_API_KEY", "LITELLM_MASTER_KEY", "OPENROUTER_API_KEY")
    return ("LITELLM_MASTER_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")


def litellm_key(env_file: Path | None, litellm_env_file: Path | None, api_url: str = DEFAULT_LLM_URL) -> str:
    key_order = provider_key_order(api_url)
    for key in key_order:
        if os.environ.get(key):
            return str(os.environ[key])
    merged: dict[str, str] = {}
    merged.update(load_env(env_file))
    merged.update(load_env(litellm_env_file))
    for key in key_order:
        if merged.get(key):
            return str(merged[key])
    raise TranslationError("no LiteLLM/OpenRouter/OpenAI key found")


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def curl_post_json(api_url: str, body: dict[str, Any], api_key: str, timeout: int) -> dict[str, Any]:
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--max-time",
        str(timeout),
        "-X",
        "POST",
        api_url,
        "-H",
        "Content-Type: application/json",
        "-H",
        f"Authorization: Bearer {api_key}",
        "--data-binary",
        "@-",
    ]
    completed = subprocess.run(
        command,
        input=json.dumps(body).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        detail = (stdout + "\n" + stderr).strip()[:800]
        raise TranslationError(f"LLM curl request failed: {detail}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise TranslationError(f"LLM curl returned non-JSON payload: {stdout[:800]}") from exc


def normalize_space(text: str) -> str:
    return re.sub(r"[ \t]+", " ", str(text or "")).strip()


def strip_json_fence(text: str) -> str:
    clean = text.strip().lstrip("\ufeff")
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def extract_json_array(text: str) -> str:
    clean = strip_json_fence(text)
    if clean.startswith("["):
        return clean
    start = clean.find("[")
    end = clean.rfind("]")
    if start >= 0 and end > start:
        return clean[start : end + 1]
    return clean


def visible_latin_words(text: str) -> list[str]:
    clean = URL_RE.sub(" ", str(text or ""))
    clean = re.sub(r"`[^`]+`", " ", clean)
    clean = PATH_RE.sub(" ", clean)
    clean = FILE_RE.sub(" ", clean)
    clean = DOMAIN_RE.sub(" ", clean)
    clean = SOURCE_SLUG_RE.sub(" ", clean)
    words = []
    protected = {term.casefold() for term in PROTECTED_LATIN_TERMS}
    for match in LATIN_WORD_RE.finditer(clean):
        word = match.group(0).strip("_-")
        if not word:
            continue
        folded = word.casefold()
        if folded in protected:
            continue
        if re.fullmatch(r"[A-Z0-9_-]+", word):
            continue
        if re.fullmatch(r"[a-f0-9]{6,}", word, flags=re.IGNORECASE):
            continue
        words.append(word)
    return words


def needs_translation(text: str) -> bool:
    return bool(visible_latin_words(text))


def needs_note_translation(text: str) -> bool:
    """Translate comments only when they are English-dominant.

    Human operational comments that are already Russian but contain product
    names or a few Latin terms should be turned into work, not echoed back as a
    "Russian version" correction.
    """
    return needs_translation(text) and not CYRILLIC_RE.search(str(text or ""))


def evidence_refs(text: str) -> list[str]:
    refs = []
    for match in EVIDENCE_REF_RE.finditer(str(text or "")):
        ref = match.group(0).strip().strip(".,;:)]}")
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def acceptable_translation(original: str, translated: str) -> bool:
    original_terms = visible_latin_words(original)
    translated_terms = visible_latin_words(translated)
    for ref in evidence_refs(original):
        if ref not in translated:
            return False
    if CYRILLIC_RE.search(original) and not CYRILLIC_RE.search(translated):
        return False
    if CYRILLIC_RE.search(original) and len(translated_terms) > max(len(original_terms) + 2, 4):
        return False
    return True


def protect_urls(original: str, translated: str) -> str:
    result = translated
    for url in URL_RE.findall(original):
        if url not in result:
            result = f"{result} {url}".strip()
    return result


def label_target(name: str) -> str | None:
    if name in LABEL_NAME_MAP:
        return LABEL_NAME_MAP[name]
    if name.startswith("отдел:"):
        value = name.split(":", 1)[1]
        return f"отдел:{DEPARTMENT_VALUE_MAP.get(value, value)}"
    if name.startswith("исполнитель:"):
        value = name.split(":", 1)[1]
        return f"исполнитель:{OWNER_VALUE_MAP.get(value, value)}"
    if name.startswith("проект:"):
        value = name.split(":", 1)[1].replace("-", " ")
        mapped = PROJECT_NAME_MAP.get(value)
        if mapped:
            return "проект:" + clean_label_token(mapped)
    if name in {"проект:Дом---стройка", "проект:Корея---торговля"}:
        return name.replace("---", "-")
    if name.startswith("подпроект:Mergen ERAP receiver"):
        return "подпроект:Mergen-ERAP-приемник"
    return None


def clean_label_token(value: str) -> str:
    return re.sub(r"[^\wА-Яа-яЁё]+", "-", value, flags=re.UNICODE).strip("-")[:40] or "General"


def unique_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_translation_payload(raw: str) -> dict[str, str]:
    payload = json.loads(extract_json_array(raw))
    if isinstance(payload, dict) and isinstance(payload.get("translations"), list):
        payload = payload["translations"]
    elif isinstance(payload, dict) and payload.get("id") and (payload.get("ru") or payload.get("text")):
        payload = [payload]
    if not isinstance(payload, list):
        raise TranslationError("translation response is not a JSON array")
    result: dict[str, str] = {}
    for row in payload:
        if not isinstance(row, dict):
            continue
        ident = str(row.get("id") or "")
        ru = row.get("ru", row.get("text"))
        if ident and isinstance(ru, str) and ru.strip():
            result[ident] = normalize_space(ru)
    return result


def single_translation_fallback(raw: str, original: str) -> str | None:
    clean = strip_json_fence(raw)
    if not clean or clean.startswith("{") or clean.startswith("["):
        return None
    clean = re.sub(r"^(?:вот\s+перевод|перевод|translation|ru)\s*[:：-]\s*", "", clean, flags=re.IGNORECASE).strip()
    clean = clean.strip(" \t\r\n\"'“”«»")
    if not CYRILLIC_RE.search(clean):
        return None
    if len(clean) > max(200, len(original) * 5):
        return None
    return normalize_space(clean)


def translate_batch(
    entries: list[dict[str, str]],
    *,
    model: str,
    api_url: str,
    api_key: str,
    timeout: int,
) -> dict[str, str]:
    system = (
        "You translate Todoist task text for a Russian-speaking Kazakhstan team. "
        "Return only a JSON array of objects with the same id and a ru field. "
        "Translate user-facing English or transliterated English into natural Russian. "
        "Preserve URLs, IDs, dates, money amounts, Todoist/GitHub/Notion/Obsidian/gbrain/OpenBrain/OpenClaw/"
        "LangSmith/LiteLLM/NCANode/ERAP/KEONA/SPECTRA/Satory product names, and source slugs. "
        "Do not add facts, owners, links, or context that are not present."
    )
    user = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": max(512, min(4096, len(user) // 2 + 800)),
    }
    req = urllib.request.Request(
        api_url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:600]
        raise TranslationError(f"LLM HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        message = str(exc)
        if api_url.startswith("https://") and ("CERTIFICATE_VERIFY_FAILED" in message or "[SSL:" in message):
            payload = curl_post_json(api_url, body, api_key, timeout)
        else:
            raise TranslationError(f"LLM request failed: {exc}") from exc
    try:
        content = payload["choices"][0]["message"]["content"]
    except Exception as exc:
        raise TranslationError(f"unexpected LLM payload: {str(payload)[:600]}") from exc
    try:
        translations = parse_translation_payload(str(content))
    except Exception as exc:
        if len(entries) == 1:
            fallback = single_translation_fallback(str(content), entries[0].get("text", ""))
            if fallback:
                translations = {entries[0]["id"]: fallback}
            else:
                raise exc
        else:
            raise exc
    missing = [entry["id"] for entry in entries if entry["id"] not in translations]
    if missing:
        raise TranslationError(f"translation response missing ids: {missing[:10]}")
    return translations


def translate_entries(
    entries: list[dict[str, str]],
    *,
    model: str,
    api_url: str,
    api_key: str,
    batch_size: int,
    timeout: int,
    sleep: float,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    translations: dict[str, str] = {}
    errors: list[dict[str, Any]] = []
    for start in range(0, len(entries), batch_size):
        batch = entries[start : start + batch_size]
        print(f"translation_batch start={start} count={len(batch)}", file=sys.stderr, flush=True)
        try:
            translations.update(translate_batch(batch, model=model, api_url=api_url, api_key=api_key, timeout=timeout))
            print(f"translation_batch done start={start}", file=sys.stderr, flush=True)
        except Exception as exc:
            print(f"translation_batch error start={start}: {exc}", file=sys.stderr, flush=True)
            if len(batch) > 1:
                for offset, entry in enumerate(batch):
                    single_start = start + offset
                    print(f"translation_single start={single_start}", file=sys.stderr, flush=True)
                    try:
                        translations.update(translate_batch([entry], model=model, api_url=api_url, api_key=api_key, timeout=timeout))
                        print(f"translation_single done start={single_start}", file=sys.stderr, flush=True)
                    except Exception as single_exc:
                        errors.append({"start": single_start, "count": 1, "id": entry.get("id"), "error": str(single_exc)})
                        print(f"translation_single error start={single_start}: {single_exc}", file=sys.stderr, flush=True)
                    time.sleep(sleep)
            else:
                errors.append({"start": start, "count": len(batch), "id": batch[0].get("id") if batch else None, "error": str(exc)})
        time.sleep(sleep)
    return translations, errors


def sync(client: Todoist) -> dict[str, Any]:
    return client.sync()


def active_objects(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    payload = filter_satory_sync(payload)
    projects = [p for p in payload.get("projects", []) if isinstance(p, dict) and active_project(p)]
    sections = [s for s in payload.get("sections", []) if isinstance(s, dict) and active_section(s)]
    labels = [l for l in payload.get("labels", []) if isinstance(l, dict) and not l.get("is_deleted")]
    items = [i for i in payload.get("items", []) if isinstance(i, dict) and active_item(i)]
    return projects, sections, labels, items


def active_notes(payload: dict[str, Any], active_item_ids: set[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for note in payload.get("notes", []):
        if not isinstance(note, dict) or note.get("is_deleted"):
            continue
        item_id = str(note.get("item_id") or note.get("parent_id") or "")
        if item_id and item_id not in active_item_ids:
            continue
        result.append(note)
    return result


def build_plan(payload: dict[str, Any], translations: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    projects, sections, _labels, items = active_objects(payload)
    plan: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for project in projects:
        old = str(project.get("name") or "")
        new = PROJECT_NAME_MAP.get(old)
        if new and new != old:
            plan.append({"action": "update_project", "id": str(project["id"]), "before": old, "after": new})

    for section in sections:
        old = str(section.get("name") or "")
        new = SECTION_NAME_MAP.get(old)
        if new and new != old:
            plan.append({"action": "update_section", "id": str(section["id"]), "before": old, "after": new})

    for item in items:
        task_id = str(item.get("id") or "")
        update: dict[str, Any] = {}
        before: dict[str, Any] = {}

        content = str(item.get("content") or "")
        content_key = f"task:{task_id}:content"
        translated_content = translations.get(content_key)
        if translated_content:
            translated_content = protect_urls(content, translated_content)
            if not acceptable_translation(content, translated_content):
                skipped.append({"action": "update_task", "id": task_id, "field": "content", "before": content, "after": translated_content, "reason": "translation would regress Russian text"})
            elif translated_content != content:
                update["content"] = translated_content
                before["content"] = content

        description = str(item.get("description") or "")
        description_key = f"task:{task_id}:description"
        translated_description = translations.get(description_key)
        if translated_description:
            translated_description = protect_urls(description, translated_description)
            if not acceptable_translation(description, translated_description):
                skipped.append({"action": "update_task", "id": task_id, "field": "description", "before": description, "after": translated_description, "reason": "translation would regress Russian text"})
            elif translated_description != description:
                update["description"] = translated_description
                before["description"] = description

        old_labels = labels_for(item)
        new_labels = unique_preserve_order([label_target(label) or label for label in old_labels])
        if new_labels != old_labels:
            update["labels"] = new_labels
            before["labels"] = old_labels

        if update:
            plan.append({"action": "update_task", "id": task_id, "before": before, "after": update})

    active_item_ids = {str(item.get("id")) for item in items}
    for note in active_notes(payload, active_item_ids):
        note_id = str(note.get("id") or "")
        content = str(note.get("content") or "")
        translated_content = translations.get(f"note:{note_id}:content")
        if not note_id or not translated_content:
            continue
        if not needs_note_translation(content):
            skipped.append({"action": "update_note", "id": note_id, "before": content, "after": translated_content, "reason": "mixed Russian human comment; do not echo translation"})
            continue
        translated_content = protect_urls(content, translated_content)
        if not acceptable_translation(content, translated_content):
            skipped.append({"action": "update_note", "id": note_id, "before": content, "after": translated_content, "reason": "translation would regress Russian text"})
        elif translated_content != content:
            plan.append({"action": "update_note", "id": note_id, "item_id": str(note.get("item_id") or note.get("parent_id") or ""), "before": content, "after": translated_content})

    residual = {
        "skipped": skipped,
        "translation_errors": [],
    }
    return plan, residual


def candidate_entries(payload: dict[str, Any]) -> list[dict[str, str]]:
    _projects, _sections, _labels, items = active_objects(payload)
    active_item_ids = {str(item.get("id")) for item in items}
    entries: list[dict[str, str]] = []
    for item in items:
        task_id = str(item.get("id") or "")
        content = normalize_space(str(item.get("content") or ""))
        if task_id and content and needs_translation(content):
            entries.append({"id": f"task:{task_id}:content", "text": content})
        description = normalize_space(str(item.get("description") or ""))
        if task_id and description and needs_translation(description):
            entries.append({"id": f"task:{task_id}:description", "text": description})
    for note in active_notes(payload, active_item_ids):
        note_id = str(note.get("id") or "")
        content = normalize_space(str(note.get("content") or ""))
        if note_id and content and needs_note_translation(content):
            entries.append({"id": f"note:{note_id}:content", "text": content})
    return entries


def apply_plan(client: Todoist, plan: list[dict[str, Any]], sleep: float) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for item in plan:
        action = item["action"]
        if action == "update_project":
            client.request("POST", f"/projects/{item['id']}", json={"name": item["after"]})
        elif action == "update_section":
            client.request("POST", f"/sections/{item['id']}", json={"name": item["after"]})
        elif action == "update_note":
            try:
                client.request("POST", f"/comments/{item['id']}", json={"content": item["after"]})
            except requests.HTTPError as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status == 400:
                    counts["update_note_immutable_skipped"] += 1
                    time.sleep(sleep)
                    continue
                raise
        elif action == "update_task":
            client.update_task(item["id"], item["after"])
        else:
            raise RuntimeError(f"unknown action: {action}")
        counts[action] += 1
        time.sleep(sleep)
    return dict(counts)


def english_exposure(payload: dict[str, Any]) -> dict[str, Any]:
    projects, sections, labels, items = active_objects(payload)
    active_item_ids = {str(item.get("id")) for item in items}
    categories = {
        "projects": [(str(p.get("id")), str(p.get("name") or "")) for p in projects],
        "sections": [(str(s.get("id")), str(s.get("name") or "")) for s in sections],
        "labels": [(str(l.get("id")), str(l.get("name") or "")) for l in labels],
        "task_titles": [(str(i.get("id")), str(i.get("content") or "")) for i in items],
        "task_descriptions": [(str(i.get("id")), str(i.get("description") or "")) for i in items if str(i.get("description") or "").strip()],
        "comments": [(str(n.get("id")), str(n.get("content") or "")) for n in active_notes(payload, active_item_ids)],
    }
    result: dict[str, Any] = {}
    for name, rows in categories.items():
        hits = [
            {"id": ident, "text": text, "terms": visible_latin_words(text)[:12]}
            for ident, text in rows
            if visible_latin_words(text)
        ]
        result[name] = {"total": len(rows), "with_english": len(hits), "samples": hits[:20]}
    return result


def render_audit(
    *,
    captured_at: str,
    before: dict[str, Any],
    after: dict[str, Any] | None,
    plan: list[dict[str, Any]],
    applied: dict[str, int] | None,
    translation_errors: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    dry_run: bool,
) -> str:
    lines = [
        "---",
        "type: audit",
        "id: AUDIT-todoist-russianization",
        'title: "Todoist Russianization Audit"',
        f"date: {captured_at[:10]}",
        "status: active",
        "tags: [audit, todoist, russian, control-plane, notion, gbrain]",
        "---",
        "",
        "# Аудит русификации Todoist",
        "",
        f"- Время: `{captured_at}`",
        f"- Режим dry-run: `{dry_run}`",
        f"- Действий в плане: `{len(plan)}`",
        f"- Применено: `{applied or {}}`",
        f"- Ошибок перевода: `{len(translation_errors)}`",
        f"- Пропущено безопасно: `{len(skipped)}`",
        "",
        "## Root Cause",
        "",
        "Предыдущий контроль Todoist проверял структуру: проект, раздел, владелец, отдел, метки, приоритет и наличие реального контекста. Он не проверял язык пользовательского текста. Поэтому доска была операционно чистой, но для русскоязычной команды оставалась неудобной.",
        "",
        "## Exposure Before",
        "",
        "```json",
        json.dumps(before, ensure_ascii=False, indent=2)[:12000],
        "```",
    ]
    if after is not None:
        lines.extend(["", "## Exposure After", "", "```json", json.dumps(after, ensure_ascii=False, indent=2)[:12000], "```"])
    lines.extend(["", "## Applied / Planned Counts", ""])
    counts = collections.Counter(item["action"] for item in plan)
    if counts:
        for action, count in sorted(counts.items()):
            lines.append(f"- `{action}`: `{count}`")
    else:
        lines.append("- deterministic update plan is empty")
    if skipped:
        lines.extend(["", "## Safe Skips", "", "```json", json.dumps(skipped[:80], ensure_ascii=False, indent=2), "```"])
    if translation_errors:
        lines.extend(["", "## Translation Errors", "", "```json", json.dumps(translation_errors, ensure_ascii=False, indent=2), "```"])
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "Не добавлялись выдуманные описания. Пустые описания остались пустыми до появления реального источника. Все изменения обратимы по JSON-плану: в каждом `update_task` сохранено поле `before`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    *,
    plan: list[dict[str, Any]],
    before: dict[str, Any],
    after: dict[str, Any] | None,
    applied: dict[str, int] | None,
    translation_errors: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, str]:
    stamp = now_kzt().strftime("%Y-%m-%d-%H%M%S")
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    plan_path = AUDIT_DIR / f"todoist-russianization-plan-{stamp}.json"
    audit_path = AUDIT_DIR / f"AUDIT-todoist-russianization-{stamp}.md"
    captured_at = now_kzt().isoformat()
    plan_payload = {
        "captured_at": captured_at,
        "dry_run": dry_run,
        "plan": plan,
        "applied": applied,
        "before": before,
        "after": after,
        "translation_errors": translation_errors,
        "skipped": skipped,
    }
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    audit_path.write_text(
        render_audit(
            captured_at=captured_at,
            before=before,
            after=after,
            plan=plan,
            applied=applied,
            translation_errors=translation_errors,
            skipped=skipped,
            dry_run=dry_run,
        ),
        encoding="utf-8",
    )
    return {"plan_json": str(plan_path), "audit_md": str(audit_path)}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--litellm-env-file", type=Path, default=Path.home() / "nous-agaas" / "litellm" / ".env")
    parser.add_argument("--litellm-url", default=DEFAULT_LLM_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--max-translation-entries", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    client = Todoist(token_from_env(args.env_file))
    before_payload = sync(client)
    before_exposure = english_exposure(before_payload)
    entries = candidate_entries(before_payload)
    if args.max_translation_entries:
        entries = entries[: max(0, args.max_translation_entries)]
    translations: dict[str, str] = {}
    translation_errors: list[dict[str, Any]] = []
    if entries and not args.no_llm:
        api_key = litellm_key(args.env_file, args.litellm_env_file, args.litellm_url)
        translations, translation_errors = translate_entries(
            entries,
            model=args.model,
            api_url=args.litellm_url,
            api_key=api_key,
            batch_size=max(1, args.batch_size),
            timeout=args.timeout,
            sleep=args.sleep,
        )
    plan, residual = build_plan(before_payload, translations)
    translation_errors.extend(residual["translation_errors"])
    skipped = residual["skipped"]
    applied = None
    after_exposure = None
    if args.apply and translation_errors:
        applied = None
        after_exposure = None
    elif args.apply and plan:
        applied = apply_plan(client, plan, args.sleep)
        after_payload = sync(client)
        after_exposure = english_exposure(after_payload)
    artifacts = write_artifacts(
        plan=plan,
        before=before_exposure,
        after=after_exposure,
        applied=applied,
        translation_errors=translation_errors,
        skipped=skipped,
        dry_run=not args.apply,
    )
    payload = {
        "status": "done" if not translation_errors else "not_done",
        "dry_run": not args.apply,
        "translation_candidates": len(entries),
        "translations": len(translations),
        "plan_count": len(plan),
        "plan_counts": dict(collections.Counter(item["action"] for item in plan)),
        "applied": applied,
        "before": before_exposure,
        "after": after_exposure,
        "translation_errors": translation_errors,
        "skipped": skipped[:50],
        "artifacts": artifacts,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
