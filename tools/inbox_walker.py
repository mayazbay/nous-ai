#!/usr/bin/env python3
"""inbox_walker.py — Gap 3 of telegram-ingest-pipeline.

Walks pages/inbox/YYYY-MM-DD/*.md and elevates any note with intent=unknown
by calling the shared intent_classifier + telegram_ingest_persist.classify
side-effect router. Idempotent: skips notes with intent != unknown.

Designed to run on Air via launchd (com.nous.inbox-walker, hourly :15).
Acts as the safety net for Phase 2.5 misses (LiteLLM down, /ask never fired,
manual-edit inbox notes, etc).

Usage:
  python3 tools/inbox_walker.py                # walks today + yesterday
  python3 tools/inbox_walker.py --days 7       # walks last 7 days
  python3 tools/inbox_walker.py --dry-run      # logs verdicts, no side-effects
  python3 tools/inbox_walker.py --limit 5      # cap per-run cost
  python3 tools/inbox_walker.py --now          # alias for cron-fired form

Exit code: ALWAYS 0 (no cron retry loops on transient classifier failures).
Log: ~/nous-agaas/logs/inbox_walker.log
"""
import argparse
import datetime
import json
import logging
import os
import re
import sys
from pathlib import Path

LOG_PATH = Path.home() / "nous-agaas" / "logs" / "inbox_walker.log"


def _vault_root() -> Path:
    env = os.environ.get("NOUS_WIKI") or os.environ.get("NOUS_VAULT_ROOT")
    if env and Path(env).exists():
        return Path(env)
    script_relative = Path(__file__).parent.parent
    if (script_relative / "pages").is_dir():
        return script_relative
    for cand in [
        Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous"),
        Path("/Users/madia/nous-agaas/wiki"),
        Path("/root/nous-agaas/wiki"),
    ]:
        if (cand / "pages").is_dir():
            return cand
    return script_relative


def _read_intent(fpath: Path) -> str:
    """Return current intent value from frontmatter, or 'unknown' if not parseable."""
    try:
        text = fpath.read_text(encoding="utf-8")
    except Exception:
        return "unknown"
    m = re.search(r'^intent:\s*(\S+)\s*$', text, re.MULTILINE)
    if not m:
        return "unknown"
    return m.group(1).strip().strip('"').strip("'").lower()


def _read_body(fpath: Path) -> str:
    """Extract '# Original message' body from inbox note."""
    try:
        text = fpath.read_text(encoding="utf-8")
    except Exception:
        return ""
    m = re.search(r'#\s*Original message\s*\n+(.+?)(?:\n+#\s|\Z)', text, re.DOTALL)
    return m.group(1).strip() if m else ""


def collect_candidates(vault: Path, days: int) -> list[Path]:
    """Return list of inbox files with intent=unknown across last `days` days."""
    today = datetime.date.today()
    out = []
    for offset in range(days):
        d = today - datetime.timedelta(days=offset)
        day_dir = vault / "pages" / "inbox" / d.isoformat()
        if not day_dir.is_dir():
            continue
        for f in sorted(day_dir.glob("*-unknown.md")):
            if _read_intent(f) == "unknown":
                out.append(f)
    return out


def process_one(fpath: Path, vault: Path, dry_run: bool, log: logging.Logger) -> dict:
    """Classify one file. Returns result dict for logging."""
    sys.path.insert(0, str(vault / "tools"))
    try:
        import intent_classifier as _ic
        import telegram_ingest_persist as _tip
    finally:
        try:
            sys.path.remove(str(vault / "tools"))
        except ValueError:
            pass

    body = _read_body(fpath)
    slug = fpath.relative_to(vault).as_posix().removesuffix(".md")
    if not body:
        return {"slug": slug, "status": "skip-empty-body"}

    verdict = _ic.classify(body)
    intent = verdict.get("intent", "unknown")
    conf = float(verdict.get("confidence", 0.0))
    rationale = verdict.get("rationale", "")
    model = verdict.get("classifier_model", "deepseek-v4-flash")

    if intent == "unknown" or conf < 0.5:
        return {"slug": slug, "status": "skip-low-conf",
                "intent": intent, "confidence": conf, "rationale": rationale}

    if dry_run:
        return {"slug": slug, "status": "dry-run",
                "intent": intent, "confidence": conf, "rationale": rationale}

    try:
        result = _tip.classify(slug, intent, conf, rationale, classifier_model=model)
        return {"slug": slug, "status": "elevated",
                "new_slug": result.get("slug"), "intent": intent,
                "confidence": conf, "side_effects": result.get("side_effects")}
    except Exception as e:
        log.warning(f"persist failed for {slug}: {type(e).__name__}: {e}")
        return {"slug": slug, "status": "persist-error",
                "error": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2,
                    help="walk last N days of inbox (default: 2 = today + yesterday)")
    ap.add_argument("--dry-run", action="store_true",
                    help="classify but skip side-effects")
    ap.add_argument("--limit", type=int, default=20,
                    help="cap items processed per run (default: 20)")
    ap.add_argument("--now", action="store_true",
                    help="alias used by launchd; same as default invocation")
    ap.add_argument("--vault", type=str, default=None, help="override vault root")
    args = ap.parse_args()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_PATH),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("inbox_walker")

    vault = Path(args.vault) if args.vault else _vault_root()
    if not (vault / "pages").is_dir():
        log.error(f"no vault found at {vault}")
        print(json.dumps({"status": "no-vault", "vault": str(vault)}))
        return 0

    candidates = collect_candidates(vault, args.days)
    log.info(f"found {len(candidates)} unknown-intent inbox notes (days={args.days})")

    results = []
    for fpath in candidates[: args.limit]:
        try:
            r = process_one(fpath, vault, args.dry_run, log)
        except Exception as e:
            slug = fpath.relative_to(vault).as_posix().removesuffix(".md")
            r = {"slug": slug, "status": "process-error",
                 "error": f"{type(e).__name__}: {e}"}
            log.warning(f"process_one crashed on {slug}: {type(e).__name__}: {e}")
        results.append(r)
        log.info(json.dumps(r, ensure_ascii=False))

    summary = {
        "vault": str(vault),
        "days": args.days,
        "dry_run": args.dry_run,
        "found": len(candidates),
        "processed": len(results),
        "elevated": sum(1 for r in results if r.get("status") == "elevated"),
        "skipped_low_conf": sum(1 for r in results if r.get("status") == "skip-low-conf"),
        "errors": sum(1 for r in results if r.get("status") == "persist-error"),
    }
    log.info(f"summary: {json.dumps(summary)}")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
