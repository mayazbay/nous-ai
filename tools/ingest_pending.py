#!/usr/bin/env python3
"""
Auto-ingest tool for raw/pending/

Watches /root/nous-agaas/wiki/raw/pending/ for new files. When one appears:
1. Read the file
2. Use Sonnet (cheap) to extract: title, summary (3-5 sentences), key entities mentioned, suggested wiki page type, suggested cross-references
3. Write a summary page to pages/sources/source-<slug>-<date>.md with frontmatter
4. Move the original from raw/pending/ to raw/processed/
5. Append entry to log.md
6. (Optional) suggest cross-reference updates to existing pages — but does NOT auto-modify existing pages, only flags

Independent of the main factory loop. Runs as systemd timer or cron, every 60s.
Cost: ~$0.01-0.05 per ingested source. Free when no files in pending/.

LESSON-058 + AUDIT-023 P1.6 implementation.
"""

import os
import sys
import re
import json
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/root/nous-agaas")
from dotenv import load_dotenv
load_dotenv("/root/nous-agaas/.env", override=True)

WIKI = Path("/root/nous-agaas/wiki")
RAW = WIKI / "raw"
PENDING = RAW / "pending"
PROCESSED = RAW / "processed"
SOURCES = WIKI / "pages" / "sources"
LOG = WIKI / "log.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ingest_pending")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s.lower())
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60].strip("-") or "untitled"


def gemini_transcribe_audio(file_path: Path) -> dict:
    """LESSON-059 follow-up: transcribe .m4a/.mp3/.wav via Gemini 2.5 Flash.
    Returns dict with transcript + summary + entities + actions.
    Cost: ~$0.01 per minute of audio.
    """
    import google.generativeai as genai
    import os as _os
    api_key = _os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    log.info(f"Uploading audio to Gemini: {file_path.name}")
    f = genai.upload_file(path=str(file_path))
    while f.state.name == "PROCESSING":
        time.sleep(2)
        f = genai.get_file(f.name)
    if f.state.name != "ACTIVE":
        raise RuntimeError(f"Gemini upload failed state: {f.state.name}")

    prompt = """Transcribe this audio recording in full. If speakers are speaking Russian or Kazakh, transcribe in original language.

After the transcript, output a JSON block with these keys:
{
  "title": "concise English title (max 80 chars)",
  "title_ru": "concise Russian title if applicable (max 80 chars)",
  "summary_en": "3-5 sentence English summary of the recording",
  "summary_ru": "3-5 sentence Russian summary if applicable",
  "duration_estimate_minutes": <integer>,
  "speakers": ["speaker 1 description", ...],
  "key_entities": ["Person/company name 1", ...],
  "key_actions": ["action item 1", ...],
  "key_decisions": ["decision 1", ...],
  "topics": ["topic 1", "topic 2"],
  "priority": "p0 | p1 | p2"
}

Output format:
## TRANSCRIPT
<full transcript>

## METADATA
<JSON object>"""

    resp = model.generate_content([f, prompt], request_options={"timeout": 600})
    text = resp.text

    # Parse out the JSON metadata block
    import re as _re, json as _json
    json_match = _re.search(r"\{[^{}]*\"title[^{}]*\}", text, _re.DOTALL)
    metadata = {}
    if json_match:
        try:
            metadata = _json.loads(json_match.group(0))
        except _json.JSONDecodeError:
            log.warning("Could not parse JSON metadata from Gemini response")

    return {
        "raw_response": text,
        "transcript": text.split("## METADATA")[0].replace("## TRANSCRIPT", "").strip() if "## TRANSCRIPT" in text else text,
        "metadata": metadata,
    }


