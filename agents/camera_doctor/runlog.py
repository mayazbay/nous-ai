"""agents.camera_doctor.runlog — JSONL append-only run-log per AUDIT-060 DevEx #2+#7.

Phase 3 Task 3.3 of PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1.

Every Camera Doctor run appends ONE line to:
    <log_dir>/<YYYY-MM-DD>.jsonl   (daily-rotated)

The line carries the full reasoning trace so a future agent (or operator
debugging at 03:00 after a false alert) can reproduce what the run saw
without re-SSHing to VPS:

  - exact_sql:                 post-template-substitution SQL
  - exact_ssh_command:         exact ssh invocation used
  - raw_query_result_sample:   first 5 rows of result, verbatim
  - correlation_id:            matches Notion page + TG msg + PDF path
  - tg_msg_id, pdf_path:       cross-link to delivery artifacts
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "ts", "run_id", "ssh_rtt_ms", "query_ms", "rows_returned",
    "online_pct", "online_pct_p10_14d", "threshold",
    "decision", "alert_sent", "tg_msg_id", "pdf_path",
    "exact_sql", "exact_ssh_command", "raw_query_result_sample",
    "correlation_id",
)
RAW_SAMPLE_CAP = 5


def _now_iso(now: dt.datetime | None = None) -> str:
    n = now or dt.datetime.now(dt.timezone.utc)
    return n.isoformat()


def _date_key(now: dt.datetime | None = None) -> str:
    n = now or dt.datetime.now(dt.timezone.utc)
    return n.strftime("%Y-%m-%d")


def build_record(
    *,
    run_id: str,
    ssh_rtt_ms: int,
    query_ms: int,
    rows_returned: int,
    online_pct: float,
    online_pct_p10_14d: float,
    threshold: float,
    decision: str,
    alert_sent: bool,
    tg_msg_id: int | None,
    pdf_path: str | None,
    exact_sql: str,
    exact_ssh_command: str,
    raw_query_result_sample: list[dict[str, Any]],
    correlation_id: str,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Build a record dict with all required fields. Caps raw sample to RAW_SAMPLE_CAP."""
    if not isinstance(raw_query_result_sample, list):
        raw_query_result_sample = list(raw_query_result_sample or [])
    capped_sample = raw_query_result_sample[:RAW_SAMPLE_CAP]
    return {
        "ts": _now_iso(now),
        "run_id": run_id,
        "ssh_rtt_ms": int(ssh_rtt_ms),
        "query_ms": int(query_ms),
        "rows_returned": int(rows_returned),
        "online_pct": float(online_pct),
        "online_pct_p10_14d": float(online_pct_p10_14d),
        "threshold": float(threshold),
        "decision": decision,
        "alert_sent": bool(alert_sent),
        "tg_msg_id": tg_msg_id,
        "pdf_path": pdf_path,
        "exact_sql": exact_sql,
        "exact_ssh_command": exact_ssh_command,
        "raw_query_result_sample": capped_sample,
        "correlation_id": correlation_id,
    }


def append(record: dict[str, Any], log_dir: Path | str,
           now: dt.datetime | None = None) -> Path:
    """Append `record` as one JSONL line to <log_dir>/<YYYY-MM-DD>.jsonl.

    Creates `log_dir` if missing. Atomic per-line: file is opened in append
    mode and one full line (record + '\\n') is written per call.
    """
    log_dir = Path(log_dir).expanduser().resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{_date_key(now)}.jsonl"
    line = json.dumps(record, ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return path