def call_sonnet(prompt: str) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def ingest_one(file_path: Path) -> bool:
    """Ingest a single file from raw/pending/. Returns True on success."""
    log.info(f"Ingesting: {file_path.name}")

    suffix = file_path.suffix.lower()
    audio_exts = (".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac")
    text_exts = (".md", ".txt")

    audio_data = None
    if suffix in audio_exts:
        # Audio path: transcribe with Gemini Flash
        try:
            audio_data = gemini_transcribe_audio(file_path)
            content = audio_data["transcript"][:8000]
            log.info(f"Audio transcribed ({len(audio_data['transcript'])} chars)")
        except Exception as e:
            msg = str(e).lower()
            if "credit" in msg or "quota" in msg:
                log.error("Gemini API quota/credit issue. Skipping. File stays in pending/")
                return False
            log.error(f"Audio transcription failed: {e}")
            return False
    elif suffix in text_exts:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")[:8000]
        except Exception as e:
            log.error(f"Read failed: {e}")
            return False
    else:
        log.warning(f"Skipping unsupported file type: {file_path.name} ({suffix})")
        return False

    # Build prompt
    prompt = f"""You are ingesting a new source document into the Nous AGaaS / Spectra ITS wiki.
The wiki tracks government VMS / ERAP / Safe City work in Kazakhstan.

Source filename: {file_path.name}
Source content (first 8000 chars):
---
{content}
---

Output STRICTLY as JSON (no markdown, no commentary), with these keys:
{{
  "title": "Concise English title (max 80 chars)",
  "title_ru": "Concise Russian title (max 80 chars) — leave empty if source isn't Russian-context",
  "type": "source",
  "tags": ["tag1", "tag2"],
  "date": "YYYY-MM-DD",
  "summary_en": "3-5 sentence English summary of the document's contents and significance",
  "key_entities": ["Entity name 1", "Entity name 2"],
  "key_actions": ["action item 1", "action item 2"],
  "related_pages_to_update": ["page-stem-1", "page-stem-2"],
  "page_type_suggestion": "source | meeting | spec | progress | lesson | concept",
  "priority": "p0 | p1 | p2"
}}

Use 2026-04-07 as today's date. Be concise. Output ONLY the JSON object."""

    try:
        raw_json = call_sonnet(prompt)
    except Exception as e:
        msg = str(e).lower()
        if "credit balance is too low" in msg:
            log.error("Anthropic credits exhausted. Skipping ingest. File stays in pending/")
            return False
        log.error(f"Sonnet call failed: {e}")
        return False

    # Parse JSON
    try:
        json_match = re.search(r'\{.*\}', raw_json, re.DOTALL)
        if not json_match:
            log.error(f"No JSON in response: {raw_json[:200]}")
            return False
        meta = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        log.error(f"JSON parse failed: {e} | raw: {raw_json[:300]}")
        return False

    # Build wiki source page
    title = meta.get("title", file_path.stem)
    slug = slugify(title)
    date = meta.get("date", datetime.now().strftime("%Y-%m-%d"))
    page_id = f"INGEST-{date}-{slug.upper()[:30]}"
    out_filename = f"source-ingest-{date}-{slug}.md"
    out_path = SOURCES / out_filename

    # Don't overwrite existing
    if out_path.exists():
        out_filename = f"source-ingest-{date}-{slug}-{int(time.time())}.md"
        out_path = SOURCES / out_filename

    frontmatter = {
        "type": meta.get("type", "source"),
        "id": page_id,
        "title": meta.get("title", title),
        "tags": meta.get("tags", ["source", "auto-ingest"]),
        "date": date,
        "auto_ingested": True,
        "raw_source": f"raw/processed/{file_path.name}",
    }

    fm_lines = ["---"]
    for k, v in frontmatter.items():
        if isinstance(v, list):
            fm_lines.append(f"{k}: [{', '.join(repr(x) for x in v)}]")
        elif isinstance(v, bool):
            fm_lines.append(f"{k}: {str(v).lower()}")
        else:
            fm_lines.append(f"{k}: {v!r}" if isinstance(v, str) and ":" in v else f"{k}: {v}")
    fm_lines.append("---")
    fm = "\n".join(fm_lines)

    body_lines = [
        fm,
        "",
        f"# {title}",
        "",
        f"> **Auto-ingested 2026-04-07** from `raw/pending/{file_path.name}` by `tools/ingest_pending.py`",
        f"> Original moved to `raw/processed/{file_path.name}`",
        "",
    ]
    if meta.get("title_ru"):
        body_lines += [f"## Заголовок (RU)\n{meta['title_ru']}", ""]
    body_lines += [
        "## Summary",
        meta.get("summary_en", "_(no summary generated)_"),
        "",
        "## Key entities mentioned",
    ]
    for e in meta.get("key_entities", []) or ["_(none extracted)_"]:
        body_lines.append(f"- {e}")
    body_lines += ["", "## Key action items"]
    for a in meta.get("key_actions", []) or ["_(none extracted)_"]:
        body_lines.append(f"- [ ] {a}")
    body_lines += [
        "",
        "## Suggested cross-references (to be reviewed)",
        "These pages may need updating with content from this source. Manual review recommended:",
    ]
    for p in meta.get("related_pages_to_update", []) or ["_(none suggested)_"]:
        body_lines.append(f"- [[{p}]]")
    body_lines += [
        "",
        "## Priority",
        f"**{meta.get('priority', 'p2').upper()}**",
        "",
        "## Raw source",
        f"Original file preserved at `raw/processed/{file_path.name}` (immutable).",
        "",
        "## See also",
        "- [[index]]",
        "- [[CLAUDE]]",
    ]

    out_path.write_text("\n".join(body_lines))
    log.info(f"Wrote {out_path.name}")

    # Move raw file to processed/
    PROCESSED.mkdir(exist_ok=True)
    target = PROCESSED / file_path.name
    if target.exists():
        target = PROCESSED / f"{file_path.stem}-{int(time.time())}{file_path.suffix}"
    shutil.move(str(file_path), str(target))
    log.info(f"Moved raw to {target}")

    # Append to log.md
    log_entry = f"\n## [{date}] auto-ingest | {title} (from raw/pending/{file_path.name})\n"
    with LOG.open("a") as f:
        f.write(log_entry)


    # GBrain enrichment: create/update entity pages for detected entities
    entities = meta.get("key_entities", [])
    if entities:
        _enrich_path = "/root/nous-agaas/tools"
        if _enrich_path not in sys.path:
            sys.path.insert(0, _enrich_path)
        try:
            from gbrain_enrich import enrich_entity
            source_slug = out_filename.replace(".md", "")
            for entity_name in entities[:10]:
                try:
                    result = enrich_entity(
                        name=entity_name,
                        entity_type="person",
                        facts=[f"Mentioned in source: {title}"],
                        source=source_slug,
                    )
                    log.info(f"Enriched entity: {entity_name} -> {result['action']}")
                except Exception as e:
                    log.warning(f"Entity enrichment failed for {entity_name}: {e}")
        except ImportError as e:
            log.warning(f"GBrain enrichment not available: {e}")

    return True


def main():
    if not PENDING.exists():
        PENDING.mkdir(parents=True, exist_ok=True)
        log.info(f"Created {PENDING}")

    files = sorted(PENDING.glob("*"))
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]

    # LESSON-062: skip 0-byte files. They cause Anthropic 400 errors and burn API budget.
    # Move them to raw/unsorted/ so they are visible but not retried.
    UNSORTED = WIKI / "raw" / "unsorted"
    skipped_empty = []
    for f in list(files):
        try:
            if f.stat().st_size == 0:
                UNSORTED.mkdir(parents=True, exist_ok=True)
                target = UNSORTED / f"empty-{f.name}"
                shutil.move(str(f), str(target))
                skipped_empty.append(f.name)
                files.remove(f)
        except Exception as e:
            log.warning(f"empty-check failed for {f.name}: {e}")
    if skipped_empty:
        log.info(f"Moved {len(skipped_empty)} empty file(s) to raw/unsorted/: {skipped_empty}")

    if not files:
        log.debug("Nothing to ingest")
        return 0

    log.info(f"Found {len(files)} file(s) in pending/")
    successes = 0
    for f in files:
        if ingest_one(f):
            successes += 1

    log.info(f"Ingested {successes}/{len(files)} files")
    return 0 if successes == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
